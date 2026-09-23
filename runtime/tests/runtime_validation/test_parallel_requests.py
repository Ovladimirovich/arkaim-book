"""Scenario 6 — Parallel Requests: trace isolation under concurrency."""

import asyncio
import pytest

from aethon.xray import store as global_store, start_trace, start_span, SpanKind


class TestParallelRequests:
    """Multiple concurrent requests must not mix trace_ids or spans."""

    @pytest.mark.asyncio
    async def test_parallel_trace_isolation(self):
        """Each parallel trace has a unique trace_id."""
        async def make_trace(session_id: str) -> str:
            trace = start_trace("telegram.update", correlation_id=session_id)
            trace_id = trace.trace_id
            s = start_span(SpanKind.TELEGRAM_UPDATE, "update", trace_id=trace_id)
            await asyncio.sleep(0.01)
            s.end()
            trace.end()
            return trace_id

        ids = await asyncio.gather(*[make_trace(f"p:{i}") for i in range(10)])
        assert len(set(ids)) == 10

    @pytest.mark.asyncio
    async def test_parallel_span_no_cross_contamination(self):
        """Spans from parallel traces must not borrow each other's IDs."""
        results = {}

        async def make_trace(idx: int):
            trace = start_trace("test", correlation_id=f"p:{idx}")
            trace_id = trace.trace_id
            s = start_span(SpanKind.CUSTOM, f"work_{idx}", trace_id=trace_id)
            await asyncio.sleep(0.02)
            results[idx] = {"trace_id": trace_id, "span_id": s.span_id}
            s.end()
            trace.end()

        await asyncio.gather(*[make_trace(i) for i in range(10)])

        span_ids = [r["span_id"] for r in results.values()]
        assert len(set(span_ids)) == 10

    def test_mixed_fallback_parallel(self):
        """Fallback chains in parallel must not interfere."""
        traces = []
        for i in range(5):
            trace = start_trace("core.chat", correlation_id=f"mp:{i}")
            trace_id = trace.trace_id
            orch = start_span(SpanKind.CORE_ORCHESTRATE, "orchestrate", trace_id=trace_id)
            p1 = start_span(SpanKind.PROVIDER_CALL, "gigachat.chat", trace_id=trace_id, parent_span_id=orch.span_id)
            p1.end("error")
            p2 = start_span(SpanKind.PROVIDER_CALL, "openrouter.chat", trace_id=trace_id, parent_span_id=orch.span_id)
            p2.end("ok")
            orch.end()
            trace.end()
            traces.append(trace_id)

        stats = global_store.stats
        assert stats["orphan_spans"] == 0

        # Each trace should have correct tree
        for tid in traces:
            tree = global_store.get_trace_tree(tid)
            assert tree is not None
            assert tree["status"] == "ok"

    def test_timeout_does_not_affect_other_traces(self):
        """A timeout in one trace should not impact other traces."""
        # Normal trace
        t1 = start_trace("gateway.chat", correlation_id="to:a")
        t1_id = t1.trace_id
        s1 = start_span(SpanKind.GATEWAY_REQUEST, "proxy_chat", trace_id=t1_id)
        s1.end("ok")
        t1.end("ok")

        # Timeout trace
        t2 = start_trace("gateway.chat", correlation_id="to:b")
        t2_id = t2.trace_id
        s2 = start_span(SpanKind.GATEWAY_REQUEST, "proxy_chat", trace_id=t2_id)
        s2.end("error")
        t2.end("error")

        # Normal trace still ok
        tree1 = global_store.get_trace_tree(t1_id)
        assert tree1["status"] == "ok"
        tree2 = global_store.get_trace_tree(t2_id)
        assert tree2["status"] == "error"
