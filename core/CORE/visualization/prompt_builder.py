"""
Prompt Builder — собирает полноценный SD-промпт из всей глубины Visual Genome.
Без LLM. Все данные из генома: сцены, персонажи, локации, палитры, стили.

Модуль больше НЕ содержит собственных словарей: смысловые значения
(EMOTION_TO_VISUAL, EMOTION_SUFFIX, LOCATION_TYPE_VISUALS, QUALITY_SUFFIXES,
NEGATIVE_PROMPT_DEFAULT) ре-экспортируются из канона
``visual.visual_context_builder`` — единого источника истины.
"""
from visual.visual_context_builder import (  # noqa: F401 — ре-экспорт канона
    EMOTION_SUFFIX,
    EMOTION_TO_VISUAL,
    LOCATION_TYPE_VISUALS,
    NEGATIVE_PROMPT_DEFAULT,
    QUALITY_SUFFIXES,
    _normalize_emotion,
)


def _hex_to_name(h: str) -> str:
    """Шестнадцатеричный цвет → приблизительное словесное описание."""
    h = h.lstrip("#")
    if len(h) != 6:
        return h
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return h
    if r > 200 and g > 200 and b > 200:
        return "white"
    if r < 50 and g < 50 and b < 50:
        return "black"
    if r > 200 and g < 100 and b < 100:
        return "crimson red"
    if r > 200 and g > 150 and b < 100:
        return "golden amber"
    if r < 100 and g < 100 and b > 180:
        return "deep blue"
    if r > 200 and g > 200 and b < 100:
        return "pale yellow"
    if r < 100 and g > 150 and b < 100:
        return "forest green"
    if r > 150 and g < 100 and b > 150:
        return "royal purple"
    if r > 200 and g < 100 and b > 200:
        return "magenta"
    if r > 180 and g > 100 and b < 50:
        return "burnt orange"
    if r < 50 and g < 100 and b > 100:
        return "indigo"
    if r > 200 and g > 200 and b > 200:
        return "bright white"
    if r > 150 and g > 100 and b < 80:
        return "terracotta"
    if r > 100 and g < 80 and b < 50:
        return "dark brown"
    if r > 180 and g > 180 and b > 150:
        return "warm beige"
    if r < 80 and g < 80 and b > 120:
        return "twilight blue"
    return f"#{h}"


def _describe_color_palette(colors: list[str]) -> str:
    if not colors:
        return ""
    names = [_hex_to_name(c) for c in colors[:5]]
    unique = []
    for n in names:
        if n not in unique:
            unique.append(n)
    if not unique:
        return ""
    if len(unique) == 1:
        return f"color palette dominated by {unique[0]}"
    return f"color palette of {', '.join(unique[:-1])} and {unique[-1]}"


def _describe_meaning_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    clean = [t.replace("theme:", "").replace("конфликт:", "") for t in tags if t]
    if not clean:
        return ""
    return f"symbolic themes: {', '.join(clean[:4])}"


class PromptBuilder:
    """Собирает SD-промпт из всех данных Visual Genome.

    MD-2 DEPRECATED как точка НОВОГО входа: маршруты A/B/C/E переведены
    на канонический SceneContext (visual.visual_context_builder.
    build_scene_context*). Класс сохраняется (legacy-контракты /visualize,
    /visualize/epoch, /assets/generate, film /shots/generate продолжают
    работать через него для промпт-совместимости); НЕ УДАЛЁН.
    Новые генерации должны входить через SceneContext-билдер.
    """

    def __init__(self, pulse):
        self._pulse = pulse

    def build_scene_prompt(self, scene: dict, character_visuals: dict, location: dict) -> str:
        parts = []

        # 1. Стилевой префикс от VisualStyleLayer
        style_prefix = self._get_style_prefix()

        # 2. Эпическая/сюжетная основа — название сцены
        title = scene.get("title", "Untitled scene")
        parts.append(f"epic fantasy scene, {title}")

        # 3. Эмоция → визуальное описание
        emotion = _normalize_emotion(scene.get("emotion", ""))
        emotion_visual = EMOTION_TO_VISUAL.get(emotion, "")
        if not emotion_visual and emotion:
            emotion_visual = emotion.replace("_", " ")
        if emotion_visual:
            parts.append(emotion_visual)

        # 4. Персонажи (полное описание)
        for char_id in scene.get("characters", []):
            cv = character_visuals.get(char_id, {})
            if not cv:
                parts.append(char_id)
                continue

            desc_parts = [f"{char_id}"]
            age = cv.get("age_range", "") or cv.get("age", "")
            if age and age != "не указан" and age != "unknown":
                desc_parts.append(age)

            build = cv.get("build", "")
            if build and build != "среднее" and build != "average":
                desc_parts.append(build)

            hair = cv.get("hair", "")
            if hair and hair != "не указаны" and hair != "not specified":
                desc_parts.append(hair)

            eyes = cv.get("eyes", "")
            if eyes and eyes != "не указаны" and eyes != "not specified":
                desc_parts.append(eyes)

            clothing = cv.get("clothing", "")
            if clothing and clothing not in ("не указана", "not specified", "одежда не описана", "", None):
                desc_parts.append(f"wearing {clothing}")

            accessories = cv.get("accessories", [])
            if accessories:
                desc_parts.append(f"with {', '.join(accessories)}")

            palette = cv.get("color_palette", [])
            if palette and palette != ["earth tones"]:
                desc_parts.append(_describe_color_palette(palette))

            style_constants = cv.get("style_constants", [])
            if style_constants:
                desc_parts.append(", ".join(style_constants))

            parts.append(". ".join(desc_parts))

        # 5. Локация (полное описание)
        loc_parts = self._build_location_parts(location)
        if loc_parts:
            parts.extend(loc_parts)

        # 6. Meaning tags → символика
        tags = scene.get("meaning_tags", [])
        tag_desc = _describe_meaning_tags(tags)
        if tag_desc:
            parts.append(tag_desc)

        # 7. Цветовая палитра сцены
        scene_palette = scene.get("color_palette", []) or scene.get("palette_a", [])
        if scene_palette:
            palette_desc = _describe_color_palette(scene_palette)
            if palette_desc:
                parts.append(palette_desc)

        # 8. visual_style_hint — кинематографический стиль
        style_hint = scene.get("visual_style_hint", "")
        if style_hint and style_hint not in ("natural", "", None):
            parts.append(style_hint.replace("_", " "))

        # 9. Стилевой суффикс
        emotion_suffix = EMOTION_SUFFIX.get(emotion, "")
        if emotion_suffix:
            parts.append(emotion_suffix)

        # 10. Quality (дедуплицировано глобально)
        seen = set()
        deduped = []
        for p in parts:
            key = p.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped.append(p)
        parts = deduped

        seen_q = set()
        quality_parts = []
        if style_prefix:
            for sp in style_prefix.split(","):
                s = sp.strip().lower()
                if s and s not in seen_q:
                    seen_q.add(s)
                    quality_parts.append(sp.strip())
        for q in QUALITY_SUFFIXES:
            q_lower = q.lower()
            if q_lower not in seen_q:
                seen_q.add(q_lower)
                quality_parts.append(q)
            if len(quality_parts) >= 5:
                break
        parts.extend(quality_parts)

        return ", ".join(parts)

    def build_negative_prompt(self, scene: dict) -> str:
        """Собрать negative prompt на основе сцены."""
        return NEGATIVE_PROMPT_DEFAULT

    def build_epoch_prompt(self, epoch_id: str, context: dict) -> str:
        """Build SD prompt from epoch temporal data.

        M7.2: bridges WorldModel temporal context → visual prompt.
        Uses EMOTION_TO_VISUAL mapping derived from epoch identity.
        Does NOT mutate any model state. Read-only.
        """
        epoch = context.get("epoch") or {}
        name_ru = epoch.get("name_ru", epoch_id)
        description = epoch.get("description", "")
        event_count = context.get("event_count", 0)
        char_count = context.get("character_count", 0)

        # Derive emotion from epoch identity (deterministic, no LLM)
        epoch_emotion_map: dict[str, str] = {
            "pre_arkaim": "dark_mystical",
            "satya_yuga": "hopeful_golden",
            "treta_yuga": "warm_devotion",
            "dvapara_yuga": "duality_contrast",
            "kali_yuga": "melancholic_dark",
            "arkaim_era": "epic_reveal",
        }
        emotion_key = epoch_emotion_map.get(epoch_id, "neutral")
        emotion_visual = EMOTION_TO_VISUAL.get(emotion_key, "")

        parts = [f"epic fantasy scene, {name_ru}"]
        if description:
            parts.append(description[:200])
        if emotion_visual:
            parts.append(emotion_visual)
        if event_count > 0:
            parts.append(f"{event_count} canonical events")
        if char_count > 0:
            parts.append(f"{char_count} characters present in era")

        # Reuse existing quality suffixes (last 5 only)
        parts.extend(QUALITY_SUFFIXES[-5:])

        # Join then deduplicate on comma-separated phrases
        raw = ", ".join(parts)
        phrases = [p.strip() for p in raw.split(",")]
        seen: set[str] = set()
        deduped: list[str] = []
        for p in phrases:
            k = p.lower()
            if k and k not in seen:
                seen.add(k)
                deduped.append(p)
        return ", ".join(deduped)

    def build_full_prompt_pair(self, scene: dict, character_visuals: dict, location: dict) -> tuple[str, str]:
        """DEPRECATED (MD-3.3, audit D1): 0 production-потребителей.

        Canonical replacement: MediaPlanBuilder.build_image_plan(ctx) →
        план несёт prompt + negative_constraints (единый смысловой
        контракт MD-3; см. ADR_MEDIA_PLAN_V0). Функция сохранена без
        изменения поведения для внешних/legacy-вызовов; удаление — MD-5+.

        Историческое поведение: (positive_prompt, negative_prompt).
        """
        pos = self.build_scene_prompt(scene, character_visuals, location)
        neg = self.build_negative_prompt(scene)
        return pos, neg

    def _get_style_prefix(self) -> str:
        style_prefix = ""
        vs_layer = self._pulse.layers.get("visual_style")
        if vs_layer:
            try:
                response = vs_layer.respond_to("")
                if response:
                    style_prefix = response.text
            except Exception:
                pass
        return style_prefix

    @staticmethod
    def _build_location_parts(location: dict) -> list[str]:
        parts = []
        loc_type = location.get("type", "")
        type_visual = LOCATION_TYPE_VISUALS.get(loc_type, "")
        if type_visual:
            parts.append(type_visual)
        elif loc_type and loc_type != "unknown":
            parts.append(loc_type.replace("_", " "))

        architecture = location.get("architecture", "")
        if architecture and architecture != "описание не заполнено" and architecture != "не описана":
            parts.append(architecture[:200])

        atmosphere = location.get("atmosphere", "")
        if atmosphere and atmosphere != "нейтральная":
            parts.append(atmosphere)

        lighting = location.get("lighting", "")
        if lighting and lighting != "естественный" and lighting != "natural":
            parts.append(lighting)

        palette = location.get("palette", [])
        if palette and palette != ["neutral"] and palette != ["#808080"]:
            palette_desc = _describe_color_palette(palette)
            if palette_desc:
                parts.append(palette_desc)

        return parts
