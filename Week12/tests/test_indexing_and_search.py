"""
Unit tests for Task 5: Indexing and Hybrid Search.
"""
from pathlib import Path
import pytest
from src.utils.schemas import LegalChunk
from src.indexing.bm25_index import LegalBM25Index
from src.indexing.vector_store import DenseVectorStore
from src.indexing.hybrid_search import HybridLegalSearchEngine

@pytest.fixture
def sample_chunks():
    return [
        LegalChunk(
            chunk_id="CHK_001",
            document_id="STAT_002",
            document_type="Statute",
            strategy="section_level",
            content="Section 302 Punishment of Qatl-i-amd. Death or imprisonment for life as tazir.",
            token_count=13,
            metadata={"act": "Pakistan Penal Code", "section": "Section 302", "year": 1860, "court": "Federal"}
        ),
        LegalChunk(
            chunk_id="CHK_002",
            document_id="STAT_003",
            document_type="Statute",
            strategy="section_level",
            content="Section 497 When bail may be taken in case of non-bailable offence.",
            token_count=13,
            metadata={"act": "Code of Criminal Procedure", "section": "Section 497", "year": 1898, "court": "Federal"}
        ),
        LegalChunk(
            chunk_id="CHK_003",
            document_id="CONT_001",
            document_type="Contract",
            strategy="section_level",
            content="Clause 5 Governing Law and Jurisdiction in Delaware United States.",
            token_count=10,
            metadata={"contract_title": "Commercial NDA", "section": "Clause 5", "court": "Delaware"}
        )
    ]

def test_bm25_index_and_search(sample_chunks):
    bm25 = LegalBM25Index()
    bm25.add_chunks(sample_chunks)
    res = bm25.search("punishment qatl-i-amd", top_k=1)
    assert len(res) == 1
    assert res[0]["chunk_id"] == "CHK_001"

def test_vector_store_and_search(sample_chunks):
    vstore = DenseVectorStore()
    vstore.add_chunks(sample_chunks)
    res = vstore.search("non-bailable bail offence", top_k=1)
    assert len(res) == 1
    assert res[0]["chunk_id"] == "CHK_002"

def test_vector_store_persistence_and_metadata_filter(sample_chunks, tmp_path):
    vstore = DenseVectorStore(collection_name="persistence_test")
    vstore.add_chunks(sample_chunks)
    index_path = tmp_path / "vectors.chroma"
    vstore.save(index_path)

    loaded = DenseVectorStore.load(index_path)
    results = loaded.search(
        "non-bailable bail",
        top_k=3,
        metadata_filter={"section": "Section 497"},
    )
    assert [result["chunk_id"] for result in results] == ["CHK_002"]

def test_hybrid_search(sample_chunks):
    bm25 = LegalBM25Index()
    bm25.add_chunks(sample_chunks)
    vstore = DenseVectorStore()
    vstore.add_chunks(sample_chunks)
    
    engine = HybridLegalSearchEngine(bm25, vstore)
    res = engine.search("qatl-i-amd section 302", top_k=1)
    assert len(res) == 1
    assert res[0]["chunk_id"] == "CHK_001"
    assert "rrf_score" in res[0]
