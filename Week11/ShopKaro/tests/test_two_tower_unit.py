"""Fast unit tests for the neural two-tower on a tiny synthetic catalogue (no database needed)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

pytest.importorskip("torch")

from shopkaro.recommendations.two_tower import TwoTowerRecommender  # noqa: E402


def _toy_data(n_users: int = 300, n_items: int = 40, seed: int = 0):
    """Two categories; each user browses only one category, so the model has a clear pattern to learn."""
    rng = np.random.default_rng(seed)
    cats = np.array(["Phones"] * (n_items // 2) + ["Lawn"] * (n_items // 2))
    catalogue = pd.DataFrame(
        {
            "product_id": [f"P{i:03d}" for i in range(n_items)],
            "title": [f"item {i}" for i in range(n_items)],
            "category": cats,
            "brand": "B",
            "price_pkr": rng.uniform(500, 50000, n_items),
            "in_stock": True,
        }
    )
    rows, cols = [], []
    for u in range(n_users):
        pool = np.arange(n_items // 2) + (0 if u % 2 == 0 else n_items // 2)
        for c in rng.choice(pool, size=4, replace=False):
            rows.append(u)
            cols.append(int(c))
    R = sp.csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(n_users, n_items))
    user_to_row = {f"U{u}": u for u in range(n_users)}
    item_to_col = {pid: i for i, pid in enumerate(catalogue["product_id"])}
    emb = rng.normal(size=(n_items, 16)).astype(np.float32)
    emb[: n_items // 2, 0] += 3.0  # text embeddings also separate the two categories
    return catalogue, user_to_row, item_to_col, list(catalogue["product_id"]), R, emb


def _fit(**kw) -> TwoTowerRecommender:
    catalogue, u2r, i2c, c2i, R, emb = _toy_data()
    model = TwoTowerRecommender(dim=16, id_dim=8, hidden=32, batch_size=64, max_epochs=3, verbose=False, **kw)
    return model.fit_from_sparse(catalogue, u2r, i2c, c2i, R, {}, emb, val_ground_truth=None)


def test_learns_category_pattern_and_respects_filters() -> None:
    model = _fit()
    assert model.item_vectors.shape == (40, 16)
    recs = [pid for pid, _ in model.recommend_ids("U0", k=5, exclude_seen=True)]  # U0 browses Phones (P000-P019)
    assert sum(int(pid[1:]) < 20 for pid in recs) >= 4
    seen = {model.col_to_item[c] for c in model.R_log_csr[0].indices}
    assert not seen & set(recs)  # exclude_seen honoured


def test_cold_user_uses_onboarding_category() -> None:
    model = _fit()
    model.cold_category_bonus = 0.0  # rely on the tower alone, not the category bonus
    model.set_cold_user_context({"NEW-1": "Lawn"})
    recs = [pid for pid, _ in model.recommend_ids("NEW-1", k=5)]
    assert sum(int(pid[1:]) >= 20 for pid in recs) >= 4
    # Unknown user without onboarding -> popularity fallback, still k valid items
    assert len(model.recommend_ids("NEW-2", k=5)) == 5


def test_same_seed_same_vectors() -> None:
    a, b = _fit(seed=7), _fit(seed=7)
    np.testing.assert_allclose(a.item_vectors, b.item_vectors, atol=1e-5)
