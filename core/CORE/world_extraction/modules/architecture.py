"""Экстрактор архитектуры мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.architecture")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_architecture() -> ExtractionResult:
    """Извлечь данные об архитектуре из KNOWLEDGE."""
    items = []
    source_files = []
    
    # 1. Из ARCHAE.json (археологические данные о строениях)
    arch_path = KNOWLEDGE_DIR / "ARCHAEOLOGY.json"
    if arch_path.exists():
        source_files.append(str(arch_path))
        try:
            data = json.loads(arch_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    # Ищем упоминания строений
                    arch_keywords = ["храм", "стена", "здание", "дом", "башня", 
                                    "крепость", "городище", "поселение", "архитектур"]
                    if any(kw in content.lower() for kw in arch_keywords):
                        items.append(WorldKnowledge(
                            id=f"arch_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="architecture",
                            description=content[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="ARCHAEOLOGY.json",
                        ))
        except Exception as e:
            log.error("archaeology_arch_error: %s", e)
    
    # 2. Из TECHNOLOGY.json (строительные технологии)
    tech_path = KNOWLEDGE_DIR / "TECHNOLOGY.json"
    if tech_path.exists():
        source_files.append(str(tech_path))
        try:
            data = json.loads(tech_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    build_keywords = ["строит", "архитектур", "конструкц", "материал"]
                    if any(kw in content.lower() for kw in build_keywords):
                        items.append(WorldKnowledge(
                            id=f"tech_arch_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="architecture",
                            description=content[:500],
                            properties={"type": "building_technology"},
                            source="TECHNOLOGY.json",
                        ))
        except Exception as e:
            log.error("technology_arch_error: %s", e)
    
    # 3. Из GEOGRAPHY.json (описания мест с архитектурой)
    geo_path = KNOWLEDGE_DIR / "GEOGRAPHY.json"
    if geo_path.exists():
        source_files.append(str(geo_path))
        try:
            data = json.loads(geo_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    if any(kw in content.lower() for kw in ["храм", "стена", "городище"]):
                        items.append(WorldKnowledge(
                            id=f"geo_arch_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="architecture",
                            description=content[:500],
                            properties={"type": "location_architecture"},
                            source="GEOGRAPHY.json",
                        ))
        except Exception as e:
            log.error("geography_arch_error: %s", e)
    
    return ExtractionResult(
        category="architecture",
        items=items,
        source_files=source_files,
    )




