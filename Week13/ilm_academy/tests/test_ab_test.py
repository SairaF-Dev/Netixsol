"""The A/B test's machinery: assignment, sample size, sample-ratio check, analysis, decision."""
import pandas as pd
import pytest

from ilm.evaluation import ab_test as T


def test_assignment_is_stable_and_even():
    assert T.assign("ali") == T.assign("ali")
    arms = [T.assign(str(i)) for i in range(20_000)]
    assert abs(arms.count("adaptive") / len(arms) - 0.5) < 0.01


def test_new_salt_reshuffles():
    same = sum(T.assign(str(i)) == T.assign(str(i), "other-test") for i in range(5_000))
    assert 0.45 < same / 5_000 < 0.55          # independent of the old split


def test_sample_size_matches_textbook_and_inverts():
    # 45% -> 41%, alpha 0.05 two-sided, power 0.8: about 2,400 per arm (normal approximation)
    assert 2_350 <= T.n_per_arm() <= 2_450
    assert T.n_per_arm(mde=0.11) < T.n_per_arm(mde=0.04) < T.n_per_arm(mde=0.03)
    assert T.mde(T.n_per_arm()) == pytest.approx(0.04, abs=0.001)


def test_srm():
    assert T.srm(5_000, 5_000) == 1.0
    assert T.srm(5_300, 4_700) < 0.001          # a broken split is caught


def _frame(drop_f, drop_a, gain_f, gain_a, n=2_000):
    rows = []
    for arm, drop, gain in (("fixed", drop_f, gain_f), ("adaptive", drop_a, gain_a)):
        for i in range(n):
            rows.append({"arm": arm, "pretest": i % 7, "dropped_by_week4": int(i < drop * n),
                         "gain": gain + (i % 5) - 2, "hours": 3 + (i % 3) * 0.1, "hours_per_concept": 0.2})
    return pd.DataFrame(rows)


def test_decision_ships_only_a_real_win():
    win = T.analyse(_frame(0.45, 0.38, 10, 10))
    assert T.decide(win)["decision"] == "ship the adaptive path"
    learns_less = T.analyse(_frame(0.45, 0.38, 10, 7))
    assert T.decide(learns_less)["decision"].startswith("do not ship as is")
    nothing = T.analyse(_frame(0.45, 0.45, 10, 10))
    assert T.decide(nothing)["decision"].startswith("keep the fixed path")
    worse = T.analyse(_frame(0.40, 0.47, 10, 10))
    assert T.decide(worse)["decision"] == "do not ship: dropout is higher"


def test_broken_split_blocks_any_decision():
    df = _frame(0.45, 0.38, 10, 10)
    df = pd.concat([df, df[df.arm == "fixed"]])     # fixed arm doubled
    assert T.decide(T.analyse(df))["decision"].startswith("invalid")
