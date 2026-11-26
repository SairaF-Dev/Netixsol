"""IRT recovers known question parameters and flags planted bad questions."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ilm.tracing.irt import IRT, first_answers, precision_recall


@pytest.fixture(scope="module")
def synthetic():
    rng = np.random.default_rng(0)
    n_s, n_q = 600, 30
    theta = rng.normal(0, 1, n_s)
    b = rng.normal(0, 1, n_q)
    a = rng.lognormal(0, 0.2, n_q)
    a[[0, 1, 2]] = 0.0          # planted: measure nothing
    a[3] = -1.0                 # planted: wrong answer key
    rows = [(s, f"q{q}", int(rng.random() < 1 / (1 + np.exp(-a[q] * (theta[s] - b[q])))))
            for s in range(n_s) for q in range(n_q)]
    df = pd.DataFrame(rows, columns=["user_id", "question_id", "correct"])
    return df, theta, b, a


def test_2pl_recovers_difficulty_discrimination_and_ability(synthetic):
    df, theta, b, a = synthetic
    m = IRT("2pl").fit(df)
    p = m.item_params.loc[[f"q{i}" for i in range(len(b))]]
    good = a > 0.5                                  # difficulty is undefined when a is ~0
    assert np.corrcoef(p["b"][good], b[good])[0, 1] > 0.9
    assert np.corrcoef(p["a"], a)[0, 1] > 0.9
    assert np.corrcoef(m.theta.loc[range(len(theta))], theta)[0, 1] > 0.85


def test_planted_bad_questions_are_flagged_with_the_right_reason(synthetic):
    df, *_ = synthetic
    flags = IRT("2pl").fit(df).flag_bad()
    assert precision_recall(set(flags.index), {"q0", "q1", "q2", "q3"})["recall"] == 1.0
    assert "answer key" in flags.loc["q3", "reason"]


def test_1pl_cannot_see_discrimination(synthetic):
    df, *_ = synthetic
    m = IRT("1pl").fit(df)
    # after rescaling the shared a is not exactly 1, but it IS the same for every question
    assert np.allclose(m.item_params["a"], m.item_params["a"].iloc[0]) and m.flag_bad().empty


def test_first_answers_keeps_only_the_first_try():
    df = pd.DataFrame({"user_id": [1, 1, 1, 2], "question_id": ["x", "x", "y", "x"],
                       "correct": [0, 1, 1, 1]})
    assert first_answers(df, "user_id", "question_id")["correct"].tolist() == [0, 1, 1]


def test_precision_recall_by_hand():
    assert precision_recall({"a", "b", "c", "d"}, {"a", "b", "x"}) == \
        {"flagged": 4, "planted": 3, "found": 2, "precision": 0.5, "recall": 0.667}


def test_noise_around_zero_is_weak_not_an_answer_key_problem():
    m = IRT("2pl")
    m.item_params = pd.DataFrame({"a": [-0.1, -0.8, 0.1, 1.2], "n": 100}, index=list("wxyz"))
    reasons = m.flag_bad()["reason"]
    assert "weak" in reasons["w"] and "answer key" in reasons["x"] and "weak" in reasons["y"]
    assert "z" not in reasons.index
