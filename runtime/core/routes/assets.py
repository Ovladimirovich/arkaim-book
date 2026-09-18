"""Visual Assets — эндпоинты хранения ассетов (/book/assets/*).

НОВАЯ ГРАНИЦА (Arkaim Media Boundary): Arkaim НЕ генерирует изображения и видео.
Этот модуль отвечает только за хранение ассетов (включая пользовательские
reference-изображения для Studio) и за подготовку Prompt Package (MediaPlan)
из SceneContext. Исполнение генерации принадлежит внешнему media-проекту
(arkaim-media). Локальных пайплайнов/очередей/провайдеров здесь нет.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse

from auth.rbac import require_role
from core.dto.responses import SuccessResponse

log = logging.getLogger("routes.assets")

router = APIRouter(
    tags=["Visual Assets"],
    dependencies=[Depends(require_role("reader"))],
)


def _get_asset_store():
    from core.adc_deps import registry
    return registry.get("asset_store")


# ── Подготовка Prompt Package (без генерации) ─────────────

@router.post("/assets/generate-context", dependencies=[Depends(require_role("editor"))], summary="Подготовить MediaPlan из SceneContext (без генерации)")
async def prepare_asset_context(
    chapter: int = Query(..., ge=1),
    scene_id: str = Query(..., min_length=1),
    asset_type: str = Query("image", pattern="^(image|video)$"),
    style: str = Query("cinematic_fantasy"),
):
    """Канонический вход подготовки (MD-2/MD-3.2): SceneContext → MediaPlan.

    НОВАЯ ГРАНИЦА: возвращает готовый Prompt Package (MediaPlan) и НЕ запускает
    генерацию. Исполнение — за пределами Arkaim (media-проект).
    """
    from core.adc_deps import registry
    from media_plan import MediaPlanBuilder

    # Канонический SceneContext — единый смысловой вход генерации.
    visual_ctx_builder = registry.get("visual_context_builder")
    ctx = await visual_ctx_builder.build_scene_context(chapter, scene_id)

    intent = "key_frame" if asset_type == "image" else "video_clip"
    plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
        ctx, intent=intent, created_from="scene_context",
        style_override=style, custom_prompt=None,
    )
    return {"media_plan": plan.model_dump(mode="json")}


# ── Просмотр ──────────────────────────────────────────────

@router.get("/assets", summary="Список ассетов")
async def list_assets(
    chapter: int | None = Query(None, ge=1),
    asset_type: str | None = Query(None, pattern="^(image|video)$"),
    status: str | None = Query(None, pattern="^(pending|generating|completed|failed)$"),
    scene_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Получить список ассетов (включая reference-изображения)."""
    try:
        from visual_assets.schemas import AssetType, AssetStatus

        store = _get_asset_store()
        at = AssetType(asset_type) if asset_type else None
        st = AssetStatus(status) if status else None
        assets = await store.list_assets(chapter=chapter, asset_type=at, status=st, scene_id=scene_id, limit=limit, offset=offset)
        return SuccessResponse(data=[a.model_dump(mode="json") for a in assets])
    except Exception as e:
        log.error("list_assets_error: %s", e)
        raise HTTPException(500, f"Ошибка: {e}")


@router.get("/assets/{asset_id}", summary="Метаданные ассета")
async def get_asset(asset_id: str):
    """Получить метаданные конкретного ассета."""
    store = _get_asset_store()
    asset = await store.get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return SuccessResponse(data=asset.model_dump(mode="json"))


@router.get("/assets/{asset_id}/file", summary="Файл ассета")
async def get_asset_file(asset_id: str):
    """Скачать файл ассета (изображение или видео)."""
    store = _get_asset_store()
    asset = await store.get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    file_path = store.get_file_path(asset)
    if not file_path:
        raise HTTPException(404, "File not found")

    media_type = "image/png" if asset.asset_type.value == "image" else "video/mp4"
    return FileResponse(str(file_path), media_type=media_type)


@router.get("/assets/{asset_id}/thumbnail", summary="Thumbnail ассета")
async def get_asset_thumbnail(asset_id: str):
    """Получить thumbnail ассета."""
    store = _get_asset_store()
    asset = await store.get(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    thumb_path = store.get_thumbnail_path(asset)
    if not thumb_path:
        raise HTTPException(404, "Thumbnail not found")

    return FileResponse(str(thumb_path), media_type="image/png")


# ── Управление ──────────────────────────────────────────

@router.delete("/assets/{asset_id}", dependencies=[Depends(require_role("admin"))], summary="Удалить ассет")
async def delete_asset(asset_id: str):
    """Удалить ассет и его файлы."""
    store = _get_asset_store()
    if not await store.delete(asset_id):
        raise HTTPException(404, "Asset not found")
    return SuccessResponse(data={"deleted": asset_id})


@router.post("/assets/delete-all", dependencies=[Depends(require_role("admin"))], summary="Удалить все ассеты (пакетное удаление)")
async def delete_all_assets(
    chapter: int | None = Query(None, ge=1),
    asset_type: str | None = Query(None, pattern="^(image|video)$"),
    status: str | None = Query(None, pattern="^(pending|generating|completed|failed)$"),
):
    """Удалить ассеты по фильтрам. Без фильтров — удалить все."""
    from visual_assets.schemas import AssetType, AssetStatus
    store = _get_asset_store()
    at = AssetType(asset_type) if asset_type else None
    st = AssetStatus(status) if status else None
    assets = await store.list_assets(chapter=chapter, asset_type=at, status=st, limit=10000)
    deleted = 0
    for asset in assets:
        await store.delete(asset.asset_id)
        deleted += 1
    return SuccessResponse(data={"deleted": deleted})
