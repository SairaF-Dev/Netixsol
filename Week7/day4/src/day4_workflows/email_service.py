"""Non-blocking email notification gateways."""
from __future__ import annotations
import asyncio, html, smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
from .models import Appointment

class EmailError(RuntimeError): pass

@dataclass(frozen=True)
class OutboundEmail:
    recipient: str
    subject: str
    text: str
    html: str

class EmailGateway(Protocol):
    async def send(self, message: OutboundEmail) -> None: ...

class InMemoryEmailGateway:
    def __init__(self, fail: bool = False) -> None: self.messages, self.fail = [], fail
    async def send(self, message: OutboundEmail) -> None:
        if self.fail: raise EmailError("simulated email failure")
        self.messages.append(message)

class SMTPEmailGateway:
    def __init__(self, host: str, port: int, sender: str, username: str | None, password: str | None, use_tls: bool = True) -> None:
        self.host, self.port, self.sender, self.username, self.password, self.use_tls = host, port, sender, username, password, use_tls
    async def send(self, message: OutboundEmail) -> None: await asyncio.to_thread(self._send_sync, message)
    def _send_sync(self, message: OutboundEmail) -> None:
        email = EmailMessage(); email["From"], email["To"], email["Subject"] = self.sender, message.recipient, message.subject
        email.set_content(message.text); email.add_alternative(message.html, subtype="html")
        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as client:
                if self.use_tls: client.starttls()
                if self.username: client.login(self.username, self.password or "")
                client.send_message(email)
        except (OSError, smtplib.SMTPException) as exc: raise EmailError(str(exc)) from exc

def appointment_email(appointment: Appointment, action: str) -> OutboundEmail:
    request = appointment.request
    label = {"booked": "New appointment", "rescheduled": "Appointment rescheduled", "cancelled": "Appointment cancelled"}[action]
    when = request.starts_at.strftime("%d %b %Y, %I:%M %p %Z")
    values = {k: html.escape(str(v)) for k, v in {"label": label, "client": request.client_name, "phone": request.client_phone, "property": request.property_name, "time": when, "notes": request.meeting_notes}.items()}
    text = f"{label}\nClient: {request.client_name}\nPhone: {request.client_phone}\nProperty: {request.property_name}\nTime: {when}\nNotes: {request.meeting_notes}"
    body = f"<h2>{values['label']}</h2><p><b>Client:</b> {values['client']}</p><p><b>Phone:</b> {values['phone']}</p><p><b>Property:</b> {values['property']}</p><p><b>Time:</b> {values['time']}</p><p><b>Notes:</b> {values['notes']}</p>"
    return OutboundEmail(str(request.employee_email), f"{label}: {request.property_name}", text, body)

def customer_appointment_email(appointment: Appointment, action: str) -> OutboundEmail | None:
    """Customer-facing confirmation; skipped when no email was collected."""
    if not appointment.request.client_email:
        return None
    message = appointment_email(appointment, action)
    return OutboundEmail(appointment.request.client_email, message.subject, message.text, message.html)

def follow_up_email(appointment: Appointment) -> OutboundEmail:
    request = appointment.request
    recipient = request.client_email or str(request.employee_email)
    when = request.starts_at.strftime("%d %b %Y, %I:%M %p %Z")
    subject = f"Reminder: {request.property_name} visit"
    text = f"Assalam-o-Alaikum {request.client_name},\n\nAapki {request.property_name} visit {when} par scheduled hai. Agar time change karna ho to RealEstate Hub se rabta karein."
    body = f"<p>Assalam-o-Alaikum {html.escape(request.client_name)},</p><p>Aapki <b>{html.escape(request.property_name)}</b> visit <b>{html.escape(when)}</b> par scheduled hai.</p><p>Agar time change karna ho to RealEstate Hub se rabta karein.</p>"
    return OutboundEmail(recipient, subject, text, body)
