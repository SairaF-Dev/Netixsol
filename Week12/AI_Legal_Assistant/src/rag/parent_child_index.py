"""
Parent-child index for the Day 2 comparison (Task 3, last step).

Children (~80-word sentence windows of a legal unit) are embedded and BM25-indexed
for precise matching; each child points to its parent (the whole section /
paragraph group / clause), which is what the answer model reads. Children carry
the parent's metadata (act, section, court, page ...), so gold matching works on
them unchanged. Urdu law pages have no finer structure: each page is its own
parent and child, copied with its embedding from the main index.

Build:  python -m src.rag.parent_child_index      (about an hour on CPU; resumable)
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from src.chunking.parent_child_chunker import ParentChildChunker
from src.indexing.bm25_index import LegalBM25Index
from src.indexing.vector_store import DenseVectorStore
from src.utils.file_utils import load_json
from src.utils.logger import setup_logger
from src.utils.schemas import ContractDocument, JudgmentDocument, LegalChunk, StatuteDocument

logger = setup_logger("parent_child_index")

STRUCTURED = Path("data/structured")
INDEX_DIR = Path("data/indices")
MAIN_INDEX = INDEX_DIR / "vstore_legal.sqlite3"
CHILD_VECTORS = INDEX_DIR / "vstore_children.sqlite3"
CHILD_BM25 = INDEX_DIR / "bm25_children.pkl"
PARENTS = INDEX_DIR / "parents.jsonl"
BATCH = 500
MODELS = {"statute": StatuteDocument, "judgment": JudgmentDocument, "contract": ContractDocument}


def english_parents_and_children():
    chunker = ParentChildChunker()
    parents: List[LegalChunk] = []
    children: List[LegalChunk] = []
    for kind, model in MODELS.items():
        for path in sorted((STRUCTURED / kind).glob("*.json")):
            doc = model.model_validate(load_json(path))
            if getattr(doc, "language", "English") == "Urdu":
                continue
            p, c = getattr(chunker, f"chunk_{kind}")(doc)
            parents.extend(p)
            children.extend(c)
    return parents, children


def build(target_vectors: Path = CHILD_VECTORS) -> None:
    parents, children = english_parents_and_children()

    # Urdu pages: parent = child = page chunk, embedding copied from the main index.
    with sqlite3.connect(str(MAIN_INDEX)) as source:
        urdu_rows = source.execute("SELECT * FROM legal_chunks WHERE document_id LIKE 'PKCODE_URDU_%'").fetchall()
    urdu_chunks = [LegalChunk(chunk_id=r[0], document_id=r[1], document_type=r[2], strategy=r[3], content=r[4],
                              token_count=r[5], metadata={**json.loads(r[6]), "parent_id": r[0]}) for r in urdu_rows]

    with PARENTS.open("w", encoding="utf-8") as handle:
        for chunk in parents + urdu_chunks:
            handle.write(json.dumps({"chunk_id": chunk.chunk_id, "document_id": chunk.document_id,
                                     "document_type": chunk.document_type, "content": chunk.content,
                                     "metadata": chunk.metadata}, ensure_ascii=False) + "\n")

    bm25 = LegalBM25Index()
    bm25.add_chunks(children + urdu_chunks)
    bm25.save(CHILD_BM25)

    store = DenseVectorStore(collection_name="children", persist_directory=target_vectors)
    store.connection.executemany(
        "INSERT OR IGNORE INTO legal_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(c.chunk_id, c.document_id, c.document_type, c.strategy, c.content, c.token_count,
          json.dumps(c.metadata, ensure_ascii=False), row[7]) for c, row in zip(urdu_chunks, urdu_rows)])
    store.connection.commit()
    done = {row[0] for row in store.connection.execute("SELECT chunk_id FROM legal_chunks")}
    todo = [c for c in children if c.chunk_id not in done]
    logger.info("%d parents, %d children (+%d Urdu pages); %d children still to embed",
                len(parents), len(children), len(urdu_chunks), len(todo))
    for start in range(0, len(todo), BATCH):
        store.add_chunks(todo[start:start + BATCH])
        logger.info("Embedded %d/%d", min(start + BATCH, len(todo)), len(todo))


def load_parents() -> Dict[str, Dict]:
    with PARENTS.open(encoding="utf-8") as handle:
        return {row["chunk_id"]: row for row in map(json.loads, handle)}


if __name__ == "__main__":
    build()
