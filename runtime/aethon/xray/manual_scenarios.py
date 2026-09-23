"""Manual validation scenarios for X-RAY stabilization layer.

Each scenario is a fixed, deterministic execution that produces a trace
that can be visually inspected for correctness.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from aethon.xray.trace import start_trace
from aethon.xray.span import start_span, SpanKind
from aethon.xray.trace_store import store
from aethon.xray.causal_validator import validate_trace_causal_integrity


async def scenario_a_normal() -> dict:
    """SCENARIO A — Normal flow.

    1 request → 1 trace → no fallback.
    Validates: single root span, correct depth, no orphans, clean finalize.
    """
    trace = start_trace("manual.scenario_a", metadata={"scenario": "A", "description": "normal flow"})
    span_root = start_span(SpanKind.CUSTOM, "scenario_a.root")

    await asyncio.sleep(0.01)

    span_child = start_span(SpanKind.CUSTOM, "scenario_a.child", parent_span_id=span_root.span_id)
    await asyncio.sleep(0.01)
    span_child.end()

    await asyncio.sleep(0.01)
    span_root.end()

    trace.end("ok")

    result = {
        "trace_id": trace.trace_id,
        "status": trace.status,
        "span_count": len(trace.spans),
        "freeze": trace.freeze,
        "duration_ms": trace.duration_ms,
    }

    validation = validate_trace_causal_integrity(trace)
    replay = store.replay(trace.trace_id, mode="causal")

    return {
        "scenario": "A — Normal flow",
        "status": "ok",
        "trace": result,
        "validation": validation,
        "replay": replay,
    }


async def scenario_b_failure_fallback() -> dict:
    """SCENARIO B — Failure + fallback.

    Provider error → fallback trigger → continuity check.
    Validates: error propagation, fallback span, status consistency.
    """
    trace = start_trace("manual.scenario_b", metadata={"scenario": "B", "description": "failure + fallback"})
    orch_span = start_span(SpanKind.CORE_ORCHESTRATE, "scenario_b.orchestrate")

    # First provider fails
    span_p1 = start_span(SpanKind.PROVIDER_CALL, "scenario_b.provider.gigachat",
                         parent_span_id=orch_span.span_id)
    await asyncio.sleep(0.01)
    span_p1.end("error")

    # Fallback to second provider
    span_fb = start_span(SpanKind.PROVIDER_CALL, "scenario_b.provider.openrouter",
                         parent_span_id=orch_span.span_id)
    await asyncio.sleep(0.01)
    span_fb.end()

    orch_span.end()

    trace.end("ok")

    validation = validate_trace_causal_integrity(trace)
    replay = store.replay(trace.trace_id, mode="causal")

    return {
        "scenario": "B — Failure + fallback",
        "status": "ok",
        "trace": {
            "trace_id": trace.trace_id,
            "status": trace.status,
            "span_count": len(trace.spans),
            "freeze": trace.freeze,
        },
        "validation": validation,
        "replay": replay,
    }


async def scenario_c_parallel_chaos() -> dict:
    """SCENARIO C — Parallel chaos.

    5 concurrent requests → validate isolation.
    Validates: no cross-trace span leakage, correct per-trace counts,
    causal integrity per trace.
    """
    async def _parallel_trace(idx: int) -> dict:
        trace = start_trace(f"manual.scenario_c.{idx}",
                            metadata={"scenario": "C", "parallel_idx": idx})
        s_root = start_span(SpanKind.CUSTOM, f"scenario_c.root.{idx}")

        # Both children alive during grandchild
        s_child_a = start_span(SpanKind.CUSTOM, f"scenario_c.child_a.{idx}",
                               parent_span_id=s_root.span_id)
        s_child_b = start_span(SpanKind.CUSTOM, f"scenario_c.child_b.{idx}",
                               parent_span_id=s_root.span_id)

        s_grand = start_span(SpanKind.CUSTOM, f"scenario_c.grandchild.{idx}",
                             parent_span_id=s_child_a.span_id)
        await asyncio.sleep(0.005)
        s_grand.end()

        await asyncio.sleep(0.005)
        s_child_a.end()
        s_child_b.end()

        s_root.end()
        trace.end("ok")

        validation = validate_trace_causal_integrity(trace)
        return {
            "trace_id": trace.trace_id,
            "span_count": len(trace.spans),
            "status": trace.status,
            "validation": validation,
        }

    tasks = [_parallel_trace(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    trace_ids = [r["trace_id"] for r in results]
    all_ok = all(r["status"] == "ok" for r in results)
    no_violations = all(r["validation"]["causal_integrity"] == "ok" for r in results)

    return {
        "scenario": "C — Parallel chaos (5 concurrent)",
        "status": "ok" if all_ok else "violations",
        "no_violations": no_violations,
        "trace_count": len(results),
        "trace_ids": trace_ids,
        "results": results,
    }


SCENARIOS = {
    "A": scenario_a_normal,
    "B": scenario_b_failure_fallback,
    "C": scenario_c_parallel_chaos,
}


async def run_scenario(name: str) -> dict | None:
    """Run a manual scenario by name (A, B, or C)."""
    fn = SCENARIOS.get(name.upper())
    if fn is None:
        return None
    return await fn()
