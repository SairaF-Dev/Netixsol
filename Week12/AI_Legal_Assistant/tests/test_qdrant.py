"""Qdrant backend (src/indexing/qdrant_store.py) against an in-memory Qdrant: same rows and ranking as the
SQLite master copy, and single-document sync for uploads."""
import pytest

qdrant_client = pytest.importorskip("qdrant_client")

from src.chunking.section_chunker import SectionLevelChunker
from src.indexing.qdrant_store import QdrantDenseIndex, count, sync_all, sync_documents
from src.indexing.vector_store import DenseVectorStore
from src.rag.advanced import MemoryDenseIndex
from src.utils.schemas import ContractClause, ContractDocument


def _contract(doc_id, clauses):
    return ContractDocument(document_id=doc_id, contract_title=f"Agreement {doc_id}", contract_type="Services",
                            clauses=[ContractClause(clause_id=f"Clause {i}", clause_title=t, text=x) for i, (t, x) in enumerate(clauses, 1)])


@pytest.fixture()
def store(tmp_path):
    path = tmp_path / "vstore_legal.sqlite3"
    vectors = DenseVectorStore(persist_directory=path)
    chunker = SectionLevelChunker()
    vectors.add_chunks(chunker.chunk_contract(_contract("DOC_A", [
        ("Payment", "The Client shall pay every invoice within thirty days of receipt."),
        ("Governing Law", "This Agreement is governed by the laws of Pakistan.")])))
    vectors.add_chunks(chunker.chunk_contract(_contract("DOC_B", [
        ("Confidentiality", "Each party keeps the other party's information secret for five years.")])))
    vectors.connection.close()
    return path


def test_qdrant_returns_the_same_ranking_as_the_in_memory_index(store):
    client = qdrant_client.QdrantClient(":memory:")
    assert sync_all(client, sqlite_path=store) == count(client) == 5
    memory, qdrant = MemoryDenseIndex(store), QdrantDenseIndex(client=client)
    for question in ("When must invoices be paid?", "Which law governs the agreement?", "How long is information kept secret?"):
        assert [r["chunk_id"] for r in qdrant.search(question, 5)] == [r["chunk_id"] for r in memory.search(question, 5)]
    top = qdrant.search("When must invoices be paid?", 1)[0]
    assert top["document_id"] == "DOC_A" and "thirty days" in top["content"] and top["metadata"]["clause_title"] == "Payment"


def test_sync_documents_adds_and_removes_one_document(store):
    client = qdrant_client.QdrantClient(":memory:")
    sync_all(client, sqlite_path=store)
    vectors = DenseVectorStore.load(store)
    vectors.remove_documents(["DOC_B"])
    vectors.connection.close()
    assert sync_documents(["DOC_B"], client=client, sqlite_path=store) == 0
    assert count(client) == 3
    assert all(r["document_id"] == "DOC_A" for r in QdrantDenseIndex(client=client).search("secret information", 5))
