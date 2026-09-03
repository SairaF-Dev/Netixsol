"""Attach a customer email to an appointment and resend its confirmation."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from day4_workflows.crm_logging import PostgresCRMRepository
from day4_workflows.email_service import SMTPEmailGateway, customer_appointment_email


async def main(appointment_id: UUID, customer_email: str) -> None:
    database_url = os.environ["DATABASE_URL"]
    with psycopg.connect(database_url) as connection:
        updated = connection.execute(
            """
            UPDATE appointments
               SET request_json = jsonb_set(
                       request_json,
                       '{client_email}',
                       to_jsonb(%s::text),
                       true
                   ),
                   updated_at = NOW()
             WHERE appointment_id = %s
         RETURNING appointment_id
            """,
            (customer_email, appointment_id),
        ).fetchone()
    if not updated:
        raise SystemExit(f"Appointment not found: {appointment_id}")

    repository = PostgresCRMRepository(database_url)
    appointment = await repository.get_appointment(appointment_id)
    message = customer_appointment_email(appointment, "booked")
    if message is None:
        raise RuntimeError("Customer confirmation could not be generated")

    gateway = SMTPEmailGateway(
        os.environ["SMTP_HOST"],
        int(os.getenv("SMTP_PORT", "587")),
        os.environ["SMTP_SENDER"],
        os.getenv("SMTP_USERNAME"),
        os.getenv("SMTP_PASSWORD"),
        os.getenv("SMTP_USE_TLS", "1") not in {"0", "false", "False"},
    )
    await gateway.send(message)
    print(f"Confirmation sent to {message.recipient}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("appointment_id", type=UUID)
    parser.add_argument("customer_email")
    args = parser.parse_args()
    asyncio.run(main(args.appointment_id, args.customer_email))
