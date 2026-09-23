"""CanonClaim — атомарное утверждение с трассировкой до источника.

M1: каждый факт в системе может быть прослежен до:
  Claim → Source → Location (chapter/paragraph)

Claim — это минимальная единица авторского утверждения.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag, SourceLevel


@dataclass
class CanonClaim:
    """Атомарное утверждение из авторского источника.

    Каждая claim имеет:
      - уникальный ID (детерминированный по content+source)
      - текст утверждения
      - источник и точное местоположение
      - категорию provenance
      - уверенность
      - связанные сущности мира
      - временную метку создания
    """

    # ── Identity ─────────────────────────────────────────────────────────

    id: str
    """Уникальный ID claim."""

    # ── Content ──────────────────────────────────────────────────────────

    text: str
    """Текст утверждения."""

    source_id: str
    """ID источника (см. SourceHierarchy)."""

    source_location: str
    """Точное местоположение в источнике.

    Формат: "chapter:N paragraph:M" или "page:P line:L"
    """

    category: ProvenanceCategory
    """Категория происхождения (M1)."""

    confidence: float
    """Уверенность в утверждении (0.0–1.0)."""

    # ── World Model linkage ─────────────────────────────────────────────

    entity_ids: list[str] = field(default_factory=list)
    """Связанные сущности мира (WORLD_MODEL IDs)."""

    epoch_ids: list[str] = field(default_factory=list)
    """Связанные эпохи."""

    character_ids: list[str] = field(default_factory=list)
    """Связанные персонажи."""

    # ── Metadata ────────────────────────────────────────────────────────

    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    created_by: str = "system"
    provenance_tags: list[ProvenanceTag] = field(default_factory=list)
    notes: Optional[str] = None

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def is_canon(self) -> bool:
        """Является ли claim авторским каноном."""
        return self.category == ProvenanceCategory.AUTHOR_CANON

    @property
    def is_external(self) -> bool:
        return self.category == ProvenanceCategory.EXTERNAL_SOURCE

    @property
    def is_hypothesis(self) -> bool:
        return self.category == ProvenanceCategory.HYPOTHESIS

    @property
    def is_derived(self) -> bool:
        return self.category == ProvenanceCategory.DERIVED

    @property
    def is_reconstruction(self) -> bool:
        return self.category == ProvenanceCategory.RECONSTRUCTION

    # ── Factory methods ──────────────────────────────────────────────────

    @staticmethod
    def make_id(text: str, source_id: str, location: str) -> str:
        """Детерминированный ID по content+source+location."""
        raw = f"{source_id}:{location}:{text}"
        return f"claim_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    @classmethod
    def from_canon(
        cls,
        text: str,
        source_id: str,
        location: str,
        entity_ids: Optional[list[str]] = None,
        epoch_ids: Optional[list[str]] = None,
        character_ids: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> "CanonClaim":
        """Создать claim из канонического источника."""
        claim_id = cls.make_id(text, source_id, location)
        return cls(
            id=claim_id,
            text=text,
            source_id=source_id,
            source_location=location,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
            entity_ids=entity_ids or [],
            epoch_ids=epoch_ids or [],
            character_ids=character_ids or [],
            notes=notes,
            created_by="extractor",
        )

    @classmethod
    def from_external(
        cls,
        text: str,
        source_id: str,
        location: str,
        confidence: float = 0.7,
        entity_ids: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> "CanonClaim":
        """Создать claim из внешнего источника."""
        claim_id = cls.make_id(text, source_id, location)
        return cls(
            id=claim_id,
            text=text,
            source_id=source_id,
            source_location=location,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=confidence,
            entity_ids=entity_ids or [],
            notes=notes,
            created_by="external_source",
        )

    @classmethod
    def from_hypothesis(
        cls,
        text: str,
        source_id: str,
        location: str,
        confidence: float = 0.5,
        entity_ids: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> "CanonClaim":
        """Создать claim-гипотезу."""
        claim_id = cls.make_id(text, source_id, location)
        return cls(
            id=claim_id,
            text=text,
            source_id=source_id,
            source_location=location,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=confidence,
            entity_ids=entity_ids or [],
            notes=notes,
            created_by="hypothesis_engine",
        )

    @classmethod
    def from_reconstruction(
        cls,
        text: str,
        source_id: str,
        location: str,
        confidence: float = 0.7,
        entity_ids: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> "CanonClaim":
        """Создать claim-реконструкцию."""
        claim_id = cls.make_id(text, source_id, location)
        return cls(
            id=claim_id,
            text=text,
            source_id=source_id,
            source_location=location,
            category=ProvenanceCategory.RECONSTRUCTION,
            confidence=confidence,
            entity_ids=entity_ids or [],
            notes=notes,
            created_by="reconstruction_engine",
        )

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "source_id": self.source_id,
            "source_location": self.source_location,
            "category": self.category.value,
            "confidence": self.confidence,
            "entity_ids": self.entity_ids,
            "epoch_ids": self.epoch_ids,
            "character_ids": self.character_ids,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CanonClaim":
        """Восстановить claim из dict (для миграции)."""
        cat_val = data.get("category", "UNKNOWN")
        category = ProvenanceCategory(cat_val)
        return cls(
            id=data["id"],
            text=data["text"],
            source_id=data["source_id"],
            source_location=data.get("source_location", ""),
            category=category,
            confidence=data.get("confidence", 0.5),
            entity_ids=data.get("entity_ids", []),
            epoch_ids=data.get("epoch_ids", []),
            character_ids=data.get("character_ids", []),
            notes=data.get("notes"),
            created_by=data.get("created_by", "system"),
        )
