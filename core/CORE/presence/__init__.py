"""
Presence — книга наблюдает за сообществом и предлагает автору действия.

Книга «замечает», что обсуждают читатели, какие темы набирают вес,
и предлагает автору: «эту тему стоит осветить».

Никаких автономных действий — только предложения.
(Принцип 11: Автономия = 0 по умолчанию)
"""
from .observer import PresenceObserver
from .suggester import PresenceSuggester, AuthorSuggestion
from . import api_routes

__all__ = ["PresenceObserver", "PresenceSuggester", "AuthorSuggestion"]
