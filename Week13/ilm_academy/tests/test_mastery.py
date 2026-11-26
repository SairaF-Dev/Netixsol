"""The BKT mastery update, checked by hand and against pyBKT itself."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ilm.tracing.mastery import MASTERED, MasteryTracker, trace

PARAMS = pd.DataFrame({"prior": [0.3], "learns": [0.2], "guesses": [0.25], "slips": [0.1]},
                      index=["loops"])


def test_update_by_hand():
    t = MasteryTracker(PARAMS)
    assert t.p_correct("loops") == pytest.approx(0.3 * 0.9 + 0.7 * 0.25)        # 0.445
    # right answer: 0.27 / (0.27 + 0.175) = 0.6067, then learning: + 0.3933 * 0.2
    assert t.update("loops", True) == pytest.approx(0.27 / 0.445 + (1 - 0.27 / 0.445) * 0.2)
    t2 = MasteryTracker(PARAMS)
    # wrong answer: 0.03 / (0.03 + 0.525) = 0.0541, then learning
    assert t2.update("loops", False) == pytest.approx(0.03 / 0.555 + (1 - 0.03 / 0.555) * 0.2)


def test_right_answers_raise_and_wrong_answers_lower_mastery():
    t = MasteryTracker(PARAMS)
    seen = [t.update("loops", True) for _ in range(6)]
    assert all(b > a for a, b in zip(seen, seen[1:])) and t.mastered("loops")
    t = MasteryTracker(PARAMS)
    t.update("loops", True)
    high = t.p_known("loops")
    assert t.update("loops", False) < high


def test_a_lucky_guess_counts_for_less_when_guessing_is_easy():
    easy_guess = PARAMS.assign(guesses=0.5)
    assert MasteryTracker(easy_guess).update("loops", True) < MasteryTracker(PARAMS).update("loops", True)


def test_trace_uses_only_earlier_answers():
    log = pd.DataFrame({"student_id": ["s"] * 3, "concept": ["loops"] * 3, "correct": [1, 0, 1]})
    a = trace(log, PARAMS)
    b = trace(log.assign(correct=[1, 0, 0]), PARAMS)          # change only the LAST answer
    assert np.allclose(a["p_correct_before"], b["p_correct_before"])
    assert a["p_known_before"].iloc[0] == pytest.approx(0.3)   # first belief = the prior


@pytest.mark.slow
def test_tracker_matches_pybkt_predictions():
    """Our update must give the same P(correct) as pyBKT for the same parameters."""
    from pyBKT.models import Model
    rng = np.random.default_rng(0)
    rows = [{"student_id": u, "concept": "loops", "correct": int(rng.random() < 0.3 + 0.08 * t), "_order": u * 10 + t}
            for u in range(150) for t in range(8)]
    df = pd.DataFrame(rows)
    m = Model(seed=1, num_fits=1)
    defaults = {"user_id": "student_id", "skill_name": "concept", "correct": "correct", "order_id": "_order"}
    m.fit(data=df, defaults=defaults)
    p = m.params().reset_index().pivot_table(index="skill", columns="param", values="value")
    ours = trace(df, p[["prior", "learns", "guesses", "slips"]])["p_correct_before"].to_numpy()
    theirs = m.predict(data=df)["correct_predictions"].to_numpy()
    assert np.allclose(ours, theirs, atol=1e-4)


def test_threshold_is_the_classic_095():
    assert MASTERED == 0.95
