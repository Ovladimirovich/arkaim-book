"""
ServiceRegistry — замена @functools.cache для FastAPI DI.

Хранит单例-экземпляры, создаёт по первому вызову, очищает при shutdown.
"""

import logging
from typing import Any, Callable

log = logging.getLogger("hermes.services")


class ServiceRegistry:
    """Ленивый реестр синглтонов с поддержкой cleanup."""

    def __init__(self):
        self._instances: dict[str, Any] = {}
        self._factories: dict[str, Callable[[], Any]] = {}
        self._cleanups: dict[str, Callable[[Any], None]] = {}

    def register(
        self,
        name: str,
        factory: Callable[[], Any],
        cleanup: Callable[[Any], None] | None = None,
    ):
        """Зарегистрировать фабрику (lazy). Cleanup вызовется при close_all()."""
        self._factories[name] = factory
        if cleanup:
            self._cleanups[name] = cleanup

    def get(self, name: str) -> Any:
        """Получить单例, создать при первом вызове."""
        if name in self._instances:
            return self._instances[name]

        factory = self._factories.get(name)
        if factory is None:
            raise KeyError(f"Service '{name}' not registered")

        instance = factory()
        self._instances[name] = instance
        return instance

    def has(self, name: str) -> bool:
        return name in self._factories

    def close_all(self):
        """Вызвать cleanup для всех созданных экземпляров."""
        for name, instance in self._instances.items():
            cleanup = self._cleanups.get(name)
            if cleanup:
                try:
                    cleanup(instance)
                except Exception as e:
                    log.error("service_cleanup_error name=%s error=%s", name, e)
        self._instances.clear()
        log.info("services_closed count=%d", len(self._instances))


# Глобальный реестр
registry = ServiceRegistry()
