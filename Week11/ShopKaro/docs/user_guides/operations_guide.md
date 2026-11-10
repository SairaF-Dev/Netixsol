# ShopKaro Warehouse & Supply Chain Operations Guide

## 1. Probabilistic Demand Quantiles ($P_{10}, P_{50}, P_{90}$)
Instead of single-point averages, ShopKaro forecasts 3 daily demand bounds:
- **$P_{10}$ (Downside Floor):** 90% probability that demand will be at least this value.
- **$P_{50}$ (Expected Median):** Baseline trajectory for normal replenishment.
- **$P_{90}$ (Upper Surge Ceiling):** High-demand scenario for festival spikes (e.g., Chaand Raat surge).

## 2. Inventory Alert Categories & Actions

Rules exactly as implemented in `InventoryIntelligenceEngine` (`src/shopkaro/forecasting/inventory.py`), checked in
this order. DOI = days of inventory = stock / average daily P50 demand over the next 14 days.

| Alert Status | Trigger Condition | Recommended Action |
| :--- | :--- | :--- |
| **`CRITICAL_STOCKOUT_RISK`** | stock <= reorder point, or DOI (P50) <= 14 days | Purchase order up to 30 days of P50 demand + safety stock |
| **`FESTIVAL_SURGE_WATCH`** | otherwise, DOI at P90 demand <= 18 days | Pre-order buffer up to 30 days of P90 demand + safety stock |
| **`OVERSTOCK_DEAD_CAPITAL`** | otherwise, DOI (P50) > 90 days and stock >= 25 units | Freeze re-orders, clearance markdown |
| **`HEALTHY_STOCK`** | everything else | Normal weekly review |

## 3. Replenishment Math
$$SS = z \sqrt{L\,\sigma_D^2 + \bar{D}^2\,\sigma_L^2}, \qquad ROP = \bar{D}\,L + SS$$
- $\bar{D}$ = mean P50 daily demand over the next 14 days; $\sigma_D$ = forecast daily standard deviation.
- $L$ = the product's supplier lead time from the catalogue (3–11 days), $\sigma_L = 0.15\,L$.
- $z = 1.645$ (95% service level) when $\bar{D} \ge 3$ units/day, otherwise $1.282$ (90%).

## 4. Does the policy work? (historical replay)
`scripts/run_day3_inventory_backtest.py` replays 2025 with weekly re-ordering and compares this forecast-driven
policy against a 28-day moving average and a same-days-last-year rule. Results:
`reports/day3_inventory_backtest.csv` and the Day 3 report. Demand in this project is synthetic, so treat the
percentages as evidence that the mechanism works, not as a promise of business savings.
