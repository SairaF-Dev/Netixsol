from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID
import asyncio
import pytest
from day4_workflows.appointment_service import AppointmentWorkflowService, InvalidAppointmentState
from day4_workflows.calendar_service import (
    GoogleCalendarGateway,
    InMemoryCalendarGateway,
    SlotUnavailable,
)
from day4_workflows.config import Settings
from day4_workflows.crm_logging import InMemoryCRMRepository
from day4_workflows.email_service import (
    EmailError,
    GoogleAppsScriptEmailGateway,
    InMemoryEmailGateway,
    OutboundEmail,
)
from day4_workflows.models import AppointmentRequest, AppointmentStatus
from day4_workflows.n8n_orchestrator import InMemoryWorkflowPublisher

def request_at(starts_at: datetime, phone: str = "+92 300 1234567") -> AppointmentRequest:
    return AppointmentRequest(client_name="Ali Khan", client_phone=phone, employee_name="Sara Ahmed", employee_email="sara@example.com", property_id=101, property_name="Horizon Heights", starts_at=starts_at, meeting_notes="DHA office se keys collect karni hain")

def setup(fail_email: bool = False):
    calendar, email, crm, publisher = InMemoryCalendarGateway(), InMemoryEmailGateway(fail_email), InMemoryCRMRepository(), InMemoryWorkflowPublisher()
    return AppointmentWorkflowService(calendar, email, crm, publisher), calendar, email, crm, publisher

def test_booking_creates_calendar_email_crm_and_workflow_event():
    async def run():
        service, calendar, email, crm, publisher = setup(); result = await service.book(request_at(datetime(2030, 1, 5, 11, tzinfo=timezone(timedelta(hours=5)))))
        assert result.appointment.status == AppointmentStatus.CONFIRMED
        assert result.appointment.calendar_event_id in calendar.events
        assert result.notification_sent and len(email.messages) == 1
        assert (await crm.get_appointment(result.appointment.appointment_id)).status == AppointmentStatus.CONFIRMED
        assert publisher.events[0]["event_type"] == "appointment.booked"
    asyncio.run(run())

def test_double_booking_is_rejected_before_side_effects():
    async def run():
        service, _, email, crm, _ = setup(); start = datetime(2030, 1, 5, 11, tzinfo=timezone.utc)
        await service.book(request_at(start))
        with pytest.raises(SlotUnavailable): await service.book(request_at(start + timedelta(minutes=30), "+92 301 1234567"))
        assert len(email.messages) == 1 and len(crm.appointments) == 1
    asyncio.run(run())

def test_reschedule_and_cancel_update_all_systems():
    async def run():
        service, calendar, email, crm, publisher = setup(); start = datetime(2030, 1, 5, 11, tzinfo=timezone.utc)
        booked = await service.book(request_at(start)); aid = booked.appointment.appointment_id
        moved = await service.reschedule(aid, start + timedelta(days=1))
        assert moved.appointment.previous_starts_at == start and moved.appointment.status == AppointmentStatus.RESCHEDULED
        cancelled = await service.cancel(aid)
        assert cancelled.appointment.status == AppointmentStatus.CANCELLED
        assert booked.appointment.calendar_event_id not in calendar.events
        assert [e["event_type"] for e in publisher.events] == ["appointment.booked", "appointment.rescheduled", "appointment.cancelled"]
        with pytest.raises(InvalidAppointmentState): await service.cancel(aid)
        assert len(email.messages) == 3 and len(crm.events) == 3
    asyncio.run(run())

def test_email_failure_does_not_undo_verified_calendar_booking():
    async def run():
        service, calendar, _, crm, _ = setup(True); result = await service.book(request_at(datetime(2030, 1, 5, 11, tzinfo=timezone.utc)))
        assert result.appointment.calendar_event_id in calendar.events
        assert not result.notification_sent and result.warnings == ["Email notification failed: EmailError"]
        assert (await crm.get_appointment(result.appointment.appointment_id)).status == AppointmentStatus.CONFIRMED
    asyncio.run(run())

def test_naive_datetime_and_bad_phone_are_rejected():
    with pytest.raises(ValueError): request_at(datetime(2030, 1, 5, 11))
    with pytest.raises(ValueError): request_at(datetime(2030, 1, 5, 11, tzinfo=timezone.utc), "call-me")

def test_n8n_follow_up_sends_email_and_logs_crm_event():
    async def run():
        service, _, email, crm, _ = setup()
        booked = await service.book(request_at(datetime(2030, 1, 5, 11, tzinfo=timezone.utc)))
        result = await service.send_follow_up(booked.appointment.appointment_id)
        assert result["sent"] is True
        assert len(email.messages) == 2
        assert crm.events[-1]["event_type"] == "follow_up_sent"
    asyncio.run(run())

def test_production_configuration_rejects_in_memory_integrations():
    settings = Settings(app_env="production")
    with pytest.raises(ValueError, match="CALENDAR_BACKEND must be google"):
        settings.validate_for_production(base_dir=Path("."))

def test_development_configuration_keeps_in_memory_integrations():
    Settings(app_env="development").validate_for_production(base_dir=Path("."))

def test_google_apps_script_email_gateway_sends_and_requires_acknowledgement():
    message = OutboundEmail(
        recipient="agent@example.com",
        subject="Visit confirmed",
        text="The visit is confirmed.",
        html="<p>The visit is confirmed.</p>",
    )
    response = Mock()
    response.json.return_value = {"ok": True}
    gateway = GoogleAppsScriptEmailGateway(
        "https://script.google.com/macros/s/deployment-id/exec",
        "test-relay-token",
    )

    async def run():
        with patch("day4_workflows.email_service.httpx.AsyncClient") as client_type:
            client = AsyncMock()
            client.__aenter__.return_value = client
            client.post.return_value = response
            client_type.return_value = client
            await gateway.send(message)
            client.post.assert_awaited_once_with(
                "https://script.google.com/macros/s/deployment-id/exec",
                json={
                    "token": "test-relay-token",
                    "to": "agent@example.com",
                    "subject": "Visit confirmed",
                    "text": "The visit is confirmed.",
                    "html": "<p>The visit is confirmed.</p>",
                },
            )
            response.json.return_value = {"ok": False, "error": "unauthorized"}
            with pytest.raises(EmailError, match="did not confirm delivery"):
                await gateway.send(message)

    asyncio.run(run())

def test_google_apps_script_email_gateway_rejects_untrusted_url():
    with pytest.raises(ValueError, match="script.google.com"):
        GoogleAppsScriptEmailGateway("https://example.com/relay", "test-token")

def test_google_calendar_gateway_loads_credentials_from_environment_json():
    from google.oauth2 import service_account
    from googleapiclient import discovery

    with patch.object(
        service_account.Credentials,
        "from_service_account_info",
        return_value=object(),
    ) as credentials_factory, patch.object(discovery, "build") as build:
        GoogleCalendarGateway(
            service_account_json='{"type":"service_account","client_email":"agent@example.com"}'
        )

    credentials_factory.assert_called_once_with(
        {"type": "service_account", "client_email": "agent@example.com"},
        scopes=GoogleCalendarGateway.scopes,
    )
    build.assert_called_once()

def test_production_configuration_accepts_live_integration_settings(tmp_path: Path):
    credentials = tmp_path / "google-service-account.json"
    credentials.write_text("test credential placeholder", encoding="utf-8")
    settings = Settings(
        app_env="production",
        database_url="postgresql://db.example/appointments",
        calendar_backend="google",
        google_service_account_file=str(credentials),
        google_calendar_id="agent@example.com",
        smtp_host="smtp.example.com",
        smtp_username="agent@example.com",
        smtp_password="test-password",
        smtp_sender="visits@example.com",
        internal_api_key="test-internal-api-key",
    )
    settings.validate_for_production(base_dir=tmp_path)

def test_production_configuration_accepts_gmail_relay(tmp_path: Path):
    credentials = tmp_path / "google-service-account.json"
    credentials.write_text("test credential placeholder", encoding="utf-8")
    settings = Settings(
        app_env="production",
        database_url="postgresql://db.example/appointments",
        calendar_backend="google",
        google_service_account_file=str(credentials),
        google_calendar_id="agent@example.com",
        email_backend="google_apps_script",
        google_apps_script_url="https://script.google.com/macros/s/deployment-id/exec",
        google_apps_script_token="test-relay-token",
        internal_api_key="test-internal-api-key",
    )
    settings.validate_for_production(base_dir=tmp_path)

def test_production_configuration_rejects_gmail_relay_without_token(tmp_path: Path):
    credentials = tmp_path / "google-service-account.json"
    credentials.write_text("test credential placeholder", encoding="utf-8")
    settings = Settings(
        app_env="production",
        database_url="postgresql://db.example/appointments",
        calendar_backend="google",
        google_service_account_file=str(credentials),
        google_calendar_id="agent@example.com",
        email_backend="google_apps_script",
        google_apps_script_url="https://script.google.com/macros/s/deployment-id/exec",
        internal_api_key="test-internal-api-key",
    )
    with pytest.raises(ValueError, match="GOOGLE_APPS_SCRIPT_TOKEN is required"):
        settings.validate_for_production(base_dir=tmp_path)

def test_production_configuration_accepts_calendar_credentials_json():
    settings = Settings(
        app_env="production",
        database_url="postgresql://db.example/appointments",
        calendar_backend="google",
        google_service_account_json='{"type":"service_account","client_email":"agent@example.com"}',
        google_calendar_id="agent@example.com",
        email_backend="google_apps_script",
        google_apps_script_url="https://script.google.com/macros/s/deployment-id/exec",
        google_apps_script_token="test-relay-token",
        internal_api_key="test-internal-api-key",
    )
    settings.validate_for_production(base_dir=Path("."))
