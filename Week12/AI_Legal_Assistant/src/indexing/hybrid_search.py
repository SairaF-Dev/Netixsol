"""
Hybrid Search Engine for Khan & Associates Legal Assistant.
Combines BM25 Lexical Ranking and Dense Vector Similarity using Reciprocal Rank Fusion (RRF).
"""

from typing import List, Dict, Any, Optional
from src.indexing.bm25_index import LegalBM25Index
from src.indexing.vector_store import DenseVectorStore
from src.utils.logger import setup_logger

logger = setup_logger("hybrid_search")

class HybridLegalSearchEngine:
    """Enterprise Hybrid Search combining BM25 keyword matching and Dense Semantic search."""

    def __init__(self, bm25_index: LegalBM25Index, vector_store: DenseVectorStore, rrf_k: int = 60):
        self.bm25_index = bm25_index
        self.vector_store = vector_store
        self.rrf_k = rrf_k  # Smoothing constant for Reciprocal Rank Fusion

    def search(
        self,
        query: str,
        top_k: int = 5,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search using Reciprocal Rank Fusion:
        RRF_score(d) = bm25_w * (1 / (K + rank_bm25(d))) + vec_w * (1 / (K + rank_vec(d)))
        """
        # Fetch larger candidate pool from each retriever
        bm25_hits = self.bm25_index.search(query, top_k=top_k * 3, metadata_filter=metadata_filter)
        vec_hits = self.vector_store.search(query, top_k=top_k * 3, metadata_filter=metadata_filter)

        fused_scores: Dict[str, float] = {}
        chunk_lookup: Dict[str, Dict[str, Any]] = {}

        # Process BM25 ranks
        for rank, hit in enumerate(bm25_hits, start=1):
            cid = hit["chunk_id"]
            chunk_lookup[cid] = hit
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (bm25_weight * (1.0 / (self.rrf_k + rank)))

        # Process Vector ranks
        for rank, hit in enumerate(vec_hits, start=1):
            cid = hit["chunk_id"]
            chunk_lookup[cid] = hit
            fused_scores[cid] = fused_scores.get(cid, 0.0) + (vector_weight * (1.0 / (self.rrf_k + rank)))

        # Sort by fused score
        sorted_chunks = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

        final_results = []
        for cid, rrf_score in sorted_chunks[:top_k]:
            item = dict(chunk_lookup[cid])
            item["rrf_score"] = round(rrf_score, 6)
            final_results.append(item)

        return final_results
