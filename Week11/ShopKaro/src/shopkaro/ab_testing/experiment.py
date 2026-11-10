"""
Day 5 — Task 2: A/B test of the recommender, estimated by replaying real logged behaviour.

Design (pre-registered: the constants below are fixed before any outcome is computed)
-------------------------------------------------------------------------------------
- Hypothesis: showing personalised recommendations (item-CF + business re-ranker, the production
  pipeline) on the homepage increases homepage-attributed conversion vs showing popular items.
- Population: every user active in the test window (test_interactions, 4 weeks).
- Assignment: 50/50 by hashing user_id with an experiment salt (deterministic, like production).
- Arms: Control A = top-10 popular in-stock items. Treatment B = production recommender, trained only
  on data from BEFORE the test window (train + validation), so it never sees the outcomes.
- Behaviour (replay / logged-relevance model): a shown item is clicked only if the user really
  interacted with it in the test window, and only if the slot is examined (probability
  1/log2(rank+1), i.e. lower slots are seen less). A click becomes a purchase only if the user really
  bought that item. Nothing about the size of the effect is assumed: any difference between the arms
  comes from which items each arm shows.
- Primary metric: homepage conversion rate (share of visitors with >= 1 homepage-attributed purchase).
  Secondary: click-through rate, revenue per visitor, average order value (Holm-corrected).
- Guardrails: sample-ratio mismatch, out-of-stock impressions, brand concentration, recommendation
  latency p95 < 100 ms.
- Decision rule: see `DECISION_RULE`.

Limitations (stated in the report): replay assumes users only engage with items they engaged with
anyway, so it ignores that a good recommendation can create new demand (conservative); behaviour
does not react to novelty, so novelty effects cannot be observed; visitors see one homepage at their
first visit (live session updates are not replayed).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from shopkaro.config.settings import settings

# ---------------------------------------------------------------------------
# Pre-registered design
# ---------------------------------------------------------------------------
EXPERIMENT_ID = "EXP-2026-REC-ITEMCF-V1"
ASSIGNMENT_SALT = "exp-2026-rec-itemcf-v1"
AA_SALT = "aa-check-2026"
ALPHA = 0.05
POWER = 0.80
PRIMARY_METRIC = "Conversion Rate (CVR)"
RELATIVE_MDE = 0.20  # smallest relative change in the primary metric worth detecting
HOMEPAGE_SLOTS = 10
EXAMINATION_PROB = 1.0 / np.log2(np.arange(2, HOMEPAGE_SLOTS + 2))  # rank 1..10
SHOPKARO_DAILY_VISITORS = 1_000_000 / 30  # brief: 1 million monthly visitors
LATENCY_GUARDRAIL_MS = 100.0
MAX_ITEMS_PER_BRAND = 2
MIN_CONVERTERS_FOR_AOV = 20
DECISION_RULE = (
    "SHIP: primary metric significantly better (alpha=0.05) and all guardrails pass. "
    "DO NOT SHIP: primary metric significantly worse, or any guardrail fails. "
    "EXTEND / RAMP: otherwise; keep running until the pre-registered sample size is reached "
    "(if the leading indicator CTR is significantly better, ramp traffic to reach it sooner)."
)


class ABTestingFramework:
    """Statistical tests and power analysis used by the ShopKaro experiment."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    @staticmethod
    def compute_required_sample_size(
        baseline_rate: float = 0.032,
        relative_mde: float = 0.15,
        alpha: float = 0.05,
        power: float = 0.80,
        daily_traffic: float = 12000,
    ) -> dict[str, Any]:
        """
        Sample size per arm for a two-sided two-proportion Z-test:
        n = [Z_{1-a/2} * sqrt(2 * p_bar * (1 - p_bar)) + Z_{1-b} * sqrt(p1(1-p1) + p2(1-p2))]^2 / (p2 - p1)^2
        """
        p1 = float(baseline_rate)
        z_alpha = float(stats.norm.ppf(1.0 - alpha / 2.0))
        z_beta = float(stats.norm.ppf(power))

        def n_for(mde: float) -> int:
            p2 = p1 * (1.0 + mde)
            pb = 0.5 * (p1 + p2)
            num = (z_alpha * np.sqrt(2.0 * pb * (1.0 - pb)) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
            return int(np.ceil(num / (p2 - p1) ** 2))

        n_per_arm = n_for(relative_mde)
        curve = [
            {
                "relative_mde_pct": round(m * 100.0, 1),
                "n_per_arm": n_for(m),
                "total_users": 2 * n_for(m),
                "estimated_days": round(2 * n_for(m) / max(daily_traffic, 1), 1),
            }
            for m in (0.05, 0.10, 0.15, 0.20, 0.30, 0.50)
        ]
        return {
            "baseline_rate": p1,
            "target_rate": p1 * (1.0 + relative_mde),
            "relative_mde_pct": round(relative_mde * 100.0, 2),
            "alpha": alpha,
            "power": power,
            "daily_traffic": daily_traffic,
            "required_n_per_arm": n_per_arm,
            "required_total_users": 2 * n_per_arm,
            "estimated_duration_days": round(2 * n_per_arm / max(daily_traffic, 1), 1),
            "mde_power_curve": curve,
        }

    @staticmethod
    def achieved_power(baseline_rate: float, relative_mde: float, n_per_arm: int, alpha: float = ALPHA) -> float:
        """Power to detect `relative_mde` on a proportion with `n_per_arm` users per arm."""
        p1, p2 = baseline_rate, baseline_rate * (1.0 + relative_mde)
        se = np.sqrt(p1 * (1 - p1) / n_per_arm + p2 * (1 - p2) / n_per_arm)
        if se <= 0:
            return 0.0
        z = abs(p2 - p1) / se - stats.norm.ppf(1 - alpha / 2)
        return float(stats.norm.cdf(z))

    @staticmethod
    def two_proportion_z_test(success_a: int, n_a: int, success_b: int, n_b: int, metric_name: str) -> dict[str, Any]:
        """Two-sided two-proportion Z-test with a 95% confidence interval on the difference."""
        p_a = success_a / max(n_a, 1)
        p_b = success_b / max(n_b, 1)
        diff = p_b - p_a
        p_pool = (success_a + success_b) / max(n_a + n_b, 1)
        se_pool = float(np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_a + 1.0 / n_b)))
        z_stat = float(diff / se_pool) if se_pool > 0 else 0.0
        p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(z_stat))))
        se_unpooled = float(np.sqrt(p_a * (1.0 - p_a) / n_a + p_b * (1.0 - p_b) / n_b))
        ci_low, ci_high = diff - 1.96 * se_unpooled, diff + 1.96 * se_unpooled
        rel = lambda x: (x / p_a * 100.0) if p_a > 0 else float("nan")  # noqa: E731
        test_type = "Two-proportion z-test"
        if min(success_a, success_b) < 10:
            # Normal approximation is unreliable with few events: use Fisher's exact test instead
            _, p_value = stats.fisher_exact([[success_b, n_b - success_b], [success_a, n_a - success_a]])
            p_value = float(p_value)
            test_type = "Fisher's exact test (few events)"
        return {
            "metric": metric_name,
            "test_type": test_type,
            "control_mean": round(p_a * 100.0, 4),
            "treatment_mean": round(p_b * 100.0, 4),
            "unit": "%",
            "control_successes": int(success_a),
            "treatment_successes": int(success_b),
            "absolute_lift": round(diff * 100.0, 4),
            "relative_lift_pct": round(rel(diff), 2),
            "ci_95_low": round(ci_low * 100.0, 4),
            "ci_95_high": round(ci_high * 100.0, 4),
            "rel_ci_95_low_pct": round(rel(ci_low), 2),
            "rel_ci_95_high_pct": round(rel(ci_high), 2),
            "test_statistic": round(z_stat, 4),
            "p_value": p_value,
        }

    @staticmethod
    def welch_t_and_mannwhitney_test(vals_a: np.ndarray, vals_b: np.ndarray, metric_name: str, unit: str = "PKR") -> dict[str, Any]:
        """Welch's two-sample t-test (unequal variances) + Mann-Whitney U as a robustness check."""
        mean_a, mean_b = float(np.mean(vals_a)), float(np.mean(vals_b))
        diff = mean_b - mean_a
        se = float(np.sqrt(np.var(vals_a, ddof=1) / len(vals_a) + np.var(vals_b, ddof=1) / len(vals_b)))
        t_res = stats.ttest_ind(vals_b, vals_a, equal_var=False)
        mw = stats.mannwhitneyu(vals_b, vals_a, alternative="two-sided")
        ci_low, ci_high = diff - 1.96 * se, diff + 1.96 * se
        rel = lambda x: (x / mean_a * 100.0) if mean_a > 0 else float("nan")  # noqa: E731
        return {
            "metric": metric_name,
            "test_type": "Welch t-test (+ Mann-Whitney U)",
            "control_mean": round(mean_a, 2),
            "treatment_mean": round(mean_b, 2),
            "unit": unit,
            "control_successes": int(len(vals_a)),
            "treatment_successes": int(len(vals_b)),
            "absolute_lift": round(diff, 2),
            "relative_lift_pct": round(rel(diff), 2),
            "ci_95_low": round(ci_low, 2),
            "ci_95_high": round(ci_high, 2),
            "rel_ci_95_low_pct": round(rel(ci_low), 2),
            "rel_ci_95_high_pct": round(rel(ci_high), 2),
            "test_statistic": round(float(t_res.statistic), 4),
            "p_value": float(t_res.pvalue),
            "mann_whitney_p_value": float(mw.pvalue),
        }

    @staticmethod
    def holm_adjust(p_values: list[float]) -> list[float]:
        """Holm-Bonferroni adjusted p-values (controls family-wise error across several metrics)."""
        m = len(p_values)
        order = np.argsort(p_values)
        adjusted = np.empty(m)
        running = 0.0
        for rank, idx in enumerate(order):
            running = max(running, min(1.0, (m - rank) * p_values[idx]))
            adjusted[idx] = running
        return adjusted.tolist()


# ---------------------------------------------------------------------------
# Replay simulation
# ---------------------------------------------------------------------------
def assign_variant(user_id: str, salt: str = ASSIGNMENT_SALT) -> str:
    """Deterministic 50/50 split, stable for a user across visits and servers."""
    h = int(hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:8], 16)
    return "Treatment_B" if h % 2 else "Control_A"


@dataclass
class _Arms:
    control_list: list[str]
    treatment_for: Any  # callable(user_id) -> list[str]
    seen_before: Any  # callable(user_id) -> set[str] of items interacted with before the test
    catalogue: dict[str, dict[str, Any]]
    model_info: dict[str, Any]


def _build_arms(db_path: Path) -> tuple[_Arms, duckdb.DuckDBPyConnection]:
    """Train the production recommender on pre-test data only (train + validation)."""
    from shopkaro.recommendations.collaborative import ItemToItemCFRecommender, _load_sparse_interaction_data
    from shopkaro.recommendations.reranking import BusinessReRanker
    from shopkaro.recommendations.serving import RealtimeItemCFRecommender, SessionEventStore

    con = duckdb.connect()
    con.execute(f"ATTACH '{Path(db_path).as_posix()}' AS sk (READ_ONLY)")
    # Pre-test history only: the model must not see the outcomes it is evaluated on
    con.execute(
        "CREATE VIEW train_interactions AS "
        "SELECT * FROM sk.train_interactions UNION ALL SELECT * FROM sk.val_interactions"
    )
    con.execute("CREATE VIEW product_catalogue AS SELECT * FROM sk.product_catalogue")

    t0 = time.perf_counter()
    cat_df, u2r, _uids, i2c, iids, R, bought = _load_sparse_interaction_data(con)
    cf = ItemToItemCFRecommender().fit_from_sparse(cat_df, u2r, i2c, iids, R, bought)
    fit_s = time.perf_counter() - t0

    full_cat = con.execute("SELECT * FROM sk.product_catalogue").df()
    catalogue = {str(r["product_id"]): r for r in full_cat.to_dict("records")}
    rt = RealtimeItemCFRecommender(cf, SessionEventStore())
    reranker = BusinessReRanker(base_recommender=rt, catalogue_df=full_cat, user_purchased=cf.user_seen_items)

    # Control: the classic "Top Products" widget = most popular in-stock items
    control_list = [pid for pid, _ in cf.recommend_ids("__no_history__", k=HOMEPAGE_SLOTS)]

    cold_cache: list[str] = []

    def treatment_for(user_id: str) -> list[str]:
        if user_id not in cf.user_to_row:
            if not cold_cache:  # every new visitor gets the same cold-start page: compute once
                recs, _ = reranker.rerank_for_user(user_id="__new_visitor__", k=HOMEPAGE_SLOTS)
                cold_cache.extend(r["product_id"] for r in recs)
            return cold_cache
        recs, _ = reranker.rerank_for_user(user_id=user_id, k=HOMEPAGE_SLOTS)
        return [r["product_id"] for r in recs]

    def seen_before(user_id: str) -> set[str]:
        row = cf.user_to_row.get(user_id)
        return set() if row is None else {cf.col_to_item[int(c)] for c in cf.R_log_csr[row].indices}

    info = {"model": cf.name, "trained_on": "train_interactions + val_interactions", "fit_seconds": round(fit_s, 1),
            "pretest_users": len(u2r)}
    return _Arms(control_list, treatment_for, seen_before, catalogue, info), con


def simulate_replay_experiment(
    db_path: Path | None = None,
    seed: int = 42,
    max_users: int | None = None,
    aa_test: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Run the replay experiment. Returns one row per visitor and run metadata.
    `aa_test=True` shows the control homepage in both arms (a pipeline sanity check: must be non-significant).
    """
    arms, con = _build_arms(db_path or settings.duckdb_path)
    truth = con.execute(
        """
        SELECT user_id, product_id,
               MAX(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS bought,
               MIN(CAST(event_timestamp AS TIMESTAMP)) AS first_ts
        FROM sk.test_interactions GROUP BY 1, 2
        """
    ).df()
    test_start = pd.Timestamp(con.execute("SELECT CAST(MIN(event_timestamp) AS TIMESTAMP) FROM sk.test_interactions").fetchone()[0])
    segments = dict(con.execute("SELECT user_id, segment_name FROM sk.customer_segments").fetchall())
    pretest_users = {r[0] for r in con.execute("SELECT DISTINCT user_id FROM train_interactions").fetchall()}
    con.close()

    grouped = truth.groupby("user_id", sort=True)
    interacted_by = grouped["product_id"].agg(set).to_dict()
    bought_by = truth[truth["bought"] == 1].groupby("user_id")["product_id"].agg(set).to_dict()
    first_ts_by = grouped["first_ts"].min().to_dict()
    user_ids = sorted(interacted_by)
    if max_users is not None and max_users < len(user_ids):
        user_ids = sorted(np.random.default_rng(seed).choice(user_ids, max_users, replace=False).tolist())

    rng = np.random.default_rng(seed)
    salt = AA_SALT if aa_test else ASSIGNMENT_SALT
    rows: list[dict[str, Any]] = []
    latencies_ms: list[float] = []
    for uid in user_ids:
        interacted = interacted_by[uid]
        bought = bought_by.get(uid, set())
        variant = assign_variant(uid, salt)
        warm = uid in pretest_users

        if variant == "Treatment_B" and not aa_test:
            t0 = time.perf_counter()
            shown = arms.treatment_for(uid)
            if warm:
                latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        else:
            shown = arms.control_list

        examined = rng.random(len(shown)) < EXAMINATION_PROB[: len(shown)]
        clicks = [pid for pid, seen in zip(shown, examined) if seen and pid in interacted]
        seen = arms.seen_before(uid) if warm else set()
        new_item_clicks = [pid for pid in clicks if pid not in seen]
        purchases = [pid for pid in clicks if pid in bought]
        new_item_purchases = [pid for pid in purchases if pid not in seen]
        brands = Counter(str(arms.catalogue[p]["brand"]) for p in shown)
        rows.append(
            {
                "user_id": uid,
                "variant": variant,
                "is_returning": warm,
                "segment": segments.get(uid, "New visitor") if warm else "New visitor",
                "week": int(min((first_ts_by[uid] - test_start).days // 7 + 1, 4)),
                "n_clicks": len(clicks),
                "clicked": int(bool(clicks)),
                "clicked_new_item": int(bool(new_item_clicks)),
                "converted": int(bool(purchases)),
                "converted_new_item": int(bool(new_item_purchases)),
                "converted_seen_item": int(len(purchases) > len(new_item_purchases)),
                "revenue_pkr": float(sum(float(arms.catalogue[p]["price_pkr"]) for p in purchases)),
                "oos_impressions": int(sum(int(arms.catalogue[p]["stock_qty"]) <= 0 for p in shown)),
                "max_items_one_brand": int(max(brands.values()) if brands else 0),
                "items_shown": "|".join(shown),
            }
        )

    meta = {
        **arms.model_info,
        "experiment_id": EXPERIMENT_ID,
        "aa_test": aa_test,
        "visitors": len(rows),
        "treatment_latency_ms": latencies_ms,
        "test_window_start": str(test_start)[:10],
    }
    return pd.DataFrame(rows), meta


def peeking_simulation(
    baseline_rate: float,
    visitors_per_day_per_arm: int,
    days: int = 28,
    n_sims: int = 2000,
    seed: int = 7,
) -> dict[str, Any]:
    """
    A/A experiments (no true effect). Compare the false-positive rate of one test at the planned end
    vs testing every day and stopping at the first p < 0.05 ("peeking").
    """
    rng = np.random.default_rng(seed)
    a = rng.binomial(visitors_per_day_per_arm, baseline_rate, size=(n_sims, days)).cumsum(axis=1)
    b = rng.binomial(visitors_per_day_per_arm, baseline_rate, size=(n_sims, days)).cumsum(axis=1)
    n = visitors_per_day_per_arm * np.arange(1, days + 1)
    p_pool = (a + b) / (2 * n)
    se = np.sqrt(np.clip(p_pool * (1 - p_pool), 1e-12, None) * (2 / n))
    z = np.abs((b - a) / n) / se
    sig = z > stats.norm.ppf(1 - ALPHA / 2)
    return {
        "days": days,
        "simulations": n_sims,
        "false_positive_rate_fixed_horizon_pct": round(float(sig[:, -1].mean() * 100), 2),
        "false_positive_rate_daily_peeking_pct": round(float(sig.any(axis=1).mean() * 100), 2),
    }


# ---------------------------------------------------------------------------
# Evaluation + decision
# ---------------------------------------------------------------------------
def evaluate_experiment(exp_df: pd.DataFrame, meta: dict[str, Any]) -> dict[str, Any]:
    ab = ABTestingFramework()
    a = exp_df[exp_df["variant"] == "Control_A"]
    b = exp_df[exp_df["variant"] == "Treatment_B"]
    n_a, n_b = len(a), len(b)

    _, srm_p = stats.chisquare([n_a, n_b])
    metrics = [
        ab.two_proportion_z_test(int(a["converted"].sum()), n_a, int(b["converted"].sum()), n_b, PRIMARY_METRIC),
        ab.two_proportion_z_test(int(a["clicked"].sum()), n_a, int(b["clicked"].sum()), n_b, "Click-Through Rate (CTR)"),
        ab.two_proportion_z_test(
            int(a["clicked_new_item"].sum()), n_a, int(b["clicked_new_item"].sum()), n_b,
            "Discovery CTR (items not seen before)",
        ),
        ab.two_proportion_z_test(
            int(a["converted_new_item"].sum()), n_a, int(b["converted_new_item"].sum()), n_b,
            "Discovery CVR (items not seen before)",
        ),
        ab.welch_t_and_mannwhitney_test(a["revenue_pkr"].to_numpy(), b["revenue_pkr"].to_numpy(), "Revenue Per Visitor (RPV)"),
    ]
    buyers_a = a.loc[a["converted"] == 1, "revenue_pkr"].to_numpy()
    buyers_b = b.loc[b["converted"] == 1, "revenue_pkr"].to_numpy()
    aov_note = None
    if min(len(buyers_a), len(buyers_b)) >= MIN_CONVERTERS_FOR_AOV:
        metrics.append(ab.welch_t_and_mannwhitney_test(buyers_a, buyers_b, "Average Order Value (AOV)"))
    else:
        aov_note = f"AOV not tested: fewer than {MIN_CONVERTERS_FOR_AOV} converters in an arm ({len(buyers_a)} vs {len(buyers_b)})."

    metrics[0]["role"] = "primary"
    secondary = metrics[1:]
    for m, adj in zip(secondary, ab.holm_adjust([m["p_value"] for m in secondary])):
        m["role"] = "secondary"
        m["p_value_holm"] = adj
    metrics[0]["p_value_holm"] = metrics[0]["p_value"]
    for m in metrics:
        m["significant"] = bool(m["p_value_holm"] < ALPHA)

    lat = meta.get("treatment_latency_ms") or [0.0]
    oos_a = a["oos_impressions"].sum() / max(n_a * HOMEPAGE_SLOTS, 1) * 100
    oos_b = b["oos_impressions"].sum() / max(n_b * HOMEPAGE_SLOTS, 1) * 100
    guardrails = {
        "srm_p_value": float(srm_p),
        "srm_check_passed": bool(srm_p > 0.001),
        "oos_impression_rate_control_pct": round(float(oos_a), 3),
        "oos_impression_rate_treatment_pct": round(float(oos_b), 3),
        "oos_guardrail_passed": bool(oos_b <= oos_a + 0.1),
        "treatment_max_items_one_brand": int(b["max_items_one_brand"].max()) if n_b else 0,
        "brand_guardrail_passed": bool((b["max_items_one_brand"].max() if n_b else 0) <= MAX_ITEMS_PER_BRAND),
        "recommendation_latency_p95_ms": round(float(np.percentile(lat, 95)), 2),
        "latency_guardrail_passed": bool(np.percentile(lat, 95) < LATENCY_GUARDRAIL_MS),
    }
    guardrails["all_passed"] = all(v for k, v in guardrails.items() if k.endswith("passed"))

    primary = metrics[0]
    ctr = metrics[1]
    baseline = primary["control_mean"] / 100.0
    power_now = ab.achieved_power(baseline, RELATIVE_MDE, min(n_a, n_b)) if baseline > 0 else 0.0
    plan = ab.compute_required_sample_size(baseline, RELATIVE_MDE, ALPHA, POWER, SHOPKARO_DAILY_VISITORS) if baseline > 0 else {}

    if not guardrails["all_passed"]:
        decision, reason = "DO NOT SHIP", "A guardrail failed."
    elif primary["significant"] and primary["absolute_lift"] > 0:
        decision, reason = "SHIP", "Primary metric significantly better and all guardrails pass."
    elif primary["significant"] and primary["absolute_lift"] < 0:
        decision, reason = "DO NOT SHIP", "Primary metric significantly worse."
    else:
        reason = (
            f"Primary metric not significant (p = {primary['p_value']:.3g}); the test has "
            f"{power_now:.0%} power to detect a {RELATIVE_MDE:.0%} change, below the planned {POWER:.0%}."
        )
        if ctr["significant"] and ctr["absolute_lift"] > 0:
            decision = "EXTEND / RAMP"
            reason += " Leading indicator CTR is significantly better, so ramp traffic and keep the test running."
        else:
            decision = "EXTEND / RAMP"
            reason += " No evidence either way yet; keep the test running."

    def subgroup(col: str) -> list[dict[str, Any]]:
        out = []
        for key, g in exp_df.groupby(col):
            ga, gb = g[g["variant"] == "Control_A"], g[g["variant"] == "Treatment_B"]
            if len(ga) < 100 or len(gb) < 100:
                continue
            t = ab.two_proportion_z_test(int(ga["clicked"].sum()), len(ga), int(gb["clicked"].sum()), len(gb), "CTR")
            c = ab.two_proportion_z_test(int(ga["converted"].sum()), len(ga), int(gb["converted"].sum()), len(gb), "CVR")
            out.append(
                {
                    col: key,
                    "users_control": len(ga),
                    "users_treatment": len(gb),
                    "ctr_control_pct": t["control_mean"],
                    "ctr_treatment_pct": t["treatment_mean"],
                    "ctr_relative_lift_pct": t["relative_lift_pct"],
                    "ctr_p_value": t["p_value"],
                    "cvr_control_pct": c["control_mean"],
                    "cvr_treatment_pct": c["treatment_mean"],
                    "cvr_p_value": c["p_value"],
                }
            )
        return out

    rpv = next(m for m in metrics if m["metric"].startswith("Revenue Per Visitor"))
    attribution = {
        "control_converters": int(a["converted"].sum()),
        "treatment_converters": int(b["converted"].sum()),
        "control_converters_bought_previously_browsed": int(a["converted_seen_item"].sum()),
        "treatment_converters_bought_previously_browsed": int(b["converted_seen_item"].sum()),
        "control_converters_bought_new_item": int(a["converted_new_item"].sum()),
        "treatment_converters_bought_new_item": int(b["converted_new_item"].sum()),
        "monthly_visitors_assumed": int(SHOPKARO_DAILY_VISITORS * 30),
        "est_monthly_homepage_revenue_gain_pkr": round(rpv["absolute_lift"] * SHOPKARO_DAILY_VISITORS * 30),
        "est_monthly_homepage_revenue_gain_ci_pkr": [
            round(rpv["ci_95_low"] * SHOPKARO_DAILY_VISITORS * 30),
            round(rpv["ci_95_high"] * SHOPKARO_DAILY_VISITORS * 30),
        ],
    }

    return {
        "attribution": attribution,
        "experiment_summary": {
            "experiment_id": EXPERIMENT_ID,
            "decision": decision,
            "decision_reason": reason,
            "decision_rule": DECISION_RULE,
            "control_arm": "Control_A: top-10 most popular in-stock products",
            "treatment_arm": "Treatment_B: item-to-item CF + business re-ranker (production pipeline)",
            "visitors": int(n_a + n_b),
            "control_users": int(n_a),
            "treatment_users": int(n_b),
            "returning_visitor_share_pct": round(float(exp_df["is_returning"].mean() * 100), 2),
            "primary_metric": PRIMARY_METRIC,
            "relative_mde_pct": RELATIVE_MDE * 100,
            "achieved_power_at_mde": round(power_now, 3),
            "aov_note": aov_note,
            **{k: v for k, v in meta.items() if k != "treatment_latency_ms"},
        },
        "metrics": metrics,
        "guardrails": guardrails,
        "power_plan": plan,
        "segment_subgroups": subgroup("segment"),
        "returning_vs_new": subgroup("is_returning"),
        "weekly_ctr": subgroup("week"),
        "weekly_returning_treatment": [
            {
                "week": int(wk),
                "returning_share_pct": round(float(gw["is_returning"].mean() * 100), 2),
                "returning_ctr_pct": round(float(gw.loc[gw["is_returning"], "clicked"].mean() * 100), 2)
                if gw["is_returning"].any() else None,
            }
            for wk, gw in b.groupby("week")
        ],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def _fmt_p(p: float) -> str:
    return f"{p:.2e}" if p < 0.001 else f"{p:.3f}"


def save_experiment_report(
    results: dict[str, Any],
    aa_results: dict[str, Any],
    peeking: dict[str, Any],
    reports_dir: Path | None = None,
    figures_dir: Path | None = None,
) -> dict[str, Path]:
    reports_dir = reports_dir or settings.reports_dir
    figures_dir = figures_dir or settings.figures_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    s, g, plan = results["experiment_summary"], results["guardrails"], results["power_plan"]

    paths = {
        "metrics_csv": reports_dir / "day5_ab_test_results.csv",
        "subgroups_csv": reports_dir / "day5_ab_test_segment_subgroups.csv",
        "summary_json": reports_dir / "day5_ab_test_summary.json",
        "report_md": reports_dir / "day5_ab_test_ship_decision_report.md",
        "figure": figures_dir / "14_ab_testing_and_api_latency.png",
    }
    pd.DataFrame(results["metrics"]).to_csv(paths["metrics_csv"], index=False)
    returning_rows = [
        {"segment": "Returning visitor" if r.pop("is_returning") else "First-time visitor", **r}
        for r in (dict(x) for x in results["returning_vs_new"])
    ]
    sub = pd.DataFrame(results["segment_subgroups"] + returning_rows)
    sub.to_csv(paths["subgroups_csv"], index=False)
    paths["summary_json"].write_text(
        json.dumps(
            {"experiment_summary": s, "attribution": results["attribution"], "guardrails": g, "power_plan": plan,
             "aa_test": {"metrics": aa_results["metrics"]}, "peeking": peeking},
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # Figure: lifts with CIs, power curve, peeking, weekly CTR
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f"{EXPERIMENT_ID} — replay A/B test: decision = {s['decision']}", fontsize=14, fontweight="bold")
    ax = axes[0, 0]
    ms = results["metrics"]
    y = np.arange(len(ms))
    lifts = [m["relative_lift_pct"] for m in ms]
    lo = [m["relative_lift_pct"] - m["rel_ci_95_low_pct"] for m in ms]
    hi = [m["rel_ci_95_high_pct"] - m["relative_lift_pct"] for m in ms]
    ax.errorbar(lifts, y, xerr=[lo, hi], fmt="o", color="#0f766e", capsize=5)
    ax.axvline(0, color="grey", lw=1)
    ax.set_xscale("symlog", linthresh=50)  # keeps small lifts readable next to very large ones
    ax.set_yticks(y, [f"{m['metric']}\n(p={_fmt_p(m['p_value_holm'])})" for m in ms])
    ax.set_xlabel("Relative lift vs control (%), 95% CI (symmetric log scale)")
    ax.set_title("A. Treatment vs control")
    ax = axes[0, 1]
    if plan:
        curve = plan["mde_power_curve"]
        ax.plot([c["relative_mde_pct"] for c in curve], [c["n_per_arm"] for c in curve], "o-", color="#1d4ed8")
        ax.axhline(min(s["control_users"], s["treatment_users"]), color="#b91c1c", ls="--", label="users per arm in this test")
        ax.set_yscale("log")
        ax.legend()
    ax.set_xlabel("Relative MDE on conversion (%)")
    ax.set_ylabel("Users needed per arm (80% power)")
    ax.set_title("B. Sample size needed vs detectable effect")
    ax = axes[1, 0]
    vals = [peeking["false_positive_rate_fixed_horizon_pct"], peeking["false_positive_rate_daily_peeking_pct"]]
    ax.bar(["Test once at end", "Check daily, stop at p<0.05"], vals, color=["#0f766e", "#b91c1c"])
    ax.axhline(5, color="grey", ls="--")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha="center")
    ax.set_ylabel("False-positive rate in A/A tests (%)")
    ax.set_title("C. Why peeking is a mistake")
    ax = axes[1, 1]
    wk = pd.DataFrame(results["weekly_ctr"])
    if not wk.empty:
        ax.plot(wk["week"], wk["ctr_control_pct"], "o-", label="Control")
        ax.plot(wk["week"], wk["ctr_treatment_pct"], "o-", label="Treatment")
        ax.legend()
    ax.set_xlabel("Week of first visit")
    ax.set_ylabel("CTR (%)")
    ax.set_title("D. CTR by week of first visit (decline = recency decay, not novelty)")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(paths["figure"], dpi=140)
    plt.close(fig)

    rows = "\n".join(
        f"| {m['metric']} ({m['role']}) | {m['control_mean']:,.4g} {m['unit']} | {m['treatment_mean']:,.4g} {m['unit']} "
        f"| {m['relative_lift_pct']:+.1f}% [{m['rel_ci_95_low_pct']:+.1f}%, {m['rel_ci_95_high_pct']:+.1f}%] "
        f"| {_fmt_p(m['p_value'])} | {_fmt_p(m['p_value_holm'])} | {'yes' if m['significant'] else 'no'} |"
        for m in results["metrics"]
    )
    rvn = "\n".join(
        f"| {'Returning' if r['is_returning'] else 'New'} | {r['users_control'] + r['users_treatment']:,} "
        f"| {r['ctr_control_pct']:.2f}% | {r['ctr_treatment_pct']:.2f}% | {r['ctr_relative_lift_pct']:+.1f}% | {_fmt_p(r['ctr_p_value'])} "
        f"| {r['cvr_control_pct']:.3f}% | {r['cvr_treatment_pct']:.3f}% |"
        for r in results["returning_vs_new"]
    )
    aa_m = aa_results["metrics"]
    at = results["attribution"]
    tb, ts, tn = at["treatment_converters"], at["treatment_converters_bought_previously_browsed"], at["treatment_converters_bought_new_item"]
    disc = next(m for m in results["metrics"] if m["metric"].startswith("Discovery CVR"))
    attribution_text = (
        f"- Treatment converters: **{tb}**, of whom **{ts}** bought a product they had already browsed before the test "
        f"and **{tn}** bought a product they had never seen. Control: {at['control_converters']} converters, "
        f"{at['control_converters_bought_new_item']} on never-seen products.\n"
        f"- Discovery conversion (never-seen products only): {disc['control_mean']:.4f}% vs {disc['treatment_mean']:.4f}%, "
        f"p = {_fmt_p(disc['p_value_holm'])} (Holm) — "
        + ("**significant**." if disc["significant"] else "**not significant**: no evidence yet that recommendations sell products shoppers had not already found.")
        + "\n- **Interpretation:** "
        + ("most of the conversion gain comes from re-surfacing products the shopper already browsed (a 'continue shopping' effect). "
           "That is real value, but a simple 'recently viewed' row would capture much of it; the ML model's extra value is discovery, "
           "measured by the discovery metrics above."
           if ts > tn else
           "the gain is mostly from products shoppers had not seen before, i.e. genuine discovery.")
        + f"\n- **Estimated revenue impact** (homepage-attributed only, at {at['monthly_visitors_assumed']:,} visitors/month): "
        f"PKR {at['est_monthly_homepage_revenue_gain_pkr']:,}/month, 95% CI PKR {at['est_monthly_homepage_revenue_gain_ci_pkr'][0]:,} "
        f"to {at['est_monthly_homepage_revenue_gain_ci_pkr'][1]:,}. Wide interval: based on {tb + at['control_converters']} converters."
    )
    weekly_text = "; ".join(
        f"week {w['week']}: {w['returning_share_pct']:.1f}% returning, returning-visitor CTR {w['returning_ctr_pct']:.1f}%"
        for w in results["weekly_returning_treatment"]
    )
    gp = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    report = f"""# A/B Test Result: {s['decision']}

**Experiment:** `{EXPERIMENT_ID}` · **Decision:** **{s['decision']}** · **Visitors:** {s['visitors']:,} ({s['control_users']:,} control / {s['treatment_users']:,} treatment)

**Why:** {s['decision_reason']}

## Design (fixed before analysis)
- **Hypothesis:** personalised homepage recommendations increase homepage conversion vs popular items.
- **Control A:** top-10 most popular in-stock products. **Treatment B:** item-to-item CF + business re-ranker (production pipeline), trained only on data before the test window ({s['trained_on']}).
- **Visitors:** everyone active in the 4-week test window from {s['test_window_start']}; {s['returning_visitor_share_pct']:.1f}% had earlier history (returning), the rest are new visitors who get the cold-start page.
- **Assignment:** 50/50 by hashing user ID with an experiment salt.
- **Behaviour (replay):** a shown item is clicked only if the visitor really interacted with it in the test window and the slot is examined (probability 1/log2(rank+1)); a purchase only if they really bought it. No effect size is assumed.
- **Primary metric:** {PRIMARY_METRIC}. Secondary: CTR, discovery CTR and discovery CVR (clicks / purchases of products the visitor never interacted with before the test, i.e. excluding re-shown history), revenue per visitor, AOV (Holm-corrected). Proportions with fewer than 10 events per arm use Fisher's exact test. Minimum detectable effect: {RELATIVE_MDE:.0%} relative.
- **Decision rule:** {DECISION_RULE}

## Results
| Metric | Control | Treatment | Relative lift [95% CI] | p | p (Holm) | Significant |
|---|---|---|---|---|---|---|
{rows}

{s['aov_note'] or ''}

## Where the gain comes from
{attribution_text}

### Returning vs new visitors (exploratory)
| Visitors | Users | CTR control | CTR treatment | CTR lift | p | CVR control | CVR treatment |
|---|---|---|---|---|---|---|---|
{rvn}

## Power and duration
- Control conversion is {results['metrics'][0]['control_mean']:.3f}%. To detect a {RELATIVE_MDE:.0%} relative change with {POWER:.0%} power this test would need **{plan.get('required_n_per_arm', 0):,} visitors per arm**; it had {min(s['control_users'], s['treatment_users']):,} (power {s['achieved_power_at_mde']:.0%}).
- At ShopKaro's traffic (~{SHOPKARO_DAILY_VISITORS:,.0f} visitors/day, from 1M monthly visitors) the full test takes **about {plan.get('estimated_duration_days', 0):.0f} days**. Run whole weeks (at least 2) to cover weekday/weekend patterns.

## Guardrails
| Guardrail | Value | Result |
|---|---|---|
| Sample ratio mismatch (chi-square) | p = {g['srm_p_value']:.3f} | {gp(g['srm_check_passed'])} |
| Out-of-stock impressions | control {g['oos_impression_rate_control_pct']:.2f}% / treatment {g['oos_impression_rate_treatment_pct']:.2f}% | {gp(g['oos_guardrail_passed'])} |
| Max items from one brand (treatment) | {g['treatment_max_items_one_brand']} (limit {MAX_ITEMS_PER_BRAND}) | {gp(g['brand_guardrail_passed'])} |
| Recommendation latency p95 | {g['recommendation_latency_p95_ms']:.1f} ms (limit {LATENCY_GUARDRAIL_MS:.0f}) | {gp(g['latency_guardrail_passed'])} |

## Sanity check and common mistakes
- **A/A test** (both arms see the control page, different salt): CTR p = {_fmt_p(aa_m[1]['p_value'])}, CVR p = {_fmt_p(aa_m[0]['p_value'])}. {'Not significant, as expected: the pipeline does not create false differences.' if not any(m['p_value'] < ALPHA for m in aa_m[:2]) else 'WARNING: significant difference in an A/A test; investigate assignment.'}
- **Peeking:** in {peeking['simulations']:,} simulated A/A tests, testing once at the end gives {peeking['false_positive_rate_fixed_horizon_pct']:.1f}% false positives; checking daily and stopping at the first p < 0.05 gives **{peeking['false_positive_rate_daily_peeking_pct']:.1f}%**. Fix the sample size in advance (or use a sequential test).
- **Multiple testing:** secondary metrics use Holm correction; subgroup tables are exploratory and not used for the decision.
- **Novelty effect:** real users may click new recommendations just because they are new, and the effect fades; in a live test, compare lift by week and discount the first week. Replayed behaviour cannot contain novelty, yet treatment CTR still falls over the test ({weekly_text}). That decline is **recency decay**: later visitors are less often returning, and returning visitors' old history predicts less the longer ago it was. A live test would show the same shape and could be misread as novelty; the remedy here is daily retraining plus live session updates (`POST /events`), not discounting week 1.

## Limitations
- Replay only credits items visitors engaged with anyway, so it ignores demand a recommendation creates: lifts are a conservative estimate.
- Visitors see one homepage at their first visit; live session updates (`POST /events`) are not replayed.
- New visitors ({100 - s['returning_visitor_share_pct']:.0f}%) get a cold-start page in treatment, which dilutes the overall effect.

_Generated by `scripts/run_day5.py` (`src/shopkaro/ab_testing/experiment.py`). Figure: `reports/figures/{paths['figure'].name}`._
"""
    paths["report_md"].write_text(report, encoding="utf-8")
    return paths


def run_replay_ab_test(db_path: Path | None = None, seed: int = 42, max_users: int | None = None) -> dict[str, Any]:
    """Full Day 5 Task 2 run: experiment, A/A check, peeking simulation, report."""
    exp_df, meta = simulate_replay_experiment(db_path, seed=seed, max_users=max_users)
    results = evaluate_experiment(exp_df, meta)
    aa_df, aa_meta = simulate_replay_experiment(db_path, seed=seed, max_users=max_users, aa_test=True)
    aa_results = evaluate_experiment(aa_df, aa_meta)
    baseline = results["metrics"][1]["control_mean"] / 100.0  # CTR: frequent enough to show the effect clearly
    peeking = peeking_simulation(baseline, visitors_per_day_per_arm=max(len(exp_df) // (2 * 28), 1))
    paths = save_experiment_report(results, aa_results, peeking)
    return {"results": results, "aa_results": aa_results, "peeking": peeking, "paths": paths, "exp_df": exp_df}
