"""Runtime counters — provider failures, latency, fallbacks, request totals."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from aethon.xray.contracts import MetricSchema


@dataclass
class Counter:
    """Monotonically increasing counter."""
    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def inc(self, amount: float = 1.0):
        self.value += amount

    def reset(self):
        self.value = 0.0

    def snapshot(self) -> MetricSchema:
        return MetricSchema(
            name=self.name,
            value=self.value,
            timestamp=time.time(),
            labels=self.labels,
            unit=self.unit,
        )


@dataclass
class Gauge:
    """Point-in-time measurement (goes up and down)."""
    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def set(self, value: float):
        self.value = value

    def snapshot(self) -> MetricSchema:
        return MetricSchema(
            name=self.name,
            value=self.value,
            timestamp=time.time(),
            labels=self.labels,
            unit=self.unit,
        )


@dataclass
class Histogram:
    """Distribution of values over time."""
    name: str
    buckets: list[float] = field(default_factory=lambda: [10, 50, 100, 500, 1000, 5000, 30000])
    counts: list[int] = field(default_factory=list)
    total: float = 0.0
    count: int = 0
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = "ms"

    def __post_init__(self):
        if not self.counts:
            self.counts = [0] * len(self.buckets)

    def observe(self, value: float):
        self.total += value
        self.count += 1
        for i, bucket in enumerate(self.buckets):
            if value <= bucket:
                self.counts[i] += 1
                break

    def snapshot(self) -> dict:
        avg = self.total / self.count if self.count > 0 else 0.0
        return {
            "name": self.name,
            "avg": avg,
            "count": self.count,
            "total": self.total,
            "buckets": list(zip(self.buckets, self.counts)),
            "labels": self.labels,
            "unit": self.unit,
            "timestamp": time.time(),
        }


# ── Well-known metrics ──────────────────────────────────

provider_failures = Counter(
    name="provider_failures",
    unit="failures",
    labels={"component": "provider"},
)

provider_latency = Histogram(
    name="provider_latency",
    unit="ms",
    labels={"component": "provider"},
)

fallback_count = Counter(
    name="fallback_count",
    unit="fallbacks",
    labels={"component": "provider"},
)

requests_total = Counter(
    name="requests_total",
    unit="requests",
    labels={"component": "gateway"},
)

requests_failed = Counter(
    name="requests_failed",
    unit="requests",
    labels={"component": "gateway"},
)


def snapshot_all() -> list[MetricSchema | dict]:
    return [
        provider_failures.snapshot(),
        fallback_count.snapshot(),
        requests_total.snapshot(),
        requests_failed.snapshot(),
        provider_latency.snapshot(),
    ]
