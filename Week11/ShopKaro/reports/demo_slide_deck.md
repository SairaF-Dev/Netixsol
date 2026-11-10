# ShopKaro Stakeholder Presentation Slide Deck Outline

**Presentation Title:** ShopKaro AI Commerce Intelligence Platform  
**Subtitle:** Recommendations, Probabilistic Demand Forecasting & UrduLish Shopping Assistant  
**Audience:** ShopKaro Executive Leadership & Capstone Evaluation Panel  
**Slides:** 10 Slides Total

---

### Slide 1: Title & Executive Summary
- **Headline:** Transforming ShopKaro into Pakistan's #1 AI-Powered Marketplace
- **Key Takeaways:**
  - Full-stack AI Commerce Engine: real-time item-to-item recommender, quantile demand forecaster, hybrid UrduLish search, LLM shopping assistant, and 6-aspect review analysis.
  - A/B test (replay of 162,386 real visitors): homepage buyers 7 -> 42 (p = 3.6e-7), est. ~PKR 8.3M/month; most of the gain is re-surfacing products shoppers already browsed.
  - Sub-100ms real-time serving gateway with two-tier Redis caching.

---

### Slide 2: The Core Retail Problems in Pakistan
- **Four Critical Growth Bottlenecks:**
  1. *Static Merchandising:* 1M+ monthly visitors saw identical top products regardless of demographic.
  2. *Broken Search:* Keyword search failed on Roman Urdu queries (*"shaadi red lehenga 20 hazaar tak"*).
  3. *Pre-Eid Stockouts:* Re-ordering on last month's sales misses the Eid surge (in our 2025 replay a 28-day moving average lost 105,849 units during Ramadan + Eid ul Fitr).
  4. *Conflated Reviews:* 3PL courier delays dragged down high-quality authentic Pakistani designer apparel.

---

### Slide 3: End-to-End Enterprise System Architecture
- **Lakehouse Layer:** DuckDB + Apache Parquet (1.4M+ interactions, 30-min sessionization, RFM segmentation).
- **Intelligence Layer:** item-to-item collaborative filtering, gradient-boosted demand forecasts with P10/P50/P90 bands, Okapi BM25 + TF-IDF/SVD semantic search.
- **Serving Layer:** FastAPI (<10ms cached latency) + Redis L2 + In-Process L1 LRU Cache.
- **Client Layer:** Streamlit Responsive Storefront + UrduLish Conversational Assistant.

---

### Slide 4: Personalized Recommendation Engine (Two-Tower Hybrid)
- **Architecture:** User Tower (Segment + Category History) + Item Tower (Title & Category Embeddings).
- **Business Re-Ranking Rules:**
  - Out-of-Stock (OOS) suppression.
  - Brand diversity cap ($\le 2$ items/brand).
  - Festival & seasonal boosts (Ramadan lawn suits & Eid gifts).
  - Frequently Bought Together (FP-Growth association rules).
- **Benchmark Results:** NDCG@10 of **0.1923** (+35.4% lift over popularity baseline, beating the +20% requirement).

---

### Slide 5: Intelligent Roman Urdu Hybrid Search & Query Parsing
- **Hybrid Scoring:** Okapi BM25 Keyword Search + 96-D Subword Semantic Vector + Reciprocal Rank Fusion ($k=60$).
- **Rule & Regex Parser:** Automatic budget ceiling extraction (*"20 hazaar"*, *"1.5 lac"*), occasion detection (*"shaadi"*, *"eid"*), and category mapping.
- **Evaluation:** Evaluated across 50 labeled retail queries; Hybrid achieved **0.864 NDCG@10** vs 0.612 for keyword search alone.

---

### Slide 6: UrduLish AI Shopping Concierge
- **Bilingual Dialogue Engine:** Supports Roman Urdu, Urdu script, and English conversational shopping.
- **6 Integrated Tools:** `search_products`, `get_recommendations`, `compare_products`, `add_to_cart`, `get_order_status`, `get_review_summary`.
- **Zero-Hallucination Audit:** 100% of product specifications, prices, and stock counts verified against the active catalog database before response emission.

---

### Slide 7: 6-Aspect ABSA & Courier Delay De-Biasing
- **Clause-Aware NLP:** Contrastive splitters disambiguate product quality praise from courier delivery complaints (*"Kapra acha hai lekin delivery late thi"*).
- **6 Aspects:** Quality, Price, Delivery, Size/Fit, Packaging, Seller.
- **Quality vs courier:** product quality and delivery are scored separately, so courier delays are not blamed on the product (1 product(s) currently meet the "unfairly penalised" rule).
- **Measured on new hand-written reviews:** sentiment 77% accuracy (baseline 40%), spam F1 0.89, no genuine review flagged as spam.

---

### Slide 8: Supply Chain Control Tower & Quantile Demand Forecasting
- **Probabilistic Trajectories:** gradient-boosted P50 forecast with a P10–P90 band (79% measured coverage of the nominal 80%).
- **Automated Inventory Decisions:** Dynamic Reorder Points ($ROP$), Safety Stock ($SS$), and 14-day stockout risk alerts.
- **2025 replay (synthetic demand):** forecast-driven weekly re-ordering lost **96% fewer units during Ramadan + Eid ul Fitr** than a 28-day moving average (94% fewer than same-days-last-year) while holding **22% less stock**. Demand was generated from the same festival calendar the model uses, so real gains would be smaller.

---

### Slide 9: A/B Test and Rollout Decision (`EXP-2026-REC-ITEMCF-V1`)
- **Method:** replay of 4 weeks of real behaviour, 162,386 visitors, 50/50 hashed split; model trained only on earlier data; decision rule fixed in advance.
- **Primary (homepage conversion):** 0.0086% -> 0.0517% (7 vs 42 buyers), Fisher's exact p = 3.6e-7. Click-through 0.84% -> 2.50%.
- **Where it comes from:** 37 of 42 buyers bought a product they had already browsed. Discovery conversion: no significant difference (p = 0.58).
- **Checks:** guardrails pass, A/A test clean, peeking would have inflated false positives from 5% to 27%.
- **Decision:** **SHIP**, then confirm with a live test measured weekly (watch recency decay).

---

### Slide 10: Production Readiness, Cultural Localization & Future Roadmap
- **Cultural & Islamic Modesty (Haya):** Curated Pakistani studio photography (3-piece modest lawn, full-coverage bridal lehenga, Sunnah-inspired kurtas, Arabian oud sets).
- **Deployment:** Docker containerized stack (`docker-compose.yml` for FastAPI, Redis, Streamlit).
- **Post-Capstone Roadmap:** Visual "Shop the Look" image search, Kafka clickstream ingestion, and WhatsApp Conversational Commerce.

