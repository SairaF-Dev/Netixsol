"""Tests for the OCR'd Pakistan Code Urdu laws: text cleanup, page units, chunking and search tokens."""
from src.chunking.section_chunker import SectionLevelChunker
from src.extraction.urdu_statute_extractor import extract_urdu_law
from src.extraction.urdu_text import clean_urdu_ocr, normalize_for_search, urdu_year
from src.indexing.bm25_index import tokenize_legal_text


def test_clean_urdu_ocr_letters_digits_watermark():
    raw = "دفعه ٣٠٢ كي سزا يه هے THE PAKIS COD\n١٢\nIBCC ~ |"
    cleaned = clean_urdu_ocr(raw)
    assert cleaned == "دفعہ ۳۰۲ کی سزا یہ ہے\nIBCC"


def test_search_normalisation_matches_ascii_and_urdu_digits():
    assert normalize_for_search("دفعه ٣٠٢۔") == normalize_for_search("دفعہ 302 ")
    assert tokenize_legal_text("دفعه ٣٠٢، قتل") == ["دفعہ", "302", "قتل"]


def test_urdu_year_from_title():
    assert urdu_year("مجموعہ تعزیرات پاکستان ۱۸۶۰ء") == 1860
    assert urdu_year("بلا سال") is None


def test_extract_urdu_law_pages_and_chunks(tmp_path):
    folder = tmp_path / "PKCODE_URDU_999"
    folder.mkdir()
    (folder / "page_0001.txt").write_text("مختصر عنوان اور آغاز نفاذ ٢٠١٠", encoding="utf-8")
    (folder / "page_0002.txt").write_text("", encoding="utf-8")  # blank page
    record = {"document_id": "PKCODE_URDU_999", "title": "نمونہ ایکٹ ، ۲۰۱۰ء", "pages": 3, "file_path": "x.pdf"}

    doc = extract_urdu_law(record, ocr_dir=tmp_path)
    pages = doc.chapters[0].sections
    assert doc.language == "Urdu" and doc.year == 2010
    assert [p.page_start for p in pages] == [1]
    assert doc.pages_needing_ocr == [3]

    chunks = SectionLevelChunker().chunk_statute(doc)
    assert len(chunks) == 1
    assert chunks[0].metadata["page"] == 1 and chunks[0].metadata["language"] == "Urdu"
    assert chunks[0].content.startswith("نمونہ ایکٹ ، ۲۰۱۰ء | صفحہ 1")
