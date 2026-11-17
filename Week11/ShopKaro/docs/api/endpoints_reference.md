# ShopKaro REST API Endpoints Reference

Base URL: `http://localhost:8000` · interactive docs at `/docs` · JSON responses.  
Every example below is a real response from the API (captured 2026-11-17), shortened where marked `…`.

**Latency** (`reports/recommender_serving_latency.json`, 200 warm users, uncached, through the API with the business
re-ranker): `/recommendations` p95 **4.0 ms** with item-CF, **4.8 ms** with the two-tower — well under the 100 ms
target. Cached responses are faster still. `/search` and `/assistant/chat` are slower: search runs neural models
(the first call also loads them, ~4 s), and the assistant waits for the LLM (typically 1–15 s).

**Caching:** an in-process LRU + TTL cache (5 minutes) always runs. If `REDIS_URL` is set and reachable (as in
`docker-compose.yml`), Redis is used as a shared second level; `/health` shows which (`Redis_With_InMemory_L1`, or
`InMemory_LRU_TTL` / `InMemory_LRU_TTL (Redis_Fallback)` without Redis).

**User IDs** are strings. Demo users with real history: `USR-928443` (lawn & Eid), `USR-368401` (phones),
`USR-1398811` (kids & school). Any unknown ID (e.g. `new-visitor-1`) is treated as a new visitor (cold start).

---

## 1. System Health & Telemetry

### `GET /health`
Service status, DuckDB connection, assistant engine and cache state.

```bash
curl "http://localhost:8000/health"
```
```json
{
  "status": "healthy",
  "service": "ShopKaro",
  "environment": "development",
  "duckdb_connected": true,
  "assistant_engine": "llm (gemini-3.1-flash-lite)",
  "tables_count": 29,
  "cache": {"backend": "InMemory_LRU_TTL", "entries": 0, "hits": 0, "misses": 0, "hit_rate_pct": 0.0}
}
```

### `GET /metrics`
Cache statistics and latency percentiles (mean, p50, p95, p99) overall and per route since the API started, plus
the SLA check for recommendation routes.

```json
{
  "service": "ShopKaro",
  "cache": {"backend": "InMemory_LRU_TTL", "entries": 7, "hits": 0, "misses": 7, "hit_rate_pct": 0.0},
  "latency": {
    "overall": {
      "total_requests": 10,
      "sla_scope": "recommendation routes, p95 < 100 ms",
      "recommendation_p95_ms": 9.43,
      "sla_p95_under_100ms_met": true,
      "…": "…"
    },
    "routes": {
      "/recommendations/{user_id}": {"requests": 2, "mean_ms": 7.01, "p50_ms": 7.01, "p95_ms": 9.43, "p99_ms": 9.65},
      "…": "…"
    }
  }
}
```

---

## 2. Recommendation Engine Endpoints

### `GET /recommendations/{user_id}`
Personalised top-K list: item-to-item CF on the user's history plus live session clicks, then the business re-ranker
(in stock only, already-bought removed, max 2 per brand, sale / margin / festival boosts). Set `RECOMMENDER=two_tower`
to serve the neural two-tower instead; the `model` block in the response says which model actually served.

**Parameters:**
- `user_id` (path, required): customer ID string, e.g. `USR-928443`. Unknown IDs get the cold-start path.
- `top_k` (query, 1–50, default `10`)
- `occasion` (query, optional): festival boost, e.g. `Eid`, `Ramadan`, `11.11`, `Shaadi`, `Winter`.

```bash
curl "http://localhost:8000/recommendations/USR-928443?top_k=3&occasion=Eid"
```
```json
{
  "user_id": "USR-928443",
  "segment_name": "Bargain Hunters & Cart Hesitators",
  "is_cold_start": false,
  "favorite_category": "Women's Lawn & Unstitched",
  "ranking_strategy": "item_cf_realtime+business_reranker",
  "history_items": 40,
  "session_events": 0,
  "onboarding_categories": [],
  "business_rules_applied": {
    "in_stock_only": true, "exclude_already_purchased": true, "max_per_brand": 2, "festival_boost": "Eid",
    "out_of_stock_removed": 7, "already_purchased_removed": 0, "brand_cap_skipped": 0
  },
  "model": {
    "model": "4. Item-to-Item Collaborative Filtering (Cosine)",
    "trained_at": "2026-11-16T16:55:45+00:00",
    "requested_recommender": "item_cf",
    "serving_recommender": "item_cf",
    "fallback_reason": null,
    "…": "…"
  },
  "count": 3,
  "recommendations": [
    {
      "rank": 1,
      "product_id": "SK-06148",
      "title": "Alkaram Studio Luxury Embroidered Shawl (Emerald Green)",
      "brand": "Alkaram Studio",
      "category": "Women's Lawn & Unstitched",
      "price_pkr": 5450.0,
      "on_sale": false,
      "discount_pct": 0.0,
      "stock_qty": 42,
      "avg_rating": null,
      "review_count": 0,
      "model_score": 0.6939,
      "rerank_score": 1.4464,
      "reason_type": "revisit",
      "because_of_product_id": "SK-06148",
      "explanation_roman_urdu": "Aap ne yeh pehle dekha tha — abhi bhi stock mein hai. (Eid special)",
      "explanation_en": "You viewed this before and it's still in stock. (Eid pick)"
    },
    "…"
  ],
  "cache_hit": false
}
```

- `reason_type`: `revisit` | `similar_to_history` | `popular_in_category`; `because_of_product_id` names the item
  that triggered it.
- New visitor (`/recommendations/new-visitor-1`): `"is_cold_start": true`,
  `"ranking_strategy": "cold_start_popularity+business_reranker"`, items such as
  `SK-00002` Khaadi festive lawn with *"'Women's Lawn & Unstitched' mein ShopKaro ke maqbool products mein se ek (10% OFF)."*
  After onboarding (below) the strategy uses the chosen categories; after a click it personalises from that click.

### `POST /events`
Records a live click; the user's next `/recommendations` call reflects it (the cache key includes the user's
event version). Events last for the session (30 minutes).
```bash
curl -X POST http://localhost:8000/events -H "Content-Type: application/json" \
  -d '{"user_id": "new-visitor-1", "product_id": "SK-00013", "event_type": "view"}'
```
`event_type`: `view` | `addtocart` | `transaction` (`422` otherwise). Unknown product -> `404`.

### `POST /onboarding/{user_id}`
Cold-start onboarding answers. Until the user has clicks, recommendations are popular items in these categories.
```bash
curl -X POST http://localhost:8000/onboarding/new-visitor-1 -H "Content-Type: application/json" \
  -d '{"categories": ["Kids & School Supplies"]}'
```

### `GET /similar/{product_id}`
Nearest neighbours of a SKU by cosine similarity of its title + description text embedding
(`models/item_text_embeddings.npy`). Text only (no images). Works for brand-new products with no interactions, so it
is also the new-item cold-start path. In-stock items only; duplicate titles are collapsed.
Query params: `top_k` (1–50, default 10). `404` for unknown SKUs.

```bash
curl "http://localhost:8000/similar/SK-00013?top_k=2"
```
```json
{
  "product_id": "SK-00013",
  "source": {"product_id": "SK-00013", "title": "Samsung Galaxy A55 5G (8GB/256GB) Awesome Navy — Official PTA Approved",
             "brand": "Samsung", "category": "Smartphones & Accessories", "price_pkr": 119999.0, "stock_qty": 1715,
             "avg_rating": 4.07, "review_count": 15},
  "method": "content_cosine_item_text_embeddings",
  "results": [
    {"product_id": "SK-02476", "title": "Samsung Original 5G Smartphone in White with Fast Charging", "brand": "Samsung",
     "category": "Smartphones & Accessories", "price_pkr": 41750.0, "stock_qty": 6, "avg_rating": null,
     "review_count": 0, "similarity": 0.9365},
    "…"
  ],
  "count": 2,
  "cache_hit": false
}
```

### `GET /bought-together/{product_id}`
Complementary products. Each result has a `rule_source`:
- `Session_Basket_FP_Growth`: pair rule mined from session co-occurrence; `support`, `confidence`, `lift` are measured.
- `Curated_Accessory_Bundle_FP_Growth` / `Cross_Category_Complement_Rule`: hand-written category fallbacks. These have
  **no measured statistics**, so `support/confidence/lift` are `null` and `mined_from_data` is `false`.

Query params: `top_k` (1–20, default 5). `404` for unknown SKUs.

```bash
curl "http://localhost:8000/bought-together/SK-00013?top_k=3"
```
```json
{
  "product_id": "SK-00013",
  "source": {"product_id": "SK-00013", "title": "Samsung Galaxy A55 5G (8GB/256GB) Awesome Navy — Official PTA Approved", "…": "…"},
  "count": 3,
  "results": [
    {"product_id": "SK-00014", "title": "Samsung Original 45W Super Fast USB-C Wall Charger Adapter", "brand": "Samsung",
     "category": "Smartphones & Accessories", "price_pkr": 4200.0, "rule_source": "Curated_Accessory_Bundle_FP_Growth",
     "mined_from_data": false, "support": null, "confidence": null, "lift": null,
     "explanation_roman_urdu": "Kyun ke aap ne Samsung Galaxy dekha, yeh covers aur chargers bhi pasand kiye ja rahe hain."},
    "…"
  ],
  "cache_hit": false
}
```

---

## 3. Search & UrduLish Assistant

### `GET /search`
Hybrid search: Okapi BM25 keyword search + multilingual-e5 vector search, fused with Reciprocal Rank Fusion, then a
feature re-ranker and a cross-encoder on the top 50. The Roman Urdu / English parser extracts budget, category,
colour, occasion and brand. With `SEARCH_EMBEDDINGS=lsa` and `SEARCH_CROSS_ENCODER=off` (the lite cloud deploy) the
neural parts are replaced by TF-IDF + SVD vectors and no cross-encoder.

**Parameters:**
- `q` (required): query, e.g. `shaadi ke liye red lehenga 20 hazaar tak`.
- `top_k` (optional, default `10`)
- `user_id` (optional): re-rank for this shopper (`"personalized": true` in the response).

```bash
curl "http://localhost:8000/search?q=shaadi%20ke%20liye%20red%20lehenga%2020%20hazaar%20tak&top_k=3"
```
```json
{
  "query": "shaadi ke liye red lehenga 20 hazaar tak",
  "personalized": false,
  "personalization_method": null,
  "user_id": null,
  "parsed_constraints": {
    "max_price_pkr": 20000.0,
    "min_price_pkr": null,
    "detected_category": "Bridal & Formal Wear",
    "detected_color": "Red",
    "detected_occasion": "Shaadi/Wedding",
    "detected_brand": null
  },
  "count": 3,
  "results": [
    {
      "rank": 1,
      "product_id": "SK-00006",
      "title": "Maria B Crimson Red Bridal Embroidered Lehenga Choli — Shaadi Collection",
      "category": "Bridal & Formal Wear",
      "sub_category": "Bridal Embroidered Lehenga",
      "brand": "Maria B",
      "color": "Crimson Red",
      "occasion": "Shaadi/Wedding",
      "price_pkr": 18500.0,
      "on_sale": true,
      "discount_pct": 10.0,
      "in_stock": true,
      "within_budget": true,
      "score": 3.8941,
      "search_mode": "3. Hybrid Search (BM25 + Semantic + RRF + feature + cross-encoder re-ranker)",
      "avg_rating": 4.29,
      "review_count": 14
    },
    "…"
  ],
  "cache_hit": false
}
```

### `POST /assistant/chat`
UrduLish shopping assistant (Roman Urdu, Urdu script, English). It may only state products, prices and stock that
come from its tools.

```bash
curl -X POST http://localhost:8000/assistant/chat -H "Content-Type: application/json" \
  -d '{"message": "Ammi ke liye Eid gift chahiye, 3000 tak", "session_id": "cust-session-102", "user_id": "USR-928443"}'
```
```json
{
  "session_id": "cust-session-102",
  "user_id": "USR-928443",
  "user_message": "Ammi ke liye Eid gift chahiye, 3000 tak",
  "engine": "llm",
  "fallback_reason": null,
  "detected_intent": "get_recommendations",
  "assistant_response": "Ammi ke liye Eid gift ke taur par ye kuch behtareen options hain jo aapke 3000 ke budget mein hain:\n\n1. **SK-00010** Khaadi Luxury Embroidered Shawl in Ivory White … PKR 2,450 …",
  "tool_calls": ["get_recommendations"],
  "tool_outputs": {
    "get_recommendations": {
      "tool": "get_recommendations",
      "occasion": "Eid",
      "max_budget_pkr": 3000.0,
      "recommendations": [
        {"rank": 1, "product_id": "SK-00010", "title": "Khaadi Luxury Embroidered Shawl in Ivory White — Ammi Eid Gift Edition",
         "brand": "Khaadi", "price_pkr": 2450.0, "on_sale": true, "discount_pct": 15.0, "in_stock": true, "…": "…"},
        "…"
      ]
    },
    "_llm": {"model": "gemini-3.1-flash-lite", "latency_ms": 8540.9, "corrected": false, "prompt_tokens": 3977,
             "output_tokens": 204, "llm_calls": 2}
  },
  "cart": {"item_count": 0, "total_pkr": 0, "items": []},
  "hallucination_audit": {
    "mentioned_product_ids": ["SK-00010", "SK-00011", "SK-00012"],
    "valid_product_ids": ["SK-00010", "SK-00011", "SK-00012"],
    "hallucinated_product_ids": [],
    "mentioned_prices_pkr": [2450.0, 2800.0, 2250.0],
    "hallucinated_prices_pkr": [],
    "mismatched_sku_prices": [],
    "passed_zero_hallucination_check": true
  }
}
```

**How it works.** With `ASSISTANT_ENGINE=auto` (default) and `LLM_API_KEY` set, Gemini decides which of the 6 tools
to call (`search_products`, `get_recommendations`, `compare_products`, `add_to_cart`, `get_order_status`,
`get_review_summary`). The tools run against the real catalogue. Before a reply is returned, every SK-id and PKR
amount in it is checked against the tool results, including that each product is quoted with **its own** price
(`mismatched_sku_prices`); a budget the customer typed is allowed. One failed check gets a correction round; a second
failure, or any LLM error, falls back to a deterministic reply rendered from the tool output.

Fields:
- `engine`: `llm`, `rules` (no key / `ASSISTANT_ENGINE=rules`) or `rules_fallback` (LLM failed this turn)
- `fallback_reason`: why the fallback happened, else `null`
- `tool_outputs._llm`: model, latency, number of LLM calls, tokens, whether a correction was needed
- `cart`: the session's bag after this turn (e.g. after *"Pehla wala cart mein daal do"*:
  `{"item_count": 1, "total_pkr": 2450.0, …}`)

---

## 4. Demand Forecasting & Inventory

### `GET /forecast/{product_id}`
30-day probabilistic forecast (P10 / P50 / P90 per day and in total) with the replenishment decision. Covers the 300
forecast-tracked SKUs.

```bash
curl "http://localhost:8000/forecast/SK-00051"
```
```json
{
  "product_id": "SK-00051",
  "title": "Sapphire Chiffon Dupatta Suit in Maroon — Eid Festive Collection",
  "category": "Women's Lawn & Unstitched",
  "brand": "Sapphire",
  "current_stock_units": 309,
  "forecast_30d_p10_units": 1934.3,
  "forecast_30d_p50_units": 2679.6,
  "forecast_30d_p90_units": 3728.7,
  "safety_stock_units": 104.0,
  "reorder_point_units": 440.0,
  "days_of_inventory": 2.8,
  "alert_status": "CRITICAL_STOCKOUT_RISK",
  "recommended_order_qty": 2475,
  "recommended_action": "URGENT REORDER: Stock (309 units, 2.8d left) is below ROP (440 units, Lead Time=3d). Place PO for 2475 units immediately to prevent stock-out.",
  "horizon_days": 30,
  "daily_forecasts": [
    {"product_id": "SK-00051", "forecast_date": "2025-03-16", "horizon_day": 1, "category": "Women's Lawn & Unstitched",
     "brand": "Sapphire", "p10_units": 77.23, "p50_units": 110.42, "p90_units": 129.87},
    "… 29 more days"
  ],
  "cache_hit": false
}
```

### `GET /inventory/alerts`
Alerts for the 300 forecast-tracked SKUs, most urgent (fewest days of inventory) first, plus `counts_by_status`.
Query params:
- `status`: `CRITICAL_STOCKOUT_RISK`, `FESTIVAL_SURGE_WATCH`, `OVERSTOCK_DEAD_CAPITAL` or `HEALTHY_STOCK`
  (case-insensitive; `422` otherwise)
- `limit`: 1–500, default 50

```bash
curl "http://localhost:8000/inventory/alerts?status=CRITICAL_STOCKOUT_RISK&limit=1"
```
```json
{
  "status_filter": "CRITICAL_STOCKOUT_RISK",
  "counts_by_status": {"CRITICAL_STOCKOUT_RISK": 129, "FESTIVAL_SURGE_WATCH": 94, "OVERSTOCK_DEAD_CAPITAL": 7, "HEALTHY_STOCK": 70},
  "total_tracked_skus": 300,
  "count": 1,
  "alerts": [
    {
      "product_id": "SK-00030",
      "title": "Limelight Luxury 2-Piece Printed Lawn (Ivory White) with Printed Dupatta",
      "category": "Women's Lawn & Unstitched",
      "brand": "Limelight",
      "current_stock_qty": 0,
      "lead_time_days": 7,
      "forecast_14d_p50": 1948.0,
      "forecast_30d_p50": 3292.9,
      "forecast_30d_p90": 4440.4,
      "safety_stock_units": 259,
      "reorder_point_units": 1233,
      "days_of_inventory_p50": 0.0,
      "recommended_order_qty": 3552,
      "alert_status": "CRITICAL_STOCKOUT_RISK",
      "recommended_action": "URGENT REORDER: Stock (0 units, 0.0d left) is below ROP (1233 units, Lead Time=7d). Place PO for 3552 units immediately to prevent stock-out."
    }
  ]
}
```

---

## 5. Review Intelligence

### `GET /reviews/summary/{product_id}`
Genuine review count (spam removed), rating, sentiment, six aspect scores (net score from −1 to +1), the Roman Urdu
"what customers say" line, a courier check (`is_unfairly_penalized_by_courier`: good product, bad delivery) and recent
reviews.

```bash
curl "http://localhost:8000/reviews/summary/SK-00010"
```
```json
{
  "product_id": "SK-00010",
  "title": "Khaadi Luxury Embroidered Shawl in Ivory White — Ammi Eid Gift Edition",
  "brand": "Khaadi",
  "category": "Women's Lawn & Unstitched",
  "genuine_review_count": 16,
  "spam_filtered_count": 0,
  "avg_rating": 4.438,
  "positive_sentiment_pct": 81.25,
  "negative_sentiment_pct": 6.25,
  "avg_delivery_delay_days": -11.312,
  "aspect_scores": {"quality": 0.875, "price": 0.438, "delivery": 0.562, "size_fit": 0.125, "packaging": 0.375, "seller": 0.188},
  "quality_positive_pct": 93.75,
  "delivery_negative_pct": 6.25,
  "is_unfairly_penalized_by_courier": false,
  "recommended_action": "Feature in Top-Rated Campaign",
  "what_customers_say": "Zyada tar customers (94%) ko cheez ki quality pasand aayi. (16 reviews)",
  "recent_reviews": [
    {"product_id": "SK-00010", "review_id": "REV-06010", "language": "Roman_Urdu", "rating": 5,
     "sentiment_label": "Positive", "review_title": "Paisa wasool product",
     "review_text": "Price ke hisaab se Embroidered Shawl ki quality kamaal hai. Packing bhi mehfooz thi aur seller ne bohot acha taawun kiya.",
     "delivery_delay_days": -17},
    "…"
  ],
  "cache_hit": false
}
```

`avg_delivery_delay_days` is delivered date minus promised date (negative = early), from the Olist orders the
reviews are linked to.

---

## Legacy aliases
`/recommend/{user_id}`, `/chat` and `/reviews/{product_id}` still work (hidden from `/docs`) so older scripts and the
Day 5 tests keep running. New code should use the paths above.
