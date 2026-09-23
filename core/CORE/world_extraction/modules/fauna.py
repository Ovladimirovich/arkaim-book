"""Экстрактор фауны мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.fauna")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_fauna() -> ExtractionResult:
    """Извлечь данные о фауне."""
    items = []
    source_files = []
    
    # Ищем в THEMESEXPANDED.json и других файлах
    for filename in ["THEMES_EXPANDED.json", "deep_daily_life.json", "SYMBOLS_EXPANDED.json"]:
        filepath = KNOWLEDGE_DIR / filename
        if filepath.exists():
            source_files.append(str(filepath))
            try:
                data = json.loads(filepath.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    for item in data:
                        topic = item.get("topic", "")
                        content = item.get("content", "")
                        fauna_keywords = ["животн", "скот", "кон", "птиц", "звер", 
                                         "рыб", "охот", "тотем", "символ"]
                        if any(kw in content.lower() for kw in fauna_keywords):
                            items.append(WorldKnowledge(
                                id=f"fauna_{topic.lower().replace(' ', '_')}",
                                name=topic,
                                name_ru=topic,
                                category="fauna",
                                description=content[:500],
                                properties={"source_file": filename},
                                source=filename,
                            ))
            except Exception as e:
                log.error("fauna_extract_error file=%s: %s", filename, e)
    
    return ExtractionResult(
        category="fauna",
        items=items,
        source_files=source_files,
    )




