"""Content-free operational metrics for presentation rendering."""

from __future__ import annotations

import threading
from collections import Counter
from typing import Any


_OUTCOME_MODES = (
    "generated",
    "cached",
    "bundled",
    "deterministic_fallback",
)


class PresentationMetrics:
    """Collect process-local counters without retaining reader content."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = 0
        self._outcomes: Counter[str] = Counter()
        self._events: Counter[str] = Counter()
        self._total_latency_seconds = 0.0
        self._maximum_latency_seconds = 0.0

    def record_result(self, mode: str, elapsed_seconds: float) -> None:
        elapsed = max(0.0, float(elapsed_seconds))
        with self._lock:
            self._requests += 1
            self._outcomes[str(mode)] += 1
            self._total_latency_seconds += elapsed
            self._maximum_latency_seconds = max(
                self._maximum_latency_seconds,
                elapsed,
            )

    def record_unhandled_failure(self, elapsed_seconds: float) -> None:
        elapsed = max(0.0, float(elapsed_seconds))
        with self._lock:
            self._requests += 1
            self._events["unhandled_failures"] += 1
            self._total_latency_seconds += elapsed
            self._maximum_latency_seconds = max(
                self._maximum_latency_seconds,
                elapsed,
            )

    def record_event(self, name: str) -> None:
        with self._lock:
            self._events[name] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            requests = self._requests
            average_latency = (
                self._total_latency_seconds / requests if requests else 0.0
            )
            return {
                "requests_total": requests,
                "outcomes": {
                    mode: self._outcomes[mode]
                    for mode in _OUTCOME_MODES
                },
                "provider": {
                    "attempts": self._events["provider_attempts"],
                    "failures": self._events["provider_failures"],
                    "parse_failures": self._events["provider_parse_failures"],
                    "rejections": self._events["provider_rejections"],
                    "saturated": self._events["provider_saturation"],
                },
                "cache": {
                    "read_failures": self._events["cache_read_failures"],
                    "write_failures": self._events["cache_write_failures"],
                    "discard_failures": self._events["cache_discard_failures"],
                },
                "bundles": {
                    "grounding_rejections": self._events["bundle_rejections"],
                },
                "unhandled_failures": self._events["unhandled_failures"],
                "latency_ms": {
                    "average": round(average_latency * 1000, 3),
                    "maximum": round(self._maximum_latency_seconds * 1000, 3),
                },
            }
