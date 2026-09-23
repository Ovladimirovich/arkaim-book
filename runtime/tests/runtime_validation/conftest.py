"""Shared fixtures for runtime validation tests."""

import time
import pytest

from aethon.xray import (
    TraceStore, store as global_store, Span,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Clear the global trace store before each test."""
    global_store.clear()
    yield
    global_store.clear()


@pytest.fixture
def fresh_store():
    """Return a clean isolated store (does not touch global state)."""
    s = TraceStore()
    return s


def make_chain(store, trace_id: str, span_ids: list[str], parent_map: dict[str, str | None]):
    """Build a span chain in the store for testing."""
    now = time.time()
    spans = []
    for i, sid in enumerate(span_ids):
        parent = parent_map.get(sid)
        span = Span(
            span_id=sid,
            trace_id=trace_id,
            kind="test",
            name=f"span_{sid}",
            started_at=now + i * 0.1,
            ended_at=now + i * 0.1 + 0.05,
            duration_ms=50.0,
            status="ok",
            parent_span_id=parent,
        )
        store.register_span(span)
        spans.append(span)
    return spans
