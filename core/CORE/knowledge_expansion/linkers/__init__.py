"""
Base Linker — абстрактный базовый класс для связывания с Knowledge Graph.
"""
from abc import ABC, abstractmethod
from ..models import EnrichedKnowledge, LinkedKnowledge


class BaseLinker(ABC):
    """Абстрактный linker для связывания знаний с графом."""

    @abstractmethod
    async def link(self, enriched: list[EnrichedKnowledge]) -> list[LinkedKnowledge]:
        """Связать обогащённые знания с существующим Knowledge Graph."""
        pass
