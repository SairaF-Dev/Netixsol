"""
Unit tests for Task 2: PDF Parsing and OCR.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest
from evaluations import ocr_evaluation
from src.ingestion.pdf_parser import LegalPDFParser
from src.ingestion import ocr_engine
from src.ingestion.ocr_engine import compute_cer, compute_wer

def test_pdf_parser_classification():
    parser = LegalPDFParser()
    sample_statute = Path("data/statutes/REAL_STAT_001.pdf")
    if sample_statute.exists():
        info = parser.inspect_pdf(sample_statute)
        assert info["classification"] in ["digital", "hybrid"]
        assert info["page_count"] >= 1
        assert info["total_chars"] > 50

def test_pdf_parser_table_extraction():
    parser = LegalPDFParser()
    # A short Pakistan Code PDF: table detection on the 252-page Constitution (Ministry of Law
    # edition, many vector drawings) takes minutes per page.
    sample_statute = Path("data/raw/pakistani_laws/Defense_Forces_of_Pakistan_Act_2026.pdf")
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


def test_load_available_engines_skips_missing_engine(monkeypatch):
    class AvailableOCR:
        def __init__(self):
            self.name = "available"

    class MissingOCR:
        def __init__(self):
            raise RuntimeError("not installed")

    class BlockedOCRError(OSError):
        pass

    class BlockedOCR:
        def __init__(self):
            raise BlockedOCRError("application control blocked file")

    monkeypatch.setattr(ocr_evaluation, "TesseractUrduOCR", AvailableOCR)
    monkeypatch.setattr(ocr_evaluation, "EasyOCRUrduOCR", BlockedOCR)

    available = ocr_evaluation.load_available_engines()
    assert len(available) == 1
    assert available[0].name == "available"


def test_garbled_char_ratio_flags_private_use_area_text():
    from src.ingestion.pdf_parser import garbled_char_ratio

    assert garbled_char_ratio("") == 0.0
    assert garbled_char_ratio("عدالت عالیہ لاہور Section 302") == 0.0
    assert garbled_char_ratio(" ") == 1.0


def test_garbled_text_layer_page_is_routed_to_ocr():
    """A page that extracts as Private Use Area codes must not be treated as digital."""
    parser = LegalPDFParser()
    garbled = "" * 20
    assert parser.classify_page(garbled, image_count=0) == "garbled_text_layer"
    assert parser.classify_page("Readable statute text " * 5, image_count=0) == "digital"

    real_urdu = Path("data/pakistani_urdu_code/administratorcurdua7f4f2b3b5b93d09a4aa20kl.pdf")
    if not real_urdu.exists():
        pytest.skip("Pakistan Code Urdu PDFs are not available")
    info = parser.inspect_pdf(real_urdu)
    assert info["classification"] == "scanned"
    assert info["garbled_text_pages"] == info["page_count"]

    class FixtureOCR:
        def extract_text(self, document_path, page_num=0):
            return {"text": "OCR text"}

    pages = LegalPDFParser().extract_text_and_tables(real_urdu)["pages"]
    assert all(p["needs_ocr"] and p["text"] == "" for p in pages)
    ocr_pages = LegalPDFParser(ocr_engine=FixtureOCR()).extract_text_and_tables(real_urdu)["pages"]
    assert all(p["text_source"] == "ocr" and p["text"] == "OCR text" for p in ocr_pages)
