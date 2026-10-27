"""UnifiedClaim — единая модель утверждения с полным provenance и lineage.

M4: единая модель для всех claim в системе:
  CLAIM
   ├── source        (source_ref, doc_id, chunk_id)
   ├── evidence      (что поддерживает утверждение)
   ├── provenance    (ProvenanceTag: category, source_level, confidence, notes)
   ├── epistemic_status (CANON / DERIVED / EXTERNAL_SOURCE / RECONSTRUCTION /
                          HYPOTHESIS / ARTISTIC_MODEL / FUTURE_EXTRAPOLATION / UNKNOWN)
   ├── confidence    (0.0–1.0)
   └── derived_from  (список claim/evidence ID, от которых выведено)

Инварианты:
  - derived_from пуст для source claims (canon, external, hypothesis, unknown)
  - derived claim не может иметь epistemic_status = AUTHOR_CANON без
    явного owner-confirm (проверяется на уровне модели и реестра)
  - Всякая claim имеет единый детерминированный ID
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)


class ClaimOrigin(str, Enum):
    """Происхождение claim: первичное утверждение или производное."""
    SOURCE = "source"          # Первичное утверждение из источника
    DERIVED = "derived"        # Выведено из других claim/evidence


class UnifiedClaim(BaseModel):
    """Единая модель утверждения с трассировкой происхождения.

    Каждая claim имеет:
      - уникальный ID
      - текст утверждения
      - источник (source_ref, doc_id, chunk_id)
      - evidence (что поддерживает утверждение)
      - provenance (ProvenanceTag)
      - epistemic_status (категория достоверности)
      - confidence (0.0–1.0)
      - derived_from (ID claim/evidence, от которых выведено — пусто для source)
      - связанные сущности мира
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "claim_abc123def456",
                "text": "Аркаим построен потомками гипербореев",
                "source_ref": "book:chunk_p_0042_abc",
                "doc_id": "book_document",
                "chunk_id": "chunk_p_0042_abc",
                "evidence": "Прямая цитата из главы 42 книги",
                "provenance": {
                    "source_level": "CANON",
                    "category": "AUTHOR_CANON",
                    "confidence": 1.0,
                    "notes": "из книги «Наследие Аркаима»",
                },
                "epistemic_status": "AUTHOR_CANON",
                "confidence": 1.0,
                "derived_from": [],
                "entity_ids": ["region_arkaim"],
                "created_by": "book_extractor",
            }
        }
    )

    # ── Identity ─────────────────────────────────────────────────────────

    id: str = Field(default_factory=lambda: f"claim_{uuid4().hex[:12]}")
    """Уникальный ID claim."""

    origin: ClaimOrigin = ClaimOrigin.SOURCE
    """Происхождение: SOURCE (первичное) или DERIVED (выведенное)."""

    # ── Content ──────────────────────────────────────────────────────────

    text: str = Field(min_length=1)
    """Текст утверждения."""

    source_ref: str = ""
    """Ссылка на источник (book:chunk_*, ESOTERIC_CONNECTIONS.json#traditions[0], etc.)."""

    doc_id: Optional[str] = None
    """ID документа-источника."""

    chunk_id: Optional[str] = None
    """ID чанка (для book claims — трассировка до章节/абзаца)."""

    evidence: Optional[str] = None
    """Что поддерживает это утверждение (цитата, ссылка, фрагмент)."""

    # ── Provenance ───────────────────────────────────────────────────────

    provenance: ProvenanceTag
    """Тег provenance: category, source_level, confidence, notes."""

    epistemic_status: ProvenanceCategory
    """Статус достоверности: CANON / DERIVED / EXTERNAL_SOURCE / ... / UNKNOWN."""

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    """Уверенность в утверждении (0.0–1.0)."""

    # ── Lineage ──────────────────────────────────────────────────────────

    derived_from: list[str] = Field(default_factory=list)
    """ID claim/evidence, от которых выведено это утверждение.

    Пуст для source claims. Заполнен для derived/reconstruction claims.
    """

    # ── World Model linkage ─────────────────────────────────────────────

    entity_ids: list[str] = Field(default_factory=list)
    """Связанные сущности мира (WORLD_MODEL IDs)."""

    # ── Metadata ─────────────────────────────────────────────────────────

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    created_by: str = "system"
    notes: Optional[str] = None

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("derived_from")
    @classmethod
    def _derived_from_empty_for_source(cls, v: list[str], info) -> list[str]:
        """Source claims не могут иметь derived_from."""
        origin = info.data.get("origin", ClaimOrigin.SOURCE)
        if origin == ClaimOrigin.SOURCE and len(v) > 0:
            raise ValueError(
                "source claim не может иметь derived_from — "
                "используйте origin=DERIVED для производных утверждений"
            )
        return v

    @field_validator("epistemic_status")
    @classmethod
    def _derived_cannot_be_canon(cls, v: ProvenanceCategory, info) -> ProvenanceCategory:
        """Derived claim не может иметь epistemic_status = AUTHOR_CANON."""
        origin = info.data.get("origin", ClaimOrigin.SOURCE)
        if origin == ClaimOrigin.DERIVED and v == ProvenanceCategory.AUTHOR_CANON:
            raise ValueError(
                "derived claim не может иметь epistemic_status = AUTHOR_CANON. "
                "Используйте DERIVED, RECONSTRUCTION или HYPOTHESIS. "
                "Повышение до CANON требует owner-confirm."
            )
        return v

    @field_validator("confidence")
    @classmethod
    def _confidence_matches_provenance(cls, v: float, info) -> float:
        """Confidence не противоречит provenance confidence."""
        provenance = info.data.get("provenance")
        if provenance is not None and provenance.confidence is not None:
            if abs(v - provenance.confidence) > 0.01:
                raise ValueError(
                    f"claim confidence ({v}) не совпадает с provenance "
                    f"confidence ({provenance.confidence})"
                )
        return v

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def is_canon(self) -> bool:
        """Является ли claim авторским каноном."""
        return self.epistemic_status == ProvenanceCategory.AUTHOR_CANON

    @property
    def is_external(self) -> bool:
        return self.epistemic_status == ProvenanceCategory.EXTERNAL_SOURCE

    @property
    def is_hypothesis(self) -> bool:
        return self.epistemic_status == ProvenanceCategory.HYPOTHESIS

    @property
    def is_derived(self) -> bool:
        return self.epistemic_status == ProvenanceCategory.DERIVED

    @property
    def is_reconstruction(self) -> bool:
        return self.epistemic_status == ProvenanceCategory.RECONSTRUCTION

    @property
    def has_lineage(self) -> bool:
        """Есть ли у claim производная линия (не пустой derived_from)."""
        return len(self.derived_from) > 0

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Сериализовать в dict для API и persistence."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> "UnifiedClaim":
        """Восстановить claim из dict (для миграции legacy данных)."""
        return cls(**data)

    # ── Factory methods ─────────────────────────────────────────────────

    @classmethod
    def make_id(cls, text: str, source_ref: str) -> str:
        """Детерминированный ID по content+source_ref."""
        raw = f"{source_ref}:{text}"
        return f"claim_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    # ── Конвертеры из существующих моделей ───────────────────────────────

    def from_card_claim(
        cls,
        card_claim: "CardClaim",
        source_ref: str = "",
    ) -> "UnifiedClaim":
        """Создать UnifiedClaim из CardClaim (Knowledge Card claim model)."""
        # Deferred import
        from knowledge_card.models import CardClaim as _CC  # noqa: F811

        provenance = card_claim.provenance

        return cls(
            id=cls.make_id(card_claim.text, source_ref or card_claim.source_ref),
            text=card_claim.text,
            source_ref=source_ref or card_claim.source_ref,
            doc_id=None,
            chunk_id=card_claim.chunk_id,
            evidence=card_claim.chapter_title or None,
            provenance=provenance,
            epistemic_status=provenance.category,
            confidence=provenance.confidence,
            derived_from=[],
            entity_ids=[],
            created_at=datetime.now(tz=timezone.utc),
            created_by="knowledge_card",
            notes=card_claim.notes,
        )

    @classmethod
    def from_fact(
        cls,
        fact: "Fact",
    ) -> "UnifiedClaim":
        """Создать UnifiedClaim из Fact (legacy schema model)."""
        # Deferred import
        from schemas.fact import Fact as _F  # noqa: F811

        category = fact.provenance_category()
        provenance = ProvenanceTag(
            source_level=SourceLevel.SYSTEM_INTERPRETATION,
            category=category,
            confidence=fact.confidence,
            source_url=fact.doc_id,
            source_title=fact.entity_id,
            notes=f"legacy_fact:{fact.id}",
        )

        return cls(
            id=fact.id,
            text=fact.statement,
            source_ref=fact.doc_id,
            doc_id=fact.doc_id,
            chunk_id=fact.chunk_id,
            evidence=None,
            provenance=provenance,
            epistemic_status=category,
            confidence=fact.confidence,
            derived_from=[],
            entity_ids=[fact.entity_id],
            created_at=fact.created_at,
            created_by="legacy_fact",
            notes=None,
        )

    @classmethod
    def from_canon_claim(
        cls,
        canon_claim: "CanonClaim",
    ) -> "UnifiedClaim":
        """Создать UnifiedClaim из CanonClaim (M1 model).

        Конвертирует существующий CanonClaim в новую UnifiedClaim модель,
        сохраняя все поля. Архитектурный invariant: AUTHOR_CANON допускается
        только если derived_from пуст (source claim, а не derived).

        Args:
            canon_claim: Существующий CanonClaim из M1 модели.

        Returns:
            UnifiedClaim с теми же данными.

        Raises:
            ValueError: Если attempt convert derived claim to AUTHOR_CANON
                без explicit owner confirmation (was hidden elevation).
        """
        # Обрабатываем derived_from: у CanonClaim может не быть этого поля (M1 модель),
        # поэтому используем getattr с default=[]
        derived_from = getattr(canon_claim, 'derived_from', [])

        # Определяем origin: SOURCE если derived_from пуст, иначе DERIVED
        origin = ClaimOrigin.SOURCE if not derived_from else ClaimOrigin.DERIVED

        # Проверяем архитектурный invariant:
        # AUTHOR_CANON допускается только для source claims (derived_from пуст)
        if (
            canon_claim.category == ProvenanceCategory.AUTHOR_CANON
            and canon_claim.derived_from
        ):
            raise ValueError(
                f"Cannot convert CanonClaim with AUTHOR_CANON category "
                f"and non-empty derived_from. "
                f"This would be hidden elevation of derived claim to CANON. "
                f"derived_from={canon_claim.derived_from}"
            )

        # Определяем provenance category
        provenance_category = canon_claim.category

        # Создаем ProvenanceTag
        provenance = ProvenanceTag(
            source_level=SourceLevel.CANON
            if provenance_category == ProvenanceCategory.AUTHOR_CANON
            else SourceLevel.SYSTEM_INTERPRETATION,
            category=provenance_category,
            confidence=canon_claim.confidence,
            notes=canon_claim.notes or "",
        )

        # Обрабатываем derived_from: у CanonClaim может не быть этого поля (M1 модель),
# поэтому используем getattr с default=[]
        derived_from = getattr(canon_claim, 'derived_from', [])

        # Архитектурный invariant: AUTHOR_CANON допускается только для source claims
        # (derived_from пуст). Если derived_from非空 и category AUTHOR_CANON —
        # это попытка скрытого повышения статуса, что запрещено.
        if (
            canon_claim.category == ProvenanceCategory.AUTHOR_CANON
            and derived_from
        ):
            raise ValueError(
                f"Cannot convert CanonClaim with AUTHOR_CANON category "
                f"and non-empty derived_from. "
                f"This would be hidden elevation of derived claim to CANON. "
                f"derived_from={derived_from}"
            )

        # Детерминированный ID на основе текста и source_id
        claim_id = cls.make_id(canon_claim.text, canon_claim.source_id)

        return cls(
            id=claim_id,
            text=canon_claim.text,
            source_ref=canon_claim.source_id or "",
            doc_id=canon_claim.source_id or "",
            chunk_id=None,
            evidence=canon_claim.source_location or "",
            provenance=provenance,
            epistemic_status=provenance_category,
            confidence=canon_claim.confidence,
            derived_from=derived_from,
            entity_ids=list(canon_claim.entity_ids) if canon_claim.entity_ids else [],
            created_at=canon_claim.created_at,
            created_by=canon_claim.created_by,
            notes=canon_claim.notes,
        )

    def to_canon_claim(self) -> "CanonClaim":
        """Преобразовать UnifiedClaim обратно в CanonClaim (M1 model).

        Возвращает None, если claim не является canon (нельзя потерять
        derived_from и epistemic_status при обратном преобразовании).
        """
        from narrative_engine.provenance.claim import CanonClaim as _CC  # noqa: F811

        if self.epistemic_status != ProvenanceCategory.AUTHOR_CANON:
            raise ValueError(
                f"Нельзя преобразовать claim с epistemic_status="
                f"{self.epistemic_status.value} в CanonClaim. "
                "CanonClaim допускает только AUTHOR_CANON."
            )

        return CanonClaim(
            id=self.id,
            text=self.text,
            source_id=self.source_ref,
            source_location=self.evidence or "",
            category=self.epistemic_status,
            confidence=self.confidence,
            entity_ids=list(self.entity_ids),
            created_at=self.created_at,
            created_by=self.created_by,
            notes=self.notes,
        )

