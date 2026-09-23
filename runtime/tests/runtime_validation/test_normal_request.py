"""Scenario 1 — Normal Request: full trace chain through all layers."""

import time

from aethon.xray import store as global_store, start_trace, start_span, SpanKind


class TestNormalRequest:
    """One Telegram message → one trace with correct span nesting."""

    def test_full_chain_single_trace_id(self):
        """All layers share the same trace_id."""
        trace = start_trace("telegram.update", correlation_id="tg:1")
        trace_id = trace.trace_id
        ts = start_span(SpanKind.TELEGRAM_UPDATE, "telegram.update", trace_id=trace_id)
        gw = start_span(SpanKind.GATEWAY_REQUEST, "gateway.chat", trace_id=trace_id, parent_span_id=ts.span_id)
        co = start_span(SpanKind.CORE_ORCHESTRATE, "core.chat", trace_id=trace_id, parent_span_id=gw.span_id)
        pc = start_span(SpanKind.PROVIDER_CALL, "gigachat.chat", trace_id=trace_id, parent_span_id=co.span_id)
        pc.end()
        co.end()
        gw.end()
        ts.end()
        trace.end()

        tree = global_store.get_trace_tree(trace_id)
        assert tree is not None
        assert tree["trace_id"] == trace_id
        assert tree["status"] == "ok"

    def test_correct_span_nesting(self):
        """Spans form a proper parent-child tree."""
        trace = start_trace("telegram.update", correlation_id="tg:2")
        trace_id = trace.trace_id
        ts = start_span(SpanKind.TELEGRAM_UPDATE, "telegram.update", trace_id=trace_id)
        gw = start_span(SpanKind.GATEWAY_REQUEST, "gateway.chat", trace_id=trace_id, parent_span_id=ts.span_id)

        assert gw.parent_span_id == ts.span_id

        gw.end()
        ts.end()
        trace.end()

    def test_completed_trace_no_orphans(self):
        """Completed trace should leave no orphan spans."""
        trace = start_trace("telegram.update", correlation_id="tg:3")
        trace_id = trace.trace_id
        s1 = start_span(SpanKind.TELEGRAM_UPDATE, "s1", trace_id=trace_id)
        s2 = start_span(SpanKind.GATEWAY_REQUEST, "s2", trace_id=trace_id, parent_span_id=s1.span_id)
        s2.end()
        s1.end()
        trace.end()

        stats = global_store.stats
        assert stats["orphan_spans"] == 0
        assert stats["completed_traces"] >= 1

    def test_trace_has_correct_duration(self):
        """Trace duration should reflect actual wall-clock time."""
        trace = start_trace("test.duration", correlation_id="tg:4")
        trace_id = trace.trace_id
        s = start_span(SpanKind.CUSTOM, "work", trace_id=trace_id)
        time.sleep(0.01)
        s.end()
        trace.end()

        assert trace.duration_ms is not None
        assert trace.duration_ms > 5
