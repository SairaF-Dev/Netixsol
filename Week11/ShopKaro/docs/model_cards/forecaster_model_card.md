# Model Card: ShopKaro Demand Forecaster and Inventory Policy

_Rewritten 2026-11-09 from the generated reports. An earlier version contained a results table, a safety-stock
formula and two business claims ("84.2% of pre-Eid stockouts prevented", "31.5% less dead capital") that no code
produced; they are removed._

## Model details
- **Point forecast:** global LightGBM (`lightgbm`, Python 3.11 venv; falls back to scikit-learn
  `HistGradientBoostingRegressor` when the library is missing) trained jointly on all series. Features:
  rolling means of the de-seasonalised series (7/14/28/60 days), raw lag-7, 14-day mean and standard deviation,
  same-weekday mean over 4 weeks, calendar features, and the Pakistani festival calendar (Ramadan, both Eids,
  Azadi, back to school, 11.11, Black Friday, wedding season) with their moving Hijri dates.
- **Intervals (P10 / P90):** P50 +- 1.28 x sigma, where sigma comes from an over-dispersed Poisson model
  (variance = mu + 0.1 mu^2) scaled per series by its recent residuals and widened slightly with the horizon.
- **Code:** `src/shopkaro/forecasting/models.py`, `inventory.py`, `inventory_backtest.py`.

## Intended use
Weekly re-ordering and stock alerts for the 300 SKUs that have daily sales history (2024-01-01..2025-12-31).
Not validated for other products, real ShopKaro data, or horizons beyond 30 days.

## Data
Daily unit sales are **synthetic**: generated per SKU from velocity tier, weekly pattern, category seasonality and
the festival calendar multipliers. The forecaster receives the same festival calendar, so accuracy here is an upper
bound on what to expect with real sales.

## Accuracy: 4-fold rolling-origin backtest
Cut-offs 2025-03-15 (Eid ul Fitr), 2025-05-25 (Eid ul Adha), 2025-08-08 (Azadi / back to school), 2025-11-05
(11.11 / winter). 14-day horizon (7 and 30 days in `reports/day3_forecasting_backtest_comparison.csv`):

| Model | Category WAPE | Category MAE (units/day) | Top-50 SKU WAPE | Top-50 SKU MAE |
| :--- | :---: | :---: | :---: | :---: |
| Naive (Last Observed Value) | 42.9% | 333.7 | 52.4% | 40.3 |
| Seasonal Naive (7-Day Cycle) | 42.3% | 329.2 | 52.7% | 40.5 |
| Classical Holt-Winters ETS (s=7) | 41.8% | 325.6 | 49.8% | 38.3 |
| Prophet (Fourier + Moving Islamic Holidays) | 6.2% | 48.4 | 27.3% | 21.0 |
| Global LightGBM (Lags + Rolling + Festival Features) | 6.0% | 47.0 | 26.5% | 20.3 |
| Croston-SBA (intermittent demand, alpha 0.1) | 47.9% | 373.1 | 52.7% | 40.5 |
| TSB (intermittent demand, alpha = beta = 0.1) | 46.4% | 361.3 | 51.5% | 39.6 |

The seasonal naive baseline here repeats last week (7-day cycle). The brief's target, beating seasonal naive on
WAPE, is met at every level and horizon.

**Interval calibration** (30 days after 2025-03-15, 300 SKUs): 79.0% of actual values fall inside P10-P90 (target
80%), 0 quantile crossings.

## Inventory policy
Safety stock SS = z * sqrt(L * sigma_D^2 + D^2 * (0.15 L)^2), reorder point = D * L + SS, with L the product's
catalogue lead time (3-11 days) and z = 1.645 (>= 3 units/day) or 1.282. Alert rules: `docs/user_guides/operations_guide.md`.

**2025 replay** (weekly re-ordering, lost sales, `reports/day3_inventory_backtest.csv`):

| Policy (weekly re-order, same safety-stock rule) | Fill rate | Lost units | Lost gross margin (PKR) | Stock-out SKU-days | Lost units, Ramadan + Eid ul Fitr | Lost units, Eid ul Adha | Avg stock value (PKR) | Avg dead capital (PKR) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 28-day moving average | 87.4% | 238,290 | 850.1M | 6,495 | 105,849 | 59,570 | 561.6M | 7.9M |
| Same days last year (seasonal naive) | 92.0% | 151,881 | 481.9M | 4,523 | 69,944 | 51,514 | 466.5M | 0.3M |
| **Forecast-driven (P50 + forecast uncertainty)** | 98.7% | 24,442 | 109.6M | 2,363 | 4,415 | 3,465 | 438.9M | 0.1M |

Forecast-driven ordering lost 90% fewer units than a 28-day moving average and
84% fewer than same-days-last-year, while holding 22% /
6% less stock. Because the synthetic demand follows the calendar the model is given,
treat this as evidence the mechanism works, not as an expected saving.

## Calibration and segments (added 2026-11-10)
- P90 covered actual demand on 87.6% of SKU-days (target 90%); P10 was below actual on 91.2% (target 90%).
- Festival days are forecast as well as regular days by Prophet / LightGBM (category WAPE ~6%), unlike the baselines.
- **Slow / intermittent movers (checked 2026-11-10):** 67% of their days sell nothing, so per-day WAPE is above 100%
  for every model, Croston and TSB included (forecasting zero scores exactly 100%, yet is useless for stocking).
  Reordering uses the 14-day *total*, and on that LightGBM is the best model: total error 49.6%, bias +1.5% on the
  4 festival folds, and 41.9% / +4.2% on 8 extra mostly non-festival cut-offs, vs Croston-SBA 58.4% / 48.8% and TSB
  60.5% / 54.1% (both under-forecast festival weeks by ~42% because they ignore the calendar). Croston / TSB were
  therefore **not** adopted; slow movers stay on LightGBM. `reports/day3_forecast_accuracy_breakdown.csv`
  (`total_wape_pct`, `total_bias_pct`), `scripts/run_day3_slow_mover_check.py`.

## Limitations
- Synthetic demand and synthetic stock levels; no real sales were available.
- The plan is made from one snapshot date (2025-03-15); in production it would run daily.
- Stock-out days in the training history are not corrected for (lost sales would bias forecasts low on real data).
- Lead-time variability (15%) is assumed, not measured.
