"""Экстрактор цивилизаций мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.civilizations")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_civilizations() -> ExtractionResult:
    """Извлечь данные о цивилизациях."""
    items = []
    source_files = []
    
    # 1. Из civilization_profiles.json
    profiles_path = KNOWLEDGE_DIR / "civilization_profiles.json"
    if profiles_path.exists():
        source_files.append(str(profiles_path))
        try:
            data = json.loads(profiles_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for civ in data:
                    items.append(WorldKnowledge(
                        id=f"civ_{civ.get('name', '').lower().replace(' ', '_')}",
                        name=civ.get("name", ""),
                        name_ru=civ.get("name_ru", civ.get("name", "")),
                        category="civilizations",
                        description=civ.get("description", ""),
                        properties={
                            "epoch": civ.get("epoch"),
                            "values": civ.get("values", []),
                            "technologies": civ.get("technologies", []),
                            "religion": civ.get("religion"),
                            "social_structure": civ.get("social_structure"),
                        },
                        source="civilization_profiles.json",
                    ))
            elif isinstance(data, dict):
                for key, civ in data.items():
                    if isinstance(civ, dict):
                        items.append(WorldKnowledge(
                            id=f"civ_{key.lower().replace(' ', '_')}",
                            name=civ.get("name", key),
                            name_ru=civ.get("name_ru", civ.get("name", key)),
                            category="civilizations",
                            description=civ.get("description", ""),
                            properties={
                                "epoch": civ.get("epoch"),
                                "values": civ.get("values", []),
                            },
                            source="civilization_profiles.json",
                        ))
        except Exception as e:
            log.error("civilization_profiles_error: %s", e)
    
    # 2. Из CHARACTERS.json (извлекаем типы как цивилизации)
    characters_path = KNOWLEDGE_DIR / "CHARACTERS.json"
    if characters_path.exists():
        source_files.append(str(characters_path))
        try:
            data = json.loads(characters_path.read_text(encoding="utf-8-sig"))
            characters = data.get("characters", data) if isinstance(data, dict) else data
            if isinstance(characters, list):
                types_seen = set()
                for char in characters:
                    if isinstance(char, dict):
                        char_type = char.get("type", "")
                        if char_type and char_type not in types_seen:
                            types_seen.add(char_type)
                            items.append(WorldKnowledge(
                                id=f"civ_type_{char_type.lower().replace(' ', '_')}",
                                name=char_type,
                                name_ru=char_type,
                                category="civilizations",
                                description=f"Тип персонажей: {char_type}",
                                properties={"type": "character_type"},
                                source="CHARACTERS.json",
                            ))
        except Exception as e:
            log.error("characters_civ_error: %s", e)
    
    # 3. Из KNOWLEDGE/ARCHAEOLOGY.json (исторические цивилизации)
    arch_path = KNOWLEDGE_DIR / "ARCHAEOLOGY.json"
    if arch_path.exists():
        source_files.append(str(arch_path))
        try:
            data = json.loads(arch_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "")
                    content = item.get("content", "")
                    if topic and ("цивилиз" in content.lower() or "народ" in content.lower()):
                        items.append(WorldKnowledge(
                            id=f"arch_civ_{topic.lower().replace(' ', '_')}",
                            name=topic,
                            name_ru=topic,
                            category="civilizations",
                            description=content[:500],
                            source="ARCHAEOLOGY.json",
                        ))
        except Exception as e:
            log.error("archaeology_civ_error: %s", e)
    
    return ExtractionResult(
        category="civilizations",
        items=items,
        source_files=source_files,
    )
