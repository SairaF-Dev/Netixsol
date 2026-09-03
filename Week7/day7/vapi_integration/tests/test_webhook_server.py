"""Integration tests for VAPI webhook server.

Tests verify:
1. Webhook server starts correctly
2. Call-start event creates a session
3. Transcript event returns a response
4. Tool-call events execute via Day 4 API (mocked)
5. End-of-call event closes session and logs to CRM
6. Security: invalid webhook secret is rejected
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def client(monkeypatch):
    """Test client for the VAPI webhook server."""
    # Import here to avoid path issues before session_manager is mocked
    from vapi_integration.webhook_server import app
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
    return TestClient(app, headers={"x-vapi-secret": "test-secret"})


@pytest.fixture
def mock_session_manager():
    """Mock session manager so tests don't need Day 3 installed."""
    with patch("vapi_integration.webhook_server.session_manager") as mock:
        mock.active_count.return_value = 1
        mock.create_session = AsyncMock(return_value=None)
        mock.process_turn = AsyncMock(
            return_value="Assalam-o-Alaikum! Main aap ki madad kar sakti hoon."
        )
        mock.get_session = AsyncMock(return_value=MagicMock(appointment_id=None))
        mock.close_session = AsyncMock(return_value=None)
        yield mock


@pytest.fixture
def mock_tool_handler():
    with patch("vapi_integration.webhook_server.tool_handler") as mock:
        mock.execute = AsyncMock(return_value="Appointment successfully book ho gayi!")
        yield mock


# ── Tests ─────────────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "sara-vapi-webhook"


class TestWebhookSecurity:
    def test_rejects_invalid_secret(self, client, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "correct-secret")
        payload = {"message": {"type": "call-start", "call": {"id": "test-123"}}}
        resp = client.post(
            "/vapi/webhook",
            json=payload,
            headers={"x-vapi-secret": "wrong-secret"},
        )
        assert resp.status_code == 403

    def test_accepts_correct_secret(self, client, mock_session_manager, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "correct-secret")
        payload = {
            "message": {
                "type": "call-start",
                "call": {"id": "test-123", "customer": {"number": "+923001234567"}},
            }
        }
        resp = client.post(
            "/vapi/webhook",
            json=payload,
            headers={"x-vapi-secret": "correct-secret"},
        )
        assert resp.status_code == 200

    def test_missing_server_secret_fails_closed(self, client, mock_session_manager, monkeypatch):
        monkeypatch.delenv("VAPI_WEBHOOK_SECRET", raising=False)
        payload = {
            "message": {
                "type": "call-start",
                "call": {"id": "test-456", "customer": {"number": "+923001234567"}},
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 503


class TestCallStart:
    def test_call_start_creates_session(self, client, mock_session_manager, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "call-start",
                "call": {
                    "id": "call-abc-123",
                    "customer": {"number": "+923001234567"},
                },
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_session_manager.create_session.assert_called_once_with(
            "call-abc-123", caller_phone="+923001234567"
        )


class TestTranscript:
    def test_user_message_returns_sara_response(self, client, mock_session_manager, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "transcript",
                "call": {"id": "call-xyz-456"},
                "role": "user",
                "transcript": "DHA mein 3 bedroom apartment chahiye budget 2 crore",
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "text"
        assert len(data["content"]) > 0
        mock_session_manager.process_turn.assert_called_once()

    def test_assistant_transcript_is_ignored(self, client, mock_session_manager, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "transcript",
                "call": {"id": "call-xyz-456"},
                "role": "assistant",
                "transcript": "Ji zaroor, main property dhundh rahi hoon",
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        mock_session_manager.process_turn.assert_not_called()

    def test_empty_transcript_is_ignored(self, client, mock_session_manager, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "transcript",
                "call": {"id": "call-xyz-456"},
                "role": "user",
                "transcript": "  ",  # whitespace only
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.json()["status"] == "ignored"


class TestToolCalls:
    def test_current_vapi_tool_call_shape(
        self, client, mock_session_manager, mock_tool_handler, monkeypatch
    ):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call-search-123"},
                "toolCallList": [
                    {
                        "id": "tool-call-search",
                        "name": "search_properties",
                        "parameters": {
                            "location": "DHA Phase 6 Lahore",
                            "bedrooms": 3,
                            "max_price": 40000000,
                            "purpose": "buy",
                        },
                    }
                ],
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert result["name"] == "search_properties"
        assert result["toolCallId"] == "tool-call-search"
        mock_tool_handler.execute.assert_awaited_once()

    def test_book_appointment_tool_call(
        self, client, mock_session_manager, mock_tool_handler, monkeypatch
    ):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "call-book-789"},
                "toolCalls": [
                    {
                        "id": "tool-call-001",
                        "function": {
                            "name": "book_appointment",
                            "arguments": {
                                "client_name": "Ahmed Khan",
                                "client_phone": "+923001234567",
                                "property_name": "DHA Villa",
                                "starts_at": "2025-09-05T10:00:00+05:00",
                            },
                        },
                    }
                ],
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["toolCallId"] == "tool-call-001"


class TestCallEnd:
    def test_end_of_call_closes_session(self, client, mock_session_manager, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "call-end-999"},
                "summary": "Customer asked about DHA properties. Appointment booked.",
                "transcript": "User: DHA property...\nAssistant: Ji bilkul...",
                "recordingUrl": "https://storage.vapi.ai/recordings/test.mp3",
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        mock_session_manager.close_session.assert_called_once_with(
            call_id="call-end-999",
            summary="Customer asked about DHA properties. Appointment booked.",
            transcript="User: DHA property...\nAssistant: Ji bilkul...",
            recording_url="https://storage.vapi.ai/recordings/test.mp3",
        )


class TestAssistantRequest:
    def test_assistant_request_returns_config(self, client, monkeypatch):
        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        payload = {
            "message": {
                "type": "assistant-request",
                "call": {"id": "new-call-000"},
            }
        }
        resp = client.post("/vapi/webhook", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "assistant" in data
        assert data["assistant"]["model"]["provider"] == "custom-llm"
        assert "tools" in data["assistant"]["model"]
        # Verify all 4 tools are present
        tool_names = [t["function"]["name"] for t in data["assistant"]["model"]["tools"]]
        assert "book_appointment" in tool_names
        assert "reschedule_appointment" in tool_names
        assert "cancel_appointment" in tool_names
        assert "search_properties" in tool_names
