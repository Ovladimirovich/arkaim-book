"""Экстрактор мифологии мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.mythology")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_mythology() -> ExtractionResult:
    """Извлечь данные о мифологии."""
    items = []
    source_files = []
    
    # 1. Из SYMBOLS.json и SYMBOLS_EXPANDED.json
    for filename in ["SYMBOLS.json", "SYMBOLS_EXPANDED.json", "SYMBOLS_DEEP.json"]:
        filepath = KNOWLEDGE_DIR / filename
        if filepath.exists():
            source_files.append(str(filepath))
            try:
                data = json.loads(filepath.read_text(encoding="utf-8-sig"))
                if isinstance(data, list):
                    for item in data:
                        topic = item.get("topic", "")
                        if topic:
                            items.append(WorldKnowledge(
                                id=f"myth_{topic.lower().replace(' ', '_')}",
                                name=topic,
                                name_ru=topic,
                                category="mythology",
                                description=item.get("content", "")[:500],
                                properties={"source_file": filename},
                                source=filename,
                            ))
            except Exception as e:
                log.error("mythology_extract_error file=%s: %s", filename, e)
    
    # 2. Из COSMOLOGY.json (космогонические мифы)
    cosmo_path = KNOWLEDGE_DIR / "COSMOLOGY.json"
    if cosmo_path.exists():
        source_files.append(str(cosmo_path))
        try:
            data = json.loads(cosmo_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"cosmo_myth_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="mythology",
                            description=item.get("content", "")[:500],
                            properties={"type": "cosmological_myth"},
                            source="COSMOLOGY.json",
                        ))
        except Exception as e:
            log.error("cosmology_myth_error: %s", e)
    
    return ExtractionResult(
        category="mythology",
        items=items,
        source_files=source_files,
    )




