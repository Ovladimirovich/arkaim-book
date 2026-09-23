from __future__ import annotations

from typing import Dict
from uuid import uuid4

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    doc_id: str
    text: str
    position: int = Field(ge=0)
    metadata: Dict = Field(default_factory=dict)
