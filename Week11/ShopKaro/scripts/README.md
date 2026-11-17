# ShopKaro — Scripts

Command-line entry points that build the data, train and evaluate the models, and write everything in `reports/`.

## How to run

Run from the project root (`Week11/ShopKaro`) with the Python 3.11 virtual environment and `src` on the path:

```powershell
.venv311\Scripts\Activate.ps1
$env:PYTHONPATH = "src"
python scripts/run_day1_pipeline.py
```

Useful environment variables (all optional, see `src/shopkaro/config/settings.py`):

| Variable | Default | Effect |
| :-- | :-- | :-- |
| `REPORTS_DIR` | `reports` | Where CSV / JSON / Markdown results and `figures/` are written. Point it elsewhere for a trial run so the committed reports are not overwritten. |
| `SEARCH_EMBEDDINGS` | `auto` | `auto` uses the multilingual-e5 neural model; `lsa` uses the light TF-IDF + SVD vectors (no model download). |
| `SEARCH_CROSS_ENCODER` | `auto` | `off` skips the cross-encoder re-ranker in search. |
| `HF_HUB_OFFLINE` | unset | `1` uses only Hugging Face models already in the local cache. |
| `RECOMMENDER` | `item_cf` | `two_tower` serves the neural two-tower instead of item-CF (API / dashboard). |
| `LLM_API_KEY` | unset | Gemini key for the LLM shopping assistant and the weekly report prose. Without it the rule-based / template versions are used. |

## Rebuild order

Each day reads what the previous day wrote to `data/processed/shopkaro.duckdb`. A full rebuild runs, in order:

1. `run_day1_pipeline.py`
2. `run_day2_task1.py` … `run_day2_task5.py`, then `run_day2_discovery_eval.py` and `run_two_tower_seeds.py`
3. `precompute_recommendations.py --two-tower` (serving models used by Days 4–5)
4. `run_day3_task1.py`, `run_day3_task2_task3.py`, `run_day3_task4_task5.py`, `run_day3_inventory_backtest.py`
5. `run_day4_task1.py`, `run_day4_task2_task3.py`, `python -m shopkaro.search.personalization_eval`, `run_day4_task4_task5.py`
6. `run_day5.py`, `measure_recommender_latency.py`, `run_weekly_insight_report.py`
7. For deployment: `build_dashboard_images.py`, `build_deploy_bundle.py`

Times are on a laptop CPU.

## Script reference

### Day 1 — data foundation

| Script | What it does | Writes |
| :-- | :-- | :-- |
| `run_day1_pipeline.py` | Loads RetailRocket / Olist data into DuckDB, removes bots and duplicates, builds 30-minute sessions, maps items to the Pakistani catalogue (per-type prices and brands), runs EDA, RFM + K-Means segments, cohort retention, the chronological train / val / test split and the 64-dim item text embeddings. | `data/processed/shopkaro.duckdb`, `models/item_text_embeddings.npy`, `reports/figures/01–07_*.png`, `docs/architecture/data_model_er.md` |

### Day 2 — recommendation engine

| Script | What it does | Writes |
| :-- | :-- | :-- |
| `run_day2_task1.py` | Fits and scores the 3 baselines (popular, favourite-category popular, 7-day trending). | console only |
| `run_day2_task2.py` | Item-to-item CF and implicit ALS; tunes ALS over 4 configs on validation; prints "similar products". | console only |
| `run_day2_task3.py` | Content-based model, hybrid blend and cold-start routing. | console only |
| `run_day2_task4.py` | Evaluates all 8 models (incl. the PyTorch two-tower) on the chronological test set, then a paired bootstrap (2,000 resamples, same users) of the two-tower vs the hybrid blend, item-CF and ALS. | `reports/day2_model_comparison.csv`, `reports/day2_two_tower_significance.json`, `reports/day2_two_tower_training_log.json`, `reports/figures/08_recommender_model_comparison.png` |
| `run_day2_task5.py` | Business re-ranker (stock / purchased filters, brand cap, margin / sale / Eid boosts), association rules, Roman Urdu explanations. | console only |
| `run_day2_discovery_eval.py` | "Repeat own history" baseline and the discovery protocol (only never-seen items count). | `reports/day2_discovery_evaluation.csv` |
| `run_two_tower_seeds.py` | Trains the two-tower with seeds 42 / 43 / 44 and scores each on main, discovery and new-user protocols. | `reports/day2_two_tower_seeds.csv` |
| `precompute_recommendations.py` | Daily batch job: retrains item-CF on all interactions (~1 min); with `--two-tower` also the neural two-tower (~10 min). | `models/item_cf_serving.joblib`, `models/two_tower_serving.joblib` |
| `measure_recommender_latency.py` | Serving latency of both recommenders (model only, then through the API with the re-ranker, uncached). Needs both serving models. | `reports/recommender_serving_latency.json` |

### Day 3 — forecasting and inventory

| Script | What it does | Writes |
| :-- | :-- | :-- |
| `run_day3_task1.py` | Seasonal decomposition, ADF stationarity tests, festival uplift and the lunar-calendar shift. | `reports/figures/09_*.png`, `10_*.png` |
| `run_day3_task2_task3.py` | Forecasting models (baselines, ETS / ARIMA, Prophet, global LightGBM, Croston / TSB) with 4-fold rolling-origin backtest. | `reports/day3_forecasting_backtest_comparison.csv`, `reports/day3_forecast_accuracy_breakdown.csv`, `reports/figures/11_*.png` |
| `run_day3_task4_task5.py` | P10 / P50 / P90 forecasts, safety stock, reorder points, stock alerts and the pre-festival plan. | `reports/day3_inventory_alerts.csv`, `reports/day3_prefestival_plan_top100.csv`, `reports/figures/12_*.png`, DuckDB tables `sku_forecasts_30d`, `inventory_alerts` |
| `run_day3_inventory_backtest.py` | Replays 2025 inventory under moving-average, seasonal-naive and forecast-driven replenishment (~20 min). | `reports/day3_inventory_backtest.csv`, `reports/day3_inventory_backtest.json` |
| `run_day3_slow_mover_check.py` | Robustness check: Croston-SBA / TSB vs LightGBM on 8 extra non-festival cut-offs. | `reports/day3_slow_mover_extra_cutoffs.csv` |

### Day 4 — search, assistant and reviews

| Script | What it does | Writes |
| :-- | :-- | :-- |
| `run_day4_task1.py` | Hybrid search (BM25 + multilingual-e5 + RRF + feature re-ranker + cross-encoder) and the Roman Urdu query parser; benchmark on dev and held-out queries with significance tests. | `reports/day4_search_comparison.csv`, `reports/day4_search_per_query.csv`, `reports/day4_search_significance.json`, `models/search_semantic_index.pkl` |
| `run_day4_task2_task3.py` | Personalised search re-ranking demo and the tool-calling UrduLish shopping assistant. | console only |
| `python -m shopkaro.search.personalization_eval` | Measures personalised vs plain search on dev and held-out users. | `reports/day4_personalized_search_eval.json`, `reports/day4_personalized_search_per_query.csv` |
| `run_day4_task4_task5.py` | Review intelligence: sentiment, 6-aspect ABSA, topics, fake / spam detection, seller scorecards and complaint tables. | `reports/day4_product_review_intelligence.csv`, `reports/day4_review_intelligence_metrics.csv`, `reports/day4_review_benchmark_errors.json`, `reports/day4_seller_scorecards.csv`, `reports/day4_complaints_by_*.csv`, `reports/day4_falling_sentiment.csv`, `reports/figures/13_*.png` |
| `run_weekly_insight_report.py` | Weekly management report: numbers from SQL / pandas, prose from Gemini if `LLM_API_KEY` is set. Any number in the LLM text that is not in the computed facts makes it fall back to the template. | `reports/weekly_insight_report.md`, `reports/weekly_insight_facts.json` |

### Day 5 — serving, A/B test and dashboard

| Script | What it does | Writes |
| :-- | :-- | :-- |
| `run_day5.py` | FastAPI latency benchmark, A/B test (power analysis, z-test, Welch t-test, segments, guardrails, ship decision) and the dashboard data check. | `reports/day5_ab_test_results.csv`, `reports/day5_ab_test_segment_subgroups.csv`, `reports/day5_ab_test_summary.json`, `reports/day5_ab_test_ship_decision_report.md`, `reports/figures/14_*.png` |

### Deployment

| Script | What it does | Writes |
| :-- | :-- | :-- |
| `build_dashboard_images.py` | Resizes the dashboard's product photos for the web, so a page no longer sends ~30 MB of base64 images. | `src/shopkaro/dashboard/static/` |
| `build_deploy_bundle.py` | Zips the DuckDB database and the three model files the lite (Streamlit Cloud) dashboard needs. Upload the zip to a GitHub Release and set `DATA_BUNDLE_URL` to its link; the app downloads it on first start if the database is missing. | `dist/shopkaro_data_bundle.zip` |
