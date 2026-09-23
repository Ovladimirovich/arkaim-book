"""Экстрактор технологий мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.technologies")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_technologies() -> ExtractionResult:
    """Извлечь данные о технологиях."""
    items = []
    source_files = []
    
    # 1. Из TECHNOLOGY.json
    tech_path = KNOWLEDGE_DIR / "TECHNOLOGY.json"
    if tech_path.exists():
        source_files.append(str(tech_path))
        try:
            data = json.loads(tech_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"tech_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="technologies",
                            description=item.get("content", "")[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="TECHNOLOGY.json",
                        ))
        except Exception as e:
            log.error("technology_error: %s", e)
    
    # 2. Из COSMOLOGY.json (космические технологии)
    cosmo_path = KNOWLEDGE_DIR / "COSMOLOGY.json"
    if cosmo_path.exists():
        source_files.append(str(cosmo_path))
        try:
            data = json.loads(cosmo_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    tech_keywords = ["технолог", "энерг", "кристалл", "звук", "свет"]
                    if any(kw in content.lower() for kw in tech_keywords):
                        items.append(WorldKnowledge(
                            id=f"cosmo_tech_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="technologies",
                            description=content[:500],
                            properties={"type": "cosmic_technology"},
                            source="COSMOLOGY.json",
                        ))
        except Exception as e:
            log.error("cosmology_tech_error: %s", e)
    
    return ExtractionResult(
        category="technologies",
        items=items,
        source_files=source_files,
    )




