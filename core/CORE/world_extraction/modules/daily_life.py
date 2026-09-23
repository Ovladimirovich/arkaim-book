"""Экстрактор быта мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.daily_life")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_daily_life() -> ExtractionResult:
    """Извлечь данные о быте."""
    items = []
    source_files = []
    
    # 1. Из deep_daily_life.json
    daily_path = KNOWLEDGE_DIR / "deep_daily_life.json"
    if daily_path.exists():
        source_files.append(str(daily_path))
        try:
            data = json.loads(daily_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                # Обрабатываем структуру deep_daily_life.json
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, dict):
                                # Вложенный словарь
                                items.append(WorldKnowledge(
                                    id=f"daily_{key}_{sub_key}",
                                    name=f"{key}: {sub_key}",
                                    name_ru=f"{key}: {sub_key}",
                                    category="daily_life",
                                    description=str(sub_value)[:500],
                                    properties={"type": "daily_life_detail", "category": key},
                                    source="deep_daily_life.json",
                                ))
                            elif isinstance(sub_value, list):
                                # Список
                                items.append(WorldKnowledge(
                                    id=f"daily_{key}_{sub_key}",
                                    name=f"{key}: {sub_key}",
                                    name_ru=f"{key}: {sub_key}",
                                    category="daily_life",
                                    description=str(sub_value)[:500],
                                    properties={"type": "daily_life_list", "category": key},
                                    source="deep_daily_life.json",
                                ))
                    elif isinstance(value, str) and value:
                        items.append(WorldKnowledge(
                            id=f"daily_{key}",
                            name=key,
                            name_ru=key,
                            category="daily_life",
                            description=value[:500],
                            properties={"type": "daily_life_string"},
                            source="deep_daily_life.json",
                        ))
        except Exception as e:
            log.error("daily_life_error: %s", e)
    
    # 2. Из THEMESEXPANDED.json (бытовые темы)
    themes_path = KNOWLEDGE_DIR / "THEMES_EXPANDED.json"
    if themes_path.exists():
        source_files.append(str(themes_path))
        try:
            data = json.loads(themes_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        topic = item.get("topic", "")
                        content = item.get("content", "")
                        if topic and content:
                            items.append(WorldKnowledge(
                                id=f"theme_daily_{topic.lower().replace(' ', '_')}",
                                name=topic,
                                name_ru=topic,
                                category="daily_life",
                                description=content[:500],
                                properties={"source_file": "THEMES_EXPANDED.json"},
                                source="THEMES_EXPANDED.json",
                            ))
        except Exception as e:
            log.error("themes_daily_error: %s", e)
    
    return ExtractionResult(
        category="daily_life",
        items=items,
        source_files=source_files,
    )
