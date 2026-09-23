"""Impact Assessor — оценка влияния события на мир.

Реализует архитектуру World Explorer: Logic Engine → Impact Assessor (Этап 2).
Оценивает влияние на:
- Персонажей (состояния, отношения, мотивации)
- Локации (география, инфраструктура)
- Цивилизации (культура, технологии, ценности)
- Временную шкалу (последствия для будущих эпох)
- Ценности (духовные, культурные)
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.planners.cause_effect import CauseEffectTree, CauseEffectNode

log = logging.getLogger("hermes.narrative.impact_assessor")


class CharacterImpact(BaseModel):
    """Влияние на конкретного персонажа."""
    character_name: str
    impact_type: str  # "positive", "negative", "neutral", "transformation"
    description: str = ""
    state_change: str = ""  # что изменилось
    confidence: float = 0.5


class LocationImpact(BaseModel):
    """Влияние на конкретную локацию."""
    location_id: str
    location_name: str
    impact_type: str  # "destruction", "creation", "modification", "energy_shift"
    description: str = ""
    confidence: float = 0.5


class CivilizationImpact(BaseModel):
    """Влияние на цивилизацию."""
    civilization_id: str
    impact_type: str  # "cultural_shift", "technological_advance", "decline", "revival"
    description: str = ""
    confidence: float = 0.5


class TimelineImpact(BaseModel):
    """Влияние на временную шкалу."""
    impact_type: str  # "acceleration", "deceleration", "branch", "paradox"
    description: str = ""
    affected_epochs: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class ValueImpact(BaseModel):
    """Влияние на ценности."""
    value_name: str
    impact_type: str  # "strengthening", "weakening", "transformation"
    description: str = ""
    confidence: float = 0.5


class ImpactReport(BaseModel):
    """Полный отчёт о влиянии события на мир."""
    event_description: str = ""
    character_impacts: list[CharacterImpact] = Field(default_factory=list)
    location_impacts: list[LocationImpact] = Field(default_factory=list)
    civilization_impacts: list[CivilizationImpact] = Field(default_factory=list)
    timeline_impacts: list[TimelineImpact] = Field(default_factory=list)
    value_impacts: list[ValueImpact] = Field(default_factory=list)
    overall_impact_score: float = Field(ge=0.0, le=1.0, description="Общая оценка влияния [0, 1]")
    affected_entities_count: int = 0
    summary: str = ""


class ImpactAssessor:
    """Оценивает влияние события на мир.

    Принимает CauseEffectTree и WorldModel, возвращает ImpactReport.
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model

    def assess(
        self,
        tree: CauseEffectTree,
        epoch_id: Optional[str] = None,
    ) -> ImpactReport:
        """Оценить влияние дерева причин-следствий на мир."""
        # Собираем все задействованные сущности
        all_characters = set()
        all_locations = set()
        for node in tree.nodes:
            all_characters.update(node.characters_involved)

        # Оцениваем влияние на персонажей
        character_impacts = self._assess_character_impacts(tree, all_characters, epoch_id)

        # Оцениваем влияние на локации
        location_impacts = self._assess_location_impacts(tree, epoch_id)

        # Оцениваем влияние на цивилизации
        civilization_impacts = self._assess_civilization_impacts(tree, epoch_id)

        # Оцениваем влияние на временную шкалу
        timeline_impacts = self._assess_timeline_impacts(tree, epoch_id)

        # Оцениваем влияние на ценности
        value_impacts = self._assess_value_impacts(tree)

        # Рассчитываем общую оценку
        total_impacts = (
            len(character_impacts)
            + len(location_impacts)
            + len(civilization_impacts)
            + len(timeline_impacts)
            + len(value_impacts)
        )
        overall_score = min(1.0, total_impacts * 0.1)

        # Генерируем сводку
        summary = self._generate_summary(
            character_impacts, location_impacts, civilization_impacts,
            timeline_impacts, value_impacts,
        )

        return ImpactReport(
            event_description=tree.root[:200],
            character_impacts=character_impacts,
            location_impacts=location_impacts,
            civilization_impacts=civilization_impacts,
            timeline_impacts=timeline_impacts,
            value_impacts=value_impacts,
            overall_impact_score=overall_score,
            affected_entities_count=total_impacts,
            summary=summary,
        )

    def _assess_character_impacts(
        self,
        tree: CauseEffectTree,
        characters: set[str],
        epoch_id: Optional[str],
    ) -> list[CharacterImpact]:
        """Оценить влияние на персонажей."""
        impacts = []

        for char_name in characters:
            # Определяем тип влияния по узлам дерева
            impact_type = "neutral"
            description = ""
            state_change = ""

            for node in tree.nodes:
                if char_name in node.characters_involved:
                    if node.type == "effect":
                        impact_type = "positive"
                        description = node.description[:150]
                        state_change = f"Состояние изменено: {description}"
                    elif node.type == "reaction":
                        impact_type = "transformation"
                        description = node.description[:150]
                        state_change = f"Трансформация: {description}"
                    elif node.type == "constraint":
                        impact_type = "negative"
                        description = node.description[:150]
                        state_change = f"Ограничение: {description}"

            impacts.append(CharacterImpact(
                character_name=char_name,
                impact_type=impact_type,
                description=description,
                state_change=state_change,
                confidence=0.7,
            ))

        return impacts

    def _assess_location_impacts(
        self,
        tree: CauseEffectTree,
        epoch_id: Optional[str],
    ) -> list[LocationImpact]:
        """Оценить влияние на локации."""
        impacts = []

        if not epoch_id:
            return impacts

        # Получаем локации эпохи
        locations = self._wm.get_locations(epoch_id)

        for loc in locations[:5]:
            # Проверяем, упоминается ли локация в дереве
            loc_name_lower = loc.name_ru.lower()
            mentioned = False
            impact_type = "energy_shift"
            description = ""

            for node in tree.nodes:
                if loc_name_lower in node.description.lower():
                    mentioned = True
                    if node.type == "world_change":
                        impact_type = "modification"
                        description = node.description[:150]
                    break

            if mentioned:
                impacts.append(LocationImpact(
                    location_id=loc.id,
                    location_name=loc.name_ru,
                    impact_type=impact_type,
                    description=description,
                    confidence=0.6,
                ))

        return impacts

    def _assess_civilization_impacts(
        self,
        tree: CauseEffectTree,
        epoch_id: Optional[str],
    ) -> list[CivilizationImpact]:
        """Оценить влияние на цивилизации."""
        impacts = []

        if not epoch_id:
            return impacts

        # Анализируем узлы дерева на предмет культурных изменений
        cultural_keywords = ["культура", "традиц", "ценности", "знание", "понимание"]
        tech_keywords = ["технолог", "изобретени", "открыт"]

        for node in tree.nodes:
            desc_lower = node.description.lower()
            if any(kw in desc_lower for kw in cultural_keywords):
                impacts.append(CivilizationImpact(
                    civilization_id="main",
                    impact_type="cultural_shift",
                    description=node.description[:150],
                    confidence=0.5,
                ))
            elif any(kw in desc_lower for kw in tech_keywords):
                impacts.append(CivilizationImpact(
                    civilization_id="main",
                    impact_type="technological_advance",
                    description=node.description[:150],
                    confidence=0.5,
                ))

        return impacts[:3]

    def _assess_timeline_impacts(
        self,
        tree: CauseEffectTree,
        epoch_id: Optional[str],
    ) -> list[TimelineImpact]:
        """Оценить влияние на временную шкалу."""
        impacts = []

        # Проверяем временные нарушения
        temporal_keywords = ["будущее", "прошлое", "время", "эпоха", "цикл"]
        for node in tree.nodes:
            desc_lower = node.description.lower()
            if any(kw in desc_lower for kw in temporal_keywords):
                impacts.append(TimelineImpact(
                    impact_type="branch",
                    description=f"Потенциальное ветвление: {node.description[:100]}",
                    affected_epochs=[epoch_id] if epoch_id else [],
                    confidence=0.4,
                ))
                break

        return impacts

    def _assess_value_impacts(
        self,
        tree: CauseEffectTree,
    ) -> list[ValueImpact]:
        """Оценить влияние на ценности."""
        impacts = []

        value_keywords = {
            "познание": "Познание",
            "гармония": "Гармония",
            "служение": "Служение",
            "мудрость": "Мудрость",
            "любовь": "Любовь",
            "сострадание": "Сострадание",
            "истина": "Истина",
        }

        for node in tree.nodes:
            desc_lower = node.description.lower()
            for keyword, value_name in value_keywords.items():
                if keyword in desc_lower:
                    impacts.append(ValueImpact(
                        value_name=value_name,
                        impact_type="strengthening",
                        description=f"Ценность '{value_name}' укрепляется: {node.description[:80]}",
                        confidence=0.6,
                    ))
                    break

        return impacts[:5]

    def _generate_summary(
        self,
        character_impacts: list[CharacterImpact],
        location_impacts: list[LocationImpact],
        civilization_impacts: list[CivilizationImpact],
        timeline_impacts: list[TimelineImpact],
        value_impacts: list[ValueImpact],
    ) -> str:
        """Генерировать сводку влияния."""
        parts = []

        if character_impacts:
            chars = [ci.character_name for ci in character_impacts[:3]]
            parts.append(f"Затронуты персонажи: {', '.join(chars)}")

        if location_impacts:
            locs = [li.location_name for li in location_impacts[:3]]
            parts.append(f"Затронуты локации: {', '.join(locs)}")

        if civilization_impacts:
            parts.append(f"Культурные изменения: {len(civilization_impacts)}")

        if timeline_impacts:
            parts.append(f"Временные ветвления: {len(timeline_impacts)}")

        if value_impacts:
            values = [vi.value_name for vi in value_impacts[:3]]
            parts.append(f"Укрепляются ценности: {', '.join(values)}")

        return "; ".join(parts) if parts else "Влияние минимально"
