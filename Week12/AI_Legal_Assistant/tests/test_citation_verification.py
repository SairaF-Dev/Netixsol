"""Tests for Task 5: code-only citation verification."""
from pathlib import Path

import pytest

from src.rag.answer import NO_SOURCE, CitedAnswer, Citation
from src.rag.verify import parse_reference, quote_found, verify_answer

CONTRACT_ACT = Path("data/structured/statute/PKLAW_012.json")
S23 = ("Section 23. What considerations and objects are lawful and what not. The consideration or object of an "
       "agreement is lawful, unless it is forbidden by law. Every agreement of which the object or consideration "
       "is unlawful is void.")


def passage(doc="PKLAW_012", content=S23, **meta):
    return {"chunk_id": f"{doc}_X", "document_id": doc, "content": content,
            "metadata": {"act": "Contract Act, 1872", **meta}}


def cite(source=1, act="Contract Act, 1872", ref="Section 23",
         quote="Every agreement of which the object or consideration is unlawful is void."):
    return Citation(source=source, act_or_case=act, section_or_paragraph=ref, quote=quote)


def test_parse_reference_forms():
    assert parse_reference("Section 23(1)") == ("section", "Section 23")
    assert parse_reference("Article 203F(1)") == ("section", "Article 203F")
    assert parse_reference("دفعہ ۲۳") == ("section", "Section 23")
    assert parse_reference("para 7") == ("paragraph", "7")
    assert parse_reference("Order V Rule 20") == ("section", "Order V Rule 20")
    assert parse_reference("page 19") == ("page", "19")


def test_quote_must_be_verbatim_but_ignores_spacing_and_footnote_marks():
    assert quote_found("requiring factual inquiry. Equally settled is", "one requiring factual inquiry1. Equally settled is the")
    assert quote_found("in a cadre or service, the services", "in a cadre or service , the services of")
    assert quote_found("lawful, unless ... is unlawful is void", S23)
    assert not quote_found("Every agreement whose consideration is unlawful is void", S23)  # paraphrase


@pytest.mark.skipif(not CONTRACT_ACT.exists(), reason="structured corpus not available")
def test_verify_keeps_real_and_removes_fabricated_citations():
    results = [passage(section="Section 23")]
    good, report = verify_answer(CitedAnswer(short_answer="Yes", citations=[cite()]), results)
    assert len(good.citations) == 1 and report[0]["verified"]

    fake_section = cite(ref="Section 2399")
    fake_quote = cite(quote="Every unlawful agreement is punishable with a fine of ten thousand rupees.")
    wrong_source = cite(source=4)
    page_only = cite(ref="page 19")
    checked, report = verify_answer(CitedAnswer(short_answer="Yes", citations=[fake_section, fake_quote, wrong_source, page_only]), results)
    assert checked.short_answer == NO_SOURCE and not checked.citations
    assert [r["reason"].split(":")[0] for r in report] == ["reference", "quote", "source", "imprecise"]


@pytest.mark.skipif(not CONTRACT_ACT.exists(), reason="structured corpus not available")
def test_statute_quoted_inside_a_judgment_passage_is_accepted():
    judgment = {"chunk_id": "J_X", "document_id": "LHC_2026LHC8476", "metadata": {"court": "Lahore High Court"},
                "content": "Section 23 of the Contract Act provides: Every agreement of which the object or "
                           "consideration is unlawful is void."}
    checked, report = verify_answer(CitedAnswer(short_answer="Yes", citations=[cite()]), [judgment])
    assert report[0]["verified"] and checked.citations


def test_format_answer_shows_verified_citations_and_refusal():
    from src.rag.pipeline import format_answer
    base = {"question": "Q?", "config": "rerank", "retrieved": [{"rank": 1, "source": "Contract Act, 1872 | Section 23"}]}
    answered = format_answer({**base, "short_answer": "Yes.", "explanation": "Because.", "removed_citations": [],
                              "citations": [{"act_or_case": "Contract Act, 1872", "reference": "Section 23",
                                             "title": "What considerations and objects are lawful and what not",
                                             "page": 19, "quote": "Every agreement ... is void."}]})
    assert "Contract Act, 1872, Section 23 - What considerations" in answered and "page 19" in answered
    refused = format_answer({**base, "short_answer": NO_SOURCE, "explanation": "", "citations": [],
                             "removed_citations": [{"citation": "X | Section 9", "reason": "quote: not found"}]})
    assert refused.splitlines()[4] == NO_SOURCE + "." and "quote: not found" in refused


URDU_SRA = Path("data/structured/statute/PKCODE_URDU_039.json")


@pytest.mark.skipif(not URDU_SRA.exists(), reason="structured corpus not available")
def test_urdu_law_is_cited_by_page_not_by_guessed_section():
    text = "عدالت معاہدسےکی عدمقمیل کے لیےزرتلافی دلواسکتی ےاوراگرضروری ہو"
    urdu = {"chunk_id": "PKCODE_URDU_039_19", "document_id": "PKCODE_URDU_039", "content": text,
            "metadata": {"act": "مخصوص دادرسی ایکٹ ، ۱۸۷۷ء", "page": 19}}
    act = "مخصوص دادرسی ایکٹ"
    by_page = Citation(source=1, act_or_case=act, section_or_paragraph="صفحہ ۱۹", quote="کے لیے زرتلافی دلواسکتی")
    wrong_page = Citation(source=1, act_or_case=act, section_or_paragraph="page 7", quote="کے لیے زرتلافی دلواسکتی")
    guessed_section = Citation(source=1, act_or_case=act, section_or_paragraph="دفعہ ۲۰", quote="کے لیے زرتلافی دلواسکتی")
    checked, report = verify_answer(CitedAnswer(short_answer="ہاں", citations=[by_page, wrong_page, guessed_section]), [urdu])
    assert [r["verified"] for r in report] == [True, False, False]
    assert [r["reason"].split(":")[0] for r in report[1:]] == ["reference", "unverifiable"]
    assert checked.citations == [by_page]


def test_urdu_quotes_ignore_ocr_spacing_but_not_letters():
    ocr = "عدالت معاہدسےکی عدمقمیل کے لیےزرتلافی دلواسکتی ےاوراگرضروری ہو"
    assert quote_found("کے لیے زرتلافی دلوا سکتی", ocr)          # OCR glued/split words
    assert not quote_found("کے لیے جرمانہ دلوا سکتی", ocr)         # a different word
    assert not quote_found("زرتلافی", ocr)                          # too short to prove anything


@pytest.mark.skipif(not URDU_SRA.exists(), reason="structured corpus not available")
def test_urdu_ocr_fuzzy_match_shows_source_text_never_the_models_wording():
    ocr = ("عدالت معاہدسےکی عدمقمیل کے لیےزرتلافی دلواسکتی ےاوراگرضروری ہوتوءاس معاہدے کی تکمیل کا حکم "
           "دے سکتی ہے جو بصورت دیگر مخصوص نفاذ کے لیے مناسب ہو")
    urdu = {"chunk_id": "PKCODE_URDU_039_19", "document_id": "PKCODE_URDU_039", "content": ocr,
            "metadata": {"act": "مخصوص دادرسی ایکٹ ، ۱۸۷۷ء", "page": 19}}
    negated = ("عدالت معاہدے کی عدم تعمیل کے لیے زرتلافی نہیں دلوا سکتی ہے اور اگر ضروری ہو تو اس "
               "معاہدے کی تکمیل کا حکم دے سکتی ہے")   # "not" added: must never be shown as a quote
    wrong_text = "ہر معاہدہ کرنے والا شخص کسی معاہدے کی تکمیل میں چھوٹ دے سکتا ہے یا اس کی تکمیل کے لیے وقت بڑھا سکتا ہے"
    act = "مخصوص دادرسی ایکٹ"
    checked, report = verify_answer(CitedAnswer(short_answer="ہاں", citations=[
        Citation(source=1, act_or_case=act, section_or_paragraph="صفحہ ۱۹", quote=negated),
        Citation(source=1, act_or_case=act, section_or_paragraph="صفحہ ۱۹", quote=wrong_text)]), [urdu])
    assert [r["verified"] for r in report] == [True, False]
    shown = checked.citations[0].quote
    assert "نہیں" not in shown and quote_found(shown, ocr)
