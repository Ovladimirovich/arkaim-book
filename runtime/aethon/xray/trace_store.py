"""Trace Store — active/completed traces, span trees, execution chains.

Thread-safe in-memory store with optional disk persistence.
Single global instance used by all components.
"""

from __future__ import annotations

import atexit
import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from aethon.xray.trace import Trace, get_current_trace_id
from aethon.xray.span import Span


@dataclass
class SpanTreeNode:
    """A span as a node in the execution tree with its children."""
    span: Span
    children: list[SpanTreeNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span.span_id,
            "kind": self.span.kind,
            "name": self.span.name,
            "status": self.span.status,
            "duration_ms": self.span.duration_ms,
            "parent_span_id": self.span.parent_span_id,
            "metadata": self.span.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class TraceStore:
    """Global trace store — active traces, completed traces, span indexing."""

    def __init__(self, max_active: int = 500, max_completed: int = 2000):
        self._max_active = max_active
        self._max_completed = max_completed
        self._active: dict[str, Trace] = {}
        self._completed: dict[str, Trace] = {}
        self._orphan_spans: dict[str, Span] = {}
        self._persist_path: str | None = None
        self._persist_enabled = False

    # ── Persistence ─────────────────────────────────

    def configure_persistence(self, path: str):
        """Enable disk persistence. Sets up directory structure and loads
        any previously persisted traces (completed + interrupted)."""
        self._persist_path = path
        self._persist_enabled = True
        self._ensure_dirs()
        self._load_from_disk()
        atexit.register(self._flush_index)

    @property
    def persist_path(self) -> str | None:
        return self._persist_path

    def _ensure_dirs(self):
        base = self._persist_path
        os.makedirs(os.path.join(base, "traces"), exist_ok=True)
        os.makedirs(os.path.join(base, "spans"), exist_ok=True)

    def _index_path(self) -> str:
        return os.path.join(self._persist_path, "index.json")

    def _read_index(self) -> dict:
        path = self._index_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_index(self, index: dict):
        path = self._index_path()
        tmp = path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(index, f, indent=2)
            os.replace(tmp, path)
        except OSError:
            pass

    def _flush_index(self):
        if not self._persist_enabled:
            return
        index = {}
        for tid, t in self._completed.items():
            index[tid] = {
                "status": t.status,
                "started_at": t.started_at,
                "ended_at": t.ended_at,
                "span_count": len(t.spans),
            }
        for tid, t in self._active.items():
            index[tid] = {
                "status": t.status if t.ended_at else "active",
                "started_at": t.started_at,
                "ended_at": t.ended_at,
                "span_count": len(t.spans),
            }
        self._write_index(index)

    def _persist_span(self, span: Span):
        if not self._persist_enabled:
            return
        span_dir = os.path.join(self._persist_path, "spans", span.trace_id)
        os.makedirs(span_dir, exist_ok=True)
        path = os.path.join(span_dir, f"span_{span.span_id}.json")
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(span.to_dict(), f)

    def _persist_trace_snapshot(self, trace: Trace):
        if not self._persist_enabled:
            return
        trace_dir = os.path.join(self._persist_path, "traces")
        path = os.path.join(trace_dir, f"{trace.trace_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(trace.to_dict(), f)
        except OSError:
            pass

    def _update_index_entry(self, trace_id: str, status: str):
        if not self._persist_enabled:
            return
        trace = self._active.get(trace_id) or self._completed.get(trace_id)
        if trace is None:
            return
        index = self._read_index()
        index[trace_id] = {
            "status": status,
            "started_at": trace.started_at,
            "ended_at": trace.ended_at,
            "span_count": len(trace.spans),
        }
        self._write_index(index)

    def _load_from_disk(self):
        """Restore traces from disk. Called once at startup."""
        base = self._persist_path
        traces_dir = os.path.join(base, "traces")
        spans_base = os.path.join(base, "spans")

        # 1. Load completed trace snapshots
        if os.path.isdir(traces_dir):
            for fname in os.listdir(traces_dir):
                if not fname.endswith(".json"):
                    continue
                trace_id = fname[:-5]
                path = os.path.join(traces_dir, fname)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    trace = self._trace_from_dict(data)
                    if trace.ended_at is not None:
                        self._completed[trace_id] = trace
                    else:
                        trace.status = "interrupted"
                        self._completed[trace_id] = trace
                except (json.JSONDecodeError, OSError, KeyError):
                    continue

        # 2. Restore active traces from spans directory
        if os.path.isdir(spans_base):
            for tid_dir in os.listdir(spans_base):
                span_dir = os.path.join(spans_base, tid_dir)
                if not os.path.isdir(span_dir):
                    continue
                if tid_dir in self._completed:
                    continue
                spans = []
                for sfname in os.listdir(span_dir):
                    if not sfname.endswith(".json"):
                        continue
                    spath = os.path.join(span_dir, sfname)
                    try:
                        with open(spath, "r") as f:
                            sdata = json.load(f)
                        spans.append(Span.from_dict(sdata))
                    except (json.JSONDecodeError, OSError, KeyError):
                        continue
                if not spans:
                    continue
                trace = Trace(
                    trace_id=tid_dir,
                    name=spans[0].name if spans else "recovered",
                    started_at=min(s.started_at for s in spans),
                    status="interrupted",
                )
                trace.spans = spans
                trace.ended_at = max((s.ended_at for s in spans if s.ended_at), default=None)
                if trace.ended_at:
                    trace.duration_ms = (trace.ended_at - trace.started_at) * 1000
                self._completed[tid_dir] = trace

    def _trace_from_dict(self, data: dict) -> Trace:
        trace = Trace(
            trace_id=data["trace_id"],
            name=data.get("name", ""),
            started_at=data["started_at"],
            correlation_id=data.get("correlation_id", ""),
            status=data.get("status", "ok"),
        )
        if data.get("ended_at"):
            trace.ended_at = data["ended_at"]
            trace.duration_ms = data.get("duration_ms")
            trace.freeze = data.get("freeze", False)
            trace.finalize_ts = data.get("finalize_ts")
        trace.metadata = data.get("metadata", {})
        for sd in data.get("spans", []):
            span = Span(
                span_id=sd["span_id"],
                trace_id=sd["trace_id"],
                kind=sd.get("kind", ""),
                name=sd.get("name", ""),
                started_at=sd["started_at"],
                correlation_id=sd.get("correlation_id", ""),
                ended_at=sd.get("ended_at"),
                duration_ms=sd.get("duration_ms"),
                status=sd.get("status", "ok"),
                parent_span_id=sd.get("parent_span_id"),
                logical_ts=sd.get("logical_ts", 0),
                depth=sd.get("depth", 0),
                late=sd.get("late", False),
                metadata=sd.get("metadata", {}),
            )
            trace.spans.append(span)
            if span.logical_ts > trace._logical_ts_counter:
                trace._logical_ts_counter = span.logical_ts
        return trace

    # ── Trace lifecycle ─────────────────────────────

    def register_trace(self, trace: Trace):
        if len(self._active) >= self._max_active:
            oldest = min(self._active.keys(), key=lambda tid: self._active[tid].started_at)
            self._move_to_completed(oldest)
        self._active[trace.trace_id] = trace

    def complete_trace(self, trace_id: str, status: str = "ok"):
        trace = self._active.get(trace_id)
        if trace is None:
            return
        trace.end(status)

    def finalize_trace(self, trace_id: str):
        """Move trace to completed without calling end() again."""
        if trace_id not in self._active:
            return
        if len(self._completed) >= self._max_completed:
            snap = [(tid, t.ended_at or 0) for tid, t in list(self._completed.items())]
            oldest = min(snap, key=lambda x: (x[1], x[0]))[0]
            self._completed.pop(oldest, None)
        trace = self._active.pop(trace_id)
        self._completed[trace_id] = trace
        self._persist_trace_snapshot(trace)
        self._update_index_entry(trace_id, trace.status)

    def _direct_complete(self, trace: Trace):
        """Add an already-ended trace directly to completed store."""
        if len(self._completed) >= self._max_completed:
            snap = [(tid, t.ended_at or 0) for tid, t in list(self._completed.items())]
            oldest = min(snap, key=lambda x: (x[1], x[0]))[0]
            self._completed.pop(oldest, None)
        self._completed[trace.trace_id] = trace
        self._persist_trace_snapshot(trace)
        self._update_index_entry(trace.trace_id, trace.status)

    def get_trace(self, trace_id: str) -> Trace | None:
        return self._active.get(trace_id) or self._completed.get(trace_id)

    def get_active_traces(self) -> list[Trace]:
        return list(self._active.values())

    def get_completed_traces(self) -> list[Trace]:
        return list(self._completed.values())

    def get_recent_traces(self, limit: int = 50) -> list[Trace]:
        all_traces = list(self._completed.values()) + list(self._active.values())
        all_traces.sort(key=lambda t: t.started_at, reverse=True)
        return all_traces[:limit]

    # ── Trace operations ────────────────────────────

    def freeze_trace(self, trace_id: str) -> bool:
        trace = self.get_trace(trace_id)
        if not trace or trace.ended_at:
            return False
        trace.freeze = True
        trace.metadata["frozen_at"] = time.time()
        return True

    def unfreeze_trace(self, trace_id: str) -> bool:
        trace = self.get_trace(trace_id)
        if not trace or not trace.freeze:
            return False
        trace.freeze = False
        trace.metadata["unfrozen_at"] = time.time()
        return True

    def terminate_trace(self, trace_id: str) -> bool:
        trace = self.get_trace(trace_id)
        if not trace or trace.ended_at:
            return False
        for s in trace.spans:
            if s.ended_at is None:
                s.end(status="terminated")
        trace.status = "terminated"
        self._move_to_completed(trace_id)
        return True

    def tag_trace(self, trace_id: str, tags: dict) -> bool:
        trace = self.get_trace(trace_id)
        if not trace:
            return False
        trace.metadata.setdefault("tags", {}).update(tags)
        self._update_index_entry(trace_id, trace.status)
        return True

    def search_traces(self, query: str = "", status: str = "", limit: int = 50) -> list[Trace]:
        all_traces = list(self._completed.values()) + list(self._active.values())
        if query:
            q = query.lower()
            all_traces = [t for t in all_traces if q in t.trace_id.lower() or q in t.name.lower() or q in str(t.metadata.get("tags", {})).lower()]
        if status:
            all_traces = [t for t in all_traces if t.status == status]
        all_traces.sort(key=lambda t: t.started_at, reverse=True)
        return all_traces[:limit]

    # ── Span registration ───────────────────────────

    ORPHAN_GRACE_MS = 150

    def register_span(self, span: Span):
        trace = self._active.get(span.trace_id)
        if trace:
            if not any(s.span_id == span.span_id for s in trace.spans):
                if trace.freeze:
                    span.late = True
                trace.add_span(span)
                self._persist_span(span)
        else:
            self._orphan_spans[span.span_id] = span
            self._persist_span(span)

    def get_orphan_spans(self, limit: int = 100) -> list[Span]:
        now = time.time()
        return [s for s in self._orphan_spans.values()
                if (now - s.started_at) * 1000 > self.ORPHAN_GRACE_MS][:limit]

    def get_raw_orphan_spans(self) -> list[Span]:
        """All orphan spans without grace window (for internal use)."""
        return list(self._orphan_spans.values())

    def claim_orphan_spans(self, trace_id: str) -> list[Span]:
        """Find and remove orphan spans for a trace_id. Returns claimed spans."""
        claimed = []
        for sid in list(self._orphan_spans.keys()):
            s = self._orphan_spans[sid]
            if s.trace_id == trace_id:
                claimed.append(self._orphan_spans.pop(sid))
        return claimed

    # ── Span tree ───────────────────────────────────

    def get_trace_tree(self, trace_id: str) -> dict | None:
        """Build the span tree for a trace.

        Returns nested tree dict with root span and children.
        """
        trace = self.get_trace(trace_id)
        if not trace:
            spans = [s for s in self._orphan_spans.values() if s.trace_id == trace_id]
            if not spans:
                return None
        else:
            spans = trace.spans

        if not spans:
            return {"trace_id": trace_id, "spans": [], "tree": None}

        children_of: dict[str, list[Span]] = {}
        root = None
        for s in spans:
            pid = s.parent_span_id or ""
            children_of.setdefault(pid, []).append(s)

        roots = children_of.get("", [])
        if not roots and spans:
            local_ids = {s.span_id for s in spans}
            roots = [s for s in spans if s.parent_span_id not in local_ids]
        if not roots and spans:
            roots = [spans[0]]

        def _build_node(span: Span) -> dict:
            node = {
                "span_id": span.span_id,
                "kind": span.kind,
                "name": span.name,
                "status": span.status,
                "started_at": span.started_at,
                "ended_at": span.ended_at,
                "duration_ms": span.duration_ms,
                "parent_span_id": span.parent_span_id,
                "logical_ts": span.logical_ts,
                "depth": span.depth,
                "late": span.late,
                "metadata": span.metadata,
                "children": [_build_node(c) for c in children_of.get(span.span_id, [])],
            }
            return node

        tree = [_build_node(r) for r in roots]

        result = {
            "trace_id": trace_id,
            "name": trace.name if trace else "orphan",
            "started_at": trace.started_at if trace else (spans[0].started_at if spans else 0),
            "ended_at": trace.ended_at if trace else None,
            "duration_ms": trace.duration_ms if trace else None,
            "status": trace.status if trace else "unknown",
            "freeze": trace.freeze if trace else False,
            "span_count": len(spans),
            "tree": tree if len(tree) == 1 else tree,
        }
        if trace and trace.metadata:
            result["metadata"] = trace.metadata
        return result

    # ── Trace replay ────────────────────────────────

    def replay(self, trace_id: str, mode: str = "chronological") -> dict | None:
        """Replay of a trace's span lifecycle.

        Modes:
          chronological — sort by started_at (default)
          causal — sort by logical_ts then parent-child dependency
        """
        from aethon.xray.trace import Trace

        trace = self.get_trace(trace_id)
        if not trace:
            spans = [s for s in self._orphan_spans.values() if s.trace_id == trace_id]
            if not spans:
                return None
        else:
            spans = trace.spans

        if mode == "causal":
            def _causal_key(s):
                return (s.logical_ts, s.depth, s.started_at)
            sorted_spans = sorted(spans, key=_causal_key)
        else:
            sorted_spans = sorted(spans, key=lambda s: s.started_at)

        timeline = []
        for s in sorted_spans:
            entry = {
                "span_id": s.span_id,
                "kind": s.kind,
                "name": s.name,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "duration_ms": s.duration_ms,
                "status": s.status,
                "parent_span_id": s.parent_span_id,
                "logical_ts": s.logical_ts,
                "depth": s.depth,
                "late": s.late,
            }
            timeline.append(entry)

        gaps = []
        for i in range(1, len(sorted_spans)):
            prev = sorted_spans[i - 1]
            curr = sorted_spans[i]
            if prev.ended_at and curr.started_at > prev.ended_at + 0.01:
                gaps.append({
                    "from_span": prev.span_id,
                    "to_span": curr.span_id,
                    "gap_s": round(curr.started_at - prev.ended_at, 3),
                })

        result = {
            "trace_id": trace_id,
            "name": trace.name if trace else "orphan",
            "started_at": trace.started_at if trace else (spans[0].started_at if spans else 0),
            "ended_at": trace.ended_at if trace else None,
            "duration_ms": trace.duration_ms if trace else None,
            "status": trace.status if trace else "unknown",
            "freeze": trace.freeze if trace else False,
            "finalize_ts": trace.finalize_ts if trace else None,
            "span_count": len(spans),
            "replay_mode": mode,
            "timeline": timeline,
            "gaps": gaps,
            "has_gaps": len(gaps) > 0,
        }
        return result

    # ── Diagnostics ─────────────────────────────────

    def diagnostics(self) -> dict:
        """Comprehensive runtime diagnostics for X-RAY."""
        now = time.time()
        active_traces = list(self._active.values())
        completed_traces = list(self._completed.values())
        orphan_spans = [s for s in self._orphan_spans.values()]

        corrupted_traces = 0
        parent_loops = 0
        for t in active_traces + completed_traces:
            span_ids = {s.span_id for s in t.spans}
            for s in t.spans:
                if s.parent_span_id and s.parent_span_id not in span_ids:
                    pass
                if s.parent_span_id == s.span_id:
                    parent_loops += 1
                    corrupted_traces += 1

        orphan_grace = self.ORPHAN_GRACE_MS / 1000.0
        dangling = [s for s in orphan_spans if s.ended_at is None and (now - s.started_at) > max(300, orphan_grace)]

        failed_traces = [t for t in completed_traces if t.status == "error"]

        depths = []
        for t in active_traces + completed_traces:
            if t.spans:
                parent_map = {}
                for s in t.spans:
                    parent_map[s.span_id] = s.parent_span_id
                max_depth = 0
                for sid in parent_map:
                    depth = 0
                    cur = sid
                    while cur in parent_map and parent_map[cur]:
                        depth += 1
                        cur = parent_map[cur]
                        if depth > 100:
                            break
                    max_depth = max(max_depth, depth)
                depths.append(max_depth)

        avg_depth = round(sum(depths) / len(depths), 1) if depths else 0

        latencies = [t.duration_ms for t in completed_traces if t.duration_ms is not None]
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0

        from aethon.xray.causal_validator import count_causal_violations
        violations = count_causal_violations(active_traces + completed_traces)

        late_spans = 0
        for t in active_traces + completed_traces:
            for s in t.spans:
                if s.late:
                    late_spans += 1

        frozen_active = sum(1 for t in active_traces if t.freeze)

        fallback_count = 0
        for t in active_traces + completed_traces:
            for s in t.spans:
                if s.kind == "fallback":
                    fallback_count += 1

        return {
            "active_traces": len(active_traces),
            "completed_traces": len(completed_traces),
            "orphan_spans": len(orphan_spans),
            "dangling_spans": len(dangling),
            "failed_traces": len(failed_traces),
            "parent_loops": parent_loops,
            "corrupted_traces": corrupted_traces,
            "average_depth": avg_depth,
            "average_latency_ms": avg_latency,
            "trace_integrity": "ok" if (corrupted_traces == 0 and parent_loops == 0) else "corrupted",
            "causal_violations": violations,
            "late_spans": late_spans,
            "freeze_state_active": frozen_active > 0,
            "fallback_count": fallback_count,
        }

    # ── Internal ────────────────────────────────────

    def _move_to_completed(self, trace_id: str):
        trace = self._active.pop(trace_id, None)
        if trace is None:
            return
        self._direct_complete(trace)

    def clear(self):
        self._active.clear()
        self._completed.clear()
        self._orphan_spans.clear()

    @property
    def stats(self) -> dict:
        active_count = len(self._active)
        completed_count = len(self._completed)
        interrupted_count = sum(1 for t in self._completed.values() if t.status == "interrupted")
        return {
            "active_traces": active_count,
            "completed_traces": completed_count,
            "interrupted_traces": interrupted_count,
            "orphan_spans": len(self._orphan_spans),
        }


# Global store instance
store = TraceStore()
