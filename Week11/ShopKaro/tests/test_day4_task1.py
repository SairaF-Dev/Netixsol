"""
Automated tests for Day 4 — Task 1: Hybrid Search Engine & Roman Urdu Query Parser.
"""

from __future__ import annotations

from shopkaro.search.hybrid_search import run_day4_task1_hybrid_search


def test_day4_task1_hybrid_search() -> None:
    """Verify UrduLishQueryParser, BM25 vs Semantic vs Hybrid metrics, and all 4 PDF demo queries."""
    eval_df, engine, demo_outputs = run_day4_task1_hybrid_search()

    assert len(eval_df) == 3
    assert engine.parser is not None

    # 1. Verify UrduLishQueryParser price & entity extraction on the 4 PDF queries
    p1 = engine.parser.parse("eid ke liye lawn suit under 5000")
    assert p1.max_price_pkr == 5000.0
    assert p1.category_hint == "Women's Lawn & Unstitched"
    assert p1.occasion_hint == "Eid"

    p2 = engine.parser.parse("bachon ke liye school bag")
    assert p2.category_hint == "Kids & School Supplies"

    p3 = engine.parser.parse("shaadi ke liye red lehenga 20 hazaar tak")
    assert p3.max_price_pkr == 20000.0
    assert p3.category_hint == "Bridal & Formal Wear"
    assert p3.color_hint == "Red"

    p4 = engine.parser.parse("laptop for coding under 1.5 lac")
    assert p4.max_price_pkr == 150000.0
    assert p4.category_hint == "Laptops & Computing"

    # 2. Brief's minimum target: hybrid beats keyword search on NDCG@10, shown on both query sets
    import json

    from shopkaro.config.settings import settings

    assert set(eval_df["queries_evaluated"]) == {50}
    bm25_row, sem_row, hyb_row = eval_df.iloc[0], eval_df.iloc[1], eval_df.iloc[2]
    assert float(hyb_row["ndcg_at_10"]) > float(bm25_row["ndcg_at_10"])
    assert float(hyb_row["ndcg_at_10"]) > float(sem_row["ndcg_at_10"])
    assert float(hyb_row["budget_compliance_pct"]) >= 95.0
    sig = json.loads((settings.reports_dir / "day4_search_significance.json").read_text(encoding="utf-8"))
    for set_name in ("dev_50", "holdout_20"):
        c = sig[set_name]["hybrid_vs_keyword"]
        assert c["mean_ndcg_diff"] > 0 and c["ci_95"][0] > 0, (set_name, c)
        assert c["sign_test_p"] < 0.05, (set_name, c)

    # 3. Verify all 4 demo queries return in-stock, budget-compliant top results
    for q_str, res_list in demo_outputs.items():
        assert len(res_list) == 5
        parsed_q = engine.parser.parse(q_str)
        for item in res_list[:3]:
            assert item["in_stock"] is True
            if parsed_q.max_price_pkr is not None:
                assert float(item["price_pkr"]) <= parsed_q.max_price_pkr
            if parsed_q.category_hint is not None:
                assert item["category"] == parsed_q.category_hint

