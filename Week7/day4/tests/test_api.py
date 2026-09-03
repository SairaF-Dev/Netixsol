from datetime import datetime, timezone
import os
from fastapi.testclient import TestClient
from api.main import create_app
from day4_workflows.appointment_service import AppointmentWorkflowService
from day4_workflows.calendar_service import InMemoryCalendarGateway
from day4_workflows.crm_logging import InMemoryCRMRepository
from day4_workflows.email_service import InMemoryEmailGateway
from day4_workflows.n8n_orchestrator import InMemoryWorkflowPublisher

def client():
    os.environ["DAY4_API_KEY"] = "test-day4-key"
    service = AppointmentWorkflowService(InMemoryCalendarGateway(), InMemoryEmailGateway(), InMemoryCRMRepository(), InMemoryWorkflowPublisher())
    return TestClient(create_app(service), headers={"Authorization": "Bearer test-day4-key"})

def payload():
    return {"client_name":"Ali Khan","client_phone":"+923001234567","employee_name":"Sara Ahmed","employee_email":"sara@example.com","property_id":101,"property_name":"Horizon Heights","starts_at":"2030-01-05T11:00:00+05:00","meeting_notes":"Bring brochure"}

def test_complete_api_lifecycle():
    api = client()
    assert api.get("/health").status_code == 200
    booked = api.post("/appointments", json=payload()); assert booked.status_code == 201
    aid = booked.json()["appointment"]["appointment_id"]
    moved = api.patch(f"/appointments/{aid}/reschedule", json={"starts_at":"2030-01-06T12:00:00+05:00"}); assert moved.status_code == 200
    cancelled = api.delete(f"/appointments/{aid}"); assert cancelled.status_code == 200
    assert cancelled.json()["appointment"]["status"] == "cancelled"

def test_api_returns_conflict_for_overlap():
    api = client()
    assert api.post("/appointments", json=payload()).status_code == 201
    second = payload(); second["client_phone"] = "+923011234567"
    assert api.post("/appointments", json=second).status_code == 409

def test_appointment_endpoints_require_authentication():
    os.environ["DAY4_API_KEY"] = "test-day4-key"
    service = AppointmentWorkflowService(InMemoryCalendarGateway(), InMemoryEmailGateway(), InMemoryCRMRepository(), InMemoryWorkflowPublisher())
    api = TestClient(create_app(service))
    assert api.post("/appointments", json=payload()).status_code == 401
    assert api.post("/appointments", json=payload(), headers={"Authorization": "Bearer wrong"}).status_code == 401
