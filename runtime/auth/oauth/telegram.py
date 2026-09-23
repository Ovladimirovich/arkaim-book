import hashlib
import hmac
import time
from typing import Any

from core.config import settings


TELEGRAM_LOGIN_FIELDS = ("auth_date", "first_name", "id", "last_name", "photo_url", "username")
TELEGRAM_AUTH_DATE_MAX_AGE = 600  # 10 минут — рекомендация Telegram


class TelegramOAuthError(Exception):
    pass


def _build_data_check_string(data: dict[str, Any]) -> str:
    return "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if v is not None and k != "hash")


def verify_telegram_login(data: dict[str, Any]) -> dict[str, Any]:
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise TelegramOAuthError("TELEGRAM_BOT_TOKEN не задан")
    received_hash = data.get("hash")
    if not received_hash:
        raise TelegramOAuthError("Отсутствует hash")

    # Проверка свежести auth_date (защита от replay-атаки)
    auth_date_str = data.get("auth_date")
    if not auth_date_str:
        raise TelegramOAuthError("Отсутствует auth_date")
    try:
        auth_date = int(auth_date_str)
    except (ValueError, TypeError):
        raise TelegramOAuthError("Некорректный auth_date")
    if abs(time.time() - auth_date) > TELEGRAM_AUTH_DATE_MAX_AGE:
        raise TelegramOAuthError("Данные Telegram устарели (auth_date)")

    data_check_string = _build_data_check_string(data)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramOAuthError("Неверный hash Telegram")
    return {
        "provider": "telegram",
        "provider_user_id": str(data["id"]),
        "username": data.get("username"),
        "display_name": " ".join(filter(None, [data.get("first_name"), data.get("last_name")])),
        "auth_date": data.get("auth_date"),
        "photo_url": data.get("photo_url"),
    }
