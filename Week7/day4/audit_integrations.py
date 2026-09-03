"""Read-only integration checks used by the capstone audit."""

from __future__ import annotations

import asyncio
import os
import smtplib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def check_postgres() -> str:
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM appointments")
            count = cursor.fetchone()[0]
    return f"ok (appointments={count})"


def check_smtp() -> str:
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=10) as client:
        if os.getenv("SMTP_USE_TLS", "1") not in {"0", "false", "False"}:
            client.starttls()
        client.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
    return "ok (authenticated; no email sent)"


async def check_google_calendar() -> str:
    from src.day4_workflows.calendar_service import GoogleCalendarGateway

    credential_path = Path(os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"])
    if not credential_path.is_absolute():
        credential_path = ROOT / credential_path
    gateway = GoogleCalendarGateway(str(credential_path))
    start = datetime.now(timezone.utc) + timedelta(days=3650)
    end = start + timedelta(minutes=15)
    await gateway.is_available("primary", start, end)
    return "ok (free/busy read succeeded; no event created)"


async def main() -> None:
    checks = {
        "postgres": lambda: asyncio.to_thread(check_postgres),
        "smtp": lambda: asyncio.to_thread(check_smtp),
        "google_calendar": check_google_calendar,
    }
    for name, check in checks.items():
        try:
            result = await check()
        except Exception as exc:
            result = f"failed ({type(exc).__name__}: {exc})"
        print(f"{name}: {result}")


if __name__ == "__main__":
    asyncio.run(main())
