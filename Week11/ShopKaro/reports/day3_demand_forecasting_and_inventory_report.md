# ShopKaro AI — Day 3 Demand Forecasting & Inventory Intelligence Report

**Stage:** Day 3 — Demand Forecasting & Inventory Intelligence (Weight: 20%)  
**Database:** [`data/processed/shopkaro.duckdb`](file:///d:/Netixsol/Week11/ShopKaro/data/processed/shopkaro.duckdb) (`daily_sales`, `festival_calendar`, `sku_forecasts_30d`, `inventory_alerts`)  
**Backtest Table:** [`reports/day3_forecasting_backtest_comparison.csv`](file:///d:/Netixsol/Week11/ShopKaro/reports/day3_forecasting_backtest_comparison.csv)  
**Inventory Alerts Export:** [`reports/day3_inventory_alerts.csv`](file:///d:/Netixsol/Week11/ShopKaro/reports/day3_inventory_alerts.csv)  
**Figures:**
- [`reports/figures/09_timeseries_decomposition_and_seasonality.png`](file:///d:/Netixsol/Week11/ShopKaro/reports/figures/09_timeseries_decomposition_and_seasonality.png)
- [`reports/figures/10_pakistani_festival_uplift_and_lunar_shift.png`](file:///d:/Netixsol/Week11/ShopKaro/reports/figures/10_pakistani_festival_uplift_and_lunar_shift.png)
- [`reports/figures/11_forecasting_backtest_comparison.png`](file:///d:/Netixsol/Week11/ShopKaro/reports/figures/11_forecasting_backtest_comparison.png)
- [`reports/figures/12_probabilistic_forecast_and_inventory_alerts.png`](file:///d:/Netixsol/Week11/ShopKaro/reports/figures/12_probabilistic_forecast_and_inventory_alerts.png)

---

## 1. Executive Summary

> **Updated 2026-11-10:** results below were re-measured with the real libraries on Python 3.11; see `reports/library_migration_py311.md` for before/after numbers.

Day 3 replaces ShopKaro's reactive manual restocking with an automated **Multi-Horizon Probabilistic Demand Forecasting & Inventory Intelligence Engine** across `731` days of Pakistani retail history (`2024-01-01` to `2025-12-31`, `300` tracked SKUs, `3.55M` units sold, `PKR 73.41B` revenue):

1. **Task 1 — Time-Series Analysis, Decomposition & Stationarity (`timeseries_analysis.py`):** Built 3 hierarchy levels (`Platform Total`, `11 Categories`, `Top-50 SKUs`), decomposed daily demand into 28-day Trend, Weekly Seasonality (Jummah/Weekend surge), and Residual shocks, verified stationarity via **Augmented Dickey-Fuller (ADF)** tests across all 12 series, and quantified **moving Hijri lunar festival shifts (`-10` to `-11` days earlier in 2025 vs. 2024)**.
2. **Task 2 & Task 3 — Multi-Model Forecasting & 4-Fold Rolling-Origin Backtesting (`models.py`):** Evaluated 5 progressive architectures (`Naive`, `Seasonal Naive 7d`, `Classical Holt-Winters ETS`, `Prophet with Moving Islamic Holidays`, and `Global LightGBM`) across 4 seasonal origins and 3 horizons (`7d`, `14d`, `30d`) on `WAPE` (primary), `MAE`, `RMSE`, and `sMAPE`.
3. **Task 4 — Probabilistic Quantile Forecasting (`inventory.py`):** Generated calibrated `P10 / P50 / P90` daily demand intervals across 30 days (`79.03%` empirical coverage on the nominal `80%` interval, `0` quantile crossings).
4. **Task 5 — Inventory Intelligence & Automated Alert Engine (`inventory.py`):** Calculated **Safety Stock**, **Reorder Point (ROP)**, **Days of Inventory Remaining (`DOI_P50` & `DOI_P90`)**, **Recommended Order Quantities (ROQ)**, and **Overstock Working Capital at Risk (`PKR 61.93M`)** across all `300` SKUs, plus a 2025 replay of forecast-driven vs rule-based re-ordering (section 4.3).

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

---

## 3. Tasks 2 & 3: 4-Fold Rolling-Origin Backtest Results (`14-Day` Operational Horizon)

| Hierarchy Level | Model Name | 7d WAPE (%) | 14d WAPE (%) | 30d WAPE (%) | 14d MAE | 14d RMSE | 14d sMAPE (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Category Level** (`11` Series) | `1. Naive (Last Observed Value)` | `44.69%` | `44.47%` | `44.73%` | `331.85` | `637.83` | `44.01%` |
| **Category Level** (`11` Series) | `2. Seasonal Naive (7-Day Cycle)` | `39.27%` | `43.01%` | `41.84%` | `320.95` | `656.45` | `40.71%` |
| **Category Level** (`11` Series) | `3. Classical Holt-Winters ETS (s=7)` | `39.03%` | `42.19%` | `41.69%` | `314.84` | `647.28` | `43.31%` |
| **Category Level** (`11` Series) | **`4. Prophet (Fourier + Moving Islamic Holidays)`** | `7.59%` | `7.46%` | `7.87%` | `55.65` | `92.92` | `11.08%` |
| **Category Level** (`11` Series) | **`5. Global LightGBM (Lags + Rolling + Festivals)`** | **`6.48%`** | **`6.87%`** | **`7.03%`** | **`51.25`** | **`83.81`** | **`11.09%`** |
| **Product Level** (`Top-50` SKUs) | `1. Naive (Last Observed Value)` | `52.98%` | `53.35%` | `54.79%` | `39.50` | `61.00` | `56.10%` |
| **Product Level** (`Top-50` SKUs) | `2. Seasonal Naive (7-Day Cycle)` | `52.44%` | `54.04%` | `54.67%` | `40.00` | `62.14` | `58.32%` |
| **Product Level** (`Top-50` SKUs) | `3. Classical Holt-Winters ETS (s=7)` | `48.15%` | `50.38%` | `51.69%` | `37.30` | `59.82` | `52.11%` |
| **Product Level** (`Top-50` SKUs) | **`4. Prophet (Fourier + Moving Islamic Holidays)`** | `26.79%` | `27.40%` | `28.06%` | `20.28` | `31.34` | `28.72%` |
| **Product Level** (`Top-50` SKUs) | **`5. Global LightGBM (Lags + Rolling + Festivals)`** | **`26.33%`** | **`27.19%`** | **`27.49%`** | **`20.13`** | **`31.01`** | **`28.36%`** |

---

## 4. Tasks 4 & 5: Probabilistic Calibration & Inventory Alert Summary (`300` Tracked SKUs)

### 4.1 Probabilistic `P10 / P50 / P90` Calibration (`30-Day` Horizon Across `300` SKUs)
- **Nominal Interval Target (`[P10, P90]`):** `80.00%`
- **Measured Empirical Coverage (`[P10, P90]`):** **`79.03%`**
- **Quantile Crossing Violations ($\text{P10} > \text{P50}$ or $\text{P50} > \text{P90}$):** **`0` violations** across `9,000` SKU-day predictions
- **Pinball Losses:** `Pinball(P10) = 1.7663`, `Pinball(P50) = 4.6562`, `Pinball(P90) = 2.3865`

### 4.2 Inventory Alert Breakdown (`300` Tracked SKUs)

| Alert Tier | SKU Count | Operational Trigger Rule | Recommended Supply Chain Action |
| :--- | :---: | :--- | :--- |
| **`CRITICAL_STOCKOUT_RISK`** | `143` SKUs | `stock_qty <= ROP` or `DOI_P50 <= 14 days` | Purchase order (`162,685` total PO units across all alerts) |
| **`FESTIVAL_SURGE_WATCH`** | `85` SKUs | `DOI_P50 > 14d` but `DOI_P90 <= 18d` | Pre-build festival safety buffer ahead of `P90` peak |
| **`OVERSTOCK_DEAD_CAPITAL`** | `8` SKUs | `DOI_P50 > 90 days` (`PKR 61.93M` stock value) | Freeze reorders & clearance promotion |
| **`HEALTHY_STOCK`** | `64` SKUs | everything else | No immediate action; review in 7 days |

The plan is made on 2025-03-15, six days before Eid ul Fitr. 126 of the 228 SKUs in Eid-boosted categories (55%)
are critical, against 17 of the other 72 (24%): stock sized on the previous month's sales is short for the surge.
Stock levels are synthetic: each product's stock is its own recent daily sales times a random number of days of
cover (median 30, see `calibrate_stock_to_demand`). Before this calibration stock was random (5-250 units regardless
of sales) and 221 of 300 SKUs were critical.

### 4.3b Accuracy breakdowns, MAPE, calibration and pre-festival plan (added 2026-11-10)

`reports/day3_forecast_accuracy_breakdown.csv` (14-day horizon, 4 folds). A third panel of 60 SKUs (the 20
highest-volume products in each velocity tier) was added because the top-50 SKUs are all fast movers.

**Festival vs regular days (WAPE).** The calendar-aware models stay accurate during festivals; the baselines do not.

| Model | festival days | regular days |
| :--- | :---: | :---: |
| Naive | 44.3% | 22.6% |
| Seasonal Naive | 44.5% | 11.4% |
| Classical Holt-Winters ETS | 44.1% | 10.1% |
| Prophet | 6.2% | 6.3% |
| Global LightGBM | 6.0% | 6.2% |

**By sales volume (WAPE, 60-SKU panel).**

| Model | Fast_Mover | Steady_Mover | Slow_Intermittent |
| :--- | :---: | :---: | :---: |
| Naive | 51.2% | 53.9% | 112.0% |
| Seasonal Naive | 52.7% | 55.3% | 127.6% |
| Classical Holt-Winters ETS | 50.2% | 52.3% | 121.1% |
| Prophet | 27.0% | 30.4% | 115.8% |
| Global LightGBM | 26.8% | 30.6% | 135.7% |
| Croston-SBA (added 2026-11-10) | 53.8% | 55.4% | 120.6% |
| TSB (added 2026-11-10) | 52.5% | 54.1% | 120.9% |

**Slow / intermittent movers (updated 2026-11-10).** 67% of their days have zero sales, so per-day WAPE is above
100% for every model (forecasting zero scores exactly 100% but would never restock anything). Croston-SBA and TSB, the
standard intermittent-demand methods, were added as models 6 and 7 (textbook smoothing 0.1, not tuned). Reordering
uses the forecast 14-day *total*, so that is the fair yardstick (`total_wape_pct` = sum over SKUs and folds of
|forecast total - actual total| / actual total):

| Slow movers, 14-day total | 4 festival folds: error | bias | 8 extra cut-offs: error | bias |
| :--- | :---: | :---: | :---: | :---: |
| Seasonal Naive | 65.9% | -42.6% | 62.3% | -3.7% |
| Prophet | 61.5% | -55.2% | 52.5% | -42.4% |
| **Global LightGBM** | **49.6%** | **+1.5%** | **41.9%** | **+4.2%** |
| Croston-SBA | 58.4% | -41.9% | 48.8% | +12.8% |
| TSB | 60.5% | -42.6% | 54.1% | +16.0% |

(Extra cut-offs: `scripts/run_day3_slow_mover_check.py` -> `reports/day3_slow_mover_extra_cutoffs.csv`.) LightGBM is
the best and nearly unbiased in both checks; its high per-day WAPE comes from spreading small amounts over days that
turn out to be zero, which is right for the total. Croston / TSB ignore the festival calendar and under-forecast
festival weeks. **Decision: not adopted; slow movers stay on LightGBM.**

**MAPE vs WAPE (14-day horizon).** MAPE divides by the actual value, so it is undefined on zero-sale days and explodes
on days with 1-2 sales; it is computed here only over days with sales, next to the share of zero-sale days.

| Level | Model | WAPE | MAPE | sMAPE | Zero-sale days |
| :--- | :--- | :---: | :---: | :---: | :---: |
| Category_Level | Seasonal Naive | 42.3% | 34.6% | 44.0% | 0.0% |
| Category_Level | Prophet | 6.2% | 15.4% | 13.4% | 0.0% |
| Category_Level | Global LightGBM | 6.0% | 14.2% | 12.9% | 0.0% |
| Top50_SKU_Level | Seasonal Naive | 52.7% | 49.9% | 56.7% | 0.0% |
| Top50_SKU_Level | Prophet | 27.3% | 31.8% | 28.8% | 0.0% |
| Top50_SKU_Level | Global LightGBM | 26.5% | 32.9% | 28.0% | 0.0% |
| SKU_By_Velocity_60 | Seasonal Naive | 54.4% | 59.1% | 70.5% | 22.4% |
| SKU_By_Velocity_60 | Prophet | 29.1% | 42.5% | 80.1% | 22.4% |
| SKU_By_Velocity_60 | Global LightGBM | 29.2% | 41.4% | 75.2% | 22.4% |

**Calibration check (brief: "does P90 cover reality ~90% of the time?").** On the 30 days after 2025-03-15, actual
demand was <= P90 on **87.6%** of SKU-days (target 90%) and >= P10 on **91.2%** (target 90%); the P10-P90
band covered 78.8% (target 80%). P90 is slightly low, so surge buffers are slightly under-sized.

**Pre-festival stocking plan, top 100 products** (`reports/day3_prefestival_plan_top100.csv`), for
Chaand Raat & Eid ul Fitr (2025-03-21 to 2025-04-03), planned on 2025-03-15:
order up to P90 demand until the festival ends + safety stock. 37 products should order
now, 22 need nothing, and **41 cannot arrive in time** (order-by date already
passed for their lead time) and need expediting. Total 111,705 units,
PKR 574M at cost. Lesson: run the plan at least two weeks before a festival.

### 4.3 Historical replay: does forecast-driven ordering beat simple rules? (added 2026-11-09)

`scripts/run_day3_inventory_backtest.py` (`src/shopkaro/forecasting/inventory_backtest.py`) replays all of 2025
for the 300 tracked SKUs. Every week each SKU is re-ordered up to "forecast demand over (7 days + its lead
time) + safety stock". The three policies differ only in the forecast: a 28-day moving average, the same days one
year earlier, or this project's forecaster refitted every 14 days on data up to that day (29
refits, no look-ahead). Unmet demand is lost; supplier lead times vary +-15% with identical random draws for every
policy; all start from the same stock on 2024-12-01. Dead capital = stock the next 60 days of actual demand would
not sell.

| Policy (weekly re-order, same safety-stock rule) | Fill rate | Lost units | Lost gross margin (PKR) | Stock-out SKU-days | Lost units, Ramadan + Eid ul Fitr | Lost units, Eid ul Adha | Avg stock value (PKR) | Avg dead capital (PKR) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 28-day moving average | 87.4% | 238,290 | 850.1M | 6,495 | 105,849 | 59,570 | 561.6M | 7.9M |
| Same days last year (seasonal naive) | 92.0% | 151,881 | 481.9M | 4,523 | 69,944 | 51,514 | 466.5M | 0.3M |
| **Forecast-driven (P50 + forecast uncertainty)** | 98.7% | 24,442 | 109.6M | 2,363 | 4,415 | 3,465 | 438.9M | 0.1M |

Forecast-driven vs moving average: 90% fewer lost units, 96% fewer
during Ramadan + Eid ul Fitr, 22% less average stock. Vs same-days-last-year:
84% fewer lost units, 94% fewer during Ramadan + Eid ul Fitr (last
year's dates are 11 days off because Eid moves with the lunar calendar), 6% less stock.

**How much to trust this.** The demand is synthetic and was generated from the same festival calendar and
multipliers the forecaster is given, so the forecaster has an inside advantage that it would not have on real
sales; real gains would be smaller. The result shows the mechanism works (anticipating moving festivals cuts lost
sales without raising stock), not a business saving. Dead capital is small for both seasonal policies; the large
moving-average figure is mostly winter-wear stock bought on February sales that did not sell in spring.

**Correction.** Earlier versions of the slides and the forecaster model card claimed "84.2% of pre-Eid stockouts
prevented" and "31.5% less dead capital". No code produced those numbers; they have been replaced by this replay.



---

## Note (2026-11-09): data regenerated
Product categories now follow RetailRocket's real category tree instead of being random per item, and all
artefacts were regenerated. Numbers in the tables above predate that change. Current results are in the CSVs in
`reports/`. Conclusions are unchanged: at 14-day horizon, category-level WAPE is 6.1% for global gradient boosting vs 42.3% for seasonal naive (Top-50 SKUs: 26.5% vs 52.7%). The inventory tables in section 4.2 were refreshed after stock calibration (2026-11-09).
