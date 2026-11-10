"""
Runner script for Day 2 — Task 4: Comprehensive Offline Evaluation of All 7 Models.
"""

from __future__ import annotations

import time

from shopkaro.recommendations.evaluation import run_day2_task4_offline_evaluation


def main() -> None:
    t0 = time.perf_counter()
    print(">>> Running Day 2 — Task 4: Comprehensive Offline Evaluation (All 7 Models)...")

    comparison_df, _, fig_path = run_day2_task4_offline_evaluation(
        k=10,
        max_eval_users=5000,
        max_cold_users=2000,
    )
    elapsed = time.perf_counter() - t0

    print(f"\n=== Day 2 Task 4: Full 7-Model Offline Evaluation Table ({elapsed:.2f}s) ===")
    cols_accuracy = [
        "model_name",
        "precision_at_10",
        "recall_at_10",
        "ndcg_at_10",
        "map_at_10",
        "hit_rate_at_10",
    ]
    print("\n--- Part A: Ranking Accuracy Metrics (Warm Test Set, K=10) ---")
    print(comparison_df[cols_accuracy].to_string(index=False))

    cols_beyond = [
        "model_name",
        "catalogue_coverage_pct",
        "intra_list_diversity_at_10",
        "novelty_bits_at_10",
        "cold_user_ndcg_at_10",
        "cold_item_hit_rate_at_10",
    ]
    print("\n--- Part B: Beyond-Accuracy & Cold-Start Metrics ---")
    print(comparison_df[cols_beyond].to_string(index=False))

    print(f"\nSaved comparison chart to: {fig_path}")


if __name__ == "__main__":
    main()

