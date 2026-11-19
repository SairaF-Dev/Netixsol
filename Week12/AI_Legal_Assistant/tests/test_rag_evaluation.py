"""Tests for Day 2 scoring: gold matching, ranks and citation checks (no LLM calls)."""
from evaluations.rag_evaluation import citation_correct
from src.rag.answer import CitedAnswer, Citation, NO_SOURCE, is_refusal
from src.rag.retrieval import first_hit_rank, hits_gold

STATUTE_ITEM = {
    "gold": [{"document_id": "PKLAW_012", "act": "Contract Act, 1872", "section": "Section 23"}],
    "quote": "Every agreement of which the object or consideration is unlawful is void.",
}
CASE_ITEM = {
    "gold": [{"document_id": "SC_c.a._333_2024", "matter_id": "SC:C-A-333-2024", "paragraph": "5"}],
    "quote": "the reserved seats must be allocated",
}


def result(doc, content="text", **meta):
    return {"chunk_id": f"{doc}_X", "document_id": doc, "content": content, "metadata": meta}


def test_fixed_chunk_hits_by_covered_section_or_quote():
    assert hits_gold(result("PKLAW_012", covers=["Section 22", "Section 23"]), STATUTE_ITEM["gold"][0])
    assert not hits_gold(result("PKLAW_012", covers=["Section 24"]), STATUTE_ITEM["gold"][0])
    # Quote match also counts (e.g. a chunk without labels), but only in the gold document.
    quoted = "... Every agreement of which the object or consideration is unlawful is   void. ..."
    assert hits_gold(result("PKLAW_012", quoted), STATUTE_ITEM["gold"][0], STATUTE_ITEM["quote"])
    assert not hits_gold(result("PKLAW_010", quoted), STATUTE_ITEM["gold"][0], STATUTE_ITEM["quote"])


def test_section_chunk_and_paragraph_ranges():
    assert hits_gold(result("PKLAW_012", section="Section 23"), STATUTE_ITEM["gold"][0])
    gold = CASE_ITEM["gold"][0]
    assert hits_gold(result("SC_c.a._333_2024", section="paras 3-6"), gold)
    assert not hits_gold(result("SC_c.a._333_2024", section="paras 6-8"), gold)
    # Another file of the same legal matter counts when it contains the quote.
    other = result("SC_c.a._333_2024_mv", "... the reserved seats must be allocated ...", matter_id="SC:C-A-333-2024")
    assert hits_gold(other, gold, CASE_ITEM["quote"])


def test_first_hit_rank():
    results = [result("PKLAW_010", section="Section 302"), result("PKLAW_012", section="Section 24"),
               result("PKLAW_012", section="Section 23")]
    assert first_hit_rank(results, STATUTE_ITEM) == 3
    assert first_hit_rank(results[:2], STATUTE_ITEM) is None


def test_citation_correct_needs_gold_document_and_number():
    results = [result("PKLAW_010"), result("PKLAW_012")]
    cite = lambda source, label: CitedAnswer(short_answer="Yes", citations=[
        Citation(source=source, act_or_case="Contract Act", section_or_paragraph=label, quote="q")])
    assert citation_correct(cite(2, "Section 23"), results, STATUTE_ITEM)
    assert citation_correct(cite(2, "s. 23"), results, STATUTE_ITEM)
    assert not citation_correct(cite(2, "Section 24"), results, STATUTE_ITEM)
    assert not citation_correct(cite(1, "Section 23"), results, STATUTE_ITEM)  # passage from another Act
    assert not citation_correct(cite(9, "Section 23"), results, STATUTE_ITEM)  # no such passage


def test_refusal_detection():
    assert is_refusal(CitedAnswer(short_answer=NO_SOURCE))
    assert not is_refusal(CitedAnswer(short_answer="Yes, it is void."))


def test_citation_number_accepts_urdu_digits():
    results = [result("PKLAW_012")]
    answer = CitedAnswer(short_answer="ہاں", citations=[
        Citation(source=1, act_or_case="قانون معاہدہ", section_or_paragraph="دفعہ ۲۳", quote="q")])
    assert citation_correct(answer, results, STATUTE_ITEM)
