from vapi_integration.customer_learning import (
    ExplainablePreferenceRanker,
    PreferenceProfile,
    approved_learning_dataset,
    build_profile,
    customer_key_for_phone,
    evaluate_ranker,
    extract_features,
)


def test_customer_key_is_stable_without_exposing_phone():
    key = customer_key_for_phone("+92 300 1234567", salt="test-salt")
    assert key == customer_key_for_phone("923001234567", salt="test-salt")
    assert "923001234567" not in key


def test_features_and_dataset_only_include_approved_records():
    approved = {
        "review_status": "approved",
        "call_id": "call-1",
        "customer_key": "customer-1",
        "messages": [{"role": "user", "content": "DHA Phase 6 Lahore 3 bedroom apartment budget 2 crore parking"}],
        "features": {"viewed_property_ids": ["p1"], "rejected_property_ids": ["p2"]},
    }
    features = extract_features(approved)
    assert features["city"] == "Lahore"
    assert features["area"] == "DHA Phase 6"
    assert features["budget"] == 20_000_000
    assert features["bedrooms"] == 3
    assert "parking" in features["amenities"]

    dataset = approved_learning_dataset([approved, {"review_status": "unreviewed", "customer_key": "customer-1"}])
    assert len(dataset) == 1
    assert build_profile(dataset, "customer-1").area == "DHA Phase 6"


def test_ranker_is_explainable_and_preserves_candidate_facts():
    profile = PreferenceProfile(customer_key="customer-1", city="Lahore", area="DHA", budget=50_000_000, rejected_property_ids=["p2"])
    candidates = [
        {"property_id": "p2", "city": "Lahore", "area": "DHA", "price": 40_000_000, "verified_on": "2026-01-01"},
        {"property_id": "p1", "city": "Lahore", "area": "DHA Phase 6", "price": 40_000_000, "verified_on": "2026-01-01"},
    ]

    ranked = ExplainablePreferenceRanker().rank(candidates, profile)
    assert [item["property_id"] for item in ranked] == ["p1", "p2"]
    assert ranked[0]["verified_on"] == "2026-01-01"
    assert "area match" in ranked[0]["_ml_reasons"]


def test_ranker_evaluation_reports_quality_metrics():
    profile = PreferenceProfile(customer_key="c", city="Lahore", amenities=["parking"])
    metrics = evaluate_ranker(ExplainablePreferenceRanker(), [{
        "profile": profile,
        "expected_property_ids": ["p1"],
        "candidates": [
            {"property_id": "p1", "city": "Lahore", "amenities": ["Parking"]},
            {"property_id": "p2", "city": "Karachi", "amenities": []},
        ],
    }])
    assert metrics["cases"] == 1.0
    assert metrics["top1_hit_rate"] == 1.0
    assert metrics["mean_reciprocal_rank"] == 1.0
