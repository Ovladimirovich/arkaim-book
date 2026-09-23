"""
Модуль для работы с VK (ВКонтакте).
Интеграция с VK API для российского рынка.
"""
import logging
import httpx
from config import config

logger = logging.getLogger(__name__)


class VKBot:
    """
    VK Bot интеграция для российского рынка.
    Поддерживает Callback API, сообщения и сообщества.
    """

    def __init__(self):
        self.config = config
        self.group_id = getattr(self.config, 'VK_GROUP_ID', None)
        self.access_token = getattr(self.config, 'VK_ACCESS_TOKEN', None)
        self.confirmation_code = getattr(self.config, 'VK_CONFIRMATION_CODE', None)
        self.api_url = "https://api.vk.com/method"
        self.api_version = "5.199"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call_api(self, method: str, params: dict = None) -> dict:
        """Вызов VK API."""
        if not self.access_token:
            logger.warning("VK_ACCESS_TOKEN не настроен, использую stub режим")
            return {"response": {}}

        try:
            url = f"{self.api_url}/{method}"
            params = params or {}
            params.update({
                "access_token": self.access_token,
                "v": self.api_version
            })
            response = await self._client.post(url, data=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"VK API error: {e}")
            return {"error": {"error_msg": str(e)}}

    async def handle_callback(self, data: dict) -> str:
        """
        Обработка Callback API от VK.
        Возвращает ответ для VK.
        """
        event_type = data.get("type")

        if event_type == "confirmation":
            # Подтверждение сервера
            if self.confirmation_code:
                return self.confirmation_code
            else:
                logger.warning("VK_CONFIRMATION_CODE не настроен")
                return "ok"

        elif event_type == "message_new":
            # Новое сообщение
            message = data.get("object", {}).get("message", {})
            user_id = message.get("from_id")
            text = message.get("text", "")
            logger.info(f"VK сообщение от {user_id}: {text}")

            # Process message through orchestrator
            try:
                from core.orchestrator import Orchestrator
                from core.providers.registry import ProviderRegistry

                orchestrator = Orchestrator(
                    memory=None,
                    skills=[],
                    config=self.config,
                )

                # Build request for orchestrator
                req = {
                    "messages": [{"role": "user", "content": text}],
                    "provider": "gigachat",
                    "model": "GigaChat",
                    "metadata": {"session_id": f"vk_{user_id}", "source": "vk"},
                }

                # Get user info from VK
                user_info = {
                    "sub": f"vk_{user_id}",
                    "username": f"vk_{user_id}",
                    "provider": "vk",
                }

                # Process through orchestrator
                response = await orchestrator.run(req, user_info)

                if response and "choices" in response:
                    reply_text = response["choices"][0]["message"]["content"]
                    await self.send_message(user_id, reply_text)
                else:
                    await self.send_message(user_id, "Извините, не удалось обработать сообщение.")

            except Exception as e:
                logger.error(f"VK message processing error: {e}")
                await self.send_message(user_id, "Произошла ошибка при обработке сообщения.")

            return "ok"

        elif event_type == "group_join":
            # Пользователь вступил в группу
            user_id = data.get("object", {}).get("user_id")
            logger.info(f"Пользователь {user_id} вступил в группу")
            return "ok"

        elif event_type == "group_leave":
            # Пользователь покинул группу
            user_id = data.get("object", {}).get("user_id")
            logger.info(f"Пользователь {user_id} покинул группу")
            return "ok"

        return "ok"

    async def send_message(self, user_id: str, message: str) -> bool:
        """
        Отправка сообщения пользователю VK.
        """
        result = await self._call_api("messages.send", {
            "user_id": user_id,
            "message": message,
            "random_id": 0  # VK требует random_id
        })

        success = "error" not in result
        logger.info(f"VK сообщение отправлено: {success}")
        return success

    async def send_group_message(self, message: str) -> bool:
        """
        Отправка сообщения в группу (через wall.post).
        """
        if not self.group_id:
            logger.warning("VK_GROUP_ID не настроен")
            return False

        result = await self._call_api("wall.post", {
            "owner_id": f"-{self.group_id}",
            "message": message,
            "from_group": 1
        })

        success = "error" not in result
        logger.info(f"VK пост в группе: {success}")
        return success

    async def get_group_info(self) -> dict:
        """
        Получение информации о группе.
        """
        if not self.group_id:
            return {}

        result = await self._call_api("groups.getById", {
            "group_id": self.group_id
        })
        return result.get("response", {})

    async def get_group_members(self, count: int = 100) -> dict:
        """
        Получение списка участников группы.
        """
        if not self.group_id:
            return {}

        result = await self._call_api("groups.getMembers", {
            "group_id": self.group_id,
            "count": count
        })
        return result.get("response", {})

    async def close(self):
        """Закрытие HTTP клиента."""
        await self._client.aclose()
