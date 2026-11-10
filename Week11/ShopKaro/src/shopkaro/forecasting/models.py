"""
Day 3 — Task 2 & Task 3: Multi-Model Forecasting Pipeline & 4-Fold Rolling-Origin Backtesting.

Implements 5 Progressive Forecasting Models:
1. `NaiveForecaster`: Last observed value (random-walk baseline).
2. `SeasonalNaive7DForecaster`: Same day last week (s = 7 weekly cycle baseline).
3. `HoltWintersETSForecaster`: Classical additive Holt-Winters Exponential Smoothing / SARIMA(0,1,1)(0,1,1)_7.
4. `ProphetFourierHolidayForecaster`: Decomposable Trend + Yearly Fourier Harmonics + Weekly Dummies
   + Moving Islamic & Pakistani Festival Regressors (Ridge-regularized Prophet formulation).
5. `GlobalLGBMForecaster`: Global Gradient Boosted Trees (`HistGradientBoostingRegressor` — native
   LightGBM histogram algorithm) trained jointly across all series with lag, rolling, calendar,
   category-seasonality, and Pakistani festival features.
6. `CrostonSBAForecaster` / 7. `TSBForecaster`: intermittent-demand rates (checked for slow movers; not adopted).

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


def _build_date_category_festival_lookup(
    festival_cal_df: pd.DataFrame,
    all_categories: list[str],
    start_date: str = "2024-01-01",
    end_date: str = "2026-03-31",
) -> dict[tuple[pd.Timestamp, str], tuple[float, int, str]]:
    """
    Precompute known calendar & festival multipliers `(fest_mult, is_fest, fest_name)` for
    every `(date, category)` pair using ShopKaro's official `festival_calendar`.
    """
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]] = {}

    for d in dates:
        for cat in all_categories:
            lookup[(d, cat)] = (1.0, 0, "Regular_Day")

    for rec in festival_cal_df.to_dict("records"):
        f_start = pd.Timestamp(rec["start_date"])
        f_end = pd.Timestamp(rec["end_date"])
        f_name = str(rec["festival_name"])
        mult = float(rec["demand_multiplier"])
        boost_cats = {c.strip() for c in str(rec["boost_categories"]).split(",")}

        cur = f_start
        while cur <= f_end:
            for cat in all_categories:
                prev_mult, _, _ = lookup.get((cur, cat), (1.0, 0, "Regular_Day"))
                target_m = mult if cat in boost_cats else 1.15
                if target_m >= prev_mult:
                    lookup[(cur, cat)] = (target_m, 1, f_name)
            cur += pd.Timedelta(days=1)

    return lookup


def _category_climate_index(category: str, day_of_year: np.ndarray, month: np.ndarray) -> np.ndarray:
    """Compute annual climate seasonal wave for a category given day-of-year and month."""
    if category == "Women's Lawn & Unstitched":
        return 1.0 + 0.55 * np.sin(2.0 * np.pi * (day_of_year - 60.0) / 365.25)
    if category == "Winter Wear & Jackets":
        return np.where(np.isin(month, [11, 12, 1, 2]), 2.4, 0.08)
    return 1.0 + 0.18 * np.sin(2.0 * np.pi * (day_of_year - 90.0) / 365.25)


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
# Model 4: Prophet-Style Decomposable Trend + Fourier + Moving Islamic Holidays
# ============================================================================
class ProphetFourierHolidayForecaster:
    """
    Task 2D: Prophet-Style Decomposable Time-Series Model:
        log(1 + y_t) = g(t) + s_weekly(t) + s_yearly_fourier(t, K=6) + X_holidays(t) * β + ε_t
    Explicitly incorporates moving Islamic festival windows (Ramadan, Eid ul Fitr, Eid ul Adha)
    and fixed commercial events (11.11, Blessed Friday, Back-to-School).
    """

    name = "4. Prophet (Fourier + Moving Islamic Holidays)"

    def __init__(self, fourier_order: int = 6, ridge_alpha: float = 1.5) -> None:
        self.fourier_order = fourier_order
        self.ridge_alpha = ridge_alpha

    def _build_design_matrix(
        self,
        dates: pd.Series | pd.DatetimeIndex,
        category: str,
        fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
        t0: pd.Timestamp,
    ) -> np.ndarray:
        dt = pd.to_datetime(dates)
        t_scaled = np.asarray((dt - t0).dt.days if hasattr(dt, "dt") else (dt - t0).days, dtype=np.float64) / 365.25
        dow = np.asarray(dt.dt.day_of_week if hasattr(dt, "dt") else dt.day_of_week, dtype=int)
        doy = np.asarray(dt.dt.day_of_year if hasattr(dt, "dt") else dt.day_of_year, dtype=np.float64)
        month = np.asarray(dt.dt.month if hasattr(dt, "dt") else dt.month, dtype=int)

        features: list[np.ndarray] = [
            np.ones_like(t_scaled),
            t_scaled,
        ]
        # Weekly day-of-week one-hot (Mon..Sat, Sun as reference)
        for d_idx in range(6):
            features.append((dow == d_idx).astype(np.float64))

        # Yearly Fourier harmonics (sin/cos pairs)
        for k in range(1, self.fourier_order + 1):
            angle = 2.0 * np.pi * k * doy / 365.25
            features.append(np.sin(angle))
            features.append(np.cos(angle))

        # Category winter indicator for abrupt winter wear transition
        features.append(np.log(_category_climate_index(category, doy, month)))

        # Moving Islamic & Pakistani Festival regressors from `festival_calendar`
        fest_mults = np.array(
            [fest_lookup.get((pd.Timestamp(d), category), (1.0, 0, ""))[0] for d in dt],
            dtype=np.float64,
        )
        is_fest = np.array(
            [fest_lookup.get((pd.Timestamp(d), category), (1.0, 0, ""))[1] for d in dt],
            dtype=np.float64,
        )
        features.append(is_fest)
        features.append(np.log(np.maximum(fest_mults, 1.0)))

        return np.column_stack(features)

    def fit_predict_series(
        self,
        train_df: pd.DataFrame,
        future_dates: pd.DatetimeIndex,
        category: str,
        fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
    ) -> np.ndarray:
        t0 = pd.Timestamp(train_df["sale_date"].iloc[0])
        y_train_log = np.log1p(np.maximum(train_df["units_sold"].to_numpy(dtype=np.float64), 0.0))
        if prophet_available():
            return self._fit_predict_prophet(train_df, y_train_log, future_dates, category, fest_lookup, t0)
        X_train = self._build_design_matrix(train_df["sale_date"], category, fest_lookup, t0)

        # Fallback without the `prophet` library: same decomposition fitted by ridge regression
        # Ridge regression closed-form solution: (X^T X + λI)^{-1} X^T y
        n_feat = X_train.shape[1]
        reg_mat = np.eye(n_feat, dtype=np.float64) * self.ridge_alpha
        reg_mat[0, 0] = 0.0  # Do not regularize intercept
        beta = np.linalg.solve(X_train.T @ X_train + reg_mat, X_train.T @ y_train_log)

        X_future = self._build_design_matrix(future_dates, category, fest_lookup, t0)
        pred_log = X_future @ beta
        # Smearing correction for log-normal residuals
        resid = y_train_log - (X_train @ beta)
        smear = float(np.mean(np.exp(resid)))
        preds = np.expm1(pred_log) * min(max(smear, 0.95), 1.08)
        return np.maximum(0.0, preds)

    def _fit_predict_prophet(
        self,
        train_df: pd.DataFrame,
        y_train_log: np.ndarray,
        future_dates: pd.DatetimeIndex,
        category: str,
        fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
        t0: pd.Timestamp,
    ) -> np.ndarray:
        """Real Prophet: trend + weekly + yearly seasonality, festival and climate signals as extra regressors."""
        import logging

        from prophet import Prophet

        logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

        def regressors(dates: pd.Series | pd.DatetimeIndex) -> pd.DataFrame:
            X = self._build_design_matrix(dates, category, fest_lookup, t0)
            # Last three columns of the design matrix: log climate index, festival flag, log festival multiplier
            return pd.DataFrame({"climate": X[:, -3], "is_fest": X[:, -2], "fest_log_mult": X[:, -1]})

        hist = pd.DataFrame({"ds": pd.to_datetime(train_df["sale_date"]).to_numpy(), "y": y_train_log})
        hist = pd.concat([hist, regressors(train_df["sale_date"])], axis=1)
        m = Prophet(
            yearly_seasonality=self.fourier_order,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        for col in ("climate", "is_fest", "fest_log_mult"):
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
class GlobalLGBMForecaster:
    """
    Task 2E: Global Gradient Boosted Trees Forecaster (`HistGradientBoostingRegressor` —
    scikit-learn's native LightGBM histogram algorithm) trained jointly across all series.

    Engineered Features:
    - Lag & Rolling statistics anchored at origin T (deseasonalized series level & momentum):
      `deseason_mean_7d`, `deseason_mean_14d`, `deseason_mean_28d`, `deseason_mean_60d`,
      `raw_lag_7`, `raw_mean_14d`, `raw_std_14d`, `dow_specific_mean_4w`
    - Target Date Calendar & Cyclical features:
      `day_of_week`, `is_weekend`, `month`, `day_of_year`, `weekly_mult`, `trend_factor`
    - Category & Moving Pakistani Festival features:
      `category_id`, `climate_seasonal_idx`, `is_festival_day`, `festival_multiplier`,
      ` Structural_Expected_Baseline = deseason_level * trend * weekly_mult * climate_idx * fest_mult`
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
        self.model: HistGradientBoostingRegressor | None = None
        self.cat_to_code: dict[str, int] = {}

    @staticmethod
    def _compute_structural_divisor(
        dates: pd.Series | pd.DatetimeIndex,
        category: str,
        fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        dt = pd.to_datetime(dates)
        dow = np.asarray(dt.dt.day_of_week if hasattr(dt, "dt") else dt.day_of_week, dtype=int)
        doy = np.asarray(dt.dt.day_of_year if hasattr(dt, "dt") else dt.day_of_year, dtype=np.float64)
        month = np.asarray(dt.dt.month if hasattr(dt, "dt") else dt.month, dtype=int)

        days_since_start = np.asarray(
            (dt - pd.Timestamp("2024-01-01")).dt.days
            if hasattr(dt, "dt")
            else (dt - pd.Timestamp("2024-01-01")).days,
            dtype=np.float64,
        )
        trend_mult = 1.0 + 0.18 * (days_since_start / 730.0)
        weekly_mult = np.where(dow == 4, 1.25, np.where(dow >= 5, 1.35, 0.92))
        climate_mult = _category_climate_index(category, doy, month)
        fest_mult = np.array(
            [fest_lookup.get((pd.Timestamp(d), category), (1.0, 0, ""))[0] for d in dt],
            dtype=np.float64,
        )
        return trend_mult, weekly_mult, climate_mult, fest_mult

    def _build_series_training_panel(
        self,
        series_df: pd.DataFrame,
        series_id: int,
        category: str,
        fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
    ) -> tuple[np.ndarray, np.ndarray]:
        df = series_df.sort_values("sale_date").reset_index(drop=True)
        y = df["units_sold"].to_numpy(dtype=np.float64)
        n = len(y)

        trend_m, week_m, clim_m, fest_m = self._compute_structural_divisor(
            df["sale_date"], category, fest_lookup
        )
        total_mult = np.maximum(trend_m * week_m * clim_m * fest_m, 0.05)
        deseason_y = y / total_mult

        s_des = pd.Series(deseason_y)
        s_raw = pd.Series(y)

        des_7 = s_des.shift(1).rolling(7, min_periods=3).mean().to_numpy()
        des_14 = s_des.shift(1).rolling(14, min_periods=5).mean().to_numpy()
        des_28 = s_des.shift(1).rolling(28, min_periods=7).mean().to_numpy()
        des_60 = s_des.shift(1).rolling(60, min_periods=14).mean().to_numpy()

        raw_lag7 = s_raw.shift(7).to_numpy()
        raw_mean14 = s_raw.shift(1).rolling(14, min_periods=5).mean().to_numpy()
        raw_std14 = s_raw.shift(1).rolling(14, min_periods=5).std().fillna(0.0).to_numpy()

        dt = pd.to_datetime(df["sale_date"])
        dow = dt.dt.day_of_week.to_numpy(dtype=np.float64)
        month = dt.dt.month.to_numpy(dtype=np.float64)
        doy = dt.dt.day_of_year.to_numpy(dtype=np.float64)
        cat_code = float(self.cat_to_code.get(category, 0))

        base_est = 0.15 * des_7 + 0.25 * des_14 + 0.35 * des_28 + 0.25 * des_60
        structural_expected = base_est * total_mult

        X_all = np.column_stack(
            [
                np.full(n, series_id, dtype=np.float64),
                np.full(n, cat_code, dtype=np.float64),
                des_7,
                des_14,
                des_28,
                des_60,
                raw_lag7,
                raw_mean14,
                raw_std14,
                dow,
                (dow >= 4).astype(np.float64),
                month,
                doy,
                trend_m,
                week_m,
                clim_m,
                fest_m,
                (fest_m > 1.01).astype(np.float64),
                structural_expected,
            ]
        )

        valid = ~np.isnan(X_all).any(axis=1)
        # Predict residual adjustment ratio around structural expectation for stability across scales
        return X_all[valid], y[valid] - structural_expected[valid]

    def fit_and_predict_panel(
        self,
        series_dict: dict[str, tuple[pd.DataFrame, str]],
        future_dates: pd.DatetimeIndex,
        fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
    ) -> dict[str, np.ndarray]:
        """Fit a single Global HistGradientBoostingRegressor on all series and predict `future_dates`."""
        all_cats = sorted({cat for _, cat in series_dict.values()})
        self.cat_to_code = {c: idx for idx, c in enumerate(all_cats)}

        X_parts: list[np.ndarray] = []
        y_parts: list[np.ndarray] = []

        for s_idx, (s_key, (train_df, cat)) in enumerate(series_dict.items()):
            Xs, ys = self._build_series_training_panel(
                series_df=train_df,
                series_id=s_idx,
                category=cat,
                fest_lookup=fest_lookup,
            )
            if len(Xs) > 0:
                X_parts.append(Xs)
                y_parts.append(ys)

        X_train = np.vstack(X_parts)
        y_train_resid = np.concatenate(y_parts)

        self.model = _make_gbm_regressor(
            max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            max_leaf_nodes=self.max_leaf_nodes,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
        )
        self.model.fit(X_train, y_train_resid)

        predictions: dict[str, np.ndarray] = {}
        h = len(future_dates)
        dow = future_dates.day_of_week.to_numpy(dtype=np.float64)
        month = future_dates.month.to_numpy(dtype=np.float64)
        doy = future_dates.day_of_year.to_numpy(dtype=np.float64)

        for s_idx, (s_key, (train_df, cat)) in enumerate(series_dict.items()):
            df = train_df.sort_values("sale_date").reset_index(drop=True)
            y_hist = df["units_sold"].to_numpy(dtype=np.float64)
            t_m, w_m, c_m, f_m = self._compute_structural_divisor(
                df["sale_date"], cat, fest_lookup
            )
            tot_m = np.maximum(t_m * w_m * c_m * f_m, 0.05)
            des_hist = y_hist / tot_m

            des_7 = float(np.mean(des_hist[-7:]))
            des_14 = float(np.mean(des_hist[-14:]))
            des_28 = float(np.mean(des_hist[-28:]))
            des_60 = float(np.mean(des_hist[-min(60, len(des_hist)) :]))

            last_7_raw = y_hist[-7:]
            reps = int(np.ceil(h / 7.0))
            raw_lag7_vec = np.tile(last_7_raw, reps)[:h]
            raw_mean14 = float(np.mean(y_hist[-14:]))
            raw_std14 = float(np.std(y_hist[-14:]))

            fut_t_m, fut_w_m, fut_c_m, fut_f_m = self._compute_structural_divisor(
                future_dates, cat, fest_lookup
            )
            fut_tot_m = np.maximum(fut_t_m * fut_w_m * fut_c_m * fut_f_m, 0.05)
            base_est = 0.15 * des_7 + 0.25 * des_14 + 0.35 * des_28 + 0.25 * des_60
            structural_expected = base_est * fut_tot_m

            cat_code = float(self.cat_to_code.get(cat, 0))
            X_fut = np.column_stack(
                [
                    np.full(h, s_idx, dtype=np.float64),
                    np.full(h, cat_code, dtype=np.float64),
                    np.full(h, des_7, dtype=np.float64),
                    np.full(h, des_14, dtype=np.float64),
                    np.full(h, des_28, dtype=np.float64),
                    np.full(h, des_60, dtype=np.float64),
                    raw_lag7_vec,
                    np.full(h, raw_mean14, dtype=np.float64),
                    np.full(h, raw_std14, dtype=np.float64),
                    dow,
                    (dow >= 4).astype(np.float64),
                    month,
                    doy,
                    fut_t_m,
                    fut_w_m,
                    fut_c_m,
                    fut_f_m,
                    (fut_f_m > 1.01).astype(np.float64),
                    structural_expected,
                ]
            )
            resid_pred = self.model.predict(X_fut)
            # Blend structural expectation with dampened tree residual correction
            final_pred = np.maximum(0.0, structural_expected + 0.35 * resid_pred)
            predictions[s_key] = final_pred

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
    fest_lookup: dict[tuple[pd.Timestamp, str], tuple[float, int, str]],
    breakdown_sink: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """
    Run 4-Fold Rolling-Origin Backtesting for all 7 models across 7d, 14d, and 30d horizons.
    If `breakdown_sink` is given, also append accuracy at BREAKDOWN_HORIZON split by festival vs regular days and
    by velocity tier.
    """
    panel = panel_df.copy()
    panel["sale_date"] = pd.to_datetime(panel["sale_date"])
    series_ids = sorted(panel[id_col].unique().tolist())

    m1_naive = NaiveForecaster()
    m2_snaive = SeasonalNaive7DForecaster()
    m3_ets = HoltWintersETSForecaster()
    m4_prophet = ProphetFourierHolidayForecaster(fourier_order=6, ridge_alpha=1.5)
    m5_lgbm = GlobalLGBMForecaster()
    m6_croston = CrostonSBAForecaster()
    m7_tsb = TSBForecaster()

    model_names = [
        m1_naive.name,
        m2_snaive.name,
        m3_ets.name,
        m4_prophet.name,
        m5_lgbm.name,
        m6_croston.name,
        m7_tsb.name,
    ]

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
            fest_lookup=fest_lookup,
        )

        # Fit & predict local models per series
        for sid_str, (tr_s, cat) in series_train_dict.items():
            y_actual_30 = series_test_dict[sid_str]
            p_naive = m1_naive.fit_predict_series(tr_s, future_dates)
            p_snaive = m2_snaive.fit_predict_series(tr_s, future_dates)
            p_ets = m3_ets.fit_predict_series(tr_s, future_dates)
            p_prophet = m4_prophet.fit_predict_series(tr_s, future_dates, cat, fest_lookup)
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

            for h in HORIZONS:
                for m_name, p_vec in preds_by_model.items():
                    collector[(m_name, h)][0].append(y_actual_30[:h])
                    collector[(m_name, h)][1].append(p_vec[:h])

            if breakdown_sink is not None:
                h = BREAKDOWN_HORIZON
                fest_flags = np.array(
                    [bool(fest_lookup.get((pd.Timestamp(dt), cat), (1.0, 0, ""))[1]) for dt in future_dates[:h]]
                )
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
        "ShopKaro AI — Day 3 Tasks 2 & 3: 4-Fold Rolling-Origin Backtesting (7 Models x 3 Horizons)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    cat_df = backtest_df[backtest_df["hierarchy_level"] == "Category_Level"]
    sku_df = backtest_df[backtest_df["hierarchy_level"] == "Top50_SKU_Level"]

    colors = {7: "#6baed6", 14: "#3182bd", 30: "#08519c"}
    short_models = [
        "1. Naive",
        "2. Seasonal Naive (7d)",
        "3. Holt-Winters ETS",
        "4. Prophet (Holidays)",
        "5. Global LightGBM",
        "6. Croston-SBA",
        "7. TSB",
    ]
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

    all_categories = sorted(category_df["category"].astype(str).unique().tolist())
    fest_lookup = _build_date_category_festival_lookup(
        festival_cal_df=festival_cal_df,
        all_categories=all_categories,
    )

    breakdown: list[dict[str, Any]] = []
    cat_backtest_df = _evaluate_panel_across_folds(
        panel_df=category_df,
        id_col="category",
        hierarchy_label="Category_Level",
        fest_lookup=fest_lookup,
        breakdown_sink=breakdown,
    )
    sku_backtest_df = _evaluate_panel_across_folds(
        panel_df=top50_sku_df,
        id_col="product_id",
        hierarchy_label="Top50_SKU_Level",
        fest_lookup=fest_lookup,
        breakdown_sink=breakdown,
    )
    vel_backtest_df = _evaluate_panel_across_folds(
        panel_df=velocity_df,
        id_col="product_id",
        hierarchy_label="SKU_By_Velocity_60",
        fest_lookup=fest_lookup,
        breakdown_sink=breakdown,
    )

    full_backtest_df = pd.concat([cat_backtest_df, sku_backtest_df, vel_backtest_df], ignore_index=True)

    csv_out = settings.reports_dir / "day3_forecasting_backtest_comparison.csv"
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    full_backtest_df.to_csv(csv_out, index=False)
    pd.DataFrame(breakdown).to_csv(settings.reports_dir / "day3_forecast_accuracy_breakdown.csv", index=False)

    fig_out = settings.figures_dir / "11_forecasting_backtest_comparison.png"
    plot_backtest_comparison_chart(full_backtest_df, output_path=fig_out)

    return full_backtest_df, fig_out

