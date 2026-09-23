"""Экстрактор хронологии мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.chronology")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_chronology() -> ExtractionResult:
    """Извлечь данные о хронологии."""
    items = []
    source_files = []
    
    # 1. Из PLOT.json
    plot_path = KNOWLEDGE_DIR / "PLOT.json"
    if plot_path.exists():
        source_files.append(str(plot_path))
        try:
            data = json.loads(plot_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    if topic:
                        items.append(WorldKnowledge(
                            id=f"plot_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="chronology",
                            description=item.get("content", "")[:500],
                            properties=item.get("metadata", {}).get("layers", {}),
                            source="PLOT.json",
                        ))
        except Exception as e:
            log.error("plot_error: %s", e)
    
    # 2. Из THEMES_EXPANDED.json (хронологические темы)
    themes_path = KNOWLEDGE_DIR / "THEMES_EXPANDED.json"
    if themes_path.exists():
        source_files.append(str(themes_path))
        try:
            data = json.loads(themes_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    chrono_keywords = ["эпох", "время", "истор", "древн", "прошл", 
                                      "будущ", "цикл", "период"]
                    if any(kw in content.lower() for kw in chrono_keywords):
                        items.append(WorldKnowledge(
                            id=f"chrono_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="chronology",
                            description=content[:500],
                            properties={"source_file": "THEMES_EXPANDED.json"},
                            source="THEMES_EXPANDED.json",
                        ))
        except Exception as e:
            log.error("themes_chrono_error: %s", e)
    
    return ExtractionResult(
        category="chronology",
        items=items,
        source_files=source_files,
    )




