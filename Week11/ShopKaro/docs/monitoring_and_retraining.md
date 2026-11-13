# ShopKaro Production Monitoring, Retraining & Future Enhancements Guide

## 1. Automated Retraining Schedule

| Component | Retraining Cadence | Trigger Mechanism | Artifact Updated |
| :--- | :--- | :--- | :--- |
| **Recommender Semantic Index** | **Daily (02:00 PKT)** | Scheduled cron job over recent 24h clickstream interactions. | `models/search_semantic_index.pkl`, Redis cache invalidation. |
| **Item-to-Item CF Recommender (production)** | **Daily (02:00 PKT)** | `python scripts/precompute_recommendations.py` retrains on all interactions (~10 s), then restart the API to load it. Live clicks between retrains are handled by `POST /events`. | `models/item_cf_serving.joblib` |
| **Neural Two-Tower Recommender (`RECOMMENDER=two_tower`)** | **Daily (02:00 PKT)** | `python scripts/precompute_recommendations.py --two-tower` (~7 min CPU, needs torch; settings fixed from the Day 2 validation run). If the artifact is missing or stale the API falls back to item-CF and says so. | `models/two_tower_serving.joblib` |
| **LightGBM Quantile Forecaster** | **Weekly (Sunday 04:00 PKT)** | Incorporates latest 7-day actual sales figures and inventory adjustments. | `models/forecaster_lightgbm.pkl`, `data/duckdb/shopkaro.duckdb` alerts. |
| **Customer RFM Segmentation** | **Monthly (1st of Month)** | Re-clustering 1M+ active user vectors via K-Means ($k=5$). | `models/customer_segments.parquet` |

---

## 2. Production Health & Drift Monitoring

### A. Data Drift Monitoring (Input Feature Drift)
- **Population Stability Index (PSI):** Evaluated daily on user price distribution and search query length. Alert triggered if $\text{PSI} > 0.25$.
- **Kolmogorov-Smirnov (KS) Test:** Run on numerical click frequencies to detect bot surges.

### B. Concept Drift Monitoring (Model Degradation)
- **CTR & CVR Rolling Thresholds:** If 3-day rolling conversion falls $>15\%$ below baseline, traffic automatically rolls back to Control (Popularity + Category fallback).
- **Out-of-Stock Impression Rate:** Hard guardrail threshold of $\le 1.0\%$. If violated, instant alert dispatched to logistics on-call.

---

## 3. Rollback & Failover Strategy
- **L1 In-Memory LRU Failover:** If Redis connection drops, `HybridTTLCache` automatically falls back to in-process memory without throwing 500 errors.
- **Serving Fallback Hierarchy:**
  1. Two-Tower Personalized Hybrid Model (Normal)
  2. Segment-Conditioned Category Popularity (Degraded Recommender)
  3. Global Top-10 In-Stock Bestsellers (Emergency Failover)

---

## 4. Future Enhancements Roadmap (Post-Week 11)

1. **Visual "Shop the Look" Image Search:** Integration of CLIP / SigLIP vision transformers allowing shoppers to upload Pakistani bridal dresses from Instagram and discover matching catalog dupes.
2. **Real-Time Event Streaming via Apache Kafka:** Transitioning from 30-minute micro-batches to sub-second clickstream event processing with Flink/Kafka.
3. **WhatsApp Conversational Commerce:** Extending the UrduLish Shopping Concierge to the WhatsApp Business API for automated order placement and COD tracking.
4. **Dynamic Courier Allocation Engine:** Real-time routing between TCS, Leopards, and Trax based on historical delivery reliability per postal code.
5. **Reinforcement Learning for Search Re-Ranking (Bandits):** Contextual multi-armed bandits to optimize trade-offs between exploration of new SKUs and exploitation of proven bestsellers.

## Weekly management insight report (added 2026-11-10)
Every Monday: `python scripts/run_weekly_insight_report.py` writes `reports/weekly_insight_report.md` (LLM prose,
numbers from SQL in `weekly_insight_facts.json`; LLM text with any number not in the facts is replaced by a template).
