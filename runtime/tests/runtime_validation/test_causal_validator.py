"""Causal integrity validation tests."""

import time

from aethon.xray import (
    store as global_store, start_trace, start_span, SpanKind,
)
from aethon.xray.causal_validator import (
    detect_time_violations,
    detect_orphan_over_time,
    validate_trace_causal_integrity,
)


class TestLogicalTimestamps:
    """Spans get sequential logical_ts within a trace."""

    def test_logical_ts_increases(self):
        trace = start_trace("test.logical")
        tid = trace.trace_id
        s1 = start_span(SpanKind.CUSTOM, "s1", trace_id=tid)
        s2 = start_span(SpanKind.CUSTOM, "s2", trace_id=tid)
        s3 = start_span(SpanKind.CUSTOM, "s3", trace_id=tid)
        assert s1.logical_ts < s2.logical_ts < s3.logical_ts
        s3.end()
        s2.end()
        s1.end()
        trace.end()

    def test_depth_tracks_nesting(self):
        trace = start_trace("test.depth")
        tid = trace.trace_id
        s1 = start_span(SpanKind.CUSTOM, "root", trace_id=tid)
        assert s1.depth == 0
        s2 = start_span(SpanKind.CUSTOM, "child", trace_id=tid, parent_span_id=s1.span_id)
        assert s2.depth == s1.depth + 1
        s3 = start_span(SpanKind.CUSTOM, "grandchild", trace_id=tid, parent_span_id=s2.span_id)
        assert s3.depth == s2.depth + 1 == 2
        s3.end()
        s2.end()
        s1.end()
        trace.end()


class TestFreezeState:
    """Trace freeze prevents new spans without blocking."""

    def test_freeze_on_end(self):
        trace = start_trace("test.freeze")
        assert trace.freeze is False
        trace.end()
        assert trace.freeze is True
        assert trace.finalize_ts is not None

    def test_span_after_freeze_is_late(self):
        trace = start_trace("test.late")
        tid = trace.trace_id
        s1 = start_span(SpanKind.CUSTOM, "normal", trace_id=tid)
        s1.end()
        trace.end()
        # Span created after freeze should be marked late
        s2 = start_span(SpanKind.CUSTOM, "late", trace_id=tid)
        assert s2.late is True
        s2.end()

    def test_double_freeze_safe(self):
        trace = start_trace("test.double_freeze")
        trace.end()
        ts1 = trace.finalize_ts
        trace.end()
        assert trace.finalize_ts == ts1


class TestCausalValidator:
    """Causal validation detects ordering violations."""

    def test_no_violations_clean_trace(self):
        trace = start_trace("test.clean")
        tid = trace.trace_id
        s1 = start_span(SpanKind.CUSTOM, "parent", trace_id=tid)
        s2 = start_span(SpanKind.CUSTOM, "child", trace_id=tid, parent_span_id=s1.span_id)
        s2.end()
        s1.end()
        trace.end()
        result = validate_trace_causal_integrity(trace)
        assert result["causal_integrity"] == "ok"
        assert result["violation_count"] == 0

    def test_detect_child_before_parent_time(self):
        """Child start before parent start is a violation."""
        trace = start_trace("test.time_violation")
        tid = trace.trace_id
        s1 = start_span(SpanKind.CUSTOM, "parent", trace_id=tid)
        # Manually create a child with earlier start time
        from aethon.xray.span import Span
        s2 = Span(
            span_id="violation",
            trace_id=tid,
            kind="custom",
            name="child",
            started_at=s1.started_at - 1.0,  # BEFORE parent!
            parent_span_id=s1.span_id,
        )
        trace.add_span(s2)
        s1.end()
        trace.end()
        violations = detect_time_violations(trace)
        assert any(v["type"] == "child_before_parent" for v in violations)

    def test_orphan_detection_with_grace_window(self):
        """Orphans within grace window are NOT flagged."""
        from aethon.xray.trace_store import store
        store.clear()
        # Create orphan span
        from aethon.xray.span import Span
        s = Span(span_id="fresh_orphan", trace_id="ghost", kind="custom", name="fresh", started_at=time.time())
        store._orphan_spans[s.span_id] = s
        # Within grace window — no violation
        violations = detect_orphan_over_time(store.get_completed_traces(), store=store)
        fresh_violations = [v for v in violations if v["span_id"] == "fresh_orphan"]
        assert len(fresh_violations) == 0
        store.clear()

    def test_causal_replay_mode(self):
        """Causal replay sorts by logical_ts, not wall clock."""
        trace = start_trace("test.causal_replay")
        tid = trace.trace_id
        s1 = start_span(SpanKind.CUSTOM, "first", trace_id=tid)
        s2 = start_span(SpanKind.CUSTOM, "second", trace_id=tid)
        s1.end()
        s2.end()
        trace.end()
        # Causal replay should respect logical_ts order
        replay = global_store.replay(tid, mode="causal")
        assert replay["replay_mode"] == "causal"
        timestamps = [e["logical_ts"] for e in replay["timeline"]]
        assert timestamps == sorted(timestamps)
