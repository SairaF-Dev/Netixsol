"""
Automated tests for Day 1: Data Pipeline, Pakistani Context Adaptation,
EDA, RFM Segmentation, Cohort Analysis, and Chronological Splits.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.data.synthesizer import (
    generate_daily_sales_history,
    generate_festival_calendar,
    generate_product_catalogue,
)


def test_festival_calendar_and_catalogue_generation(tmp_path):
    """Verify Pakistani festival calendar and product catalogue generation."""
    fest_df = generate_festival_calendar(output_dir=tmp_path)
    assert len(fest_df) >= 15
    assert "Ramadan" in fest_df["festival_name"].values
    assert "Chaand Raat & Eid ul Fitr" in fest_df["festival_name"].values
    assert "11.11 Mega Sale" in fest_df["festival_name"].values

    cat_df = generate_product_catalogue(
        active_item_ids=list(range(100, 150)),
        olist_product_ids=[f"olist_{i}" for i in range(50)],
        output_dir=tmp_path,
        seed=42,
    )
    assert len(cat_df) == 50
    assert (cat_df["price_pkr"] > 0).all()
    assert cat_df["is_synthetic"].all()

    sales_df = generate_daily_sales_history(
        catalogue_df=cat_df,
        festival_df=fest_df,
        top_n_products=10,
        start_date="2024-01-01",
        end_date="2025-12-31",
        output_dir=tmp_path,
        seed=42,
    )
    # 10 products * 731 days (2024 is leap year: 366 + 365 = 731)
    assert len(sales_df) == 10 * 731
    assert (sales_df["units_sold"] >= 0).all()


def test_duckdb_day1_tables_and_chronological_splits():
    """Verify that the populated Day 1 DuckDB database has valid tables and zero temporal leakage."""
    assert settings.duckdb_path.exists(), "DuckDB database must exist after running Day 1 pipeline."
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)

    required_tables = {
        "raw_events",
        "interactions_clean",
        "sessions",
        "product_catalogue",
        "festival_calendar",
        "daily_sales",
        "reviews",
        "user_id_map",
        "item_id_map",
        "customer_segments",
        "user_features",
        "item_features",
        "train_interactions",
        "val_interactions",
        "test_interactions",
        "cold_start_test",
    }
    existing_tables = {
        r[0]
        for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
    }
    assert required_tables.issubset(existing_tables)

    # Verify chronological ordering of splits (max(train) <= min(val) and max(val) <= min(test))
    bounds = con.execute(
        """
        SELECT
            (SELECT EPOCH(MAX(event_timestamp)) FROM train_interactions) AS max_train,
            (SELECT EPOCH(MIN(event_timestamp)) FROM val_interactions) AS min_val,
            (SELECT EPOCH(MAX(event_timestamp)) FROM val_interactions) AS max_val,
            (SELECT EPOCH(MIN(event_timestamp)) FROM test_interactions) AS min_test
        """
    ).fetchall()[0]
    assert bounds[0] <= bounds[1], "Train max timestamp must not exceed Validation min timestamp"
    assert bounds[2] <= bounds[3], "Validation max timestamp must not exceed Test min timestamp"

    # Verify no session in `sessions` exceeds the 1,000-click bot threshold
    max_session_clicks = con.execute("SELECT MAX(total_events) FROM sessions").fetchall()[0][0]
    assert max_session_clicks < settings.bot_max_clicks_per_session

    con.close()

