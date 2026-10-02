"""Evidence contract for traceable Knowledge Core claims."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from narrative_engine.source_levels import ProvenanceCategory, ProvenanceTag


class EvidenceStatus(str, Enum):
    """Lifecycle status of a claim→evidence reference.

    Distinct from claim provenance: it describes whether the referenced
    fragment can currently be reached, not whether the claim is true.

      * ``RESOLVED``    — locator reaches the fragment and version/hash matches.
      * ``UNAVAILABLE`` — checked, but the fragment cannot be reached now.
      * ``UNKNOWN``     — reference not verified / cannot be verified.
      * ``SUPERSEDED``  — fragment changed; a newer reference replaces this one.
    """

    RESOLVED = "RESOLVED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    SUPERSEDED = "SUPERSEDED"


class Evidence(BaseModel):
    """A resolvable fragment or locator in a registered source.

    Evidence is not a claim and does not alter claim provenance. It identifies
    material from which one or more claims may have been extracted.
    """

    id: str
    source_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    text: Optional[str] = None
    content_hash: Optional[str] = Field(default=None, min_length=1)
    source_version: Optional[str] = None
    provenance: Optional[ProvenanceTag] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @model_validator(mode="after")
    def validate_locator(self) -> "Evidence":
        if not self.locator.strip():
            raise ValueError("evidence locator must not be empty")
        return self

    @classmethod
    def make_id(cls, source_id: str, locator: str, content_hash: str | None = None) -> str:
        raw = f"{source_id}:{locator}:{content_hash or ''}"
        return f"evidence_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

    @classmethod
    def from_locator(
        cls,
        *,
        source_id: str,
        source_type: str,
        locator: str,
        text: str | None = None,
        source_version: str | None = None,
        provenance: ProvenanceTag | None = None,
        metadata: dict | None = None,
    ) -> "Evidence":
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None
        return cls(
            id=cls.make_id(source_id, locator, content_hash),
            source_id=source_id,
            source_type=source_type,
            locator=locator,
            text=text,
            content_hash=content_hash,
            source_version=source_version,
            provenance=provenance,
            metadata=metadata or {},
        )

    @classmethod
    def from_chunk(cls, chunk: dict, *, source_id: str | None = None, source_type: str = "book") -> "Evidence":
        """Adapt existing RAG chunk data without changing its retrieval semantics."""
        metadata = dict(chunk.get("metadata") or {})
        locator = str(chunk.get("chunk_id") or metadata.get("id") or "")
        if not locator:
            raise ValueError("chunk has no resolvable chunk_id/id locator")
        return cls.from_locator(
            source_id=source_id or str(chunk.get("source") or metadata.get("source") or source_type),
            source_type=source_type,
            locator=locator,
            text=chunk.get("text"),
            provenance=None,
            metadata={
                "chapter_title": chunk.get("chapter_title", metadata.get("chapter_title", "")),
                "chapter_number": chunk.get("chapter_number", metadata.get("chapter_number", -1)),
                "paragraph_id": chunk.get("paragraph_id", metadata.get("paragraph_id", "")),
                "char_start": chunk.get("char_start", metadata.get("char_start", -1)),
                "char_end": chunk.get("char_end", metadata.get("char_end", -1)),
            },
        )


class ClaimEvidenceLink(BaseModel):
    """Explicit relation between a canonical claim and an evidence object.

    A link is also the unit of evidence lifecycle tracking. It records the
    expected content hash / source version of the referenced fragment, so that a
    later re-check can distinguish "still valid" from "changed" or "gone"
    without deleting either the claim or the evidence.
    """

    claim_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    relation: str = Field(default="supports", min_length=1)
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # --- lifecycle (M2 broken/missing reference handling) ---
    link_id: str = ""
    status: EvidenceStatus = EvidenceStatus.RESOLVED
    reason: str = ""
    source_id: str = ""
    locator: str = ""
    expected_content_hash: Optional[str] = None
    expected_source_version: Optional[str] = None
    supersedes_link_id: Optional[str] = None
    checked_at: Optional[datetime] = None

    @classmethod
    def make_link_id(cls, claim_id: str, evidence_id: str, relation: str = "supports") -> str:
        raw = f"{claim_id}:{evidence_id}:{relation}"
        return f"link_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

    @model_validator(mode="after")
    def validate_ids(self) -> "ClaimEvidenceLink":
        if not self.claim_id.strip() or not self.evidence_id.strip():
            raise ValueError("claim_id and evidence_id must be non-empty")
        if not self.link_id.strip():
            self.link_id = self.make_link_id(self.claim_id, self.evidence_id, self.relation)
        return self


__all__ = ["Evidence", "ClaimEvidenceLink", "EvidenceStatus", "ProvenanceCategory"]
