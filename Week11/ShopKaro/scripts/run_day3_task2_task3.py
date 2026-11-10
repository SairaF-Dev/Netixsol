"""
Runner script for Day 3 — Tasks 2 & 3: Multi-Model Forecasting Pipeline & 4-Fold Rolling-Origin Backtesting.
"""

from __future__ import annotations

import time

from shopkaro.forecasting.models import run_day3_task2_task3_forecasting_backtest


def main() -> None:
    t0 = time.perf_counter()
    print(
        ">>> Running Day 3 — Tasks 2 & 3: Multi-Model Forecasting Pipeline & 4-Fold Rolling-Origin Backtesting..."
    )

    backtest_df, fig_path = run_day3_task2_task3_forecasting_backtest()
    elapsed = time.perf_counter() - t0

    print(f"\n=== Day 3 Tasks 2 & 3: 4-Fold Rolling-Origin Backtest Results ({elapsed:.2f}s) ===")
    cols = [
        "model_name",
        "horizon_days",
        "n_folds",
        "n_series",
        "wape_pct",
        "mae",
        "rmse",
        "smape_pct",
    ]

    print("\n--- Level A: Category-Level Backtest (11 Categories x 4 Folds) ---")
    cat_sub = backtest_df[backtest_df["hierarchy_level"] == "Category_Level"]
    print(cat_sub[cols].to_string(index=False))

    print("\n--- Level B: Product-Level Backtest (Top-50 SKUs x 4 Folds) ---")
    sku_sub = backtest_df[backtest_df["hierarchy_level"] == "Top50_SKU_Level"]
    print(sku_sub[cols].to_string(index=False))

    print(f"\nSaved Figure 11: {fig_path}")


if __name__ == "__main__":
    main()

