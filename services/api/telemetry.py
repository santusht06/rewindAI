"""Operational Telemetry & Performance Instrumentation for Rewind.

Implements:
- OPS-001: Structured operational events with privacy-safe payloads
- OPS-004: Latency percentiles (p50, p95, p99), failure rates, and token/cost accounting
- NFR-PERF-001, NFR-COST-001: Observable system health without leaking user text or secrets
"""

import math
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class TelemetrySnapshot:
    """Read-only operational metrics snapshot."""
    timestamp: str
    total_requests: int
    outcomes: dict[str, int]
    latencies_p50_ms: dict[str, float]
    latencies_p95_ms: dict[str, float]
    latencies_p99_ms: dict[str, float]
    token_usage: dict[str, int]
    estimated_cost_usd: float


class TelemetryRegistry:
    """Thread-safe, privacy-preserving in-memory operational metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_requests = 0
        self._outcomes: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, list[float]] = defaultdict(list)
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._estimated_cost_usd = 0.0

    def record_request(self) -> None:
        with self._lock:
            self._total_requests += 1

    def record_outcome(self, outcome: str) -> None:
        with self._lock:
            self._outcomes[outcome] += 1

    def record_latency(self, operation: str, duration_ms: float) -> None:
        with self._lock:
            # Bound history size to prevent unbounded memory growth
            history = self._latencies[operation]
            if len(history) > 5000:
                history.pop(0)
            history.append(duration_ms)

    def record_token_usage(self, prompt_tokens: int, completion_tokens: int, cost_usd: float = 0.0) -> None:
        with self._lock:
            self._prompt_tokens += prompt_tokens
            self._completion_tokens += completion_tokens
            self._estimated_cost_usd += cost_usd

    def _calculate_percentile(self, values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(sorted_vals[int(k)], 2)
        d0 = sorted_vals[int(f)] * (c - k)
        d1 = sorted_vals[int(c)] * (k - f)
        return round(d0 + d1, 2)

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            p50 = {}
            p95 = {}
            p99 = {}
            for op, vals in self._latencies.items():
                p50[op] = self._calculate_percentile(vals, 50.0)
                p95[op] = self._calculate_percentile(vals, 95.0)
                p99[op] = self._calculate_percentile(vals, 99.0)

            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "total_requests": self._total_requests,
                "outcomes": dict(self._outcomes),
                "latencies_ms": {
                    "p50": p50,
                    "p95": p95,
                    "p99": p99,
                },
                "tokens": {
                    "prompt_tokens": self._prompt_tokens,
                    "completion_tokens": self._completion_tokens,
                    "total_tokens": self._prompt_tokens + self._completion_tokens,
                },
                "estimated_cost_usd": round(self._estimated_cost_usd, 6),
            }

    def reset(self) -> None:
        with self._lock:
            self._total_requests = 0
            self._outcomes.clear()
            self._latencies.clear()
            self._prompt_tokens = 0
            self._completion_tokens = 0
            self._estimated_cost_usd = 0.0


# Global singleton instance
telemetry = TelemetryRegistry()
