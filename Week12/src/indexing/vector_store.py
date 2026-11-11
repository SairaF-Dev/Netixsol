"""SQLite-backed dense vector index using multilingual sentence embeddings."""

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from src.utils.logger import setup_logger
from src.utils.schemas import LegalChunk

logger = setup_logger("vector_store")
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


@lru_cache(maxsize=1)
def _load_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")


class DenseVectorStore:
    """Persist chunks and multilingual embeddings in SQLite for exact cosine search."""

    def __init__(
        self,
        collection_name: str = "legal_chunks",
        persist_directory: str | Path | None = None,
    ):
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory) if persist_directory else None
        self.model = _load_embedding_model()
        if self.persist_directory:
            self.persist_directory.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(self.persist_directory))
        else:
            self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                metadata_json TEXT NOT NULL,
                embedding BLOB NOT NULL
            )
            """
        )
        self.connection.commit()

    @property
    def chunks(self) -> List[LegalChunk]:
        rows = self.connection.execute(
            """
            SELECT chunk_id, document_id, document_type, strategy, content,
                   token_count, metadata_json
            FROM legal_chunks ORDER BY chunk_id
            """
        ).fetchall()
        return [
            LegalChunk(
                chunk_id=row[0],
                document_id=row[1],
                document_type=row[2],
                strategy=row[3],
                content=row[4],
                token_count=row[5],
                metadata=json.loads(row[6]),
            )
            for row in rows
        ]

    def add_chunks(self, chunks: List[LegalChunk]) -> None:
        """Embed chunks and insert or update their SQLite records."""
        if not chunks:
            return
        embeddings = self.model.encode(
            [f"passage: {chunk.content}" for chunk in chunks],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32)
        records = [
            (
                chunk.chunk_id,
                chunk.document_id,
                chunk.document_type,
                chunk.strategy,
                chunk.content,
                chunk.token_count,
                json.dumps(chunk.metadata, ensure_ascii=False),
                embedding.tobytes(),
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        self.connection.executemany(
            """
            INSERT INTO legal_chunks (
                chunk_id, document_id, document_type, strategy, content,
                token_count, metadata_json, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id=excluded.document_id,
                document_type=excluded.document_type,
                strategy=excluded.strategy,
                content=excluded.content,
                token_count=excluded.token_count,
                metadata_json=excluded.metadata_json,
                embedding=excluded.embedding
            """,
            records,
        )
        self.connection.commit()
        total_chunks = self.connection.execute(
            "SELECT COUNT(*) FROM legal_chunks"
        ).fetchone()[0]
        logger.info("Dense vector index updated: %s chunks", total_chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return nearest chunks by cosine similarity, with exact metadata filters."""
        if top_k <= 0:
            return []
        query_embedding = self.model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0].astype(np.float32)
        rows = self.connection.execute(
            """
            SELECT chunk_id, document_id, document_type, content,
                   metadata_json, embedding
            FROM legal_chunks
            """
        ).fetchall()

        candidates = []
        for chunk_id, document_id, document_type, content, metadata_json, embedding_bytes in rows:
            metadata = json.loads(metadata_json)
            if metadata_filter and any(
                key not in metadata or str(metadata[key]).casefold() != str(value).casefold()
                for key, value in metadata_filter.items()
            ):
                continue
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            score = float(np.dot(query_embedding, embedding))
            candidates.append(
                (
                    score,
                    {
                        "chunk_id": chunk_id,
                        "score": round(score, 4),
                        "document_id": document_id,
                        "document_type": document_type,
                        "content": content,
                        "metadata": metadata,
                    },
                )
            )

        candidates.sort(key=lambda result: result[0], reverse=True)
        return [result for _, result in candidates[:top_k]]

    @staticmethod
    def _database_path(file_path: str | Path) -> Path:
        path = Path(file_path)
        return path.with_suffix(".sqlite3") if path.suffix == ".pkl" else path

    def save(self, file_path: str | Path) -> None:
        """Persist the in-memory index to a SQLite database file."""
        target = self._database_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.persist_directory == target:
            self.connection.commit()
            return
        target_connection = sqlite3.connect(str(target))
        try:
            self.connection.backup(target_connection)
            target_connection.commit()
        finally:
            target_connection.close()
        logger.info("Dense vector index persisted to %s", target)

    @classmethod
    def load(cls, file_path: str | Path) -> "DenseVectorStore":
        """Open an existing SQLite vector index."""
        target = cls._database_path(file_path)
        if not target.is_file():
            raise FileNotFoundError(f"SQLite vector index does not exist: {target}")
        return cls(persist_directory=target)
