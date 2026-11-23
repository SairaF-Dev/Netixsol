"""
Qdrant vector database backend for the main search index (VECTOR_BACKEND=qdrant; used in Docker).

* The SQLite vector store (data/indices/vstore_legal.sqlite3) stays the master copy: it is what Day 1
  indexing and uploads write. Qdrant is the serving copy, filled from it with the SAME embeddings
  (multilingual-e5-small, normalised), so search results match the in-memory index (cosine = dot
  product on normalised vectors).
* `python -m src.indexing.qdrant_store sync` copies every passage into the collection (about a minute for
  11,232); `sync_documents([...])` copies or removes single documents (the upload job calls it).
* QDRANT_URL=http://qdrant:6333 points at the server (Docker); without it an embedded local Qdrant in
  data/qdrant/ is used (the same engine in-process, for tests and laptops).
* `QdrantDenseIndex` has the interface the retriever expects from `MemoryDenseIndex`: search(text, top_k,
  prefix, metadata_filter) -> rows. Access control stays in the retriever (src/rag/advanced.py `allow`).
"""

import argparse
import json
import os
import sqlite3
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np

COLLECTION = os.getenv("QDRANT_COLLECTION", "legal_chunks")
SQLITE_INDEX = Path("data/indices/vstore_legal.sqlite3")
_NAMESPACE = uuid.UUID("6f1c2a3e-5b7d-4c8e-9a1f-2b3c4d5e6f70")
BATCH = 256


def get_client():
    from qdrant_client import QdrantClient
    url = os.getenv("QDRANT_URL")
    if url:
        return QdrantClient(url=url, api_key=os.getenv("QDRANT_API_KEY") or None, timeout=60)
    return QdrantClient(path=os.getenv("QDRANT_PATH", "data/qdrant"))


@lru_cache(maxsize=1)
def _shared_client():
    return get_client()


def point_id(chunk_id: str) -> str:
    """Qdrant ids must be integers or UUIDs: a stable UUID from the chunk id."""
    return str(uuid.uuid5(_NAMESPACE, chunk_id))


def _rows_from_sqlite(path: Path, document_ids: Optional[List[str]] = None) -> Iterable[tuple]:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        sql = "SELECT chunk_id, document_id, document_type, content, metadata_json, embedding FROM legal_chunks"
        if document_ids:
            sql += f" WHERE document_id IN ({','.join('?' * len(document_ids))})"
        yield from con.execute(sql, document_ids or [])
    finally:
        con.close()


def _upsert(client, rows: Iterable[tuple], collection: str = COLLECTION) -> int:
    from qdrant_client.models import PointStruct
    n, batch = 0, []
    for chunk_id, document_id, document_type, content, metadata, embedding in rows:
        batch.append(PointStruct(id=point_id(chunk_id), vector=np.frombuffer(embedding, dtype=np.float32).tolist(),
                                 payload={"chunk_id": chunk_id, "document_id": document_id, "document_type": document_type,
                                          "content": content, "metadata": json.loads(metadata)}))
        if len(batch) == BATCH:
            client.upsert(collection_name=collection, points=batch)
            n, batch = n + len(batch), []
    if batch:
        client.upsert(collection_name=collection, points=batch)
        n += len(batch)
    return n


def _ensure_collection(client, dim: int, collection: str = COLLECTION, recreate: bool = False) -> None:
    from qdrant_client.models import Distance, PayloadSchemaType, VectorParams
    exists = client.collection_exists(collection)
    if exists and recreate:
        client.delete_collection(collection)
        exists = False
    if not exists:
        client.create_collection(collection, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
        try:   # index document_id so deletes and filters by document are fast (no-op in embedded mode)
            client.create_payload_index(collection, field_name="document_id", field_schema=PayloadSchemaType.KEYWORD)
        except Exception:
            pass


def sync_all(client=None, sqlite_path: Path = SQLITE_INDEX, collection: str = COLLECTION) -> int:
    """Rebuild the collection from the SQLite master copy."""
    client = client or get_client()
    first = next(iter(_rows_from_sqlite(sqlite_path)), None)
    if first is None:
        raise RuntimeError(f"{sqlite_path} has no passages")
    _ensure_collection(client, len(np.frombuffer(first[5], dtype=np.float32)), collection, recreate=True)
    return _upsert(client, _rows_from_sqlite(sqlite_path), collection)


def sync_documents(document_ids: List[str], client=None, sqlite_path: Path = SQLITE_INDEX, collection: str = COLLECTION) -> int:
    """Make Qdrant match SQLite for these documents (added, changed or removed)."""
    from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchAny
    client = client or get_client()
    if client.collection_exists(collection):
        client.delete(collection_name=collection, points_selector=FilterSelector(
            filter=Filter(must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))])))
    rows = list(_rows_from_sqlite(sqlite_path, document_ids))
    if not rows:
        return 0
    _ensure_collection(client, len(np.frombuffer(rows[0][5], dtype=np.float32)), collection)
    return _upsert(client, rows, collection)


def count(client=None, collection: str = COLLECTION) -> int:
    client = client or get_client()
    return client.count(collection, exact=True).count if client.collection_exists(collection) else 0


def _payload_row(payload: Dict) -> Dict:
    return {"chunk_id": payload["chunk_id"], "document_id": payload["document_id"],
            "document_type": payload["document_type"], "content": payload["content"], "metadata": payload["metadata"]}


class QdrantDenseIndex:
    """Drop-in for MemoryDenseIndex (src/rag/advanced.py), searching the Qdrant collection."""

    def __init__(self, client=None, collection: str = COLLECTION):
        self.client = client or _shared_client()
        self.collection = collection
        self.by_id: Dict[str, Dict] = {}   # BM25 hits already carry the passage, so no id table is needed
        self._rows: Optional[List[Dict]] = None

    @property
    def rows(self) -> List[Dict]:
        """Every passage (only the 'metadata' configuration scans them): loaded once, on first use."""
        if self._rows is None:
            rows, offset = [], None
            while True:
                points, offset = self.client.scroll(self.collection, limit=1000, offset=offset, with_payload=True)
                rows += [_payload_row(p.payload) for p in points]
                if offset is None:
                    break
            self._rows = rows
        return self._rows

    def search(self, text: str, top_k: int = 30, prefix: str = "query: ", metadata_filter: Optional[Dict] = None) -> List[Dict]:
        from src.rag.advanced import _embedder
        vector = _embedder().encode([prefix + text], normalize_embeddings=True)[0].astype(np.float32)
        # metadata filters compare case-insensitively like the in-memory index: over-fetch, then filter here
        limit = top_k * 10 if metadata_filter else top_k
        points = self.client.query_points(self.collection, query=vector.tolist(), limit=limit, with_payload=True).points
        out = []
        for p in points:
            row = _payload_row(p.payload)
            if metadata_filter and any(str(row["metadata"].get(k, "")).lower() != str(v).lower() for k, v in metadata_filter.items()):
                continue
            out.append(row)
            if len(out) == top_k:
                break
        return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sync", "count"])
    args = parser.parse_args()
    if args.command == "sync":
        start = time.time()
        print(f"{sync_all()} passages copied to Qdrant collection '{COLLECTION}' in {time.time() - start:.0f} s")
    else:
        print(count())
