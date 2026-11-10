"""
Automated tests for Day 3 — Task 1: Time-Series Analysis, Seasonal Decomposition, ADF Stationarity & Festival Spikes.
"""

from __future__ import annotations

from shopkaro.forecasting.timeseries_analysis import run_day3_task1_timeseries_analysis


def test_day3_task1_timeseries_analysis() -> None:
    """Verify 3-level aggregation, ADF stationarity tests, festival uplifts, lunar shift, and plots."""
    (
        platform_df,
        category_df,
        top50_sku_df,
        adf_df,
        fest_summary_df,
        lunar_shift_df,
        (fig9_path, fig10_path),
    ) = run_day3_task1_timeseries_analysis()

    # 1. Verify 3 hierarchy levels across 731 days (2024-01-01 .. 2025-12-31)
    assert len(platform_df) == 731
    assert len(category_df) == 11 * 731
    assert len(top50_sku_df) == 50 * 731

    # 2. Verify ADF stationarity table (1 Platform + 11 Categories = 12 series)
    assert len(adf_df) == 12
    assert (adf_df["is_stationary_diff1_5pct"] == True).all()  # noqa: E712

    # 3. Verify Pakistani festival uplift & lunar shift
    assert len(fest_summary_df) >= 8
    assert float(fest_summary_df["observed_uplift_multiplier"].max()) > 2.5

    # Islamic lunar festivals must show negative Gregorian shift (-10 to -12 days in 2025 vs 2024)
    lunar_rows = lunar_shift_df[lunar_shift_df["calendar_type"] == "Islamic_Moving"]
    assert len(lunar_rows) == 3
    assert (lunar_rows["gregorian_shift_days"] <= -9).all()

    # Fixed Gregorian festivals (e.g. 11.11, Azadi Sale) have 0 day shift
    fixed_rows = lunar_shift_df[lunar_shift_df["gregorian_shift_days"] == 0]
    assert len(fixed_rows) >= 2

    # 4. Verify saved diagnostic figures
    assert fig9_path.exists()
    assert fig10_path.exists()
