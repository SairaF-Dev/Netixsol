"""
Day 1 — Task 5: Feature Engineering, Time-Based Splits & Cold-Start Evaluation Sets.

Why Time-Based Splits Are Mandatory for Recommender Systems:
------------------------------------------------------------
A random train/test split leaks future user behavior into the training set:
1. It allows the model to observe future purchases at time t+k when predicting past actions at time t.
2. It leaks global popularity and seasonal festival surges (e.g., Eid lawn demand) before they occur.
3. In production, a recommender trained up to day T must predict behavior on days T+1..T+k.
Therefore, we strictly sort interactions chronologically and partition into:
- Train (first 70% of timeline)
- Validation (next 15% of timeline)
- Test (final 15% of timeline)
- Cold-Start Test Set: subset of Test containing users or items unseen in Train.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from shopkaro.config.settings import settings


@dataclass
class SplitSummary:
    """Summary metrics for time-based splits and feature engineering."""

    train_rows: int
    val_rows: int
    test_rows: int
    cold_start_test_rows: int
    cold_users_in_test: int
    cold_items_in_test: int
    train_end_timestamp: str
    val_end_timestamp: str
    user_features_count: int
    item_features_count: int
    embedding_dim: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_rows": self.train_rows,
            "val_rows": self.val_rows,
            "test_rows": self.test_rows,
            "cold_start_test_rows": self.cold_start_test_rows,
            "cold_users_in_test": self.cold_users_in_test,
            "cold_items_in_test": self.cold_items_in_test,
            "train_end_timestamp": self.train_end_timestamp,
            "val_end_timestamp": self.val_end_timestamp,
            "user_features_count": self.user_features_count,
            "item_features_count": self.item_features_count,
            "embedding_dim": self.embedding_dim,
        }


def build_features_and_time_splits(
    db_path: Path | None = None,
    embedding_dim: int = 64,
) -> SplitSummary:
    """
    Build user features, item features (with text embeddings of title + description),
    chronological train/val/test splits, and the cold-start test set.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db))

    # ------------------------------------------------------------------
    # 1. Chronological Time-Based Train / Validation / Test Split
    # ------------------------------------------------------------------
    quantiles = con.execute(
        f"""
        SELECT
             CAST(quantile_cont(CAST(event_timestamp AS TIMESTAMP), {settings.train_ratio}) AS VARCHAR) AS train_cutoff,
             CAST(quantile_cont(CAST(event_timestamp AS TIMESTAMP), {settings.train_ratio + settings.val_ratio}) AS VARCHAR) AS val_cutoff
        FROM interactions_clean;
        """
    ).fetchall()[0]

    train_cutoff = quantiles[0]
    val_cutoff = quantiles[1]

    con.execute(
        f"""
        CREATE OR REPLACE TABLE train_interactions AS
        SELECT * FROM interactions_clean
        WHERE CAST(event_timestamp AS TIMESTAMP) <= TIMESTAMP '{train_cutoff}';

        CREATE OR REPLACE TABLE val_interactions AS
        SELECT * FROM interactions_clean
        WHERE CAST(event_timestamp AS TIMESTAMP) > TIMESTAMP '{train_cutoff}'
          AND CAST(event_timestamp AS TIMESTAMP) <= TIMESTAMP '{val_cutoff}';

        CREATE OR REPLACE TABLE test_interactions AS
        SELECT * FROM interactions_clean
        WHERE CAST(event_timestamp AS TIMESTAMP) > TIMESTAMP '{val_cutoff}';
        """
    )

    # ------------------------------------------------------------------
    # 2. Cold-Start Test Set (Users or Items NOT seen in Training)
    # ------------------------------------------------------------------
    con.execute(
        """
        CREATE OR REPLACE TABLE cold_start_test AS
        WITH train_users AS (
            SELECT DISTINCT user_id FROM train_interactions
        ),
        train_items AS (
            SELECT DISTINCT product_id FROM train_interactions
        )
        SELECT
            t.*,
            CASE WHEN tu.user_id IS NULL THEN TRUE ELSE FALSE END AS is_cold_user,
            CASE WHEN ti.product_id IS NULL THEN TRUE ELSE FALSE END AS is_cold_item
        FROM test_interactions t
        LEFT JOIN train_users tu ON t.user_id = tu.user_id
        LEFT JOIN train_items ti ON t.product_id = ti.product_id
        WHERE tu.user_id IS NULL OR ti.product_id IS NULL;
        """
    )

    # ------------------------------------------------------------------
    # 3. User Features (Computed on Training Window to Avoid Leakage)
    # ------------------------------------------------------------------
    # Check if customer_segments table already exists from Task 3
    has_segments = (
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'customer_segments'"
        ).fetchall()[0][0]
        > 0
    )

    segment_join = (
        "LEFT JOIN customer_segments cs ON u.user_id = cs.user_id"
        if has_segments
        else ""
    )
    segment_col = (
        "COALESCE(cs.segment_name, 'Casual & Window Browsers')"
        if has_segments
        else "'Casual & Window Browsers'"
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE user_features AS
        WITH user_cat_ranks AS (
            SELECT
                user_id,
                category,
                COUNT(*) AS cat_events,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id
                    ORDER BY SUM(implicit_weight) DESC, COUNT(*) DESC
                ) AS rn
            FROM train_interactions
            GROUP BY user_id, category
        ),
        user_stats AS (
            SELECT
                user_id,
                COUNT(*) AS total_events,
                COUNT(DISTINCT session_id) AS total_sessions,
                SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS view_count,
                SUM(CASE WHEN event_type = 'addtocart' THEN 1 ELSE 0 END) AS cart_count,
                SUM(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS purchase_count,
                AVG(price_pkr) AS avg_browsed_price_pkr,
                COALESCE(
                    AVG(CASE WHEN event_type = 'transaction' THEN price_pkr END),
                    AVG(price_pkr)
                ) AS avg_order_value_pkr,
                SUM(CASE WHEN event_type = 'transaction' THEN price_pkr ELSE 0.0 END) AS total_spend_pkr,
                AVG(CASE WHEN is_festival_period THEN 1.0 ELSE 0.0 END) AS festival_activity_share
            FROM train_interactions
            GROUP BY user_id
        )
        SELECT
            um.user_idx,
            u.user_id,
            {segment_col} AS segment_name,
            COALESCE(uc.category, 'Women''s Lawn & Unstitched') AS favourite_category,
            u.total_events,
            u.total_sessions,
            u.view_count,
            u.cart_count,
            u.purchase_count,
            ROUND(u.avg_browsed_price_pkr, 2) AS avg_browsed_price_pkr,
            ROUND(u.avg_order_value_pkr, 2) AS avg_order_value_pkr,
            ROUND(u.total_spend_pkr, 2) AS total_spend_pkr,
            ROUND(CAST(u.purchase_count AS DOUBLE) / GREATEST(u.view_count, 1), 4) AS conversion_rate,
            ROUND(u.festival_activity_share, 4) AS festival_activity_share
        FROM user_stats u
        JOIN user_id_map um ON u.user_id = um.user_id
        LEFT JOIN user_cat_ranks uc ON u.user_id = uc.user_id AND uc.rn = 1
        {segment_join};
        """
    )

    # ------------------------------------------------------------------
    # 4. Item Features + Text Embeddings of (Title + Description)
    # ------------------------------------------------------------------
    item_df = con.execute(
        """
        WITH item_stats AS (
            SELECT
                product_id,
                COUNT(*) AS total_events,
                SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS view_count,
                SUM(CASE WHEN event_type = 'addtocart' THEN 1 ELSE 0 END) AS cart_count,
                SUM(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS purchase_count,
                SUM(implicit_weight) AS weighted_popularity
            FROM train_interactions
            GROUP BY product_id
        )
        SELECT
            im.item_idx,
            p.product_id,
            p.raw_itemid,
            p.title,
            p.description,
            p.category,
            p.sub_category,
            p.brand,
            p.color,
            p.occasion,
            p.price_pkr,
            p.price_band,
            p.on_sale,
            p.discount_pct,
            p.margin_pct,
            p.stock_qty,
            p.in_stock,
            COALESCE(s.total_events, 0) AS total_events,
            COALESCE(s.view_count, 0) AS view_count,
            COALESCE(s.cart_count, 0) AS cart_count,
            COALESCE(s.purchase_count, 0) AS purchase_count,
            COALESCE(s.weighted_popularity, 0.0) AS popularity_score,
            ROUND(
                CAST(COALESCE(s.purchase_count, 0) AS DOUBLE)
                / GREATEST(COALESCE(s.view_count, 0), 1),
                4
            ) AS item_conversion_rate
        FROM product_catalogue p
        JOIN item_id_map im ON p.product_id = im.product_id
        LEFT JOIN item_stats s ON p.product_id = s.product_id
        ORDER BY im.item_idx;
        """
    ).df()

    # Compute dense normalized text embeddings (TF-IDF + LSA/SVD) of title + description + category + brand
    corpus = (
        item_df["title"].fillna("")
        + " "
        + item_df["category"].fillna("")
        + " "
        + item_df["brand"].fillna("")
        + " "
        + item_df["occasion"].fillna("")
        + " "
        + item_df["description"].fillna("")
    ).tolist()

    tfidf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words="english")
    tfidf_mat = tfidf.fit_transform(corpus)
    actual_dim = min(embedding_dim, tfidf_mat.shape[1] - 1, tfidf_mat.shape[0] - 1)
    svd = TruncatedSVD(n_components=actual_dim, random_state=settings.random_seed)
    emb_matrix = normalize(svd.fit_transform(tfidf_mat)).astype(np.float32)

    # Save the dense embedding matrix as numpy array for fast cosine similarity in Day 2 & Day 4
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    np.save(settings.models_dir / "item_text_embeddings.npy", emb_matrix)

    # Store compact 8-dim summary + norm on item_features table
    for d in range(min(8, actual_dim)):
        item_df[f"text_emb_{d}"] = np.round(emb_matrix[:, d], 5)

    item_feat_parquet = str(settings.processed_dir / "item_features.parquet").replace("\\", "/")
    item_df.to_parquet(settings.processed_dir / "item_features.parquet", index=False)

    con.execute(
        f"""
        CREATE OR REPLACE TABLE item_features AS
        SELECT * FROM read_parquet('{item_feat_parquet}');
        """
    )

    # Export splits & user features to Parquet
    for tbl_name in [
        "train_interactions",
        "val_interactions",
        "test_interactions",
        "cold_start_test",
        "user_features",
    ]:
        out_path = str(settings.processed_dir / f"{tbl_name}.parquet").replace("\\", "/")
        con.execute(f"COPY {tbl_name} TO '{out_path}' (FORMAT PARQUET);")

    train_rows = int(con.execute("SELECT COUNT(*) FROM train_interactions").fetchall()[0][0])
    val_rows = int(con.execute("SELECT COUNT(*) FROM val_interactions").fetchall()[0][0])
    test_rows = int(con.execute("SELECT COUNT(*) FROM test_interactions").fetchall()[0][0])
    cold_rows = int(con.execute("SELECT COUNT(*) FROM cold_start_test").fetchall()[0][0])
    cold_users = int(
        con.execute("SELECT COUNT(DISTINCT user_id) FROM cold_start_test WHERE is_cold_user").fetchall()[0][0]
    )
    cold_items = int(
        con.execute("SELECT COUNT(DISTINCT product_id) FROM cold_start_test WHERE is_cold_item").fetchall()[0][0]
    )
    user_feat_cnt = int(con.execute("SELECT COUNT(*) FROM user_features").fetchall()[0][0])

    con.close()

    return SplitSummary(
        train_rows=train_rows,
        val_rows=val_rows,
        test_rows=test_rows,
        cold_start_test_rows=cold_rows,
        cold_users_in_test=cold_users,
        cold_items_in_test=cold_items,
        train_end_timestamp=str(train_cutoff),
        val_end_timestamp=str(val_cutoff),
        user_features_count=user_feat_cnt,
        item_features_count=len(item_df),
        embedding_dim=actual_dim,
    )

