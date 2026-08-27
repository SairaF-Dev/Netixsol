import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = PROJECT_ROOT / "02_rag"

sys.path.insert(0, str(RAG_DIR))

from loader import load_documents
from chunker import chunk_documents
from embeddings import LocalEmbedding
from vector_store import ChromaVectorStore


QUESTIONS = [
    (
        "What amenities are listed for Skyline Residences?",
        "skyline_residences.md",
    ),
    (
        "What is the demo price of DHA Pearl Apartments?",
        "dha_pearl_apartments.md",
    ),
    (
        "What is the demo price of Bahria Grand Apartments?",
        "bahria_grand_apartments.md",
    ),
    (
        "Can Sara guarantee investment returns?",
        "real_estate_faq.md",
    ),
]


def evaluate(chunk_size):
    documents_dir = RAG_DIR / "documents"

    docs = load_documents(str(documents_dir))

    print(f"Documents loaded: {len(docs)}")

    chunks = chunk_documents(
        docs,
        chunk_size=chunk_size,
        overlap_sentences=1,
    )

    print(f"Chunks created: {len(chunks)}")

    embedder = LocalEmbedding()

    store = ChromaVectorStore(
        embedder=embedder,
        persist_directory=str(
            Path(__file__).resolve().parent
            / f"evaluation_chroma_{chunk_size}"
        ),
        collection_name=f"evaluation_{chunk_size}",
    )

    store.add(chunks)

    hits = 0

    for question, expected_source in QUESTIONS:
        results = store.search(
            question,
            top_k=3,
        )

        if any(
            expected_source in result["source"]
            for result in results
        ):
            hits += 1

    return {
        "chunk_size": chunk_size,
        # "overlap": 1,
        "overlap_sentences": 1,
        "chunks": len(chunks),
        "questions": len(QUESTIONS),
        "top3_source_hit_rate": hits / len(QUESTIONS),
    }

if __name__ == "__main__":
    print("\nCHUNK SIZE EVALUATION")
    print("=" * 60)

    for size in (256, 512, 1024):
        result = evaluate(size)

        print(
            f"\nChunk size: {result['chunk_size']}"
            f"\nOverlap sentences: {result['overlap_sentences']}"
            f"\nChunks: {result['chunks']}"
            f"\nQuestions: {result['questions']}"
            f"\nTop-3 source hit rate: "
            f"{result['top3_source_hit_rate']:.2%}"
        )