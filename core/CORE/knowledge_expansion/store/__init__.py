"""
Base Store — абстрактный базовый класс для хранения знаний.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from ..models import ValidatedKnowledge, SaveResult


class BaseStore(ABC):
    """Абстрактный store для сохранения знаний."""

    @abstractmethod
    async def save(self, validated: list[ValidatedKnowledge], output_path: Path) -> SaveResult:
        """Сохранить знания и обновить граф."""
        pass
