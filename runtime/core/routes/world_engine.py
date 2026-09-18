"""
World Engine API — эндпоинты для работы с вычислимой моделью мира.

Предоставляет:
- Поиск по миру
- Получение сущностей
- Визуальные промпты
- Проверка консистентности
- Режимы работы
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional

from auth.rbac import require_role

log = logging.getLogger("routes.world_engine")

router = APIRouter(
    prefix="/world",
    tags=["World Engine"],
    dependencies=[Depends(require_role("reader"))],
)


# ── Модели запросов ────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(10, ge=1, le=100)


class EntityRequest(BaseModel):
    entity_id: str


class VisualPromptRequest(BaseModel):
    entity_id: str
    style: str = "cinematic"


class ValidateRequest(BaseModel):
    entity: dict


class ExperiencePathRequest(BaseModel):
    mode: str


# ── Фабрики ────────────────────────────────────────────────────

def _get_world_engine():
    from narrative_engine.world_engine import get_world_engine
    return get_world_engine()


# ── Эндпоинты ──────────────────────────────────────────────────

@router.get("/summary", summary="Краткая сводка мира")
async def world_summary():
    """Получить краткую сводку о мире."""
    engine = _get_world_engine()
    return {
        "summary": engine.summary(),
        "stats": engine.get_stats(),
    }


@router.post("/search", summary="Поиск по миру")
async def world_search(request: SearchRequest):
    """Поиск сущностей по запросу."""
    engine = _get_world_engine()
    results = engine.search(request.query)
    
    # Ограничиваем результаты
    if "world_model" in results:
        results["world_model"] = results["world_model"][:request.limit]
    if "relations" in results:
        results["relations"] = results["relations"][:request.limit]
    
    return results


@router.get("/entity/{entity_id}", summary="Получить сущность")
async def get_entity(entity_id: str):
    """Получить сущность по ID."""
    engine = _get_world_engine()
    entity = engine.get_entity(entity_id)
    
    if not entity:
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    
    return entity


@router.get("/entity/{entity_id}/context", summary="Контекст сущности")
async def get_entity_context(entity_id: str):
    """Получить контекст сущности — все её связи и формы."""
    engine = _get_world_engine()
    context = engine.get_entity_context(entity_id)
    
    if not context.get("entity"):
        raise HTTPException(404, f"Entity '{entity_id}' not found")
    
    return context


@router.get("/entity/{entity_id}/visual-prompt", summary="Визуальный промпт")
async def get_visual_prompt(
    entity_id: str,
    style: str = Query("cinematic", pattern="^(cinematic|realistic|watercolor|ethereal)$"),
):
    """Генерировать визуальный промпт для сущности."""
    engine = _get_world_engine()
    
    if not engine._form_engine:
        raise HTTPException(500, "FormEngine not initialized")
    
    prompt = engine._form_engine.generate_visual_prompt(entity_id, style)
    
    if not prompt:
        raise HTTPException(404, f"No visual prompt for entity '{entity_id}'")
    
    return {
        "entity_id": entity_id,
        "style": style,
        "prompt": prompt,
    }


@router.post("/validate", summary="Проверка консистентности", dependencies=[Depends(require_role("editor"))])
async def validate_entity(request: ValidateRequest):
    """Проверить сущность на соответствие правилам мира."""
    engine = _get_world_engine()
    
    if not engine._consistency_engine:
        raise HTTPException(500, "ConsistencyEngine not initialized")
    
    report = engine._consistency_engine.validate_entity(request.entity)
    
    return {
        "is_valid": report.is_valid,
        "score": report.score,
        "violations": len(report.violations),
        "warnings": len(report.warnings),
        "details": {
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.value,
                    "description": v.description,
                }
                for v in report.violations
            ],
            "warnings": [
                {
                    "rule_id": w.rule_id,
                    "rule_name": w.rule_name,
                    "severity": w.severity.value,
                    "description": w.description,
                }
                for w in report.warnings
            ],
        },
    }


@router.get("/rules", summary="Правила мира")
async def get_rules():
    """Получить все правила консистентности."""
    engine = _get_world_engine()
    
    if not engine._consistency_engine:
        raise HTTPException(500, "ConsistencyEngine not initialized")
    
    rules = engine._consistency_engine.get_rules()
    
    return {
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "name_ru": r.name_ru,
                "description": r.description,
                "description_ru": r.description_ru,
                "rule_type": r.rule_type.value,
                "severity": r.severity.value,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@router.get("/modes", summary="Режимы работы")
async def get_modes():
    """Получить доступные режимы работы."""
    engine = _get_world_engine()
    
    if not engine._experience_engine:
        raise HTTPException(500, "ExperienceEngine not initialized")
    
    modes = engine._experience_engine.get_available_modes()
    
    return {
        "modes": modes,
        "total": len(modes),
    }


@router.get("/categories", summary="Категории мира")
async def get_categories():
    """Получить список категорий мира."""
    engine = _get_world_engine()
    categories = engine._world_model.get_categories()
    
    result = {}
    for cat in categories:
        items = engine._world_model.get_category(cat)
        result[cat] = len(items)
    
    return {
        "categories": result,
        "total": len(categories),
    }


@router.get("/form-library", summary="Библиотека форм")
async def get_form_library():
    """Получить библиотеку форм для визуализации."""
    engine = _get_world_engine()
    
    if not engine._form_engine:
        raise HTTPException(500, "FormEngine not initialized")
    
    forms = engine._form_engine.get_available_forms()
    
    return {
        "forms": forms,
        "total": sum(len(v) for v in forms.values()),
    }
