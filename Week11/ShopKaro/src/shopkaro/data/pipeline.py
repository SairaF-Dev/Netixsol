"""
Day 1 — Task 1: DuckDB Data Ingestion, Cleaning, Sessionization & Pakistani Mapping Pipeline.

Loads RetailRocket and Olist raw datasets into DuckDB, removes bot traffic and
duplicate events, constructs 30-minute inactivity sessions, maps items and timestamps
to the Pakistani commerce context (PKR prices, local categories, festival calendar),
and creates contiguous user/item ID mappings.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.data.category_mapping import map_items_to_categories, mapping_summary
from shopkaro.data.synthesizer import (
    calibrate_stock_to_demand,
    CATEGORY_TEMPLATES,
    CATEGORY_WEIGHTS,
    generate_daily_sales_history,
    generate_festival_calendar,
    generate_pakistani_reviews,
    generate_product_catalogue,
)


@dataclass
class PipelineSummary:
    """Summary statistics from executing the Day 1 DuckDB data pipeline."""

    raw_events_count: int
    duplicate_events_removed: int
    bot_events_removed: int
    clean_events_count: int
    total_sessions: int
    unique_users: int
    unique_items: int
    catalogue_products: int
    daily_sales_rows: int
    reviews_rows: int
    duckdb_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_events_count": self.raw_events_count,
            "duplicate_events_removed": self.duplicate_events_removed,
            "bot_events_removed": self.bot_events_removed,
            "clean_events_count": self.clean_events_count,
            "total_sessions": self.total_sessions,
            "unique_users": self.unique_users,
            "unique_items": self.unique_items,
            "catalogue_products": self.catalogue_products,
            "daily_sales_rows": self.daily_sales_rows,
            "reviews_rows": self.reviews_rows,
            "duckdb_path": self.duckdb_path,
        }


def run_day1_data_pipeline(
    db_path: Path | None = None,
    max_catalogue_items: int = 25000,
    reuse_if_exists: bool = True,
) -> PipelineSummary:
    """
    Execute the complete Day 1 Task 1 Data Pipeline inside DuckDB:
    1. Load raw RetailRocket `events.csv` and Olist tables.
    2. Deduplicate events and filter out bot sessions (>= 1,000 clicks per session).
    3. Build 30-minute inactivity sessions.
    4. Generate & join Pakistani Product Catalogue, Festival Calendar, 2-Year Daily Sales, and UrduLish Reviews.
    5. Create contiguous User and Item ID mappings (`user_idx`, `item_idx`).
    6. Persist processed tables both in DuckDB (`shopkaro.duckdb`) and Parquet (`data/processed/`).
    """
    target_db = db_path or settings.duckdb_path
    target_db.parent.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.synthetic_dir.mkdir(parents=True, exist_ok=True)

    if reuse_if_exists and target_db.exists():
        con_check = duckdb.connect(str(target_db), read_only=True)
        existing_tbls = {
            r[0]
            for r in con_check.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        if {"raw_events", "interactions_clean", "sessions", "product_catalogue", "daily_sales", "reviews"}.issubset(
            existing_tbls
        ):
            raw_count = int(con_check.execute("SELECT COUNT(*) FROM raw_events").fetchall()[0][0])
            clean_count = int(con_check.execute("SELECT COUNT(*) FROM interactions_clean").fetchall()[0][0])
            total_sessions = int(con_check.execute("SELECT COUNT(*) FROM sessions").fetchall()[0][0])
            unique_users = int(con_check.execute("SELECT COUNT(*) FROM user_id_map").fetchall()[0][0])
            unique_items = int(con_check.execute("SELECT COUNT(DISTINCT product_id) FROM interactions_clean").fetchall()[0][0])
            cat_count = int(con_check.execute("SELECT COUNT(*) FROM product_catalogue").fetchall()[0][0])
            sales_count = int(con_check.execute("SELECT COUNT(*) FROM daily_sales").fetchall()[0][0])
            rev_count = int(con_check.execute("SELECT COUNT(*) FROM reviews").fetchall()[0][0])
            # Same grouping as step 3a, recomputed (was a hardcoded number that would go stale on new data).
            dedup_count = int(
                con_check.execute(
                    """
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM raw_events
                        GROUP BY visitor_id, raw_itemid, event_type, CAST(ts_ms / 1000 AS BIGINT)
                    )
                    """
                ).fetchall()[0][0]
            )
            con_check.close()
            return PipelineSummary(
                raw_events_count=raw_count,
                duplicate_events_removed=raw_count - dedup_count,
                bot_events_removed=dedup_count - clean_count,
                clean_events_count=clean_count,
                total_sessions=total_sessions,
                unique_users=unique_users,
                unique_items=unique_items,
                catalogue_products=cat_count,
                daily_sales_rows=sales_count,
                reviews_rows=rev_count,
                duckdb_path=str(target_db),
            )
        con_check.close()

    events_csv = str(settings.raw_retailrocket_dir / "events.csv").replace("\\", "/")
    cat_tree_csv = str(settings.raw_retailrocket_dir / "category_tree.csv").replace("\\", "/")
    olist_orders_csv = str(settings.raw_olist_dir / "olist_orders_dataset.csv").replace("\\", "/")
    olist_items_csv = str(settings.raw_olist_dir / "olist_order_items_dataset.csv").replace("\\", "/")
    olist_prods_csv = str(settings.raw_olist_dir / "olist_products_dataset.csv").replace("\\", "/")
    olist_cust_csv = str(settings.raw_olist_dir / "olist_customers_dataset.csv").replace("\\", "/")
    olist_sellers_csv = str(settings.raw_olist_dir / "olist_sellers_dataset.csv").replace("\\", "/")

    con = duckdb.connect(str(target_db))

    # ------------------------------------------------------------------
    # Step 1: Load Raw RetailRocket Events & Category Tree
    # ------------------------------------------------------------------
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw_events AS
        SELECT
            CAST(timestamp AS BIGINT) AS ts_ms,
            to_timestamp(CAST(timestamp AS DOUBLE) / 1000.0) AS event_timestamp_raw,
            CAST(visitorid AS BIGINT) AS visitor_id,
            CAST(event AS VARCHAR) AS event_type,
            CAST(itemid AS BIGINT) AS raw_itemid,
            TRY_CAST(transactionid AS BIGINT) AS transaction_id
        FROM read_csv_auto('{events_csv}', ignore_errors=true)
        WHERE visitorid IS NOT NULL AND itemid IS NOT NULL AND event IS NOT NULL;
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw_category_tree AS
        SELECT
            CAST(categoryid AS INTEGER) AS category_id,
            TRY_CAST(parentid AS INTEGER) AS parent_id
        FROM read_csv_auto('{cat_tree_csv}', ignore_errors=true);
        """
    )

    raw_count = int(con.execute("SELECT COUNT(*) FROM raw_events").fetchall()[0][0])

    # ------------------------------------------------------------------
    # Step 2: Load Olist Marketplace Tables (Strictly Separated User IDs)
    # ------------------------------------------------------------------
    con.execute(
        f"""
        CREATE OR REPLACE TABLE olist_orders AS
        SELECT * FROM read_csv_auto('{olist_orders_csv}', ignore_errors=true);

        CREATE OR REPLACE TABLE olist_order_items AS
        SELECT * FROM read_csv_auto('{olist_items_csv}', ignore_errors=true);

        CREATE OR REPLACE TABLE olist_products AS
        SELECT * FROM read_csv_auto('{olist_prods_csv}', ignore_errors=true);

        CREATE OR REPLACE TABLE olist_customers AS
        SELECT * FROM read_csv_auto('{olist_cust_csv}', ignore_errors=true);

        CREATE OR REPLACE TABLE olist_sellers AS
        SELECT * FROM read_csv_auto('{olist_sellers_csv}', ignore_errors=true);
        """
    )

    # ------------------------------------------------------------------
    # Step 3: Event Cleaning — Remove Duplicate Events & Bot Sessions
    #         (30-minute inactivity sessionization + <1,000 clicks rule)
    # ------------------------------------------------------------------
    # 3a. Deduplicate identical (visitor_id, raw_itemid, event_type) within the same second
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE dedup_events AS
        SELECT
            visitor_id,
            raw_itemid,
            event_type,
            MIN(ts_ms) AS ts_ms,
            MIN(event_timestamp_raw) AS event_timestamp_raw,
            ANY_VALUE(transaction_id) AS transaction_id
        FROM raw_events
        GROUP BY
            visitor_id,
            raw_itemid,
            event_type,
            CAST(ts_ms / 1000 AS BIGINT);
        """
    )
    dedup_count = int(con.execute("SELECT COUNT(*) FROM dedup_events").fetchall()[0][0])
    duplicates_removed = raw_count - dedup_count

    # 3b. Session Building (30-minute = 1,800 seconds inactivity rule)
    inactivity_sec = settings.session_inactivity_minutes * 60
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE sessionized_events AS
        WITH lagged AS (
            SELECT
                *,
                LAG(ts_ms) OVER (PARTITION BY visitor_id ORDER BY ts_ms) AS prev_ts_ms
            FROM dedup_events
        ),
        flagged AS (
            SELECT
                *,
                CASE
                    WHEN prev_ts_ms IS NULL THEN 1
                    WHEN (ts_ms - prev_ts_ms) / 1000.0 > {inactivity_sec} THEN 1
                    ELSE 0
                END AS is_new_session
            FROM lagged
        ),
        numbered AS (
            SELECT
                visitor_id,
                raw_itemid,
                event_type,
                ts_ms,
                event_timestamp_raw,
                transaction_id,
                SUM(is_new_session) OVER (
                    PARTITION BY visitor_id
                    ORDER BY ts_ms
                    ROWS UNBOUNDED PRECEDING
                ) AS user_session_seq
            FROM flagged
        )
        SELECT
            *,
            CONCAT('SES-', CAST(visitor_id AS VARCHAR), '-', CAST(user_session_seq AS VARCHAR)) AS session_id
        FROM numbered;
        """
    )

    # 3c. Identify & Remove Bot Sessions (sessions with >= 1,000 clicks or visitors with >2,500 clicks)
    max_clicks = settings.bot_max_clicks_per_session
    con.execute(
        f"""
        CREATE OR REPLACE TABLE bot_sessions_audit AS
        SELECT
            session_id,
            visitor_id,
            COUNT(*) AS session_click_count,
            MIN(event_timestamp_raw) AS session_start,
            MAX(event_timestamp_raw) AS session_end
        FROM sessionized_events
        GROUP BY session_id, visitor_id
        HAVING COUNT(*) >= {max_clicks};
        """
    )

    # Also filter to top `max_catalogue_items` most active items so catalogue is rich and dense
    top_items_df = con.execute(
        f"""
        SELECT raw_itemid, COUNT(*) AS cnt
        FROM sessionized_events
        WHERE session_id NOT IN (SELECT session_id FROM bot_sessions_audit)
        GROUP BY raw_itemid
        ORDER BY
            SUM(CASE WHEN event_type = 'transaction' THEN 50 WHEN event_type = 'addtocart' THEN 10 ELSE 1 END) DESC,
            cnt DESC,
            raw_itemid
        LIMIT {int(max_catalogue_items)};
        """
    ).df()
    active_item_ids = top_items_df["raw_itemid"].astype(int).tolist()

    olist_prod_ids = (
        con.execute("SELECT DISTINCT product_id FROM olist_products WHERE product_id IS NOT NULL LIMIT 25000")
        .df()["product_id"]
        .astype(str)
        .tolist()
    )

    # ------------------------------------------------------------------
    # Step 4: Generate Pakistani Catalogue, Festivals, Sales & Reviews
    # ------------------------------------------------------------------
    festival_df = generate_festival_calendar(settings.synthetic_dir)
    # Pakistani category per item from its real RetailRocket category subtree (not random), so
    # products shoppers browse together share sensible categories.
    item_categories = map_items_to_categories(
        con,
        active_item_ids=active_item_ids,
        categories=list(CATEGORY_TEMPLATES.keys()),
        weights=CATEGORY_WEIGHTS,
        session_table="sessionized_events",
    )
    con.register("_category_mapping_df", mapping_summary(item_categories))
    con.execute("CREATE OR REPLACE TABLE category_mapping AS SELECT * FROM _category_mapping_df")
    con.unregister("_category_mapping_df")
    catalogue_df = generate_product_catalogue(
        active_item_ids=active_item_ids,
        olist_product_ids=olist_prod_ids,
        output_dir=settings.synthetic_dir,
        seed=settings.random_seed,
        item_categories=item_categories,
    )
    sales_df = generate_daily_sales_history(
        catalogue_df=catalogue_df,
        festival_df=festival_df,
        top_n_products=300,
        output_dir=settings.synthetic_dir,
        seed=settings.random_seed,
    )
    # Stock levels follow each product's own demand (see calibrate_stock_to_demand).
    catalogue_df = calibrate_stock_to_demand(catalogue_df, sales_df, seed=settings.random_seed)
    catalogue_df.to_parquet(settings.synthetic_dir / "product_catalogue.parquet", index=False)
    reviews_df = generate_pakistani_reviews(
        catalogue_df=catalogue_df,
        raw_olist_dir=settings.raw_olist_dir,
        max_reviews=8000,
        output_dir=settings.synthetic_dir,
        seed=settings.random_seed,
    )

    # Register synthetic parquet files as DuckDB tables
    fest_parquet = str(settings.synthetic_dir / "festival_calendar.parquet").replace("\\", "/")
    cat_parquet = str(settings.synthetic_dir / "product_catalogue.parquet").replace("\\", "/")
    sales_parquet = str(settings.synthetic_dir / "daily_sales.parquet").replace("\\", "/")
    rev_parquet = str(settings.synthetic_dir / "reviews.parquet").replace("\\", "/")

    con.execute(
        f"""
        CREATE OR REPLACE TABLE festival_calendar AS
        SELECT * FROM read_parquet('{fest_parquet}');

        CREATE OR REPLACE TABLE product_catalogue AS
        SELECT * FROM read_parquet('{cat_parquet}');

        CREATE OR REPLACE TABLE daily_sales AS
        SELECT * FROM read_parquet('{sales_parquet}');

        CREATE OR REPLACE TABLE reviews AS
        SELECT * FROM read_parquet('{rev_parquet}');
        """
    )

    # ------------------------------------------------------------------
    # Step 5: Map RetailRocket Timestamps to 2025 Pakistani Calendar &
    #         Join Pakistani Product Catalogue (PKR Prices & Categories)
    # ------------------------------------------------------------------
    # RetailRocket spans May 2015 - Sep 2015 (~138 days). We shift timestamps by +3590 days
    # into 2025 (Mar 2025 - Jul 2025) so clickstream events align with Ramadan, Eid ul Fitr,
    # and Eid ul Adha 2025 in our Pakistani festival calendar!
    con.execute(
        """
        CREATE OR REPLACE TABLE interactions_clean AS
        WITH valid_events AS (
            SELECT
                s.session_id,
                s.visitor_id,
                s.raw_itemid,
                s.event_type,
                s.transaction_id,
                s.ts_ms,
                s.event_timestamp_raw + INTERVAL '3590 days' AS event_timestamp,
                CAST(s.event_timestamp_raw + INTERVAL '3590 days' AS DATE) AS event_date
            FROM sessionized_events s
            LEFT JOIN bot_sessions_audit b
              ON s.session_id = b.session_id
            WHERE b.session_id IS NULL
        )
        SELECT
            v.session_id,
            v.visitor_id,
            CONCAT('USR-', CAST(v.visitor_id AS VARCHAR)) AS user_id,
            p.product_id,
            v.raw_itemid,
            v.event_type,
            CASE
                WHEN v.event_type = 'view' THEN 1.0
                WHEN v.event_type = 'addtocart' THEN 3.0
                WHEN v.event_type = 'transaction' THEN 6.0
                ELSE 1.0
            END AS implicit_weight,
            v.transaction_id,
            v.event_timestamp,
            v.event_date,
            EXTRACT('dayofweek' FROM v.event_timestamp) AS day_of_week,
            EXTRACT('hour' FROM v.event_timestamp) AS hour_of_day,
            p.category,
            p.sub_category,
            p.brand,
            p.price_pkr,
            p.price_band,
            COALESCE(f.festival_name, 'Regular_Day') AS festival_name,
            CASE WHEN f.festival_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_festival_period
        FROM valid_events v
        INNER JOIN product_catalogue p
          ON v.raw_itemid = p.raw_itemid
        LEFT JOIN festival_calendar f
          ON v.event_date BETWEEN f.start_date AND f.end_date;
        """
    )

    clean_count = int(con.execute("SELECT COUNT(*) FROM interactions_clean").fetchall()[0][0])
    bot_or_unmapped_removed = dedup_count - clean_count

    # ------------------------------------------------------------------
    # Step 6: Build Session Summary Table & User/Item Contiguous ID Maps
    # ------------------------------------------------------------------
    con.execute(
        """
        CREATE OR REPLACE TABLE sessions AS
        SELECT
            session_id,
            user_id,
            visitor_id,
            MIN(event_timestamp) AS session_start,
            MAX(event_timestamp) AS session_end,
            DATE_DIFF('second', MIN(event_timestamp), MAX(event_timestamp)) AS session_duration_sec,
            COUNT(*) AS total_events,
            SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS view_count,
            SUM(CASE WHEN event_type = 'addtocart' THEN 1 ELSE 0 END) AS cart_count,
            SUM(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS purchase_count,
            SUM(CASE WHEN event_type = 'transaction' THEN price_pkr ELSE 0.0 END) AS session_revenue_pkr,
            MAX(CASE WHEN is_festival_period THEN 1 ELSE 0 END) = 1 AS is_festival_session
        FROM interactions_clean
        GROUP BY session_id, user_id, visitor_id;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE user_id_map AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY visitor_id) - 1 AS user_idx,
            user_id,
            visitor_id,
            COUNT(*) AS total_interactions,
            SUM(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS total_purchases
        FROM interactions_clean
        GROUP BY user_id, visitor_id;

        CREATE OR REPLACE TABLE item_id_map AS
        SELECT
            ROW_NUMBER() OVER (ORDER BY product_id) - 1 AS item_idx,
            product_id,
            raw_itemid,
            category,
            brand,
            price_pkr
        FROM product_catalogue;
        """
    )

    # Export key processed tables to Parquet for fast downstream consumption
    interactions_parquet = str(settings.processed_dir / "interactions_clean.parquet").replace("\\", "/")
    sessions_parquet = str(settings.processed_dir / "sessions.parquet").replace("\\", "/")
    user_map_parquet = str(settings.processed_dir / "user_id_map.parquet").replace("\\", "/")
    item_map_parquet = str(settings.processed_dir / "item_id_map.parquet").replace("\\", "/")

    con.execute(
        f"""
        COPY interactions_clean TO '{interactions_parquet}' (FORMAT PARQUET);
        COPY sessions TO '{sessions_parquet}' (FORMAT PARQUET);
        COPY user_id_map TO '{user_map_parquet}' (FORMAT PARQUET);
        COPY item_id_map TO '{item_map_parquet}' (FORMAT PARQUET);
        """
    )

    total_sessions = int(con.execute("SELECT COUNT(*) FROM sessions").fetchall()[0][0])
    unique_users = int(con.execute("SELECT COUNT(*) FROM user_id_map").fetchall()[0][0])
    unique_items = int(con.execute("SELECT COUNT(DISTINCT product_id) FROM interactions_clean").fetchall()[0][0])

    con.close()

    return PipelineSummary(
        raw_events_count=raw_count,
        duplicate_events_removed=duplicates_removed,
        bot_events_removed=bot_or_unmapped_removed,
        clean_events_count=clean_count,
        total_sessions=total_sessions,
        unique_users=unique_users,
        unique_items=unique_items,
        catalogue_products=len(catalogue_df),
        daily_sales_rows=len(sales_df),
        reviews_rows=len(reviews_df),
        duckdb_path=str(target_db),
    )

