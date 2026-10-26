"""Q4 (OWNER-GO): dev-панели World Explorer доступны только editor/admin.

Эндпоинты dev-панелей ``/book/world-explorer/*``:
  - ``GET /cache/stats``
  - ``POST /cache/clear``
  - ``GET /sources/search``

после решения владельца (вариант B) требуют роли ``editor`` или ``admin``
(backend ``require_role("editor")``). Для ``reader`` — 403, без авторизации — 401.

Проверяется минимальным FastAPI-приложением с роутером narrative_engine
(паттерн из test_g10_visual_knowledge_cards.py): без полного core.main.app
и без обращения к внешним сетевым источникам (external_sources мокается).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

DEV_PANEL_ENDPOINTS = [
    ("GET", "/world-explorer/cache/stats", {}),
    ("POST", "/world-explorer/cache/clear", {}),
    ("GET", "/world-explorer/sources/search", {"query": "Аркаим"}),
]


def _client_for_role(role: str | None) -> TestClient:
    """Минимальное приложение с роутером narrative_engine и фиксированной ролью.

    role=None имитирует отсутствие сессии (get_current_user отдаёт 401).
    """
    from auth import rbac
    from narrative_engine.api_routes import router as world_explorer_router

    app = FastAPI()
    app.include_router(world_explorer_router)

    if role is None:

        async def anon_user() -> dict:
            raise HTTPException(status_code=401, detail="Не авторизован")

        app.dependency_overrides[rbac.get_current_user] = anon_user
    else:

        async def fixed_user() -> dict:
            return {"user_id": "q4-test", "role": role, "provider": "test"}

        app.dependency_overrides[rbac.get_current_user] = fixed_user

    return TestClient(app)


def _stub_external_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Убирает сетевые вызовы /sources/search: пустые списки результатов."""
    import narrative_engine.external_sources as ext

    async def fake_search_all_sources(query, limit_per_source=3, sources=None):
        return []

    def fake_search_local_knowledge(query, knowledge_dir=None, limit=5):
        return []

    monkeypatch.setattr(ext, "search_all_sources", fake_search_all_sources)
    monkeypatch.setattr(ext, "search_local_knowledge", fake_search_local_knowledge)


def _request(client: TestClient, method: str, path: str, params: dict, monkeypatch: pytest.MonkeyPatch) -> int:
    if path.endswith("/sources/search"):
        _stub_external_sources(monkeypatch)
    if method == "GET":
        return client.get(path, params=params).status_code
    return client.post(path, params=params).status_code


class TestDevPanelRbac:
    @pytest.mark.parametrize("method,path,params", DEV_PANEL_ENDPOINTS, ids=lambda v: v if isinstance(v, str) else "endpoint")
    def test_reader_denied_403(self, monkeypatch: pytest.MonkeyPatch, method: str, path: str, params: dict):
        client = _client_for_role("reader")
        assert _request(client, method, path, params, monkeypatch) == 403

    def test_anonymous_denied_401(self, monkeypatch: pytest.MonkeyPatch):
        client = _client_for_role(None)
        for method, path, params in DEV_PANEL_ENDPOINTS:
            assert _request(client, method, path, params, monkeypatch) == 401, path

    @pytest.mark.parametrize("role", ["editor", "admin"], ids=lambda r: r)
    def test_editor_and_admin_allowed(self, monkeypatch: pytest.MonkeyPatch, role: str):
        client = _client_for_role(role)
        for method, path, params in DEV_PANEL_ENDPOINTS:
            assert _request(client, method, path, params, monkeypatch) == 200, f"{role}: {path}"

    def test_user_facing_endpoints_remain_open(self, monkeypatch: pytest.MonkeyPatch):
        """Гейт задет только dev-панели: статистика и эпохи доступны reader."""
        client = _client_for_role("reader")
        assert client.get("/world-explorer/stats").status_code == 200
        assert client.get("/world-explorer/epochs").status_code == 200
