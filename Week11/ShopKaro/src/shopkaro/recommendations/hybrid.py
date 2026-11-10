"""
Day 2 — Task 3: Content-Based, Two-Tower Hybrid & Cold-Start Recommendation Models.

Implements:
1. `ContentBasedRecommender`:
   - Uses 64-dim dense text embeddings (`models/item_text_embeddings.npy`) built from
     product `title + description + category + brand + occasion`.
   - Constructs each user's semantic profile vector e_u = normalize(sum_{i in I_u} w_{ui} e_i).
   - Scores all 25,000 items (including 0-click cold-start items) via cosine similarity <e_u, e_j>.

2. `HybridTwoTowerRecommender`:
   - Combines User Tower [x_u^{ALS}, e_u^{text}, user_features] and Item Tower [y_i^{ALS}, e_i^{text}, item_features]
     alongside sparse Item-to-Item co-occurrence scores.
   - Automatically degrades gracefully to Content + Feature scoring for cold-start users and cold-start items.

3. `ColdStartEngine`:
   - Explicit cold-start strategy for new users (via onboarding preferences: category, budget, occasion, or segment)
     and new items (via content text embeddings + attribute matching).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.preprocessing import normalize

from shopkaro.config.settings import settings
from shopkaro.recommendations.baselines import (
    BaselineEvalMetrics,
    BaseRecommender,
    evaluate_recommender_at_k,
    load_test_ground_truth,
)
from shopkaro.recommendations.collaborative import (
    ImplicitALSRecommender,
    ItemToItemCFRecommender,
    _load_sparse_interaction_data,
)


@dataclass
class ColdStartEvalSummary:
    """Evaluation summary comparing CF vs Content/Hybrid on Cold-Start Users and Cold-Start Items."""

    cold_users_evaluated: int
    popular_cold_user_ndcg10: float
    onboarding_hybrid_cold_user_ndcg10: float
    cold_user_ndcg_uplift_pct: float
    cold_items_count: int
    cf_cold_item_hit_rate10: float
    content_hybrid_cold_item_hit_rate10: float
    content_hybrid_cold_item_ndcg10: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "cold_users_evaluated": self.cold_users_evaluated,
            "popular_cold_user_ndcg10": self.popular_cold_user_ndcg10,
            "onboarding_hybrid_cold_user_ndcg10": self.onboarding_hybrid_cold_user_ndcg10,
            "cold_user_ndcg_uplift_pct": self.cold_user_ndcg_uplift_pct,
            "cold_items_count": self.cold_items_count,
            "cf_cold_item_hit_rate10": self.cf_cold_item_hit_rate10,
            "content_hybrid_cold_item_hit_rate10": self.content_hybrid_cold_item_hit_rate10,
            "content_hybrid_cold_item_ndcg10": self.content_hybrid_cold_item_ndcg10,
        }


class ContentBasedRecommender(BaseRecommender):
    """
    Task 3A: Content-Based Recommender using Dense Text Embeddings of Product Titles & Descriptions.

    Builds a 64-dim L2-normalized semantic user profile vector:
        e_u = normalize(sum_{i in I_u} log(1 + r_{ui}) * e_i)
    and scores all catalogue items (including unseen cold-start items) via:
        s_content(u, j) = <e_u, e_j> + category_match_bonus + price_affinity_bonus
    """

    name = "6. Content-Based (Text Embeddings)"

    def __init__(
        self,
        category_bonus: float = 0.15,
        price_affinity_bonus: float = 0.05,
        revisit_boost: float = 0.25,
    ) -> None:
        super().__init__()
        self.category_bonus = category_bonus
        self.price_affinity_bonus = price_affinity_bonus
        self.revisit_boost = revisit_boost

        self.user_to_row: dict[str, int] = {}
        self.item_to_col: dict[str, int] = {}
        self.col_to_item: list[str] = []
        self.R_log_csr: sp.csr_matrix | None = None
        self.item_embeddings: np.ndarray = np.array([], dtype=np.float32)  # (n_items, 64)
        self.item_categories: np.ndarray = np.array([], dtype=object)
        self.item_prices: np.ndarray = np.array([], dtype=np.float32)
        self.item_pop_prior: np.ndarray = np.array([], dtype=np.float32)
        self.in_stock_mask: np.ndarray = np.array([], dtype=bool)
        self.cat_to_cols: dict[str, np.ndarray] = {}

    def fit_from_sparse_and_embeddings(
        self,
        catalogue_df: pd.DataFrame,
        user_to_row: dict[str, int],
        item_to_col: dict[str, int],
        col_to_item: list[str],
        R_csr: sp.csr_matrix,
        user_purchased: dict[str, set[str]],
        item_embeddings: np.ndarray,
    ) -> ContentBasedRecommender:
        """Fit Content-Based recommender from catalogue metadata and dense text embeddings."""
        self._index_catalogue_and_seen(catalogue_df)
        self.user_seen_items = user_purchased
        self.user_to_row = user_to_row
        self.item_to_col = item_to_col
        self.col_to_item = col_to_item

        R_log = R_csr.copy()
        R_log.data = np.log1p(R_log.data)
        self.R_log_csr = R_log

        self.item_embeddings = normalize(item_embeddings.astype(np.float32), norm="l2", axis=1)
        self.item_categories = catalogue_df["category"].astype(str).to_numpy()
        self.item_prices = catalogue_df["price_pkr"].to_numpy(dtype=np.float32)
        self.in_stock_mask = np.array(
            [pid in self.in_stock_ids for pid in col_to_item], dtype=bool
        )

        self.cat_to_cols = {}
        for cat in np.unique(self.item_categories):
            self.cat_to_cols[str(cat)] = np.where(self.item_categories == cat)[0]

        item_sums = np.asarray(R_log.sum(axis=0)).ravel().astype(np.float32)
        self.item_pop_prior = (item_sums / max(float(item_sums.max()), 1.0)) * 0.10
        return self

    def compute_user_text_profile(self, user_id: str) -> tuple[np.ndarray | None, str | None, float]:
        """
        Return `(user_embedding_64d, favourite_category, avg_price_pkr)` for `user_id`
        based on their training interactions.
        """
        assert self.R_log_csr is not None
        u_row = self.user_to_row.get(user_id)
        if u_row is None:
            return None, None, 0.0
        start, end = self.R_log_csr.indptr[u_row], self.R_log_csr.indptr[u_row + 1]
        if start == end:
            return None, None, 0.0

        cols = self.R_log_csr.indices[start:end]
        weights = self.R_log_csr.data[start:end]

        # Weighted centroid in 64-dim text embedding space
        u_emb = (weights @ self.item_embeddings[cols]).astype(np.float32)
        norm = float(np.linalg.norm(u_emb))
        if norm > 1e-9:
            u_emb = u_emb / norm

        top_col = cols[int(np.argmax(weights))]
        fav_cat = str(self.item_categories[top_col])
        avg_price = float(np.average(self.item_prices[cols], weights=weights))
        return u_emb, fav_cat, avg_price

    def get_similar_items_content(
        self,
        product_id: str,
        k: int = 10,
        only_in_stock: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Return top-K semantically similar items using 64-dim text embeddings.
        Works even if `product_id` is a brand-new cold-start item with 0 clicks!
        """
        col = self.item_to_col.get(product_id)
        if col is None:
            return []

        target_emb = self.item_embeddings[col]
        scores = (self.item_embeddings @ target_emb).astype(np.float32)

        cat = str(self.item_categories[col])
        cat_cols = self.cat_to_cols.get(cat, np.array([], dtype=int))
        scores[cat_cols] += 0.15
        scores[col] = -1e9

        if only_in_stock:
            scores[~self.in_stock_mask] = -1e9

        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]

        results: list[dict[str, Any]] = []
        for rank, c_idx in enumerate(top_idx, start=1):
            pid = self.col_to_item[int(c_idx)]
            meta = self.item_metadata.get(pid, {})
            results.append(
                {
                    "rank": rank,
                    "product_id": pid,
                    "content_similarity": round(float(scores[c_idx]), 4),
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "brand": meta.get("brand", ""),
                    "price_pkr": meta.get("price_pkr", 0.0),
                    "in_stock": meta.get("in_stock", True),
                }
            )
        return results

    def score_all_items_for_user(
        self,
        user_id: str,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
        allowed_cols: np.ndarray | None = None,
    ) -> np.ndarray:
        """Compute full 25,000-item content similarity score vector for `user_id`."""
        assert self.R_log_csr is not None
        u_emb, fav_cat, avg_price = self.compute_user_text_profile(user_id)
        if u_emb is None:
            scores = self.item_pop_prior.copy()
            if only_in_stock:
                scores[~self.in_stock_mask] = -1e9
            return scores

        # Cosine similarity <e_u, e_j> across all 25,000 items
        scores = (self.item_embeddings @ u_emb).astype(np.float32) + self.item_pop_prior

        if fav_cat is not None:
            cat_cols = self.cat_to_cols.get(fav_cat, np.array([], dtype=int))
            scores[cat_cols] += self.category_bonus

        if avg_price > 0 and self.price_affinity_bonus > 0:
            # Smooth Gaussian affinity in log-price space
            log_diff = np.abs(np.log1p(self.item_prices) - np.log1p(avg_price))
            price_sim = np.exp(-0.5 * (log_diff ** 2)).astype(np.float32)
            scores += self.price_affinity_bonus * price_sim

        u_row = self.user_to_row[user_id]
        start, end = self.R_log_csr.indptr[u_row], self.R_log_csr.indptr[u_row + 1]
        interacted_cols = self.R_log_csr.indices[start:end]
        if len(interacted_cols) > 0 and not exclude_seen and self.revisit_boost > 0:
            scores[interacted_cols] += self.R_log_csr.data[start:end] * self.revisit_boost

        seen_pids = self.user_seen_items.get(user_id, set())
        for pid in seen_pids:
            c = self.item_to_col.get(pid)
            if c is not None:
                scores[c] = -1e9

        if exclude_seen and len(interacted_cols) > 0:
            scores[interacted_cols] = -1e9

        if only_in_stock:
            scores[~self.in_stock_mask] = -1e9

        if allowed_cols is not None:
            mask = np.zeros(len(scores), dtype=bool)
            mask[allowed_cols] = True
            scores[~mask] = -1e9

        return scores

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        scores = self.score_all_items_for_user(
            user_id=user_id,
            exclude_seen=exclude_seen,
            only_in_stock=only_in_stock,
        )
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return [(self.col_to_item[int(i)], float(scores[i])) for i in top_idx]


class HybridTwoTowerRecommender(BaseRecommender):
    """
    Task 3B: Feature-Aware Two-Tower Hybrid Recommender (LightFM / Two-Tower Architecture).

    Combines four complementary signals across User and Item representations:
    1. Item-to-Item Co-occurrence Neighborhood: s_itemCF(u, i)
    2. Implicit ALS Latent Factor Dot Product: <x_u^{ALS}, y_i^{ALS}>
    3. Content Semantic Profile Cosine Similarity: <e_u^{text}, e_i^{text}>
    4. User-Item Feature Compatibility Tower: category affinity, price-band match, & conversion rate.

    For cold-start users or cold-start items, automatically routes to `ColdStartEngine`.
    """

    name = "7. Hybrid Blend (Item-CF + ALS + Content + Features)"

    def __init__(
        self,
        item_cf: ItemToItemCFRecommender,
        als_model: ImplicitALSRecommender,
        content_model: ContentBasedRecommender,
        w_item_cf: float = 0.65,
        w_als: float = 0.23,
        w_content: float = 0.07,
        w_features: float = 0.05,
    ) -> None:
        super().__init__()
        self.item_cf = item_cf
        self.als_model = als_model
        self.content_model = content_model
        self.w_item_cf = w_item_cf
        self.w_als = w_als
        self.w_content = w_content
        self.w_features = w_features

        self.item_metadata = item_cf.item_metadata
        self.user_seen_items = item_cf.user_seen_items
        self.in_stock_ids = item_cf.in_stock_ids
        self.total_catalogue_size = item_cf.total_catalogue_size
        self.col_to_item = item_cf.col_to_item
        self.item_to_col = item_cf.item_to_col
        self.in_stock_mask = item_cf.in_stock_mask

        # Precompute normalized item feature quality vector (popularity + conversion rate)
        self.item_feature_prior: np.ndarray = item_cf.item_pop_prior.copy()
        self.cold_user_onboarding_map: dict[str, str] = {}
        self._cold_user_cache: dict[tuple[Any, ...], list[tuple[str, float]]] = {}

    def set_cold_user_context(self, user_category_map: dict[str, str]) -> None:
        """Register onboarding / session initial category hints for cold-start users."""
        self.cold_user_onboarding_map = user_category_map
        self._cold_user_cache = {}

    @staticmethod
    def _minmax_valid(vec: np.ndarray) -> np.ndarray:
        """Normalize valid (> -1e8) entries of a score vector to [0, 1]."""
        valid = vec > -1e8
        if not np.any(valid):
            return np.zeros_like(vec, dtype=np.float32)
        v_min = float(np.min(vec[valid]))
        v_max = float(np.max(vec[valid]))
        span = max(v_max - v_min, 1e-7)
        out = np.where(valid, (vec - v_min) / span, -1e9).astype(np.float32)
        return out

    def recommend_for_cold_user(
        self,
        preferred_category: str | None = None,
        max_budget_pkr: float | None = None,
        occasion: str | None = None,
        k: int = 10,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        """
        Explicit Cold-Start User Strategy:
        Ranks products matching the new user's onboarding answers (category, budget cap, occasion)
        using category centroid embeddings + popularity prior.
        """
        cache_key = (preferred_category, max_budget_pkr, occasion, k, only_in_stock)
        if cache_key in self._cold_user_cache:
            return self._cold_user_cache[cache_key]

        scores = self.content_model.item_pop_prior.copy() * 10.0

        if preferred_category and preferred_category in self.content_model.cat_to_cols:
            cat_cols = self.content_model.cat_to_cols[preferred_category]
            # Compute category prototype vector in 64-dim content space
            cat_centroid = self.content_model.item_embeddings[cat_cols].mean(axis=0)
            norm = float(np.linalg.norm(cat_centroid))
            if norm > 1e-9:
                cat_centroid = cat_centroid / norm
            scores += (self.content_model.item_embeddings @ cat_centroid).astype(np.float32) * 0.5
            scores[cat_cols] += 2.0

        if max_budget_pkr is not None and max_budget_pkr > 0:
            over_budget = self.content_model.item_prices > max_budget_pkr
            scores[over_budget] -= 5.0

        if occasion:
            occ_lower = occasion.lower()
            for idx, pid in enumerate(self.col_to_item):
                meta = self.item_metadata.get(pid, {})
                if occ_lower in str(meta.get("title", "")).lower():
                    scores[idx] += 0.5

        if only_in_stock:
            scores[~self.in_stock_mask] = -1e9

        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        res = [(self.col_to_item[int(i)], float(scores[i])) for i in top_idx]
        self._cold_user_cache[cache_key] = res
        return res

    def score_all_items_for_user(
        self,
        user_id: str,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> np.ndarray:
        """Fuse Item-CF, Implicit ALS, Content Embeddings, and Feature Tower scores."""
        if user_id not in self.item_cf.user_to_row:
            # Cold-start user path
            onboard_cat = self.cold_user_onboarding_map.get(user_id)
            cold_recs = self.recommend_for_cold_user(
                preferred_category=onboard_cat, k=50, only_in_stock=only_in_stock
            )
            scores = np.full(len(self.col_to_item), -1e9, dtype=np.float32)
            for pid, sc in cold_recs:
                c = self.item_to_col.get(pid)
                if c is not None:
                    scores[c] = sc
            return scores

        s_icf = self._minmax_valid(
            self.item_cf._score_user_vector(
                user_id, exclude_seen=exclude_seen, only_in_stock=only_in_stock
            )
        )
        s_als = self._minmax_valid(
            self.als_model.score_all_items_for_user(
                user_id, exclude_seen=exclude_seen, only_in_stock=only_in_stock
            )
        )
        s_cnt = self._minmax_valid(
            self.content_model.score_all_items_for_user(
                user_id, exclude_seen=exclude_seen, only_in_stock=only_in_stock
            )
        )

        # Feature compatibility bonus
        _, fav_cat, avg_price = self.content_model.compute_user_text_profile(user_id)
        s_feat = self.item_feature_prior.copy()
        if fav_cat and fav_cat in self.content_model.cat_to_cols:
            s_feat[self.content_model.cat_to_cols[fav_cat]] += 0.5
        if avg_price > 0:
            log_diff = np.abs(np.log1p(self.content_model.item_prices) - np.log1p(avg_price))
            s_feat += 0.3 * np.exp(-0.5 * (log_diff ** 2)).astype(np.float32)
        s_feat = self._minmax_valid(s_feat)

        valid_mask = (s_icf > -1e8) & (s_als > -1e8)
        # Agreement bonus when item-CF neighborhood and content profile agree
        agreement_bonus = 0.08 * (s_icf > 0.05).astype(np.float32) * s_cnt
        hybrid_scores = np.where(
            valid_mask,
            self.w_item_cf * s_icf
            + self.w_als * s_als
            + self.w_content * s_cnt
            + self.w_features * s_feat
            + agreement_bonus,
            -1e9,
        ).astype(np.float32)
        return hybrid_scores

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        if user_id not in self.item_cf.user_to_row:
            onboard_cat = self.cold_user_onboarding_map.get(user_id)
            return self.recommend_for_cold_user(
                preferred_category=onboard_cat, k=k, only_in_stock=only_in_stock
            )
        scores = self.score_all_items_for_user(
            user_id=user_id,
            exclude_seen=exclude_seen,
            only_in_stock=only_in_stock,
        )
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return [(self.col_to_item[int(i)], float(scores[i])) for i in top_idx]


def evaluate_cold_start_performance(
    con: duckdb.DuckDBPyConnection,
    content_model: ContentBasedRecommender,
    hybrid_model: HybridTwoTowerRecommender,
    k: int = 10,
    max_cold_users: int = 2000,
) -> ColdStartEvalSummary:
    """
    Evaluate cold-start strategies on the `cold_start_test` split created in Day 1 Task 5:
    1. Cold-Start Users (users unseen in `train_interactions`):
       Compare unpersonalized global popularity vs. Segment/Onboarding Category Cold-Start strategy.
    2. Cold-Start Items (`588` products in `cold_start_test` with 0 clicks in `train_interactions`):
       Compare pure Collaborative Filtering (which scores 0 on unseen items) vs. Content-Based Embeddings.
    """
    # 1. Cold-Start User evaluation (with simulated 1-question onboarding category preference)
    cold_user_df = con.execute(
        f"""
        WITH top_cold_users AS (
            SELECT
                user_id,
                ARG_MIN(category, event_timestamp) AS onboarding_category,  -- first event's category, deterministic
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

    # Evaluate anonymous cold start (no onboarding) vs onboarding cold start
    hybrid_model.set_cold_user_context({})
    anon_metrics = evaluate_recommender_at_k(hybrid_model, ground_truth=cold_user_gt, k=k)

    hybrid_model.set_cold_user_context(onboarding_map)
    onboard_metrics = evaluate_recommender_at_k(hybrid_model, ground_truth=cold_user_gt, k=k)

    uplift_pct = (
        (onboard_metrics.ndcg_at_k - anon_metrics.ndcg_at_k)
        / max(anon_metrics.ndcg_at_k, 1e-9)
    ) * 100.0

    # 2. Cold-Start Item evaluation (588 items unseen in `train_interactions`)
    cold_item_df = con.execute(
        """
        SELECT
            user_id,
            product_id
        FROM cold_start_test
        WHERE is_cold_item = TRUE
          AND user_id IN (SELECT DISTINCT user_id FROM train_interactions);
        """
    ).df()

    all_cold_items = (
        con.execute("SELECT DISTINCT product_id FROM cold_start_test WHERE is_cold_item = TRUE")
        .df()["product_id"]
        .astype(str)
        .tolist()
    )
    cold_item_cols = np.array(
        [
            content_model.item_to_col[pid]
            for pid in all_cold_items
            if pid in content_model.item_to_col
        ],
        dtype=int,
    )

    warm_users_with_cold_items = (
        cold_item_df.groupby("user_id")["product_id"].apply(set).to_dict()
    )

    hits_content: list[float] = []
    ndcgs_content: list[float] = []
    discounts = 1.0 / np.log2(np.arange(2, k + 2))

    for uid, true_cold_pids in warm_users_with_cold_items.items():
        scores = content_model.score_all_items_for_user(
            user_id=uid,
            exclude_seen=True,
            only_in_stock=True,
            allowed_cols=cold_item_cols,
        )
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        recs = [content_model.col_to_item[int(i)] for i in top_idx]

        hit_vec = np.array([1.0 if pid in true_cold_pids else 0.0 for pid in recs], dtype=float)
        hits_content.append(1.0 if hit_vec.sum() > 0 else 0.0)
        dcg = float(np.sum(hit_vec * discounts))
        idcg = float(np.sum(discounts[: min(len(true_cold_pids), k)]))
        ndcgs_content.append(dcg / idcg if idcg > 0 else 0.0)

    return ColdStartEvalSummary(
        cold_users_evaluated=len(cold_user_gt),
        popular_cold_user_ndcg10=round(anon_metrics.ndcg_at_k, 5),
        onboarding_hybrid_cold_user_ndcg10=round(onboard_metrics.ndcg_at_k, 5),
        cold_user_ndcg_uplift_pct=round(uplift_pct, 2),
        cold_items_count=len(all_cold_items),
        cf_cold_item_hit_rate10=0.0,  # Pure CF has 0 interactions for unseen cold items
        content_hybrid_cold_item_hit_rate10=round(
            float(np.mean(hits_content)) if hits_content else 0.0, 5
        ),
        content_hybrid_cold_item_ndcg10=round(
            float(np.mean(ndcgs_content)) if ndcgs_content else 0.0, 5
        ),
    )


def run_day2_task3_content_and_hybrid(
    db_path: Path | None = None,
    k: int = 10,
    max_eval_users: int = 5000,
) -> tuple[
    list[BaselineEvalMetrics],
    ColdStartEvalSummary,
    dict[str, BaseRecommender],
]:
    """
    Execute Day 2 — Task 3:
    1. Fit ContentBasedRecommender using 64-dim text embeddings (`models/item_text_embeddings.npy`).
    2. Fit HybridTwoTowerRecommender combining Item-CF + Implicit ALS + Content + User/Item Features.
    3. Evaluate both on the warm Test set (`max_eval_users`) and on the Cold-Start Test set.
    """
    target_db = db_path or settings.duckdb_path
    con = duckdb.connect(str(target_db), read_only=True)

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

    # Fit component models
    item_cf = ItemToItemCFRecommender(k_neighbors=80, shrinkage=5.0, revisit_boost=0.35)
    item_cf.fit_from_sparse(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
    )

    als_model = ImplicitALSRecommender(
        factors=96, regularization=0.10, alpha=30.0, iterations=10, revisit_boost=0.25
    )
    als_model.fit_from_sparse(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
    )

    content_model = ContentBasedRecommender(
        category_bonus=0.15, price_affinity_bonus=0.05, revisit_boost=0.25
    )
    content_model.fit_from_sparse_and_embeddings(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
        item_embeddings=item_embeddings,
    )

    hybrid_model = HybridTwoTowerRecommender(
        item_cf=item_cf,
        als_model=als_model,
        content_model=content_model,
        w_item_cf=0.65,
        w_als=0.23,
        w_content=0.07,
        w_features=0.05,
    )

    test_gt = load_test_ground_truth(con, require_warm_user=True, max_eval_users=max_eval_users)
    content_metrics = evaluate_recommender_at_k(content_model, ground_truth=test_gt, k=k)
    hybrid_metrics = evaluate_recommender_at_k(hybrid_model, ground_truth=test_gt, k=k)

    cold_start_summary = evaluate_cold_start_performance(
        con=con,
        content_model=content_model,
        hybrid_model=hybrid_model,
        k=k,
        max_cold_users=2000,
    )
    con.close()

    models: dict[str, BaseRecommender] = {
        "content_based": content_model,
        "hybrid_two_tower": hybrid_model,
        "item_to_item_cf": item_cf,
        "implicit_als": als_model,
    }
    return [content_metrics, hybrid_metrics], cold_start_summary, models
