"""Geography Context — географический контекст для локации."""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel

log = logging.getLogger("hermes.narrative.contexts.geography")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


class LocationInfo(BaseModel):
    id: str
    name_ru: str
    type: str
    description: str = ""
    coordinates: Optional[dict] = None


class MigrationRoute(BaseModel):
    from_location: str
    to_location: str
    description: str = ""


class EnergyLine(BaseModel):
    name: str
    description: str = ""
    connected_locations: list[str] = Field(default_factory=list)


class GeographyContext(BaseModel):
    location: Optional[LocationInfo] = None
    nearby_locations: list[LocationInfo] = Field(default_factory=list)
    migration_routes: list[MigrationRoute] = Field(default_factory=list)
    energy_lines: list[EnergyLine] = Field(default_factory=list)
    terrain: str = ""


class GeographyContextBuilder:
    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._map_data = self._load("MAP_DATA.json")
        self._geography = self._load("GEOGRAPHY.json")
        self._energy = self._load("ENERGY_OF_PLACES.json")

    def _load(self, filename: str):
        path = KNOWLEDGE_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def build(self, location_id: Optional[str] = None, epoch_id: Optional[str] = None) -> GeographyContext:
        if not location_id:
            return GeographyContext()

        location = self._wm.get_location(location_id)
        if not location:
            return GeographyContext()

        loc_info = LocationInfo(
            id=location.id,
            name_ru=location.name_ru,
            type=location.type,
            description=location.description,
            coordinates=location.coordinates,
        )

        nearby = []
        if location.region_id:
            for loc in self._wm.get_locations():
                if loc.region_id == location.region_id and loc.id != location_id:
                    nearby.append(LocationInfo(
                        id=loc.id,
                        name_ru=loc.name_ru,
                        type=loc.type,
                        description=loc.description[:100] if loc.description else "",
                    ))

        energy_lines = []
        energy_data = self._energy
        if isinstance(energy_data, dict):
            ep = energy_data.get("energy_of_places", {})
            book_examples = ep.get("book_examples", []) if isinstance(ep, dict) else []
            for place in book_examples:
                if isinstance(place, dict):
                    place_name = place.get("name", "").lower()
                    if location_id.lower() in place_name or place_name in location_id.lower():
                        energy_lines.append(EnergyLine(
                            name=place.get("name", ""),
                            description=place.get("description", "")[:200],
                            connected_locations=[],
                        ))

        migration_routes = []
        map_data = self._map_data
        if isinstance(map_data, dict):
            routes = map_data.get("migration_routes", [])
            for route in routes:
                if isinstance(route, dict):
                    if route.get("from") == location_id or route.get("to") == location_id:
                        migration_routes.append(MigrationRoute(
                            from_location=route.get("from", ""),
                            to_location=route.get("to", ""),
                            description=route.get("description", ""),
                        ))

        terrain = ""
        geo_data = self._geography
        if isinstance(geo_data, list):
            for g in geo_data:
                if isinstance(g, dict):
                    topic = g.get("topic", "")
                    content = g.get("content", "")
                    if location_id.lower() in topic.lower() or location_id.lower() in content.lower():
                        terrain = content[:200]
                        break
        elif isinstance(geo_data, dict):
            for g in geo_data.get("regions", []):
                if g.get("id") == location_id or location_id in str(g.get("locations", [])):
                    terrain = g.get("terrain", "")
                    break

        return GeographyContext(
            location=loc_info,
            nearby_locations=nearby[:5],
            migration_routes=migration_routes[:3],
            energy_lines=energy_lines[:3],
            terrain=terrain,
        )
