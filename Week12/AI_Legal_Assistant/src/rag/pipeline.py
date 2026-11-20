"""
Day 2, Task 4: answer a legal question with verified citations.

    question -> retrieve top 5 passages (a Task 3 configuration)
             -> Gemini answer: short answer, explanation, citations with quotes (src/rag/answer.py)
             -> code verification of every citation (src/rag/verify.py)
             -> only verified citations are shown; none left -> "No sufficient source found"

Used by `python main.py --ask "..."` and by the demo in evaluations/demo_answers.py.
"""

from functools import lru_cache
from typing import Dict, List, Optional

from src.rag.answer import NO_SOURCE, answer_question, is_refusal, source_label
from src.rag.verify import _document, parse_reference, verify_answer

DEFAULT_CONFIG = "rerank"


@lru_cache(maxsize=4)
def _retriever(config: str):
    from src.rag.advanced import CONFIGS, AdvancedRetriever
    if config == "naive":
        from src.rag.retrieval import NaiveDenseRetriever
        return NaiveDenseRetriever()
    return AdvancedRetriever(config, **CONFIGS[config])


@lru_cache(maxsize=1)
def _llm():
    from src.llm.gemini_client import GeminiClient
    return GeminiClient()


def _section_title(document_id: str, label: str) -> Optional[str]:
    doc = _document(document_id) or {}
    for chapter in doc.get("chapters", []):
        for section in chapter["sections"]:
            if section["section_number"] == label:
                return section["title"]
    return None


def _checked_answer(question: str, results: List[Dict]):
    """Draft -> citation verification -> conclusion check; one redraft if the conclusion does not follow
    from the sources; withheld if it still does not."""
    from src.rag.answer import CitedAnswer
    from src.rag.conclusion_check import check_conclusion

    draft = answer_question(_llm(), question, results)
    verified, report = verify_answer(draft, results)
    check = check_conclusion(_llm(), question, verified, results)
    info = {"verdict": check.verdict, "issue": check.issue, "redrafted": False, "withheld": False, "first_issue": ""}
    if check.verdict == "not_supported":
        info.update(redrafted=True, first_issue=check.issue)
        second = answer_question(_llm(), question, results, review_note=check.issue)
        verified, report = verify_answer(second, results)
        check = check_conclusion(_llm(), question, verified, results)
        info.update(verdict=check.verdict, issue=check.issue)
        if check.verdict == "not_supported":
            info["withheld"] = True
            verified = CitedAnswer(short_answer=NO_SOURCE)
    return draft, verified, report, info


def answer_with_citations(question: str, config: str = DEFAULT_CONFIG, top_k: int = 5) -> Dict:
    results = _retriever(config).retrieve(question, top_k=top_k)
    draft, verified, report, conclusion = _checked_answer(question, results)

    citations: List[Dict] = []
    for citation in verified.citations:
        result = results[citation.source - 1]
        meta = result.get("metadata", {})
        kind, label = parse_reference(citation.section_or_paragraph)
        citations.append({
            "source": citation.source,
            "act_or_case": citation.act_or_case,
            # a page-level citation (Urdu laws) shows the page once, from the metadata below
            "reference": label if kind == "section" else (f"para {label}" if kind == "paragraph" else
                                                         ("" if kind == "page" else citation.section_or_paragraph)),
            "title": _section_title(result["document_id"], label) if kind == "section" else None,
            "page": meta.get("page"),
            "document_id": result["document_id"],
            "quote": citation.quote,
        })
    return {
        "question": question,
        "config": config,
        "short_answer": verified.short_answer,
        "explanation": "" if is_refusal(verified) else verified.explanation,
        "citations": citations,
        "removed_citations": [{"citation": f"{r['act_or_case']} | {r['section_or_paragraph']}", "reason": r["reason"]}
                              for r in report if not r["verified"]],
        "draft_refused": is_refusal(draft),
        "conclusion_check": conclusion,
        "retrieved": [{"rank": i, "source": source_label(r), "document_id": r["document_id"]}
                      for i, r in enumerate(results, start=1)],
    }


def format_answer(result: Dict) -> str:
    lines = ["=" * 80, f"QUESTION: {result['question']}", "=" * 80, ""]
    check = result.get("conclusion_check") or {}
    if check.get("withheld"):
        lines += [NO_SOURCE + ".", "",
                  "(An answer was drafted twice, but a review found its conclusion does not follow from the sources:)",
                  f"  {check['issue']}"]
    elif result["short_answer"] == NO_SOURCE:
        lines.append(NO_SOURCE + ".")
        if check.get("redrafted"):
            lines += ["", f"(A first answer was rejected by the conclusion check: {check['first_issue']})"]
        if result["removed_citations"]:
            lines += ["", "(The model drafted an answer, but none of its citations passed verification:)"]
            lines += [f"  - {r['citation']}: {r['reason']}" for r in result["removed_citations"]]
    else:
        lines += ["SHORT ANSWER", f"  {result['short_answer']}", "", "EXPLANATION", f"  {result['explanation']}", "",
                  "CITATIONS (verified against the source text)"]
        for number, c in enumerate(result["citations"], start=1):
            title = f" - {c['title']}" if c.get("title") else ""
            page = f", page {c['page']}" if c.get("page") else ""
            reference = f", {c['reference']}" if c.get("reference") else ""
            lines.append(f"  [{number}] {c['act_or_case']}{reference}{title}{page}")
            lines.append(f"      \"{c['quote']}\"")
        if result["removed_citations"]:
            lines += ["", f"  ({len(result['removed_citations'])} citation(s) removed by verification:)"]
            lines += [f"   - {r['citation']}: {r['reason']}" for r in result["removed_citations"]]
        if check.get("redrafted"):
            lines += ["", f"  (First draft rejected by the conclusion check: {check['first_issue']})"]
        if check.get("verdict") == "partly":
            lines += ["", f"  CAUTION (conclusion check): {check['issue']}"]
    lines += ["", "SOURCES RETRIEVED (" + result["config"] + ")"]
    lines += [f"  {r['rank']}. {r['source']}" for r in result["retrieved"]]
    lines.append("")
    lines.append("This is research assistance from the firm's document corpus, not legal advice.")
    return "\n".join(lines)
