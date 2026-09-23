"""Экстрактор астрономии мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.astronomy")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_astronomy() -> ExtractionResult:
    """Извлечь данные об астрономии."""
    items = []
    source_files = []
    
    # 1. Из COSMOLOGY.json (астрономические знания)
    cosmo_path = KNOWLEDGE_DIR / "COSMOLOGY.json"
    if cosmo_path.exists():
        source_files.append(str(cosmo_path))
        try:
            data = json.loads(cosmo_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    astro_keywords = ["звёзд", "созвезд", "планет", "луна", "солнц", 
                                     "небо", "вселенн", "космос", "цикл", "орбита"]
                    if any(kw in content.lower() for kw in astro_keywords):
                        items.append(WorldKnowledge(
                            id=f"astro_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="astronomy",
                            description=content[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="COSMOLOGY.json",
                        ))
        except Exception as e:
            log.error("cosmology_astro_error: %s", e)
    
    # 2. Из COSMOLOGY_DEEP.json
    deep_path = KNOWLEDGE_DIR / "COSMOLOGY_DEEP.json"
    if deep_path.exists():
        source_files.append(str(deep_path))
        try:
            data = json.loads(deep_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    astro_keywords = ["звёзд", "созвезд", "цикл", "орбита", "астроном"]
                    if any(kw in content.lower() for kw in astro_keywords):
                        items.append(WorldKnowledge(
                            id=f"astro_deep_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="astronomy",
                            description=content[:500],
                            properties={"depth": "deep"},
                            source="COSMOLOGY_DEEP.json",
                        ))
        except Exception as e:
            log.error("cosmology_deep_astro_error: %s", e)
    
    return ExtractionResult(
        category="astronomy",
        items=items,
        source_files=source_files,
    )




