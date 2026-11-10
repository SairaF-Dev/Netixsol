# ShopKaro REST API Endpoints Reference

Base URL: `http://localhost:8000`  
Protocol: HTTP/1.1  
Response Format: JSON  
SLA Guarantee: **p95 Latency < 100 ms** (Cold < 50 ms, Cached < 5 ms)

---

## 1. System Health & Telemetry

### `GET /health`
Returns system status, DuckDB connection health, active catalogue count, and cache uptime.

**Request:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "ShopKaro Commerce Serving API",
  "environment": "production",
  "active_skus": 25000,
  "cache_driver": "HybridTTLCache (L1 Memory + L2 Redis)",
  "uptime_seconds": 1420.5
}
```

### `GET /metrics`
Returns real-time latency percentiles (`mean`, `p50`, `p95`, `p99`), total request counts, and cache hit ratios.

---

## 2. Recommendation Engine Endpoints

### `GET /recommendations/{user_id}`
Generates personalized Top-$K$ product recommendations via the Two-Tower Hybrid model with business re-ranking.

**Parameters:**
- `user_id` (path, required): Integer ID (e.g. `15442`) or persona string (e.g. `PERSONA_LUXURY_VIP`).
- `top_k` (query, optional, default: `10`): Number of recommended items.
- `occasion` (query, optional): Seasonal context (`Eid`, `Shaadi/Wedding`, `11.11 Sale`, `All-Season`).

**Request:**
```bash
curl -X GET "http://localhost:8000/recommendations/15442?top_k=4&occasion=Eid"
```

**Response (200 OK):**
```json
{
  "user_id": 15442,
  "segment_name": "Loyal Electronics & VIP Buyers",
  "occasion": "Eid",
  "count": 4,
  "recommendations": [
    {
      "product_id": "SK-00001",
      "title": "Sapphire 3-Piece Unstitched Embroidered Lawn Suit in Emerald Green",
      "brand": "Sapphire",
      "category": "Women's Lawn & Unstitched",
      "price_pkr": 4450.0,
      "stock_qty": 34,
      "explanation_roman_urdu": "Kyunke aap ko Sapphire aur Eid festive lawn pasand hain."
    }
  ],
  "cache_hit": false
}
```

**How recommendations are produced:** item-to-item CF on the user's history plus live session clicks,
then business re-ranking (stock, already-bought, max 2 per brand, sale/margin/festival boosts). `occasion`
accepts `Eid`, `Ramadan`, `11.11`, `Shaadi`, `Winter`. Each item carries `reason_type`
(`revisit` | `similar_to_history` | `popular_in_category`), `because_of_product_id`, and Roman Urdu + English
explanations. `ranking_strategy` is `item_cf_realtime+business_reranker`, or a `cold_start_*` strategy for unknown
users. Demo users with real history: `USR-928443` (lawn), `USR-368401` (phones), `USR-1398811` (kids & school).

### `POST /events`
Records a live click; the user's next `/recommendations` call reflects it (the cache key includes the user's
event version). Events last for the session (30 minutes).
```bash
curl -X POST http://localhost:8000/events -H "Content-Type: application/json"   -d '{"user_id": "new-visitor-1", "product_id": "SK-00013", "event_type": "view"}'
```
`event_type`: `view` | `addtocart` | `transaction` (`422` otherwise). Unknown product -> `404`.

### `POST /onboarding/{user_id}`
Cold-start onboarding answers. Until the user has clicks, recommendations are popular items in these categories.
```bash
curl -X POST http://localhost:8000/onboarding/new-visitor-1 -H "Content-Type: application/json"   -d '{"categories": ["Kids & School Supplies"]}'
```

### `GET /similar/{product_id}`
Returns the nearest neighbours of a SKU by cosine similarity over its title + description text
embedding (`models/item_text_embeddings.npy`). Text-only (no image embeddings). Works for brand-new
products with no interactions, so it doubles as the new-item cold-start path. In-stock items only;
duplicate titles are collapsed. Query params: `top_k` (1-50, default 10). `404` for unknown SKUs.

```bash
curl "http://localhost:8000/similar/SK-00013?top_k=5"
```
Each result: `product_id, title, brand, category, price_pkr, stock_qty, avg_rating, similarity`.

### `GET /bought-together/{product_id}`
Returns complementary products. Each result has a `rule_source`:
- `Session_Basket_FP_Growth`: pair rule mined from session co-occurrence. `support`, `confidence`, `lift` are measured.
- `Curated_Accessory_Bundle_FP_Growth` / `Cross_Category_Complement_Rule`: hand-written category fallbacks.
  These have **no measured statistics**, so `support/confidence/lift` are `null` and `mined_from_data` is `false`.

Query params: `top_k` (1-20, default 5). `404` for unknown SKUs.

---

## 3. Intelligent Search & UrduLish Assistant

### `GET /search`
Hybrid search combining Okapi BM25 keyword matching, 96-D multilingual subword embeddings, Reciprocal Rank Fusion, and Roman Urdu constraint parsing.

**Parameters:**
- `q` (query, required): Search query string (e.g. `shaadi ke liye red lehenga 20 hazaar tak`).
- `top_k` (query, optional, default: `10`): Number of results.
- `user_id` (query, optional): User ID for personalized re-ranking.

**Request:**
```bash
curl -X GET "http://localhost:8000/search?q=shaadi%20ke%20liye%20red%20lehenga%2020%20hazaar%20tak&top_k=3"
```

**Response (200 OK):**
```json
{
  "query": "shaadi ke liye red lehenga 20 hazaar tak",
  "parsed_constraints": {
    "max_price_pkr": 20000.0,
    "detected_category": "Bridal & Formal Wear",
    "detected_color": "Red",
    "detected_occasion": "Shaadi/Wedding"
  },
  "count": 3,
  "results": [
    {
      "product_id": "SK-00006",
      "title": "Maria B Crimson Red Bridal Embroidered Lehenga Choli",
      "brand": "Maria B",
      "price_pkr": 18500.0,
      "score": 0.892
    }
  ]
}
```

### `POST /assistant/chat`
Conversational shopping assistant supporting Roman Urdu, Urdu script, and English with strict zero-hallucination tool ground truth.

**Request Body:**
```json
{
  "message": "Ammi ke liye Eid gift chahiye, 3000 tak",
  "session_id": "cust-session-102",
  "user_id": 15442
}
```

**Response (200 OK):**
```json
{
  "session_id": "cust-session-102",
  "detected_intent": "search_products",
  "assistant_response": "Ji zaroor! Ammi ke liye 3,000 PKR ke budget mein yeh behtareen Eid gifts hain: Khaadi Embroidered Shawl (2,450 PKR) aur J. Fragrances Oud Gift Set (2,800 PKR).",
  "tool_calls": ["search_products"],
  "cart": {"item_count": 0, "total_pkr": 0.0, "items": []},
  "hallucination_audit": {"passed_zero_hallucination_check": true}
}
```

---


**How it works.** With `ASSISTANT_ENGINE=auto` (default) and `LLM_API_KEY` set, Gemini decides which of the
6 tools to call (`search_products`, `get_recommendations`, `compare_products`, `add_to_cart`,
`get_order_status`, `get_review_summary`). The tools run against the real catalogue. Every SK-id and PKR
amount in the reply is checked against tool results. One failed check gets a correction round. A second
failure, or any LLM error, falls back to a deterministic, grounded reply.

Extra response fields:
- `engine`: `llm`, `rules` (no key / `ASSISTANT_ENGINE=rules`) or `rules_fallback` (LLM failed this turn)
- `fallback_reason`: why the fallback happened, else `null`
- `tool_outputs._llm`: model, latency_ms, llm_calls, prompt/output tokens, whether a correction was needed

Typical LLM latency is 1-15 s per turn (Gemini response time; the tools take milliseconds).

## 4. Supply Chain & Demand Forecasting

### `GET /forecast/{product_id}`
Retrieves 30-day daily probabilistic demand trajectories ($P_{10}, P_{50}, P_{90}$) and dynamic replenishment policies.

**Request:**
```bash
curl -X GET "http://localhost:8000/forecast/SK-00001"
```

**Response (200 OK):**
```json
{
  "product_id": "SK-00001",
  "current_stock_units": 45,
  "safety_stock_units": 28.5,
  "reorder_point_units": 84.0,
  "days_of_inventory": 5.6,
  "alert_status": "CRITICAL_STOCKOUT_RISK",
  "recommended_order_qty": 120,
  "recommended_action": "Issue Immediate Purchase Order (Lead time: 7 days)"
}
```

### `GET /inventory/alerts`
Returns inventory alerts for the 300 forecast-tracked SKUs, most urgent (fewest days of inventory) first,
plus `counts_by_status`. Query params:
- `status`: one of `CRITICAL_STOCKOUT_RISK`, `FESTIVAL_SURGE_WATCH`, `OVERSTOCK_DEAD_CAPITAL`, `HEALTHY_STOCK` (case-insensitive; `422` otherwise)
- `limit`: 1-500, default 50

```bash
curl "http://localhost:8000/inventory/alerts?status=CRITICAL_STOCKOUT_RISK&limit=10"
```

---

## 5. Review Intelligence & Courier Diagnostics

### `GET /reviews/summary/{product_id}`
Returns genuine review totals, spam count, and 6-Aspect ABSA sentiment net scores.

**Request:**
```bash
curl -X GET "http://localhost:8000/reviews/summary/SK-00001"
```

**Response (200 OK):**
```json
{
  "product_id": "SK-00001",
  "avg_rating": 4.62,
  "genuine_review_count": 48,
  "spam_filtered_count": 3,
  "aspect_scores": {
    "quality": 0.94,
    "price": 0.88,
    "delivery": 0.82,
    "size_fit": 0.78,
    "packaging": 0.85,
    "seller": 0.86
  },
  "is_unfairly_penalized_by_courier": false
}
```


---

## Legacy aliases
`/recommend/{user_id}`, `/chat` and `/reviews/{product_id}` still work (hidden from `/docs`) so older
scripts and the Day 5 tests keep running. New code should use the paths above.
