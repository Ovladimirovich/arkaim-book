"""World Visualizer — построение визуальной спецификации локации."""
from typing import Optional


class WorldVisualizer:
    """Создаёт визуальную спецификацию локации на основе Genome."""

    def __init__(self, genome: dict):
        self._genome = genome

    def visualize(self, location_id: str) -> Optional[dict]:
        """Получить LocationVisual."""
        # 1. Готовые локации из genome.modules.location_visuals
        locs = self._genome.get("modules", {}).get("location_visuals", [])
        for lv in locs:
            if lv.get("location_id") == location_id:
                return lv

        # 2. Fallback: world_entities
        for we in self._genome.get("world_entities", []):
            if we.get("name", "").lower() == location_id.lower():
                return self._build_from_entity(we)

        return None

    def _build_from_entity(self, entity: dict) -> dict:
        """Строит локацию из world_entity."""
        return {
            "location_id": entity["name"],
            "type": "unknown",
            "architecture": entity.get("description", "")[:100],
            "atmosphere": "",
            "lighting": "",
            "palette": ["neutral"],
        }