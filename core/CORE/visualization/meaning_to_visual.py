"""Meaning → Visual — эмоциональная экстраполяция через Pulse.

MeaningLayer знает смыслы и эмоциональную окраску фрагментов.
Каждая тема/ценность маппится в визуальный стиль сцены.
"""
from typing import Optional

EMOTION_MAP = {
    "утрата": "melancholic_dark",
    "смирение": "calm_acceptance",
    "рассвет": "hopeful_golden",
    "надежда": "bright_warm",
    "мистика": "dark_mystical",
    "борьба": "dramatic_contrast",
    "просветление": "ethereal_light",
    "память": "sepia_flashback",
    "передача": "ceremonial_warm",
    "духовность": "sacred_glow",
    "эволюция": "progressive_light",
    "служение": "warm_devotion",
    "предназначение": "epic_reveal",
    "единство": "harmonious_blend",
    "трансформация": "metamorphosis",
}

PALETTE_MAP = {
    "утрата": ["#2C3E50", "#34495E", "#1A1A2E", "#4A4A4A"],
    "надежда": ["#F39C12", "#F1C40F", "#FFF3E0", "#FFD54F"],
    "мистика": ["#1A1A2E", "#16213E", "#0F3460", "#533483"],
    "просветление": ["#FFF8E1", "#E8F5E9", "#BBDEFB", "#FFFFFF"],
    "рассвет": ["#FF9A76", "#FFD6A5", "#FDFFB6", "#FFEAA7"],
    "борьба": ["#8B0000", "#B22222", "#DC143C", "#2C3E50"],
    "память": ["#D2B48C", "#DEB887", "#F5DEB3", "#BC8F8F"],
    "духовность": ["#E1BEE7", "#CE93D8", "#BA68C8", "#FFFFFF"],
    "эволюция": ["#4CAF50", "#8BC34A", "#CDDC39", "#FFF"],
    "служение": ["#FF8A65", "#FFAB91", "#FFCCBC", "#FFF"],
    "предназначение": ["#FFD700", "#FFA000", "#FF6F00", "#FFF8E1"],
    "единство": ["#4FC3F7", "#81D4FA", "#B3E5FC", "#E1F5FE"],
    "трансформация": ["#E040FB", "#7C4DFF", "#448AFF", "#FFF"],
}

STYLE_HINT_MAP = {
    "утрата": "soft_gloom",
    "надежда": "warm_glow",
    "мистика": "chiaroscuro",
    "просветление": "divine_light",
    "рассвет": "golden_hour",
    "борьба": "high_contrast",
    "память": "vintage_fade",
    "духовность": "ethereal_bloom",
    "эволюция": "dynamic_progression",
    "служение": "soft_devotion",
    "предназначение": "epic_wide",
    "единство": "harmonious_blend",
    "трансформация": "metamorphic",
}


def _find_emotional_tags(genome: dict) -> list[str]:
    """Извлечь эмоциональные теги из генома.

    Смотрит themes, values, author_intent.main_message.
    Возвращает список русских ключевых слов-эмоций.
    """
    tags = []
    text_to_scan = ""

    modules = genome.get("modules", {})
    for theme in modules.get("themes", []):
        text_to_scan += " " + theme.get("name", "") + " " + theme.get("description", "")
    for value in modules.get("values", []):
        text_to_scan += " " + value.get("name", "") + " " + value.get("description", "")

    ai = genome.get("author_intent", {})
    text_to_scan += " " + ai.get("main_message", "")
    text_to_scan += " " + " ".join(ai.get("core_values", []))

    text_lower = text_to_scan.lower()
    for keyword in EMOTION_MAP:
        if keyword in text_lower:
            tags.append(keyword)

    # Дедупликация, сохраняем порядок
    seen = set()
    unique = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)

    return unique


def _palette_for_tags(tags: list[str]) -> list[str]:
    """Усреднить палитры по всем тегам."""
    all_colors = []
    for tag in tags:
        palette = PALETTE_MAP.get(tag, [])
        all_colors.extend(palette)
    if not all_colors:
        return ["#808080", "#A9A9A9", "#D3D3D3"]
    # Дедуплицировать, сохранить первые 5
    seen = set()
    unique = []
    for c in all_colors:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique[:5]


def generate_visuals_from_meaning(genome: dict) -> tuple[list[dict], list[dict]]:
    """Сгенерировать Scene и style_preset из смыслов генома.

    Возвращает (scenes, style_presets).
    """
    tags = _find_emotional_tags(genome)
    if not tags:
        return [], []

    scenes = []
    style_presets = {}

    palette = _palette_for_tags(tags)
    primary_emotion = tags[0]
    emotion_value = EMOTION_MAP.get(primary_emotion, "neutral")
    style_hint = STYLE_HINT_MAP.get(primary_emotion, "natural")

    style_id = f"meaning_{primary_emotion}"
    style_presets[style_id] = {
        "preset_id": style_id,
        "name": f"Стиль: {primary_emotion}",
        "prompt_suffix": f"{emotion_value}, {style_hint}",
        "negative_prompt": "blurry, oversaturated, cartoon",
        "palette": palette,
    }

    modules = genome.get("modules", {})
    chapter_count = len(modules.get("timeline", []))
    for i in range(min(5, max(chapter_count, 1))):
        scene = {
            "chapter": i + 1,
            "scene_id": f"meaning_auto_ch{i+1}",
            "title": f"Сцена из смыслов (глава {i+1})",
            "characters": [],
            "location": "",
            "emotion": emotion_value,
            "meaning_tags": tags[:5],
            "visual_style_hint": style_hint,
            "color_palette": palette,
            "source": "meaning_layer_auto",
        }
        scenes.append(scene)

    return scenes, list(style_presets.values())
