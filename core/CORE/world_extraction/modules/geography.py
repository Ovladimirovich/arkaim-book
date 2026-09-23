"""Экстрактор географии мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.geography")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_geography() -> ExtractionResult:
    """Извлечь географические данные из KNOWLEDGE/*.json."""
    items = []
    source_files = []
    
    # 1. Из MAP_DATA.json
    map_data_path = KNOWLEDGE_DIR / "MAP_DATA.json"
    if map_data_path.exists():
        source_files.append(str(map_data_path))
        try:
            data = json.loads(map_data_path.read_text(encoding="utf-8-sig"))
            
            # Регионы
            for region in data.get("regions", []):
                if isinstance(region, dict):
                    items.append(WorldKnowledge(
                        id=f"region_{region.get('id', 'unknown')}",
                        name=region.get("name", ""),
                        name_ru=region.get("name", ""),
                        category="geography",
                        description=region.get("description", ""),
                        properties={
                            "type": "region",
                            "coordinates": region.get("coordinates"),
                            "era": region.get("era"),
                            "color": region.get("color"),
                            "icon": region.get("icon"),
                        },
                        source="MAP_DATA.json",
                    ))
            
            # Маршруты
            for route in data.get("routes", []):
                if isinstance(route, dict):
                    items.append(WorldKnowledge(
                        id=f"route_{route.get('id', 'unknown')}",
                        name=route.get("name", ""),
                        name_ru=route.get("name", ""),
                        category="geography",
                        description=route.get("description", ""),
                        properties={
                            "type": "route",
                            "from_location": route.get("from"),
                            "to_location": route.get("to"),
                            "distance": route.get("distance"),
                        },
                        source="MAP_DATA.json",
                    ))
            
            # Энергетические линии
            for line in data.get("energy_lines", []):
                if isinstance(line, dict):
                    items.append(WorldKnowledge(
                        id=f"energy_line_{line.get('id', 'unknown')}",
                        name=line.get("name", ""),
                        name_ru=line.get("name", ""),
                        category="geography",
                        description=line.get("description", ""),
                        properties={
                            "type": "energy_line",
                            "direction": line.get("direction"),
                            "power": line.get("power"),
                        },
                        source="MAP_DATA.json",
                    ))
        except Exception as e:
            log.error("map_data_error: %s", e)
    
    # 2. Из GEOGRAPHY.json
    geography_path = KNOWLEDGE_DIR / "GEOGRAPHY.json"
    if geography_path.exists():
        source_files.append(str(geography_path))
        try:
            data = json.loads(geography_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        topic = item.get("topic", "")
                        if topic:
                            items.append(WorldKnowledge(
                                id=f"geo_{topic.lower().replace(' ', '_')}",
                                name=topic,
                                name_ru=topic,
                                category="geography",
                                description=item.get("content", "")[:500],
                                properties=item.get("metadata", {}).get("layers", {}),
                                source="GEOGRAPHY.json",
                            ))
        except Exception as e:
            log.error("geography_error: %s", e)
    
    # 3. Из CHARACTERS.json (локации персонажей)
    characters_path = KNOWLEDGE_DIR / "CHARACTERS.json"
    if characters_path.exists():
        source_files.append(str(characters_path))
        try:
            data = json.loads(characters_path.read_text(encoding="utf-8-sig"))
            characters = data.get("characters", data) if isinstance(data, dict) else data
            if isinstance(characters, list):
                locations_seen = set()
                for char in characters:
                    if isinstance(char, dict):
                        # Извлекаем локации из описания персонажа
                        desc = char.get("description", "")
                        loc_keywords = ["Аркаим", "Гиперборея", "Атлантида", "Океания"]
                        for loc in loc_keywords:
                            if loc.lower() in desc.lower() and loc not in locations_seen:
                                locations_seen.add(loc)
                                items.append(WorldKnowledge(
                                    id=f"char_location_{loc.lower().replace(' ', '_')}",
                                    name=loc,
                                    name_ru=loc,
                                    category="geography",
                                    description=f"Локация, упомянутая в описании персонажа {char.get('name', '')}",
                                    properties={"type": "character_location", "character": char.get("name")},
                                    source="CHARACTERS.json",
                                ))
        except Exception as e:
            log.error("characters_locations_error: %s", e)
    
    return ExtractionResult(
        category="geography",
        items=items,
        source_files=source_files,
    )
