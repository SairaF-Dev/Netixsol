"""
Automated tests for Day 2 — Task 3: Content-Based, Hybrid Two-Tower & Cold-Start Models.
"""

from __future__ import annotations

from shopkaro.recommendations.hybrid import (
    ContentBasedRecommender,
    HybridTwoTowerRecommender,
    run_day2_task3_content_and_hybrid,
)


def test_day2_task3_content_hybrid_and_cold_start():
    """Verify Content-Based, Hybrid Two-Tower, and Cold-Start evaluation on warm and cold splits."""
    metrics_list, cold_summary, models = run_day2_task3_content_and_hybrid(
        k=10, max_eval_users=500
    )

    assert len(metrics_list) == 2
    content_m, hybrid_m = metrics_list

    # Verify Hybrid model achieves strong NDCG@10 and beats Content-Based alone
    assert content_m.ndcg_at_k > 0.01
    assert hybrid_m.ndcg_at_k >= content_m.ndcg_at_k

    # Verify Cold-Start User onboarding beats anonymous popularity cold start
    assert cold_summary.onboarding_hybrid_cold_user_ndcg10 > cold_summary.popular_cold_user_ndcg10
    assert cold_summary.cold_user_ndcg_uplift_pct > 0.0

    # Verify Cold-Start Items (0 clicks in train) are recommended via Content embeddings (> 0 hit rate)
    assert cold_summary.cold_items_count > 500
    assert cold_summary.content_hybrid_cold_item_hit_rate10 > 0.0

    # Verify Content-Based Similar Products works and respects budget/category onboarding
    content_model: ContentBasedRecommender = models["content_based"]  # type: ignore[assignment]
    sims = content_model.get_similar_items_content("SK-00001", k=5)
    assert len(sims) == 5
    assert all(s["product_id"] != "SK-00001" for s in sims)

    hybrid_model: HybridTwoTowerRecommender = models["hybrid_two_tower"]  # type: ignore[assignment]
    cold_recs = hybrid_model.recommend_for_cold_user(
        preferred_category="Women's Lawn & Unstitched",
        max_budget_pkr=5000.0,
        occasion="Eid",
        k=5,
    )
    assert len(cold_recs) == 5
    for pid, _ in cold_recs:
        meta = hybrid_model.item_metadata[pid]
        assert meta["category"] == "Women's Lawn & Unstitched"
        assert meta["price_pkr"] <= 5000.0

