"""
Day 2 — Task 4: Comprehensive Offline Evaluation of All 8 Recommender Models.

Compares:
1. Baseline 1: Most Popular Overall
2. Baseline 2: Most Popular in User's Favourite Category
3. Baseline 3: Recently Trending (Last 7 Days)
4. Collaborative 1: Item-to-Item Collaborative Filtering (Cosine)
5. Collaborative 2: Implicit Matrix Factorisation (ALS)
6. Content-Based: 64-Dim Text Embeddings + Metadata Profile
7. Hybrid Blend: hand-weighted Item-CF + ALS + Content + User/Item Features + Cold-Start Router
8. Neural Two-Tower (PyTorch): user and item towers trained jointly with in-batch softmax (two_tower.py)

Across:
- Precision@10, Recall@10, NDCG@10, MAP@10, HitRate@10
- Catalogue Coverage (%)
- Intra-List Diversity (ILD@10) using pairwise cosine dissimilarity of content embeddings
- Novelty@10 (mean self-information -log2 P(i) in bits)
- Cold-Start User NDCG@10 & Cold-Start Item HitRate@10
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings
from shopkaro.recommendations.baselines import (
    BaseRecommender,
    FavouriteCategoryPopularRecommender,
    PopularOverallRecommender,
    Trending7DayRecommender,
    load_test_ground_truth,
)
from shopkaro.recommendations.collaborative import (
    ImplicitALSRecommender,
    ItemToItemCFRecommender,
    _load_sparse_interaction_data,
)
from shopkaro.recommendations.collaborative import load_val_ground_truth
from shopkaro.recommendations.hybrid import (
    ContentBasedRecommender,
    HybridTwoTowerRecommender,
)
from shopkaro.recommendations.two_tower import TwoTowerRecommender, load_val_cold_users


@dataclass
class FullModelEvalRow:
    """Comprehensive evaluation row for a recommender model on Day 2 Task 4."""

    model_name: str
    model_family: str
    k: int
    evaluated_users: int
    precision_at_10: float
    recall_at_10: float
    ndcg_at_10: float
    map_at_10: float
    hit_rate_at_10: float
    catalogue_coverage_pct: float
    intra_list_diversity_at_10: float
    novelty_bits_at_10: float
    cold_user_ndcg_at_10: float
    cold_item_hit_rate_at_10: float


def _compute_item_self_information_bits(
    con: duckdb.DuckDBPyConnection,
    all_product_ids: list[str],
) -> dict[str, float]:
    """
    Compute Novelty (Self-Information) per item i in bits:
        Novelty(i) = -log2( (users_interacted(i) + 1) / (total_train_users + 1) )
    """
    n_train_users = int(
        con.execute("SELECT COUNT(DISTINCT user_id) FROM train_interactions").fetchall()[0][0]
    )
    pop_df = con.execute(
        """
        SELECT
            product_id,
            COUNT(DISTINCT user_id) AS n_users
        FROM train_interactions
        GROUP BY product_id;
        """
    ).df()
    user_counts = dict(
        zip(pop_df["product_id"].astype(str), pop_df["n_users"].astype(int), strict=False)
    )
    denom = float(max(n_train_users + 1, 2))
    novelty_map: dict[str, float] = {}
    for pid in all_product_ids:
        cnt = user_counts.get(pid, 0)
        prob = (cnt + 1.0) / denom
        novelty_map[pid] = float(-np.log2(prob))
    return novelty_map


def _compute_list_ild(
    rec_pids: list[str],
    item_to_col: dict[str, int],
    item_embeddings: np.ndarray,
) -> float:
    """
    Compute Intra-List Diversity (ILD@K) for a recommended list R_u:
        ILD(R_u) = 2 / (K * (K - 1)) * sum_{a < b} (1 - <e_a, e_b>)
    Using vectorized sum identity for unit-normalized vectors:
        sum_{a != b} <e_a, e_b> = ||sum_a e_a||_2^2 - K
    """
    cols = [item_to_col[pid] for pid in rec_pids if pid in item_to_col]
    m = len(cols)
    if m <= 1:
        return 0.0
    sub_emb = item_embeddings[cols]  # (m, 64), each row unit L2 norm
    sum_vec = sub_emb.sum(axis=0)
    sum_off_diag_cos = float(np.dot(sum_vec, sum_vec) - m)
    avg_cos = sum_off_diag_cos / float(m * (m - 1))
    # Clamp numerical noise to [0, 1]
    return float(np.clip(1.0 - avg_cos, 0.0, 1.0))


def evaluate_single_model_full(
    model: BaseRecommender,
    model_family: str,
    warm_gt: dict[str, set[str]],
    cold_user_gt: dict[str, set[str]],
    cold_item_warm_user_gt: dict[str, set[str]],
    cold_item_cols: np.ndarray,
    item_to_col: dict[str, int],
    item_embeddings: np.ndarray,
    novelty_map: dict[str, float],
    k: int = 10,
    exclude_seen: bool = False,
) -> FullModelEvalRow:
    """Evaluate a single recommender across accuracy, beyond-accuracy, and cold-start metrics."""
    precisions: list[float] = []
    recalls: list[float] = []
    ndcgs: list[float] = []
    aps: list[float] = []
    hits: list[float] = []
    ilds: list[float] = []
    novelties: list[float] = []
    recommended_catalogue: set[str] = set()

    discounts = 1.0 / np.log2(np.arange(2, k + 2))

    for uid, relevant_items in warm_gt.items():
        if not relevant_items:
            continue
        recs_with_scores = model.recommend_ids(
            user_id=uid,
            k=k,
            exclude_seen=exclude_seen,
            only_in_stock=True,
        )
        recs = [pid for pid, _ in recs_with_scores[:k]]
        recommended_catalogue.update(recs)

        hit_vec = np.array([1.0 if pid in relevant_items else 0.0 for pid in recs], dtype=float)
        n_hits = float(hit_vec.sum())

        precisions.append(n_hits / k)
        recalls.append(n_hits / len(relevant_items))
        hits.append(1.0 if n_hits > 0 else 0.0)

        dcg = float(np.sum(hit_vec[: len(discounts)] * discounts[: len(hit_vec)]))
        ideal_len = min(len(relevant_items), k)
        idcg = float(np.sum(discounts[:ideal_len]))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

        if n_hits > 0:
            cum_hits = np.cumsum(hit_vec)
            ranks = np.arange(1, len(hit_vec) + 1, dtype=float)
            ap = float(np.sum((cum_hits / ranks) * hit_vec) / min(len(relevant_items), k))
        else:
            ap = 0.0
        aps.append(ap)

        # Beyond-accuracy: Intra-List Diversity & Novelty
        ilds.append(_compute_list_ild(recs, item_to_col=item_to_col, item_embeddings=item_embeddings))
        if recs:
            novelties.append(float(np.mean([novelty_map.get(pid, 12.0) for pid in recs])))

    # Cold-Start User NDCG@10
    cold_user_ndcgs: list[float] = []
    for uid, rel_items in cold_user_gt.items():
        if not rel_items:
            continue
        recs_scores = model.recommend_ids(user_id=uid, k=k, exclude_seen=False, only_in_stock=True)
        recs = [pid for pid, _ in recs_scores[:k]]
        hit_vec = np.array([1.0 if pid in rel_items else 0.0 for pid in recs], dtype=float)
        dcg = float(np.sum(hit_vec[: len(discounts)] * discounts[: len(hit_vec)]))
        idcg = float(np.sum(discounts[: min(len(rel_items), k)]))
        cold_user_ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

    # Cold-Start Item HitRate@10 (can the model surface brand-new items with 0 training clicks?)
    cold_item_hits: list[float] = []
    if isinstance(model, ContentBasedRecommender):
        content_ref = model
    elif isinstance(model, HybridTwoTowerRecommender):
        content_ref = model.content_model
    elif getattr(model, "scores_cold_items", False):  # neural two-tower: item tower embeds unseen items
        content_ref = model
    else:
        content_ref = None

    if content_ref is not None:
        for uid, true_cold_pids in cold_item_warm_user_gt.items():
            scores = content_ref.score_all_items_for_user(
                user_id=uid,
                exclude_seen=True,
                only_in_stock=True,
                allowed_cols=cold_item_cols,
            )
            top_idx = np.argpartition(scores, -k)[-k:]
            recs = [content_ref.col_to_item[int(i)] for i in top_idx]
            cold_item_hits.append(1.0 if any(pid in true_cold_pids for pid in recs) else 0.0)
    else:
        # Pure popularity/trending/CF models have 0 historical interactions for cold items
        cold_item_hits = [0.0]

    total_cat = max(model.total_catalogue_size, 1)
    coverage_pct = (len(recommended_catalogue) / total_cat) * 100.0

    return FullModelEvalRow(
        model_name=model.name,
        model_family=model_family,
        k=k,
        evaluated_users=len(precisions),
        precision_at_10=round(float(np.mean(precisions)), 5),
        recall_at_10=round(float(np.mean(recalls)), 5),
        ndcg_at_10=round(float(np.mean(ndcgs)), 5),
        map_at_10=round(float(np.mean(aps)), 5),
        hit_rate_at_10=round(float(np.mean(hits)), 5),
        catalogue_coverage_pct=round(coverage_pct, 3),
        intra_list_diversity_at_10=round(float(np.mean(ilds)), 4),
        novelty_bits_at_10=round(float(np.mean(novelties)), 3),
        cold_user_ndcg_at_10=round(float(np.mean(cold_user_ndcgs)), 5),
        cold_item_hit_rate_at_10=round(float(np.mean(cold_item_hits)), 5),
    )


def plot_recommender_comparison_chart(
    comparison_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Generate a 4-panel publication-grade comparison chart (`08_recommender_model_comparison.png`):
    1. Warm Ranking Accuracy (NDCG@10 & HitRate@10)
    2. Catalogue Coverage (% of 25,000 SKUs surfaced)
    3. Beyond-Accuracy: Intra-List Diversity (ILD@10) & Novelty (Bits)
    4. Cold-Start Robustness (Cold-User NDCG@10 & Cold-Item HitRate@10)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    short_labels = [
        "1. Most Popular",
        "2. Fav Category Pop",
        "3. Trending (7d)",
        "4. Item-to-Item CF",
        "5. Implicit ALS",
        "6. Content-Based",
        "7. Hybrid Blend",
        "8. Neural Two-Tower",
    ][: len(comparison_df)]
    y_pos = np.arange(len(comparison_df))

    fig, axes = plt.subplots(2, 2, figsize=(16, 12.5))
    fig.suptitle(
        f"ShopKaro AI — Day 2 Recommendation Engine Offline Evaluation ({len(comparison_df)} Models @ K=10)",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )

    # Panel 1: Warm Ranking Accuracy (NDCG@10 & HitRate@10)
    ax1 = axes[0, 0]
    w = 0.36
    bars_ndcg = ax1.barh(
        y_pos - w / 2,
        comparison_df["ndcg_at_10"],
        height=w,
        label="NDCG@10",
        color="#1f77b4",
    )
    bars_hr = ax1.barh(
        y_pos + w / 2,
        comparison_df["hit_rate_at_10"],
        height=w,
        label="HitRate@10",
        color="#2ca02c",
    )
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(short_labels, fontsize=10)
    ax1.invert_yaxis()
    ax1.set_xlabel("Score (Higher is Better)")
    ax1.set_title("1. Ranking Accuracy on Chronological Warm Test Set", fontweight="bold")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=False)
    for b in bars_ndcg:
        ax1.text(
            b.get_width() + 0.002,
            b.get_y() + b.get_height() / 2,
            f"{b.get_width():.4f}",
            va="center",
            fontsize=8.5,
        )

    # Panel 2: Catalogue Coverage (%)
    ax2 = axes[0, 1]
    palette_cov = ["#9ecae1", "#6baed6", "#9ecae1", "#3182bd", "#2171b5", "#fd8d3c", "#08519c", "#6a51a3"]
    bars_cov = ax2.barh(
        y_pos,
        comparison_df["catalogue_coverage_pct"],
        color=palette_cov[: len(comparison_df)],
        height=0.55,
    )
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(short_labels, fontsize=10)
    ax2.invert_yaxis()
    ax2.set_xlabel("Catalogue Coverage (% of 25,000 SKUs)")
    ax2.set_title("2. Long-Tail Discovery & Catalogue Coverage (%)", fontweight="bold")
    for b in bars_cov:
        ax2.text(
            b.get_width() + 0.8,
            b.get_y() + b.get_height() / 2,
            f"{b.get_width():.2f}%",
            va="center",
            fontsize=9,
        )
    ax2.set_xlim(0, max(comparison_df["catalogue_coverage_pct"]) * 1.18)

    # Panel 3: Intra-List Diversity & Self-Information Novelty
    ax3 = axes[1, 0]
    bars_ild = ax3.barh(
        y_pos - w / 2,
        comparison_df["intra_list_diversity_at_10"],
        height=w,
        label="Intra-List Diversity (ILD@10)",
        color="#9467bd",
    )
    bars_nov = ax3.barh(
        y_pos + w / 2,
        comparison_df["novelty_bits_at_10"] / 20.0,
        height=w,
        label="Novelty@10 (Bits / 20)",
        color="#ff7f0e",
    )
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(short_labels, fontsize=10)
    ax3.invert_yaxis()
    ax3.set_xlabel("Normalized Score (Higher = More Diverse / More Novel)")
    ax3.set_title("3. Beyond Accuracy: Intra-List Diversity & Novelty", fontweight="bold")
    ax3.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=False)
    for b, raw_nov in zip(bars_nov, comparison_df["novelty_bits_at_10"], strict=False):
        ax3.text(
            b.get_width() + 0.01,
            b.get_y() + b.get_height() / 2,
            f"{raw_nov:.1f} bits",
            va="center",
            fontsize=8.5,
        )

    # Panel 4: Cold-Start Performance (Cold-User NDCG@10 & Cold-Item HitRate@10)
    ax4 = axes[1, 1]
    bars_cu = ax4.barh(
        y_pos - w / 2,
        comparison_df["cold_user_ndcg_at_10"] * 100.0,
        height=w,
        label="Cold-User NDCG@10 (x100)",
        color="#17becf",
    )
    bars_ci = ax4.barh(
        y_pos + w / 2,
        comparison_df["cold_item_hit_rate_at_10"] * 100.0,
        height=w,
        label="Cold-Item HitRate@10 (%)",
        color="#d62728",
    )
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(short_labels, fontsize=10)
    ax4.invert_yaxis()
    ax4.set_xlabel("Percentage / Scaled Score")
    ax4.set_title("4. Cold-Start Robustness (Unseen Users & 588 Unseen Items)", fontweight="bold")
    ax4.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, frameon=False)
    for b in bars_ci:
        if b.get_width() > 0:
            ax4.text(
                b.get_width() + 0.05,
                b.get_y() + b.get_height() / 2,
                f"{b.get_width():.2f}%",
                va="center",
                fontsize=8.5,
            )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def run_day2_task4_offline_evaluation(
    db_path: Path | None = None,
    k: int = 10,
    max_eval_users: int = 5000,
    max_cold_users: int = 2000,
) -> tuple[pd.DataFrame, dict[str, BaseRecommender], Path]:
    """
    Execute Day 2 — Task 4:
    Fit all 8 models, evaluate them across all 10 metrics on the warm and cold-start test sets,
    save `reports/day2_model_comparison.csv`, and generate `reports/figures/08_recommender_model_comparison.png`.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)

    # 1. Fit 3 Baselines
    b1_pop = PopularOverallRecommender().fit_from_duckdb(con)
    b2_fav = FavouriteCategoryPopularRecommender().fit_from_duckdb(con)
    b3_trend = Trending7DayRecommender().fit_from_duckdb(con)

    # 2. Load sparse interaction matrix & embeddings for CF, Content, and Hybrid
    (
        catalogue_df,
        user_to_row,
        user_ids,
        item_to_col,
        col_to_item,
        R_csr,
        user_purchased,
    ) = _load_sparse_interaction_data(con)

    emb_path = settings.models_dir / "item_text_embeddings.npy"
    item_embeddings = np.load(emb_path)

    cf_item = ItemToItemCFRecommender(k_neighbors=80, shrinkage=5.0, revisit_boost=0.35)
    cf_item.fit_from_sparse(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
    )

    cf_als = ImplicitALSRecommender(
        factors=96, regularization=0.10, alpha=30.0, iterations=10, revisit_boost=0.25
    )
    cf_als.fit_from_sparse(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
    )

    content_rec = ContentBasedRecommender(
        category_bonus=0.15, price_affinity_bonus=0.05, revisit_boost=0.25
    )
    content_rec.fit_from_sparse_and_embeddings(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
        item_embeddings=item_embeddings,
    )

    hybrid_rec = HybridTwoTowerRecommender(
        item_cf=cf_item,
        als_model=cf_als,
        content_model=content_rec,
        w_item_cf=0.65,
        w_als=0.23,
        w_content=0.07,
        w_features=0.05,
    )

    # 3. Prepare evaluation ground truth & novelty table
    warm_gt = load_test_ground_truth(con, require_warm_user=True, max_eval_users=max_eval_users)
    novelty_map = _compute_item_self_information_bits(con, all_product_ids=col_to_item)

    cold_user_df = con.execute(
        f"""
        WITH top_cold_users AS (
            SELECT
                user_id,
                -- deterministic simulated onboarding answer: the category of the user's first event
                ARG_MIN(category, event_timestamp) AS onboarding_category,
                COUNT(DISTINCT product_id) AS n_items
            FROM cold_start_test
            WHERE is_cold_user = TRUE
            GROUP BY user_id
            ORDER BY n_items DESC, user_id
            LIMIT {int(max_cold_users)}
        )
        SELECT
            c.user_id,
            c.product_id,
            u.onboarding_category
        FROM cold_start_test c
        JOIN top_cold_users u ON c.user_id = u.user_id
        WHERE c.is_cold_user = TRUE;
        """
    ).df()
    cold_user_gt = cold_user_df.groupby("user_id")["product_id"].apply(set).to_dict()
    onboarding_map = (
        cold_user_df.drop_duplicates("user_id")
        .set_index("user_id")["onboarding_category"]
        .astype(str)
        .to_dict()
    )
    hybrid_rec.set_cold_user_context(onboarding_map)

    cold_item_df = con.execute(
        """
        SELECT user_id, product_id
        FROM cold_start_test
        WHERE is_cold_item = TRUE
          AND user_id IN (SELECT DISTINCT user_id FROM train_interactions);
        """
    ).df()
    cold_item_warm_user_gt = cold_item_df.groupby("user_id")["product_id"].apply(set).to_dict()
    all_cold_items = (
        con.execute("SELECT DISTINCT product_id FROM cold_start_test WHERE is_cold_item = TRUE")
        .df()["product_id"]
        .astype(str)
        .tolist()
    )
    cold_item_cols = np.array(
        [item_to_col[pid] for pid in all_cold_items if pid in item_to_col], dtype=int
    )
    # Neural two-tower: epochs and serving knobs chosen on the validation window, never on test
    val_gt = load_val_ground_truth(con, max_eval_users=2000)
    val_cold_gt, val_cold_cat = load_val_cold_users(con, max_users=2000)
    con.close()
    neural_tt = TwoTowerRecommender()
    neural_tt.fit_from_sparse(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
        item_embeddings=item_embeddings,
        val_ground_truth=val_gt,
    )
    neural_tt.tune_cold_start(val_cold_gt, val_cold_cat)  # new-user settings from validation only
    neural_tt.set_cold_user_context(onboarding_map)  # same simulated onboarding answers the hybrid blend gets

    # 4. Evaluate all 8 models
    model_specs: list[tuple[str, BaseRecommender, str]] = [
        ("most_popular", b1_pop, "Baseline"),
        ("favourite_category_popular", b2_fav, "Baseline"),
        ("recently_trending_7d", b3_trend, "Baseline"),
        ("item_to_item_cf", cf_item, "Collaborative Filtering"),
        ("implicit_als", cf_als, "Collaborative Filtering"),
        ("content_based", content_rec, "Content-Based"),
        ("hybrid_two_tower", hybrid_rec, "Hybrid Blend"),
        ("neural_two_tower", neural_tt, "Neural Two-Tower (PyTorch)"),
    ]

    rows: list[FullModelEvalRow] = []
    models_dict: dict[str, BaseRecommender] = {}
    for key, mdl, family in model_specs:
        models_dict[key] = mdl
        row = evaluate_single_model_full(
            model=mdl,
            model_family=family,
            warm_gt=warm_gt,
            cold_user_gt=cold_user_gt,
            cold_item_warm_user_gt=cold_item_warm_user_gt,
            cold_item_cols=cold_item_cols,
            item_to_col=item_to_col,
            item_embeddings=item_embeddings,
            novelty_map=novelty_map,
            k=k,
            exclude_seen=False,
        )
        rows.append(row)

    comparison_df = pd.DataFrame([asdict(r) for r in rows])

    # Save CSV & figure
    csv_out = settings.reports_dir / "day2_model_comparison.csv"
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(csv_out, index=False)

    fig_out = settings.figures_dir / "08_recommender_model_comparison.png"
    plot_recommender_comparison_chart(comparison_df, output_path=fig_out)

    return comparison_df, models_dict, fig_out
