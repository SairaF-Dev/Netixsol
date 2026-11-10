"""Personalised search: evaluation protocol and the collaborative re-ranker used in serving."""

from __future__ import annotations

import duckdb
import pytest

from shopkaro.api.main import serving_container
from shopkaro.config.settings import settings
from shopkaro.search import personalization_eval as pe


def test_ndcg_and_split_helpers() -> None:
    assert pe._ndcg(["a", "b"], {"a": 3}) == pytest.approx(1.0)
    assert pe._ndcg(["x", "a"], {"a": 1}) < 1.0
    assert pe._ndcg(["x"], {"a": 1}) == 0.0
    assert pe._half("USR-1") == pe._half("USR-1")  # deterministic
    halves = {pe._half(f"USR-{i}") for i in range(50)}
    assert halves == {"dev", "holdout"}


def test_queries_use_only_test_window_relevance() -> None:
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    user = con.execute(
        "SELECT user_id FROM test_interactions GROUP BY user_id ORDER BY COUNT(*) DESC, user_id LIMIT 1"
    ).fetchone()[0]
    queries = pe.build_queries(con, {user})
    test_items = {r[0] for r in con.execute("SELECT product_id FROM test_interactions WHERE user_id = ?", [user]).fetchall()}
    con.close()
    assert len(queries) > 0
    for q in queries.itertuples():
        assert set(q.relevant) <= test_items
        assert set(q.relevant.values()) <= {1, 2, 3}


def test_cf_rerank_reorders_search_candidates_only() -> None:
    """Personalised results must come from the hybrid candidates (same query constraints, e.g. budget)."""
    serving_container.ensure_initialized()
    pers = serving_container.personalizer
    user = "USR-928443"
    assert pers.cf_recommender is not None and pers.cf_recommender.is_known(user)
    query = "lawn suit 5000 tak"
    results, parsed = pers.search_personalized(query, user_id=user, k=10)
    pool_ids = {r["product_id"] for r in pers.search_engine.search_hybrid(query, k=pers.cf_pool, only_in_stock=True)[0]}
    assert results and {r["product_id"] for r in results} <= pool_ids
    assert all(r["price_pkr"] <= 5000 for r in results)
    assert [r["rank"] for r in results] == list(range(1, len(results) + 1))
    assert all(r["personalized_for"] == "your browsing history (item-CF)" for r in results)
