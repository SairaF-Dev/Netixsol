"""Learning path: time estimate, path order, and an honest message, on a tiny course a -> b -> c."""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from ilm.adaptive.path import (MAX_ANSWERS, MINUTES_PER_DAY, build_path, expected_answers,
                               speed_factor, urdulish_message)
from ilm.tracing.mastery import STREAK

COURSE = SimpleNamespace(order=["a", "b", "c"], prereqs={"a": [], "b": ["a"], "c": ["b"]})
PARAMS = pd.DataFrame({"prior": 0.2, "learns": 0.3, "guesses": 0.2, "slips": 0.1}, index=COURSE.order)
NAMES = {"a": "Loops", "b": "Functions", "c": "Recursion"}
Q_SEC = pd.Series({"a-01": 60.0, "b-01": 60.0, "c-01": 60.0})
C_SEC = pd.Series({"a": 60.0, "b": 60.0, "c": 60.0})


def history(rows, seconds=60.0):
    return pd.DataFrame([{"question_id": f"{c}-01", "concept": c, "correct": ok, "response_time_sec": seconds}
                         for c, ok in rows], columns=["question_id", "concept", "correct", "response_time_sec"])


def plan_for(h):
    return build_path(h, COURSE, PARAMS, NAMES, {}, Q_SEC, C_SEC)


def test_a_sure_thing_takes_exactly_the_streak():
    row = pd.Series({"prior": 1.0, "learns": 0.0, "guesses": 0.0, "slips": 0.0})
    assert expected_answers(row, p_known=1.0) == STREAK


def test_nothing_to_learn_from_hits_the_cap():
    row = pd.Series({"prior": 0.0, "learns": 0.0, "guesses": 0.0, "slips": 0.0})
    assert expected_answers(row, p_known=0.0) == MAX_ANSWERS


def test_knowing_more_already_means_fewer_answers():
    row = PARAMS.loc["a"]
    assert expected_answers(row, 0.9) < expected_answers(row, 0.5) < expected_answers(row, 0.1)


def test_speed_factor():
    assert speed_factor(history([("a", 1)] * 10, seconds=120.0), Q_SEC) == pytest.approx(2.0)
    assert speed_factor(history([("a", 1)] * 2, seconds=120.0), Q_SEC) == 1.0   # too few answers


def test_mastered_concepts_leave_the_path_and_prerequisites_show():
    p = plan_for(history([("a", 1)] * 6))
    assert p["mastered"] == ["Loops"]
    assert [s["concept"] for s in p["path"]] == ["b", "c"]
    assert p["path"][0]["status"] == "ready" and p["path"][1]["status"] == "after Functions"


def test_likely_known_is_a_quick_check_not_a_lesson():
    p = plan_for(history([("a", 1), ("a", 1)]))           # high P(known), no 3-streak yet
    first = p["path"][0]
    assert first["concept"] == "a" and first["kind"] == "quick check"
    assert p["path"][1]["kind"] == "learn"


def test_slower_student_gets_a_longer_estimate():
    fast = plan_for(history([("a", 1)] * 6, seconds=30.0))
    slow = plan_for(history([("a", 1)] * 6, seconds=120.0))
    assert slow["total_minutes"] > 3 * fast["total_minutes"]


def test_message_numbers_come_from_the_plan():
    h = history([("a", 1)] * 6 + [("b", 0)] * 3)
    p = plan_for(h)
    msg = urdulish_message(p, h, name="Ali")
    assert msg.startswith("Ali, ")
    assert f"{p['days_at_that_pace']} din" in msg and f"{MINUTES_PER_DAY} minute" in msg
    assert "Loops" in msg                                  # the strength is named
    assert "Functions" in msg                              # and so is the weak spot / next step


def test_new_student_gets_a_welcome_and_done_student_a_congrats():
    empty = history([])
    assert "khush aamdeed" in urdulish_message(plan_for(empty), empty)
    done = {"path": [], "mastered": ["Loops"]}
    assert "master ho gaye" in urdulish_message(done, empty)
