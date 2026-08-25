"""
Semantic Retrieval — Task 3 (semantic half)

Use vector retrieval for anything free-text, descriptive, or where the
customer's phrasing won't match a keyword exactly: brochures,
descriptions, FAQs. There's no single "correct" row to look up here —
it's about finding the most SIMILAR content, which is what embeddings
are for.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag"))

from loader import load_faqs, load_brochures
from chunking import chunk_documents
from embeddings import get_embedder
from vectorstore import InMemoryVectorStore
from retriever import Retriever


def build_semantic_index(source="all"):
    if source == "faqs":
        documents = load_faqs()
    elif source == "brochures":
        documents = load_brochures()
    else:
        documents = load_faqs() + load_brochures()

    chunks = chunk_documents(documents, strategy="sentence", chunk_size=200)
    embedder = get_embedder("tfidf")
    embedder.fit([c["text"] for c in chunks])
    vectors = embedder.embed_batch([c["text"] for c in chunks])

    store = InMemoryVectorStore()
    store.add(chunks, vectors)
    return Retriever(embedder, store)


if __name__ == "__main__":
    retriever = build_semantic_index()
    results = retriever.retrieve("kya property ki price kam ho sakti hai", top_k=2)
    for r in results:
        print(f"{r['chunk_id']} (score={r['score']:.3f}): {r['text'][:80]}")
