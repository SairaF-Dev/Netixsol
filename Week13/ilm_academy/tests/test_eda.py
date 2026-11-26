"""EDA statistics, checked against answers worked out by hand."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ilm.analytics import eda


def test_wilson_interval_known_values():
    lo, hi = eda.wilson(50, 100)
    assert lo == pytest.approx(0.404, abs=1e-3) and hi == pytest.approx(0.596, abs=1e-3)
    lo, hi = eda.wilson(0, 10)                     # the naive formula gives [0, 0] here
    assert lo == pytest.approx(0.0, abs=1e-12) and hi == pytest.approx(0.278, abs=1e-3)


def test_accuracy_by_drops_small_groups_and_sorts_hardest_first():
    df = pd.DataFrame({"skill": ["a"] * 300 + ["b"] * 300 + ["c"] * 10,
                       "correct": [1] * 240 + [0] * 60 + [1] * 90 + [0] * 210 + [0] * 10})
    t = eda.accuracy_by(df, "skill", min_n=200)
    assert t["skill"].tolist() == ["b", "a"]          # c has too few answers to rank
    assert t["accuracy"].tolist() == [0.3, 0.8]


def test_learning_curve_same_students_removes_the_who_is_left_effect():
    # strong student: right at once, stops after 2 attempts; weak: wrong, wrong, right, right
    df = pd.DataFrame({"s": ["strong"] * 2 + ["weak"] * 4, "k": "x",
                       "correct": [1, 1, 0, 0, 1, 1]})
    df = eda.add_attempt(df, "s", "k")
    everyone = eda.learning_curve(df, 4, same_students=False)
    same = eda.learning_curve(df, 4, same_students=True)
    assert everyone["accuracy"].tolist() == [0.5, 0.5, 1.0, 1.0]
    assert same["accuracy"].tolist() == [0.0, 0.0, 1.0, 1.0]    # only the weak student


def test_survival_hazard_by_hand():
    people = pd.DataFrame({"dropped_week": [1, 1, 2, np.nan, np.nan],
                           "finished_week": [np.nan, np.nan, np.nan, 2, np.nan]})
    t = eda.survival(people, 3)
    assert t["at_risk"].tolist() == [5, 3, 1]       # finisher leaves the risk set after week 2
    assert t["dropped"].tolist() == [2, 1, 0]
    assert t["hazard"].round(3).tolist() == [0.4, 0.333, 0.0]
    assert t["not_dropped_share"].tolist() == [0.6, 0.4, 0.4]


def test_separable_means_intervals_do_not_overlap():
    a, b, c = (pd.Series({"low": lo, "high": hi}) for lo, hi in ((0.1, 0.2), (0.3, 0.4), (0.15, 0.35)))
    assert eda.separable(a, b) and not eda.separable(a, c)


def test_end_labels_of_lines_that_finish_together_are_pushed_apart():
    # found 2026-11-26: two learning curves both ending at 68% printed their names on top of each other
    assert eda.label_offsets([0.68, 0.681], span=0.2) == [-6, 6]
    assert eda.label_offsets([0.3, 0.7], span=0.4) == [0, 0]
