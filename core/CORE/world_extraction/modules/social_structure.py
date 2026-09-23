"""Экстрактор социальной структуры мира книги."""
import json
import logging
from pathlib import Path

from ..models import WorldKnowledge, ExtractionResult

log = logging.getLogger("hermes.world_extraction.social_structure")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


def extract_social_structure() -> ExtractionResult:
    """Извлечь данные о социальной структуре."""
    items = []
    source_files = []
    
    # 1. Из CHARACTERS.json (роли персонажей)
    characters_path = KNOWLEDGE_DIR / "CHARACTERS.json"
    if characters_path.exists():
        source_files.append(str(characters_path))
        try:
            data = json.loads(characters_path.read_text(encoding="utf-8-sig"))
            characters = data.get("characters", data) if isinstance(data, dict) else data
            if isinstance(characters, list):
                roles_seen = set()
                for char in characters:
                    if isinstance(char, dict):
                        role = char.get("type")
                        if role and role not in roles_seen:
                            roles_seen.add(role)
                            items.append(WorldKnowledge(
                                id=f"role_{role.lower().replace(' ', '_')}",
                                name=role,
                                name_ru=role,
                                category="social_structure",
                                description=f"Социальная роль: {role}",
                                properties={"type": "social_role", "count": sum(1 for c in characters if isinstance(c, dict) and c.get("type") == role)},
                                source="CHARACTERS.json",
                            ))
        except Exception as e:
            log.error("characters_role_error: %s", e)
    
    # 2. Из civilization_profiles.json (социальная структура цивилизаций)
    civ_path = KNOWLEDGE_DIR / "civilization_profiles.json"
    if civ_path.exists():
        source_files.append(str(civ_path))
        try:
            data = json.loads(civ_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                for key, civ in data.items():
                    if isinstance(civ, dict):
                        social = civ.get("social_structure")
                        if social:
                            items.append(WorldKnowledge(
                                id=f"social_{key}",
                                name=f"Социальная структура: {key}",
                                name_ru=f"Социальная структура: {key}",
                                category="social_structure",
                                description=str(social)[:500],
                                properties={"civilization": key},
                                source="civilization_profiles.json",
                            ))
        except Exception as e:
            log.error("civ_social_error: %s", e)
    
    # 3. Из deep_daily_life.json
    daily_path = KNOWLEDGE_DIR / "deep_daily_life.json"
    if daily_path.exists():
        source_files.append(str(daily_path))
        try:
            data = json.loads(daily_path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, str) and sub_value:
                                social_keywords = ["род", "семья", "старейшин", "воин", "жрец", 
                                                  "учител", "женщин", "дет", "общин", "класс"]
                                if any(kw in sub_value.lower() for kw in social_keywords):
                                    items.append(WorldKnowledge(
                                        id=f"daily_social_{key}_{sub_key}",
                                        name=f"{key}: {sub_key}",
                                        name_ru=f"{key}: {sub_key}",
                                        category="social_structure",
                                        description=sub_value[:500],
                                        properties={"source_file": "deep_daily_life.json"},
                                        source="deep_daily_life.json",
                                    ))
        except Exception as e:
            log.error("daily_social_error: %s", e)
    
    return ExtractionResult(
        category="social_structure",
        items=items,
        source_files=source_files,
    )
