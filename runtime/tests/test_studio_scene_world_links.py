"""Read-only API связей сцен сценария с миром: контракт, статусы, честность."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from core.main import app  # noqa: E402

_ALLOWED_STATUSES = {"CONFIRMED", "DERIVED", "UNRESOLVED", "AMBIGUOUS"}
_PROJECT = Path(__file__).resolve().parent.parent.parent

_SOURCE_FILES = (
    _PROJECT / "core" / "KNOWLEDGE" / "SYNOPSIS_DOCUMENT.json",
    _PROJECT / "core" / "KNOWLEDGE" / "screenplay_links.json",
    _PROJECT / "core" / "KNOWLEDGE" / "claim_temporal_links.json",
    _PROJECT / "core" / "KNOWLEDGE" / "enriched_chunks.json",
    _PROJECT / "core" / "CORE" / "narrative_engine" / "data" / "WORLD_MODEL.json",
    _PROJECT / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json",
)


@pytest.fixture()
def client():
    return TestClient(app)


def _world_links(client: TestClient, scene_id: str) -> dict:
    resp = client.get(f"/studio/scenes/{scene_id}/world-links", params={"chapter": 0})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["scene_id"] == scene_id
    return data


def _of_type(links: list[dict], link_type: str, status: str | None = None) -> list[dict]:
    return [link for link in links if link["link_type"] == link_type and (status is None or link["status"] == status)]


def test_endpoint_returns_full_contract(client):
    data = _world_links(client, "scene_004")

    assert set(data) == {
        "scene_id",
        "chapter",
        "links",
        "summary",
        "missing",
        "provenance",
    }
    assert data["chapter"] == 0
    assert isinstance(data["links"], list) and data["links"]
    assert isinstance(data["summary"], dict)
    assert isinstance(data["missing"], dict)
    assert data["provenance"]["world_links"] in {"CONFIRMED", "DERIVED", "MIXED", "ABSENT"}

    for link in data["links"]:
        assert link["status"] in _ALLOWED_STATUSES
        assert link["link_type"]
        assert link["basis"]
        assert "provenance" in link
        assert "source_files" in link
        if link["status"] in {"UNRESOLVED", "AMBIGUOUS"}:
            assert link["target_id"] == ""


def test_summary_matches_links(client):
    data = _world_links(client, "scene_019")
    summary = data["summary"]

    assert summary["total"] == len(data["links"])
    assert summary["confirmed"] + summary["derived"] + summary["unresolved"] + summary["ambiguous"] == summary["total"]
    for status in _ALLOWED_STATUSES:
        assert summary[status.lower()] == len([link for link in data["links"] if link["status"] == status])


def test_confirmed_event_and_epoch_expose_provenance(client):
    data = _world_links(client, "scene_004")
    events = _of_type(data["links"], "event", "CONFIRMED")
    epochs = _of_type(data["links"], "epoch", "CONFIRMED")

    assert len(events) == 1
    event = events[0]
    assert event["target_id"] == "event_cosmic_impulse"
    assert event["epoch_id"] == "pre_arkaim"
    assert event["provenance"]["category"] == "AUTHOR_CANON"
    assert "core/KNOWLEDGE/claim_temporal_links.json" in event["source_files"]
    assert [step["step"] for step in event["chain"]][-1] == "world_event"

    assert len(epochs) == 1
    assert epochs[0]["target_id"] == "pre_arkaim"


def test_derived_links_are_not_presented_as_confirmed(client):
    data = _world_links(client, "scene_019")
    locations = _of_type(data["links"], "location")

    assert len(locations) == 1
    assert locations[0]["status"] == "DERIVED"
    assert locations[0]["target_id"] == "океания"
    assert "алиас" in locations[0]["basis"]
    assert not _of_type(data["links"], "location", "CONFIRMED")

    relations = _of_type(data["links"], "character_relation")
    assert not relations, "в сцене без персонажей не может быть связей персонажей"


def test_place_mention_forms_are_exposed_via_api(client):
    """Утверждённая форма упоминания места видна в ответе Studio."""
    data = _world_links(client, "scene_050")

    mentions = [link for link in data["links"] if link["link_type"] == "location_mention"]
    assert len(mentions) == 1
    assert mentions[0]["target_id"] == "океания"
    assert mentions[0]["status"] == "DERIVED"
    assert mentions[0].get("mention_only") is True

    locations = [link for link in data["links"] if link["link_type"] == "location"]
    assert locations[0]["status"] == "UNRESOLVED"


def test_oceania_scene_exposes_location_and_mention_separately(client):
    data = _world_links(client, "scene_021")

    locations = [link for link in data["links"] if link["link_type"] == "location"]
    mentions = [link for link in data["links"] if link["link_type"] == "location_mention"]

    assert len(locations) == 1
    assert locations[0]["status"] == "DERIVED"
    assert locations[0]["target_id"] == "океания"

    assert len(mentions) == 1
    assert mentions[0]["status"] == "DERIVED"
    assert mentions[0].get("mention_only") is True


def test_unresolved_location_is_missing_data_with_reason(client):
    data = _world_links(client, "scene_013")
    locations = _of_type(data["links"], "location")

    assert len(locations) == 1
    assert locations[0]["status"] == "UNRESOLVED"
    assert locations[0]["target_id"] == ""
    assert "World Model" in locations[0]["basis"]
    assert data["missing"]["location"]
    assert data["provenance"]["world_links"] == "ABSENT"


def test_location_mention_is_not_a_location(client):
    data = _world_links(client, "scene_118")
    mentions = _of_type(data["links"], "location_mention")

    assert len(mentions) == 1
    mention = mentions[0]
    assert mention["status"] == "DERIVED"
    assert mention.get("mention_only") is True
    assert "Аркаим" in mention["basis"]
    assert not _of_type(data["links"], "location", "CONFIRMED")


def test_character_links_carry_world_provenance(client):
    data = _world_links(client, "scene_050")
    characters = _of_type(data["links"], "character", "CONFIRMED")

    assert [link["target_id"] for link in characters] == ["Славный", "Велик", "Световит"]
    assert characters[0]["epochs"] == ["satya_yuga"]

    relations = _of_type(data["links"], "character_relation")
    assert len(relations) == 1
    assert relations[0]["status"] == "DERIVED"
    assert relations[0]["character"] == "Световит"
    assert relations[0]["target"] == "Велик"


def test_unknown_scene_returns_404(client):
    resp = client.get("/studio/scenes/scene_999/world-links")
    assert resp.status_code == 404


def test_endpoint_requires_auth():
    from auth.rbac import get_current_user

    override = app.dependency_overrides.pop(get_current_user, None)
    try:
        client = TestClient(app)
        resp = client.get("/studio/scenes/scene_000/world-links")
        assert resp.status_code == 401
    finally:
        if override is not None:
            app.dependency_overrides[get_current_user] = override


def test_sources_are_not_modified_by_endpoint(client):
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in _SOURCE_FILES}
    _world_links(client, "scene_004")
    _world_links(client, "scene_013")
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in _SOURCE_FILES}
    assert before == after
