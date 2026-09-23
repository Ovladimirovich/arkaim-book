"""Archetype Visuals — наследование визуальных шаблонов от архетипов персонажей."""
from typing import Optional

ARCHETYPE_VISUAL_TEMPLATES = {
    "Искатель": {
        "clothing": "лёгкая походная одежда, плащ, дорожные сапоги",
        "color_palette": ["#8B4513", "#2F4F4F", "#6B8E23"],
        "accessories": ["поясная сумка", "карта"],
        "style_constants": ["natural_light", "outdoor"],
    },
    "Мудрец": {
        "clothing": "белые льняные одежды, посох, плащ с капюшоном",
        "color_palette": ["#F5F5DC", "#8B4513", "#D3D3D3"],
        "accessories": ["посох", "свиток"],
        "style_constants": ["soft_light", "wise_expression"],
    },
    "Хранитель": {
        "clothing": "тёмные доспехи, металлические наплечники, тяжёлый плащ",
        "color_palette": ["#2F4F4F", "#708090", "#1A1A2E"],
        "accessories": ["меч", "щит", "амулет"],
        "style_constants": ["dramatic_shadow", "strong_contrast"],
    },
    "Проводник": {
        "clothing": "голубые одежды с вышивкой, светящиеся символы на ткани",
        "color_palette": ["#4FC3F7", "#FFD700", "#E1BEE7"],
        "accessories": ["кристалл", "светящийся шар"],
        "style_constants": ["ethereal_glow", "soft_bloom"],
    },
    "Архат": {
        "clothing": "минималистичные белые одежды, золотая вышивка",
        "color_palette": ["#FFFFFF", "#FFD700", "#FFF8E1"],
        "accessories": [],
        "style_constants": ["divine_light", "halo_effect"],
    },
    "Наставник": {
        "clothing": "удобные практичные одежды, кожаный жилет, рабочие штаны",
        "color_palette": ["#A0522D", "#6B8E23", "#BC8F8F"],
        "accessories": ["книга", "инструмент"],
        "style_constants": ["warm_light", "friendly"],
    },
    "Лидер": {
        "clothing": "парадные одежды, знаки отличия, плащ с мехом",
        "color_palette": ["#800020", "#FFD700", "#2F4F4F"],
        "accessories": ["корона", "скипетр"],
        "style_constants": ["epic_lighting", "authoritative"],
    },
    "Учёный": {
        "clothing": "удлинённая туника, очки, перчатки без пальцев",
        "color_palette": ["#696969", "#B0C4DE", "#F5F5DC"],
        "accessories": ["книги", "странный прибор"],
        "style_constants": ["focused_light", "detail_shot"],
    },
}

DEFAULT_TEMPLATE = {
    "clothing": "одежда не описана",
    "color_palette": ["earth tones"],
    "accessories": [],
    "style_constants": [],
}


def archetype_to_visual(character: dict) -> dict:
    """Построить character_visual из архетипа персонажа.

    Берёт character.archetype, маппит в шаблон.
    Если архетип не найден — возвращает шаблон по умолчанию.
    """
    template = ARCHETYPE_VISUAL_TEMPLATES.get(
        character.get("archetype", ""),
        DEFAULT_TEMPLATE,
    )
    return {
        "character_id": character.get("id", character.get("name", "unknown")),
        "age_range": "не указан",
        "build": "среднее",
        "hair": "не указаны",
        "eyes": "не указаны",
        "clothing": template["clothing"],
        "accessories": template["accessories"].copy(),
        "color_palette": template["color_palette"].copy(),
        "style_constants": template["style_constants"].copy(),
    }


def fill_missing_archetype_visuals(genome: dict) -> int:
    """Заполнить отсутствующие character_visuals из архетипов.

    Проходит по всем персонажам genome.modules.characters.
    Если для персонажа нет character_visual → создаёт из archetype.
    Возвращает количество созданных визуалов.
    """
    modules = genome.setdefault("modules", {})
    characters = modules.get("characters", [])
    existing_visuals = modules.setdefault("character_visuals", [])
    existing_ids = {v.get("character_id") for v in existing_visuals}

    created = 0
    for ch in characters:
        char_id = ch.get("id") or ch.get("name")
        if not char_id:
            continue
        if char_id in existing_ids:
            continue
        visual = archetype_to_visual(ch)
        existing_visuals.append(visual)
        existing_ids.add(char_id)
        created += 1

    return created
