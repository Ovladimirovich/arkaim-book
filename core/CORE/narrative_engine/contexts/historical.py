"""Historical Context — исторический контекст для эпохи."""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel

log = logging.getLogger("hermes.narrative.contexts.historical")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


class ContextFact(BaseModel):
    text: str
    source_level: str = "CANON"
    confidence: float = 0.9
    source_file: str = ""


class CulturalParallel(BaseModel):
    culture: str
    source: str
    detail: str


class AcademicSource(BaseModel):
    title: str
    source_level: str = "SCIENTIFIC"
    detail: str = ""


class HistoricalContext(BaseModel):
    epoch_facts: list[ContextFact] = Field(default_factory=list)
    parallels: list[CulturalParallel] = Field(default_factory=list)
    academic_sources: list[AcademicSource] = Field(default_factory=list)
    timeline_position: str = ""


class HistoricalContextBuilder:
    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._cosmology = self._load("COSMOLOGY.json")
        self._philosophy = self._load("PHILOSOPHY_DEEP.json")
        self._cross_refs = self._load("CROSS_REFERENCES.json")
        self._academic = self._load("ACADEMIC_CONFIRMATIONS.json")

    def _load(self, filename: str) -> dict:
        path = KNOWLEDGE_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def build(self, epoch_id: Optional[str] = None) -> HistoricalContext:
        if not epoch_id:
            return HistoricalContext()

        epoch = self._wm.get_epoch(epoch_id)
        if not epoch:
            return HistoricalContext()

        facts = []
        facts.append(ContextFact(
            text=f"Эпоха: {epoch.name_ru}. {epoch.description}",
            source_level="CANON",
            confidence=1.0,
        ))

        techs = self._wm.get_technologies(epoch_id)
        if techs:
            tech_text = "Технологии: " + ", ".join(t.name_ru for t in techs[:5])
            facts.append(ContextFact(text=tech_text, source_level="SYSTEM_INTERPRETATION"))

        events = self._wm.get_events(epoch_id)
        for ev in events[:5]:
            facts.append(ContextFact(
                text=f"Событие: {ev.title_ru}. {ev.description}",
                source_level=ev.source_level.value if hasattr(ev.source_level, 'value') else str(ev.source_level),
            ))

        parallels = []
        for ref in self._cross_refs.get("cross_references", []):
            for p in ref.get("parallels", []):
                parallels.append(CulturalParallel(
                    culture=p.get("culture", ""),
                    source=p.get("source", ""),
                    detail=p.get("detail", ""),
                ))

        academic = []
        for src in self._academic.get("confirmations", [])[:5]:
            academic.append(AcademicSource(
                title=src.get("title", ""),
                detail=src.get("detail", ""),
            ))

        return HistoricalContext(
            epoch_facts=facts,
            parallels=parallels[:10],
            academic_sources=academic,
            timeline_position=f"Эпоха {epoch.name_ru} (порядок: {epoch.order})",
        )
