"""Абстрактный шаблон промпта."""
from __future__ import annotations
from abc import ABC, abstractmethod


class PromptTemplate(ABC):
    """Базовый шаблон для генерации промптов."""

    @abstractmethod
    def render(self, ctx) -> str:
        """VisualContext → промпт."""

    @abstractmethod
    def render_negative(self, ctx) -> str:
        """VisualContext → negative prompt."""
