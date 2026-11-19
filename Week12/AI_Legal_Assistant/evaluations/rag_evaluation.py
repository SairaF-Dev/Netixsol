"""
Day 2, Tasks 2-3: evaluate a RAG configuration on the 100-question set.

Retrieval metrics (no LLM, free):
  Recall@5      share of answerable questions whose gold section / paragraph is in the top 5
  MRR@5         mean of 1/rank of the first gold chunk (0 if not in the top 5)
  Doc recall@5  share whose gold DOCUMENT appears in the top 5 (diagnostic)

Answer metrics (Gemini; skipped with --no-llm):
  Citation accuracy   share of answerable questions whose answer cites the gold
                      section / paragraph from a passage of the gold document
  Faithfulness        judge model splits the answer into claims and checks each against
                      the retrieved passages; score = supported / total (answered questions)
  Correct refusals    share of no-answer questions answered "No sufficient source found"
  False refusals      share of answerable questions wrongly refused

Per-question results go to evaluations/rag_runs/<config>.jsonl, the summary of every
configuration run so far to evaluations/rag_runs/summary.json and the comparison
table to evaluations/rag_comparison_report.md.

Run:  python -m evaluations.rag_evaluation --config naive [--no-llm] [--reviewed-only]
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from tabulate import tabulate

from src.rag.answer import CitedAnswer, answer_question, format_sources, is_refusal
from src.rag.retrieval import NaiveDenseRetriever, first_hit_rank, same_document
from src.utils.logger import setup_logger

logger = setup_logger("rag_evaluation")

EVAL_SET = Path("evaluations/rag_eval_set.jsonl")
RUN_DIR = Path("evaluations/rag_runs")
REPORT = Path("evaluations/rag_comparison_report.md")
TOP_K = 5

from src.rag.advanced import CONFIGS as ADVANCED_CONFIGS, DESCRIPTIONS as ADVANCED_DESCRIPTIONS, AdvancedRetriever

RETRIEVERS = {"naive": NaiveDenseRetriever,
              **{name: (lambda name=name, flags=flags: AdvancedRetriever(name, **flags))
                 for name, flags in ADVANCED_CONFIGS.items()}}
DESCRIPTIONS = {"naive": "0. Naive: fixed 200-word chunks, vector search only, top 5", **ADVANCED_DESCRIPTIONS}


class Claim(BaseModel):
    claim: str
    supported: bool = Field(description="True only if the passages state or directly imply this claim")


class FaithfulnessVerdict(BaseModel):
    claims: List[Claim]


def load_eval_set(reviewed_only: bool = False) -> List[Dict]:
    items = [json.loads(line) for line in EVAL_SET.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [item for item in items if item.get("reviewed")] if reviewed_only else items


# --------------------------------------------------------------------------- answer checks
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _number(text: str) -> Optional[str]:
    """'Section 23' / 's. 23' / 'دفعہ ۲۳' -> '23'; 'Section 337-Q' -> '337Q'."""
    text = text.translate(_DIGITS).upper().replace(" ", "").replace("-", "")
    match = re.search(r"([0-9]+[A-Z]*)", text)
    return match.group(1) if match else None


def citation_correct(answer: CitedAnswer, results: List[Dict], item: Dict) -> bool:
    """Does any citation point to the gold section / paragraph, from a passage of the gold document?"""
    for citation in answer.citations:
        if not 1 <= citation.source <= len(results):
            continue
        result = results[citation.source - 1]
        cited = _number(citation.section_or_paragraph)
        for gold in item["gold"]:
            if not same_document(result, gold):
                continue
            target = _number(gold.get("section") or "") if gold.get("section") else (gold.get("paragraph") or "").upper()
            if cited and target and cited == target:
                return True
    return False


def faithfulness(judge, question: str, answer: CitedAnswer, results: List[Dict]) -> Optional[float]:
    if is_refusal(answer):
        return None
    verdict = judge.generate_json(
        f"""Source passages:
{format_sources(results)}

Question: {question}
Answer: {answer.short_answer}
{answer.explanation}

Split the answer into its factual claims (at most 8). For each, decide whether the source
passages above state it or directly imply it. Background knowledge does not count: a claim
that is true in law but not in the passages is NOT supported.""",
        FaithfulnessVerdict, temperature=0.0)
    if not verdict.claims:
        return None
    return sum(c.supported for c in verdict.claims) / len(verdict.claims)


# --------------------------------------------------------------------------- run
def run(config: str, use_llm: bool = True, reviewed_only: bool = False) -> Dict:
    items = load_eval_set(reviewed_only)
    retriever = RETRIEVERS[config]()
    llm = judge = None
    if use_llm:
        from src.llm.gemini_client import GeminiClient
        llm, judge = GeminiClient(), GeminiClient.judge()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    started = time.time()
    for number, item in enumerate(items, start=1):
        results = retriever.retrieve(item["question"], top_k=TOP_K)
        record = {"id": item["id"], "type": item["type"], "language": item["language"],
                  "retrieved": [{"chunk_id": r["chunk_id"], "document_id": r["document_id"]} for r in results]}
        if getattr(retriever, "last_trace", None):
            record["trace"] = retriever.last_trace
        if item["gold"]:
            rank = first_hit_rank(results, item)
            record.update(rank=rank, doc_hit=any(same_document(r, g) for r in results for g in item["gold"]))
        if use_llm:
            answer = answer_question(llm, item["question"], results)
            record["answer"] = answer.model_dump()
            record["refused"] = is_refusal(answer)
            if item["gold"]:
                record["citation_correct"] = citation_correct(answer, results, item)
                record["faithfulness"] = faithfulness(judge, item["question"], answer, results)
        records.append(record)
        if number % 10 == 0:
            logger.info("%s: %d/%d questions (%.0fs)", config, number, len(items), time.time() - started)

    with (RUN_DIR / f"{config}.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = summarize(config, records, use_llm, reviewed_only)
    if llm:
        summary["llm_calls"] = llm.calls + judge.calls
    save_summary(summary)
    write_report()
    return summary


def _mean(values: List[float]) -> Optional[float]:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def summarize(config: str, records: List[Dict], use_llm: bool, reviewed_only: bool) -> Dict:
    answerable = [r for r in records if r["type"] != "no_answer"]
    no_answer = [r for r in records if r["type"] == "no_answer"]
    by_type = lambda kind: [r for r in answerable if r["type"] == kind]
    recall = lambda rows: _mean([1.0 if r["rank"] else 0.0 for r in rows])
    summary = {
        "config": config, "description": DESCRIPTIONS.get(config, config),
        "questions": len(records), "reviewed_only": reviewed_only,
        "recall@5": recall(answerable), "recall@5_statute": recall(by_type("statute")),
        "recall@5_case_law": recall(by_type("case_law")),
        "mrr@5": _mean([1.0 / r["rank"] if r["rank"] else 0.0 for r in answerable]),
        "doc_recall@5": _mean([1.0 if r["doc_hit"] else 0.0 for r in answerable]),
    }
    if use_llm:
        summary.update({
            "citation_accuracy": _mean([1.0 if r["citation_correct"] else 0.0 for r in answerable]),
            "faithfulness": _mean([r["faithfulness"] for r in answerable]),
            "correct_refusals": _mean([1.0 if r["refused"] else 0.0 for r in no_answer]),
            "false_refusals": _mean([1.0 if r["refused"] else 0.0 for r in answerable]),
        })
    return summary


def save_summary(summary: Dict) -> None:
    path = RUN_DIR / "summary.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    previous = data.get(summary["config"], {})
    # A --no-llm run keeps the answer metrics of an earlier full run of the same config.
    data[summary["config"]] = {**previous, **summary}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_report() -> None:
    data = json.loads((RUN_DIR / "summary.json").read_text(encoding="utf-8"))
    pct = lambda v: "–" if v is None else f"{100 * v:.0f}%"
    num = lambda v: "–" if v is None else f"{v:.2f}"
    order = [name for name in RETRIEVERS if name in data] + [name for name in data if name not in RETRIEVERS]
    rows = [[DESCRIPTIONS.get(name, s["description"]), pct(s.get("recall@5")), pct(s.get("recall@5_statute")),
             pct(s.get("recall@5_case_law")), num(s.get("mrr@5")), pct(s.get("doc_recall@5")),
             pct(s.get("citation_accuracy")), pct(s.get("faithfulness")), pct(s.get("correct_refusals")),
             pct(s.get("false_refusals"))]
            for name, s in ((name, data[name]) for name in order)]
    table = tabulate(rows, tablefmt="github", headers=[
        "Configuration", "Recall@5", "Recall@5 statute", "Recall@5 case-law", "MRR@5", "Doc recall@5",
        "Citation accuracy", "Faithfulness", "Correct refusals", "False refusals"])
    first = next(iter(data.values()))
    REPORT.write_text(f"""# RAG Comparison (Day 2)

Evaluation set: `{EVAL_SET}` ({first['questions']} questions: 50 statute, 30 case-law, 20 with no
answer in the corpus). {'Only reviewed questions are used: every question was checked against its source text by Claude (an AI model), not by a person; 16 drafts were dropped and 6 corrected during that review (see `evaluations/rag_eval_set_review.csv` and `evaluations/rag_eval_set_dropped.jsonl`).' if first.get('reviewed_only') else 'Questions not yet reviewed.'}
The Constitution in the corpus is the Ministry of Law 2025 edition (amended up to the 27th Amendment).
"–" = not measured yet: steps 4-7 were first run for retrieval only (`--no-llm`), because free-tier
Gemini allows 500 requests a day; their answer metrics are added after the next full run.
Recall@5 / MRR@5 count a hit when a top-5 chunk comes from the gold document (or the same legal
matter) and contains the gold section / paragraph or the gold quote. Citation accuracy, faithfulness
and refusals are measured on Gemini answers; faithfulness is judged by an LLM (gemini-3.5-flash-lite),
not by a person.

{table}
""", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="naive", choices=list(RETRIEVERS))
    parser.add_argument("--no-llm", action="store_true", help="retrieval metrics only (no Gemini calls)")
    parser.add_argument("--reviewed-only", action="store_true", help="use only questions marked ok/fix in the review")
    args = parser.parse_args()
    result = run(args.config, use_llm=not args.no_llm, reviewed_only=args.reviewed_only)
    print(json.dumps(result, indent=2))
