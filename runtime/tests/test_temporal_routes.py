"""M5 tests: Temporal API routes.

M5.1: API routes для temporal model.
Тестирует: /book/temporal/* endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.main import app


# ═══════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def loaded_world_model():
    from narrative_engine.world_model import WorldModel
    return WorldModel.load()


# ═══════════════════════════════════════════════════════════════
# GET /book/temporal/chain
# ═══════════════════════════════════════════════════════════════


class TestTemporalChain:
    def test_get_chain_backward(self, client, loaded_world_model):
        """BACKWARD chain должен вернуть данные."""
        resp = client.get("/book/temporal/chain?direction=BACKWARD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "data" in data
        assert "stats" in data
        assert data["stats"]["nodes"] > 0

    def test_get_chain_forward(self, client, loaded_world_model):
        """FORWARD chain должен вернуть данные."""
        resp = client.get("/book/temporal/chain?direction=FORWARD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["data"]["direction"] == "FORWARD"

    def test_get_chain_invalid_direction(self, client):
        """Невалидное направление → 400."""
        resp = client.get("/book/temporal/chain?direction=INVALID")
        assert resp.status_code == 400

    def test_chain_stats_correct(self, client, loaded_world_model):
        """Статистика цепочки должна соответствовать данным."""
        resp = client.get("/book/temporal/chain?direction=BACKWARD")
        data = resp.json()
        nodes = data["data"]["nodes"]
        relations = data["data"]["relations"]
        assert data["stats"]["nodes"] == len(nodes)
        assert data["stats"]["relations"] == len(relations)


# ═══════════════════════════════════════════════════════════════
# GET /book/temporal/node/{epoch_id}
# ═══════════════════════════════════════════════════════════════


class TestTemporalNode:
    def test_get_node_existing(self, client, loaded_world_model):
        """Существующая эпоха → 200."""
        epochs = loaded_world_model.get_epochs()
        if not epochs:
            pytest.skip("No epochs in WorldModel")
        
        epoch_id = epochs[0].id
        resp = client.get(f"/book/temporal/node/{epoch_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "data" in data
        assert data["data"]["era_id"] == epoch_id

    def test_get_node_not_found(self, client):
        """Несуществующая эпоха → 404."""
        resp = client.get("/book/temporal/node/nonexistent_epoch")
        assert resp.status_code == 404

    def test_get_node_arkaim_era(self, client, loaded_world_model):
        """Эпоха arkaim_era должна быть anchor node."""
        resp = client.get("/book/temporal/node/arkaim_era")
        if resp.status_code == 200:
            data = resp.json()
            assert data["data"]["is_anchor"] is True


# ═══════════════════════════════════════════════════════════════
# GET /book/temporal/context/{epoch_id}
# ═══════════════════════════════════════════════════════════════


class TestTemporalContext:
    def test_get_context_existing(self, client, loaded_world_model):
        """Контекст существующей эпохи."""
        epochs = loaded_world_model.get_epochs()
        if not epochs:
            pytest.skip("No epochs in WorldModel")
        
        epoch_id = epochs[0].id
        resp = client.get(f"/book/temporal/context/{epoch_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        ctx = data["data"]
        assert "temporal_node" in ctx
        assert "epoch" in ctx
        assert "events" in ctx
        assert "characters" in ctx
        assert "technologies" in ctx

    def test_get_context_not_found(self, client):
        """Несуществующая эпоха → 404."""
        resp = client.get("/book/temporal/context/nonexistent_epoch")
        assert resp.status_code == 404

    def test_context_has_counts(self, client, loaded_world_model):
        """Контекст должен содержать счётчики."""
        epochs = loaded_world_model.get_epochs()
        if not epochs:
            pytest.skip("No epochs in WorldModel")
        
        epoch_id = epochs[0].id
        resp = client.get(f"/book/temporal/context/{epoch_id}")
        data = resp.json()["data"]
        assert "event_count" in data
        assert "character_count" in data


# ═══════════════════════════════════════════════════════════════
# POST /book/temporal/reconstruct
# ═══════════════════════════════════════════════════════════════


class TestTemporalReconstruct:
    def test_reconstruct_valid(self, client, loaded_world_model):
        """Реконструкция пути между существующими узлами."""
        epochs = loaded_world_model.get_epochs()
        if len(epochs) < 2:
            pytest.skip("Need at least 2 epochs")
        
        source = epochs[-1].id  # Последняя эпоха
        target = epochs[0].id   # Первая эпоха
        
        resp = client.post("/book/temporal/reconstruct", json={
            "source": source,
            "target": target,
            "direction": "BACKWARD",
            "max_depth": 10,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "data" in data
        assert "results" in data["data"]

    def test_reconstruct_invalid_nodes(self, client):
        """Реконструкция с несуществующими узлами."""
        resp = client.post("/book/temporal/reconstruct", json={
            "source": "nonexistent1",
            "target": "nonexistent2",
            "direction": "BACKWARD",
            "max_depth": 5,
        })
        # Должен вернуть 200, но с пустым results
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["data"]["paths_found"] == 0


# ═══════════════════════════════════════════════════════════════
# GET /book/temporal/chains
# ═══════════════════════════════════════════════════════════════


class TestTemporalChains:
    def test_list_chains(self, client):
        """Список цепочек должен содержать BACKWARD и FORWARD."""
        resp = client.get("/book/temporal/chains")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        chains = data["data"]
        assert "BACKWARD" in chains
        assert "FORWARD" in chains
        assert chains["BACKWARD"]["nodes"] > 0

    def test_chains_stats(self, client):
        """Статистика цепочек должна быть корректной."""
        resp = client.get("/book/temporal/chains")
        data = resp.json()["data"]
        for direction in ("BACKWARD", "FORWARD"):
            assert "nodes" in data[direction]
            assert "relations" in data[direction]
            assert "gaps" in data[direction]
            assert isinstance(data[direction]["nodes"], int)
            assert data[direction]["nodes"] > 0


# ═══════════════════════════════════════════════════════════════
# GET /book/temporal/nodes
# ═══════════════════════════════════════════════════════════════


class TestTemporalNodes:
    def test_list_nodes(self, client, loaded_world_model):
        """Список всех nodes."""
        resp = client.get("/book/temporal/nodes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "data" in data
        assert "total" in data
        assert data["total"] == len(data["data"])
        assert data["total"] > 0

    def test_nodes_structure(self, client):
        """Каждый node должен иметь обязательные поля."""
        resp = client.get("/book/temporal/nodes")
        nodes = resp.json()["data"]
        if nodes:
            node = nodes[0]
            assert "id" in node
            assert "label" in node
            assert "precision" in node
            assert "era_id" in node


# ═══════════════════════════════════════════════════════════════
# Integration: Full temporal workflow
# ═══════════════════════════════════════════════════════════════


class TestTemporalWorkflow:
    def test_full_workflow(self, client, loaded_world_model):
        """Полный workflow: list → chain → node → context."""
        # 1. Список узлов
        nodes_resp = client.get("/book/temporal/nodes")
        assert nodes_resp.status_code == 200
        node_ids = [n["era_id"] for n in nodes_resp.json()["data"]]
        
        # 2. Цепочка
        chain_resp = client.get("/book/temporal/chain?direction=BACKWARD")
        assert chain_resp.status_code == 200
        
        # 3. Конкретный узел
        if node_ids:
            epoch_id = node_ids[0]
            node_resp = client.get(f"/book/temporal/node/{epoch_id}")
            assert node_resp.status_code == 200
            
            # 4. Контекст
            ctx_resp = client.get(f"/book/temporal/context/{epoch_id}")
            assert ctx_resp.status_code == 200
            ctx = ctx_resp.json()["data"]
            assert ctx["epoch"]["id"] == epoch_id
