"""
Structure for the Pakistan Code Urdu laws (inventory rows PKCODE_URDU_*), built from
the EasyOCR page texts in data/ocr_text/<document_id>/page_NNNN.txt.

Why pages, not sections: the Urdu laws number sections as "۱۔ مختصر عنوان", but
EasyOCR never outputs the Urdu full stop "۔" and merges each page into one
paragraph, so section headings cannot be found reliably (the numbered headings that
do survive are mostly on table-of-contents pages). Each OCR'd page is therefore one
unit labelled with the Act and its page number, which is what a citation to the
official PDF needs. Act name and year come from the official title in the inventory.
"""

from pathlib import Path
from typing import Any, Dict, List

from src.extraction.urdu_text import clean_urdu_ocr, urdu_year
from src.ingestion.urdu_ocr import OCR_TEXT_DIR
from src.utils.schemas import ChapterItem, SectionItem, StatuteDocument

MIN_PAGE_CHARS = 20  # pages with less text (blank pages) are skipped


def extract_urdu_law(record: Dict[str, Any], ocr_dir: Path = OCR_TEXT_DIR) -> StatuteDocument:
    """One inventory row -> StatuteDocument with one SectionItem per OCR'd page."""
    doc_id = str(record["document_id"])
    title = str(record["title"]).strip()
    total_pages = int(record["pages"])
    folder = Path(ocr_dir) / doc_id

    pages: List[SectionItem] = []
    missing: List[int] = []
    for page in range(1, total_pages + 1):
        path = folder / f"page_{page:04d}.txt"
        if not path.exists():
            missing.append(page)
            continue
        text = clean_urdu_ocr(path.read_text(encoding="utf-8"))
        if len(text) >= MIN_PAGE_CHARS:
            pages.append(SectionItem(section_number=f"Page {page}", title="", content=text, page_start=page))
    if not pages:
        raise FileNotFoundError(f"No OCR text for {doc_id} in {folder}; run the Urdu OCR first")

    return StatuteDocument(
        document_id=doc_id,
        act_name=title,
        year=urdu_year(title) or 0,
        language="Urdu",
        preamble="",
        chapters=[ChapterItem(chapter_number="", chapter_title="", sections=pages)],
        source_file=str(record["file_path"]),
        pages_needing_ocr=missing,
    )
