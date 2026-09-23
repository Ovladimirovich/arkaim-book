"""Normalizer — converts internal X-RAY state to stable DTOs.

Decouples the control plane from internal data structures.
All UI-facing endpoints MUST use this normalizer.
"""

from __future__ import annotations

from aethon.xray.control_plane.dto import (
    AuditCheckDTO,
    AuditResultDTO,
    HealthMetricsDTO,
    ReplayFrameDTO,
    SpanNodeDTO,
    TraceDetailDTO,
    TraceSummaryDTO,
)
from aethon.xray.span import Span
from aethon.xray.trace import Trace


def trace_to_summary(trace: Trace) -> TraceSummaryDTO:
    """Convert a Trace to a stable summary DTO."""
    has_errors = any(s.status == "error" for s in trace.spans)
    has_fallback = any(s.kind == "fallback" for s in trace.spans)
    depth = _compute_depth(trace)
    return TraceSummaryDTO(
        trace_id=trace.trace_id,
        name=trace.name,
        status=trace.status,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_ms=trace.duration_ms,
        freeze=trace.freeze,
        span_count=len(trace.spans),
        depth=depth,
        has_errors=has_errors,
        has_fallback=has_fallback,
        metadata=trace.metadata,
    )


def _compute_depth(trace: Trace) -> int:
    """Compute max nesting depth from parent-child chain."""
    if not trace.spans:
        return 0
    parent_map = {}
    for s in trace.spans:
        parent_map[s.span_id] = s.parent_span_id
    max_depth = 0
    for sid in parent_map:
        depth = 0
        cur = sid
        while cur in parent_map and parent_map[cur]:
            depth += 1
            cur = parent_map[cur]
            if depth > 100:
                break
        max_depth = max(max_depth, depth)
    return max_depth


def _span_to_node(span: Span, children: list[SpanNodeDTO]) -> SpanNodeDTO:
    """Convert a Span and its children to a tree node DTO."""
    return SpanNodeDTO(
        span_id=span.span_id,
        kind=span.kind,
        name=span.name,
        status=span.status,
        started_at=span.started_at,
        ended_at=span.ended_at,
        duration_ms=span.duration_ms,
        parent_span_id=span.parent_span_id,
        logical_ts=span.logical_ts,
        depth=span.depth,
        late=span.late,
        children=children,
    )


def trace_to_detail(trace: Trace, tree_nodes: list, metadata: dict | None = None) -> TraceDetailDTO:
    """Convert a Trace + raw tree nodes to a detail DTO."""
    dto_nodes = [_build_node_dto(n) for n in tree_nodes]
    return TraceDetailDTO(
        trace_id=trace.trace_id,
        name=trace.name,
        status=trace.status,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_ms=trace.duration_ms,
        freeze=trace.freeze,
        span_count=len(trace.spans),
        tree=dto_nodes,
        metadata=metadata or trace.metadata,
    )


def _build_node_dto(raw: dict) -> SpanNodeDTO:
    """Recursively build a SpanNodeDTO from a raw tree dict."""
    return SpanNodeDTO(
        span_id=raw.get("span_id", ""),
        kind=raw.get("kind", ""),
        name=raw.get("name", ""),
        status=raw.get("status", "ok"),
        started_at=raw.get("started_at", 0.0),
        ended_at=raw.get("ended_at"),
        duration_ms=raw.get("duration_ms"),
        parent_span_id=raw.get("parent_span_id"),
        logical_ts=raw.get("logical_ts", 0),
        depth=raw.get("depth", 0),
        late=raw.get("late", False),
        children=[_build_node_dto(c) for c in raw.get("children", [])],
    )


def span_to_replay_frame(span: Span) -> ReplayFrameDTO:
    """Convert a Span to a replay frame DTO."""
    return ReplayFrameDTO(
        span_id=span.span_id,
        kind=span.kind,
        name=span.name,
        started_at=span.started_at,
        duration_ms=span.duration_ms,
        status=span.status,
        parent_span_id=span.parent_span_id,
        logical_ts=span.logical_ts,
        depth=span.depth,
        late=span.late,
    )


def replay_entry_to_frame(entry: dict) -> ReplayFrameDTO:
    """Convert a raw replay timeline entry dict to a DTO."""
    return ReplayFrameDTO(
        span_id=entry.get("span_id", ""),
        kind=entry.get("kind", ""),
        name=entry.get("name", ""),
        started_at=entry.get("started_at", 0.0),
        duration_ms=entry.get("duration_ms"),
        status=entry.get("status", "?"),
        parent_span_id=entry.get("parent_span_id"),
        logical_ts=entry.get("logical_ts", 0),
        depth=entry.get("depth", 0),
        late=entry.get("late", False),
    )


def audit_checks_to_result(
    trace_id: str | None,
    all_passed: bool,
    checks: dict[str, dict],
) -> AuditResultDTO:
    """Convert raw audit check dicts to an AuditResultDTO."""
    check_dtos = []
    for name, ck in checks.items():
        check_dtos.append(AuditCheckDTO(
            name=name,
            passed=ck.get("passed", False),
            skipped=ck.get("skipped", False),
            detail=ck.get("reason", "") or ck.get("detail", ""),
            status=ck.get("status", "passed" if ck.get("passed") else "failed"),
        ))
    return AuditResultDTO(
        trace_id=trace_id,
        all_passed=all_passed,
        checks=check_dtos,
    )


def raw_stats_to_health_metrics(stats: dict, diag: dict) -> HealthMetricsDTO:
    """Convert raw stats + diagnostics dicts to a HealthMetricsDTO."""
    return HealthMetricsDTO(
        active_traces=stats.get("active_traces", diag.get("active_traces", 0)),
        completed_traces=stats.get("completed_traces", diag.get("completed_traces", 0)),
        interrupted_traces=stats.get("interrupted_traces", diag.get("failed_traces", 0)),
        orphan_spans=stats.get("orphan_spans", diag.get("orphan_spans", 0)),
        causal_violations=diag.get("causal_violations", 0),
        average_latency_ms=diag.get("average_latency_ms", 0.0),
        fallback_count=diag.get("fallback_count", 0),
        trace_integrity=diag.get("trace_integrity", "unknown"),
    )
