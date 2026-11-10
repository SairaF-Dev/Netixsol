# ShopKaro — Data Dictionary & Schema Reference

This data dictionary documents every table created in `data/processed/shopkaro.duckdb`, `data/processed/*.parquet`, and `data/synthetic/*.parquet`.

---

## 1. Core Catalogue & Calendar Tables (`data/synthetic/`)

### 1.1 `product_catalogue` (`product_catalogue.parquet`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `product_id` | `VARCHAR` | Primary Key (`SK-00001` to `SK-25000`). |
| `raw_itemid` | `BIGINT` | Mapped RetailRocket `itemid` for interaction join. |
| `olist_product_id` | `VARCHAR` | Mapped Olist `product_id` for fulfillment/review reference. |
| `title` | `VARCHAR` | Product title in English + Roman Urdu context. |
| `description` | `VARCHAR` | Detailed description including UrduLish search keywords. |
| `category` | `VARCHAR` | 11 Pakistani categories (e.g., `Women's Lawn & Unstitched`, `Smartphones & Accessories`). |
| `sub_category` | `VARCHAR` | Specific product type (e.g., `3-Piece Lawn Suit`, `Waterproof Ergonomic School Bag`). |
| `brand` | `VARCHAR` | Brand name (e.g., `Khaadi`, `Sapphire`, `Gul Ahmed`, `Samsung`, `Lenovo`, `Bata`). |
| `color` | `VARCHAR` | Dominant product color. |
| `occasion` | `VARCHAR` | Target occasion (`Eid`, `Shaadi/Wedding`, `School/Office`, `Winter`, `Summer`). |
| `price_pkr` | `DOUBLE` | Retail price in Pakistani Rupees (PKR). |
| `price_band` | `VARCHAR` | `Budget (<2k PKR)`, `Mid-Range (2k-5k PKR)`, `Premium (5k-25k PKR)`, `Luxury (>25k PKR)`. |
| `on_sale` | `BOOLEAN` | True if currently discounted. |
| `discount_pct` | `DOUBLE` | Discount percentage (`0.0` to `25.0`). |
| `margin_pct` | `DOUBLE` | Gross margin ratio (`0.10` to `0.60`). |
| `stock_qty` | `INTEGER` | Available warehouse units (`0` if out of stock). |
| `in_stock` | `BOOLEAN` | `True` when `stock_qty > 0`. |
| `lead_time_days` | `INTEGER` | Supplier replenishment lead time in days (`3` to `12`). |
| `is_synthetic` | `BOOLEAN` | Provenance marker (`True`). |

### 1.2 `festival_calendar` (`festival_calendar.parquet`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `festival_id` | `INTEGER` | Sequential festival identifier (`1..17`). |
| `festival_name` | `VARCHAR` | Name (`Ramadan`, `Chaand Raat & Eid ul Fitr`, `Eid ul Adha`, `11.11 Mega Sale`, etc.). |
| `festival_type` | `VARCHAR` | `Islamic_Moving`, `Commercial_Fixed`, `National_Fixed`, `Seasonal_Fixed`. |
| `start_date` | `DATE` | Start date of promotional/festival window. |
| `end_date` | `DATE` | End date of promotional/festival window. |
| `boost_categories` | `VARCHAR` | Categories experiencing major demand surges. |
| `demand_multiplier` | `DOUBLE` | Demand uplift factor (`2.0x` to `4.5x`). |

---

## 2. Behavioral Interaction & Session Tables (`data/processed/`)

### 2.1 `interactions_clean` (`interactions_clean.parquet`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `session_id` | `VARCHAR` | 30-minute inactivity session identifier (`SES-<visitor>-<seq>`). |
| `user_id` | `VARCHAR` | Standardized customer ID (`USR-<visitor_id>`). |
| `visitor_id` | `BIGINT` | Original RetailRocket `visitorid`. |
| `product_id` | `VARCHAR` | Foreign key to `product_catalogue.product_id`. |
| `event_type` | `VARCHAR` | `view`, `addtocart`, or `transaction`. |
| `implicit_weight` | `DOUBLE` | Confidence weight (`view=1.0`, `addtocart=3.0`, `transaction=6.0`). |
| `event_timestamp` | `TIMESTAMP` | Cleaned event timestamp aligned to 2025 calendar. |
| `event_date` | `DATE` | Event calendar date. |
| `day_of_week` | `INTEGER` | Day of week (`0=Sunday` .. `6=Saturday`). |
| `hour_of_day` | `INTEGER` | Hour of day (`0..23`). |
| `price_pkr` | `DOUBLE` | Item price in PKR. |
| `festival_name` | `VARCHAR` | Active festival on `event_date` or `Regular_Day`. |
| `is_festival_period` | `BOOLEAN` | True if event occurred during a Pakistani festival. |

### 2.2 `customer_segments` (`customer_segments.parquet`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `user_id` | `VARCHAR` | Customer identifier (`USR-<visitor_id>`). |
| `recency_days` | `INTEGER` | Days elapsed since customer's most recent interaction. |
| `frequency_sessions` | `INTEGER` | Total distinct 30-minute sessions. |
| `monetary_intent_pkr` | `DOUBLE` | Realized and intent-weighted value in PKR. |
| `r_score`, `f_score`, `m_score` | `INTEGER` | Quintile scores (`1` lowest to `5` highest). |
| `cluster_id` | `INTEGER` | K-Means behavioral cluster index (`0..4`). |
| `segment_name` | `VARCHAR` | Assigned persona (e.g., `Eid & Festive Lawn Shoppers`, `Loyal Electronics & VIP Buyers`). |
| `recommended_marketing_action` | `VARCHAR` | Actionable retention or upsell campaign rule. |

---

## 3. Forecasting & Review Intelligence Tables (`data/synthetic/`)

### 3.1 `daily_sales` (`daily_sales.parquet`)
- **Granularity:** Daily (`sale_date` $\times$ `product_id`) across 731 days (`2024-01-01` to `2025-12-31`) for the top 300 products (`219,300` rows).
- **Columns:** `sale_date`, `product_id`, `category`, `brand`, `velocity_tier` (`Fast_Mover`, `Steady_Mover`, `Slow_Intermittent`), `units_sold`, `unit_price_pkr`, `revenue_pkr`, `festival_name`, `is_festival_day`.

### 3.2 `reviews` (`reviews.parquet`)
- **Granularity:** 8,000 customer reviews mapped to Olist order delivery timelines and ShopKaro products.
- **Columns:** `review_id`, `order_id`, `product_id`, `seller_id`, `rating` (1–5), `sentiment_label`, `language` (`Roman_Urdu`, `English`, `Urdu`), `review_title`, `review_text`, `delivery_delay_days`, `aspect_quality`, `aspect_price`, `aspect_delivery`, `aspect_size_fit`, `aspect_packaging`, `aspect_seller`, `is_fake_spam`, `spam_reason`.



---

## `product_catalogue` (added columns, 2026-11-09)
| Column | Type | Description |
|---|---|---|
| `rr_categoryid` | INTEGER (nullable) | Latest RetailRocket `categoryid` of the source item (from `item_properties`). |
| `category_source` | VARCHAR | How `category` was chosen: `retailrocket_tree`, `session_neighbours` (item had no RetailRocket category; majority category of co-browsed items), `fallback_deficit`, or `curated_hero`. |

## `category_mapping`
One row per RetailRocket level-1 category group (child of a root category) and the Pakistani category it maps to.
Built by `src/shopkaro/data/category_mapping.py` in the Day 1 pipeline.

| Column | Type | Description |
|---|---|---|
| `rr_group_id` | INTEGER | RetailRocket level-1 category id. |
| `category` | VARCHAR | ShopKaro (Pakistani) category assigned to every item in this group. |
| `items` | BIGINT | Catalogue items in the group. |
| `rr_leaf_categories` | BIGINT | Distinct RetailRocket leaf categories in the group. |
