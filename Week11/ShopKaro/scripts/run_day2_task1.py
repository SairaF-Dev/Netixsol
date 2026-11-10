"""
Execution script for Day 2 — Task 1: Baseline Recommenders.

Fits and evaluates:
1. Most Popular Overall (`PopularOverallRecommender`)
2. Most Popular in the User's Favourite Category (`FavouriteCategoryPopularRecommender`)
3. Recently Trending - Last 7 Days (`Trending7DayRecommender`)
"""

from __future__ import annotations

import json
import time

import pandas as pd

from shopkaro.recommendations.baselines import run_day2_task1_baselines


def main() -> None:
    t0 = time.perf_counter()
    print(">>> Running Day 2 — Task 1: Fitting and Evaluating Baseline Recommenders (K=10)...")
    metrics_list, models = run_day2_task1_baselines(k=10, max_eval_users=5000)
    elapsed = time.perf_counter() - t0

    df_metrics = pd.DataFrame([m.to_dict() for m in metrics_list])
    print(f"\n=== Day 2 Task 1: Baseline Evaluation Results (Completed in {elapsed:.2f}s) ===")
    print(df_metrics.to_string(index=False))

    # Show sample top-5 recommendations for a warm user and a cold-start user
    fav_cat_model = models["favourite_category"]
    sample_users = list(fav_cat_model.user_top_categories.keys())[:2]
    if sample_users:
        uid = sample_users[0]
        user_cats = fav_cat_model.user_top_categories[uid]
        print(f"\n=== Sample Recommendations for Warm User '{uid}' (Top Categories: {user_cats}) ===")
        for key, model in models.items():
            recs = model.recommend(uid, k=3)
            print(f"\n[{model.name}]")
            for r in recs:
                print(
                    f"  #{r['rank']} {r['product_id']} | {r['title'][:58]} | "
                    f"{r['category']} | PKR {r['price_pkr']:,.0f} | score={r['score']}"
                )


if __name__ == "__main__":
    main()

