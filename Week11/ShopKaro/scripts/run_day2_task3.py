"""
Execution script for Day 2 — Task 3: Content-Based, Two-Tower Hybrid & Cold-Start Models.
"""

from __future__ import annotations

import json
import time
import pandas as pd

from shopkaro.recommendations.hybrid import (
    ContentBasedRecommender,
    HybridTwoTowerRecommender,
    run_day2_task3_content_and_hybrid,
)


def main() -> None:
    t0 = time.perf_counter()
    print(">>> Running Day 2 — Task 3: Content-Based, Two-Tower Hybrid & Cold-Start Evaluation...")
    metrics_list, cold_summary, models = run_day2_task3_content_and_hybrid(
        k=10, max_eval_users=5000
    )
    elapsed = time.perf_counter() - t0

    df_eval = pd.DataFrame([m.to_dict() for m in metrics_list])
    print(f"\n=== Day 2 Task 3: Content & Hybrid Evaluation on Warm Test Set ({elapsed:.2f}s) ===")
    print(df_eval.to_string(index=False))

    print("\n=== Cold-Start User & Cold-Start Item Evaluation Summary ===")
    print(json.dumps(cold_summary.to_dict(), indent=2))

    # Show Content-Based Similar Products for SK-00001 (Sapphire Lawn) and SK-00008 (Lenovo Coding Laptop)
    content_model: ContentBasedRecommender = models["content_based"]  # type: ignore[assignment]
    for pid in ["SK-00001", "SK-00008"]:
        meta = content_model.item_metadata.get(pid, {})
        print(f"\n=== Content-Based Similar Products to {pid}: {meta.get('title', '')[:60]} ===")
        for sim in content_model.get_similar_items_content(pid, k=3):
            print(
                f"  #{sim['rank']} {sim['product_id']} | {sim['title'][:58]} | "
                f"{sim['category']} | PKR {sim['price_pkr']:,.0f} | sim={sim['content_similarity']}"
            )

    # Show Cold-Start Onboarding User Demo ("Eid Lawn Suit under 5,000 PKR")
    hybrid_model: HybridTwoTowerRecommender = models["hybrid_two_tower"]  # type: ignore[assignment]
    cold_recs = hybrid_model.recommend_for_cold_user(
        preferred_category="Women's Lawn & Unstitched",
        max_budget_pkr=5000.0,
        occasion="Eid",
        k=4,
    )
    print("\n=== Cold-Start New User Demo (Onboarding: Women's Lawn, Budget <= 5000 PKR, Occasion=Eid) ===")
    for rank, (pid, sc) in enumerate(cold_recs, start=1):
        meta = hybrid_model.item_metadata.get(pid, {})
        print(
            f"  #{rank} {pid} | {meta.get('title', '')[:58]} | "
            f"{meta.get('category', '')} | PKR {meta.get('price_pkr', 0):,.0f} | score={sc:.3f}"
        )


if __name__ == "__main__":
    main()

