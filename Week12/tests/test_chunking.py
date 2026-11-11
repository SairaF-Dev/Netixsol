"""
Unit tests for Task 4: Chunking Strategies.
"""
from pathlib import Path
import pytest
from src.extraction.structure_extractor import UnifiedStructureExtractor
from src.chunking.fixed_chunker import FixedSizeChunker
from src.chunking.section_chunker import SectionLevelChunker
from src.chunking.parent_child_chunker import ParentChildChunker

def test_fixed_chunker():
    chunker = FixedSizeChunker(chunk_size=50, chunk_overlap=10)
    text = "word " * 120
    chunks = chunker.chunk_text(text, "DOC_TEST", "TestDoc")
    assert len(chunks) >= 2
    assert chunks[0].strategy == "fixed_size"
    assert chunks[0].metadata["chunk_index"] == 0

def test_section_chunker_statute():
    extractor = UnifiedStructureExtractor()
    chunker = SectionLevelChunker()
    doc_path = Path("data/statutes/STAT_001.json")
    if doc_path.exists():
        statute = extractor.extract(doc_path, "Statute")
        chunks = chunker.chunk_statute(statute)
        assert len(chunks) >= 2
        # Check metadata
        for c in chunks:
            assert "act" in c.metadata
            assert "section" in c.metadata

def test_parent_child_chunker():
    extractor = UnifiedStructureExtractor()
    chunker = ParentChildChunker()
    doc_path = Path("data/statutes/STAT_002.json")
    if doc_path.exists():
        statute = extractor.extract(doc_path, "Statute")
        parents, children = chunker.chunk_statute(statute)
        assert len(parents) > 0
        assert len(children) > 0
        # Check child links to parent
        for child in children:
            assert "parent_id" in child.metadata
            assert child.metadata["is_child"] is True
