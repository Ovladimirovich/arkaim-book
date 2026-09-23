"""Conflict Palettes — генерация визуальных палитр из конфликтов сущностей."""
from typing import Optional

from .prompt_builder import _normalize_emotion

CONFLICT_TEMPLATES = {
    "гиперборея_атлантида": {
        "color_a": ["#DAA520", "#8B4513", "#F5DEB3"],
        "color_b": ["#1E3A5F", "#4A6FA5", "#B0C4DE"],
        "visual_style_hint": "duality_contrast",
        "emotion": "conflict_civilizations",
    },
    "кали_юга_сати_юга": {
        "color_a": ["#2C3E50", "#1A1A2E", "#16213E"],
        "color_b": ["#F1C40F", "#E67E22", "#FFF3E0"],
        "visual_style_hint": "transition_between_eras",
        "emotion": "era_transition",
    },
    "материя_дух": {
        "color_a": ["#8B4513", "#A0522D", "#D2691E"],
        "color_b": ["#E0E0FF", "#BBDEFB", "#FFFFFF"],
        "visual_style_hint": "earth_vs_ethereal",
        "emotion": "duality_of_existence",
    },
    "хаос_гармония": {
        "color_a": ["#8B0000", "#FF4500", "#FF6347"],
        "color_b": ["#90EE90", "#98FB98", "#F0FFF0"],
        "visual_style_hint": "chaos_vs_order",
        "emotion": "struggle_of_opposites",
    },
}

DEFAULT_CONFLICT = {
    "color_a": ["#2C3E50"],
    "color_b": ["#E74C3C"],
    "visual_style_hint": "contrast",
    "emotion": "conflict",
}


def _normalize(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def resolve_conflict_key(entity_a_name: str, entity_b_name: str) -> Optional[str]:
    """Найти ключ шаблона по именам двух конфликтующих сущностей."""
    a = _normalize(entity_a_name)
    b = _normalize(entity_b_name)
    key1 = f"{a}_{b}"
    key2 = f"{b}_{a}"
    if key1 in CONFLICT_TEMPLATES:
        return key1
    if key2 in CONFLICT_TEMPLATES:
        return key2
    return None


def generate_conflict_scene(
    entity_a: dict,
    entity_b: dict,
    chapter: int = 1,
) -> dict:
    """Создать Scene-словарь для конфликта двух сущностей."""
    a_name = entity_a.get("name", entity_a.get("id", "entity_a"))
    b_name = entity_b.get("name", entity_b.get("id", "entity_b"))

    key = resolve_conflict_key(a_name, b_name)
    template = CONFLICT_TEMPLATES.get(key, DEFAULT_CONFLICT)

    return {
        "chapter": chapter,
        "scene_id": f"conflict_{_normalize(a_name)}_{_normalize(b_name)}",
        "title": f"Конфликт: {a_name} vs {b_name}",
        "characters": [],
        "location": "граница миров",
        "emotion": template["emotion"],
        "meaning_tags": [f"конфликт:{_normalize(a_name)}", f"конфликт:{_normalize(b_name)}"],
        "visual_style_hint": template["visual_style_hint"],
        "palette_a": template["color_a"],
        "palette_b": template["color_b"],
    }


def generate_all_conflict_scenes(genome: dict) -> list[dict]:
    """Обойти world_entities и conflicts, создать сцены для конфликтов.

    Читает genome.world_entities[].conflict_with
    и genome.modules.conflicts[].
    Возвращает список Scene-словарей.
    """
    scenes = []
    seen = set()

    world_entities = genome.get("world_entities", [])
    entity_by_name = {e["name"].lower(): e for e in world_entities if e.get("name")}

    for entity in world_entities:
        name = entity.get("name", "")
        conflicts = entity.get("conflict_with") or []
        for conflict_name in conflicts:
            conflict_name_lower = conflict_name.lower().strip()
            if not conflict_name_lower:
                continue
            pair_key = tuple(sorted([name.lower(), conflict_name_lower]))
            if pair_key in seen:
                continue
            seen.add(pair_key)
            target = entity_by_name.get(conflict_name_lower, {"name": conflict_name})
            scene = generate_conflict_scene(entity, target, chapter=1)
            scenes.append(scene)

    return scenes
