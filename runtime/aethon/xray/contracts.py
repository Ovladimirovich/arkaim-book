"""Frozen schemas and interfaces for X-RAY Lite.

No runtime imports allowed — only stdlib, typing, dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComponentKind(str, Enum):
    GATEWAY = "gateway"
    CORE = "core"
    PROVIDER = "provider"
    TELEGRAM = "telegram"
    MEMORY = "memory"
    SKILLS = "skills"
    CONTROL_CENTER = "control_center"
    XRAY = "xray"
    UNKNOWN = "unknown"


class EventKind(str, Enum):
    PROVIDER_CALL = "provider_call"
    PROVIDER_FAILED = "provider_failed"
    PROVIDER_FALLBACK = "provider_fallback"
    GATEWAY_REQUEST = "gateway_request"
    GATEWAY_RATE_LIMIT = "gateway_rate_limit"
    CORE_ORCHESTRATE = "core_orchestrate"
    TELEGRAM_UPDATE = "telegram_update"
    TELEGRAM_SEND = "telegram_send"
    MEMORY_ACCESS = "memory_access"
    SKILL_EXECUTION = "skill_execution"
    TRANSPORT_FAILURE = "transport_failure"
    HEALTH_CHECK = "health_check"
    CONFIG_CHANGE = "config_change"
    PROCESS_START = "process_start"
    PROCESS_STOP = "process_stop"
    DIAGNOSTIC = "diagnostic"
    CUSTOM = "custom"


class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class EventSchema:
    """Canonical event shape every X-RAY event must match."""
    timestamp: float
    trace_id: str
    component: ComponentKind | str
    event: EventKind | str
    severity: Severity
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceSchema:
    """Canonical trace shape."""
    trace_id: str
    name: str
    started_at: float
    correlation_id: str = ""
    ended_at: float | None = None
    duration_ms: float | None = None
    status: str = "ok"
    spans: list[SpanSchema] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SpanSchema:
    """Canonical span shape."""
    span_id: str
    trace_id: str
    kind: str
    name: str
    started_at: float
    correlation_id: str = ""
    ended_at: float | None = None
    duration_ms: float | None = None
    status: str = "ok"
    parent_span_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricSchema:
    """Canonical metric shape."""
    name: str
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""
