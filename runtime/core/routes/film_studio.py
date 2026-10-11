"""Film Studio — API эндпоинты для проектов фильмов (/book/film/*).

НОВАЯ ГРАНИЦА (Arkaim Media Boundary): Film Studio в Arkaim НЕ генерирует
и НЕ собирает видео. Она работает со сценами/шотами и их Prompt Packages
(см. MediaPlan v0). Исполнение генерации/сборки целиком принадлежит внешнему
media-проекту (arkaim-media). Arkaim лишь готовит смысловой план (MediaPlan)
и хранит метаданные шотов.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse

from core.dto.responses import SuccessResponse
from auth.rbac import require_role

log = logging.getLogger("routes.film_studio")

router = APIRouter(
    tags=["Film Studio"],
    dependencies=[Depends(require_role("editor"))],
)


def _get_store():
    from core.adc_deps import registry

    return registry.get("film_store")


# ── Projects ──────────────────────────────────────────


@router.post("/film/create", summary="Создать проект фильма")
async def create_project(
    title: str = Query(..., min_length=1),
    description: str = Query(""),
    style: str = Query("cinematic_fantasy"),
    mood: str = Query("neutral"),
    aspect_ratio: str = Query("16:9"),
    fps: int = Query(24, ge=12, le=60),
):
    store = _get_store()
    project = await store.create_project(
        title=title,
        description=description,
        style=style,
        mood=mood,
        aspect_ratio=aspect_ratio,
        fps=fps,
    )
    return SuccessResponse(data=project.model_dump(mode="json"))


@router.get("/film/list", summary="Список проектов")
async def list_projects(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    store = _get_store()
    projects = await store.list_projects(limit=limit, offset=offset)
    return SuccessResponse(data=[p.model_dump(mode="json") for p in projects])


@router.get("/film/{project_id}", summary="Детали проекта")
async def get_project(project_id: str):
    store = _get_store()
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return SuccessResponse(data=project.model_dump(mode="json"))


@router.put("/film/{project_id}", summary="Обновить проект")
async def update_project(
    project_id: str,
    title: str | None = Query(None),
    description: str | None = Query(None),
    style: str | None = Query(None),
    mood: str | None = Query(None),
    aspect_ratio: str | None = Query(None),
    fps: int | None = Query(None),
):
    store = _get_store()
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if description is not None:
        kwargs["description"] = description
    if style is not None:
        kwargs["style"] = style
    if mood is not None:
        kwargs["mood"] = mood
    if aspect_ratio is not None:
        kwargs["aspect_ratio"] = aspect_ratio
    if fps is not None:
        kwargs["fps"] = fps
    if not kwargs:
        raise HTTPException(400, "No fields to update")
    if not await store.update_project(project_id, **kwargs):
        raise HTTPException(404, "Project not found")
    project = await store.get_project(project_id)
    return SuccessResponse(data=project.model_dump(mode="json"))


@router.delete("/film/{project_id}", summary="Удалить проект")
async def delete_project(project_id: str):
    store = _get_store()
    if not await store.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return SuccessResponse(data={"deleted": project_id})


@router.get("/film/{project_id}/output", summary="Скачать собранное видео")
async def download_output(project_id: str):
    """Скачать assembled video файл проекта (если он был получен извне)."""
    from fastapi.responses import FileResponse

    store = _get_store()
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.output_path:
        raise HTTPException(404, "Output not found — assemble the project in the external media project first")
    import os

    if not os.path.exists(project.output_path):
        raise HTTPException(404, "Output file not found on disk")
    return FileResponse(project.output_path, media_type="video/mp4", filename=f"{project.title}.mp4")


# ── Scenes ────────────────────────────────────────────


@router.post("/film/{project_id}/scenes", summary="Добавить сцену в проект")
async def add_scene(
    project_id: str,
    scene_id: str = Query(..., min_length=1),
    order: int = Query(0),
    duration_sec: float = Query(3.0, gt=0),
):
    store = _get_store()
    project = await store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    scene = await store.add_scene(
        project_id=project_id,
        scene_id=scene_id,
        order=order,
        duration_sec=duration_sec,
    )
    if not scene:
        raise HTTPException(500, "Failed to add scene")
    return SuccessResponse(data=scene.model_dump(mode="json"))


@router.delete("/film/{project_id}/scenes/{scene_db_id}", summary="Удалить сцену из проекта")
async def delete_scene(project_id: str, scene_db_id: str):
    store = _get_store()
    if not await store.delete_scene(scene_db_id):
        raise HTTPException(404, "Scene not found")
    return SuccessResponse(data={"deleted": scene_db_id})


@router.put("/film/{project_id}/scenes/{scene_db_id}", summary="Обновить сцену")
async def update_scene(
    project_id: str,
    scene_db_id: str,
    order: int | None = Query(None),
    duration_sec: float | None = Query(None, gt=0),
    prompt_override: str | None = Query(None),
):
    store = _get_store()
    scene = await store.get_scene(scene_db_id)
    if not scene:
        raise HTTPException(404, "Scene not found")
    kwargs = {}
    if order is not None:
        kwargs["sort_order"] = order
    if duration_sec is not None:
        kwargs["duration_sec"] = duration_sec
    if prompt_override is not None:
        kwargs["prompt_override"] = prompt_override
    if not kwargs:
        raise HTTPException(400, "No fields to update")
    await store.update_scene(scene_db_id, **kwargs)
    scene = await store.get_scene(scene_db_id)
    return SuccessResponse(data=scene.model_dump(mode="json"))


# ── Shots ─────────────────────────────────────────────


@router.post("/film/{project_id}/scenes/{scene_db_id}/shots", summary="Добавить шот")
async def add_shot(
    project_id: str,
    scene_db_id: str,
    prompt: str = Query(""),
    duration_sec: float = Query(3.0, gt=0),
    camera_shot_type: str = Query("medium_shot"),
    camera_angle: str = Query("eye_level"),
    camera_motion: str = Query("static"),
):
    store = _get_store()
    from film_studio.schemas import CameraSpec, CameraMotion

    try:
        motion = CameraMotion(camera_motion)
    except ValueError:
        motion = CameraMotion.STATIC
    camera = CameraSpec(
        shot_type=camera_shot_type,
        angle=camera_angle,
        motion=motion,
    )
    shot = await store.add_shot(
        scene_id=scene_db_id,
        project_id=project_id,
        prompt=prompt,
        camera=camera,
        duration_sec=duration_sec,
    )
    if not shot:
        raise HTTPException(500, "Failed to add shot")
    return SuccessResponse(data=shot.model_dump(mode="json"))


@router.post("/film/{project_id}/scenes/{scene_db_id}/shots/new-version", summary="Новая версия шота")
async def create_shot_version(
    project_id: str,
    scene_db_id: str,
    prompt: str = Query(""),
    duration_sec: float = Query(3.0, gt=0),
    camera_shot_type: str = Query("medium_shot"),
    camera_angle: str = Query("eye_level"),
    camera_motion: str = Query("static"),
):
    store = _get_store()
    from film_studio.schemas import CameraSpec, CameraMotion

    try:
        motion = CameraMotion(camera_motion)
    except ValueError:
        motion = CameraMotion.STATIC
    camera = CameraSpec(
        shot_type=camera_shot_type,
        angle=camera_angle,
        motion=motion,
    )
    shot = await store.create_shot_version(
        scene_id=scene_db_id,
        project_id=project_id,
        prompt=prompt,
        camera=camera,
        duration_sec=duration_sec,
    )
    return SuccessResponse(data=shot.model_dump(mode="json"))


@router.put("/film/shots/{shot_id}/activate", summary="Активировать версию шота")
async def activate_shot(shot_id: str):
    store = _get_store()
    if not await store.activate_shot(shot_id):
        raise HTTPException(404, "Shot not found")
    return SuccessResponse(data={"activated": shot_id})


@router.delete("/film/shots/{shot_id}", summary="Удалить шот")
async def delete_shot(shot_id: str):
    store = _get_store()
    if not await store.delete_shot(shot_id):
        raise HTTPException(404, "Shot not found")
    return SuccessResponse(data={"deleted": shot_id})


@router.put("/film/shots/{shot_id}", summary="Обновить шот")
async def update_shot(
    shot_id: str,
    prompt: str | None = Query(None),
    duration_sec: float | None = Query(None, gt=0),
    camera_shot_type: str | None = Query(None),
    camera_angle: str | None = Query(None),
    camera_motion: str | None = Query(None),
    quality: str | None = Query(None, pattern="^(draft|standard|high|ultra)$"),
):
    store = _get_store()
    kwargs = {}
    if prompt is not None:
        kwargs["prompt"] = prompt
    if duration_sec is not None:
        kwargs["duration_sec"] = duration_sec
    if quality is not None:
        kwargs["quality"] = quality
    if camera_shot_type is not None or camera_angle is not None or camera_motion is not None:
        from film_studio.schemas import CameraSpec, CameraMotion

        cam = CameraSpec(
            shot_type=camera_shot_type or "medium_shot",
            angle=camera_angle or "eye_level",
            motion=CameraMotion(camera_motion) if camera_motion else CameraMotion.STATIC,
        )
        kwargs["camera"] = cam
    if not kwargs:
        raise HTTPException(400, "No fields to update")
    if not await store.update_shot(shot_id, **kwargs):
        raise HTTPException(404, "Shot not found")
    return SuccessResponse(data={"updated": shot_id})


# ── Stats ─────────────────────────────────────────────


@router.get("/film/{project_id}/stats", summary="Статистика проекта")
async def get_stats(project_id: str):
    store = _get_store()
    stats = await store.get_project_stats(project_id)
    return SuccessResponse(data=stats)
