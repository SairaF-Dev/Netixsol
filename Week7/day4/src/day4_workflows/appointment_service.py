"""Transactional booking, rescheduling and cancellation use cases."""
from __future__ import annotations
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from .calendar_service import CalendarEvent, CalendarGateway
from .crm_logging import CRMRepository
from .email_service import EmailGateway, appointment_email, customer_appointment_email, follow_up_email
from .models import Appointment, AppointmentRequest, AppointmentStatus, WorkflowResult

class InvalidAppointmentState(RuntimeError): pass

class AppointmentWorkflowService:
    def __init__(self, calendar: CalendarGateway, email: EmailGateway, crm: CRMRepository, publisher) -> None:
        self.calendar, self.email, self.crm, self.publisher = calendar, email, crm, publisher
    async def book(self, request: AppointmentRequest) -> WorkflowResult:
        ends_at = request.starts_at + timedelta(minutes=request.duration_minutes)
        if not await self.calendar.is_available(request.employee_calendar_id, request.starts_at, ends_at):
            from .calendar_service import SlotUnavailable
            raise SlotUnavailable("The selected employee is not available at that time")
        now = datetime.now().astimezone()
        appointment = Appointment(request=request, status=AppointmentStatus.PENDING, created_at=now, updated_at=now)
        await self.crm.save_appointment(appointment)
        # The service account owns the configured calendar. Adding an attendee
        # requires Google Workspace domain-wide delegation and makes consumer
        # Gmail/service-account bookings fail. Employee notification is sent
        # separately through the email gateway.
        event = CalendarEvent("", request.employee_calendar_id, f"Property visit: {request.property_name}", request.starts_at, ends_at, self._description(request), ())
        created = await self.calendar.create_event(event)
        appointment = appointment.model_copy(update={"status": AppointmentStatus.CONFIRMED, "calendar_event_id": created.event_id, "calendar_link": created.link, "updated_at": datetime.now().astimezone()})
        await self.crm.save_appointment(appointment); await self.crm.log_workflow_event(appointment.appointment_id, "booked", self._payload(appointment))
        warnings, sent = await self._notify(appointment, "booked")
        event_id = await self._publish("appointment.booked", appointment, warnings)
        return WorkflowResult(appointment=appointment, notification_sent=sent, workflow_event_id=event_id, warnings=warnings)
    async def reschedule(self, appointment_id: UUID, starts_at: datetime) -> WorkflowResult:
        if starts_at.tzinfo is None: raise ValueError("starts_at must include a timezone offset")
        appointment = await self.crm.get_appointment(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED or not appointment.calendar_event_id: raise InvalidAppointmentState("A cancelled or unconfirmed appointment cannot be rescheduled")
        old = appointment.request.starts_at; ends_at = starts_at + timedelta(minutes=appointment.request.duration_minutes)
        await self.calendar.reschedule_event(appointment.request.employee_calendar_id, appointment.calendar_event_id, starts_at, ends_at)
        request = appointment.request.model_copy(update={"starts_at": starts_at})
        appointment = appointment.model_copy(update={"request": request, "status": AppointmentStatus.RESCHEDULED, "previous_starts_at": old, "updated_at": datetime.now().astimezone()})
        await self.crm.save_appointment(appointment); await self.crm.log_workflow_event(appointment_id, "rescheduled", self._payload(appointment))
        warnings, sent = await self._notify(appointment, "rescheduled")
        event_id = await self._publish("appointment.rescheduled", appointment, warnings)
        return WorkflowResult(appointment=appointment, notification_sent=sent, workflow_event_id=event_id, warnings=warnings)
    async def cancel(self, appointment_id: UUID) -> WorkflowResult:
        appointment = await self.crm.get_appointment(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED: raise InvalidAppointmentState("Appointment is already cancelled")
        if not appointment.calendar_event_id: raise InvalidAppointmentState("Appointment has no confirmed calendar event")
        await self.calendar.cancel_event(appointment.request.employee_calendar_id, appointment.calendar_event_id)
        appointment = appointment.model_copy(update={"status": AppointmentStatus.CANCELLED, "updated_at": datetime.now().astimezone()})
        await self.crm.save_appointment(appointment); await self.crm.log_workflow_event(appointment_id, "cancelled", self._payload(appointment))
        warnings, sent = await self._notify(appointment, "cancelled")
        event_id = await self._publish("appointment.cancelled", appointment, warnings)
        return WorkflowResult(appointment=appointment, notification_sent=sent, workflow_event_id=event_id, warnings=warnings)
    async def send_follow_up(self, appointment_id: UUID) -> dict:
        appointment = await self.crm.get_appointment(appointment_id)
        if appointment.status == AppointmentStatus.CANCELLED:
            return {"sent": False, "reason": "appointment_cancelled"}
        await self.email.send(follow_up_email(appointment))
        await self.crm.log_workflow_event(appointment_id, "follow_up_sent", self._payload(appointment))
        return {"sent": True, "appointment_id": str(appointment_id)}
    async def _notify(self, appointment: Appointment, action: str) -> tuple[list[str], bool]:
        try:
            await self.email.send(appointment_email(appointment, action))
            customer_message = customer_appointment_email(appointment, action)
            if customer_message:
                await self.email.send(customer_message)
            return [], True
        except Exception as exc: return [f"Email notification failed: {type(exc).__name__}"], False
    async def _publish(self, event_type: str, appointment: Appointment, warnings: list[str]) -> str | None:
        try: return await self.publisher.publish(event_type, self._payload(appointment))
        except Exception as exc: warnings.append(f"n8n notification failed: {type(exc).__name__}"); return None
    @staticmethod
    def _description(r: AppointmentRequest) -> str: return f"Client: {r.client_name}\nPhone: {r.client_phone}\nEmployee: {r.employee_name}\nProperty ID: {r.property_id}\nNotes: {r.meeting_notes}"
    @staticmethod
    def _payload(a: Appointment) -> dict: return a.model_dump(mode="json")
