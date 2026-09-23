"""Ability Model — модель возможностей мира.

Реализует архитектуру World Explorer: AbilityModel (Этап 1 дорожной карты).
Определяет, что МОЖЕТ произойти в каждом состоянии мира на основе:
- доступных персонажей
- доступных технологий
- причинно-следственных правил
- тематических доминант
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel, Epoch
from narrative_engine.source_levels import SourceLevel, ProvenanceTag

log = logging.getLogger("hermes.narrative.ability_model")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"


class WorldPossibility(BaseModel):
    """Одна возможность мира — что может произойти."""
    id: str
    title: str
    title_ru: str
    description: str = ""
    category: str  # "event", "character_arc", "technology", "cultural_shift", "conflict"
    epoch: str = ""
    required_elements: list[str] = Field(default_factory=list)
    forbidden_elements: list[str] = Field(default_factory=list)
    source_level: SourceLevel = SourceLevel.SYSTEM_INTERPRETATION
    confidence: float = 0.5
    tags: list[str] = Field(default_factory=list)


class AbilityModel:
    """Модель возможностей мира.

    Для каждого состояния мира (эпоха + локация) определяет:
    - Какие события могут произойти
    - Какие арки персонажей возможны
    - Какие технологии доступны для развития
    - Какие культурные сдвиги вероятны
    - Какие конфликты могут возникнуть
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._patterns = self._load_patterns()
        self._themes = self._load_themes()

    def _load_patterns(self) -> list[dict]:
        path = KNOWLEDGE_DIR / "PATTERNS.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get("patterns", [])
            except Exception:
                return []
        return []

    def _load_themes(self) -> list[dict]:
        path = KNOWLEDGE_DIR / "THEMES_DEEP.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get("themes", [])
            except Exception:
                return []
        return []

    def get_possibilities(
        self,
        epoch_id: Optional[str] = None,
        location_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[WorldPossibility]:
        """Получить список возможных событий для данного состояния мира."""
        possibilities: list[WorldPossibility] = []

        # 1. События, основанные на паттернах
        possibilities.extend(self._possibilities_from_patterns(epoch_id))

        # 2. Арки персонажей
        possibilities.extend(self._possibilities_from_characters(epoch_id))

        # 3. Технологические возможности
        possibilities.extend(self._possibilities_from_technology(epoch_id))

        # 4. Тематические возможности
        possibilities.extend(self._possibilities_from_themes())

        # 5. Конфликтные возможности
        possibilities.extend(self._possibilities_from_conflicts(epoch_id))

        # Дедупликация и лимит
        seen_ids = set()
        unique: list[WorldPossibility] = []
        for p in possibilities:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique.append(p)
                if len(unique) >= limit:
                    break

        return unique

    def get_possibilities_for_hypothesis(
        self,
        hypothesis: str,
        epoch_id: Optional[str] = None,
    ) -> list[WorldPossibility]:
        """Получить возможности, релевантные для конкретной гипотезы."""
        all_poss = self.get_possibilities(epoch_id, limit=50)
        hypothesis_lower = hypothesis.lower()

        scored: list[tuple[float, WorldPossibility]] = []
        for p in all_poss:
            # Простой скоринг по ключевым словам
            score = 0.0
            words = p.title.lower().split() + p.description.lower().split()
            for word in words:
                if len(word) > 3 and word in hypothesis_lower:
                    score += 0.1
            for tag in p.tags:
                if tag.lower() in hypothesis_lower:
                    score += 0.2
            scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:10]]

    # ── Внутренние методы генерации возможностей ──────────

    def _possibilities_from_patterns(self, epoch_id: Optional[str]) -> list[WorldPossibility]:
        """Возможности на основе мифологических паттернов."""
        possibilities = []
        for i, pattern in enumerate(self._patterns):
            name = pattern.get("name", "")
            desc = pattern.get("description", "")
            possibilities.append(WorldPossibility(
                id=f"pattern_{i}",
                title=f"Паттерн: {name}",
                title_ru=f"Паттерн: {name}",
                description=desc,
                category="event",
                epoch=epoch_id or "",
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                confidence=0.7,
                tags=["pattern", name.lower()],
            ))
        return possibilities

    def _possibilities_from_characters(self, epoch_id: Optional[str]) -> list[WorldPossibility]:
        """Возможности на основе персонажей эпохи."""
        possibilities = []
        if not epoch_id:
            return possibilities

        chars = self._wm.get_characters_alive(epoch_id)
        for i, char in enumerate(chars[:10]):
            possibilities.append(WorldPossibility(
                id=f"char_arc_{i}",
                title=f"Арка: {char.character_name}",
                title_ru=f"Арка: {char.character_name}",
                description=f"Развитие пути персонажа {char.character_name} ({char.status})",
                category="character_arc",
                epoch=epoch_id,
                required_elements=[char.character_name],
                source_level=SourceLevel.CANON,
                confidence=0.8,
                tags=["character", char.character_name.lower(), char.status],
            ))
        return possibilities

    def _possibilities_from_technology(self, epoch_id: Optional[str]) -> list[WorldPossibility]:
        """Возможности на основе технологий эпохи."""
        possibilities = []
        if not epoch_id:
            return possibilities

        techs = self._wm.get_technologies(epoch_id)
        for i, tech in enumerate(techs[:10]):
            possibilities.append(WorldPossibility(
                id=f"tech_{i}",
                title=f"Технология: {tech.name_ru}",
                title_ru=f"Технология: {tech.name_ru}",
                description=f"Применение или развитие технологии {tech.name_ru}",
                category="technology",
                epoch=epoch_id,
                required_elements=[tech.name_ru],
                source_level=SourceLevel.CANON,
                confidence=0.6,
                tags=["technology", tech.name.lower()],
            ))
        return possibilities

    def _possibilities_from_themes(self) -> list[WorldPossibility]:
        """Возможности на основе тематических доминант."""
        possibilities = []
        for i, theme in enumerate(self._themes[:10]):
            name = theme.get("name", "")
            desc = theme.get("description", "")
            possibilities.append(WorldPossibility(
                id=f"theme_{i}",
                title=f"Тема: {name}",
                title_ru=f"Тема: {name}",
                description=desc,
                category="cultural_shift",
                source_level=SourceLevel.SYSTEM_INTERPRETATION,
                confidence=0.5,
                tags=["theme", name.lower()],
            ))
        return possibilities

    def _possibilities_from_conflicts(self, epoch_id: Optional[str]) -> list[WorldPossibility]:
        """Возможности на основе конфликтных ситуаций."""
        possibilities = []
        if not epoch_id:
            return possibilities

        chars = self._wm.get_characters_alive(epoch_id)
        if len(chars) >= 2:
            for i in range(min(3, len(chars) - 1)):
                for j in range(i + 1, min(4, len(chars))):
                    c1, c2 = chars[i], chars[j]
                    possibilities.append(WorldPossibility(
                        id=f"conflict_{i}_{j}",
                        title=f"Конфликт: {c1.character_name} vs {c2.character_name}",
                        title_ru=f"Конфликт: {c1.character_name} vs {c2.character_name}",
                        description=f"Потенциальный конфликт между {c1.character_name} и {c2.character_name}",
                        category="conflict",
                        epoch=epoch_id,
                        required_elements=[c1.character_name, c2.character_name],
                        source_level=SourceLevel.SYSTEM_INTERPRETATION,
                        confidence=0.4,
                        tags=["conflict", c1.character_name.lower(), c2.character_name.lower()],
                    ))
        return possibilities

    def summary(self) -> str:
        """Краткая сводка возможностей мира."""
        epochs = self._wm.get_epochs()
        total_poss = 0
        for ep in epochs:
            total_poss += len(self.get_possibilities(ep.id, limit=100))
        return (
            f"AbilityModel: {len(epochs)} эпох, "
            f"{len(self._patterns)} паттернов, "
            f"{len(self._themes)} тем, "
            f"~{total_poss} возможностей"
        )
