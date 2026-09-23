"""Scenario 4 — Telegram Disconnect: transport failure during active trace."""

import time

from aethon.xray import (
    store as global_store, start_trace, start_span, SpanKind,
    Event, emit, EventKind, ComponentKind, Severity,
)


class TestTelegramDisconnect:
    """Telegram disconnection should emit transport_failure and clean up."""

    def test_transport_failure_event(self):
        """Transport failure event should be emitted on disconnect."""
        trace = start_trace("telegram.update", correlation_id="td:1")
        trace_id = trace.trace_id
        emit(Event(time.time(), trace_id, ComponentKind.TELEGRAM, EventKind.TRANSPORT_FAILURE, Severity.ERROR, "connection lost"))
        trace.end("error")

        assert trace.status == "error"

    def test_disconnect_no_orphan_spans(self):
        """Trace should complete without orphan spans after disconnect."""
        trace = start_trace("telegram.update", correlation_id="td:2")
        trace_id = trace.trace_id
        span = start_span(SpanKind.TELEGRAM_UPDATE, "poll", trace_id=trace_id)
        emit(Event(time.time(), trace_id, ComponentKind.TELEGRAM, EventKind.TRANSPORT_FAILURE, Severity.ERROR, "connection lost"))
        span.end("error")
        trace.end("error")

        stats = global_store.stats
        assert stats["orphan_spans"] == 0

    def test_disconnect_incomplete_trace_cleanup(self):
        """Forcibly ending a trace during disconnect should clean up spans."""
        trace = start_trace("telegram.update", correlation_id="td:3")
        trace_id = trace.trace_id
        span = start_span(SpanKind.TELEGRAM_UPDATE, "poll", trace_id=trace_id)
        # Disconnect without ending span
        trace.end("error")

        assert span.ended_at is not None
        assert trace.status == "error"

    def test_reconnect_new_trace(self):
        """After disconnect, new messages get a fresh trace."""
        trace1 = start_trace("telegram.update", correlation_id="td:4a")
        trace1_id = trace1.trace_id
        trace1.end("error")

        trace2 = start_trace("telegram.update", correlation_id="td:4b")
        trace2_id = trace2.trace_id
        s = start_span(SpanKind.TELEGRAM_UPDATE, "poll", trace_id=trace2_id)
        s.end()
        trace2.end()

        assert trace1_id != trace2_id
        tree = global_store.get_trace_tree(trace2_id)
        assert tree is not None
        assert tree["status"] == "ok"
