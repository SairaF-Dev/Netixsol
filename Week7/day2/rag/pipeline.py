"""
RAG Pipeline — ties loader -> chunking -> embeddings -> vectorstore -> retriever -> generator

Run: python rag/pipeline.py
Uses the offline TF-IDF embedder + in-memory store + no-context-fallback
generator by default, so it runs with zero API keys / zero internet for
grading. Swap in OpenAIEmbedder / ChromaVectorStore / generate_answer_openai
for the production deployment.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loader import load_all_documents
from chunking import chunk_documents
from embeddings import get_embedder
from vectorstore import InMemoryVectorStore
from retriever import Retriever
from generator import generate_answer_no_context_fallback


def build_pipeline(chunk_strategy="sentence", chunk_size=200):
    documents = load_all_documents()
    chunks = chunk_documents(documents, strategy=chunk_strategy, chunk_size=chunk_size)

    embedder = get_embedder("tfidf")
    embedder.fit([c["text"] for c in chunks])
    vectors = embedder.embed_batch([c["text"] for c in chunks])

    store = InMemoryVectorStore()
    store.add(chunks, vectors)

    retriever = Retriever(embedder, store)
    return retriever, len(documents), len(chunks)


def answer_query(retriever, query, top_k=3):
    retrieved = retriever.retrieve(query, top_k=top_k)
    answer = generate_answer_no_context_fallback(query, retrieved)
    return answer, retrieved


if __name__ == "__main__":
    retriever, n_docs, n_chunks = build_pipeline()
    print(f"Indexed {n_docs} documents -> {n_chunks} chunks\n")

    test_queries = [
        "Property book karne ke liye kitni advance chahiye?",
        "DHA Phase 6 ka bungalow kaisa hai?",
        "Kya installment plan available hai?",
    ]
    for q in test_queries:
        answer, retrieved = answer_query(retriever, q)
        print(f"Q: {q}")
        print(f"Top match: {retrieved[0]['chunk_id']} (score={retrieved[0]['score']:.3f})")
        print(f"A: {answer}\n")
