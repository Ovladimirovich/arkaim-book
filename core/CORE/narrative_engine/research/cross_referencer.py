"""Cross Referencer — классификация и скоринг находок."""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from narrative_engine.source_levels import SourceLevel, ProvenanceTag
from narrative_engine.research.entity_extractor import ExtractedEntity
from narrative_engine.research.source_searcher import ExternalSource

log = logging.getLogger("hermes.narrative.cross_referencer")


class ResearchFinding(BaseModel):
    id: str
    entity: ExtractedEntity
    external_sources: list[ExternalSource] = Field(default_factory=list)
    suggested_fact: Optional[dict] = None
    source_level: SourceLevel = SourceLevel.SYSTEM_INTERPRETATION
    confidence: float = 0.5


def classify_finding(entity: ExtractedEntity,
                     sources: list[ExternalSource]) -> ResearchFinding:
    """Классифицировать находку и определить уровень источника."""
    # Определяем уровень источника по типу
    source_type_map = {
        "archaeological": SourceLevel.HISTORICAL,
        "historical": SourceLevel.HISTORICAL,
        "academic": SourceLevel.SCIENTIFIC,
        "mythological": SourceLevel.MYTHOLOGICAL,
        "web": SourceLevel.SYSTEM_INTERPRETATION,
    }

    # Берём наиболее авторитетный уровень
    best_level = SourceLevel.SYSTEM_INTERPRETATION
    best_score = 0.0
    for src in sources:
        level = source_type_map.get(src.source_type, SourceLevel.SYSTEM_INTERPRETATION)
        if src.relevance_score > best_score:
            best_score = src.relevance_score
            best_level = level

    # Генерируем suggested fact
    suggested_fact = {
        "entity_type": entity.entity_type,
        "entity_name": entity.name,
        "description": f"Информация о {entity.name} из {len(sources)} источников.",
        "source_level": best_level.value,
    }

    return ResearchFinding(
        id=f"finding_{entity.name.lower().replace(' ', '_')}",
        entity=entity,
        external_sources=sources,
        suggested_fact=suggested_fact,
        source_level=best_level,
        confidence=best_score,
    )
