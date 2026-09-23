"""Контекст выполнения BOOK OS — трассировка запросов."""

import uuid
from contextvars import ContextVar
from typing import Optional

_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


class TraceContext:
    """Контекст трассировки для цепочки вызовов OS."""

    @staticmethod
    def get_trace_id() -> Optional[str]:
        return _trace_id.get()

    @staticmethod
    def set_trace_id(trace_id: str) -> None:
        _trace_id.set(trace_id)

    @staticmethod
    def generate() -> str:
        return uuid.uuid4().hex[:16]


def trace_context(operation: str = "os_call"):
    """Контекстный менеджер трассировки.

    with trace_context("get_entity"):
        provider.get_entity("Велик")
    """
    class _TraceContextManager:
        def __enter__(self):
            self.old_trace = TraceContext.get_trace_id()
            new_trace = TraceContext.generate()
            TraceContext.set_trace_id(new_trace)
            return new_trace

        def __exit__(self, *args):
            if self.old_trace:
                TraceContext.set_trace_id(self.old_trace)
            else:
                TraceContext.set_trace_id(None)

    return _TraceContextManager()
