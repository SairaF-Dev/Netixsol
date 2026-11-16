"""
ORACLE - not a forecasting model. Kept only as a clearly labelled upper bound in the Day 3 backtest.

This is the original "Global LightGBM" forecaster. It turned out to rebuild the data generator's own formula
(`shopkaro.data.synthesizer.generate_daily_sales_history`): the same weekly multipliers (0.92 / 1.25 / 1.35), the same
category season curves (lawn sine, winter 2.4 / 0.08), the same +18% trend, and the TRUE festival `demand_multiplier`
and `boost_categories` from the festival calendar. It then only learned a small correction on top of that formula.
A real retailer does not know those numbers, so its ~6% WAPE was not a real result.

The honest forecaster is `shopkaro.forecasting.models.GlobalLGBMForecaster`. Nothing in the inventory engine, the
inventory replay or the API uses this module; `tests/test_forecast_leakage.py` checks that.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from shopkaro.forecasting.models import _make_gbm_regressor

ORACLE_MODEL_NAME = "8. Oracle (Generator Formula - Upper Bound, Not a Real Model)"


def build_oracle_festival_lookup(
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


class OracleGeneratorFormulaForecaster:
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

    name = ORACLE_MODEL_NAME

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
        self.model = None
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
