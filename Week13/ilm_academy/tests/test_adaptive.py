"""Adaptive engine: one test per idea, on a tiny course a -> b -> c."""
from __future__ import annotations

import pandas as pd

from ilm.adaptive.engine import REVIEW_DAYS, ZPD, AdaptiveEngine

ORDER = ["a", "b", "c"]
PREREQS = {"a": [], "b": ["a"], "c": ["b"]}
QUESTIONS = {"a": ["a-01", "a-02"], "b": ["b-01", "b-02"], "c": ["c-01", "c-02"]}
PARAMS = pd.DataFrame({"prior": 0.1, "learns": 0.3, "guesses": 0.2, "slips": 0.1}, index=ORDER)


def engine(**kw):
    return AdaptiveEngine(ORDER, PREREQS, QUESTIONS, PARAMS, **kw)


def master(e, sid, concept, day=0):
    while not e.mastered(sid, concept):
        q = QUESTIONS[concept][0]
        e.next_question(sid, day)
        e.observe(sid, q, True, day)


def test_locked_concepts_are_never_asked_before_their_prerequisites():
    e = engine()
    asked = {e.concept_of[e.next_question("s", 0)] for _ in range(20)}
    assert asked == {"a"}                     # b needs a, c needs b
    master(e, "s", "a")
    assert e.frontier("s") == ["b"]


def test_without_prerequisites_everything_is_open():
    assert engine(use_prereqs=False).frontier("s") == ["a", "b", "c"]


def test_zpd_picks_the_question_closest_to_70_percent():
    item = pd.DataFrame({"a": [1.0, 1.0], "b": [-3.0, 0.5]}, index=["a-01", "a-02"])
    e = engine(item_params=item)
    p = {q: e.predicted("s", q) for q in QUESTIONS["a"]}
    target = sum(ZPD) / 2
    assert e.next_question("s") == min(p, key=lambda q: abs(p[q] - target))
    assert p["a-01"] > p["a-02"]              # the lower-difficulty question is easier


def test_flagged_bad_questions_are_skipped():
    e = engine(bad={"a-01"})
    assert {e.next_question("s", 0) for _ in range(5)} == {"a-02"}


def test_bandit_learns_which_concept_produces_learning():
    e = engine(use_prereqs=False, use_zpd=False)
    for _ in range(200):          # practising a never helps, b always helps
        e.wins["b"] += 1
        e.losses["a"] += 1
    picks = [e.concept_of[e.next_question(f"s{i}", 0)] for i in range(100)]
    assert picks.count("b") > 90


def test_mastered_concept_comes_back_for_review_on_schedule():
    e = engine()
    master(e, "s", "a", day=0)
    assert "a" not in e.due_reviews("s", REVIEW_DAYS[0] - 1)
    assert e.due_reviews("s", REVIEW_DAYS[0]) == ["a"]
    q = e.next_question("s", REVIEW_DAYS[0])
    e.observe("s", q, True, REVIEW_DAYS[0])          # passed: the next gap is longer
    assert e.due_reviews("s", REVIEW_DAYS[0] + REVIEW_DAYS[1] - 1) == []
    assert e.due_reviews("s", REVIEW_DAYS[0] + REVIEW_DAYS[1]) == ["a"]


def test_engine_says_done_when_everything_is_mastered():
    e = engine(use_reviews=False)
    for c in ORDER:
        master(e, "s", c)
    assert e.next_question("s", 10) is None
