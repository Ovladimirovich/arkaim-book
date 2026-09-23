"""Интеграционные HTTP-тесты для Book Intelligence (/book/*)."""
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.main import app

client = TestClient(app)


def _override_auth(role: str = "reader"):
    async def _fake_user():
        return {
            "user_id": "test-user",
            "role": role,
            "provider": "test",
            "username": "tester",
            "display_name": "Test User",
        }
    from auth.rbac import get_current_user
    app.dependency_overrides[get_current_user] = _fake_user


class TestBookHealth:
    def test_book_health(self):
        r = client.get("/book/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_book_root(self):
        _override_auth("reader")
        r = client.get("/book")
        assert r.status_code == 200
        data = r.json()
        assert "endpoints" in data
        assert "/book/ask" in str(data["endpoints"])

    def test_book_genome(self):
        _override_auth("reader")
        r = client.get("/book/genome")
        assert r.status_code in (200, 404)

    def test_book_layers(self):
        _override_auth("reader")
        r = client.get("/book/layers")
        assert r.status_code == 200
        data = r.json()
        assert "knowledge_layer" in data
        assert "meaning_layer" in data
        assert "identity_layer" in data
        assert "mission_layer" in data

    def test_book_drafts_empty(self):
        _override_auth("reader")
        r = client.get("/book/drafts")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("data"), list)

    def test_book_drafts_pending_empty(self):
        _override_auth("reader")
        r = client.get("/book/drafts?status=pending")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("data"), list)

    def test_book_memory_stats(self):
        _override_auth("admin")
        r = client.get("/book/memory/stats")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "total_events" in data.get("data", {}) or "status" in data.get("data", {})

    def test_book_xray(self):
        r = client.get("/xray/version")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
