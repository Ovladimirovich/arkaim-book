"""Экстрактор экономики мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.economy")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_economy() -> ExtractionResult:
    """Извлечь данные об экономике."""
    items = []
    source_files = []
    
    # Ищем в THEMESEXPANDED.json и других файлах
    for filename in ["THEMES_EXPANDED.json", "CROSS_REFERENCES.json", "deep_daily_life.json", "deep_concepts.json"]:
        filepath = KNOWLEDGE_DIR / filename
        if filepath.exists():
            source_files.append(str(filepath))
            try:
                data = json.loads(filepath.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            topic = item.get("topic", "")
                            content = item.get("content", "")
                            if topic and content:
                                # Более широкий поиск
                                econ_keywords = ["торговл", "обмен", "ремесл", "производств", 
                                                "ресурс", "деньги", "ценность", "богатств", "работа",
                                                "труд", "хозяйств", "земледели", "скотовод"]
                                if any(kw in content.lower() for kw in econ_keywords):
                                    items.append(WorldKnowledge(
                                        id=f"econ_{filename}_{topic.lower().replace(' ', '_')}",
                                        name=topic,
                                        name_ru=topic,
                                        category="economy",
                                        description=content[:500],
                                        properties={"source_file": filename},
                                        source=filename,
                                    ))
                elif isinstance(data, dict):
                    # Обрабатываем словари
                    for key, value in data.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if isinstance(sub_value, str) and sub_value:
                                    econ_keywords = ["торговл", "обмен", "ремесл", "производств", 
                                                    "ресурс", "деньги", "ценность", "богатств"]
                                    if any(kw in sub_value.lower() for kw in econ_keywords):
                                        items.append(WorldKnowledge(
                                            id=f"econ_{filename}_{key}_{sub_key}",
                                            name=f"{key}: {sub_key}",
                                            name_ru=f"{key}: {sub_key}",
                                            category="economy",
                                            description=sub_value[:500],
                                            properties={"source_file": filename},
                                            source=filename,
                                        ))
            except Exception as e:
                log.error("economy_extract_error file=%s: %s", filename, e)
    
    return ExtractionResult(
        category="economy",
        items=items,
        source_files=source_files,
    )
