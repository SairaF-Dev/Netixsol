# Understanding Day 5 — Real-Time FastAPI Serving, Statistical A/B Testing & 3-View Interactive Dashboard

This guide explains the engineering architecture, latency optimization patterns, statistical hypothesis testing mathematics, and containerization strategy implemented in **Day 5 (`25%` of the Capstone grade)**.

---

## 1. End-to-End Production Serving Architecture

```
                   ┌──────────────────────────────────────────────────────────┐
                   │   3-View Streamlit Dashboard (Port 8501) / Mobile / Web  │
                   └─────────────────────────────┬────────────────────────────┘
                                                 │ HTTP / JSON
                   ┌─────────────────────────────▼────────────────────────────┐
                   │       FastAPI Serving Gateway (Port 8000, <100ms)        │
                   │  - LatencyTelemetry Middleware (p50, p95, p99, Mean)     │
                   │  - HybridTTLCache (Redis L2 + Thread-Safe LRU/TTL L1)    │
                   └────┬──────────┬─────────────┬─────────────┬──────────┬───┘
                        │          │             │             │          │
        ┌───────────────▼┐ ┌───────▼───────┐ ┌───▼──────────┐ ┌▼────────┐ ┌▼────────────────┐
        │ /recommend/{u} │ │ /search?q=... │ │ /forecast/{p}│ │  /chat  │ │  /reviews/{p}   │
        │ Two-Tower +    │ │ BM25+Vector+  │ │ 30d P10/P50/ │ │ 6 Tools │ │ 6-Aspect ABSA + │
        │ BusinessReRank │ │ RRF+CrossEnc  │ │ P90 + Alerts │ │ + Audit │ │ Courier Penalty │
        └────────────────┘ └───────────────┘ └──────────────┘ └─────────┘ └─────────────────┘
```

---

## 2. Task 1: Sub-100ms FastAPI Serving & Two-Tier Caching ([`src/shopkaro/api/main.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/api/main.py))

### 2.1 Why Naive Model Serving Misses the `<100 ms` SLA
If an API endpoint connects to DuckDB on every request, runs SQL aggregations over `1.4M+` interactions, or re-computes TF-IDF/SVD matrices on the fly, p95 latency spikes to `800–2,500 ms`.

### 2.2 How `ShopKaroServingContainer` Achieves `<50 ms` Cold & `<2 ms` Warm Latency
1. **Singleton Warm-Up (`ensure_initialized`):**
   - Loads the pre-fitted `96-D` semantic index (`models/search_semantic_index.pkl`), customer segment profiles, `sku_forecasts_30d`, `inventory_alerts`, and `review_intelligence_summary` into hash maps once at startup.
2. **Two-Tier `HybridTTLCache`:**
   - **Tier 1 (L1 In-Process OrderedDict LRU + TTL):** Zero-serialization memory lookup (`<0.5 ms` on cache hits) with configurable TTL (`300s`) and max capacity (`4,096` keys).
   - **Tier 2 (L2 Optional Redis Backend):** Automatically connects to `REDIS_URL` (`redis://redis:6379/0` in Docker) so multiple Uvicorn workers share warm cache entries, falling back gracefully to L1 when running standalone.
3. **Real-Time Telemetry Middleware (`/metrics`):**
   - Measures exact wall-clock execution time via `time.perf_counter()`, attaches `X-Process-Time-Ms` to every HTTP response header, and computes rolling `p50`, `p95`, `p99`, and `mean_ms` latency percentiles per route.

---

## 3. Task 2: Statistical A/B Testing Framework ([`src/shopkaro/ab_testing/experiment.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/ab_testing/experiment.py))

### 3.1 Sample Size & Statistical Power Formula
Before launching an online experiment comparing **Control A (`Popularity Baseline`)** against **Treatment B (`Two-Tower Hybrid + Business Re-Ranker + Roman Urdu Explanations`)**, we must determine the minimum sample size per arm ($n$) to avoid underpowered false negatives (Type II error $\beta$):

$$n_{\text{per\_arm}} = \frac{\left(Z_{1-\alpha/2}\sqrt{2\bar{p}(1-\bar{p})} + Z_{1-\beta}\sqrt{p_1(1-p_1) + p_2(1-p_2)}\right)^2}{(p_2 - p_1)^2}$$

For baseline conversion rate $p_1 = 3.20\%$, relative Minimum Detectable Effect $\text{MDE} = +15\%$ ($p_2 = 3.68\%$, $\Delta = 0.0048$), two-sided $\alpha = 0.05$ ($Z_{0.975} = 1.96$), and power $1 - \beta = 0.80$ ($Z_{0.80} = 0.8416$):
- **`required_n_per_arm = 22,732` users** (`45,464` total users, or `~3.8` days at `12,000` daily active users).

### 3.2 Sample Ratio Mismatch (SRM) Verification
Before trusting any metric lift, we run a Pearson $\chi^2$ goodness-of-fit test on the observed user counts $(N_A, N_B)$ against the expected `50/50` split:
$$\chi^2 = \frac{(N_A - E)^2}{E} + \frac{(N_B - E)^2}{E}, \quad E = \frac{N_A + N_B}{2}$$
If $p_{\text{SRM}} < 0.05$, logging or bucketing bias is present and the experiment is invalidated. In our experiment, $p_{\text{SRM}} > 0.05$ (**PASS**).

### 3.3 Parametric & Non-Parametric Hypothesis Tests
1. **Binary Rate Metrics (`CTR`, `CVR`) — Two-Proportion $Z$-Test:**
   $$Z = \frac{\hat{p}_B - \hat{p}_A}{\sqrt{\hat{p}_{\text{pool}}(1 - \hat{p}_{\text{pool}})\left(\frac{1}{N_A} + \frac{1}{N_B}\right)}}, \quad \text{CI}_{95\%} = (\hat{p}_B - \hat{p}_A) \pm 1.96\sqrt{\frac{\hat{p}_A(1-\hat{p}_A)}{N_A} + \frac{\hat{p}_B(1-\hat{p}_B)}{N_B}}$$
2. **Continuous Skewed Monetary Metrics (`AOV`, `RPU` in PKR) — Welch's Two-Sample $t$-Test + Mann-Whitney $U$ Test:**
   $$t = \frac{\bar{Y}_B - \bar{Y}_A}{\sqrt{\frac{s_A^2}{N_A} + \frac{s_B^2}{N_B}}}$$
   Because e-commerce order values follow a heavy-tailed log-normal distribution, we pair Welch's $t$-test with the non-parametric **Mann-Whitney $U$ rank-sum test** to confirm that outliers do not drive the significance decision.

---

## 4. Task 3: 3-View Interactive Streamlit Dashboard & Docker Deployment

### 4.1 Three Role-Specific Operational Views ([`src/shopkaro/dashboard/app.py`](file:///d:/Netixsol/Week11/ShopKaro/src/shopkaro/dashboard/app.py))
1. **Customer Shopping & UrduLish Assistant View:** Live personalized recommendations with Roman Urdu explanations, Hybrid UrduLish search bar with budget parsing, and multi-turn conversational shopping assistant.
2. **Operations & Inventory Control Tower:** 30-day probabilistic `P10 / P50 / P90` quantile fan charts, Safety Stock & Reorder Point (`ROP`) calculators, `CRITICAL_STOCKOUT_7D` / `OVERSTOCK_DEAD_CAPITAL` filters, and the Pakistani Hijri festival calendar.
3. **Executive, Seller & A/B Experimentation Hub:** Customer RFM segments, 6-Aspect ABSA scorecards, products flagged *"unfairly penalised by courier"* (from predicted aspects) (de-conflating product quality from 3PL courier delays), and the A/B test decision summary.

### 4.2 Running Locally & via Docker

```powershell
# 1. Run Day 5 Verification & Benchmark Suite
.\.venv\Scripts\python.exe scripts/run_day5.py
.\.venv\Scripts\python.exe -m pytest tests/test_day5.py -v

# 2. Launch FastAPI Server Locally (Port 8000)
.\.venv\Scripts\python.exe -m uvicorn shopkaro.api.main:app --host 0.0.0.0 --port 8000

# 3. Launch 3-View Streamlit Dashboard Locally (Port 8501)
.\.venv\Scripts\python.exe -m streamlit run src/shopkaro/dashboard/app.py

# 4. Launch Full Stack via Docker Compose (Redis + FastAPI + Streamlit)
docker compose up --build
```

---

### 4.3 Islamic Modesty (Haya) & Authentic Pakistani Cultural Localization

To ensure ShopKaro reflects genuine Pakistani e-commerce standards (modeled after **Bareeze**, **Khaadi**, **Junaid Jamshed (J.)**, and **Sapphire**), the catalog imagery and UX strictly observe Islamic modesty principles and Pakistani cultural heritage:

1. **Islamic Modesty in Apparel (Haya & Full Coverage):**
   - **Women's Lawn Suits (`pakistani_modest_lawn.jpg`):** Modest 3-piece unstitched lawn ensemble featuring long kameez with subtle neckline embroidery, loose cambric trousers, and a flowy dupatta draped gracefully over the shoulders with full modest coverage.
   - **Modest Pakistani Bridal Attire (`pakistani_modest_bridal_lehenga.jpg`):** Authentic Pakistani Muslim Nikah/Baraat ensemble in deep crimson red with a long-length embroidered bridal kurti (fully covering the midriff and waist with intricate dabka, tilla, and zardozi needlework, eliminating bare midriffs or Indian choli cuts), paired with a flared lehenga and a sheer dupatta draped modestly over the head.
   - **Sunnah-Inspired Men's Kurta Shalwar (`pakistani_modest_mens_kurta.jpg`):** Crisp off-white and cream textured cotton-silk kurta featuring a classic ban/mandarin collar with fine tonal needlework along the placket, cuffed sleeves, and modest cut.
2. **Pakistani Islamic Gifts & Traditional Footwear:**
   - **Eid Gift Hamper (`pakistani_islamic_eid_gift_oud_shawl.jpg`):** Luxury crystal flacon bottle of Arabian Oud & Amber Attar perfume (J. Fragrances style), folded ivory-white pure pashmina shawl, and olive-wood prayer beads (*tasbeeh*) arranged on a carved Islamic geometric walnut tray.
   - **Handcrafted Velvet Khussa (`pakistani_khussa_maroon.jpg`):** Handcrafted maroon velvet Punjabi khussa shoes with traditional golden tilla embroidery.
3. **Local Asset Serving via Base64 Data URIs:**
   - All assets reside locally in `src/shopkaro/dashboard/assets/`, cached in memory via LRU cache, eliminating broken external CDN links and ensuring immediate, sub-millisecond local rendering.

