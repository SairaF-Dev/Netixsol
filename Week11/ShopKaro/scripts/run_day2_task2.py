"""
Execution script for Day 2 — Task 2: Collaborative Filtering
(Item-to-Item Cosine Similarity + Implicit ALS Matrix Factorisation + Hyperparameter Tuning).
"""

from __future__ import annotations

import time
import pandas as pd

from shopkaro.recommendations.collaborative import (
    ItemToItemCFRecommender,
    run_day2_task2_collaborative_filtering,
)


def main() -> None:
    t0 = time.perf_counter()
    print(">>> Running Day 2 — Task 2: Collaborative Filtering & Hyperparameter Tuning...")
    cf_metrics, tuning_results, models = run_day2_task2_collaborative_filtering(
        k=10, max_eval_users=5000
    )
    elapsed = time.perf_counter() - t0

    df_tune = pd.DataFrame([t.to_dict() for t in tuning_results])
    print("\n=== Implicit ALS Hyperparameter Tuning Results (on Validation Set) ===")
    print(df_tune.to_string(index=False))

    df_eval = pd.DataFrame([m.to_dict() for m in cf_metrics])
    print(f"\n=== Collaborative Filtering Evaluation on Test Set (Completed in {elapsed:.2f}s) ===")
    print(df_eval.to_string(index=False))

    # Show "Similar Products" for SK-00001 (Sapphire Lawn Suit) and SK-00013 (Samsung Galaxy A55)
    item_cf: ItemToItemCFRecommender = models["item_to_item_cf"]  # type: ignore[assignment]
    for target_pid in ["SK-00001", "SK-00013"]:
        meta = item_cf.item_metadata.get(target_pid, {})
        print(
            f"\n=== Similar Products to {target_pid}: {meta.get('title', '')[:55]} "
            f"({meta.get('category', '')}) ==="
        )
        for sim in item_cf.get_similar_items(target_pid, k=4):
            print(
                f"  #{sim['rank']} {sim['product_id']} | {sim['title'][:55]} | "
                f"{sim['category']} | PKR {sim['price_pkr']:,.0f} | sim={sim['similarity_score']}"
            )


if __name__ == "__main__":
    main()

