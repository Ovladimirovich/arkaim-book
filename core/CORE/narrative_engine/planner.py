"""Unified Planner — оркестратор всех планировщиков."""

import logging

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.context_assembler import FullContext
from narrative_engine.constraint_engine import StoryRequest
from narrative_engine.planners.cause_effect import CauseEffectPlanner, CauseEffectTree
from narrative_engine.planners.character import CharacterPlanner, CharacterArc
from narrative_engine.planners.timeline import TimelinePlanner, TimelinePlan
from narrative_engine.planners.conflict import ConflictPlanner, ConflictArc

log = logging.getLogger("hermes.narrative.planner")


class NarrativePlan(BaseModel):
    """Полный план повествования."""
    cause_effect: CauseEffectTree = Field(default_factory=CauseEffectTree)
    character_arcs: list[CharacterArc] = Field(default_factory=list)
    timeline: TimelinePlan = Field(default_factory=TimelinePlan)
    conflicts: list[ConflictArc] = Field(default_factory=list)
    story_structure: list[str] = Field(default_factory=list)
    constraints_for_llm: list[str] = Field(default_factory=list)


class UnifiedPlanner:
    """
    Оркестратор планировщиков.

    Использование:
        planner = UnifiedPlanner(world_model)
        narrative_plan = planner.plan(story_request, full_context)
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._cause_effect = CauseEffectPlanner(world_model)
        self._character = CharacterPlanner(world_model)
        self._timeline = TimelinePlanner(world_model)
        self._conflict = ConflictPlanner(world_model)

    def plan(self, request: StoryRequest, context: FullContext) -> NarrativePlan:
        log.info("planning_start prompt=%s", request.prompt[:50])

        cause_effect = self._cause_effect.plan(request, context)
        log.info("cause_effect_done nodes=%d", len(cause_effect.nodes))

        character_arcs = self._character.plan(request, context)
        log.info("character_arcs_done arcs=%d", len(character_arcs))

        timeline = self._timeline.plan(request, context)
        log.info("timeline_done events=%d conflicts=%d",
                 len(timeline.events_chronological),
                 len(timeline.temporal_conflicts))

        conflicts = self._conflict.plan(request, context)
        log.info("conflict_done arcs=%d", len(conflicts))

        story_structure = self._build_story_structure(
            cause_effect, character_arcs, timeline, conflicts
        )

        constraints_for_llm = self._build_llm_constraints(
            cause_effect, character_arcs, timeline, conflicts
        )

        return NarrativePlan(
            cause_effect=cause_effect,
            character_arcs=character_arcs,
            timeline=timeline,
            conflicts=conflicts,
            story_structure=story_structure,
            constraints_for_llm=constraints_for_llm,
        )

    def _build_story_structure(
        self,
        cause_effect: CauseEffectTree,
        character_arcs: list[CharacterArc],
        timeline: TimelinePlan,
        conflicts: list[ConflictArc],
    ) -> list[str]:
        structure = []

        if timeline.events_chronological:
            first_event = timeline.events_chronological[0]
            structure.append(f"Экспозиция: {first_event.title} ({first_event.epoch})")

        if conflicts:
            structure.append(f"Завязка: {conflicts[0].tension_source}")

        if character_arcs:
            for arc in character_arcs[:2]:
                structure.append(f"Развитие: {arc.character} — {arc.motivation}")

        if cause_effect.nodes:
            climax_nodes = [n for n in cause_effect.nodes if n.type == "effect"]
            if climax_nodes:
                structure.append(f"Кульминация: {climax_nodes[0].description[:100]}")

        structure.append("Развязка: трансформация и возвращение с даром")

        return structure

    def _build_llm_constraints(
        self,
        cause_effect: CauseEffectTree,
        character_arcs: list[CharacterArc],
        timeline: TimelinePlan,
        conflicts: list[ConflictArc],
    ) -> list[str]:
        constraints = []

        for node in cause_effect.nodes:
            if node.type == "world_change":
                constraints.append(f"Ограничение: {node.description}")

        for conflict in timeline.temporal_conflicts:
            constraints.append(f"Временной конфликт: {conflict}")

        for arc in character_arcs:
            if arc.obstacle:
                constraints.append(f"Препятствие для {arc.character}: {arc.obstacle}")

        if cause_effect.matched_pattern:
            constraints.append(f"Следовать паттерну: {cause_effect.matched_pattern}")

        return constraints
