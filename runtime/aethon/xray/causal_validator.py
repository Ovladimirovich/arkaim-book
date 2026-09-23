"""Causal integrity validation for X-RAY Lite.

Read-only checks — never modifies execution state.
Validates parent-child ordering, logical clock monotonicity,
orphan grace windows, and out-of-order span detection.
"""

from __future__ import annotations

import time
from typing import Any

from aethon.xray.span import Span
from aethon.xray.trace import Trace
from aethon.xray.contracts import Severity


def detect_time_violations(trace: Trace) -> list[dict]:
    """Check wall-clock time ordering constraints.

    Returns list of violations:
      - child.start < parent.start → ERROR (impossible ordering)
      - child.end > trace.finalize_ts → WARNING (late completion)
    """
    violations = []
    span_map = {s.span_id: s for s in trace.spans}

    for s in trace.spans:
        if s.parent_span_id and s.parent_span_id in span_map:
            parent = span_map[s.parent_span_id]
            if s.started_at < parent.started_at:
                violations.append({
                    "type": "child_before_parent",
                    "severity": "error",
                    "span_id": s.span_id,
                    "name": s.name,
                    "parent_span_id": s.parent_span_id,
                    "detail": f"child.start ({s.started_at:.3f}) < parent.start ({parent.started_at:.3f})",
                })
            if s.ended_at and trace.finalize_ts and s.ended_at > trace.finalize_ts:
                violations.append({
                    "type": "span_ends_after_freeze",
                    "severity": "warning",
                    "span_id": s.span_id,
                    "name": s.name,
                    "detail": f"span.end ({s.ended_at:.3f}) > trace.finalize_ts ({trace.finalize_ts:.3f})",
                })

    return violations


def detect_parent_child_order_violations(trace: Trace) -> list[dict]:
    """Check parent-child lifecycle ordering.

    Returns list of violations:
      - parent.end < child.end → WARNING (child outlived parent)
      - child exists after frozen trace → LATE EVENT
    """
    violations = []
    span_map = {s.span_id: s for s in trace.spans}

    for s in trace.spans:
        if s.parent_span_id and s.parent_span_id in span_map:
            parent = span_map[s.parent_span_id]
            if s.ended_at and parent.ended_at and s.ended_at > parent.ended_at:
                violations.append({
                    "type": "child_outlives_parent",
                    "severity": "warning",
                    "span_id": s.span_id,
                    "name": s.name,
                    "parent_span_id": s.parent_span_id,
                    "detail": f"child.end ({s.ended_at:.3f}) > parent.end ({parent.ended_at:.3f})",
                })

        if trace.freeze and s.late:
            violations.append({
                "type": "late_span_after_freeze",
                "severity": "info",
                "span_id": s.span_id,
                "name": s.name,
                "late": True,
                "detail": "span started after trace was frozen",
            })

    return violations


def detect_orphan_over_time(traces: list[Trace], store=None) -> list[dict]:
    """Detect orphans only after grace window.

    An orphan span is considered valid only if:
      - No active trace with its trace_id exists
      - More than ORPHAN_GRACE_MS have passed since it was created
    """
    if store is None:
        from aethon.xray.trace_store import store
    grace_s = store.ORPHAN_GRACE_MS / 1000.0
    now = time.time()
    active_ids = {t.trace_id for t in traces}

    violations = []
    for s in store.get_raw_orphan_spans():
        age = now - s.started_at
        if age > grace_s:
            if s.trace_id not in active_ids:
                violations.append({
                    "type": "confirmed_orphan",
                    "severity": "error" if age > 60 else "warning",
                    "span_id": s.span_id,
                    "trace_id": s.trace_id,
                    "name": s.name,
                    "age_s": round(age, 1),
                    "grace_ms": store.ORPHAN_GRACE_MS,
                    "detail": f"orphan span {s.span_id} ({s.name}) age={age:.1f}s > grace={store.ORPHAN_GRACE_MS}ms",
                })
        # Within grace window — no violation

    return violations


def detect_out_of_order_spans(trace: Trace) -> list[dict]:
    """Check logical clock monotonicity along each parent-child path.

    logical_ts MUST increase from parent to child along any path.
    A violation means the causal order stored does not match creation order.
    """
    violations = []
    span_map = {s.span_id: s for s in trace.spans}

    for s in trace.spans:
        if s.parent_span_id and s.parent_span_id in span_map:
            parent = span_map[s.parent_span_id]
            if parent.logical_ts > 0 and s.logical_ts > 0 and s.logical_ts <= parent.logical_ts:
                violations.append({
                    "type": "logical_clock_regression",
                    "severity": "warning",
                    "span_id": s.span_id,
                    "name": s.name,
                    "parent_span_id": s.parent_span_id,
                    "detail": f"child.logical_ts ({s.logical_ts}) <= parent.logical_ts ({parent.logical_ts})",
                })

    # Check for non-monotonic logical_ts across all spans (sorted by creation)
    sorted_spans = sorted(trace.spans, key=lambda s: s.started_at)
    prev_ts = 0
    for s in sorted_spans:
        if s.logical_ts > 0 and s.logical_ts < prev_ts:
            violations.append({
                "type": "logical_clock_non_monotonic",
                "severity": "warning",
                "span_id": s.span_id,
                "name": s.name,
                "detail": f"logical_ts ({s.logical_ts}) < previous ({prev_ts}) in chronological order",
            })
        if s.logical_ts > 0:
            prev_ts = s.logical_ts

    return violations


def count_causal_violations(traces: list[Trace]) -> int:
    """Count total causal violations across all traces (fast, no detail)."""
    total = 0
    for t in traces:
        total += len(detect_time_violations(t))
        total += len(detect_parent_child_order_violations(t))
        total += len(detect_out_of_order_spans(t))
    return total


def validate_trace_causal_integrity(trace: Trace) -> dict:
    """Run all causal checks on a single trace. Returns summary."""
    time_violations = detect_time_violations(trace)
    order_violations = detect_parent_child_order_violations(trace)
    clock_violations = detect_out_of_order_spans(trace)
    all_violations = time_violations + order_violations + clock_violations

    return {
        "trace_id": trace.trace_id,
        "name": trace.name,
        "causal_integrity": "ok" if not all_violations else "violations",
        "violation_count": len(all_violations),
        "violations": all_violations,
        "time_violations": len(time_violations),
        "order_violations": len(order_violations),
        "clock_violations": len(clock_violations),
        "logical_clock_drift": _compute_clock_drift(trace),
    }


def _compute_clock_drift(trace: Trace) -> int:
    """Estimate logical clock drift as max gap in logical_ts sequence."""
    if not trace.spans:
        return 0
    sorted_spans = sorted(
        [s for s in trace.spans if s.logical_ts > 0],
        key=lambda s: s.logical_ts,
    )
    if len(sorted_spans) < 2:
        return 0
    max_gap = 0
    for i in range(1, len(sorted_spans)):
        gap = sorted_spans[i].logical_ts - sorted_spans[i - 1].logical_ts
        max_gap = max(max_gap, gap - 1)
    return max_gap
