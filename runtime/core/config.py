"""
config — совместимость: проксирует shared_config.settings + добавляет 2 поля.
Импорты типа `from core.config import settings` продолжают работать.
"""
import os

from shared_config import settings as _shared_settings


class Settings:
    """Прокси к SharedSettings с двумя дополнительными полями."""

    def __getattr__(self, name: str):
        return getattr(_shared_settings, name)

    # Дополнительные поля, которых нет в shared_config
    HERMES_SKILLS_PATH: str = os.getenv("HERMES_SKILLS_PATH", "")
    BUSINESS_PACK: str = os.getenv("BUSINESS_PACK", "")


settings = Settings()
