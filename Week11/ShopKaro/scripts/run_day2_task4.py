"""
Runner script for Day 2 — Task 4: Comprehensive Offline Evaluation of All 8 Models.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict

from shopkaro.config.settings import settings

from shopkaro.recommendations.evaluation import run_day2_task4_offline_evaluation


def main() -> None:
    t0 = time.perf_counter()
    print(">>> Running Day 2 — Task 4: Comprehensive Offline Evaluation (All 8 Models)...")

    comparison_df, models, fig_path = run_day2_task4_offline_evaluation(
        k=10,
        max_eval_users=5000,
        max_cold_users=2000,
    )
    elapsed = time.perf_counter() - t0

    print(f"\n=== Day 2 Task 4: Full 8-Model Offline Evaluation Table ({elapsed:.2f}s) ===")
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

    log = asdict(models["neural_two_tower"].training_log)
    log_path = settings.reports_dir / "day2_two_tower_training_log.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(
        f"\nNeural two-tower: best epoch {log['best_epoch']} of {log['epochs_trained']}, "
        f"val NDCG@10 {log['best_val_ndcg_at_10']}, pop_weight {log['best_pop_weight']}, "
        f"revisit_boost {log['best_revisit_boost']}, {log['seconds']}s -> {log_path}"
    )
    print(f"Saved comparison chart to: {fig_path}")


if __name__ == "__main__":
    main()

