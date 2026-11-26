"""Learner data: ASSISTments cleaning, the student-level split, and the simulator."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ilm.learners import simulator as sim
from ilm.learners.assistments import clean
from ilm.learners.split import student_split


# ------------------------------------------------------------ ASSISTments ----
def _raw(rows):
    cols = ["order_id", "user_id", "problem_id", "skill_id", "skill_name", "correct",
            "attempt_count", "hint_count", "ms_first_response", "original", "assignment_id"]
    return pd.DataFrame(rows, columns=cols)


def test_cleaning_keeps_one_row_per_real_answer_in_time_order():
    raw = _raw([
        # order, user, problem, skill, name, correct, attempts, hints, ms, original, assignment
        (30, 1, 7, 5.0, "Area", 1, 1, 0, 9000, 1, 1),
        (30, 1, 7, 5.0, "Area", 1, 1, 0, 9000, 1, 1),         # documented duplicate bug
        (10, 1, 8, 5.0, "Area", 0, 2, 1, 4000, 1, 1),         # earlier answer, listed later
        (20, 1, 9, 5.0, "Area", 1, 1, 0, -5, 0, 1),           # broken time, scaffolding
        (20, 1, 9, 2.0, "Angles", 1, 1, 0, -5, 0, 1),         # same answer, 2nd skill
        (40, 2, 7, np.nan, None, 1, 1, 0, 3000, 1, 1),        # no skill
    ])
    df, rep = clean(raw)
    assert len(df) == 3 and df["order_id"].tolist() == [10, 20, 30]   # time order
    assert df["seq"].tolist() == [1, 2, 3]
    multi = df[df["order_id"] == 20].iloc[0]
    assert multi["skill"] == "2_5" and multi["n_skills"] == 2 and multi["skill_name"] == "Angles + Area"
    assert np.isnan(multi["response_time_sec"]) and multi["is_scaffolding"] == 1
    assert rep["dropped_no_skill"] == 1 and rep["dropped_repeated_same_skill"] == 1
    assert rep["merged_multi_skill_copies"] == 1
    # every raw row is accounted for
    assert rep["raw_rows"] - rep["dropped_no_skill"] - rep["dropped_repeated_same_skill"] \
        - rep["merged_multi_skill_copies"] == rep["rows"]


# ------------------------------------------------------------------ split ----
def test_student_split_never_shares_a_student_and_is_repeatable():
    df = pd.DataFrame({"user_id": np.repeat(np.arange(100), 5), "correct": 1})
    train, test = student_split(df, test_frac=0.2, seed=1)
    assert not set(train["user_id"]) & set(test["user_id"])
    assert test["user_id"].nunique() == 20 and len(train) + len(test) == len(df)
    shuffled = df.sample(frac=1, random_state=0)
    assert set(student_split(shuffled, seed=1)[1]["user_id"]) == set(test["user_id"])


# --------------------------------------------------------------- simulator ----
@pytest.fixture(scope="module")
def course():
    return sim.Course.load()


@pytest.fixture(scope="module")
def run(course):
    return sim.simulate(300, seed=7, drop_base=-1.5, course=course)


def test_simulation_is_reproducible(course, run):
    log2, people2 = sim.simulate(300, seed=7, drop_base=-1.5, course=course)
    pd.testing.assert_frame_equal(run[0], log2)
    pd.testing.assert_frame_equal(run[1], people2)


def test_knowing_a_concept_makes_correct_answers_more_likely(run):
    acc = run[0].groupby("truth_knew")["correct"].mean()
    assert acc[1] - acc[0] > 0.2


def test_planted_bad_questions_do_not_separate_strong_from_weak(run, course):
    log = run[0].merge(run[1][["student_id", "truth_ability"]], on="student_id")
    log = log.join(course.truth["truth_bad"], on="question_id")
    corr = log.groupby("truth_bad").apply(
        lambda g: np.corrcoef(g["correct"], g["truth_ability"])[0, 1], include_groups=False)
    assert corr[False] > 0.2 and abs(corr[True]) < 0.15


def test_practice_increases_knowledge(run):
    log = run[0].copy()
    log["attempt"] = log.groupby(["student_id", "concept"]).cumcount() + 1
    known = log.groupby("attempt")["truth_knew"].mean()
    assert known.is_monotonic_increasing and known.iloc[-1] > known.iloc[0] + 0.15


def test_dropout_rises_with_base_rate_so_bisection_is_valid(course):
    rates = [sim.dropout_rate(sim.simulate(200, 3, b, course, with_personas=False)[1])
             for b in (-4.0, -1.5, 1.0)]
    assert rates[0] < rates[1] < rates[2]


def test_low_motivation_students_drop_out_more(run):
    people = run[1][run[1]["persona"] == ""]
    early = people["dropped_week"].fillna(99) <= 3
    assert people.loc[early, "truth_motivation"].mean() < people.loc[~early, "truth_motivation"].mean()


def test_fixed_path_gives_everyone_the_same_questions(run):
    log = run[0]
    finished = run[1].loc[run[1]["finished_week"].notna(), "student_id"]
    paths = {tuple(log.loc[log["student_id"] == s, "question_id"]) for s in finished}
    assert len(paths) == 1


def test_personas_match_the_day2_scenario(course):
    ali, sara = sim.personas(course)
    assert {"for_loops", "while_loops"} <= ali.known
    assert not set(sim.ALI_WEAK) & ali.known and ali.weak["recursion"] < 1
    assert sara.speed < 0.6 and sara.slip >= 0.25


def test_public_view_hides_the_answer_key(run):
    for df in run:
        assert not [c for c in sim.public(df).columns if c.startswith("truth_")]
    assert "correct" in sim.public(run[0]).columns
