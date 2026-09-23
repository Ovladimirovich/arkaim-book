"""Character Planner — арки и мотивации персонажей."""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.context_assembler import FullContext
from narrative_engine.constraint_engine import StoryRequest

log = logging.getLogger("hermes.narrative.planners.character")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


class CharacterArc(BaseModel):
    character: str
    starting_state: str = ""
    ending_state: str = ""
    motivation: str = ""
    obstacle: str = ""
    transformation: str = ""
    key_moments: list[str] = Field(default_factory=list)
    relationships_used: list[str] = Field(default_factory=list)


class CharacterPlanner:
    """Строит арки персонажей для истории."""

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._char_profiles = self._load("character_profiles.json")
        self._themes_deep = self._load("THEMES_DEEP.json")

    def _load(self, filename: str) -> dict:
        path = KNOWLEDGE_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def plan(self, request: StoryRequest, context: FullContext) -> list[CharacterArc]:
        arcs = []
        prompt_lower = request.prompt.lower()

        relevant_chars = self._find_relevant_characters(request, context)

        for char_name in relevant_chars[:3]:
            arc = self._build_arc(char_name, request, context)
            if arc:
                arcs.append(arc)

        return arcs

    def _find_relevant_characters(
        self, request: StoryRequest, context: FullContext
    ) -> list[str]:
        prompt_lower = request.prompt.lower()
        chars = []

        if context.world_state and isinstance(context.world_state, dict):
            for ch in context.world_state.get("characters_alive", []):
                name = ch.get("character_name", "")
                if name and any(part in prompt_lower for part in name.lower().split() if len(part) > 3):
                    chars.append(name)

        if not chars:
            for ch in self._char_profiles.values():
                if ch.get("mention_count", 0) > 3:
                    chars.append(ch.get("name", ""))

        return chars[:5]

    def _build_arc(
        self, char_name: str, request: StoryRequest, context: FullContext
    ) -> Optional[CharacterArc]:
        profile = self._char_profiles.get(char_name, {})

        starting = profile.get("role", "Неизвестно")

        episodes = profile.get("key_episodes", [])
        key_moments = [ep.get("text", "")[:100] for ep in episodes[:3]]

        archetype = profile.get("archetype", "")

        motivation = self._infer_motivation(char_name, request)

        return CharacterArc(
            character=char_name,
            starting_state=starting,
            ending_state=f"Трансформация через {motivation.lower()}" if motivation else "",
            motivation=motivation,
            obstacle="Внутренние ограничения и внешние обстоятельства",
            transformation=f"Рост от '{starting}' к осознанию через путь {archetype.lower()}" if archetype else "",
            key_moments=key_moments,
            relationships_used=self._find_relationships(char_name, context),
        )

    def _infer_motivation(self, char_name: str, request: StoryRequest) -> str:
        prompt_lower = request.prompt.lower()

        archetype_motivations = {
            "Проводник": "Провести других через испытание",
            "Хранитель": "Сохранить знания и традиции",
            "Мудрец": "Передать мудрость следующему поколению",
            "Герой": "Преодолеть препятствия ради общего блага",
            "Наставник": "Направить ученика на путь истины",
        }

        profile = self._char_profiles.get(char_name, {})
        archetype = profile.get("archetype", "")
        return archetype_motivations.get(archetype, "Духовное развитие и служение")

    def _find_relationships(self, char_name: str, context: FullContext) -> list[str]:
        relationships = []
        for epoch in self._wm.get_epochs():
            chars = self._wm.get_characters_alive(epoch.id)
            names = [c.character_name for c in chars]
            if char_name in names:
                relationships.extend([n for n in names if n != char_name][:3])
                break

        return list(set(relationships))[:5]
