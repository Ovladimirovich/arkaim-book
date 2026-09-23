"""Экстрактор ритуалов мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.rituals")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_rituals() -> ExtractionResult:
    """Извлечь данные о ритуалах."""
    items = []
    source_files = []
    
    # 1. Из RITUALS.json
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
                            category="rituals",
                            description=item.get("content", "")[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="RITUALS.json",
                        ))
        except Exception as e:
            log.error("rituals_error: %s", e)
    
    # 2. Из ESOTERIC_CONNECTIONS.json (ритуальные практики)
    esoteric_path = KNOWLEDGE_DIR / "ESOTERIC_CONNECTIONS.json"
    if esoteric_path.exists():
        source_files.append(str(esoteric_path))
        try:
            data = json.loads(esoteric_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    ritual_keywords = ["ритуал", "обряд", "практика", "церемони", "инициац"]
                    if any(kw in content.lower() for kw in ritual_keywords):
                        items.append(WorldKnowledge(
                            id=f"esoteric_ritual_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="rituals",
                            description=content[:500],
                            properties={"type": "esoteric_ritual"},
                            source="ESOTERIC_CONNECTIONS.json",
                        ))
        except Exception as e:
            log.error("esoteric_ritual_error: %s", e)
    
    return ExtractionResult(
        category="rituals",
        items=items,
        source_files=source_files,
    )




