"""Community API — FastAPI routes для интерпретаций, артефактов, комментариев и уведомлений."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth.rbac import require_role
from community.interpretations import InterpretationStore
from community.artifacts import ArtifactStore
from community.comments import CommentStore
from community.notifications import NotificationStore

log = logging.getLogger("hermes.community_api")

router = APIRouter(prefix="/book/community", tags=["Community"])

# Stores (инициализируются при первом запросе)
_interp_store: InterpretationStore | None = None
_artifact_store: ArtifactStore | None = None
_comment_store: CommentStore | None = None
_notification_store: NotificationStore | None = None


def _get_interp_store() -> InterpretationStore:
    global _interp_store
    if _interp_store is None:
        _interp_store = InterpretationStore()
    return _interp_store


def _get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        _artifact_store = ArtifactStore()
    return _artifact_store


def _get_comment_store() -> CommentStore:
    global _comment_store
    if _comment_store is None:
        _comment_store = CommentStore()
    return _comment_store


def _get_notification_store() -> NotificationStore:
    global _notification_store
    if _notification_store is None:
        _notification_store = NotificationStore()
    return _notification_store


# ── Request models ──────────────────────────────────────


class CommentRequest(BaseModel):
    text: str


class InterpretationRequest(BaseModel):
    text: str
    themes: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)


class ArtifactRequest(BaseModel):
    title: str
    description: str
    category: str
    source: str
    connection_to_book: str
    related_themes: list[str] = Field(default_factory=list)
    related_characters: list[str] = Field(default_factory=list)
    location: str = ""
    url: str = ""


# ── Интерпретации ──────────────────────────────────────


@router.get("/interpretations")
async def list_interpretations(
    status: str | None = None,
    sort: str = Query("newest", pattern="^(newest|oldest|popular)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """Получить список интерпретаций."""
    store = _get_interp_store()
    items = await store.get_all(status=status)

    # Сортировка
    if sort == "newest":
        items.sort(key=lambda i: i.created_at, reverse=True)
    elif sort == "oldest":
        items.sort(key=lambda i: i.created_at)
    elif sort == "popular":
        items.sort(key=lambda i: i.likes, reverse=True)

    return {
        "interpretations": [i.to_dict() for i in items[:limit]],
        "count": len(items),
    }


@router.get("/interpretations/mine")
async def my_interpretations(user: dict = Depends(require_role("reader"))):
    """Мои интерпретации."""
    store = _get_interp_store()
    items = await store.get_by_reader(user["user_id"])
    items.sort(key=lambda i: i.created_at, reverse=True)
    return {"interpretations": [i.to_dict() for i in items]}


@router.post("/interpretations")
async def submit_interpretation(
    request: InterpretationRequest,
    user: dict = Depends(require_role("reader")),
):
    """Отправить интерпретацию на модерацию."""
    store = _get_interp_store()
    interp = await store.submit(
        reader_id=user["user_id"],
        reader_name=user.get("display_name") or user.get("username", ""),
        text=request.text,
        themes=request.themes,
        characters=request.characters,
    )
    return {"ok": True, "interpretation": interp.to_dict()}


@router.post("/interpretations/{interp_id}/like")
async def like_interpretation(interp_id: str):
    """Поставить лайк интерпретации."""
    store = _get_interp_store()
    # Find the interpretation to get reader_id for notification
    items = await store.get_all()
    interp = next((i for i in items if i.id == interp_id), None)
    if not interp:
        raise HTTPException(404, "Интерпретация не найдена")
    ok = await store.like(interp_id)
    # Create notification for the author
    if ok and interp.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=interp.reader_id,
            type="comment_liked",
            title="Вашу интерпретацию оценили",
            message=f"Кто-то поставил лайк вашей интерпретации",
            link="/interpretations",
        )
    return {"ok": True}


@router.post("/interpretations/{interp_id}/approve")
async def approve_interpretation(interp_id: str, user: dict = Depends(require_role("admin"))):
    """Одобрить интерпретацию (admin)."""
    store = _get_interp_store()
    items = await store.get_all()
    interp = next((i for i in items if i.id == interp_id), None)
    if not interp:
        raise HTTPException(404, "Интерпретация не найдена")
    ok = await store.approve(interp_id)
    # Create notification for the author
    if ok and interp.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=interp.reader_id,
            type="interpretation_approved",
            title="Интерпретация одобрена",
            message=f"Ваша интерпретация одобрена и опубликована",
            link="/interpretations",
        )
    return {"ok": True}


@router.post("/interpretations/{interp_id}/reject")
async def reject_interpretation(interp_id: str, user: dict = Depends(require_role("admin"))):
    """Отклонить интерпретацию (admin)."""
    store = _get_interp_store()
    items = await store.get_all()
    interp = next((i for i in items if i.id == interp_id), None)
    if not interp:
        raise HTTPException(404, "Интерпретация не найдена")
    ok = await store.reject(interp_id)
    if ok and interp.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=interp.reader_id,
            type="interpretation_rejected",
            title="Интерпретация отклонена",
            message=f"Ваша интерпретация не прошла модерацию",
            link="/interpretations",
        )
    return {"ok": True}


@router.delete("/interpretations/{interp_id}")
async def delete_interpretation(interp_id: str, user: dict = Depends(require_role("admin"))):
    """Удалить интерпретацию (admin)."""
    store = _get_interp_store()
    ok = await store.delete(interp_id)
    if not ok:
        raise HTTPException(404, "Интерпретация не найдена")
    return {"ok": True}


@router.get("/interpretations/stats")
async def interpretation_stats():
    """Статистика интерпретаций."""
    store = _get_interp_store()
    return store.get_stats()


# ── Артефакты ──────────────────────────────────────────


@router.get("/artifacts")
async def list_artifacts(
    status: str | None = None,
    category: str | None = None,
    sort: str = Query("newest", pattern="^(newest|oldest|popular)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """Получить список артефактов."""
    store = _get_artifact_store()
    items = await store.get_all(status=status, category=category)

    # Сортировка
    if sort == "newest":
        items.sort(key=lambda a: a.created_at, reverse=True)
    elif sort == "oldest":
        items.sort(key=lambda a: a.created_at)
    elif sort == "popular":
        items.sort(key=lambda a: a.likes, reverse=True)

    return {
        "artifacts": [a.to_dict() for a in items[:limit]],
        "count": len(items),
    }


@router.get("/artifacts/mine")
async def my_artifacts(user: dict = Depends(require_role("reader"))):
    """Мои артефакты."""
    store = _get_artifact_store()
    items = await store.get_by_reader(user["user_id"])
    items.sort(key=lambda a: a.created_at, reverse=True)
    return {"artifacts": [a.to_dict() for a in items]}


@router.post("/artifacts")
async def submit_artifact(
    request: ArtifactRequest,
    user: dict = Depends(require_role("reader")),
):
    """Отправить артефакт на модерацию."""
    store = _get_artifact_store()
    artifact = await store.submit(
        reader_id=user["user_id"],
        reader_name=user.get("display_name") or user.get("username", ""),
        title=request.title,
        description=request.description,
        category=request.category,
        source=request.source,
        connection_to_book=request.connection_to_book,
        related_themes=request.related_themes,
        related_characters=request.related_characters,
        location=request.location,
        url=request.url,
    )
    return {"ok": True, "artifact": artifact.to_dict()}


@router.post("/artifacts/{artifact_id}/like")
async def like_artifact(artifact_id: str):
    """Поставить лайк артефакту."""
    store = _get_artifact_store()
    items = await store.get_all()
    artifact = next((a for a in items if a.id == artifact_id), None)
    if not artifact:
        raise HTTPException(404, "Артефакт не найден")
    ok = await store.like(artifact_id)
    if ok and artifact.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=artifact.reader_id,
            type="artifact_liked",
            title="Ваш артефакт оценили",
            message=f"Кто-то поставил лайк вашему артефакту «{artifact.title}»",
            link="/artifacts",
        )
    return {"ok": True}


@router.post("/artifacts/{artifact_id}/approve")
async def approve_artifact(artifact_id: str, user: dict = Depends(require_role("admin"))):
    """Одобрить артефакт (admin)."""
    store = _get_artifact_store()
    items = await store.get_all()
    artifact = next((a for a in items if a.id == artifact_id), None)
    if not artifact:
        raise HTTPException(404, "Артефакт не найден")
    ok = await store.approve(artifact_id)
    if ok and artifact.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=artifact.reader_id,
            type="artifact_approved",
            title="Артефакт одобрен",
            message=f"Ваш артефакт «{artifact.title}» одобрен и опубликован",
            link="/artifacts",
        )
    return {"ok": True}


@router.post("/artifacts/{artifact_id}/reject")
async def reject_artifact(artifact_id: str, user: dict = Depends(require_role("admin"))):
    """Отклонить артефакт (admin)."""
    store = _get_artifact_store()
    items = await store.get_all()
    artifact = next((a for a in items if a.id == artifact_id), None)
    if not artifact:
        raise HTTPException(404, "Артефакт не найден")
    ok = await store.reject(artifact_id)
    if ok and artifact.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=artifact.reader_id,
            type="artifact_rejected",
            title="Артефакт отклонён",
            message=f"Ваш артефакт «{artifact.title}» не прошёл модерацию",
            link="/artifacts",
        )
    return {"ok": True}


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, user: dict = Depends(require_role("admin"))):
    """Удалить артефакт (admin)."""
    store = _get_artifact_store()
    ok = await store.delete(artifact_id)
    if not ok:
        raise HTTPException(404, "Артефакт не найден")
    return {"ok": True}


@router.get("/artifacts/stats")
async def artifact_stats():
    """Статистика артефактов."""
    store = _get_artifact_store()
    return store.get_stats()


# ── Комментарии ──────────────────────────────────────────────


@router.get("/comments/{parent_type}/{parent_id}")
async def get_comments(parent_type: str, parent_id: str):
    """Получить комментарии к элементу (interpretation/artifact)."""
    if parent_type not in ("interpretation", "artifact"):
        raise HTTPException(400, "parent_type должен быть interpretation или artifact")
    store = _get_comment_store()
    comments = await store.get_for_parent(parent_id)
    return {
        "comments": [c.to_dict() for c in comments],
        "count": len(comments),
    }


@router.post("/comments/{parent_type}/{parent_id}")
async def add_comment(
    parent_type: str,
    parent_id: str,
    request: CommentRequest,
    user: dict = Depends(require_role("reader")),
):
    """Добавить комментарий к интерпретации или артефакту."""
    if parent_type not in ("interpretation", "artifact"):
        raise HTTPException(400, "parent_type должен быть interpretation или artifact")
    store = _get_comment_store()
    comment = await store.add(
        parent_id=parent_id,
        parent_type=parent_type,
        reader_id=user["user_id"],
        reader_name=user.get("display_name") or user.get("username", ""),
        text=request.text,
    )
    return {"ok": True, "comment": comment.to_dict()}


@router.post("/comments/{comment_id}/like")
async def like_comment(comment_id: str):
    """Поставить лайк комментарию."""
    store = _get_comment_store()
    comment = next((c for c in store._items if c.id == comment_id), None)
    if not comment:
        raise HTTPException(404, "Комментарий не найден")
    ok = await store.like(comment_id)
    if ok and comment.reader_id:
        notif_store = _get_notification_store()
        await notif_store.create(
            user_id=comment.reader_id,
            type="comment_liked",
            title="Ваш комментарий оценили",
            message=f"Кто-то поставил лайк вашему комментарию",
            link=f"/{comment.parent_type}s",
        )
    return {"ok": True}


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(require_role("admin"))):
    """Удалить комментарий (admin)."""
    store = _get_comment_store()
    ok = await store.delete(comment_id)
    if not ok:
        raise HTTPException(404, "Комментарий не найден")
    return {"ok": True}


# ── Поиск ──────────────────────────────────────────────────────


@router.get("/search")
async def search_community(
    q: str = Query(..., min_length=2),
    type: str = Query("all", pattern="^(all|interpretations|artifacts)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """Поиск по интерпретациям и артефактам."""
    results = {"interpretations": [], "artifacts": []}
    q_lower = q.lower()

    if type in ("all", "interpretations"):
        interp_store = _get_interp_store()
        all_interps = await interp_store.get_all(status="approved")
        matched = [
            i for i in all_interps
            if q_lower in i.text.lower()
            or any(q_lower in t.lower() for t in i.themes)
            or any(q_lower in c.lower() for c in i.characters)
        ]
        results["interpretations"] = [i.to_dict() for i in matched[:limit]]

    if type in ("all", "artifacts"):
        artifact_store = _get_artifact_store()
        all_artifacts = await artifact_store.get_all(status="approved")
        matched = [
            a for a in all_artifacts
            if q_lower in a.title.lower()
            or q_lower in a.description.lower()
            or q_lower in a.connection_to_book.lower()
            or any(q_lower in t.lower() for t in a.related_themes)
            or q_lower in a.location.lower()
        ]
        results["artifacts"] = [a.to_dict() for a in matched[:limit]]

    results["total"] = len(results["interpretations"]) + len(results["artifacts"])
    return results


# ── Уведомления ──────────────────────────────────────────────


@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_role("reader")),
):
    """Получить уведомления пользователя."""
    store = _get_notification_store()
    items = await store.get_for_user(user["user_id"], unread_only=unread_only)
    return {
        "notifications": [n.to_dict() for n in items[:limit]],
        "count": len(items),
        "unread_count": store.get_unread_count(user["user_id"]),
    }


@router.get("/notifications/unread-count")
async def get_unread_count(user: dict = Depends(require_role("reader"))):
    """Получить количество непрочитанных уведомлений."""
    store = _get_notification_store()
    return {"count": store.get_unread_count(user["user_id"])}


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(require_role("reader"))):
    """Отметить уведомление как прочитанное."""
    store = _get_notification_store()
    ok = await store.mark_read(notification_id)
    if not ok:
        raise HTTPException(404, "Уведомление не найдено")
    return {"ok": True}


@router.post("/notifications/read-all")
async def mark_all_read(user: dict = Depends(require_role("reader"))):
    """Отметить все уведомления как прочитанные."""
    store = _get_notification_store()
    count = await store.mark_all_read(user["user_id"])
    return {"ok": True, "marked": count}


@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, user: dict = Depends(require_role("reader"))):
    """Удалить уведомление."""
    store = _get_notification_store()
    ok = await store.delete(notification_id)
    if not ok:
        raise HTTPException(404, "Уведомление не найдено")
    return {"ok": True}


@router.get("/notifications/stats")
async def notification_stats(user: dict = Depends(require_role("reader"))):
    """Статистика уведомлений."""
    store = _get_notification_store()
    return store.get_stats()


# ── Knowledge Expansion ──────────────────────────────────────


@router.post("/knowledge/refresh")
async def refresh_knowledge(user: dict = Depends(require_role("admin"))):
    """Принудительное обогащение знаний."""
    from knowledge_expansion.pipeline import create_default_pipeline
    pipeline = create_default_pipeline()
    results = await pipeline.run_all()
    return {
        "ok": True,
        "results": {k: {"saved": v.items_saved, "skipped": v.items_skipped} for k, v in results.items()},
    }


@router.get("/knowledge/status")
async def knowledge_status():
    """Статус пайплайна знаний."""
    from knowledge_expansion.pipeline import create_default_pipeline
    pipeline = create_default_pipeline()
    return pipeline.get_status()


# ── Map & Timeline ──────────────────────────────────────


@router.get("/map-data")
async def get_map_data():
    """Получить данные для интерактивной карты."""
    map_file = Path(__file__).resolve().parents[3] / "core" / "KNOWLEDGE" / "MAP_DATA.json"
    if map_file.exists():
        data = json.loads(map_file.read_text(encoding="utf-8"))
        return data
    return {"regions": [], "routes": [], "energy_lines": []}


@router.get("/timeline")
async def get_timeline():
    """Получить хронологию событий книги."""
    timeline = [
        {"year": "~7000 до н.э.", "title": "Гиперборея (расцвет)", "type": "civilization"},
        {"year": "~5000 до н.э.", "title": "Строительство городов", "type": "city"},
        {"year": "~4000 до н.э.", "title": "Аркаим", "type": "city"},
        {"year": "~3000 до н.э.", "title": "Гардарика", "type": "city"},
        {"year": "~2000 до н.э.", "title": "Миграция на юг", "type": "migration"},
        {"year": "~1000 до н.э.", "title": "Кали Юга", "type": "event"},
        {"year": "Настоящее", "title": "Аркаим открыт", "type": "event"},
    ]
    return {"events": timeline}

