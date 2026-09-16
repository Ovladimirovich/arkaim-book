"""
ProviderRegistry — реестр LLM-провайдеров с circuit breaker.

Thread-safe: использует asyncio.Lock для критических секций.
Rolling window: ошибки сгорают через PROVIDER_COOLDOWN_SECONDS.
"""
import asyncio
import time
from typing import Optional

from core.config import settings
from core.providers.base import BaseProvider
from core.logging import log


class _CircuitBreakerState:
    """Состояние circuit breaker для одного провайдера."""

    __slots__ = ("failure_count", "cooldown_until", "last_failure_time")

    def __init__(self):
        self.failure_count: int = 0
        self.cooldown_until: float = 0.0
        self.last_failure_time: float = 0.0

    def is_open(self) -> bool:
        """Circuit breaker открыт (провайдер недоступен)?"""
        if self.cooldown_until == 0.0:
            return False
        if time.time() >= self.cooldown_until:
            # Cooldown истёк — сбрасываем
            self.cooldown_until = 0.0
            self.failure_count = 0
            return False
        return True

    def record_failure(self, threshold: int, cooldown_seconds: int) -> bool:
        """Записать ошибку. Возвращает True если circuit breaker открылся."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= threshold:
            self.cooldown_until = time.time() + cooldown_seconds
            return True
        return False

    def record_success(self) -> int:
        """Записать успех. Возвращает количество сброшенных ошибок."""
        prev = self.failure_count
        self.failure_count = 0
        self.cooldown_until = 0.0
        return prev


class ProviderRegistry:
    """Реестр провайдеров с thread-safe circuit breaker."""

    _providers: dict[str, type[BaseProvider]] = {}
    _frozen: bool = False
    _health_state: dict[str, _CircuitBreakerState] = {}
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseProvider]):
        if cls._frozen:
            raise RuntimeError("Provider registry is frozen after startup")
        cls._providers[name] = provider_cls
        cls._health_state[name] = _CircuitBreakerState()
        log.info("provider_registered name=%s", name)

    @classmethod
    def select_provider(cls, requested: Optional[str] = None) -> str:
        """Выбирает провайдера с поддержкой A/B тестирования."""
        try:
            from core.providers.ab_testing import ab_selector
            return ab_selector.select_provider(requested)
        except ImportError:
            if requested and requested in cls._providers:
                return requested
            return settings.PROVIDER_CHAIN[0]

    @classmethod
    def reset(cls):
        cls._frozen = False
        cls._providers = {}
        cls._health_state = {}
        cls._lock = None

    @classmethod
    def freeze(cls):
        cls._frozen = True
        log.info("provider_registry_frozen providers=%s", list(cls._providers))

    @classmethod
    def get(cls, name: str) -> BaseProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        return cls._providers[name]()

    @classmethod
    def chain(cls, requested: str) -> list[str]:
        if requested in cls._providers:
            chain = [requested]
        else:
            chain = []
        for name in settings.PROVIDER_CHAIN:
            if name not in chain and name in cls._providers:
                chain.append(name)
        return chain

    @classmethod
    def all(cls) -> dict[str, type[BaseProvider]]:
        return dict(cls._providers)

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._providers

    @classmethod
    def is_healthy(cls, name: str) -> bool:
        """Проверяет здоровье провайдера (без lock — быстрый путь)."""
        if name not in cls._health_state:
            return True
        return not cls._health_state[name].is_open()

    @classmethod
    def report_failure(cls, name: str):
        """Записать ошибку провайдера."""
        if name not in cls._health_state:
            return
        state = cls._health_state[name]
        opened = state.record_failure(
            threshold=settings.PROVIDER_FAILURE_THRESHOLD,
            cooldown_seconds=settings.PROVIDER_COOLDOWN_SECONDS,
        )
        if opened:
            log.warning(
                "circuit_breaker_open provider=%s failures=%d cooldown=%ds",
                name, state.failure_count, settings.PROVIDER_COOLDOWN_SECONDS,
            )

    @classmethod
    def report_success(cls, name: str):
        """Записать успех провайдера."""
        if name not in cls._health_state:
            return
        prev = cls._health_state[name].record_success()
        if prev > 0:
            log.info("circuit_breaker_close provider=%s previous_failures=%d", name, prev)

    @classmethod
    def chain_healthy(cls, requested: str) -> list[str]:
        return [name for name in cls.chain(requested) if cls.is_healthy(name)]

    @classmethod
    async def health(cls) -> list[dict]:
        results = []
        for name, p_cls in cls._providers.items():
            try:
                provider = p_cls()
                status = await provider.health()
                status["name"] = name
                status["healthy"] = cls.is_healthy(name)
                results.append(status)
            except Exception as exc:
                results.append({"name": name, "status": "error", "error": str(exc), "healthy": cls.is_healthy(name)})
        return results

    # ── Async-safe методы (для использования в orchestrator) ──

    @classmethod
    async def areport_failure(cls, name: str):
        """Async-версия report_failure с lock."""
        async with cls._get_lock():
            cls.report_failure(name)

    @classmethod
    async def areport_success(cls, name: str):
        """Async-версия report_success с lock."""
        async with cls._get_lock():
            cls.report_success(name)

    @classmethod
    async def achain_healthy(cls, requested: str) -> list[str]:
        """Async-версия chain_healthy с lock."""
        async with cls._get_lock():
            return cls.chain_healthy(requested)

    @classmethod
    async def list_all_models(cls) -> list[dict]:
        all_models = []
        for name, p_cls in cls._providers.items():
            try:
                provider = p_cls()
                models = await provider.list_models()
                for model in models:
                    model["id"] = f"{name}/{model.get('id', name)}"
                    model["provider"] = name
                all_models.extend(models)
            except Exception as exc:
                log.warning("provider_list_models_failed provider=%s error=%s", name, exc)
                all_models.append({"id": name, "object": "model", "owned_by": name, "status": "unavailable", "error": str(exc)})
        return all_models

    @classmethod
    async def get_provider_models(cls, name: str) -> list[dict]:
        if name not in cls._providers:
            return []
        try:
            provider = cls.get(name)
            return await provider.list_models()
        except Exception as exc:
            log.warning("provider_list_models_failed provider=%s error=%s", name, exc)
            return [{"id": name, "object": "model", "owned_by": name, "status": "unavailable", "error": str(exc)}]
