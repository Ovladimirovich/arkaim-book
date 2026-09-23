"""
Base Validator — абстрактный базовый класс для валидации знаний.
"""
from abc import ABC, abstractmethod
from ..models import LinkedKnowledge, ValidatedKnowledge


class BaseValidator(ABC):
    """Абстрактный validator для проверки качества знаний."""

    @abstractmethod
    async def validate(self, linked: list[LinkedKnowledge]) -> list[ValidatedKnowledge]:
        """Проверить качество и формат знаний."""
        pass
