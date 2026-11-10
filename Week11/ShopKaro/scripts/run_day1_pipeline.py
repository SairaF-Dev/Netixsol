"""
Master execution script for Week 11 — Day 1:
Data Foundation, Customer Analytics & Segmentation.

Runs all 5 tasks in order:
- Task 1: DuckDB Ingestion, Bot/Duplicate Cleaning, 30-Min Sessions, Pakistani Mapping
- Task 2: Exploratory Data Analysis (5 Visualizations + 5 Business Insights)
- Task 3: Customer RFM & K-Means Behavioral Segmentation + Marketing Actions
- Task 4: Monthly Cohort Retention Heatmap, Repeat Purchase Rate, CLV & 90-Day Churn
- Task 5: User/Item Feature Engineering (with Text Embeddings) & Time-Based + Cold-Start Splits
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from shopkaro.analytics.cohorts import run_cohort_and_retention_analysis
from shopkaro.analytics.eda import run_exploratory_analysis
from shopkaro.config.settings import settings
from shopkaro.data.pipeline import run_day1_data_pipeline
from shopkaro.data.splits import build_features_and_time_splits
from shopkaro.segmentation.rfm import run_customer_segmentation


def _df_to_markdown(df) -> str:
    """Format a pandas DataFrame as a GitHub-Flavored Markdown table without external dependencies."""
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for _, row in df.iterrows():
        cells = [str(row[c]).replace("|", "\\|") for c in df.columns]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *rows])


def generate_day1_markdown_report(
    pipeline_res,
    eda_res,
    seg_res,
    cohort_res,
    split_res,
    elapsed_sec: float,
) -> Path:
    """Write a comprehensive Day 1 executive and technical report to `reports/`."""
    report_path = settings.reports_dir / "day1_analytics_and_segmentation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    funnel_md = _df_to_markdown(eda_res.funnel_df)
    top_cat_md = _df_to_markdown(eda_res.top_categories_df.head(8))
    top_brand_md = _df_to_markdown(eda_res.top_brands_df.head(10))
    seg_md = _df_to_markdown(
        seg_res.segment_profiles_df[
            [
                "segment_name",
                "user_count",
                "user_share_pct",
                "avg_recency_days",
                "avg_sessions",
                "avg_monetary_pkr",
                "avg_rfm_score",
                "recommended_marketing_action",
            ]
        ]
    )
    cohort_md = _df_to_markdown(cohort_res.retention_matrix.round(2).reset_index())

    content = f"""# ShopKaro — Day 1 Report: Data Foundation, Customer Analytics & Segmentation

**Execution Time:** {elapsed_sec:.1f} seconds  
**DuckDB Database:** `data/processed/shopkaro.duckdb`  
**ER Data Model:** [`docs/architecture/data_model_er.md`](../docs/architecture/data_model_er.md)

---

## 1. Task 1 — Data Pipeline, Cleaning & Sessionization Summary

| Metric | Value | Notes |
| :--- | ---: | :--- |
| **Raw RetailRocket Events** | {pipeline_res.raw_events_count:,} | Original `events.csv` rows |
| **Exact / 1-Sec Duplicates Removed** | {pipeline_res.duplicate_events_removed:,} | Deduplicated on `(visitor_id, item_id, event_type, second)` |
| **Bot & Unmapped Tail Events Filtered** | {pipeline_res.bot_events_removed:,} | Removed sessions with $\\ge 1,000$ clicks & tail items |
| **Clean Active Interactions** | {pipeline_res.clean_events_count:,} | Mapped to Pakistani Catalogue & Festival Calendar |
| **30-Min Inactivity Sessions Built** | {pipeline_res.total_sessions:,} | Globally unique `SES-<visitor>-<seq>` |
| **Unique Active Users (`user_id_map`)** | {pipeline_res.unique_users:,} | Contiguous `user_idx` $0 \\dots N-1$ |
| **Pakistani Catalogue SKUs (`item_id_map`)** | {pipeline_res.catalogue_products:,} | PKR prices, local brands, English + Roman Urdu tags |
| **2-Year Daily Sales Rows (`daily_sales`)** | {pipeline_res.daily_sales_rows:,} | 300 top products $\\times$ 731 days (2024–2025) |
| **Multilingual Reviews (`reviews`)** | {pipeline_res.reviews_rows:,} | English, Roman Urdu (UrduLish) & Urdu + 6 aspects |

---

## 2. Task 2 — Exploratory Data Analysis & One-Line Business Insights

### 2.1 Conversion Funnel (`view` $\\to$ `addtocart` $\\to$ `transaction`)
**One-Line Insight:** *{eda_res.insights["conversion_funnel"]}*

{funnel_md}

![Conversion Funnel](figures/01_conversion_funnel.png)

### 2.2 Top Categories and Brands
**One-Line Insight:** *{eda_res.insights["top_categories_and_brands"]}*

#### Top Categories by Revenue (PKR Millions)
{top_cat_md}

#### Top 10 Brands by Revenue (PKR Millions)
{top_brand_md}

![Top Categories and Brands](figures/02_top_categories_brands.png)

### 2.3 Long-Tail Pareto Analysis
**One-Line Insight:** *{eda_res.insights["long_tail_pareto"]}*

- **SKUs driving 80% of Purchases:** `{eda_res.pct_products_for_80pct_sales:.2f}%`
- **SKUs driving 80% of Views:** `{eda_res.pct_products_for_80pct_views:.2f}%`

![Long-Tail Pareto Curve](figures/03_long_tail_pareto.png)

### 2.4 Temporal & Pakistani Festival Sales Patterns
**One-Line Insight:** *{eda_res.insights["temporal_and_festival_sales"]}*

![Temporal and Festival Sales](figures/04_temporal_and_festival_sales.png)

### 2.5 User–Item Matrix Sparsity
**One-Line Insight:** *{eda_res.insights["user_item_sparsity"]}*

- **Matrix Dimensions:** `{eda_res.n_users:,}` Users $\\times$ `{eda_res.n_items:,}` Items
- **Observed Unique User–Item Pairs:** `{eda_res.n_unique_pairs:,}`
- **Matrix Sparsity:** `{eda_res.user_item_sparsity_pct:.4f}%`

![User-Item Sparsity](figures/05_user_item_sparsity.png)

---

## 3. Task 3 — Customer RFM & Behavioral Segmentation

- **Segmented Users:** `{seg_res.total_segmented_users:,}`
- **Number of Behavioral Clusters (K-Means):** `{seg_res.n_clusters}`
- **Cluster Silhouette Score:** `{seg_res.silhouette_score:.4f}`

{seg_md}

![Customer RFM Segments](figures/06_customer_rfm_segments.png)

---

## 4. Task 4 — Cohort & Retention Analysis

- **Repeat Purchase Rate (among buyers):** `{cohort_res.repeat_purchase_rate_pct:.2f}%`
- **Repeat Multi-Session Rate (all visitors):** `{cohort_res.repeat_session_rate_pct:.2f}%`
- **Average Order Value (AOV):** `PKR {cohort_res.avg_order_value_pkr:,.2f}`
- **Average Purchase Frequency (buyers):** `{cohort_res.avg_purchase_frequency:.2f} orders`
- **Estimated Customer Lifetime Value (CLV):** `PKR {cohort_res.estimated_clv_pkr:,.2f}`
- **Churn Definition:** No activity/purchase within `{cohort_res.churn_threshold_days}` days (`Churn Rate: {cohort_res.churn_rate_pct:.2f}%`)

### Monthly Cohort Retention Matrix (%)
{cohort_md}

![Cohort Retention Heatmap](figures/07_cohort_retention_heatmap.png)

---

## 5. Task 5 — Feature Engineering & Chronological Splits

### Why Never Use a Random Split for Recommendations
A random split mixes future interactions ($t + k$) into the training set while testing on earlier interactions ($t$). This introduces severe **temporal data leakage**:
1. The model already observes a user's future checkout before predicting their earlier browsing session.
2. Seasonal surges (such as Ramadan/Eid lawn trends) leak backwards in time.
3. In production, models are trained on historical logs up to timestamp $T$ and must predict unseen future interactions on $(T, T + \\Delta]$.

### Chronological Split & Cold-Start Summary
| Partition | Event Rows | Cutoff / Details |
| :--- | ---: | :--- |
| **Train Set (70%)** | {split_res.train_rows:,} | Up to `{split_res.train_end_timestamp}` |
| **Validation Set (15%)** | {split_res.val_rows:,} | `{split_res.train_end_timestamp}` $\\to$ `{split_res.val_end_timestamp}` |
| **Test Set (15%)** | {split_res.test_rows:,} | After `{split_res.val_end_timestamp}` |
| **Cold-Start Test Set** | {split_res.cold_start_test_rows:,} | `{split_res.cold_users_in_test:,}` unseen users, `{split_res.cold_items_in_test:,}` unseen items |
| **User Features Table** | {split_res.user_features_count:,} | Segment, AOV, favourite category, conversion rate |
| **Item Features + Text Embeddings** | {split_res.item_features_count:,} | `{split_res.embedding_dim}`-dim dense SVD embeddings saved to `models/item_text_embeddings.npy` |
"""
    report_path.write_text(content, encoding="utf-8")
    return report_path


def main() -> None:
    import sys

    # --rebuild: regenerate everything even if shopkaro.duckdb already exists
    rebuild = "--rebuild" in sys.argv
    t0 = time.perf_counter()
    print(">>> [1/5] Running Day 1 Task 1: DuckDB Ingestion, Cleaning, 30-Min Sessions & Pakistani Mapping...")
    pipeline_res = run_day1_data_pipeline(reuse_if_exists=not rebuild)
    print("    Task 1 Done:", json.dumps(pipeline_res.to_dict(), indent=2))

    print("\n>>> [2/5] Running Day 1 Task 2: Exploratory Data Analysis & Visualizations...")
    eda_res = run_exploratory_analysis()
    print("    Task 2 Done. Figures generated:", len(eda_res.figure_paths))

    print("\n>>> [3/5] Running Day 1 Task 3: Customer RFM & K-Means Segmentation...")
    seg_res = run_customer_segmentation()
    print("    Task 3 Done. Silhouette Score:", seg_res.silhouette_score)

    print("\n>>> [4/5] Running Day 1 Task 4: Cohort Retention, Repeat Rate, CLV & Churn...")
    cohort_res = run_cohort_and_retention_analysis()
    print("    Task 4 Done:", json.dumps(cohort_res.to_dict(), indent=2))

    print("\n>>> [5/5] Running Day 1 Task 5: User/Item Features & Chronological + Cold-Start Splits...")
    split_res = build_features_and_time_splits()
    print("    Task 5 Done:", json.dumps(split_res.to_dict(), indent=2))

    elapsed = time.perf_counter() - t0
    report_file = generate_day1_markdown_report(
        pipeline_res, eda_res, seg_res, cohort_res, split_res, elapsed
    )
    print(f"\n>>> Day 1 Complete in {elapsed:.1f}s! Report written to: {report_file}")


if __name__ == "__main__":
    main()
