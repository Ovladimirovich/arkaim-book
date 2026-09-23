"""Retention policy engine for X-RAY trace persistence.

Provides configurable cleanup of trace snapshots and span files
based on age, count, and storage limits. Frozen traces are
preserved. Active traces are never touched.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TraceRetentionPolicy:
    """Configurable retention policy for persisted traces.

    A trace is eligible for cleanup when ALL applicable limits
    are exceeded. Frozen traces are always exempt.
    """

    max_days: int = 30
    max_traces: int = 1000
    max_storage_mb: int = 500
    orphan_ttl_hours: int = 24
    quarantine_ttl_days: int = 7
    archive_before_delete: bool = True
    skip_frozen: bool = True
    skip_active: bool = True
    skip_interrupted: bool = False

    def to_dict(self) -> dict:
        return {
            "max_days": self.max_days,
            "max_traces": self.max_traces,
            "max_storage_mb": self.max_storage_mb,
            "orphan_ttl_hours": self.orphan_ttl_hours,
            "quarantine_ttl_days": self.quarantine_ttl_days,
            "archive_before_delete": self.archive_before_delete,
            "skip_frozen": self.skip_frozen,
            "skip_active": self.skip_active,
            "skip_interrupted": self.skip_interrupted,
        }


def _load_trace_snapshot(path: str) -> dict | None:
    """Load a trace snapshot JSON from disk."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _trace_mtime(path: str) -> float:
    """Get modification time of a trace snapshot file."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _collect_trace_snapshots(persist_path: str) -> list[dict]:
    """Collect all trace snapshot files with metadata.

    Returns list of dicts:
      {path, trace_id, mtime, size_bytes, status, freeze, age_days}
    """
    traces_dir = os.path.join(persist_path, "traces")
    if not os.path.isdir(traces_dir):
        return []

    now = time.time()
    results: list[dict] = []
    for fname in os.listdir(traces_dir):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(traces_dir, fname)
        trace_id = fname[:-5]
        mtime = _trace_mtime(path)
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        info = _load_trace_snapshot(path)
        status = (info or {}).get("status", "unknown")
        freeze = (info or {}).get("freeze", False)
        age_days = (now - mtime) / 86400.0 if mtime else 0.0
        span_count = len((info or {}).get("spans", []))
        results.append({
            "path": path,
            "trace_id": trace_id,
            "mtime": mtime,
            "size_bytes": size,
            "status": status,
            "freeze": freeze,
            "age_days": age_days,
            "span_count": span_count,
        })
    return results


def _span_dir_size(persist_path: str, trace_id: str) -> int:
    """Compute total size of span files for a trace."""
    span_dir = os.path.join(persist_path, "spans", trace_id)
    if not os.path.isdir(span_dir):
        return 0
    total = 0
    for root, _dirs, files in os.walk(span_dir):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _delete_trace_files(persist_path: str, trace_id: str) -> dict:
    """Delete trace snapshot + span directory for a trace.

    Returns dict with counts of deleted items.
    """
    result = {"snapshot": False, "span_dir": False}
    snapshot_path = os.path.join(persist_path, "traces", f"{trace_id}.json")
    if os.path.isfile(snapshot_path):
        try:
            os.remove(snapshot_path)
            result["snapshot"] = True
        except OSError:
            pass
    span_dir = os.path.join(persist_path, "spans", trace_id)
    if os.path.isdir(span_dir):
        try:
            shutil.rmtree(span_dir)
            result["span_dir"] = True
        except OSError:
            pass
    return result


def _archive_trace_files(persist_path: str, trace_id: str) -> str | None:
    """Archive a trace's snapshot + span files to a zip.

    Returns the archive path, or None on failure.
    """
    archive_dir = os.path.join(persist_path, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(archive_dir, f"{trace_id}_{ts}.zip")

    snapshot_path = os.path.join(persist_path, "traces", f"{trace_id}.json")
    span_dir = os.path.join(persist_path, "spans", trace_id)

    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(snapshot_path):
                zf.write(snapshot_path, f"trace_{trace_id}.json")
            if os.path.isdir(span_dir):
                for root, _dirs, files in os.walk(span_dir):
                    for f in files:
                        fpath = os.path.join(root, f)
                        arcname = os.path.relpath(fpath, os.path.dirname(persist_path))
                        zf.write(fpath, arcname)
        return archive_path
    except OSError:
        return None


def _compute_storage_stats(persist_path: str) -> dict:
    """Compute storage usage stats for the trace store.

    Returns dict with trace_snapshots_mb, span_files_mb,
    archive_mb, quarantine_mb, total_mb, trace_count, span_count.
    """
    trace_bytes = 0
    span_bytes = 0
    archive_bytes = 0
    quarantine_bytes = 0

    traces_dir = os.path.join(persist_path, "traces")
    if os.path.isdir(traces_dir):
        for fname in os.listdir(traces_dir):
            fpath = os.path.join(traces_dir, fname)
            if os.path.isfile(fpath):
                try:
                    trace_bytes += os.path.getsize(fpath)
                except OSError:
                    pass

    spans_dir = os.path.join(persist_path, "spans")
    if os.path.isdir(spans_dir):
        for root, _dirs, files in os.walk(spans_dir):
            for f in files:
                try:
                    span_bytes += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

    archive_dir = os.path.join(persist_path, "archive")
    if os.path.isdir(archive_dir):
        for root, _dirs, files in os.walk(archive_dir):
            for f in files:
                try:
                    archive_bytes += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

    quarantine_dir = os.path.join(persist_path, "quarantine")
    if os.path.isdir(quarantine_dir):
        for root, _dirs, files in os.walk(quarantine_dir):
            for f in files:
                try:
                    quarantine_bytes += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass

    trace_count = len([f for f in os.listdir(traces_dir) if f.endswith(".json")]) if os.path.isdir(traces_dir) else 0
    span_count = 0
    if os.path.isdir(spans_dir):
        for root, _dirs, files in os.walk(spans_dir):
            span_count += len([f for f in files if f.endswith(".json")])

    to_mb = lambda b: round(b / (1024 * 1024), 2)
    return {
        "trace_snapshots_mb": to_mb(trace_bytes),
        "span_files_mb": to_mb(span_bytes),
        "archive_mb": to_mb(archive_bytes),
        "quarantine_mb": to_mb(quarantine_bytes),
        "total_mb": to_mb(trace_bytes + span_bytes + archive_bytes + quarantine_bytes),
        "trace_count": trace_count,
        "span_count": span_count,
    }


def cleanup_by_age(
    persist_path: str,
    policy: TraceRetentionPolicy,
    dry_run: bool = True,
) -> dict:
    """Delete/archive traces older than max_days.

    Skips frozen and active traces per policy.
    """
    snapshots = _collect_trace_snapshots(persist_path)
    deleted: list[str] = []
    archived: list[str] = []
    skipped_frozen: list[str] = []
    skipped_active: list[str] = []
    errors: list[str] = []

    for snap in snapshots:
        trace_id = snap["trace_id"]
        if snap["freeze"] and policy.skip_frozen:
            skipped_frozen.append(trace_id)
            continue
        if snap["status"] == "active" and policy.skip_active:
            skipped_active.append(trace_id)
            continue
        if snap["age_days"] < policy.max_days:
            continue

        if dry_run:
            deleted.append(trace_id)
            continue

        if policy.archive_before_delete:
            path = _archive_trace_files(persist_path, trace_id)
            if path:
                archived.append(trace_id)
            else:
                errors.append(f"{trace_id}:archive_failed")

        _delete_trace_files(persist_path, trace_id)
        deleted.append(trace_id)

    return {
        "pass": "cleanup_by_age",
        "max_days": policy.max_days,
        "dry_run": dry_run,
        "deleted_count": len(deleted),
        "deleted_ids": deleted[:20],
        "archived_count": len(archived),
        "skipped_frozen": len(skipped_frozen),
        "skipped_active": len(skipped_active),
        "errors": errors,
        "archived_ids": archived[:10],
    }


def cleanup_by_count(
    persist_path: str,
    policy: TraceRetentionPolicy,
    dry_run: bool = True,
) -> dict:
    """Keep at most max_traces snapshots, delete oldest.

    Skips frozen and active traces per policy.
    """
    snapshots = _collect_trace_snapshots(persist_path)
    eligible = [s for s in snapshots if not (s["freeze"] and policy.skip_frozen) and not (s["status"] == "active" and policy.skip_active)]
    eligible.sort(key=lambda s: s["mtime"])
    keep = policy.max_traces

    deleted: list[str] = []
    archived: list[str] = []
    skipped_frozen: int = sum(1 for s in snapshots if s["freeze"])
    skipped_active: int = sum(1 for s in snapshots if s["status"] == "active" and not s["freeze"])

    if len(eligible) <= keep:
        return {
            "pass": "cleanup_by_count",
            "max_traces": policy.max_traces,
            "dry_run": dry_run,
            "deleted_count": 0,
            "archived_count": 0,
            "skipped_frozen": skipped_frozen,
            "skipped_active": skipped_active,
            "total_eligible": len(eligible),
            "errors": [],
        }

    to_remove = eligible[: len(eligible) - keep]
    for snap in to_remove:
        trace_id = snap["trace_id"]
        if dry_run:
            deleted.append(trace_id)
            continue

        if policy.archive_before_delete:
            path = _archive_trace_files(persist_path, trace_id)
            if path:
                archived.append(trace_id)

        _delete_trace_files(persist_path, trace_id)
        deleted.append(trace_id)

    return {
        "pass": "cleanup_by_count",
        "max_traces": policy.max_traces,
        "dry_run": dry_run,
        "deleted_count": len(deleted),
        "deleted_ids": deleted[:20],
        "archived_count": len(archived),
        "skipped_frozen": skipped_frozen,
        "skipped_active": skipped_active,
        "total_eligible": len(eligible),
        "errors": [],
    }


def cleanup_by_size(
    persist_path: str,
    policy: TraceRetentionPolicy,
    dry_run: bool = True,
) -> dict:
    """Keep total storage under max_storage_mb.

    If exceeded, deletes oldest eligible traces
    (with archive) until under the limit.
    """
    stats = _compute_storage_stats(persist_path)
    usable_mb = stats["trace_snapshots_mb"] + stats["span_files_mb"]
    if usable_mb <= policy.max_storage_mb:
        return {
            "pass": "cleanup_by_size",
            "max_storage_mb": policy.max_storage_mb,
            "current_usable_mb": usable_mb,
            "dry_run": dry_run,
            "deleted_count": 0,
            "archived_count": 0,
            "errors": [],
        }

    snapshots = _collect_trace_snapshots(persist_path)
    eligible = [s for s in snapshots if not (s["freeze"] and policy.skip_frozen) and not (s["status"] == "active" and policy.skip_active)]
    eligible.sort(key=lambda s: s["mtime"])

    deleted: list[str] = []
    archived: list[str] = []
    freed_mb = 0.0
    target_freed = usable_mb - policy.max_storage_mb

    for snap in eligible:
        if freed_mb >= target_freed:
            break
        trace_id = snap["trace_id"]
        snap_mb = snap["size_bytes"] / (1024 * 1024)
        span_mb = _span_dir_size(persist_path, trace_id) / (1024 * 1024)

        if dry_run:
            deleted.append(trace_id)
            freed_mb += snap_mb + span_mb
            continue

        if policy.archive_before_delete:
            path = _archive_trace_files(persist_path, trace_id)
            if path:
                archived.append(trace_id)

        _delete_trace_files(persist_path, trace_id)
        deleted.append(trace_id)
        freed_mb += snap_mb + span_mb

    return {
        "pass": "cleanup_by_size",
        "max_storage_mb": policy.max_storage_mb,
        "current_usable_mb": usable_mb,
        "target_freed_mb": round(target_freed, 2),
        "freed_mb": round(freed_mb, 2),
        "dry_run": dry_run,
        "deleted_count": len(deleted),
        "deleted_ids": deleted[:20],
        "archived_count": len(archived),
        "errors": [],
    }


def cleanup_quarantine(persist_path: str, policy: TraceRetentionPolicy, dry_run: bool = True) -> dict:
    """Remove quarantined traces older than quarantine_ttl_days."""
    quarantine_dir = os.path.join(persist_path, "quarantine")
    if not os.path.isdir(quarantine_dir):
        return {"pass": "cleanup_quarantine", "deleted_count": 0, "dry_run": dry_run, "errors": [], "deleted_ids": []}

    now = time.time()
    deleted: list[str] = []
    for entry in os.listdir(quarantine_dir):
        entry_path = os.path.join(quarantine_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        try:
            mtime = os.path.getmtime(entry_path)
            age_days = (now - mtime) / 86400.0
        except OSError:
            continue
        if age_days < policy.quarantine_ttl_days:
            continue
        if dry_run:
            deleted.append(entry)
            continue
        try:
            shutil.rmtree(entry_path)
            deleted.append(entry)
        except OSError:
            pass

    return {
        "pass": "cleanup_quarantine",
        "ttl_days": policy.quarantine_ttl_days,
        "dry_run": dry_run,
        "deleted_count": len(deleted),
        "deleted_ids": deleted[:20],
        "errors": [],
    }


def run_retention_policy(
    persist_path: str,
    policy: TraceRetentionPolicy | None = None,
    dry_run: bool = True,
) -> dict:
    """Run all retention policy passes and return aggregate results."""
    if policy is None:
        policy = TraceRetentionPolicy()

    results: dict[str, Any] = {
        "policy": policy.to_dict(),
        "dry_run": dry_run,
        "storage_before": _compute_storage_stats(persist_path),
        "passes": [],
    }

    results["passes"].append(cleanup_by_age(persist_path, policy, dry_run=dry_run))
    results["passes"].append(cleanup_by_count(persist_path, policy, dry_run=dry_run))
    results["passes"].append(cleanup_by_size(persist_path, policy, dry_run=dry_run))
    results["passes"].append(cleanup_quarantine(persist_path, policy, dry_run=dry_run))

    total_deleted = sum(p.get("deleted_count", 0) for p in results["passes"])
    total_archived = sum(p.get("archived_count", 0) for p in results["passes"])

    results["total_deleted"] = total_deleted
    results["total_archived"] = total_archived
    results["storage_after"] = _compute_storage_stats(persist_path) if not dry_run else results["storage_before"]

    return results
