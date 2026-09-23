"""
Pydantic models for Knowledge Card — entity-centric structured knowledge.

Design principles:
- Claim-level provenance (each claim has its own provenance)
- Cross-source aggregation without epistemic blending
- Contradictions preserved as data, not resolved
- Uncertainty explicit, not hidden
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag


class CardClaim(BaseModel):
    """Утверждение о сущности с заявленным provenance."""

    text: str
    provenance: ProvenanceTag
    source_ref: str = ""          # "book:chunk_p_0001_xxx", "archaeology:sites[0]", etc.
    chunk_id: Optional[str] = None  # For book claims — traceable to source location
    chapter_title: Optional[str] = None
    notes: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Аркаим построен потомками гипербореев",
                "provenance": {
                    "source_level": "CANON",
                    "category": "AUTHOR_CANON",
                    "confidence": 1.0,
                    "notes": "from GENOME: Аркаим",
                },
                "source_ref": "book:chunk_p_0042_abc",
                "chunk_id": "chunk_p_0042_abc",
                "chapter_title": "Часть 3",
            }
        }


class SourceAggregation(BaseModel):
    """Агрегация из одного источника с claims и metadata."""

    source_name: str              # "book", "archaeology", "cross_references", "academic"
    provenance_category: ProvenanceCategory
    claim_count: int = 0
    claims: list[CardClaim] = Field(default_factory=list)
    summary: str = ""             # One-line summary of what this source says
    confidence: float = 0.0       # Aggregate confidence for this source
    raw_refs: list[dict] = Field(default_factory=list)  # Raw data references

    class Config:
        json_schema_extra = {
            "example": {
                "source_name": "archaeology",
                "provenance_category": "EXTERNAL_SOURCE",
                "claim_count": 3,
                "summary": "Археологические данные подтверждают городище ~4000 до н.э.",
                "confidence": 0.8,
            }
        }


class ContradictionNote(BaseModel):
    """Запись о конфликте между утверждениями из разных источников."""

    description: str
    involved_claims: list[str] = Field(default_factory=list)
    source_1_claim: str
    source_2_claim: str
    resolution: str = "UNRESOLVED"

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Книга связывает Аркаим с гипербореями, археология этого не подтверждает",
                "source_1_claim": "AUTHOR_CANON: Аркаим — потомки Океании",
                "source_2_claim": "EXTERNAL_SOURCE: нет данных о связи с гипербореями",
                "resolution": "DIFFERENT_PERSPECTIVES",
            }
        }


class CardMetadata(BaseModel):
    """Метаданные карточки."""

    entity_id: str
    entity_name: str
    source: str = "knowledge_card"
    version: str = "1.0.0"
    created_at: str = ""
    coverage_note: str = ""       # Описание покрытия знаниями

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "region_arkaim",
                "entity_name": "Аркаим",
                "coverage_note": "Данные из книги, археологии и академических источников",
            }
        }


class KnowledgeCard(BaseModel):
    """
    Entity-centric knowledge card.

    Aggregates claims from multiple sources while preserving provenance.
    Does NOT resolve contradictions — shows them as data.
    """

    metadata: CardMetadata
    primary_entity: Optional[dict] = None   # From WorldEngine if found
    sources: list[SourceAggregation] = Field(default_factory=list)
    relations: list[dict] = Field(default_factory=list)  # From RelationGraph
    contradictions: list[ContradictionNote] = Field(default_factory=list)
    uncertainty: Optional[dict] = None      # From UncertaintyFlag or manual
    search_suggestions: list[str] = Field(default_factory=list)
    related_entities: list[dict] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to plain dict for API response."""
        return self.model_dump(mode="json")

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {"entity_id": "region_arkaim", "entity_name": "Аркаим"},
                "sources": [
                    {
                        "source_name": "book",
                        "provenance_category": "AUTHOR_CANON",
                        "claim_count": 2,
                        "summary": "Книга описывает Аркаим как древнее городище",
                        "confidence": 1.0,
                    },
                    {
                        "source_name": "archaeology",
                        "provenance_category": "EXTERNAL_SOURCE",
                        "claim_count": 3,
                        "summary": "Археология подтверждает городище ~4000 до н.э.",
                        "confidence": 0.8,
                    },
                ],
                "contradictions": [
                    {
                        "description": "Книга связывает с гипербореями, археология молчит",
                        "source_1_claim": "AUTHOR_CANON: связь с гипербореями",
                        "source_2_claim": "EXTERNAL_SOURCE: нет данных",
                        "resolution": "DIFFERENT_PERSPECTIVES",
                    }
                ],
            }
        }
