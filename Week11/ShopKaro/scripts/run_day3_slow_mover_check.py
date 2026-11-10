"""
Robustness check for slow / intermittent movers: are Croston-SBA and TSB better than the production forecaster
(global LightGBM) on extra cut-offs that are NOT the 4 festival-season folds of the Day 3 backtest?

Same 60-SKU velocity panel (20 highest-volume SKUs per tier) and the same models; 8 extra cut-offs spread over 2025.
Reports per-day WAPE and the error of each SKU's 14-day TOTAL (what a reorder decision uses).

Writes reports/day3_slow_mover_extra_cutoffs.csv. Usage:  python scripts/run_day3_slow_mover_check.py   (~5 min)
"""

from __future__ import annotations

import duckdb
import pandas as pd

import shopkaro.forecasting.models as fm
from shopkaro.config.settings import settings

EXTRA_CUTOFFS = ["2025-01-20", "2025-02-10", "2025-04-20", "2025-06-25", "2025-07-15", "2025-09-15", "2025-10-10",
                 "2025-12-01"]


def main() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    panel = con.execute(
        """
        WITH r AS (
            SELECT product_id, velocity_tier,
                   ROW_NUMBER() OVER (PARTITION BY velocity_tier ORDER BY SUM(units_sold) DESC, product_id) AS rn
            FROM daily_sales GROUP BY product_id, velocity_tier
        )
        SELECT CAST(d.sale_date AS TIMESTAMP) AS sale_date, d.product_id, d.category, d.velocity_tier, d.units_sold
        FROM daily_sales d JOIN r USING (product_id) WHERE r.rn <= 20 ORDER BY d.product_id, d.sale_date
        """
    ).df()
    fest_cal = con.execute("SELECT * FROM festival_calendar").df()
    con.close()
    fest_lookup = fm._build_date_category_festival_lookup(
        festival_cal_df=fest_cal, all_categories=sorted(panel["category"].astype(str).unique().tolist())
    )

    saved = fm.BACKTEST_FOLD_CUTOFFS
    fm.BACKTEST_FOLD_CUTOFFS = [(c, c) for c in EXTRA_CUTOFFS]  # the fold loop reads this module constant
    try:
        sink: list[dict] = []
        fm._evaluate_panel_across_folds(panel, "product_id", "SKU_By_Velocity_60_extra_cutoffs", fest_lookup, sink)
    finally:
        fm.BACKTEST_FOLD_CUTOFFS = saved

    df = pd.DataFrame(sink)
    df = df[df["segment_type"] == "velocity"].reset_index(drop=True)
    out = settings.reports_dir / "day3_slow_mover_extra_cutoffs.csv"
    df.to_csv(out, index=False)
    slow = df[df["segment"] == "Slow_Intermittent"].set_index("model_name")
    print(slow[["wape_pct", "total_wape_pct", "total_bias_pct"]].to_string())
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
