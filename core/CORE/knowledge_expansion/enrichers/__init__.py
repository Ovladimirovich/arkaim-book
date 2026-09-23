"""
Base Enricher — абстрактный базовый класс для обогащения знаний.
"""
from abc import ABC, abstractmethod
from ..models import RawKnowledge, EnrichedKnowledge


class BaseEnricher(ABC):
    """Абстрактный enricher для обогащения знаний через LLM."""

    @abstractmethod
    async def enrich(self, raw: list[RawKnowledge]) -> list[EnrichedKnowledge]:
        """Обогатить сырые знания через LLM-анализ."""
        pass
