"""
Knowledge Card — entity-centric view aggregating knowledge from multiple sources
while preserving provenance and epistemic distinctions.

The card answers: "What does the system know about this entity, and from which sources?"
"""
from __future__ import annotations

from .models import (
    KnowledgeCard,
    CardClaim,
    SourceAggregation,
    ContradictionNote,
    CardMetadata,
)
from .builder import KnowledgeCardBuilder, get_card_builder

__all__ = [
    "KnowledgeCard",
    "CardClaim",
    "SourceAggregation",
    "ContradictionNote",
    "CardMetadata",
    "KnowledgeCardBuilder",
    "get_card_builder",
]
