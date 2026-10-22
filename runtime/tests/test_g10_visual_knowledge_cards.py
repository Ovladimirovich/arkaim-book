"""G10 — единый обзор 8 визуальных карточек (read-only).

Эндпоинт ``GET /studio/visual-knowledge/cards`` собирает все восемь библиотек
визуального слоя в один список для авторской ревизии: файл, классификация,
признак «требует авторского подтверждения», предполагаемое использование
и сами записи.

Проверяется:
  - отдаются ровно 8 карточек, в ожидаемом порядке;
  - каждая карточка помечена ``requires_author_review`` и ``ARTISTIC_MODEL``;
  - записи и промпт-превью не пустые;
  - слой не изменяется (read-only).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

_VISUAL_DIR = _PROJECT_ROOT / "core" / "CORE" / "visual" / "VISUAL_KNOWLEDGE"

EXPECTED_FILES: tuple[str, ...] = (
    "LOCATION_VISUALS.json",
    "CHARACTER_VISUALS.json",
    "ATMOSPHERES.json",
    "VISUAL_SYMBOLS.json",
    "CAMERA_LIBRARY.json",
    "STYLE_LIBRARY.json",
    "SHOT_LIBRARY.json",
    "VIDEO_RULES.json",
)


def _client() -> TestClient:
    from fastapi import FastAPI
    from auth import rbac
    from core.routes import studio as studio_routes

    app = FastAPI()
    app.include_router(studio_routes.router)

    async def current_user() -> dict:
        return {"id": "g10-tester", "role": "reader"}

    app.dependency_overrides[rbac.get_current_user] = current_user
    return TestClient(app)


def _layer_digest() -> dict[str, str]:
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(_VISUAL_DIR.glob("*.json"))}


@pytest.fixture(scope="module")
def payload() -> dict:
    response = _client().get("/studio/visual-knowledge/cards")
    assert response.status_code == 200
    return response.json()["data"]


class TestVisualKnowledgeCards:
    def test_returns_all_eight_libraries_in_order(self, payload):
        assert payload["total_files"] == 8
        assert [card["filename"] for card in payload["cards"]] == list(EXPECTED_FILES)

    def test_every_card_is_flagged_for_author_review(self, payload):
        assert payload["all_require_author_review"] is True
        for card in payload["cards"]:
            assert card["requires_author_review"] is True, card["filename"]
            assert card["is_canon"] is False, card["filename"]
            assert card["category"] == "ARTISTIC_MODEL", card["filename"]

    def test_every_card_declares_source_and_intended_use(self, payload):
        for card in payload["cards"]:
            assert card["source_path"], card["filename"]
            assert card["source_path"].endswith(card["filename"]), card["filename"]
            assert card["intended_use"], card["filename"]
            assert card["description"], card["filename"]

    def test_every_card_has_entries_with_prompt_preview(self, payload):
        for card in payload["cards"]:
            assert card["entry_count"] > 0, card["filename"]
            assert len(card["entries"]) == card["entry_count"], card["filename"]
            for entry in card["entries"]:
                assert entry["key"], card["filename"]
                assert isinstance(entry["fields"], dict)
                assert entry["fields"], card["filename"]
                assert entry["prompt_preview"], f"{card['filename']}:{entry['key']}"

    def test_total_entries_matches_sum_of_cards(self, payload):
        assert payload["total_entries"] == sum(card["entry_count"] for card in payload["cards"])

    def test_known_libraries_expose_expected_groups(self, payload):
        by_name = {card["filename"]: card for card in payload["cards"]}
        camera = by_name["CAMERA_LIBRARY.json"]
        groups = {entry["group"] for entry in camera["entries"]}
        assert {"shot_types", "movements", "transitions"} <= groups
        video = by_name["VIDEO_RULES.json"]
        assert "rhythm" in {entry["group"] for entry in video["entries"]}

    def test_flat_libraries_are_listed_as_entries(self, payload):
        """Плоские библиотеки (одна запись = один ключ) тоже попадают в обзор."""
        by_name = {card["filename"]: card for card in payload["cards"]}
        atmospheres = by_name["ATMOSPHERES.json"]
        keys = {entry["key"] for entry in atmospheres["entries"]}
        assert "sacred" in keys
        assert "neutral" in keys

    def test_layer_is_not_modified_by_the_endpoint(self):
        before = _layer_digest()
        assert before
        response = _client().get("/studio/visual-knowledge/cards")
        assert response.status_code == 200
        assert _layer_digest() == before

    def test_endpoint_is_read_only_envelope(self):
        response = _client().get("/studio/visual-knowledge/cards")
        body = response.json()
        assert body["ok"] is True
        assert "data" in body
