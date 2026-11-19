"""
Answer generation for the Day 2 RAG pipeline.

The same generator is used for every retrieval configuration, so differences in
the comparison come from retrieval. The model sees only the retrieved passages
and must return:

    short_answer, explanation, citations [{source, act_or_case, section_or_paragraph, quote}]

or the exact refusal "No sufficient source found" when the passages do not
answer the question. Citations point to a passage number so they can be checked
against what was actually retrieved (Task 5 verifies them).
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from src.llm.gemini_client import GeminiClient

NO_SOURCE = "No sufficient source found"

SYSTEM = f"""You are a legal research assistant for a Pakistani law firm.
Answer ONLY from the numbered source passages you are given. Never use outside knowledge,
never invent a section, case or quote.
- If the passages do not contain the answer, set short_answer to exactly "{NO_SOURCE}",
  leave explanation empty and give no citations.
- Otherwise give a short answer (1-2 sentences), an explanation, and citations.
- Each citation: the passage number it comes from, the Act (or case), the exact section
  (e.g. "Section 23", "Article 199") or paragraph (e.g. "para 7"), and a quote copied
  word for word from that passage that supports the answer.
- A passage labelled only with an Act and a page (the Urdu laws) has no section numbers: cite it
  by its page, e.g. "page 19", and never guess a section (دفعہ) number.
- Answer in the language of the question (English, Roman Urdu or Urdu); citations and quotes
  stay in the language of the source."""


class Citation(BaseModel):
    source: int = Field(description="Number of the passage the citation comes from")
    act_or_case: str
    section_or_paragraph: str = Field(description='e.g. "Section 23", "Article 199", "para 7"')
    quote: str = Field(description="Exact words copied from that passage")


class CitedAnswer(BaseModel):
    short_answer: str
    explanation: str = ""
    citations: List[Citation] = Field(default_factory=list)


def source_label(result: Dict) -> str:
    """Human-readable source line built from chunk metadata."""
    meta = result.get("metadata", {})
    if meta.get("act"):
        parts = [meta["act"]]
        if meta.get("section"):
            parts.append(str(meta["section"]))
    elif meta.get("court"):
        parts = [meta["court"], meta.get("case_number", "")]
        if meta.get("section"):
            parts.append(str(meta["section"]))
    elif meta.get("contract_title"):
        parts = [meta["contract_title"]]
        if meta.get("section"):
            parts.append(str(meta["section"]))
    else:
        parts = [result["document_id"]]
    if meta.get("page"):
        parts.append(f"page {meta['page']}")
    return " | ".join(p for p in parts if p)


def format_sources(results: List[Dict], max_chars: int = 2500) -> str:
    return "\n\n".join(f"[{i}] {source_label(r)}\n{r['content'][:max_chars]}" for i, r in enumerate(results, start=1))


def answer_question(llm: GeminiClient, question: str, results: List[Dict]) -> CitedAnswer:
    if not results:
        return CitedAnswer(short_answer=NO_SOURCE)
    prompt = f"Question: {question}\n\nSource passages:\n{format_sources(results)}"
    return llm.generate_json(prompt, CitedAnswer, system=SYSTEM, temperature=0.0)


def is_refusal(answer: CitedAnswer) -> bool:
    return NO_SOURCE.lower() in answer.short_answer.lower()
