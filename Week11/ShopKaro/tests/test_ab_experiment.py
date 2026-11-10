"""
Tests for the Day 5 A/B experiment. They check that the METHOD is sound (assignment, statistics,
decision rule, no leakage, A/A sanity), never that it reaches a particular decision.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from shopkaro.ab_testing.experiment import (
    ABTestingFramework,
    assign_variant,
    evaluate_experiment,
    peeking_simulation,
    simulate_replay_experiment,
)


def _fake_experiment(cvr_a: float, cvr_b: float, n: int = 40000, seed: int = 0, oos_b: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for variant, cvr in (("Control_A", cvr_a), ("Treatment_B", cvr_b)):
        conv = rng.random(n) < cvr
        clicked = conv | (rng.random(n) < 0.02)
        rows.append(
            pd.DataFrame(
                {
                    "user_id": [f"{variant}-{i}" for i in range(n)],
                    "variant": variant,
                    "is_returning": rng.random(n) < 0.1,
                    "segment": "New visitor",
                    "week": rng.integers(1, 5, n),
                    "clicked": clicked.astype(int),
                    "clicked_new_item": clicked.astype(int),
                    "converted": conv.astype(int),
                    "converted_new_item": conv.astype(int),
                    "converted_seen_item": 0,
                    "revenue_pkr": np.where(conv, rng.lognormal(8, 0.5, n), 0.0),
                    "oos_impressions": oos_b if variant == "Treatment_B" else 0,
                    "max_items_one_brand": 2,
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


META = {"treatment_latency_ms": [5.0, 8.0, 12.0]}


def test_assignment_is_deterministic_and_balanced() -> None:
    users = [f"USR-{i}" for i in range(20000)]
    first = [assign_variant(u) for u in users]
    assert first == [assign_variant(u) for u in users]
    share = np.mean([v == "Treatment_B" for v in first])
    assert 0.48 < share < 0.52
    # A different salt gives an independent split (used for the A/A check)
    other = [assign_variant(u, "another-salt") for u in users]
    assert 0.45 < np.mean([a == b for a, b in zip(first, other)]) < 0.55


def test_decision_rule_follows_the_data() -> None:
    better = evaluate_experiment(_fake_experiment(0.020, 0.030), META)
    assert better["experiment_summary"]["decision"] == "SHIP"

    worse = evaluate_experiment(_fake_experiment(0.030, 0.020), META)
    assert worse["experiment_summary"]["decision"] == "DO NOT SHIP"

    same = evaluate_experiment(_fake_experiment(0.020, 0.020, seed=3), META)
    assert same["experiment_summary"]["decision"] == "EXTEND / RAMP"

    guardrail_broken = evaluate_experiment(_fake_experiment(0.020, 0.030, oos_b=3), META)
    assert guardrail_broken["guardrails"]["oos_guardrail_passed"] is False
    assert guardrail_broken["experiment_summary"]["decision"] == "DO NOT SHIP"


def test_statistics_helpers() -> None:
    ab = ABTestingFramework()
    # Holm: smallest p x m, then monotone
    assert np.allclose(ab.holm_adjust([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    # Few events -> Fisher's exact test
    small = ab.two_proportion_z_test(2, 50000, 9, 50000, "x")
    assert small["test_type"].startswith("Fisher")
    big = ab.two_proportion_z_test(500, 50000, 600, 50000, "x")
    assert big["test_type"] == "Two-proportion z-test" and big["p_value"] < 0.01
    # Power grows with sample size
    assert ab.achieved_power(0.01, 0.2, 10_000) < ab.achieved_power(0.01, 0.2, 100_000)


def test_peeking_inflates_false_positives() -> None:
    res = peeking_simulation(baseline_rate=0.02, visitors_per_day_per_arm=500, days=28, n_sims=1000)
    assert 2.0 <= res["false_positive_rate_fixed_horizon_pct"] <= 8.0
    assert res["false_positive_rate_daily_peeking_pct"] > 2 * res["false_positive_rate_fixed_horizon_pct"]


def test_replay_experiment_is_leak_free_and_aa_is_null() -> None:
    exp_df, meta = simulate_replay_experiment(max_users=8000, seed=1)
    assert meta["trained_on"] == "train_interactions + val_interactions"  # never sees the test window
    assert len(exp_df) == 8000
    assert set(exp_df["variant"]) == {"Control_A", "Treatment_B"}
    # Control always shows the same popular page; treatment personalises returning visitors
    control_pages = exp_df.loc[exp_df["variant"] == "Control_A", "items_shown"].unique()
    assert len(control_pages) == 1
    returning_t = exp_df[(exp_df["variant"] == "Treatment_B") & exp_df["is_returning"]]
    assert returning_t["items_shown"].nunique() > 1

    res = evaluate_experiment(exp_df, meta)
    assert res["guardrails"]["srm_check_passed"]
    assert res["guardrails"]["brand_guardrail_passed"]
    assert res["guardrails"]["recommendation_latency_p95_ms"] < 100

    aa_df, aa_meta = simulate_replay_experiment(max_users=8000, seed=1, aa_test=True)
    aa = evaluate_experiment(aa_df, aa_meta)
    ctr = next(m for m in aa["metrics"] if m["metric"].startswith("Click-Through"))
    assert ctr["p_value"] > 0.01, "an A/A test must not show a real difference"
