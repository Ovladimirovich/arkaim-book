"""LocationEngine — визуальный паспорт локаций."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from .visual_models import LocationContext, ArchitectureContext, LandscapeContext

log = logging.getLogger("visual.location_engine")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"


class LocationEngine:
    """Возвращает обогащённый LocationContext для локации."""

    def __init__(self, genome: dict, knowledge_path: Path | None = None):
        self._genome = genome
        self._knowledge = self._load_knowledge(knowledge_path or _KNOWLEDGE_DIR)

    def _load_knowledge(self, path: Path) -> dict:
        f = path / "LOCATION_VISUALS.json"
        if f.exists():
            return json.loads(f.read_text("utf-8-sig"))
        return {}

    def get_location_context(self, location_id: str, time_of_day: str = "dawn") -> LocationContext:
        # 1. VISUAL_KNOWLEDGE
        if location_id in self._knowledge:
            return self._from_knowledge(location_id, self._knowledge[location_id], time_of_day)

        # 2. Genome location_visuals
        for lv in self._genome.get("modules", {}).get("location_visuals", []):
            if lv.get("location_id", "").lower() == location_id.lower():
                return LocationContext(
                    location_id=location_id,
                    name=location_id,
                    type=lv.get("type", "unknown"),
                    architecture=ArchitectureContext(style=lv.get("architecture", "")),
                    palette=lv.get("palette", []),
                )

        # 3. Fallback: world_entities
        for we in self._genome.get("world_entities", []):
            if we.get("name", "").lower() == location_id.lower():
                return LocationContext(
                    location_id=location_id,
                    name=location_id,
                    architecture=ArchitectureContext(style=we.get("description", "")[:150]),
                )

        return LocationContext(location_id=location_id, name=location_id)

    def _from_knowledge(self, location_id: str, data: dict, time_of_day: str) -> LocationContext:
        arch = data.get("architecture", {})
        land = data.get("landscape", {})
        atmo = data.get("atmosphere", {})

        return LocationContext(
            location_id=location_id,
            name=location_id,
            type=data.get("type", "unknown"),
            architecture=ArchitectureContext(
                style=arch.get("style", ""),
                materials=arch.get("materials", ""),
                features=arch.get("features", []),
                age=arch.get("age", ""),
                condition=arch.get("condition", ""),
            ),
            landscape=LandscapeContext(
                terrain=land.get("terrain", ""),
                vegetation=land.get("vegetation", ""),
                water=land.get("water", ""),
                sky=land.get("sky", ""),
            ),
            palette=data.get("palette", []),
            atmosphere_default=atmo.get("default", ""),
            atmosphere_by_time=atmo.get("time_variants", {}),
            sound=data.get("sound", ""),
            symbols=data.get("symbols", []),
        )

    def list_locations(self) -> list[str]:
        return list(self._knowledge.keys())
