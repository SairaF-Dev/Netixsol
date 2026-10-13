"""Environment configuration with safe local defaults."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite:///./day4.db"
    calendar_backend: str = "memory"
    google_service_account_file: str | None = None
    google_service_account_json: str | None = None
    google_calendar_id: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str = "appointments@example.invalid"
    smtp_use_tls: bool = True
    email_backend: str = "smtp"
    google_apps_script_url: str | None = None
    google_apps_script_token: str | None = None
    internal_api_key: str | None = None
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
            google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
            google_calendar_id=os.getenv("GOOGLE_CALENDAR_ID"),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_sender=os.getenv("SMTP_SENDER", "appointments@example.invalid"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "1") not in {"0", "false", "False"},
            email_backend=os.getenv("EMAIL_BACKEND", "smtp").strip().lower(),
            google_apps_script_url=os.getenv("GOOGLE_APPS_SCRIPT_URL"),
            google_apps_script_token=os.getenv("GOOGLE_APPS_SCRIPT_TOKEN"),
            internal_api_key=os.getenv("DAY4_API_KEY"),
            n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL"),
            n8n_api_key=os.getenv("N8N_API_KEY"),
            workflow_timeout_seconds=float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "8")),
            workflow_max_attempts=int(os.getenv("WORKFLOW_MAX_ATTEMPTS", "3")),
        )

    def validate_for_production(self, *, base_dir: Path) -> None:
        if self.app_env.casefold() not in {"prod", "production"}:
            return

        missing: list[str] = []
        if not self.database_url.startswith(("postgres://", "postgresql://")):
            missing.append("DATABASE_URL must use PostgreSQL")
        if self.calendar_backend != "google":
            missing.append("CALENDAR_BACKEND must be google")
        if self.google_service_account_json:
            try:
                credential_info = json.loads(self.google_service_account_json)
            except json.JSONDecodeError:
                missing.append("GOOGLE_SERVICE_ACCOUNT_JSON must contain valid JSON")
            else:
                if not isinstance(credential_info, dict) or credential_info.get("type") != "service_account":
                    missing.append("GOOGLE_SERVICE_ACCOUNT_JSON must be a service-account JSON object")
        elif not self.google_service_account_file:
            missing.append("GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON is required")
        else:
            credential_path = Path(self.google_service_account_file)
            if not credential_path.is_absolute():
                credential_path = base_dir / credential_path
            if not credential_path.is_file():
                missing.append("GOOGLE_SERVICE_ACCOUNT_FILE must point to an existing secret file")
        if not self.google_calendar_id:
            missing.append("GOOGLE_CALENDAR_ID is required")
        if self.email_backend == "google_apps_script":
            relay_url = urlparse(self.google_apps_script_url or "")
            if relay_url.scheme != "https" or relay_url.hostname != "script.google.com":
                missing.append("GOOGLE_APPS_SCRIPT_URL must be a deployed https://script.google.com URL")
            if not self.google_apps_script_token:
                missing.append("GOOGLE_APPS_SCRIPT_TOKEN is required")
        elif self.email_backend == "smtp":
            if not self.smtp_host:
                missing.append("SMTP_HOST is required")
            if not self.smtp_username:
                missing.append("SMTP_USERNAME is required")
            if not self.smtp_password:
                missing.append("SMTP_PASSWORD is required")
            if not self.smtp_sender or self.smtp_sender.casefold().endswith(".invalid"):
                missing.append("SMTP_SENDER must be a deliverable sender address")
        else:
            missing.append("EMAIL_BACKEND must be smtp or google_apps_script")
        if not self.internal_api_key:
            missing.append("DAY4_API_KEY is required")
        if missing:
            raise ValueError("Production appointment service configuration is incomplete: " + "; ".join(missing))
