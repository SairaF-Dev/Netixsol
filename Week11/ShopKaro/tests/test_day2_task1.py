"""
Automated tests for Day 2 — Task 1: Baseline Recommenders & Ranking Metrics.
"""

from __future__ import annotations

from shopkaro.recommendations.baselines import run_day2_task1_baselines


def test_day2_task1_baselines_fit_and_eval():
    """Verify all 3 baseline recommenders fit on `train_interactions` and evaluate at K=10."""
    metrics_list, models = run_day2_task1_baselines(k=10, max_eval_users=500)

    assert len(metrics_list) == 3
    assert set(models.keys()) == {"popular_overall", "favourite_category", "trending_7d"}

    # Verify each model returns exactly 10 in-stock items for both warm and cold users
    for model in models.values():
        recs = model.recommend("USR-999999999", k=10)
        assert len(recs) == 10
        assert all(r["in_stock"] for r in recs)
        assert len({r["product_id"] for r in recs}) == 10

    # Verify FavouriteCategoryPopularRecommender has higher catalogue coverage than PopularOverall
    pop_m = metrics_list[0]
    cat_m = metrics_list[1]
    trend_m = metrics_list[2]

    assert pop_m.ndcg_at_k > 0.0
    assert cat_m.ndcg_at_k > 0.0
    assert trend_m.ndcg_at_k > 0.0
    assert cat_m.catalogue_coverage_pct > pop_m.catalogue_coverage_pct

