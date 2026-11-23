"""
Job queue in SQLite (data/jobs/jobs.sqlite3, WAL mode so the web app and a separate worker process can
share it).

    queued -> running -> done | failed

The web app `enqueue`s a job and returns its id at once; a worker (src/jobs/worker.py) `claim`s the oldest
queued job in one transaction, so two workers can never take the same job; the page polls the job until
it is done. Workers write a heartbeat; a job left "running" by a worker whose heartbeat stopped (a crash,
a restart) is marked failed rather than run twice, because re-running would spend Gemini quota again.
"""

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

JOB_DB = Path(os.getenv("JOB_DB", "data/jobs/jobs.sqlite3"))   # Docker: a named volume (SQLite WAL needs a real local file system)
STALE_SECONDS = 120


def _connect() -> sqlite3.Connection:
    JOB_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(JOB_DB), timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, user TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
        params TEXT NOT NULL, result TEXT, error TEXT, progress TEXT, worker TEXT,
        created REAL NOT NULL, started REAL, finished REAL)""")
    con.execute("CREATE TABLE IF NOT EXISTS workers (id TEXT PRIMARY KEY, beat REAL NOT NULL)")
    return con


@contextmanager
def _db():
    con = _connect()
    try:
        yield con
    finally:
        con.close()   # sqlite3's own "with" only commits; an open connection keeps the file locked on Windows


def _row(row: sqlite3.Row, with_params: bool = False) -> Dict:
    out = {k: row[k] for k in ("id", "user", "kind", "status", "error", "progress", "created", "started", "finished")}
    out["result"] = json.loads(row["result"]) if row["result"] else None
    if with_params:
        out["params"] = json.loads(row["params"])
    return out


def enqueue(user: str, kind: str, params: Dict) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _db() as con:
        con.execute("INSERT INTO jobs (id, user, kind, status, params, created) VALUES (?, ?, ?, 'queued', ?, ?)",
                    (job_id, user, kind, json.dumps(params, ensure_ascii=False), time.time()))
    return job_id


def get(job_id: str) -> Optional[Dict]:
    with _db() as con:
        row = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row(row) if row else None


def list_for(user: str, limit: int = 20) -> List[Dict]:
    with _db() as con:
        rows = con.execute("SELECT * FROM jobs WHERE user = ? ORDER BY created DESC LIMIT ?", (user, limit)).fetchall()
    return [{**_row(r), "result": None} for r in rows]


def claim(worker: str) -> Optional[Dict]:
    con = _connect()
    try:
        con.execute("BEGIN IMMEDIATE")   # one writer at a time: no two workers get the same job
        row = con.execute("SELECT * FROM jobs WHERE status = 'queued' ORDER BY created LIMIT 1").fetchone()
        if row is None:
            con.execute("COMMIT")
            return None
        con.execute("UPDATE jobs SET status = 'running', worker = ?, started = ? WHERE id = ?", (worker, time.time(), row["id"]))
        con.execute("COMMIT")
        return _row(row, with_params=True)
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def progress(job_id: str, text: str) -> None:
    with _db() as con:
        con.execute("UPDATE jobs SET progress = ? WHERE id = ?", (text[:200], job_id))


def finish(job_id: str, result: Optional[Dict] = None, error: Optional[str] = None) -> None:
    with _db() as con:
        con.execute("UPDATE jobs SET status = ?, result = ?, error = ?, finished = ? WHERE id = ?",
                    ("failed" if error else "done", json.dumps(result, ensure_ascii=False) if result is not None else None,
                     error, time.time(), job_id))


def heartbeat(worker: str) -> None:
    with _db() as con:
        con.execute("INSERT INTO workers (id, beat) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET beat = excluded.beat",
                    (worker, time.time()))


def last_heartbeat() -> Optional[float]:
    with _db() as con:
        row = con.execute("SELECT MAX(beat) AS beat FROM workers").fetchone()
    return row["beat"] if row and row["beat"] else None


def fail_stale() -> int:
    """Running jobs whose worker stopped beating -> failed (not re-run: that would spend quota twice)."""
    cutoff = time.time() - STALE_SECONDS
    with _db() as con:
        cur = con.execute("""UPDATE jobs SET status = 'failed', finished = ?, error = 'The worker stopped while running this job; please try again.'
                             WHERE status = 'running' AND (worker IS NULL OR worker NOT IN (SELECT id FROM workers WHERE beat >= ?))""",
                          (time.time(), cutoff))
        return cur.rowcount


def counts() -> Dict[str, int]:
    with _db() as con:
        rows = con.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
    return {r["status"]: r["n"] for r in rows}
