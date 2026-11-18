"""
Task 3: extract structure for every Statute / Judgment / Contract in inventory.csv.

Writes one JSON per document to data/structured/<type>/<document_id>.json (the
full raw text is left out to keep the files small) and a field-coverage report
to evaluations/extraction_report.md. The Pakistan Code Urdu laws (PKCODE_URDU_*)
are built from their OCR page texts (data/ocr_text); the other Scanned/Urdu rows
(single benchmark pages cut from those laws) are skipped.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pydantic import BaseModel
from tabulate import tabulate

from src.extraction.structure_extractor import UnifiedStructureExtractor
from src.ingestion.urdu_ocr import OCR_TEXT_DIR
from src.ingestion.pdf_parser import LegalPDFParser
from src.utils.file_utils import ensure_directory, save_json, write_text
from src.utils.logger import setup_logger
from src.utils.schemas import ContractDocument, JudgmentDocument, StatuteDocument

logger = setup_logger("corpus_extraction")

STRUCTURED_DIR = Path("data/structured")
REPORT_PATH = Path("evaluations/extraction_report.md")
EXTRACTABLE_TYPES = ("Statute", "Judgment", "Contract")


def _english_ocr_engine():
    """Tesseract (English) for scanned English judgments, or None if unavailable."""
    try:
        from src.ingestion.ocr_engine import TesseractUrduOCR
        return TesseractUrduOCR(languages="eng")
    except Exception as exc:  # pragma: no cover - depends on local install
        logger.warning("English OCR unavailable (%s); scanned pages will be skipped.", exc)
        return None


def extract_corpus(
    inventory_path: str | Path = "inventory.csv",
    output_dir: Optional[Path] = STRUCTURED_DIR,
    use_ocr: bool = True,
    types: Tuple[str, ...] = EXTRACTABLE_TYPES,
    include_urdu_laws: bool = True,
) -> List[BaseModel]:
    """Extract every inventory row of the given types; optionally save JSON + report."""
    inventory = pd.read_csv(inventory_path)
    selected = inventory["type"].isin(types)
    if include_urdu_laws:
        has_ocr = inventory["document_id"].astype(str).map(
            lambda doc_id: doc_id.startswith("PKCODE_URDU_") and any((OCR_TEXT_DIR / doc_id).glob("page_*.txt")))
        selected |= has_ocr
    rows = inventory[selected].to_dict(orient="records")
    parser = LegalPDFParser(ocr_engine=_english_ocr_engine() if use_ocr else None)
    extractor = UnifiedStructureExtractor(parser=parser)

    documents: List[BaseModel] = []
    for number, row in enumerate(rows, start=1):
        if number % 50 == 0:
            logger.info("Extracted %d/%d documents", number, len(rows))
        try:
            documents.append(extractor.extract_record(row))
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", row["document_id"], exc)

    if output_dir is not None:
        for doc in documents:
            folder = ensure_directory(Path(output_dir) / type(doc).__name__.replace("Document", "").lower())
            save_json(doc.model_dump(exclude={"raw_text", "full_text"}), folder / f"{doc.document_id}.json")
        write_text(coverage_report(documents), REPORT_PATH)
        logger.info("Wrote %d structured JSON files to %s and %s", len(documents), output_dir, REPORT_PATH)
    return documents


def _share(docs: List[BaseModel], check) -> str:
    hits = sum(1 for doc in docs if check(doc))
    return f"{hits}/{len(docs)} ({100 * hits / max(1, len(docs)):.0f}%)"


def coverage_report(documents: List[BaseModel]) -> str:
    """Markdown table of how often each field was found (presence, not correctness)."""
    statutes = [d for d in documents if isinstance(d, StatuteDocument) and d.language != "Urdu"]
    urdu_laws = [d for d in documents if isinstance(d, StatuteDocument) and d.language == "Urdu"]
    urdu_pages = [s for d in urdu_laws for c in d.chapters for s in c.sections]
    judgments = [d for d in documents if isinstance(d, JudgmentDocument)]
    contracts = [d for d in documents if isinstance(d, ContractDocument) and not d.document_id.startswith("CONT_SYNTH")]
    sections = [s for d in statutes for c in d.chapters for s in c.sections]

    rows: List[Tuple[str, str, str]] = [
        ("Statute", "documents with sections", _share(statutes, lambda d: any(c.sections for c in d.chapters))),
        ("Statute", "sections / articles / rules found", str(len(sections))),
        ("Statute", "sections with start page", _share(sections, lambda s: s.page_start is not None)),
        ("Statute", "preamble", _share(statutes, lambda d: bool(d.preamble))),
        ("Urdu law (OCR)", "laws with OCR text", _share(urdu_laws, lambda d: any(c.sections for c in d.chapters))),
        ("Urdu law (OCR)", "pages with text (one unit each)", str(len(urdu_pages))),
        ("Urdu law (OCR)", "pages still without OCR text", str(sum(len(d.pages_needing_ocr) for d in urdu_laws))),
        ("Urdu law (OCR)", "year from official title", _share(urdu_laws, lambda d: d.year > 0)),
        ("Judgment", "case number", _share(judgments, lambda d: d.case_number != "Unknown")),
        ("Judgment", "petitioner / appellant", _share(judgments, lambda d: d.parties.appellant_or_petitioner != "Unknown")),
        ("Judgment", "respondent", _share(judgments, lambda d: d.parties.respondent != "Unknown")),
        ("Judgment", "bench / author judge", _share(judgments, lambda d: bool(d.bench))),
        ("Judgment", "year", _share(judgments, lambda d: d.year is not None)),
        ("Judgment", "date of hearing", _share(judgments, lambda d: bool(d.date_of_hearing))),
        ("Judgment", "case-law citations", _share(judgments, lambda d: bool(d.citations))),
        ("Judgment", "statutes cited", _share(judgments, lambda d: bool(d.statutes_cited))),
        ("Judgment", "numbered paragraphs (>= 3)", _share(judgments, lambda d: len(d.paragraphs) >= 3)),
        ("Judgment", "holding with outcome word", _share(judgments, lambda d: d.outcome is not None)),
        ("Judgment", "pages still needing OCR", _share(judgments, lambda d: bool(d.pages_needing_ocr))),
        ("Contract (CUAD)", "title", _share(contracts, lambda d: d.contract_title != "Untitled contract")),
        ("Contract (CUAD)", "two parties", _share(contracts, lambda d: len(d.parties) == 2)),
        ("Contract (CUAD)", "effective date", _share(contracts, lambda d: bool(d.effective_date))),
        ("Contract (CUAD)", "governing law", _share(contracts, lambda d: bool(d.governing_law))),
        ("Contract (CUAD)", "3+ clauses", _share(contracts, lambda d: len(d.clauses) >= 3)),
    ]
    table = tabulate(rows, headers=["Type", "Field", "Found in"], tablefmt="github")
    return f"""# Structure Extraction Coverage

Documents: {len(statutes)} English statutes, {len(urdu_laws)} Urdu laws (OCR), {len(judgments)} judgments,
{len(contracts)} CUAD contracts (the 20 synthetic contracts use their generated JSON and are not counted).
Urdu laws are split by page, not by section: EasyOCR drops the "۔" after Urdu
section numbers, so section headings cannot be detected reliably.

"Found in" measures whether a field was extracted, **not** whether it is correct;
correctness has not been checked against a hand-labelled set. Fields that cannot be
found are left empty rather than filled with defaults.

{table}
"""
