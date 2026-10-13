"""
test_task4_voice_ml.py
----------------------
Unit & integration test suite for Week 8 Day 4 Task 4:
- 4A: Voice agent property price valuation tool ("Mera ghar kitne ka bikega?")
- 4B: Post-call lead scoring integration
- 4C: Hot lead email alert notification
- 4D: Webhook server end-of-call integration
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from vapi_integration.tool_handler import VapiToolHandler
from vapi_integration.lead_scoring_service import score_call_lead, send_hot_lead_email


# ==============================================================================
# 4A. Voice Agent Property Price Valuation Tool Tests
# ==============================================================================

class TestVoicePriceValuationTool:
    def test_price_tool_missing_city_prompts_user(self):
        handler = VapiToolHandler()
        # Area provided, but city is missing
        res = asyncio.run(
            handler.execute(
                tool_name="predict_property_price",
                arguments={"area_marla": 10.0, "property_type": "House"},
                call_id="call-001",
            )
        )
        assert "shehar" in res.lower()
        assert "konsa hai" in res.lower() or "batayein" in res.lower()

    def test_price_tool_missing_area_prompts_user(self):
        handler = VapiToolHandler()
        # City provided, but area is missing
        res = asyncio.run(
            handler.execute(
                tool_name="predict_property_price",
                arguments={"city": "Lahore", "property_type": "House"},
                call_id="call-002",
            )
        )
        assert "area" in res.lower()
        assert "marlay" in res.lower() or "kitne marlay" in res.lower()

    def test_price_tool_valid_inputs_calls_api_and_returns_urdulish(self):
        handler = VapiToolHandler()
        mock_response = MagicMock(
            status_code=200,
            json=lambda: {
                "predicted_fair_price_pkr": 32500000.0,
                "lower_bound_pkr": 29000000.0,
                "upper_bound_pkr": 36000000.0,
                "purpose": "For Sale",
                "verdict": "Fair Market Value",
            },
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            res = asyncio.run(
                handler.execute(
                    tool_name="predict_property_price",
                    arguments={
                        "city": "Lahore",
                        "location": "DHA Phase 5",
                        "area_marla": 10.0,
                        "purpose": "For Sale",
                        "property_type": "House",
                    },
                    call_id="call-003",
                )
            )
            assert "3.25 Crore" in res or "32,500,000" in res
            assert "Lahore" in res
            assert "DHA Phase 5" in res
            assert "Disclaimer:" in res or "official valuation" in res

    def test_price_tool_extreme_area_rejected_ood(self):
        handler = VapiToolHandler()
        mock_response = MagicMock(
            status_code=422,
            json=lambda: {
                "error_code": "OUT_OF_DISTRIBUTION",
                "message": "OUT_OF_DISTRIBUTION: area is outside the training distribution",
            },
            text='{"error_code":"OUT_OF_DISTRIBUTION"}',
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            res = asyncio.run(
                handler.execute(
                    tool_name="predict_property_price",
                    arguments={
                        "city": "Lahore",
                        "location": "DHA Phase 5",
                        "area_marla": 5000.0,
                        "purpose": "For Sale",
                    },
                    call_id="call-004",
                )
            )
        assert "supported range se bahir" in res.lower()
        assert "5000" in res


# ==============================================================================
# 4B. Post-Call Lead Scoring Tests
# ==============================================================================

class TestPostCallLeadScoring:
    def test_score_call_lead_successful_api_call(self):
        mock_score = {
            "conversion_probability": 0.82,
            "lead_score_pct": 82.0,
            "tier": "Hot",
            "priority_rank": 1,
            "recommended_sla_action": "Call within 15 minutes by Senior Agent",
            "customer_persona": "High-Net-Worth Investor",
            "urdulish_explanation": "Strong conversion propensity based on visit and call duration.",
        }

        mock_resp = MagicMock(status_code=200, json=lambda: mock_score)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            score_data = asyncio.run(
                score_call_lead(
                    caller_phone="+923001234567",
                    call_duration_seconds=720,  # 12 minutes
                    visit_booked=True,
                    client_name="Kamran Shah",
                    preferred_city="Islamabad",
                    preferred_location="F-7",
                    budget_pkr=60000000,
                )
            )

            assert score_data is not None
            assert score_data["tier"] == "Hot"
            assert score_data["lead_score_pct"] == 82.0
            assert score_data["customer_persona"] == "High-Net-Worth Investor"


# ==============================================================================
# 4C. Hot Lead Email Notification Tests
# ==============================================================================

class TestHotLeadEmailNotification:
    def test_send_hot_lead_email_dispatches(self, monkeypatch):
        monkeypatch.setenv("EMPLOYEE_EMAIL", "agent@realestatehub.com")
        score_data = {
            "lead_score_pct": 85.5,
            "tier": "Hot",
            "customer_persona": "High-Net-Worth Investor",
            "recommended_sla_action": "Call within 15 minutes",
            "urdulish_explanation": "Client interested in prime property.",
        }

        with patch("vapi_integration.lead_scoring_service.SMTP_USER", "notifications@realestatehub.com"), \
             patch("vapi_integration.lead_scoring_service.SMTP_PASS", "app_password"), \
             patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            success = asyncio.run(
                send_hot_lead_email(
                    score_data=score_data,
                    caller_phone="+923219876543",
                    client_name="<script>alert(1)</script>",
                    call_duration_seconds=480,
                    recipient_email="agent@realestatehub.com",
                )
            )

            assert success is True
            assert mock_server.send_message.called
            email = mock_server.send_message.call_args.args[0]
            html_body = email.get_body(preferencelist=("html",)).get_content()
            text_body = email.get_body(preferencelist=("plain",)).get_content()
            assert email["Subject"].startswith("[DEMO ONLY] Synthetic-label lead score")
            assert "<script>" not in html_body
            assert "not validated against real CRM outcomes" in html_body
            assert "not a validated likelihood of sale" in text_body

    def test_missing_smtp_credentials_reports_email_not_sent(self):
        score_data = {"lead_score_pct": 85.5, "tier": "Hot"}
        with patch("vapi_integration.lead_scoring_service.SMTP_USER", ""), \
             patch("vapi_integration.lead_scoring_service.SMTP_PASS", ""):
            sent = asyncio.run(
                send_hot_lead_email(
                    score_data=score_data,
                    caller_phone="+923219876543",
                    recipient_email="agent@realestatehub.com",
                )
            )
        assert sent is False

    def test_smtp_failure_reports_email_not_sent(self):
        score_data = {"lead_score_pct": 85.5, "tier": "Hot"}
        with patch("vapi_integration.lead_scoring_service.SMTP_USER", "sender@example.com"), \
             patch("vapi_integration.lead_scoring_service.SMTP_PASS", "test-password"), \
             patch("smtplib.SMTP", side_effect=OSError("SMTP unavailable")):
            sent = asyncio.run(
                send_hot_lead_email(
                    score_data=score_data,
                    caller_phone="+923219876543",
                    recipient_email="agent@realestatehub.com",
                )
            )
        assert sent is False

    def test_gmail_relay_sends_hot_lead_email_over_https(self):
        gateway = MagicMock()
        gateway.send = AsyncMock()
        with patch("vapi_integration.lead_scoring_service.EMAIL_BACKEND", "google_apps_script"), \
             patch("vapi_integration.lead_scoring_service.GOOGLE_APPS_SCRIPT_URL", "https://script.google.com/macros/s/deployment-id/exec"), \
             patch("vapi_integration.lead_scoring_service.GOOGLE_APPS_SCRIPT_TOKEN", "test-relay-token"), \
             patch("vapi_integration.lead_scoring_service.GoogleAppsScriptEmailGateway", return_value=gateway):
            sent = asyncio.run(
                send_hot_lead_email(
                    score_data={"lead_score_pct": 91.0, "tier": "Hot"},
                    caller_phone="+923001234567",
                    client_name="<script>alert(1)</script>",
                    recipient_email="agent@example.com",
                )
            )

        assert sent is True
        gateway.send.assert_awaited_once()
        email = gateway.send.call_args.args[0]
        assert email.recipient == "agent@example.com"
        assert email.subject.startswith("[DEMO ONLY] Synthetic-label lead score")
        assert "&lt;script&gt;" in email.html
        assert "not validated against real CRM outcomes" in email.html

    def test_gmail_relay_missing_credentials_reports_email_not_sent(self):
        with patch("vapi_integration.lead_scoring_service.EMAIL_BACKEND", "google_apps_script"), \
             patch("vapi_integration.lead_scoring_service.GOOGLE_APPS_SCRIPT_URL", ""), \
             patch("vapi_integration.lead_scoring_service.GOOGLE_APPS_SCRIPT_TOKEN", ""):
            sent = asyncio.run(
                send_hot_lead_email(
                    score_data={"lead_score_pct": 91.0, "tier": "Hot"},
                    caller_phone="+923001234567",
                    recipient_email="agent@example.com",
                )
            )

        assert sent is False


# ==============================================================================
# 4D. Webhook Server End-of-Call Event Integration Test
# ==============================================================================

class TestEndOfCallReportWebhook:
    def test_end_of_call_report_triggers_scoring_and_closes_session(self, monkeypatch):
        from vapi_integration.webhook_server import app
        import vapi_integration.webhook_server as ws

        monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "test-secret")
        client = TestClient(app, headers={"x-vapi-secret": "test-secret"})

        mock_session = MagicMock(
            caller_phone="+923001122334",
            appointment_id="apt-1234",
            preference_snapshot={"client_name": "Tariq Ali", "city": "Lahore", "location": "DHA", "max_price": 40000000},
        )

        mock_sm = MagicMock()
        mock_sm.get_session = AsyncMock(return_value=mock_session)
        mock_sm.close_session = AsyncMock(return_value=None)

        mock_score = {
            "tier": "Hot",
            "lead_score_pct": 88.0,
            "customer_persona": "High-Net-Worth Investor",
            "recommended_sla_action": "Call within 15 mins",
            "urdulish_explanation": "Hot lead explanation",
        }

        with patch.object(ws, "session_manager", mock_sm), \
             patch("vapi_integration.webhook_server.score_call_lead", new_callable=AsyncMock, return_value=mock_score) as mock_score_fn, \
             patch("vapi_integration.webhook_server.send_hot_lead_email", new_callable=AsyncMock, return_value=True) as mock_email_fn:

            payload = {
                "message": {
                    "type": "end-of-call-report",
                    "call": {"id": "call-1234"},
                    "summary": "Customer discussed 10 marla house in DHA and booked a visit.",
                    "transcript": "Aap DHA Phase 5 mein visit book kar dein.",
                    "durationSeconds": 600,
                }
            }

            resp = client.post("/vapi/webhook", json=payload)
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}
            assert mock_score_fn.called
            assert mock_email_fn.called
            assert mock_sm.close_session.called
