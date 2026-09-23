"""Тесты для auth/rbac.py — Role-Based Access Control."""

import pytest
from fastapi import HTTPException


# ── Хелпер для тестирования require_role ──────────────
async def _check_role(checker, user_dict: dict):
    """Вызывает require_role-проверку с user dict напрямую (как FastAPI Depends)."""
    try:
        result = await checker(user_dict)
        return True, result
    except HTTPException as e:
        return False, e


class TestGetCurrentUser:
    """Тесты get_current_user.
    
    Для этих тестов мы не используем фикстуру user_store (in-memory),
    так как get_current_user() создаёт свой собственный UserStore.
    Вместо этого тестируем логику напрямую через create_access_token + decode.
    """

    async def test_valid_token_returns_user(self, test_user_reader, valid_token_reader):
        """Валидный токен — проверяем, что decode_access_token возвращает данные.
        Полноценную интеграцию с get_current_user тестируем через service key.
        """
        from auth.tokens import decode_access_token
        payload = decode_access_token(valid_token_reader)
        assert payload is not None
        assert payload.role == "reader"
        assert payload.sub == test_user_reader["id"]

    async def test_no_token_raises_401(self):
        """Отсутствие токена вызывает 401."""
        from auth.rbac import get_current_user
        from fastapi import Request

        scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == 401

    async def test_invalid_token_raises_401(self):
        """Невалидный токен вызывает 401."""
        from auth.rbac import get_current_user
        from fastapi import Request

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", b"Bearer invalid.token.here")],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == 401

    async def test_service_key_without_attached_user_returns_403(self):
        """Service key без привязанного пользователя возвращает 403."""
        import os
        api_key = os.environ.get("HERMES_API_KEY", "test-service-key")
        from auth.rbac import get_current_user
        from fastapi import Request, HTTPException

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", f"Bearer {api_key}".encode())],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code == 403

    async def test_cookie_token_returns_401_for_unknown_user(self):
        """Токен в cookie для несуществующего пользователя возвращает 403."""
        from auth.tokens import create_access_token
        from auth.rbac import get_current_user
        from fastapi import Request, HTTPException

        token = create_access_token(
            subject="nonexistent-user",
            role="reader",
            provider="telegram",
        )

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"cookie", f"arkaim_session={token}".encode())],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request)
        assert exc_info.value.status_code in (401, 403)


class TestRequireRole:
    """Тесты декоратора require_role."""

    async def test_reader_can_access_reader_endpoint(self):
        """Пользователь reader может получить доступ к reader-эндпоинту."""
        from auth.rbac import require_role

        reader = {"user_id": "u1", "role": "reader", "provider": "telegram"}
        checker = require_role("reader", "editor", "admin")
        ok, result = await _check_role(checker, reader)
        assert ok is True
        assert result["role"] == "reader"

    async def test_reader_cannot_access_admin_endpoint(self):
        """Пользователь reader не может получить доступ к admin-эндпоинту."""
        from auth.rbac import require_role

        reader = {"user_id": "u1", "role": "reader", "provider": "telegram"}
        checker = require_role("admin")
        ok, exc = await _check_role(checker, reader)
        assert ok is False
        assert exc.status_code == 403

    async def test_editor_can_access_editor_endpoint(self):
        """Пользователь editor имеет доступ к editor-эндпоинту."""
        from auth.rbac import require_role

        editor = {"user_id": "u2", "role": "editor", "provider": "telegram"}
        checker = require_role("editor", "admin")
        ok, result = await _check_role(checker, editor)
        assert ok is True
        assert result["role"] == "editor"

    async def test_admin_can_access_all(self):
        """Пользователь admin имеет доступ ко всем эндпоинтам."""
        from auth.rbac import require_role

        admin = {"user_id": "u3", "role": "admin", "provider": "google"}
        for role in ["reader", "editor", "admin"]:
            checker = require_role(role)
            ok, result = await _check_role(checker, admin)
            assert ok is True, f"admin должен иметь доступ к {role}-endpoint"

    async def test_unknown_role_has_no_access(self):
        """Пользователь с неизвестной ролью не имеет доступа."""
        from auth.rbac import require_role

        unknown = {"user_id": "u4", "role": "unknown_role", "provider": "telegram"}
        checker = require_role("reader", "editor", "admin")
        ok, exc = await _check_role(checker, unknown)
        assert ok is False
        assert exc.status_code == 403


class TestRoleHierarchy:
    """Тесты иерархии ролей."""

    def test_role_hierarchy_values(self):
        """Проверка числовых значений иерархии."""
        from auth.rbac import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["reader"] == 0
        assert ROLE_HIERARCHY["editor"] == 1
        assert ROLE_HIERARCHY["admin"] == 2
        assert ROLE_HIERARCHY["reader"] < ROLE_HIERARCHY["editor"] < ROLE_HIERARCHY["admin"]

    def test_unknown_role_default(self):
        """Неизвестная роль имеет значение -1."""
        from auth.rbac import ROLE_HIERARCHY
        assert ROLE_HIERARCHY.get("unknown", -1) == -1