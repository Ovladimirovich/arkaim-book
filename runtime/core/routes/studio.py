"""Studio API — endpoints для Studio v2 (Phase 1B).

Эндпоинты Studio: сессии, discussion, версии, reference, финализация, export.

Studio НЕ генерирует описания — получает три результата от Arkaim Description System
(через /visual/studio-describe). Затем позволяет пользователю обсуждать, корректировать,
создавать варианты и финализировать.

RBAC: editor + admin (Studio = инструмент автора).
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form

from auth.rbac import require_role
from core.dto.responses import SuccessResponse
from core.adc_deps import registry
from studio.session_models import UserModification

log = logging.getLogger("hermes.routes.studio")

router = APIRouter(prefix="/studio", tags=["Studio"])


def _get_store():
    from studio.store import StudioStore
    return StudioStore()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ── 0. Available scenes ─────────────────────────────────────────


@router.get("/scenes", summary="Список доступных сцен для создания Studio-сессии")
async def list_scenes():
    """Возвращает сцены из генома книги, доступные для Studio."""
    from core.routes.book import _get_genome_data
    genome = _get_genome_data()
    if not genome:
        return SuccessResponse(data=[])
    scenes = genome.get("modules", {}).get("scenes", [])
    result = []
    for s in scenes:
        result.append({
            "scene_id": s.get("scene_id", s.get("id", "")),
            "chapter": s.get("chapter", 1),
            "title": s.get("title", ""),
        })
    return SuccessResponse(data=result)


# ── 1. Create session ────────────────────────────────────────────


@router.post("/create", summary="Создать Studio-сессию из сцены")
async def create_session(
    chapter: int,
    scene_id: str,
    user: dict = Depends(require_role("editor")),
):
    """Создать Studio-сессию. Получает три описания от Arkaim Description System.

    Вызывает /visual/studio-describe pipeline для получения:
    - Image Description (MediaPlan, media_kind="image")
    - Video Description (MediaPlan, media_kind="video")
    - Full Video Scenario (VideoScenario)

    Studio НЕ генерирует эти описания — они приходят из существующей системы.
    """
    from studio.session_models import StudioSession
    from studio.store import StudioStore

    store = StudioStore()
    scene_engine = registry.get("scene_engine")
    scene = scene_engine.get_scene(chapter, scene_id)
    if not scene:
        raise HTTPException(404, "Scene not found")

    title = scene.get("title", f"Scene {scene_id}")

    session = await store.create_session(
        user_id=user.get("user_id", ""),
        title=title,
        chapter=chapter,
        scene_id=scene_id,
    )

    # Build initial descriptions from Arkaim Description System
    from media_plan import MediaPlanBuilder
    from studio.scenario_builder import VideoScenarioBuilder
    from visual.video_intelligence import VideoIntelligence

    visual_ctx_builder = registry.get("visual_context_builder")
    ctx = await visual_ctx_builder.build_scene_context(chapter, scene_id)

    # A. Image Description — existing pipeline
    image_plan = MediaPlanBuilder(generator="comfyui").build_image_plan(
        ctx, intent="key_frame", created_from="scene_context",
    )

    # B. Video Description — existing VideoIntelligence
    vi = VideoIntelligence()
    video_ctx = vi.create_video_context(ctx)
    video_plan = MediaPlanBuilder(generator="comfyui").build_video_plan(
        video_ctx, intent="video_clip",
        duration_sec=video_ctx.duration_sec, fps=video_ctx.fps,
    )

    # C. Full Video Scenario — VideoScenarioBuilder
    scenario_builder = VideoScenarioBuilder(video_intelligence=vi)
    scenario = scenario_builder.build(ctx, duration_sec=30.0)

    # Create initial version
    version = await store.create_version(
        session_id=session.session_id,
        version_number=1,
        image_description=image_plan,
        video_description=video_plan,
        video_scenario=scenario,
        created_by="system",
        note="Initial description from Arkaim Description System",
    )

    # System message
    await store.add_message(
        session_id=session.session_id,
        role="system",
        content=f"Studio session created for scene '{title}'. Three descriptions prepared.",
        created_version_id=version.version_id,
    )

    return SuccessResponse(data={
        "session": session.model_dump(mode="json"),
        "version": version.model_dump(mode="json"),
    })


# ── 2. List sessions ────────────────────────────────────────────


@router.get("/list", summary="Список Studio-сессий пользователя")
async def list_sessions(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_role("reader")),
):
    store = _get_store()
    sessions = await store.list_sessions(
        user_id=user.get("user_id", ""),
        status=status, limit=limit, offset=offset,
    )
    return SuccessResponse(data=[s.model_dump(mode="json") for s in sessions])


# ── 3. Get session ──────────────────────────────────────────────


@router.get("/{session_id}", summary="Получить Studio-сессию с версиями и сообщениями")
async def get_session(
    session_id: str,
    user: dict = Depends(require_role("reader")),
):
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    versions = await store.get_versions(session_id)
    messages = await store.get_messages(session_id)
    references = await store.get_references(session_id)

    return SuccessResponse(data={
        "session": session.model_dump(mode="json"),
        "versions": [v.model_dump(mode="json") for v in versions],
        "messages": [m.model_dump(mode="json") for m in messages],
        "references": [r.model_dump(mode="json") for r in references],
    })


# ── 3b. Delete session ───────────────────────────────────────────


@router.delete("/{session_id}", summary="Удалить Studio-сессию")
async def delete_session(
    session_id: str,
    user: dict = Depends(require_role("editor")),
):
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    deleted = await store.delete_session(session_id)
    if not deleted:
        raise HTTPException(500, "Failed to delete session")
    return SuccessResponse(data={"deleted": session_id})


# ── 4. Discussion ───────────────────────────────────────────────


@router.post("/{session_id}/discuss", summary="Отправить сообщение в discussion")
async def discuss(
    session_id: str,
    message: str,
    user: dict = Depends(require_role("editor")),
):
    """Discussion с Arkaim. LLM отвечает текстом — НЕ меняет описания.

    Контракт:
      - LLM получает контекст трёх описаний + историю discussion
      - LLM возвращает текстовый ответ (proposal / explanation / question)
      - LLM НЕ создаёт новую StudioVersion
      - LLM НЕ изменяет существующие описания
      - LLM НЕ модифицирует World Model / SceneContext

    Чтобы применить изменение — пользователь вызывает /modify (explicit confirmation).
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    # Save user message
    user_msg = await store.add_message(session_id, "user", message)

    # Get current version for LLM context
    active_version = await store.get_active_version(session_id)
    if not active_version:
        raise HTTPException(409, "No active version")

    # LLM discussion: applies user correction to existing descriptions
    # Context: current three descriptions + last 10 messages
    messages = await store.get_messages(session_id, limit=10)

    from core.adc_deps import registry as _reg
    voice = _reg.get("voice")

    # Build LLM context from existing descriptions
    context_parts = []
    if active_version.image_description:
        context_parts.append(f"Image prompt: {active_version.image_description.prompt}")
    if active_version.video_description:
        context_parts.append(f"Video prompt: {active_version.video_description.prompt}")
    if active_version.video_scenario:
        context_parts.append(f"Scenario synopsis: {active_version.video_scenario.synopsis}")

    context = "\n".join(context_parts)
    history = [{"role": m.role.value, "content": m.content} for m in messages]

    system_prompt = (
        "Ты помощник автора в Studio. Помогаешь уточнять описание сцены. "
        "Всё исходное описание сформировано системой описаний Arkaim — "
        "ты НЕ придумываешь содержание заново, а корректируешь существующее. "
        "Не меняешь исторические факты. Не предлагаешь execution-параметры (model, steps, seed). "
        "Отвечай на русском."
    )

    full_query = f"{system_prompt}\n\nКонтекст описаний:\n{context}\n\nПользователь: {message}"

    utterance = await voice.speak(
        query=full_query,
        reader_id=user.get("user_id", ""),
        reader_name=user.get("display_name", "") or user.get("username", ""),
        messages=history,
    )

    answer = utterance.text if hasattr(utterance, 'text') else str(utterance)

    # Save assistant message
    assistant_msg = await store.add_message(session_id, "assistant", answer)

    # Update status
    await store.update_session_status(session_id, "discussing")

    return SuccessResponse(data={
        "user_message": user_msg.model_dump(mode="json"),
        "assistant_message": assistant_msg.model_dump(mode="json"),
    })


# ── 5. Manual modify ────────────────────────────────────────────


@router.post("/{session_id}/modify", summary="Ручное изменение описания")
async def modify(
    session_id: str,
    target: str,       # "image_description" | "video_description" | "video_scenario"
    field_path: str,   # "atmosphere", "camera.shot_type", etc.
    new_value: str,
    note: str = "",
    user: dict = Depends(require_role("editor")),
):
    """Ручное редактирование поля описания. Создаёт новую версию (immutable)."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    active = await store.get_active_version(session_id)
    if not active:
        raise HTTPException(409, "No active version")

    # Apply modification to the target description
    modification = UserModification(
        target=target,
        field_path=field_path,
        old_value="",
        new_value=new_value,
        reason=note or f"Manual edit by user",
        timestamp=_now(),
    )

    # Copy current descriptions and apply change
    img = active.image_description
    vid = active.video_description
    scenario = active.video_scenario

    # Apply to image description
    if target == "image_description" and img:
        old_val = _get_nested_field(img, field_path)
        modification.old_value = str(old_val) if old_val else ""
        img = _apply_to_mediaplan(img, field_path, new_value)

    # Apply to video description
    elif target == "video_description" and vid:
        old_val = _get_nested_field(vid, field_path)
        modification.old_value = str(old_val) if old_val else ""
        vid = _apply_to_mediaplan(vid, field_path, new_value)

    # Apply to video scenario
    elif target == "video_scenario" and scenario:
        old_val = _get_nested_field(scenario, field_path)
        modification.old_value = str(old_val) if old_val else ""
        scenario = _apply_to_scenario(scenario, field_path, new_value)

    versions = await store.get_versions(session_id)
    new_version = await store.create_version(
        session_id=session_id,
        version_number=len(versions) + 1,
        image_description=img,
        video_description=vid,
        video_scenario=scenario,
        parent_version_id=active.version_id,
        derivation="adaptation",
        user_modifications=[modification],
        created_by="user",
        note=note or f"Manual edit: {field_path}",
    )

    # System message
    await store.add_message(
        session_id, "system",
        f"Manual edit applied: {target}.{field_path} = {new_value[:100]}",
        created_version_id=new_version.version_id,
    )

    return SuccessResponse(data=new_version.model_dump(mode="json"))


# ── 6. Create variant ───────────────────────────────────────────


@router.post("/{session_id}/variant", summary="Создать варианты (до 5)")
async def create_variants(
    session_id: str,
    count: int = 2,
    notes: str = "",
    user: dict = Depends(require_role("editor")),
):
    """Создать варианты текущего описания. Каждый вариант — независимая версия."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "rejected", "sent"):
        raise HTTPException(409, "Session is finalized")

    count = min(max(count, 1), 5)  # O6: max 5

    active = await store.get_active_version(session_id)
    if not active:
        raise HTTPException(409, "No active version")

    versions = await store.get_versions(session_id)
    variants = []

    for i in range(count):
        v = await store.create_version(
            session_id=session_id,
            version_number=len(versions) + i + 1,
            image_description=active.image_description,
            video_description=active.video_description,
            video_scenario=active.video_scenario,
            parent_version_id=active.version_id,
            derivation="variation",
            created_by="user",
            note=notes or f"Variant {i+1}",
        )
        variants.append(v)

    await store.add_message(
        session_id, "system",
        f"Created {count} variant(s) from version {active.version_number}",
    )

    return SuccessResponse(data=[v.model_dump(mode="json") for v in variants])


# ── 7. Activate version ─────────────────────────────────────────


@router.post("/{session_id}/activate-version", summary="Активировать версию")
async def activate_version(
    session_id: str,
    version_id: str,
    user: dict = Depends(require_role("editor")),
):
    store = _get_store()
    version = await store.get_version(version_id)
    if not version or version.session_id != session_id:
        raise HTTPException(404, "Version not found")

    conn = await store._get_conn()
    await conn.execute("UPDATE studio_versions SET is_active = 0 WHERE session_id = ?", (session_id,))
    await conn.execute("UPDATE studio_versions SET is_active = 1 WHERE version_id = ?", (version_id,))
    now = _now()
    await conn.execute("UPDATE studio_sessions SET active_version_id = ?, updated_at = ? WHERE session_id = ?",
                       (version_id, now, session_id))
    await conn.commit()

    return SuccessResponse(data={"activated": version_id})


# ── 8. Upload reference ─────────────────────────────────────────


@router.post("/{session_id}/upload-reference", summary="Загрузить reference-изображение")
async def upload_reference(
    session_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    user: dict = Depends(require_role("editor")),
):
    """Загрузить reference-изображение. Сохраняется в AssetStorage с source_type="user_reference"."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    # Save file using existing AssetStorage
    from visual_assets.storage import AssetStorage
    asset_storage = AssetStorage()

    asset_id = f"ref_{uuid.uuid4().hex[:12]}"
    file_data = await file.read()
    file_path = await asset_storage.save_file(asset_id, "image", file_data)

    # Create reference record
    reference = await store.add_reference(session_id, asset_id, description)

    await store.add_message(
        session_id, "system",
        f"Reference image uploaded: {description or 'no description'}",
    )

    return SuccessResponse(data=reference.model_dump(mode="json"))


# ── 9. Approve ──────────────────────────────────────────────────


@router.post("/{session_id}/approve", summary="Финализировать (утвердить)")
async def approve(
    session_id: str,
    version_id: str | None = None,
    user: dict = Depends(require_role("editor")),
):
    """Финализировать сессию. Помечает активную (или указанную) версию как final."""
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status in ("approved", "sent"):
        raise HTTPException(409, "Already finalized")

    target_id = version_id or session.active_version_id
    if not target_id:
        raise HTTPException(409, "No version to finalize")

    version = await store.get_version(target_id)
    if not version or version.session_id != session_id:
        raise HTTPException(404, "Version not found")

    await store.finalize_version(target_id)
    await store.update_session_status(session_id, "approved")

    await store.add_message(
        session_id, "system",
        f"Version {version.version_number} finalized as approved",
    )

    return SuccessResponse(data={
        "status": "approved",
        "version_id": target_id,
    })


# ── 10. Reject ──────────────────────────────────────────────────


@router.post("/{session_id}/reject", summary="Отклонить")
async def reject(
    session_id: str,
    reason: str = "",
    user: dict = Depends(require_role("editor")),
):
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    await store.update_session_status(session_id, "rejected")
    await store.add_message(session_id, "system", f"Session rejected: {reason}")

    return SuccessResponse(data={"status": "rejected", "reason": reason})


# ── 11. Export ───────────────────────────────────────────────────


@router.get("/{session_id}/export", summary="Экспорт финального StudioExport")
async def export_session(
    session_id: str,
    user: dict = Depends(require_role("editor")),
):
    """Экспорт финального результата: три описания + references + lineage.

    MediaPlan v0 не расширяется. References — внешние asset references.
    """
    store = _get_store()
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != "approved":
        raise HTTPException(409, "Session not approved")

    # Find final version
    versions = await store.get_versions(session_id)
    final_version = None
    for v in versions:
        if v.is_final:
            final_version = v
            break
    if not final_version:
        raise HTTPException(409, "No finalized version")

    # Build lineage
    lineage = []
    current = final_version
    while current:
        lineage.insert(0, current.version_id)
        if current.parent_version_id:
            current = await store.get_version(current.parent_version_id)
        else:
            break

    # Build references
    references = []
    for ref in await store.get_references(session_id):
        references.append({
            "asset_id": ref.asset_id,
            "description": ref.description,
            "file_url": f"/book/assets/{ref.asset_id}/file",
        })

    export = {
        "session_id": session_id,
        "export_id": _new_id("export"),
        "image_description": final_version.image_description.model_dump(mode="json") if final_version.image_description else None,
        "video_description": final_version.video_description.model_dump(mode="json") if final_version.video_description else None,
        "video_scenario": final_version.video_scenario.to_dict() if final_version.video_scenario else None,
        "references": references,
        "version_lineage": lineage,
        "exported_at": _now(),
    }

    return export  # direct return (not enveloped) for export


# ── Helpers ──────────────────────────────────────────────────────


def _get_nested_field(obj, field_path: str):
    """Get nested field from object by dot-notation path."""
    parts = field_path.split(".")
    current = obj
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _apply_to_mediaplan(plan, field_path: str, new_value: str):
    """Apply modification to MediaPlan. Returns new MediaPlan (immutable)."""
    from copy import deepcopy
    data = plan.model_dump()
    parts = field_path.split(".")
    current = data
    for part in parts[:-1]:
        if part in current:
            current = current[part]
        else:
            return plan
    if parts[-1] in current:
        current[parts[-1]] = new_value
    try:
        return plan.__class__.model_validate(data)
    except Exception:
        return plan


def _apply_to_scenario(scenario, field_path: str, new_value: str):
    """Apply modification to VideoScenario. Returns new VideoScenario (immutable)."""
    from copy import deepcopy
    data = scenario.model_dump()
    parts = field_path.split(".")
    current = data
    for part in parts[:-1]:
        if part in current:
            current = current[part]
        else:
            return scenario
    if parts[-1] in current:
        current[parts[-1]] = new_value
    try:
        return scenario.__class__.model_validate(data)
    except Exception:
        return scenario
