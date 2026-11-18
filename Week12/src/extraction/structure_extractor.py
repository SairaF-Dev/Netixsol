"""
Unified structure extraction for Khan & Associates Legal Assistant Pipeline.

`extract_record` takes an inventory.csv row and routes it to the statute,
judgment or contract extractor, passing reliable hints from the inventory
(act name, case number from the court's file name, neutral citation, CUAD
category). Pakistan Code Urdu laws (PKCODE_URDU_*) are built from their OCR page
texts; other Scanned/Urdu rows (the OCR benchmark pages) are not extracted.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.extraction.contract_extractor import ContractStructureExtractor
from src.extraction.judgment_extractor import JudgmentStructureExtractor
from src.extraction.statute_extractor import StatuteStructureExtractor
from src.extraction.urdu_statute_extractor import extract_urdu_law
from src.utils.logger import setup_logger

logger = setup_logger("structure_extractor")


def _supreme_court_case_number(document_id: str) -> Optional[str]:
    """'SC_c.p._2413_l_2025' -> 'C.P. 2413-L/2025'."""
    parts = document_id.removeprefix("SC_").rstrip(".").split("_")
    rest = parts[1:]
    # The year is the last 4-digit token after the case number; anything after it
    # (decision dates, "r1", "mv", "hj3" ...) is a file-name suffix.
    year_positions = [i for i, p in enumerate(rest) if i > 0 and re.fullmatch(r"(?:19|20)\d\d[a-z]?", p)]
    if not year_positions:
        return None
    year_at = year_positions[0]
    numbers = [p for p in rest[:year_at] if p]
    return f"{parts[0].upper()} {'-'.join(numbers).upper()}/{rest[year_at][:4]}"


def _contract_type(record: Dict[str, Any]) -> Optional[str]:
    title = str(record.get("title", ""))
    if title.startswith("CUAD ") and ":" in title:
        return title[5:].split(":", 1)[0].strip()
    stem = Path(str(record["file_path"])).stem
    if "_" in stem:
        return re.sub(r"\d+$", "", stem.rsplit("_", 1)[-1]).strip()
    return None


class UnifiedStructureExtractor:
    """Routes documents to the statute, judgment or contract extractor."""

    def __init__(self, parser: Any = None):
        self.parser = parser
        self.statute_extractor = StatuteStructureExtractor()
        self.judgment_extractor = JudgmentStructureExtractor()
        self.contract_extractor = ContractStructureExtractor()

    def extract_record(self, record: Dict[str, Any]) -> BaseModel:
        """Extract one inventory.csv row (Statute, Judgment or Contract)."""
        doc_type = record["type"]
        doc_id = str(record["document_id"])
        path = Path(str(record["file_path"]))

        if doc_id.startswith("PKCODE_URDU_"):
            return extract_urdu_law(record)

        if doc_type == "Statute":
            return self.statute_extractor.extract_from_file(
                path, doc_id=doc_id, act_name=str(record["title"]), parser=self.parser)

        if doc_type == "Judgment":
            if doc_id.startswith("LHC_"):
                code = doc_id.removeprefix("LHC_")
                neutral = re.sub(r"^(\d{4})LHC(\d+)$", r"\1 LHC \2", code)
                return self.judgment_extractor.extract_from_file(
                    path, doc_id=doc_id, parser=self.parser,
                    court_hint="Lahore High Court", neutral_citation=neutral)
            return self.judgment_extractor.extract_from_file(
                path, doc_id=doc_id, parser=self.parser, court_hint="Supreme Court of Pakistan",
                case_number_hint=_supreme_court_case_number(doc_id))

        if doc_type == "Contract":
            # Synthetic contracts keep their generated structure next to the PDF.
            sibling_json = path.with_suffix(".json")
            if sibling_json.is_file():
                return self.contract_extractor.extract_from_file(sibling_json, doc_id=doc_id)
            return self.contract_extractor.extract_from_file(
                path, doc_id=doc_id, parser=self.parser,
                title_hint=str(record.get("title") or ""), contract_type=_contract_type(record))

        raise ValueError(f"Structure extraction is not available for type {doc_type!r} ({doc_id})")

    def extract(self, file_path: str | Path, doc_type: str) -> BaseModel:
        """Extract a single file of a known type (no inventory hints)."""
        path = Path(file_path)
        extractor = {
            "Statute": self.statute_extractor,
            "Judgment": self.judgment_extractor,
            "Contract": self.contract_extractor,
        }[doc_type]
        return extractor.extract_from_file(path, parser=self.parser)
