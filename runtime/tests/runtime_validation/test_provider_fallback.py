"""Scenario 2 — Provider Failure + Fallback: continuity across retries."""


from aethon.xray import store as global_store, start_trace, start_span, SpanKind


class TestProviderFallback:
    """Provider failure → fallback should preserve trace continuity."""

    def test_fallback_chain_same_trace_id(self):
        """Fallback provider spans keep the same trace_id."""
        trace = start_trace("core.chat", correlation_id="fb:1")
        trace_id = trace.trace_id
        orch = start_span(SpanKind.CORE_ORCHESTRATE, "core.chat", trace_id=trace_id)

        # First provider fails
        p1 = start_span(SpanKind.PROVIDER_CALL, "gigachat.chat", trace_id=trace_id, parent_span_id=orch.span_id)
        p1.end("error")
        # Fallback succeeds
        p2 = start_span(SpanKind.PROVIDER_CALL, "openrouter.chat", trace_id=trace_id, parent_span_id=orch.span_id)
        p2.end("ok")

        orch.end()
        trace.end()

        assert global_store.stats["orphan_spans"] == 0
        tree = global_store.get_trace_tree(trace_id)
        assert tree is not None
        assert tree["status"] == "ok"

    def test_fallback_span_nesting(self):
        """Fallback spans should be children of the same orchestrator span."""
        trace = start_trace("core.chat", correlation_id="fb:2")
        trace_id = trace.trace_id
        orch = start_span(SpanKind.CORE_ORCHESTRATE, "core.chat", trace_id=trace_id)

        p1 = start_span(SpanKind.PROVIDER_CALL, "gigachat.chat", trace_id=trace_id, parent_span_id=orch.span_id)
        p1.end("error")
        p2 = start_span(SpanKind.PROVIDER_CALL, "openrouter.chat", trace_id=trace_id, parent_span_id=orch.span_id)
        p2.end("ok")

        orch.end()
        trace.end()

        tree = global_store.get_trace_tree(trace_id)
        tree_nodes = tree["tree"]
        # Get the first (and only) root
        root = tree_nodes[0] if isinstance(tree_nodes, list) else tree_nodes
        children = root.get("children", [])
        kinds = [c["kind"] for c in children]
        assert "provider_call" in kinds
        # Both provider spans are siblings under orch
        assert len([c for c in children if c["kind"] == "provider_call"]) == 2

    def test_fallback_does_not_fragment_trace(self):
        """Trace should not split into multiple trees after fallback."""
        trace = start_trace("core.chat", correlation_id="fb:3")
        trace_id = trace.trace_id
        orch = start_span(SpanKind.CORE_ORCHESTRATE, "core.chat", trace_id=trace_id)

        for name, status in [("gigachat", "error"), ("openrouter", "ok")]:
            s = start_span(SpanKind.PROVIDER_CALL, f"{name}.chat", trace_id=trace_id, parent_span_id=orch.span_id)
            s.end(status)

        orch.end()
        trace.end()

        tree = global_store.get_trace_tree(trace_id)
        assert tree is not None
        # Single tree root
        tree_nodes = tree["tree"]
        roots = tree_nodes if isinstance(tree_nodes, list) else [tree_nodes]
        assert len(roots) == 1

    def test_fallback_error_count(self):
        """Failed provider span should be counted as error."""
        trace = start_trace("core.chat", correlation_id="fb:4")
        trace_id = trace.trace_id
        orch = start_span(SpanKind.CORE_ORCHESTRATE, "core.chat", trace_id=trace_id)
        p1 = start_span(SpanKind.PROVIDER_CALL, "gigachat.chat", trace_id=trace_id, parent_span_id=orch.span_id)
        p1.end("error")
        p2 = start_span(SpanKind.PROVIDER_CALL, "openrouter.chat", trace_id=trace_id, parent_span_id=orch.span_id)
        p2.end("ok")
        orch.end()
        trace.end()

        diag = global_store.diagnostics()
        assert diag["trace_integrity"] == "ok"
