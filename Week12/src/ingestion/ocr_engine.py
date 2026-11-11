"""Image-based OCR adapters and text error-rate metrics."""

import io
import importlib
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict

import fitz
import jiwer
import numpy as np
from PIL import Image


def _render_pdf_page(document_path: str | Path, page_num: int) -> bytes:
    """Render a PDF page to PNG bytes so OCR engines process pixels, not embedded text."""
    path = Path(document_path)
    if not path.is_file():
        raise FileNotFoundError(f"OCR input PDF not found: {path}")

    with fitz.open(str(path)) as document:
        if page_num < 0 or page_num >= len(document):
            raise IndexError(
                f"Page index {page_num} is out of range for {path} "
                f"({len(document)} pages)"
            )
        pixmap = document[page_num].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        return pixmap.tobytes("png")


class TesseractUrduOCR:
    """Run the Tesseract executable with Urdu and English language data."""

    name = "Tesseract (urd+eng)"

    def __init__(self) -> None:
        self.executable = shutil.which("tesseract")
        if not self.executable:
            raise RuntimeError(
                "Tesseract is not installed or is not on PATH. Install Tesseract "
                "with Urdu (urd) and English (eng) language data to run OCR evaluation."
            )

        result = subprocess.run(
            [self.executable, "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Unable to list Tesseract languages: {result.stderr.strip()}")
        languages = set(result.stdout.splitlines()[1:])
        if not {"urd", "eng"}.issubset(languages):
            missing = sorted({"urd", "eng"} - languages)
            raise RuntimeError(
                f"Tesseract is missing language data: {', '.join(missing)}. "
                "Install these traineddata files before running OCR evaluation."
            )

    def extract_text(self, document_path: str | Path, page_num: int = 0) -> Dict[str, Any]:
        image = _render_pdf_page(document_path, page_num)
        started = time.perf_counter()
        result = subprocess.run(
            [self.executable, "stdin", "stdout", "-l", "urd+eng", "--psm", "6"],
            input=image,
            capture_output=True,
            check=False,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Tesseract OCR failed for {document_path}: {error}")
        return {
            "engine": self.name,
            "text": result.stdout.decode("utf-8", errors="replace").strip(),
            "latency_ms": round(latency_ms, 2),
        }


class EasyOCRUrduOCR:
    """Run EasyOCR on a rendered PDF page; requires the optional ``easyocr`` package."""

    name = "EasyOCR (ur+en)"

    def __init__(self) -> None:
        try:
            easyocr = importlib.import_module("easyocr")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "EasyOCR is not installed. Install the optional 'easyocr' package "
                "before running OCR evaluation."
            ) from exc
        self.reader = easyocr.Reader(["ur", "en"], gpu=False)

    def extract_text(self, document_path: str | Path, page_num: int = 0) -> Dict[str, Any]:
        image_bytes = _render_pdf_page(document_path, page_num)
        image = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        started = time.perf_counter()
        lines = self.reader.readtext(image, detail=0, paragraph=True)
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "engine": self.name,
            "text": "\n".join(str(line) for line in lines).strip(),
            "latency_ms": round(latency_ms, 2),
        }


def compute_cer(reference: str, hypothesis: str) -> float:
    """Calculate character error rate (insertions + deletions + substitutions / reference)."""
    ref_clean = unicodedata.normalize("NFC", reference.strip())
    hyp_clean = unicodedata.normalize("NFC", hypothesis.strip())
    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0
    return float(jiwer.cer(ref_clean, hyp_clean))


def compute_wer(reference: str, hypothesis: str) -> float:
    """Calculate word error rate (insertions + deletions + substitutions / reference)."""
    ref_clean = unicodedata.normalize("NFC", reference.strip())
    hyp_clean = unicodedata.normalize("NFC", hypothesis.strip())
    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0
    return float(jiwer.wer(ref_clean, hyp_clean))
