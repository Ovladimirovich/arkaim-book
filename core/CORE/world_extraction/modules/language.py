"""Экстрактор языка мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.language")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_language() -> ExtractionResult:
    """Извлечь данные о языке."""
    items = []
    source_files = []
    
    # 1. Из LANGUAGE.json
    lang_path = KNOWLEDGE_DIR / "LANGUAGE.json"
    if lang_path.exists():
        source_files.append(str(lang_path))
        try:
            data = json.loads(lang_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"lang_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="language",
                            description=item.get("content", "")[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="LANGUAGE.json",
                        ))
        except Exception as e:
            log.error("language_error: %s", e)
    
    return ExtractionResult(
        category="language",
        items=items,
        source_files=source_files,
    )




