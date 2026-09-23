import logging
from typing import Any

import httpx
from jose import JWTError, jwt
from jose import jwk as jose_jwk

from core.config import settings

log = logging.getLogger("hermes.auth.google")


class GoogleOAuthError(Exception):
    pass


GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Кэш для Google JWKS ключей (загружаются один раз)
_google_jwks_cache: dict[str, Any] = {}


async def _get_google_jwks() -> dict[str, Any]:
    """Загрузить Google JWKS ключи с кэшированием."""
    global _google_jwks_cache
    if _google_jwks_cache:
        return _google_jwks_cache
    discovery = await get_google_discovery()
    jwks_uri = discovery.get("jwks_uri")
    if not jwks_uri:
        raise GoogleOAuthError("jwks_uri не найден в discovery document")
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        _google_jwks_cache = resp.json()
    return _google_jwks_cache


async def get_google_discovery() -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_DISCOVERY_URL)
        resp.raise_for_status()
        return resp.json()


async def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    if not client_id or not client_secret:
        raise GoogleOAuthError("GOOGLE_CLIENT_ID или GOOGLE_CLIENT_SECRET не задан")
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            raise GoogleOAuthError("Ошибка обмена кода Google")
        return resp.json()


async def verify_google_id_token(id_token: str) -> dict[str, Any]:
    """Верифицировать Google ID-токен с проверкой подписи через JWKS."""
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise GoogleOAuthError("GOOGLE_CLIENT_ID не задан")
    try:
        # Сначала декодируем без проверки подписи чтобы получить header
        unverified = jwt.get_unverified_header(id_token)
        kid = unverified.get("kid")

        # Загружаем JWKS ключи
        jwks = await _get_google_jwks()

        # Находим ключ по kid
        signing_key = None
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                signing_key = jose_jwk.construct(key_data)
                break

        if not signing_key:
            raise GoogleOAuthError("Ключ подписи Google не найден в JWKS")

        # Верифицируем подпись + audience + issuer
        payload = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=("https://accounts.google.com", "accounts.google.com"),
        )
        return payload
    except JWTError as e:
        raise GoogleOAuthError(f"Неверный ID-токен: {e}")


def get_google_auth_url(redirect_uri: str) -> str:
    from urllib.parse import urlencode
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise GoogleOAuthError("GOOGLE_CLIENT_ID не задан")
    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
    })
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


def parse_google_user(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "google",
        "provider_user_id": payload["sub"],
        "username": payload.get("email", "").split("@")[0],
        "display_name": payload.get("name", ""),
        "email": payload.get("email", ""),
    }
