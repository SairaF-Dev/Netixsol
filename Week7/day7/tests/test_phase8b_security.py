from pathlib import Path

from test_auth_api import A, client


def test_csrf_required_for_authenticated_mutation_but_not_get():
    web, auth = client()
    auth.validate_csrf = lambda session, csrf: session == "token-a" and csrf == "valid"
    web.cookies.set("sara_session", "token-a")
    assert web.get("/api/me/preferences").status_code == 200
    assert web.patch("/api/me/preferences", json={"area": "DHA"}).status_code == 403
    assert web.patch("/api/me/preferences", json={"area": "DHA"}, headers={"X-CSRF-Token": "bad"}).status_code == 403
    assert web.patch("/api/me/preferences", json={"area": "DHA"}, headers={"X-CSRF-Token": "valid"}).status_code == 200


def test_login_rate_limit_returns_generic_429():
    web, auth = client()
    auth.rate_allowed = lambda *args: False
    response = web.post("/api/auth/login", json={"email": "a@example.com", "password": "anything"})
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many authentication attempts"}


def test_owned_appointment_listing_uses_only_repository_ids():
    web, auth = client()
    auth.repository.list_appointment_ids = lambda user_id: ["11111111-1111-1111-1111-111111111111"] if user_id == "ua" else []

    async def listing(ids):
        assert ids == ["11111111-1111-1111-1111-111111111111"]
        return [{"appointment_id": ids[0], "status": "cancelled", "request": {"property_id": "P1", "property_name": "Home", "starts_at": "2030-01-01T10:00:00+05:00"}}]

    web.app.state.services.appointments.list_owned = listing
    web.cookies.set("sara_session", "token-a")
    response = web.get("/api/me/appointments")
    assert response.status_code == 200
    assert response.json()["appointments"][0]["status"] == "cancelled"


def test_phase8b_schema_is_additive_and_contains_no_raw_secrets():
    schema = (Path(__file__).parents[1] / "web_api" / "auth_schema.sql").read_text(encoding="utf-8")
    assert "recommendation_sessions" in schema
    assert "recommendation_session_properties" in schema
    assert "auth_rate_limits" in schema and "auth_audit_events" in schema
    assert "shown_recorded" in schema and "expires_at" in schema
    audit_section = schema.split("CREATE TABLE IF NOT EXISTS auth_audit_events", 1)[1]
    assert "raw_session_token" not in schema
    assert "password_hash" not in audit_section and "token_digest" not in audit_section
