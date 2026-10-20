"""Continuity — связность между планами, сценами и эпизодами (Studio Phase 1).

Задача модуля — честно показать режиссёру, что связывает соседние планы и
сцены, и где есть ПОТЕНЦИАЛЬНОЕ несоответствие. Модуль НЕ придумывает данные:
если характеристика неизвестна — она не сравнивается.

Источники (переиспользуются, не дублируются):
  - геном книги (canonical сцены: chapter/scene_id/characters/location/…);
  - активная версия Studio-сессии (VideoScenario: планы, переопределения);
  - FilmArtDirection (общие правила, утверждённые образы персонажей);
  - VisualContext (окружение/свет/палитра/внешность) — опционально.

Разделяются:
  - исходные сведения сценария (genome / scenario) — source;
  - режиссёрские ограничения (art_direction) — directorial;
  - фактические характеристики (VisualContext, approved-кадры) — actual;
  - обнаруженные несоответствия (findings);
  - разрешённые режиссёром отличия (ContinuityDecision, persist).

Состояния связи: unchecked / mismatch / consistent / waived.

Ни одно поле изображения не предполагается: наличие/совпадение
утверждённых кадров фиксируется, но их содержимое НЕ утверждается.

Хранение решений — существующая SQLite studio.db (таблица
studio_continuity_decisions), новых хранилищ не создаётся.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .scenario_schemas import ScenarioShot  # noqa: F401  (типы планов)

_MODEL_CONFIG = ConfigDict(extra="forbid")

# ── Отношения между элементами ──────────────────────────────────────────
RELATION_SHOTS = "shots_within_scene"  # соседние планы одной сцены
RELATION_SCENE_BOUNDARY = "scene_boundary_shots"  # последний план A → первый план B
RELATION_ADJACENT = "adjacent_scenes"  # соседние сцены одного эпизода
RELATION_CROSS_EPISODE = "cross_episode"  # сцены разных эпизодов (кандидат)

# ── Состояния связи ─────────────────────────────────────────────────────
STATUS_UNCHECKED = "unchecked"  # проверка не выполнена (нет сопоставимых данных)
STATUS_MISMATCH = "mismatch"  # есть потенциальное несоответствие
STATUS_CONSISTENT = "consistent"  # согласовано
STATUS_WAIVED = "waived"  # отличие разрешено режиссёром

# ── Решения режиссёра (ContinuityDecision.action) ───────────────────────
ACTION_WAIVED = "waived"  # отличие разрешено (связь закрыта)
ACTION_APPLIED = "applied"  # перенос ограничений из связанной сцены применён

#: Префикс ключа применённого переноса (одно решение на сцену-приёмник).
APPLY_PREFIX = "apply"

_SEVERITY_WARNING = "warning"
_SEVERITY_INFO = "info"

# ── Источники данных (provenance) ───────────────────────────────────────
SRC_GENOME = "genome"
SRC_SCENARIO = "scenario"
SRC_ART_DIRECTION = "art_direction"
SRC_VISUAL_CONTEXT = "visual_context"
SRC_SESSION = "session"


class ContinuityFinding(BaseModel):
    """Обнаруженное отличие/несоответствие между двумя сторонами связи."""

    model_config = _MODEL_CONFIG

    field: str = (
        ""  # location | time_of_day | lighting | palette | character_appearance | …
    )
    kind: str = "difference"  # difference | change
    severity: str = _SEVERITY_INFO  # warning | info
    message: str = ""  # человеческое объяснение причины
    subject: str = ""  # персонаж (id/имя) для character-* или пусто
    from_value: str = ""
    to_value: str = ""
    certainty: str = (
        "confirmed"  # confirmed — данные известны; candidate — предположение
    )
    sources: list[str] = Field(default_factory=list)  # откуда взяты обе стороны


class ContinuityDecision(BaseModel):
    """Решение режиссёра по связи (persist в studio.db).

    Подтверждает осознанное отличие. Хранит отпечаток контекста (basis),
    на котором решение было принято: если контекст изменился (например,
    утверждён новый кадр или выросли общие правила) — decision.stale=True,
    решение больше не закрывает связь, и она требует повторного просмотра.
    """

    model_config = _MODEL_CONFIG

    decision_id: str = ""
    link_key: str = ""  # стабильный ключ связи (relation:from->to) или apply:<scene_id>
    session_id: str = ""  # сессия, из которой принято решение (если есть)
    action: str = (
        ACTION_WAIVED  # waived — отличие разрешено; applied — перенос применён
    )
    note: str = ""
    by: str = ""
    basis: dict = Field(default_factory=dict)
    stale: bool = False
    #: Переносимые ограничения (только для action=applied): location/time_of_day/
    #: lighting/palette/characters/visual_style. Пусто для waived.
    constraints: dict = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class ShotContinuitySnapshot(BaseModel):
    """Известные характеристики одного плана (для сравнения соседних планов)."""

    model_config = _MODEL_CONFIG

    shot_id: str = ""
    order: int = 0
    shot_type: str = ""
    lighting_note: str = ""
    mood_note: str = ""
    style_override: str = ""
    palette_override: list[str] = Field(default_factory=list)
    approved_image_asset_id: str | None = None
    character_ids: list[str] = Field(default_factory=list)
    character_names: list[str] = Field(default_factory=list)
    environment_elements: list[str] = Field(default_factory=list)


class ContinuityCharacterStub(BaseModel):
    """Персонаж сцены с известными характеристиками внешности (если есть)."""

    model_config = _MODEL_CONFIG

    character_id: str = ""
    name: str = ""
    appearance: str = ""
    clothing: str = ""
    approved_image_asset_id: str | None = None
    sources: list[str] = Field(default_factory=list)


class SceneContinuitySnapshot(BaseModel):
    """Известные характеристики сцены для сравнения со связанной сценой.

    known_fields перечисляет ТОЛЬКО фактически известные поля — сравнение
    идёт лишь по ним; отсутствующие данные не подменяются догадками.
    """

    model_config = _MODEL_CONFIG

    scene_id: str = ""
    chapter: int = 0
    order_global: int = -1
    title: str = ""

    location: str = ""
    location_reference_asset_id: str | None = None
    time_of_day: str = ""
    season: str = ""
    weather: str = ""
    lighting_direction: str = ""
    lighting_color: str = ""
    palette: list[str] = Field(default_factory=list)
    visual_style: str = ""
    emotion: str = ""

    characters: list[ContinuityCharacterStub] = Field(default_factory=list)
    approved_image_asset_id: str | None = None

    has_session: bool = False
    session_id: str | None = None
    has_scenario: bool = False
    shot_count: int = 0
    shots: list[ShotContinuitySnapshot] = Field(default_factory=list)

    art_direction_revision: int = 0
    known_fields: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)


class ClipBoundaryContract(BaseModel):
    """Контракт связи клипов: предыдущий клип / end frame → следующий клип / start frame.

    Значения — только идентификаторы фактически существующих сущностей.
    Содержимое кадров НЕ утверждается (status="unknown" пока нет видео).
    Контракт не привязан к конкретному видеогенератору.
    """

    model_config = _MODEL_CONFIG

    previous_clip_asset_id: str | None = None
    end_frame_asset_id: str | None = None
    next_clip_asset_id: str | None = None
    start_frame_asset_id: str | None = None
    status: str = "unknown"  # unknown | declared
    note: str = ""


class ContinuityLink(BaseModel):
    """Связь между двумя планами или сценами + результат проверки."""

    model_config = _MODEL_CONFIG

    link_id: str = ""
    link_key: str = ""
    relation: str = ""
    certainty: str = "confirmed"  # confirmed | candidate
    from_ref: str = ""
    to_ref: str = ""
    from_scene_id: str = ""
    to_scene_id: str = ""
    status: str = STATUS_UNCHECKED
    findings: list[ContinuityFinding] = Field(default_factory=list)
    reason: str = ""  # почему связь вообще рассматривается (для candidate)
    decision: ContinuityDecision | None = None
    clip_boundary: ClipBoundaryContract | None = None
    basis: dict = Field(default_factory=dict)  # отпечаток контекста для решения


class SceneContinuityReport(BaseModel):
    """Полный отчёт связности для одной сцены (ответ GET .../continuity)."""

    model_config = _MODEL_CONFIG

    scene: SceneContinuitySnapshot = Field(default_factory=SceneContinuitySnapshot)
    links: list[ContinuityLink] = Field(default_factory=list)
    overall_status: str = STATUS_UNCHECKED
    limitations: list[str] = Field(default_factory=list)


# ── Утилиты ─────────────────────────────────────────────────────────────


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _is_known(value: str | None) -> bool:
    return bool((value or "").strip())


def _finding(
    field: str,
    kind: str,
    severity: str,
    message: str,
    from_value: str,
    to_value: str,
    *,
    subject: str = "",
    certainty: str = "confirmed",
    sources: list[str] | None = None,
) -> ContinuityFinding:
    return ContinuityFinding(
        field=field,
        kind=kind,
        severity=severity,
        message=message,
        subject=subject,
        from_value=from_value,
        to_value=to_value,
        certainty=certainty,
        sources=sources or [],
    )


def ordered_scene_ids(scenes: list[dict]) -> list[str]:
    """Глобальный порядок сцен = порядок массива генома."""
    ids: list[str] = []
    for s in scenes:
        sid = s.get("scene_id", s.get("id", ""))
        if sid:
            ids.append(sid)
    return ids


def scene_by_id(scenes: list[dict]) -> dict[str, dict]:
    return {s.get("scene_id", s.get("id", "")): s for s in scenes}


def build_shot_snapshot(shot: ScenarioShot) -> ShotContinuitySnapshot:
    char_ids: list[str] = []
    char_names: list[str] = []
    for ca in shot.character_actions or []:
        if ca.character_id:
            char_ids.append(ca.character_id)
        if ca.character_name:
            char_names.append(ca.character_name)
    env = [ea.element for ea in (shot.environment_actions or []) if ea.element]
    return ShotContinuitySnapshot(
        shot_id=shot.shot_id,
        order=shot.order,
        shot_type=shot.shot_type,
        lighting_note=shot.lighting_note,
        mood_note=shot.mood_note,
        style_override=shot.style_override,
        palette_override=list(shot.palette_override or []),
        approved_image_asset_id=shot.approved_image_asset_id,
        character_ids=char_ids,
        character_names=char_names,
        environment_elements=env,
    )


def build_scene_snapshot(
    scene: dict,
    *,
    order_global: int,
    session=None,
    scenario=None,
    art_direction=None,
    visual_context=None,
) -> SceneContinuitySnapshot:
    """Собрать снимок сцены из существующих источников (без генерации).

    Приоритеты: VisualContext (фактические) > scenario/art_direction; genome —
    базовая канва (персонажи, локация, эмоция).
    """
    scene_id = scene.get("scene_id", scene.get("id", ""))
    chapter = scene.get("chapter", 0)
    genre_chars = [c for c in (scene.get("characters") or []) if c]
    scene_source = scene.get("source") or SRC_GENOME

    snap = SceneContinuitySnapshot(
        scene_id=scene_id,
        chapter=chapter,
        order_global=order_global,
        title=scene.get("title", ""),
        location=scene.get("location", ""),
        emotion=scene.get("emotion", ""),
    )
    known: set[str] = set()
    prov: dict[str, str] = {}
    if snap.location:
        known.add("location")
        prov["location"] = scene_source
    if snap.emotion:
        known.add("emotion")
        prov["emotion"] = scene_source
    if genre_chars:
        known.add("characters")
        prov["characters"] = scene_source

    # ── Персонажи: канва из генома, обогащение из VisualContext ──
    chars: dict[str, ContinuityCharacterStub] = {}
    for cid in genre_chars:
        stub = chars.setdefault(
            _norm(cid) or cid, ContinuityCharacterStub(character_id=cid, name=cid)
        )
        stub.sources.append(scene_source)
    if visual_context is not None:
        for vc in getattr(visual_context, "characters", []) or []:
            key = _norm(vc.character_id) or _norm(vc.name)
            if not key:
                continue
            stub = chars.setdefault(
                key,
                ContinuityCharacterStub(character_id=vc.character_id, name=vc.name),
            )
            if vc.character_id:
                stub.character_id = vc.character_id
            if vc.name:
                stub.name = vc.name
            if vc.appearance_summary:
                stub.appearance = vc.appearance_summary
                known.add("character_appearance")
                prov["character_appearance"] = SRC_VISUAL_CONTEXT
            if vc.clothing:
                stub.clothing = vc.clothing
            if SRC_VISUAL_CONTEXT not in stub.sources:
                stub.sources.append(SRC_VISUAL_CONTEXT)

    # ── Общие правила фильма: утверждённые образы персонажей/локации ──
    if art_direction is not None:
        snap.art_direction_revision = int(getattr(art_direction, "revision", 0) or 0)
        ad_chars = list(getattr(art_direction, "characters", []) or [])
        for key, stub in chars.items():
            match = next(
                (
                    ac
                    for ac in ad_chars
                    if _norm(ac.knowledge_key) in (key, _norm(stub.name))
                    or _norm(ac.name) in (key, _norm(stub.name))
                ),
                None,
            )
            if match is not None:
                if match.approved_image_asset_id:
                    stub.approved_image_asset_id = match.approved_image_asset_id
                if SRC_ART_DIRECTION not in stub.sources:
                    stub.sources.append(SRC_ART_DIRECTION)
        loc_key = _norm(snap.location)
        for loc in getattr(art_direction, "locations", []) or []:
            if loc_key and loc_key in (_norm(loc.knowledge_key), _norm(loc.name)):
                if loc.reference_asset_id:
                    snap.location_reference_asset_id = loc.reference_asset_id
                    known.add("location_reference")
                    prov["location_reference"] = SRC_ART_DIRECTION
                if loc.palette and not snap.palette:
                    snap.palette = list(loc.palette)
                    known.add("palette")
                    prov["palette"] = SRC_ART_DIRECTION
                break
        if getattr(art_direction, "palette", None) and not snap.palette:
            snap.palette = list(art_direction.palette)
            known.add("palette")
            prov["palette"] = SRC_ART_DIRECTION
        if getattr(art_direction, "style_preset", ""):
            snap.visual_style = art_direction.style_preset
            known.add("visual_style")
            prov["visual_style"] = SRC_ART_DIRECTION

    # ── VisualContext: окружение, свет, палитра локации ──
    if visual_context is not None:
        env = getattr(visual_context, "environment", None)
        if env is not None:
            if env.time_of_day:
                snap.time_of_day = env.time_of_day
                known.add("time_of_day")
                prov["time_of_day"] = SRC_VISUAL_CONTEXT
            if env.season:
                snap.season = env.season
                known.add("season")
                prov["season"] = SRC_VISUAL_CONTEXT
            if env.weather:
                snap.weather = env.weather
                known.add("weather")
                prov["weather"] = SRC_VISUAL_CONTEXT
        light = getattr(visual_context, "lighting", None)
        if light is not None:
            if light.direction:
                snap.lighting_direction = light.direction
                known.add("lighting")
                prov["lighting"] = SRC_VISUAL_CONTEXT
            if light.color:
                snap.lighting_color = light.color
        loc = getattr(visual_context, "location", None)
        if loc is not None and loc.palette and not snap.palette:
            snap.palette = list(loc.palette)
            known.add("palette")
            prov["palette"] = SRC_VISUAL_CONTEXT

    snap.characters = list(chars.values())

    # ── Сессия Studio: утверждённый кадр, планы ──
    if session is not None:
        snap.has_session = True
        snap.session_id = getattr(session, "session_id", None)
        snap.approved_image_asset_id = getattr(session, "approved_image_asset_id", None)
        if snap.approved_image_asset_id:
            known.add("approved_image")
            prov["approved_image"] = SRC_SESSION
    if scenario is not None and getattr(scenario, "shots", None):
        snap.has_scenario = True
        ordered = sorted(scenario.shots, key=lambda s: s.order)
        snap.shots = [build_shot_snapshot(s) for s in ordered]
        snap.shot_count = len(snap.shots)
        known.add("shots")
        prov["shots"] = SRC_SCENARIO

    snap.known_fields = sorted(known)
    snap.provenance = prov
    return snap


# ── Сравнение ───────────────────────────────────────────────────────────


def _char_index(snap: SceneContinuitySnapshot) -> dict[str, ContinuityCharacterStub]:
    idx: dict[str, ContinuityCharacterStub] = {}
    for c in snap.characters:
        for key in (_norm(c.character_id), _norm(c.name)):
            if key:
                idx.setdefault(key, c)
    return idx


def compare_shots(
    from_shot: ShotContinuitySnapshot,
    to_shot: ShotContinuitySnapshot,
    *,
    relation: str = RELATION_SHOTS,
    from_scene_id: str = "",
    to_scene_id: str = "",
) -> ContinuityLink:
    """Сравнить два соседних плана (свет, палитра, стиль). Отсутствующие — не сравниваются."""
    findings: list[ContinuityFinding] = []
    compared = False

    if _is_known(from_shot.lighting_note) and _is_known(to_shot.lighting_note):
        compared = True
        if _norm(from_shot.lighting_note) != _norm(to_shot.lighting_note):
            findings.append(
                _finding(
                    "lighting",
                    "difference",
                    _SEVERITY_WARNING,
                    "Разное описание света у соседних планов одной сцены",
                    from_shot.lighting_note,
                    to_shot.lighting_note,
                    sources=[SRC_SCENARIO],
                )
            )

    if from_shot.palette_override and to_shot.palette_override:
        compared = True
        if {_norm(p) for p in from_shot.palette_override} != {
            _norm(p) for p in to_shot.palette_override
        }:
            findings.append(
                _finding(
                    "palette",
                    "difference",
                    _SEVERITY_WARNING,
                    "Разная палитра у соседних планов одной сцены",
                    ", ".join(from_shot.palette_override),
                    ", ".join(to_shot.palette_override),
                    sources=[SRC_SCENARIO],
                )
            )

    if _is_known(from_shot.style_override) and _is_known(to_shot.style_override):
        compared = True
        if _norm(from_shot.style_override) != _norm(to_shot.style_override):
            findings.append(
                _finding(
                    "style",
                    "difference",
                    _SEVERITY_WARNING,
                    "Разный локальный стиль у соседних планов одной сцены",
                    from_shot.style_override,
                    to_shot.style_override,
                    sources=[SRC_SCENARIO],
                )
            )

    link_id = f"{relation}:{from_shot.shot_id}->{to_shot.shot_id}"
    if not compared:
        status = STATUS_UNCHECKED
    elif any(f.severity == _SEVERITY_WARNING for f in findings):
        status = STATUS_MISMATCH
    else:
        status = STATUS_CONSISTENT
    return ContinuityLink(
        link_id=link_id,
        link_key=link_id,
        relation=relation,
        from_ref=from_shot.shot_id,
        to_ref=to_shot.shot_id,
        from_scene_id=from_scene_id,
        to_scene_id=to_scene_id,
        status=status,
        findings=findings,
    )


def compare_scenes(
    a: SceneContinuitySnapshot,
    b: SceneContinuitySnapshot,
    *,
    relation: str = RELATION_ADJACENT,
    certainty: str = "confirmed",
    reason: str = "",
) -> ContinuityLink:
    """Сравнить две связанные сцены. Смена места/времени — намеренное отличие (info),
    а не ошибка; предупреждения — только при противоречии внутри одинаковых условий."""
    findings: list[ContinuityFinding] = []
    compared = False

    loc_a, loc_b = _norm(a.location), _norm(b.location)
    same_location = bool(loc_a and loc_b and loc_a == loc_b)

    if _is_known(a.location) and _is_known(b.location):
        compared = True
        if loc_a != loc_b:
            findings.append(
                _finding(
                    "location",
                    "change",
                    _SEVERITY_INFO,
                    "Смена локации между сценами — проверьте, что это намеренно",
                    a.location,
                    b.location,
                    sources=[SRC_GENOME],
                )
            )

    time_changed = False
    if _is_known(a.time_of_day) and _is_known(b.time_of_day):
        compared = True
        if _norm(a.time_of_day) != _norm(b.time_of_day):
            time_changed = True
            findings.append(
                _finding(
                    "time_of_day",
                    "change",
                    _SEVERITY_INFO,
                    "Разное время суток между сценами",
                    a.time_of_day,
                    b.time_of_day,
                    sources=[SRC_VISUAL_CONTEXT],
                )
            )

    if _is_known(a.weather) and _is_known(b.weather):
        compared = True
        if _norm(a.weather) != _norm(b.weather):
            findings.append(
                _finding(
                    "weather",
                    "change",
                    _SEVERITY_INFO,
                    "Разная погода между сценами",
                    a.weather,
                    b.weather,
                    sources=[SRC_VISUAL_CONTEXT],
                )
            )

    if _is_known(a.season) and _is_known(b.season):
        compared = True
        if _norm(a.season) != _norm(b.season):
            findings.append(
                _finding(
                    "season",
                    "change",
                    _SEVERITY_INFO,
                    "Разный сезон между сценами",
                    a.season,
                    b.season,
                    sources=[SRC_VISUAL_CONTEXT],
                )
            )

    # Персонажи, встречающиеся в обеих сценах
    idx_a, idx_b = _char_index(a), _char_index(b)
    shared = sorted(set(idx_a) & set(idx_b))
    for key in shared:
        ca, cb = idx_a[key], idx_b[key]
        subject = cb.name or cb.character_id or key
        if _is_known(ca.appearance) and _is_known(cb.appearance):
            compared = True
            if _norm(ca.appearance) != _norm(cb.appearance):
                findings.append(
                    _finding(
                        "character_appearance",
                        "difference",
                        _SEVERITY_WARNING,
                        f"Разная внешность персонажа «{subject}» в связанных сценах",
                        ca.appearance,
                        cb.appearance,
                        subject=subject,
                        sources=[SRC_VISUAL_CONTEXT],
                    )
                )
        if _is_known(ca.approved_image_asset_id) and _is_known(
            cb.approved_image_asset_id
        ):
            compared = True
            if ca.approved_image_asset_id != cb.approved_image_asset_id:
                findings.append(
                    _finding(
                        "character_approved_image",
                        "difference",
                        _SEVERITY_WARNING,
                        f"У персонажа «{subject}» разные утверждённые образы в связанных сценах",
                        ca.approved_image_asset_id or "",
                        cb.approved_image_asset_id or "",
                        subject=subject,
                        sources=[SRC_ART_DIRECTION],
                    )
                )

    # Противоречия только внутри одинаковых условий (та же локация, то же время)
    if same_location and not time_changed:
        if _is_known(a.lighting_direction) and _is_known(b.lighting_direction):
            compared = True
            if _norm(a.lighting_direction) != _norm(b.lighting_direction):
                findings.append(
                    _finding(
                        "lighting",
                        "difference",
                        _SEVERITY_WARNING,
                        "Одинаковая локация и время, но разное направление света",
                        a.lighting_direction,
                        b.lighting_direction,
                        sources=[SRC_VISUAL_CONTEXT],
                    )
                )
        if a.palette and b.palette:
            compared = True
            if {_norm(p) for p in a.palette} != {_norm(p) for p in b.palette}:
                findings.append(
                    _finding(
                        "palette",
                        "difference",
                        _SEVERITY_WARNING,
                        "Одинаковая локация, но разная палитра между сценами",
                        ", ".join(a.palette),
                        ", ".join(b.palette),
                        sources=[SRC_ART_DIRECTION],
                    )
                )
        if _is_known(a.visual_style) and _is_known(b.visual_style):
            compared = True
            if _norm(a.visual_style) != _norm(b.visual_style):
                findings.append(
                    _finding(
                        "visual_style",
                        "difference",
                        _SEVERITY_WARNING,
                        "Разный визуальный стиль между связанными сценами",
                        a.visual_style,
                        b.visual_style,
                        sources=[SRC_ART_DIRECTION],
                    )
                )

    link_id = f"{relation}:{a.scene_id}->{b.scene_id}"
    if not compared:
        status = STATUS_UNCHECKED
    elif any(f.severity == _SEVERITY_WARNING for f in findings):
        status = STATUS_MISMATCH
    else:
        status = STATUS_CONSISTENT
    return ContinuityLink(
        link_id=link_id,
        link_key=link_id,
        relation=relation,
        certainty=certainty,
        reason=reason,
        from_ref=a.scene_id,
        to_ref=b.scene_id,
        from_scene_id=a.scene_id,
        to_scene_id=b.scene_id,
        status=status,
        findings=findings,
    )


def cross_episode_candidates(
    scene: dict, all_scenes: list[dict], order_by_id: dict[str, int]
) -> list[tuple[str, str]]:
    """Кандидаты смысловой связи сцен разных эпизодов.

    Основание — явные meaning_tags генома (авторская разметка), а не догадка.
    Возвращает список (other_scene_id, общий_тег) для сцен другого эпизода.
    НЕ создаёт связь, если общих тегов нет.
    """
    my_chapter = scene.get("chapter", 0)
    my_tags = {_norm(t) for t in (scene.get("meaning_tags") or []) if _norm(t)}
    if not my_tags:
        return []
    result: list[tuple[str, str]] = []
    for other in all_scenes:
        if other is scene:
            continue
        other_id = other.get("scene_id", other.get("id", ""))
        if not other_id or other.get("chapter", 0) == my_chapter:
            continue
        shared = my_tags & {
            _norm(t) for t in (other.get("meaning_tags") or []) if _norm(t)
        }
        if shared:
            result.append((other_id, sorted(shared)[0]))
    return result


def clip_boundary_for(
    a: SceneContinuitySnapshot, b: SceneContinuitySnapshot
) -> ClipBoundaryContract:
    """Контракт связи клипов A→B. Заполняются только существующие идентификаторы."""
    end_frame = a.approved_image_asset_id or (
        a.shots[-1].approved_image_asset_id if a.shots else None
    )
    start_frame = b.approved_image_asset_id or (
        b.shots[0].approved_image_asset_id if b.shots else None
    )
    status = "declared" if (end_frame or start_frame) else "unknown"
    return ClipBoundaryContract(
        previous_clip_asset_id=None,
        end_frame_asset_id=end_frame,
        next_clip_asset_id=None,
        start_frame_asset_id=start_frame,
        status=status,
        note=(
            "Контракт связи клипов: end frame предыдущего клипа должен совпасть с start frame "
            "следующего. Содержимое кадров не проверяется — только объявленные утверждённые кадры."
        ),
    )


def transfer_constraints(prev: SceneContinuitySnapshot) -> tuple[dict, dict]:
    """Ограничения, переносимые из связанной сцены в текущую (Фаза 2).

    Возвращает (constraints, sources). Только фактически известные
    характеристики — неизвестные НЕ подменяются. Это то же множество, что
    показывает предпросмотр «Согласовать со сценой».
    """
    constraints: dict = {}
    sources: dict = {}
    if prev.location:
        constraints["location"] = prev.location
        sources["location"] = prev.provenance.get("location", "")
    if prev.time_of_day:
        constraints["time_of_day"] = prev.time_of_day
        sources["time_of_day"] = prev.provenance.get("time_of_day", "")
    if prev.lighting_direction:
        constraints["lighting"] = prev.lighting_direction
        sources["lighting"] = prev.provenance.get("lighting", "")
    if prev.palette:
        constraints["palette"] = list(prev.palette)
        sources["palette"] = prev.provenance.get("palette", "")
    char_names = [
        c.name or c.character_id for c in prev.characters if (c.name or c.character_id)
    ]
    if char_names:
        constraints["characters"] = char_names
        sources["characters"] = "genome/visual_context"
    if prev.visual_style:
        constraints["visual_style"] = prev.visual_style
        sources["visual_style"] = prev.provenance.get("visual_style", "")
    return constraints, sources


def applied_link_key(scene_id: str) -> str:
    """Стабильный ключ применённого переноса для сцены-приёмника."""
    return f"{APPLY_PREFIX}:{scene_id}"


def find_applied_decision(
    decisions: list[ContinuityDecision], scene_id: str, basis: dict
) -> tuple[ContinuityDecision | None, bool]:
    """Найти действующее решение о переносе для сцены.

    Возвращает (решение, устарело). Устаревшее решение НЕ применяется
    (нельзя молча использовать устаревший контекст), но факт устаревания
    сообщается (stale=True) — режиссёр подтверждает перенос заново.
    """
    key = applied_link_key(scene_id)
    decision: ContinuityDecision | None = None
    for d in decisions:
        if d.link_key == key and d.action == ACTION_APPLIED:
            decision = d  # последнее по времени (список отсортирован по created_at)
    if decision is None:
        return None, False
    if decision_is_stale(decision, basis):
        return None, True
    return decision, False


def make_basis(
    *,
    scene_id: str,
    art_direction_revision: int,
    from_approved: str | None = None,
    to_approved: str | None = None,
) -> dict:
    """Отпечаток контекста связи для выявления устаревших решений.

    Меняется при новом утверждённом кадре (from/to) или при росте общих
    правил (revision) — тогда решение режиссёра помечается устаревшим.
    """
    return {
        "scene_id": scene_id,
        "art_direction_revision": int(art_direction_revision or 0),
        "from_approved": from_approved or "",
        "to_approved": to_approved or "",
    }


def decision_is_stale(decision: ContinuityDecision, basis: dict) -> bool:
    """Решение устарело, если контекст изменился после его принятия."""
    if not basis:
        return False
    stored = decision.basis or {}
    return any(stored.get(k) != basis.get(k) for k in basis)


def make_apply_basis(*, scene_id: str, art_direction_revision: int) -> dict:
    """Отпечаток контекста ПРИМЕНЁННОГО переноса (Фаза 2).

    Переносимые ограничения (локация/время/свет/палитра/персонажи/стиль) не
    зависят от утверждённых кадров, но зависят от общих правил фильма
    (revision): их изменение делает перенос устаревшим и требует
    подтверждения заново.
    """
    return {
        "scene_id": scene_id,
        "art_direction_revision": int(art_direction_revision or 0),
    }


def apply_decisions(
    links: list[ContinuityLink],
    decisions_by_key: dict[str, ContinuityDecision],
) -> None:
    """Применить сохранённые решения к связям (мутирует links)."""
    for link in links:
        decision = decisions_by_key.get(link.link_key)
        if decision is None:
            continue
        decision.stale = decision_is_stale(decision, link.basis)
        link.decision = decision
        if decision.stale:
            continue  # устаревшее решение связь не закрывает
        if link.status in (STATUS_MISMATCH, STATUS_CONSISTENT) or link.findings:
            link.status = STATUS_WAIVED


def mark_candidate(link: ContinuityLink) -> None:
    """Пометить связь как кандидата: отличия показываются, но не считаются
    несоответствием (ложные предупреждения по слабой связи исключены)."""
    link.certainty = "candidate"
    for finding in link.findings:
        finding.severity = _SEVERITY_INFO
        finding.certainty = "candidate"
    link.status = STATUS_CONSISTENT if link.findings else STATUS_UNCHECKED


def overall_status(links: list[ContinuityLink]) -> str:
    if not links:
        return STATUS_UNCHECKED
    if any(link.status == STATUS_MISMATCH for link in links):
        return STATUS_MISMATCH
    if any(link.status == STATUS_WAIVED for link in links):
        return STATUS_WAIVED
    if any(link.status == STATUS_CONSISTENT for link in links):
        return STATUS_CONSISTENT
    return STATUS_UNCHECKED
