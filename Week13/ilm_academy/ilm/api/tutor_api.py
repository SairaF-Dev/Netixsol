"""The Socratic tutor behind the student app's tutor panel (Day 5).

Wraps ilm.tutor.tutor.Tutor (Day 3: grounded answers with source links, a 4-rung hint ladder,
leak checks that run code). Added here:
  - the student's mastery from their learning plan, so explanations match their level
  - a per-student limit (the LLM's free quota is shared by everyone)
  - a usage log for the teacher's safety page: metadata only (kind, rung, language, whether a
    leak was blocked). What the student typed is NOT stored: whether teachers may read tutor
    conversations needs the student's consent (open question in the UI plan).
  - when the model is unavailable (quota, network), an honest error, never a made-up answer
"""
from __future__ import annotations

import os
import threading
import time
from functools import partial

from ilm.api import service

TUTOR_MODEL = os.getenv("TUTOR_MODEL", "")          # empty: config.LLM_MODEL
PER_MINUTE, PER_DAY = 8, 80
_lock = threading.Lock()
_tutor = None
_calls: dict[str, list[float]] = {}


class TutorUnavailable(RuntimeError):
    pass


class TutorLimited(RuntimeError):
    pass


def _get():
    global _tutor
    with _lock:
        if _tutor is None:
            from ilm import llm
            from ilm.content.search import RewriteSearch
            from ilm.tutor.tutor import Tutor
            ask = partial(llm.ask, model=TUTOR_MODEL) if TUTOR_MODEL else llm.ask
            _tutor = Tutor(search=RewriteSearch(ask=ask), ask=ask)
    return _tutor


def check_limit(username: str):
    now = time.time()
    calls = [t for t in _calls.get(username, []) if now - t < 86400]
    if len([t for t in calls if now - t < 60]) >= PER_MINUTE:
        raise TutorLimited("You're asking faster than I can think. Wait a minute and ask again.")
    if len(calls) >= PER_DAY:
        raise TutorLimited("That's today's tutor limit. Your progress is saved; the tutor is back tomorrow.")
    calls.append(now)
    _calls[username] = calls


def mastery_for(learner: str | None) -> dict[str, float]:
    plan = service.learner_plan(learner) if learner else None
    if not plan:
        return {}
    return {s["concept"]: float(s["p_known"]) for s in plan["path"]}


def _log(username: str, kind: str, reply, exercise: str | None = None):
    with service._db_lock, service._db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS tutor_log (username TEXT, kind TEXT, level INTEGER, exercise TEXT, "
                    "language TEXT, grounded INTEGER, leak_blocked INTEGER, sources INTEGER, at REAL)")
        con.execute("INSERT INTO tutor_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (username, kind, reply.level, exercise or reply.exercise, reply.language, int(reply.grounded),
                     int(reply.leak_blocked), len(reply.sources), time.time()))


def _public(reply) -> dict:
    from ilm.tutor.tutor import LEVELS
    return {"text": reply.text, "sources": reply.sources, "grounded": reply.grounded, "language": reply.language,
            "level": reply.level, "level_name": LEVELS.get(reply.level) if reply.level else None,
            "exercise": reply.exercise, "leak_blocked": reply.leak_blocked}


def _run(fn):
    try:
        return fn()
    except (TutorLimited, ValueError, KeyError):
        raise
    except Exception as e:                    # quota, network, provider errors
        msg = str(e)
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            raise TutorUnavailable("The tutor has reached today's free usage limit. Try again later; "
                                   "your exercises still run and get feedback.") from e
        raise TutorUnavailable("The tutor couldn't answer just now. Try again in a moment.") from e


def ask(username: str, learner: str | None, message: str, language: str = "auto") -> dict:
    check_limit(username)
    reply = _run(lambda: _get().ask(message, mastery=mastery_for(learner), language=language))
    _log(username, "ask", reply)
    return _public(reply)


def hint(username: str, learner: str | None, exercise: str, code: str, message: str, level: int,
         language: str = "auto") -> dict:
    if exercise not in service.bank():
        raise KeyError(exercise)
    check_limit(username)
    reply = _run(lambda: _get().hint(exercise, student_code=code, message=message, level=level,
                                     mastery=mastery_for(learner), language=language))
    _log(username, "hint", reply, exercise)
    return _public(reply)


def warm_up():
    """Load the search index in the background so the first question is not slow."""
    threading.Thread(target=_get, daemon=True).start()
