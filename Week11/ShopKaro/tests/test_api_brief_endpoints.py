"""
Contract tests for the exact endpoint paths required by the Week 11 brief (Day 5, Task 1):
GET /recommendations/{user_id}, GET /similar/{product_id}, GET /bought-together/{product_id},
GET /search, POST /assistant/chat, GET /forecast/{product_id}, GET /inventory/alerts,
GET /reviews/summary/{product_id}.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from shopkaro.api.main import app, serving_container


def _client() -> TestClient:
    serving_container.ensure_initialized()
    return TestClient(app)


def test_brief_paths_are_registered_in_openapi() -> None:
    paths = set(_client().get("/openapi.json").json()["paths"])
    required = {
        "/recommendations/{user_id}",
        "/similar/{product_id}",
        "/bought-together/{product_id}",
        "/search",
        "/assistant/chat",
        "/forecast/{product_id}",
        "/inventory/alerts",
        "/reviews/summary/{product_id}",
    }
    assert required <= paths, f"missing: {required - paths}"


def test_recommendations_warm_vs_cold_and_cache() -> None:
    client = _client()
    warm = client.get("/recommendations/USR-928443?top_k=5").json()
    assert warm["is_cold_start"] is False and warm["count"] == 5
    assert client.get("/recommendations/USR-928443?top_k=5").json()["cache_hit"] is True

    cold = client.get("/recommendations/new-visitor-abc?top_k=5").json()
    assert cold["is_cold_start"] is True and cold["count"] == 5


def test_similar_products_are_real_in_stock_catalogue_items() -> None:
    client = _client()
    body = client.get("/similar/SK-00013?top_k=8").json()
    assert body["count"] == 8
    ids = [r["product_id"] for r in body["results"]]
    assert "SK-00013" not in ids, "source product must not be its own neighbour"
    assert len(set(ids)) == len(ids)
    sims = [r["similarity"] for r in body["results"]]
    assert sims == sorted(sims, reverse=True)
    for r in body["results"]:
        assert r["product_id"] in serving_container.catalogue_by_sku
        assert r["stock_qty"] > 0

    assert client.get("/similar/SK-99999999").status_code == 404


def test_bought_together_only_reports_measured_statistics() -> None:
    body = _client().get("/bought-together/SK-00013?top_k=5").json()
    assert body["count"] >= 1
    for r in body["results"]:
        assert r["product_id"] != "SK-00013"
        assert r["product_id"] in serving_container.catalogue_by_sku
        if r["mined_from_data"]:
            assert r["confidence"] is not None and r["lift"] is not None
        else:
            assert r["confidence"] is None and r["lift"] is None


def test_inventory_alerts_filter_and_sort() -> None:
    client = _client()
    all_alerts = client.get("/inventory/alerts?limit=500").json()
    assert all_alerts["total_tracked_skus"] == sum(all_alerts["counts_by_status"].values())

    crit = client.get("/inventory/alerts?status=critical_stockout_risk&limit=20").json()
    assert crit["count"] > 0
    assert all(a["alert_status"] == "CRITICAL_STOCKOUT_RISK" for a in crit["alerts"])
    days = [a["days_of_inventory_p50"] for a in crit["alerts"]]
    assert days == sorted(days)

    assert client.get("/inventory/alerts?status=bogus").status_code == 422


def test_assistant_chat_and_review_summary_paths() -> None:
    client = _client()
    chat = client.post(
        "/assistant/chat",
        json={"message": "eid ke liye lawn suit under 5000", "session_id": "brief-test", "user_id": 15442},
    )
    assert chat.status_code == 200
    assert chat.json()["assistant_response"]

    rev = client.get("/reviews/summary/SK-00045")
    assert rev.status_code == 200 and rev.json()["product_id"] == "SK-00045"


def test_ratings_are_real_or_absent() -> None:
    """Unreviewed products must report no rating (null / 0 reviews), never an invented default."""
    import duckdb

    from shopkaro.config.settings import settings

    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    reviewed = dict(con.execute("SELECT product_id, avg_rating FROM review_intelligence_summary").fetchall())
    unreviewed = con.execute(
        "SELECT product_id FROM product_catalogue WHERE product_id NOT IN "
        "(SELECT product_id FROM review_intelligence_summary) ORDER BY product_id LIMIT 1"
    ).fetchone()[0]
    con.close()

    client = _client()
    summary = client.get(f"/reviews/summary/{unreviewed}").json()
    assert summary["avg_rating"] is None and summary["genuine_review_count"] == 0

    results = client.get("/search", params={"q": "lawn suit", "top_k": 10}).json()["results"]
    assert results
    for r in results:
        if r["product_id"] in reviewed:
            assert r["avg_rating"] == pytest.approx(round(reviewed[r["product_id"]], 2)) and r["review_count"] > 0
        else:
            assert r["avg_rating"] is None and r["review_count"] == 0
