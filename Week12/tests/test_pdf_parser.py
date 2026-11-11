"""
Unit tests for Task 2: PDF Parsing and OCR.
"""
from pathlib import Path
import pytest
from src.ingestion.pdf_parser import LegalPDFParser
from src.ingestion.ocr_engine import compute_cer, compute_wer, LexicalMorphUrduOCR, DeepContextualUrduOCR

def test_pdf_parser_classification():
    parser = LegalPDFParser()
    sample_statute = Path("data/statutes/STAT_001.pdf")
    if sample_statute.exists():
        info = parser.inspect_pdf(sample_statute)
        assert info["classification"] in ["digital", "hybrid"]
        assert info["page_count"] >= 1
        assert info["total_chars"] > 50

def test_pdf_parser_table_extraction():
    parser = LegalPDFParser()
    sample_statute = Path("data/statutes/STAT_001.pdf")
    if sample_statute.exists():
        extracted = parser.extract_text_and_tables(sample_statute)
        assert "full_text" in extracted
        assert len(extracted["full_text"]) > 0

def test_cer_and_wer_metrics():
    ref = "عدالت عالیہ لاہور"
    hyp_exact = "عدالت عالیہ لاہور"
    hyp_err = "عدالت عالیہ لاھور"
    
    assert compute_cer(ref, hyp_exact) == 0.0
    assert compute_wer(ref, hyp_exact) == 0.0
    assert compute_cer(ref, hyp_err) > 0.0
