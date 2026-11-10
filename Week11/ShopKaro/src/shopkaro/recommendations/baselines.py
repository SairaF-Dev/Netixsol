"""
Day 2 — Task 1: Baseline Recommenders & Ranking Evaluation Metrics.

Implements and evaluates the three foundational baselines required by ShopKaro:
1. `PopularOverallRecommender`: Most popular overall across the training set.
2. `FavouriteCategoryPopularRecommender`: Most popular within each user's favourite category.
3. `Trending7DayRecommender`: Recently trending products over the final 7 days of training.

All advanced models in Tasks 2 & 3 must beat these baselines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from shopkaro.config.settings import settings


@dataclass
class BaselineEvalMetrics:
    """Offline evaluation metrics for a recommender model at top-K."""

    model_name: str
    k: int
    evaluated_users: int
    precision_at_k: float
    recall_at_k: float
    ndcg_at_k: float
    map_at_k: float
    hit_rate_at_k: float
    catalogue_coverage_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "k": self.k,
            "evaluated_users": self.evaluated_users,
            "precision_at_10": self.precision_at_k,
            "recall_at_10": self.recall_at_k,
            "ndcg_at_10": self.ndcg_at_k,
            "map_at_10": self.map_at_k,
            "hit_rate_at_10": self.hit_rate_at_k,
            "catalogue_coverage_pct": self.catalogue_coverage_pct,
        }


class BaseRecommender(ABC):
    """Unified base interface for all ShopKaro recommendation models."""

    name: str = "BaseRecommender"

    def __init__(self) -> None:
        self.item_metadata: dict[str, dict[str, Any]] = {}
        self.user_seen_items: dict[str, set[str]] = {}
        self.in_stock_ids: set[str] = set()
        self.total_catalogue_size: int = 0

    def _index_catalogue_and_seen(
        self,
        catalogue_df: pd.DataFrame,
        user_seen_df: pd.DataFrame | None = None,
    ) -> None:
        """Cache product metadata, stock flags, and user historical training items."""
        self.total_catalogue_size = len(catalogue_df)
        self.item_metadata = {}
        self.in_stock_ids = set()

        for rec in catalogue_df.to_dict("records"):
            pid = str(rec["product_id"])
            in_stock = bool(rec.get("in_stock", True))
            if in_stock:
                self.in_stock_ids.add(pid)
            self.item_metadata[pid] = {
                "product_id": pid,
                "title": rec.get("title", ""),
                "category": rec.get("category", ""),
                "brand": rec.get("brand", ""),
                "price_pkr": float(rec.get("price_pkr", 0.0)),
                "in_stock": in_stock,
            }

        if user_seen_df is not None and not user_seen_df.empty:
            self.user_seen_items = (
                user_seen_df.groupby("user_id")["product_id"]
                .apply(set)
                .to_dict()
            )

    @abstractmethod
    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        """Return a list of `(product_id, score)` tuples of length `k`."""

    def recommend(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[dict[str, Any]]:
        """Return enriched product dictionaries with rank, score, title, brand, and PKR price."""
        scored = self.recommend_ids(
            user_id=user_id,
            k=k,
            exclude_seen=exclude_seen,
            only_in_stock=only_in_stock,
        )
        results: list[dict[str, Any]] = []
        for rank, (pid, score) in enumerate(scored, start=1):
            meta = self.item_metadata.get(pid, {"product_id": pid})
            results.append(
                {
                    "rank": rank,
                    "product_id": pid,
                    "score": round(float(score), 4),
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "brand": meta.get("brand", ""),
                    "price_pkr": meta.get("price_pkr", 0.0),
                    "in_stock": meta.get("in_stock", True),
                    "model": self.name,
                }
            )
        return results

    def recommend_batch(
        self,
        user_ids: list[str],
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> dict[str, list[str]]:
        """Generate top-K product_id lists for a batch of users."""
        return {
            uid: [
                pid
                for pid, _ in self.recommend_ids(
                    user_id=uid,
                    k=k,
                    exclude_seen=exclude_seen,
                    only_in_stock=only_in_stock,
                )
            ]
            for uid in user_ids
        }


class PopularOverallRecommender(BaseRecommender):
    """
    Baseline 1: Most Popular Overall.
    Ranks products by log-dampened implicit feedback score across all training users:
        PopScore(i) = sum_{u} log(1 + sum_{e in E(u, i)} implicit_weight(e))
    """

    name = "1. Most Popular Overall"

    def __init__(self) -> None:
        super().__init__()
        self.ranked_items: list[tuple[str, float]] = []

    def fit_from_duckdb(self, con: duckdb.DuckDBPyConnection) -> PopularOverallRecommender:
        """Fit popularity scores directly from `train_interactions` in DuckDB."""
        catalogue_df = con.execute(
            "SELECT product_id, title, category, brand, price_pkr, in_stock FROM product_catalogue"
        ).df()
        self._index_catalogue_and_seen(catalogue_df)

        pop_df = con.execute(
            """
            WITH user_item_weights AS (
                SELECT
                    user_id,
                    product_id,
                    LN(1.0 + SUM(implicit_weight)) AS log_user_weight
                FROM train_interactions
                GROUP BY user_id, product_id
            )
            SELECT
                product_id,
                SUM(log_user_weight) AS pop_score
            FROM user_item_weights
            GROUP BY product_id
            ORDER BY pop_score DESC;
            """
        ).df()

        max_score = float(pop_df["pop_score"].max()) if not pop_df.empty else 1.0
        self.ranked_items = [
            (str(pid), float(sc) / max(max_score, 1e-9))
            for pid, sc in zip(pop_df["product_id"], pop_df["pop_score"])
        ]
        return self

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        seen = self.user_seen_items.get(user_id, set()) if exclude_seen else set()
        out: list[tuple[str, float]] = []
        for pid, score in self.ranked_items:
            if only_in_stock and pid not in self.in_stock_ids:
                continue
            if exclude_seen and pid in seen:
                continue
            out.append((pid, score))
            if len(out) >= k:
                break
        return out


class FavouriteCategoryPopularRecommender(BaseRecommender):
    """
    Baseline 2: Most Popular in the User's Favourite Category.
    Personalizes popularity at the category level:
    - Computes top popular products within each of the 11 Pakistani categories.
    - Identifies each user's top 1 and top 2 categories from `train_interactions`.
    - Recommends top popular items from the user's favourite category (with fallback to global popular
      for unseen cold-start users).
    """

    name = "2. Most Popular in User's Favourite Category"

    def __init__(self) -> None:
        super().__init__()
        self.category_rankings: dict[str, list[tuple[str, float]]] = {}
        self.user_top_categories: dict[str, list[tuple[str, float]]] = {}
        self.global_fallback: list[tuple[str, float]] = []
        self._cat_combo_cache: dict[tuple[Any, ...], list[tuple[str, float]]] = {}

    def fit_from_duckdb(
        self, con: duckdb.DuckDBPyConnection
    ) -> FavouriteCategoryPopularRecommender:
        """Fit category-level item rankings and user category affinities from `train_interactions`."""
        catalogue_df = con.execute(
            "SELECT product_id, title, category, brand, price_pkr, in_stock FROM product_catalogue"
        ).df()
        self._index_catalogue_and_seen(catalogue_df)

        # 1. Category-level popularity rankings
        cat_pop_df = con.execute(
            """
            WITH user_item_weights AS (
                SELECT
                    user_id,
                    product_id,
                    category,
                    LN(1.0 + SUM(implicit_weight)) AS log_user_weight
                FROM train_interactions
                GROUP BY user_id, product_id, category
            )
            SELECT
                category,
                product_id,
                SUM(log_user_weight) AS cat_pop_score
            FROM user_item_weights
            GROUP BY category, product_id
            ORDER BY category, cat_pop_score DESC;
            """
        ).df()

        self.category_rankings = {}
        for cat, grp in cat_pop_df.groupby("category"):
            max_s = float(grp["cat_pop_score"].max()) if not grp.empty else 1.0
            self.category_rankings[str(cat)] = [
                (str(r["product_id"]), float(r["cat_pop_score"]) / max(max_s, 1e-9))
                for _, r in grp.iterrows()
            ]

        # Global fallback for cold-start users
        glob_df = cat_pop_df.sort_values("cat_pop_score", ascending=False)
        max_g = float(glob_df["cat_pop_score"].max()) if not glob_df.empty else 1.0
        self.global_fallback = [
            (str(r["product_id"]), float(r["cat_pop_score"]) / max(max_g, 1e-9))
            for _, r in glob_df.head(200).iterrows()
        ]

        # 2. User top-2 categories in `train_interactions` (computed & normalized in DuckDB)
        user_cats_df = con.execute(
            """
            WITH ranked_cats AS (
                SELECT
                    user_id,
                    category,
                    SUM(implicit_weight) AS cat_weight,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id
                        ORDER BY SUM(implicit_weight) DESC, COUNT(*) DESC
                    ) AS rn
                FROM train_interactions
                GROUP BY user_id, category
            ),
            top2 AS (
                SELECT
                    user_id,
                    category,
                    cat_weight,
                    SUM(cat_weight) OVER (PARTITION BY user_id) AS total_w,
                    rn
                FROM ranked_cats
                WHERE rn <= 2
            )
            SELECT
                user_id,
                category,
                cat_weight / GREATEST(total_w, 1e-9) AS cat_share
            FROM top2
            ORDER BY user_id, rn;
            """
        ).df()

        self.user_top_categories = {}
        for uid, cat, share in zip(
            user_cats_df["user_id"],
            user_cats_df["category"],
            user_cats_df["cat_share"],
        ):
            self.user_top_categories.setdefault(str(uid), []).append((str(cat), float(share)))

        return self

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        seen = self.user_seen_items.get(user_id, set()) if exclude_seen else set()
        user_cats = self.user_top_categories.get(user_id)

        if not user_cats:
            # Cold-start user fallback
            out: list[tuple[str, float]] = []
            for pid, score in self.global_fallback:
                if only_in_stock and pid not in self.in_stock_ids:
                    continue
                if exclude_seen and pid in seen:
                    continue
                out.append((pid, score))
                if len(out) >= k:
                    break
            return out

        # Allocate slots across user's primary (and optional secondary) category
        cache_key = (
            tuple((c, round(s, 1)) for c, s in user_cats),
            k,
            only_in_stock,
        )
        if not exclude_seen and cache_key in self._cat_combo_cache:
            return self._cat_combo_cache[cache_key]

        out = []
        picked: set[str] = set()
        for idx, (cat_name, cat_share) in enumerate(user_cats):
            slot_target = k if len(user_cats) == 1 else (max(int(round(k * cat_share)), 7) if idx == 0 else k)
            candidates = self.category_rankings.get(cat_name, [])
            for pid, score in candidates:
                if pid in picked:
                    continue
                if only_in_stock and pid not in self.in_stock_ids:
                    continue
                if exclude_seen and pid in seen:
                    continue
                out.append((pid, score * (1.0 if idx == 0 else 0.85)))
                picked.add(pid)
                if len(out) >= slot_target or len(out) >= k:
                    break
            if len(out) >= k:
                break

        # Top up from global fallback if category had fewer than k items
        if len(out) < k:
            for pid, score in self.global_fallback:
                if pid in picked:
                    continue
                if only_in_stock and pid not in self.in_stock_ids:
                    continue
                if exclude_seen and pid in seen:
                    continue
                out.append((pid, score * 0.5))
                picked.add(pid)
                if len(out) >= k:
                    break

        res = out[:k]
        if not exclude_seen:
            self._cat_combo_cache[cache_key] = res
        return res


class Trending7DayRecommender(BaseRecommender):
    """
    Baseline 3: Recently Trending (Last 7 Days).
    Scores items by their interaction velocity in the final 7 days of `train_interactions`
    weighted by their surge momentum compared to the prior training days:
        TrendScore(i) = Volume_7d(i) * (1 + DailyRate_7d(i) / (DailyRate_Prior(i) + 1.0))
    """

    name = "3. Recently Trending (Last 7 Days)"

    def __init__(self) -> None:
        super().__init__()
        self.trending_items: list[tuple[str, float]] = []
        self.window_start: str = ""
        self.window_end: str = ""

    def fit_from_duckdb(self, con: duckdb.DuckDBPyConnection) -> Trending7DayRecommender:
        """Compute 7-day trending velocity scores at the end of `train_interactions`."""
        catalogue_df = con.execute(
            "SELECT product_id, title, category, brand, price_pkr, in_stock FROM product_catalogue"
        ).df()
        self._index_catalogue_and_seen(catalogue_df)

        bounds = con.execute(
            """
            SELECT
                CAST(MIN(event_timestamp) AS VARCHAR) AS min_ts,
                CAST(MAX(event_timestamp) AS VARCHAR) AS max_ts,
                CAST(MAX(event_timestamp) - INTERVAL '7 days' AS VARCHAR) AS cutoff_7d,
                GREATEST(DATE_DIFF('day', MIN(event_timestamp), MAX(event_timestamp)) - 7, 1) AS prior_days
            FROM train_interactions;
            """
        ).fetchall()[0]

        self.window_end = str(bounds[1])
        self.window_start = str(bounds[2])
        prior_days = float(bounds[3])

        trend_df = con.execute(
            f"""
            WITH item_windows AS (
                SELECT
                    product_id,
                    SUM(
                        CASE
                            WHEN CAST(event_timestamp AS TIMESTAMP) >= TIMESTAMP '{self.window_start}'
                            THEN implicit_weight ELSE 0.0
                        END
                    ) AS weight_7d,
                    SUM(
                        CASE
                            WHEN CAST(event_timestamp AS TIMESTAMP) < TIMESTAMP '{self.window_start}'
                            THEN implicit_weight ELSE 0.0
                        END
                    ) AS weight_prior
                FROM train_interactions
                GROUP BY product_id
            )
            SELECT
                product_id,
                weight_7d,
                weight_prior,
                weight_7d * (
                    1.0 + (weight_7d / 7.0) / ((weight_prior / {prior_days}) + 1.0)
                ) AS trend_score
            FROM item_windows
            WHERE weight_7d > 0
            ORDER BY trend_score DESC;
            """
        ).df()

        max_t = float(trend_df["trend_score"].max()) if not trend_df.empty else 1.0
        self.trending_items = [
            (str(r["product_id"]), float(r["trend_score"]) / max(max_t, 1e-9))
            for _, r in trend_df.iterrows()
        ]
        return self

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        seen = self.user_seen_items.get(user_id, set()) if exclude_seen else set()
        out: list[tuple[str, float]] = []
        for pid, score in self.trending_items:
            if only_in_stock and pid not in self.in_stock_ids:
                continue
            if exclude_seen and pid in seen:
                continue
            out.append((pid, score))
            if len(out) >= k:
                break
        return out


# ---------------------------------------------------------------------------
# Offline Ranking Evaluator for Top-K Recommendations
# ---------------------------------------------------------------------------
def evaluate_recommender_at_k(
    model: BaseRecommender,
    ground_truth: dict[str, set[str]],
    k: int = 10,
    exclude_seen: bool = False,
    only_in_stock: bool = True,
) -> BaselineEvalMetrics:
    """
    Evaluate a recommender model on a dictionary of `{user_id: set(true_test_product_ids)}`.
    Computes:
    - Precision@K
    - Recall@K
    - NDCG@K
    - MAP@K
    - HitRate@K
    - Catalogue Coverage (%)
    """
    user_ids = list(ground_truth.keys())
    preds_by_user = model.recommend_batch(
        user_ids=user_ids,
        k=k,
        exclude_seen=exclude_seen,
        only_in_stock=only_in_stock,
    )

    precisions: list[float] = []
    recalls: list[float] = []
    ndcgs: list[float] = []
    aps: list[float] = []
    hits: list[float] = []
    recommended_items_union: set[str] = set()

    # Precompute discount denominators 1 / log2(rank + 1) for ranks 1..k
    discounts = 1.0 / np.log2(np.arange(2, k + 2))

    for uid in user_ids:
        true_items = ground_truth[uid]
        if not true_items:
            continue
        recs = preds_by_user.get(uid, [])[:k]
        recommended_items_union.update(recs)

        hit_vec = np.array([1.0 if pid in true_items else 0.0 for pid in recs], dtype=float)
        if len(hit_vec) < k:
            hit_vec = np.pad(hit_vec, (0, k - len(hit_vec)), constant_values=0.0)

        n_hits = float(hit_vec.sum())
        hits.append(1.0 if n_hits > 0 else 0.0)
        precisions.append(n_hits / k)
        recalls.append(n_hits / len(true_items))

        # DCG@K and IDCG@K
        dcg = float(np.sum(hit_vec * discounts))
        ideal_len = min(len(true_items), k)
        idcg = float(np.sum(discounts[:ideal_len]))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

        # Average Precision (AP@K)
        if n_hits > 0:
            cum_hits = np.cumsum(hit_vec)
            ranks = np.arange(1, k + 1, dtype=float)
            ap = float(np.sum((cum_hits / ranks) * hit_vec) / min(len(true_items), k))
            aps.append(ap)
        else:
            aps.append(0.0)

    cat_size = max(model.total_catalogue_size, 1)
    coverage_pct = (len(recommended_items_union) / cat_size) * 100.0

    return BaselineEvalMetrics(
        model_name=model.name,
        k=k,
        evaluated_users=len(precisions),
        precision_at_k=round(float(np.mean(precisions)) if precisions else 0.0, 5),
        recall_at_k=round(float(np.mean(recalls)) if recalls else 0.0, 5),
        ndcg_at_k=round(float(np.mean(ndcgs)) if ndcgs else 0.0, 5),
        map_at_k=round(float(np.mean(aps)) if aps else 0.0, 5),
        hit_rate_at_k=round(float(np.mean(hits)) if hits else 0.0, 5),
        catalogue_coverage_pct=round(coverage_pct, 3),
    )


def load_test_ground_truth(
    con: duckdb.DuckDBPyConnection,
    require_warm_user: bool = True,
    max_eval_users: int = 5000,
) -> dict[str, set[str]]:
    """
    Load ground-truth `{user_id: set(product_ids)}` from `test_interactions`.
    By default evaluates on warm users (users present in both `train_interactions` and
    `test_interactions`) so personalized models and baselines are compared on the same cohort.
    """
    warm_clause = (
        "WHERE user_id IN (SELECT DISTINCT user_id FROM train_interactions)"
        if require_warm_user
        else ""
    )
    df = con.execute(
        f"""
        WITH target_users AS (
            SELECT
                user_id,
                COUNT(DISTINCT product_id) AS n_test_items,
                SUM(implicit_weight) AS total_weight
            FROM test_interactions
            {warm_clause}
            GROUP BY user_id
            ORDER BY total_weight DESC, n_test_items DESC, user_id
            LIMIT {int(max_eval_users)}
        )
        SELECT
            t.user_id,
            t.product_id
        FROM test_interactions t
        JOIN target_users u ON t.user_id = u.user_id;
        """
    ).df()

    return df.groupby("user_id")["product_id"].apply(set).to_dict()


def run_day2_task1_baselines(
    db_path: Path | None = None,
    k: int = 10,
    max_eval_users: int = 5000,
) -> tuple[list[BaselineEvalMetrics], dict[str, BaseRecommender]]:
    """Fit and evaluate all 3 Day 2 Task 1 baseline recommenders."""
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)

    pop_model = PopularOverallRecommender().fit_from_duckdb(con)
    cat_model = FavouriteCategoryPopularRecommender().fit_from_duckdb(con)
    trend_model = Trending7DayRecommender().fit_from_duckdb(con)

    ground_truth = load_test_ground_truth(
        con, require_warm_user=True, max_eval_users=max_eval_users
    )
    con.close()

    models: dict[str, BaseRecommender] = {
        "popular_overall": pop_model,
        "favourite_category": cat_model,
        "trending_7d": trend_model,
    }

    metrics = [
        evaluate_recommender_at_k(m, ground_truth=ground_truth, k=k)
        for m in models.values()
    ]
    return metrics, models
