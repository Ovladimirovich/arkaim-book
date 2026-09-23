from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


RELATIONSHIP_TYPES = [
    "teacher_student", "friend", "belongs_to", "located_in",
    "symbolizes", "opposes", "predecessor_of", "created_by",
    "origin", "brotherhood", "cycle", "structure", "founder",
    "legacy", "civilization_link",
    "embodies", "related_to", "conflicts_with",
]


class Relationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    target_id: str
    type: str = Field(
        pattern=r"^(teacher_student|friend|belongs_to|located_in|"
                r"symbolizes|opposes|predecessor_of|created_by|"
                r"origin|brotherhood|cycle|structure|founder|"
                r"legacy|civilization_link|"
                r"embodies|related_to|conflicts_with)$"
    )
    doc_id: str = "genome"
    description: str = ""
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
