"""Temporal API Alignment tests (B1 + C1, ADR_TEMPORAL_WORLD_MODEL).

B1: /book/temporal/nodes отражает canonical M8.1 — temporal_today присутствует.
C1: /book/temporal/chain — canonical provenance arkaim-якоря (как M8.1 engine).
Invariants: today без relations; Present→Arkaim не создаётся; C2 не реализован
(PRECEDES-рёбра без provenance); 12 узлов / 11 PRECEDES-связей неизменны.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def loaded_world_model():
    from narrative_engine.world_model import WorldModel

    return WorldModel.load()


# ═══════════════════════════════════════════════════════════════
# B1: GET /book/temporal/nodes
# ═══════════════════════════════════════════════════════════════


class TestB1TemporalTodayInNodes:
    def test_nodes_contains_temporal_today(self, client, loaded_world_model):
        """B1: temporal_today присутствует в выдаче /nodes (canonical M8.1)."""
        resp = client.get("/book/temporal/nodes")
        assert resp.status_code == 200
        data = resp.json()
        ids = [n["id"] for n in data["data"]]
        assert "temporal_today" in ids

    def test_nodes_total_consistent(self, client, loaded_world_model):
        """total == len(data); today добавлен ровно один раз."""
        resp = client.get("/book/temporal/nodes")
        data = resp.json()
        assert data["total"] == len(data["data"])
        ids = [n["id"] for n in data["data"]]
        assert ids.count("temporal_today") == 1

    def test_today_is_last_canonical_order(self, client, loaded_world_model):
        """Порядок canonical engine: эпохи, затем today."""
        resp = client.get("/book/temporal/nodes")
        ids = [n["id"] for n in resp.json()["data"]]
        assert ids[-1] == "temporal_today"

    def test_today_semantics(self, client, loaded_world_model):
        """Today = методологический anchor: HYPOTHESIS, EXACT, is_anchor=False, era_id=""." """
        resp = client.get("/book/temporal/nodes")
        today = next(n for n in resp.json()["data"] if n["id"] == "temporal_today")
        cats = [p["category"] for p in today["provenance"]]
        assert cats == ["HYPOTHESIS"]
        assert today["precision"] == "EXACT"
        assert today["is_anchor"] is False
        assert today["era_id"] == ""
        assert today["bounds"]["start"] == "2025 CE"

    def test_no_second_arkaim_anchor_node(self, client, loaded_world_model):
        """D-принцип ADR: в /nodes нет дубля temporal_arkaim_anchor."""
        resp = client.get("/book/temporal/nodes")
        ids = [n["id"] for n in resp.json()["data"]]
        assert "temporal_arkaim_anchor" not in ids


# ═══════════════════════════════════════════════════════════════
# C1: GET /book/temporal/chain — canonical provenance якоря
# ═══════════════════════════════════════════════════════════════


class TestC1CanonicalAnchorProvenance:
    @pytest.mark.parametrize("direction", ["FORWARD", "BACKWARD"])
    def test_arkaim_era_provenance_enriched(self, client, loaded_world_model, direction):
        """C1: у temporal_arkaim_era provenance из ArkaimAnchor (AUTHOR_CANON + EXTERNAL_SOURCE)."""
        resp = client.get(f"/book/temporal/chain?direction={direction}")
        assert resp.status_code == 200
        chain = resp.json()["data"]
        anchor = next(n for n in chain["nodes"] if n["id"] == "temporal_arkaim_era")
        cats = {p["category"] for p in anchor["provenance"]}
        assert "AUTHOR_CANON" in cats
        assert "EXTERNAL_SOURCE" in cats

    @pytest.mark.parametrize("direction", ["FORWARD", "BACKWARD"])
    def test_arkaim_era_confidence_canonical(self, client, loaded_world_model, direction):
        """C1: confidence якоря = 0.85 (как reconstruction_engine.py:595)."""
        resp = client.get(f"/book/temporal/chain?direction={direction}")
        anchor = next(n for n in resp.json()["data"]["nodes"] if n["id"] == "temporal_arkaim_era")
        assert anchor["confidence"] == 0.85

    def test_provenance_sources_canonical(self, client, loaded_world_model):
        """C1: теги provenance — те же источники, что ArkaimAnchor.from_existing_data()."""
        resp = client.get("/book/temporal/chain?direction=FORWARD")
        anchor = next(n for n in resp.json()["data"]["nodes"] if n["id"] == "temporal_arkaim_era")
        by_cat = {p["category"]: p for p in anchor["provenance"]}
        assert by_cat["AUTHOR_CANON"]["source_title"] == "КНИГА.md"
        assert by_cat["EXTERNAL_SOURCE"]["source_title"] == "ARCHAEOLOGY.json"

    def test_other_nodes_not_changed(self, client, loaded_world_model):
        """C1: enrichment не затрагивает остальные узлы (provenance/confidence прежние).

        Проверяем, что enrichment (_enrich_canonical_anchor) меняет ТОЛЬКО якорный узел
        temporal_arkaim_era. Остальные узлы должны сохранить provenance/confidence
        из WorldModel (для CANON эпох — AUTHOR_CANON, для SYSTEM_INTERPRETATION — пусто).
        """
        resp = client.get("/book/temporal/chain?direction=FORWARD")
        chain = resp.json()["data"]
        anchor = next(n for n in chain["nodes"] if n["id"] == "temporal_arkaim_era")
        others = [n for n in chain["nodes"] if n["id"] != "temporal_arkaim_era"]

        # Якорный узел обогащён: AUTHOR_CANON + EXTERNAL_SOURCE, confidence=0.85
        anchor_cats = {p["category"] for p in anchor["provenance"]}
        assert "AUTHOR_CANON" in anchor_cats
        assert "EXTERNAL_SOURCE" in anchor_cats
        assert anchor["confidence"] == 0.85

        # Остальные узлы: provenance соответствует WorldModel (CANON -> AUTHOR_CANON, SYSTEM_INTERPRETATION -> [])
        # confidence = 0.8 (baseline)
        for node in others:
            assert node["confidence"] == 0.8
            # Проверяем консистентность с WorldModel: если эпоха CANON -> есть AUTHOR_CANON
            # Если SYSTEM_INTERPRETATION -> пусто
            epoch_id = node["id"].replace("temporal_", "")
            epoch = next((e for e in loaded_world_model.get_epochs() if e.id == epoch_id), None)
            if epoch and epoch.source_level == "CANON":
                node_cats = {p["category"] for p in node["provenance"]}
                assert "AUTHOR_CANON" in node_cats, f"CANON epoch {epoch_id} should have AUTHOR_CANON provenance"
            elif epoch and epoch.source_level == "SYSTEM_INTERPRETATION":
                assert node["provenance"] == [], f"SYSTEM_INTERPRETATION epoch {epoch_id} should have empty provenance"

    def test_anchor_is_anchor_flag(self, client, loaded_world_model):
        """Флаг is_anchor на месте (не сломан enrichment-обходом)."""
        resp = client.get("/book/temporal/chain?direction=FORWARD")
        anchor = next(n for n in resp.json()["data"]["nodes"] if n["id"] == "temporal_arkaim_era")
        assert anchor["is_anchor"] is True


# ═══════════════════════════════════════════════════════════════
# Invariants (ADR §5)
# ═══════════════════════════════════════════════════════════════


class TestAlignmentInvariants:
    @pytest.mark.parametrize("direction", ["FORWARD", "BACKWARD"])
    def test_chain_does_not_contain_today(self, client, loaded_world_model, direction):
        """Сегодня в исторической цепочке НЕ участвует (узел без relations)."""
        resp = client.get(f"/book/temporal/chain?direction={direction}")
        chain = resp.json()["data"]
        ids = [n["id"] for n in chain["nodes"]]
        assert "temporal_today" not in ids

    @pytest.mark.parametrize("direction", ["FORWARD", "BACKWARD"])
    def test_no_present_to_arkaim_relation(self, client, loaded_world_model, direction):
        """КРИТИЧНО: relation с участием temporal_today не создаётся ни в какую сторону."""
        resp = client.get(f"/book/temporal/chain?direction={direction}")
        for rel in resp.json()["data"]["relations"]:
            assert rel["source_id"] != "temporal_today"
            assert rel["target_id"] != "temporal_today"

    @pytest.mark.parametrize("direction", ["FORWARD", "BACKWARD"])
    def test_chain_shape_unchanged(self, client, loaded_world_model, direction):
        """12 узлов, 7 хронологических групп, 6 PRECEDES и 5 разрывов.

        Историческая ось состоит из 12 эпох, объединённых в 7 параллельных
        групп (order: 0,1,1,2,2,3,3,4,4,5,5,6 — эпохи йог идут параллельно
        эпохам Аркаима). PRECEDES-ребро ставится только между РАЗНЫМИ
        группами, поэтому 11 соседних пар дают 6 рёбер и 5 разрывов.
        Разрыв — не потеря данных: это честная отметка «между этими эпохами
        нет явной временной связи» (см. epoch_parallels в WORLD_MODEL.json).
        """
        body = client.get(f"/book/temporal/chain?direction={direction}").json()
        chain = body["data"]
        assert len(chain["nodes"]) == 12
        assert len(chain["relations"]) == 6
        assert len(chain["gaps"]) == 5
        assert all(r["relation_type"] == "PRECEDES" for r in chain["relations"])
        assert body["stats"]["nodes"] == 12
        assert body["stats"]["relations"] == 6
        assert body["stats"]["gaps"] == 5
        # Каждая соседняя пара без ребра помечена разрывом: 11 пар = 6 + 5
        assert len(chain["relations"]) + len(chain["gaps"]) == len(chain["nodes"]) - 1

    def test_c2_precedes_edges_have_derived_provenance(self, client, loaded_world_model):
        """C2: PRECEDES-рёбра оси несут DERIVED provenance (ADR TEMPORAL §4).

        Порядок эпох — интерпретация канона, не прямое утверждение текста.
        Поэтому provenance = DERIVED @ SYSTEM_INTERPRETATION, NEVER AUTHOR_CANON.
        """
        resp = client.get("/book/temporal/chain?direction=FORWARD")
        for rel in resp.json()["data"]["relations"]:
            assert len(rel["provenance"]) == 1
            tag = rel["provenance"][0]
            assert tag["category"] == "DERIVED"
            assert tag["notes"] == "temporal precedence — derived from epoch ordering in canon"
            assert tag["source_level"] == "SYSTEM_INTERPRETATION"
