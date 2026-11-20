"""
Conclusion check: does the answer's conclusion follow from the sources?

The citation verifier (src/rag/verify.py) proves that every quote exists in a retrieved passage. It cannot
tell whether the conclusion drawn from a real quote is right. Two ways an answer with verified citations
can still be wrong:
  * the quoted passage deals with a different legal issue from the one asked;
  * another retrieved passage contradicts or limits the conclusion (a cap, an exception, a condition).
Example (Day 2 demo, Urdu): asked whether a court can award MORE than the penalty amount fixed in a
contract, the model answered yes, citing a real Specific Relief Act passage about enforcing the contract
itself, while Section 74 of the Contract Act, retrieved at rank 3, caps compensation at the amount named.

A second Gemini call reviews the answer the way a senior lawyer would, from the retrieved passages only:
  supported      the passages relied on answer this question, and nothing retrieved contradicts it;
  partly         right direction, but stated more broadly than the passages allow or missing a limit;
  not_supported  the passages address a different issue, or a retrieved passage contradicts it.

Used by src/rag/pipeline.py: not_supported -> the answer is drafted once more with the reviewer's note
(and its citations verified again); still not_supported -> withheld. partly -> shown with the caution.
"""

from typing import Dict, List, Literal

from pydantic import BaseModel, Field

from src.rag.answer import CitedAnswer, format_sources, is_refusal


class ConclusionVerdict(BaseModel):
    # reasoning fields first: the model writes them before it commits to a verdict
    question_asks: str = Field(default="", description="The precise legal point the question asks, in English")
    passages_establish: str = Field(default="", description="What the passages the answer relies on actually say on that point, in English")
    conflicts: str = Field(default="", description="Any passage that contradicts, caps or limits the answer; 'none' if none")
    verdict: Literal["supported", "partly", "not_supported"]
    issue: str = Field(default="", description="What is wrong, in one or two plain sentences; empty if supported")
    deciding_sources: List[int] = Field(default_factory=list, description="Passage numbers that actually decide the question")


SYSTEM = """You are a senior lawyer at a Pakistani law firm checking a junior's research answer before it reaches
a client. You get the question, the numbered source passages the junior had, and the junior's answer. Judge
ONLY from the passages, never from outside knowledge of the law. Check three things:
1. Issue: do the passages the answer relies on deal with the legal question actually asked, or with a
   different one (for example enforcing a contract vs the amount of compensation; bail vs conviction)?
2. Conflict: does ANY passage, cited or not, contradict, cap, limit or make an exception to the conclusion?
3. Scope: is the conclusion stated more broadly or more certainly than the passages allow?
First write question_asks (the exact point asked, e.g. "can the court award MORE than the amount named"),
then passages_establish (what the relied-on passages say about THAT point, not about the topic in general),
then conflicts. An answer whose passages are about the same topic but do not establish the exact point
asked is "not_supported".
verdict: "supported" if the issue matches and there is no conflict or overstatement; "partly" if the
direction is right but it is overstated or misses a limit stated in a passage; "not_supported" if the
passages address a different issue or a passage contradicts the conclusion.
issue: one or two plain sentences naming the passage numbers (empty when supported).
deciding_sources: the passage numbers that actually decide the question.
The question and answer may be in English, Urdu or Roman Urdu: judge the meaning, not the wording.
Do not penalise an answer for leaving out details the question did not ask about."""


def check_conclusion(llm, question: str, answer: CitedAnswer, results: List[Dict]) -> ConclusionVerdict:
    if is_refusal(answer) or not results:
        return ConclusionVerdict(verdict="supported")
    cited = ", ".join(f"[{c.source}] {c.section_or_paragraph}" for c in answer.citations) or "none"
    prompt = (f"Question: {question}\n\nSource passages:\n{format_sources(results)}\n\n"
              f"Junior's answer:\n{answer.short_answer}\n{answer.explanation}\nCitations: {cited}")
    return llm.generate_json(prompt, ConclusionVerdict, system=SYSTEM, temperature=0.0)
