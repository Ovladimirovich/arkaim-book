"""World State Builder — построение снимка состояния мира для конкретной эпохи."""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel

log = logging.getLogger("hermes.narrative.world_state")


class CharacterState(BaseModel):
    name: str
    status: str  # alive, awakened, departed, mythic
    location: Optional[str] = None
    relationships: list[str] = Field(default_factory=list)
    known_facts: list[str] = Field(default_factory=list)
    notes: str = ""


class LocationState(BaseModel):
    id: str
    name_ru: str
    type: str
    description: str = ""
    characters_present: list[str] = Field(default_factory=list)


class Technology(BaseModel):
    id: str
    name_ru: str
    description: str = ""


class CanonicalEvent(BaseModel):
    id: str
    title_ru: str
    description: str = ""
    order_in_epoch: int = 0


class CausalRule(BaseModel):
    id: str
    description: str
    rule_type: str


class WorldState(BaseModel):
    """Снимок состояния мира для конкретной эпохи."""
    epoch_id: str
    epoch_name_ru: str
    active_characters: list[CharacterState] = Field(default_factory=list)
    available_locations: list[LocationState] = Field(default_factory=list)
    technologies: list[Technology] = Field(default_factory=list)
    events_happened: list[CanonicalEvent] = Field(default_factory=list)
    events_pending: list[CanonicalEvent] = Field(default_factory=list)
    active_rules: list[CausalRule] = Field(default_factory=list)
    civilization_state: dict = Field(default_factory=dict)


class WorldStateBuilder:
    """Строит WorldState для запрошенной эпохи."""

    def __init__(self, world_model: WorldModel):
        self._wm = world_model

    def build(self, epoch_id: Optional[str] = None) -> WorldState:
        if not epoch_id:
            epochs = self._wm.get_epochs()
            if epochs:
                epoch_id = epochs[0].id
            else:
                return WorldState(epoch_id="unknown", epoch_name_ru="Неизвестная эпоха")

        epoch = self._wm.get_epoch(epoch_id)
        epoch_name = epoch.name_ru if epoch else epoch_id

        characters = []
        for presence in self._wm.get_characters_alive(epoch_id):
            characters.append(CharacterState(
                name=presence.character_name,
                status=presence.status,
                location=presence.location_id,
                notes=presence.notes,
            ))

        locations = []
        for loc in self._wm.get_locations(epoch_id):
            chars_here = [
                c.name for c in characters
                if c.location == loc.id
            ]
            locations.append(LocationState(
                id=loc.id,
                name_ru=loc.name_ru,
                type=loc.type,
                description=loc.description,
                characters_present=chars_here,
            ))

        technologies = []
        for tech in self._wm.get_technologies(epoch_id):
            technologies.append(Technology(
                id=tech.id,
                name_ru=tech.name_ru,
                description=tech.description,
            ))

        all_events = self._wm.get_events(epoch_id)
        events_happened = []
        events_pending = []
        for ev in all_events:
            ce = CanonicalEvent(
                id=ev.id,
                title_ru=ev.title_ru,
                description=ev.description,
                order_in_epoch=ev.order_in_epoch,
            )
            if ev.order_in_epoch < 50:
                events_happened.append(ce)
            else:
                events_pending.append(ce)

        rules = [
            CausalRule(
                id=r.id,
                description=r.description,
                rule_type=r.rule_type,
            )
            for r in self._wm.get_rules()
        ]

        return WorldState(
            epoch_id=epoch_id,
            epoch_name_ru=epoch_name,
            active_characters=characters,
            available_locations=locations,
            technologies=technologies,
            events_happened=events_happened,
            events_pending=events_pending,
            active_rules=rules,
        )
