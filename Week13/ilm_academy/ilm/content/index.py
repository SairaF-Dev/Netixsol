"""Vector index of course content (Chroma + sentence-transformers).

build_index(): chunk every lesson, embed, store in Chroma with metadata.
search():      embed a student question, return the closest chunks with their links.

Run:  python -m ilm.content.index                 (rebuild the index)
      python -m ilm.content.index --query "why does my function call itself"
"""
from __future__ import annotations

import argparse
import json
import time
from functools import lru_cache

from ilm import config
from ilm.content.chunking import Chunk, course_vocabulary, lesson_chunks
from ilm.content.download import all_lessons

COLLECTION = "course_content"
# bge models were trained with this instruction on QUERIES only (not on passages).
# Omitting it silently lowers retrieval quality.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=2)
def embedder(name: str | None = None):
    """Load once per process: loading takes seconds, encoding takes milliseconds."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name or config.EMBEDDING_MODEL)


def query_text(question: str, model_name: str | None = None) -> str:
    name = model_name or config.EMBEDDING_MODEL
    return BGE_QUERY_PREFIX + question if "bge" in name.lower() else question


def collect_chunks() -> tuple[list[Chunk], dict]:
    chunks, report = [], {}
    vocab = course_vocabulary()  # built once, shared by every lesson's slide cleaning
    for lesson in all_lessons():
        parts = lesson_chunks(lesson, vocab)
        report[lesson["id"]] = {src: len(c) for src, c in parts.items()}
        for c in parts.values():
            chunks.extend(c)
    return chunks, report


def client():
    import chromadb
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def build_index(model_name: str | None = None, collection: str = COLLECTION) -> dict:
    """Rebuild from scratch: delete + recreate, so re-running never leaves stale chunks."""
    chunks, report = collect_chunks()
    model = embedder(model_name)
    t0 = time.time()
    vectors = model.encode([c.text for c in chunks], batch_size=32, normalize_embeddings=True,
                           show_progress_bar=False)
    db = client()
    if collection in [c.name for c in db.list_collections()]:
        db.delete_collection(collection)
    col = db.create_collection(collection, metadata={"hnsw:space": "cosine",
                                                     "embedding_model": model_name or config.EMBEDDING_MODEL})
    for i in range(0, len(chunks), 500):  # Chroma has a max batch size
        batch = chunks[i:i + 500]
        col.add(ids=[c.id for c in batch], documents=[c.text for c in batch],
                metadatas=[c.metadata() for c in batch], embeddings=vectors[i:i + 500].tolist())
    missing = [lid for lid, r in report.items() if r["transcript"] == 0]
    summary = {"collection": collection, "chunks": len(chunks),
               "by_source": {s: sum(r[s] for r in report.values()) for s in ("transcript", "notes", "slides")},
               "lessons_missing_transcript": missing, "embed_seconds": round(time.time() - t0, 1),
               "per_lesson": report}
    out = config.PROCESSED_DIR / "index_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def search(question: str, k: int = 5, where: dict | None = None,
           model_name: str | None = None, collection: str = COLLECTION) -> list[dict]:
    """Top-k chunks for a question. `where` filters metadata, e.g. {"lesson_id": "cs50p-l5"}."""
    vec = embedder(model_name).encode([query_text(question, model_name)], normalize_embeddings=True)
    res = client().get_collection(collection).query(
        query_embeddings=vec.tolist(), n_results=k, where=where)
    return [{"id": i, "score": round(1 - d, 4), "text": doc, **meta}  # cosine distance -> similarity
            for i, d, doc, meta in zip(res["ids"][0], res["distances"][0],
                                       res["documents"][0], res["metadatas"][0])]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--query", help="search instead of rebuilding")
    p.add_argument("-k", type=int, default=5)
    a = p.parse_args()
    if a.query:
        for r in search(a.query, a.k):
            print(f"{r['score']:.3f}  {r['title']}\n       {r['url']}\n       {r['text'][:140]}...")
        return
    s = build_index()
    print(json.dumps({k: v for k, v in s.items() if k != "per_lesson"}, indent=1))


if __name__ == "__main__":
    main()
