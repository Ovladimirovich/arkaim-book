import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
CORE = ROOT / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from narrative_engine import world_model as world_model_module
from narrative_engine.world_model import WorldModel


@pytest.fixture(autouse=True)
def reset_crosswalk_cache():
    world_model_module._crosswalk_cache = None
    yield
    world_model_module._crosswalk_cache = None


def test_real_data_contains_only_approved_links():
    model = WorldModel.load(use_cache=False)

    arkaim_node = model.get_temporal_node("arkaim_era")
    satya_node = model.get_temporal_node("satya_yuga")
    assert arkaim_node is not None
    assert satya_node is not None
    assert arkaim_node["entity_ids"] == ["region_arkaim"]
    assert satya_node["entity_ids"] == ["region_hyperborea"]

    for epoch in model.get_epochs():
        if epoch.id not in {"arkaim_era", "satya_yuga"}:
            node = model.get_temporal_node(epoch.id)
            assert node is not None
            assert node["entity_ids"] == []


def test_model_uses_only_supplied_approved_mapping(monkeypatch):
    monkeypatch.setattr(world_model_module, "_load_approved_crosswalk", lambda: {"аркаим": ["region_arkaim"]})

    model = WorldModel(
        {
            "epochs": [
                {"id": "arkaim_era", "name": "Arkaim", "name_ru": "Аркаим", "order": 1},
            ],
            "canonical_events": [
                {
                    "id": "event_arkaim_construction",
                    "title": "Construction",
                    "title_ru": "Строительство",
                    "epoch": "arkaim_era",
                    "location_id": "аркаим",
                },
            ],
        }
    )

    node = model.get_temporal_node("arkaim_era")
    assert node is not None
    assert node["entity_ids"] == ["region_arkaim"]


def test_empty_crosswalk_fails_closed(monkeypatch):
    monkeypatch.setattr(world_model_module, "_load_approved_crosswalk", lambda: {})
    model = WorldModel(
        {
            "epochs": [{"id": "arkaim_era", "name": "Arkaim", "name_ru": "Аркаим", "order": 1}],
            "canonical_events": [
                {
                    "id": "event_arkaim_construction",
                    "title": "Construction",
                    "title_ru": "Строительство",
                    "epoch": "arkaim_era",
                    "location_id": "аркаим",
                },
            ],
        }
    )

    node = model.get_temporal_node("arkaim_era")
    assert node is not None
    assert node["entity_ids"] == []


def test_crosswalk_v2_schema_required_fields():
    """Crosswalk v2: каждая APPROVED mapping имеет canonical_id, provenance, category, labels."""
    import json

    here = Path(__file__).resolve().parents[4]
    crosswalk_path = (
        here / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json"
    )
    data = json.loads(crosswalk_path.read_text(encoding="utf-8"))

    assert data.get("schema_version") == "2.0"
    assert data.get("owner_decision") == "language_agnostic_stable_ids"
    assert data.get("runtime_connected") is False
    assert data.get("unmapped", {}).get("status") == "PRESERVE_UNCHANGED"

    approved = [m for m in data.get("mappings", []) if m.get("status") == "APPROVED"]
    assert len(approved) == 2
    for m in approved:
        assert m.get("canonical_id"), "canonical_id обязателен"
        assert m.get("category"), "category обязателен"
        labels = m.get("labels") or {}
        assert labels.get("ru"), "labels.ru обязателен"
        assert labels.get("en"), "labels.en обязателен"
        prov = m.get("provenance") or {}
        assert prov.get("category"), "provenance.category обязателен"
        assert prov.get("source_level"), "provenance.source_level обязателен"


def test_load_approved_crosswalk_real_data():
    """Реальный crosswalk v2 загружается как русскоязычный ярлык → [canonical_id]."""
    mapping = world_model_module._load_approved_crosswalk()
    assert mapping == {
        "аркаим": ["region_arkaim"],
        "гиперборея": ["region_hyperborea"],
    }
