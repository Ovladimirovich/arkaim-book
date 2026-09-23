"""Execution spans — atomic units of work within a trace."""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aethon.xray.contracts import SpanSchema

_current_span: ContextVar["Span | None"] = ContextVar("_current_span", default=None)


def _generate_id() -> str:
    return uuid.uuid4().hex[:12]


class SpanKind(str, Enum):
    PROVIDER_CALL = "provider_call"
    MEMORY_ACCESS = "memory_access"
    GATEWAY_REQUEST = "gateway_request"
    TELEGRAM_UPDATE = "telegram_update"
    SKILL_EXECUTION = "skill_execution"
    CORE_ORCHESTRATE = "core_orchestrate"
    DIAGNOSTIC = "diagnostic"
    CUSTOM = "custom"


@dataclass
class Span:
    """A named, timed unit of work within a trace."""
    span_id: str
    trace_id: str
    kind: str
    name: str
    started_at: float
    correlation_id: str = ""
    ended_at: float | None = None
    duration_ms: float | None = None
    status: str = "ok"
    parent_span_id: str | None = None
    logical_ts: int = 0
    depth: int = 0
    late: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def end(self, status: str = "ok"):
        if self.ended_at is not None:
            # Double close — update status only
            self.status = status
            return self
        self.ended_at = time.time()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.status = status
        _current_span.set(None)
        from aethon.xray.trace_store import store
        store.register_span(self)
        return self

    def set_metadata(self, key: str, value: Any):
        self.metadata[key] = value

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "kind": self.kind,
            "name": self.name,
            "started_at": self.started_at,
            "correlation_id": self.correlation_id,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "parent_span_id": self.parent_span_id,
            "logical_ts": self.logical_ts,
            "depth": self.depth,
            "late": self.late,
            "metadata": self.metadata,
        }

    def to_schema(self) -> SpanSchema:
        return SpanSchema(
            span_id=self.span_id,
            trace_id=self.trace_id,
            kind=self.kind,
            name=self.name,
            started_at=self.started_at,
            ended_at=self.ended_at,
            duration_ms=self.duration_ms,
            status=self.status,
            parent_span_id=self.parent_span_id,
            metadata=self.metadata,
        )

    @classmethod
    def from_dict(cls, data: dict) -> Span:
        return cls(
            span_id=data["span_id"],
            trace_id=data["trace_id"],
            kind=data.get("kind", ""),
            name=data.get("name", ""),
            started_at=data["started_at"],
            correlation_id=data.get("correlation_id", ""),
            ended_at=data.get("ended_at"),
            duration_ms=data.get("duration_ms"),
            status=data.get("status", "ok"),
            parent_span_id=data.get("parent_span_id"),
            logical_ts=data.get("logical_ts", 0),
            depth=data.get("depth", 0),
            late=data.get("late", False),
            metadata=data.get("metadata", {}),
        )


def get_current_span() -> Span | None:
    return _current_span.get()


def start_span(
    kind: SpanKind | str,
    name: str,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    correlation_id: str = "",
    metadata: dict | None = None,
) -> Span:
    from aethon.xray.trace import get_current_trace_id, _current_trace

    tid = trace_id or get_current_trace_id()
    parent = get_current_span()
    # Determine logical_ts and depth from parent or trace counter
    logical_ts = 0
    depth = 0
    current_trace = _current_trace.get()
    if current_trace and current_trace.trace_id == tid:
        logical_ts = current_trace._next_logical_ts()
        depth = (parent.depth + 1) if parent else 0
    # Check if trace is frozen — mark as late
    late = False
    if current_trace and current_trace.trace_id == tid and current_trace.freeze:
        late = True
    elif tid:
        # Trace may be frozen but not in current context (cross-process or after end())
        from aethon.xray.trace_store import store as _store
        stored_trace = _store.get_trace(tid)
        if stored_trace and stored_trace.freeze:
            late = True
    span = Span(
        span_id=_generate_id(),
        trace_id=tid,
        kind=kind.value if isinstance(kind, SpanKind) else kind,
        name=name,
        started_at=time.time(),
        correlation_id=correlation_id,
        parent_span_id=parent_span_id or (parent.span_id if parent else None),
        logical_ts=logical_ts,
        depth=depth,
        late=late,
        metadata=metadata or {},
    )
    _current_span.set(span)
    # Register with trace immediately so un-ended spans are tracked
    from aethon.xray.trace_store import store
    store.register_span(span)
    return span
