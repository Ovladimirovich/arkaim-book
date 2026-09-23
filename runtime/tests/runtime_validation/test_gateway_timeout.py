"""Scenario 3 — Gateway Timeout: span closed on timeout, no dangling."""


from aethon.xray import store as global_store, start_trace, start_span, SpanKind


class TestGatewayTimeout:
    """Timeout should properly close spans without leaving dangling."""

    def test_timeout_span_status_error(self):
        """Span should have error status after timeout."""
        trace = start_trace("gateway.chat", correlation_id="to:1")
        trace_id = trace.trace_id
        span = start_span(SpanKind.GATEWAY_REQUEST, "proxy_chat", trace_id=trace_id)
        # Simulate timeout — no response
        span.end("error")
        trace.end("error")

        assert span.status == "error"
        assert trace.status == "error"

    def test_timeout_no_dangling_spans(self):
        """No dangling spans after timeout closure."""
        trace = start_trace("gateway.chat", correlation_id="to:2")
        trace_id = trace.trace_id
        span = start_span(SpanKind.GATEWAY_REQUEST, "proxy_chat", trace_id=trace_id)
        span.end("error")
        trace.end("error")

        diag = global_store.diagnostics()
        assert diag["dangling_spans"] == 0

    def test_timeout_trace_closes_all_spans(self):
        """Trace.end() should close any unclosed child spans."""
        trace = start_trace("gateway.chat", correlation_id="to:3")
        trace_id = trace.trace_id
        span = start_span(SpanKind.GATEWAY_REQUEST, "proxy_chat", trace_id=trace_id)
        # Deliberately NOT closing span — trace.end() should handle it
        trace.end("error")

        assert span.ended_at is not None
        assert trace.ended_at is not None

    def test_double_end_timeout(self):
        """Calling end() twice on same span is safe."""
        trace = start_trace("gateway.chat", correlation_id="to:4")
        trace_id = trace.trace_id
        span = start_span(SpanKind.GATEWAY_REQUEST, "proxy_chat", trace_id=trace_id)
        span.end("error")
        duration_1 = span.duration_ms
        span.end("ok")  # Second close — should be no-op for duration
        assert span.duration_ms == duration_1
        trace.end()
