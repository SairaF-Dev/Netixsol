"""
Automated tests for Day 3 — Tasks 2 & 3: Multi-Model Forecasting Pipeline & 4-Fold Rolling-Origin Backtesting.
"""

from __future__ import annotations

import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.forecasting.models import run_day3_task2_task3_forecasting_backtest


def test_day3_task2_task3_forecasting_backtest() -> None:
    """Verify all 7 forecasting models across 4 folds and 3 horizons (7d, 14d, 30d)."""
    backtest_df, fig_path = run_day3_task2_task3_forecasting_backtest()

    # 3 panels (11 categories, top-50 SKUs, 60 SKUs stratified by velocity) x 3 horizons x 7 models = 63 rows
    assert len(backtest_df) == 63
    assert set(backtest_df["hierarchy_level"]) == {"Category_Level", "Top50_SKU_Level", "SKU_By_Velocity_60"}
    breakdown = pd.read_csv(settings.reports_dir / "day3_forecast_accuracy_breakdown.csv")
    assert {"festival days", "regular days", "Fast_Mover", "Steady_Mover", "Slow_Intermittent"} <= set(breakdown["segment"])

    # Slow movers: judged on the error of the 14-day total (what reordering uses), not per-day WAPE.
    slow = breakdown[
        (breakdown["hierarchy_level"] == "SKU_By_Velocity_60") & (breakdown["segment"] == "Slow_Intermittent")
    ].set_index("model_name")
    assert {"6. Croston-SBA (Intermittent Demand)", "7. TSB (Intermittent Demand)"} <= set(slow.index)
    lgbm_total = float(slow.loc["5. Global LightGBM (Lags + Rolling + Festival Features)", "total_wape_pct"])
    assert lgbm_total < 100.0  # better than forecasting zero (which scores exactly 100%)
    assert lgbm_total < float(slow.loc["2. Seasonal Naive (7-Day Cycle)", "total_wape_pct"])
    assert fig_path.exists()
    assert (settings.reports_dir / "day3_forecasting_backtest_comparison.csv").exists()

    required_cols = {
        "hierarchy_level",
        "model_name",
        "horizon_days",
        "n_folds",
        "n_series",
        "wape_pct",
        "mae",
        "rmse",
        "smape_pct",
        "mape_pct",
        "zero_actual_days_pct",
    }
    assert required_cols.issubset(set(backtest_df.columns))
    assert (backtest_df["n_folds"] == 4).all()

    # Verify Global LightGBM and Prophet beat Naive, Seasonal Naive, and Holt-Winters ETS on WAPE across all horizons
    for level in ["Category_Level", "Top50_SKU_Level"]:
        for h in [7, 14, 30]:
            sub = backtest_df[
                (backtest_df["hierarchy_level"] == level) & (backtest_df["horizon_days"] == h)
            ].set_index("model_name")

            w_naive = float(sub.loc["1. Naive (Last Observed Value)", "wape_pct"])
            w_snaive = float(sub.loc["2. Seasonal Naive (7-Day Cycle)", "wape_pct"])
            w_ets = float(sub.loc["3. Classical Holt-Winters ETS (s=7)", "wape_pct"])
            w_prophet = float(
                sub.loc["4. Prophet (Fourier + Moving Islamic Holidays)", "wape_pct"]
            )
            w_lgbm = float(
                sub.loc["5. Global LightGBM (Lags + Rolling + Festival Features)", "wape_pct"]
            )

            assert w_prophet < min(w_naive, w_snaive, w_ets)
            assert w_lgbm < min(w_naive, w_snaive, w_ets)

