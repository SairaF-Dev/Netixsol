"""
Historical inventory replay: does forecast-driven replenishment beat simple rules?

Every SKU with sales history is restocked once a week for all of 2025 under three policies that differ ONLY in the
demand forecast they use. Each policy orders up to "forecast demand over (review period + lead time) + safety
stock" (same service levels, same lead-time allowance):

1. `moving_average`  - average of the last 28 days (common spreadsheet practice; no seasonality, no festivals)
2. `seasonal_naive`  - the same days one year earlier, aligned by weekday (misses the 11-day Hijri festival shift)
3. `forecast`        - the project's P10/P50/P90 forecaster, refitted every 14 days on data up to that day

Demand is the recorded daily sales (synthetic, see the data dictionary). Unmet demand is lost (no back orders).
Actual supplier lead times vary +-15% around the catalogue value, with the same random draws for every policy.
Everything starts from the same stock on 2024-12-01; results are measured on 2025-01-01..2025-12-31.

Measured: fill rate, lost units / revenue / gross margin, stockout SKU-days (all year and in Eid windows),
average stock value, and "dead capital" = value of stock that the next 60 days of actual demand would not sell.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.forecasting.inventory import ProbabilisticQuantileForecaster
from shopkaro.forecasting.models import _build_date_category_festival_lookup

REVIEW_DAYS = 7
REFIT_EVERY_DAYS = 14
FORECAST_HORIZON = 42  # >= refit interval + review period + longest lead time (11 days)
LEAD_TIME_CV = 0.15
DEAD_STOCK_DAYS = 60
WARMUP_START = "2024-12-01"
EVAL_START = "2025-01-01"
EVAL_END = "2025-12-31"
POLICIES = ("moving_average", "seasonal_naive", "forecast")

# Pre-festival peak windows (start of Ramadan to end of Eid ul Fitr; two weeks before Eid ul Adha to its end).
EID_WINDOWS = {
    "Ramadan + Eid ul Fitr 2025": ("2025-03-01", "2025-04-03"),
    "Eid ul Adha 2025 (incl. 2 weeks before)": ("2025-05-14", "2025-06-10"),
}


def _z(mean_daily: np.ndarray) -> np.ndarray:
    """Service level rule shared by every policy (same as InventoryIntelligenceEngine): 95% fast, 90% slow."""
    return np.where(mean_daily >= 3.0, 1.645, 1.282)


def simulate(
    demand: np.ndarray,
    order_up_to: Callable[[int], np.ndarray],
    lead_times: np.ndarray,
    start_idx: int,
    end_idx: int,
    initial_stock: np.ndarray,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    """
    Simulate a periodic-review, lost-sales inventory for all SKUs at once.

    demand: (n_sku, n_days) actual daily demand. `order_up_to(t)` returns the target inventory position per SKU
    for a review on day t (it may only use information up to day t-1). Orders placed on day t arrive at the start
    of day t + actual_lead_time. Returns daily (n_sku, n_days) arrays for days start_idx..end_idx (others zero).
    """
    n_sku, n_days = demand.shape
    rng = np.random.default_rng(seed)  # identical lead-time draws for every policy (common random numbers)
    on_hand = initial_stock.astype(float).copy()
    arrivals = np.zeros((n_sku, n_days + 64))
    on_hand_end = np.zeros((n_sku, n_days))
    sold = np.zeros((n_sku, n_days))
    lost = np.zeros((n_sku, n_days))
    orders = np.zeros((n_sku, n_days))

    for t in range(start_idx, end_idx + 1):
        on_hand += arrivals[:, t]
        noise = rng.standard_normal(n_sku)
        if (t - start_idx) % REVIEW_DAYS == 0:
            pipeline = arrivals[:, t + 1 :].sum(axis=1)
            qty = np.maximum(0.0, np.ceil(order_up_to(t) - on_hand - pipeline))
            actual_lt = np.maximum(1, np.round(lead_times * (1.0 + LEAD_TIME_CV * noise))).astype(int)
            arrivals[np.arange(n_sku), t + actual_lt] += qty
            orders[:, t] = qty
        s = np.minimum(on_hand, demand[:, t])
        sold[:, t] = s
        lost[:, t] = demand[:, t] - s
        on_hand -= s
        on_hand_end[:, t] = on_hand
    return {"on_hand_end": on_hand_end, "sold": sold, "lost": lost, "orders": orders}


def _variance_with_lead_time(var_sum: np.ndarray, mean_daily: np.ndarray, lead_times: np.ndarray) -> np.ndarray:
    return var_sum + (mean_daily ** 2) * (LEAD_TIME_CV * lead_times) ** 2


def moving_average_policy(demand: np.ndarray, lead_times: np.ndarray) -> Callable[[int], np.ndarray]:
    def target(t: int) -> np.ndarray:
        hist = demand[:, t - 28 : t]
        mu, sd = hist.mean(axis=1), hist.std(axis=1)
        cover = REVIEW_DAYS + lead_times
        var = _variance_with_lead_time(cover * sd ** 2, mu, lead_times)
        return mu * cover + _z(mu) * np.sqrt(var)

    return target


def seasonal_naive_policy(demand: np.ndarray, lead_times: np.ndarray) -> Callable[[int], np.ndarray]:
    fallback = moving_average_policy(demand, lead_times)

    def target(t: int) -> np.ndarray:
        if t < 364 + 6:  # under a week of year-ago history (warm-up and the first days of January 2025)
            return fallback(t)
        cover = REVIEW_DAYS + lead_times
        out = np.zeros(demand.shape[0])
        lo = max(t - 28, 364)
        recent_err = demand[:, lo:t] - demand[:, lo - 364 : t - 364]
        sd = recent_err.std(axis=1)
        mu = demand[:, t - 28 : t].mean(axis=1)
        for i in range(demand.shape[0]):
            out[i] = demand[i, t - 364 : t - 364 + cover[i]].sum()
        var = _variance_with_lead_time(cover * sd ** 2, mu, lead_times)
        return out + _z(mu) * np.sqrt(var)

    return target


def forecast_policy(
    forecasts: dict[int, dict[str, np.ndarray]], lead_times: np.ndarray
) -> Callable[[int], np.ndarray]:
    """`forecasts[o]` holds p50 / sigma arrays (n_sku, FORECAST_HORIZON) for days o+1 .. o+H, fitted on data <= o."""
    origins = np.array(sorted(forecasts))

    def target(t: int) -> np.ndarray:
        o = int(origins[origins <= t - 1].max())
        off = t - (o + 1)
        cover = REVIEW_DAYS + lead_times
        out = np.zeros(len(lead_times))
        var = np.zeros(len(lead_times))
        mu = np.zeros(len(lead_times))
        p50, sig = forecasts[o]["p50"], forecasts[o]["sigma"]
        for i, c in enumerate(cover):
            out[i] = p50[i, off : off + c].sum()
            var[i] = (sig[i, off : off + c] ** 2).sum()
            mu[i] = p50[i, off : off + c].mean()
        var = _variance_with_lead_time(var, mu, lead_times)
        return out + _z(mu) * np.sqrt(var)

    return target


def fit_rolling_forecasts(
    sales: pd.DataFrame,
    dates: pd.DatetimeIndex,
    sku_ids: list[str],
    fest_lookup: dict,
    origin_idxs: list[int],
) -> dict[int, dict[str, np.ndarray]]:
    """Refit the probabilistic forecaster at each origin using only sales up to and including that day."""
    out: dict[int, dict[str, np.ndarray]] = {}
    for o in origin_idxs:
        origin = dates[o]
        train = sales[sales["sale_date"] <= origin]
        series = {pid: (g, str(g["category"].iloc[0])) for pid, g in train.groupby("product_id")}
        fut = pd.date_range(origin + pd.Timedelta(days=1), periods=FORECAST_HORIZON, freq="D")
        res = ProbabilisticQuantileForecaster(random_state=42).fit_and_predict_quantiles(series, fut, fest_lookup)
        out[o] = {
            "p50": np.vstack([res[p]["p50"] for p in sku_ids]),
            "sigma": np.vstack([res[p]["sigma_daily"] for p in sku_ids]),
        }
    return out


def summarise(
    sim: dict[str, np.ndarray],
    demand: np.ndarray,
    dates: pd.DatetimeIndex,
    price: np.ndarray,
    unit_cost: np.ndarray,
) -> dict[str, float]:
    ev = (dates >= EVAL_START) & (dates <= EVAL_END)
    d, lost, oh = demand[:, ev], sim["lost"][:, ev], sim["on_hand_end"][:, ev]
    res = {
        "demand_units": float(d.sum()),
        "fill_rate_pct": round(100.0 * (1.0 - lost.sum() / d.sum()), 2),
        "lost_units": float(lost.sum()),
        "lost_revenue_pkr": round(float((lost * price[:, None]).sum()), 0),
        "lost_gross_margin_pkr": round(float((lost * (price - unit_cost)[:, None]).sum()), 0),
        "stockout_sku_days": int((lost > 0).sum()),
        "avg_stock_value_pkr": round(float((oh * unit_cost[:, None]).sum(axis=0).mean()), 0),
        "orders_placed": int((sim["orders"][:, ev] > 0).sum()),
    }
    for name, (a, b) in EID_WINDOWS.items():
        w = (dates >= a) & (dates <= b)
        res[f"lost_units | {name}"] = float(sim["lost"][:, w].sum())
        res[f"stockout_sku_days | {name}"] = int((sim["lost"][:, w] > 0).sum())

    # Dead capital: stock that the next DEAD_STOCK_DAYS of actual demand would not sell (needs a full look-ahead,
    # so measured on days whose 60-day window ends inside the data).
    csum = np.concatenate([np.zeros((demand.shape[0], 1)), np.cumsum(demand, axis=1)], axis=1)
    dead_vals = []
    for t in np.where(ev)[0]:
        if t + DEAD_STOCK_DAYS >= demand.shape[1]:
            break
        future = csum[:, t + 1 + DEAD_STOCK_DAYS] - csum[:, t + 1]
        dead_vals.append(float((np.maximum(0.0, sim["on_hand_end"][:, t] - future) * unit_cost).sum()))
    res["avg_dead_capital_pkr"] = round(float(np.mean(dead_vals)), 0)
    res["dead_capital_days_measured"] = len(dead_vals)
    return res


def run_inventory_backtest(db_path: Path | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    con = duckdb.connect(str(db_path or settings.duckdb_path), read_only=True)
    sales = con.execute(
        "SELECT CAST(sale_date AS TIMESTAMP) AS sale_date, product_id, category, units_sold "
        "FROM daily_sales ORDER BY product_id, sale_date"
    ).df()
    cat = con.execute(
        "SELECT product_id, price_pkr, margin_pct, lead_time_days FROM product_catalogue "
        "WHERE product_id IN (SELECT DISTINCT product_id FROM daily_sales) ORDER BY product_id"
    ).df()
    fest = con.execute("SELECT * FROM festival_calendar").df()
    con.close()

    sku_ids = cat["product_id"].tolist()
    dates = pd.DatetimeIndex(sorted(sales["sale_date"].unique()))
    demand = (
        sales.pivot(index="product_id", columns="sale_date", values="units_sold")
        .reindex(index=sku_ids, columns=dates)
        .fillna(0)
        .to_numpy(dtype=float)
    )
    lead_times = np.maximum(cat["lead_time_days"].to_numpy(dtype=int), 1)
    price = cat["price_pkr"].to_numpy(dtype=float)
    unit_cost = price * (1.0 - cat["margin_pct"].to_numpy(dtype=float))

    start = int(dates.get_loc(pd.Timestamp(WARMUP_START)))
    end = int(dates.get_loc(pd.Timestamp(EVAL_END)))
    initial = np.ceil(demand[:, start - 28 : start].mean(axis=1) * 30.0)

    fest_lookup = _build_date_category_festival_lookup(
        festival_cal_df=fest, all_categories=sorted(sales["category"].astype(str).unique())
    )
    origin_idxs = list(range(start - 1, end, REFIT_EVERY_DAYS))
    forecasts = fit_rolling_forecasts(sales, dates, sku_ids, fest_lookup, origin_idxs)

    targets = {
        "moving_average": moving_average_policy(demand, lead_times),
        "seasonal_naive": seasonal_naive_policy(demand, lead_times),
        "forecast": forecast_policy(forecasts, lead_times),
    }
    rows = []
    for name in POLICIES:
        sim = simulate(demand, targets[name], lead_times, start, end, initial)
        rows.append({"policy": name, **summarise(sim, demand, dates, price, unit_cost)})
    results = pd.DataFrame(rows)

    def change(metric: str, base: str) -> float:
        b = float(results.loc[results.policy == base, metric].iloc[0])
        f = float(results.loc[results.policy == "forecast", metric].iloc[0])
        return round(100.0 * (f - b) / b, 1) if b else float("nan")

    eid_cols = [c for c in results.columns if c.startswith("lost_units | ")]
    comparison: dict[str, object] = {
        "skus": len(sku_ids),
        "forecast_refits": len(origin_idxs),
        "evaluation_period": f"{EVAL_START}..{EVAL_END}",
        "note": "Demand is synthetic; percentages show the effect of the forecast inside this simulation, "
        "not a measured business result.",
    }
    for base in ("moving_average", "seasonal_naive"):
        comparison[f"forecast_vs_{base}_pct_change"] = {
            "lost_units": change("lost_units", base),
            "lost_gross_margin_pkr": change("lost_gross_margin_pkr", base),
            "stockout_sku_days": change("stockout_sku_days", base),
            **{f"lost_units_{c.split(' | ')[1]}": change(c, base) for c in eid_cols},
            "avg_stock_value_pkr": change("avg_stock_value_pkr", base),
            "avg_dead_capital_pkr": change("avg_dead_capital_pkr", base),
        }

    out = settings.reports_dir
    out.mkdir(parents=True, exist_ok=True)
    results.to_csv(out / "day3_inventory_backtest.csv", index=False)
    (out / "day3_inventory_backtest.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    return results, comparison
