"""
Unified Structure Extractor Router for Khan & Associates Legal Assistant Pipeline.
"""

from pathlib import Path
from typing import Dict, Any, Union
from pydantic import BaseModel

from src.extraction.statute_extractor import StatuteStructureExtractor
from src.extraction.judgment_extractor import JudgmentStructureExtractor
from src.extraction.contract_extractor import ContractStructureExtractor
from src.utils.schemas import StatuteDocument, JudgmentDocument, ContractDocument
from src.utils.logger import setup_logger

logger = setup_logger("structure_extractor")

class UnifiedStructureExtractor:
    """Enterprise router that extracts structured JSON based on document type."""

    def __init__(self):
        self.statute_extractor = StatuteStructureExtractor()
        self.judgment_extractor = JudgmentStructureExtractor()
        self.contract_extractor = ContractStructureExtractor()

    def extract(self, file_path: str | Path, doc_type: str = "auto") -> BaseModel:
        path = Path(file_path)
        name_lower = path.name.lower()
        
        # Heuristic doc_type detection if auto
        if doc_type == "auto":
            if "stat" in name_lower or "act" in name_lower or "ordinance" in name_lower:
                doc_type = "Statute"
            elif "jud" in name_lower or "appeal" in name_lower:
                doc_type = "Judgment"
            elif "cuad" in name_lower or "cont" in name_lower or "agreement" in name_lower:
                doc_type = "Contract"
            else:
                doc_type = "Judgment"

        if doc_type == "Statute":
            return self.statute_extractor.extract_from_file(path)
        elif doc_type == "Judgment":
            return self.judgment_extractor.extract_from_file(path)
        elif doc_type == "Contract":
            return self.contract_extractor.extract_from_file(path)
        else:
            # Fallback to judgment
            return self.judgment_extractor.extract_from_file(path)
