"""
telegram_bot — Telegram бот для «Наследие Аркаима».
Обрабатывает команду /login для авторизации через ссылку.
"""
import asyncio
import logging
import os
from typing import Optional

import httpx

from auth.login_tokens import generate_login_token

log = logging.getLogger("hermes.telegram_bot")

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramBot:
    """Простой Telegram бот для обработки команд."""

    def __init__(self, bot_token: str, public_base_url: str):
        self.bot_token = bot_token
        self.public_base_url = public_base_url.rstrip("/")
        self._offset = 0
        self._running = False

    async def _api(self, method: str, data: dict = None) -> dict:
        """Вызов Telegram Bot API."""
        url = TELEGRAM_API.format(token=self.bot_token, method=method)
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=data or {}, timeout=10)
            return resp.json()

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML"):
        """Отправить сообщение с проверкой ответа."""
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        result = await self._api("sendMessage", data)
        if not result.get("ok"):
            error_code = result.get("error_code", 0)
            description = result.get("description", "unknown")
            if error_code == 400 and "parse" in description.lower():
                log.warning("telegram_parse_error chat=%d desc=%s — retrying plain", chat_id, description)
                await self._api("sendMessage", {"chat_id": chat_id, "text": text})
            else:
                log.error("telegram_send_error chat=%d code=%d desc=%s", chat_id, error_code, description)

    async def handle_command(self, message: dict):
        """Обработка команд."""
        chat_id = message["chat"]["id"]
        user = message.get("from", {})
        text = message.get("text", "").strip()
        username = user.get("username", "")
        display_name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
        telegram_user_id = str(user.get("id", ""))

        if text == "/login":
            # Генерируем одноразовый токен
            token = generate_login_token(
                telegram_user_id=telegram_user_id,
                username=username,
                display_name=display_name,
            )
            login_url = f"{self.public_base_url}/login?token={token}"

            # Plain text — Telegram НЕ автолинкует URL в бот-сообщениях
            # поэтому даём инструкцию скопировать
            msg = (
                "Вход в «Наследие Аркаима»\n\n"
                "Скопируйте ссылку и откройте в браузере:\n\n"
                f"{login_url}\n\n"
                "Ссылка действительна 10 минут.\n"
                f"Пользователь: @{username or 'без username'}"
            )

            await self.send_message(chat_id, msg, None)
            log.info("login_token_sent user_id=%s username=%s url=%s", telegram_user_id, username, login_url)

        elif text == "/start":
            await self.send_message(chat_id,
                "👋 Добро пожаловать в «Наследие Аркаима»!\n\n"
                "Команды:\n"
                "/login — Войти в систему\n"
                "/help — Помощь"
            )

        elif text == "/help":
            await self.send_message(chat_id,
                "📖 <b>Наследие Аркаима</b> — цифровое сознание книги\n\n"
                "Команды:\n"
                "/login — Получить ссылку для входа\n"
                "/help — Эта справка"
            )

    async def poll(self):
        """Long polling — обработка входящих сообщений."""
        self._running = True
        log.info("telegram_bot_started")

        consecutive_errors = 0
        max_consecutive_errors = 5

        while self._running:
            try:
                result = await self._api("getUpdates", {
                    "offset": self._offset,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                })

                if not result.get("ok"):
                    error_code = result.get("error_code", 0)
                    description = result.get("description", "unknown")
                    # 409 = conflict (another bot instance), 401 = unauthorized
                    if error_code in (401, 409):
                        log.warning("telegram_bot致命 error_code=%d desc=%s — останавливаю polling", error_code, description)
                        self._running = False
                        break
                    log.error("telegram_get_updates_error code=%d desc=%s", error_code, description)
                    consecutive_errors += 1
                    await asyncio.sleep(min(5 * consecutive_errors, 60))
                    continue

                consecutive_errors = 0  # Сброс при успешном запросе

                for update in result.get("result", []):
                    self._offset = update["update_id"] + 1
                    message = update.get("message")
                    if message and message.get("text", "").startswith("/"):
                        try:
                            await self.handle_command(message)
                        except Exception as e:
                            log.error("telegram_handle_command_error: %s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    log.warning("telegram_poll_error (attempt %d/%d): %s", consecutive_errors, max_consecutive_errors, e)
                elif consecutive_errors == max_consecutive_errors:
                    log.error("telegram_poll_error: слишком много ошибок подряд, снижаю частоту polling")
                await asyncio.sleep(min(5 * consecutive_errors, 120))

    def stop(self):
        """Остановить polling."""
        self._running = False


# Синглтон
_bot: Optional[TelegramBot] = None


def get_bot() -> Optional[TelegramBot]:
    """Получить экземпляр бота."""
    return _bot


def init_bot():
    """Инициализировать бота из env."""
    global _bot
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    # Ссылка для входа должна вести на фронтенд, не на бэкенд
    frontend_url = os.getenv("FRONTEND_URL", "") or os.getenv("PUBLIC_BASE_URL", "http://localhost:3000")

    if not bot_token:
        log.warning("telegram_bot_not_configured: TELEGRAM_BOT_TOKEN не задан")
        return None

    _bot = TelegramBot(bot_token=bot_token, public_base_url=frontend_url)
    log.info("telegram_bot_initialized base_url=%s", frontend_url)
    return _bot
