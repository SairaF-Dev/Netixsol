"""Calendar ports and Google/in-memory implementations."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4

class CalendarError(RuntimeError): pass
class SlotUnavailable(CalendarError): pass
class CalendarEventNotFound(CalendarError): pass

@dataclass(frozen=True)
class CalendarEvent:
    event_id: str
    calendar_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    description: str
    attendees: tuple[str, ...] = ()
    link: str | None = None

class CalendarGateway(Protocol):
    async def is_available(self, calendar_id: str, starts_at: datetime, ends_at: datetime, *, exclude_event_id: str | None = None) -> bool: ...
    async def create_event(self, event: CalendarEvent) -> CalendarEvent: ...
    async def reschedule_event(self, calendar_id: str, event_id: str, starts_at: datetime, ends_at: datetime) -> CalendarEvent: ...
    async def cancel_event(self, calendar_id: str, event_id: str) -> None: ...

class InMemoryCalendarGateway:
    def __init__(self) -> None:
        self.events: dict[str, CalendarEvent] = {}
        self._lock = asyncio.Lock()

    async def is_available(self, calendar_id: str, starts_at: datetime, ends_at: datetime, *, exclude_event_id: str | None = None) -> bool:
        if ends_at <= starts_at: return False
        return not any(e.calendar_id == calendar_id and e.event_id != exclude_event_id and starts_at < e.ends_at and ends_at > e.starts_at for e in self.events.values())

    async def create_event(self, event: CalendarEvent) -> CalendarEvent:
        async with self._lock:
            if not await self.is_available(event.calendar_id, event.starts_at, event.ends_at):
                raise SlotUnavailable("The selected employee is not available at that time")
            event_id = event.event_id or uuid4().hex
            created = CalendarEvent(**{**event.__dict__, "event_id": event_id, "link": event.link or f"memory://calendar/{event_id}"})
            self.events[event_id] = created
            return created

    async def reschedule_event(self, calendar_id: str, event_id: str, starts_at: datetime, ends_at: datetime) -> CalendarEvent:
        async with self._lock:
            current = self.events.get(event_id)
            if current is None or current.calendar_id != calendar_id: raise CalendarEventNotFound(event_id)
            if not await self.is_available(calendar_id, starts_at, ends_at, exclude_event_id=event_id): raise SlotUnavailable("The selected employee is not available at that time")
            updated = CalendarEvent(**{**current.__dict__, "starts_at": starts_at, "ends_at": ends_at})
            self.events[event_id] = updated
            return updated

    async def cancel_event(self, calendar_id: str, event_id: str) -> None:
        async with self._lock:
            event = self.events.get(event_id)
            if event is None or event.calendar_id != calendar_id: raise CalendarEventNotFound(event_id)
            del self.events[event_id]

class GoogleCalendarGateway:
    """Async wrapper using service-account credentials; no browser OAuth in the API."""
    scopes = ("https://www.googleapis.com/auth/calendar",)
    def __init__(self, service_account_file: str) -> None:
        if not service_account_file: raise CalendarError("GOOGLE_SERVICE_ACCOUNT_FILE is required")
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc: raise CalendarError("Install Google Calendar dependencies") from exc
        credentials = service_account.Credentials.from_service_account_file(service_account_file, scopes=self.scopes)
        self._service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    async def is_available(self, calendar_id: str, starts_at: datetime, ends_at: datetime, *, exclude_event_id: str | None = None) -> bool:
        body = {"timeMin": starts_at.isoformat(), "timeMax": ends_at.isoformat(), "items": [{"id": calendar_id}]}
        response = await asyncio.to_thread(lambda: self._service.freebusy().query(body=body).execute())
        if not response.get("calendars", {}).get(calendar_id, {}).get("busy", []): return True
        if not exclude_event_id: return False
        result = await asyncio.to_thread(lambda: self._service.events().list(calendarId=calendar_id, timeMin=starts_at.isoformat(), timeMax=ends_at.isoformat(), singleEvents=True).execute())
        return not any(item.get("id") != exclude_event_id for item in result.get("items", []))

    async def create_event(self, event: CalendarEvent) -> CalendarEvent:
        if not await self.is_available(event.calendar_id, event.starts_at, event.ends_at): raise SlotUnavailable("The selected employee is not available at that time")
        created = await asyncio.to_thread(lambda: self._service.events().insert(calendarId=event.calendar_id, body=self._body(event), sendUpdates="all").execute())
        return CalendarEvent(**{**event.__dict__, "event_id": created["id"], "link": created.get("htmlLink")})

    async def reschedule_event(self, calendar_id: str, event_id: str, starts_at: datetime, ends_at: datetime) -> CalendarEvent:
        if not await self.is_available(calendar_id, starts_at, ends_at, exclude_event_id=event_id): raise SlotUnavailable("The selected employee is not available at that time")
        current = await asyncio.to_thread(lambda: self._service.events().get(calendarId=calendar_id, eventId=event_id).execute())
        current["start"], current["end"] = {"dateTime": starts_at.isoformat()}, {"dateTime": ends_at.isoformat()}
        updated = await asyncio.to_thread(lambda: self._service.events().update(calendarId=calendar_id, eventId=event_id, body=current, sendUpdates="all").execute())
        return CalendarEvent(event_id, calendar_id, updated.get("summary", "Property visit"), starts_at, ends_at, updated.get("description", ""), tuple(x["email"] for x in updated.get("attendees", [])), updated.get("htmlLink"))

    async def cancel_event(self, calendar_id: str, event_id: str) -> None:
        await asyncio.to_thread(lambda: self._service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute())

    @staticmethod
    def _body(event: CalendarEvent) -> dict:
        return {"summary": event.title, "description": event.description, "start": {"dateTime": event.starts_at.isoformat()}, "end": {"dateTime": event.ends_at.isoformat()}, "attendees": [{"email": x} for x in event.attendees], "extendedProperties": {"private": {"source": "sara-day4"}}}
