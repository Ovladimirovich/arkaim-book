"""Performance — оптимизация производительности World Explorer.

Реализует архитектура World Explorer: Этап 13 — Производительность.

Компоненты:
1. LRU-кэш для частых запросов (эпохи, гипотезы, возможности)
2. Батчевая обработка (параллельная оценка ветвей)
3. Оптимизация запросов к БД
4. Метрики производительности
"""

import time
import logging
from collections import OrderedDict
from typing import Optional, Any, Callable
from functools import wraps

log = logging.getLogger("hermes.narrative.performance")


class LRUCache:
    """Простой LRU-кэш с ограничением по размеру и TTL."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl_seconds:
                self._cache.move_to_end(key)
                self._hits += 1
                return value
            else:
                # Истёк TTL
                del self._cache[key]

        self._misses += 1
        return None

    def set(self, key: str, value: Any):
        """Сохранить значение в кэш."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, time.time())

        # Удаляем старые записи при превышении размера
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str):
        """Удалить запись из кэша."""
        self._cache.pop(key, None)

    def clear(self):
        """Очистить весь кэш."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> dict:
        """Статистика кэша."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
        }


# Глобальные кэши
_epochs_cache = LRUCache(max_size=50, ttl_seconds=600)
_hypotheses_cache = LRUCache(max_size=200, ttl_seconds=300)
_possibilities_cache = LRUCache(max_size=200, ttl_seconds=300)
_compatibility_cache = LRUCache(max_size=500, ttl_seconds=60)


def get_cache_stats() -> dict:
    """Получить статистику всех кэшей."""
    return {
        "epochs": _epochs_cache.stats,
        "hypotheses": _hypotheses_cache.stats,
        "possibilities": _possibilities_cache.stats,
        "compatibility": _compatibility_cache.stats,
    }


def clear_all_caches():
    """Очистить все кэши."""
    _epochs_cache.clear()
    _hypotheses_cache.clear()
    _possibilities_cache.clear()
    _compatibility_cache.clear()


def cached_epochs(func: Callable) -> Callable:
    """Декоратор для кэширования результатов по эпохам."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f"epochs:{hash(str(args) + str(kwargs))}"
        result = _epochs_cache.get(key)
        if result is not None:
            log.debug("cache_hit key=%s", key)
            return result

        result = await func(*args, **kwargs)
        _epochs_cache.set(key, result)
        return result
    return wrapper


def cached_hypotheses(func: Callable) -> Callable:
    """Декоратор для кэширования гипотез."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f"hypotheses:{hash(str(args) + str(kwargs))}"
        result = _hypotheses_cache.get(key)
        if result is not None:
            log.debug("cache_hit key=%s", key)
            return result

        result = await func(*args, **kwargs)
        _hypotheses_cache.set(key, result)
        return result
    return wrapper


def cached_possibilities(func: Callable) -> Callable:
    """Декоратор для кэширования возможностей."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f"possibilities:{hash(str(args) + str(kwargs))}"
        result = _possibilities_cache.get(key)
        if result is not None:
            log.debug("cache_hit key=%s", key)
            return result

        result = await func(*args, **kwargs)
        _possibilities_cache.set(key, result)
        return result
    return wrapper


def cached_compatibility(func: Callable) -> Callable:
    """Декоратор для кэширования проверок совместимости."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        key = f"compat:{hash(str(args) + str(kwargs))}"
        result = _compatibility_cache.get(key)
        if result is not None:
            log.debug("cache_hit key=%s", key)
            return result

        result = await func(*args, **kwargs)
        _compatibility_cache.set(key, result)
        return result
    return wrapper


# ── Батчевая обработка ────────────────────────────────────

async def batch_evaluate(
    items: list,
    evaluate_func: Callable,
    max_concurrent: int = 5,
) -> list:
    """Параллельная оценка списка элементов.

    Args:
        items: Список элементов для оценки
        evaluate_func: Функция оценки (async)
        max_concurrent: Максимальное количество параллельных задач
    """
    import asyncio

    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def process_item(item):
        async with semaphore:
            return await evaluate_func(item)

    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Фильтруем исключения
    valid_results = []
    for result in results:
        if not isinstance(result, Exception):
            valid_results.append(result)
        else:
            log.warning("batch_evaluate_error error=%s", result)

    return valid_results


# ── Метрики производительности ─────────────────────────────

class PerformanceMetrics:
    """Сбор метрик производительности."""

    def __init__(self):
        self._metrics: dict[str, list[float]] = {}

    def record(self, metric_name: str, duration_ms: float):
        """Записать метрику."""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append(duration_ms)

        # Ограничиваем историю
        if len(self._metrics[metric_name]) > 1000:
            self._metrics[metric_name] = self._metrics[metric_name][-500:]

    def get_stats(self, metric_name: str) -> dict:
        """Получить статистику по метрике."""
        if metric_name not in self._metrics:
            return {"count": 0, "avg_ms": 0, "min_ms": 0, "max_ms": 0}

        values = self._metrics[metric_name]
        return {
            "count": len(values),
            "avg_ms": round(sum(values) / len(values), 2),
            "min_ms": round(min(values), 2),
            "max_ms": round(max(values), 2),
        }

    def get_all_stats(self) -> dict:
        """Получить статистику по всем метрикам."""
        return {name: self.get_stats(name) for name in self._metrics}

    def clear(self):
        """Очистить все метрики."""
        self._metrics.clear()


# Глобальный экземпляр метрик
metrics = PerformanceMetrics()


def timed(metric_name: str):
    """Декоратор для измерения времени выполнения."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            metrics.record(metric_name, duration_ms)
            log.debug("timed metric=%s duration=%.2fms", metric_name, duration_ms)
            return result
        return wrapper
    return decorator
