"""Character Visualizer — построение визуальной спецификации персонажа."""
from typing import Optional


class CharacterVisualizer:
    """Создаёт визуальную спецификацию персонажа на основе Genome."""

    def __init__(self, genome: dict):
        self._genome = genome

    def visualize(self, character_id: str) -> Optional[dict]:
        """Получить Visual VisualSpec для персонажа."""
        # 1. Пробуем взять готовую CharacterVisual из genome.modules.character_visuals
        visuals = self._genome.get("modules", {}).get("character_visuals", [])
        for cv in visuals:
            if cv.get("character_id") == character_id:
                return cv

        # 2. Fallback: строим на основе Character из genome
        chars = self._genome.get("modules", {}).get("characters", [])
        for ch in chars:
            if ch.get("id") == character_id:
                return self._build_from_character(ch)

        return None

    def _build_from_character(self, character: dict) -> dict:
        """Строит визуаль на основе character data."""
        return {
            "character_id": character["id"],
            "age_range": "unknown",
            "build": "average",
            "hair": "not specified",
            "eyes": "not specified",
            "clothing": character.get("description", "")[:100],
            "accessories": [],
            "color_palette": ["earth tones"],
            "style_constants": [],
        }