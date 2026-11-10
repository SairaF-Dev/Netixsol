"""
Automated tests for Day 3 — Tasks 4 & 5: Probabilistic P10/P50/P90 Forecasting & Inventory Intelligence.
"""

from __future__ import annotations

from shopkaro.config.settings import settings
from shopkaro.forecasting.inventory import (
    run_day3_task4_task5_probabilistic_and_inventory,
)


def test_day3_task4_task5_probabilistic_and_inventory() -> None:
    """Verify P10/P50/P90 quantile calibration, safety stock, ROP, alerts, and DuckDB persistence."""
    prob_metrics, inv_summary, forecast_30d_df, alerts_df, fig_path = (
        run_day3_task4_task5_probabilistic_and_inventory(
            eval_origin_date="2025-03-15",
            horizon_days=30,
        )
    )

    # 1. Verify Task 4 Probabilistic Forecasting
    assert prob_metrics.evaluated_skus == 300
    assert prob_metrics.horizon_days == 30
    assert prob_metrics.quantile_crossing_count == 0
    assert 65.0 <= prob_metrics.empirical_coverage_80pct <= 95.0
    assert len(forecast_30d_df) == 300 * 30
    assert (forecast_30d_df["p10_units"] <= forecast_30d_df["p50_units"]).all()
    assert (forecast_30d_df["p50_units"] <= forecast_30d_df["p90_units"]).all()

    # 2. Verify Task 5 Inventory Intelligence & Alert Tiers
    assert len(alerts_df) == 300
    assert inv_summary.total_tracked_skus == 300
    assert inv_summary.critical_stockout_count > 0
    assert inv_summary.overstock_dead_capital_count > 0
    assert inv_summary.healthy_stock_count > 0
    assert (
        inv_summary.critical_stockout_count
        + inv_summary.festival_surge_watch_count
        + inv_summary.overstock_dead_capital_count
        + inv_summary.healthy_stock_count
        == 300
    )

    # Verify Safety Stock & Reorder Point math: ROP >= SS > 0
    assert (alerts_df["safety_stock_units"] > 0).all()
    assert (alerts_df["reorder_point_units"] >= alerts_df["safety_stock_units"]).all()

    # Verify Winter Wear & Jackets in warm March/April appear in OVERSTOCK_DEAD_CAPITAL
    overstock_cats = set(
        alerts_df[alerts_df["alert_status"] == "OVERSTOCK_DEAD_CAPITAL"]["category"].unique()
    )
    assert "Winter Wear & Jackets" in overstock_cats

    # Verify files saved
    assert fig_path.exists()
    assert (settings.reports_dir / "day3_inventory_alerts.csv").exists()

