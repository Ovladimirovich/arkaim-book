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
