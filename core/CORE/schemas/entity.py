from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


ENTITY_TYPES = [
    "person", "location", "civilization", "concept",
    "symbol", "artifact", "era", "event", "organization",
    "character", "theme", "conflict", "value",
]


class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    type: str = Field(pattern=r"^(person|location|civilization|concept|symbol|artifact|era|event|organization|character|theme|conflict|value)$")
    aliases: List[str] = Field(default_factory=list)
    description: str = ""
    first_seen: Optional[str] = None
