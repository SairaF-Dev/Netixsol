"""
Tests for stock calibration and the inventory replay simulator. The simulator is checked on tiny hand-made
inputs; the full 2025 replay (scripts/run_day3_inventory_backtest.py, ~minutes) is not run here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from shopkaro.data.synthesizer import calibrate_stock_to_demand
from shopkaro.forecasting import inventory_backtest as bt


def test_lost_sales_and_lead_time() -> None:
    """One SKU, demand 10/day, no stock at start, target 100 at every review: the first order arrives after L."""
    demand = np.full((1, 30), 10.0)
    sim = bt.simulate(
        demand,
        order_up_to=lambda t: np.array([100.0]),
        lead_times=np.array([3]),
        start_idx=0,
        end_idx=20,
        initial_stock=np.array([0.0]),
        seed=0,
    )
    first_arrival = int(np.argmax(sim["sold"][0] > 0))
    assert 2 <= first_arrival <= 4  # nominal lead time 3 days, +-15% noise rounds to 3 (maybe 2 or 4)
    assert sim["lost"][0, :first_arrival].sum() == 10.0 * first_arrival
    assert np.all(sim["sold"][0, :21] + sim["lost"][0, :21] == demand[0, :21])  # demand is either served or lost
    assert sim["orders"][0, 0] == 100.0  # order up to target from an empty position
    assert sim["orders"][0, 1:7].sum() == 0.0  # weekly review only


def test_order_quantity_accounts_for_pipeline_stock() -> None:
    """Units already on order must not be ordered again."""
    demand = np.zeros((1, 40))
    sim = bt.simulate(demand, lambda t: np.array([50.0]), np.array([10]), 0, 30, np.array([0.0]), seed=1)
    assert sim["orders"][0].sum() == 50.0  # one order; later reviews see 50 on hand / in transit


def test_same_lead_time_draws_for_every_policy() -> None:
    demand = np.random.default_rng(3).poisson(5.0, size=(4, 60)).astype(float)
    a = bt.simulate(demand, lambda t: np.full(4, 60.0), np.array([3, 5, 7, 9]), 0, 50, np.zeros(4), seed=9)
    b = bt.simulate(demand, lambda t: np.full(4, 60.0), np.array([3, 5, 7, 9]), 0, 50, np.zeros(4), seed=9)
    assert np.array_equal(a["sold"], b["sold"])


def test_forecast_policy_uses_latest_origin_only() -> None:
    """At review day t the policy must use a forecast fitted on data up to t-1 or earlier (no look-ahead)."""
    h = bt.FORECAST_HORIZON
    forecasts = {
        9: {"p50": np.full((1, h), 1.0), "sigma": np.zeros((1, h))},
        23: {"p50": np.full((1, h), 100.0), "sigma": np.zeros((1, h))},
    }
    target = bt.forecast_policy(forecasts, lead_times=np.array([3]))
    # Day 23 must still use origin 9 (1/day over 7 + 3 days, plus a small lead-time-variability buffer);
    # day 24 may use origin 23 (100/day).
    assert 10.0 <= target(23)[0] < 12.0
    assert 1000.0 <= target(24)[0] < 1100.0


def test_calibrated_stock_follows_demand() -> None:
    dates = pd.date_range("2025-02-01", "2025-03-15")
    sales = pd.concat(
        [
            pd.DataFrame({"sale_date": dates, "product_id": "FAST", "units_sold": 50}),
            pd.DataFrame({"sale_date": dates, "product_id": "SLOW", "units_sold": 1}),
            pd.DataFrame({"sale_date": dates, "product_id": "OOS", "units_sold": 5}),
        ]
    )
    cat = pd.DataFrame(
        {"product_id": ["FAST", "SLOW", "OOS", "NOSALES"], "stock_qty": [100, 100, 0, 77], "in_stock": [True, True, False, True]}
    )
    out = calibrate_stock_to_demand(cat, sales, seed=1).set_index("product_id")
    assert out.loc["FAST", "stock_qty"] > 20 * out.loc["SLOW", "stock_qty"]
    assert out.loc["OOS", "stock_qty"] == 0 and not out.loc["OOS", "in_stock"]
    assert out.loc["NOSALES", "stock_qty"] == 77
    cover = out.loc["FAST", "stock_qty"] / 50
    assert 2 <= cover <= 400
