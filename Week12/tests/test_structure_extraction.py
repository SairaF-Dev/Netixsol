"""
Unit tests for Task 3: Legal Structure Extraction.
"""
from pathlib import Path
import pytest
from src.extraction.structure_extractor import UnifiedStructureExtractor
from src.utils.schemas import StatuteDocument, JudgmentDocument, ContractDocument

def test_extract_statute_structure():
    extractor = UnifiedStructureExtractor()
    doc_path = Path("data/statutes/STAT_002.json")
    if doc_path.exists():
        statute = extractor.extract(doc_path, "Statute")
        assert isinstance(statute, StatuteDocument)
        assert "Penal Code" in statute.act_name
        assert len(statute.chapters) >= 1

def test_extract_judgment_structure():
    extractor = UnifiedStructureExtractor()
    doc_path = Path("data/judgments/JUD_001.json")
    if doc_path.exists():
        judgment = extractor.extract(doc_path, "Judgment")
        assert isinstance(judgment, JudgmentDocument)
        assert judgment.case_number != ""
        assert judgment.holding != ""
        assert judgment.parties.appellant_or_petitioner != ""

def test_extract_contract_structure():
    extractor = UnifiedStructureExtractor()
    doc_path = Path("data/contracts/cuad/CUAD_001.json")
    if doc_path.exists():
        contract = extractor.extract(doc_path, "Contract")
        assert isinstance(contract, ContractDocument)
        assert len(contract.clauses) >= 1
        assert len(contract.parties) >= 1
