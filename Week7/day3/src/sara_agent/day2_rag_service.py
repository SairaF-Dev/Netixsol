from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
import sys
import threading
from typing import Any, Callable, Mapping


logger = logging.getLogger(__name__)

FALLBACK_ANSWER = (
    "Verified information is currently unavailable."
)


class Day2RAGService:
    """
    Lazy adapter around the actual Day 2 RAGPipeline.

    DAY2_ROOT remains the single integration boundary. This service does
    not copy or re-implement the Day 2 retriever/vector store.

    The heavy embedding/Chroma stack is initialized only when a semantic
    question actually reaches RAG. One service can therefore be safely
    shared across many Sara conversation sessions.
    """

    def __init__(
        self,
        day2_root: str | Path | None = None,
        *,
        pipeline_factory: Callable[..., Any] | None = None,
    ):
        self.day2_root = self._resolve_root(
            day2_root
        )
        self.rag_dir = (
            self.day2_root
            / "02_rag"
        )

        self.documents_dir = self._resolve_path(
            "SARA_RAG_DOCUMENTS_DIR",
            self.rag_dir / "documents",
        )
        self.persist_directory = self._resolve_path(
            "SARA_RAG_PERSIST_DIRECTORY",
            self.rag_dir / "chroma_db",
        )

        self.pipeline_factory = pipeline_factory

        self._pipeline = None
        self._load_error: Exception | None = None
        self._lock = threading.RLock()

    def answer(
        self,
        question: str,
    ) -> str | None:
        if not isinstance(
            question,
            str,
        ):
            return None

        question = question.strip()

        if not question:
            return None

        pipeline = self._get_pipeline()

        result = pipeline.answer(
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
            ).strip()

            if reason in {
                "structured_fact_requires_postgresql",
                "no_relevant_context",
                "llm_provider_error",
            }:
                return None

            answer = result.get(
                "answer"
            )

        else:
            answer = result

        if not isinstance(
            answer,
            str,
        ):
            return None

        answer = answer.strip()

        if not answer:
            return None

        if (
            answer.casefold()
            == FALLBACK_ANSWER.casefold()
        ):
            return None

        return answer

    def warmup(
        self,
    ) -> dict[str, Any]:
        """Initialize embeddings/vector store now instead of on first query."""

        self._get_pipeline()
        return self.status()

    def status(
        self,
    ) -> dict[str, Any]:
        return {
            "configured": True,
            "rag_dir_exists": self.rag_dir.exists(),
            "documents_exist": self.documents_dir.exists(),
            "initialized": self._pipeline is not None,
            "ready": (
                self.rag_dir.exists()
                and self.documents_dir.exists()
                and self._load_error is None
            ),
            "load_error_type": (
                self._load_error.__class__.__name__
                if self._load_error is not None
                else None
            ),
        }

    def _get_pipeline(
        self,
    ):
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is not None:
                return self._pipeline

            try:
                factory = (
                    self.pipeline_factory
                    or self._load_pipeline_class()
                )

                kwargs: dict[str, Any] = {
                    "documents_dir": str(
                        self.documents_dir
                    ),
                    "persist_directory": str(
                        self.persist_directory
                    ),
                }

                chunk_size = self._optional_int(
                    "SARA_RAG_CHUNK_SIZE"
                )

                top_k = self._optional_int(
                    "SARA_RAG_TOP_K"
                )

                distance = self._optional_float(
                    "SARA_RAG_DISTANCE_THRESHOLD"
                )

                if chunk_size is not None:
                    kwargs["chunk_size"] = chunk_size

                if top_k is not None:
                    kwargs["top_k"] = top_k

                if distance is not None:
                    kwargs[
                        "distance_threshold"
                    ] = distance

                self.persist_directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                self._pipeline = factory(
                    **kwargs
                )
                self._load_error = None

                return self._pipeline

            except Exception as exc:
                self._load_error = exc
                logger.exception(
                    "Day 2 RAG initialization failed"
                )
                raise

    def _load_pipeline_class(
        self,
    ):
        path = (
            self.rag_dir
            / "rag_pipeline.py"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Day 2 RAG pipeline not found: {path}"
            )

        if not self.documents_dir.exists():
            raise FileNotFoundError(
                "Day 2 RAG documents directory "
                f"not found: {self.documents_dir}"
            )

        # Day 2's RAG modules intentionally use simple sibling imports
        # such as `from retriever import Retriever`. Put only the verified
        # Day 2 RAG folder at the front of sys.path before loading it.
        rag_dir_text = str(
            self.rag_dir
        )

        if rag_dir_text not in sys.path:
            sys.path.insert(
                0,
                rag_dir_text,
            )

        spec = importlib.util.spec_from_file_location(
            "sara_day2_rag_pipeline",
            path,
        )

        if (
            spec is None
            or spec.loader is None
        ):
            raise ImportError(
                "Cannot load Day 2 RAGPipeline"
            )

        module = (
            importlib.util
            .module_from_spec(
                spec
            )
        )

        spec.loader.exec_module(
            module
        )

        pipeline_class = getattr(
            module,
            "RAGPipeline",
            None,
        )

        if pipeline_class is None:
            raise ImportError(
                "Day 2 rag_pipeline.py does not "
                "expose RAGPipeline"
            )

        return pipeline_class

    def _resolve_root(
        self,
        explicit: str | Path | None,
    ) -> Path:
        raw = (
            str(explicit)
            if explicit is not None
            else os.getenv(
                "DAY2_ROOT",
                "",
            )
        ).strip()

        if not raw:
            raise ValueError(
                "DAY2_ROOT is not configured"
            )

        path = (
            Path(raw)
            .expanduser()
            .resolve()
        )

        if not path.exists():
            raise FileNotFoundError(
                f"DAY2_ROOT not found: {path}"
            )

        return path

    def _resolve_path(
        self,
        env_name: str,
        default: Path,
    ) -> Path:
        raw = os.getenv(
            env_name,
            "",
        ).strip()

        if not raw:
            return default.resolve()

        path = (
            Path(raw)
            .expanduser()
        )

        if not path.is_absolute():
            path = (
                self.rag_dir
                / path
            )

        return path.resolve()

    def _optional_int(
        self,
        name: str,
    ) -> int | None:
        raw = os.getenv(
            name
        )

        if raw is None or not raw.strip():
            return None

        value = int(
            raw
        )

        if value <= 0:
            raise ValueError(
                f"{name} must be greater than 0"
            )

        return value

    def _optional_float(
        self,
        name: str,
    ) -> float | None:
        raw = os.getenv(
            name
        )

        if raw is None or not raw.strip():
            return None

        value = float(
            raw
        )

        if value < 0:
            raise ValueError(
                f"{name} cannot be negative"
            )

        return value
