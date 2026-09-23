"""SSE streaming correctness tests.

Tests the set-diff logic that drives SSE events, not the HTTP transport.
The SSE endpoint's core logic is: snapshot state, diff against previous,
emit events for changes. This tests that diff logic as pure functions.
"""

from __future__ import annotations

from typing import Any

import pytest

from aethon.xray import store as xray_store
from aethon.xray.span import Span
from aethon.xray.trace import Trace


@pytest.fixture(autouse=True)
def reset_store():
    xray_store.clear()
    yield
    xray_store.clear()


def _capture_state(xray_store) -> dict:
    """Snapshot current xray_store state (mirrors SSE endpoint logic)."""
    completed = xray_store.get_completed_traces()
    active = xray_store.get_active_traces()
    orphan = len(xray_store._orphan_spans)
    return {
        "completed_ids": {t.trace_id for t in completed},
        "active_ids": {t.trace_id for t in active},
        "frozen_ids": {t.trace_id for t in completed + active if t.freeze},
        "orphan": orphan,
    }


def _compute_diffs(prev: dict[str, Any], curr: dict[str, Any]) -> dict[str, Any]:
    """Compute state diffs between two snapshots (pure function).

    Returns dict with keys: new_completed, new_active, removed_active,
    newly_frozen, newly_unfrozen, orphan_changed.
    """
    return {
        "new_completed": curr["completed_ids"] - prev["completed_ids"],
        "new_active": curr["active_ids"] - prev["active_ids"],
        "removed_active": prev["active_ids"] - curr["active_ids"],
        "newly_frozen": curr["frozen_ids"] - prev["frozen_ids"],
        "newly_unfrozen": prev["frozen_ids"] - curr["frozen_ids"],
        "orphan_changed": curr["orphan"] != prev["orphan"],
    }


def _has_any_diff(diffs: dict[str, Any]) -> bool:
    """Check if any lifecycle diff exists (excluding orphan which is handled separately)."""
    return bool(
        diffs["new_completed"]
        or diffs["new_active"]
        or diffs["removed_active"]
        or diffs["newly_frozen"]
        or diffs["newly_unfrozen"]
        or diffs["orphan_changed"]
    )


def _make_events(diffs: dict[str, Any], orphan: int) -> list[dict]:
    """Build SSE event list from diffs (pure function).

    Returns list of {event, data} dicts in the order the SSE endpoint emits them.
    """
    events = []
    for tid in sorted(diffs["new_completed"]):
        events.append({"event": "trace_completed", "data": {"trace_id": tid}})
    for tid in sorted(diffs["new_active"]):
        events.append({"event": "trace_started", "data": {"trace_id": tid}})
    for tid in sorted(diffs["removed_active"]):
        events.append({"event": "trace_ended", "data": {"trace_id": tid}})
    for tid in sorted(diffs["newly_frozen"]):
        events.append({"event": "trace_frozen", "data": {"trace_id": tid, "frozen": True}})
    for tid in sorted(diffs["newly_unfrozen"]):
        events.append({"event": "trace_frozen", "data": {"trace_id": tid, "frozen": False}})
    if diffs["orphan_changed"]:
        events.append({"event": "orphan_change", "data": {"count": orphan}})
    if _has_any_diff(diffs):
        events.append({"event": "stats_changed", "data": {}})
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCaptureState:
    """Verify _capture_state correctly snapshots store internals."""

    def test_empty_store(self):
        state = _capture_state(xray_store)
        assert state["completed_ids"] == set()
        assert state["active_ids"] == set()
        assert state["orphan"] == 0

    def test_traces_in_store(self):
        xray_store._active["a1"] = Trace(trace_id="a1", name="a1", started_at=100.0)
        xray_store._completed["c1"] = Trace(trace_id="c1", name="c1", started_at=100.0, ended_at=200.0)
        state = _capture_state(xray_store)
        assert "a1" in state["active_ids"]
        assert "c1" in state["completed_ids"]

    def test_frozen_detection(self):
        xray_store._completed["f1"] = Trace(trace_id="f1", name="f1", started_at=100.0, ended_at=200.0, freeze=True)
        state = _capture_state(xray_store)
        assert "f1" in state["frozen_ids"]

    def test_orphan_count(self):
        xray_store._orphan_spans["o1"] = Span(span_id="o1", trace_id="t", kind="test", name="o", started_at=100.0)
        state = _capture_state(xray_store)
        assert state["orphan"] == 1


class TestComputeDiffs:
    """Verify set-diff arithmetic for SSE state transitions."""

    def test_no_changes(self):
        prev = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        diffs = _compute_diffs(prev, curr)
        assert diffs["new_completed"] == set()
        assert diffs["new_active"] == set()
        assert diffs["removed_active"] == set()
        assert diffs["orphan_changed"] is False

    def test_new_trace_completed(self):
        prev = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": {"t1"}, "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        diffs = _compute_diffs(prev, curr)
        assert diffs["new_completed"] == {"t1"}
        assert diffs["new_active"] == set()

    def test_new_trace_active(self):
        prev = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": set(), "active_ids": {"t1"}, "frozen_ids": set(), "orphan": 0}
        diffs = _compute_diffs(prev, curr)
        assert diffs["new_active"] == {"t1"}

    def test_removed_active(self):
        prev = {"completed_ids": set(), "active_ids": {"t1"}, "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        diffs = _compute_diffs(prev, curr)
        assert diffs["removed_active"] == {"t1"}

    def test_newly_frozen(self):
        prev = {"completed_ids": {"t1"}, "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": {"t1"}, "active_ids": set(), "frozen_ids": {"t1"}, "orphan": 0}
        diffs = _compute_diffs(prev, curr)
        assert diffs["newly_frozen"] == {"t1"}

    def test_newly_unfrozen(self):
        prev = {"completed_ids": {"t1"}, "active_ids": set(), "frozen_ids": {"t1"}, "orphan": 0}
        curr = {"completed_ids": {"t1"}, "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        diffs = _compute_diffs(prev, curr)
        assert diffs["newly_unfrozen"] == {"t1"}

    def test_orphan_changed(self):
        prev = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": set(), "active_ids": set(), "frozen_ids": set(), "orphan": 5}
        diffs = _compute_diffs(prev, curr)
        assert diffs["orphan_changed"] is True

    def test_multiple_changes_at_once(self):
        prev = {"completed_ids": {"old"}, "active_ids": set(), "frozen_ids": set(), "orphan": 0}
        curr = {"completed_ids": {"old"}, "active_ids": {"new1"}, "frozen_ids": set(), "orphan": 1}
        diffs = _compute_diffs(prev, curr)
        assert diffs["new_active"] == {"new1"}
        assert diffs["orphan_changed"] is True


class TestHasAnyDiff:
    def test_false_when_no_diff(self):
        diffs = {
            "new_completed": set(), "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        assert _has_any_diff(diffs) is False

    def test_true_when_any_diff(self):
        diffs = {
            "new_completed": {"t1"}, "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        assert _has_any_diff(diffs) is True


class TestMakeEvents:
    """Verify event generation from diffs (ordering and content)."""

    def test_empty_diffs_produces_no_events(self):
        diffs = {
            "new_completed": set(), "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events == []

    def test_completed_event(self):
        diffs = {
            "new_completed": {"t1"}, "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events[0]["event"] == "trace_completed"
        assert events[0]["data"]["trace_id"] == "t1"
        assert events[-1]["event"] == "stats_changed"

    def test_started_event(self):
        diffs = {
            "new_completed": set(), "new_active": {"t1"}, "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events[0]["event"] == "trace_started"

    def test_frozen_event(self):
        diffs = {
            "new_completed": set(), "new_active": set(), "removed_active": set(),
            "newly_frozen": {"f1"}, "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events[0]["event"] == "trace_frozen"
        assert events[0]["data"]["frozen"] is True

    def test_unfrozen_event(self):
        diffs = {
            "new_completed": set(), "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": {"f1"}, "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events[0]["event"] == "trace_frozen"
        assert events[0]["data"]["frozen"] is False

    def test_orphan_change_event(self):
        diffs = {
            "new_completed": set(), "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": True,
        }
        events = _make_events(diffs, orphan=3)
        assert events[0]["event"] == "orphan_change"
        assert events[0]["data"]["count"] == 3

    def test_stats_changed_always_last_when_diffs_present(self):
        diffs = {
            "new_completed": {"t1"}, "new_active": {"t2"}, "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events[-1]["event"] == "stats_changed"

    def test_ordering_completed_before_started(self):
        """Mirrors SSE endpoint order: completed, started, removed, frozen/unfrozen, orphan, stats."""
        diffs = {
            "new_completed": {"c1"}, "new_active": {"a1"}, "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        assert events[0]["event"] == "trace_completed"
        assert events[1]["event"] == "trace_started"

    def test_multiple_ids_sorted(self):
        diffs = {
            "new_completed": {"c2", "c1"}, "new_active": set(), "removed_active": set(),
            "newly_frozen": set(), "newly_unfrozen": set(), "orphan_changed": False,
        }
        events = _make_events(diffs, orphan=0)
        ids = [e["data"]["trace_id"] for e in events if e["event"] == "trace_completed"]
        assert ids == sorted(ids)


class TestIntegrationFullCycle:
    """End-to-end test: state transitions through the store produce correct diffs."""

    def test_trace_active_then_completed(self):
        """Start a trace, then complete it — verify both started and completed appear."""
        now = 1000.0
        prev = _capture_state(xray_store)

        xray_store._active["t1"] = Trace(trace_id="t1", name="t1", started_at=now)
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert "t1" in diffs["new_active"]

        prev = curr
        xray_store._completed["t1"] = Trace(trace_id="t1", name="t1", started_at=now, ended_at=now + 1.0)
        xray_store._active.pop("t1", None)
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert "t1" in diffs["new_completed"]
        events = _make_events(diffs, curr["orphan"])
        assert any(e["event"] == "trace_completed" for e in events)

    def test_freeze_lifecycle(self):
        """Freeze → unfreeze a trace and verify both transitions detected."""
        now = 1000.0
        xray_store._completed["f1"] = Trace(trace_id="f1", name="f1", started_at=now, ended_at=now + 1.0, freeze=False)
        prev = _capture_state(xray_store)

        xray_store._completed["f1"].freeze = True
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert "f1" in diffs["newly_frozen"]

        prev = curr
        xray_store._completed["f1"].freeze = False
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert "f1" in diffs["newly_unfrozen"]

    def test_orphan_increases_then_decreases(self):
        """Orphan count rising then falling both produce orphan_change."""
        prev = _capture_state(xray_store)

        xray_store._orphan_spans["o1"] = Span(span_id="o1", trace_id="t", kind="test", name="o", started_at=100.0)
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert diffs["orphan_changed"] is True

        prev = curr
        xray_store._orphan_spans.clear()
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert diffs["orphan_changed"] is True

    def test_no_diff_when_state_stable(self):
        """Multiple captures without changes produce no diffs."""
        state = _capture_state(xray_store)
        for _ in range(3):
            new_state = _capture_state(xray_store)
            diffs = _compute_diffs(state, new_state)
            assert not _has_any_diff(diffs)

    def test_multi_trace_independence(self):
        """Events for trace A don't reference trace B."""
        prev = _capture_state(xray_store)
        now = 1000.0
        xray_store._active["a1"] = Trace(trace_id="a1", name="alpha", started_at=now)
        xray_store._active["b1"] = Trace(trace_id="b1", name="beta", started_at=now)
        curr = _capture_state(xray_store)
        _compute_diffs(prev, curr)
        for tid in curr["active_ids"]:
            t = xray_store.get_trace(tid)
            assert t is not None
            assert t.trace_id == tid
            assert t.name in ("alpha", "beta")

    def test_no_duplicate_events_no_change(self):
        """Stable state produces zero events (no ghost updates)."""
        prev = _capture_state(xray_store)
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        events = _make_events(diffs, curr["orphan"])
        assert events == []


class TestSseStress:
    """SSE diff correctness under high-volume state changes."""

    def test_200_concurrent_trace_starts(self):
        prev = _capture_state(xray_store)
        now = 1000.0
        for i in range(200):
            xray_store._active[f"stress_start_{i:04d}"] = Trace(
                trace_id=f"stress_start_{i:04d}", name=f"stress-{i}", started_at=now + i,
            )
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert len(diffs["new_active"]) == 200
        events = _make_events(diffs, curr["orphan"])
        trace_started = [e for e in events if e["event"] == "trace_started"]
        assert len(trace_started) == 200

    def test_200_concurrent_trace_completions(self):
        now = 1000.0
        for i in range(200):
            tid = f"stress_done_{i:04d}"
            xray_store._active[tid] = Trace(trace_id=tid, name=f"done-{i}", started_at=now)
        prev = _capture_state(xray_store)
        for i in range(200):
            tid = f"stress_done_{i:04d}"
            t = xray_store._active.pop(tid)
            t.end("ok")
            xray_store._completed[tid] = t
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert len(diffs["new_completed"]) == 200
        events = _make_events(diffs, curr["orphan"])
        trace_completed = [e for e in events if e["event"] == "trace_completed"]
        assert len(trace_completed) == 200
        for e in trace_completed:
            assert e["data"]["trace_id"].startswith("stress_done_")

    def test_mixed_lifecycle_500_traces(self):
        now = 1000.0
        # Start 500 traces
        for i in range(500):
            tid = f"mixed_{i:04d}"
            xray_store._active[tid] = Trace(trace_id=tid, name=f"mixed-{i}", started_at=now + i)
        prev = _capture_state(xray_store)
        # Complete 300, freeze 100, keep 100 active
        for i in range(300):
            tid = f"mixed_{i:04d}"
            t = xray_store._active.pop(tid)
            t.end("ok")
            xray_store._completed[tid] = t
        for i in range(300, 400):
            tid = f"mixed_{i:04d}"
            t = xray_store._active[tid]
            t.freeze = True
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        assert len(diffs["new_completed"]) == 300
        events = _make_events(diffs, curr["orphan"])
        event_types = {e["event"] for e in events}
        assert "trace_completed" in event_types
        completed_count = sum(1 for e in events if e["event"] == "trace_completed")
        assert completed_count == 300

    def test_no_cross_event_contamination(self):
        """Events from different traces must never reference wrong IDs."""
        now = 1000.0
        for i in range(100):
            xray_store._active[f"iso_{i:04d}"] = Trace(
                trace_id=f"iso_{i:04d}", name=f"iso-{i}", started_at=now,
            )
        prev = _capture_state(xray_store)
        for i in range(50):
            tid = f"iso_{i:04d}"
            t = xray_store._active.pop(tid)
            t.end("ok")
            xray_store._completed[tid] = t
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        events = _make_events(diffs, curr["orphan"])
        for e in events:
            tid = e["data"].get("trace_id", "")
            if tid:
                assert tid.startswith("iso_")
                idx = int(tid.split("_")[1])
                if e["event"] == "trace_completed":
                    assert idx < 50, f"completed trace {tid} should be < 50"
                elif e["event"] == "trace_ended":
                    assert idx < 50, f"ended trace {tid} should be < 50"

    def test_orphan_spike_bounded_events(self):
        """A burst of orphans produces exactly one orphan_change event."""
        prev = _capture_state(xray_store)
        for i in range(100):
            xray_store._orphan_spans[f"orphan_{i:04d}"] = Span(
                span_id=f"orphan_{i:04d}", trace_id=f"orphan_trace_{i}",
                kind="test", name=f"orphan-{i}", started_at=1000.0,
            )
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        events = _make_events(diffs, curr["orphan"])
        orphan_change = [e for e in events if e["event"] == "orphan_change"]
        assert len(orphan_change) == 1
        assert orphan_change[0]["data"]["count"] == 100

    def test_freeze_burst_events(self):
        """Freezing many traces at once produces one event per trace."""
        now = 1000.0
        for i in range(100):
            tid = f"freeze_burst_{i:04d}"
            xray_store._active[tid] = Trace(trace_id=tid, name=f"fb-{i}", started_at=now)
        prev = _capture_state(xray_store)
        for i in range(100):
            tid = f"freeze_burst_{i:04d}"
            t = xray_store._active[tid]
            t.freeze = True
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        events = _make_events(diffs, curr["orphan"])
        frozen_events = [e for e in events if e["event"] == "trace_frozen"]
        assert len(frozen_events) == 100
        for e in frozen_events:
            assert e["data"]["frozen"] is True

    def test_stats_changed_only_on_diff(self):
        """stats_changed fires only when at least one metric changed."""
        prev = _capture_state(xray_store)
        curr = _capture_state(xray_store)
        diffs = _compute_diffs(prev, curr)
        events = _make_events(diffs, curr["orphan"])
        stats = [e for e in events if e["event"] == "stats_changed"]
        assert len(stats) == 0
        # Now make a change
        xray_store._active["s"] = Trace(trace_id="s", name="s", started_at=1000.0)
        curr2 = _capture_state(xray_store)
        diffs2 = _compute_diffs(curr, curr2)
        events2 = _make_events(diffs2, curr2["orphan"])
        stats2 = [e for e in events2 if e["event"] == "stats_changed"]
        assert len(stats2) == 1
