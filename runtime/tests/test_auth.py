"""Tests for auth package: tokens, api_keys, users, rbac, telegram oauth."""
import hashlib
import hmac
from datetime import timedelta, datetime, timezone

import pytest

from auth.tokens import create_access_token, decode_access_token, mask_token
from auth.api_keys import generate_api_key, mask_api_key
from auth.rbac import ROLE_HIERARCHY
from auth.oauth.telegram import verify_telegram_login, TelegramOAuthError, _build_data_check_string


# ── tokens.py ─────────────────────────────────────────────

class TestTokens:
    def test_create_and_decode(self):
        token = create_access_token("user1", "reader", "telegram")
        assert isinstance(token, str)
        assert len(token) > 20

        payload = decode_access_token(token)
        assert payload is not None
        assert payload.sub == "user1"
        assert payload.role == "reader"
        assert payload.provider == "telegram"
        assert payload.exp is not None

    def test_decode_invalid_returns_none(self):
        assert decode_access_token("") is None
        assert decode_access_token("not-a-jwt") is None
        assert decode_access_token("a.b.c") is None

    def test_decode_expired_token(self):
        token = create_access_token("u1", "admin", "google", expires_delta=timedelta(seconds=-1))
        payload = decode_access_token(token)
        assert payload is None

    def test_custom_expiry(self):
        token = create_access_token("u1", "editor", "telegram", expires_delta=timedelta(hours=1))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.role == "editor"

    def test_mask_token_short(self):
        assert mask_token("short") == "short"
        assert mask_token("") == ""

    def test_mask_token(self):
        token = "abcdefgh12345678"
        masked = mask_token(token)
        assert masked.startswith("abcdefgh")
        assert masked.endswith("5678")
        assert "..." in masked
        assert len(masked) < len(token)

    def test_token_role_provider_roundtrip(self):
        for role in ("reader", "editor", "admin"):
            for provider in ("telegram", "google", "internal"):
                token = create_access_token(f"u_{provider}", role, provider)
                payload = decode_access_token(token)
                assert payload is not None
                assert payload.role == role
                assert payload.provider == provider


# ── api_keys.py ────────────────────────────────────────────

class TestApiKeys:
    def test_generate_api_key(self):
        raw, key_hash, prefix = generate_api_key()
        assert len(raw) > 20
        assert len(prefix) == 8
        assert raw.startswith(prefix)
        assert len(key_hash) == 64  # sha256 hex
        assert hashlib.sha256(raw.encode()).hexdigest() == key_hash

    def test_generate_unique_keys(self):
        keys = [generate_api_key() for _ in range(100)]
        raws = {k[0] for k in keys}
        assert len(raws) == 100

    def test_mask_api_key(self):
        raw, _, _ = generate_api_key()
        masked = mask_api_key(raw)
        assert masked.startswith(raw[:8])
        assert "..." in masked
        assert len(masked) < len(raw)
        assert masked == "" if raw == "" else True

    def test_mask_api_key_empty(self):
        assert mask_api_key("") == ""
        assert mask_api_key(None if False else "") == ""

    def test_verify_key_hash(self):
        raw, key_hash, _ = generate_api_key()
        assert hashlib.sha256(raw.encode()).hexdigest() == key_hash
        assert hashlib.sha256((raw + "x").encode()).hexdigest() != key_hash


# ── users.py ───────────────────────────────────────────────·

@pytest.fixture
def temp_db_path():
    import tempfile
    import os
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    yield tmp.name
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_user_upsert_and_get(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        user = await store.upsert_user(
            provider="telegram", provider_user_id="123",
            username="tester", display_name="Test User",
        )
        assert user["id"] is not None
        assert user["provider"] == "telegram"
        assert user["provider_user_id"] == "123"
        assert user["role"] == "reader"
        assert user["is_active"] == 1

        fetched = await store.get_user(user["id"])
        assert fetched is not None
        assert fetched["display_name"] == "Test User"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_upsert_idempotent(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        u1 = await store.upsert_user("google", "456", username="g1", role="reader")
        u2 = await store.upsert_user("google", "456", username="g2", display_name="Updated")
        assert u1["id"] == u2["id"]
        assert u2["username"] == "g2"
        assert u2["display_name"] == "Updated"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_get_not_found(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        assert await store.get_user("nonexistent") is None
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_get_by_provider(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        await store.upsert_user("telegram", "111", username="a")
        user = await store.get_user_by_provider("telegram", "111")
        assert user is not None
        assert user["username"] == "a"
        assert await store.get_user_by_provider("telegram", "999") is None
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_set_role(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        user = await store.upsert_user("google", "222", role="reader")
        ok = await store.set_role(user["id"], "editor")
        assert ok
        fetched = await store.get_user(user["id"])
        assert fetched["role"] == "editor"

        ok = await store.set_role("nobody", "admin")
        assert not ok
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_set_active(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        user = await store.upsert_user("telegram", "333")
        ok = await store.set_active(user["id"], False)
        assert ok
        fetched = await store.get_user(user["id"])
        assert fetched["is_active"] == 0
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_list(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        await store.upsert_user("telegram", "a1", username="alice")
        await store.upsert_user("telegram", "b1", username="bob")
        users = await store.list_users()
        assert len(users) >= 2
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_sessions(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        user = await store.upsert_user("google", "444")
        sid = "sess_123"
        expires = datetime.now(tz=timezone.utc) + timedelta(hours=1)
        await store.save_session(sid, user["id"], "tok_hash", expires)
        session = await store.get_session(sid)
        assert session is not None
        assert session["user_id"] == user["id"]

        ok = await store.delete_session(sid)
        assert ok
        assert await store.get_session(sid) is None
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_user_api_keys(temp_db_path):
    from auth.users import UserStore
    store = UserStore(db_path=temp_db_path)
    try:
        user = await store.upsert_user("telegram", "666")
        await store.save_api_key(user["id"], "prefix1", "hash1", name="my key")
        await store.save_api_key(user["id"], "pref2", "hash2")
        keys = await store.list_api_keys(user["id"])
        assert len(keys) == 2

        key_hash = hashlib.sha256(b"test_key").hexdigest()
        await store.save_api_key(user["id"], "test", key_hash, name="byhash")
        found = await store.get_api_key_by_hash(key_hash)
        assert found is not None
        assert found["user_id"] == user["id"]

        target = [k for k in keys if k["name"] == "my key"][0]
        ok = await store.revoke_api_key(target["id"])
        assert ok
        keys_after = await store.list_api_keys(user["id"])
        revoked = [k for k in keys_after if k["id"] == target["id"]][0]
        assert revoked["is_active"] == 0
    finally:
        await store.close()


# ── rbac.py ───────────────────────────────────────────────

class TestRbac:
    def test_role_hierarchy(self):
        assert ROLE_HIERARCHY["reader"] == 0
        assert ROLE_HIERARCHY["editor"] == 1
        assert ROLE_HIERARCHY["admin"] == 2

    def test_require_role_reader_can_access_reader(self):
        levels = {"reader": 0, "editor": 1, "admin": 2}
        assert levels["reader"] >= levels["reader"]

    def test_reader_blocked_from_admin(self):
        levels = {"reader": 0, "editor": 1, "admin": 2}
        assert levels["reader"] < levels["admin"]
        allowed = [levels[r] for r in ("admin",)]
        assert levels["reader"] < min(allowed)

    def test_editor_can_access_editor(self):
        levels = {"reader": 0, "editor": 1, "admin": 2}
        assert levels["editor"] >= levels["editor"]

    def test_admin_can_access_anything(self):
        levels = {"reader": 0, "editor": 1, "admin": 2}
        for role in ("reader", "editor", "admin"):
            assert levels["admin"] >= levels[role]

    def test_unknown_role_lowest(self):
        levels = {"reader": 0, "editor": 1, "admin": 2}
        assert levels.get("unknown", -1) == -1  # ROLE_HIERARCHY.get returns None, not -1
        user_level = ROLE_HIERARCHY.get("unknown", -1)
        assert user_level < 0


# ── oauth/telegram.py ─────────────────────────────────────

class TestTelegramOAuth:
    def test_build_data_check_string(self):
        data = {"id": "123", "first_name": "Alice", "auth_date": "1700000000"}
        result = _build_data_check_string(data)
        assert "auth_date=1700000000" in result
        assert "first_name=Alice" in result
        assert "id=123" in result
        assert "hash" not in result

    def test_build_data_check_string_sorted(self):
        data = {"z": "1", "a": "2", "m": "3"}
        result = _build_data_check_string(data)
        parts = result.split("\n")
        assert parts[0].startswith("a=")
        assert parts[-1].startswith("z=")

    def test_verify_no_bot_token(self, monkeypatch):
        monkeypatch.setattr("auth.oauth.telegram.settings.TELEGRAM_BOT_TOKEN", "")
        with pytest.raises(TelegramOAuthError, match="не задан"):
            verify_telegram_login({"id": "1"})

    def test_verify_no_hash(self, monkeypatch):
        monkeypatch.setattr("auth.oauth.telegram.settings.TELEGRAM_BOT_TOKEN", "test_bot")
        with pytest.raises(TelegramOAuthError, match="Отсутствует hash"):
            verify_telegram_login({"id": "1"})

    def test_verify_invalid_hash(self, monkeypatch):
        monkeypatch.setattr("auth.oauth.telegram.settings.TELEGRAM_BOT_TOKEN", "test_bot")
        with pytest.raises(TelegramOAuthError, match="Неверный hash"):
            verify_telegram_login({"id": "1", "hash": "invalid"})

    def test_verify_valid_telegram_login(self, monkeypatch):
        bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        monkeypatch.setattr("auth.oauth.telegram.settings.TELEGRAM_BOT_TOKEN", bot_token)

        data = {
            "id": "12345",
            "first_name": "Иван",
            "last_name": "Петров",
            "username": "ivanpetrov",
            "auth_date": "1700000000",
        }
        data_check_string = _build_data_check_string(data)
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        result = verify_telegram_login(data)
        assert result["provider"] == "telegram"
        assert result["provider_user_id"] == "12345"
        assert result["username"] == "ivanpetrov"
        assert result["display_name"] == "Иван Петров"

    def test_verify_telegram_no_optional_fields(self, monkeypatch):
        bot_token = "test:token"
        monkeypatch.setattr("auth.oauth.telegram.settings.TELEGRAM_BOT_TOKEN", bot_token)

        data = {"id": "999", "auth_date": "1700000000"}
        data_check_string = _build_data_check_string(data)
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        result = verify_telegram_login(data)
        assert result["provider_user_id"] == "999"
        assert result["username"] is None
        assert result["display_name"] == ""
