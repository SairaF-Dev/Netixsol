"""
Runner script for Day 3 — Tasks 4 & 5: Probabilistic P10/P50/P90 Forecasting & Inventory Intelligence.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import time

from shopkaro.forecasting.inventory import (
    run_day3_task4_task5_probabilistic_and_inventory,
)


def main() -> None:
    t0 = time.perf_counter()
    print(
        ">>> Running Day 3 — Tasks 4 & 5: Probabilistic P10/P50/P90 Forecasting & Inventory Intelligence..."
    )

    prob_metrics, inv_summary, _, alerts_df, fig_path = (
        run_day3_task4_task5_probabilistic_and_inventory(
            eval_origin_date="2025-03-15",
            horizon_days=30,
        )
    )
    elapsed = time.perf_counter() - t0

    print(f"\n=== Task 4: Probabilistic P10/P50/P90 Calibration Metrics ({elapsed:.2f}s) ===")
    print(json.dumps(asdict(prob_metrics), indent=2))

    print("\n=== Task 5: Inventory Intelligence & Alert Summary (300 Tracked SKUs) ===")
    print(json.dumps(asdict(inv_summary), indent=2))

    print("\n=== Top 5 CRITICAL_STOCKOUT_RISK Alerts (Hero & High-Velocity SKUs) ===")
    crit_df = alerts_df[
        (alerts_df["alert_status"] == "CRITICAL_STOCKOUT_RISK")
        & (alerts_df["current_stock_qty"] > 0)
    ].head(5)
    for _, row in crit_df.iterrows():
        print(
            f"  * {row['product_id']} ({row['brand']} | {row['category']}) | "
            f"Stock={row['current_stock_qty']} | ROP={row['reorder_point_units']} | "
            f"SS={row['safety_stock_units']} | DOI_P50={row['days_of_inventory_p50']}d"
        )
        print(f"    Action: {row['recommended_action']}")

    print("\n=== Top 5 OVERSTOCK_DEAD_CAPITAL Alerts (Including Off-Season Winter Wear) ===")
    over_df = (
        alerts_df[alerts_df["alert_status"] == "OVERSTOCK_DEAD_CAPITAL"]
        .sort_values("days_of_inventory_p50", ascending=False)
        .head(5)
    )
    for _, row in over_df.iterrows():
        print(
            f"  * {row['product_id']} ({row['brand']} | {row['category']}) | "
            f"Stock={row['current_stock_qty']} | Daily P50={row['daily_demand_p50']} | "
            f"DOI_P50={row['days_of_inventory_p50']}d | Value=PKR {row['inventory_value_pkr']:,.0f}"
        )
        print(f"    Action: {row['recommended_action']}")

    print(f"\nSaved Figure 12: {fig_path}")


if __name__ == "__main__":
    main()
