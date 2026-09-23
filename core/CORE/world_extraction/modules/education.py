"""Экстрактор образования мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.education")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_education() -> ExtractionResult:
    """Извлечь данные об образовании."""
    items = []
    source_files = []
    
    # Ищем в THEMESEXPANDED.json и других файлах
    for filename in ["THEMES_EXPANDED.json", "deep_characters.json", "deep_concepts.json"]:
        filepath = KNOWLEDGE_DIR / filename
        if filepath.exists():
            source_files.append(str(filepath))
            try:
                data = json.loads(filepath.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    for item in data:
                        topic = item.get("topic", "")
                        content = item.get("content", "")
                        edu_keywords = ["ученик", "учител", "знани", "обучен", "мудрост", 
                                       "посвящен", "инициац", "передача", "школа", "учить"]
                        if any(kw in content.lower() for kw in edu_keywords):
                            items.append(WorldKnowledge(
                                id=f"edu_{topic.lower().replace(' ', '_')}",
                                name=topic,
                                name_ru=topic,
                                category="education",
                                description=content[:500],
                                properties={"source_file": filename},
                                source=filename,
                            ))
            except Exception as e:
                log.error("education_extract_error file=%s: %s", filename, e)
    
    return ExtractionResult(
        category="education",
        items=items,
        source_files=source_files,
    )




