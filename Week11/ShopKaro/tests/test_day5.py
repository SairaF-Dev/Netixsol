"""
Verification test suite for Day 5 — Tasks 1, 2 & 3:
- Task 1: Real-Time FastAPI Serving (<100ms SLA, HybridTTLCache, 6 endpoint families)
- Task 2: Statistical A/B Testing Framework & 1-Page Ship/No-Ship Decision Report
- Task 3: 3-View Interactive Streamlit Dashboard & Containerization (Dockerfile / docker-compose.yml)
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from shopkaro.ab_testing.experiment import ABTestingFramework
from shopkaro.api.main import app, serving_container
from shopkaro.config.settings import settings
from shopkaro.dashboard.app import analyze_live_review_text, load_dashboard_snapshot


def test_day5_fastapi_serving_ab_testing_and_dashboard() -> None:
    serving_container.ensure_initialized()
    # Earlier tests (e.g. dashboard renders) may have cached the same recommendation; this test checks miss -> hit.
    serving_container.cache.clear()
    client = TestClient(app)

    # 1. Test /health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    h_json = r_health.json()
    assert h_json["status"] == "healthy"
    assert h_json["duckdb_connected"] is True
    assert h_json["tables_count"] >= 15

    # 2. Test /recommend/{user_id} (Warm User + Cache Hit + Cold-Start User)
    r_rec1 = client.get("/recommend/USR-928443?top_k=6&occasion=Eid")
    assert r_rec1.status_code == 200
    rec1 = r_rec1.json()
    assert rec1["count"] == 6
    assert rec1["is_cold_start"] is False
    assert rec1["cache_hit"] is False
    for item in rec1["recommendations"]:
        assert item["stock_qty"] > 0
        assert "explanation_roman_urdu" in item

    r_rec2 = client.get("/recommend/USR-928443?top_k=6&occasion=Eid")
    assert r_rec2.status_code == 200
    assert r_rec2.json()["cache_hit"] is True

    r_rec_cold = client.get("/recommend/999999?top_k=5")
    assert r_rec_cold.status_code == 200
    assert r_rec_cold.json()["is_cold_start"] is True
    assert r_rec_cold.json()["count"] == 5

    # 3. Test /search (Anonymous & Personalized)
    r_search = client.get("/search?q=shaadi+ke+liye+red+lehenga+20+hazaar+tak&top_k=5")
    assert r_search.status_code == 200
    s_json = r_search.json()
    assert s_json["count"] == 5
    assert s_json["parsed_constraints"]["max_price_pkr"] == 20000.0
    for item in s_json["results"]:
        assert item["price_pkr"] <= 20000.0

    # Known shopper: collaborative re-ranking, budget still respected
    r_search_pers = client.get("/search?q=sasta+gaming+phone+under+50000&top_k=5&user_id=USR-928443")
    assert r_search_pers.status_code == 200
    pers_json = r_search_pers.json()
    assert pers_json["personalized"] is True and pers_json["personalization_method"] == "item_cf_rerank"
    assert all(item["price_pkr"] <= 50000.0 for item in pers_json["results"])
    # Unknown user id: plain search, not silently personalised as somebody else
    r_unknown = client.get("/search?q=sasta+gaming+phone+under+50000&top_k=5&user_id=15442").json()
    assert r_unknown["personalized"] is False and r_unknown["personalization_method"] is None

    # 4. Test /forecast/{product_id}
    r_fc = client.get("/forecast/SK-00001")
    assert r_fc.status_code == 200
    fc_json = r_fc.json()
    assert fc_json["product_id"] == "SK-00001"
    assert fc_json["horizon_days"] == 30
    assert len(fc_json["daily_forecasts"]) == 30
    assert fc_json["forecast_30d_p10_units"] <= fc_json["forecast_30d_p50_units"] <= fc_json["forecast_30d_p90_units"]

    # 5. Test POST /chat (Multi-turn UrduLish Assistant + Hallucination Audit)
    r_chat1 = client.post(
        "/chat",
        json={
            "message": "Ammi ke liye Eid gift chahiye, 3000 tak",
            "session_id": "pytest-day5-session",
            "user_id": 15442,
        },
    )
    assert r_chat1.status_code == 200
    c1 = r_chat1.json()
    assert c1["hallucination_audit"]["passed_zero_hallucination_check"] is True
    assert len(c1["tool_calls"]) >= 1

    r_chat2 = client.post(
        "/chat",
        json={
            "message": "Pehla wala cart mein daal do",
            "session_id": "pytest-day5-session",
            "user_id": 15442,
        },
    )
    assert r_chat2.status_code == 200
    c2 = r_chat2.json()
    assert c2["hallucination_audit"]["passed_zero_hallucination_check"] is True
    assert len(c2["cart"]["items"]) >= 1

    # 6. Test /reviews/{product_id}
    # Pick a courier-penalised product from the data instead of hardcoding an SK code
    # (non-hero SK codes change whenever the catalogue is regenerated).
    penalised_sku = next(
        sku for sku, rec in sorted(serving_container.review_summary_map.items())
        if bool(rec["is_unfairly_penalized_by_courier"])
    )
    r_rev = client.get(f"/reviews/{penalised_sku}")
    assert r_rev.status_code == 200
    rev_json = r_rev.json()
    assert rev_json["product_id"] == penalised_sku
    assert "quality" in rev_json["aspect_scores"]
    assert rev_json["is_unfairly_penalized_by_courier"] is True

    # 7. Test /metrics & <100ms SLA
    r_metrics = client.get("/metrics")
    assert r_metrics.status_code == 200
    m_json = r_metrics.json()
    assert m_json["latency"]["overall"]["sla_p95_under_100ms_met"] is True
    assert m_json["cache"]["hits"] >= 1

    # 8. Task 2 (A/B test) is covered by tests/test_ab_experiment.py; here only the power formula
    power = ABTestingFramework.compute_required_sample_size(
        baseline_rate=0.032, relative_mde=0.15, alpha=0.05, power=0.80
    )
    assert 20000 <= power["required_n_per_arm"] <= 25000

    # 9. Test Task 3: 3-View Streamlit Dashboard Snapshot, Live Review Sandbox & Docker files
    snap = load_dashboard_snapshot()
    assert len(snap["segments_summary"]) == 5
    assert len(snap["inventory_alerts"]) == 300
    # Dashboard must list every courier-penalised product in the review summary (count depends on data)
    n_penalised = sum(
        bool(r["is_unfairly_penalized_by_courier"]) for r in serving_container.review_summary_map.values()
    )
    assert n_penalised > 0
    assert len(snap["unfairly_penalized_gems"]) == n_penalised

    live_rev = analyze_live_review_text(
        "Product bohot acha hai lekin delivery 10 din late aayi", rating=3
    )
    assert live_rev["is_contrastive_mixed"] is True
    assert live_rev["aspects"]["quality"] == 1
    assert live_rev["aspects"]["delivery"] == -1
    assert live_rev["is_fake_spam"] is False

    assert (settings.project_root / "Dockerfile").exists()
    assert (settings.project_root / "docker-compose.yml").exists()
