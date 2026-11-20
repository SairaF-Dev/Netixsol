"""Tests for the conclusion check flow in src/rag/pipeline.py (fake LLM, no Gemini)."""
import pytest

from src.rag import pipeline
from src.rag.answer import NO_SOURCE, CitedAnswer, Citation
from src.rag.conclusion_check import ConclusionVerdict, check_conclusion

RESULTS = [{"chunk_id": "c1", "document_id": "D", "content": "A contract may be enforced although a sum is named for breach.",
            "metadata": {"act": "Specific Relief Act, 1877", "section": "Section 20"}}]
WRONG = CitedAnswer(short_answer="Yes, the court can award more.", explanation="...",
                    citations=[Citation(source=1, act_or_case="Specific Relief Act, 1877", section_or_paragraph="Section 20",
                                        quote="A contract may be enforced")])
RIGHT = CitedAnswer(short_answer=NO_SOURCE)


class FakeLLM:
    """Answers: first draft, then the redraft; verdicts in order."""
    def __init__(self, drafts, verdicts):
        self.drafts, self.verdicts, self.prompts = list(drafts), list(verdicts), []

    def generate_json(self, prompt, schema, system=None, temperature=0.0):
        self.prompts.append(prompt)
        if schema is CitedAnswer:
            return self.drafts.pop(0)
        return ConclusionVerdict(verdict=self.verdicts.pop(0), issue="The passage is about enforcing the contract, not the amount.")


@pytest.fixture()
def use(monkeypatch):
    def install(llm):
        monkeypatch.setattr(pipeline, "_llm", lambda: llm)
        monkeypatch.setattr(pipeline, "verify_answer", lambda draft, results: (draft, []))
        return llm
    return install


def test_supported_answer_is_kept(use):
    llm = use(FakeLLM([WRONG], ["supported"]))
    _, shown, _, info = pipeline._checked_answer("q", RESULTS)
    assert shown is WRONG and not info["redrafted"] and len(llm.prompts) == 2


def test_rejected_answer_is_redrafted_with_the_reviewers_note(use):
    llm = use(FakeLLM([WRONG, RIGHT], ["not_supported"]))
    _, shown, _, info = pipeline._checked_answer("q", RESULTS)
    assert shown.short_answer == NO_SOURCE and info["redrafted"] and not info["withheld"]
    assert "not the amount" in llm.prompts[2]           # the redraft prompt carries the objection


def test_answer_rejected_twice_is_withheld(use):
    use(FakeLLM([WRONG, WRONG], ["not_supported", "not_supported"]))
    _, shown, _, info = pipeline._checked_answer("q", RESULTS)
    assert shown.short_answer == NO_SOURCE and info["withheld"]


def test_refusals_are_not_sent_to_the_checker():
    class NoCall:
        def generate_json(self, *a, **k):
            raise AssertionError("no LLM call expected")
    assert check_conclusion(NoCall(), "q", RIGHT, RESULTS).verdict == "supported"
