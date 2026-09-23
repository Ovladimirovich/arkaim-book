"""World Explorer API Routes — /book/world-explorer/*.

Полный pipeline исследования мира:
  Request → Hypothesis → Scenario → Impact → Contradictions → Delta → Quality → Response
"""

import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth.rbac import get_current_user

from narrative_engine.world_model import WorldModel
from narrative_engine.world_explorer import (
    WorldExplorer,
    ExplorationRequest,
    ExplorationResult,
)
from narrative_engine.hypothesis_generator import Hypothesis, HypothesisGraph
from narrative_engine.compatibility_checker import CompatibilityReport
from narrative_engine.constraint_engine import StoryRequest
from narrative_engine.exploration_ws import exploration_notifier

log = logging.getLogger("hermes.narrative.world_explorer_api")

router = APIRouter(prefix="/world-explorer", tags=["World Explorer"])


def _get_world_model() -> WorldModel:
    from narrative_engine.world_model import WorldModel as WM
    return WM.load()


# ── Эндпоинты ────────────────────────────────────────────


@router.post("/explore", summary="Исследование мира (полный pipeline)")
async def explore(request: ExplorationRequest):
    """Исследовать альтернативные развития для идеи.

    Pipeline:
    1. Проверка совместимости (6 осей)
    2. Генерация гипотез
    3. Моделирование сценариев (2-5 ветвей)
    4. Оценка влияния на мир
    5. Обнаружение противоречий
    6. Расчёт изменений мира
    7. Оценка качества (5 критериев)
    8. Ранжирование альтернатив
    """
    wm = _get_world_model()
    explorer = WorldExplorer(wm)

    try:
        result = explorer.explore(request, ws_notifier=exploration_notifier)
        return {
            "ok": True,
            "data": _serialize_result(result),
            "summary": result.summary,
        }
    except Exception as e:
        log.error("exploration_error error=%s", e)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(exploration_notifier.notify_error(str(e)))
        except RuntimeError:
            pass  # No running event loop
        raise HTTPException(500, detail=str(e))


@router.post("/explore/hypothesis", summary="Исследование от гипотезы")
async def explore_from_hypothesis(
    hypothesis_id: str,
    epoch: str = "satya_yuga",
    branch_count: int = 3,
):
    """Исследовать от конкретной гипотезы."""
    wm = _get_world_model()
    explorer = WorldExplorer(wm)

    # Получаем гипотезы
    hypotheses = explorer.get_hypotheses(epoch, limit=10)
    hypothesis = None
    for h in hypotheses:
        if h.id == hypothesis_id:
            hypothesis = h
            break

    if not hypothesis:
        raise HTTPException(404, detail=f"Гипотеза '{hypothesis_id}' не найдена")

    try:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(exploration_notifier.notify_started(
                    f"hyp_{hypothesis_id}", hypothesis.title, epoch, branch_count
                ))
        except RuntimeError:
            pass  # No running event loop

        result = explorer.explore_from_hypothesis(hypothesis, branch_count=branch_count)

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(exploration_notifier.notify_complete(
                    result.summary, len(result.ranked_branches),
                    result.ranked_branches[0].quality_report.overall_score if result.ranked_branches else 0.0,
                    result.duration_ms,
                ))
        except RuntimeError:
            pass  # No running event loop

        return {
            "ok": True,
            "data": _serialize_result(result),
            "summary": result.summary,
        }
    except Exception as e:
        log.error("exploration_error error=%s", e)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(exploration_notifier.notify_error(str(e)))
        except RuntimeError:
            pass  # No running event loop
        raise HTTPException(500, detail=str(e))


@router.get("/hypotheses/{epoch_id}", summary="Гипотезы для эпохи")
async def get_hypotheses(epoch_id: str, limit: int = 10):
    """Получить гипотезы для конкретной эпохи (с кэшированием)."""
    from narrative_engine.performance import _hypotheses_cache

    cache_key = f"{epoch_id}:{limit}"
    cached = _hypotheses_cache.get(cache_key)
    if cached is not None:
        return {"ok": True, "data": cached, "count": len(cached), "cached": True}

    wm = _get_world_model()
    explorer = WorldExplorer(wm)

    hypotheses = explorer.get_hypotheses(epoch_id, limit=limit)
    serialized = [_serialize_hypothesis(h) for h in hypotheses]
    _hypotheses_cache.set(cache_key, serialized)

    return {
        "ok": True,
        "data": serialized,
        "count": len(hypotheses),
        "cached": False,
    }


@router.get("/possibilities/{epoch_id}", summary="Возможности эпохи")
async def get_possibilities(epoch_id: str, limit: int = 10):
    """Получить возможности для конкретной эпохи (с кэшированием)."""
    from narrative_engine.performance import _possibilities_cache

    cache_key = f"{epoch_id}:{limit}"
    cached = _possibilities_cache.get(cache_key)
    if cached is not None:
        return {"ok": True, "data": cached, "count": len(cached), "cached": True}

    wm = _get_world_model()
    explorer = WorldExplorer(wm)

    possibilities = explorer.get_possibilities(epoch_id, limit=limit)
    serialized = [p.model_dump() for p in possibilities]
    _possibilities_cache.set(cache_key, serialized)

    return {
        "ok": True,
        "data": serialized,
        "count": len(possibilities),
        "cached": False,
    }
    return {
        "ok": True,
        "data": [p.model_dump() for p in possibilities],
        "count": len(possibilities),
    }


@router.post("/validate", summary="Проверка совместимости идеи")
async def validate_idea(request: StoryRequest):
    """Проверить идею на совместимость с каноном (6 осей)."""
    wm = _get_world_model()
    from narrative_engine.compatibility_checker import CompatibilityChecker

    checker = CompatibilityChecker(wm)
    report = checker.check(request)

    return {
        "ok": True,
        "data": _serialize_compatibility(report),
        "overall_score": report.overall_score,
        "is_compatible": report.is_compatible,
        "risk_level": report.risk_level,
    }


@router.get("/epochs", summary="Список эпох для исследования")
async def get_epochs():
    """Получить список всех эпох, доступных для исследования."""
    wm = _get_world_model()
    epochs = wm.get_epochs()
    return {
        "ok": True,
        "data": [
            {
                "id": e.id,
                "name": e.name,
                "name_ru": e.name_ru,
                "order": e.order,
            }
            for e in epochs
        ],
    }


@router.get("/stats", summary="Статистика World Explorer")
async def get_stats():
    """Получить статистику системы."""
    wm = _get_world_model()
    from narrative_engine.planners.cause_effect import PATTERN_CHAINS

    return {
        "ok": True,
        "data": {
            "world_model": wm.summary(),
            "patterns_count": len(PATTERN_CHAINS),
            "epochs_count": len(wm.get_epochs()),
            "locations_count": len(wm.get_locations()),
            "events_count": len(wm.get_events()),
        },
    }


@router.get("/cache/stats", summary="Статистика кэша")
async def get_cache_stats():
    """Получить статистику кэширования."""
    from narrative_engine.performance import get_cache_stats, metrics

    return {
        "ok": True,
        "data": {
            "caches": get_cache_stats(),
            "performance_metrics": metrics.get_all_stats(),
        },
    }


@router.post("/cache/clear", summary="Очистить кэш")
async def clear_cache():
    """Очистить все кэши World Explorer."""
    from narrative_engine.performance import clear_all_caches

    clear_all_caches()
    return {"ok": True, "message": "Кэш очищен"}


# ── Unified Pipeline (Explorer + Story Engine) ────────────


class UnifiedRequest(BaseModel):
    prompt: str
    epoch: Optional[str] = None
    location: Optional[str] = None
    branch_count: int = 3
    style: str = "literary"
    max_length: int = 2000
    generate_story: bool = True
    select_best: bool = True


@router.post("/unified", summary="Единый pipeline: исследование + генерация")
async def unified_pipeline(request: UnifiedRequest):
    """Полный pipeline: World Explorer → Story Engine.

    1. Исследование мира (генерация гипотез, моделирование сценариев)
    2. Выбор лучшей ветви
    3. Генерация текста через Story Engine
    4. Валидация результата
    """
    try:
        from narrative_engine.unified_pipeline import UnifiedPipeline, UnifiedRequest as UReq

        wm = _get_world_model()
        pipeline = UnifiedPipeline(wm)

        unified_request = UReq(
            prompt=request.prompt,
            epoch=request.epoch,
            location=request.location,
            branch_count=request.branch_count,
            style=request.style,
            max_length=request.max_length,
            generate_story=request.generate_story,
            select_best=request.select_best,
        )

        result = pipeline.run(unified_request)

        return {
            "ok": True,
            "data": {
                "exploration": {
                    "branch_count": len(result.exploration.ranked_branches) if result.exploration else 0,
                    "best_score": result.exploration.ranked_branches[0].quality_report.overall_score if result.exploration and result.exploration.ranked_branches else 0,
                    "summary": result.exploration.summary if result.exploration else "",
                } if result.exploration else None,
                "story": {
                    "system_instruction": result.story.system_instruction[:500] if result.story else "",
                    "user_prompt": result.story.user_prompt[:1000] if result.story else "",
                    "style": result.story.style if result.story else "",
                    "constraints_summary": result.story.constraints_summary if result.story else "",
                } if result.story else None,
                "selected_branch_rank": result.selected_branch_rank,
                "pipeline_steps": result.pipeline_steps,
                "duration_ms": result.total_duration_ms,
            },
            "summary": result.summary,
        }
    except Exception as e:
        log.error("unified_pipeline_error error=%s", e)
        raise HTTPException(500, detail=str(e))


# ── Экспорт результатов ───────────────────────────────────


class ExportRequest(BaseModel):
    prompt: str
    epoch: Optional[str] = None
    branch_count: int = 3


@router.post("/export", summary="Экспорт результатов исследования в Markdown")
async def export_results(request: ExportRequest):
    """Сгенерировать Markdown отчёт о результатах исследования."""
    try:
        from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest as ExpReq
        from narrative_engine.export_report import generate_markdown_report

        wm = _get_world_model()
        explorer = WorldExplorer(wm)

        exploration_request = ExpReq(
            prompt=request.prompt,
            epoch=request.epoch,
            branch_count=request.branch_count,
        )
        result = explorer.explore(exploration_request)
        report = generate_markdown_report(result)

        return {
            "ok": True,
            "data": {
                "title": report.title,
                "created_at": report.created_at,
                "prompt": report.prompt,
                "epoch": report.epoch,
                "branch_count": report.branch_count,
                "best_score": report.best_score,
                "duration_ms": report.duration_ms,
                "branches_summary": report.branches_summary,
                "recommendations": report.recommendations,
                "markdown": report.markdown,
            },
        }
    except Exception as e:
        log.error("export_error error=%s", e)
        raise HTTPException(500, detail=str(e))


# ── Внешние источники ─────────────────────────────────────


@router.get("/sources/search", summary="Поиск во внешних источниках")
async def search_external_sources(
    query: str,
    limit: int = 5,
    sources: Optional[str] = None,
):
    """Поиск во внешних источниках (Wikipedia, Semantic Scholar, OpenAlex).

    Args:
        query: Поисковый запрос
        limit: Максимум результатов с одного источника
        sources: Список источников через запятую (wikipedia,semantic_scholar,openalex)
    """
    try:
        from narrative_engine.external_sources import search_all_sources, search_local_knowledge

        source_list = sources.split(",") if sources else None
        external_results = await search_all_sources(query, limit_per_source=limit, sources=source_list)
        local_results = search_local_knowledge(query, limit=limit)

        all_results = external_results + local_results

        return {
            "ok": True,
            "data": [r.model_dump() for r in all_results],
            "count": len(all_results),
            "sources_searched": source_list or ["wikipedia", "semantic_scholar", "openalex", "local"],
        }
    except Exception as e:
        log.error("sources_search_error error=%s", e)
        raise HTTPException(500, detail=str(e))


# ── Глубокое исследование ─────────────────────────────────


class DeepExplorationRequest(BaseModel):
    prompt: str
    epoch: Optional[str] = None
    parent_branch_id: Optional[str] = None
    max_depth: int = 3
    branches_per_level: int = 3


@router.post("/explore-deep", summary="Глубокое исследование мира")
async def explore_deep(request: DeepExplorationRequest):
    """Многоуровневое исследование мира с ветвлением от ветвей."""
    try:
        from narrative_engine.deep_explorer import DeepExplorer, DeepExplorationRequest as DEReq

        wm = _get_world_model()
        explorer = DeepExplorer(wm)

        deep_request = DEReq(
            prompt=request.prompt,
            epoch=request.epoch,
            parent_branch_id=request.parent_branch_id,
            max_depth=request.max_depth,
            branches_per_level=request.branches_per_level,
        )

        tree = explorer.explore_deep(deep_request)

        return {
            "ok": True,
            "data": {
                "total_nodes": tree.total_nodes,
                "max_depth": tree.max_depth_reached,
                "summary": tree.summary,
                "nodes": {
                    nid: {
                        "id": n.id,
                        "hypothesis_title": n.hypothesis.title_ru if n.hypothesis else "",
                        "hypothesis_type": n.hypothesis.hypothesis_type.value if n.hypothesis and hasattr(n.hypothesis.hypothesis_type, 'value') else "",
                        "quality_score": n.quality_score,
                        "depth": n.depth,
                        "children": n.children,
                        "parent_id": n.parent_id,
                    }
                    for nid, n in tree.nodes.items()
                },
            },
        }
    except Exception as e:
        log.error("deep_exploration_error error=%s", e)
        raise HTTPException(500, detail=str(e))


@router.get("/free-points", summary="Свободные точки мира")
async def get_free_points(epoch: Optional[str] = None):
    """Обнаружить «свободные точки» мира — где есть потенциал для развития."""
    try:
        from narrative_engine.deep_explorer import DeepExplorer

        wm = _get_world_model()
        explorer = DeepExplorer(wm)
        free_points = explorer.find_free_points(epoch_id=epoch)

        return {
            "ok": True,
            "data": free_points,
            "count": len(free_points),
        }
    except Exception as e:
        log.error("free_points_error error=%s", e)
        raise HTTPException(500, detail=str(e))


@router.get("/best-paths", summary="Лучшие пути в дереве")
async def get_best_paths(tree_id: str = "root", top_n: int = 3):
    """Найти лучшие пути в дереве глубокого исследования."""
    # Заглушка — в реальности tree хранится в сессии/БД
    return {
        "ok": True,
        "data": [],
        "message": "Используйте /explore-deep для создания дерева, затем best-paths",
    }


# ── Обратная связь ────────────────────────────────────────


class FeedbackRequest(BaseModel):
    exploration_id: Optional[int] = None
    branch_rank: int = 0
    branch_type: str = ""
    branch_title: str = ""
    rating: int = Field(ge=1, le=5)
    comment: str = ""


@router.post("/feedback", summary="Добавить отзыв к ветви")
async def add_feedback(request: FeedbackRequest, user: dict = Depends(get_current_user)):
    """Добавить обратную связь к ветви исследования."""
    try:
        from core.memory.feedback_store import get_feedback_store
        store = get_feedback_store()
        item_id = await store.add_feedback(
            user_id=user.get("user_id", ""),
            exploration_id=request.exploration_id,
            branch_rank=request.branch_rank,
            branch_type=request.branch_type,
            branch_title=request.branch_title,
            rating=request.rating,
            comment=request.comment,
        )
        return {"ok": True, "id": item_id}
    except Exception as e:
        log.error("feedback_add_error error=%s", e)
        raise HTTPException(500, detail=str(e))


@router.get("/feedback", summary="Отзывы пользователя")
async def get_feedback(limit: int = 50, user: dict = Depends(get_current_user)):
    """Получить список отзывов текущего пользователя."""
    try:
        from core.memory.feedback_store import get_feedback_store
        store = get_feedback_store()
        items = await store.get_feedback_by_user(user.get("user_id", ""), limit=limit)
        return {"ok": True, "data": items, "count": len(items)}
    except Exception as e:
        log.warning("feedback_load_error error=%s", e)
        return {"ok": True, "data": [], "count": 0}


@router.get("/feedback/average", summary="Средний рейтинг")
async def get_average_rating(branch_type: Optional[str] = None):
    """Получить средний рейтинг по типу ветви."""
    try:
        from core.memory.feedback_store import get_feedback_store
        store = get_feedback_store()
        stats = await store.get_average_rating(branch_type=branch_type)
        return {"ok": True, "data": stats}
    except Exception as e:
        log.error("feedback_stats_error error=%s", e)
        raise HTTPException(500, detail=str(e))


@router.delete("/feedback/{feedback_id}", summary="Удалить отзыв")
async def delete_feedback(feedback_id: int, user: dict = Depends(get_current_user)):
    """Удалить свой отзыв."""
    try:
        from core.memory.feedback_store import get_feedback_store
        store = get_feedback_store()
        deleted = await store.delete_feedback(feedback_id, user.get("user_id", ""))
        if not deleted:
            raise HTTPException(404, detail="Отзыв не найден")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        log.error("feedback_delete_error error=%s", e)
        raise HTTPException(500, detail=str(e))


# ── История исследований ──────────────────────────────────


@router.get("/history", summary="История исследований")
async def get_history(limit: int = 50, offset: int = 0, user: dict = Depends(get_current_user)):
    """Получить список прошлых исследований (для текущего пользователя)."""
    try:
        from core.memory.exploration_store import get_exploration_store
        store = get_exploration_store()
        items = await store.list_by_user(user_id=user.get("user_id", ""), limit=limit, offset=offset)
        return {"ok": True, "data": items, "count": len(items)}
    except Exception as e:
        log.warning("history_load_error error=%s", e)
        return {"ok": True, "data": [], "count": 0}


@router.get("/history/{exploration_id}", summary="Детали исследования")
async def get_history_item(exploration_id: int):
    """Получить полные данные конкретного исследования."""
    try:
        from core.memory.exploration_store import get_exploration_store
        store = get_exploration_store()
        item = await store.get(exploration_id)
        if not item:
            raise HTTPException(404, detail="Исследование не найдено")
        # Парсим result_json обратно в dict
        if "result_json" in item and isinstance(item["result_json"], str):
            try:
                item["result"] = json.loads(item["result_json"])
            except Exception:
                item["result"] = None
            del item["result_json"]
        return {"ok": True, "data": item}
    except HTTPException:
        raise
    except Exception as e:
        log.error("history_item_error error=%s", e)
        raise HTTPException(500, detail=str(e))


@router.delete("/history/{exploration_id}", summary="Удалить исследование")
async def delete_history_item(exploration_id: int, user: dict = Depends(get_current_user)):
    """Удалить исследование из истории."""
    try:
        from core.memory.exploration_store import get_exploration_store
        store = get_exploration_store()
        deleted = await store.delete(exploration_id, user_id=user.get("user_id", ""))
        if not deleted:
            raise HTTPException(404, detail="Исследование не найдено")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        log.error("history_delete_error error=%s", e)
        raise HTTPException(500, detail=str(e))


class SaveExplorationRequest(BaseModel):
    prompt: str
    epoch: Optional[str] = None
    branch_count: int = 3
    hypothesis_id: Optional[str] = None
    hypothesis_title: Optional[str] = None
    result_json: str
    summary: str = ""
    overall_score: float = 0.0
    branch_count_actual: int = 0
    duration_ms: float = 0.0


@router.post("/history", summary="Сохранить исследование")
async def save_history(request: SaveExplorationRequest, user: dict = Depends(get_current_user)):
    """Сохранить результат исследования в историю."""
    try:
        from core.memory.exploration_store import get_exploration_store
        store = get_exploration_store()
        item_id = await store.save(
            user_id=user.get("user_id", ""),
            prompt=request.prompt,
            epoch=request.epoch,
            branch_count=request.branch_count,
            hypothesis_id=request.hypothesis_id,
            hypothesis_title=request.hypothesis_title,
            result_json=request.result_json,
            summary=request.summary,
            overall_score=request.overall_score,
            branch_count_actual=request.branch_count_actual,
            duration_ms=request.duration_ms,
        )
        return {"ok": True, "id": item_id}
    except Exception as e:
        log.error("history_save_error error=%s", e)
        raise HTTPException(500, detail=str(e))


# ── Генерация текста из ветви ────────────────────────────


class GenerateFromBranchRequest(BaseModel):
    exploration_prompt: str
    branch_title: str
    branch_type: str
    epoch: Optional[str] = None
    location: Optional[str] = None
    style: str = "literary"
    max_length: int = 2000
    quality_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


@router.post("/generate-from-branch", summary="Генерация текста из ветви")
async def generate_from_branch(request: GenerateFromBranchRequest):
    """Сформировать промпт для LLM на основе ветви World Explorer.

    Возвращает system_instruction + user_prompt для отправки в LLM.
    """
    try:
        from narrative_engine.story_from_branch import build_story_from_branch, BranchToStoryRequest

        wm = _get_world_model()
        branch_request = BranchToStoryRequest(
            exploration_prompt=request.exploration_prompt,
            branch_title=request.branch_title,
            branch_type=request.branch_type,
            epoch=request.epoch,
            location=request.location,
            style=request.style,
            max_length=request.max_length,
            quality_score=request.quality_score,
            strengths=request.strengths,
            weaknesses=request.weaknesses,
        )

        result = build_story_from_branch(branch_request, wm)

        return {
            "ok": True,
            "data": {
                "system_instruction": result.system_instruction,
                "user_prompt": result.user_prompt,
                "style": result.style,
                "max_length": result.max_length,
                "branch_title": result.branch_title,
                "quality_score": result.quality_score,
                "constraints_summary": result.constraints_summary,
            },
        }
    except Exception as e:
        log.error("generate_from_branch_error error=%s", e)
        raise HTTPException(500, detail=str(e))


# ── Сериализация ──────────────────────────────────────────


def _serialize_result(result: ExplorationResult) -> dict:
    """Сериализовать результат исследования."""
    return {
        "request": result.request.model_dump(),
        "hypothesis": _serialize_hypothesis(result.hypothesis) if result.hypothesis else None,
        "scenario": {
            "branch_count": result.scenario.branch_count if result.scenario else 0,
            "best_branch_id": result.scenario.best_branch_id if result.scenario else "",
            "summary": result.scenario.summary if result.scenario else "",
        },
        "ranked_branches": [
            {
                "rank": rb.rank,
                "branch_type": rb.branch.branch_type,
                "title": rb.branch.title_ru,
                "quality_score": rb.quality_report.overall_score,
                "quality_summary": rb.quality_report.summary,
                "strengths": rb.quality_report.strengths,
                "weaknesses": rb.quality_report.weaknesses,
                "impact_score": rb.impact_report.overall_impact_score if rb.impact_report else 0.0,
                "contradictions": rb.contradiction_report.hard_count if rb.contradiction_report else 0,
                "delta_changes": rb.world_delta.total_changes if rb.world_delta else 0,
            }
            for rb in result.ranked_branches
        ],
        "duration_ms": result.duration_ms,
        "summary": result.summary,
    }


def _serialize_hypothesis(h: Hypothesis) -> dict:
    """Сериализовать гипотезу."""
    return {
        "id": h.id,
        "title": h.title_ru,
        "description": h.description,
        "type": h.hypothesis_type.value if hasattr(h.hypothesis_type, 'value') else str(h.hypothesis_type),
        "epoch": h.epoch,
        "confidence": h.confidence,
        "tags": h.tags,
    }


def _serialize_compatibility(report: CompatibilityReport) -> dict:
    """Сериализовать отчёт о совместимости."""
    return {
        "overall_score": report.overall_score,
        "is_compatible": report.is_compatible,
        "risk_level": report.risk_level,
        "axis_scores": [
            {
                "axis": ax.axis,
                "score": ax.score,
                "violations_count": len(ax.violations),
                "warnings_count": len(ax.warnings),
            }
            for ax in report.axis_scores
        ],
        "violations_count": len(report.violations),
        "warnings_count": len(report.warnings),
        "recommendations": report.recommendations,
    }
