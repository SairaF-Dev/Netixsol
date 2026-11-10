"""
Day 1 — Task 3: Customer RFM Analysis & Behavioral K-Means Segmentation.

Implements:
1. Recency, Frequency, Monetary (RFM) scoring (1-5 quintiles)
2. K-Means clustering on standardized behavioral features
3. Pakistani marketplace persona naming, profiling, and targeted marketing actions
4. Visualization of segment sizes and RFM profiles (`06_customer_rfm_segments.png`)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from shopkaro.config.settings import settings


SEGMENT_MARKETING_ACTIONS: dict[str, dict[str, str]] = {
    "Loyal Electronics & VIP Buyers": {
        "description": "High-monetary, recent repeat buyers purchasing smartphones, laptops, and premium appliances.",
        "marketing_action": "Grant early VIP access to 11.11 Mega Sales, zero-markup installment plans, and bundled accessory cross-sells.",
    },
    "Eid & Festive Lawn Shoppers": {
        "description": "Customers whose browsing and purchasing heavily concentrate during Ramadan, Chaand Raat, and Eid.",
        "marketing_action": "Send WhatsApp & push lookbooks 15 days before Ramadan and Eid with 'Complete the Eid Look' dupatta/khussa bundles.",
    },
    "Active Multi-Category Families": {
        "description": "Consistent household shoppers buying across Women's Lawn, Kids School Supplies, and Groceries.",
        "marketing_action": "Enroll in ShopKaro Family Loyalty Points with free delivery thresholds on monthly rashan and back-to-school kits.",
    },
    "Bargain Hunters & Cart Hesitators": {
        "description": "High view and add-to-cart activity on budget/sale items but lower checkout completion.",
        "marketing_action": "Trigger automated 2-hour abandoned-cart 10% flash discount codes and highlight 'Under 3,000 PKR' deals.",
    },
    "At-Risk & Dormant Browsers": {
        "description": "Previously active visitors with high recency (60+ days inactive) at high risk of permanent churn.",
        "marketing_action": "Launch a 'We Miss You' win-back campaign with Rs. 500 voucher on their historical favourite category.",
    },
}


@dataclass
class SegmentationReport:
    """Summary of RFM and K-Means behavioral customer segmentation."""

    total_segmented_users: int
    n_clusters: int
    silhouette_score: float
    segment_profiles_df: pd.DataFrame
    figure_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_segmented_users": self.total_segmented_users,
            "n_clusters": self.n_clusters,
            "silhouette_score": self.silhouette_score,
            "segment_profiles": self.segment_profiles_df.to_dict("records"),
            "figure_path": self.figure_path,
        }


def run_customer_segmentation(
    db_path: Path | None = None,
    figures_dir: Path | None = None,
    n_clusters: int = 5,
) -> SegmentationReport:
    """
    Compute RFM metrics + behavioral features in DuckDB, run K-Means clustering,
    assign meaningful Pakistani e-commerce segment personas and marketing actions,
    and persist `customer_segments` to DuckDB and Parquet.
    """
    target_db = db_path or settings.duckdb_path
    fig_dir = figures_dir or settings.figures_dir
    fig_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(target_db))

    # Extract behavioral & RFM metrics for engaged users (all buyers/carters + top active visitors)
    rfm_df = con.execute(
        """
        WITH max_dt AS (
            SELECT MAX(event_date) AS ref_date FROM interactions_clean
        ),
        user_agg AS (
            SELECT
                user_id,
                DATE_DIFF('day', MAX(event_date), (SELECT ref_date FROM max_dt)) AS recency_days,
                COUNT(DISTINCT session_id) AS frequency_sessions,
                COUNT(*) AS total_events,
                SUM(CASE WHEN event_type = 'addtocart' THEN 1 ELSE 0 END) AS cart_events,
                SUM(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS purchase_events,
                SUM(
                    CASE
                        WHEN event_type = 'transaction' THEN price_pkr
                        WHEN event_type = 'addtocart' THEN price_pkr * 0.25
                        ELSE price_pkr * 0.02
                    END
                ) AS monetary_intent_pkr,
                SUM(CASE WHEN event_type = 'transaction' THEN price_pkr ELSE 0.0 END) AS realized_spend_pkr,
                AVG(CASE WHEN is_festival_period THEN 1.0 ELSE 0.0 END) AS festival_share,
                AVG(
                    CASE
                        WHEN category IN ('Smartphones & Accessories', 'Laptops & Computing', 'Home & Kitchen Appliances')
                        THEN 1.0 ELSE 0.0
                    END
                ) AS electronics_share,
                AVG(CASE WHEN on_sale_flag THEN 1.0 ELSE 0.0 END) AS sale_item_share
            FROM (
                SELECT
                    i.*,
                    p.on_sale AS on_sale_flag
                FROM interactions_clean i
                JOIN product_catalogue p ON i.product_id = p.product_id
            )
            GROUP BY user_id
        )
        SELECT *
        FROM user_agg
        ORDER BY purchase_events DESC, cart_events DESC, total_events DESC
        LIMIT 60000;
        """
    ).df()

    # Compute 1-5 RFM Quintile Scores (5 = Best: lowest recency, highest frequency, highest monetary)
    rfm_df["r_score"] = pd.qcut(
        rfm_df["recency_days"].rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    rfm_df["f_score"] = pd.qcut(
        rfm_df["frequency_sessions"].rank(method="first", ascending=True), 5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    rfm_df["m_score"] = pd.qcut(
        rfm_df["monetary_intent_pkr"].rank(method="first", ascending=True), 5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    rfm_df["rfm_composite"] = rfm_df["r_score"] + rfm_df["f_score"] + rfm_df["m_score"]

    # Feature matrix for K-Means clustering
    feature_cols = [
        "recency_days",
        "frequency_sessions",
        "monetary_intent_pkr",
        "festival_share",
        "electronics_share",
        "sale_item_share",
    ]
    X_raw = rfm_df[feature_cols].copy()
    X_raw["frequency_sessions"] = np.log1p(X_raw["frequency_sessions"])
    X_raw["monetary_intent_pkr"] = np.log1p(X_raw["monetary_intent_pkr"])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    kmeans = KMeans(n_clusters=n_clusters, random_state=settings.random_seed, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    rfm_df["cluster_id"] = clusters

    # Compute Silhouette Score on a 5,000-user subsample for speed
    rng = np.random.default_rng(settings.random_seed)
    sample_idx = rng.choice(len(X_scaled), size=min(5000, len(X_scaled)), replace=False)
    sil_score = float(silhouette_score(X_scaled[sample_idx], clusters[sample_idx]))

    # Deterministically map each cluster ID to one of the 5 named Pakistani personas
    cluster_means = rfm_df.groupby("cluster_id")[
        ["recency_days", "monetary_intent_pkr", "festival_share", "electronics_share", "sale_item_share"]
    ].mean()

    assigned_names: dict[int, str] = {}
    remaining = set(range(n_clusters))

    # 1. Highest electronics & monetary -> Loyal Electronics & VIP Buyers
    c_vip = int(
        (cluster_means.loc[list(remaining), "electronics_share"] * 2.0
         + cluster_means.loc[list(remaining), "monetary_intent_pkr"].rank(pct=True)).idxmax()
    )
    assigned_names[c_vip] = "Loyal Electronics & VIP Buyers"
    remaining.remove(c_vip)

    # 2. Highest festival share -> Eid & Festive Lawn Shoppers
    c_eid = int(cluster_means.loc[list(remaining), "festival_share"].idxmax())
    assigned_names[c_eid] = "Eid & Festive Lawn Shoppers"
    remaining.remove(c_eid)

    # 3. Highest recency (longest inactive) -> At-Risk & Dormant Browsers
    c_dormant = int(cluster_means.loc[list(remaining), "recency_days"].idxmax())
    assigned_names[c_dormant] = "At-Risk & Dormant Browsers"
    remaining.remove(c_dormant)

    # 4. Highest sale_item_share among remaining -> Bargain Hunters & Cart Hesitators
    c_bargain = int(cluster_means.loc[list(remaining), "sale_item_share"].idxmax())
    assigned_names[c_bargain] = "Bargain Hunters & Cart Hesitators"
    remaining.remove(c_bargain)

    # 5. Remaining cluster -> Active Multi-Category Families
    for c_rem in remaining:
        assigned_names[int(c_rem)] = "Active Multi-Category Families"

    rfm_df["segment_name"] = rfm_df["cluster_id"].map(assigned_names)
    rfm_df["segment_description"] = rfm_df["segment_name"].map(
        lambda s: SEGMENT_MARKETING_ACTIONS[s]["description"]
    )
    rfm_df["recommended_marketing_action"] = rfm_df["segment_name"].map(
        lambda s: SEGMENT_MARKETING_ACTIONS[s]["marketing_action"]
    )

    # Build Segment Summary Table
    segment_profiles_df = (
        rfm_df.groupby(["segment_name", "segment_description", "recommended_marketing_action"], as_index=False)
        .agg(
            user_count=("user_id", "count"),
            avg_recency_days=("recency_days", "mean"),
            avg_sessions=("frequency_sessions", "mean"),
            avg_monetary_pkr=("monetary_intent_pkr", "mean"),
            avg_festival_share=("festival_share", "mean"),
            avg_rfm_score=("rfm_composite", "mean"),
        )
        .sort_values("avg_monetary_pkr", ascending=False)
        .reset_index(drop=True)
    )
    segment_profiles_df["user_share_pct"] = np.round(
        (segment_profiles_df["user_count"] / len(rfm_df)) * 100.0, 2
    )
    for col in ["avg_recency_days", "avg_sessions", "avg_monetary_pkr", "avg_festival_share", "avg_rfm_score"]:
        segment_profiles_df[col] = np.round(segment_profiles_df[col], 2)

    # Persist to Parquet & DuckDB
    seg_parquet = str(settings.processed_dir / "customer_segments.parquet").replace("\\", "/")
    rfm_df.to_parquet(settings.processed_dir / "customer_segments.parquet", index=False)

    con.execute(
        f"""
        CREATE OR REPLACE TABLE customer_segments AS
        SELECT * FROM read_parquet('{seg_parquet}');
        """
    )
    con.close()

    # Plot Segment Distribution & RFM Comparison
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    sns.barplot(
        data=segment_profiles_df,
        y="segment_name",
        x="user_count",
        hue="segment_name",
        legend=False,
        palette="viridis",
        ax=axes[0],
    )
    axes[0].set_title("Customer Segment Distribution (User Count)", fontweight="bold")
    axes[0].set_xlabel("Number of Customers")
    axes[0].set_ylabel("")

    sns.barplot(
        data=segment_profiles_df,
        y="segment_name",
        x="avg_monetary_pkr",
        hue="segment_name",
        legend=False,
        palette="magma",
        ax=axes[1],
    )
    axes[1].set_title("Average Monetary Value / Intent per Segment (PKR)", fontweight="bold")
    axes[1].set_xlabel("Avg Value (PKR)")
    axes[1].set_ylabel("")
    plt.tight_layout()
    f6 = fig_dir / "06_customer_rfm_segments.png"
    plt.savefig(f6, dpi=150)
    plt.close(fig)

    return SegmentationReport(
        total_segmented_users=len(rfm_df),
        n_clusters=n_clusters,
        silhouette_score=round(sil_score, 4),
        segment_profiles_df=segment_profiles_df,
        figure_path=str(f6),
    )

