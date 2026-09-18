"""
A/B тестирование провайдеров LLM.
Позволяет распределять нагрузку между GigaChat и OpenRouter
для объективного сравнения качества, скорости и стоимости.
"""
import random
import time
from typing import Optional, List, Dict

from core.config import settings
from core.provider_registry import ProviderRegistry
from core.logging import log

# ── Тип для хранения результата A/B теста ──────────────────────────
class ABTestResult:
    """Результат одного A/B запроса."""

    def __init__(
        self,
        provider: str,
        selected_by: str,  # 'chain' | 'ab_test' | 'requested'
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
    ):
        self.provider = provider
        self.selected_by = selected_by
        self.latency_ms = latency_ms
        self.success = success
        self.error = error
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "selected_by": self.selected_by,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


# ── A/B селектор провайдеров ──────────────────────────────────────
class ProviderABSelector:
    """
    Селектор провайдеров с поддержкой A/B тестирования.

    Режимы работы:
    1. 'chain' — оригинальное поведение: fallback chain по PROVIDER_CHAIN
    2. 'ab_test' — случайное распределение с весом A/B
    3. 'latency_aware' — выбирает провайдера с наименьшей исторической latency

    Конфигурация через .env:
      PROVIDER_AB_TEST_ENABLED=false
      PROVIDER_AB_TEST_A=gigachat
      PROVIDER_AB_TEST_B=openrouter
      PROVIDER_AB_TEST_PERCENTAGE=50  (процент запросов на провайдер B)
    """

    def __init__(self):
        self._latency_history: Dict[str, List[float]] = {}
        self._max_history = 100  # храним последние 100 замеров на провайдера

    @property
    def mode(self) -> str:
        """Определяет режим работы: chain | ab_test | latency_aware."""
        if not hasattr(settings, 'PROVIDER_AB_TEST_ENABLED'):
            return 'chain'
        enabled = str(getattr(settings, 'PROVIDER_AB_TEST_ENABLED', 'false')).lower()
        if enabled in ('1', 'true'):
            return 'ab_test'
        return 'chain'

    @property
    def provider_a(self) -> str:
        """Провайдер A (контрольная группа)."""
        return getattr(settings, 'PROVIDER_AB_TEST_A', 'gigachat')

    @property
    def provider_b(self) -> str:
        """Провайдер B (экспериментальная группа)."""
        return getattr(settings, 'PROVIDER_AB_TEST_B', 'openrouter')

    @property
    def b_percentage(self) -> int:
        """Процент запросов на провайдер B (0-100)."""
        try:
            return int(getattr(settings, 'PROVIDER_AB_TEST_PERCENTAGE', '50'))
        except (ValueError, TypeError):
            return 50

    def select_provider(self, requested: Optional[str] = None) -> str:
        """
        Выбирает провайдера на основе режима.

        Args:
            requested: Запрошенный провайдер (если указан, используется он).

        Returns:
            Имя выбранного провайдера.
        """
        # Если провайдер явно запрошен — используем его
        if requested and ProviderRegistry.is_registered(requested):
            return requested

        mode = self.mode

        if mode == 'chain':
            # Оригинальное поведение: первый из PROVIDER_CHAIN
            return settings.PROVIDER_CHAIN[0]

        if mode == 'latency_aware':
            return self._select_latency_aware()

        # A/B тестирование
        return self._select_ab()

    def _select_ab(self) -> str:
        """A/B случайный выбор."""
        if not ProviderRegistry.is_registered(self.provider_b):
            return self.provider_a
        if not ProviderRegistry.is_registered(self.provider_a):
            return self.provider_b

        if random.randint(1, 100) <= self.b_percentage:
            log.debug("ab_test_select provider=%s (B)", self.provider_b)
            return self.provider_b
        log.debug("ab_test_select provider=%s (A)", self.provider_a)
        return self.provider_a

    def _select_latency_aware(self) -> str:
        """Выбирает провайдера с наименьшей средней latency."""
        available = [n for n in [self.provider_a, self.provider_b] if ProviderRegistry.is_registered(n)]
        if not available:
            return settings.PROVIDER_CHAIN[0]
        if len(available) == 1:
            return available[0]

        # Сравниваем среднюю latency
        def avg_latency(name: str) -> float:
            history = self._latency_history.get(name, [])
            if not history:
                return float('inf')
            return sum(history[-20:]) / min(len(history[-20:]), 20)

        best = min(available, key=avg_latency)
        log.debug("latency_aware_select provider=%s (best latency)", best)
        return best

    def record_latency(self, provider: str, latency_ms: float):
        """Записывает latency провайдера для latency_aware режима."""
        if provider not in self._latency_history:
            self._latency_history[provider] = []
        self._latency_history[provider].append(latency_ms)
        # Ограничиваем историю
        if len(self._latency_history[provider]) > self._max_history:
            self._latency_history[provider] = self._latency_history[provider][-self._max_history:]

    def get_stats(self) -> dict:
        """Возвращает статистику A/B тестирования."""
        return {
            "mode": self.mode,
            "provider_a": self.provider_a,
            "provider_b": self.provider_b,
            "b_percentage": self.b_percentage,
            "latency_history": {
                name: {
                    "count": len(history),
                    "avg_ms": sum(history) / len(history) if history else 0,
                    "min_ms": min(history) if history else 0,
                    "max_ms": max(history) if history else 0,
                }
                for name, history in self._latency_history.items()
            },
        }


# Singleton
ab_selector = ProviderABSelector()
