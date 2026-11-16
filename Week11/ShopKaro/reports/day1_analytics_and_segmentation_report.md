# ShopKaro — Day 1 Report: Data Foundation, Customer Analytics & Segmentation

**Execution Time:** 43.9 seconds  
**DuckDB Database:** `data/processed/shopkaro.duckdb`  
**ER Data Model:** [`docs/architecture/data_model_er.md`](../docs/architecture/data_model_er.md)

---

## 1. Task 1 — Data Pipeline, Cleaning & Sessionization Summary

| Metric | Value | Notes |
| :--- | ---: | :--- |
| **Raw RetailRocket Events** | 2,756,101 | Original `events.csv` rows |
| **Exact / 1-Sec Duplicates Removed** | 4,034 | Deduplicated on `(visitor_id, item_id, event_type, second)` |
| **Bot & Unmapped Tail Events Filtered** | 758,712 | Removed sessions with $\ge 1,000$ clicks & tail items |
| **Clean Active Interactions** | 1,993,355 | Mapped to Pakistani Catalogue & Festival Calendar |
| **30-Min Inactivity Sessions Built** | 1,066,507 | Globally unique `SES-<visitor>-<seq>` |
| **Unique Active Users (`user_id_map`)** | 849,398 | Contiguous `user_idx` $0 \dots N-1$ |
| **Pakistani Catalogue SKUs (`item_id_map`)** | 25,000 | PKR prices, local brands, English + Roman Urdu tags |
| **2-Year Daily Sales Rows (`daily_sales`)** | 219,300 | 300 top products $\times$ 731 days (2024–2025) |
| **Multilingual Reviews (`reviews`)** | 8,000 | English, Roman Urdu (UrduLish) & Urdu + 6 aspects |

---

## 2. Task 2 — Exploratory Data Analysis & One-Line Business Insights

### 2.1 Conversion Funnel (`view` $\to$ `addtocart` $\to$ `transaction`)
**One-Line Insight:** *Only 3.62% of product views convert to cart additions and 1.35% to final purchases (37.2% cart-to-buy completion), highlighting massive opportunity for personalized homepage recommendations and cart-recovery nudges.*

| event_type | event_count | unique_users | unique_sessions | pct_of_views |
| --- | --- | --- | --- | --- |
| view | 1898978 | 845981 | 1060672 | 100.0 |
| addtocart | 68765 | 34900 | 40651 | 3.62 |
| transaction | 25612 | 11719 | 14297 | 1.35 |

![Conversion Funnel](figures/01_conversion_funnel.png)

### 2.2 Top Categories and Brands
**One-Line Insight:** *'Smartphones & Accessories' and 'Samsung' lead gross merchandise value (GMV), indicating that high-AOV electronics and festive Pakistani lawn wear anchor marketplace revenue.*

#### Top Categories by Revenue (PKR Millions)
| category | total_events | purchases | revenue_million_pkr |
| --- | --- | --- | --- |
| Smartphones & Accessories | 326974 | 3783.0 | 88.9 |
| Laptops & Computing | 65626 | 762.0 | 74.37 |
| Bridal & Formal Wear | 123170 | 1572.0 | 49.88 |
| Women's Lawn & Unstitched | 534745 | 7059.0 | 45.95 |
| Home & Kitchen Appliances | 114520 | 1392.0 | 27.25 |
| Men's Kurta & Ethnic | 220135 | 2510.0 | 15.87 |
| Footwear & Khussa | 140786 | 2802.0 | 12.91 |
| Beauty & Fragrances | 176568 | 2319.0 | 7.35 |

#### Top 10 Brands by Revenue (PKR Millions)
| brand | category | total_events | purchases | revenue_million_pkr |
| --- | --- | --- | --- | --- |
| Samsung | Smartphones & Accessories | 45866 | 686.0 | 25.31 |
| HP | Laptops & Computing | 15751 | 176.0 | 17.23 |
| Lenovo | Laptops & Computing | 7899 | 91.0 | 14.61 |
| Asus | Laptops & Computing | 11662 | 158.0 | 14.26 |
| Dell | Laptops & Computing | 15153 | 168.0 | 14.03 |
| Acer | Laptops & Computing | 7644 | 86.0 | 13.59 |
| Realme | Smartphones & Accessories | 22880 | 250.0 | 11.73 |
| Infinix | Smartphones & Accessories | 11087 | 134.0 | 11.08 |
| Xiaomi Redmi | Smartphones & Accessories | 24943 | 235.0 | 11.0 |
| Vivo | Smartphones & Accessories | 9617 | 126.0 | 10.63 |

![Top Categories and Brands](figures/02_top_categories_brands.png)

### 2.3 Long-Tail Pareto Analysis
**One-Line Insight:** *Just 27.6% of catalogue SKUs generate 80% of all purchases (and 49.6% generate 80% of views), proving severe catalog concentration that requires long-tail discovery and diversity re-ranking.*

- **SKUs driving 80% of Purchases:** `27.61%`
- **SKUs driving 80% of Views:** `49.58%`

![Long-Tail Pareto Curve](figures/03_long_tail_pareto.png)

### 2.4 Temporal & Pakistani Festival Sales Patterns
**One-Line Insight:** *Daily revenue surges by 2.61x during 'Chaand Raat & Eid ul Fitr' compared to regular days, with peak shopping activity occurring between 18:00 and 22:00 and on weekends.*

![Temporal and Festival Sales](figures/04_temporal_and_festival_sales.png)

### 2.5 User–Item Matrix Sparsity
**One-Line Insight:** *The user–item matrix is 99.9940% sparse (1,278,690 observed pairs across 849,398 users and 25,000 items), making matrix factorization (ALS/BPR) combined with content embeddings essential for cold-start resilience.*

- **Matrix Dimensions:** `849,398` Users $\times$ `25,000` Items
- **Observed Unique User–Item Pairs:** `1,278,690`
- **Matrix Sparsity:** `99.9940%`

![User-Item Sparsity](figures/05_user_item_sparsity.png)

---

## 3. Task 3 — Customer RFM & Behavioral Segmentation

- **Segmented Users:** `60,000`
- **Number of Behavioral Clusters (K-Means):** `5`
- **Cluster Silhouette Score:** `0.2582`

| segment_name | user_count | user_share_pct | avg_recency_days | avg_sessions | avg_monetary_pkr | avg_rfm_score | recommended_marketing_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bargain Hunters & Cart Hesitators | 6632 | 11.05 | 41.67 | 12.07 | 42496.01 | 12.73 | Trigger automated 2-hour abandoned-cart 10% flash discount codes and highlight 'Under 3,000 PKR' deals. |
| Loyal Electronics & VIP Buyers | 11970 | 19.95 | 82.05 | 2.11 | 18146.61 | 9.16 | Grant early VIP access to 11.11 Mega Sales, zero-markup installment plans, and bundled accessory cross-sells. |
| Eid & Festive Lawn Shoppers | 15604 | 26.01 | 102.29 | 1.85 | 5390.86 | 7.44 | Send WhatsApp & push lookbooks 15 days before Ramadan and Eid with 'Complete the Eid Look' dupatta/khussa bundles. |
| At-Risk & Dormant Browsers | 8350 | 13.92 | 66.42 | 1.76 | 5237.35 | 8.42 | Launch a 'We Miss You' win-back campaign with Rs. 500 voucher on their historical favourite category. |
| Active Multi-Category Families | 17444 | 29.07 | 47.74 | 1.73 | 4260.03 | 9.14 | Enroll in ShopKaro Family Loyalty Points with free delivery thresholds on monthly rashan and back-to-school kits. |

![Customer RFM Segments](figures/06_customer_rfm_segments.png)

---

## 4. Task 4 — Cohort & Retention Analysis

- **Repeat Purchase Rate (among buyers):** `29.96%`
- **Repeat Multi-Session Rate (all visitors):** `12.48%`
- **Average Order Value (AOV):** `PKR 12,568.93`
- **Average Purchase Frequency (buyers):** `2.19 orders`
- **Estimated Customer Lifetime Value (CLV):** `PKR 81,845.95`
- **Churn Definition:** No activity/purchase within `90` days (`Churn Rate: 33.56%`)

### Monthly Cohort Retention Matrix (%)
| cohort_month | Month +0 | Month +1 | Month +2 | Month +3 | Month +4 |
| --- | --- | --- | --- | --- | --- |
| 2025-03 | 100.0 | 4.01 | 2.15 | 1.4 | 0.73 |
| 2025-04 | 100.0 | 3.56 | 1.51 | 0.69 | 0.0 |
| 2025-05 | 100.0 | 2.66 | 0.83 | 0.0 | 0.0 |
| 2025-06 | 100.0 | 2.13 | 0.0 | 0.0 | 0.0 |
| 2025-07 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 |

![Cohort Retention Heatmap](figures/07_cohort_retention_heatmap.png)

---

## 5. Task 5 — Feature Engineering & Chronological Splits

### Why Never Use a Random Split for Recommendations
A random split mixes future interactions ($t + k$) into the training set while testing on earlier interactions ($t$). This introduces severe **temporal data leakage**:
1. The model already observes a user's future checkout before predicting their earlier browsing session.
2. Seasonal surges (such as Ramadan/Eid lawn trends) leak backwards in time.
3. In production, models are trained on historical logs up to timestamp $T$ and must predict unseen future interactions on $(T, T + \Delta]$.

### Chronological Split & Cold-Start Summary
| Partition | Event Rows | Cutoff / Details |
| :--- | ---: | :--- |
| **Train Set (70%)** | 1,395,348 | Up to `2025-05-25 16:58:28.6958` |
| **Validation Set (15%)** | 299,003 | `2025-05-25 16:58:28.6958` $\to$ `2025-06-19 23:10:23.5101` |
| **Test Set (15%)** | 299,004 | After `2025-06-19 23:10:23.5101` |
| **Cold-Start Test Set** | 278,031 | `155,661` unseen users, `585` unseen items |
| **User Features Table** | 549,150 | Segment, AOV, favourite category, conversion rate |
| **Item Features + Text Embeddings** | 25,000 | `64`-dim dense SVD embeddings saved to `models/item_text_embeddings.npy` |
