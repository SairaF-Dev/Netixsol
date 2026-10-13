"""Non-blocking email notification gateways."""
from __future__ import annotations
import asyncio, html, smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlparse

import httpx

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

class GoogleAppsScriptEmailGateway:
    def __init__(self, url: str, token: str, timeout: float = 12.0) -> None:
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.hostname != "script.google.com":
            raise ValueError("Google Apps Script email relay URL must use https://script.google.com")
        if not token:
            raise ValueError("Google Apps Script email relay token is required")
        self.url, self.token, self.timeout = url, token, timeout

    async def send(self, message: OutboundEmail) -> None:
        payload = {
            "token": self.token,
            "to": message.recipient,
            "subject": message.subject,
            "text": message.text,
            "html": message.html,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise EmailError("Google Apps Script email relay request failed") from exc

        if not isinstance(result, dict) or result.get("ok") is not True:
            raise EmailError("Google Apps Script email relay did not confirm delivery")

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
    request = appointment.request
    if not request.client_email:
        return None

    first_name = (request.client_name or "").split()[0] if request.client_name else "Valued Client"

    try:
        from zoneinfo import ZoneInfo
        pkt_time = request.starts_at.astimezone(ZoneInfo("Asia/Karachi"))
    except Exception:
        from datetime import timezone, timedelta
        pkt_time = request.starts_at.astimezone(timezone(timedelta(hours=5)))

    formatted_time = pkt_time.strftime("%A, %B %d, %Y at %I:%M %p PKT")

    raw_agent = request.agent or request.employee_name
    agent_name = raw_agent if (raw_agent and raw_agent != "Verified Property Specialist") else "Azam Ali"
    raw_agency = request.agency
    agency_name = raw_agency if (raw_agency and raw_agency not in ("Real Estate Hub Partners", "Sara AI Support")) else "Mash Allah Estate & Builders"
    agent_phone = request.agent_phone or "+92 300 8472910"
    meeting_spot = request.meeting_spot or (f"{request.location}, {request.city}" if request.location else "Property Main Entrance")

    if action == "cancelled":
        subject = f"Cancelled: Visit for {request.property_name}"
        status_label = "Cancelled"
        badge_html = '<span style="display:inline-block;padding:5px 12px;background:#fee2e2;color:#991b1b;border:1px solid #fecaca;border-radius:6px;font-weight:700;font-size:12px;text-transform:uppercase;">Cancelled</span>'
        greeting_line = f"Dear {html.escape(first_name)}, your scheduled property tour has been <b>cancelled</b> as requested."
        banner_bg = "#991b1b"
        banner_title = "Visit Cancelled"
        notice_box = """
        <div style="margin-top:20px;padding:16px;background:#fef2f2;border-left:4px solid #ef4444;border-radius:6px;color:#991b1b;font-size:14px;line-height:1.5;">
            <b>Important Notice:</b> Yeh visit slot cancel kar diya gaya hai. Agar aap dobara visit schedule karna chahein, to aap hamari website se kisi bhi waqt naya tour book kar sakte hain.
        </div>
        """
    elif action == "rescheduled":
        subject = f"Rescheduled: Visit for {request.property_name} with {agency_name}"
        status_label = "Rescheduled"
        badge_html = '<span style="display:inline-block;padding:5px 12px;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;border-radius:6px;font-weight:700;font-size:12px;text-transform:uppercase;">Rescheduled</span>'
        greeting_line = f"Dear {html.escape(first_name)}, your tour for <b>{html.escape(request.property_name)}</b> has been successfully rescheduled with <b>{html.escape(agency_name)}</b>."
        banner_bg = "#1d4ed8"
        banner_title = "Visit Rescheduled"
        notice_box = """
        <div style="margin-top:20px;padding:16px;background:#f0fdf4;border-left:4px solid #16a34a;border-radius:6px;color:#166534;font-size:14px;line-height:1.5;">
            <b>Meeting Instructions:</b> Kindly arrive at the meeting spot 10 minutes prior to the scheduled time. Aapke dedicated property specialist time par wahan maujood honge.
        </div>
        """
    else:
        subject = f"Confirmed: Visit for {request.property_name} with {agency_name}"
        status_label = "Confirmed"
        badge_html = '<span style="display:inline-block;padding:5px 12px;background:#e8f5e9;color:#166534;border:1px solid #bbf7d0;border-radius:6px;font-weight:700;font-size:12px;text-transform:uppercase;">Confirmed</span>'
        greeting_line = f"Dear {html.escape(first_name)}, thank you for booking a tour with <b>{html.escape(agency_name)}</b>!"
        banner_bg = "#1e3a2f"
        banner_title = "Property Visit Confirmed"
        notice_box = """
        <div style="margin-top:20px;padding:16px;background:#f0fdf4;border-left:4px solid #16a34a;border-radius:6px;color:#166534;font-size:14px;line-height:1.5;">
            <b>Meeting Instructions:</b> Kindly arrive at the meeting spot 10 minutes prior to the scheduled time. Aapke dedicated property specialist time par wahan maujood honge.
        </div>
        """

    text = f"{subject}\n\n{greeting_line}\n\nProperty: {request.property_name}\nTime: {formatted_time}\nAgency: {agency_name}\nAgent: {agent_name} ({agent_phone})\nMeeting Spot: {meeting_spot}\nStatus: {status_label}\n"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{html.escape(subject)}</title>
    </head>
    <body style="margin:0;padding:24px 12px;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f172a;">
      <div style="max-width:600px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.06);border:1px solid #e2e8f0;">
        <!-- Brand Header -->
        <div style="background:{banner_bg};padding:24px 28px;color:#ffffff;display:flex;align-items:center;justify-content:space-between;">
          <div>
            <h1 style="margin:0;font-size:20px;font-weight:700;letter-spacing:-0.02em;">{banner_title}</h1>
            <p style="margin:4px 0 0;font-size:13px;opacity:0.85;">Real Estate Hub • Verified Properties</p>
          </div>
          <div>{badge_html}</div>
        </div>

        <!-- Body Content -->
        <div style="padding:28px;">
          <p style="font-size:16px;line-height:1.5;margin:0 0 20px;color:#1e293b;">
            {greeting_line}
          </p>

          <!-- Visit Details Card -->
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:18px 20px;margin-bottom:20px;">
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
              <tr>
                <td style="padding:8px 0;color:#64748b;font-weight:600;width:120px;">Property</td>
                <td style="padding:8px 0;color:#0f172a;font-weight:700;">{html.escape(request.property_name)}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;color:#64748b;font-weight:600;">Date & Time</td>
                <td style="padding:8px 0;color:#1e3a2f;font-weight:700;">🗓️ {html.escape(formatted_time)}</td>
              </tr>
              <tr>
                <td style="padding:8px 0;color:#64748b;font-weight:600;">Meeting Spot</td>
                <td style="padding:8px 0;color:#0f172a;font-weight:500;">📍 {html.escape(meeting_spot)}</td>
              </tr>
              {f'<tr><td style="padding:8px 0;color:#64748b;font-weight:600;">Client Notes</td><td style="padding:8px 0;color:#475569;font-style:italic;">"{html.escape(request.meeting_notes)}"</td></tr>' if request.meeting_notes else ''}
            </table>
          </div>

          <!-- Grounded Agent & Agency Card -->
          <div style="background:#ffffff;border:1px solid #cbd5e1;border-radius:10px;padding:18px 20px;margin-bottom:20px;">
            <h3 style="margin:0 0 12px;font-size:14px;color:#0f172a;text-transform:uppercase;letter-spacing:0.04em;">Assigned Property Specialist</h3>
            <div style="display:flex;align-items:center;gap:14px;">
              <div style="width:44px;height:44px;border-radius:50%;background:#1e3a2f;color:#ffffff;font-size:16px;font-weight:800;display:flex;align-items:center;justify-content:center;text-align:center;line-height:44px;">
                {html.escape(agent_name[:2].upper())}
              </div>
              <div>
                <div style="font-size:15px;font-weight:700;color:#0f172a;">{html.escape(agent_name)}</div>
                <div style="font-size:13px;color:#64748b;margin-top:2px;">🏢 {html.escape(agency_name)}</div>
                <div style="font-size:13px;color:#0369a1;margin-top:2px;">📞 {html.escape(agent_phone)}</div>
              </div>
            </div>
          </div>

          {notice_box}
        </div>

        <!-- Footer -->
        <div style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:18px 28px;text-align:center;font-size:12px;color:#94a3b8;">
          <p style="margin:0;">Real Estate Hub Pakistan • Verified Real Estate Network</p>
          <p style="margin:4px 0 0;">Need help? Reply directly to this email or visit our website.</p>
        </div>
      </div>
    </body>
    </html>
    """
    return OutboundEmail(request.client_email, subject, text, html_content)

def follow_up_email(appointment: Appointment) -> OutboundEmail:
    request = appointment.request
    recipient = request.client_email or str(request.employee_email)
    when = request.starts_at.strftime("%d %b %Y, %I:%M %p %Z")
    subject = f"Reminder: {request.property_name} visit"
    text = f"Assalam-o-Alaikum {request.client_name},\n\nAapki {request.property_name} visit {when} par scheduled hai. Agar time change karna ho to RealEstate Hub se rabta karein."
    body = f"<p>Assalam-o-Alaikum {html.escape(request.client_name)},</p><p>Aapki <b>{html.escape(request.property_name)}</b> visit <b>{html.escape(when)}</b> par scheduled hai.</p><p>Agar time change karna ho to RealEstate Hub se rabta karein.</p>"
    return OutboundEmail(recipient, subject, text, body)
