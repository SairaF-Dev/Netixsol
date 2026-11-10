"""
Tests for real-time recommendation serving (Day 5 Task 1 on top of the Day 2 item-CF model):
the served model matches the evaluated model, personalisation, cold start, onboarding,
live session clicks, business rules, cache invalidation and the <100 ms latency target.
"""

from __future__ import annotations

import statistics
import time

from fastapi.testclient import TestClient

from shopkaro.api.main import app, serving_container

LAWN_USER = "USR-928443"  # Eid & Festive Lawn Shopper
PHONE_USER = "USR-368401"  # smartphone-heavy history
KIDS_USER = "USR-1398811"  # kids & school supplies history


def _client() -> TestClient:
    serving_container.ensure_initialized()
    return TestClient(app)


def _ids(body: dict) -> list[str]:
    return [r["product_id"] for r in body["recommendations"]]


def test_served_model_scores_exactly_like_the_evaluated_item_cf() -> None:
    _client()
    rt = serving_container.realtime_recommender
    assert rt is not None
    for uid in (LAWN_USER, PHONE_USER, KIDS_USER):
        assert rt.recommend_ids(uid, k=20) == rt.cf.recommend_ids(uid, k=20)


def test_different_users_get_different_homepages() -> None:
    client = _client()
    pages = {u: client.get(f"/recommendations/{u}?top_k=10").json() for u in (LAWN_USER, PHONE_USER, KIDS_USER)}
    for body in pages.values():
        assert body["is_cold_start"] is False
        assert body["ranking_strategy"].startswith("item_cf_realtime")
        assert body["count"] == 10
    assert pages[LAWN_USER]["favorite_category"] == "Women's Lawn & Unstitched"
    assert pages[PHONE_USER]["favorite_category"] == "Smartphones & Accessories"
    assert pages[KIDS_USER]["favorite_category"] == "Kids & School Supplies"
    a, b = set(_ids(pages[LAWN_USER])), set(_ids(pages[PHONE_USER]))
    assert len(a & b) <= 3, "two different shoppers should not see the same homepage"


def test_business_rules_hold() -> None:
    client = _client()
    rt = serving_container.realtime_recommender
    assert rt is not None
    for uid in (LAWN_USER, PHONE_USER, KIDS_USER, "brand-new-visitor"):
        body = client.get(f"/recommendations/{uid}?top_k=10").json()
        purchased = rt.cf.user_seen_items.get(uid, set())
        brands: dict[str, int] = {}
        for r in body["recommendations"]:
            assert r["stock_qty"] > 0
            assert r["product_id"] not in purchased
            brands[r["brand"]] = brands.get(r["brand"], 0) + 1
            assert r["reason_type"] in {"revisit", "similar_to_history", "popular_in_category"}
            assert r["explanation_roman_urdu"]
        assert max(brands.values()) <= 2


def test_explanations_name_a_real_history_item() -> None:
    body = _client().get(f"/recommendations/{LAWN_USER}?top_k=10").json()
    rt = serving_container.realtime_recommender
    assert rt is not None
    vec = rt.user_vector(LAWN_USER)
    history = {rt.cf.col_to_item[int(c)] for c in vec.indices}
    for r in body["recommendations"]:
        if r["reason_type"] in ("revisit", "similar_to_history"):
            assert r["because_of_product_id"] in history


def test_cold_start_and_onboarding() -> None:
    client = _client()
    cold = client.get("/recommendations/cold-visitor-x?top_k=8").json()
    assert cold["is_cold_start"] is True and cold["count"] == 8
    assert cold["ranking_strategy"].startswith("cold_start_popularity")

    r = client.post("/onboarding/cold-visitor-y", json={"categories": ["Kids & School Supplies"]})
    assert r.status_code == 200
    body = client.get("/recommendations/cold-visitor-y?top_k=8").json()
    assert body["ranking_strategy"].startswith("cold_start_onboarding")
    assert {x["category"] for x in body["recommendations"]} == {"Kids & School Supplies"}

    assert client.post("/onboarding/cold-visitor-z", json={"categories": ["Spaceships"]}).status_code == 422


def test_live_clicks_update_recommendations_and_invalidate_cache() -> None:
    client = _client()
    uid = "live-click-visitor"
    before = client.get(f"/recommendations/{uid}?top_k=10").json()
    assert before["is_cold_start"] is True
    assert client.get(f"/recommendations/{uid}?top_k=10").json()["cache_hit"] is True

    r = client.post("/events", json={"user_id": uid, "product_id": "SK-00013", "event_type": "addtocart"})
    assert r.status_code == 200 and r.json()["session_events"] == 1

    after = client.get(f"/recommendations/{uid}?top_k=10").json()
    assert after["cache_hit"] is False, "a new click must bypass the cached homepage"
    assert after["is_cold_start"] is False and after["session_events"] == 1
    assert after["favorite_category"] == "Smartphones & Accessories"
    assert _ids(after) != _ids(before)
    assert any(x["because_of_product_id"] == "SK-00013" for x in after["recommendations"])

    # Buying it removes it from the list
    client.post("/events", json={"user_id": uid, "product_id": "SK-00013", "event_type": "transaction"})
    assert "SK-00013" not in _ids(client.get(f"/recommendations/{uid}?top_k=10").json())

    assert client.post("/events", json={"user_id": uid, "product_id": "SK-00013", "event_type": "like"}).status_code == 422
    assert client.post("/events", json={"user_id": uid, "product_id": "SK-99999999"}).status_code == 404


def test_recommendation_latency_under_100ms() -> None:
    client = _client()
    uncached, cached = [], []
    for i in range(20):
        uid = [LAWN_USER, PHONE_USER, KIDS_USER][i % 3]
        t0 = time.perf_counter()
        client.get(f"/recommendations/{uid}?top_k=10&occasion=lat{i}")  # unique key -> computed
        uncached.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        client.get(f"/recommendations/{uid}?top_k=10&occasion=lat{i}")  # same key -> cache
        cached.append((time.perf_counter() - t0) * 1000)
    p95 = lambda xs: statistics.quantiles(xs, n=20)[-1]  # noqa: E731
    assert p95(cached) < 100, f"cached p95 {p95(cached):.1f} ms"
    assert p95(uncached) < 100, f"uncached p95 {p95(uncached):.1f} ms"
