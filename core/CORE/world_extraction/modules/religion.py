"""Экстрактор религии мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.religion")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_religion() -> ExtractionResult:
    """Извлечь данные о религии."""
    items = []
    source_files = []
    
    # 1. Из ESOTERIC_CONNECTIONS.json
    esoteric_path = KNOWLEDGE_DIR / "ESOTERIC_CONNECTIONS.json"
    if esoteric_path.exists():
        source_files.append(str(esoteric_path))
        try:
            data = json.loads(esoteric_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"rel_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="religion",
                            description=item.get("content", "")[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="ESOTERIC_CONNECTIONS.json",
                        ))
        except Exception as e:
            log.error("esoteric_error: %s", e)
    
    # 2. Из RITUALS.json
    rituals_path = KNOWLEDGE_DIR / "RITUALS.json"
    if rituals_path.exists():
        source_files.append(str(rituals_path))
        try:
            data = json.loads(rituals_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"ritual_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="religion",
                            description=item.get("content", "")[:500],
                            properties={"type": "ritual"},
                            source="RITUALS.json",
                        ))
        except Exception as e:
            log.error("rituals_error: %s", e)
    
    # 3. Из PHILOSOPHY.json (религиозные концепции)
    phil_path = KNOWLEDGE_DIR / "PHILOSOPHY.json"
    if phil_path.exists():
        source_files.append(str(phil_path))
        try:
            data = json.loads(phil_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    rel_keywords = ["религ", "бог", "духовн", "священн", "культ"]
                    if any(kw in content.lower() for kw in rel_keywords):
                        items.append(WorldKnowledge(
                            id=f"phil_rel_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="religion",
                            description=content[:500],
                            properties={"type": "religious_philosophy"},
                            source="PHILOSOPHY.json",
                        ))
        except Exception as e:
            log.error("philosophy_rel_error: %s", e)
    
    return ExtractionResult(
        category="religion",
        items=items,
        source_files=source_files,
    )




