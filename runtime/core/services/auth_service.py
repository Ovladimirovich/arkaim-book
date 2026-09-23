"""Сервис аутентификации — бизнес-логика входа/выхода/ролей."""
from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from auth.tokens import create_access_token, decode_access_token
from auth.oauth.telegram import verify_telegram_login, TelegramOAuthError
from auth.oauth.google import (
    exchange_code,
    verify_google_id_token,
    parse_google_user,
    get_google_auth_url,
    GoogleOAuthError,
)
from auth.api_keys import generate_api_key, mask_api_key
from core.repositories.user_repo import UserRepository
from core.repositories.api_key_repo import ApiKeyRepository
from core.dto.requests import LoginData

log = logging.getLogger("hermes.auth.service")

TOKEN_EXPIRY = timedelta(hours=12)


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.api_key_repo = ApiKeyRepository(self.user_repo)

    # ── Telegram ──────────────────────────────────────

    async def login_telegram(self, telegram_data: dict) -> dict:
        """Обработать вход через Telegram. Возвращает user + token."""
        verified = verify_telegram_login(telegram_data)
        user = await self.user_repo.upsert(
            provider=verified["provider"],
            provider_user_id=verified["provider_user_id"],
            username=verified.get("username"),
            display_name=verified.get("display_name"),
            role="reader",
        )
        token = create_access_token(
            subject=user["id"],
            role=user["role"],
            provider=user["provider"],
            expires_delta=TOKEN_EXPIRY,
        )
        log.info("user_logged_in provider=telegram user_id=%s", user["id"])
        return {"user": user, "token": token}

    # ── Google ────────────────────────────────────────

    async def login_google(self, code: str, redirect_uri: str) -> dict:
        """Обработать вход через Google. Возвращает user + token."""
        tokens = await exchange_code(code, redirect_uri)
        id_token = tokens.get("id_token")
        if not id_token:
            raise ValueError("Отсутствует id_token")
        payload = verify_google_id_token(id_token)
        google_data = parse_google_user(payload)
        user = await self.user_repo.upsert(
            provider=google_data["provider"],
            provider_user_id=google_data["provider_user_id"],
            username=google_data.get("username"),
            display_name=google_data.get("display_name"),
            role="reader",
        )
        token = create_access_token(
            subject=user["id"],
            role=user["role"],
            provider=user["provider"],
            expires_delta=TOKEN_EXPIRY,
        )
        log.info("user_logged_in provider=google user_id=%s", user["id"])
        return {"user": user, "token": token}

    def get_google_auth_url(self, redirect_uri: str) -> str:
        return get_google_auth_url(redirect_uri)

    # ── API Keys ──────────────────────────────────────

    async def create_api_key(self, user_id: str, name: str | None = None) -> dict:
        raw, key_hash, prefix = generate_api_key()
        key_id = await self.api_key_repo.create(user_id=user_id, key_prefix=prefix, key_hash=key_hash, name=name)
        return {"key_id": key_id, "key": raw, "key_masked": mask_api_key(raw)}

    async def list_api_keys(self, user_id: str) -> list[dict]:
        keys = await self.api_key_repo.list_by_user(user_id)
        return [{k: v for k, v in key.items() if k != "key_hash"} for key in keys]

    # ── Service key ───────────────────────────────────

    async def authenticate_service_key(self, token: str) -> dict | None:
        """Аутентифицировать сервисный ключ. Возвращает user или None."""
        from core.config import settings
        if not settings.HERMES_API_KEY or token != settings.HERMES_API_KEY:
            return None
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = await self.api_key_repo.get_by_hash(key_hash)
        if not api_key or not api_key.get("is_active"):
            return None
        user = await self.user_repo.get_by_id(api_key["user_id"])
        if not user or not user.get("is_active"):
            return None
        return user

    # ── Stats ─────────────────────────────────────────

    async def get_stats(self) -> dict:
        users = await self.user_repo.list_all(limit=10000)
        return {
            "total": len(users),
            "by_role": await self.user_repo.count_by_role(),
        }
