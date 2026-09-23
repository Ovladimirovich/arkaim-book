"""
login_tokens — генерация и проверка одноразовых токенов для входа через Telegram бот.
Пользователь отправляет /login боту → бот генерирует токен → пользователь переходит по ссылке → авторизация.
"""
import hashlib
import secrets
import time
from typing import Optional

# Хранилище токенов в памяти (token -> {user_id, username, display_name, created_at})
_tokens: dict[str, dict] = {}

# TTL токена — 10 минут
TOKEN_TTL = 600


def generate_login_token(
    telegram_user_id: str,
    username: Optional[str] = None,
    display_name: Optional[str] = None,
    role: str = "reader",
) -> str:
    """Генерирует одноразовый токен для входа."""
    token = secrets.token_urlsafe(32)
    _tokens[token] = {
        "telegram_user_id": telegram_user_id,
        "username": username,
        "display_name": display_name,
        "role": role,
        "created_at": time.time(),
    }
    return token


def verify_login_token(token: str) -> Optional[dict]:
    """Проверяет токен и возвращает данные пользователя. Токен одноразовый — удаляется после проверки."""
    data = _tokens.pop(token, None)
    if data is None:
        return None

    # Проверка TTL
    if time.time() - data["created_at"] > TOKEN_TTL:
        return None

    return {
        "provider": "telegram",
        "provider_user_id": data["telegram_user_id"],
        "username": data.get("username"),
        "display_name": data.get("display_name"),
        "role": data.get("role", "reader"),
    }


def cleanup_expired():
    """Удаляет протухшие токены."""
    now = time.time()
    expired = [t for t, d in _tokens.items() if now - d["created_at"] > TOKEN_TTL]
    for t in expired:
        _tokens.pop(t, None)
