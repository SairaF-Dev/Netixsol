from __future__ import annotations

from collections.abc import Mapping
import logging
import os
from typing import Any


logger = logging.getLogger(__name__)


FALLBACK_ANSWERS = {
    "verified information is currently unavailable.",
}


class RagBridge:
    """Fail-closed adapter for verified Day 2 RAG services."""

    def __init__(
        self,
        service: Any = None,
    ):
        self.service = service

    def answer(
        self,
        question: str,
    ) -> str | None:
        if not isinstance(
            question,
            str,
        ) or not question.strip():
            return None

        service = self.service

        if service is None:
            return None

        result = None

        if callable(
            service
        ):
            result = service(
                question
            )

        elif callable(
            getattr(
                service,
                "answer",
                None,
            )
        ):
            result = service.answer(
                question
            )

        elif callable(
            getattr(
                service,
                "ask",
                None,
            )
        ):
            result = service.ask(
                question
            )

        if isinstance(
            result,
            Mapping,
        ):
            reason = str(
                result.get(
                    "reason",
                    "",
                )
            )

            if reason in {
                "structured_fact_requires_postgresql",
                "no_relevant_context",
                "llm_provider_error",
            }:
                return None

            result = result.get(
                "answer"
            )

        if not isinstance(
            result,
            str,
        ):
            return None

        result = result.strip()

        if not result:
            return None

        if (
            result.casefold()
            in FALLBACK_ANSWERS
        ):
            return None

        return result

    def status(
        self,
    ) -> dict[str, Any]:
        if self.service is None:
            return {
                "enabled": False,
                "ready": False,
            }

        status_method = getattr(
            self.service,
            "status",
            None,
        )

        if not callable(
            status_method
        ):
            return {
                "enabled": True,
                "ready": True,
            }

        try:
            details = status_method()
        except Exception as exc:
            logger.exception(
                "RAG status lookup failed"
            )
            return {
                "enabled": True,
                "ready": False,
                "status_error_type": (
                    exc.__class__.__name__
                ),
            }

        if not isinstance(
            details,
            dict,
        ):
            details = {}

        return {
            "enabled": True,
            **details,
        }


def build_default_rag_bridge(
) -> RagBridge:
    enabled = os.getenv(
        "SARA_RAG_ENABLED",
        "1",
    ).strip().casefold()

    if enabled in {
        "0",
        "false",
        "no",
        "off",
    }:
        return RagBridge()

    required = os.getenv(
        "SARA_RAG_REQUIRED",
        "0",
    ).strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }

    try:
        from .day2_rag_service import (
            Day2RAGService,
        )

        service = Day2RAGService()

        warm_on_startup = os.getenv(
            "SARA_RAG_WARM_ON_STARTUP",
            "0",
        ).strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if required or warm_on_startup:
            service.warmup()

        return RagBridge(
            service
        )

    except Exception:
        logger.exception(
            "Day 2 RAG configuration failed"
        )

        if required:
            raise

        return RagBridge()
