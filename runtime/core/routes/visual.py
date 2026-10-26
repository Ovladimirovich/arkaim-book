"""Visual Genome — эндпоинты подготовки визуальных промптов (/book/visual-*).

НОВАЯ ГРАНИЦА (Arkaim Media Boundary): Arkaim НЕ генерирует изображения и
видео. Эти эндпоинты только готовят смысловые данные (SceneContext → MediaPlan,
Prompt Package) из контекстов книги. Исполнение генерации принадлежит внешнему
media-проекту (arkaim-media). Локальных ComfyUI/провайдеров и очередей здесь нет.
"""

import logging

from fastapi import APIRouter, HTTPException, Depends, Body

from auth.rbac import require_role
from core.dto.requests import (
    VisualSceneRequest,
    VisualCharacterRequest,
    VisualLocationRequest,
    VisualFromSpeechRequest,
    VisualizeRequest,
    EpochVisualRequest,
)
from core.dto.responses import SuccessResponse
from core.adc_deps import get_config, get_voice, get_scene_engine
from core.routes.book import _load_genome_full, _save_genome

log = logging.getLogger("hermes.routes.visual")

router = APIRouter(tags=["Visual Genome"])


def _edm_res_pilot_enabled() -> bool:
    """OWNER-GATE для EDM-RES пилота (/book/ask и /visualize).

    По умолчанию выключено: без флага /visualize byte-идентичен legacy
    (нет ключа `edm`, SceneContext не наполняется из EDM). Флаг читается
    на каждом вызове (dev-переключение без перезапуска, паттерн
    _stage2_enabled из routes/book.py).
    """
    try:
        from shared_config import settings as shared_settings

        return bool(getattr(shared_settings, "EDM_RES_PILOT_ENABLED", False))
    except Exception as exc:  # pragma: no cover - конфиг всегда доступен
        log.warning("edm_res_pilot_gate_check_failed error=%s", exc)
        return False


@router.post("/visualize", summary="Подготовить Prompt Package сцены (без генерации)")
async def visualize_scene(
    req: VisualizeRequest,
    scene_engine=Depends(get_scene_engine),
):
    """Подготовка Prompt Package (MediaPlan) из сцены книги.

    НОВАЯ ГРАНИЦА: Arkaim НЕ генерирует изображение. Endpoint строит
    канонический SceneContext и возвращает MediaPlan (Prompt Package),
    который затем передаётся во внешний media-проект. Исполнение
    генерации — за пределами Arkaim.

    EDM-RES пилот (OWNER-GATE, флаг выключен по умолчанию): при
    EDM_RES_PILOT_ENABLED SceneContext НАПОЛНЯЕТСЯ из совпавших EDM-
    сущностей ДО постройки плана: architecture/landscape/environment —
    только существующие поля, weather/season → явный UNKNOWN вместо
    fail-open дефолта "clear"; прувенанс — в блоке `edm` ответа и в
    source_refs ("edm:<entity_id>"). Сущности можно задать явно —
    req.edm_entity_ids (определяющий пилотный вход). E2 авто-матчинг:
    location-строка сцены автоматически разрешается через engine/crosswalk
    (region_*) → EDM-карточки + трасса `edm.location_matched`. Флаг выключен —
    ответ byte-identичен legacy (нет ключа `edm`).

    E3: chapter=0 (CATALOG_CHAPTER) — каталог-сцена киносценария: сцена →
    resolve_scene_location → EDM location match → VisualContext → MediaPlan
    (существующие механизмы engine/builder; несуществующие id — 404, без
    подстановки отсутствующих фактов). Сцены книги — chapter>=1, семантика без
    изменений.
    """
    from core.adc_deps import registry
    from media_plan import MediaPlanBuilder

    # Канонический SceneContext (единый смысловой вход MD-2, read-only).
    visual_ctx_builder = registry.get("visual_context_builder")
    ctx = await visual_ctx_builder.build_scene_context(req.chapter, req.scene_id)

    # 404-контракт прежний: сцена обязана существовать в genome/RAG.
    scene = scene_engine.get_scene(req.chapter, req.scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    # EDM-RES пилот: наполнение SceneContext из EDM ДО постройки плана
    # (единый canonical ctx, план строится из уже наполненного контекста).
    edm_report = None
    if _edm_res_pilot_enabled():
        try:
            from core.services import edm_pilot

            # E2 авто-матчинг: location-строка сцены → engine/crosswalk →
            # region_* → EDM (детерминированно, fail-closed; сбой моста не
            # ломает legacy-путь — strict-матчинг ниже остаётся).
            loc_match = edm_pilot.resolve_scene_location(
                ctx.scene.location,
                location_id=ctx.location.location_id,
                location_name=ctx.location.name,
            )
            edm_report = edm_pilot.apply_edm_to_context(
                ctx,
                location_id=ctx.location.location_id,
                location_name=ctx.location.name,
                scene_location=ctx.scene.location,
                explicit_ids=req.edm_entity_ids or None,
                auto_matched_ids=loc_match["entity_ids"] or None,
                location_matched=loc_match if loc_match["entity_ids"] else None,
            )
            if edm_report.get("applied"):
                log.info("edm_pilot_applied entity_ids=%s", edm_report.get("entity_ids"))
        except Exception as exc:
            # Сбой пилота не ломает legacy-путь: план строится из ctx как есть.
            log.warning("edm_pilot_apply_failed scene_id=%s error=%s", req.scene_id, exc)

    # Канонический смысловой план из SceneContext — единственный выход в media-контур.
    plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
        ctx,
        intent="key_frame",
        created_from="scene_context",
    )
    result: dict = {"media_plan": plan.model_dump(mode="json")}
    # Блок `edm` появляется при НАСТОЯЩЕЙ мутации ctx (applied) ИЛИ при
    # E2-трассе авто-матчинга (location_matched: кандидаты есть, применимых
    # Claim'ов нет — plan legacy, но разрешённые сущности видны). Флаг off —
    # блок не появляется (legacy-контракт).
    if _edm_res_pilot_enabled() and edm_report and (edm_report.get("applied") or edm_report.get("location_matched")):
        result["edm"] = edm_report
    return result


@router.post(
    "/visualize/epoch/{epoch_id}",
    summary="Подготовить Prompt Package эпохи (без генерации)",
)
async def visualize_epoch(
    epoch_id: str,
    req: EpochVisualRequest = Body(EpochVisualRequest()),
):
    """Подготовка Prompt Package (MediaPlan) из временной модели (M7.2).

    WorldModel temporal context → SceneContext → MediaPlan. Не мутирует
    каноническое состояние. Исполнение генерации — за пределами Arkaim.
    """
    from core.adc_deps import registry
    from media_plan import MediaPlanBuilder

    visual_ctx_builder = registry.get("visual_context_builder")
    ctx = await visual_ctx_builder.build_scene_context_for_epoch(epoch_id)

    # 404-контракт: эпоха обязана существовать в WorldModel.
    temporal = ctx.scene_extras.temporal
    if not temporal.is_temporal:
        raise HTTPException(404, detail=f"Epoch '{epoch_id}' not found")

    plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
        ctx,
        intent="era_establishing",
        created_from="epoch",
    )
    return {"media_plan": plan.model_dump(mode="json")}


@router.post("/visual-genome/scene", response_model=SuccessResponse, dependencies=[Depends(require_role("editor"))])
async def save_visual_scene(req: VisualSceneRequest, config=Depends(get_config)):
    genome = _load_genome_full(config)
    modules = genome.setdefault("modules", {})
    scenes = modules.setdefault("scenes", [])
    scene_id = f"ui_scene_{len(scenes) + 1:03d}"
    scene = {
        "chapter": req.chapter,
        "scene_id": scene_id,
        "title": req.title,
        "characters": req.characters,
        "location": req.location,
        "emotion": req.emotion,
        "meaning_tags": req.meaning_tags,
        "color_palette": req.color_palette or None,
        "source": "ui_form",
    }
    scenes.append(scene)
    _save_genome(genome, config)
    return SuccessResponse(data={"scene_id": scene_id, "scene": scene})


@router.post("/visual-genome/character", response_model=SuccessResponse, dependencies=[Depends(require_role("editor"))])
async def save_visual_character(req: VisualCharacterRequest, config=Depends(get_config)):
    genome = _load_genome_full(config)
    modules = genome.setdefault("modules", {})
    visuals = modules.setdefault("character_visuals", [])
    palette = [v for v in req.color_palette if v] if req.color_palette else ["earth tones"]
    visual = {
        "character_id": req.character_id,
        "name": req.name,
        "archetype": req.archetype,
        "color_palette": palette,
        "visual_description": req.visual_description,
        "source": "ui_form",
    }
    for i, v in enumerate(visuals):
        if v.get("character_id") == req.character_id:
            visuals[i] = visual
            break
    else:
        visuals.append(visual)
    _save_genome(genome, config)
    return SuccessResponse(data=visual)


@router.post("/visual-genome/location", response_model=SuccessResponse, dependencies=[Depends(require_role("editor"))])
async def save_visual_location(req: VisualLocationRequest, config=Depends(get_config)):
    genome = _load_genome_full(config)
    modules = genome.setdefault("modules", {})
    visuals = modules.setdefault("location_visuals", [])
    visual = {
        "location_id": req.location_id,
        "name": req.name,
        "atmosphere": req.atmosphere or "нейтральная",
        "architecture": req.architecture or "не описана",
        "lighting": req.lighting or "естественный",
    }
    for i, v in enumerate(visuals):
        if v.get("location_id") == req.location_id:
            visuals[i] = visual
            break
    else:
        visuals.append(visual)
    _save_genome(genome, config)
    return SuccessResponse(data=visual)


@router.post("/visual-genome/from-speech", response_model=SuccessResponse, dependencies=[Depends(require_role("editor"))])
async def visual_from_speech(req: VisualFromSpeechRequest, config=Depends(get_config), voice=Depends(get_voice)):
    """Голосовой ввод — LLM преобразует описание в Visual Genome."""
    if not hasattr(voice, "extract_visual_from_speech"):
        raise HTTPException(501, "Голосовой ввод не поддерживается")

    try:
        result = await voice.extract_visual_from_speech(req.text)
        if result:
            genome = _load_genome_full(config)
            modules = genome.setdefault("modules", {})
            if "scenes" in result:
                modules.setdefault("scenes", []).extend(result["scenes"])
            if "character_visuals" in result:
                modules.setdefault("character_visuals", []).extend(result["character_visuals"])
            if "location_visuals" in result:
                modules.setdefault("location_visuals", []).extend(result["location_visuals"])
            _save_genome(genome, config)
            scene = result.get("scenes", [None])[0] if result.get("scenes") else None
            return SuccessResponse(data=scene)
        raise HTTPException(422, "Не удалось распознать визуальные элементы")
    except HTTPException:
        raise
    except Exception as e:
        log.error("visual_from_speech_error: %s", e)
        raise HTTPException(500, "Ошибка обработки")


# ── Studio Preparation (Phase 1A) ──────────────────────────────────────────


@router.post(
    "/studio-describe",
    summary="Подготовить три описания сцены для Studio",
)
async def studio_describe(
    req: VisualizeRequest,
    scene_engine=Depends(get_scene_engine),
):
    """Подготовка трёх описаний сцены для Studio.

    Возвращает:
      - image_description: MediaPlan (media_kind="image") — Image Description
      - video_description: MediaPlan (media_kind="video") — Video Description
      - video_scenario: VideoScenario — Full Video Scenario

    Это НЕ Studio-session endpoint (Phase 1A — только описание системы).
    Arkaim НЕ генерирует media. Endpoint строит три смысловых описания
    из canonical SceneContext через существующую систему описаний.
    """
    from core.adc_deps import registry
    from media_plan import MediaPlanBuilder
    from studio.scenario_builder import VideoScenarioBuilder
    from visual.video_intelligence import VideoIntelligence

    # 1. Canonical SceneContext
    visual_ctx_builder = registry.get("visual_context_builder")
    ctx = await visual_ctx_builder.build_scene_context(req.chapter, req.scene_id)

    scene = scene_engine.get_scene(req.chapter, req.scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    # 2. A. Image Description — existing pipeline
    image_plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
        ctx,
        intent="key_frame",
        created_from="scene_context",
    )

    # 3. B. Video Description — existing VideoIntelligence, connected to production
    vi = VideoIntelligence()
    video_ctx = vi.create_video_context(ctx)
    video_plan = MediaPlanBuilder(generator="comfyui").build_video_plan(
        video_ctx,
        intent="video_clip",
        duration_sec=video_ctx.duration_sec,
        fps=video_ctx.fps,
    )

    # 4. C. Full Video Scenario — new VideoScenarioBuilder
    scenario_builder = VideoScenarioBuilder(video_intelligence=vi)
    scenario = scenario_builder.build(ctx, duration_sec=30.0)

    return {
        "image_description": image_plan.model_dump(mode="json"),
        "video_description": video_plan.model_dump(mode="json"),
        "video_scenario": scenario.to_dict(),
    }
