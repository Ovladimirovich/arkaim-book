"""Trace lifecycle — global execution flow tracking."""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from aethon.xray.contracts import TraceSchema
from aethon.xray.span import Span

_current_trace_id: ContextVar[str] = ContextVar("_current_trace_id", default="")
_current_trace: ContextVar["Trace | None"] = ContextVar("_current_trace", default=None)


def get_current_trace_id() -> str:
    return _current_trace_id.get()


def set_current_trace_id(trace_id: str):
    _current_trace_id.set(trace_id)


def _generate_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass
class Trace:
    """Represents a complete execution trace through the system."""
    trace_id: str
    name: str
    started_at: float
    correlation_id: str = ""
    ended_at: float | None = None
    duration_ms: float | None = None
    status: str = "ok"
    spans: list[Span] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    freeze: bool = False
    finalize_ts: float | None = None
    _logical_ts_counter: int = 0

    def _next_logical_ts(self) -> int:
        self._logical_ts_counter += 1
        return self._logical_ts_counter

    def end(self, status: str = "ok"):
        if self.ended_at is not None:
            self.status = status
            return self
        self.freeze = True
        self.finalize_ts = time.time()
        self.ended_at = self.finalize_ts
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.status = status
        # Close all registered spans
        for span in self.spans:
            if span.ended_at is None:
                span.end()
        # Claim and close any orphan spans that belong to this trace
        from aethon.xray.trace_store import store
        orphan_claims = store.claim_orphan_spans(self.trace_id)
        for span in orphan_claims:
            if span.ended_at is None:
                span.end(status)
            self.spans.append(span)
        # Move to completed in store (without calling end() again)
        store.finalize_trace(self.trace_id)
        _current_trace.set(None)
        _current_trace_id.set("")
        return self

    def add_span(self, span: Span):
        self.spans.append(span)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "started_at": self.started_at,
            "correlation_id": self.correlation_id,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "freeze": self.freeze,
            "finalize_ts": self.finalize_ts,
            "spans": [s.to_dict() for s in self.spans],
            "metadata": self.metadata,
        }

    def to_schema(self) -> TraceSchema:
        return TraceSchema(
            trace_id=self.trace_id,
            name=self.name,
            started_at=self.started_at,
            ended_at=self.ended_at,
            duration_ms=self.duration_ms,
            status=self.status,
            spans=[s.to_schema() for s in self.spans],
            metadata=self.metadata,
        )


def start_trace(name: str, trace_id: str | None = None, correlation_id: str = "", metadata: dict | None = None) -> Trace:
    from aethon.xray.trace_store import store
    tid = trace_id or _generate_id()
    trace = Trace(
        trace_id=tid,
        name=name,
        started_at=time.time(),
        correlation_id=correlation_id,
        metadata=metadata or {},
    )
    _current_trace.set(trace)
    _current_trace_id.set(tid)
    store.register_trace(trace)
    return trace
