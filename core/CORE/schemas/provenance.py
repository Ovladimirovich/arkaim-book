from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    fact_id: str
    type: str = Field(pattern=r"^(source|derived|interpretation|external|hypothesis)$")
    label: str
    doc_id: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
