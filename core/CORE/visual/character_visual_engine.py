"""CharacterVisualEngine — консистентный визуал персонажей."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from .visual_models import CharacterVisualContext

log = logging.getLogger("visual.character_engine")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"


class CharacterVisualEngine:
    """Возвращает CharacterVisualContext для персонажа."""

    def __init__(self, genome: dict, knowledge_path: Path | None = None):
        self._genome = genome
        self._knowledge = self._load(knowledge_path or _KNOWLEDGE_DIR)

    def _load(self, path: Path) -> dict:
        f = path / "CHARACTER_VISUALS.json"
        if f.exists():
            return json.loads(f.read_text("utf-8-sig"))
        return {}

    def get_character_context(self, character_id: str) -> CharacterVisualContext:
        # 1. VISUAL_KNOWLEDGE
        if character_id in self._knowledge:
            cv = self._knowledge[character_id]
            clothing = cv.get("clothing", {})
            if isinstance(clothing, dict):
                clothing_str = clothing.get("daily", str(clothing))
            else:
                clothing_str = str(clothing)
            return CharacterVisualContext(
                character_id=character_id,
                name=character_id,
                age_range=cv.get("age_range", ""),
                face=cv.get("face", ""),
                hair=cv.get("hair", ""),
                eyes=cv.get("eyes", ""),
                build=cv.get("build", ""),
                clothing=clothing_str,
                accessories=cv.get("accessories", []),
                mannerisms=cv.get("mannerisms", ""),
                movement=cv.get("movement", ""),
                appearance_summary=f"{character_id}, {cv.get('build', '')}, {cv.get('hair', '')}, {cv.get('eyes', '')}",
            )

        # 2. Genome character_visuals
        for gcv in self._genome.get("modules", {}).get("character_visuals", []):
            if gcv.get("character_id") == character_id:
                return CharacterVisualContext(
                    character_id=character_id,
                    name=character_id,
                    build=gcv.get("build", ""),
                    clothing=gcv.get("clothing", ""),
                    appearance_summary=gcv.get("clothing", "")[:150],
                )

        return CharacterVisualContext(character_id=character_id, name=character_id)

    def list_characters(self) -> list[str]:
        return list(self._knowledge.keys())
