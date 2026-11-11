"""
Unit tests for Task 2: PDF Parsing and OCR.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.ingestion.pdf_parser import LegalPDFParser
from src.ingestion import ocr_engine
from src.ingestion.ocr_engine import compute_cer, compute_wer

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

def test_generated_urdu_fixture_is_image_only():
    parser = LegalPDFParser()
    sample_scan = Path("data/scanned_urdu/benchmark_cer/URDU_GT_001.pdf")
    if sample_scan.exists():
        info = parser.inspect_pdf(sample_scan)
        assert info["classification"] == "scanned"
        assert info["total_chars"] == 0

def test_pdf_parser_routes_scanned_page_to_injected_ocr():
    sample_scan = Path("data/scanned_urdu/benchmark_cer/URDU_GT_001.pdf")
    if not sample_scan.exists():
        pytest.skip("OCR fixture PDF is not available")

    class FixtureOCR:
        def extract_text(self, document_path, page_num=0):
            assert page_num == 0
            return {"text": "recognized Urdu page"}

    result = LegalPDFParser(ocr_engine=FixtureOCR()).extract_text_and_tables(sample_scan)
    page = result["pages"][0]
    assert page["page_type"] == "scanned"
    assert page["text_source"] == "ocr"
    assert page["text"] == "recognized Urdu page"
    assert page["needs_ocr"] is False

def test_cer_and_wer_metrics():
    ref = "عدالت عالیہ لاہور"
    hyp_exact = "عدالت عالیہ لاہور"
    hyp_err = "عدالت عالیہ لاھور"
    
    assert compute_cer(ref, hyp_exact) == 0.0
    assert compute_wer(ref, hyp_exact) == 0.0
    assert compute_cer(ref, hyp_err) > 0.0

def test_ocr_page_is_rendered_and_sent_to_tesseract(monkeypatch):
    sample_pdf = Path("data/scanned_urdu/benchmark_cer/URDU_GT_001.pdf")
    if not sample_pdf.exists():
        pytest.skip("OCR fixture PDF is not available")

    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if "--list-langs" in args:
            return SimpleNamespace(
                returncode=0,
                stdout="List of available languages (2):\neng\nurd\n",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout=b"recognized text", stderr=b"")

    monkeypatch.setattr(ocr_engine.shutil, "which", lambda _: "tesseract")
    monkeypatch.setattr(ocr_engine.subprocess, "run", fake_run)

    result = ocr_engine.TesseractUrduOCR().extract_text(sample_pdf)
    assert result["text"] == "recognized text"
    assert len(calls) == 2
    assert calls[1][1]["input"].startswith(b"\x89PNG\r\n\x1a\n")
