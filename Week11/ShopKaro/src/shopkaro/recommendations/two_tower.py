"""
Day 2 — a real neural Two-Tower recommender trained with PyTorch.

Why a separate model: `HybridTwoTowerRecommender` in hybrid.py is a hand-weighted blend of item-CF, ALS and content
scores. It has the two-tower *shape* but nothing is learned end-to-end. This module trains both towers jointly.

Architecture
------------
Item tower  v_i = normalize(MLP([id_emb(i) | text_emb(i) | cat_emb(i) | price_band_emb(i)]))
User tower  u   = normalize(MLP([weighted-mean id_emb(history) | weighted-mean text_emb(history)]))
Score       s(u, i) = <u, v_i> / tau

The user tower has no per-user ID: a user is described by the items they touched. That means any user with at least
one interaction gets a vector, including users who were not in the training data.

Training (train_interactions only; no validation or test rows)
-------------------------------------------------------------
* Examples: leave-one-out. For every user with >= 2 items, each item becomes a target once per epoch and the
  user's *other* items form the history.
* Loss: in-batch sampled softmax. The other targets in the batch act as negatives, with the logQ correction
  (logit - log q_j, where q_j is the item's sampling frequency) so popular items are not over-penalised as negatives.
  Duplicate targets inside a batch are masked out so an item is never its own negative.
* ID dropout (20%): the item ID embedding is replaced by the "unknown" row. The tower therefore learns to embed an
  item from text, category and price alone, which is what it must do for brand-new (cold) items at serving time.

Selection
---------
The number of epochs and two serving knobs (`pop_weight`: how much of log-popularity to add back after logQ
training; `revisit_boost`: how much to favour items the user already viewed, the same convention as the other
models) are picked on the validation window (`val_interactions`). The test set is only used by the Day 2 comparison.

Serving needs only numpy: after training, the weights are copied into numpy arrays, so `torch` is imported lazily
inside `fit_from_sparse` and the lite cloud deployment (no torch) can still import this module.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import scipy.sparse as sp

from shopkaro.recommendations.baselines import BaseRecommender

UNKNOWN_ID = 0  # row 0 of the ID table = "item never seen in training"


@dataclass
class TwoTowerTrainingLog:
    epochs_trained: int = 0
    best_epoch: int = 0
    best_val_ndcg_at_10: float = 0.0
    best_pop_weight: float = 0.0
    best_revisit_boost: float = 0.0
    train_examples_per_epoch: int = 0
    seconds: float = 0.0
    per_epoch: list[dict] = field(default_factory=list)
    cold_start_selected: dict = field(default_factory=dict)  # new-user settings chosen on validation new users


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


def _l2(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.maximum(n, 1e-9)


def _gather_rows(indptr: np.ndarray, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For CSR rows `rows`, return (flat positions into indices/data, bag offsets)."""
    starts = indptr[rows]
    lens = indptr[rows + 1] - starts
    offsets = np.zeros(len(rows), dtype=np.int64)
    if len(rows) > 1:
        offsets[1:] = np.cumsum(lens)[:-1]
    total = int(lens.sum())
    flat = np.arange(total, dtype=np.int64) - np.repeat(offsets, lens) + np.repeat(starts, lens)
    return flat, offsets


def load_val_cold_users(con, max_users: int = 2000) -> tuple[dict[str, set[str]], dict[str, str]]:  # noqa: ANN001
    """
    Validation new users (in val_interactions, absent from train) with a simulated one-question onboarding answer.
    Same protocol as the Day 2 test cold users: the answer is the category of the user's first event in that window, so it is
    optimistic for every model that uses it; it is used here only to choose settings, never to report results.
    """
    df = con.execute(
        f"""
        WITH cold AS (
            SELECT user_id, ARG_MIN(category, event_timestamp) AS onboarding_category, COUNT(DISTINCT product_id) AS n_items
            FROM val_interactions
            WHERE user_id NOT IN (SELECT DISTINCT user_id FROM train_interactions)
            GROUP BY user_id
            ORDER BY n_items DESC, user_id
            LIMIT {int(max_users)}
        )
        SELECT v.user_id, v.product_id, c.onboarding_category
        FROM val_interactions v JOIN cold c ON v.user_id = c.user_id;
        """
    ).df()
    gt = df.groupby("user_id")["product_id"].apply(set).to_dict()
    cats = df.drop_duplicates("user_id").set_index("user_id")["onboarding_category"].astype(str).to_dict()
    return gt, cats


class TwoTowerRecommender(BaseRecommender):
    """Neural two-tower recommender (PyTorch training, numpy serving)."""

    name = "8. Neural Two-Tower (PyTorch)"
    scores_cold_items = True  # the item tower can embed items with zero training clicks

    def __init__(
        self,
        dim: int = 64,
        id_dim: int = 32,
        hidden: int = 128,
        temperature: float = 0.05,
        batch_size: int = 1024,
        lr: float = 2e-3,
        max_epochs: int = 12,
        patience: int = 2,
        id_dropout: float = 0.2,
        n_price_bands: int = 10,
        seed: int = 42,
        num_threads: int | None = 8,
        pop_weight_grid: tuple[float, ...] = (0.0, 0.5, 1.0),
        revisit_boost_grid: tuple[float, ...] = (0.0, 2.0, 5.0, 10.0, 20.0, 40.0),
        verbose: bool = True,
    ) -> None:
        super().__init__()
        self.dim, self.id_dim, self.hidden = dim, id_dim, hidden
        self.temperature, self.batch_size, self.lr = temperature, batch_size, lr
        self.max_epochs, self.patience, self.id_dropout = max_epochs, patience, id_dropout
        self.n_price_bands, self.seed, self.verbose = n_price_bands, seed, verbose
        self.num_threads = num_threads  # results depend on the thread count, so it is fixed (None = torch default)
        self.pop_weight_grid, self.revisit_boost_grid = pop_weight_grid, revisit_boost_grid

        self.pop_weight = 0.0
        self.revisit_boost = 0.0
        self.user_to_row: dict[str, int] = {}
        self.item_to_col: dict[str, int] = {}
        self.col_to_item: list[str] = []
        self.R_log_csr: sp.csr_matrix | None = None
        self.item_vectors = np.zeros((0, dim), dtype=np.float32)
        self.log_pop = np.zeros(0, dtype=np.float32)
        self.in_stock_mask = np.zeros(0, dtype=bool)
        self.user_params: dict[str, np.ndarray] = {}
        self.training_log = TwoTowerTrainingLog()
        # New-user (cold-start) path: onboarding category -> seed vector built from that category's popular items
        self.cat_to_cols: dict[str, np.ndarray] = {}
        self.train_count = np.zeros(0, dtype=np.int64)
        self.cold_user_map: dict[str, str] = {}
        self.cold_n_seed = 20
        self.cold_category_bonus = 5.0
        self.cold_pop_weight = 0.5
        self._cold_cache: dict[str, np.ndarray] = {}
        self.cold_tuning: list[dict] = []

    # ------------------------------------------------------------------ training
    def fit_from_sparse(
        self,
        catalogue_df: pd.DataFrame,
        user_to_row: dict[str, int],
        item_to_col: dict[str, int],
        col_to_item: list[str],
        R_csr: sp.csr_matrix,
        user_purchased: dict[str, set[str]],
        item_embeddings: np.ndarray,
        val_ground_truth: dict[str, set[str]] | None = None,
    ) -> TwoTowerRecommender:
        import torch  # lazy: serving and the lite deploy do not need torch
        from torch import nn

        t0 = time.time()
        prev_threads = torch.get_num_threads()
        if self.num_threads:
            # cap by the machine's cores, not by the current setting (other libraries can lower that)
            torch.set_num_threads(max(1, min(self.num_threads, os.cpu_count() or 1)))
        try:
            return self._fit(torch, nn, t0, catalogue_df, user_to_row, item_to_col, col_to_item, R_csr,
                             user_purchased, item_embeddings, val_ground_truth)
        finally:
            torch.set_num_threads(prev_threads)

    def _fit(self, torch, nn, t0, catalogue_df, user_to_row, item_to_col, col_to_item, R_csr,  # noqa: ANN001, PLR0913
             user_purchased, item_embeddings, val_ground_truth) -> TwoTowerRecommender:
        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)

        self._index_catalogue_and_seen(catalogue_df)
        self.user_seen_items = user_purchased
        self.user_to_row, self.item_to_col, self.col_to_item = user_to_row, item_to_col, col_to_item
        n_items = len(col_to_item)

        R = R_csr.tocsr().astype(np.float32)
        R.sort_indices()
        R_log = R.copy()
        R_log.data = np.log1p(R_log.data)
        self.R_log_csr = R_log
        self.in_stock_mask = np.array([pid in self.in_stock_ids for pid in col_to_item], dtype=bool)

        # Item features
        text = item_embeddings[:n_items].astype(np.float32)
        text = text / np.maximum(np.linalg.norm(text, axis=1, keepdims=True), 1e-9)
        cats = catalogue_df["category"].astype(str).to_numpy()
        cat_codes = pd.Categorical(cats).codes.astype(np.int64)
        log_price = np.log1p(catalogue_df["price_pkr"].to_numpy(dtype=np.float64))
        edges = np.quantile(log_price, np.linspace(0, 1, self.n_price_bands + 1)[1:-1])
        price_band = np.searchsorted(edges, log_price).astype(np.int64)
        train_count = np.diff(R.tocsc().indptr)  # interactions per item in training
        item_id_idx = np.where(train_count > 0, np.arange(n_items) + 1, UNKNOWN_ID).astype(np.int64)
        self.train_count = train_count.astype(np.int64)
        self.cat_to_cols = {str(c): np.where(cats == c)[0] for c in np.unique(cats)}
        self._cold_cache = {}

        # Popularity: q_j for logQ correction (target frequency) and log-pop for serving
        q = (train_count + 1.0) / float(train_count.sum() + n_items)
        self.log_pop = np.log(q).astype(np.float32)

        # Leave-one-out examples: every interaction of a user with >= 2 items
        row_nnz = np.diff(R.indptr)
        multi_rows = np.where(row_nnz >= 2)[0]
        ex_pos = _gather_rows(R.indptr, multi_rows)[0]  # positions in R.indices
        ex_row = np.repeat(multi_rows, row_nnz[multi_rows]).astype(np.int64)
        n_examples = len(ex_pos)
        self.training_log.train_examples_per_epoch = int(n_examples)

        d, idd, h = self.dim, self.id_dim, self.hidden

        class Towers(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.item_id = nn.Embedding(n_items + 1, idd)
                self.hist_id = nn.EmbeddingBag(n_items + 1, idd, mode="sum")
                self.text = nn.Embedding.from_pretrained(torch.from_numpy(text), freeze=True)
                self.text_bag = nn.EmbeddingBag.from_pretrained(torch.from_numpy(text), freeze=True, mode="sum")
                self.cat = nn.Embedding(int(cat_codes.max()) + 1, 8)
                self.price = nn.Embedding(int(price_band.max()) + 1, 8)
                self.item_mlp = nn.Sequential(nn.Linear(idd + text.shape[1] + 16, h), nn.ReLU(), nn.Linear(h, d))
                self.user_mlp = nn.Sequential(nn.Linear(idd + text.shape[1], h), nn.ReLU(), nn.Linear(h, d))
                nn.init.normal_(self.item_id.weight, std=0.05)
                nn.init.normal_(self.hist_id.weight, std=0.05)

            def items(self, cols, id_idx):
                x = torch.cat([self.item_id(id_idx), self.text(cols), self.cat(cat_t[cols]), self.price(price_t[cols])], 1)
                return nn.functional.normalize(self.item_mlp(x), dim=1)

            def users(self, hist_cols, hist_ids, offsets, weights):
                x = torch.cat(
                    [
                        self.hist_id(hist_ids, offsets, per_sample_weights=weights),
                        self.text_bag(hist_cols, offsets, per_sample_weights=weights),
                    ],
                    1,
                )
                return nn.functional.normalize(self.user_mlp(x), dim=1)

        cat_t = torch.from_numpy(cat_codes)
        price_t = torch.from_numpy(price_band)
        item_id_t = torch.from_numpy(item_id_idx)
        log_q_t = torch.from_numpy(np.log(q).astype(np.float32))
        model = Towers()
        opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=self.lr)

        def history_batch(rows: np.ndarray, drop_pos: np.ndarray | None):
            flat, offsets = _gather_rows(R_log.indptr, rows)
            cols = R_log.indices[flat].astype(np.int64)
            w = R_log.data[flat].astype(np.float32).copy()
            if drop_pos is not None:  # leave the target out of its own history
                w[np.isin(flat, drop_pos)] = 0.0
            # normalise weights per bag -> weighted mean
            bag = np.repeat(np.arange(len(rows)), np.diff(np.append(offsets, len(flat))))
            sums = np.bincount(bag, weights=w, minlength=len(rows))
            w = w / np.maximum(sums[bag], 1e-9)
            return (
                torch.from_numpy(cols),
                item_id_t[torch.from_numpy(cols)],
                torch.from_numpy(offsets),
                torch.from_numpy(w.astype(np.float32)),
            )

        best_state, best_score, bad_epochs = None, -1.0, 0
        val_users = self._val_users(val_ground_truth)
        for epoch in range(1, self.max_epochs + 1):
            model.train()
            perm = rng.permutation(n_examples)
            total_loss, steps = 0.0, 0
            for s in range(0, n_examples, self.batch_size):
                b = perm[s : s + self.batch_size]
                pos, rows = ex_pos[b], ex_row[b]
                tgt = torch.from_numpy(R.indices[pos].astype(np.int64))
                tgt_ids = item_id_t[tgt].clone()
                tgt_ids[torch.rand(len(b)) < self.id_dropout] = UNKNOWN_ID
                u = model.users(*history_batch(rows, pos))
                v = model.items(tgt, tgt_ids)
                logits = (u @ v.T) / self.temperature - log_q_t[tgt][None, :]
                same = tgt[:, None] == tgt[None, :]
                logits = logits.masked_fill(same & ~torch.eye(len(b), dtype=torch.bool), float("-inf"))
                loss = nn.functional.cross_entropy(logits, torch.arange(len(b)))
                opt.zero_grad()
                loss.backward()
                opt.step()
                total_loss += float(loss)
                steps += 1

            self._export(model, item_id_idx, n_items)
            entry = {"epoch": epoch, "train_loss": round(total_loss / max(steps, 1), 4)}
            if val_users:
                score, pw, rb = self._select_on_validation(val_users)
                entry.update({"val_ndcg_at_10": round(score, 5), "pop_weight": pw, "revisit_boost": rb})
                if score > best_score:
                    best_score, bad_epochs = score, 0
                    best_state = (self.item_vectors.copy(), {k: v.copy() for k, v in self.user_params.items()}, pw, rb)
                    self.training_log.best_epoch = epoch
                else:
                    bad_epochs += 1
            self.training_log.per_epoch.append(entry)
            self.training_log.epochs_trained = epoch
            if self.verbose:
                print(f"  two-tower epoch {epoch}: {entry}  ({time.time() - t0:.0f}s)", flush=True)
            if val_users and bad_epochs >= self.patience:
                break

        if best_state is not None:
            self.item_vectors, self.user_params, self.pop_weight, self.revisit_boost = best_state
            self.training_log.best_val_ndcg_at_10 = round(best_score, 5)
            self.training_log.best_pop_weight = self.pop_weight
            self.training_log.best_revisit_boost = self.revisit_boost
        self.training_log.seconds = round(time.time() - t0, 1)
        return self

    def _export(self, model, item_id_idx: np.ndarray, n_items: int) -> None:
        """Copy the trained towers into numpy (item vectors precomputed; user tower weights kept)."""
        import torch

        model.eval()
        with torch.no_grad():
            cols = torch.arange(n_items)
            vecs = [model.items(cols[s : s + 8192], torch.from_numpy(item_id_idx[s : s + 8192])) for s in range(0, n_items, 8192)]
            self.item_vectors = torch.cat(vecs).numpy().astype(np.float32)
            lin1, lin2 = model.user_mlp[0], model.user_mlp[2]
            self.user_params = {
                "hist_id": model.hist_id.weight.numpy().copy(),
                "text": model.text.weight.numpy().copy(),
                "item_id_idx": item_id_idx.copy(),
                "W1": lin1.weight.numpy().T.copy(),
                "b1": lin1.bias.numpy().copy(),
                "W2": lin2.weight.numpy().T.copy(),
                "b2": lin2.bias.numpy().copy(),
            }

    # ------------------------------------------------------------------ serving (numpy only)
    def _user_vectors(self, rows: np.ndarray) -> np.ndarray:
        assert self.R_log_csr is not None
        flat, offsets = _gather_rows(self.R_log_csr.indptr, rows)
        bag = np.repeat(np.arange(len(rows)), np.diff(np.append(offsets, len(flat))))
        return self._tower_from_bags(self.R_log_csr.indices[flat], self.R_log_csr.data[flat], bag, len(rows))

    def _tower_from_bags(self, cols: np.ndarray, w: np.ndarray, bag: np.ndarray, n_bags: int) -> np.ndarray:
        """Numpy forward pass of the user tower over weighted item bags."""
        p = self.user_params
        w = w.astype(np.float32)
        sums = np.bincount(bag, weights=w, minlength=n_bags)
        w = (w / np.maximum(sums[bag], 1e-9)).astype(np.float32)
        id_part = np.zeros((n_bags, p["hist_id"].shape[1]), dtype=np.float32)
        text_part = np.zeros((n_bags, p["text"].shape[1]), dtype=np.float32)
        np.add.at(id_part, bag, p["hist_id"][p["item_id_idx"][cols]] * w[:, None])
        np.add.at(text_part, bag, p["text"][cols] * w[:, None])
        x = np.concatenate([id_part, text_part], axis=1)
        return _l2(_relu(x @ p["W1"] + p["b1"]) @ p["W2"] + p["b2"]).astype(np.float32)

    # ------------------------------------------------------------------ new users (cold start)
    def set_cold_user_context(self, user_category_map: dict[str, str]) -> None:
        """Register onboarding category answers for users with no history (same hook as the hybrid blend)."""
        self.cold_user_map = dict(user_category_map)

    def _cold_scores(self, category: str | None, n_seed: int, cat_bonus: float, pop_weight: float) -> np.ndarray:
        """
        Score the catalogue for a new user. With an onboarding category, the user tower is run on a pseudo-history:
        the category's `n_seed` most-interacted training items, weighted by log(1 + count). Items in the chosen
        category get `cat_bonus`. Without a category (or an unknown one) this is plain popularity.
        """
        cols = self.cat_to_cols.get(category or "")
        if cols is None or len(cols) == 0:
            return self.log_pop.copy()
        key = f"{category}|{n_seed}"
        if key not in self._cold_cache:
            seed = cols[np.argsort(-self.train_count[cols], kind="stable")[:n_seed]]
            w = np.log1p(self.train_count[seed]).astype(np.float32) + 1e-3
            self._cold_cache[key] = self._tower_from_bags(seed, w, np.zeros(len(seed), dtype=np.int64), 1)[0]
        scores = (self.item_vectors @ self._cold_cache[key]) / self.temperature + pop_weight * self.log_pop
        scores = scores.astype(np.float32)
        scores[cols] += cat_bonus
        return scores

    def tune_cold_start(
        self,
        val_cold_gt: dict[str, set[str]],
        val_cold_category: dict[str, str],
        n_seed_grid: tuple[int, ...] = (5, 20, 100, 500),
        cat_bonus_grid: tuple[float, ...] = (0.0, 2.0, 5.0, 1000.0),
        pop_weight_grid: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0),
        k: int = 10,
    ) -> dict:
        """Pick the new-user settings on VALIDATION new users (never on test). Returns the best setting."""
        discounts = 1.0 / np.log2(np.arange(2, k + 2))
        users = [(u, rel, val_cold_category.get(u)) for u, rel in val_cold_gt.items() if rel]
        self.cold_tuning = []
        best = {"ndcg_at_10": -1.0}
        for n_seed in n_seed_grid:
            for cb in cat_bonus_grid:
                for pw in pop_weight_grid:
                    cache: dict[str | None, list[str]] = {}
                    ndcgs = []
                    for _u, rel, cat in users:
                        if cat not in cache:
                            sc = self._cold_scores(cat, n_seed, cb, pw)
                            sc[~self.in_stock_mask] = -1e9
                            top = np.argpartition(sc, -k)[-k:]
                            cache[cat] = [self.col_to_item[c] for c in top[np.argsort(sc[top])[::-1]]]
                        hit = np.array([pid in rel for pid in cache[cat]], dtype=float)
                        ndcgs.append(float((hit * discounts).sum() / discounts[: min(len(rel), k)].sum()))
                    row = {"n_seed": n_seed, "cat_bonus": cb, "pop_weight": pw, "ndcg_at_10": round(float(np.mean(ndcgs)), 5)}
                    self.cold_tuning.append(row)
                    if row["ndcg_at_10"] > best["ndcg_at_10"]:
                        best = row
        self.cold_n_seed, self.cold_category_bonus, self.cold_pop_weight = best["n_seed"], best["cat_bonus"], best["pop_weight"]
        self.training_log.cold_start_selected = dict(best, validation_users=len(users))
        return best

    def _base_scores(self, U: np.ndarray, pop_weight: float) -> np.ndarray:
        return (U @ self.item_vectors.T) / self.temperature + pop_weight * self.log_pop[None, :]

    def _val_users(self, val_gt: dict[str, set[str]] | None) -> list[tuple[int, set[str]]]:
        if not val_gt:
            return []
        return [(self.user_to_row[u], items) for u, items in val_gt.items() if u in self.user_to_row and items]

    def _select_on_validation(self, val_users: list[tuple[int, set[str]]], k: int = 10) -> tuple[float, float, float]:
        """Return (best NDCG@10, pop_weight, revisit_boost) on the validation users for the current weights."""
        assert self.R_log_csr is not None
        rows = np.array([r for r, _ in val_users])
        U = self._user_vectors(rows)
        discounts = 1.0 / np.log2(np.arange(2, k + 2))
        purchased_cols = [
            [self.item_to_col[p] for p in self.user_seen_items.get(self._user_id_of_row(r), ()) if p in self.item_to_col]
            for r in rows
        ]
        best = (-1.0, 0.0, 0.0)
        for pw in self.pop_weight_grid:
            base = self._base_scores(U, pw).astype(np.float32)
            base[:, ~self.in_stock_mask] = -1e9
            for rb in self.revisit_boost_grid:
                ndcgs = []
                for i, (r, rel) in enumerate(val_users):
                    s = base[i].copy()
                    a, b = self.R_log_csr.indptr[r], self.R_log_csr.indptr[r + 1]
                    if rb:
                        s[self.R_log_csr.indices[a:b]] += rb * self.R_log_csr.data[a:b]
                    s[purchased_cols[i]] = -1e9
                    top = np.argpartition(s, -k)[-k:]
                    top = top[np.argsort(s[top])[::-1]]
                    hit = np.array([self.col_to_item[c] in rel for c in top], dtype=float)
                    idcg = discounts[: min(len(rel), k)].sum()
                    ndcgs.append(float((hit * discounts).sum() / idcg))
                score = float(np.mean(ndcgs))
                if score > best[0]:
                    best = (score, pw, rb)
        return best

    def _user_id_of_row(self, row: int) -> str:
        if not hasattr(self, "_row_to_user"):
            self._row_to_user = {r: u for u, r in self.user_to_row.items()}
        return self._row_to_user[row]

    def score_all_items_for_user(
        self,
        user_id: str,
        exclude_seen: bool = False,
        only_in_stock: bool = True,
        allowed_cols: np.ndarray | None = None,
    ) -> np.ndarray:
        assert self.R_log_csr is not None
        row = self.user_to_row.get(user_id)
        if row is None or self.R_log_csr.indptr[row] == self.R_log_csr.indptr[row + 1]:
            # no history: onboarding category through the user tower if known, else popularity
            scores = self._cold_scores(
                self.cold_user_map.get(user_id), self.cold_n_seed, self.cold_category_bonus, self.cold_pop_weight
            )
        else:
            scores = self._base_scores(self._user_vectors(np.array([row])), self.pop_weight)[0].astype(np.float32)
            a, b = self.R_log_csr.indptr[row], self.R_log_csr.indptr[row + 1]
            seen_cols = self.R_log_csr.indices[a:b]
            if exclude_seen:
                scores[seen_cols] = -1e9
            elif self.revisit_boost:
                scores[seen_cols] += self.revisit_boost * self.R_log_csr.data[a:b]
        for pid in self.user_seen_items.get(user_id, ()):
            c = self.item_to_col.get(pid)
            if c is not None:
                scores[c] = -1e9
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
        scores = self.score_all_items_for_user(user_id, exclude_seen=exclude_seen, only_in_stock=only_in_stock)
        top = np.argpartition(scores, -k)[-k:]
        top = top[np.argsort(scores[top])[::-1]]
        return [(self.col_to_item[int(i)], float(scores[i])) for i in top]
