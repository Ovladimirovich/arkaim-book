"""Data sanitizer for X-RAY trace store.

Read-only scans + explicit repair actions.
Never hooks into runtime execution path.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from typing import Any

from aethon.xray.trace_store import store


def scan_duplicate_span_ids() -> dict:
    """Scan all persisted span files for duplicate span_ids.

    Returns report with duplicate groups, their trace_ids, and file paths.
    Read-only — does not modify any data.
    """
    persist_path = store.persist_path
    if not persist_path or not os.path.isdir(persist_path):
        return {"error": "persistence not configured", "duplicates": []}

    spans_base = os.path.join(persist_path, "spans")
    if not os.path.isdir(spans_base):
        return {"spans_directory_missing": True, "duplicates": []}

    seen: dict[str, list[dict]] = {}
    trace_ids_found: set[str] = set()

    for trace_id in os.listdir(spans_base):
        trace_dir = os.path.join(spans_base, trace_id)
        if not os.path.isdir(trace_dir):
            continue
        trace_ids_found.add(trace_id)
        for fname in os.listdir(trace_dir):
            if not fname.startswith("span_") or not fname.endswith(".json"):
                continue
            span_id = fname[5:-5]
            fpath = os.path.join(trace_dir, fname)
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                seen.setdefault(span_id, []).append({
                    "trace_id": trace_id,
                    "file": fpath,
                    "name": "?",
                    "parse_error": True,
                })
                continue
            seen.setdefault(span_id, []).append({
                "trace_id": trace_id,
                "file": fpath,
                "name": data.get("name", "?"),
                "kind": data.get("kind", "?"),
                "status": data.get("status", "?"),
            })

    duplicates = []
    for sid, occurrences in seen.items():
        if len(occurrences) > 1:
            duplicates.append({
                "span_id": sid,
                "occurrence_count": len(occurrences),
                "occurrences": occurrences,
            })

    return {
        "scanned_at": time.time(),
        "total_span_files": sum(len([f for f in os.listdir(os.path.join(spans_base, tid)) if f.endswith(".json")]) for tid in os.listdir(spans_base) if os.path.isdir(os.path.join(spans_base, tid))),
        "total_traces_on_disk": len(trace_ids_found),
        "unique_span_ids": len(seen),
        "duplicate_groups": len(duplicates),
        "duplicates": duplicates,
    }


def repair_duplicate_span_ids(dry_run: bool = True) -> dict:
    """Repair duplicate span_ids by quarantining corrupted traces.

    In dry_run mode (default), only reports what would be done.
    Set dry_run=False to actually quarantine.

    Quarantine moves corrupted trace directories to:
      {persist_path}/quarantine/{trace_id}_{timestamp}/
    """
    scan = scan_duplicate_span_ids()
    if scan.get("error"):
        return scan

    persist_path = store.persist_path
    quarantine_base = os.path.join(persist_path, "quarantine")

    actions = []
    corrupted_trace_ids: set[str] = set()

    for dup in scan.get("duplicates", []):
        for occ in dup.get("occurrences", []):
            tid = occ.get("trace_id")
            if tid:
                corrupted_trace_ids.add(tid)

    for tid in sorted(corrupted_trace_ids):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest_name = f"{tid}_{timestamp}"

        spans_src = os.path.join(persist_path, "spans", tid)
        trace_src = os.path.join(persist_path, "traces", f"{tid}.json")

        if dry_run:
            actions.append({
                "trace_id": tid,
                "action": "quarantine",
                "dry_run": True,
                "spans_dir": spans_src if os.path.isdir(spans_src) else None,
                "trace_file": trace_src if os.path.isfile(trace_src) else None,
            })
            continue

        dest = os.path.join(quarantine_base, dest_name)
        os.makedirs(dest, exist_ok=True)

        moved_spans = False
        if os.path.isdir(spans_src):
            shutil.move(spans_src, os.path.join(dest, "spans"))
            moved_spans = True

        moved_trace = False
        if os.path.isfile(trace_src):
            shutil.move(trace_src, os.path.join(dest, "trace.json"))
            moved_trace = True

        actions.append({
            "trace_id": tid,
            "action": "quarantine",
            "dry_run": False,
            "moved_spans": moved_spans,
            "moved_trace": moved_trace,
            "destination": dest,
        })

    return {
        "repaired_at": time.time(),
        "dry_run": dry_run,
        "corrupted_trace_count": len(corrupted_trace_ids),
        "corrupted_trace_ids": sorted(corrupted_trace_ids),
        "actions": actions,
    }


def orphan_cleanup_pass(ttl_hours: float = 24, dry_run: bool = True) -> dict:
    """Clean up orphan spans older than TTL.

    An orphan is a span file on disk whose trace_id has no completed
    trace snapshot and whose parent trace was never completed.

    In dry_run mode, only reports. Set dry_run=False to delete.
    """
    persist_path = store.persist_path
    if not persist_path or not os.path.isdir(persist_path):
        return {"error": "persistence not configured"}

    spans_base = os.path.join(persist_path, "spans")
    if not os.path.isdir(spans_base):
        return {"orphan_trace_dirs": []}

    traces_dir = os.path.join(persist_path, "traces")
    completed_trace_ids: set[str] = set()
    if os.path.isdir(traces_dir):
        for fname in os.listdir(traces_dir):
            if fname.endswith(".json"):
                completed_trace_ids.add(fname[:-5])

    now = time.time()
    ttl_seconds = ttl_hours * 3600

    orphan_dirs = []
    for trace_id in os.listdir(spans_base):
        trace_dir = os.path.join(spans_base, trace_id)
        if not os.path.isdir(trace_dir):
            continue
        if trace_id in completed_trace_ids:
            continue

        dir_mtime = os.path.getmtime(trace_dir)
        age_seconds = now - dir_mtime
        if age_seconds < ttl_seconds:
            continue

        span_count = len([f for f in os.listdir(trace_dir) if f.endswith(".json")])
        orphan_dirs.append({
            "trace_id": trace_id,
            "age_hours": round(age_seconds / 3600, 1),
            "span_count": span_count,
            "path": trace_dir,
        })

    if not dry_run:
        deleted_count = 0
        for od in orphan_dirs:
            try:
                shutil.rmtree(od["path"])
                od["deleted"] = True
                deleted_count += 1
            except OSError as e:
                od["deleted"] = False
                od["error"] = str(e)

    return {
        "cleaned_at": time.time(),
        "dry_run": dry_run,
        "ttl_hours": ttl_hours,
        "orphan_dirs_found": len(orphan_dirs),
        "orphan_dirs": orphan_dirs,
        "deleted_count": len([o for o in orphan_dirs if o.get("deleted")]) if not dry_run else 0,
    }


def corrupted_trace_registry() -> dict:
    """List all quarantined traces in the quarantine directory."""
    persist_path = store.persist_path
    if not persist_path:
        return {"error": "persistence not configured"}

    quarantine_base = os.path.join(persist_path, "quarantine")
    if not os.path.isdir(quarantine_base):
        return {"quarantine_dir": quarantine_base, "quarantined_traces": []}

    entries = []
    for name in sorted(os.listdir(quarantine_base)):
        entry_path = os.path.join(quarantine_base, name)
        if not os.path.isdir(entry_path):
            continue
        has_spans = os.path.isdir(os.path.join(entry_path, "spans"))
        has_trace = os.path.isfile(os.path.join(entry_path, "trace.json"))
        mtime = os.path.getmtime(entry_path)
        entries.append({
            "name": name,
            "path": entry_path,
            "quarantined_at": mtime,
            "has_spans": has_spans,
            "has_trace": has_trace,
        })

    return {
        "quarantine_dir": quarantine_base,
        "quarantined_count": len(entries),
        "quarantined_traces": entries,
    }
