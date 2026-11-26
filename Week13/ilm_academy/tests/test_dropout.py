"""Dropout early warning: checkpoint rows see only the past, the right students are at risk,
and risk levels / reasons map to actions."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ilm.analytics.dropout import (FEATURES, cutoffs, level, level_table, reason, snapshot)
from ilm.learners.simulator import drop_hazard

Q_SEC = pd.Series({"q-01": 30.0})


def log_for(student, weeks, correct=1):
    rows, seq = [], 0
    for w in weeks:
        for d in (0, 2):
            seq += 1
            rows.append({"student_id": student, "seq": seq, "week": w, "day": (w - 1) * 7 + d,
                         "question_id": "q-01", "qtype": "mcq", "correct": correct, "response_time_sec": 30.0})
    return pd.DataFrame(rows)


def test_checkpoint_features_do_not_see_the_future():
    people = pd.DataFrame({"student_id": ["s"], "dropped_week": [np.nan], "finished_week": [np.nan]})
    a = snapshot(log_for("s", range(1, 9)), people, Q_SEC)
    changed = log_for("s", range(1, 9))
    changed.loc[changed.week >= 3, "correct"] = 0                 # change only weeks 3+
    b = snapshot(changed, people, Q_SEC)
    early = lambda d: d[d.week <= 2][FEATURES].reset_index(drop=True)
    pd.testing.assert_frame_equal(early(a), early(b))
    assert not a[a.week == 3][FEATURES].equals(b[b.week == 3][FEATURES])


def test_who_is_at_risk_at_each_checkpoint():
    people = pd.DataFrame({"student_id": ["quits3", "stays", "done2"],
                           "dropped_week": [3, np.nan, np.nan], "finished_week": [np.nan, np.nan, 2]})
    log = pd.concat([log_for("quits3", [1, 2, 3]), log_for("stays", range(1, 9)), log_for("done2", [1, 2])])
    s = snapshot(log, people, Q_SEC)
    q = s[s.student_id == "quits3"]
    assert q.week.tolist() == [1, 2, 3] and q.label.tolist() == [0, 0, 1]   # label at the quit week only
    assert s[s.student_id == "stays"].label.sum() == 0 and len(s[s.student_id == "stays"]) == 7
    assert s[s.student_id == "done2"].week.tolist() == [1]                  # finished: no longer at risk


def test_an_empty_week_is_visible():
    people = pd.DataFrame({"student_id": ["s"], "dropped_week": [np.nan], "finished_week": [np.nan]})
    s = snapshot(log_for("s", [1, 3]), people, Q_SEC).set_index("week")
    assert s.loc[2, "empty_week"] == 1 and s.loc[2, "days_since_last"] == 7 + 4
    assert s.loc[3, "empty_week"] == 0


def test_risk_levels_follow_capacity_cutoffs():
    scores = np.linspace(0, 1, 1001)
    cuts = cutoffs(scores)
    levels = np.array([level(x, cuts) for x in scores])
    assert abs((levels == "high").mean() - 0.10) < 0.01 and abs((levels == "medium").mean() - 0.20) < 0.01
    t = level_table(np.r_[np.ones(100), np.zeros(901)].astype(int), levels[::-1])
    assert t.loc["high", "share_of_all_dropouts"] == 1.0


def test_reason_comes_from_the_biggest_push_up():
    assert reason(pd.Series({"acc_last10": 0.4, "empty_week": 0.1}))[0] == "struggling"
    assert reason(pd.Series({"acc_last10": 0.1, "empty_week": 0.5}))[0] == "activity"
    assert reason(pd.Series({"acc_last10": -0.2, "empty_week": -0.1}))[0] == "other"   # nothing pushes up


def test_simulator_hazard_rises_with_failure_and_inactivity_and_falls_with_motivation():
    base = drop_hazard(-1.5, 0.5, 0.0, False)
    assert drop_hazard(-1.5, 0.9, 0.0, False) > base
    assert drop_hazard(-1.5, 0.5, 0.0, True) > base
    assert drop_hazard(-1.5, 0.5, 1.0, False) < base
