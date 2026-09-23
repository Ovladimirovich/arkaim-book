"""
TimeAwareCache — ин-мемори кэш с TTL и автоматической инвалидацией.

Поддерживает:
- TTL (time-to-live) для каждого ключа
- Максимальный размер кэша (LRU eviction)
- Статистику попаданий/промахов
- Thread-safe операции (asyncio.Lock)
"""

import time
import asyncio
import logging
from typing import Any, Optional
from dataclasses import dataclass, field

log = logging.getLogger("hermes.cache")


@dataclass
class _CacheEntry:
    value: Any
    created_at: float
    ttl: float
    access_count: int = 0
    last_accessed: float = 0.0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl

    def touch(self) -> None:
        self.access_count += 1
        self.last_accessed = time.time()


class TimeAwareCache:
    """
    Ин-мемори кэш с TTL.

    Usage:
        cache = TimeAwareCache(default_ttl=300, max_size=100)
        await cache.set("key", value)
        value = await cache.get("key")
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 256) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша. Возвращает None при промахе или истечении TTL."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            entry.touch()
            self._stats["hits"] += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Сохранить значение в кэш с опциональным TTL."""
        async with self._lock:
            # Evict LRU if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            self._cache[key] = _CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl or self._default_ttl,
            )

    async def invalidate(self, key: str) -> bool:
        """Удалить ключ из кэша. Возвращает True если ключ существовал."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Очистить весь кэш."""
        async with self._lock:
            self._cache.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    async def get_or_set(self, key: str, factory, ttl: Optional[int] = None) -> Any:
        """Получить из кэша или создать через factory и сохранить."""
        value = await self.get(key)
        if value is not None:
            return value
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        await self.set(key, value, ttl)
        return value

    def _evict_lru(self) -> None:
        """Удалить наименее используемую запись."""
        if not self._cache:
            return
        # Find entry with lowest access_count (or oldest if tied)
        worst_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].access_count, self._cache[k].created_at)
        )
        del self._cache[worst_key]
        self._stats["evictions"] += 1

    @property
    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "size": len(self._cache),
            "hit_rate": f"{self._stats['hits']/total*100:.1f}%" if total > 0 else "N/A",
        }

    def __len__(self) -> int:
        return len(self._cache)


# ── Готовые кэши для проекта ──────────────────────────────

# Кэш для genome данных (TTL 10 минут)
genome_cache = TimeAwareCache(default_ttl=600, max_size=16)

# Кэш для enriched chunks (TTL 10 минут)
chunks_cache = TimeAwareCache(default_ttl=600, max_size=8)

# Кэш для World Model (TTL 5 минут)
world_model_cache = TimeAwareCache(default_ttl=300, max_size=4)

# Кэш для API ответов (TTL 1 минута)
api_cache = TimeAwareCache(default_ttl=60, max_size=128)

# Кэш для RAG запросов (TTL 2 минуты)
rag_cache = TimeAwareCache(default_ttl=120, max_size=64)
