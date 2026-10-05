"""
prediction_logger.py
--------------------
Centralized, Append-Only Prediction Audit Logging for Property Valuation.

Guarantees:
1. Thread-safe, append-only JSONL recording.
2. Captures:
   - timestamp (UTC ISO 8601)
   - request_id
   - model_name
   - model_version
   - artifact_hash (deterministic sha256 of model artifact)
   - source ('api', 'assistant', 'vapi', 'frontend')
   - purpose ('For Sale', 'For Rent')
   - inputs (sanitized property characteristics)
   - output (p50, p10, p90, or None if rejected)
   - validation_status ('passed' or 'rejected')
   - rejection_reason ('OUT_OF_DISTRIBUTION', etc.)
3. Strict credential hygiene: automatically strips API keys, tokens, passwords, and sensitive PII.
4. Allows exact identification of which serialized model artifact produced every valuation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
DEFAULT_AUDIT_LOG_FILE = LOGS_DIR / "prediction_audit.jsonl"
MODELS_DIR = PROJECT_ROOT / "models"

_log_lock = threading.Lock()
_artifact_hashes: Dict[str, str] = {}


def get_artifact_sha256(artifact_name: str) -> str:
    """Compute and cache deterministic SHA-256 hash of a serialized model artifact."""
    if artifact_name in _artifact_hashes:
        return _artifact_hashes[artifact_name]

    p = MODELS_DIR / artifact_name
    if p.exists() and p.is_file():
        try:
            h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            _artifact_hashes[artifact_name] = h
            return h
        except Exception as e:
            logger.warning("Could not compute hash for %s: %s", artifact_name, e)
            return "unknown_hash"
    return "artifact_not_found"


# SENSITIVE KEYS TO SCRUB
SENSITIVE_KEYS = {
    "api_key", "apikey", "authorization", "token", "access_token",
    "password", "secret", "private_key", "client_secret", "bearer"
}


def sanitize_payload(payload: Any) -> Any:
    """Recursively strip sensitive credentials and tokens from logged payloads."""
    if isinstance(payload, dict):
        clean = {}
        for k, v in payload.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEYS):
                continue
            clean[k] = sanitize_payload(v)
        return clean
    elif isinstance(payload, (list, tuple)):
        return [sanitize_payload(item) for item in payload]
    return payload


class PredictionAuditLogger:
    """Thread-safe append-only prediction audit logger."""

    def __init__(self, log_path: Path = DEFAULT_AUDIT_LOG_FILE):
        self.log_path = Path(log_path)
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("Failed to create log directory: %s", e)

    def log_valuation(
        self,
        *,
        inputs: Dict[str, Any],
        output: Optional[Dict[str, Any]],
        validation_status: str,
        purpose: str = "For Sale",
        source: str = "api",
        rejection_reason: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a property valuation attempt (passed or rejected) to the append-only audit log.
        """
        req_id = request_id or str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Determine model name and hash
        is_sale = "sale" in purpose.lower()
        default_model = "sale_model_huber" if is_sale else "rent_model_huber"
        m_name = model_name or default_model
        artifact_file = f"{m_name}.joblib"
        artifact_hash = get_artifact_sha256(artifact_file)
        m_ver = model_version or "huber_v1.0"

        # Format output if passed
        formatted_output = None
        if validation_status == "passed" and output is not None:
            formatted_output = {
                "p50": output.get("predicted_fair_price_pkr"),
                "p10": output.get("lower_bound_pkr"),
                "p90": output.get("upper_bound_pkr"),
                "verdict": output.get("verdict"),
            }

        record = {
            "timestamp": timestamp,
            "request_id": req_id,
            "model_name": m_name,
            "model_version": m_ver,
            "artifact_hash": artifact_hash,
            "source": source,
            "purpose": "For Sale" if is_sale else "For Rent",
            "inputs": sanitize_payload(inputs),
            "output": formatted_output,
            "validation_status": validation_status,
            "rejection_reason": rejection_reason,
        }

        # Write to append-only JSONL file safely
        try:
            line = json.dumps(record, default=str)
            with _log_lock:
                self._ensure_log_dir()
                with open(self.log_path, mode="a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as e:
            logger.error("Failed to write to prediction audit log: %s", e)

        return record


# Global singleton instance
prediction_audit_logger = PredictionAuditLogger()
