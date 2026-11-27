"""What the API does, kept apart from HTTP so it can be tested directly.

Rule: nothing that leaves this module may contain a HIDDEN test (its call or its answer).
Exercise pages carry visible tests only, and submission results go through `public_result`,
a whitelist: the grader's raw per-test results stay on the server.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import yaml

from ilm import config

MAX_CODE_CHARS = 20_000
PER_MINUTE = 12                          # submissions per student per minute
_pool = ThreadPoolExecutor(max_workers=4)
_db_lock = threading.Lock()
_recent: dict[str, list[float]] = {}


# ------------------------------------------------------------------ course data ----
@lru_cache(maxsize=1)
def bank() -> dict:
    from ilm.questions.validate import load_bank
    return {q.id: q for q in load_bank()[0]}


@lru_cache(maxsize=1)
def concepts() -> dict:
    from ilm.graph.concept_graph import load_concepts
    return {c["id"]: c for c in load_concepts()}


@lru_cache(maxsize=1)
def lessons() -> dict:
    """lesson id -> {"title", "course"} from ilm/content/sources.yaml."""
    data = yaml.safe_load((config.PROJECT_ROOT / "ilm" / "content" / "sources.yaml").read_text(encoding="utf-8"))
    out = {}
    for course in data.get("courses", data.get("sources", [])):
        short = "CS50P" if "CS50" in course.get("title", "") else "MIT 6.0001"
        for l in course.get("lectures", course.get("lessons", [])):
            out[l["id"]] = {"title": l["title"], "course": short, "n": l.get("n")}
    return out


def lesson_label(lesson_id: str) -> str:
    l = lessons().get(lesson_id)
    return f"{l['course']} Lecture {l['n']}: {l['title']}" if l and l.get("n") is not None else (
        f"{l['course']}: {l['title']}" if l else lesson_id)


def exercise_summary(q) -> dict:
    c = concepts()[q.concepts[0]]
    taught = c.get("taught_in", [])
    return {"id": q.id, "function": q.function, "concept": c["name"], "concept_id": c["id"],
            "difficulty": q.difficulty, "lesson": lesson_label(taught[0]) if taught else None,
            "first_line": q.stem.split(". ")[0][:120]}


def list_exercises() -> list[dict]:
    order = {cid: i for i, cid in enumerate(concepts())}
    qs = [q for q in bank().values() if q.type == "code"]
    return [exercise_summary(q) for q in sorted(qs, key=lambda q: (order.get(q.concepts[0], 999), q.id))]


def exercise_detail(qid: str) -> dict | None:
    q = bank().get(qid)
    if q is None or q.type != "code":
        return None
    visible = [{"call": t.call, "expect": t.expect, "raises": t.raises} for t in q.tests if not t.hidden]
    starter = q.starter or f"def {q.function}():\n    ...\n"
    return {**exercise_summary(q), "stem": q.stem, "code": q.code, "starter": starter,
            "visible_tests": visible, "hidden_tests": hidden_count(q)}


def learner_plan(learner: str) -> dict | None:
    p = config.PROJECT_ROOT / "reports" / "learning_path" / f"{learner}.json"
    if not p.exists():
        return None
    plan = json.loads(p.read_text(encoding="utf-8"))
    names = {c["id"]: c["name"] for c in concepts().values()}
    return {"mastered": plan["mastered"], "strongest": plan["strongest"], "weakest": plan["weakest"],
            "concepts_total": len(names), "quick_checks": plan["quick_checks"],
            "quick_check_minutes": plan["quick_check_minutes"], "total_minutes": plan["total_minutes"],
            "minutes_per_day": plan["minutes_per_day"], "days": plan["days_at_that_pace"],
            "message_urdulish": plan.get("message"), "path": plan["path"]}


# ------------------------------------------------------------------ submissions ----
def _db() -> sqlite3.Connection:
    config.API_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.API_DB, check_same_thread=False)
    con.execute("""CREATE TABLE IF NOT EXISTS submissions (
        id TEXT PRIMARY KEY, username TEXT, exercise TEXT, code TEXT, status TEXT,
        result TEXT, created REAL, finished REAL)""")
    return con


def _save(sid: str, **cols):
    with _db_lock, _db() as con:
        sets = ", ".join(f"{k} = ?" for k in cols)
        con.execute(f"UPDATE submissions SET {sets} WHERE id = ?", (*cols.values(), sid))


def rate_limited(username: str) -> bool:
    now = time.time()
    recent = [t for t in _recent.get(username, []) if now - t < 60]
    _recent[username] = recent
    if len(recent) >= PER_MINUTE:
        return True
    recent.append(now)
    return False


def submit(username: str, qid: str, code: str) -> str:
    sid = uuid.uuid4().hex[:16]
    with _db_lock, _db() as con:
        con.execute("INSERT INTO submissions VALUES (?, ?, ?, ?, 'queued', NULL, ?, NULL)",
                    (sid, username, qid, code, time.time()))
    _pool.submit(_grade, sid, qid, code)
    return sid


_lessons_index = None
_side = ThreadPoolExecutor(max_workers=4)          # quality checks run beside the sandbox
_lessons_lock = threading.Lock()


def lesson_index():
    """Lesson search (loads the embedding model once). warm_up() calls it at API start-up."""
    global _lessons_index
    with _lessons_lock:
        if _lessons_index is None:
            from ilm.grading.feedback import Lessons
            _lessons_index = Lessons()
            _lessons_index.link("variables")                    # loads the model and the index
    return _lessons_index


def warm_up():
    threading.Thread(target=lesson_index, daemon=True).start()


def _grade(sid: str, qid: str, code: str):
    """Runs in a worker thread: sandbox -> grader -> feedback; stores only the public result."""
    from ilm.grading.feedback import feedback, forbidden_calls, quality
    from ilm.grading.grader import grade
    try:
        _save(sid, status="running")
        q = bank()[qid]
        qa_future = _side.submit(quality, code, forbidden_calls(q))     # static checks, in parallel
        graded = grade({"id": sid, "code": code}, q, test_set="edge")
        fb = feedback(graded, q, code, lesson_index(), qa=qa_future.result())
        _save(sid, status="done", result=json.dumps(public_result(fb, graded)), finished=time.time())
    except Exception as e:                    # never leave a submission spinning
        _save(sid, status="error", result=json.dumps({"message": f"Grading failed: {type(e).__name__}"}),
              finished=time.time())


def public_result(fb: dict, graded: dict) -> dict:
    """Whitelist of what a student may see. Hidden tests: count and kind only."""
    from ilm.grading.feedback import rule_hint
    t = fb["tests"]
    return {"mark": fb["mark"], "passed": t["passed"], "total": t["total"],
            "visible_failed": [{"call": v["call"], "expected": v["expected"], "got": v["got"], "why": v["why"]}
                               for v in t["visible_failed"]],
            "hidden_failed": t["hidden_failed"],
            "hidden_failed_how": [{"how": h["how"], "count": h["count"]} for h in t["hidden_failed_how"]],
            "rules": [rule_hint(r) for r in fb["rules_broken"]],
            "slow": bool(fb["slow"]),
            "quality": [i["hint"] for i in fb["quality"]["issues"][:3]],
            "next_step": fb["one_improvement"],
            "lesson": fb["lesson"],
            "sandbox": "timed out" if graded["status"].startswith("timeout") else (
                "flagged for review" if graded["status"] == "tampered" else "ok")}


def get_submission(sid: str, username: str) -> dict | None:
    with _db_lock, _db() as con:
        row = con.execute("SELECT id, exercise, status, result, created, finished, code FROM submissions "
                          "WHERE id = ? AND username = ?", (sid, username)).fetchone()
    if row is None:
        return None
    return {"id": row[0], "exercise": row[1], "status": row[2],
            "result": json.loads(row[3]) if row[3] else None, "created": row[4],
            "seconds": round(row[5] - row[4], 1) if row[5] else None, "code": row[6]}


def recent_submissions(username: str, qid: str, n: int = 5) -> list[dict]:
    with _db_lock, _db() as con:
        rows = con.execute("SELECT id, status, result, created FROM submissions WHERE username = ? AND exercise = ? "
                           "ORDER BY created DESC LIMIT ?", (username, qid, n)).fetchall()
    out = []
    for sid, status, result, created in rows:
        r = json.loads(result) if result else {}
        out.append({"id": sid, "status": status, "created": created, "mark": r.get("mark"),
                    "passed": r.get("passed"), "total": r.get("total")})
    return out


def hidden_count(q) -> int:
    """Hidden tests the grader really runs: the bank's hidden ones + the edge cases (grader.EDGE)."""
    from ilm.grading.grader import EDGE
    return sum(t.hidden for t in q.tests) + len(EDGE.get(q.id, []))
