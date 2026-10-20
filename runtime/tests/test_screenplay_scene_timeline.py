"""Временная линия сцен сценария: только подтверждённые эпохи, без догадок."""

from __future__ import annotations

import hashlib
import sys
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from core.main import app  # noqa: E402
from knowledge.screenplay_scene_catalog import list_scenes  # noqa: E402
from knowledge.screenplay_scene_timeline import build_scene_timeline  # noqa: E402

_SOURCE_FILES = (
    _CORE.parent / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md",
    _CORE.parent / "KNOWLEDGE" / "SYNOPSIS_DOCUMENT.json",
    _CORE.parent / "KNOWLEDGE" / "screenplay_links.json",
    _CORE.parent / "KNOWLEDGE" / "claim_temporal_links.json",
    _CORE / "narrative_engine" / "data" / "WORLD_MODEL.json",
)


@lru_cache(maxsize=1)
def _timeline() -> dict:
    return build_scene_timeline()


@pytest.fixture()
def client():
    return TestClient(app)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_timeline_keeps_canonical_scene_order():
    timeline = _timeline()
    scene_ids = [entry["scene_id"] for entry in timeline["scenes"]]

    assert len(scene_ids) == 119
    assert scene_ids == [f"scene_{index:03d}" for index in range(119)]
    assert [entry["order_global"] for entry in timeline["scenes"]] == list(range(119))


def test_epoch_is_set_only_for_confirmed_event_chains():
    timeline = _timeline()
    catalog = {scene["scene_id"]: scene for scene in list_scenes()}

    for entry in timeline["scenes"]:
        scene = catalog[entry["scene_id"]]
        confirmed = [link for link in scene["world_links"] if link["link_type"] == "event" and link["status"] == "CONFIRMED"]
        if confirmed:
            assert entry["epoch_id"], f"{entry['scene_id']}: подтверждённое событие без эпохи"
            assert entry["epoch_status"] == "CONFIRMED"
            assert entry["temporal_node_id"] == f"temporal_{entry['epoch_id']}"
            assert entry["event_ids"]
        else:
            assert entry["epoch_id"] == ""
            assert entry["epoch_status"] == "UNRESOLVED"
            assert entry["reason"], f"{entry['scene_id']}: нет причины отсутствия эпохи"
            assert entry["event_ids"] == []


def test_epochs_exist_in_world_model():
    from narrative_engine.world_model import WorldModel

    world = WorldModel.load()
    known = {epoch.id for epoch in world.get_epochs()}

    for block in _timeline()["epochs"]:
        assert block["epoch_id"] in known
        assert block["epoch_name_ru"]
        assert block["temporal_node_id"] == f"temporal_{block['epoch_id']}"


def test_summary_matches_scenes():
    timeline = _timeline()
    summary = timeline["summary"]

    assert summary["scene_count"] == len(timeline["scenes"])
    assert summary["scenes_with_epoch"] == sum(1 for e in timeline["scenes"] if e["epoch_id"])
    assert summary["scenes_without_epoch"] == summary["scene_count"] - summary["scenes_with_epoch"]
    assert summary["epoch_count"] == len(timeline["epochs"])
    assert 0 < summary["coverage"] <= 1


def test_epoch_blocks_cover_exactly_scenes_with_epoch():
    timeline = _timeline()
    from_epochs = {scene_id for block in timeline["epochs"] for scene_id in block["scene_ids"]}
    with_epoch = {entry["scene_id"] for entry in timeline["scenes"] if entry["epoch_id"]}

    assert from_epochs == with_epoch
    for block in timeline["epochs"]:
        assert block["scene_count"] == len(block["scene_ids"])


def test_timeline_api_returns_contract(client):
    resp = client.get("/studio/timeline")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert set(data) == {"scenes", "epochs", "summary", "basis", "limitations"}
    assert len(data["scenes"]) == 119
    assert data["summary"]["scenes_with_epoch"] > 0
    assert data["limitations"]


def test_timeline_api_requires_auth():
    from auth.rbac import get_current_user

    override = app.dependency_overrides.pop(get_current_user, None)
    try:
        client = TestClient(app)
        resp = client.get("/studio/timeline")
        assert resp.status_code == 401
    finally:
        if override is not None:
            app.dependency_overrides[get_current_user] = override


def test_timeline_does_not_modify_sources():
    before = {path: _hash(path) for path in _SOURCE_FILES}
    build_scene_timeline()
    after = {path: _hash(path) for path in _SOURCE_FILES}
    assert before == after
