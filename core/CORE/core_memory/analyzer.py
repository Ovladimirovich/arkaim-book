"""MemoryAnalyzer — заглушка для обратной совместимости."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes.memory.analyzer")


class MemoryAnalyzer:
    """Простой анализатор паттернов в данных."""

    def __init__(self):
        self._events: List[Dict[str, Any]] = []

    def record(self, event: Dict[str, Any]) -> None:
        self._events.append(event)

    def get_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._events[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        return {"total_events": len(self._events)}


class XRayObserver:
    """Заглушка XRayObserver для обратной совместимости."""

    def __init__(self):
        self._traces: List[Dict[str, Any]] = []

    def observe(self, trace: Dict[str, Any]) -> None:
        self._traces.append(trace)

    def get_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._traces[-limit:]

    def analyze(self) -> Dict[str, Any]:
        return {"total_traces": len(self._traces)}
