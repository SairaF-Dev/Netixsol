"""Environment configuration with safe local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite:///./day4.db"
    calendar_backend: str = "memory"
    google_service_account_file: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str = "appointments@example.invalid"
    smtp_use_tls: bool = True
    n8n_webhook_url: str | None = None
    n8n_api_key: str | None = None
    workflow_timeout_seconds: float = 8.0
    workflow_max_attempts: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./day4.db"),
            calendar_backend=os.getenv("CALENDAR_BACKEND", "memory").lower(),
            google_service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_sender=os.getenv("SMTP_SENDER", "appointments@example.invalid"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "1") not in {"0", "false", "False"},
            n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL"),
            n8n_api_key=os.getenv("N8N_API_KEY"),
            workflow_timeout_seconds=float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "8")),
            workflow_max_attempts=int(os.getenv("WORKFLOW_MAX_ATTEMPTS", "3")),
        )
