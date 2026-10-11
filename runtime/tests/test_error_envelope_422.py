"""H2-A GO-2 — единый формат ошибок: 422 валидации в envelope (2026-10-11).

Ранее 401/404/500 отдавали ``{"ok": false, "error": {code, message}}``, а 422 —
голый FastAPI ``{"detail": [...]}``. GO-2 приводит 422 к тому же envelope;
статусы и список ошибок валидации сохраняются.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core" / "CORE"
for import_root in (ROOT, CORE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from fastapi.testclient import TestClient

from auth.rbac import get_current_user
from core.main import app


def _client() -> TestClient:
    return TestClient(app)


def _assert_envelope_422(body: dict) -> None:
    assert body["ok"] is False
    assert body["error"]["code"] == "HTTP_422"
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    details = body["error"]["details"]
    assert isinstance(details, list) and details
    for item in details:
        assert isinstance(item["loc"], list) and item["loc"]
        assert isinstance(item["msg"], str) and item["msg"]
        assert isinstance(item["type"], str) and item["type"]


def test_search_without_q_returns_envelope_422():
    response = _client().get("/knowledge/cards/search")
    assert response.status_code == 422
    _assert_envelope_422(response.json())


def test_search_empty_q_returns_envelope_422():
    response = _client().get("/knowledge/cards/search", params={"q": ""})
    assert response.status_code == 422
    body = response.json()
    _assert_envelope_422(body)
    assert any(item["type"] == "string_too_short" for item in body["error"]["details"])


def test_search_limit_out_of_range_returns_envelope_422():
    response = _client().get("/knowledge/cards/search", params={"q": "аркаим", "limit": 0})
    assert response.status_code == 422
    _assert_envelope_422(response.json())


def test_ask_invalid_body_returns_envelope_422():
    response = _client().post(
        "/book/ask",
        content=b"invalid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    _assert_envelope_422(response.json())


def test_unknown_card_still_returns_envelope_404():
    response = _client().get("/knowledge/cards/__definitely_missing_entity__")
    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "HTTP_404"


def test_unauthenticated_request_still_returns_envelope_401():
    override = app.dependency_overrides.pop(get_current_user, None)
    try:
        response = _client().get("/knowledge/cards/search", params={"q": "аркаим"})
        assert response.status_code == 401
        body = response.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "HTTP_401"
    finally:
        if override is not None:
            app.dependency_overrides[get_current_user] = override
