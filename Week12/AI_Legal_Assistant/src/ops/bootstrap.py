"""
One-shot start-up task for the Docker deployment (the `bootstrap` service; the API and worker start only
after it succeeds). Safe to run on every `docker compose up`: each step is skipped when already done.

1. Search data present? data/indices/ must hold the SQLite vector store and the BM25 index (built on the
   host by `python main.py --index`, or copied in): without them search cannot work, so it stops here.
2. Qdrant: if the collection does not hold every passage of the SQLite master copy, copy them all.
3. Neo4j: if the graph has no Case nodes, load data/graph/*.csv (python -m src.graph.load_neo4j).
4. Users and matters: if data/security/users.json is missing, create the demo users with random passwords
   (data/security/initial_passwords.txt).

Run:  python -m src.ops.bootstrap [--force-graph] [--force-vectors]
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from src.utils.logger import setup_logger

log = setup_logger("bootstrap")
INDEX = Path("data/indices/vstore_legal.sqlite3")
BM25 = Path("data/indices/bm25_legal.pkl")


def _retry(what: str, fn, attempts: int = 30, wait: float = 4):
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == attempts:
                raise
            log.info("%s not ready (%s); retrying in %.0f s", what, type(exc).__name__, wait)
            time.sleep(wait)


def check_index() -> int:
    if not INDEX.exists() or not BM25.exists():
        log.error("Search index missing: %s and %s are needed (python main.py --index on the host).", INDEX, BM25)
        sys.exit(1)
    with sqlite3.connect(f"file:{INDEX.as_posix()}?mode=ro", uri=True) as con:
        n = con.execute("SELECT COUNT(*) FROM legal_chunks").fetchone()[0]
    log.info("search index: %d passages", n)
    return n


def vectors(expected: int, force: bool) -> None:
    if os.getenv("VECTOR_BACKEND", "sqlite").lower() != "qdrant":
        log.info("VECTOR_BACKEND is not qdrant: nothing to copy")
        return
    from src.indexing.qdrant_store import count, get_client, sync_all
    client = _retry("Qdrant", get_client)
    have = _retry("Qdrant", lambda: count(client))
    if have == expected and not force:
        log.info("Qdrant already holds all %d passages", have)
        return
    log.info("copying %d passages to Qdrant (it holds %d)", expected, have)
    start = time.time()
    log.info("Qdrant: %d passages copied in %.0f s", sync_all(client), time.time() - start)


def graph(force: bool) -> None:
    if not os.getenv("NEO4J_URI"):
        log.info("NEO4J_URI not set: graph skipped")
        return
    from src.graph.neo4j_client import database, get_driver

    def cases() -> int:
        driver = get_driver()
        try:
            with driver.session(database=database()) as session:
                return session.run("MATCH (c:Case) RETURN count(c) AS n").single()["n"]
        finally:
            driver.close()
    n = _retry("Neo4j", cases)
    if n and not force:
        log.info("Neo4j already holds %d cases", n)
        return
    from src.graph.load_neo4j import load
    start = time.time()
    counts = load()
    log.info("Neo4j loaded in %.0f s: %s", time.time() - start, ", ".join(f"{k} {v}" for k, v in counts.items()))


def users() -> None:
    from src.security import access
    if access.USERS.exists() and access.MATTERS.exists():
        log.info("users and matters present")
        return
    access.seed()
    log.info("demo users created; passwords in data/security/initial_passwords.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-graph", action="store_true")
    parser.add_argument("--force-vectors", action="store_true")
    args = parser.parse_args()
    passages = check_index()
    vectors(passages, args.force_vectors)
    graph(args.force_graph)
    users()
    log.info("bootstrap complete")
