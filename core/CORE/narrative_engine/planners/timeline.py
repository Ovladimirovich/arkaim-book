"""Timeline Planner — временная согласованность."""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.context_assembler import FullContext
from narrative_engine.constraint_engine import StoryRequest

log = logging.getLogger("hermes.narrative.planners.timeline")


class ChronologicalEvent(BaseModel):
    id: str
    title: str
    epoch: str
    order: int = 0
    description: str = ""


class TimelinePlan(BaseModel):
    events_chronological: list[ChronologicalEvent] = Field(default_factory=list)
    temporal_conflicts: list[str] = Field(default_factory=list)
    character_lifetimes: dict = Field(default_factory=dict)
    safe_period: str = ""


class TimelinePlanner:
    """Проверяет и строит временную согласованность."""

    def __init__(self, world_model: WorldModel):
        self._wm = world_model

    def plan(self, request: StoryRequest, context: FullContext) -> TimelinePlan:
        events = []
        conflicts = []
        lifetimes = {}

        for epoch in self._wm.get_epochs():
            epoch_events = self._wm.get_events(epoch.id)
            for ev in epoch_events:
                events.append(ChronologicalEvent(
                    id=ev.id,
                    title=ev.title_ru,
                    epoch=epoch.name_ru,
                    order=ev.order_in_epoch,
                    description=ev.description[:100] if ev.description else "",
                ))

        epochs_order = {e.id: e.order for e in self._wm.get_epochs()}
        events.sort(key=lambda e: epochs_order.get(e.epoch, 0) * 1000 + e.order)

        conflicts.extend(self._check_temporal_conflicts(events))

        for epoch in self._wm.get_epochs():
            chars = self._wm.get_characters_alive(epoch.id)
            for ch in chars:
                if ch.character_name not in lifetimes:
                    lifetimes[ch.character_name] = []
                lifetimes[ch.character_name].append(epoch.name_ru)

        safe_period = self._determine_safe_period(request, context)

        return TimelinePlan(
            events_chronological=events[:20],
            temporal_conflicts=conflicts,
            character_lifetimes=lifetimes,
            safe_period=safe_period,
        )

    def _check_temporal_conflicts(self, events: list[ChronologicalEvent]) -> list[str]:
        conflicts = []
        seen = set()
        for ev in events:
            key = f"{ev.epoch}:{ev.title}"
            if key in seen:
                conflicts.append(f"Дублирующееся событие: {ev.title} в {ev.epoch}")
            seen.add(key)
        return conflicts

    def _determine_safe_period(
        self, request: StoryRequest, context: FullContext
    ) -> str:
        if request.epoch:
            epoch = self._wm.get_epoch(request.epoch)
            if epoch:
                return f"{epoch.name_ru} (порядок: {epoch.order})"
        return "Любая эпоха"
