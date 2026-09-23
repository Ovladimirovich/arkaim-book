"""Тесты для core.services.auth_service — бизнес-логика аутентификации."""
import hashlib
import os
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Устанавливаем окружение ДО импорта модулей
os.environ.setdefault("SESSION_SECRET", "test-auth-svc-secret-12345")
os.environ.setdefault("AUTH_DB_PATH", ":memory:")
os.environ.setdefault("HERMES_API_KEY", "test-hermes-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-bot-token")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")

from auth.tokens import create_access_token, decode_access_token
from auth.api_keys import generate_api_key


# ── Фикстуры ──────────────────────────────────────────

@pytest_asyncio.fixture
async def in_memory_repos():
    """Создаёт in-memory UserRepository и ApiKeyRepository."""
    import aiosqlite
    from core.repositories.user_repo import UserRepository
    from core.repositories.api_key_repo import ApiKeyRepository

    user_repo = UserRepository()
    user_repo._conn = await aiosqlite.connect(":memory:")
    user_repo._conn.row_factory = aiosqlite.Row
    await user_repo._conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, provider TEXT NOT NULL, provider_user_id TEXT NOT NULL,
            username TEXT, display_name TEXT, role TEXT NOT NULL DEFAULT 'reader',
            is_active BOOLEAN NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_uid ON users(provider, provider_user_id);
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, key_prefix TEXT NOT NULL,
            key_hash TEXT NOT NULL, name TEXT, last_used_at TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
    """)
    api_key_repo = ApiKeyRepository(user_repo)
    api_key_repo._conn = user_repo._conn

    yield user_repo, api_key_repo

    await user_repo._conn.close()


@pytest_asyncio.fixture
async def auth_service(in_memory_repos):
    """AuthService с in-memory репозиториями."""
    from core.services.auth_service import AuthService
    user_repo, api_key_repo = in_memory_repos
    service = AuthService.__new__(AuthService)
    service.user_repo = user_repo
    service.api_key_repo = api_key_repo
    return service


def _make_telegram_data(user_id: str = "12345", username: str = "testuser") -> dict:
    """Создать валидные данные Telegram с HMAC-подписью."""
    import hmac
    import hashlib
    import time
    from core.config import settings

    data = {
        "id": user_id,
        "username": username,
        "first_name": "Test",
        "last_name": "User",
        "auth_date": str(int(time.time())),
    }
    bot_token = settings.TELEGRAM_BOT_TOKEN or "test-telegram-bot-token"
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return data


# ── Telegram Login Tests ──────────────────────────────

class TestAuthServiceTelegram:
    @pytest.mark.asyncio
    async def test_login_telegram_creates_user(self, auth_service):
        data = _make_telegram_data("tg_001", "alice")
        result = await auth_service.login_telegram(data)
        assert "user" in result
        assert "token" in result
        assert result["user"]["provider"] == "telegram"
        assert result["user"]["provider_user_id"] == "tg_001"
        assert result["user"]["username"] == "alice"

    @pytest.mark.asyncio
    async def test_login_telegram_returns_valid_token(self, auth_service):
        data = _make_telegram_data("tg_002", "bob")
        result = await auth_service.login_telegram(data)
        payload = decode_access_token(result["token"])
        assert payload is not None
        assert payload.sub == result["user"]["id"]
        assert payload.role == "reader"

    @pytest.mark.asyncio
    async def test_login_telegram_upserts_existing_user(self, auth_service):
        data = _make_telegram_data("tg_003", "carol")
        r1 = await auth_service.login_telegram(data)
        r2 = await auth_service.login_telegram(data)
        assert r1["user"]["id"] == r2["user"]["id"]

    @pytest.mark.asyncio
    async def test_login_telegram_invalid_hash(self, auth_service):
        data = _make_telegram_data("tg_004")
        data["hash"] = "invalid_hash"
        with pytest.raises(Exception):
            await auth_service.login_telegram(data)


# ── API Key Tests ─────────────────────────────────────

class TestAuthServiceApiKeys:
    @pytest.mark.asyncio
    async def test_create_api_key(self, auth_service, in_memory_repos):
        user_repo, _ = in_memory_repos
        user = await user_repo.upsert("telegram", "ak_001", username="keyuser")
        result = await auth_service.create_api_key(user["id"], name="my-key")
        assert "key_id" in result
        assert "key" in result
        assert "key_masked" in result
        assert result["key"]  # raw key не пустой
        assert "..." in result["key_masked"]  # замаскирован

    @pytest.mark.asyncio
    async def test_list_api_keys(self, auth_service, in_memory_repos):
        user_repo, _ = in_memory_repos
        user = await user_repo.upsert("telegram", "ak_002")
        await auth_service.create_api_key(user["id"], name="key1")
        await auth_service.create_api_key(user["id"], name="key2")
        keys = await auth_service.list_api_keys(user["id"])
        assert len(keys) == 2
        # key_hash не должен возвращаться
        for key in keys:
            assert "key_hash" not in key

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, auth_service, in_memory_repos):
        user_repo, _ = in_memory_repos
        user = await user_repo.upsert("telegram", "ak_003")
        keys = await auth_service.list_api_keys(user["id"])
        assert keys == []


# ── Service Key Tests ─────────────────────────────────

class TestAuthServiceServiceKey:
    @pytest.mark.asyncio
    async def test_authenticate_service_key_valid(self, auth_service, in_memory_repos):
        user_repo, api_key_repo = in_memory_repos
        # Создаём пользователя и привязываем сервисный ключ
        user = await user_repo.upsert("telegram", "sk_001", username="svc_user")
        key_hash = hashlib.sha256(b"test-hermes-key").hexdigest()
        await api_key_repo.create(user["id"], "svc", key_hash, name="service")

        result = await auth_service.authenticate_service_key("test-hermes-key")
        assert result is not None
        assert result["id"] == user["id"]

    @pytest.mark.asyncio
    async def test_authenticate_service_key_wrong_key(self, auth_service):
        result = await auth_service.authenticate_service_key("wrong-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_service_key_no_attached_user(self, auth_service):
        """Сервисный ключ без привязанного пользователя."""
        # Ключ не существует в api_keys
        result = await auth_service.authenticate_service_key("test-hermes-key")
        assert result is None


# ── Stats Tests ───────────────────────────────────────

class TestAuthServiceStats:
    @pytest.mark.asyncio
    async def test_get_stats_empty(self, auth_service):
        stats = await auth_service.get_stats()
        assert stats["total"] == 0
        assert stats["by_role"] == {}

    @pytest.mark.asyncio
    async def test_get_stats_with_users(self, auth_service, in_memory_repos):
        user_repo, _ = in_memory_repos
        await user_repo.upsert("telegram", "st_001", role="reader")
        await user_repo.upsert("telegram", "st_002", role="admin")
        stats = await auth_service.get_stats()
        assert stats["total"] == 2
        assert stats["by_role"]["reader"] == 1
        assert stats["by_role"]["admin"] == 1


# ── Token Creation Tests ──────────────────────────────

class TestAuthTokenCreation:
    def test_create_token_decode_roundtrip(self):
        token = create_access_token(
            subject="user-rt",
            role="editor",
            provider="google",
            expires_delta=timedelta(hours=1),
        )
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.sub == "user-rt"
        assert payload.role == "editor"
        assert payload.provider == "google"

    def test_create_token_expiry(self):
        from datetime import datetime, timezone
        token = create_access_token(
            subject="user-exp",
            role="reader",
            provider="telegram",
            expires_delta=timedelta(seconds=45),
        )
        payload = decode_access_token(token)
        assert payload is not None
        now = datetime.now(tz=timezone.utc)
        diff = (payload.exp - now).total_seconds()
        assert diff < 60
        assert diff > 30
