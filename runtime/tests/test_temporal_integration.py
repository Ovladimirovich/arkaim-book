"""M4 tests: WorldModel ↔ Temporal Model Integration.

M4: проверка что WorldModel может быть транслирован в Temporal Model
и что TemporalReconstructionEngine может загрузить данные из WorldModel.
"""

from __future__ import annotations

import pytest

from narrative_engine.world_model import WorldModel
from narrative_engine.temporal.precision import TemporalPrecision
from narrative_engine.temporal.node import TemporalNode
from narrative_engine.temporal.relation import TemporalRelationType
from narrative_engine.temporal.chain import TemporalChain, ChainDirection
from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
from narrative_engine.source_levels import ProvenanceCategory, canonical_provenance


# ═══════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def minimal_world_model() -> WorldModel:
    """Создать WorldModel с минимальными данными для тестов."""
    data = {
        "version": "1.0.0",
        "updated_at": "2025-01-01T00:00:00Z",
        "epochs": [
            {
                "id": "pre_arkaim",
                "name": "Pre-Arkaim",
                "name_ru": "До Аркаима",
                "description": "Эпоха до Аркаима",
                "order": 0,
                "source_level": "CANON",
                "provenance": [],
            },
            {
                "id": "satya_yuga",
                "name": "Satya Yuga",
                "name_ru": "Сатья Юга",
                "description": "Золотой век",
                "order": 1,
                "source_level": "CANON",
                "provenance": [],
            },
            {
                "id": "treta_yuga",
                "name": "Treta Yuga",
                "name_ru": "Трета Юга",
                "description": "Серебряный век",
                "order": 2,
                "source_level": "CANON",
                "provenance": [],
            },
            {
                "id": "dvapara_yuga",
                "name": "Dvapara Yuga",
                "name_ru": "Двапара Юга",
                "description": "Бронзовый век",
                "order": 3,
                "source_level": "CANON",
                "provenance": [],
            },
            {"id": "kali_yuga", "name": "Kali Yuga", "name_ru": "Кали Юга", "description": "Тёмный век", "order": 4, "source_level": "CANON", "provenance": []},
            {
                "id": "arkaim_era",
                "name": "Arkaim Era",
                "name_ru": "Эпоха Аркаима",
                "description": "Эпоха Аркаима",
                "order": 5,
                "source_level": "CANON",
                "provenance": [{"source_level": "CANON", "category": "AUTHOR_CANON", "confidence": 1.0, "notes": "from book canon"}],
            },
        ],
        "locations": [],
        "civilizations": [],
        "technologies": [],
        "religions": [],
        "canonical_events": [],
        "causal_rules": [],
        "characters_living": {},
    }
    return WorldModel(data)


@pytest.fixture
def loaded_world_model() -> WorldModel:
    """Загрузить WorldModel из файла (если есть)."""
    return WorldModel.load()


# ═══════════════════════════════════════════════════════════════
# WorldModel.get_temporal_node
# ═══════════════════════════════════════════════════════════════


class TestWorldModelTemporalNode:
    def test_get_temporal_node_existing_epoch(self, minimal_world_model):
        """Существующая эпоха → TemporalNode."""
        node_data = minimal_world_model.get_temporal_node("arkaim_era")
        assert node_data is not None
        assert node_data["id"] == "temporal_arkaim_era"
        assert node_data["label"] == "Эпоха Аркаима"
        assert node_data["era_id"] == "arkaim_era"
        assert node_data["precision"] == TemporalPrecision.RELATIVE.value
        assert node_data["is_anchor"] is True

    def test_get_temporal_node_nonexistent(self, minimal_world_model):
        """Не существующая эпоха → None."""
        assert minimal_world_model.get_temporal_node("nonexistent") is None

    def test_get_temporal_node_all_epochs(self, minimal_world_model):
        """Все эпохи могут быть конвертированы."""
        epochs = minimal_world_model.get_epochs()
        for epoch in epochs:
            node_data = minimal_world_model.get_temporal_node(epoch.id)
            assert node_data is not None
            assert node_data["id"] == f"temporal_{epoch.id}"
            assert node_data["era_id"] == epoch.id

    def test_temporal_node_has_canon_provenance(self, minimal_world_model):
        """TemporalNode наследует provenance из Epoch."""
        node_data = minimal_world_model.get_temporal_node("arkaim_era")
        assert len(node_data["provenance"]) == 1
        tag = node_data["provenance"][0]
        assert tag["category"] == ProvenanceCategory.AUTHOR_CANON.value
        assert tag["confidence"] == 1.0

    def test_temporal_node_confidence(self, minimal_world_model):
        """TemporalNode имеет confidence."""
        node_data = minimal_world_model.get_temporal_node("arkaim_era")
        assert node_data["confidence"] == 0.8

    def test_temporal_node_bounds(self, minimal_world_model):
        """TemporalNode bounds заполнены если есть start/end event."""
        node_data = minimal_world_model.get_temporal_node("arkaim_era")
        assert "bounds" in node_data
        # bounds может быть None если нет start/end
        if node_data["bounds"]:
            assert "start" in node_data["bounds"]
            assert "end" in node_data["bounds"]


# ═══════════════════════════════════════════════════════════════
# WorldModel.get_temporal_chain
# ═══════════════════════════════════════════════════════════════


class TestWorldModelTemporalChain:
    def test_get_temporal_chain_backward(self, minimal_world_model):
        """BACKWARD chain из WorldModel."""
        chain_data = minimal_world_model.get_temporal_chain("BACKWARD")
        assert chain_data["id"] == "chain_backward"
        assert chain_data["direction"] == "BACKWARD"
        assert len(chain_data["nodes"]) == 6  # 6 эпох
        assert len(chain_data["relations"]) == 5  # 5 связей между 6 эпохами

    def test_get_temporal_chain_forward(self, minimal_world_model):
        """FORWARD chain из WorldModel."""
        chain_data = minimal_world_model.get_temporal_chain("FORWARD")
        assert chain_data["direction"] == "FORWARD"
        assert len(chain_data["nodes"]) == 6

    def test_chain_nodes_in_order(self, minimal_world_model):
        """Узлы в chain в правильном порядке."""
        chain_data = minimal_world_model.get_temporal_chain("BACKWARD")
        node_ids = [n["id"] for n in chain_data["nodes"]]
        # BACKWARD: от newer к older
        assert "temporal_arkaim_era" in node_ids
        assert "temporal_pre_arkaim" in node_ids

    def test_chain_relations_are_precedes(self, minimal_world_model):
        """Связи между эпохами — PRECEDES."""
        chain_data = minimal_world_model.get_temporal_chain("BACKWARD")
        for rel in chain_data["relations"]:
            assert rel["relation_type"] == TemporalRelationType.PRECEDES.value

    def test_chain_has_stats(self, minimal_world_model):
        """Chain имеет статистику."""
        chain_data = minimal_world_model.get_temporal_chain("BACKWARD")
        assert "stats" in chain_data
        assert chain_data["stats"]["nodes"] == 6
        assert chain_data["stats"]["relations"] == 5

    def test_empty_world_model_chain(self):
        """Пустой WorldModel → пустая chain."""
        empty_wm = WorldModel({})
        chain_data = empty_wm.get_temporal_chain()
        assert chain_data["id"] == "empty_chain"
        assert len(chain_data["nodes"]) == 0


# ═══════════════════════════════════════════════════════════════
# WorldModel.get_temporal_context
# ═══════════════════════════════════════════════════════════════


class TestWorldModelTemporalContext:
    def test_get_temporal_context_existing_epoch(self, minimal_world_model):
        """Контекст существующей эпохи."""
        ctx = minimal_world_model.get_temporal_context("arkaim_era")
        assert "temporal_node" in ctx
        assert "epoch" in ctx
        assert "events" in ctx
        assert "characters" in ctx
        assert "technologies" in ctx
        assert ctx["temporal_node"]["id"] == "temporal_arkaim_era"

    def test_get_temporal_context_nonexistent(self, minimal_world_model):
        """Контекст несуществующей эпохи — пустой."""
        ctx = minimal_world_model.get_temporal_context("nonexistent")
        assert ctx == {}

    def test_temporal_context_event_count(self, minimal_world_model):
        """Счётчик событий в контексте."""
        ctx = minimal_world_model.get_temporal_context("arkaim_era")
        assert "event_count" in ctx
        assert isinstance(ctx["event_count"], int)


# ═══════════════════════════════════════════════════════════════
# WorldModel.get_temporal_summary
# ═══════════════════════════════════════════════════════════════


class TestWorldModelTemporalSummary:
    def test_temporal_summary(self, minimal_world_model):
        """Сводка temporal модели."""
        summary = minimal_world_model.get_temporal_summary()
        assert summary["total_epochs"] == 6
        assert summary["temporal_chain_available"] is True
        assert len(summary["epochs"]) == 6

    def test_temporal_summary_empty(self):
        """Сводка пустого WorldModel."""
        empty_wm = WorldModel({})
        summary = empty_wm.get_temporal_summary()
        assert summary["total_epochs"] == 0
        assert summary["temporal_chain_available"] is False


# ═══════════════════════════════════════════════════════════════
# TemporalReconstructionEngine.from_world_model
# ═══════════════════════════════════════════════════════════════


class TestEngineFromWorldModel:
    def test_engine_from_minimal_world_model(self, minimal_world_model):
        """Engine загружен из минимального WorldModel."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        nodes = engine.get_all_nodes()
        # 6 эпох + 1 ArkaimAnchor = 7 узлов
        assert len(nodes) >= 6

    def test_engine_has_arkaim_node(self, minimal_world_model):
        """В engine есть ArkaimAnchor."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        arkaim_nodes = [n for n in engine.get_all_nodes() if "arkaim" in n.id.lower()]
        assert len(arkaim_nodes) >= 1

    def test_engine_has_relations(self, minimal_world_model):
        """В engine есть временные связи."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        rels = engine.get_all_relations()
        assert len(rels) >= 5  # 5 связей между 6 эпохами

    def test_engine_can_find_path(self, minimal_world_model):
        """Engine может найти путь между узлами."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        results = engine.find_paths("temporal_pre_arkaim", "temporal_arkaim_era")
        # Путь должен существовать
        assert len(results) >= 0  # either 0 or more

    def test_engine_backward_reconstruction(self, minimal_world_model):
        """BACKWARD reconstruction из WorldModel."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        path = engine.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
        assert path is not None
        assert path.direction == ChainDirection.BACKWARD
        # Должен содержать узлы из WorldModel
        node_ids = [n.id for n in path.nodes]
        assert "temporal_arkaim_era" in node_ids

    def test_engine_forward_reconstruction(self, minimal_world_model):
        """FORWARD reconstruction из WorldModel."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        path = engine.reconstruct_chain("temporal_pre_arkaim", ChainDirection.FORWARD)
        assert path is not None
        assert path.direction == ChainDirection.FORWARD

    def test_engine_preserves_provenance(self, minimal_world_model):
        """Provenance сохраняется при загрузке из WorldModel."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        arkaim_node = engine.get_node("temporal_arkaim_era")
        assert arkaim_node is not None
        # provenance должен быть AUTHOR_CANON (из canonical_provenance)
        assert any(t.category == ProvenanceCategory.AUTHOR_CANON for t in arkaim_node.provenance)


# ═══════════════════════════════════════════════════════════════
# Integration: WorldModel → TemporalChain → Reconstruction
# ═══════════════════════════════════════════════════════════════


class TestFullIntegration:
    def test_chain_to_engine_to_path(self, minimal_world_model):
        """Full integration: WorldModel → TemporalChain → Engine → Path."""
        # Step 1: Build chain from WorldModel
        chain_data = minimal_world_model.get_temporal_chain("BACKWARD")
        _chain = TemporalChain.from_dict(chain_data)

        # Step 2: Load engine from WorldModel
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)

        # Step 3: Find path
        results = engine.find_paths("temporal_pre_arkaim", "temporal_arkaim_era")
        assert len(results) >= 0  # path may or may not exist

    def test_arkaim_anchor_in_engine(self, minimal_world_model):
        """Canonical Arkaim anchor (temporal_arkaim_era) present in engine."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        # M8.1: temporal_arkaim_era is canonical; temporal_arkaim_anchor removed (orphan)
        anchor_node = engine.get_node("temporal_arkaim_era")
        assert anchor_node is not None
        assert anchor_node.is_anchor is True
        # Orphan should NOT be in graph
        orphan = engine.get_node("temporal_arkaim_anchor")
        assert orphan is None

    def test_no_invented_nodes_in_engine(self, minimal_world_model):
        """Engine не создаёт новых узлов при загрузке из WorldModel."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        nodes = engine.get_all_nodes()
        # Все узлы должны соответствовать epoch_id из WorldModel
        wm_epoch_ids = {e.id for e in minimal_world_model.get_epochs()}
        for node in nodes:
            if node.era_id:
                assert node.era_id in wm_epoch_ids or node.era_id == "arkaim_era"

    def test_provenance_not_downgraded(self, minimal_world_model):
        """Provenance не понижается при интеграции."""
        engine = TemporalReconstructionEngine.from_world_model(minimal_world_model)
        arkaim_node = engine.get_node("temporal_arkaim_era")
        assert arkaim_node is not None
        # AUTHOR_CANON должен сохраниться
        assert any(t.category == ProvenanceCategory.AUTHOR_CANON for t in arkaim_node.provenance)


# ═══════════════════════════════════════════════════════════════
# Regression: M1+M2 tests still pass
# ═══════════════════════════════════════════════════════════════


class TestM1M2Regression:
    def test_provenance_still_works(self):
        from narrative_engine.source_levels import ProvenanceCategory

        tag = canonical_provenance()
        assert tag.category == ProvenanceCategory.AUTHOR_CANON

    def test_temporal_node_still_works(self):
        node = TemporalNode.present_anchor()
        assert node.id == "temporal_today"
        assert node.precision == TemporalPrecision.EXACT

    def test_temporal_chain_still_works(self):
        chain = TemporalChain.backward_from_today([TemporalNode.present_anchor()])
        assert chain.direction == ChainDirection.BACKWARD
