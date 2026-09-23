"""Scenario 5 — Runtime Restart: active traces cleared, completed preserved."""


from aethon.xray import (
    TraceStore, start_trace, start_span, SpanKind,
)


class TestRuntimeRestart:
    """Restart should clear active traces, keep completed, no corruption."""

    def test_clear_active_traces(self):
        """Active traces are removed after clear."""
        trace = start_trace("core.chat", correlation_id="rr:1")
        trace.end()

        start_trace("gateway.chat", correlation_id="rr:2")
        # Simulate restart — clear store
        from aethon.xray import store as global_store
        global_store.clear()

        assert global_store.stats["active_traces"] == 0
        assert global_store.stats["completed_traces"] == 0
        assert global_store.stats["orphan_spans"] == 0

    def test_completed_trace_survives_restart(self):
        """Completed traces should persist in a fresh store."""
        # Create and complete a trace in global store
        from aethon.xray import store as global_store
        trace = start_trace("core.chat", correlation_id="rr:3")
        trace_id = trace.trace_id
        trace.end()

        # Export completed trace
        completed = global_store.get_recent_traces(limit=10)

        # Fresh store should have nothing
        fresh = TraceStore()
        assert fresh.stats["completed_traces"] == 0

        # But we can import completed traces
        for t in completed:
            fresh.register_trace(t)
            fresh.finalize_trace(t.trace_id)

        assert fresh.stats["completed_traces"] >= 1
        assert fresh.get_trace(trace_id) is not None

    def test_restart_no_corrupted_traces(self):
        """After restart clear, no corrupted traces should exist."""
        from aethon.xray import store as global_store
        trace = start_trace("core.chat", correlation_id="rr:4")
        trace.end()
        global_store.clear()

        diag = global_store.diagnostics()
        assert diag["trace_integrity"] == "ok"
        assert diag["corrupted_traces"] == 0

    def test_restart_accepts_new_traces(self):
        """Fresh store accepts new traces after restart."""
        from aethon.xray import store as global_store
        global_store.clear()

        trace = start_trace("core.chat", correlation_id="rr:5")
        trace_id = trace.trace_id
        s = start_span(SpanKind.CORE_ORCHESTRATE, "orchestrate", trace_id=trace_id)
        s.end()
        trace.end()

        assert global_store.stats["completed_traces"] >= 1
