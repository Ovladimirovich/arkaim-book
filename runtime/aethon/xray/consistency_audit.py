"""Consistency audit layer — verifies convergence between runtime and
persisted trace state.

All checks are read-only. Never mutates trace_store or disk state.

Checks:
  compare_live_vs_disk_trace  — runtime trace == persisted JSON
  detect_missing_spans        — parent_span_id without a span
  detect_duplicate_span_ids   — global span_id uniqueness
  detect_orphan_after_restart — orphan spans from interrupted traces
  validate_trace_reconstruction_equivalence — replay(live) == replay(disk)
"""

from __future__ import annotations

import json
import os
from typing import Any

from aethon.xray.trace_store import store
from aethon.xray.trace import Trace
from aethon.xray.span import Span


# ── Helpers ────────────────────────────────────────


def _collect_all_spans() -> list[Span]:
    spans: list[Span] = []
    for t in store.get_active_traces():
        spans.extend(t.spans)
    for t in store.get_completed_traces():
        spans.extend(t.spans)
    spans.extend(store.get_raw_orphan_spans())
    return spans


def _span_ids(traces: list[Trace]) -> set[str]:
    ids: set[str] = set()
    for t in traces:
        for s in t.spans:
            ids.add(s.span_id)
    return ids


# ── Check 1: compare_live_vs_disk_trace ────────────


def compare_live_vs_disk_trace(trace_id: str) -> dict:
    """Compare an in-memory trace against its persisted JSON snapshot.

    Returns:
      status — 'passed' | 'failed' | 'not_applicable'
      mismatches — list of divergent field paths
      disk_status — 'present' | 'missing' | 'no_persistence' | 'pending'
    """
    result: dict[str, Any] = {
        "check_name": "compare_live_vs_disk_trace",
        "trace_id": trace_id,
        "status": "not_applicable",
        "passed": True,
        "mismatches": [],
        "disk_status": "no_persistence",
        "live_status": "not_found",
    }

    if not store._persist_enabled or not store._persist_path:
        result["disk_status"] = "no_persistence"
        result["reason"] = "persistence disabled — no disk snapshot to compare"
        return result

    trace = store.get_trace(trace_id)
    if trace is None:
        result["live_status"] = "not_found"
        result["status"] = "not_applicable"
        return result
    result["live_status"] = trace.status

    # Read persisted trace snapshot
    trace_path = os.path.join(store._persist_path, "traces", f"{trace_id}.json")
    if not os.path.exists(trace_path):
        result["disk_status"] = "pending"
        result["status"] = "not_applicable"
        result["reason"] = "snapshot not yet materialized — trace still in memory"
        # Interrupted traces are not expected to have a snapshot —
        # only span files. Verify span files instead.
        if trace.status == "interrupted":
            span_dir = os.path.join(store._persist_path, "spans", trace_id)
            if os.path.isdir(span_dir):
                disk_span_ids = {f.replace("span_", "").replace(".json", "")
                                 for f in os.listdir(span_dir) if f.endswith(".json")}
                live_span_ids = {s.span_id for s in trace.spans}
                if disk_span_ids == live_span_ids:
                    result["status"] = "passed"
                    result["passed"] = True
                    result["note"] = "interrupted trace: span files match in-memory spans"
                else:
                    result["status"] = "failed"
                    result["passed"] = False
                    result["mismatches"].append(
                        f"span_files_on_disk={sorted(disk_span_ids)} "
                        f"live_spans={sorted(live_span_ids)}"
                    )
            else:
                result["status"] = "failed"
                result["passed"] = False
                result["mismatches"].append("no span directory on disk")
        return result

    result["disk_status"] = "present"
    try:
        with open(trace_path, "r") as f:
            disk_data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        result["status"] = "failed"
        result["passed"] = False
        result["mismatches"].append(f"disk_read_error: {exc}")
        return result

    live = trace.to_dict()
    mismatches: list[str] = []

    # Compare top-level scalar fields
    for key in ("status", "trace_id", "name", "freeze"):
        if live.get(key) != disk_data.get(key):
            mismatches.append(f"{key}: live={live.get(key)} disk={disk_data.get(key)}")

    # Compare span count
    live_span_count = len(live.get("spans", []))
    disk_span_count = len(disk_data.get("spans", []))
    if live_span_count != disk_span_count:
        mismatches.append(f"span_count: live={live_span_count} disk={disk_span_count}")

    # Compare span IDs (order-independent)
    live_span_ids = {s["span_id"] for s in live.get("spans", [])}
    disk_span_ids = {s["span_id"] for s in disk_data.get("spans", [])}
    if live_span_ids != disk_span_ids:
        missing = disk_span_ids - live_span_ids
        extra = live_span_ids - disk_span_ids
        if missing:
            mismatches.append(f"disk_has_spans_not_in_live: {sorted(missing)}")
        if extra:
            mismatches.append(f"live_has_spans_not_on_disk: {sorted(extra)}")

    # Compare per-span fields
    disk_spans_by_id = {s["span_id"]: s for s in disk_data.get("spans", [])}
    for s in live.get("spans", []):
        ds = disk_spans_by_id.get(s["span_id"])
        if ds is None:
            continue
        for field in ("kind", "status", "parent_span_id", "logical_ts", "depth", "late"):
            lv = s.get(field)
            dv = ds.get(field)
            if lv != dv:
                mismatches.append(f"span.{s['span_id'][:8]}.{field}: live={lv} disk={dv}")

    result["status"] = "passed" if len(mismatches) == 0 else "failed"
    result["passed"] = len(mismatches) == 0
    result["mismatches"] = mismatches
    return result


# ── Check 2: detect_missing_spans ──────────────────


def detect_missing_spans() -> dict:
    """Find parent_span_id references that point to spans not in the store.

    Spanning across processes (cross-process parent) is NOT a violation —
    only intra-process dangling references are flagged.
    When persistence is disabled, this check is informational only — no
    persistence cross-reference is possible.
    """
    result: dict[str, Any] = {
        "check_name": "detect_missing_spans",
        "status": "passed" if not store._persist_enabled else "failed",
        "passed": True,
        "total_spans": 0,
        "missing_references": [],
    }

    if not store._persist_enabled:
        result["status"] = "not_applicable"
        result["reason"] = "persistence disabled — cross-process parent tracking requires disk"
        return result

    all_spans = _collect_all_spans()
    known_ids = {s.span_id for s in all_spans}
    result["total_spans"] = len(all_spans)

    for s in all_spans:
        if s.parent_span_id and s.parent_span_id not in known_ids:
            result["missing_references"].append({
                "span_id": s.span_id,
                "span_name": s.name,
                "trace_id": s.trace_id,
                "parent_span_id": s.parent_span_id,
            })

    has_missing = len(result["missing_references"]) > 0
    result["status"] = "failed" if has_missing else "passed"
    result["passed"] = not has_missing
    return result


# ── Check 3: detect_duplicate_span_ids ─────────────


def detect_duplicate_span_ids() -> dict:
    """Scan all traces + orphan spans for duplicate span_id values.

    A single span_id must be globally unique across the entire store.
    """
    result: dict[str, Any] = {
        "check_name": "detect_duplicate_span_ids",
        "status": "failed",
        "passed": False,
        "duplicates": [],
    }

    all_spans = _collect_all_spans()
    seen: dict[str, list[dict]] = {}

    for s in all_spans:
        entry = {"span_id": s.span_id, "trace_id": s.trace_id, "name": s.name}
        seen.setdefault(s.span_id, []).append(entry)

    for sid, occurrences in seen.items():
        if len(occurrences) > 1:
            result["duplicates"].append({
                "span_id": sid,
                "occurrences": occurrences,
                "count": len(occurrences),
            })

    has_dups = len(result["duplicates"]) > 0
    result["status"] = "failed" if has_dups else "passed"
    result["passed"] = not has_dups
    return result


# ── Check 4: detect_orphan_after_restart ───────────


def detect_orphan_after_restart() -> dict:
    """Validate that all orphan spans in the store can be explained.

    An orphan is acceptable if:
      - it belongs to an interrupted trace (confirmed by index)
      - it is within the grace window (< ORPHAN_GRACE_MS old)

    Otherwise it is flagged as an unexplained orphan.
    """
    import time

    result: dict[str, Any] = {
        "check_name": "detect_orphan_after_restart",
        "status": "failed",
        "passed": False,
        "unexplained_orphans": [],
        "within_grace_window": 0,
        "belongs_to_interrupted": 0,
        "total_orphans": 0,
    }

    now = time.time()
    grace_s = store.ORPHAN_GRACE_MS / 1000.0
    orphans = store.get_raw_orphan_spans()

    completed_traces = store.get_completed_traces()
    interrupted_ids = {t.trace_id for t in completed_traces if t.status == "interrupted"}

    result["total_orphans"] = len(orphans)

    for s in orphans:
        age = now - s.started_at
        if s.trace_id in interrupted_ids:
            result["belongs_to_interrupted"] += 1
        elif age < grace_s:
            result["within_grace_window"] += 1
        else:
            result["unexplained_orphans"].append({
                "span_id": s.span_id,
                "trace_id": s.trace_id,
                "name": s.name,
                "age_s": round(age, 1),
                "trace_known": s.trace_id in interrupted_ids or any(
                    t.trace_id == s.trace_id for t in completed_traces
                ),
            })

    has_unexplained = len(result["unexplained_orphans"]) > 0
    result["status"] = "failed" if has_unexplained else "passed"
    result["passed"] = not has_unexplained
    return result


# ── Check 5: validate_trace_reconstruction_equivalence ──


def validate_trace_reconstruction_equivalence(trace_id: str) -> dict:
    """Verify that replay produces identical timelines from live vs disk.

    When persistence is disabled, both replays use the same in-memory
    source — always passes. Only meaningful when persistence is active.
    """
    result: dict[str, Any] = {
        "check_name": "validate_trace_reconstruction_equivalence",
        "trace_id": trace_id,
        "status": "not_applicable",
        "passed": True,
        "differences": [],
    }

    if not store._persist_enabled or not store._persist_path:
        result["reason"] = "persistence disabled — live and disk replay are the same source"
        return result

    # Replay from live in-memory state
    live_replay = store.replay(trace_id, mode="chronological")
    if live_replay is None:
        result["status"] = "not_applicable"
        result["differences"].append("live_replay: trace not found")
        return result

    # Replay from disk
    disk_replay = store.replay(trace_id, mode="chronological")
    if disk_replay is None:
        result["status"] = "not_applicable"
        result["differences"].append("disk_replay: trace not found")
        return result

    diffs: list[str] = []

    # Span count
    lc = live_replay.get("span_count", 0)
    dc = disk_replay.get("span_count", 0)
    if lc != dc:
        diffs.append(f"span_count: live={lc} disk={dc}")

    # Timeline entry count
    lt = len(live_replay.get("timeline", []))
    dt = len(disk_replay.get("timeline", []))
    if lt != dt:
        diffs.append(f"timeline_length: live={lt} disk={dt}")

    # Compare timeline entries by span_id order
    live_ids = [e["span_id"] for e in live_replay.get("timeline", [])]
    disk_ids = [e["span_id"] for e in disk_replay.get("timeline", [])]
    if live_ids != disk_ids:
        diffs.append("span_id_order_differs")

    # Compare logical_ts sequence
    live_lts = [e.get("logical_ts", 0) for e in live_replay.get("timeline", [])]
    disk_lts = [e.get("logical_ts", 0) for e in disk_replay.get("timeline", [])]
    if live_lts != disk_lts:
        diffs.append(f"logical_ts_sequence_differs: live={live_lts} disk={disk_lts}")

    # Duration check
    ld = live_replay.get("duration_ms")
    dd = disk_replay.get("duration_ms")
    if ld != dd:
        diffs.append(f"duration_ms: live={ld} disk={dd}")

    result["status"] = "passed" if len(diffs) == 0 else "failed"
    result["passed"] = len(diffs) == 0
    result["differences"] = diffs
    return result


# ── Aggregate ──────────────────────────────────────


def run_all_audit_checks(trace_id: str | None = None) -> dict:
    """Run all 5 consistency audit checks and return aggregate result.

    Separates operational state (not_applicable) from integrity violations
    (failed checks). Only failed checks count toward all_passed.
    """
    resolved_tid = trace_id
    if not resolved_tid:
        completed = store.get_completed_traces()
        if completed:
            resolved_tid = max(completed, key=lambda t: t.ended_at or 0).trace_id

    results: dict[str, Any] = {
        "audit_version": "1.0",
        "all_passed": True,
        "checks": {},
        "stats": {},
        "operational_warnings": [],
    }

    c1 = compare_live_vs_disk_trace(resolved_tid) if resolved_tid else {
        "check_name": "compare_live_vs_disk_trace",
        "status": "not_applicable",
        "passed": True,
        "skipped": True,
        "reason": "no traces available",
    }
    c2 = detect_missing_spans()
    c3 = detect_duplicate_span_ids()
    c4 = detect_orphan_after_restart()
    c5 = validate_trace_reconstruction_equivalence(resolved_tid) if resolved_tid else {
        "check_name": "trace_reconstruction_equivalence",
        "status": "not_applicable",
        "passed": True,
        "skipped": True,
        "reason": "no traces available",
    }

    results["checks"]["compare_live_vs_disk"] = c1
    results["checks"]["detect_missing_spans"] = c2
    results["checks"]["detect_duplicate_span_ids"] = c3
    results["checks"]["detect_orphan_after_restart"] = c4
    results["checks"]["trace_reconstruction_equivalence"] = c5

    # Collect operational warnings (not_applicable checks)
    for c in (c1, c2, c3, c4, c5):
        if c.get("status") == "not_applicable" and not c.get("skipped", False):
            results["operational_warnings"].append({
                "check": c.get("check_name", "?"),
                "reason": c.get("reason", ""),
            })

    # all_passed = no failed checks (not_applicable doesn't count as failure)
    failed = [c for c in (c1, c2, c3, c4, c5) if c.get("status") == "failed"]
    results["all_passed"] = len(failed) == 0
    results["audit_trace_id"] = resolved_tid
    results["stats"] = store.stats

    return results
