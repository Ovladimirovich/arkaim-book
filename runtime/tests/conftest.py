"""Auto-override auth dependency for all tests using core.main.app."""

import pytest
from core.main import app
from auth.rbac import get_current_user
from core.database import close_db_manager


async def _fake_user():
    return {
        "user_id": "test-user",
        "role": "admin",
        "provider": "test",
        "username": "tester",
        "display_name": "Test User",
    }


app.dependency_overrides[get_current_user] = _fake_user


@pytest.fixture(scope="session", autouse=True)
async def _close_db_manager_at_session_end():
    """Закрыть все соединения aiosqlite после завершения тестовой сессии.

    aiosqlite создаёт не-daemon поток _connection_worker_thread на каждое
    соединение. Если соединения не закрыты, процесс pytest не завершается.
    """
    yield
    await close_db_manager()
