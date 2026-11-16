"""
Day 3 — Task 4 & Task 5: Probabilistic Quantile Forecasting (P10/P50/P90) & Inventory Intelligence.

Implements:
1. `ProbabilisticQuantileForecaster`:
   - P10 (downside), P50 (median expected) and P90 (surge upper bound) daily demand over 30 days:
     P50 from the global LightGBM forecaster, P10 / P90 from split conformal prediction (the model's own errors on
     the last 28 known days, grouped by forecast size and horizon). Non-crossing by construction
     (0 <= P10 <= P50 <= P90). Coverage is measured on the holdout, not assumed.
2. `InventoryIntelligenceEngine`:
   - Computes Safety Stock (SS), Reorder Point (ROP), Days of Inventory Remaining (DOI_P50 & DOI_P90),
     Recommended Order Quantity (ROQ), and Working Capital Tied Up (PKR) across all 300 tracked SKUs.
   - Classifies each SKU into actionable alert tiers:
     * `CRITICAL_STOCKOUT_RISK` (DOI_P50 <= 14 days or stock_qty <= ROP)
     * `FESTIVAL_SURGE_WATCH` (DOI_P50 > 14 days but DOI_P90 <= 18 days ahead of festival surge)
     * `OVERSTOCK_DEAD_CAPITAL` (DOI_P50 > 90 days — e.g. Winter Jackets sitting in warm months)
     * `HEALTHY_STOCK` (14 < DOI_P50 <= 90 days and stock_qty > ROP)
   - Saves `sku_forecasts_30d` and `inventory_alerts` tables into `shopkaro.duckdb` and exports CSV + Figure 12.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.data.synthesizer import INVENTORY_SNAPSHOT_DATE
from shopkaro.forecasting.festivals import FestivalCalendar
from shopkaro.forecasting.models import GlobalLGBMForecaster


@dataclass
class ProbabilisticEvalMetrics:
    """Calibration and accuracy summary for Task 4 P10/P50/P90 probabilistic forecasts."""

    evaluated_skus: int
    horizon_days: int
    p50_wape_pct: float
    empirical_coverage_80pct: float
    mean_interval_width_units: float
    quantile_crossing_count: int
    pinball_loss_p10: float
    pinball_loss_p50: float
    pinball_loss_p90: float
    # Calibration check from the brief: does P90 cover reality ~90% of the time (and P10 sit below it ~90%)?
    p90_upper_coverage_pct: float = float("nan")
    p10_lower_coverage_pct: float = float("nan")


@dataclass
class InventoryAlertSummary:
    """Operational summary of Task 5 Inventory Intelligence across 300 tracked SKUs."""

    total_tracked_skus: int
    critical_stockout_count: int
    festival_surge_watch_count: int
    overstock_dead_capital_count: int
    healthy_stock_count: int
    total_recommended_po_units: int
    total_po_procurement_value_pkr: float
    overstock_capital_at_risk_pkr: float


def _pinball_loss(y_true: np.ndarray, y_q: np.ndarray, alpha: float) -> float:
    """Compute quantile pinball (check) loss at quantile level `alpha` in (0, 1)."""
    diff = y_true - y_q
    loss = np.where(diff >= 0.0, alpha * diff, (alpha - 1.0) * diff)
    return round(float(np.mean(loss)), 4)


class ProbabilisticQuantileForecaster:
    """
    Task 4: Probabilistic Demand Forecaster producing P10, P50, and P90 trajectories.

    P50 comes from the global LightGBM point forecaster. P10 / P90 come from split conformal prediction:
    1. Calibration: refit the same forecaster on data up to `CALIBRATION_DAYS` before the last known day, forecast
       those days (which are known), and record the errors (actual - forecast). The same is done for the same
       28 days one year earlier, so the errors of the coming season (e.g. Eid) are represented too.
    2. The errors are grouped by forecast size (quintiles of the calibration forecast) and horizon (1-7, 8-14,
       15+ days), because big forecasts and far-ahead days miss by more. The 10th and 90th percentile of each group's
       errors are added to P50.
    No noise distribution is assumed: the band width comes from how wrong the model actually was on recent data.
    (The earlier version assumed variance = mu + 0.1 mu^2, which is the data generator's own noise formula.)
    """

    CALIBRATION_DAYS = 28
    N_SIZE_BINS = 5
    HORIZON_BINS = (7, 14)  # edges -> groups 1-7, 8-14, 15+
    Z_80 = 1.2816  # converts the P10-P90 width into a daily sigma for safety-stock maths

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.point_forecaster = GlobalLGBMForecaster(random_state=random_state)

    def _horizon_group(self, h: np.ndarray) -> np.ndarray:
        return np.digitize(h, np.asarray(self.HORIZON_BINS) + 0.5)

    def _calibrate(
        self,
        series_dict: dict[str, tuple[pd.DataFrame, str]],
        calendar: FestivalCalendar,
    ) -> tuple[np.ndarray, dict[tuple[int, int], tuple[float, float]], tuple[float, float]]:
        """
        Errors of forecasts whose outcome is already known -> per-group (q10, q90) of actual - forecast.
        Two calibration windows, each a real forecast made with data up to its start only:
        - the last CALIBRATION_DAYS days (recent behaviour of the model), and
        - the same CALIBRATION_DAYS days one year earlier (same season: if a festival is coming, last year's window
          usually contained it too, so festival-sized errors are represented).
        """
        c = self.CALIBRATION_DAYS
        last_day = max(pd.Timestamp(pd.to_datetime(df["sale_date"]).max()) for df, _ in series_dict.values())
        p_parts, e_parts, h_parts = [], [], []
        for cut in (last_day - pd.Timedelta(days=c), last_day - pd.Timedelta(days=364)):
            cal_dates = pd.date_range(cut + pd.Timedelta(days=1), periods=c, freq="D")
            cal_train: dict[str, tuple[pd.DataFrame, str]] = {}
            cal_actual: dict[str, np.ndarray] = {}
            for key, (df, cat) in series_dict.items():
                sd = pd.to_datetime(df["sale_date"])
                train = df[sd <= cut]
                actual = df[(sd > cut) & (sd <= cal_dates[-1])]
                if len(train) < 60 or len(actual) < c:
                    continue
                cal_train[key] = (train, cat)
                cal_actual[key] = actual.sort_values("sale_date")["units_sold"].to_numpy(dtype=np.float64)
            if not cal_train:
                continue
            calibrator = GlobalLGBMForecaster(random_state=self.random_state)
            preds = calibrator.fit_and_predict_panel(cal_train, cal_dates, calendar)
            p_parts.append(np.concatenate([preds[k] for k in cal_train]))
            e_parts.append(np.concatenate([cal_actual[k] - preds[k] for k in cal_train]))
            h_parts.append(np.tile(np.arange(1, c + 1), len(cal_train)))
        if not p_parts:
            return np.array([np.inf]), {}, (0.0, 0.0)
        p, err, h = np.concatenate(p_parts), np.concatenate(e_parts), np.concatenate(h_parts)

        size_edges = np.quantile(p, np.linspace(0, 1, self.N_SIZE_BINS + 1)[1:-1])
        size_g = np.digitize(p, size_edges)
        hor_g = self._horizon_group(h)

        def q(e: np.ndarray) -> tuple[float, float]:
            # Finite-sample conformal levels: ceil((n + 1) * 0.9) / n and its mirror
            n = len(e)
            hi = min(np.ceil((n + 1) * 0.9) / n, 1.0)
            lo = max(1.0 - hi, 0.0)
            return float(np.quantile(e, lo, method="lower")), float(np.quantile(e, hi, method="higher"))

        table = {}
        for sg in range(self.N_SIZE_BINS):
            for hg in range(len(self.HORIZON_BINS) + 1):
                m = (size_g == sg) & (hor_g == hg)
                if m.sum() >= 30:
                    table[(sg, hg)] = q(err[m])
                elif (size_g == sg).sum() >= 30:
                    table[(sg, hg)] = q(err[size_g == sg])
        return size_edges, table, q(err)

    def fit_and_predict_quantiles(
        self,
        series_dict: dict[str, tuple[pd.DataFrame, str]],
        future_dates: pd.DatetimeIndex,
        calendar: FestivalCalendar,
    ) -> dict[str, dict[str, np.ndarray]]:
        """
        Fit on `series_dict` and return
        `series_id -> {"p10", "p50", "p90", "sigma_daily": arrays over future_dates, "hist_std": float}`.
        """
        p50_map = self.point_forecaster.fit_and_predict_panel(
            series_dict=series_dict,
            future_dates=future_dates,
            calendar=calendar,
        )
        size_edges, table, overall = self._calibrate(series_dict, calendar)

        results: dict[str, dict[str, np.ndarray]] = {}
        for s_key, (train_df, _) in series_dict.items():
            p50 = np.maximum(0.0, p50_map[s_key])
            last_day = pd.Timestamp(pd.to_datetime(train_df["sale_date"]).max())
            h = np.asarray((pd.DatetimeIndex(future_dates) - last_day).days, dtype=np.int64)
            size_g = np.digitize(p50, size_edges)
            hor_g = self._horizon_group(h)
            q10 = np.array([table.get((s, g), overall)[0] for s, g in zip(size_g, hor_g)])
            q90 = np.array([table.get((s, g), overall)[1] for s, g in zip(size_g, hor_g)])

            # Non-crossing by construction: 0 <= P10 <= P50 <= P90
            p10 = np.clip(p50 + q10, 0.0, p50)
            p90 = np.maximum(p50 + q90, p50)
            sigma_t = (p90 - p10) / (2.0 * self.Z_80)

            y_hist = train_df["units_sold"].to_numpy(dtype=np.float64)
            hist_std = float(np.std(y_hist[-28:])) if len(y_hist) >= 7 else 1.0

            results[s_key] = {
                "p10": np.round(p10, 2),
                "p50": np.round(p50, 2),
                "p90": np.round(p90, 2),
                "sigma_daily": np.round(sigma_t, 3),
                "hist_std": round(hist_std, 3),
            }

        return results


class InventoryIntelligenceEngine:
    """
    Task 5: Inventory Optimization, Safety Stock, Reorder Point & Automated Alert System.

    Formulas:
    - Safety Stock: SS_i = z_alpha * sqrt( L_i * sigma_{D,i}^2 + D_bar_i^2 * sigma_{L,i}^2 )
      where z_{0.95} = 1.645, L_i = supplier lead_time_days, sigma_{L,i} = 0.15 * L_i.
    - Reorder Point: ROP_i = D_bar_i * L_i + SS_i
    - Days of Inventory: DOI_P50 = stock_qty / max(D_bar_P50, 0.05)
    """

    def __init__(
        self,
        service_level_z_fast: float = 1.645,  # 95% service level for Fast/Steady movers
        service_level_z_slow: float = 1.282,  # 90% service level for Slow movers
        lead_time_cv: float = 0.15,  # 15% supplier lead-time variability
        stockout_alert_days: float = 14.0,
        overstock_alert_days: float = 90.0,
        target_cover_days: float = 30.0,
    ) -> None:
        self.service_level_z_fast = service_level_z_fast
        self.service_level_z_slow = service_level_z_slow
        self.lead_time_cv = lead_time_cv
        self.stockout_alert_days = stockout_alert_days
        self.overstock_alert_days = overstock_alert_days
        self.target_cover_days = target_cover_days

    def compute_inventory_plan(
        self,
        catalogue_df: pd.DataFrame,
        quantile_forecasts: dict[str, dict[str, np.ndarray]],
        future_dates: pd.DatetimeIndex,
    ) -> tuple[pd.DataFrame, pd.DataFrame, InventoryAlertSummary]:
        """
        Build:
        1. `forecast_30d_df`: Daily P10/P50/P90 table for all forecasted SKUs (`300 x 30 = 9,000` rows).
        2. `inventory_alerts_df`: Per-SKU Safety Stock, ROP, DOI, Alert Status, and Recommended Action.
        3. `InventoryAlertSummary`: Executive KPI summary.
        """
        cat_lookup = {
            str(r["product_id"]): r for r in catalogue_df.to_dict("records")
        }

        daily_rows: list[dict[str, object]] = []
        alert_rows: list[dict[str, object]] = []

        for pid, q_dict in quantile_forecasts.items():
            meta = cat_lookup.get(pid, {})
            title = str(meta.get("title", pid))
            category = str(meta.get("category", "General"))
            brand = str(meta.get("brand", "ShopKaro"))
            price_pkr = float(meta.get("price_pkr", 1000.0))
            margin_pct = float(meta.get("margin_pct", 0.30))
            unit_cost_pkr = price_pkr * (1.0 - margin_pct)
            stock_qty = int(meta.get("stock_qty", 0))
            lead_time_days = max(int(meta.get("lead_time_days", 5)), 1)

            p10_vec = q_dict["p10"]
            p50_vec = q_dict["p50"]
            p90_vec = q_dict["p90"]
            sigma_vec = q_dict["sigma_daily"]

            for d_idx, dt in enumerate(future_dates):
                daily_rows.append(
                    {
                        "product_id": pid,
                        "forecast_date": dt.strftime("%Y-%m-%d"),
                        "horizon_day": d_idx + 1,
                        "category": category,
                        "brand": brand,
                        "p10_units": float(p10_vec[d_idx]),
                        "p50_units": float(p50_vec[d_idx]),
                        "p90_units": float(p90_vec[d_idx]),
                    }
                )

            # 14-day and 30-day demand aggregates
            d_bar_p50 = float(np.mean(p50_vec[:14]))
            d_bar_p90 = float(np.mean(p90_vec[:14]))
            demand_14d_p50 = float(np.sum(p50_vec[:14]))
            demand_30d_p50 = float(np.sum(p50_vec[:30]))
            demand_30d_p90 = float(np.sum(p90_vec[:30]))

            # Demand uncertainty sigma_D from P90-P50 spread and historical std
            sigma_d_forecast = float(np.mean(sigma_vec[:14]))
            sigma_d = max(sigma_d_forecast, float(q_dict.get("hist_std", 1.0)) * 0.5, 0.2)

            # Lead time standard deviation sigma_L
            sigma_l = self.lead_time_cv * float(lead_time_days)

            z_val = (
                self.service_level_z_fast if d_bar_p50 >= 3.0 else self.service_level_z_slow
            )
            safety_stock = float(
                np.ceil(
                    z_val
                    * np.sqrt(
                        float(lead_time_days) * (sigma_d ** 2)
                        + (d_bar_p50 ** 2) * (sigma_l ** 2)
                    )
                )
            )
            lead_time_demand = float(np.ceil(d_bar_p50 * float(lead_time_days)))
            reorder_point = lead_time_demand + safety_stock

            doi_p50 = round(float(stock_qty) / max(d_bar_p50, 0.08), 1)
            doi_p90 = round(float(stock_qty) / max(d_bar_p90, 0.08), 1)

            # Classify alert status & compute Recommended Order Quantity (ROQ)
            if stock_qty <= reorder_point or doi_p50 <= self.stockout_alert_days:
                alert_status = "CRITICAL_STOCKOUT_RISK"
                target_stock = float(np.ceil(demand_30d_p50 + safety_stock))
                roq = max(int(target_stock - stock_qty), int(lead_time_demand + safety_stock))
                action = (
                    f"URGENT REORDER: Stock ({stock_qty} units, {doi_p50}d left) is below ROP "
                    f"({int(reorder_point)} units, Lead Time={lead_time_days}d). "
                    f"Place PO for {roq} units immediately to prevent stock-out."
                )
            elif doi_p90 <= 18.0:
                alert_status = "FESTIVAL_SURGE_WATCH"
                target_stock = float(np.ceil(demand_30d_p90 + safety_stock))
                roq = max(int(target_stock - stock_qty), 0)
                action = (
                    f"PRE-FESTIVAL BUFFER: P50 cover is {doi_p50}d, but P90 surge cover is only "
                    f"{doi_p90}d. Pre-order {roq} buffer units ahead of peak demand."
                )
            elif doi_p50 > self.overstock_alert_days and stock_qty >= 25:
                alert_status = "OVERSTOCK_DEAD_CAPITAL"
                roq = 0
                excess_units = max(int(stock_qty - np.ceil(demand_30d_p50 * 2.0)), 10)
                excess_pkr = excess_units * unit_cost_pkr
                action = (
                    f"OVERSTOCK MARKDOWN: {stock_qty} units in warehouse ({doi_p50:.0f} days of cover, "
                    f"PKR {excess_pkr:,.0f} working capital tied up). Freeze reorders & run 20% OFF clearance promo."
                )
            else:
                alert_status = "HEALTHY_STOCK"
                roq = 0
                action = (
                    f"HEALTHY: {stock_qty} units covers {doi_p50}d expected demand "
                    f"(ROP={int(reorder_point)} units). Next review in 7 days."
                )

            alert_rows.append(
                {
                    "product_id": pid,
                    "title": title,
                    "category": category,
                    "brand": brand,
                    "price_pkr": price_pkr,
                    "unit_cost_pkr": round(unit_cost_pkr, 2),
                    "current_stock_qty": stock_qty,
                    "lead_time_days": lead_time_days,
                    "daily_demand_p50": round(d_bar_p50, 2),
                    "daily_demand_p90": round(d_bar_p90, 2),
                    "forecast_14d_p50": round(demand_14d_p50, 1),
                    "forecast_30d_p50": round(demand_30d_p50, 1),
                    "forecast_30d_p90": round(demand_30d_p90, 1),
                    "safety_stock_units": int(safety_stock),
                    "reorder_point_units": int(reorder_point),
                    "days_of_inventory_p50": doi_p50,
                    "days_of_inventory_p90": doi_p90,
                    "recommended_order_qty": int(roq),
                    "po_procurement_cost_pkr": round(float(roq) * unit_cost_pkr, 2),
                    "inventory_value_pkr": round(float(stock_qty) * unit_cost_pkr, 2),
                    "alert_status": alert_status,
                    "recommended_action": action,
                }
            )

        forecast_30d_df = pd.DataFrame(daily_rows)
        alerts_df = pd.DataFrame(alert_rows)

        # Sort alerts: CRITICAL_STOCKOUT_RISK first (lowest DOI), then FESTIVAL_SURGE_WATCH, then OVERSTOCK
        priority_map = {
            "CRITICAL_STOCKOUT_RISK": 1,
            "FESTIVAL_SURGE_WATCH": 2,
            "OVERSTOCK_DEAD_CAPITAL": 3,
            "HEALTHY_STOCK": 4,
        }
        alerts_df["priority_rank"] = alerts_df["alert_status"].map(priority_map)
        alerts_df = (
            alerts_df.sort_values(["priority_rank", "days_of_inventory_p50"])
            .drop(columns=["priority_rank"])
            .reset_index(drop=True)
        )

        n_crit = int((alerts_df["alert_status"] == "CRITICAL_STOCKOUT_RISK").sum())
        n_fest = int((alerts_df["alert_status"] == "FESTIVAL_SURGE_WATCH").sum())
        n_over = int((alerts_df["alert_status"] == "OVERSTOCK_DEAD_CAPITAL").sum())
        n_ok = int((alerts_df["alert_status"] == "HEALTHY_STOCK").sum())

        overstock_sub = alerts_df[alerts_df["alert_status"] == "OVERSTOCK_DEAD_CAPITAL"]
        summary = InventoryAlertSummary(
            total_tracked_skus=len(alerts_df),
            critical_stockout_count=n_crit,
            festival_surge_watch_count=n_fest,
            overstock_dead_capital_count=n_over,
            healthy_stock_count=n_ok,
            total_recommended_po_units=int(alerts_df["recommended_order_qty"].sum()),
            total_po_procurement_value_pkr=round(
                float(alerts_df["po_procurement_cost_pkr"].sum()), 2
            ),
            overstock_capital_at_risk_pkr=round(
                float(overstock_sub["inventory_value_pkr"].sum()), 2
            ),
        )
        return forecast_30d_df, alerts_df, summary


def build_prefestival_plan(
    forecast_30d_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    festival_cal_df: pd.DataFrame,
    origin_dt: pd.Timestamp,
    history_df: pd.DataFrame,
    top_n: int = 100,
) -> pd.DataFrame:
    """
    Pre-festival stocking plan for the top `top_n` products (by sales in the 28 days before the plan date) for
    the next festival that starts after the plan date and ends inside the 30-day forecast horizon:
        units needed = P90 demand from tomorrow to the festival's last day + safety stock
        order qty    = max(0, units needed - current stock)
        order by     = festival start - supplier lead time (late if that date has already passed)
    """
    horizon_end = pd.to_datetime(forecast_30d_df["forecast_date"]).max()
    fests = festival_cal_df.assign(
        start=pd.to_datetime(festival_cal_df["start_date"]), end=pd.to_datetime(festival_cal_df["end_date"])
    )
    upcoming = fests[(fests["end"] > origin_dt) & (fests["end"] <= horizon_end)].sort_values("end")
    if upcoming.empty:
        return pd.DataFrame()
    eid = upcoming[upcoming["festival_name"].str.contains("Eid")]
    fest = eid.iloc[0] if not eid.empty else upcoming.iloc[0]

    recent = history_df[history_df["sale_date"] > origin_dt - pd.Timedelta(days=28)]
    top_ids = recent.groupby("product_id")["units_sold"].sum().sort_values(ascending=False).head(top_n).index
    fc = forecast_30d_df[pd.to_datetime(forecast_30d_df["forecast_date"]) <= fest["end"]]
    need_p90 = fc.groupby("product_id")["p90_units"].sum()
    need_p50 = fc.groupby("product_id")["p50_units"].sum()

    rows = []
    a = alerts_df.set_index("product_id")
    for rank, pid in enumerate(top_ids, start=1):
        if pid not in a.index:
            continue
        r = a.loc[pid]
        needed = float(need_p90.get(pid, 0.0)) + float(r["safety_stock_units"])
        order_qty = max(0, int(np.ceil(needed - float(r["current_stock_qty"]))))
        order_by = fest["start"] - pd.Timedelta(days=int(r["lead_time_days"]))
        rows.append(
            {
                "rank": rank,
                "product_id": pid,
                "title": r["title"],
                "category": r["category"],
                "festival": fest["festival_name"],
                "festival_start": fest["start"].date().isoformat(),
                "festival_end": fest["end"].date().isoformat(),
                "current_stock_units": int(r["current_stock_qty"]),
                "demand_to_festival_end_p50": round(float(need_p50.get(pid, 0.0)), 0),
                "demand_to_festival_end_p90": round(float(need_p90.get(pid, 0.0)), 0),
                "safety_stock_units": int(r["safety_stock_units"]),
                "order_qty_units": order_qty,
                "order_value_pkr": round(order_qty * float(r["unit_cost_pkr"]), 0),
                "lead_time_days": int(r["lead_time_days"]),
                "order_by": order_by.date().isoformat(),
                "status": "no order needed" if order_qty == 0 else (
                    "LATE: arrives after festival starts, expedite" if order_by < origin_dt else "order now"
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_probabilistic_and_inventory_chart(
    daily_sales_df: pd.DataFrame,
    forecast_30d_df: pd.DataFrame,
    alerts_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Generate Figure 12 (`12_probabilistic_forecast_and_inventory_alerts.png`):
    1. P10 / P50 / P90 Probabilistic Fan Chart for Hero Lawn SKU (`SK-00001`: Sapphire Eid Lawn)
    2. P10 / P50 / P90 Probabilistic Fan Chart for Hero Smartphone SKU (`SK-00013`: Samsung Galaxy A55)
    3. Inventory Alert Tier Breakdown across 300 Tracked SKUs
    4. Current Stock vs Reorder Point (ROP) & Safety Stock for Top Critical Stock-Out SKUs
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle(
        "ShopKaro AI — Day 3 Tasks 4 & 5: Probabilistic P10/P50/P90 Forecasts & Inventory Intelligence",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    for ax_idx, (hero_pid, hero_label) in enumerate(
        [
            ("SK-00001", "1. SK-00001: Sapphire 3-Piece Eid Lawn Suit (P10 / P50 / P90 Fan Chart)"),
            ("SK-00013", "2. SK-00013: Samsung Galaxy A55 5G (P10 / P50 / P90 Fan Chart)"),
        ]
    ):
        ax = axes[0, ax_idx]
        hist_sub = (
            daily_sales_df[daily_sales_df["product_id"] == hero_pid]
            .sort_values("sale_date")
            .tail(45)
        )
        fut_sub = forecast_30d_df[forecast_30d_df["product_id"] == hero_pid].sort_values(
            "forecast_date"
        )

        h_dates = pd.to_datetime(hist_sub["sale_date"])
        f_dates = pd.to_datetime(fut_sub["forecast_date"])

        ax.plot(
            h_dates,
            hist_sub["units_sold"],
            color="#1f77b4",
            linewidth=1.8,
            label="Historical Actuals (Last 45d)",
        )
        ax.plot(
            f_dates,
            fut_sub["p50_units"],
            color="#d62728",
            linewidth=2.2,
            label="P50 Forecast (Expected)",
        )
        ax.fill_between(
            f_dates,
            fut_sub["p10_units"],
            fut_sub["p90_units"],
            color="#ff9896",
            alpha=0.38,
            label="P10–P90 Prediction Interval (80%)",
        )
        ax.axvline(h_dates.iloc[-1], color="black", linestyle="--", linewidth=1.0)
        ax.set_title(hero_label, fontweight="bold")
        ax.set_ylabel("Daily Units")
        ax.legend(loc="upper left", fontsize=8.5)
        ax.tick_params(axis="x", rotation=20)

    # Panel 3: Alert Status Distribution across 300 SKUs
    ax3 = axes[1, 0]
    status_order = [
        "CRITICAL_STOCKOUT_RISK",
        "FESTIVAL_SURGE_WATCH",
        "OVERSTOCK_DEAD_CAPITAL",
        "HEALTHY_STOCK",
    ]
    counts = alerts_df["alert_status"].value_counts().reindex(status_order, fill_value=0)
    palette = ["#d62728", "#ff7f0e", "#9467bd", "#2ca02c"]
    bars = ax3.barh(status_order, counts.values, color=palette, height=0.55)
    ax3.invert_yaxis()
    ax3.set_title("3. Inventory Alert Distribution (300 Tracked SKUs)", fontweight="bold")
    ax3.set_xlabel("Number of SKUs")
    for b in bars:
        ax3.text(
            b.get_width() + 2,
            b.get_y() + b.get_height() / 2,
            f"{int(b.get_width())} SKUs",
            va="center",
            fontsize=9.5,
            fontweight="bold",
        )
    ax3.set_xlim(0, max(counts.values) * 1.18)

    # Panel 4: Current Stock vs Reorder Point (ROP) for Top 8 Critical Stock-Out SKUs
    ax4 = axes[1, 1]
    crit_top = (
        alerts_df[
            (alerts_df["alert_status"] == "CRITICAL_STOCKOUT_RISK")
            & (alerts_df["current_stock_qty"] > 0)
        ]
        .head(8)
        .iloc[::-1]
    )
    y_p = np.arange(len(crit_top))
    w = 0.36
    ax4.barh(
        y_p - w / 2,
        crit_top["current_stock_qty"],
        height=w,
        color="#1f77b4",
        label="Current Warehouse Stock",
    )
    ax4.barh(
        y_p + w / 2,
        crit_top["reorder_point_units"],
        height=w,
        color="#d62728",
        label="Reorder Point (ROP = Lead Demand + SS)",
    )
    ax4.set_yticks(y_p)
    ax4.set_yticklabels(
        [f"{r['product_id']} ({r['brand'][:10]})" for _, r in crit_top.iterrows()],
        fontsize=9,
    )
    ax4.set_xlabel("Units")
    ax4.set_title("4. Stock vs Reorder Point (Top In-Stock Critical SKUs)", fontweight="bold")
    ax4.legend(loc="lower right", fontsize=8.5)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def run_day3_task4_task5_probabilistic_and_inventory(
    db_path: Path | None = None,
    eval_origin_date: str = INVENTORY_SNAPSHOT_DATE,
    horizon_days: int = 30,
) -> tuple[
    ProbabilisticEvalMetrics,
    InventoryAlertSummary,
    pd.DataFrame,
    pd.DataFrame,
    Path,
]:
    """
    Execute Day 3 — Tasks 4 & 5:
    1. Evaluate probabilistic P10/P50/P90 calibration on the 30-day holdout after `eval_origin_date`
       (`2025-03-15`, capturing Pre-Eid, Chaand Raat & Spring transition across all 300 SKUs).
    2. Compute Safety Stock, Reorder Point, Days of Inventory, and Alert Tiers across all 300 SKUs.
    3. Persist `sku_forecasts_30d` and `inventory_alerts` into `shopkaro.duckdb` and save CSV + Figure 12.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db))

    daily_sales_df = con.execute(
        """
        SELECT
            CAST(sale_date AS TIMESTAMP) AS sale_date,
            product_id,
            category,
            brand,
            velocity_tier,
            units_sold,
            unit_price_pkr,
            revenue_pkr,
            festival_name,
            is_festival_day
        FROM daily_sales
        ORDER BY product_id, sale_date;
        """
    ).df()

    catalogue_df = con.execute(
        """
        SELECT
            product_id,
            title,
            category,
            sub_category,
            brand,
            price_pkr,
            margin_pct,
            stock_qty,
            in_stock,
            lead_time_days
        FROM product_catalogue
        WHERE product_id IN (SELECT DISTINCT product_id FROM daily_sales)
        ORDER BY product_id;
        """
    ).df()

    festival_cal_df = con.execute("SELECT * FROM festival_calendar").df()

    calendar = FestivalCalendar(festival_cal_df)  # festival dates and names only

    origin_dt = pd.Timestamp(eval_origin_date)
    future_end = origin_dt + pd.Timedelta(days=horizon_days)
    future_dates = pd.date_range(
        start=origin_dt + pd.Timedelta(days=1),
        end=future_end,
        freq="D",
    )

    train_slice = daily_sales_df[daily_sales_df["sale_date"] <= origin_dt]
    test_slice = daily_sales_df[
        (daily_sales_df["sale_date"] > origin_dt) & (daily_sales_df["sale_date"] <= future_end)
    ]

    series_dict: dict[str, tuple[pd.DataFrame, str]] = {}
    actuals_dict: dict[str, np.ndarray] = {}

    for pid, grp in train_slice.groupby("product_id"):
        pid_str = str(pid)
        cat = str(grp["category"].iloc[0])
        series_dict[pid_str] = (grp.sort_values("sale_date"), cat)

    for pid, grp in test_slice.groupby("product_id"):
        actuals_dict[str(pid)] = grp.sort_values("sale_date")["units_sold"].to_numpy(
            dtype=np.float64
        )

    # 1. Fit & Predict P10 / P50 / P90 across all 300 SKUs
    prob_forecaster = ProbabilisticQuantileForecaster(random_state=42)
    quantile_forecasts = prob_forecaster.fit_and_predict_quantiles(
        series_dict=series_dict,
        future_dates=future_dates,
        calendar=calendar,
    )

    # Evaluate calibration & quantile metrics on the 30-day holdout
    y_true_all: list[np.ndarray] = []
    p10_all: list[np.ndarray] = []
    p50_all: list[np.ndarray] = []
    p90_all: list[np.ndarray] = []
    crossings = 0

    for pid, q_res in quantile_forecasts.items():
        if pid not in actuals_dict:
            continue
        yt = actuals_dict[pid]
        q10 = q_res["p10"][: len(yt)]
        q50 = q_res["p50"][: len(yt)]
        q90 = q_res["p90"][: len(yt)]

        crossings += int(np.sum((q10 > q50) | (q50 > q90)))
        y_true_all.append(yt)
        p10_all.append(q10)
        p50_all.append(q50)
        p90_all.append(q90)

    yt_vec = np.concatenate(y_true_all)
    q10_vec = np.concatenate(p10_all)
    q50_vec = np.concatenate(p50_all)
    q90_vec = np.concatenate(p90_all)

    in_band = (yt_vec >= q10_vec) & (yt_vec <= q90_vec)
    coverage_80 = float(np.mean(in_band) * 100.0)
    mean_width = float(np.mean(q90_vec - q10_vec))
    p50_wape = float(np.sum(np.abs(yt_vec - q50_vec)) / max(float(np.sum(yt_vec)), 1.0) * 100.0)

    prob_metrics = ProbabilisticEvalMetrics(
        evaluated_skus=len(quantile_forecasts),
        horizon_days=horizon_days,
        p50_wape_pct=round(p50_wape, 3),
        empirical_coverage_80pct=round(coverage_80, 2),
        mean_interval_width_units=round(mean_width, 2),
        quantile_crossing_count=crossings,
        pinball_loss_p10=_pinball_loss(yt_vec, q10_vec, 0.10),
        pinball_loss_p50=_pinball_loss(yt_vec, q50_vec, 0.50),
        pinball_loss_p90=_pinball_loss(yt_vec, q90_vec, 0.90),
        p90_upper_coverage_pct=round(float(np.mean(yt_vec <= q90_vec) * 100.0), 2),
        p10_lower_coverage_pct=round(float(np.mean(yt_vec >= q10_vec) * 100.0), 2),
    )

    # 2. Compute Inventory Intelligence & Alerts across all 300 SKUs
    inv_engine = InventoryIntelligenceEngine()
    forecast_30d_df, alerts_df, inv_summary = inv_engine.compute_inventory_plan(
        catalogue_df=catalogue_df,
        quantile_forecasts=quantile_forecasts,
        future_dates=future_dates,
    )

    # 3. Persist tables into DuckDB for Day 5 FastAPI & Streamlit
    con.register("tmp_forecast_30d", forecast_30d_df)
    con.execute("CREATE OR REPLACE TABLE sku_forecasts_30d AS SELECT * FROM tmp_forecast_30d;")
    con.unregister("tmp_forecast_30d")

    con.register("tmp_inv_alerts", alerts_df)
    con.execute("CREATE OR REPLACE TABLE inventory_alerts AS SELECT * FROM tmp_inv_alerts;")
    con.unregister("tmp_inv_alerts")
    con.close()

    # Export CSV & Figure 12
    csv_out = settings.reports_dir / "day3_inventory_alerts.csv"
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    alerts_df.to_csv(csv_out, index=False)
    build_prefestival_plan(forecast_30d_df, alerts_df, festival_cal_df, origin_dt, train_slice).to_csv(
        settings.reports_dir / "day3_prefestival_plan_top100.csv", index=False
    )

    fig_out = settings.figures_dir / "12_probabilistic_forecast_and_inventory_alerts.png"
    plot_probabilistic_and_inventory_chart(
        daily_sales_df=train_slice,
        forecast_30d_df=forecast_30d_df,
        alerts_df=alerts_df,
        output_path=fig_out,
    )

    return prob_metrics, inv_summary, forecast_30d_df, alerts_df, fig_out
