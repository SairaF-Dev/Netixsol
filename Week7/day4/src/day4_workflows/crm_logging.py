"""CRM appointment persistence ports with memory and PostgreSQL backends."""
from __future__ import annotations
import asyncio, json
from datetime import datetime
from typing import Protocol
from uuid import UUID
from .models import Appointment, AppointmentStatus

class CRMError(RuntimeError): pass
class AppointmentNotFound(CRMError): pass

class CRMRepository(Protocol):
    async def save_appointment(self, appointment: Appointment) -> None: ...
    async def get_appointment(self, appointment_id: UUID) -> Appointment: ...
    async def log_workflow_event(self, appointment_id: UUID, event_type: str, payload: dict) -> None: ...

class InMemoryCRMRepository:
    def __init__(self) -> None:
        self.appointments: dict[UUID, Appointment] = {}; self.events: list[dict] = []
    async def save_appointment(self, appointment: Appointment) -> None: self.appointments[appointment.appointment_id] = appointment.model_copy(deep=True)
    async def get_appointment(self, appointment_id: UUID) -> Appointment:
        try: return self.appointments[appointment_id].model_copy(deep=True)
        except KeyError as exc: raise AppointmentNotFound(str(appointment_id)) from exc
    async def log_workflow_event(self, appointment_id: UUID, event_type: str, payload: dict) -> None:
        self.events.append({"appointment_id": str(appointment_id), "event_type": event_type, "payload": payload, "created_at": datetime.now().astimezone().isoformat()})

class PostgresCRMRepository:
    """PostgreSQL implementation; blocking driver calls run outside the event loop."""
    def __init__(self, database_url: str) -> None: self.database_url = database_url
    async def initialize(self) -> None: await asyncio.to_thread(self._initialize_sync)
    def _initialize_sync(self) -> None:
        import psycopg
        with psycopg.connect(self.database_url) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS appointments (appointment_id UUID PRIMARY KEY, session_id UUID NOT NULL, status TEXT NOT NULL CHECK (status IN ('pending','confirmed','rescheduled','cancelled')), request_json JSONB NOT NULL, calendar_event_id TEXT, calendar_link TEXT, previous_starts_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL); CREATE INDEX IF NOT EXISTS appointments_session_idx ON appointments(session_id); CREATE TABLE IF NOT EXISTS workflow_events (id BIGSERIAL PRIMARY KEY, appointment_id UUID NOT NULL REFERENCES appointments(appointment_id), event_type TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());""")
    async def save_appointment(self, appointment: Appointment) -> None: await asyncio.to_thread(self._save_sync, appointment)
    def _save_sync(self, a: Appointment) -> None:
        import psycopg
        with psycopg.connect(self.database_url) as conn:
            conn.execute("""INSERT INTO appointments (appointment_id,session_id,status,request_json,calendar_event_id,calendar_link,previous_starts_at,created_at,updated_at) VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s) ON CONFLICT (appointment_id) DO UPDATE SET status=EXCLUDED.status,request_json=EXCLUDED.request_json,calendar_event_id=EXCLUDED.calendar_event_id,calendar_link=EXCLUDED.calendar_link,previous_starts_at=EXCLUDED.previous_starts_at,updated_at=EXCLUDED.updated_at""", (a.appointment_id,a.request.session_id,a.status.value,a.request.model_dump_json(),a.calendar_event_id,a.calendar_link,a.previous_starts_at,a.created_at,a.updated_at))
    async def get_appointment(self, appointment_id: UUID) -> Appointment: return await asyncio.to_thread(self._get_sync, appointment_id)
    def _get_sync(self, appointment_id: UUID) -> Appointment:
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            row = conn.execute("SELECT * FROM appointments WHERE appointment_id=%s", (appointment_id,)).fetchone()
        if not row: raise AppointmentNotFound(str(appointment_id))
        return Appointment(appointment_id=row["appointment_id"], request=row["request_json"], status=AppointmentStatus(row["status"]), calendar_event_id=row["calendar_event_id"], calendar_link=row["calendar_link"], previous_starts_at=row["previous_starts_at"], created_at=row["created_at"], updated_at=row["updated_at"])
    async def log_workflow_event(self, appointment_id: UUID, event_type: str, payload: dict) -> None: await asyncio.to_thread(self._log_sync, appointment_id, event_type, payload)
    def _log_sync(self, appointment_id: UUID, event_type: str, payload: dict) -> None:
        import psycopg
        with psycopg.connect(self.database_url) as conn: conn.execute("INSERT INTO workflow_events (appointment_id,event_type,payload) VALUES (%s,%s,%s::jsonb)", (appointment_id,event_type,json.dumps(payload, default=str)))
