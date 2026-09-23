"""Расширение WorldModel для загрузки данных из WORLD_MODEL/*.json."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

log = logging.getLogger("hermes.world_model_ext")

# Путь к WORLD_MODEL относительно этого файла
# файл: core/CORE/narrative_engine/world_model_ext.py
# WORLD_MODEL: core/CORE/WORLD_MODEL/
WORLD_MODEL_DIR = Path(__file__).resolve().parent.parent / "WORLD_MODEL"


class WorldModelExt:
    """Расширенная модель мира — загружает данные из WORLD_MODEL/*.json."""
    
    def __init__(self, world_model_dir: Path | None = None):
        self._dir = world_model_dir or WORLD_MODEL_DIR
        self._data: dict[str, list[dict]] = {}
        self._load_all()
    
    def _load_all(self):
        """Загрузить все JSON-файлы из WORLD_MODEL/."""
        if not self._dir.exists():
            log.warning("world_model_dir_not_found path=%s", self._dir)
            return
        
        for json_file in self._dir.glob("*.json"):
            category = json_file.stem.lower()
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._data[category] = data
                    log.info("world_model_loaded category=%s items=%d", category, len(data))
                elif isinstance(data, dict):
                    self._data[category] = [data]
                    log.info("world_model_loaded category=%s items=1", category)
            except Exception as e:
                log.error("world_model_load_error file=%s error=%s", json_file, e)
    
    def get_category(self, category: str) -> list[dict]:
        """Получить все сущности категории."""
        return self._data.get(category.lower(), [])
    
    def get_entity(self, category: str, entity_id: str) -> Optional[dict]:
        """Получить сущность по ID."""
        items = self.get_category(category)
        for item in items:
            if item.get("id") == entity_id:
                return item
        return None
    
    def search(self, query: str) -> list[dict]:
        """Поиск по всем категориям."""
        results = []
        query_lower = query.lower()
        
        for category, items in self._data.items():
            for item in items:
                name = item.get("name", "").lower()
                description = item.get("description", "").lower()
                if query_lower in name or query_lower in description:
                    results.append({
                        "category": category,
                        **item,
                    })
        
        return results
    
    def get_categories(self) -> list[str]:
        """Получить список всех категорий."""
        return list(self._data.keys())
    
    def get_stats(self) -> dict:
        """Статистика модели."""
        stats = {
            "total_categories": len(self._data),
            "total_entities": sum(len(items) for items in self._data.values()),
            "by_category": {cat: len(items) for cat, items in self._data.items()},
        }
        return stats
    
    def summary(self) -> str:
        """Текстовая сводка."""
        stats = self.get_stats()
        parts = [f"{count} {cat}" for cat, count in stats["by_category"].items()]
        return (
            f"Расширенный мир: {stats['total_entities']} сущностей в "
            f"{stats['total_categories']} категориях ({', '.join(parts)})"
        )


# ── Фабрика ────────────────────────────────────────────────────

_world_model_ext_cache: Optional[WorldModelExt] = None

def get_world_model_ext() -> WorldModelExt:
    """Получить singleton WorldModelExt."""
    global _world_model_ext_cache
    if _world_model_ext_cache is None:
        _world_model_ext_cache = WorldModelExt()
    return _world_model_ext_cache

def invalidate_world_model_ext():
    """Сбросить кэш."""
    global _world_model_ext_cache
    _world_model_ext_cache = None
