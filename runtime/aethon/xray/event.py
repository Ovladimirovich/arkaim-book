"""Standardized runtime event — the atomic unit of X-RAY observability."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from aethon.xray.contracts import ComponentKind, EventKind, EventSchema, Severity

log = logging.getLogger("aethon.xray.event")


@dataclass
class Event:
    """A single observability event. Immutable after creation."""
    timestamp: float
    trace_id: str
    component: ComponentKind | str
    event: EventKind | str
    severity: Severity = Severity.INFO
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self._frozen = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "component": self.component.value if isinstance(self.component, ComponentKind) else self.component,
            "event": self.event.value if isinstance(self.event, EventKind) else self.event,
            "severity": self.severity.value if isinstance(self.severity, Severity) else self.severity,
            "message": self.message,
            "metadata": self.metadata,
        }

    def to_schema(self) -> EventSchema:
        return EventSchema(
            timestamp=self.timestamp,
            trace_id=self.trace_id,
            component=self.component,
            event=self.event,
            severity=self.severity,
            message=self.message,
            metadata=self.metadata,
        )


# Module-level emission state
_emission_enabled = True
_emission_handlers: list[callable] = []


def disable_emission():
    global _emission_enabled
    _emission_enabled = False


def enable_emission():
    global _emission_enabled
    _emission_enabled = True


def add_handler(handler: callable):
    _emission_handlers.append(handler)


def remove_handler(handler: callable):
    _emission_handlers.remove(handler)


def emit(event: Event):
    if not _emission_enabled:
        return
    level = event.severity.value if isinstance(event.severity, Severity) else event.severity
    log.log(
        _severity_to_log_level(level),
        "[%s] [%s] [%s] %s",
        event.component.value if isinstance(event.component, ComponentKind) else event.component,
        event.trace_id[:8] if event.trace_id else "-",
        event.event.value if isinstance(event.event, EventKind) else event.event,
        event.message or json.dumps(event.metadata, ensure_ascii=False),
    )
    for handler in _emission_handlers:
        try:
            handler(event)
        except Exception:
            pass


def make_event(
    trace_id: str,
    component: ComponentKind | str,
    event: EventKind | str,
    severity: Severity = Severity.INFO,
    message: str = "",
    metadata: dict | None = None,
) -> Event:
    return Event(
        timestamp=time.time(),
        trace_id=trace_id,
        component=component,
        event=event,
        severity=severity,
        message=message,
        metadata=metadata or {},
    )


def _severity_to_log_level(severity: str) -> int:
    mapping = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    return mapping.get(severity, logging.INFO)
