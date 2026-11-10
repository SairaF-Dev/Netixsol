"""
Day 3 — Task 1: Time-Series Analysis, Seasonal Decomposition, ADF Stationarity & Festival Spikes.

Implements:
1. Three-level daily demand aggregation (`731` days: `2024-01-01` to `2025-12-31`):
   - Level 1: Platform Total (`731` rows)
   - Level 2: Category Level (`11 categories x 731 days = 8,041` rows)
   - Level 3: Top-50 Products Level (`50 SKUs x 731 days = 36,550` rows)
2. Classical & Calendar Decomposition:
   - 28-day centered Trend, 7-day Day-of-Week Seasonality, Monthly/Seasonal wave, and Residual shocks
3. Augmented Dickey-Fuller (ADF) Stationarity Test Suite:
   - Tests raw series Y_t and first-differenced series ΔY_t across Platform + all 11 Categories
4. Pakistani Festival Uplift & Moving Hijri Lunar Shift Analysis:
   - Quantifies uplift multipliers across all 17 festival windows (2024–2025)
   - Measures the ~11-day earlier Gregorian shift of Ramadan, Eid ul Fitr, and Eid ul Adha in 2025 vs 2024
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from shopkaro.config.settings import settings


@dataclass
class ADFStationarityRow:
    """Augmented Dickey-Fuller stationarity test result for raw and 1st-differenced series."""

    series_name: str
    hierarchy_level: str
    n_obs: int
    adf_stat_raw: float
    p_value_raw: float
    is_stationary_raw_5pct: bool
    adf_stat_diff1: float
    p_value_diff1: float
    is_stationary_diff1_5pct: bool
    crit_val_1pct: float
    crit_val_5pct: float
    crit_val_10pct: float
    recommended_differencing_d: int


@dataclass
class LunarFestivalShiftRow:
    """Comparison of 2024 vs 2025 festival dates and observed demand uplift."""

    festival_base_name: str
    calendar_type: str
    start_2024: str
    start_2025: str
    gregorian_shift_days: int
    avg_daily_units_festival: float
    avg_daily_units_baseline: float
    observed_uplift_multiplier: float


def compute_adf_test(y: np.ndarray, max_lags: int = 7) -> tuple[float, float, dict[str, float]]:
    """
    Execute Augmented Dickey-Fuller (ADF) unit-root test with constant:
        Δy_t = α + γ * y_{t-1} + sum_{j=1}^{p} δ_j * Δy_{t-j} + e_t
    Returns `(adf_t_stat, approx_p_value, critical_values)`.
    """
    arr = np.asarray(y, dtype=np.float64)
    dy = np.diff(arr)
    n = len(dy)
    p = min(max_lags, max(1, n // 15))

    # Target: Δy_t for t = p .. n-1
    target = dy[p:]
    y_lag1 = arr[p:-1]

    # Design matrix: [1, y_{t-1}, Δy_{t-1}, ..., Δy_{t-p}]
    cols = [np.ones_like(y_lag1), y_lag1]
    for lag in range(1, p + 1):
        cols.append(dy[p - lag : n - lag])
    X = np.column_stack(cols)

    # OLS fit via QR/SVD
    beta, _, _, _ = np.linalg.lstsq(X, target, rcond=None)
    resid = target - X @ beta
    dof = max(len(target) - X.shape[1], 1)
    sigma2 = float(np.dot(resid, resid) / dof)
    cov_beta = sigma2 * np.linalg.pinv(X.T @ X)
    se_gamma = float(np.sqrt(max(cov_beta[1, 1], 1e-15)))
    adf_stat = float(beta[1] / se_gamma)

    # MacKinnon (2010) critical values for ADF with constant (N >= 500)
    crit = {"1%": -3.439, "5%": -2.865, "10%": -2.569}

    # Smooth MacKinnon p-value approximation for constant-only specification
    if adf_stat <= -6.0:
        p_val = 0.0001
    elif adf_stat <= crit["1%"]:
        p_val = float(0.01 * np.exp(0.95 * (adf_stat - crit["1%"])))
    elif adf_stat <= crit["5%"]:
        p_val = float(0.01 + 0.04 * (adf_stat - crit["1%"]) / (crit["5%"] - crit["1%"]))
    elif adf_stat <= crit["10%"]:
        p_val = float(0.05 + 0.05 * (adf_stat - crit["5%"]) / (crit["10%"] - crit["5%"]))
    else:
        p_val = float(min(0.99, 0.10 + 0.85 * stats.norm.cdf(adf_stat + 1.5)))

    return round(adf_stat, 4), round(p_val, 5), crit


def build_three_level_timeseries(
    con: duckdb.DuckDBPyConnection,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Build the 3 hierarchy levels from `daily_sales`:
    1. `platform_daily_df`: 731 days of total ShopKaro units & PKR revenue.
    2. `category_daily_df`: 11 categories x 731 days = 8,041 rows.
    3. `top50_sku_daily_df`: Top 50 SKUs by total units x 731 days = 36,550 rows.
    """
    platform_daily_df = con.execute(
        """
        SELECT
            CAST(sale_date AS TIMESTAMP) AS sale_date,
            SUM(units_sold) AS units_sold,
            SUM(revenue_pkr) AS revenue_pkr,
            COUNT(DISTINCT product_id) AS active_skus,
            BOOL_OR(is_festival_day) AS is_festival_day,
            ANY_VALUE(festival_name) AS festival_name
        FROM daily_sales
        GROUP BY sale_date
        ORDER BY sale_date;
        """
    ).df()

    category_daily_df = con.execute(
        """
        SELECT
            CAST(sale_date AS TIMESTAMP) AS sale_date,
            category,
            SUM(units_sold) AS units_sold,
            SUM(revenue_pkr) AS revenue_pkr,
            BOOL_OR(is_festival_day) AS is_festival_day,
            ANY_VALUE(festival_name) AS festival_name
        FROM daily_sales
        GROUP BY sale_date, category
        ORDER BY category, sale_date;
        """
    ).df()

    top50_sku_daily_df = con.execute(
        """
        WITH top50 AS (
            SELECT
                product_id,
                SUM(units_sold) AS total_units
            FROM daily_sales
            GROUP BY product_id
            ORDER BY total_units DESC
            LIMIT 50
        )
        SELECT
            CAST(d.sale_date AS TIMESTAMP) AS sale_date,
            d.product_id,
            d.category,
            d.brand,
            d.velocity_tier,
            d.units_sold,
            d.unit_price_pkr,
            d.revenue_pkr,
            d.is_festival_day,
            d.festival_name
        FROM daily_sales d
        JOIN top50 t ON d.product_id = t.product_id
        ORDER BY d.product_id, d.sale_date;
        """
    ).df()

    return platform_daily_df, category_daily_df, top50_sku_daily_df


def decompose_platform_timeseries(platform_daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Decompose Platform Daily Demand into:
    - `trend_28d`: 28-day centered moving average
    - `weekly_seasonal`: Day-of-week seasonal effect (Mon=0 .. Sun=6)
    - `residual`: Irregular shock + festival surge
    """
    df = platform_daily_df.copy().sort_values("sale_date").reset_index(drop=True)
    df["sale_date"] = pd.to_datetime(df["sale_date"])
    df["day_of_week"] = df["sale_date"].dt.day_name()
    df["dow_idx"] = df["sale_date"].dt.day_of_week
    df["month"] = df["sale_date"].dt.month

    # 28-day centered moving average for smooth trend
    df["trend_28d"] = (
        df["units_sold"].rolling(window=28, center=True, min_periods=7).mean()
    )
    detrended = df["units_sold"] - df["trend_28d"]

    # Day-of-week seasonal component (zero-centered)
    dow_means = detrended.groupby(df["dow_idx"]).transform("mean")
    df["weekly_seasonal"] = dow_means - dow_means.mean()

    # Residual (captures festival spikes + random variation)
    df["residual"] = df["units_sold"] - df["trend_28d"] - df["weekly_seasonal"]
    return df


def run_adf_stationarity_suite(
    platform_daily_df: pd.DataFrame,
    category_daily_df: pd.DataFrame,
) -> pd.DataFrame:
    """Run ADF tests on raw and 1st-differenced series for Platform Total and all 11 Categories."""
    rows: list[ADFStationarityRow] = []

    # 1. Platform Total
    y_plat = platform_daily_df["units_sold"].to_numpy(dtype=float)
    stat_raw, p_raw, crit = compute_adf_test(y_plat, max_lags=7)
    stat_d1, p_d1, _ = compute_adf_test(np.diff(y_plat), max_lags=7)
    rows.append(
        ADFStationarityRow(
            series_name="ShopKaro Platform Total",
            hierarchy_level="Platform",
            n_obs=len(y_plat),
            adf_stat_raw=stat_raw,
            p_value_raw=p_raw,
            is_stationary_raw_5pct=bool(stat_raw < crit["5%"]),
            adf_stat_diff1=stat_d1,
            p_value_diff1=p_d1,
            is_stationary_diff1_5pct=bool(stat_d1 < crit["5%"]),
            crit_val_1pct=crit["1%"],
            crit_val_5pct=crit["5%"],
            crit_val_10pct=crit["10%"],
            recommended_differencing_d=0 if stat_raw < crit["5%"] else 1,
        )
    )

    # 2. All 11 Categories
    for cat, grp in category_daily_df.groupby("category"):
        y_cat = grp.sort_values("sale_date")["units_sold"].to_numpy(dtype=float)
        s_raw, pv_raw, c_dict = compute_adf_test(y_cat, max_lags=7)
        s_d1, pv_d1, _ = compute_adf_test(np.diff(y_cat), max_lags=7)
        rows.append(
            ADFStationarityRow(
                series_name=str(cat),
                hierarchy_level="Category",
                n_obs=len(y_cat),
                adf_stat_raw=s_raw,
                p_value_raw=pv_raw,
                is_stationary_raw_5pct=bool(s_raw < c_dict["5%"]),
                adf_stat_diff1=s_d1,
                p_value_diff1=pv_d1,
                is_stationary_diff1_5pct=bool(s_d1 < c_dict["5%"]),
                crit_val_1pct=c_dict["1%"],
                crit_val_5pct=c_dict["5%"],
                crit_val_10pct=c_dict["10%"],
                recommended_differencing_d=0 if s_raw < c_dict["5%"] else 1,
            )
        )

    return pd.DataFrame([asdict(r) for r in rows])


def analyze_festival_spikes_and_lunar_shift(
    con: duckdb.DuckDBPyConnection,
    platform_daily_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    1. Calculate observed demand uplift across all festival windows in `daily_sales`.
    2. Quantify the 2024 vs 2025 Hijri lunar date shift (~11 days earlier) vs Gregorian fixed events.
    """
    baseline_avg = float(
        platform_daily_df.loc[~platform_daily_df["is_festival_day"], "units_sold"].mean()
    )

    fest_summary_df = (
        platform_daily_df[platform_daily_df["is_festival_day"]]
        .groupby("festival_name", as_index=False)
        .agg(
            festival_days=("sale_date", "count"),
            start_date=("sale_date", "min"),
            end_date=("sale_date", "max"),
            avg_daily_units=("units_sold", "mean"),
            peak_daily_units=("units_sold", "max"),
            total_festival_revenue_pkr=("revenue_pkr", "sum"),
        )
    )
    fest_summary_df["baseline_daily_units"] = round(baseline_avg, 1)
    fest_summary_df["observed_uplift_multiplier"] = (
        fest_summary_df["avg_daily_units"] / max(baseline_avg, 1.0)
    ).round(2)
    fest_summary_df = fest_summary_df.sort_values(
        "observed_uplift_multiplier", ascending=False
    ).reset_index(drop=True)

    # Compare 2024 vs 2025 start dates from `festival_calendar`
    cal_df = con.execute("SELECT * FROM festival_calendar ORDER BY start_date").df()
    cal_df["start_date"] = pd.to_datetime(cal_df["start_date"])
    cal_df["year"] = cal_df["start_date"].dt.year
    cal_df["base_name"] = (
        cal_df["festival_name"]
        .astype(str)
        .str.replace(" 2024", "", regex=False)
        .str.replace(" 2025", "", regex=False)
        .str.strip()
    )

    shift_rows: list[LunarFestivalShiftRow] = []
    for base_name, grp in cal_df.groupby("base_name"):
        g24 = grp[grp["year"] == 2024]
        g25 = grp[grp["year"] == 2025]
        if g24.empty or g25.empty:
            continue
        d24 = pd.Timestamp(g24.iloc[0]["start_date"])
        d25 = pd.Timestamp(g25.iloc[0]["start_date"])
        # Compare day-of-year difference between 2025 and 2024
        # (Account for 2024 leap year after Feb 29)
        d24_same_year = pd.Timestamp(year=2025, month=d24.month, day=d24.day)
        shift_days = int((d25 - d24_same_year).days)
        cal_type = str(g24.iloc[0]["festival_type"])

        matched = fest_summary_df[
            fest_summary_df["festival_name"].str.startswith(str(base_name))
        ]
        avg_fest_u = (
            float(matched["avg_daily_units"].mean()) if not matched.empty else baseline_avg
        )
        shift_rows.append(
            LunarFestivalShiftRow(
                festival_base_name=str(base_name),
                calendar_type=cal_type,
                start_2024=d24.strftime("%Y-%m-%d"),
                start_2025=d25.strftime("%Y-%m-%d"),
                gregorian_shift_days=shift_days,
                avg_daily_units_festival=round(avg_fest_u, 1),
                avg_daily_units_baseline=round(baseline_avg, 1),
                observed_uplift_multiplier=round(avg_fest_u / max(baseline_avg, 1.0), 2),
            )
        )

    lunar_shift_df = pd.DataFrame([asdict(r) for r in shift_rows]).sort_values(
        "observed_uplift_multiplier", ascending=False
    )
    return fest_summary_df, lunar_shift_df


def plot_task1_diagnostics(
    decomp_df: pd.DataFrame,
    fest_summary_df: pd.DataFrame,
    lunar_shift_df: pd.DataFrame,
) -> tuple[Path, Path]:
    """Generate diagnostic plots `09_timeseries_decomposition_and_seasonality.png` & `10_pakistani_festival_uplift_and_lunar_shift.png`."""
    settings.figures_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    # Figure 09: 4-Panel Time-Series Decomposition & Day-of-Week Seasonality
    fig9_path = settings.figures_dir / "09_timeseries_decomposition_and_seasonality.png"
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(
        "ShopKaro AI — Day 3 Task 1: Platform Daily Demand Decomposition & Seasonality (2024–2025)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    ax1 = axes[0, 0]
    ax1.plot(
        decomp_df["sale_date"],
        decomp_df["units_sold"],
        color="#1f77b4",
        alpha=0.65,
        linewidth=1.0,
        label="Daily Units Sold",
    )
    fest_pts = decomp_df[decomp_df["is_festival_day"]]
    ax1.scatter(
        fest_pts["sale_date"],
        fest_pts["units_sold"],
        color="#d62728",
        s=14,
        label="Pakistani Festival Days",
        zorder=3,
    )
    ax1.set_title("1. Observed Daily Demand & Festival Spikes (731 Days)", fontweight="bold")
    ax1.set_ylabel("Units Sold / Day")
    ax1.legend(loc="upper left")

    ax2 = axes[0, 1]
    ax2.plot(
        decomp_df["sale_date"],
        decomp_df["trend_28d"],
        color="#2ca02c",
        linewidth=2.2,
        label="28-Day Centered Trend",
    )
    ax2.set_title("2. Secular Marketplace Growth & Seasonal Wave (28d MA)", fontweight="bold")
    ax2.set_ylabel("Trend Units / Day")
    ax2.legend(loc="upper left")

    ax3 = axes[1, 0]
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_profile = (
        decomp_df.groupby("day_of_week")["units_sold"]
        .mean()
        .reindex(dow_order)
    )
    colors_dow = ["#9ecae1"] * 4 + ["#fd8d3c", "#e6550d", "#d94801"]
    bars = ax3.bar(
        [d[:3] for d in dow_order],
        dow_profile.values,
        color=colors_dow,
        width=0.6,
    )
    ax3.set_title(
        "3. Weekly Seasonality Profile (Jummah & Weekend Surge)",
        fontweight="bold",
    )
    ax3.set_ylabel("Mean Daily Units Sold")
    for b in bars:
        ax3.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 40,
            f"{b.get_height():,.0f}",
            ha="center",
            fontsize=8.5,
        )

    ax4 = axes[1, 1]
    ax4.plot(
        decomp_df["sale_date"],
        decomp_df["residual"],
        color="#9467bd",
        linewidth=0.9,
        alpha=0.8,
    )
    ax4.axhline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax4.set_title(
        "4. Decomposition Residuals (Stationary Noise + Festival Anomalies)",
        fontweight="bold",
    )
    ax4.set_ylabel("Residual Units")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(fig9_path, dpi=180)
    plt.close(fig)

    # Figure 10: Pakistani Festival Uplift & Hijri Lunar Shift
    fig10_path = settings.figures_dir / "10_pakistani_festival_uplift_and_lunar_shift.png"
    fig2, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 6.5))
    fig2.suptitle(
        "ShopKaro AI — Pakistani Festival Demand Multipliers & Moving Hijri Lunar Shift (2024 vs 2025)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    top_fests = fest_summary_df.head(12).iloc[::-1]
    b_left = ax_left.barh(
        top_fests["festival_name"],
        top_fests["observed_uplift_multiplier"],
        color="#e6550d",
        height=0.6,
    )
    ax_left.axvline(1.0, color="black", linestyle="--", linewidth=1.0, label="Regular Baseline (1.0x)")
    ax_left.set_title("1. Observed Demand Multiplier by Festival Window", fontweight="bold")
    ax_left.set_xlabel("Demand Uplift vs Regular Non-Festival Day (x)")
    for b in b_left:
        ax_left.text(
            b.get_width() + 0.03,
            b.get_y() + b.get_height() / 2,
            f"{b.get_width():.2f}x",
            va="center",
            fontsize=8.5,
        )
    ax_left.set_xlim(0, max(top_fests["observed_uplift_multiplier"]) * 1.18)

    shift_plot = lunar_shift_df.iloc[::-1]
    shift_colors = [
        "#d62728" if s < 0 else "#3182bd" for s in shift_plot["gregorian_shift_days"]
    ]
    b_right = ax_right.barh(
        shift_plot["festival_base_name"],
        shift_plot["gregorian_shift_days"],
        color=shift_colors,
        height=0.55,
    )
    ax_right.axvline(0, color="black", linewidth=1.1)
    ax_right.set_title(
        "2. 2025 vs 2024 Gregorian Date Shift (Lunar Holidays Move ~11 Days Earlier)",
        fontweight="bold",
    )
    ax_right.set_xlabel("Date Shift in 2025 vs 2024 (Days)")
    for b in b_right:
        w = b.get_width()
        offset = -1.2 if w < 0 else 0.4
        ax_right.text(
            w + offset,
            b.get_y() + b.get_height() / 2,
            f"{int(w):+d}d",
            va="center",
            fontsize=9,
            fontweight="bold",
        )
    ax_right.set_xlim(-15, 6)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig2.savefig(fig10_path, dpi=180)
    plt.close(fig2)

    return fig9_path, fig10_path


def run_day3_task1_timeseries_analysis(
    db_path: Path | None = None,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    tuple[Path, Path],
]:
    """
    Execute Day 3 — Task 1:
    1. Aggregate daily sales across Platform, 11 Categories, and Top-50 SKUs.
    2. Decompose Platform series into Trend, Weekly Seasonality, and Residual.
    3. Run ADF Stationarity tests on raw and 1st-differenced series across Platform + 11 Categories.
    4. Quantify Pakistani Festival Uplift & 2024-vs-2025 Hijri Lunar Shift.
    5. Save diagnostic charts 09 & 10.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)

    platform_df, category_df, top50_sku_df = build_three_level_timeseries(con)
    decomp_df = decompose_platform_timeseries(platform_df)
    adf_df = run_adf_stationarity_suite(platform_df, category_df)
    fest_summary_df, lunar_shift_df = analyze_festival_spikes_and_lunar_shift(con, platform_df)
    con.close()

    fig_paths = plot_task1_diagnostics(decomp_df, fest_summary_df, lunar_shift_df)
    return (
        platform_df,
        category_df,
        top50_sku_df,
        adf_df,
        fest_summary_df,
        lunar_shift_df,
        fig_paths,
    )
