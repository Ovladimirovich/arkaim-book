"""Conflict Planner — драматическое напряжение."""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.context_assembler import FullContext
from narrative_engine.constraint_engine import StoryRequest

log = logging.getLogger("hermes.narrative.planners.conflict")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


class ConflictArc(BaseModel):
    conflict_type: str  # "internal" | "external" | "moral"
    tension_source: str = ""
    stakes: str = ""
    arc_structure: list[str] = Field(default_factory=list)
    resolution_options: list[str] = Field(default_factory=list)


class ConflictPlanner:
    """Строит конфликтные дуги для истории."""

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._genome = self._load_genome()

    def _load_genome(self) -> dict:
        genome_path = Path(__file__).resolve().parent.parent.parent.parent / "GENOME" / "GENOME_v1.0.0.json"
        if genome_path.exists():
            try:
                return json.loads(genome_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def plan(self, request: StoryRequest, context: FullContext) -> list[ConflictArc]:
        conflicts = []

        genome_conflicts = self._genome.get("modules", {}).get("conflicts", [])
        for conf in genome_conflicts[:3]:
            arc = self._build_arc_from_genome(conf, request)
            if arc:
                conflicts.append(arc)

        if not conflicts:
            conflicts.append(self._create_default_conflict(request, context))

        return conflicts

    def _build_arc_from_genome(self, conf: dict, request: StoryRequest) -> Optional[ConflictArc]:
        name = conf.get("name", "")
        description = conf.get("description", "")

        if any(kw in name.lower() for kw in ["война", "битва", "столкновение"]):
            ctype = "external"
        elif any(kw in name.lower() for kw in ["дилемма", "выбор", "сомнени"]):
            ctype = "moral"
        else:
            ctype = "internal"

        return ConflictArc(
            conflict_type=ctype,
            tension_source=name,
            stakes=description[:200] if description else "",
            arc_structure=[
                f"Завязка: {name} обостряется",
                "Развитие: персонажи сталкиваются с последствиями",
                "Кульминация: точка невозврата",
                "Развязка: преодоление через понимание",
            ],
            resolution_options=[
                "Через духовное развитие",
                "Через единство и сотрудничество",
                "Через жертвенность",
            ],
        )

    def _create_default_conflict(
        self, request: StoryRequest, context: FullContext
    ) -> ConflictArc:
        return ConflictArc(
            conflict_type="internal",
            tension_source="Путь познания и самопреодоления",
            stakes="Духовное развитие героя и его способность служить другим",
            arc_structure=[
                "Завязка: герой сталкивается с вызовом",
                "Развитие: через испытания обретает понимание",
                "Кульминация: осознание глубинной истины",
                "Развязка: трансформация и возвращение с даром",
            ],
            resolution_options=[
                "Через познание себя",
                "Через связь с учителем",
                "Через служение другим",
            ],
        )
