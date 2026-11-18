"""
Resumable EasyOCR pass over the Pakistan Code Urdu laws (inventory rows PKCODE_URDU_*).

Each page's text is written to data/ocr_text/<document_id>/page_NNNN.txt as soon
as it is recognised; pages that already have a file are skipped, so the job can
be stopped and restarted at any time. EasyOCR was chosen from the benchmark
(CER 32.9% vs 70.3% for Tesseract) and takes roughly 15-20 s per page on CPU.

Run:  python main.py --ocr-urdu            (all remaining pages)
      python main.py --ocr-urdu --max-pages 5
"""

import time
from pathlib import Path
from typing import Dict, Optional

import fitz
import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger("urdu_ocr")

OCR_TEXT_DIR = Path("data/ocr_text")


def page_text_path(document_id: str, page_number: int) -> Path:
    return OCR_TEXT_DIR / document_id / f"page_{page_number:04d}.txt"


def ocr_status(inventory_path: str | Path = "inventory.csv") -> Dict[str, Dict[str, int]]:
    """Pages done / total for each Urdu law."""
    inventory = pd.read_csv(inventory_path)
    rows = inventory[inventory["document_id"].astype(str).str.startswith("PKCODE_URDU_")]
    status = {}
    for row in rows.itertuples():
        done = len(list((OCR_TEXT_DIR / row.document_id).glob("page_*.txt")))
        status[row.document_id] = {"done": done, "total": int(row.pages)}
    return status


def build_colab_input(zip_path: str | Path = "colab/urdu_ocr_input.zip",
                      inventory_path: str | Path = "inventory.csv") -> Path:
    """Zip the Urdu law PDFs, a manifest and the list of pages already OCR'd locally."""
    import csv
    import io
    import zipfile

    inventory = pd.read_csv(inventory_path)
    rows = inventory[inventory["document_id"].astype(str).str.startswith("PKCODE_URDU_")]
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = io.StringIO()
    writer = csv.writer(manifest)
    writer.writerow(["document_id", "filename", "pages", "title"])
    done = io.StringIO()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for row in rows.itertuples():
            pdf = Path(row.file_path)
            archive.write(pdf, f"pdfs/{pdf.name}")
            writer.writerow([row.document_id, pdf.name, int(row.pages), row.title])
            for page_file in sorted((OCR_TEXT_DIR / row.document_id).glob("page_*.txt")):
                done.write(f"{row.document_id}/{page_file.name}\n")
        archive.writestr("manifest.csv", manifest.getvalue())
        archive.writestr("done_pages.txt", done.getvalue())
    logger.info("Colab input written to %s", zip_path)
    return zip_path


def import_ocr_results(zip_path: str | Path) -> int:
    """Copy page_*.txt files from the Colab output zip into data/ocr_text (existing pages are kept)."""
    import zipfile

    added = 0
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            parts = Path(name).parts
            if len(parts) < 2 or not parts[-1].startswith("page_") or not parts[-1].endswith(".txt"):
                continue
            target = OCR_TEXT_DIR / parts[-2] / parts[-1]
            if not parts[-2].startswith("PKCODE_URDU_") or target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
            added += 1
    status = ocr_status()
    logger.info("Imported %d pages; now %d/%d pages OCR'd", added,
                sum(s["done"] for s in status.values()), sum(s["total"] for s in status.values()))
    return added


def run_urdu_ocr(inventory_path: str | Path = "inventory.csv", max_pages: Optional[int] = None) -> int:
    """OCR remaining pages, smallest laws first (so complete laws become usable early)."""
    from src.ingestion.ocr_engine import EasyOCRUrduOCR

    inventory = pd.read_csv(inventory_path)
    rows = inventory[inventory["document_id"].astype(str).str.startswith("PKCODE_URDU_")]
    rows = rows.sort_values("pages")
    total_pages = int(rows["pages"].sum())
    done_before = sum(s["done"] for s in ocr_status(inventory_path).values())
    logger.info("Urdu OCR: %d/%d pages already done", done_before, total_pages)

    engine = EasyOCRUrduOCR()
    processed = 0
    started = time.time()
    for row in rows.itertuples():
        with fitz.open(str(row.file_path)) as doc:
            page_count = doc.page_count
        for page_number in range(1, page_count + 1):
            out_path = page_text_path(row.document_id, page_number)
            if out_path.exists():
                continue
            if max_pages is not None and processed >= max_pages:
                return processed
            text = engine.extract_text(row.file_path, page_num=page_number - 1)["text"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = out_path.with_suffix(".tmp")
            tmp_path.write_text(text, encoding="utf-8")
            tmp_path.replace(out_path)  # a page file exists only once fully written
            processed += 1
            if processed % 10 == 0:
                rate = (time.time() - started) / processed
                remaining = total_pages - done_before - processed
                logger.info("OCR %s page %d/%d | %d pages this run | ~%.0f s/page | ~%.1f h left",
                            row.document_id, page_number, page_count, processed, rate, remaining * rate / 3600)
    logger.info("Urdu OCR finished: %d pages this run", processed)
    return processed
