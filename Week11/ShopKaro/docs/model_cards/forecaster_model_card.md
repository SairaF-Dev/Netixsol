# Model Card: ShopKaro Demand Forecaster and Inventory Policy

_Rewritten 2026-11-16 after a leakage fix (see "Correction" below). All numbers come from the current reports._

## Correction (2026-11-16): the earlier forecaster copied the data generator
The daily sales are synthetic. The previous "Global LightGBM" was given the generator's own formula: the same
weekly multipliers (0.92 / 1.25 / 1.35), the same category season curves, the same +18% trend and the **true festival
multipliers** from the calendar. It then only learned a small correction on top. Its 6.0% category WAPE and 79%
interval coverage were therefore not real results, and neither was the "90% fewer lost units" replay figure.

What changed:
- The forecasters now see only past sales and the festival calendar's **names, types and dates**
  (`src/shopkaro/forecasting/festivals.py`). How much a festival lifts sales is learned from the series' own history.
- The intervals no longer assume the generator's noise formula; they come from conformal prediction (below).
- The old model is kept as a labelled **oracle** row in the backtest ("upper bound, not a real model",
  `src/shopkaro/forecasting/oracle.py`) so the gap is visible. The inventory engine, replay and API never use it.
- `tests/test_forecast_leakage.py` blocks a repeat: the honest code may not read the answer columns, and in an
  "altered world" (sales made with different rules, e.g. Ramadan lowering sales) the honest LightGBM must beat
  seasonal naive and the oracle. Result: honest 15.4% WAPE, seasonal naive 64.6%, oracle 63.5%.

## Model details
- **Point forecast (P50):** one global LightGBM model (`lightgbm`; scikit-learn `HistGradientBoostingRegressor`
  if the library is missing) across all products, direct multi-horizon (1-42 days). For an origin day and a
  target day it sees:
  - recent level and volatility (7 / 28 / 91-day means, 28-day standard deviation, share of zero-sale days)
  - same-weekday average of the last 4 weeks (weekly pattern, learned)
  - last year around the target date relative to last year's level, plus whether last year's date was a festival
    (Islamic festivals move ~11 days a year, so "same date last year" can be wrong)
  - target-date calendar (weekday, month, day of year), horizon, category
  - which festivals run on the target date, and how much each one lifted this product the previous time and so far
    this time (from sales up to the origin only)

  Target = sales / (28-day level + 0.1), weighted by that level so the fit matches WAPE. A festival that has never
  happened before the origin (e.g. "Spring Back to School", first held in 2025) is treated as a regular day: there is
  no history to learn its effect from.
- **Prophet (compared, not used for inventory):** trend + weekly + yearly Fourier (order 10) + one regressor per
  festival built from its dates; Prophet learns each festival's effect.
- **Intervals (P10 / P90): split conformal prediction.** The same model is refitted twice on data that ends 28 days
  before the origin and 364 days before it (same season last year), and its errors on those known 28-day windows are
  collected. The 10th / 90th percentiles of the errors, grouped by forecast size (quintiles) and horizon
  (1-7 / 8-14 / 15+ days), are added to P50. No noise distribution is assumed.
- **Code:** `src/shopkaro/forecasting/models.py`, `festivals.py`, `inventory.py`, `inventory_backtest.py`.

## Intended use
Weekly re-ordering and stock alerts for the 300 products with daily sales history (2024-01-01..2025-12-31).
Not validated for other products, real ShopKaro data, or horizons beyond 42 days.

## Data
Daily unit sales are **synthetic**: generated per product from a velocity tier, a weekly pattern, a category season
curve and festival multipliers (`shopkaro.data.synthesizer`). The forecasters do not receive any of those
parameters. The synthetic sales still repeat the same rules every year, which real sales do not, so real accuracy
would be lower.

## Accuracy: 4-fold rolling-origin backtest
Cut-offs 2025-03-15 (Eid ul Fitr), 2025-05-25 (Eid ul Adha), 2025-08-08 (Azadi / back to school), 2025-11-05
(11.11 / winter). 14-day horizon (7 and 30 days in `reports/day3_forecasting_backtest_comparison.csv`):

| Model | Category WAPE | Category MAE (units/day) | Top-50 SKU WAPE | Top-50 SKU MAE |
| :--- | :---: | :---: | :---: | :---: |
| Naive (last observed value) | 42.9% | 333.7 | 52.4% | 40.3 |
| Seasonal naive (7-day cycle) | 42.3% | 329.2 | 52.7% | 40.5 |
| Holt-Winters ETS (s=7) | 41.8% | 325.6 | 49.8% | 38.3 |
| Prophet (festival regressors) | **15.2%** | 118.4 | 30.7% | 23.6 |
| **Global LightGBM** | 15.4% | 119.6 | **29.2%** | 22.5 |
| Croston-SBA | 47.9% | 373.1 | 52.7% | 40.5 |
| TSB | 46.4% | 361.3 | 51.5% | 39.6 |
| _Oracle (generator formula, not a real model)_ | _6.0%_ | _47.0_ | _26.5%_ | _20.3_ |

The brief's target, beating seasonal naive on WAPE, is met by LightGBM and Prophet at every level and horizon.
LightGBM is used for inventory because it is best at product level and its 30-day error stays flat (15.6% category,
31.0% top-50) while it handles slow movers (below).

**Festival vs regular days (category level, 14 days):** LightGBM 16.0% / 7.1%, Prophet 15.8% / 7.2%,
seasonal naive 44.5% / 11.4%. Festivals are still the hard part, but no longer guessed blind.

## Probabilistic forecasts (30 days after 2025-03-15, 300 products, 9,000 product-days)
| Check | Result | Target |
| :--- | :---: | :---: |
| Actual inside P10-P90 | 75.2% | 80% |
| Actual <= P90 | 85.9% | 90% |
| Actual >= P10 | 89.3% | 90% |
| Quantile crossings | 0 | 0 |

The band is slightly too narrow: this window contains Eid ul Fitr and a festival held for the first time
("Spring Back to School"), which the calibration windows could not fully represent. Surge buffers sized on P90 are
therefore a little small for festivals.

## Slow / intermittent movers
67% of their days sell nothing, so per-day WAPE is above 100% for every model (forecasting zero scores exactly 100%,
yet would never restock). Re-ordering uses the 14-day **total**, so that is the yardstick:

| Slow movers, 14-day total | 4 festival folds: error / bias | 8 extra cut-offs: error / bias |
| :--- | :---: | :---: |
| Seasonal naive | 65.9% / -42.6% | 62.3% / -3.7% |
| Prophet | 64.3% / -52.4% | 53.9% / -41.2% |
| **Global LightGBM** | **51.2% / +4.1%** | **38.8% / -4.1%** |
| Croston-SBA | 58.4% / -41.9% | 48.8% / +12.8% |
| TSB | 60.5% / -42.6% | 54.1% / +16.0% |

Croston / TSB were not adopted; slow movers stay on LightGBM. (`reports/day3_forecast_accuracy_breakdown.csv`,
`reports/day3_slow_mover_extra_cutoffs.csv`.)

## Inventory policy
Safety stock SS = z * sqrt(L * sigma_D^2 + D^2 * (0.15 L)^2), reorder point = D * L + SS, with L the product's
catalogue lead time (3-11 days), sigma_D from the P10-P90 width, and z = 1.645 (>= 3 units/day) or 1.282.
Alert rules: `docs/user_guides/operations_guide.md`. Snapshot 2025-03-15: 129 critical, 94 festival-surge watch,
7 overstock (mostly winter wear in spring, PKR 60.9M of stock), 70 healthy.

**2025 replay** (weekly re-ordering, unmet demand lost, forecaster refitted every 14 days on data up to that day,
29 refits; `reports/day3_inventory_backtest.csv`):

| Policy | Fill rate | Lost units | Lost gross margin (PKR) | Stock-out SKU-days | Lost units, Ramadan + Eid ul Fitr | Lost units, Eid ul Adha | Avg stock value (PKR) | Avg dead capital (PKR) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 28-day moving average | 87.4% | 238,290 | 776.2M | 6,495 | 105,849 | 59,570 | 356.7M | 14.1M |
| Same days last year | 92.0% | 151,881 | 480.9M | 4,523 | 69,944 | 51,514 | 295.5M | 0.4M |
| **Forecast-driven** | **97.9%** | **40,710** | **125.1M** | **1,991** | **12,223** | **3,699** | 304.4M | 0.9M |

Forecast-driven ordering lost 83% fewer units than the moving average while holding 15% less stock, and 73% fewer
than same-days-last-year while holding 3% **more** stock (it buys ahead of festivals that the last-year rule misses
because Eid moves 11 days). Synthetic demand repeats yearly patterns, so treat this as evidence that the mechanism
works, not as an expected saving.

## Limitations
- Synthetic demand and synthetic stock levels; no real sales were available.
- A festival held for the first time has no history, so its effect is not forecast.
- Each festival has been seen only once (2024) before the 2025 tests; uplift estimates rest on one occurrence.
- The plan is made from one snapshot date (2025-03-15); in production it would run daily.
- Stock-out days in the training history are not corrected for (lost sales would bias forecasts low on real data).
- Lead-time variability (15%) is assumed, not measured.
