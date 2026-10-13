"""
lead_scoring_service.py
-----------------------
Week 7 Voice Agent + Week 8 ML Integration Service.

Fulfills:
- Task 4B: Post-call lead scoring via Week 8 POST /predict/lead-score
- Task 4C: Hot Lead email notification to assigned real estate agent/employee
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, Optional

import httpx

_DAY4_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "day4", "src"))
if _DAY4_SRC not in sys.path:
    sys.path.insert(0, _DAY4_SRC)

from day4_workflows.email_service import (
    EmailError,
    GoogleAppsScriptEmailGateway,
    OutboundEmail,
)

logger = logging.getLogger("vapi.lead_scoring")

WEEK8_API_URL = os.getenv("WEEK8_API_URL", "http://localhost:8000").rstrip("/")
EMPLOYEE_EMAIL = os.getenv("EMPLOYEE_EMAIL", "").strip()
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "smtp").strip().lower()
GOOGLE_APPS_SCRIPT_URL = os.getenv("GOOGLE_APPS_SCRIPT_URL", "").strip()
GOOGLE_APPS_SCRIPT_TOKEN = os.getenv("GOOGLE_APPS_SCRIPT_TOKEN", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USERNAME", "")
SMTP_PASS = os.getenv("SMTP_PASSWORD", "")
SMTP_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")


async def score_call_lead(
    caller_phone: str,
    call_duration_seconds: float,
    visit_booked: bool = False,
    client_name: Optional[str] = None,
    preferred_city: Optional[str] = None,
    preferred_location: Optional[str] = None,
    budget_pkr: Optional[float] = None,
    property_type: Optional[str] = None,
    purpose: Optional[str] = None,
    number_of_calls: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Call Week 8 POST /predict/lead-score using actual post-call data and
    safe justified defaults for unobserved fields according to model contract.
    """
    duration_min = max(0.5, round(call_duration_seconds / 60.0, 1))

    payload = {
        "lead_source": "Call",
        "preferred_city": (preferred_city or "Lahore").strip().title(),
        "preferred_location": (preferred_location or "Unknown").strip(),
        "property_type": (property_type or "House").strip().title(),
        "purpose": (purpose or "Buy").strip().title(),
        "budget_pkr": float(budget_pkr or 25_000_000.0),
        "number_of_calls": int(number_of_calls),
        "total_call_duration_min": float(duration_min),
        "response_time_minutes": 5.0,
        "visit_booked": 1 if visit_booked else 0,
        "days_since_first_contact": 1,
        "follow_up_count": 0,
        "budget_match_ratio": 1.0,
        "objection_raised": "None",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(f"{WEEK8_API_URL}/predict/lead-score", json=payload)
            if res.status_code == 200:
                score_data = res.json()
                logger.info(
                    "Lead scored for %s: Tier=%s, Score=%.1f%%, Persona=%s",
                    caller_phone,
                    score_data.get("tier"),
                    score_data.get("lead_score_pct", 0),
                    score_data.get("customer_persona"),
                )
                return score_data
            else:
                logger.warning("Week 8 lead score API returned %d: %s", res.status_code, res.text)
                return None
    except Exception as exc:
        logger.exception("Failed to score lead via Week 8 API: %s", exc)
        return None


async def send_hot_lead_email(
    score_data: Dict[str, Any],
    caller_phone: str,
    client_name: Optional[str] = None,
    call_duration_seconds: float = 0.0,
    recipient_email: Optional[str] = None,
) -> bool:
    """
    Task 4C: Send urgent email alert to assigned employee when a lead is classified as Hot.
    Supports SMTP for local deployments and the Gmail HTTPS relay for free hosts.
    """
    recipient = recipient_email or EMPLOYEE_EMAIL
    if not recipient:
        logger.warning("No recipient employee email configured for hot lead alert.")
        return False

    c_name = client_name or "Phone Inquirer"
    score_pct = score_data.get("lead_score_pct", 0.0)
    tier = score_data.get("tier", "Hot")
    persona = score_data.get("customer_persona", "High-Propensity Buyer")
    action = score_data.get("recommended_sla_action", "Call within 15 minutes")
    urdulish = score_data.get("urdulish_explanation", "")
    duration_str = f"{call_duration_seconds / 60.0:.1f} mins" if call_duration_seconds else "N/A"
    html_values = {
        "client_name": html.escape(c_name),
        "caller_phone": html.escape(caller_phone),
        "score": html.escape(f"{score_pct:.1f}% ({tier})"),
        "persona": html.escape(str(persona)),
        "duration": html.escape(duration_str),
        "action": html.escape(str(action)),
        "explanation": html.escape(str(urdulish)),
    }

    subject = f"[DEMO ONLY] Synthetic-label lead score — {c_name} ({score_pct:.1f}%)"

    text_content = f"""
DEMO MODEL PRIORITY NOTICE
----------------------------
A caller received a HOT follow-up tier from the Week 8 demo model.
The model was trained on synthetic conversion labels and has not been validated
against real CRM outcomes. This percentage is not a validated likelihood of sale.

Customer Name:    {c_name}
Customer Phone:   {caller_phone}
Call Duration:    {duration_str}
Demo Model Score: {score_pct:.1f}% (Tier: {tier})
Customer Persona: {persona}
SLA Action:       {action}

UrduLish Rationale:
"{urdulish}"

Use the recommendation as a demo-only prompt for human review; confirm lead details
and priority independently before acting.
Generated by RealEstate Hub AI Serving Gateway.
""".strip()

    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #17332d; line-height: 1.6;">
  <div style="background-color: #795548; color: white; padding: 18px 24px; border-radius: 8px 8px 0 0;">
    <h2 style="margin: 0;">Demo only: Lead priority suggestion</h2>
    <p style="margin: 4px 0 0; font-size: 0.9em;">Week 8 model trained on synthetic conversion labels</p>
  </div>
  <div style="border: 1px solid #dce2dc; border-top: 0; padding: 24px; border-radius: 0 0 8px 8px; background-color: #ffffff;">
    <p><b>A caller completed a phone consultation with Sara AI. The demo model assigned this follow-up tier:</b></p>
    <p style="background-color: #fff8e1; padding: 12px 16px; border-radius: 6px;">
      This score is not validated against real CRM outcomes and is not a validated likelihood of sale.
      Confirm lead details and priority independently before acting.
    </p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #6b7772;"><b>Customer:</b></td>
        <td style="padding: 8px 0;"><strong>{html_values["client_name"]}</strong></td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #6b7772;"><b>Phone:</b></td>
        <td style="padding: 8px 0;"><strong>{html_values["caller_phone"]}</strong></td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #6b7772;"><b>Demo Model Score:</b></td>
        <td style="padding: 8px 0;"><span style="background-color: #fde8e8; color: #9b1c1c; padding: 3px 8px; border-radius: 12px; font-weight: bold;">{html_values["score"]}</span></td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #6b7772;"><b>Predicted Persona:</b></td>
        <td style="padding: 8px 0;">{html_values["persona"]}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #6b7772;"><b>Call Duration:</b></td>
        <td style="padding: 8px 0;">{html_values["duration"]}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #6b7772;"><b>Recommended SLA:</b></td>
        <td style="padding: 8px 0;"><strong style="color: #214e43;">{html_values["action"]}</strong></td>
      </tr>
    </table>
    <div style="background-color: #f5f1e8; padding: 12px 16px; border-radius: 6px; margin-top: 14px; font-style: italic;">
      &ldquo;{html_values["explanation"]}&rdquo;
    </div>
  </div>
</body>
</html>
""".strip()

    if EMAIL_BACKEND == "google_apps_script":
        if not GOOGLE_APPS_SCRIPT_URL or not GOOGLE_APPS_SCRIPT_TOKEN:
            logger.warning("Gmail relay settings are missing; no hot-lead email was sent.")
            return False
        try:
            gateway = GoogleAppsScriptEmailGateway(
                GOOGLE_APPS_SCRIPT_URL,
                GOOGLE_APPS_SCRIPT_TOKEN,
            )
            await gateway.send(
                OutboundEmail(
                    recipient=recipient,
                    subject=subject,
                    text=text_content,
                    html=html_content,
                )
            )
            logger.info("Hot lead notification email dispatched to %s", recipient)
            return True
        except (EmailError, ValueError) as exc:
            logger.warning("Gmail relay failed; no hot-lead email was sent: %s", exc)
            return False

    if EMAIL_BACKEND != "smtp":
        logger.error("Unsupported email backend %r; no hot-lead email was sent.", EMAIL_BACKEND)
        return False

    # Try SMTP transmission if username and password are provided.
    if SMTP_USER and SMTP_PASS:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = recipient
            msg.set_content(text_content)
            msg.add_alternative(html_content, subtype="html")

            def _send_sync():
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as server:
                    if SMTP_TLS:
                        server.starttls()
                    server.login(SMTP_USER, SMTP_PASS)
                    server.send_message(msg)

            await asyncio.to_thread(_send_sync)
            logger.info("Hot lead notification email dispatched to %s", recipient)
            return True
        except Exception as exc:
            logger.warning("SMTP transmission failed: %s; notification logged locally", exc)
            return False
    else:
        logger.warning("SMTP credentials are not configured; no hot-lead email was sent.")
        return False
