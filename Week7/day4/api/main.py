"""FastAPI surface for Day 4 appointment workflows."""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID
import hmac
import os
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from day4_workflows.appointment_service import AppointmentWorkflowService, InvalidAppointmentState
from day4_workflows.calendar_service import CalendarEventNotFound, GoogleCalendarGateway, InMemoryCalendarGateway, SlotUnavailable
from day4_workflows.config import Settings
from day4_workflows.crm_logging import AppointmentNotFound, InMemoryCRMRepository, PostgresCRMRepository
from day4_workflows.email_service import InMemoryEmailGateway, SMTPEmailGateway
from day4_workflows.models import AppointmentRequest, WorkflowResult
from day4_workflows.n8n_orchestrator import N8NPublisher

bearer = HTTPBearer(auto_error=False)

def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    """Authenticate internal callers with the service-owned bearer key."""
    expected = os.getenv("DAY4_API_KEY", "").strip()
    if not expected:
        raise HTTPException(503, "API authentication is not configured")
    supplied = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Invalid or missing API key", headers={"WWW-Authenticate": "Bearer"})

DAY4_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(DAY4_ROOT / ".env", override=False)

class RescheduleRequest(BaseModel):
    starts_at: datetime
    @field_validator("starts_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None: raise ValueError("starts_at must include a timezone offset")
        return value

def build_service(settings: Settings) -> AppointmentWorkflowService:
    credential_file = settings.google_service_account_file or ""
    if credential_file and not Path(credential_file).is_absolute():
        credential_file = str(DAY4_ROOT / credential_file)
    calendar = GoogleCalendarGateway(credential_file) if settings.calendar_backend == "google" else InMemoryCalendarGateway()
    if settings.database_url.startswith(("postgres://", "postgresql://")):
        crm = PostgresCRMRepository(settings.database_url)
    else:
        crm = InMemoryCRMRepository()
    email = SMTPEmailGateway(settings.smtp_host, settings.smtp_port, settings.smtp_sender, settings.smtp_username, settings.smtp_password, settings.smtp_use_tls) if settings.smtp_host else InMemoryEmailGateway()
    publisher = N8NPublisher(settings.n8n_webhook_url, settings.n8n_api_key, settings.workflow_timeout_seconds, settings.workflow_max_attempts)
    return AppointmentWorkflowService(calendar, email, crm, publisher)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env(); service = build_service(settings)
    if isinstance(service.crm, PostgresCRMRepository): await service.crm.initialize()
    app.state.settings, app.state.service = settings, service
    yield

def create_app(service: AppointmentWorkflowService | None = None) -> FastAPI:
    app = FastAPI(title="Sara Day 4 Workflows", version="1.0.0", lifespan=None if service else lifespan)
    if service: app.state.service = service
    @app.get("/health")
    async def health() -> dict: return {"status": "ok", "service": "day4-workflows"}
    @app.post("/appointments", response_model=WorkflowResult, status_code=201, dependencies=[Depends(require_api_key)])
    async def book(payload: AppointmentRequest, request: Request) -> WorkflowResult:
        try: return await request.app.state.service.book(payload)
        except SlotUnavailable as exc: raise HTTPException(409, str(exc)) from exc
    @app.patch("/appointments/{appointment_id}/reschedule", response_model=WorkflowResult, dependencies=[Depends(require_api_key)])
    async def reschedule(appointment_id: UUID, payload: RescheduleRequest, request: Request) -> WorkflowResult:
        try: return await request.app.state.service.reschedule(appointment_id, payload.starts_at)
        except (AppointmentNotFound, CalendarEventNotFound) as exc: raise HTTPException(404, "Appointment not found") from exc
        except SlotUnavailable as exc: raise HTTPException(409, str(exc)) from exc
        except InvalidAppointmentState as exc: raise HTTPException(409, str(exc)) from exc
    @app.delete("/appointments/{appointment_id}", response_model=WorkflowResult, dependencies=[Depends(require_api_key)])
    async def cancel(appointment_id: UUID, request: Request) -> WorkflowResult:
        try: return await request.app.state.service.cancel(appointment_id)
        except (AppointmentNotFound, CalendarEventNotFound) as exc: raise HTTPException(404, "Appointment not found") from exc
        except InvalidAppointmentState as exc: raise HTTPException(409, str(exc)) from exc
    @app.post("/appointments/{appointment_id}/follow-up", dependencies=[Depends(require_api_key)])
    async def follow_up(appointment_id: UUID, request: Request) -> dict:
        try: return await request.app.state.service.send_follow_up(appointment_id)
        except AppointmentNotFound as exc: raise HTTPException(404, "Appointment not found") from exc
    return app

app = create_app()
