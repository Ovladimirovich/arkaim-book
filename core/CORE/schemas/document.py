from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    type: str = Field(pattern=r"^(primary_source|secondary_source|external)$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$", default="1.0.0")
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    path: Optional[str] = None
    chunks_count: int = 0

