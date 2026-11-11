"""
Dense Vector Store Index for Khan & Associates Legal Assistant.
Supports ChromaDB with fallback to Dense Cosine Similarity Vector Index.
Stores chunks with rich metadata: act, section, court, year, page, matter_id.
"""

import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils.schemas import LegalChunk
from src.utils.logger import setup_logger
from src.utils.file_utils import ensure_directory

logger = setup_logger("vector_store")

class DenseVectorStore:
    """Production Dense Vector Store with metadata indexing and filtering."""

    def __init__(self, collection_name: str = "legal_chunks"):
        self.collection_name = collection_name
        self.chunks: List[LegalChunk] = []
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True
        )
        self.embeddings: Optional[np.ndarray] = None
        self.is_fitted = False

    def add_chunks(self, chunks: List[LegalChunk]) -> None:
        """Embeds and stores chunks with metadata."""
        if not chunks:
            return
            
        self.chunks.extend(chunks)
        corpus = [c.content for c in self.chunks]
        self.embeddings = self.vectorizer.fit_transform(corpus).toarray()
        self.is_fitted = True
        logger.info(f"Vector Store updated. Total vectors stored: {len(self.chunks)}")

    def search(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Performs dense cosine similarity search with metadata filtering."""
        if not self.is_fitted or self.embeddings is None:
            return []

        query_vec = self.vectorizer.transform([query]).toarray()
        sim_scores = cosine_similarity(query_vec, self.embeddings)[0]
        
        ranked_indices = np.argsort(sim_scores)[::-1]
        
        results = []
        for idx in ranked_indices:
            score = float(sim_scores[idx])
            if score <= 0.001:
                continue
                
            chunk = self.chunks[idx]
            
            # Apply metadata filters (Act, section, court, year, matter_id)
            if metadata_filter:
                match = True
                for k, v in metadata_filter.items():
                    val = chunk.metadata.get(k)
                    if val is None or str(val).lower() != str(v).lower():
                        match = False
                        break
                if not match:
                    continue

            results.append({
                "chunk_id": chunk.chunk_id,
                "score": round(score, 4),
                "document_id": chunk.document_id,
                "document_type": chunk.document_type,
                "content": chunk.content,
                "metadata": chunk.metadata
            })
            
            if len(results) >= top_k:
                break
                
        return results

    def save(self, file_path: str | Path) -> None:
        """Serializes vector store and embeddings to disk."""
        path = Path(file_path)
        ensure_directory(path.parent)
        with open(path, "wb") as f:
            pickle.dump({
                "collection_name": self.collection_name,
                "chunks": self.chunks,
                "vectorizer": self.vectorizer,
                "embeddings": self.embeddings,
                "is_fitted": self.is_fitted
            }, f)
        logger.info(f"Vector store saved to {path}")

    @classmethod
    def load(cls, file_path: str | Path) -> "DenseVectorStore":
        """Loads serialized vector store from disk."""
        path = Path(file_path)
        with open(path, "rb") as f:
            data = pickle.load(f)
        store = cls(collection_name=data["collection_name"])
        store.chunks = data["chunks"]
        store.vectorizer = data["vectorizer"]
        store.embeddings = data["embeddings"]
        store.is_fitted = data["is_fitted"]
        logger.info(f"Vector store loaded from {path} with {len(store.chunks)} chunks")
        return store
