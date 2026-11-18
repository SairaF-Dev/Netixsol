"""
Fixed-Size Chunking Strategy for Legal Documents.
Splits text into fixed token/character windows with sliding overlap.
"""

from typing import List, Dict, Any
from src.utils.schemas import LegalChunk

class FixedSizeChunker:
    """Standard baseline fixed-window chunker with sliding overlap."""

    def __init__(self, chunk_size: int = 250, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, document_id: str, document_type: str, metadata: Dict[str, Any] = None) -> List[LegalChunk]:
        words = text.split()
        chunks = []
        start = 0
        base_meta = metadata or {}
        chunk_idx = 0
        
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_content = " ".join(chunk_words)
            
            chunk_meta = dict(base_meta)
            chunk_meta.update({
                "chunk_index": chunk_idx,
                "start_word": start,
                "end_word": end,
                "strategy": "fixed_size"
            })
            
            chunks.append(LegalChunk(
                chunk_id=f"{document_id}_FIXED_{chunk_idx:03d}",
                document_id=document_id,
                document_type=document_type,
                strategy="fixed_size",
                content=chunk_content,
                token_count=len(chunk_words),
                metadata=chunk_meta
            ))
            
            chunk_idx += 1
            start += (self.chunk_size - self.chunk_overlap)
            if start >= len(words) - self.chunk_overlap and end == len(words):
                break
                
        return chunks
