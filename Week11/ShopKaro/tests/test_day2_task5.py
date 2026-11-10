"""
Automated tests for Day 2 — Task 5: Business Re-Ranking Layer, Association Rules & Roman Urdu Explanations.
"""

from __future__ import annotations

from collections import Counter

from shopkaro.recommendations.reranking import run_day2_task5_business_reranking


def test_day2_task5_business_reranking() -> None:
    """Verify BusinessReRanker constraints, festival boost, association rules, and Roman Urdu explanations."""
    summary, assoc_engine, reranker, demo_recs = run_day2_task5_business_reranking(
        k=10,
        eval_users_sample=100,
    )

    assert summary.users_evaluated == 100
    assert summary.association_rules_mined > 500
    # Brand diversity cap must strictly cap max items per brand at <= 2
    assert summary.reranked_max_single_brand_count <= 2
    assert summary.reranked_avg_unique_brands_top10 > summary.raw_avg_unique_brands_top10

    # Commercial & Festival boosts must increase margin, sale share, and Pre-Eid category share
    assert summary.reranked_avg_margin_pct > summary.raw_avg_margin_pct
    assert summary.reranked_sale_item_share_pct >= summary.raw_sale_item_share_pct
    assert summary.pre_eid_festival_category_share_pct > summary.normal_eid_category_share_pct

    # Verify demo recommendations have 10 in-stock items, <=2 per brand, and Roman Urdu explanations
    assert len(demo_recs) == 10
    brand_counts = Counter(r["brand"] for r in demo_recs)
    assert max(brand_counts.values()) <= 2
    for rec in demo_recs:
        assert rec["in_stock"] is True
        assert len(rec["explanation_roman_urdu"]) > 15
        assert len(rec["explanation_en"]) > 15

    # Verify Frequently Bought Together rules for Smartphone (SK-00013) & Lawn Suit (SK-00001)
    fbt_phone = assoc_engine.get_frequently_bought_together("SK-00013", k=4)
    assert len(fbt_phone) == 4
    for r in fbt_phone:
        assert r["consequent_id"] != "SK-00013"
        assert r["lift"] > 1.0
        assert "Kyun ke aap ne" in r["explanation_roman_urdu"]

    # Verify already-purchased items are excluded for a buyer user
    buyer_uid = next(iter(reranker.user_purchased.keys()))
    purchased_items = reranker.user_purchased[buyer_uid]
    user_recs, _ = reranker.rerank_for_user(
        user_id=buyer_uid,
        k=10,
        candidate_pool_size=80,
        remove_purchased=True,
        only_in_stock=True,
    )
    rec_ids = {r["product_id"] for r in user_recs}
    assert rec_ids.isdisjoint(purchased_items)

