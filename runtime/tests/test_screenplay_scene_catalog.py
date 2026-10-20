"""Guard для read-only каталога сцен киносценария (Studio, пункты 1-2)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.screenplay_scene_catalog import (  # noqa: E402
    EXPECTED_SCENE_COUNT,
    SOURCE_MD_PATH,
    SYNOPSIS_DOCUMENT_PATH,
    SceneCatalogError,
    _validate_document,
    list_scenes,
)


def _source_text() -> str:
    return SOURCE_MD_PATH.read_text(encoding="utf-8")


def _source_sha256() -> str:
    return hashlib.sha256(SOURCE_MD_PATH.read_bytes()).hexdigest()


def _document() -> dict:
    return json.loads(SYNOPSIS_DOCUMENT_PATH.read_text(encoding="utf-8"))


def test_catalog_returns_119_canonical_scenes():
    scenes = list_scenes()

    assert len(scenes) == EXPECTED_SCENE_COUNT
    assert scenes[0]["scene_id"] == "scene_000"
    assert scenes[0]["order_global"] == 0
    assert scenes[0]["chapter"] == 0
    assert scenes[0]["title"] == "1. EXT. ГЛУБОКИЙ КОСМОС"
    assert scenes[0]["location"] == "ГЛУБОКИЙ КОСМОС"
    assert scenes[-1]["scene_id"] == "scene_118"
    assert scenes[-1]["order_global"] == 118

    assert [s["scene_id"] for s in scenes] == [f"scene_{i:03d}" for i in range(EXPECTED_SCENE_COUNT)]
    assert all(s["chapter"] == 0 for s in scenes)
    assert all(s["source"] == "screenplay" for s in scenes)
    assert not any(s["scene_id"].startswith(("conflict_", "meaning_auto_")) for s in scenes)
    assert "test_meeting" not in {s["scene_id"] for s in scenes}
    assert all(s["characters"] == [] for s in scenes)
    assert all(s["emotion"] == "" for s in scenes)
    assert all(s["meaning_tags"] == [] for s in scenes)


def test_guard_accepts_current_source_and_projection():
    scenes = _validate_document(_document(), _source_text(), _source_sha256())

    assert len(scenes) == EXPECTED_SCENE_COUNT
    assert scenes[0]["id"] == "scene_000"


def test_guard_rejects_source_hash_mismatch():
    with pytest.raises(SceneCatalogError, match="sha256"):
        _validate_document(_document(), _source_text(), "0" * 64)


def test_guard_rejects_scene_count_mismatch():
    document = _document()
    document["content"]["chapters"] = document["content"]["chapters"][:-1]

    with pytest.raises(SceneCatalogError, match="scene count"):
        _validate_document(document, _source_text(), _source_sha256())


def test_guard_rejects_scene_id_drift():
    document = _document()
    document["content"]["chapters"][0]["id"] = "scene_999"

    with pytest.raises(SceneCatalogError, match="scene id"):
        _validate_document(document, _source_text(), _source_sha256())


def test_guard_rejects_text_drift():
    document = _document()
    document["content"]["chapters"][0]["text"] = "подменённый текст"

    with pytest.raises(SceneCatalogError, match="does not match"):
        _validate_document(document, _source_text(), _source_sha256())


def test_guard_rejects_provenance_drift():
    document = _document()
    document["_provenance_metadata"]["category"] = "DERIVED"

    with pytest.raises(SceneCatalogError, match="provenance category"):
        _validate_document(document, _source_text(), _source_sha256())
