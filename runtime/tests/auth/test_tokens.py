"""Тесты для auth/tokens.py — JWT создание, декодирование, верификация."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from auth.tokens import create_access_token, decode_access_token, TokenPayload, mask_token


class TestCreateAccessToken:
    """Тесты создания JWT токенов."""

    def test_creates_valid_jwt(self):
        """Проверка формата JWT: три части, разделённые точками."""
        token = create_access_token(
            subject="user-123",
            role="reader",
            provider="telegram",
        )
        parts = token.split(".")
        assert len(parts) == 3, "JWT должен состоять из 3 частей"
        assert all(len(p) > 0 for p in parts), "Каждая часть JWT не должна быть пустой"

    def test_token_contains_required_claims(self):
        """Проверка, что токен содержит sub, role, provider, exp."""
        token = create_access_token(
            subject="user-123",
            role="admin",
            provider="google",
        )
        from core.config import settings
        payload = jwt.decode(token, settings.SESSION_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert payload["provider"] == "google"
        assert "exp" in payload

    def test_custom_expiry(self):
        """Проверка кастомного времени истечения."""
        token = create_access_token(
            subject="user-123",
            role="reader",
            provider="telegram",
            expires_delta=timedelta(seconds=30),
        )
        from core.config import settings
        payload = jwt.decode(token, settings.SESSION_SECRET, algorithms=["HS256"])
        import time
        # exp должен быть в пределах 30-60 секунд от now
        now_ts = time.time()
        assert payload["exp"] - now_ts < 60, "exp должен быть ~30 секунд"
        assert payload["exp"] - now_ts > 20, "exp не должен быть меньше 20 секунд"


class TestDecodeAccessToken:
    """Тесты декодирования и верификации JWT токенов."""

    def test_decode_valid_token(self, valid_token_reader: str):
        """Успешное декодирование валидного токена."""
        payload = decode_access_token(valid_token_reader)
        assert payload is not None
        assert isinstance(payload, TokenPayload)
        assert payload.role == "reader"
        assert payload.provider == "telegram"
        assert payload.sub is not None

    def test_decode_expired_token(self, expired_token: str):
        """Ошибка при декодировании просроченного токена."""
        payload = decode_access_token(expired_token)
        assert payload is None, "Просроченный токен должен возвращать None"

    def test_decode_invalid_signature(self, tampered_token: str):
        """Ошибка при декодировании токена с невалидной подписью."""
        payload = decode_access_token(tampered_token)
        assert payload is None, "Токен с изменённой подписью должен возвращать None"

    def test_decode_garbage(self, invalid_token: str):
        """Ошибка при декодировании мусорной строки."""
        payload = decode_access_token(invalid_token)
        assert payload is None, "Мусорная строка должна возвращать None"

    def test_decode_empty_string(self):
        """Ошибка при декодировании пустой строки."""
        payload = decode_access_token("")
        assert payload is None, "Пустая строка должна возвращать None"

    def test_token_payload_fields(self, valid_token_reader: str):
        """Проверка, что TokenPayload содержит все необходимые поля."""
        payload = decode_access_token(valid_token_reader)
        assert payload is not None
        assert hasattr(payload, "sub")
        assert hasattr(payload, "role")
        assert hasattr(payload, "provider")
        assert hasattr(payload, "exp")


class TestMaskToken:
    """Тесты маскирования токенов."""

    def test_mask_long_token(self):
        """Маскирование длинного токена: первые 8 + ... + последние 4."""
        token = "abcdefghijklmnopqrstuvwxyz0123456789"
        masked = mask_token(token)
        assert masked.startswith("abcdefgh")
        assert masked.endswith("6789")
        assert "..." in masked

    def test_mask_short_token(self):
        """Короткий токен не маскируется."""
        token = "short"
        assert mask_token(token) == token

    def test_mask_empty_token(self):
        """Пустой токен возвращает пустую строку."""
        assert mask_token("") == ""

    def test_mask_boundary(self):
        """Токен длиной ровно 8 символов."""
        token = "12345678"
        assert mask_token(token) == token