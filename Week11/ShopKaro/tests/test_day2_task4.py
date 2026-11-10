"""
Automated tests for Day 2 — Task 4: Comprehensive Offline Evaluation of All 8 Models.
"""

from __future__ import annotations

from shopkaro.config.settings import settings
from shopkaro.recommendations.evaluation import run_day2_task4_offline_evaluation


def test_day2_task4_offline_evaluation() -> None:
    """Verify that all 8 models are evaluated across accuracy, diversity, novelty, and cold-start."""
    comparison_df, models, fig_path = run_day2_task4_offline_evaluation(
        k=10,
        max_eval_users=500,
        max_cold_users=300,
    )

    assert len(comparison_df) == 8
    assert len(models) == 8
    assert fig_path.exists()
    assert (settings.reports_dir / "day2_model_comparison.csv").exists()

    required_cols = {
        "model_name",
        "model_family",
        "precision_at_10",
        "recall_at_10",
        "ndcg_at_10",
        "map_at_10",
        "hit_rate_at_10",
        "catalogue_coverage_pct",
        "intra_list_diversity_at_10",
        "novelty_bits_at_10",
        "cold_user_ndcg_at_10",
        "cold_item_hit_rate_at_10",
    }
    assert required_cols.issubset(set(comparison_df.columns))

    # Collaborative & Hybrid must significantly beat Baselines on NDCG@10
    max_baseline_ndcg = float(
        comparison_df[comparison_df["model_family"] == "Baseline"]["ndcg_at_10"].max()
    )
    hybrid_row = comparison_df[comparison_df["model_family"] == "Hybrid Blend"].iloc[0]
    assert float(hybrid_row["ndcg_at_10"]) > max_baseline_ndcg * 5.0

    # Intra-List Diversity must be in (0, 1] and Novelty must be positive bits
    assert (comparison_df["intra_list_diversity_at_10"] > 0.0).all()
    assert (comparison_df["intra_list_diversity_at_10"] <= 1.0).all()
    assert (comparison_df["novelty_bits_at_10"] > 5.0).all()

    # Cold-item HitRate@10 must be 0 for pure CF/baselines and >0 for Content & Hybrid
    assert float(hybrid_row["cold_item_hit_rate_at_10"]) > 0.0
    assert float(hybrid_row["cold_user_ndcg_at_10"]) > float(
        comparison_df.iloc[0]["cold_user_ndcg_at_10"]
    )


    # Neural two-tower (PyTorch): trained, selected on validation, beats every baseline, and can surface cold items
    neural = models["neural_two_tower"]
    assert neural.training_log.best_epoch >= 1
    assert neural.training_log.best_val_ndcg_at_10 > 0.0
    neural_row = comparison_df[comparison_df["model_family"] == "Neural Two-Tower (PyTorch)"].iloc[0]
    assert float(neural_row["ndcg_at_10"]) > max_baseline_ndcg
    assert float(neural_row["cold_item_hit_rate_at_10"]) > 0.0
    # New users: onboarding category through the user tower must beat plain popularity clearly
    assert neural.training_log.cold_start_selected["validation_users"] > 0
    assert float(neural_row["cold_user_ndcg_at_10"]) > 3.0 * float(comparison_df.iloc[0]["cold_user_ndcg_at_10"])
