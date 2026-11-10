"""
Runner script for Day 4 — Task 1: Hybrid Search Engine & Roman Urdu Query Parser.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import time

from shopkaro.search.hybrid_search import run_day4_task1_hybrid_search


def main() -> None:
    t0 = time.perf_counter()
    print(
        ">>> Running Day 4 — Task 1: Hybrid Search Engine (query parser + BM25 + semantic + RRF + feature re-ranker)..."
    )

    eval_df, engine, demo_outputs = run_day4_task1_hybrid_search()
    elapsed = time.perf_counter() - t0

    print(f"\n=== Day 4 Task 1: search benchmark, 50 dev + 20 held-out queries ({elapsed:.2f}s) ===")
    from shopkaro.config.settings import settings

    print((settings.reports_dir / "day4_search_comparison.csv").read_text(encoding="utf-8"))
    sig = json.loads((settings.reports_dir / "day4_search_significance.json").read_text(encoding="utf-8"))
    for set_name, comps in sig.items():
        c = comps["hybrid_vs_keyword"]
        print(
            f"  {set_name}: hybrid - keyword NDCG@10 = {c['mean_ndcg_diff']:+.3f}, 95% CI {c['ci_95']}, "
            f"better/worse/tied = {c['queries_better']}/{c['queries_worse']}/{c['queries_tied']}, "
            f"sign test p = {c['sign_test_p']:.3g}"
        )

    for dq, results in demo_outputs.items():
        assert engine.parser is not None
        parsed = engine.parser.parse(dq)
        print(f"\n=== Query: \"{dq}\" ===")
        print(
            f"  Parsed -> Category='{parsed.category_hint}' | MaxPrice={parsed.max_price_pkr} | "
            f"Color='{parsed.color_hint}' | Occasion='{parsed.occasion_hint}'"
        )
        for r in results[:3]:
            print(
                f"  #{r['rank']} {r['product_id']} | {r['brand']} | {r['title'][:54]} | "
                f"{r['category']} | PKR {r['price_pkr']:,.0f} | Score={r['score']:.3f}"
            )


if __name__ == "__main__":
    main()

