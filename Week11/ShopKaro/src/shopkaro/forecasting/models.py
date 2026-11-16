"""
Day 3 — Task 2 & Task 3: Multi-Model Forecasting Pipeline & 4-Fold Rolling-Origin Backtesting.

Implements 5 Progressive Forecasting Models:
1. `NaiveForecaster`: Last observed value (random-walk baseline).
2. `SeasonalNaive7DForecaster`: Same day last week (s = 7 weekly cycle baseline).
3. `HoltWintersETSForecaster`: Classical additive Holt-Winters Exponential Smoothing / SARIMA(0,1,1)(0,1,1)_7.
4. `ProphetFourierHolidayForecaster`: Prophet (trend + weekly + yearly Fourier) with one regressor per festival,
   built from festival DATES only; Prophet learns each festival's effect (ridge fallback without the library).
5. `GlobalLGBMForecaster`: one global LightGBM model across all series, direct multi-horizon, with lag, rolling,
   calendar and festival features; festival uplift is learned from each series' own past sales.
6. `CrostonSBAForecaster` / 7. `TSBForecaster`: intermittent-demand rates (checked for slow movers; not adopted).
8. Oracle (comparison only, `forecasting/oracle.py`): the earlier "LightGBM" that rebuilt the data generator's own
   formula and true festival multipliers. Reported as an upper bound a real retailer could not reach.

Leakage rule: models 1-7 see only past sales and the festival calendar's names / types / dates
(`forecasting/festivals.py`). They never read `demand_multiplier`, `boost_categories` or any constant of the data
generator; `tests/test_forecast_leakage.py` enforces this.

Evaluates all 7 models via 4-Fold Expanding-Window Rolling-Origin Backtesting across
7-day, 14-day, and 30-day horizons using WAPE (primary), MAE, RMSE, and sMAPE.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from shopkaro.config.settings import settings
from shopkaro.forecasting.festivals import FestivalCalendar, festival_uplift_features
from shopkaro.forecasting.timeseries_analysis import build_three_level_timeseries

# 4 Rolling-Origin Cutoff Dates in 2025 covering distinct Pakistani retail seasons:
# Fold 1: Ramadan & Chaand Raat / Eid ul Fitr 2025
# Fold 2: Eid ul Adha 2025
# Fold 3: Azadi Sale & Back-to-School 2025
# Fold 4: 11.11 Mega Sale, Blessed Friday & Winter Peak 2025
BACKTEST_FOLD_CUTOFFS: list[tuple[str, str]] = [
    ("Fold_1_Eid_ul_Fitr", "2025-03-15"),
    ("Fold_2_Eid_ul_Adha", "2025-05-25"),
    ("Fold_3_Azadi_BackToSchool", "2025-08-08"),
    ("Fold_4_11_11_Winter", "2025-11-05"),
]

HORIZONS: list[int] = [7, 14, 30]
BREAKDOWN_HORIZON = 14  # festival / velocity breakdowns are reported at the 14-day horizon (the stock-out alert window)


@dataclass
class BacktestSummaryRow:
    """Aggregated 4-fold backtest accuracy row for a model at a given hierarchy and horizon."""

    hierarchy_level: str
    model_name: str
    horizon_days: int
    n_folds: int
    n_series: int
    wape_pct: float
    mae: float
    rmse: float
    smape_pct: float
    mape_pct: float
    zero_actual_days_pct: float


def compute_forecast_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, float]:
    """
    Compute the 4 required forecasting metrics:
    - WAPE (%): sum(|y - y_hat|) / sum(y) * 100  (Primary metric — handles zero-sale days cleanly)
    - MAE: mean(|y - y_hat|)
    - RMSE: sqrt(mean((y - y_hat)^2))
    - sMAPE (%): mean( 2 * |y - y_hat| / (|y| + |y_hat| + eps) ) * 100
    """
    yt = np.maximum(np.asarray(y_true, dtype=np.float64), 0.0)
    yp = np.maximum(np.asarray(y_pred, dtype=np.float64), 0.0)
    abs_err = np.abs(yt - yp)

    total_actual = float(np.sum(yt))
    wape = float(np.sum(abs_err) / max(total_actual, 1.0) * 100.0)
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
    denom = np.abs(yt) + np.abs(yp) + 1e-3
    smape = float(np.mean(2.0 * abs_err / denom) * 100.0)

    # MAPE divides by the actual value, so it is undefined on zero-sale days and explodes on days with 1-2 sales
    # (forecast 3 vs actual 1 = 200% error). It is computed only over days with sales, and the share of zero-sale
    # days is reported next to it; WAPE (total error / total sales) has neither problem.
    nonzero = yt > 0
    mape = float(np.mean(abs_err[nonzero] / yt[nonzero]) * 100.0) if nonzero.any() else float("nan")

    return {
        "wape_pct": round(wape, 3),
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "smape_pct": round(smape, 3),
        "mape_pct": round(mape, 3),
        "zero_actual_days_pct": round(float((~nonzero).mean() * 100.0), 2),
    }




# ============================================================================
# Model 1: Naive Forecaster (Last Value Baseline)
# ============================================================================
class NaiveForecaster:
    """Baseline 1: Repeats the last observed daily value y_T across all h = 1..H steps."""

    name = "1. Naive (Last Observed Value)"

    def fit_predict_series(
        self,
        train_df: pd.DataFrame,
        future_dates: pd.DatetimeIndex,
    ) -> np.ndarray:
        last_val = float(train_df["units_sold"].iloc[-1])
        return np.full(len(future_dates), max(0.0, last_val), dtype=np.float64)


# ============================================================================
# Model 2: Seasonal Naive Forecaster (7-Day Weekly Cycle)
# ============================================================================
class SeasonalNaive7DForecaster:
    """Baseline 2: Repeats the last observed 7-day weekly cycle y_{T + h - 7*k}."""

    name = "2. Seasonal Naive (7-Day Cycle)"

    def fit_predict_series(
        self,
        train_df: pd.DataFrame,
        future_dates: pd.DatetimeIndex,
    ) -> np.ndarray:
        vals = train_df["units_sold"].to_numpy(dtype=np.float64)
        if len(vals) < 7:
            return np.full(len(future_dates), max(0.0, float(vals[-1])), dtype=np.float64)
        last_7 = vals[-7:]
        reps = int(np.ceil(len(future_dates) / 7.0))
        preds = np.tile(last_7, reps)[: len(future_dates)]
        return np.maximum(0.0, preds)


# ============================================================================
# Model 3: Holt-Winters Exponential Smoothing (ETS / SARIMA-7 Equivalent)
# ============================================================================
class HoltWintersETSForecaster:
    """
    Task 2C: Classical Statistical Holt-Winters Exponential Smoothing (Additive Trend +
    Multiplicative/Additive 7-Day Weekly Seasonality, no external holiday regressors).
    """

    name = "3. Classical Holt-Winters ETS (s=7)"

    def __init__(
        self,
        alpha: float = 0.25,
        beta: float = 0.03,
        gamma: float = 0.20,
        damping_phi: float = 0.96,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.damping_phi = damping_phi

    def fit_predict_series(
        self,
        train_df: pd.DataFrame,
        future_dates: pd.DatetimeIndex,
    ) -> np.ndarray:
        y = train_df["units_sold"].to_numpy(dtype=np.float64)
        n = len(y)
        if n < 14:
            return np.full(len(future_dates), max(0.0, float(np.mean(y))), dtype=np.float64)

        # Initialize level, trend, and 7-day seasonal components from first 2 weeks
        level = float(np.mean(y[:7]))
        trend = float((np.mean(y[7:14]) - np.mean(y[:7])) / 7.0)
        seasonal = np.zeros(7, dtype=np.float64)
        for i in range(7):
            seasonal[i] = float(0.5 * (y[i] - level) + 0.5 * (y[i + 7] - np.mean(y[7:14])))

        for t in range(n):
            s_idx = t % 7
            prev_level = level
            prev_trend = trend
            prev_s = seasonal[s_idx]

            level = self.alpha * (y[t] - prev_s) + (1.0 - self.alpha) * (
                prev_level + self.damping_phi * prev_trend
            )
            trend = self.beta * (level - prev_level) + (1.0 - self.beta) * (
                self.damping_phi * prev_trend
            )
            seasonal[s_idx] = self.gamma * (y[t] - level) + (1.0 - self.gamma) * prev_s

        h = len(future_dates)
        preds = np.zeros(h, dtype=np.float64)
        phi_sum = 0.0
        for step in range(1, h + 1):
            phi_sum += self.damping_phi ** step
            s_idx = (n + step - 1) % 7
            preds[step - 1] = level + phi_sum * trend + seasonal[s_idx]

        return np.maximum(0.0, preds)


# ============================================================================
# Model 4: Prophet with custom festival holidays
# ============================================================================
class ProphetFourierHolidayForecaster:
    """
    Task 2D: Prophet with custom festival holidays (one model per series):
        log(1 + y_t) = trend(t) + weekly(t) + yearly_fourier(t, K) + sum_f beta_f * [festival f running on t] + e_t
    Festivals enter only as DATES: one indicator per festival name (Ramadan, Eid ul Fitr, 11.11, ...), built from the
    calendar's start/end dates, so moving Islamic dates are handled. Prophet learns each beta_f, i.e. how much that
    festival lifts THIS series, from past sales. No effect size, season curve or trend from the data generator is used.
    """

    name = "4. Prophet (Fourier + Moving Islamic Holidays)"

    def __init__(self, fourier_order: int = 10, ridge_alpha: float = 1.5) -> None:
        self.fourier_order = fourier_order
        self.ridge_alpha = ridge_alpha

    def _build_design_matrix(
        self,
        dates: pd.Series | pd.DatetimeIndex,
        calendar: FestivalCalendar,
        t0: pd.Timestamp,
    ) -> np.ndarray:
        dt = pd.DatetimeIndex(pd.to_datetime(dates))
        t_scaled = np.asarray((dt - t0).days, dtype=np.float64) / 365.25
        dow = np.asarray(dt.day_of_week, dtype=int)
        doy = np.asarray(dt.day_of_year, dtype=np.float64)

        features: list[np.ndarray] = [np.ones_like(t_scaled), t_scaled]
        for d_idx in range(6):  # weekday one-hot (Sunday = reference)
            features.append((dow == d_idx).astype(np.float64))
        for k in range(1, self.fourier_order + 1):  # yearly Fourier harmonics
            angle = 2.0 * np.pi * k * doy / 365.25
            features.append(np.sin(angle))
            features.append(np.cos(angle))
        active = calendar.active_matrix(dt).astype(np.float64)  # festival indicators (dates only)
        return np.column_stack(features + [active[:, j] for j in range(active.shape[1])])

    def fit_predict_series(
        self,
        train_df: pd.DataFrame,
        future_dates: pd.DatetimeIndex,
        calendar: FestivalCalendar,
    ) -> np.ndarray:
        t0 = pd.Timestamp(train_df["sale_date"].iloc[0])
        y_train_log = np.log1p(np.maximum(train_df["units_sold"].to_numpy(dtype=np.float64), 0.0))
        if prophet_available():
            return self._fit_predict_prophet(train_df, y_train_log, future_dates, calendar)
        X_train = self._build_design_matrix(train_df["sale_date"], calendar, t0)

        # Fallback without the `prophet` library: same decomposition fitted by ridge regression
        n_feat = X_train.shape[1]
        reg_mat = np.eye(n_feat, dtype=np.float64) * self.ridge_alpha
        reg_mat[0, 0] = 0.0  # do not regularise the intercept
        beta = np.linalg.solve(X_train.T @ X_train + reg_mat, X_train.T @ y_train_log)

        X_future = self._build_design_matrix(future_dates, calendar, t0)
        pred_log = X_future @ beta
        resid = y_train_log - (X_train @ beta)
        smear = float(np.mean(np.exp(resid)))  # smearing correction for the log transform
        preds = np.expm1(pred_log) * min(max(smear, 0.95), 1.08)
        return np.maximum(0.0, preds)

    def _fit_predict_prophet(
        self,
        train_df: pd.DataFrame,
        y_train_log: np.ndarray,
        future_dates: pd.DatetimeIndex,
        calendar: FestivalCalendar,
    ) -> np.ndarray:
        """Real Prophet: trend + weekly + yearly seasonality + one regressor per festival (dates only)."""
        import logging

        from prophet import Prophet

        logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
        cols = [f"fest_{i}" for i in range(len(calendar.names))]

        def regressors(dates: pd.Series | pd.DatetimeIndex) -> pd.DataFrame:
            return pd.DataFrame(calendar.active_matrix(dates).astype(float), columns=cols)

        hist = pd.DataFrame({"ds": pd.to_datetime(train_df["sale_date"]).to_numpy(), "y": y_train_log})
        hist = pd.concat([hist, regressors(train_df["sale_date"])], axis=1)
        m = Prophet(
            yearly_seasonality=self.fourier_order,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        for col in cols:
            if hist[col].any():  # a festival never seen in training has nothing to learn from
                m.add_regressor(col)
        m.fit(hist)
        fut = pd.concat([pd.DataFrame({"ds": future_dates}), regressors(future_dates)], axis=1)
        pred_log = m.predict(fut)["yhat"].to_numpy()
        return np.maximum(0.0, np.expm1(pred_log))



def prophet_available() -> bool:
    try:
        import prophet  # noqa: F401
    except Exception:
        return False
    return True


# ============================================================================
# Model 5: Global LightGBM / HistGradientBoosting Forecaster
# ============================================================================
def _make_gbm_regressor(
    max_iter: int, learning_rate: float, max_leaf_nodes: int, min_samples_leaf: int, random_state: int
) -> Any:
    """LightGBM when installed (Python 3.11 env); otherwise scikit-learn's histogram GBM with the same settings."""
    try:
        import lightgbm as lgb

        return lgb.LGBMRegressor(
            n_estimators=max_iter,
            learning_rate=learning_rate,
            num_leaves=max_leaf_nodes,
            min_child_samples=min_samples_leaf,
            reg_lambda=2.0,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )
    except Exception:
        return HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=max_iter,
            learning_rate=learning_rate,
            max_leaf_nodes=max_leaf_nodes,
            min_samples_leaf=min_samples_leaf,
            l2_regularization=2.0,
            random_state=random_state,
        )


def gbm_backend() -> str:
    try:
        import lightgbm  # noqa: F401

        return "lightgbm"
    except Exception:
        return "sklearn_histgbm"
TRAIN_HORIZONS: tuple[int, ...] = (1, 2, 3, 5, 7, 10, 14, 21, 28, 35, 42)
MAX_TRAIN_ROWS = 300_000  # training origins are thinned to stay near this size (keeps the 2025 replay fast)
MIN_HISTORY_DAYS = 28


def _daily_series(train_df: pd.DataFrame) -> tuple[np.ndarray, pd.DatetimeIndex]:
    """Units sold on a gap-free daily index (missing days = 0 sales)."""
    s = train_df.groupby(pd.to_datetime(train_df["sale_date"]).dt.normalize())["units_sold"].sum()
    idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(idx, fill_value=0).to_numpy(dtype=np.float64), idx


class GlobalLGBMForecaster:
    """
    Task 2E: one global gradient-boosted model (LightGBM; scikit-learn's histogram GBM if LightGBM is missing)
    trained across all series, direct multi-horizon.

    For an origin day o (the last day with known sales) and a target day o + h it only sees:
    - the series' recent level and volatility up to o: 7 / 28 / 91-day means, 28-day std, share of zero-sale days
    - the same-weekday average of the last 4 weeks before o (weekly pattern, learned from the data)
    - last year around the target date relative to last year's level (yearly season, learned from the data)
    - calendar of the target date (weekday, month, day of year), the horizon h and the category
    - which festivals run on the target date (calendar dates / names only) and how much each one lifted THIS series
      the previous time and so far this time (`festival_uplift_features`, computed from sales up to o)
    Target = sales / (28-day level + 0.1), with sample weight = that level, so the fit lines up with WAPE.
    No multiplier, season curve, trend or noise parameter of the data generator is used (the earlier version did;
    it is kept as `shopkaro.forecasting.oracle.OracleGeneratorFormulaForecaster` for comparison only).
    """

    name = "5. Global LightGBM (Lags + Rolling + Festival Features)"

    def __init__(
        self,
        max_iter: int = 220,
        learning_rate: float = 0.05,
        max_leaf_nodes: int = 31,
        min_samples_leaf: int = 25,
        random_state: int = 42,
    ) -> None:
        self.max_iter = max_iter
        self.learning_rate = learning_rate
        self.max_leaf_nodes = max_leaf_nodes
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.model: Any = None
        self.cat_to_code: dict[str, int] = {}

    @staticmethod
    def _features(
        y: np.ndarray,
        dates: pd.DatetimeIndex,
        cat_code: int,
        calendar: FestivalCalendar,
        origins: np.ndarray,
        horizons: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Feature matrix and scale (28-day level + 0.1) for (origin, horizon) pairs. Uses y[: origin + 1] only."""
        o = origins.astype(np.int64)
        h = horizons.astype(np.int64)
        t = o + h
        csum = np.concatenate([[0.0], np.cumsum(y)])
        csq = np.concatenate([[0.0], np.cumsum(y * y)])
        czero = np.concatenate([[0.0], np.cumsum(y == 0)])

        def window_mean(c: np.ndarray, end: np.ndarray, length: int) -> np.ndarray:
            start = np.maximum(end - length + 1, 0)
            return (c[end + 1] - c[start]) / (end - start + 1)

        level7 = window_mean(csum, o, 7)
        level28 = window_mean(csum, o, 28)
        level91 = window_mean(csum, o, 91)
        std28 = np.sqrt(np.maximum(window_mean(csq, o, 28) - level28**2, 0.0))
        zero28 = window_mean(czero, o, 28)
        scale = level28 + 0.1

        # Same weekday as the target, last 4 weeks up to the origin
        k0 = np.ceil((t - o) / 7.0).astype(np.int64)
        dow_vals = np.full((len(o), 4), np.nan)
        for j in range(4):
            idx = t - 7 * (k0 + j)
            ok = idx >= 0
            dow_vals[ok, j] = y[idx[ok]]
        counts = (~np.isnan(dow_vals)).sum(axis=1)
        dow_mean = np.where(counts > 0, np.nansum(dow_vals, axis=1) / np.maximum(counts, 1), np.nan)

        # Last year: target date -364 days (same weekday) +-3 days, relative to last year's level at the origin
        ly_c = t - 364
        ly_ok = (ly_c - 3) >= 0
        ly_win = np.full(len(o), np.nan)
        ly_win[ly_ok] = (csum[ly_c[ly_ok] + 4] - csum[ly_c[ly_ok] - 3]) / 7.0
        ly_o = o - 364
        lvl_ok = (ly_o - 27) >= 0
        ly_lvl = np.full(len(o), np.nan)
        ly_lvl[lvl_ok] = (csum[ly_o[lvl_ok] + 1] - csum[ly_o[lvl_ok] - 27]) / 28.0
        ly_ratio = ly_win / (ly_lvl + 0.1)

        base = dates[0]
        target_dates = pd.DatetimeIndex(base + pd.to_timedelta(t, unit="D"))
        origin_dates = pd.DatetimeIndex(base + pd.to_timedelta(o, unit="D"))
        # Islamic festivals move ~11 days a year, so "same date last year" may have been Eid when this year it is
        # not (or the reverse). Telling the model lets it discount `ly_ratio` on those days.
        ly_dates = pd.DatetimeIndex(target_dates - pd.Timedelta(days=364))
        ly_fest = calendar.is_festival(ly_dates).astype(np.float64)
        ly_since = calendar.days_since_start(ly_dates)
        doy = target_dates.day_of_year.to_numpy(dtype=np.float64)
        active = calendar.active_matrix(target_dates).astype(np.float64)
        hist_up, cur_up = festival_uplift_features(y, dates, calendar, o, target_dates)

        X = np.column_stack(
            [
                h.astype(np.float64),
                np.full(len(o), float(cat_code)),
                np.log1p(level28),
                level7 / scale,
                level91 / scale,
                std28 / scale,
                zero28,
                dow_mean / scale,
                ly_ratio,
                ly_fest,
                ly_since,
                target_dates.day_of_week.to_numpy(dtype=np.float64),
                target_dates.month.to_numpy(dtype=np.float64),
                np.sin(2.0 * np.pi * doy / 365.25),
                np.cos(2.0 * np.pi * doy / 365.25),
                calendar.days_since_start(target_dates),
                calendar.is_festival(origin_dates).astype(np.float64),
                hist_up,
                cur_up,
                active,
            ]
        )
        return X, scale

    def fit_and_predict_panel(
        self,
        series_dict: dict[str, tuple[pd.DataFrame, str]],
        future_dates: pd.DatetimeIndex,
        calendar: FestivalCalendar,
    ) -> dict[str, np.ndarray]:
        """Fit one global model on all series (data up to each series' last day) and predict `future_dates`."""
        all_cats = sorted({cat for _, cat in series_dict.values()})
        self.cat_to_code = {c: idx for idx, c in enumerate(all_cats)}
        prepared = {k: (*_daily_series(df), cat) for k, (df, cat) in series_dict.items()}

        # Festivals that never happened before the forecast origin are treated as regular days (no history)
        calendar = calendar.seen_before(min(d[-1] for _, d, _ in prepared.values()))
        max_h = max(int((pd.Timestamp(future_dates[-1]) - d[-1]).days) for _, d, _ in prepared.values())
        train_h = sorted({h for h in TRAIN_HORIZONS if h <= max_h} | {max(max_h, 1)})
        n_candidates = sum(max(len(y) - MIN_HISTORY_DAYS - h, 0) for y, _, _ in prepared.values() for h in train_h)
        step = max(1, int(np.ceil(n_candidates / MAX_TRAIN_ROWS)))

        X_parts, y_parts, w_parts = [], [], []
        for y, dates, cat in prepared.values():
            for h in train_h:
                origins = np.arange(MIN_HISTORY_DAYS - 1 + (h % step), len(y) - h, step)
                if len(origins) == 0:
                    continue
                X, scale = self._features(y, dates, self.cat_to_code[cat], calendar, origins, np.full(len(origins), h))
                X_parts.append(X)
                y_parts.append(y[origins + h] / scale)
                w_parts.append(scale)

        self.model = _make_gbm_regressor(
            max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            max_leaf_nodes=self.max_leaf_nodes,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
        )
        self.model.fit(np.vstack(X_parts), np.concatenate(y_parts), sample_weight=np.concatenate(w_parts))

        predictions: dict[str, np.ndarray] = {}
        for key, (y, dates, cat) in prepared.items():
            hs = np.asarray((pd.DatetimeIndex(future_dates) - dates[-1]).days, dtype=np.int64)
            origins = np.full(len(hs), len(y) - 1)
            X, scale = self._features(y, dates, self.cat_to_code[cat], calendar, origins, hs)
            predictions[key] = np.maximum(0.0, self.model.predict(X) * scale)
        return predictions




# ============================================================================
# Models 6 & 7: intermittent-demand methods (Croston-SBA, TSB) for slow movers
# ============================================================================
# On a slow mover most days sell nothing, so a per-day forecast is mostly wrong whatever it is. What stock planning
# needs is the average daily rate (the inventory engine multiplies it by the lead time). Croston-type methods estimate
# that rate by smoothing the size of non-zero sales and how often they happen separately. Smoothing constants are the
# textbook defaults (0.1), fixed in advance rather than tuned on the backtest.
def croston_sba_rate(y: np.ndarray, alpha: float = 0.1) -> float:
    """Croston's method with the Syntetos-Boylan bias correction: rate = (1 - alpha/2) * size / interval."""
    y = np.asarray(y, dtype=np.float64)
    nz = np.flatnonzero(y > 0)
    if len(nz) == 0:
        return 0.0
    size, interval, last = float(y[nz[0]]), float(nz[0] + 1), int(nz[0])
    for i in nz[1:]:
        size += alpha * (float(y[i]) - size)
        interval += alpha * (float(i - last) - interval)
        last = int(i)
    return (1.0 - alpha / 2.0) * size / interval


def tsb_rate(y: np.ndarray, alpha: float = 0.1, beta: float = 0.1) -> float:
    """
    Teunter-Syntetos-Babai: smooth the demand size on sale days (alpha) and the probability of a sale every day (beta),
    rate = probability * size. Unlike Croston, the rate decays during long runs of zeros (an item that stopped selling).
    """
    y = np.asarray(y, dtype=np.float64)
    sold = y > 0
    if not sold.any():
        return 0.0
    size, prob = float(y[sold].mean()), float(sold.mean())
    for v, s in zip(y, sold):
        if s:
            size += alpha * (v - size)
        prob += beta * (float(s) - prob)
    return prob * size


class CrostonSBAForecaster:
    """Model 6: Croston (SBA) flat daily rate."""

    name = "6. Croston-SBA (Intermittent Demand)"

    def fit_predict_series(self, train_df: pd.DataFrame, future_dates: pd.DatetimeIndex) -> np.ndarray:
        return np.full(len(future_dates), croston_sba_rate(train_df["units_sold"].to_numpy()), dtype=np.float64)


class TSBForecaster:
    """Model 7: TSB flat daily rate."""

    name = "7. TSB (Intermittent Demand)"

    def fit_predict_series(self, train_df: pd.DataFrame, future_dates: pd.DatetimeIndex) -> np.ndarray:
        return np.full(len(future_dates), tsb_rate(train_df["units_sold"].to_numpy()), dtype=np.float64)


def _evaluate_panel_across_folds(
    panel_df: pd.DataFrame,
    id_col: str,
    hierarchy_label: str,
    calendar: FestivalCalendar,
    breakdown_sink: list[dict[str, Any]] | None = None,
    oracle_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]] | None = None,
) -> pd.DataFrame:
    """
    Run 4-Fold Rolling-Origin Backtesting for all 7 models across 7d, 14d, and 30d horizons.
    If `breakdown_sink` is given, also append accuracy at BREAKDOWN_HORIZON split by festival vs regular days and
    by velocity tier.
    If `oracle_lookup` is given, an 8th row is added: the generator-formula ORACLE (see `forecasting/oracle.py`), an
    upper bound that a real retailer could not reach. It is reported for comparison only and used nowhere else.
    """
    panel = panel_df.copy()
    panel["sale_date"] = pd.to_datetime(panel["sale_date"])
    series_ids = sorted(panel[id_col].unique().tolist())

    m1_naive = NaiveForecaster()
    m2_snaive = SeasonalNaive7DForecaster()
    m3_ets = HoltWintersETSForecaster()
    m4_prophet = ProphetFourierHolidayForecaster()
    m5_lgbm = GlobalLGBMForecaster()
    m6_croston = CrostonSBAForecaster()
    m7_tsb = TSBForecaster()
    m8_oracle = None
    if oracle_lookup is not None:
        from shopkaro.forecasting.oracle import OracleGeneratorFormulaForecaster

        m8_oracle = OracleGeneratorFormulaForecaster()

    model_names = [
        m1_naive.name,
        m2_snaive.name,
        m3_ets.name,
        m4_prophet.name,
        m5_lgbm.name,
        m6_croston.name,
        m7_tsb.name,
    ] + ([m8_oracle.name] if m8_oracle is not None else [])

    # Store (y_true_list, y_pred_list) per (model_name, horizon)
    collector: dict[tuple[str, int], tuple[list[np.ndarray], list[np.ndarray]]] = {
        (m, h): ([], []) for m in model_names for h in HORIZONS
    }

    max_h = max(HORIZONS)
    # Per-point actuals / predictions at one horizon, for festival-vs-regular and velocity-tier breakdowns
    # (plus per-series totals over that horizon: stock planning needs the total, not each day)
    detail: dict[str, dict[str, list[Any]]] = {
        m: {"y": [], "p": [], "fest": [], "tier": [], "ytot": [], "ptot": [], "stier": []} for m in model_names
    }

    for _, cutoff_str in BACKTEST_FOLD_CUTOFFS:
        cutoff_dt = pd.Timestamp(cutoff_str)
        future_end = cutoff_dt + pd.Timedelta(days=max_h)
        future_dates = pd.date_range(
            start=cutoff_dt + pd.Timedelta(days=1),
            end=future_end,
            freq="D",
        )

        train_slice = panel[panel["sale_date"] <= cutoff_dt]
        test_slice = panel[
            (panel["sale_date"] > cutoff_dt) & (panel["sale_date"] <= future_end)
        ]

        series_train_dict: dict[str, tuple[pd.DataFrame, str]] = {}
        series_test_dict: dict[str, np.ndarray] = {}

        for sid in series_ids:
            tr_s = train_slice[train_slice[id_col] == sid].sort_values("sale_date")
            te_s = test_slice[test_slice[id_col] == sid].sort_values("sale_date")
            if len(tr_s) < 60 or len(te_s) < max_h:
                continue
            cat = str(tr_s["category"].iloc[0])
            series_train_dict[str(sid)] = (tr_s, cat)
            series_test_dict[str(sid)] = te_s["units_sold"].to_numpy(dtype=np.float64)

        # Fit & predict Global LightGBM across all series simultaneously for this fold
        lgbm_preds_map = m5_lgbm.fit_and_predict_panel(
            series_dict=series_train_dict,
            future_dates=future_dates,
            calendar=calendar,
        )
        oracle_preds_map = (
            m8_oracle.fit_and_predict_panel(series_train_dict, future_dates, oracle_lookup)
            if m8_oracle is not None
            else {}
        )
        fest_flags_h = calendar.is_festival(future_dates[:BREAKDOWN_HORIZON])

        # Fit & predict local models per series
        for sid_str, (tr_s, cat) in series_train_dict.items():
            y_actual_30 = series_test_dict[sid_str]
            p_naive = m1_naive.fit_predict_series(tr_s, future_dates)
            p_snaive = m2_snaive.fit_predict_series(tr_s, future_dates)
            p_ets = m3_ets.fit_predict_series(tr_s, future_dates)
            p_prophet = m4_prophet.fit_predict_series(tr_s, future_dates, calendar)
            p_lgbm = lgbm_preds_map[sid_str]

            preds_by_model = {
                m1_naive.name: p_naive,
                m2_snaive.name: p_snaive,
                m3_ets.name: p_ets,
                m4_prophet.name: p_prophet,
                m5_lgbm.name: p_lgbm,
                m6_croston.name: m6_croston.fit_predict_series(tr_s, future_dates),
                m7_tsb.name: m7_tsb.fit_predict_series(tr_s, future_dates),
            }
            if m8_oracle is not None:
                preds_by_model[m8_oracle.name] = oracle_preds_map[sid_str]

            for h in HORIZONS:
                for m_name, p_vec in preds_by_model.items():
                    collector[(m_name, h)][0].append(y_actual_30[:h])
                    collector[(m_name, h)][1].append(p_vec[:h])

            if breakdown_sink is not None:
                h = BREAKDOWN_HORIZON
                fest_flags = fest_flags_h
                tier = str(tr_s["velocity_tier"].iloc[-1]) if "velocity_tier" in tr_s.columns else ""
                for m_name, p_vec in preds_by_model.items():
                    detail[m_name]["y"].append(y_actual_30[:h])
                    detail[m_name]["p"].append(np.asarray(p_vec[:h], dtype=np.float64))
                    detail[m_name]["fest"].append(fest_flags)
                    detail[m_name]["tier"].append(np.array([tier] * h, dtype=object))
                    detail[m_name]["ytot"].append(float(np.sum(y_actual_30[:h])))
                    detail[m_name]["ptot"].append(float(np.sum(np.maximum(np.asarray(p_vec[:h], dtype=np.float64), 0.0))))
                    detail[m_name]["stier"].append(tier)

    summary_rows: list[BacktestSummaryRow] = []
    for h in HORIZONS:
        for m_name in model_names:
            trues, preds = collector[(m_name, h)]
            y_t_all = np.concatenate(trues)
            y_p_all = np.concatenate(preds)
            m_dict = compute_forecast_metrics(y_t_all, y_p_all)
            summary_rows.append(
                BacktestSummaryRow(
                    hierarchy_level=hierarchy_label,
                    model_name=m_name,
                    horizon_days=h,
                    n_folds=len(BACKTEST_FOLD_CUTOFFS),
                    n_series=len(series_ids),
                    wape_pct=m_dict["wape_pct"],
                    mae=m_dict["mae"],
                    rmse=m_dict["rmse"],
                    smape_pct=m_dict["smape_pct"],
                    mape_pct=m_dict["mape_pct"],
                    zero_actual_days_pct=m_dict["zero_actual_days_pct"],
                )
            )

    if breakdown_sink is not None:
        h = BREAKDOWN_HORIZON
        for m_name in model_names:
            d = detail[m_name]
            y, p = np.concatenate(d["y"]), np.concatenate(d["p"])
            fest, tier = np.concatenate(d["fest"]), np.concatenate(d["tier"])
            segments = [("period", "festival days", fest), ("period", "regular days", ~fest)]
            segments += [("velocity", str(t), tier == t) for t in sorted(set(tier.tolist())) if t]
            ytot, ptot, stier = np.array(d["ytot"]), np.array(d["ptot"]), np.array(d["stier"], dtype=object)
            for seg_type, seg, mask in segments:
                if mask.any():
                    m = compute_forecast_metrics(y[mask], p[mask])
                    # Error of the h-day TOTAL per series and fold (what a reorder decision uses); velocity rows only
                    tot = {"total_wape_pct": float("nan"), "total_bias_pct": float("nan")}
                    smask = stier == seg
                    if seg_type == "velocity" and smask.any():
                        yt_sum = max(float(ytot[smask].sum()), 1.0)
                        tot = {
                            "total_wape_pct": round(float(np.abs(ptot[smask] - ytot[smask]).sum()) / yt_sum * 100, 3),
                            "total_bias_pct": round(float((ptot[smask] - ytot[smask]).sum()) / yt_sum * 100, 3),
                        }
                    breakdown_sink.append(
                        {"hierarchy_level": hierarchy_label, "model_name": m_name, "horizon_days": h,
                         "segment_type": seg_type, "segment": seg, "n_points": int(mask.sum()), **m, **tot}
                    )

    return pd.DataFrame([asdict(r) for r in summary_rows])


def plot_backtest_comparison_chart(
    backtest_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Generate Figure 11 (`11_forecasting_backtest_comparison.png`):
    4-panel comparison of all 7 forecasting models across 7d, 14d, and 30d horizons
    at both Category Level (11 Categories) and Product Level (Top-50 SKUs).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.suptitle(
        "ShopKaro AI — Day 3 Tasks 2 & 3: 4-Fold Rolling-Origin Backtesting (7 Models x 3 Horizons, + oracle)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    cat_df = backtest_df[backtest_df["hierarchy_level"] == "Category_Level"]
    sku_df = backtest_df[backtest_df["hierarchy_level"] == "Top50_SKU_Level"]

    colors = {7: "#6baed6", 14: "#3182bd", 30: "#08519c"}
    short_names = {
        "1": "1. Naive",
        "2": "2. Seasonal Naive (7d)",
        "3": "3. Holt-Winters ETS",
        "4": "4. Prophet (Holidays)",
        "5": "5. Global LightGBM",
        "6": "6. Croston-SBA",
        "7": "7. TSB",
        "8": "8. ORACLE (not a real model)",
    }
    n_models = cat_df[cat_df["horizon_days"] == 14]["model_name"].nunique()
    short_models = [short_names[str(i)] for i in range(1, n_models + 1)]
    y_pos = np.arange(len(short_models))
    w = 0.25

    # Panel 1: Category-Level WAPE (%) across 7d, 14d, 30d
    ax1 = axes[0, 0]
    for idx_h, h in enumerate(HORIZONS):
        sub = cat_df[cat_df["horizon_days"] == h]
        bars = ax1.barh(
            y_pos + (idx_h - 1) * w,
            sub["wape_pct"],
            height=w,
            label=f"Horizon = {h}d",
            color=colors[h],
        )
        if h == 14:
            for b in bars:
                ax1.text(
                    b.get_width() + 0.4,
                    b.get_y() + b.get_height() / 2,
                    f"{b.get_width():.1f}%",
                    va="center",
                    fontsize=8.5,
                    fontweight="bold",
                )
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(short_models)
    ax1.invert_yaxis()
    ax1.set_xlabel("WAPE % (Lower is Better)")
    ax1.set_title("1. Category-Level WAPE (%) — 11 Categories x 4 Folds", fontweight="bold")
    ax1.legend(loc="lower right")

    # Panel 2: Top-50 SKU-Level WAPE (%) across 7d, 14d, 30d
    ax2 = axes[0, 1]
    for idx_h, h in enumerate(HORIZONS):
        sub = sku_df[sku_df["horizon_days"] == h]
        bars = ax2.barh(
            y_pos + (idx_h - 1) * w,
            sub["wape_pct"],
            height=w,
            label=f"Horizon = {h}d",
            color=colors[h],
        )
        if h == 14:
            for b in bars:
                ax2.text(
                    b.get_width() + 0.4,
                    b.get_y() + b.get_height() / 2,
                    f"{b.get_width():.1f}%",
                    va="center",
                    fontsize=8.5,
                    fontweight="bold",
                )
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(short_models)
    ax2.invert_yaxis()
    ax2.set_xlabel("WAPE % (Lower is Better)")
    ax2.set_title("2. Product-Level WAPE (%) — Top 50 SKUs x 4 Folds", fontweight="bold")
    ax2.legend(loc="lower right")

    # Panel 3: Category 14-Day MAE & RMSE Comparison
    ax3 = axes[1, 0]
    cat_14 = cat_df[cat_df["horizon_days"] == 14]
    ax3.barh(y_pos - 0.18, cat_14["mae"], height=0.35, label="MAE (Units)", color="#2ca02c")
    ax3.barh(y_pos + 0.18, cat_14["rmse"], height=0.35, label="RMSE (Units)", color="#ff7f0e")
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(short_models)
    ax3.invert_yaxis()
    ax3.set_xlabel("Error in Daily Units (Lower is Better)")
    ax3.set_title("3. Category-Level 14-Day MAE & RMSE", fontweight="bold")
    ax3.legend(loc="lower right")

    # Panel 4: Product-Level 14-Day sMAPE (%) & WAPE (%) Comparison
    ax4 = axes[1, 1]
    sku_14 = sku_df[sku_df["horizon_days"] == 14]
    ax4.barh(
        y_pos - 0.18, sku_14["wape_pct"], height=0.35, label="WAPE (%)", color="#1f77b4"
    )
    ax4.barh(
        y_pos + 0.18, sku_14["smape_pct"], height=0.35, label="sMAPE (%)", color="#9467bd"
    )
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(short_models)
    ax4.invert_yaxis()
    ax4.set_xlabel("Percentage Error (Lower is Better)")
    ax4.set_title("4. Product-Level 14-Day WAPE vs sMAPE (%)", fontweight="bold")
    ax4.legend(loc="lower right")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def run_day3_task2_task3_forecasting_backtest(
    db_path: Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """
    Execute Day 3 — Tasks 2 & 3:
    1. Build 3-level time-series panels and festival calendar lookup.
    2. Evaluate all 7 forecasting models across 4 Rolling-Origin Folds and 3 Horizons (7d, 14d, 30d)
       on both Category Level (11 Categories) and Product Level (Top-50 SKUs).
    3. Save `reports/day3_forecasting_backtest_comparison.csv` and `reports/figures/11_forecasting_backtest_comparison.png`.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)

    _, category_df, top50_sku_df = build_three_level_timeseries(con)
    festival_cal_df = con.execute("SELECT * FROM festival_calendar").df()
    # Top-50 SKUs are all fast movers; for the fast-vs-slow comparison take the 20 highest-volume SKUs of each tier.
    velocity_df = con.execute(
        """
        WITH ranked AS (
            SELECT product_id, velocity_tier,
                   ROW_NUMBER() OVER (PARTITION BY velocity_tier ORDER BY SUM(units_sold) DESC, product_id) AS rn
            FROM daily_sales GROUP BY product_id, velocity_tier
        )
        SELECT CAST(d.sale_date AS TIMESTAMP) AS sale_date, d.product_id, d.category, d.velocity_tier, d.units_sold
        FROM daily_sales d JOIN ranked r USING (product_id)
        WHERE r.rn <= 20
        ORDER BY d.product_id, d.sale_date
        """
    ).df()
    con.close()

    calendar = FestivalCalendar(festival_cal_df)  # dates and names only
    # The oracle (comparison row only) is the one place that reads the generator's true multipliers.
    from shopkaro.forecasting.oracle import build_oracle_festival_lookup

    oracle_lookup = build_oracle_festival_lookup(
        festival_cal_df=festival_cal_df,
        all_categories=sorted(category_df["category"].astype(str).unique().tolist()),
    )

    breakdown: list[dict[str, Any]] = []
    panels = [
        (category_df, "category", "Category_Level"),
        (top50_sku_df, "product_id", "Top50_SKU_Level"),
        (velocity_df, "product_id", "SKU_By_Velocity_60"),
    ]
    frames = [
        _evaluate_panel_across_folds(
            panel_df=panel,
            id_col=id_col,
            hierarchy_label=label,
            calendar=calendar,
            breakdown_sink=breakdown,
            oracle_lookup=oracle_lookup,
        )
        for panel, id_col, label in panels
    ]
    cat_backtest_df, sku_backtest_df, vel_backtest_df = frames

    full_backtest_df = pd.concat([cat_backtest_df, sku_backtest_df, vel_backtest_df], ignore_index=True)

    csv_out = settings.reports_dir / "day3_forecasting_backtest_comparison.csv"
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    full_backtest_df.to_csv(csv_out, index=False)
    pd.DataFrame(breakdown).to_csv(settings.reports_dir / "day3_forecast_accuracy_breakdown.csv", index=False)

    fig_out = settings.figures_dir / "11_forecasting_backtest_comparison.png"
    plot_backtest_comparison_chart(full_backtest_df, output_path=fig_out)

    return full_backtest_df, fig_out

