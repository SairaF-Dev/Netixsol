import json
import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger("sre_agent")


def setup_monitoring():
    """
    Configure application monitoring.
    """

    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(
            "api_monitoring.log",
            encoding="utf-8"
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)


def log_event(
    event: str,
    incident_id: str,
    **data: Any
):
    """
    Write a structured monitoring event.
    """

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),  
        "event": event,
        "incident_id": incident_id,
        **data,
    }

    logger.info(
        json.dumps(
            payload,
            default=str
        )
    )