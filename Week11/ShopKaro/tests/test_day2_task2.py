"""
Automated tests for Day 2 — Task 2: Collaborative Filtering
(Item-to-Item Similarity & Implicit ALS Matrix Factorisation).
"""

from __future__ import annotations

from shopkaro.recommendations.collaborative import (
    ItemToItemCFRecommender,
    run_day2_task2_collaborative_filtering,
)


def test_day2_task2_collaborative_filtering():
    """Verify Item-to-Item CF, Implicit ALS tuning, and 'Similar Products' retrieval."""
    cf_metrics, tuning_results, models = run_day2_task2_collaborative_filtering(
        k=10, max_eval_users=500
    )

    assert len(cf_metrics) == 2
    assert len(tuning_results) == 4
    assert set(models.keys()) == {"item_to_item_cf", "implicit_als"}

    # Verify both CF models significantly exceed the Task 1 PopularOverall baseline NDCG@10 (~0.00326)
    item_cf_m, als_m = cf_metrics
    assert item_cf_m.ndcg_at_k > 0.01
    assert als_m.ndcg_at_k > 0.01

    # Verify "Similar Products" returns valid in-stock items excluding the query product itself
    item_cf: ItemToItemCFRecommender = models["item_to_item_cf"]  # type: ignore[assignment]
    sims = item_cf.get_similar_items("SK-00001", k=10)
    assert len(sims) == 10
    assert all(s["product_id"] != "SK-00001" for s in sims)
    assert all(s["in_stock"] for s in sims)

