"""
Day 2 — Task 2: Collaborative Filtering (Item-to-Item Similarity & Implicit ALS Matrix Factorisation).

Explicit vs. Implicit Feedback in E-Commerce Recommender Systems
================================================================
1. Explicit Feedback (e.g., 1-5 Star Ratings):
   - Users directly state both positive (5 stars) and negative (1 star) preferences.
   - Missing entries in the User-Item matrix are treated as unknown (unobserved), so optimization
     is performed only over observed pairs (u, i) in Omega.

2. Implicit Feedback (ShopKaro Clickstreams: view=1.0, addtocart=3.0, transaction=6.0):
   - Users never explicitly click a "dislike" button.
   - A missing entry (r_{ui} = 0) does NOT mean user u dislikes item i; usually they simply have
     not discovered item i among 25,000 products.
   - Observed interactions are noisy signals of preference: a single accidental view is weak
     evidence, whereas repeated views + add-to-cart + purchase represent high confidence.
   - Following Hu, Koren & Volinsky (2008), we decouple binary preference p_{ui} from confidence c_{ui}:
         p_{ui} = 1 if r_{ui} > 0 else 0
         c_{ui} = 1 + alpha * log(1 + r_{ui})
     and minimize the weighted regularized squared error across ALL M x N user-item pairs:
         L(X, Y) = sum_{u, i} c_{ui} (p_{ui} - x_u^T y_i)^2 + lambda * (||X||_F^2 + ||Y||_F^2)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

from shopkaro.config.settings import settings
from shopkaro.recommendations.baselines import (
    BaselineEvalMetrics,
    BaseRecommender,
    evaluate_recommender_at_k,
    load_test_ground_truth,
)


@dataclass
class ALSHyperparameterResult:
    """Result of evaluating one Implicit ALS hyperparameter configuration on Validation/Test."""

    factors: int
    regularization: float
    alpha: float
    iterations: int
    val_ndcg_at_10: float
    val_precision_at_10: float
    val_recall_at_10: float
    val_hit_rate_at_10: float
    fit_time_sec: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "factors": self.factors,
            "regularization": self.regularization,
            "alpha": self.alpha,
            "iterations": self.iterations,
            "val_ndcg_at_10": self.val_ndcg_at_10,
            "val_precision_at_10": self.val_precision_at_10,
            "val_recall_at_10": self.val_recall_at_10,
            "val_hit_rate_at_10": self.val_hit_rate_at_10,
            "fit_time_sec": self.fit_time_sec,
        }


INTERACTION_TABLES = ("train_interactions", "interactions_clean")


def _load_sparse_interaction_data(
    con: duckdb.DuckDBPyConnection,
    table: str = "train_interactions",
) -> tuple[
    pd.DataFrame,
    dict[str, int],
    list[str],
    dict[str, int],
    list[str],
    sp.csr_matrix,
    dict[str, set[str]],
]:
    """
    Load user-item implicit weights from `table` (default `train_interactions`; the serving model
    is retrained on `interactions_clean`, i.e. all history) and construct a
    Compressed Sparse Row (CSR) matrix R of shape (n_train_users, n_catalogue_items).
    Also returns `{user_id: set(purchased_product_ids)}` for purchased-item filtering.
    """
    catalogue_df = con.execute(
        """
        SELECT product_id, title, category, brand, price_pkr, in_stock
        FROM product_catalogue
        ORDER BY product_id;
        """
    ).df()

    item_ids = catalogue_df["product_id"].astype(str).tolist()
    item_to_col = {pid: idx for idx, pid in enumerate(item_ids)}

    if table not in INTERACTION_TABLES:
        raise ValueError(f"table must be one of {INTERACTION_TABLES}")
    # Aggregate user-item implicit interaction weights and track already-purchased items
    agg_df = con.execute(
        f"""
        SELECT
            user_id,
            product_id,
            SUM(implicit_weight) AS raw_weight,
            MAX(CASE WHEN event_type = 'transaction' THEN 1 ELSE 0 END) AS bought
        FROM {table}
        GROUP BY user_id, product_id;
        """
    ).df()

    user_ids = agg_df["user_id"].astype(str).unique().tolist()
    user_to_row = {uid: idx for idx, uid in enumerate(user_ids)}

    row_idx = agg_df["user_id"].map(user_to_row).to_numpy(dtype=np.int32)
    col_idx = agg_df["product_id"].map(item_to_col).to_numpy(dtype=np.int32)
    weights = agg_df["raw_weight"].to_numpy(dtype=np.float32)

    R_csr = sp.csr_matrix(
        (weights, (row_idx, col_idx)),
        shape=(len(user_ids), len(item_ids)),
        dtype=np.float32,
    )

    # Purchased items per user (for `exclude_seen=True` in e-commerce)
    bought_df = agg_df.loc[agg_df["bought"] == 1, ["user_id", "product_id"]]
    user_purchased: dict[str, set[str]] = {}
    for uid, pid in zip(bought_df["user_id"], bought_df["product_id"]):
        user_purchased.setdefault(str(uid), set()).add(str(pid))

    return (
        catalogue_df,
        user_to_row,
        user_ids,
        item_to_col,
        item_ids,
        R_csr,
        user_purchased,
    )


class ItemToItemCFRecommender(BaseRecommender):
    """
    Task 2A: Item-to-Item Collaborative Filtering (Co-occurrence + Shrinkage Cosine Similarity).

    Computes the shrunk cosine similarity matrix S between all item columns:
        S_{ij} = <r_{*, i}, r_{*, j}> / (||r_{*, i}||_2 * ||r_{*, j}||_2 + shrinkage)
    Retains the top-K_neighbors strongest neighbors per item, plus a category affinity fallback
    and optional repeat-intent signal for items viewed/carted in training but not yet bought.
    Also powers `.get_similar_items(product_id, k=10)` for the "Similar Products" widget.
    """

    name = "4. Item-to-Item Collaborative Filtering (Cosine)"

    def __init__(
        self,
        k_neighbors: int = 80,
        shrinkage: float = 5.0,
        revisit_boost: float = 0.35,
    ) -> None:
        super().__init__()
        self.k_neighbors = k_neighbors
        self.shrinkage = shrinkage
        self.revisit_boost = revisit_boost

        self.user_to_row: dict[str, int] = {}
        self.item_to_col: dict[str, int] = {}
        self.col_to_item: list[str] = []
        self.R_log_csr: sp.csr_matrix | None = None
        self.sim_matrix_csr: sp.csr_matrix | None = None
        self.item_pop_prior: np.ndarray = np.array([], dtype=np.float32)
        self.in_stock_mask: np.ndarray = np.array([], dtype=bool)
        self.item_categories: np.ndarray = np.array([], dtype=object)
        self.cat_to_cols: dict[str, np.ndarray] = {}

    def fit_from_sparse(
        self,
        catalogue_df: pd.DataFrame,
        user_to_row: dict[str, int],
        item_to_col: dict[str, int],
        col_to_item: list[str],
        R_csr: sp.csr_matrix,
        user_purchased: dict[str, set[str]],
    ) -> ItemToItemCFRecommender:
        """Fit the sparse item-to-item cosine similarity matrix."""
        self._index_catalogue_and_seen(catalogue_df)
        self.user_seen_items = user_purchased
        self.user_to_row = user_to_row
        self.item_to_col = item_to_col
        self.col_to_item = col_to_item

        n_items = len(col_to_item)
        self.in_stock_mask = np.array(
            [pid in self.in_stock_ids for pid in col_to_item], dtype=bool
        )
        self.item_categories = catalogue_df["category"].astype(str).to_numpy()
        self.cat_to_cols = {}
        for cat in np.unique(self.item_categories):
            self.cat_to_cols[str(cat)] = np.where(self.item_categories == cat)[0]

        # Log-dampen raw weights: log(1 + r_{ui})
        R_log = R_csr.copy()
        R_log.data = np.log1p(R_log.data)
        self.R_log_csr = R_log

        # Global popularity prior (normalized to [0, 0.05]) for tie-breaking
        item_sums = np.asarray(R_log.sum(axis=0)).ravel().astype(np.float32)
        self.item_pop_prior = (item_sums / max(float(item_sums.max()), 1.0)) * 0.05

        # Normalize rows (users) so heavy power-users don't dominate co-occurrence
        R_user_norm = normalize(R_log, norm="l2", axis=1)

        # Compute column (item) norms with shrinkage: sqrt(sum_u r_{ui}^2) + shrinkage
        col_norms = np.sqrt(np.asarray(R_user_norm.power(2).sum(axis=0)).ravel()) + self.shrinkage
        inv_col_norms = sp.diags(1.0 / np.maximum(col_norms, 1e-9))
        R_item_scaled = R_user_norm @ inv_col_norms  # (n_users, n_items)

        # Compute sparse item-to-item Gram matrix S = R_item_scaled^T @ R_item_scaled
        S_full = (R_item_scaled.T @ R_item_scaled).tocsr()
        S_full.setdiag(0.0)
        S_full.eliminate_zeros()

        # Keep only top `k_neighbors` per item row to keep S ultra-fast and denoised
        indptr = [0]
        indices_list: list[np.ndarray] = []
        data_list: list[np.ndarray] = []

        for i in range(n_items):
            start, end = S_full.indptr[i], S_full.indptr[i + 1]
            row_cols = S_full.indices[start:end]
            row_vals = S_full.data[start:end]
            if len(row_vals) > self.k_neighbors:
                top_idx = np.argpartition(row_vals, -self.k_neighbors)[-self.k_neighbors :]
                order = top_idx[np.argsort(row_vals[top_idx])[::-1]]
                row_cols = row_cols[order]
                row_vals = row_vals[order]
            indices_list.append(row_cols)
            data_list.append(row_vals)
            indptr.append(indptr[-1] + len(row_cols))

        all_indices = (
            np.concatenate(indices_list) if indices_list else np.array([], dtype=np.int32)
        )
        all_data = (
            np.concatenate(data_list) if data_list else np.array([], dtype=np.float32)
        )
        self.sim_matrix_csr = sp.csr_matrix(
            (all_data, all_indices, np.array(indptr, dtype=np.int32)),
            shape=(n_items, n_items),
            dtype=np.float32,
        )
        return self

    def get_similar_items(
        self,
        product_id: str,
        k: int = 10,
        only_in_stock: bool = True,
    ) -> list[dict[str, Any]]:
        """Return the top-K most similar products to `product_id` ("Similar Products")."""
        assert self.sim_matrix_csr is not None
        col = self.item_to_col.get(product_id)
        if col is None:
            return []

        row_vec = self.sim_matrix_csr.getrow(col).toarray().ravel()
        # Prioritize same-category co-occurring items + category popularity tie-breaker
        cat = str(self.item_categories[col])
        cat_cols = self.cat_to_cols.get(cat, np.array([], dtype=int))
        row_vec[cat_cols] = row_vec[cat_cols] * 2.5 + self.item_pop_prior[cat_cols] + 0.05
        row_vec[col] = -1e9  # Exclude self

        if only_in_stock:
            row_vec[~self.in_stock_mask] = -1e9

        top_idx = np.argpartition(row_vec, -k)[-k:]
        top_idx = top_idx[np.argsort(row_vec[top_idx])[::-1]]

        results: list[dict[str, Any]] = []
        for rank, c_idx in enumerate(top_idx, start=1):
            pid = self.col_to_item[int(c_idx)]
            meta = self.item_metadata.get(pid, {})
            results.append(
                {
                    "rank": rank,
                    "product_id": pid,
                    "similarity_score": round(float(row_vec[c_idx]), 4),
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "brand": meta.get("brand", ""),
                    "price_pkr": meta.get("price_pkr", 0.0),
                    "in_stock": meta.get("in_stock", True),
                }
            )
        return results

    def _score_user_vector(
        self,
        user_id: str,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
        u_vec: sp.csr_matrix | None = None,
        extra_purchased: set[str] | None = None,
    ) -> np.ndarray:
        """
        Compute full 25,000-item score vector for `user_id`.

        `u_vec` (1 x n_items, log-dampened weights) overrides the stored training history; the
        real-time serving layer uses it to add live session clicks. `extra_purchased` adds
        purchases made after training to the already-bought filter.
        """
        assert self.R_log_csr is not None and self.sim_matrix_csr is not None
        if u_vec is None:
            u_row = self.user_to_row.get(user_id)
            u_vec = self.R_log_csr[u_row] if u_row is not None else None
        if u_vec is None or u_vec.nnz == 0:
            scores = self.item_pop_prior.copy()
            if only_in_stock:
                scores[~self.in_stock_mask] = -1e9
            return scores

        interacted_cols = u_vec.indices
        interacted_weights = u_vec.data
        # Item-to-item propagation: s_u = u_vec @ S
        scores = (u_vec @ self.sim_matrix_csr).toarray().ravel().astype(np.float32)

        # Boost user's preferred category popular items slightly to prevent empty neighborhoods
        if len(interacted_cols) > 0:
            top_col = interacted_cols[int(np.argmax(interacted_weights))]
            fav_cat = str(self.item_categories[top_col])
            cat_cols = self.cat_to_cols.get(fav_cat, np.array([], dtype=int))
            scores[cat_cols] += self.item_pop_prior[cat_cols] * 2.0

            if not exclude_seen and self.revisit_boost > 0:
                # In e-commerce, users frequently return to buy an item they viewed/carted earlier
                scores[interacted_cols] += interacted_weights * self.revisit_boost

        # Filter already-purchased (or all seen if exclude_seen=True)
        seen_pids = self.user_seen_items.get(user_id, set()) | (extra_purchased or set())
        for pid in seen_pids:
            c = self.item_to_col.get(pid)
            if c is not None:
                scores[c] = -1e9

        if exclude_seen and len(interacted_cols) > 0:
            scores[interacted_cols] = -1e9

        if only_in_stock:
            scores[~self.in_stock_mask] = -1e9

        return scores

    def recommend_ids(
        self,
        user_id: str,
        k: int = 10,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> list[tuple[str, float]]:
        scores = self._score_user_vector(
            user_id=user_id,
            exclude_seen=exclude_seen,
            only_in_stock=only_in_stock,
        )
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        return [(self.col_to_item[int(i)], float(scores[i])) for i in top_idx]


class ImplicitALSRecommender(BaseRecommender):
    """
    Task 2B: Implicit Feedback Matrix Factorisation (Hu-Koren-Volinsky iALS).

    Minimizes:
        sum_{u, i} c_{ui} (p_{ui} - x_u^T y_i)^2 + lambda * (||X||_F^2 + ||Y||_F^2)
    where p_{ui} = I(r_{ui} > 0) and c_{ui} = 1 + alpha * log(1 + r_{ui}).

    Uses a confidence-weighted SVD warm-start followed by Alternating Least Squares (ALS)
    Cholesky updates on the active core interaction submatrix and exact closed-form fold-in
    for all 549k training users:
        x_u = r_u^{(conf)} Y (Y^T Y + lambda * I)^{-1}
    """

    name = "5. Implicit Matrix Factorisation (ALS)"

    def __init__(
        self,
        factors: int = 64,
        regularization: float = 0.1,
        alpha: float = 25.0,
        iterations: int = 10,
        revisit_boost: float = 0.25,
    ) -> None:
        super().__init__()
        self.factors = factors
        self.regularization = regularization
        self.alpha = alpha
        self.iterations = iterations
        self.revisit_boost = revisit_boost

        self.user_to_row: dict[str, int] = {}
        self.item_to_col: dict[str, int] = {}
        self.col_to_item: list[str] = []
        self.R_log_csr: sp.csr_matrix | None = None
        self.item_factors: np.ndarray = np.array([], dtype=np.float32)  # Y: (n_items, f)
        self.projection_matrix: np.ndarray = np.array([], dtype=np.float32)  # Y (Y^T Y + reg I)^{-1}
        self.item_pop_prior: np.ndarray = np.array([], dtype=np.float32)
        self.in_stock_mask: np.ndarray = np.array([], dtype=bool)
        self.item_categories: np.ndarray = np.array([], dtype=object)
        self.cat_to_cols: dict[str, np.ndarray] = {}
        self.user_factors: np.ndarray = np.array([], dtype=np.float32)  # X: (n_users, f), implicit backend only
        self.backend = "svd_ridge"  # or "implicit"

    def fit_from_sparse(
        self,
        catalogue_df: pd.DataFrame,
        user_to_row: dict[str, int],
        item_to_col: dict[str, int],
        col_to_item: list[str],
        R_csr: sp.csr_matrix,
        user_purchased: dict[str, set[str]],
        max_core_users: int = 15000,
    ) -> ImplicitALSRecommender:
        """Fit Implicit ALS latent factors X and Y."""
        self._index_catalogue_and_seen(catalogue_df)
        self.user_seen_items = user_purchased
        self.user_to_row = user_to_row
        self.item_to_col = item_to_col
        self.col_to_item = col_to_item

        n_items = len(col_to_item)
        self.in_stock_mask = np.array(
            [pid in self.in_stock_ids for pid in col_to_item], dtype=bool
        )
        self.item_categories = catalogue_df["category"].astype(str).to_numpy()
        self.cat_to_cols = {}
        for cat in np.unique(self.item_categories):
            self.cat_to_cols[str(cat)] = np.where(self.item_categories == cat)[0]

        # Build confidence-scaled sparse matrix C_minus_I = alpha * log(1 + r_{ui})
        R_log = R_csr.copy()
        R_log.data = np.log1p(R_log.data)
        self.R_log_csr = R_log

        item_sums = np.asarray(R_log.sum(axis=0)).ravel().astype(np.float32)
        self.item_pop_prior = (item_sums / max(float(item_sums.max()), 1.0)) * 0.08

        # Real implicit-feedback ALS (Hu, Koren & Volinsky 2008) from the `implicit` library when installed
        # (Python 3.11 env). It factorises ALL users; scoring below is unchanged.
        if self._fit_with_implicit_library(R_log):
            return self

        # Fallback (no `implicit`): SVD warm start + alternating ridge on the most active users.
        # Select top active multi-interaction users for the core ALS alternating loop
        user_nnz = np.diff(R_log.indptr)
        core_user_rows = np.argsort(user_nnz)[::-1][: min(max_core_users, R_log.shape[0])]
        R_core = R_log[core_user_rows].tocsr()

        # Confidence matrix entries: c_{ui} - 1 = alpha * log(1 + r_{ui})
        C_core = R_core.copy()
        C_core.data = 1.0 + self.alpha * C_core.data

        # Warm-start Y and X_core via TruncatedSVD on confidence-weighted matrix
        svd = TruncatedSVD(
            n_components=self.factors,
            n_iter=min(self.iterations, 10),
            random_state=settings.random_seed,
        )
        X_core = svd.fit_transform(C_core).astype(np.float32)  # (n_core, f)
        Y = svd.components_.T.astype(np.float32)  # (n_items, f)

        # Run Alternating Ridge / ALS refinement steps on (X_core, Y)
        reg_eye = self.regularization * np.eye(self.factors, dtype=np.float32)
        P_core = R_core.copy()
        P_core.data = np.ones_like(P_core.data, dtype=np.float32) + 0.15 * np.log1p(
            self.alpha * R_core.data
        )

        n_als_Sweeps = max(1, self.iterations // 3)
        for _ in range(n_als_Sweeps):
            # Update Y given X_core: Y = P_core^T X_core (X_core^T X_core + reg * I)^{-1}
            XtX = (X_core.T @ X_core) + reg_eye
            Y = np.linalg.solve(XtX, (P_core.T @ X_core).T).T.astype(np.float32)

            # Update X_core given Y: X_core = P_core Y (Y^T Y + reg * I)^{-1}
            YtY = (Y.T @ Y) + reg_eye
            X_core = np.linalg.solve(YtY, (P_core @ Y).T).T.astype(np.float32)

        self.item_factors = normalize(Y, norm="l2", axis=1).astype(np.float32)
        YtY_final = (self.item_factors.T @ self.item_factors) + reg_eye
        # Precompute projection matrix M = Y (Y^T Y + reg I)^{-1} of shape (n_items, f)
        self.projection_matrix = np.linalg.solve(YtY_final, self.item_factors.T).T.astype(
            np.float32
        )
        return self

    def _fit_with_implicit_library(self, R_log: sp.csr_matrix) -> bool:
        """Fit `implicit.als.AlternatingLeastSquares`; returns False when the library is unavailable."""
        try:
            # implicit 0.7.1 calls numpy.__config__.get_info (removed in NumPy 1.26) only to warn about
            # OpenBLAS threading; provide an empty answer so the import works with the pinned NumPy.
            if not hasattr(np.__config__, "get_info"):
                np.__config__.get_info = lambda *args, **kwargs: {}  # type: ignore[attr-defined]
            from implicit.als import AlternatingLeastSquares
        except Exception:
            return False
        model = AlternatingLeastSquares(
            factors=self.factors,
            regularization=self.regularization,
            alpha=self.alpha,
            iterations=self.iterations,
            random_state=settings.random_seed,
        )
        model.fit(R_log.astype(np.float32).tocsr(), show_progress=False)
        self.user_factors = np.asarray(model.user_factors, dtype=np.float32)
        self.item_factors = np.asarray(model.item_factors, dtype=np.float32)
        self.backend = "implicit"
        return True

    def compute_user_embedding(self, user_id: str) -> np.ndarray | None:
        """User latent factors: from the `implicit` model when fitted with it, else exact ALS fold-in."""
        assert self.R_log_csr is not None
        u_row = self.user_to_row.get(user_id)
        if u_row is None:
            return None
        if self.backend == "implicit":
            return self.user_factors[u_row] if self.R_log_csr.indptr[u_row + 1] > self.R_log_csr.indptr[u_row] else None
        start, end = self.R_log_csr.indptr[u_row], self.R_log_csr.indptr[u_row + 1]
        if start == end:
            return None
        interacted_cols = self.R_log_csr.indices[start:end]
        interacted_weights = self.R_log_csr.data[start:end]
        # Confidence-weighted preference vector p_u^{(c)} = 1 + log(1 + alpha * r_u)
        conf_weights = (1.0 + np.log1p(self.alpha * interacted_weights)).astype(np.float32)
        x_u = (conf_weights @ self.projection_matrix[interacted_cols]).astype(np.float32)
        return x_u

    def score_all_items_for_user(
        self,
        user_id: str,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
    ) -> np.ndarray:
        """Compute full 25,000-item ALS score vector x_u^T Y^T for `user_id`."""
        assert self.R_log_csr is not None
        x_u = self.compute_user_embedding(user_id)
        if x_u is None:
            scores = self.item_pop_prior.copy()
            if only_in_stock:
                scores[~self.in_stock_mask] = -1e9
            return scores

        # Latent factor dot product across all 25,000 items: (n_items, f) @ (f,) -> (n_items,)
        scores = (self.item_factors @ x_u).astype(np.float32)

        u_row = self.user_to_row[user_id]
        start, end = self.R_log_csr.indptr[u_row], self.R_log_csr.indptr[u_row + 1]
        interacted_cols = self.R_log_csr.indices[start:end]
        if len(interacted_cols) > 0:
            interacted_weights = self.R_log_csr.data[start:end]
            top_col = interacted_cols[int(np.argmax(interacted_weights))]
            fav_cat = str(self.item_categories[top_col])
            cat_cols = self.cat_to_cols.get(fav_cat, np.array([], dtype=int))
            scores[cat_cols] += self.item_pop_prior[cat_cols] * 1.5

            if not exclude_seen and self.revisit_boost > 0:
                scores[interacted_cols] += interacted_weights * self.revisit_boost

        seen_pids = self.user_seen_items.get(user_id, set())
        for pid in seen_pids:
            c = self.item_to_col.get(pid)
            if c is not None:
                scores[c] = -1e9

        if exclude_seen and len(interacted_cols) > 0:
            scores[interacted_cols] = -1e9

        if only_in_stock:
            scores[~self.in_stock_mask] = -1e9

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


def load_val_ground_truth(
    con: duckdb.DuckDBPyConnection,
    max_eval_users: int = 2000,
) -> dict[str, set[str]]:
    """Load validation ground-truth `{user_id: set(product_ids)}` for hyperparameter tuning."""
    df = con.execute(
        f"""
        WITH target_users AS (
            SELECT
                user_id,
                SUM(implicit_weight) AS total_w
            FROM val_interactions
            WHERE user_id IN (SELECT DISTINCT user_id FROM train_interactions)
            GROUP BY user_id
            ORDER BY total_w DESC
            LIMIT {int(max_eval_users)}
        )
        SELECT v.user_id, v.product_id
        FROM val_interactions v
        JOIN target_users u ON v.user_id = u.user_id;
        """
    ).df()
    return df.groupby("user_id")["product_id"].apply(set).to_dict()


def run_day2_task2_collaborative_filtering(
    db_path: Path | None = None,
    k: int = 10,
    max_eval_users: int = 5000,
) -> tuple[
    list[BaselineEvalMetrics],
    list[ALSHyperparameterResult],
    dict[str, BaseRecommender],
]:
    """
    Execute Day 2 — Task 2:
    1. Fit Item-to-Item Collaborative Filtering (Cosine Co-occurrence).
    2. Run Hyperparameter Tuning for Implicit ALS across `(factors, regularization, alpha, iterations)` on Validation set.
    3. Evaluate both best ALS and Item-to-Item CF on the Test set (`max_eval_users`).
    """
    import time

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

    val_gt = load_val_ground_truth(con, max_eval_users=1500)
    test_gt = load_test_ground_truth(con, require_warm_user=True, max_eval_users=max_eval_users)
    con.close()

    # 1. Fit Item-to-Item CF
    item_cf = ItemToItemCFRecommender(k_neighbors=80, shrinkage=5.0, revisit_boost=0.35)
    item_cf.fit_from_sparse(
        catalogue_df=catalogue_df,
        user_to_row=user_to_row,
        item_to_col=item_to_col,
        col_to_item=col_to_item,
        R_csr=R_csr,
        user_purchased=user_purchased,
    )

    # 2. Hyperparameter Tuning Grid for Implicit ALS on Validation Set
    param_grid = [
        {"factors": 32, "regularization": 0.05, "alpha": 15.0, "iterations": 6},
        {"factors": 64, "regularization": 0.10, "alpha": 25.0, "iterations": 10},
        {"factors": 64, "regularization": 0.50, "alpha": 40.0, "iterations": 12},
        {"factors": 96, "regularization": 0.10, "alpha": 30.0, "iterations": 10},
    ]

    tuning_results: list[ALSHyperparameterResult] = []
    best_als_model: ImplicitALSRecommender | None = None
    best_val_ndcg = -1.0

    for params in param_grid:
        t0 = time.perf_counter()
        als_candidate = ImplicitALSRecommender(
            factors=int(params["factors"]),
            regularization=float(params["regularization"]),
            alpha=float(params["alpha"]),
            iterations=int(params["iterations"]),
            revisit_boost=0.25,
        )
        als_candidate.fit_from_sparse(
            catalogue_df=catalogue_df,
            user_to_row=user_to_row,
            item_to_col=item_to_col,
            col_to_item=col_to_item,
            R_csr=R_csr,
            user_purchased=user_purchased,
        )
        fit_sec = time.perf_counter() - t0
        val_m = evaluate_recommender_at_k(als_candidate, ground_truth=val_gt, k=k)
        tuning_results.append(
            ALSHyperparameterResult(
                factors=int(params["factors"]),
                regularization=float(params["regularization"]),
                alpha=float(params["alpha"]),
                iterations=int(params["iterations"]),
                val_ndcg_at_10=val_m.ndcg_at_k,
                val_precision_at_10=val_m.precision_at_k,
                val_recall_at_10=val_m.recall_at_k,
                val_hit_rate_at_10=val_m.hit_rate_at_k,
                fit_time_sec=round(fit_sec, 2),
            )
        )
        if val_m.ndcg_at_k > best_val_ndcg:
            best_val_ndcg = val_m.ndcg_at_k
            best_als_model = als_candidate

    assert best_als_model is not None

    # 3. Evaluate Item-to-Item CF and Best Tuned Implicit ALS on Test Set
    item_cf_metrics = evaluate_recommender_at_k(item_cf, ground_truth=test_gt, k=k)
    als_metrics = evaluate_recommender_at_k(best_als_model, ground_truth=test_gt, k=k)

    models: dict[str, BaseRecommender] = {
        "item_to_item_cf": item_cf,
        "implicit_als": best_als_model,
    }
    return [item_cf_metrics, als_metrics], tuning_results, models
