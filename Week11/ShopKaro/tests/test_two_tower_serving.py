"""
Serving the neural two-tower behind RECOMMENDER=two_tower.

Unit tests use a tiny trained model (no database). The API test uses the real batch artifact
(models/two_tower_serving.joblib from `scripts/precompute_recommendations.py --two-tower`) and is skipped without it.
"""

from __future__ import annotations

import dataclasses
import statistics
import time

import numpy as np
import pytest

from shopkaro.recommendations.serving import RealtimeTwoTowerRecommender, SessionEventStore

torch = pytest.importorskip("torch")

from tests.test_two_tower_unit import _fit  # noqa: E402


def _rt() -> RealtimeTwoTowerRecommender:
    return RealtimeTwoTowerRecommender(_fit(), SessionEventStore())


def test_without_clicks_serving_equals_the_evaluated_model() -> None:
    rt = _rt()
    rt.tt.revisit_boost = 2.0
    for uid in ("U0", "U1", "U7"):
        assert rt.recommend_ids(uid, k=10) == rt.tt.recommend_ids(uid, k=10)


def test_live_clicks_move_a_new_visitor_and_purchases_are_removed() -> None:
    rt = _rt()
    uid = "visitor-1"
    assert not rt.is_known(uid)
    for pid in ("P020", "P021", "P022"):  # Lawn items
        rt.events.add(uid, pid, "view")
    assert rt.is_known(uid)
    recs = [pid for pid, _ in rt.recommend_ids(uid, k=5, exclude_seen=True)]
    assert sum(int(pid[1:]) >= 20 for pid in recs) >= 4
    reasons = rt.explain_many(uid, recs)
    assert all(r["because_of"] in {"P020", "P021", "P022"} for r in reasons.values() if r["reason_type"] != "popular_in_category")
    assert rt.favourite_category(rt.user_vector(uid)) == "Lawn"

    rt.events.add(uid, "P020", "transaction")
    assert "P020" not in [pid for pid, _ in rt.recommend_ids(uid, k=40)]


def test_onboarding_is_restricted_to_chosen_categories() -> None:
    rt = _rt()
    rt.events.set_preferences("new-1", ["Phones"])
    recs = rt.recommend_ids("new-1", k=8)
    assert len(recs) == 8 and all(int(pid[1:]) < 20 for pid, _ in recs)
    assert len(rt.recommend_ids("new-2", k=8)) == 8  # no onboarding: popularity
    assert all(r["reason_type"] == "popular_in_category" for r in rt.explain_many("new-2", ["P000"]).values())


def test_history_with_clicks_matches_stored_row_transform() -> None:
    rt = _rt()
    cols0, w0 = rt._history("U0")
    rt.events.add("U0", "P039", "view")
    cols1, w1 = rt._history("U0")
    assert set(cols1.tolist()) == set(cols0.tolist()) | {39}
    old = dict(zip(cols1.tolist(), w1.tolist()))
    np.testing.assert_allclose([old[c] for c in cols0.tolist()], w0, rtol=1e-5)


def test_api_serves_two_tower_when_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    import shopkaro.api.main as api
    from shopkaro.recommendations.serving import TWO_TOWER_ARTIFACT_PATH

    if not TWO_TOWER_ARTIFACT_PATH.exists():
        pytest.skip("no two-tower artifact; run scripts/precompute_recommendations.py --two-tower")
    monkeypatch.setattr(api, "settings", dataclasses.replace(api.settings, recommender="two_tower"))
    container = api.ShopKaroServingContainer()
    monkeypatch.setattr(api, "serving_container", container)
    container.ensure_initialized()
    assert container.recommender_info["serving_recommender"] == "two_tower", container.recommender_info
    # The model is part of the cache key, so lists cached by an item-CF process (Redis outlives it) are not reused
    assert container.model_tag.startswith("two_tower@")
    client = TestClient(api.app)

    body = client.get("/recommendations/USR-928443?top_k=10").json()
    assert body["ranking_strategy"] == "two_tower_realtime+business_reranker"
    assert body["count"] == 10 and body["favorite_category"] == "Women's Lawn & Unstitched"
    brands: dict[str, int] = {}
    for r in body["recommendations"]:
        assert r["stock_qty"] > 0
        brands[r["brand"]] = brands.get(r["brand"], 0) + 1
    assert max(brands.values()) <= 2

    client.post("/onboarding/tt-new", json={"categories": ["Kids & School Supplies"]})
    cold = client.get("/recommendations/tt-new?top_k=8").json()
    assert cold["ranking_strategy"] == "cold_start_onboarding_two_tower+business_reranker"
    assert {x["category"] for x in cold["recommendations"]} == {"Kids & School Supplies"}

    # Latency target (<100 ms p95), uncached requests
    times = []
    for i in range(30):
        uid = ["USR-928443", "USR-368401", "USR-1398811"][i % 3]
        t0 = time.perf_counter()
        client.get(f"/recommendations/{uid}?top_k=10&occasion=tt{i}")
        times.append((time.perf_counter() - t0) * 1000)
    p95 = statistics.quantiles(times, n=20)[-1]
    assert p95 < 100, f"uncached two-tower p95 {p95:.1f} ms"
