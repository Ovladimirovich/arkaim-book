"""Экстрактор философии мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.philosophy")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_philosophy() -> ExtractionResult:
    """Извлечь данные о философии."""
    items = []
    source_files = []
    
    # 1. Из PHILOSOPHY.json
    phil_path = KNOWLEDGE_DIR / "PHILOSOPHY.json"
    if phil_path.exists():
        source_files.append(str(phil_path))
        try:
            data = json.loads(phil_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"phil_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="philosophy",
                            description=item.get("content", "")[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="PHILOSOPHY.json",
                        ))
        except Exception as e:
            log.error("philosophy_error: %s", e)
    
    # 2. Из PHILOSOPHY_DEEP.json
    deep_path = KNOWLEDGE_DIR / "PHILOSOPHY_DEEP.json"
    if deep_path.exists():
        source_files.append(str(deep_path))
        try:
            data = json.loads(deep_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"phil_deep_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="philosophy",
                            description=item.get("content", "")[:500],
                            properties={"depth": "deep"},
                            source="PHILOSOPHY_DEEP.json",
                        ))
        except Exception as e:
            log.error("philosophy_deep_error: %s", e)
    
    return ExtractionResult(
        category="philosophy",
        items=items,
        source_files=source_files,
    )




