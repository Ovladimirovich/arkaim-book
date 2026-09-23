"""Тесты для core.repositories — UserRepository, SessionRepository, ApiKeyRepository."""
import hashlib
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from core.repositories.user_repo import UserRepository
from core.repositories.session_repo import SessionRepository
from core.repositories.api_key_repo import ApiKeyRepository


@pytest.fixture(scope="module", autouse=True)
def _setup_env():
    import os
    os.environ.setdefault("SESSION_SECRET", "test-repo-secret-12345")
    os.environ.setdefault("AUTH_DB_PATH", ":memory:")


@pytest_asyncio.fixture
async def user_repo():
    repo = UserRepository()
    repo._conn = None  # Reset connection
    # Use in-memory DB
    import aiosqlite
    repo._conn = await aiosqlite.connect(":memory:")
    repo._conn.row_factory = aiosqlite.Row
    await repo._conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_user_id TEXT NOT NULL,
            username TEXT, display_name TEXT, role TEXT NOT NULL DEFAULT 'reader',
            is_active BOOLEAN NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_uid ON users(provider, provider_user_id);
    """)
    yield repo
    await repo._conn.close()


@pytest_asyncio.fixture
async def session_repo(user_repo):
    repo = SessionRepository(user_repo)
    # Create sessions table on same connection
    await user_repo._conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL
        );
    """)
    repo._conn = user_repo._conn
    yield repo


@pytest_asyncio.fixture
async def api_key_repo(user_repo):
    repo = ApiKeyRepository(user_repo)
    await user_repo._conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, key_prefix TEXT NOT NULL,
            key_hash TEXT NOT NULL, name TEXT, last_used_at TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
    """)
    repo._conn = user_repo._conn
    yield repo


# ── UserRepository Tests ──────────────────────────────

class TestUserRepository:
    @pytest.mark.asyncio
    async def test_upsert_creates_new_user(self, user_repo: UserRepository):
        user = await user_repo.upsert("telegram", "12345", username="alice")
        assert user is not None
        assert user["provider"] == "telegram"
        assert user["provider_user_id"] == "12345"
        assert user["username"] == "alice"
        assert user["role"] == "reader"
        assert user["is_active"] == 1

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_user(self, user_repo: UserRepository):
        u1 = await user_repo.upsert("telegram", "111", username="bob")
        u2 = await user_repo.upsert("telegram", "111", username="bob_updated", role="editor")
        assert u1["id"] == u2["id"]
        assert u2["username"] == "bob_updated"
        assert u2["role"] == "editor"

    @pytest.mark.asyncio
    async def test_get_by_provider(self, user_repo: UserRepository):
        await user_repo.upsert("google", "g-001", username="carol")
        found = await user_repo.get_by_provider("google", "g-001")
        assert found is not None
        assert found["username"] == "carol"

    @pytest.mark.asyncio
    async def test_get_by_provider_not_found(self, user_repo: UserRepository):
        found = await user_repo.get_by_provider("telegram", "nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repo: UserRepository):
        created = await user_repo.upsert("telegram", "222", username="dave")
        found = await user_repo.get_by_id(created["id"])
        assert found is not None
        assert found["username"] == "dave"

    @pytest.mark.asyncio
    async def test_list_all(self, user_repo: UserRepository):
        await user_repo.upsert("telegram", "l1")
        await user_repo.upsert("telegram", "l2")
        users = await user_repo.list_all()
        assert len(users) >= 2

    @pytest.mark.asyncio
    async def test_count_by_role(self, user_repo: UserRepository):
        await user_repo.upsert("telegram", "r1", role="reader")
        await user_repo.upsert("telegram", "r2", role="admin")
        counts = await user_repo.count_by_role()
        assert "reader" in counts
        assert "admin" in counts

    @pytest.mark.asyncio
    async def test_set_role(self, user_repo: UserRepository):
        user = await user_repo.upsert("telegram", "s1")
        ok = await user_repo.set_role(user["id"], "admin")
        assert ok is True
        updated = await user_repo.get_by_id(user["id"])
        assert updated["role"] == "admin"

    @pytest.mark.asyncio
    async def test_set_active(self, user_repo: UserRepository):
        user = await user_repo.upsert("telegram", "a1")
        await user_repo.set_active(user["id"], False)
        updated = await user_repo.get_by_id(user["id"])
        assert updated["is_active"] == 0


# ── SessionRepository Tests ───────────────────────────

class TestSessionRepository:
    @pytest.mark.asyncio
    async def test_save_and_get(self, session_repo: SessionRepository):
        expires = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        await session_repo.save("sess-001", "user-001", "hash123", expires)
        session = await session_repo.get("sess-001")
        assert session is not None
        assert session["user_id"] == "user-001"
        assert session["token_hash"] == "hash123"

    @pytest.mark.asyncio
    async def test_delete(self, session_repo: SessionRepository):
        expires = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        await session_repo.save("sess-del", "user-del", "hash", expires)
        ok = await session_repo.delete("sess-del")
        assert ok is True
        assert await session_repo.get("sess-del") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, session_repo: SessionRepository):
        ok = await session_repo.delete("nonexistent")
        assert ok is False


# ── ApiKeyRepository Tests ────────────────────────────

class TestApiKeyRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(self, api_key_repo: ApiKeyRepository):
        key_id = await api_key_repo.create("user-ak", "prefix123", "hash_abc", name="test-key")
        assert key_id is not None
        found = await api_key_repo.get_by_hash("hash_abc")
        assert found is not None
        assert found["user_id"] == "user-ak"
        assert found["name"] == "test-key"

    @pytest.mark.asyncio
    async def test_list_by_user(self, api_key_repo: ApiKeyRepository):
        await api_key_repo.create("user-list", "p1", "h1")
        await api_key_repo.create("user-list", "p2", "h2")
        keys = await api_key_repo.list_by_user("user-list")
        assert len(keys) >= 2

    @pytest.mark.asyncio
    async def test_revoke(self, api_key_repo: ApiKeyRepository):
        key_id = await api_key_repo.create("user-rev", "rev", "rev_hash")
        ok = await api_key_repo.revoke(key_id)
        assert ok is True
        found = await api_key_repo.get_by_hash("rev_hash")
        assert found["is_active"] == 0

    @pytest.mark.asyncio
    async def test_touch(self, api_key_repo: ApiKeyRepository):
        key_id = await api_key_repo.create("user-touch", "tch", "tch_hash")
        await api_key_repo.touch(key_id)
        found = await api_key_repo.get_by_hash("tch_hash")
        assert found["last_used_at"] is not None
