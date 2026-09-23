"""Тесты для auth/users.py — UserStore (upsert, get, set_role, sessions, api_keys)."""

import pytest


class TestUserStoreCreate:
    """Тесты создания пользователей."""

    async def test_upsert_new_user(self, user_store):
        """Создание нового пользователя."""
        user = await user_store.upsert_user(
            provider="telegram",
            provider_user_id="111",
            username="new_user",
            display_name="New User",
        )
        assert user is not None
        assert user["provider"] == "telegram"
        assert user["provider_user_id"] == "111"
        assert user["username"] == "new_user"
        assert user["role"] == "reader"
        assert user["is_active"] == 1
        assert "id" in user

    async def test_upsert_creates_unique_id(self, user_store):
        """Каждый новый пользователь получает уникальный ID."""
        user1 = await user_store.upsert_user("telegram", "u1", "user1")
        user2 = await user_store.upsert_user("telegram", "u2", "user2")
        assert user1["id"] != user2["id"]


class TestUserStoreUpdate:
    """Тесты обновления существующих пользователей."""

    async def test_upsert_existing_user_updates(self, user_store):
        """Обновление существующего пользователя."""
        user = await user_store.upsert_user("telegram", "222", "old_name")
        user_id = user["id"]

        updated = await user_store.upsert_user("telegram", "222", "new_name", "New Display")
        assert updated["id"] == user_id
        assert updated["username"] == "new_name"
        assert updated["display_name"] == "New Display"

    async def test_upsert_existing_updates_role_if_provided(self, user_store):
        """Обновление с явным указанием role меняет роль."""
        user = await user_store.upsert_user("telegram", "333", "user3", role="admin")
        updated = await user_store.upsert_user("telegram", "333", "user3_new", role="editor")
        assert updated["role"] == "editor"


class TestUserStoreGet:
    """Тесты получения пользователей."""

    async def test_get_user_by_provider(self, user_store):
        """Получение пользователя по провайдеру."""
        await user_store.upsert_user("telegram", "444", "get_test")
        user = await user_store.get_user_by_provider("telegram", "444")
        assert user is not None
        assert user["username"] == "get_test"

    async def test_get_user_by_id(self, user_store):
        """Получение пользователя по ID."""
        created = await user_store.upsert_user("google", "555", "id_test")
        user = await user_store.get_user(created["id"])
        assert user is not None
        assert user["id"] == created["id"]

    async def test_get_nonexistent_user(self, user_store):
        """Поиск отсутствующего пользователя."""
        user = await user_store.get_user("nonexistent-id")
        assert user is None

    async def test_get_nonexistent_provider(self, user_store):
        """Поиск отсутствующего провайдера."""
        user = await user_store.get_user_by_provider("telegram", "no-such-user")
        assert user is None


class TestUserStoreRole:
    """Тесты управления ролями."""

    async def test_set_role(self, user_store):
        """Изменение роли пользователя."""
        user = await user_store.upsert_user("telegram", "666", "role_test")
        result = await user_store.set_role(user["id"], "admin")
        assert result is True

        updated = await user_store.get_user(user["id"])
        assert updated["role"] == "admin"

    async def test_set_role_nonexistent_user(self, user_store):
        """Изменение роли отсутствующего пользователя."""
        result = await user_store.set_role("no-such-id", "admin")
        assert result is False

    async def test_list_users(self, user_store, test_user_reader, test_user_editor, test_user_admin):
        """Список пользователей содержит созданных."""
        users = await user_store.list_users()
        assert len(users) >= 3
        usernames = {u["username"] for u in users}
        assert "test_reader" in usernames
        assert "test_editor" in usernames
        assert "test_admin" in usernames

    async def test_set_active(self, user_store):
        """Деактивация пользователя."""
        user = await user_store.upsert_user("telegram", "777", "active_test")
        result = await user_store.set_active(user["id"], False)
        assert result is True

        updated = await user_store.get_user(user["id"])
        assert updated["is_active"] == 0


class TestUserStoreSessions:
    """Тесты управления сессиями."""

    async def test_save_and_get_session(self, user_store, test_user_reader):
        """Сохранение и получение сессии."""
        from datetime import datetime, timedelta, timezone
        session_id = "test-session-1"
        token_hash = "abc123hash"
        expires = datetime.now(tz=timezone.utc) + timedelta(days=1)

        await user_store.save_session(session_id, test_user_reader["id"], token_hash, expires)
        session = await user_store.get_session(session_id)

        assert session is not None
        assert session["id"] == session_id
        assert session["user_id"] == test_user_reader["id"]
        assert session["token_hash"] == token_hash

    async def test_delete_session(self, user_store, test_user_editor):
        """Удаление сессии."""
        from datetime import datetime, timedelta, timezone
        session_id = "test-session-to-delete"
        expires = datetime.now(tz=timezone.utc) + timedelta(days=1)

        await user_store.save_session(session_id, test_user_editor["id"], "hash123", expires)
        result = await user_store.delete_session(session_id)
        assert result is True

        session = await user_store.get_session(session_id)
        assert session is None

    async def test_get_nonexistent_session(self, user_store):
        """Поиск отсутствующей сессии."""
        session = await user_store.get_session("no-such-session")
        assert session is None


class TestUserStoreApiKeys:
    """Тесты управления API-ключами."""

    async def test_save_and_list_api_keys(self, user_store, test_user_admin):
        """Сохранение и получение списка API-ключей."""
        key_id = await user_store.save_api_key(
            test_user_admin["id"],
            "prefix123",
            "hash1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            "test-key",
        )
        assert key_id is not None

        keys = await user_store.list_api_keys(test_user_admin["id"])
        assert len(keys) >= 1
        assert any(k["id"] == key_id for k in keys)

    async def test_get_api_key_by_hash(self, user_store, test_user_reader):
        """Получение ключа по хэшу."""
        key_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        await user_store.save_api_key(test_user_reader["id"], "pref1", key_hash, "key-by-hash")

        found = await user_store.get_api_key_by_hash(key_hash)
        assert found is not None
        assert found["key_hash"] == key_hash

    async def test_revoke_api_key(self, user_store, test_user_editor):
        """Отзыв API-ключа."""
        key_hash = "revoke_test_hash_1234567890abcdef1234567890abcdef1234567890abcdef"
        key_id = await user_store.save_api_key(test_user_editor["id"], "rev", key_hash, "revoke-test")

        result = await user_store.revoke_api_key(key_id)
        assert result is True

        key = await user_store.get_api_key_by_hash(key_hash)
        assert key["is_active"] == 0

    async def test_touch_api_key(self, user_store, test_user_reader):
        """Обновление времени последнего использования ключа."""
        key_hash = "touch_test_hash_1234567890abcdef1234567890abcdef1234567890abcdef"
        key_id = await user_store.save_api_key(test_user_reader["id"], "tch", key_hash, "touch-test")

        await user_store.touch_api_key(key_id)
        key = await user_store.get_api_key_by_hash(key_hash)
        assert key["last_used_at"] is not None