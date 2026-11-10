"""
Runner script for Day 3 — Task 1: Time-Series Analysis, Seasonal Decomposition, ADF Stationarity & Festival Spikes.
"""

from __future__ import annotations

import time

from shopkaro.forecasting.timeseries_analysis import run_day3_task1_timeseries_analysis


def main() -> None:
    t0 = time.perf_counter()
    print(
        ">>> Running Day 3 — Task 1: Time-Series Analysis, Decomposition, ADF Stationarity & Festival Spikes..."
    )

    (
        platform_df,
        category_df,
        top50_sku_df,
        adf_df,
        fest_summary_df,
        lunar_shift_df,
        (fig9_path, fig10_path),
    ) = run_day3_task1_timeseries_analysis()
    elapsed = time.perf_counter() - t0

    print(f"\n=== 1. Three-Level Time-Series Aggregation Summary ({elapsed:.2f}s) ===")
    print(
        f"  - Platform Total Level : {len(platform_df):,} daily rows | "
        f"Total Units = {platform_df['units_sold'].sum():,} | "
        f"Total Revenue = PKR {platform_df['revenue_pkr'].sum():,.0f}"
    )
    print(
        f"  - Category Level (11)  : {len(category_df):,} rows ({category_df['category'].nunique()} categories x 731 days)"
    )
    print(
        f"  - Top-50 SKU Level     : {len(top50_sku_df):,} rows ({top50_sku_df['product_id'].nunique()} SKUs x 731 days)"
    )

    print("\n=== 2. Augmented Dickey-Fuller (ADF) Stationarity Test Results (Raw vs 1st Diff) ===")
    adf_cols = [
        "series_name",
        "hierarchy_level",
        "adf_stat_raw",
        "p_value_raw",
        "is_stationary_raw_5pct",
        "adf_stat_diff1",
        "p_value_diff1",
        "is_stationary_diff1_5pct",
        "recommended_differencing_d",
    ]
    print(adf_df[adf_cols].to_string(index=False))

    print("\n=== 3. Top Pakistani Festival Demand Uplift Windows (2024–2025) ===")
    fest_cols = [
        "festival_name",
        "festival_days",
        "avg_daily_units",
        "baseline_daily_units",
        "observed_uplift_multiplier",
    ]
    print(fest_summary_df[fest_cols].head(10).to_string(index=False))

    print("\n=== 4. Moving Hijri Lunar Shift vs Fixed Gregorian Festivals (2024 vs 2025) ===")
    print(lunar_shift_df.to_string(index=False))

    print(f"\nSaved Figure 09: {fig9_path}")
    print(f"Saved Figure 10: {fig10_path}")


if __name__ == "__main__":
    main()

