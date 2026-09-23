"""DTO models for stable X-RAY UI contracts.

All data flowing between core and control plane
MUST go through these DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpanNodeDTO:
    """A span in the execution tree."""
    span_id: str
    kind: str
    name: str
    status: str
    started_at: float
    ended_at: float | None = None
    duration_ms: float | None = None
    parent_span_id: str | None = None
    logical_ts: int = 0
    depth: int = 0
    late: bool = False
    children: list[SpanNodeDTO] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "kind": self.kind,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "parent_span_id": self.parent_span_id,
            "logical_ts": self.logical_ts,
            "depth": self.depth,
            "late": self.late,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class TraceSummaryDTO:
    """Summary of a trace for list views."""
    trace_id: str
    name: str
    status: str
    started_at: float
    ended_at: float | None = None
    duration_ms: float | None = None
    freeze: bool = False
    span_count: int = 0
    depth: int = 0
    has_errors: bool = False
    has_fallback: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "freeze": self.freeze,
            "span_count": self.span_count,
            "depth": self.depth,
            "has_errors": self.has_errors,
            "has_fallback": self.has_fallback,
            "metadata": self.metadata,
        }


@dataclass
class TraceDetailDTO:
    """Full trace detail with tree and timeline."""
    trace_id: str
    name: str
    status: str
    started_at: float
    ended_at: float | None = None
    duration_ms: float | None = None
    freeze: bool = False
    span_count: int = 0
    tree: list[SpanNodeDTO] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "freeze": self.freeze,
            "span_count": self.span_count,
            "tree": [n.to_dict() for n in self.tree],
            "metadata": self.metadata,
        }


@dataclass
class ReplayFrameDTO:
    """A single frame in a trace replay timeline."""
    span_id: str
    kind: str
    name: str
    started_at: float
    status: str
    duration_ms: float | None = None
    parent_span_id: str | None = None
    logical_ts: int = 0
    depth: int = 0
    late: bool = False

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "kind": self.kind,
            "name": self.name,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "parent_span_id": self.parent_span_id,
            "logical_ts": self.logical_ts,
            "depth": self.depth,
            "late": self.late,
        }


@dataclass
class AuditCheckDTO:
    """Result of a single consistency audit check."""
    name: str
    passed: bool
    skipped: bool = False
    detail: str = ""
    status: str = "passed"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "skipped": self.skipped,
            "detail": self.detail,
            "status": self.status,
        }


@dataclass
class AuditResultDTO:
    """Aggregate audit result for a trace."""
    trace_id: str | None = None
    all_passed: bool = False
    checks: list[AuditCheckDTO] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "all_passed": self.all_passed,
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class HealthMetricsDTO:
    """System health dashboard metrics."""
    active_traces: int = 0
    completed_traces: int = 0
    interrupted_traces: int = 0
    orphan_spans: int = 0
    causal_violations: int = 0
    average_latency_ms: float = 0.0
    fallback_count: int = 0
    trace_integrity: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "active_traces": self.active_traces,
            "completed_traces": self.completed_traces,
            "interrupted_traces": self.interrupted_traces,
            "orphan_spans": self.orphan_spans,
            "causal_violations": self.causal_violations,
            "average_latency_ms": self.average_latency_ms,
            "fallback_count": self.fallback_count,
            "trace_integrity": self.trace_integrity,
        }
