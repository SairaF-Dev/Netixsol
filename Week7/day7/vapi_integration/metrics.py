"""Small in-process metrics registry for operational visibility."""

from __future__ import annotations

import threading
from collections import Counter, defaultdict


class MetricsRegistry:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[name] += amount

    def observe_ms(self, name: str, value: float) -> None:
        with self._lock:
            values = self._latencies[name]
            values.append(float(value))
            if len(values) > 2000:
                del values[: len(values) - 2000]

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile))
        return round(ordered[index], 2)

    def snapshot(self) -> dict:
        with self._lock:
            counts = dict(self._counts)
            latencies = {
                name: {
                    "count": len(values),
                    "average_ms": round(sum(values) / len(values), 2) if values else 0.0,
                    "p50_ms": self._percentile(values, 0.50),
                    "p95_ms": self._percentile(values, 0.95),
                    "p99_ms": self._percentile(values, 0.99),
                }
                for name, values in self._latencies.items()
            }
        return {"counters": counts, "latencies": latencies}


metrics = MetricsRegistry()
