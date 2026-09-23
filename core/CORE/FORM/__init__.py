"""Form Library — библиотека форм для визуализации мира."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("hermes.form_library")

FORM_DIR = Path(__file__).resolve().parent


class FormLibrary:
    """Библиотека форм для визуализации мира.
    
    Содержит 11 JSON-файлов:
    - architecture.json — архитектурные стили
    - clothes.json — одежда
    - faces.json — лица
    - body_language.json — жесты и позы
    - weather.json — погода
    - sounds.json — звуки (описания)
    - textures.json — текстуры
    - lighting.json — освещение
    - materials.json — материалы
    - colors.json — цветовые палитры
    - rituals.json — ритуалы
    """
    
    def __init__(self, form_dir: Path | None = None):
        self._dir = form_dir or FORM_DIR
        self._data: dict[str, list[dict]] = {}
        self._load_all()
    
    def _load_all(self):
        """Загрузить все JSON-файлы из FORM/."""
        if not self._dir.exists():
            log.warning("form_dir_not_found path=%s", self._dir)
            return
        
        for json_file in self._dir.glob("*.json"):
            category = json_file.stem.lower()
            try:
                data = json.loads(json_file.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    self._data[category] = data
                    log.info("form_loaded category=%s items=%d", category, len(data))
            except Exception as e:
                log.error("form_load_error file=%s error=%s", json_file, e)
    
    def get_category(self, category: str) -> list[dict]:
        """Получить все формы категории."""
        return self._data.get(category.lower(), [])
    
    def get_form(self, category: str, form_id: str) -> Optional[dict]:
        """Получить форму по ID."""
        items = self.get_category(category)
        for item in items:
            if item.get("id") == form_id:
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
                visual_prompt = item.get("visual_prompt", "").lower()
                if query_lower in name or query_lower in description or query_lower in visual_prompt:
                    results.append({
                        "category": category,
                        **item,
                    })
        
        return results
    
    def get_categories(self) -> list[str]:
        """Получить список всех категорий."""
        return list(self._data.keys())
    
    def get_stats(self) -> dict:
        """Статистика библиотеки."""
        stats = {
            "total_categories": len(self._data),
            "total_forms": sum(len(items) for items in self._data.values()),
            "by_category": {cat: len(items) for cat, items in self._data.items()},
        }
        return stats
    
    def summary(self) -> str:
        """Текстовая сводка."""
        stats = self.get_stats()
        parts = [f"{count} {cat}" for cat, count in stats["by_category"].items()]
        return (
            f"Библиотека форм: {stats['total_forms']} форм в "
            f"{stats['total_categories']} категориях ({', '.join(parts)})"
        )


# ── Фабрика ────────────────────────────────────────────────────

_form_library_cache: Optional[FormLibrary] = None

def get_form_library() -> FormLibrary:
    """Получить singleton FormLibrary."""
    global _form_library_cache
    if _form_library_cache is None:
        _form_library_cache = FormLibrary()
    return _form_library_cache

def invalidate_form_library():
    """Сбросить кэш."""
    global _form_library_cache
    _form_library_cache = None

