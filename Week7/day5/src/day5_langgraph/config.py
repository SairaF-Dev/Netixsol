"""Configuration for Day 5 LangGraph agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AgentConfig:
    """Agent configuration from environment variables."""

    # LLM
    openai_api_key: str
    openai_model: str = "gpt-4-turbo"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 30.0

    # Day 4 API
    day4_api_url: str = "http://localhost:8004"
    day4_api_key: str | None = None
    day4_timeout_seconds: float = 10.0

    # RAG
    rag_enabled: bool = True
    chroma_db_path: str = "../day2/chroma_db"
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Memory
    memory_type: Literal["in_memory", "redis"] = "in_memory"
    redis_url: str | None = None
    memory_ttl_seconds: int = 3600

    # Database
    database_url: str = "sqlite:///./day5.db"

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/agent.log"
    log_to_console: bool = True

    # Agent
    agent_name: str = "Sara"
    agent_language: str = "urdu_english"
    agent_personality: str = "warm_professional"

    # Webhooks
    n8n_webhook_url: str | None = None
    slack_webhook_url: str | None = None

    # Features
    enable_conversation_logging: bool = True
    enable_voice_interrupts: bool = True
    enable_objection_handling: bool = True
    enable_analytics: bool = False

    @classmethod
    def from_env(cls) -> AgentConfig:
        """Load configuration from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
            llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
            day4_api_url=os.getenv("DAY4_API_URL", "http://localhost:8004"),
            day4_api_key=os.getenv("DAY4_API_KEY"),
            day4_timeout_seconds=float(os.getenv("DAY4_TIMEOUT_SECONDS", "10")),
            rag_enabled=os.getenv("RAG_ENABLED", "true").lower() == "true",
            chroma_db_path=os.getenv("CHROMA_DB_PATH", "../day2/chroma_db"),
            embeddings_model=os.getenv(
                "EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            memory_type=os.getenv("MEMORY_TYPE", "in_memory"),  # type: ignore
            redis_url=os.getenv("REDIS_URL"),
            memory_ttl_seconds=int(os.getenv("MEMORY_TTL_SECONDS", "3600")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./day5.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "./logs/agent.log"),
            log_to_console=os.getenv("LOG_TO_CONSOLE", "true").lower() == "true",
            agent_name=os.getenv("AGENT_NAME", "Sara"),
            agent_language=os.getenv("AGENT_LANGUAGE", "urdu_english"),
            agent_personality=os.getenv("AGENT_PERSONALITY", "warm_professional"),
            n8n_webhook_url=os.getenv("N8N_WEBHOOK_URL"),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            enable_conversation_logging=os.getenv("ENABLE_CONVERSATION_LOGGING", "true").lower()
            == "true",
            enable_voice_interrupts=os.getenv("ENABLE_VOICE_INTERRUPTS", "true").lower()
            == "true",
            enable_objection_handling=os.getenv("ENABLE_OBJECTION_HANDLING", "true").lower()
            == "true",
            enable_analytics=os.getenv("ENABLE_ANALYTICS", "false").lower() == "true",
        )
