"""X-RAY Lite — universal observability kernel for AETHON.

Runtime-agnostic, transport-agnostic, provider-agnostic.
Can observe any system, not only AETHON.
"""

from aethon.xray.event import Event, emit
from aethon.xray.trace import Trace, get_current_trace_id, set_current_trace_id, start_trace
from aethon.xray.trace_store import TraceStore, SpanTreeNode, store
from aethon.xray.span import Span, SpanKind, start_span
from aethon.xray.http_propagation import (
    extract_xray_headers,
    make_xray_headers,
    make_xray_headers_raw,
    fastapi_extract_xray,
    HEADER_TRACE_ID,
    HEADER_SPAN_ID,
    HEADER_PARENT_SPAN_ID,
    HEADER_LOGICAL_TS,
    HEADER_CAUSAL_DEPTH,
)
from aethon.xray.manual_scenarios import run_scenario, scenario_a_normal, scenario_b_failure_fallback, scenario_c_parallel_chaos
from aethon.xray.metrics import (
    Counter,
    Gauge,
    Histogram,
    provider_failures,
    provider_latency,
    fallback_count,
    requests_total,
    requests_failed,
)
from aethon.xray.diagnostics import (
    DiagnosticResult,
    TransportFailure,
    ProviderInstability,
    DeadComponent,
    HighLatency,
    check_transport,
    check_provider_stability,
    check_dead_component,
    check_latency,
    detect_orphan_spans,
    run_all_checks,
)
from aethon.xray.causal_validator import (
    detect_time_violations,
    detect_parent_child_order_violations,
    detect_orphan_over_time,
    detect_out_of_order_spans,
    validate_trace_causal_integrity,
    count_causal_violations,
)
from aethon.xray.consistency_audit import (
    compare_live_vs_disk_trace,
    detect_missing_spans,
    detect_duplicate_span_ids,
    detect_orphan_after_restart,
    validate_trace_reconstruction_equivalence,
    run_all_audit_checks,
)
from aethon.xray.data_sanitizer import (
    scan_duplicate_span_ids,
    repair_duplicate_span_ids,
    orphan_cleanup_pass,
    corrupted_trace_registry,
)
from aethon.xray.retention import (
    TraceRetentionPolicy,
    run_retention_policy,
    cleanup_by_age,
    cleanup_by_count,
    cleanup_by_size,
    cleanup_quarantine,
    _compute_storage_stats,
)
from aethon.xray.control_plane.dto import (
    SpanNodeDTO,
    TraceSummaryDTO,
    TraceDetailDTO,
    ReplayFrameDTO,
    AuditCheckDTO,
    AuditResultDTO,
    HealthMetricsDTO,
)
from aethon.xray.control_plane.normalizer import (
    trace_to_summary,
    trace_to_detail,
    span_to_replay_frame,
    replay_entry_to_frame,
    audit_checks_to_result,
    raw_stats_to_health_metrics,
)
from aethon.xray.version import VERSION, SPEC_VERSION, DTO_VERSION, EVENT_TAXONOMY_VERSION, API_VERSION
from aethon.xray.contracts import (
    EventSchema,
    TraceSchema,
    SpanSchema,
    MetricSchema,
    ComponentKind,
    EventKind,
    Severity,
)

__all__ = [
    "VERSION", "SPEC_VERSION", "DTO_VERSION", "EVENT_TAXONOMY_VERSION", "API_VERSION",
    "TraceStore", "SpanTreeNode", "store",
    "Event", "emit",
    "Trace", "start_trace", "get_current_trace_id", "set_current_trace_id",
    "Span", "SpanKind", "start_span",
    "extract_xray_headers", "make_xray_headers", "make_xray_headers_raw",
    "fastapi_extract_xray",
    "HEADER_TRACE_ID", "HEADER_SPAN_ID", "HEADER_PARENT_SPAN_ID",
    "HEADER_LOGICAL_TS", "HEADER_CAUSAL_DEPTH",
    "run_scenario", "scenario_a_normal", "scenario_b_failure_fallback", "scenario_c_parallel_chaos",
    "compare_live_vs_disk_trace", "detect_missing_spans",
    "detect_duplicate_span_ids", "detect_orphan_after_restart",
    "validate_trace_reconstruction_equivalence", "run_all_audit_checks",
    "Counter", "Gauge", "Histogram",
    "provider_failures", "provider_latency", "fallback_count",
    "requests_total", "requests_failed",
    "DiagnosticResult", "TransportFailure", "ProviderInstability",
    "DeadComponent", "HighLatency",
    "check_transport", "check_provider_stability", "check_dead_component",
    "check_latency", "detect_orphan_spans", "run_all_checks",
    "detect_time_violations", "detect_parent_child_order_violations",
    "detect_orphan_over_time", "detect_out_of_order_spans",
    "validate_trace_causal_integrity", "count_causal_violations",
    "scan_duplicate_span_ids", "repair_duplicate_span_ids",
    "orphan_cleanup_pass", "corrupted_trace_registry",
    # Retention
    "TraceRetentionPolicy", "run_retention_policy",
    "cleanup_by_age", "cleanup_by_count", "cleanup_by_size",
    "cleanup_quarantine", "_compute_storage_stats",
    # Control Plane DTOs
    "SpanNodeDTO", "TraceSummaryDTO", "TraceDetailDTO",
    "ReplayFrameDTO", "AuditCheckDTO", "AuditResultDTO", "HealthMetricsDTO",
    # Control Plane Normalizers
    "trace_to_summary", "trace_to_detail",
    "span_to_replay_frame", "replay_entry_to_frame",
    "audit_checks_to_result", "raw_stats_to_health_metrics",
]
