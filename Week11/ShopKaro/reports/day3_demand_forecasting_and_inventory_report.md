# ShopKaro AI — Day 3 Demand Forecasting & Inventory Intelligence Report

**Stage:** Day 3 — Demand Forecasting & Inventory Intelligence (Weight: 20%)  
**Database:** `data/processed/shopkaro.duckdb` (`daily_sales`, `festival_calendar`, `sku_forecasts_30d`, `inventory_alerts`)  
**Backtest table:** [`day3_forecasting_backtest_comparison.csv`](day3_forecasting_backtest_comparison.csv)  
**Accuracy breakdown:** [`day3_forecast_accuracy_breakdown.csv`](day3_forecast_accuracy_breakdown.csv)  
**Inventory alerts:** [`day3_inventory_alerts.csv`](day3_inventory_alerts.csv)  
**Figures** (generated locally into `reports/figures/`, not stored in git):
`09_timeseries_decomposition_and_seasonality.png`, `10_pakistani_festival_uplift_and_lunar_shift.png`,
`11_forecasting_backtest_comparison.png`, `12_probabilistic_forecast_and_inventory_alerts.png`  
**Model card:** [`docs/model_cards/forecaster_model_card.md`](../docs/model_cards/forecaster_model_card.md)

---

## 0. Correction (2026-11-16): the earlier forecaster copied the data generator

The daily sales are synthetic. A code review found that the previous "Global LightGBM" and "Prophet" were given the
generator's own recipe: the same weekly multipliers (0.92 / 1.25 / 1.35), the same category season curves, the same
+18% trend and the **true festival multipliers** (`demand_multiplier`, `boost_categories`) from the calendar. The
LightGBM then only learned a small correction on top, and the intervals assumed the generator's own noise formula.
The earlier headline numbers (6.9% category WAPE, 79% interval coverage, "90% fewer lost units") were therefore not
real results.

Fix:
- Forecasters now see only past sales and the festival calendar's **names, types and dates**
  (`src/shopkaro/forecasting/festivals.py`). How much each festival lifts sales is learned from history.
- Intervals now come from conformal prediction (section 4.1) instead of an assumed noise model.
- The old model is kept as a clearly labelled **oracle** row ("upper bound, not a real model",
  `src/shopkaro/forecasting/oracle.py`) so the gap is visible. Nothing else uses it.
- `tests/test_forecast_leakage.py`: the honest code may not read the answer columns, and on sales generated with
  **different** rules (Monday peak, Ramadan lowering sales, other festival sizes) the honest LightGBM must beat both
  seasonal naive and the oracle. Measured: honest **15.4%** WAPE, seasonal naive 64.6%, oracle **63.5%**: the old
  model had memorised the recipe rather than learned demand.

All tables below are from the corrected run.

---

## 1. Executive Summary

Day 3 turns 731 days of (synthetic) Pakistani sales history (`2024-01-01` to `2025-12-31`, `300` products) into
forecasts and stocking decisions:

1. **Task 1 — Time-series analysis (`timeseries_analysis.py`):** 3 hierarchy levels (platform, 11 categories, top-50
   products), trend / weekly / residual decomposition, ADF stationarity tests on 12 series, and the moving Hijri
   festival shift (Eid ul Fitr and Eid ul Adha 11 days earlier in 2025 than 2024).
2. **Tasks 2 & 3 — 7 models, 4-fold rolling-origin backtest (`models.py`):** naive, seasonal naive, Holt-Winters ETS,
   Prophet with festival regressors, global LightGBM, Croston-SBA, TSB; horizons 7 / 14 / 30 days; WAPE, MAE, RMSE,
   MAPE, sMAPE; festival vs regular days; fast vs slow movers. **LightGBM 15.4% category WAPE and 29.2% top-50 WAPE
   at 14 days, against 42.3% / 52.7% for seasonal naive** (brief target met at every level and horizon).
3. **Task 4 — P10 / P50 / P90 (`inventory.py`):** conformal intervals. On the 30 days after 2025-03-15: 75.2% of
   actual values inside P10-P90 (target 80%), P90 covers 85.9% (target 90%), 0 crossings.
4. **Task 5 — Inventory decisions (`inventory.py`, `inventory_backtest.py`):** safety stock, reorder point, days of
   inventory and 4 alert tiers for all 300 products, a pre-festival plan for the top 100, and a replay of 2025:
   forecast-driven ordering lost **83% fewer units** than a 28-day moving average (with 15% less stock) and 73% fewer
   than same-days-last-year (with 3% more stock).

---

## 2. Task 1: Pakistani Festival Uplift & Moving Hijri Lunar Shift (`2024` vs. `2025`)

| Festival Window | Calendar Type | 2024 Start | 2025 Start | Gregorian Shift | Avg Daily Units | Baseline Units | Observed Uplift |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Chaand Raat & Eid ul Fitr** | **`Islamic_Moving`** | `2024-04-01` | `2025-03-21` | **`-11 days`** | `12,688.2` | `3,689.8` | **`3.44x`** |
| **Eid ul Adha** | **`Islamic_Moving`** | `2024-06-08` | `2025-05-28` | **`-11 days`** | `8,998.4` | `3,689.8` | **`2.44x`** |
| **Ramadan** | **`Islamic_Moving`** | `2024-03-11` | `2025-03-01` | **`-10 days`** | `6,879.8` | `3,689.8` | **`1.86x`** |
| `11.11 Mega Sale` | `Commercial_Fixed` | `2024-11-08` | `2025-11-08` | `0 days` | `6,806.6` | `3,689.8` | `1.84x` |
| `Back to School Season` | `Seasonal_Fixed` | `2024-08-15` | `2025-08-15` | `0 days` | `6,584.3` | `3,689.8` | `1.78x` |
| `Azadi Sale (14 August)` | `National_Fixed` | `2024-08-10` | `2025-08-10` | `0 days` | `6,323.5` | `3,689.8` | `1.71x` |
| `Blessed Friday` | `Commercial_Fixed` | `2024-11-25` | `2025-11-24` | `-1 day` | `5,690.6` | `3,689.8` | `1.54x` |
| `Wedding & Shaadi Season` | `Seasonal_Fixed` | `2024-12-05` | `2025-12-05` | `0 days` | `5,419.7` | `3,689.8` | `1.47x` |

(Observed uplift is measured from the sales data. The forecasters are not given these numbers; they learn them.)

---

## 3. Tasks 2 & 3: Models and 4-Fold Rolling-Origin Backtest

**What each model may use.** Only sales up to the cut-off and the festival calendar's names / dates.
- **Prophet:** trend + weekly + yearly Fourier (order 10) + one regressor per festival built from its dates;
  Prophet learns each festival's effect per series. Festivals never seen before the cut-off are left out.
- **Global LightGBM:** one model across all series, direct multi-horizon. Features: 7 / 28 / 91-day level,
  28-day volatility, share of zero days, same-weekday mean of the last 4 weeks, last year around the target date
  (and whether that date was a festival, because Islamic dates move), target-date calendar, horizon, category,
  festival indicators, and each festival's uplift for this product the previous time and so far this time.
  A festival held for the first time (e.g. "Spring Back to School", new in 2025) is treated as a regular day:
  without history, guessing its size from Eid made April 2025 forecasts twice too high in an earlier attempt.
- **Croston-SBA / TSB:** intermittent-demand rates for slow movers (smoothing 0.1, not tuned).

**Cut-offs:** 2025-03-15 (Eid ul Fitr), 2025-05-25 (Eid ul Adha), 2025-08-08 (Azadi / back to school),
2025-11-05 (11.11 / winter). Each fold trains only on data up to its cut-off.

**WAPE by horizon** (lower is better):

| Level | Model | 7 days | 14 days | 30 days | 14d MAE |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Category (11 series) | Naive | 42.7% | 42.9% | 43.5% | 333.7 |
| Category | Seasonal naive (7-day) | 38.7% | 42.3% | 40.2% | 329.2 |
| Category | Holt-Winters ETS | 39.1% | 41.8% | 40.6% | 325.6 |
| Category | **Prophet** | **11.7%** | **15.2%** | **14.7%** | 118.4 |
| Category | **Global LightGBM** | 14.0% | 15.4% | 15.6% | 119.6 |
| Category | Croston-SBA | 44.4% | 47.9% | 43.6% | 373.1 |
| Category | TSB | 42.8% | 46.4% | 42.8% | 361.3 |
| Category | _Oracle (not a real model)_ | _6.0%_ | _6.0%_ | _6.4%_ | _47.0_ |
| Top-50 products | Naive | 52.3% | 52.4% | 54.8% | 40.3 |
| Top-50 | Seasonal naive (7-day) | 50.5% | 52.7% | 53.0% | 40.5 |
| Top-50 | Holt-Winters ETS | 47.6% | 49.8% | 50.9% | 38.3 |
| Top-50 | Prophet | 29.5% | 30.7% | 31.6% | 23.6 |
| Top-50 | **Global LightGBM** | **27.1%** | **29.2%** | **31.0%** | 22.5 |
| Top-50 | Croston-SBA | 49.4% | 52.7% | 49.8% | 40.5 |
| Top-50 | TSB | 48.2% | 51.5% | 49.2% | 39.6 |
| Top-50 | _Oracle (not a real model)_ | _25.3%_ | _26.5%_ | _26.9%_ | _20.3_ |

Prophet is slightly better on smooth category totals, LightGBM on individual products. **LightGBM is the
production model** because inventory decisions are made per product and it also handles slow movers (below).

**Festival vs regular days** (category level, 14 days):

| Model | Festival days | Regular days |
| :--- | :---: | :---: |
| Naive | 44.3% | 22.6% |
| Seasonal naive | 44.5% | 11.4% |
| Holt-Winters ETS | 44.1% | 10.1% |
| Prophet | 15.8% | 7.2% |
| Global LightGBM | 16.0% | 7.1% |

Festivals remain the hard part (each festival has been seen only once before 2025), but the calendar-aware models
cut festival-day error by about two thirds.

**By sales volume** (60-product panel: the 20 highest-volume products of each velocity tier; 14 days):

| Model | Fast mover WAPE | Steady mover WAPE | Slow mover WAPE | Slow mover 14-day total: error / bias |
| :--- | :---: | :---: | :---: | :---: |
| Seasonal naive | 52.7% | 55.3% | 127.6% | 65.9% / -42.6% |
| Prophet | 31.0% | 39.2% | 116.9% | 64.3% / -52.4% |
| **Global LightGBM** | **29.6%** | **32.4%** | 137.2% | **51.2% / +4.1%** |
| Croston-SBA | 53.8% | 55.4% | 120.6% | 58.4% / -41.9% |
| TSB | 52.5% | 54.1% | 120.9% | 60.5% / -42.6% |

Slow movers sell nothing on 67% of days, so per-day WAPE is above 100% for every model (forecasting zero scores
exactly 100%, yet would never restock). Re-ordering uses the 14-day **total**, where LightGBM is best and nearly
unbiased. On 8 extra, mostly non-festival cut-offs (`scripts/run_day3_slow_mover_check.py`) the totals are LightGBM
38.8% / -4.1%, Croston-SBA 48.8% / +12.8%, TSB 54.1% / +16.0%, seasonal naive 62.3% / -3.7%.
**Decision: Croston / TSB not adopted; slow movers stay on LightGBM.**

**MAPE vs WAPE (14 days).** MAPE divides by the actual value, so it is undefined on zero-sale days and explodes on
days with 1-2 sales (forecast 3, actual 1 = 200% error); it is computed only over days with sales. WAPE (total error /
total sales) has neither problem, which is why it is the primary metric.

| Level | Model | WAPE | MAPE | sMAPE | Zero-sale days |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Category | Seasonal naive | 42.3% | 34.6% | 44.0% | 0.0% |
| Category | Prophet | 15.2% | 18.3% | 16.3% | 0.0% |
| Category | Global LightGBM | 15.4% | 21.1% | 20.4% | 0.0% |
| Top-50 | Seasonal naive | 52.7% | 49.9% | 56.7% | 0.0% |
| Top-50 | Prophet | 30.7% | 34.2% | 31.0% | 0.0% |
| Top-50 | Global LightGBM | 29.2% | 36.1% | 30.6% | 0.0% |
| 60-product panel | Seasonal naive | 54.4% | 59.1% | 70.5% | 22.4% |
| 60-product panel | Prophet | 34.3% | 46.0% | 81.4% | 22.4% |
| 60-product panel | Global LightGBM | 31.7% | 43.4% | 76.5% | 22.4% |

---

## 4. Tasks 4 & 5: Probabilistic Forecasts and Inventory Decisions (300 products)

### 4.1 P10 / P50 / P90 with conformal prediction
P50 is the LightGBM forecast. For P10 / P90 the same model is refitted on data ending 28 days before the plan date,
and again on data ending 364 days before it (the same season last year, so festival-sized errors are included);
its errors on those known 28-day windows are collected. The 10th / 90th percentiles of the errors, grouped by
forecast size (5 bins) and horizon (1-7, 8-14, 15+ days), are added to P50. No noise distribution is assumed.

Calibration check on the 30 days after 2025-03-15 (300 products, 9,000 product-days):

| Check | Result | Target |
| :--- | :---: | :---: |
| Actual inside P10-P90 | **75.2%** | 80% |
| Actual <= P90 | **85.9%** | 90% |
| Actual >= P10 | 89.3% | 90% |
| Quantile crossings | 0 | 0 |
| P50 WAPE over 30 days | 34.6% | |

The band is a little narrow. This window contains Eid ul Fitr and a festival held for the first time, and neither
calibration window fully represents that, so P90-based surge buffers are slightly small around festivals. (With
only the recent window, coverage was 69.9%; adding last year's same season raised it to 75.2%.)

### 4.2 Inventory alerts (plan date 2025-03-15, six days before Eid ul Fitr)

| Alert tier | Products | Rule | Action |
| :--- | :---: | :--- | :--- |
| **`CRITICAL_STOCKOUT_RISK`** | 129 | `stock <= ROP` or `DOI_P50 <= 14 days` | Purchase order (101,778 units in total) |
| **`FESTIVAL_SURGE_WATCH`** | 94 | `DOI_P50 > 14d` but `DOI_P90 <= 18d` | Build a festival buffer towards P90 (63,167 units) |
| **`OVERSTOCK_DEAD_CAPITAL`** | 7 | `DOI_P50 > 90 days` (PKR 60.9M of stock) | Freeze re-orders, clearance promotion |
| **`HEALTHY_STOCK`** | 70 | everything else | Review in 7 days |

Safety stock SS = z * sqrt(L * sigma_D^2 + D^2 * (0.15 L)^2) and reorder point ROP = D * L + SS, with L the
product's lead time (3-11 days), sigma_D from the P10-P90 width and z = 1.645 (>= 3 units/day) or 1.282.
99 of the 174 products in categories that Eid ul Fitr typically lifts are critical (57%), against 30 of the other
126 (24%): stock sized on last month's sales is short for the surge. The overstock tier is mostly winter wear in
spring. Stock levels are synthetic (each product's recent daily sales times a random number of days of cover).

### 4.3 Pre-festival stocking plan, top 100 products
`reports/day3_prefestival_plan_top100.csv`, for Chaand Raat & Eid ul Fitr (2025-03-21 to 2025-04-03), planned on
2025-03-15: order up to P90 demand until the festival ends + safety stock. 37 products should order now, 20 need
nothing, and **43 cannot arrive in time** (their order-by date has passed for their lead time) and need expediting.
Total 111,989 units, PKR 703M. Lesson: run the plan at least two weeks before a festival.

### 4.4 Replay of 2025: does forecast-driven ordering beat simple rules?
`scripts/run_day3_inventory_backtest.py` replays 2025 for the 300 products. Every week each product is re-ordered up
to "forecast demand over (7 days + its lead time) + safety stock". The three policies differ only in the forecast:
a 28-day moving average, the same days one year earlier, or this project's forecaster refitted every 14 days on data
up to that day (29 refits, no look-ahead). Unmet demand is lost; supplier lead times vary +-15% with identical random
draws for every policy; all start from the same stock on 2024-12-01. Dead capital = stock that the next 60 days of
actual demand would not sell.

| Policy | Fill rate | Lost units | Lost gross margin (PKR) | Stock-out product-days | Lost units, Ramadan + Eid ul Fitr | Lost units, Eid ul Adha | Avg stock value (PKR) | Avg dead capital (PKR) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 28-day moving average | 87.4% | 238,290 | 776.2M | 6,495 | 105,849 | 59,570 | 356.7M | 14.1M |
| Same days last year | 92.0% | 151,881 | 480.9M | 4,523 | 69,944 | 51,514 | 295.5M | 0.4M |
| **Forecast-driven** | **97.9%** | **40,710** | **125.1M** | **1,991** | **12,223** | **3,699** | 304.4M | 0.9M |

- vs moving average: **83% fewer lost units**, 89% fewer during Ramadan + Eid ul Fitr, 15% less average stock.
- vs same days last year: **73% fewer lost units**, 83% fewer during Ramadan + Eid ul Fitr, but **3% more stock**
  (the forecast buys ahead of festivals that the last-year rule misses, because Eid moves 11 days).

**How much to trust this.** The forecaster no longer sees the generator's multipliers, but the synthetic sales still
repeat the same rules every year, which real sales do not. Treat this as evidence that anticipating moving
festivals cuts lost sales, not as an expected saving. Earlier claims ("84.2% of pre-Eid stockouts prevented",
"31.5% less dead capital", and later "90% fewer lost units") are withdrawn.
