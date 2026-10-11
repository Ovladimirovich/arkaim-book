"""Temporal API — эндпоинты для работы с temporal моделью.

Предоставляет:
- GET /book/temporal/chain — temporal chain из WorldModel
- GET /book/temporal/context/{epoch_id} — богатый контекст эпохи
- GET /book/temporal/node/{epoch_id} — отдельный temporal узел
- POST /book/temporal/reconstruct — реконструкция путей
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from auth.rbac import require_role

log = logging.getLogger("routes.temporal")

router = APIRouter(prefix="/temporal", tags=["Temporal Model"])


# ── Модели запросов ────────────────────────────────────────


class ReconstructRequest(BaseModel):
    """Запрос на реконструкцию пути."""

    source: str = Field(..., min_length=1, description="ID начального узла")
    target: str = Field(..., min_length=1, description="ID конечного узла")
    direction: str = Field("BACKWARD", description="Направление: BACKWARD или FORWARD")
    max_depth: int = Field(10, ge=1, le=50, description="Максимальная глубина поиска")


# ── Фабрики ──────────────────────────────────────────────────


def _get_world_model():
    from narrative_engine.world_model import WorldModel

    return WorldModel.load()


def _get_reconstruction_engine():
    from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
    from narrative_engine.world_model import WorldModel

    wm = WorldModel.load()
    engine = TemporalReconstructionEngine.from_world_model(wm)
    return engine


def _enrich_canonical_anchor(chain_data: dict) -> dict:
    """C1 (Temporal API Alignment, ADR_TEMPORAL_WORLD_MODEL).

    Выравнивает public /chain с canonical M8.1 engine-путём:
    temporal_arkaim_era получает provenance из ArkaimAnchor
    (AUTHOR_CANON + EXTERNAL_SOURCE, дедуп по категории) и
    confidence=0.85 — ровно то же, что делает
    TemporalReconstructionEngine.from_world_model (reconstruction_engine.py:589-595).
    Новых provenance-значений НЕ придумывается; данные не меняются.
    """
    from narrative_engine.temporal.arkaim_anchor import ArkaimAnchor

    anchor = ArkaimAnchor.from_existing_data()
    for node in chain_data.get("nodes", []):
        if node.get("id") != "temporal_arkaim_era":
            continue
        existing_cats = {p.get("category") for p in node.get("provenance", [])}
        enriched = list(node.get("provenance", []))
        for tag in anchor.provenance:
            if tag.category.value not in existing_cats:
                enriched.append(tag.to_dict())
                existing_cats.add(tag.category.value)
        node["provenance"] = enriched
        node["confidence"] = 0.85
    return chain_data


# ── Эндпоинты ────────────────────────────────────────────────


@router.get("/chain", summary="Temporal chain из WorldModel")
async def get_temporal_chain(direction: str = Query("BACKWARD", description="Направление цепочки: BACKWARD или FORWARD")):
    """Получить temporal chain, построенную из эпох WorldModel."""
    wm = _get_world_model()

    if direction not in ("BACKWARD", "FORWARD"):
        raise HTTPException(400, detail=f"Invalid direction: {direction}. Use BACKWARD or FORWARD")

    chain_data = wm.get_temporal_chain(direction)

    # C1: canonical provenance для arkaim-якоря (тот же enrichment, что M8.1 engine)
    chain_data = _enrich_canonical_anchor(chain_data)

    return {
        "ok": True,
        "data": chain_data,
        "stats": {
            "nodes": len(chain_data.get("nodes", [])),
            "relations": len(chain_data.get("relations", [])),
            "gaps": len(chain_data.get("gaps", [])),
        },
    }


@router.get("/node/{epoch_id}", summary="Temporal node для эпохи")
async def get_temporal_node(epoch_id: str):
    """Получить temporal node для конкретной эпохи."""
    wm = _get_world_model()
    node_data = wm.get_temporal_node(epoch_id)

    if not node_data:
        raise HTTPException(404, detail=f"Epoch '{epoch_id}' not found in WorldModel")

    return {
        "ok": True,
        "data": node_data,
    }


@router.get("/context/{epoch_id}", summary="Богатый контекст эпохи")
async def get_temporal_context(epoch_id: str):
    """Получить богатый контекст эпохи: узел + события + персонажи + технологии."""
    wm = _get_world_model()
    ctx = wm.get_temporal_context(epoch_id)

    if not ctx:
        raise HTTPException(404, detail=f"Epoch '{epoch_id}' not found in WorldModel")

    return {
        "ok": True,
        "data": ctx,
    }


@router.post("/reconstruct", summary="Реконструкция путей")
async def reconstruct_path(request: ReconstructRequest):
    """Запустить реконструкцию путей между узлами."""
    engine = _get_reconstruction_engine()

    # Нормализуем ID узлов
    source_id = request.source if request.source.startswith("temporal_") else f"temporal_{request.source}"
    target_id = request.target if request.target.startswith("temporal_") else f"temporal_{request.target}"

    from narrative_engine.temporal.chain import ChainDirection

    direction = ChainDirection.BACKWARD if request.direction == "BACKWARD" else ChainDirection.FORWARD

    results = engine.find_paths(
        source_id=source_id,
        target_id=target_id,
        direction=direction,
        max_depth=request.max_depth,
    )

    return {
        "ok": True,
        "data": {
            "source": source_id,
            "target": target_id,
            "direction": request.direction,
            "paths_found": len(results),
            "results": [r.to_dict() for r in results],
        },
    }


@router.get("/chains", summary="Список всех цепочек")
async def list_chains():
    """Получить список всех доступных temporal цепочек."""
    wm = _get_world_model()

    chains = {}
    for direction in ("BACKWARD", "FORWARD"):
        chain_data = wm.get_temporal_chain(direction)
        chains[direction] = {
            "id": chain_data.get("id"),
            "label": chain_data.get("label"),
            "nodes": len(chain_data.get("nodes", [])),
            "relations": len(chain_data.get("relations", [])),
            "gaps": len(chain_data.get("gaps", [])),
        }

    return {
        "ok": True,
        "data": chains,
    }


@router.get("/nodes", summary="Все temporal nodes")
async def list_nodes():
    """Получить список всех temporal nodes из WorldModel.

    B1 (Temporal API Alignment, ADR_TEMPORAL_WORLD_MODEL):
    добавляет temporal_today — методологический anchor M8.1
    (TemporalNode.present_anchor(): provenance=HYPOTHESIS, без relations).
    Порядок как в canonical engine: эпохи, затем today.
    Новая temporal semantics НЕ создаётся.
    """
    wm = _get_world_model()
    epochs = wm.get_epochs()

    nodes = []
    for epoch in epochs:
        node_data = wm.get_temporal_node(epoch.id)
        if node_data:
            nodes.append(node_data)

    # B1: canonical M8.1 anchor (той же фабрикой, что и reconstruction_engine)
    from narrative_engine.temporal.node import TemporalNode

    nodes.append(TemporalNode.present_anchor().to_dict())

    return {
        "ok": True,
        "data": nodes,
        "total": len(nodes),
    }


# ── Future Extrapolation (M8) ──────────────────────────────────


class ExtrapolateRequest(BaseModel):
    """Запрос на экстраполяцию будущего от Аркаима."""

    prompt: str = Field("", max_length=500, description="Контекст/запрос пользователя")
    max_futures: int = Field(5, ge=1, le=20, description="Максимальное количество сценариев")
    anchor_id: str = Field("arkaim_era", description="Temporal node ID для начала экстраполяции")


@router.post("/future-extrapolation", summary="Экстраполяция будущего от якоря", dependencies=[Depends(require_role("reader"))])
async def extrapolate_future(req: ExtrapolateRequest):
    """Экстраполировать возможные сценарии будущего от заданного якоря.

    M8: использует TemporalChain (FORWARD) + CompatibilityChecker.
    Read-only: не создаёт новые узлы в temporal graph.
    """
    from narrative_engine.world_model import WorldModel
    from narrative_engine.temporal.future_extrapolator import FutureExtrapolator

    wm = WorldModel.load()
    extrapolator = FutureExtrapolator(wm)

    result = extrapolator.extrapolate(
        prompt=req.prompt,
        max_futures=req.max_futures,
        anchor_id=req.anchor_id,
    )

    # Check if anchor exists
    anchor_node = wm.get_temporal_node(req.anchor_id)
    if not anchor_node:
        raise HTTPException(
            404,
            detail=f"Anchor node '{req.anchor_id}' not found in WorldModel",
        )

    return {
        "ok": True,
        "data": result,
    }
