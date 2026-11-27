"""The teacher's review queue: everything that needs a human, in one place (Day 5).

Three kinds of item, in priority order:
  similarity   "Possible copying - needs teacher review": the ranked queue from Day 4 Task 5
               (top 5 pairs per exercise), both submissions side by side with matching lines.
               The benchmark's ground-truth labels are NEVER sent: the teacher decides from the code.
  tampering    live submissions whose output imitated a result line (sandbox flag)
  low_mark     marks under 4 from the 50 graded submissions: tests give 0 to code with a good idea
               and one slip, so a human checks (Day 4 Task 2)
Decisions are stored; nothing here changes a mark or punishes anyone automatically.
"""
from __future__ import annotations

import json
import time
from functools import lru_cache

from ilm import config
from ilm.api import service

DECISIONS = {
    "similarity": ["Not copying", "Talk to both students", "Escalate"],
    "tampering": ["Harmless output", "Talk to the student", "Escalate"],
    "low_mark": ["Keep the mark", "Raise the mark", "Talk to the student"],
}
LOW_MARK = 4


def _decisions() -> dict[str, dict]:
    with service._db_lock, service._db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS review_decisions (item TEXT PRIMARY KEY, decision TEXT, "
                    "teacher TEXT, note TEXT, at REAL)")
        rows = con.execute("SELECT item, decision, teacher, note, at FROM review_decisions").fetchall()
    return {r[0]: {"decision": r[1], "teacher": r[2], "note": r[3], "at": r[4]} for r in rows}


def decide(item_id: str, decision: str, teacher: str, note: str = "") -> dict:
    kind = item_id.split(":", 1)[0]
    if decision not in DECISIONS.get(kind, []):
        raise ValueError("Unknown decision for this item.")
    _decisions()                                        # makes sure the table exists
    with service._db_lock, service._db() as con:
        con.execute("INSERT OR REPLACE INTO review_decisions VALUES (?, ?, ?, ?, ?)",
                    (item_id, decision, teacher, note[:500], time.time()))
    return {"item": item_id, "decision": decision}


@lru_cache(maxsize=1)
def _similarity_source() -> tuple[list[dict], dict]:
    rep = json.loads((config.PROJECT_ROOT / "reports" / "plagiarism" / "report.json").read_text(encoding="utf-8"))
    subs = json.loads((config.PROCESSED_DIR / "plagiarism" / "submissions.json").read_text(encoding="utf-8"))
    return rep["review_queue"].get("pairs", []), {s["submission_id"]: s["code"] for s in subs}


@lru_cache(maxsize=1)
def _graded_source() -> tuple[list[dict], dict]:
    rep = json.loads((config.PROJECT_ROOT / "reports" / "grading" / "report.json").read_text(encoding="utf-8"))
    subs = json.loads((config.DATA_DIR / "grading" / "submissions.json").read_text(encoding="utf-8"))
    return rep["grades"], {s["id"]: s["code"] for s in subs}


def _student(sub_id: str) -> str:
    """'iterating_lists-03__s04' -> 'Submission s04' (benchmark ids, no invented names)."""
    return "Submission " + sub_id.split("__")[-1]


def _items() -> list[dict]:
    items = []
    pairs, _ = _similarity_source()
    for p in pairs:
        items.append({"id": f"similarity:{p['pair_id']}", "kind": "similarity", "exercise": p["exercise_id"],
                      "title": f"{_student(p['sub_a'])} and {_student(p['sub_b'])}",
                      "why": f"Code similarity {p['combined']:.2f} (one of the 5 most similar pairs on this exercise)",
                      "score": p["combined"]})
    with service._db_lock, service._db() as con:
        rows = con.execute("SELECT id, username, exercise, result FROM submissions WHERE status = 'done'").fetchall()
    for sid, user, ex, result in rows:
        if result and json.loads(result).get("sandbox") == "flagged for review":
            items.append({"id": f"tampering:{sid}", "kind": "tampering", "exercise": ex,
                          "title": f"{user.capitalize()}'s run",
                          "why": "The output contained lines that imitate a test result", "score": 1.0})
    grades, _ = _graded_source()
    for g in grades:
        if g["mark"] < LOW_MARK:
            items.append({"id": f"low_mark:{g['id']}", "kind": "low_mark", "exercise": g["exercise"],
                          "title": f"Submission {g['id']}", "score": 1 - g["mark"] / 10,
                          "why": f"Mark {g['mark']}/10 from tests ({g['passed']} of {g['tests']} passed)"
                                 + (f"; task rule: {', '.join(g['rules_broken'])}" if g["rules_broken"] else "")})
    order = {"similarity": 0, "tampering": 1, "low_mark": 2}
    return sorted(items, key=lambda i: (order[i["kind"]], -i["score"]))


def queue() -> dict:
    decided = _decisions()
    items = [{**i, "decision": decided.get(i["id"], {}).get("decision"), "options": DECISIONS[i["kind"]]}
             for i in _items()]
    return {"items": items, "open": sum(i["decision"] is None for i in items),
            "counts": {k: sum(i["kind"] == k for i in items) for k in DECISIONS}}


def detail(item_id: str) -> dict | None:
    kind, key = item_id.split(":", 1) if ":" in item_id else ("", "")
    base = next((i for i in _items() if i["id"] == item_id), None)
    if base is None:
        return None
    q = service.bank().get(base["exercise"])
    out = {**base, "stem": q.stem if q else "", "options": DECISIONS[kind],
           "decision": _decisions().get(item_id)}
    if kind == "similarity":
        from ilm.grading.plagiarism import matching_lines
        pair = next(p for p in _similarity_source()[0] if p["pair_id"] == key)
        codes = _similarity_source()[1]
        a, b = codes[pair["sub_a"]], codes[pair["sub_b"]]
        hl_a, hl_b = matching_lines(a, b)
        out["sides"] = [{"label": _student(pair["sub_a"]), "code": a, "matching": sorted(hl_a)},
                        {"label": _student(pair["sub_b"]), "code": b, "matching": sorted(hl_b)}]
        out["scores"] = {"combined": pair["combined"], "tokens": pair["token"], "structure": pair["ast"],
                         "meaning": pair["embedding"]}
    elif kind == "low_mark":
        grades, codes = _graded_source()
        g = next(x for x in grades if x["id"] == key)
        out["code"] = codes[key]
        out["grading"] = {"mark": g["mark"], "passed": g["passed"], "tests": g["tests"],
                          "rules_broken": g["rules_broken"], "status": g["status"],
                          "failed": [f"{t['call']} -> {t['got']}" for t in g.get("test_results", []) if not t["passed"]][:6]}
    elif kind == "tampering":
        with service._db_lock, service._db() as con:
            row = con.execute("SELECT code FROM submissions WHERE id = ?", (key,)).fetchone()
        out["code"] = row[0] if row else ""
    return out
