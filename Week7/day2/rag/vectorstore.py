"""
Vector Store — Task 2, RAG Pipeline (step 4/5)

InMemoryVectorStore: dependency-free, cosine-similarity store. Good
for dev/testing and for this project's small (~25 chunk) corpus.

ChromaVectorStore: wraps chromadb (pip install chromadb) for the
production path — persistent storage, filtering by metadata, and
scaling past a few thousand chunks.
"""
import math


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1e-9
    norm_b = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (norm_a * norm_b)


class InMemoryVectorStore:
    def __init__(self):
        self.records = []  # list of {chunk_id, text, vector, metadata}

    def add(self, chunks, vectors):
        for chunk, vec in zip(chunks, vectors):
            self.records.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "vector": vec,
                "metadata": chunk.get("metadata", {}),
                "source": chunk.get("source"),
            })

    def search(self, query_vector, top_k=3, metadata_filter=None):
        candidates = self.records
        if metadata_filter:
            candidates = [
                r for r in candidates
                if all(r["metadata"].get(k) == v for k, v in metadata_filter.items())
            ]
        scored = [
            (cosine_similarity(query_vector, r["vector"]), r) for r in candidates
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"score": score, **r} for score, r in scored[:top_k]]


class ChromaVectorStore:
    """Production vector store wrapper. Requires: pip install chromadb"""

    def __init__(self, collection_name="real_estate_kb", persist_dir="./chroma_data"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(collection_name)

    def add(self, chunks, vectors):
        self.collection.add(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=vectors,
            documents=[c["text"] for c in chunks],
            metadatas=[c.get("metadata", {}) for c in chunks],
        )

    def search(self, query_vector, top_k=3, metadata_filter=None):
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=metadata_filter or None,
        )
        out = []
        for i in range(len(results["ids"][0])):
            out.append({
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],
            })
        return out
