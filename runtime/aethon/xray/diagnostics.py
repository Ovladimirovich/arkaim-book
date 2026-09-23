"""System diagnostics — rule-based, no AI logic.

Each check returns a DiagnosticResult with severity and description.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from aethon.xray.contracts import Severity


@dataclass
class DiagnosticResult:
    name: str
    passed: bool
    severity: Severity = Severity.INFO
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity.value if isinstance(self.severity, Severity) else self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class TransportFailure(DiagnosticResult):
    pass


@dataclass
class ProviderInstability(DiagnosticResult):
    pass


@dataclass
class DeadComponent(DiagnosticResult):
    pass


@dataclass
class HighLatency(DiagnosticResult):
    pass


def check_transport(
    host: str,
    port: int,
    timeout: float = 3.0,
    name: str = "transport_check",
) -> TransportFailure:
    """Check if a TCP host:port is reachable."""
    import socket
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return TransportFailure(name=name, passed=True, severity=Severity.INFO, message=f"{host}:{port} reachable")
    except (OSError, socket.timeout) as exc:
        return TransportFailure(
            name=name, passed=False, severity=Severity.ERROR,
            message=f"{host}:{port} unreachable",
            details={"host": host, "port": port, "error": str(exc)},
        )


def check_provider_stability(
    failure_count: int,
    threshold: int = 3,
    window_seconds: float = 300.0,
    provider_name: str = "unknown",
    name: str = "provider_stability",
) -> ProviderInstability:
    """Check if a provider has failed too many times in the window."""
    unstable = failure_count >= threshold
    if unstable:
        return ProviderInstability(
            name=name, passed=False, severity=Severity.WARNING,
            message=f"Provider {provider_name} unstable: {failure_count} failures in {window_seconds}s",
            details={"provider": provider_name, "failures": failure_count, "threshold": threshold, "window": window_seconds},
        )
    return ProviderInstability(name=name, passed=True, severity=Severity.INFO, message=f"Provider {provider_name} stable")


def check_dead_component(
    last_seen: float,
    timeout_seconds: float = 60.0,
    component_name: str = "unknown",
    name: str = "dead_component",
) -> DeadComponent:
    """Check if a component has stopped reporting."""
    now = time.time()
    dead = (now - last_seen) > timeout_seconds
    if dead:
        return DeadComponent(
            name=name, passed=False, severity=Severity.CRITICAL,
            message=f"Component {component_name} dead: not seen for {now - last_seen:.0f}s",
            details={"component": component_name, "last_seen": last_seen, "timeout": timeout_seconds},
        )
    return DeadComponent(name=name, passed=True, severity=Severity.INFO, message=f"Component {component_name} alive")


def check_latency(
    avg_latency_ms: float,
    threshold_ms: float = 5000.0,
    component_name: str = "unknown",
    name: str = "high_latency",
) -> HighLatency:
    """Check if average latency exceeds threshold."""
    high = avg_latency_ms > threshold_ms
    if high:
        return HighLatency(
            name=name, passed=False, severity=Severity.WARNING,
            message=f"High latency on {component_name}: {avg_latency_ms:.0f}ms (threshold {threshold_ms}ms)",
            details={"component": component_name, "avg_latency": avg_latency_ms, "threshold": threshold_ms},
        )
    return HighLatency(name=name, passed=True, severity=Severity.INFO, message=f"Latency normal on {component_name}")


def detect_orphan_spans(
    store=None,
    max_span_age_seconds: float = 300.0,
    name: str = "orphan_spans",
) -> DiagnosticResult:
    """Detect orphan spans — spans without valid trace or parent."""
    if store is None:
        from aethon.xray.trace_store import store
    orphans = store.get_orphan_spans()
    active_traces = store.get_active_traces()

    details = {
        "orphan_count": len(orphans),
        "active_trace_count": len(active_traces),
        "completed_trace_count": store.stats.get("completed_traces", 0),
        "orphan_spans": [{"span_id": s.span_id, "trace_id": s.trace_id, "name": s.name, "kind": s.kind, "age_s": round(time.time() - s.started_at, 1) if s.ended_at is None else None} for s in orphans[:20]],
    }

    # Check for dangling active spans
    dangling = []
    now = time.time()
    for s in orphans:
        if s.ended_at is None and (now - s.started_at) > max_span_age_seconds:
            dangling.append({"span_id": s.span_id, "name": s.name, "age_s": round(now - s.started_at, 1)})

    details["dangling_spans"] = dangling
    details["dangling_count"] = len(dangling)

    # Check for incomplete traces
    incomplete = []
    for t in active_traces:
        age = now - t.started_at
        if age > max_span_age_seconds:
            incomplete.append({"trace_id": t.trace_id, "name": t.name, "age_s": round(age, 1), "span_count": len(t.spans)})

    details["incomplete_traces"] = incomplete
    details["incomplete_count"] = len(incomplete)

    passed = len(orphans) == 0 and len(dangling) == 0 and len(incomplete) == 0
    severity = Severity.INFO if passed else (Severity.WARNING if len(orphans) < 10 else Severity.ERROR)
    return DiagnosticResult(
        name=name, passed=passed, severity=severity,
        message=f"Orphan spans: {len(orphans)} orphan, {len(dangling)} dangling, {len(incomplete)} incomplete traces",
        details=details,
    )


def run_all_checks(
    transport_targets: list[tuple[str, int, float]] | None = None,
    provider_failures: dict[str, int] | None = None,
    component_last_seen: dict[str, float] | None = None,
    component_latency: dict[str, float] | None = None,
    **kwargs,
) -> list[DiagnosticResult]:
    """Run all diagnostic checks and return results."""
    results: list[DiagnosticResult] = []

    if transport_targets:
        for host, port, timeout in transport_targets:
            results.append(check_transport(host, port, timeout))

    if provider_failures:
        for name, count in provider_failures.items():
            results.append(check_provider_stability(count, provider_name=name))

    if component_last_seen:
        for name, last_seen in component_last_seen.items():
            results.append(check_dead_component(last_seen, component_name=name))

    if component_latency:
        for name, latency in component_latency.items():
            results.append(check_latency(latency, component_name=name))

    return results
