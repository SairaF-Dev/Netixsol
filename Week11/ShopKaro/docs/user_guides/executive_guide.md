# ShopKaro Executive & Product Leadership Guide

## 1. Online Experimentation Decision Matrix (A/B Testing)
ShopKaro utilizes rigorous hypothesis testing before promoting any recommendation algorithm:

Experiment `EXP-2026-REC-ITEMCF-V1`: a replay of real test-window behaviour (162,386 visitors), personalised
homepage (item-CF + business rules) vs popular items. Full write-up: `reports/day5_ab_test_ship_decision_report.md`.

| Evaluation stage | Decision rule (fixed in advance) | Result |
| :--- | :--- | :---: |
| **1. Sample ratio mismatch** | Chi-square on the 50/50 split | PASS |
| **2. Primary: homepage conversion** | Significantly better at alpha = 0.05 | 0.0086% -> 0.0517% (7 vs 42 buyers), p = 3.6e-7 |
| **3. Click-through** | Secondary, Holm-corrected | 0.84% -> 2.50% |
| **4. Discovery conversion** (products not seen before) | Secondary | 0.0086% -> 0.0062%, not significant (p = 0.58) |
| **5. Guardrails** | Latency p95 < 100 ms, no extra out-of-stock items, max 2 per brand | All PASS |
| **Decision** | SHIP if 2 and 5 hold | **SHIP** |

**What this means for management:** 37 of the 42 extra buyers bought a product they had already looked at; the
homepage brings shoppers back to items they were considering. A simple "recently viewed" row would capture much
of that. The machine-learning model has **not yet** been shown to sell products shoppers had not already found.
Estimated value: about **PKR 8.3M per month** in homepage-attributed revenue (95% range PKR 2.4M to 14.3M, based on
49 buyers, so treat it as an order of magnitude). Next step: a live test to confirm, measured weekly.

## 2. Review Intelligence & Courier De-Biasing for Seller Relations
- **The Problem:** 3PL courier delays (TCS / Leopards / Trax) routinely cause frustrated buyers to leave 1-star reviews on authentic high-quality Pakistani apparel.
- **The Solution:** Reviews are scored separately for `quality` and `delivery`. Products where at least 65% of reviews praise quality but at least 35% complain about delivery (and the rating is below 4.15) are flagged as **"unfairly penalised by courier"** for a courier review rather than a seller penalty. On current data that is 1 product(s). Accuracy on new hand-written reviews: 77% for sentiment, so use it to prioritise human review, not for automatic penalties.

