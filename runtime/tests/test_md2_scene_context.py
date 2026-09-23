"""MD-2 Scene Context Consolidation — unit-тесты подэтапа 1.

Инварианты (MD2_PRE_IMPLEMENTATION_AUDIT §7):
  1. SceneContext v2 = расширение VisualContext (не новый класс);
  2. temporal — read-only из WorldModel (никакого синтеза);
  3. source_refs — ссылки, не копии;
  4. integrity.links_synthesized всегда False;
  5. media-neutral: никаких execution-полей;
  6. additive non-breaking: legacy-поля/методы не тронуты.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md2_scene_context.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from visual.visual_context import VisualContext
from visual.scene_context import (
    SceneContextExtras,
    SourceRefs,
    TemporalSceneRef,
    ProvenanceRef,
    extend_visual_context,
)


# ── Фикстуры данных (копии структур, а не загрузка всего genome) ──

GENOME = {
    "modules": {
        "scenes": [
            {
                "chapter": 1,
                "scene_id": "s1",
                "title": "Тестовая сцена",
                "characters": ["hero"],
                "location": "loc1",
                "emotion": "conflict",
                "meaning_tags": ["conflict:гиперборея"],
            }
        ],
        "character_visuals": [],
        "location_visuals": [],
    },
    "world_entities": [],
}

class FakeWorldModel:
    """Минимальный double существующего WorldModel-API (get_temporal_context/get_events).

    Воспроизводит фактическую структуру ответа WorldModel.get_temporal_context
    (world_model.py:408-431): temporal_node/epoch/events/characters/technologies.
    """

    def __init__(self, epochs=None, events=None):
        self._epochs = epochs or {}
        self._events = events or []

    def get_events(self):
        return self._events

    def get_temporal_context(self, epoch_id: str):
        if epoch_id not in self._epochs:
            return {}
        node, epoch = self._epochs[epoch_id]
        return {
            "temporal_node": node,
            "epoch": epoch,
            "events": [],
            "characters": [],
            "technologies": [],
            "event_count": 2,
            "character_count": 3,
            "technology_count": 1,
        }


WM_WITH_EPOCH = FakeWorldModel(
    epochs={
        "arkaim_era": (
            {
                "id": "temporal_arkaim_era",
                "label": "Эпоха Аркаима",
                "confidence": 0.8,
                "bounds": {"start": "2000 BCE", "end": "1500 BCE", "uncertainty": "±200 лет"},
                "provenance": [
                    {"category": "AUTHOR_CANON", "source": "book", "confidence": 0.9},
                    {"category": "EXTERNAL_SOURCE", "source": "archaeology", "confidence": 0.7},
                    {"category": "AUTHOR_CANON", "source": "book2", "confidence": 0.8},
                ],
            },
            {"name_ru": "Эпоха Аркаима", "description": "Эпоха города",
             "civilizations_active": ["arkaim"], "technologies_available": ["bronze"]},
        ),
    },
    events=[type("E", (), {"chapter": 1, "epoch": "arkaim_era"})()],
)


# ── 1. VisualContext v2 — additive non-breaking ─────────────────

class TestVisualContextV2:
    def test_scene_extras_default_none(self):
        """Без MD-2-вызова VisualContext ведёт себя как раньше (extras=None)."""
        ctx = VisualContext()
        assert ctx.scene_extras is None
        assert ctx.scene.title == ""  # все legacy-поля на месте
        assert ctx.style.name == "cinematic_fantasy"

    def test_extend_adds_extras_without_touching_legacy(self):
        ctx = VisualContext()
        ctx.scene.title = "Battle"
        extend_visual_context(ctx)
        assert isinstance(ctx.scene_extras, SceneContextExtras)
        assert ctx.scene.title == "Battle"  # legacy не изменён
        assert ctx.scene_extras.temporal.epoch_id == ""

    def test_to_dict_serializes_extras(self):
        ctx = VisualContext()
        extend_visual_context(ctx, TemporalSceneRef(epoch_id="arkaim_era"))
        d = ctx.to_dict()
        assert d["scene_extras"]["temporal"]["epoch_id"] == "arkaim_era"
        assert "scene" in d and "camera" in d  # legacy-поля сериализуются как раньше

    def test_to_dict_without_extras_returns_none(self):
        assert VisualContext().to_dict()["scene_extras"] is None

    def test_summary_shows_epoch_when_temporal(self):
        ctx = VisualContext()
        extend_visual_context(ctx, TemporalSceneRef(epoch_id="arkaim_era"))
        assert "epoch=arkaim_era" in ctx.summary()
        assert "epoch=" not in VisualContext().summary()


# ── 2. Инвариант integrity: связи не синтезируются ────────────────

class TestIntegrityInvariant:
    def test_links_never_synthesized(self):
        ctx = VisualContext()
        extend_visual_context(ctx)
        assert ctx.scene_extras.integrity.links_synthesized is False

    def test_temporal_read_only_flag(self):
        ctx = VisualContext()
        extend_visual_context(ctx, TemporalSceneRef(epoch_id="x"))
        assert ctx.scene_extras.integrity.temporal_read_only is True

    def test_provenance_inherited_only_with_temporal(self):
        ctx = VisualContext()
        extend_visual_context(ctx, TemporalSceneRef(epoch_id="x",
                                                    provenance=[ProvenanceRef(category="AUTHOR_CANON")]))
        assert ctx.scene_extras.integrity.provenance_inherited is True
        ctx2 = VisualContext()
        extend_visual_context(ctx2, TemporalSceneRef(epoch_id="x"))
        assert ctx2.scene_extras.integrity.provenance_inherited is False


# ── 3. Media-neutral: никаких execution-полей ─────────────────────

class TestMediaNeutrality:
    EXECUTION_FIELDS = {"model", "steps", "seed", "cfg", "sampler", "workflow",
                        "node_graph", "provider", "checkpoint", "backend"}

    def test_extras_have_no_execution_fields(self):
        ctx = VisualContext()
        extend_visual_context(ctx, TemporalSceneRef(epoch_id="x"))
        d = ctx.to_dict()["scene_extras"]
        flat = set()
        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    flat.add(k)
                    walk(v)
            elif isinstance(obj, list):
                for i in obj:
                    walk(i)
        walk(d)
        leaked = self.EXECUTION_FIELDS & flat
        assert not leaked, f"execution-поля утекли в SceneContext: {leaked}"

    def test_visual_context_itself_still_media_neutral(self):
        """15 измерений VisualContext не содержат execution-полей (было/стало)."""
        ctx = VisualContext()
        extend_visual_context(ctx)
        flat = set()
        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    flat.add(k)
                    walk(v)
            elif isinstance(obj, list):
                for i in obj:
                    walk(i)
        walk(ctx.to_dict())
        leaked = self.EXECUTION_FIELDS & flat
        assert not leaked, f"execution-поля в VisualContext: {leaked}"


# ── 4. TemporalSceneRef: read-only проекция, без синтеза ───────────

class TestTemporalSceneRef:
    def test_provenance_dedup_by_category(self):
        """Дедуп по категории — паттерн C1-enrichment; порядок сохраняется."""
        from visual.visual_context_builder import VisualContextBuilder
        b = VisualContextBuilder(GENOME, world_model=WM_WITH_EPOCH)
        built = b._temporal_ref_from_epoch("arkaim_era")
        assert built.provenance_categories() == ["AUTHOR_CANON", "EXTERNAL_SOURCE"]

    def test_provenance_ref_from_tag_projection(self):
        class FakeTag:
            class category:
                value = "HYPOTHESIS"
            source = "reader"
            confidence = 0.5
        ref = ProvenanceRef.from_tag(FakeTag())
        assert ref.category == "HYPOTHESIS"
        assert ref.source == "reader"
        assert ref.confidence == 0.5

    def test_is_temporal_false_for_empty(self):
        assert TemporalSceneRef().is_temporal is False
        assert TemporalSceneRef(epoch_id="arkaim_era").is_temporal is True

    def test_counts_from_context(self):
        from visual.visual_context_builder import VisualContextBuilder
        b = VisualContextBuilder(GENOME, world_model=WM_WITH_EPOCH)
        ref = b._temporal_ref_from_epoch("arkaim_era")
        assert ref.event_count == 2 and ref.character_count == 3
        assert ref.bounds_start == "2000 BCE" and ref.bounds_end == "1500 BCE"


# ── 5. Builder: канонические входы + глава→эпоха без угадывания ───

class TestSceneContextBuilder:
    @pytest.fixture
    def builder(self):
        from visual.visual_context_builder import VisualContextBuilder
        return VisualContextBuilder(GENOME, world_model=WM_WITH_EPOCH)

    def test_build_scene_context_fills_all_extras(self, builder):
        import asyncio
        ctx = asyncio.run(builder.build_scene_context(1, "s1"))
        assert ctx.scene_extras.source_refs.scene_id == "s1"
        assert ctx.scene_extras.source_refs.chapter == 1
        # глава 1 имеет событие arkaim_era в FakeWorldModel → temporal подставлен
        assert ctx.scene_extras.temporal.epoch_id == "temporal_arkaim_era"
        assert ctx.scene_extras.integrity.links_synthesized is False

    def test_explicit_epoch_overrides_chapter_resolution(self, builder):
        import asyncio
        ctx = asyncio.run(builder.build_scene_context(1, "s1", epoch_id="arkaim_era"))
        assert ctx.scene_extras.temporal.epoch_id == "temporal_arkaim_era"

    def test_no_epoch_without_evidence(self, builder):
        """Сцена без событий по главе остаётся вне temporal-оси (без угадывания)."""
        import asyncio
        wm = FakeWorldModel(epochs=WM_WITH_EPOCH._epochs, events=[])
        from visual.visual_context_builder import VisualContextBuilder
        b = VisualContextBuilder(GENOME, world_model=wm)
        ctx = asyncio.run(b.build_scene_context(1, "s1"))
        assert ctx.scene_extras.temporal.is_temporal is False

    def test_no_world_model_means_no_temporal(self):
        """WorldModel не подключён → temporal пуст (builder не строит сам)."""
        import asyncio
        from visual.visual_context_builder import VisualContextBuilder
        b = VisualContextBuilder(GENOME)  # world_model=None
        ctx = asyncio.run(b.build_scene_context(1, "s1"))
        assert ctx.scene_extras.temporal.is_temporal is False
        assert ctx.scene_extras.integrity.links_synthesized is False

    def test_epoch_context_full_projection(self, builder):
        import asyncio
        ctx = asyncio.run(builder.build_scene_context_for_epoch("arkaim_era"))
        t = ctx.scene_extras.temporal
        assert t.is_temporal is True
        assert t.epoch_id == "temporal_arkaim_era"
        assert t.name_ru == "Эпоха Аркаима"
        assert ctx.scene.title == "Эпоха Аркаима"
        assert ctx.historical.civilization == "arkaim"

    def test_epoch_context_unknown_epoch_is_not_temporal(self, builder):
        """Неизвестная эпоха → is_temporal=False → маршрут ответит 404."""
        import asyncio
        ctx = asyncio.run(builder.build_scene_context_for_epoch("nope"))
        assert ctx.scene_extras.temporal.is_temporal is False

    def test_character_and_location_contexts(self, builder):
        import asyncio
        cc = asyncio.run(builder.build_scene_context_for_character("hero"))
        assert cc.scene_extras.source_refs.character_ids == ["hero"]
        assert cc.scene_extras.temporal.is_temporal is False
        lc = asyncio.run(builder.build_scene_context_for_location("loc1"))
        assert lc.scene_extras.source_refs.location_id == "loc1"

    def test_legacy_build_methods_unchanged(self, builder):
        """build/build_for_character/build_for_location работают как раньше (без extras)."""
        import asyncio
        ctx = asyncio.run(builder.build(1, "s1"))
        assert ctx.scene_extras is None  # legacy-метод не навязывает extras
        assert ctx.scene.title == "Тестовая сцена"


# ── 6. SourceRefs — ссылки, не копии ──────────────────────────────

class TestSourceRefs:
    def test_refs_are_ids_not_copies(self):
        refs = SourceRefs(scene_id="s1", chapter=1, location_id="loc1")
        d = refs.to_dict()
        assert set(d) == {"scene_id", "chapter", "character_ids", "location_id",
                          "entity_refs", "rag_fallback"}
        # никаких описаний/содержимого genome
        assert not any(isinstance(v, str) and len(v) > 60 for v in d.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
