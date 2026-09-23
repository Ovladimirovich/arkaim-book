"""Canonical event taxonomy & runtime counters.

Events:
  chat_started        — request received by orchestrator
  chat_ok             — provider returned response successfully
  chat_failed         — all providers exhausted
  provider_selected   — which provider chosen from chain
  provider_failed     — provider raised (before circuit breaker)
  fallback_triggered  — switching to next provider in chain
  identity_repair     — identity leak detected and sanitized
  memory_hit          — memory retrieved relevant context
  memory_store        — conversation stored to memory
  skill_executed      — skill ran (handled or not)
"""
import threading


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}

    def increment(self, name: str, count: int = 1):
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + count

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self):
        with self._lock:
            self._counters.clear()


metrics = Metrics()
