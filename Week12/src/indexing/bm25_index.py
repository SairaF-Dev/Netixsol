"""
BM25 Lexical Index for Khan & Associates Legal Assistant.
Provides keyword retrieval over legal chunks with metadata filtering.
"""

import pickle
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from src.utils.schemas import LegalChunk
from src.utils.logger import setup_logger
from src.utils.file_utils import ensure_directory

logger = setup_logger("bm25_index")

def tokenize_legal_text(text: str) -> List[str]:
    """Tokenizes text preserving section numbers, acronyms, and legal identifiers."""
    clean_text = text.lower()
    # Normalize common abbreviations and keep alphanumeric tokens with hyphens
    tokens = re.findall(r"[a-z0-9\u0600-\u06FF\-_]+", clean_text)
    return tokens

class LegalBM25Index:
    """Production BM25 Okapi index for legal statutes, case law, and contracts."""

    def __init__(self):
        self.chunks: List[LegalChunk] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def add_chunks(self, chunks: List[LegalChunk]) -> None:
        """Adds and indexes a list of legal chunks."""
        self.chunks.extend(chunks)
        new_tokens = [tokenize_legal_text(c.content) for c in chunks]
        self.tokenized_corpus.extend(new_tokens)
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        logger.info(f"BM25 Index updated. Total chunks indexed: {len(self.chunks)}")

    def search(self, query: str, top_k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Searches index using BM25 with optional metadata filtering."""
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = tokenize_legal_text(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Pair chunk with score
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        
        results = []
        for idx in ranked_indices:
            score = scores[idx]
            if score <= 0.0:
                continue
                
            chunk = self.chunks[idx]
            
            # Apply metadata filters (e.g. court, year, act, section, matter_id)
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
                "score": round(float(score), 4),
                "document_id": chunk.document_id,
                "document_type": chunk.document_type,
                "content": chunk.content,
                "metadata": chunk.metadata
            })
            
            if len(results) >= top_k:
                break
                
        return results

    def save(self, file_path: str | Path) -> None:
        """Saves BM25 index state to disk."""
        path = Path(file_path)
        ensure_directory(path.parent)
        with open(path, "wb") as f:
            pickle.dump({"chunks": self.chunks, "tokenized_corpus": self.tokenized_corpus}, f)
        logger.info(f"BM25 index saved to {path}")

    @classmethod
    def load(cls, file_path: str | Path) -> "LegalBM25Index":
        """Loads BM25 index state from disk."""
        path = Path(file_path)
        with open(path, "rb") as f:
            data = pickle.load(f)
        index = cls()
        index.chunks = data["chunks"]
        index.tokenized_corpus = data["tokenized_corpus"]
        index.bm25 = BM25Okapi(index.tokenized_corpus)
        logger.info(f"BM25 index loaded from {path} with {len(index.chunks)} chunks")
        return index
