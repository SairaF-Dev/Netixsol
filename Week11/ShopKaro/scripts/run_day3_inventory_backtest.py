"""Replay 2025 inventory under moving-average, seasonal-naive and forecast-driven replenishment (~20 minutes: 29 forecaster refits)."""

from __future__ import annotations

import json
import time

import pandas as pd

from shopkaro.forecasting.inventory_backtest import run_inventory_backtest


def main() -> None:
    t0 = time.perf_counter()
    results, comparison = run_inventory_backtest()
    pd.set_option("display.width", 200)
    print(results.set_index("policy").T.to_string())
    print(json.dumps(comparison, indent=2))
    print(f"\nDone in {time.perf_counter() - t0:.0f}s -> reports/day3_inventory_backtest.csv / .json")


if __name__ == "__main__":
    main()
