"""Enhanced Prompt Builder — сборка промптов для генерации ассетов из genome + задачи.md схем."""
from __future__ import annotations

from typing import TYPE_CHECKING

from visualization.prompt_builder import (
    EMOTION_TO_VISUAL, LOCATION_TYPE_VISUALS, QUALITY_SUFFIXES,
    NEGATIVE_PROMPT_DEFAULT, _hex_to_name, _describe_color_palette,
    _describe_meaning_tags,
)

if TYPE_CHECKING:
    from .schemas import VisualAsset, ShotSpec


# Стиль-префиксы
STYLE_PRESETS = {
    "cinematic_fantasy": "cinematic fantasy, epic film still, dramatic lighting",
    "realistic": "photorealistic, natural lighting, detailed textures",
    "watercolor": "watercolor painting, soft edges, muted palette, artistic",
    "dark_gothic": "dark gothic, moody atmosphere, deep shadows, medieval",
    "ethereal": "ethereal dreamlike, soft glow, translucent light, heavenly",
    "ancient壁画": "ancient fresco style, aged texture, earth tones, historical",
    "minimalist": "minimalist composition, clean lines, negative space, modern",
    "oil_painting": "oil painting, thick brushstrokes, rich colors, classical art",
}

MOTION_DESCRIPTIONS = {
    "static": "",
    "slow_dolly_in": "slow dolly push-in, cinematic movement",
    "slow_dolly_out": "slow dolly pull-out, revealing wider view",
    "slow_pan": "slow panoramic sweep, steady camera",
    "slow_zoom_in": "slow zoom in, gradual close-up",
    "slow_zoom_out": "slow zoom out, revealing context",
    "tracking_shot": "tracking shot following subject, smooth motion",
    "crane_up": "crane shot rising upward, aerial reveal",
    "handheld": "handheld camera, organic movement, slight shake",
    "orbit": "orbiting camera around subject, 360-degree view",
    "follow": "camera following subject from behind, pursuit movement",
}


def build_asset_prompt(asset: "VisualAsset") -> str:
    """Собрать полный промпт для генерации изображения из VisualAsset.

    MD-2 DEPRECATED как точка НОВОГО входа: маршруты C (/assets/generate,
    generate-async, batch, film /shots/generate) строят смысловой вход
    через канонический SceneContext (visual.visual_context_builder.
    build_scene_context*) до вызова пайплайна; VisualAsset остаётся
    доменной записью-результатом (legacy). Функция сохранена для
    существующих вызовов пайплайна (overrides/custom_prompt-пути);
    НЕ УДАЛЕНА — новые генерации входят через SceneContext.
    """
    parts = []

    # 1. Стиль
    style_prefix = STYLE_PRESETS.get(asset.style, asset.style.replace("_", " "))
    if style_prefix:
        parts.append(style_prefix)

    # 2. Заголовок сцены
    if asset.title:
        parts.append(asset.title)

    # 3. Mood → визуальное описание
    mood_visual = EMOTION_TO_VISUAL.get(asset.mood, "")
    if not mood_visual and asset.mood:
        mood_visual = asset.mood.replace("_", " ")
    if mood_visual:
        parts.append(mood_visual)

    # 4. Персонажи
    for char in asset.characters:
        char_parts = [char.name]
        if char.appearance:
            char_parts.append(char.appearance)
        if char.expression:
            char_parts.append(f"{char.expression} expression")
        if char.pose:
            char_parts.append(char.pose)
        parts.append(", ".join(char_parts))

    # 5. Объекты на сцене
    if asset.objects:
        parts.append(f"featuring {', '.join(asset.objects[:5])}")

    # 6. Символика
    if asset.symbols:
        parts.append(f"symbolic elements: {', '.join(asset.symbols[:4])}")

    # 7. Композиция
    comp = asset.composition
    if comp:
        fg = comp.get("foreground", "")
        bg = comp.get("background", "")
        focus = comp.get("focus", "")
        if fg:
            parts.append(f"foreground: {fg}")
        if bg:
            parts.append(f"background: {bg}")
        if focus:
            parts.append(f"focal point: {focus}")

    # 8. Цветовая палитра
    if asset.palette:
        pal_desc = _describe_color_palette(asset.palette)
        if pal_desc:
            parts.append(pal_desc)

    # 9. Camera movement (для видео превью или кинематографичных кадров)
    motion = asset.camera.movement
    if motion and motion != "static":
        motion_desc = MOTION_DESCRIPTIONS.get(motion, motion.replace("_", " "))
        if motion_desc:
            parts.append(motion_desc)

    # 10. Quality suffixes
    seen = set()
    for p in parts:
        key = p.lower().strip()
        if key and key not in seen:
            seen.add(key)
    quality_count = 0
    for q in QUALITY_SUFFIXES:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            parts.append(q)
            quality_count += 1
        if quality_count >= 5:
            break

    return ", ".join(parts)


def build_shot_prompt(shot: "ShotSpec", asset: "VisualAsset") -> str:
    """Собрать промпт для отдельного кадра видео."""
    parts = []

    # Базовый промпт из кадра
    if shot.prompt:
        parts.append(shot.prompt)

    # Стиль из ассета
    style_prefix = STYLE_PRESETS.get(asset.style, "")
    if style_prefix:
        parts.append(style_prefix)

    # Camera
    if shot.camera.shot_type and shot.camera.shot_type != "medium_shot":
        parts.append(shot.camera.shot_type.replace("_", " "))
    motion = shot.camera.movement
    if motion and motion != "static":
        motion_desc = MOTION_DESCRIPTIONS.get(motion, motion.replace("_", " "))
        if motion_desc:
            parts.append(motion_desc)

    # Lighting
    if shot.lighting:
        parts.append(shot.lighting)

    # Palette
    if shot.palette:
        pal_desc = _describe_color_palette(shot.palette)
        if pal_desc:
            parts.append(pal_desc)
    elif asset.palette:
        pal_desc = _describe_color_palette(asset.palette)
        if pal_desc:
            parts.append(pal_desc)

    # Quality
    seen = set()
    deduped = []
    for p in parts:
        key = p.lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(p)
    for q in QUALITY_SUFFIXES[:3]:
        if q.lower() not in seen:
            deduped.append(q)
            seen.add(q.lower())

    return ", ".join(deduped)


def build_negative_prompt(asset: "VisualAsset") -> str:
    """Собрать negative prompt."""
    base = NEGATIVE_PROMPT_DEFAULT
    extra = asset.generation.negative_prompt
    if extra:
        return f"{base}, {', '.join(extra)}"
    return base
