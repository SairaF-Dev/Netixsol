"""
Day 2 naive baseline index: fixed-size word windows, dense (vector) search only.

The windows run over the same extracted text as the section-level index (Task 3
output), with each legal unit's label kept in the text the way it appears in the
PDF ("Section 23. What considerations ... ", "para 5. ..."), but the window
boundaries ignore the units: a window can start in the middle of one section and
end in the next. Each chunk records which units it overlaps ("covers") so that
retrieval can be scored against the gold section / paragraph.

Urdu laws are already indexed as one chunk per OCR page (no legal structure), so
their rows and embeddings are copied from the main index instead of being
re-embedded (that took about 3 hours on CPU).

Build:  python -m src.rag.naive_index        (about 45 minutes on CPU; resumable)
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

from src.chunking.fixed_chunker import FixedSizeChunker
from src.indexing.vector_store import DenseVectorStore
from src.utils.file_utils import load_json
from src.utils.logger import setup_logger
from src.utils.schemas import LegalChunk

logger = setup_logger("naive_index")

STRUCTURED = Path("data/structured")
MAIN_INDEX = Path("data/indices/vstore_legal.sqlite3")
NAIVE_INDEX = Path("data/indices/vstore_naive_fixed.sqlite3")
CHUNK_WORDS, OVERLAP_WORDS = 200, 40
MIN_COVER_WORDS = 20
BATCH = 500


def document_units(doc: Dict, kind: str) -> Tuple[List[Tuple[str, str, int]], Dict]:
    """(label, text, page) per legal unit, plus document-level metadata."""
    if kind == "statute":
        units = [(s["section_number"],
                  f"{s['section_number']}. {s['title']}. " + " ".join([s["content"]] + s["subsections"]),
                  s["page_start"]) for c in doc["chapters"] for s in c["sections"]]
        if doc.get("preamble"):
            units.insert(0, ("Preamble", doc["preamble"], units[0][2] if units else 1))
        meta = {"act": doc["act_name"], "year": doc["year"]}
    elif kind == "judgment":
        units = [(f"para {p['number'] or 'opening'}", f"{p['number'] + '. ' if p['number'] else ''}{p['text']}", p["page"])
                 for p in doc["paragraphs"]]
        if not units and doc.get("holding"):
            units = [("holding", doc["holding"], doc.get("holding_page"))]
        meta = {"court": doc["court"], "case_number": doc["case_number"], "year": doc["year"],
                "matter_id": doc.get("matter_id") or ""}
    else:
        units = [(c["clause_id"], f"{c['clause_id']}. {c['clause_title']}. {c['text']}", c.get("page_number"))
                 for c in doc["clauses"]]
        meta = {"contract_title": doc["contract_title"], "contract_type": doc["contract_type"]}
    return units, meta


def fixed_chunks(doc: Dict, kind: str) -> List[LegalChunk]:
    units, meta = document_units(doc, kind)
    starts, words = [], []
    for _, text, _ in units:
        starts.append(len(words))
        words.extend(text.split())
    chunker = FixedSizeChunker(chunk_size=CHUNK_WORDS, chunk_overlap=OVERLAP_WORDS)
    chunks = chunker.chunk_text(" ".join(words), doc["document_id"], kind.title())
    for chunk in chunks:
        first, end = chunk.metadata["start_word"], chunk.metadata["end_word"]
        ends = starts[1:] + [len(words)]
        # A unit counts as covered if the window holds at least 20 of its words, or all of it
        # (a window that only clips the first words of a section does not "contain" it).
        covered = []
        for i, (start, stop) in enumerate(zip(starts, ends)):
            overlap = min(stop, end) - max(start, first)
            if overlap > 0 and (overlap >= MIN_COVER_WORDS or overlap == stop - start):
                covered.append(i)
        chunk.metadata = {**meta, "covers": [units[i][0] for i in covered],
                          "page": units[covered[0]][2] if covered else None,
                          "chunk_index": chunk.metadata["chunk_index"], "strategy": "fixed_size"}
    return chunks


def all_fixed_chunks() -> List[LegalChunk]:
    chunks: List[LegalChunk] = []
    for kind in ("statute", "judgment", "contract"):
        for path in sorted((STRUCTURED / kind).glob("*.json")):
            doc = load_json(path)
            if doc.get("language") == "Urdu":
                continue  # copied from the main index
            chunks.extend(fixed_chunks(doc, kind))
    return chunks


def build_naive_index(target: Path = NAIVE_INDEX) -> DenseVectorStore:
    store = DenseVectorStore(collection_name="naive_fixed", persist_directory=target)

    # 1. Urdu page chunks: copy rows and embeddings from the main index.
    with sqlite3.connect(str(MAIN_INDEX)) as source:
        rows = source.execute("SELECT * FROM legal_chunks WHERE document_id LIKE 'PKCODE_URDU_%'").fetchall()
    store.connection.executemany("INSERT OR IGNORE INTO legal_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    store.connection.commit()
    logger.info("Copied %d Urdu page chunks from %s", len(rows), MAIN_INDEX)

    # 2. English documents: fixed windows, embedded in batches (skips chunks already stored).
    chunks = all_fixed_chunks()
    done = {row[0] for row in store.connection.execute("SELECT chunk_id FROM legal_chunks")}
    todo = [c for c in chunks if c.chunk_id not in done]
    logger.info("%d fixed-size chunks, %d still to embed", len(chunks), len(todo))
    for start in range(0, len(todo), BATCH):
        store.add_chunks(todo[start:start + BATCH])
        logger.info("Embedded %d/%d", min(start + BATCH, len(todo)), len(todo))
    return store


def update_documents(document_ids: List[str], target: Path = NAIVE_INDEX) -> int:
    """Replace the fixed-size chunks of some English documents (after re-extraction)."""
    store = DenseVectorStore.load(target)
    removed = store.remove_documents(document_ids)
    chunks = [c for kind in ("statute", "judgment", "contract")
              for path in sorted((STRUCTURED / kind).glob("*.json")) if path.stem in document_ids
              for c in fixed_chunks(load_json(path), kind)]
    store.add_chunks(chunks)
    logger.info("Naive index: replaced %d chunks with %d for %s", removed, len(chunks), document_ids)
    return len(chunks)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        update_documents(sys.argv[1:])   # python -m src.rag.naive_index REAL_STAT_001
    else:
        build_naive_index()
