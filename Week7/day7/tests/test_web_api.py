from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from ml.model_service import PropertyPreferenceModelService
from vapi_integration.customer_repository import Customer
from vapi_integration.preference_repository import CustomerPreferences
from web_api.app import create_app
from web_api.services import WebServices


CUSTOMER_ID = str(uuid4())


def property_row(property_id="P-1", price=10_000_000):
    return {
        "property_id": property_id, "property_name": f"Home {property_id}",
        "city": "Lahore", "area": "DHA", "price": price, "currency": "PKR",
        "bedrooms": 3, "bathrooms": 2, "property_type": "Apartment",
        "purpose": "purchase", "amenities": ["Parking"], "available": True,
        "status": "Ready",
    }


class Customers:
    def __init__(self):
        self.customer = Customer(CUSTOMER_ID, "Ali", "ali@example.com", "+923001234567")
        self.preferences = CustomerPreferences(CUSTOMER_ID, city="Lahore", area="DHA", budget_max=20_000_000, bedrooms=3, property_type="Apartment", purpose="purchase", amenities=["Parking"])

    def create_or_get_test_customer(self, **kwargs):
        return SimpleNamespace(customer=self.customer, preferences=self.preferences)

    def resolve_for_customer_id(self, customer_id):
        if customer_id != CUSTOMER_ID:
            return SimpleNamespace(customer=None, preferences=None)
        return SimpleNamespace(customer=self.customer, preferences=self.preferences)

    def update_preferences(self, customer_id, updates):
        for key, value in updates.items():
            setattr(self.preferences, key, value)
        return self.preferences


class Properties:
    def __init__(self):
        self.rows = [property_row("P-1", 10_000_000), property_row("P-2", 12_000_000)]
        self.search_calls = []

    def list_available_cities(self):
        return ["Lahore"]

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return [dict(row) for row in self.rows]

    def get_property(self, property_id):
        return next((dict(row) for row in self.rows if row["property_id"] == property_id), None)


class Interactions:
    def __init__(self):
        self.events = []

    def record_interaction(self, **kwargs):
        self.events.append(kwargs)
        return SimpleNamespace(interaction_id=str(uuid4()), **{key: kwargs[key] for key in ("customer_id", "property_id", "action")})


class Deterministic:
    def rank(self, rows, profile):
        return list(reversed(rows))


class ML:
    def __init__(self, mode="off", fail=False):
        self.mode, self.fail = mode, fail

    def rank_properties(self, rows, profile):
        if self.fail:
            return rows
        return list(reversed(rows)) if self.mode == "active_dev" else rows

    def health(self):
        return {"mode": self.mode, "loaded": self.mode != "off"}


class Appointments:
    def __init__(self):
        self.calls = []

    async def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        return 201 if method == "POST" else 200, {"ok": True}


def make_client(mode="off", ml=None):
    customers, properties, interactions, appointments = Customers(), Properties(), Interactions(), Appointments()
    services = WebServices(customers, properties, interactions, Deterministic(), ml or ML(mode), appointments)
    return TestClient(create_app(services)), services


def test_customer_creation_reuse_and_lookup():
    client, _ = make_client()
    body = {"full_name": "Ali", "email": "ALI@example.com", "phone": "0300-1234567"}
    first = client.post("/api/customers", json=body)
    second = client.post("/api/customers", json=body)
    assert first.status_code == second.status_code == 201
    assert first.json()["customer_id"] == second.json()["customer_id"]
    assert client.get(f"/api/customers/{CUSTOMER_ID}").status_code == 200
    assert client.get(f"/api/customers/{uuid4()}").status_code == 404


def test_preference_get_save_and_partial_update_preserves_omitted_values():
    client, services = make_client()
    response = client.patch(f"/api/customers/{CUSTOMER_ID}/preferences", json={"area": "Gulberg"})
    assert response.status_code == 200
    assert response.json()["area"] == "Gulberg"
    assert response.json()["city"] == "Lahore"
    assert services.customers.preferences.budget_max == 20_000_000
    assert client.get(f"/api/customers/{CUSTOMER_ID}/preferences").status_code == 200


def test_preference_cross_field_budget_validation():
    client, _ = make_client()
    assert client.patch(f"/api/customers/{CUSTOMER_ID}/preferences", json={"budget_min": 30_000_000}).status_code == 422


def test_verified_property_search_uses_repository_and_filters_internal_fields():
    client, services = make_client()
    services.properties.rows[0]["_ml_probability"] = 0.99
    response = client.post("/api/properties/search", json={"customer_id": CUSTOMER_ID, "limit": 5})
    assert response.status_code == 200
    assert services.properties.search_calls[0]["city"] == "Lahore"
    assert "_ml_probability" not in response.text
    assert response.json()[0]["property_id"] == "P-1"


def test_recommendation_modes_and_same_verified_candidate_pool():
    expected = {"off": ["P-2", "P-1"], "shadow": ["P-2", "P-1"], "active_dev": ["P-1", "P-2"]}
    for mode, ids in expected.items():
        client, _ = make_client(mode)
        response = client.post(f"/api/customers/{CUSTOMER_ID}/recommendations", json={})
        assert response.status_code == 200
        assert response.json()["ml_mode"] == mode
        assert [row["property_id"] for row in response.json()["properties"]] == ids


def test_ml_fallback_keeps_deterministic_order():
    client, _ = make_client(ml=ML("active_dev", fail=True))
    response = client.post(f"/api/customers/{CUSTOMER_ID}/recommendations", json={})
    assert [row["property_id"] for row in response.json()["properties"]] == ["P-2", "P-1"]


def test_shown_events_are_idempotent_and_snapshots_preserved():
    client, services = make_client()
    session_id = str(uuid4())
    path = f"/api/customers/{CUSTOMER_ID}/recommendations"
    assert client.post(path, json={"recommendation_session_id": session_id}).status_code == 200
    assert client.post(path, json={"recommendation_session_id": session_id}).status_code == 200
    shown = [event for event in services.interactions.events if event["action"] == "shown"]
    assert len(shown) == 2
    assert shown[0]["preference_snapshot"]["city"] == "Lahore"
    assert shown[0]["property_snapshot"]["property_id"] in {"P-1", "P-2"}
    assert "ml_probability" not in shown[0]["property_snapshot"]


def test_like_reject_shortlist_and_context_validation():
    for action in ("liked", "rejected", "shortlisted"):
        client, services = make_client()
        recommendation = client.post(f"/api/customers/{CUSTOMER_ID}/recommendations", json={}).json()
        response = client.post("/api/interactions", json={
            "customer_id": CUSTOMER_ID, "property_id": "P-1", "action": action,
            "recommendation_session_id": recommendation["recommendation_session_id"],
        })
        assert response.status_code == 201
        assert services.interactions.events[-1]["action"] == action


def test_invalid_action_property_and_customer_isolation():
    client, _ = make_client()
    recommendation = client.post(f"/api/customers/{CUSTOMER_ID}/recommendations", json={}).json()
    base = {"customer_id": CUSTOMER_ID, "property_id": "P-1", "recommendation_session_id": recommendation["recommendation_session_id"]}
    assert client.post("/api/interactions", json={**base, "action": "shown"}).status_code == 422
    assert client.post("/api/interactions", json={**base, "property_id": "NOT-SHOWN", "action": "liked"}).status_code == 422
    assert client.post("/api/interactions", json={**base, "customer_id": str(uuid4()), "action": "liked"}).status_code == 409


def test_appointment_routes_delegate_to_day4_gateway():
    client, services = make_client()
    book = client.post("/api/appointments", json={"customer_id": CUSTOMER_ID, "property_id": "P-1", "starts_at": "2030-01-02T10:00:00+05:00"})
    appointment_id = str(uuid4())
    move = client.patch(f"/api/appointments/{appointment_id}/reschedule", json={"starts_at": "2030-01-03T10:00:00+05:00"})
    cancel = client.delete(f"/api/appointments/{appointment_id}")
    assert (book.status_code, move.status_code, cancel.status_code) == (201, 200, 200)
    assert [call[0] for call in services.appointments.calls] == ["POST", "PATCH", "DELETE"]


def test_validation_health_docs_and_no_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "top-secret")
    client, _ = make_client()
    assert client.post("/api/customers", json={"full_name": "A", "email": "bad", "phone": "x"}).status_code == 422
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ml_mode"] == "off"
    assert "postgresql" not in health.text and "top-secret" not in health.text
    assert client.get("/docs").status_code == 200


def test_default_real_model_service_mode_is_off(monkeypatch):
    monkeypatch.delenv("SARA_ML_RANKING_MODE", raising=False)
    assert PropertyPreferenceModelService().mode == "off"
