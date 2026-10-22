"""Очистка диалога читателя: DELETE /book/reader/history/session и /history.

Проверяем:
  - удаляются только сообщения текущего читателя;
  - чужие диалоги и соседние сессии не затрагиваются;
  - ответ — ok-конверт с числом удалённых записей.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.main import app  # noqa: E402
import core.routes.reader as reader_routes  # noqa: E402
from memory.store import MemoryStore  # noqa: E402

client = TestClient(app)

USER_ID = "reader-clear-test"


def _override_auth(role: str = "reader"):
    async def _fake_user(request=None):
        return {
            "user_id": USER_ID,
            "role": role,
            "provider": "test",
            "username": "tester",
            "display_name": "Test User",
        }

    from auth.rbac import get_current_user

    app.dependency_overrides[get_current_user] = _fake_user
    return _fake_user


@pytest.fixture()
def store(tmp_path, monkeypatch):
    ms = MemoryStore(db_path=str(tmp_path / "clear.db"))
    monkeypatch.setattr(reader_routes, "_get_memory_store", lambda: ms)
    fake_user = _override_auth("reader")
    # Роут вызывает get_current_user(request) напрямую (не через Depends),
    # поэтому подменяем и импорт в модуле роутера.
    monkeypatch.setattr(reader_routes, "get_current_user", fake_user)
    return ms


@pytest.fixture(autouse=True)
def _restore_auth_overrides():
    """Не оставлять глобальную подмену пользователя после модуля."""
    saved = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.mark.asyncio
async def test_clear_session_endpoint_removes_own_messages_only(store):
    await store.store_exchange(session_id="s1", user_id=USER_ID, question="q1", answer="a1", metadata={})
    await store.store_exchange(session_id="s2", user_id=USER_ID, question="q2", answer="a2", metadata={})
    await store.store_exchange(session_id="s9", user_id="other-reader", question="q3", answer="a3", metadata={})

    r = client.delete("/book/reader/history/session", params={"session_id": "s1"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["deleted"] == 2
    assert body["data"]["session_id"] == "s1"

    assert await store.get_user_history_full(USER_ID, session_id="s1") == []
    assert len(await store.get_user_history_full(USER_ID, session_id="s2")) == 2
    assert len(await store.get_user_history_full("other-reader", session_id="s9")) == 2


@pytest.mark.asyncio
async def test_clear_history_endpoint_removes_all_sessions_of_reader(store):
    await store.store_exchange(session_id="s1", user_id=USER_ID, question="q1", answer="a1", metadata={})
    await store.store_exchange(session_id="s2", user_id=USER_ID, question="q2", answer="a2", metadata={})
    await store.store_exchange(session_id="s3", user_id="other-reader", question="q3", answer="a3", metadata={})

    r = client.delete("/book/reader/history")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["deleted"] == 4

    assert await store.get_user_history_full(USER_ID) == []
    assert len(await store.get_user_history_full("other-reader")) == 2


def test_clear_session_endpoint_on_unknown_session_returns_zero(store):
    r = client.delete("/book/reader/history/session", params={"session_id": "missing"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["data"]["deleted"] == 0
