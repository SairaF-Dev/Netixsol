# Day 5 Technical Report — Real-Time FastAPI Serving (`<100 ms`), Statistical A/B Testing & 3-View Interactive Streamlit Dashboard

**Project:** ShopKaro — AI Commerce Intelligence Platform (Week 11 Capstone)  
**Module Scope:** Day 5 (`25%` Total Capstone Weight: `15%` Production API, Caching & A/B Testing + `10%` 3-View Dashboard & Containerization)  
**Key Deliverables:**
- FastAPI Service: [`src/shopkaro/api/main.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/api/main.py)
- Statistical A/B Testing Engine: [`src/shopkaro/ab_testing/experiment.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/ab_testing/experiment.py)
- 1-Page Executive Ship/No-Ship Memo: [`reports/day5_ab_test_ship_decision_report.md`](file:///d:/Netixsol/Week11/ShopKaro/reports/day5_ab_test_ship_decision_report.md)
- 3-View Interactive Dashboard: [`src/shopkaro/dashboard/app.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/dashboard/app.py)
- Containerization: [`Dockerfile`](file:///d:/Netixsol/Week11/ShopKaro/Dockerfile) & [`docker-compose.yml`](file:///d:/Netixsol/Week11/ShopKaro/docker-compose.yml)

---

## 1. Task 1: Real-Time FastAPI Serving & Latency Benchmark (`<100 ms` SLA)

### 1.1 Endpoint Latency & Two-Tier Cache Telemetry

All 6 endpoint families in [`src/shopkaro/api/main.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/api/main.py) are backed by `HybridTTLCache` (Redis L2 with automatic thread-safe in-memory LRU+TTL L1 fallback, `ttl=300s`) and monitored via `LatencyTelemetry` middleware:

| Endpoint | HTTP Method | Uncached Cold Latency (ms) | Warm Cached Latency (ms) | `<100 ms` SLA Status |
| :--- | :---: | :---: | :---: | :---: |
| **`/health`** | `GET` | `81.10 ms` | `19.57 ms` | **PASS** |
| **`/recommend/{user_id}`** | `GET` | `23.52 ms` | `16.42 ms` | **PASS** |
| **`/search`** | `GET` | `79.14 ms` | `12.73 ms` | **PASS** |
| **`/forecast/{product_id}`** | `GET` | `13.51 ms` | `19.95 ms` | **PASS** |
| **`/chat`** | `POST` | `20.89 ms` | `17.19 ms` | **PASS** |
| **`/reviews/{product_id}`** | `GET` | `26.22 ms` | `27.12 ms` | **PASS** |
| **Overall Service Telemetry** | — | **Mean: `11.40 ms` / p50: `7.01 ms`** | **p95: `35.57 ms`** | **PASS (`<100 ms`)** |

---

## 2. Task 2: Statistical A/B Testing Framework & Executive Decision

### 2.1 Experiment (rewritten 2026-11-09)
The earlier version of this section reported a simulation whose lifts were typed into the code, so it could not
fail. It was replaced by a replay of real behaviour; see `reports/day5_ab_test_ship_decision_report.md`.

- **Design:** 162,386 test-window visitors, 50/50 by hashed user ID; control = top-10 popular items, treatment =
  item-CF + business re-ranker trained only on pre-test data. A shown item counts as clicked / bought only if the
  visitor really interacted with / bought it in the test window.
- **Primary metric (pre-registered):** homepage conversion 0.0086% -> 0.0517% (7 vs 42 buyers), Fisher's exact p = 3.6e-7.
- **Secondary (Holm-corrected):** CTR 0.84% -> 2.50%; discovery CTR +14% [+3%, +25%]; discovery conversion not
  significant (p = 0.58); revenue per visitor PKR 0.20 -> 8.51.
- **Checks:** guardrails pass; A/A test not significant; peeking simulation 5.2% vs 26.8% false positives.
- **Finding:** 37 of 42 treatment buyers bought a product they had already browsed, so the gain is mainly re-surfacing.
- **Decision:** SHIP (by the pre-registered rule), with a live test to confirm the size of the effect.

---

## 3. Task 3: 3-View Interactive Streamlit Dashboard & Containerization

- **View 1 — Customer Shopping & UrduLish Assistant:** Persona switcher (`Warm Customer` vs `Cold-Start Visitor`), personalized recommendations with Roman Urdu explanations, live Hybrid UrduLish search bar with budget enforcement, and multi-turn conversational shopping assistant with Zero-Hallucination verification badge.
- **View 2 — Operations, Demand Forecasting & Inventory Control Tower:** 30-day probabilistic `P10 / P50 / P90` quantile fan charts, Safety Stock & Reorder Point (`ROP`) tables across `300` top SKUs (`CRITICAL_STOCKOUT_RISK`, `FESTIVAL_SURGE_WATCH`, `OVERSTOCK_DEAD_CAPITAL`, `HEALTHY_STOCK`), and the `17`-event Pakistani Hijri Lunar & Commercial Festival Calendar.
- **View 3 — Executive, Seller & A/B Experimentation Hub:** `5` Customer RFM segments, products flagged as *"unfairly penalised by courier"* (computed from predicted aspects) (de-conflating product quality from 3PL courier delays), `100` top Seller Scorecards, and live A/B testing & API telemetry.

