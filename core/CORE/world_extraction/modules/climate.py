"""Экстрактор климата мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.climate")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_climate() -> ExtractionResult:
    """Извлечь данные о климате."""
    items = []
    source_files = []
    
    # Ищем в THEMESEXPANDED.json и других файлах
    for filename in ["THEMES_EXPANDED.json", "deep_daily_life.json", "GEOGRAPHY.json"]:
        filepath = KNOWLEDGE_DIR / filename
        if filepath.exists():
            source_files.append(str(filepath))
            try:
                data = json.loads(filepath.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    for item in data:
                        topic = item.get("topic", "")
                        content = item.get("content", "")
                        climate_keywords = ["погод", "климат", "сезон", "зим", "лет", 
                                           "осен", "весн", "холо", "жар", "дожд", "снег"]
                        if any(kw in content.lower() for kw in climate_keywords):
                            items.append(WorldKnowledge(
                                id=f"climate_{topic.lower().replace(' ', '_')}",
                                name=topic,
                                name_ru=topic,
                                category="climate",
                                description=content[:500],
                                properties={"source_file": filename},
                                source=filename,
                            ))
            except Exception as e:
                log.error("climate_extract_error file=%s: %s", filename, e)
    
    return ExtractionResult(
        category="climate",
        items=items,
        source_files=source_files,
    )




