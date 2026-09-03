"""Latency measurement and SLA tracking for Sara voice agent."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


logger = logging.getLogger(__name__)


class LatencyTracker:
    """Simple context manager for tracking latency of operations."""
    
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def track(self, name):
        """Context manager to track operation latency."""
        start = time.perf_counter()
        try:
            yield
        finally:
            self.metrics[name] = round((time.perf_counter() - start) * 1000, 2)
    
    def total_ms(self):
        """Get total time across all tracked operations."""
        return round(sum(self.metrics.values()), 2)
    
    def to_dict(self):
        """Export metrics as dict."""
        return {k: v for k, v in self.metrics.items()}


@dataclass
class LatencyMetrics:
    """Per-turn latency breakdown.
    
    Tracks timing for each component of the voice pipeline:
    - STT (Speech-to-Text): Deepgram
    - LLM (Language Model): OpenRouter
    - TTS (Text-to-Speech): EdgeTTS or Deepgram
    """
    
    # Timestamps
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Component timings (milliseconds)
    stt_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    tts_time_ms: float = 0.0
    total_time_ms: float = 0.0
    
    # Metadata
    turn_number: int = 0
    session_id: str = ""
    input_text: str = ""
    output_text: str = ""
    input_chars: int = 0
    output_chars: int = 0
    
    def record_stt_complete(self, elapsed_ms: float) -> None:
        """Record STT processing time."""
        self.stt_time_ms = elapsed_ms
        if self.input_text:
            self.input_chars = len(self.input_text)
    
    def record_llm_complete(self, elapsed_ms: float) -> None:
        """Record LLM processing time."""
        self.llm_time_ms = elapsed_ms
    
    def record_tts_complete(self, elapsed_ms: float) -> None:
        """Record TTS processing time."""
        self.tts_time_ms = elapsed_ms
        if self.output_text:
            self.output_chars = len(self.output_text)
    
    def finalize(self) -> None:
        """Calculate totals and log if SLA violation."""
        self.end_time = datetime.now()
        self.total_time_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        if not self.is_within_sla():
            logger.warning(
                f"SLA violation (turn {self.turn_number}): "
                f"STT={self.stt_time_ms:.0f}ms, "
                f"LLM={self.llm_time_ms:.0f}ms, "
                f"TTS={self.tts_time_ms:.0f}ms, "
                f"Total={self.total_time_ms:.0f}ms > 2000ms"
            )
    
    def is_within_sla(self) -> bool:
        """Check if total latency within 2-second SLA."""
        return self.total_time_ms < 2000
    
    def get_slowest_component(self) -> str:
        """Return name of slowest component."""
        times = {
            "stt": self.stt_time_ms,
            "llm": self.llm_time_ms,
            "tts": self.tts_time_ms,
        }
        return max(times, key=times.get)
    
    def to_dict(self) -> dict:
        """Export as JSON-serializable dict."""
        return {
            "turn": self.turn_number,
            "session_id": self.session_id,
            "stt_ms": round(self.stt_time_ms, 1),
            "llm_ms": round(self.llm_time_ms, 1),
            "tts_ms": round(self.tts_time_ms, 1),
            "total_ms": round(self.total_time_ms, 1),
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "within_sla": self.is_within_sla(),
            "slowest_component": self.get_slowest_component(),
            "timestamp": self.start_time.isoformat(),
        }


@dataclass
class LatencyStatistics:
    """Aggregate latency statistics across multiple turns."""
    
    total_turns: int = 0
    turns_metrics: list[LatencyMetrics] = field(default_factory=list)
    
    def add_turn(self, metrics: LatencyMetrics) -> None:
        """Add a turn's metrics."""
        self.turns_metrics.append(metrics)
        self.total_turns += 1
    
    @property
    def average_total_ms(self) -> float:
        """Average total latency across all turns."""
        if not self.turns_metrics:
            return 0.0
        total = sum(m.total_time_ms for m in self.turns_metrics)
        return total / len(self.turns_metrics)
    
    @property
    def average_stt_ms(self) -> float:
        """Average STT latency."""
        if not self.turns_metrics:
            return 0.0
        total = sum(m.stt_time_ms for m in self.turns_metrics)
        return total / len(self.turns_metrics)
    
    @property
    def average_llm_ms(self) -> float:
        """Average LLM latency."""
        if not self.turns_metrics:
            return 0.0
        total = sum(m.llm_time_ms for m in self.turns_metrics)
        return total / len(self.turns_metrics)
    
    @property
    def average_tts_ms(self) -> float:
        """Average TTS latency."""
        if not self.turns_metrics:
            return 0.0
        total = sum(m.tts_time_ms for m in self.turns_metrics)
        return total / len(self.turns_metrics)
    
    @property
    def min_total_ms(self) -> float:
        """Minimum total latency."""
        if not self.turns_metrics:
            return 0.0
        return min(m.total_time_ms for m in self.turns_metrics)
    
    @property
    def max_total_ms(self) -> float:
        """Maximum total latency."""
        if not self.turns_metrics:
            return 0.0
        return max(m.total_time_ms for m in self.turns_metrics)
    
    @property
    def sla_violation_count(self) -> int:
        """Number of turns exceeding SLA."""
        return sum(1 for m in self.turns_metrics if not m.is_within_sla())
    
    @property
    def sla_violation_rate(self) -> float:
        """Percentage of turns violating SLA."""
        if not self.turns_metrics:
            return 0.0
        return (self.sla_violation_count / len(self.turns_metrics)) * 100
    
    def to_dict(self) -> dict:
        """Export as JSON-serializable dict."""
        return {
            "total_turns": self.total_turns,
            "average_total_ms": round(self.average_total_ms, 1),
            "average_stt_ms": round(self.average_stt_ms, 1),
            "average_llm_ms": round(self.average_llm_ms, 1),
            "average_tts_ms": round(self.average_tts_ms, 1),
            "min_total_ms": round(self.min_total_ms, 1),
            "max_total_ms": round(self.max_total_ms, 1),
            "sla_violations": self.sla_violation_count,
            "sla_violation_rate_percent": round(self.sla_violation_rate, 1),
            "recent_turns": [m.to_dict() for m in self.turns_metrics[-10:]],
        }
