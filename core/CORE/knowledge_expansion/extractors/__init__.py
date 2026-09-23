"""
Base Extractor — абстрактный базовый класс для извлечения знаний.
"""
from abc import ABC, abstractmethod
from typing import Any
from ..models import RawKnowledge


class BaseExtractor(ABC):
    """Абстрактный extractor для извлечения сырых знаний."""

    @abstractmethod
    async def extract(self, source: Any) -> list[RawKnowledge]:
        """Извлечь сырые знания из источника."""
        pass
