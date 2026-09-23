"""World Engine — центральный координатор вычислимой модели мира."""
from __future__ import annotations

import logging
from typing import Any, Optional

from .world_model_ext import WorldModelExt, get_world_model_ext
from .relation_models import RelationGraph, WorldRelation, RelationType
from .relation_extractor import extract_relations

log = logging.getLogger("hermes.world_engine")


class WorldEngine:
    """Движок мира — центральный координатор.
    
    Интегрирует:
    - WorldModelExt — данные о мире (13 категорий, 406 сущностей)
    - RelationGraph — граф связей (287 связей)
    - FormEngine — визуальные формы (55 форм, 11 категорий)
    - ConsistencyEngine — проверка допустимости
    - ExperienceEngine — 10 режимов работы
    """
    
    def __init__(self):
        self._world_model = get_world_model_ext()
        self._relation_graph: Optional[RelationGraph] = None
        self._form_engine = None
        self._consistency_engine = None
        self._experience_engine = None
        self._initialized = False
        self._entity_index: dict[str, dict] = {}
        # M5.1: optional temporal integration (disabled by default)
        self._temporal_engine = None
    
    def initialize(self):
        """Инициализировать движок (загрузить данные)."""
        if self._initialized:
            return
        
        log.info("world_engine_initializing")
        
        # Загружаем граф связей
        self._relation_graph = extract_relations()
        
        # Создаём поддвижки
        from .form_engine import FormEngine
        from .consistency_engine import ConsistencyEngine
        from .experience_engine import ExperienceEngine
        
        self._form_engine = FormEngine(self)
        self._consistency_engine = ConsistencyEngine(self)
        self._experience_engine = ExperienceEngine(self)
        
        # Build entity index for O(1) lookups
        for category in self._world_model.get_categories():
            for item in self._world_model.get_category(category):
                entity_id = item.get("id")
                if entity_id:
                    self._entity_index[entity_id] = {"category": category, **item}
        
        self._initialized = True
        log.info("world_engine_initialized %s", self.summary())

    # ── Temporal Integration (M5.1) ──────────────────────────────────

    @property
    def temporal_engine(self) -> Optional["TemporalReconstructionEngine"]:
        """Optional temporal engine — None until enable_temporal() called."""
        return self._temporal_engine

    def enable_temporal(self) -> "TemporalReconstructionEngine":
        """Enable temporal reconstruction capability (opt-in, lazy).

        M5.1: builds TemporalReconstructionEngine from canonical WorldModel.
        Idempotent: repeated calls return the same instance.
        Read-only: does not mutate WorldModel or WorldModelExt.
        """
        if self._temporal_engine is not None:
            return self._temporal_engine

        from narrative_engine.world_model import WorldModel
        from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine

        # Load canonical WorldModel (separate from WorldModelExt)
        # WorldModelExt and WorldModel are different data sources:
        # - WorldModelExt: file-based categories from WORLD_MODEL/*.json
        # - WorldModel: structured epochs/events from WORLD_MODEL.json
        wm = WorldModel.load()

        self._temporal_engine = TemporalReconstructionEngine.from_world_model(wm)

        log.info(
            "temporal_engine_enabled epochs=%d nodes=%d",
            len(wm.get_epochs()),
            len(self._temporal_engine.get_all_nodes()),
        )
        return self._temporal_engine

    def refresh_temporal(self, world_model=None) -> bool:
        """Refresh temporal engine from WorldModel.

        M10: called after human-confirmed WorldModel update.
        Args:
            world_model: optional explicitly-provided WorldModel
                         (e.g. the in-memory instance just updated by the caller).
                         If None — loads canonical WorldModel.
        Read-only: does not mutate WorldModel.
        Returns True if engine was (re)built, False if nothing to build from.
        """
        from narrative_engine.world_model import WorldModel
        from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine

        wm = world_model if world_model is not None else WorldModel.load()
        if not wm.get_epochs():
            log.warning("temporal_refresh_skipped no_epochs")
            return False

        old_id = id(self._temporal_engine) if self._temporal_engine is not None else None
        self._temporal_engine = TemporalReconstructionEngine.from_world_model(wm)
        log.info(
            "temporal_engine_refreshed old_id=%s new_id=%s epochs=%d",
            old_id, id(self._temporal_engine), len(wm.get_epochs()),
        )
        return True

    # ── Temporal Query Facade (M5.2) ────────────────────────────────

    def get_temporal_chain(self, direction: str = "BACKWARD") -> Optional[dict]:
        """Get temporal chain from WorldEngine (thin facade over M3).

        Returns JSON-serializable dict or None if temporal is disabled / no chain found.
        Does NOT mutate WorldModel.
        """
        if self._temporal_engine is None:
            return None

        from narrative_engine.temporal.chain import ChainDirection

        anchor = "temporal_arkaim_era"
        chain_dir = ChainDirection(direction.upper())
        result = self._temporal_engine.reconstruct_chain(anchor, chain_dir)
        if result is None:
            return None
        return result.to_dict()

    def find_temporal_path(
        self,
        source: str,
        target: str,
        direction: str = "BACKWARD",
    ) -> Optional[dict]:
        """Find shortest temporal path between two nodes (thin facade over M3).

        Returns JSON-serializable dict or None if temporal is disabled / no path found.
        Does NOT mutate WorldModel.
        """
        if self._temporal_engine is None:
            return None

        from narrative_engine.temporal.chain import ChainDirection

        chain_dir = ChainDirection(direction.upper())
        result = self._temporal_engine.find_shortest_path(source, target, chain_dir)
        if result is None:
            return None
        return result.to_dict()

    # ── M8.1: Full Temporal Pipeline Orchestration ─────────────────

    def get_full_temporal_pipeline(
        self,
        prompt: str = "",
        max_futures: int = 5,
    ) -> Optional[dict]:
        """Compose full temporal pipeline: PRESENT → ARKAIM → FUTURE.

        M8.1: orchestrates BACKWARD reconstruction + FORWARD extrapolation.
        Does NOT create graph relations. Read-only operation.

        Pipeline:
          PRESENT (temporal_today, HYPOTHESIS)
            ↓ _trace_backward(arkaim_era) — computed reconstruction path
          ARKAIM (temporal_arkaim_era, enriched provenance)
            ↓ FutureExtrapolator — standalone M8 engine
          FUTURE (scenarios, FUTURE_EXTRAPOLATION provenance)
        """
        if self._temporal_engine is None:
            return None

        te = self._temporal_engine

        # 1. BACKWARD reconstruction (computed path, NOT graph relation)
        from narrative_engine.temporal.chain import ChainDirection
        backward = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
        backward_data = backward.to_dict() if backward else None

        # 2. Verify temporal_today exists as methodological anchor
        today_node = te.get_node("temporal_today")
        today_present = today_node is not None

        # 3. FORWARD extrapolation (M8 standalone)
        from narrative_engine.temporal.future_extrapolator import FutureExtrapolator
        from narrative_engine.world_model import WorldModel
        wm = WorldModel.load()
        extrapolator = FutureExtrapolator(wm)
        forward = extrapolator.extrapolate(
            prompt=prompt,
            max_futures=max_futures,
            anchor_id="arkaim_era",
        )

        # 4. Compose full pipeline result
        return {
            "pipeline": "PRESENT → ARKAIM → FUTURE",
            "present_anchor": {
                "id": "temporal_today",
                "label": today_node.label if today_node else "unknown",
                "exists": today_present,
                "provenance": today_node.provenance if today_node else [],
                "role": "methodological starting point — not book canon",
            },
            "backward_reconstruction": backward_data,
            "arkaim_anchor": {
                "id": "temporal_arkaim_era",
                "is_canonical": True,
                "provenance": [
                    p.to_dict() for p in (
                        te.get_node("temporal_arkaim_era").provenance
                        if te.get_node("temporal_arkaim_era") else []
                    )
                ],
            },
            "forward_extrapolation": forward,
            "provenance_invariants": {
                "present_is_hypothesis": True,
                "backward_is_reconstruction": True,
                "future_is_extrapolation": True,
                "no_graph_relation_present_to_arkaim": True,
            },
        }
    
    @property
    def world_model(self) -> WorldModelExt:
        return self._world_model
    
    @property
    def relation_graph(self) -> RelationGraph:
        if self._relation_graph is None:
            self.initialize()
        return self._relation_graph
    
    @property
    def form_engine(self):
        if self._form_engine is None:
            self.initialize()
        return self._form_engine
    
    @property
    def consistency(self):
        if self._consistency_engine is None:
            self.initialize()
        return self._consistency_engine
    
    @property
    def experience(self):
        if self._experience_engine is None:
            self.initialize()
        return self._experience_engine
    
    # ── Поиск ──────────────────────────────────────────────────
    
    def search(self, query: str) -> dict:
        """Поиск по всему миру."""
        # Ищем в WorldModel
        wm_results = self._world_model.search(query)
        
        # Ищем в графе связей
        graph_results = []
        if self._relation_graph:
            for entity_id in self._relation_graph._by_source:
                if query.lower() in entity_id.lower():
                    context = self._relation_graph.get_entity_context(entity_id)
                    graph_results.append(context)
        
        return {
            "world_model": wm_results,
            "relations": graph_results,
            "total": len(wm_results) + len(graph_results),
        }
    
    def get_entity(self, entity_id: str) -> Optional[dict]:
        """Получить сущность по ID (O(1) через индекс)."""
        return self._entity_index.get(entity_id)
    
    def get_entity_context(self, entity_id: str) -> dict:
        """Получить контекст сущности — все её связи."""
        entity = self.get_entity(entity_id)
        
        relations = {}
        if self._relation_graph:
            relations = self._relation_graph.get_entity_context(entity_id)
        
        # Добавляем визуальную форму
        form_context = None
        if self._form_engine:
            form_context = self._form_engine.build_form_context(entity_id)
        
        return {
            "entity": entity,
            "relations": relations,
            "form_context": form_context,
        }
    
    # ── Статистика ─────────────────────────────────────────────
    
    def get_stats(self) -> dict:
        """Статистика мира."""
        wm_stats = self._world_model.get_stats()
        graph_stats = self._relation_graph.get_stats() if self._relation_graph else {}
        
        return {
            "world_model": wm_stats,
            "relation_graph": graph_stats,
            "form_engine": self._form_engine.summary() if self._form_engine else "",
            "initialized": self._initialized,
        }
    
    def summary(self) -> str:
        """Текстовая сводка."""
        wm_summary = self._world_model.summary()
        graph_summary = self._relation_graph.summary() if self._relation_graph else " граф не загружен"
        form_summary = self._form_engine.summary() if self._form_engine else ""
        return f"World Engine: {wm_summary}{graph_summary}, {form_summary}"


# ── Фабрика ────────────────────────────────────────────────────

_world_engine_cache: Optional[WorldEngine] = None

def get_world_engine() -> WorldEngine:
    """Получить singleton WorldEngine."""
    global _world_engine_cache
    if _world_engine_cache is None:
        _world_engine_cache = WorldEngine()
        _world_engine_cache.initialize()
    return _world_engine_cache

def invalidate_world_engine():
    """Сбросить кэш."""
    global _world_engine_cache
    _world_engine_cache = None
