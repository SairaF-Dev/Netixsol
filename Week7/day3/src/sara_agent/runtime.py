from __future__ import annotations

from typing import Any

from .chatbot import SaraChatbot
from .day2_adapter import Day2Adapter
from .rag_bridge import (
    RagBridge,
    build_default_rag_bridge,
)


class SaraRuntime:
    """
    Shared runtime dependencies.

    Day 2 PostgreSQL adapter and RAG service are safe to share.
    Every new_bot() call still gets an independent ConversationState.
    """

    def __init__(
        self,
        knowledge: Any = None,
        rag_bridge: RagBridge | None = None,
    ):
        self.knowledge = (
            knowledge
            or Day2Adapter()
        )

        self.rag_bridge = (
            rag_bridge
            or build_default_rag_bridge()
        )

    def new_bot(
        self,
        response_mode: str | None = None,
    ) -> SaraChatbot:
        return SaraChatbot(
            self.knowledge,
            response_mode=response_mode,
            rag_bridge=self.rag_bridge,
        )

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "rag": self.rag_bridge.status(),
        }

    def readiness(
        self,
    ) -> dict[str, Any]:
        database_ready = False
        database_error_type = None

        checker = getattr(
            self.knowledge,
            "check_database",
            None,
        )

        try:
            if callable(checker):
                database_ready = bool(
                    checker()
                )
        except Exception as exc:
            database_error_type = (
                exc.__class__.__name__
            )

        return {
            "database": {
                "ready": database_ready,
                "error_type": database_error_type,
            },
            "rag": self.rag_bridge.status(),
        }
