from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


PROVENANCE_TYPES = [
    "source", "derived", "interpretation", "external", "hypothesis", "genome",
]


class Fact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str = Field(min_length=1)
    entity_id: str
    doc_id: str
    chunk_id: Optional[str] = None
    provenance: str = Field(pattern=r"^(source|derived|interpretation|external|hypothesis|genome)$")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
