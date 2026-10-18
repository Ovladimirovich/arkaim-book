"""FilmArtDirection — общие визуальные правила фильма (art direction).

Единственный редактируемый источник film-wide правил для режиссёра:
  - визуальный стиль и палитра (база: VISUAL_KNOWLEDGE/STYLE_LIBRARY);
  - персонажи фильма (ссылки на VISUAL_KNOWLEDGE + утверждённые изображения
    в AssetStorage — копирование внешности НЕ происходит);
  - локации (ссылки на VISUAL_KNOWLEDGE + палитра/референс-надстройки);
  - правила композиции и освещения.

Хранение: одна запись в существующей SQLite studio.db (таблица
studio_art_direction) — НЕ новая БД и НЕ дублирование Visual Knowledge.

Принципы (OWNER-GO):
  - изменение общих правил НЕ стирает ручные правки шотов и утверждённые
    результаты: правила только вычисляются при чтении (resolve/apply);
  - revision растёт при каждом фактическом изменении — артефакты,
    созданные до нового revision, помечаются как «затронутые»;
  - ничего не удаляется и не пересоздаётся автоматически.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .scenario_schemas import ScenarioShot

_AD_CONFIG = ConfigDict(extra="forbid")

#: Секции правил — используются для diff и «что изменилось».
AD_SECTIONS = (
    "style",
    "palette",
    "aspect_ratio",
    "composition_rules",
    "lighting_rules",
    "negative_rules",
    "characters",
    "locations",
    "references",
)

_MODEL_SECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "style": ("style_preset", "style_prompt"),
    "palette": ("palette",),
    "aspect_ratio": ("aspect_ratio",),
    "composition_rules": ("composition_rules",),
    "lighting_rules": ("lighting_rules",),
    "negative_rules": ("negative_rules",),
    "characters": ("characters",),
    "locations": ("locations",),
    "references": ("reference_asset_ids",),
}


class ArtDirectionCharacter(BaseModel):
    """Персонаж фильма: ссылка на Visual Knowledge + утверждённый образ."""

    model_config = _AD_CONFIG

    knowledge_key: str = ""  # ключ в CHARACTER_VISUALS (имя персонажа)
    name: str = ""  # отображаемое имя (дубль ключа для удобства UI)
    approved_image_asset_id: str | None = None  # asset_id в AssetStorage
    note: str = ""  # режиссёрская заметка (не дублирует внешность)


class ArtDirectionLocation(BaseModel):
    """Локация фильма: ссылка на Visual Knowledge + надстройки режиссёра."""

    model_config = _AD_CONFIG

    knowledge_key: str = ""  # ключ в LOCATION_VISUALS
    name: str = ""
    palette: list[str] = []  # пусто → палитра берётся из Visual Knowledge
    reference_asset_id: str | None = None  # эталонный кадр локации (AssetStorage)
    note: str = ""


class FilmArtDirection(BaseModel):
    """Общие визуальные правила фильма (singleton на проект, ad_id='film')."""

    model_config = _AD_CONFIG

    ad_id: str = "film"
    revision: int = 0  # инкремент при каждом фактическом изменении
    updated_at: str = ""
    updated_by: str = ""

    # ── Стиль и палитра ──
    style_preset: str = "cinematic_fantasy"  # ключ STYLE_LIBRARY
    style_prompt: str = ""  # свободный стиль режиссёра; пусто → prefix пресета
    palette: list[str] = []  # общая палитра фильма; пусто → палитра локации/VK
    aspect_ratio: str | None = None  # None → aspect_ratio пресета

    # ── Правила композиции и освещения ──
    composition_rules: list[str] = []
    lighting_rules: list[str] = []
    negative_rules: list[str] = []  # дополняют negative_additions пресета

    # ── Состав фильма ──
    characters: list[ArtDirectionCharacter] = []
    locations: list[ArtDirectionLocation] = []
    reference_asset_ids: list[str] = []  # общие референсы (ссылки в AssetStorage)

    # ── Bookkeeping ──
    last_change_sections: list[str] = []


def default_art_direction() -> FilmArtDirection:
    """Правила «по умолчанию» — ещё не сохранялись (revision=0)."""
    return FilmArtDirection()


def diff_art_direction(old: FilmArtDirection, new: FilmArtDirection) -> list[str]:
    """Секции, фактически изменившиеся между двумя снимками правил."""
    old_dump = old.model_dump()
    new_dump = new.model_dump()
    changed: list[str] = []
    for section, fields in _MODEL_SECTION_FIELDS.items():
        if any(old_dump.get(f) != new_dump.get(f) for f in fields):
            changed.append(section)
    return changed


# ── Resolve: применение общих правил к шоту ────────────────────────────────


def _vk_style(style_lib: dict, preset_key: str) -> dict:
    entry = style_lib.get(preset_key)
    return entry if isinstance(entry, dict) else {}


def match_scene_context(
    ad: FilmArtDirection, image_plan_location: str, image_plan_characters: list[str]
) -> tuple[list[ArtDirectionCharacter], ArtDirectionLocation | None]:
    """Сопоставить правила фильма со сценой (по имени/ключу)."""
    loc_key = (image_plan_location or "").strip().lower()
    matched_loc = next(
        (
            loc
            for loc in ad.locations
            if loc.knowledge_key.strip().lower() == loc_key
            or loc.name.strip().lower() == loc_key
        ),
        None,
    )
    wanted = {c.strip().lower() for c in image_plan_characters if c.strip()}
    matched_chars = [
        ch
        for ch in ad.characters
        if ch.knowledge_key.strip().lower() in wanted
        or ch.name.strip().lower() in wanted
    ]
    return matched_chars, matched_loc


def shot_local_overrides(shot: ScenarioShot) -> dict:
    """Что в шоте переопределяет/дополняет ОБЩИЕ правила фильма.

    Только поля-конкуренты правил: стиль, палитра, свет. Собственные
    параметры плана (shot_type, камера, настроение) сюда НЕ входят —
    они не конфликтуют с общими правилами.
    """
    local: dict = {}
    if shot.style_override:
        local["style_override"] = shot.style_override
    if shot.palette_override:
        local["palette_override"] = list(shot.palette_override)
    if shot.lighting_note:
        local["lighting_note"] = shot.lighting_note
    return local


def applied_rules_snapshot(
    ad: FilmArtDirection,
    matched_chars: list[ArtDirectionCharacter],
    matched_loc: ArtDirectionLocation | None,
    style_lib: dict,
) -> dict:
    """Какие общие правила применяются к сцене (для показа режиссёру)."""
    preset = _vk_style(style_lib, ad.style_preset)
    return {
        "style_preset": ad.style_preset,
        "style_prompt": ad.style_prompt or preset.get("prefix", ""),
        "palette": list(ad.palette),
        "aspect_ratio": ad.aspect_ratio or preset.get("aspect_ratio", ""),
        "composition_rules": list(ad.composition_rules),
        "lighting_rules": list(ad.lighting_rules),
        "negative_rules": list(ad.negative_rules),
        "preset_negative_additions": list(preset.get("negative_additions", [])),
        "characters": [c.model_dump() for c in matched_chars],
        "location": matched_loc.model_dump() if matched_loc else None,
        "reference_asset_ids": list(ad.reference_asset_ids),
        "revision": ad.revision,
    }


def compose_shot_prompt(
    ad: FilmArtDirection,
    shot: ScenarioShot,
    matched_chars: list[ArtDirectionCharacter],
    matched_loc: ArtDirectionLocation | None,
    style_lib: dict,
    vk_locations: dict | None = None,
    scene_title: str = "",
    continuity_context: dict | None = None,
) -> str:
    """Итоговый промпт плана: общие правила фильма + локальные переопределения.

    Локальные поля шота всегда побеждают общие (переопределение), но НЕ
    затирают правила целиком — общие правила остаются в кадре.

    continuity_context (Studio Phase 1) — ОПЦИОНАЛЬНЫЕ ограничения связности
    с предыдущей связанной сценой (локация/время/свет/палитра/персонажи).
    По умолчанию None → поведение промпта не меняется (исходные промпты не
    переписываются автоматически; контекст передаётся только по решению
    режиссёра — для предпросмотра «согласовать со сценой»).
    """
    vk_locations = vk_locations or {}
    preset = _vk_style(style_lib, ad.style_preset)

    parts: list[str] = []

    # Стиль: локальный override иначе общий (свободный текст иначе пресет)
    style = shot.style_override or ad.style_prompt or preset.get("prefix", "")
    if style:
        parts.append(style)

    # Палитра: локальная иначе общая иначе палитра локации из VK
    palette = list(shot.palette_override or ad.palette)
    if not palette and matched_loc:
        palette = list(matched_loc.palette)
    if not palette and matched_loc:
        vk_pal = (vk_locations.get(matched_loc.knowledge_key) or {}).get(
            "palette"
        ) or []
        palette = list(vk_pal)
    if palette:
        parts.append(f"color palette: {', '.join(palette)}")

    # Локация и её тип из Visual Knowledge (без копирования — только имя/тип)
    if matched_loc:
        loc_entry = vk_locations.get(matched_loc.knowledge_key) or {}
        loc_bits = [matched_loc.name or matched_loc.knowledge_key]
        loc_type = loc_entry.get("type")
        if loc_type:
            loc_bits.append(str(loc_type))
        if matched_loc.note:
            loc_bits.append(matched_loc.note)
        parts.append(f"location: {', '.join(loc_bits)}")

    # Персонажи сцены (имена — ссылки на Visual Knowledge)
    if matched_chars:
        names = [c.name or c.knowledge_key for c in matched_chars]
        parts.append(f"characters: {', '.join(names)}")

    if scene_title:
        parts.append(scene_title)

    # Содержание плана
    if shot.description:
        parts.append(shot.description)

    # Композиция: общие правила + локальные параметры шота
    if ad.composition_rules:
        parts.append("composition: " + "; ".join(ad.composition_rules))
    cam_bits = [b for b in (shot.shot_type, shot.camera_action, shot.camera_angle) if b]
    if cam_bits:
        parts.append("camera: " + ", ".join(cam_bits))

    # Свет: общие правила + локальное правило шота
    light_bits = list(ad.lighting_rules)
    if shot.lighting_note:
        light_bits.append(shot.lighting_note)
    if light_bits:
        parts.append("lighting: " + "; ".join(light_bits))

    # Настроение шота
    if shot.mood_note:
        parts.append(f"mood: {shot.mood_note}")

    # Связность со связанной сценой (опционально; иначе поведение прежнее)
    if continuity_context:
        cont_bits: list[str] = []
        loc = continuity_context.get("location")
        if loc:
            cont_bits.append(f"same location as previous scene ({loc})")
        tod = continuity_context.get("time_of_day")
        if tod:
            cont_bits.append(f"time of day: {tod}")
        light = continuity_context.get("lighting")
        if light:
            cont_bits.append(f"lighting: {light}")
        if continuity_context.get("palette"):
            cont_bits.append("palette: " + ", ".join(continuity_context["palette"]))
        chars = continuity_context.get("characters") or []
        if chars:
            cont_bits.append("consistent appearance: " + ", ".join(chars))
        if cont_bits:
            parts.append("continuity: " + "; ".join(cont_bits))

    # Качество пресета
    quality = preset.get("quality_suffixes") or []
    if quality:
        parts.append(", ".join(str(q) for q in quality))

    return ", ".join(p for p in parts if p)


def compose_shot_negative(ad: FilmArtDirection, style_lib: dict) -> list[str]:
    """Негатив итогового промпта: пресет + общие правила фильма."""
    preset = _vk_style(style_lib, ad.style_preset)
    merged: list[str] = []
    for item in list(preset.get("negative_additions", [])) + list(ad.negative_rules):
        s = str(item).strip()
        if s and s not in merged:
            merged.append(s)
    return merged


def resolve_shot(
    ad: FilmArtDirection,
    shot: ScenarioShot,
    image_plan_location: str,
    image_plan_characters: list[str],
    style_lib: dict,
    vk_locations: dict | None = None,
    scene_title: str = "",
    continuity_context: dict | None = None,
) -> dict:
    """Полный резолв плана: применённые правила + локальное + итоговый промпт."""
    matched_chars, matched_loc = match_scene_context(
        ad, image_plan_location, image_plan_characters
    )
    return {
        "applied": applied_rules_snapshot(ad, matched_chars, matched_loc, style_lib),
        "local_overrides": shot_local_overrides(shot),
        "resolved_prompt": compose_shot_prompt(
            ad,
            shot,
            matched_chars,
            matched_loc,
            style_lib,
            vk_locations,
            scene_title,
            continuity_context,
        ),
        "resolved_negative": compose_shot_negative(ad, style_lib),
    }
