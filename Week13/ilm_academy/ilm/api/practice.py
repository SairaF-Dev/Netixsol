"""Question practice: MCQ and short answers for one concept (Day 5).

Rules:
  - the answer key never reaches the browser before the student answers: questions go out
    with their options only; grading happens here
  - after an answer, the student sees whether it was right, the correct answer, and for a
    wrong MCQ option the misconception behind it (from the bank's `misconceptions` field); for
    "what does this print" questions, the program's real output
  - mastery: BKT (models/bkt_concept_params.csv) starting from the plan's P(known) for the
    concept and updated with every answer given in the app, with the same mastery rule as
    Day 2 (P(known) >= 0.95 and 3 right in a row)
  - order: easiest first, skipping questions already answered correctly; explain-type short
    questions (graded by a rubric, Day 4 Task 4) are not offered here yet
"""
from __future__ import annotations

import time
from functools import lru_cache

import pandas as pd

from ilm import config
from ilm.api import service


@lru_cache(maxsize=1)
def bkt_params() -> pd.DataFrame:
    return pd.read_csv(config.MODELS_DIR / "bkt_concept_params.csv", index_col="concept")


def _db():
    con = service._db()
    con.execute("CREATE TABLE IF NOT EXISTS answers (username TEXT, question TEXT, concept TEXT, correct INTEGER, "
                "given TEXT, at REAL)")
    return con


def practicable(q) -> bool:
    return q.type == "mcq" or (q.type == "short" and bool(q.accept))


def questions_for(concept: str) -> list:
    qs = [q for q in service.bank().values() if q.concepts[0] == concept and practicable(q)]
    return sorted(qs, key=lambda q: (q.difficulty, q.id))


def _history(username: str, concept: str | None = None) -> list[tuple]:
    with service._db_lock, _db() as con:
        sql = "SELECT question, concept, correct, at FROM answers WHERE username = ?"
        args: tuple = (username,)
        if concept:
            sql += " AND concept = ?"
            args += (concept,)
        return con.execute(sql + " ORDER BY at", args).fetchall()


def mastery(username: str, learner: str | None, concept: str) -> dict:
    """P(known) for one concept: the plan's estimate, then every app answer through BKT."""
    from ilm.tracing.mastery import MasteryTracker
    params = bkt_params()
    if concept not in params.index:
        return {"p_known": None, "mastered": False, "answers": 0}
    t = MasteryTracker(params)
    plan = service.learner_plan(learner) if learner else None
    start = next((s["p_known"] for s in (plan or {}).get("path", []) if s["concept"] == concept), None)
    if start is not None:
        t.known[concept] = float(start)
    hist = _history(username, concept)
    for _, _, ok, _ in hist:
        t.update(concept, bool(ok))
    return {"p_known": round(t.p_known(concept), 3), "mastered": t.mastered(concept), "answers": len(hist)}


def public_question(q) -> dict:
    """What the browser may see before answering: no answer index, accept list or misconceptions."""
    out = {"id": q.id, "type": q.type, "stem": q.stem, "code": q.code, "difficulty": q.difficulty}
    if q.type == "mcq":
        out["options"] = list(q.options)
    return out


def next_question(username: str, learner: str | None, concept: str) -> dict:
    qs = questions_for(concept)
    hist = _history(username, concept)
    right = {qid for qid, _, ok, _ in hist if ok}
    last_try = {qid: at for qid, _, _, at in hist}          # latest attempt per question
    # not tried yet first (easiest first), then missed ones, the longest-ago miss first:
    # a question answered wrongly comes back only after the others, never straight away
    todo = sorted((q for q in qs if q.id not in right), key=lambda q: (q.id in last_try, last_try.get(q.id, 0)))
    c = service.concepts().get(concept)
    base = {"concept": concept, "concept_name": c["name"] if c else concept, "total": len(qs),
            "done": len(qs) - len(todo), "mastery": mastery(username, learner, concept),
            "has_code_exercise": any(q.type == "code" and q.concepts[0] == concept for q in service.bank().values())}
    return {**base, "question": public_question(todo[0]) if todo else None}


def answer(username: str, learner: str | None, qid: str, choice: int | None, text: str | None) -> dict:
    from ilm.questions.runner import run_snippet
    from ilm.questions.validate import normalise_answer, normalise_output
    q = service.bank().get(qid)
    if q is None or not practicable(q):
        raise KeyError(qid)
    concept = q.concepts[0]
    before = mastery(username, learner, concept)
    misconception = None
    if q.type == "mcq":
        if choice is None or not 0 <= choice < len(q.options):
            raise ValueError("Choose one of the options.")
        correct = choice == q.answer
        given = q.options[choice]
        right_answer = q.options[q.answer]
        if not correct:
            misconception = q.misconceptions.get(choice)
    else:
        if not (text or "").strip():
            raise ValueError("Type an answer first.")
        given = text.strip()[:300]
        if q.check_output:            # compare exactly with what the program really prints
            correct = normalise_output(given) in {normalise_output(a) for a in q.accept} or \
                normalise_answer(given) in {normalise_answer(a) for a in q.accept}
        else:
            correct = normalise_answer(given) in {normalise_answer(a) for a in q.accept}
        right_answer = q.accept[0]
    with service._db_lock, _db() as con:
        con.execute("INSERT INTO answers VALUES (?, ?, ?, ?, ?, ?)", (username, qid, concept, int(correct), given, time.time()))
    output = None
    if getattr(q, "check_output", False) and q.code:
        output = normalise_output(run_snippet(q.code))     # our own bank code, run by the validator's runner
    return {"correct": correct, "right_answer": right_answer, "misconception": misconception,
            "output": output, "before": before, "after": mastery(username, learner, concept)}
