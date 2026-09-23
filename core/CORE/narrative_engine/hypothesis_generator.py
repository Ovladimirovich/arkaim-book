"""Hypothesis Generator — генерация гипотез о развитии мира.

Реализует архитектуру World Explorer: Exploration Core → Hypothesis Generator (Этап 3).

Генерирует гипотезы на основе:
- Свободных точек мира (события без последствий, персонажи без завершённых арок)
- Паттернов развития (54 мифологических паттерна)
- Пользовательских запросов
- Проактивного анализа
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.ability_model import AbilityModel, WorldPossibility
from narrative_engine.planners.cause_effect import PATTERN_CHAINS

log = logging.getLogger("hermes.narrative.hypothesis_generator")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"


class HypothesisType(str, Enum):
    """Типы гипотез."""
    WHAT_IF_PAST = "what_if_past"        # Что если прошлое было иначе?
    PARALLEL_DEVELOPMENT = "parallel"    # Параллельное развитие
    NEW_ELEMENT = "new_element"          # Новый элемент (персонаж, технология)
    CASCADE_EFFECT = "cascade"           # Каскадное следствие
    PROACTIVE = "proactive"              # Проактивная гипотеза системы


class Hypothesis(BaseModel):
    """Одна гипотеза о развитии мира."""
    id: str
    title: str
    title_ru: str
    description: str = ""
    hypothesis_type: HypothesisType
    epoch: str = ""
    location: str = ""
    source_possibility: str = ""  # ID возможности, из которой возникла гипотеза
    source_pattern: str = ""  # Паттерн, который лежит в основе
    confidence: float = 0.5
    tags: list[str] = Field(default_factory=list)
    required_elements: list[str] = Field(default_factory=list)
    potential_consequences: list[str] = Field(default_factory=list)


class HypothesisGraph(BaseModel):
    """Граф гипотез — дерево возможных исследований."""
    root_hypothesis: Optional[Hypothesis] = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    branches: list[list[str]] = Field(default_factory=list)  # Связи между гипотезами
    total_count: int = 0
    epoch: str = ""
    summary: str = ""


class HypothesisGenerator:
    """Генерирует гипотезы о развитии мира.

    Режимы работы:
    1. For Possibility — гипотеза на основе конкретной возможности
    2. For Epoch — гипотезы для конкретной эпохи
    3. For Hypothesis — производные гипотезы от существующей
    4. Proactive — проактивная генерация без пользовательского ввода
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._ability_model = AbilityModel(world_model)
        self._hypothesis_counter = 0

    def generate_for_possibility(
        self,
        possibility: WorldPossibility,
        epoch_id: Optional[str] = None,
    ) -> list[Hypothesis]:
        """Сгенерировать гипотезы на основе возможности."""
        hypotheses = []

        # Определяем тип гипотезы на основе типа возможности
        if possibility.category == "event":
            h_type = HypothesisType.CASCADE_EFFECT
        elif possibility.category == "character_arc":
            h_type = HypothesisType.PARALLEL_DEVELOPMENT
        elif possibility.category == "technology":
            h_type = HypothesisType.NEW_ELEMENT
        elif possibility.category == "cultural_shift":
            h_type = HypothesisType.WHAT_IF_PAST
        else:
            h_type = HypothesisType.CASCADE_EFFECT

        # Базовая гипотеза
        hyp = self._create_hypothesis(
            title=f"Исследование: {possibility.title}",
            title_ru=f"Исследование: {possibility.title_ru}",
            description=possibility.description,
            h_type=h_type,
            epoch=epoch_id or possibility.epoch,
            source_possibility=possibility.id,
            tags=possibility.tags,
        )
        hypotheses.append(hyp)

        # Производные гипотезы (что если...)
        if possibility.category == "character_arc":
            char_name = possibility.tags[1] if len(possibility.tags) > 1 else ""
            if char_name:
                hypotheses.append(self._create_hypothesis(
                    title=f"Что если {char_name} выбрал другой путь?",
                    title_ru=f"Что если {char_name} выбрал другой путь?",
                    description=f"Альтернативное развитие пути персонажа {char_name}",
                    h_type=HypothesisType.PARALLEL_DEVELOPMENT,
                    epoch=epoch_id or possibility.epoch,
                    source_possibility=possibility.id,
                    tags=["character", char_name, "alternative"],
                    required_elements=[char_name],
                ))

        elif possibility.category == "event":
            hypotheses.append(self._create_hypothesis(
                title=f"Что если '{possibility.title}' не произошло?",
                title_ru=f"Что если '{possibility.title_ru}' не произошло?",
                description=f"Альтернативное развитие без события '{possibility.title}'",
                h_type=HypothesisType.WHAT_IF_PAST,
                epoch=epoch_id or possibility.epoch,
                source_possibility=possibility.id,
                tags=["event", "negation"],
            ))

        return hypotheses

    def generate_for_epoch(
        self,
        epoch_id: str,
        limit: int = 10,
    ) -> list[Hypothesis]:
        """Сгенерировать гипотезы для конкретной эпохи."""
        hypotheses = []

        # Получаем возможности эпохи
        possibilities = self._ability_model.get_possibilities(epoch_id, limit=limit)

        for poss in possibilities:
            hyps = self.generate_for_possibility(poss, epoch_id)
            hypotheses.extend(hyps)

        # Добавляем проактивные гипотезы
        proactive = self._generate_proactive_hypotheses(epoch_id)
        hypotheses.extend(proactive)

        # Дедупликация и лимит
        seen = set()
        unique = []
        for h in hypotheses:
            if h.id not in seen:
                seen.add(h.id)
                unique.append(h)
                if len(unique) >= limit:
                    break

        return unique

    def generate_for_hypothesis(
        self,
        parent: Hypothesis,
        limit: int = 5,
    ) -> list[Hypothesis]:
        """Сгенерировать производные гипотезы от существующей."""
        derivatives = []

        # Ветвление: что если сделать иначе?
        derivatives.append(self._create_hypothesis(
            title=f"Альтернатива: {parent.title}",
            title_ru=f"Альтернатива: {parent.title_ru}",
            description=f"Противоположный путь развития для: {parent.description[:100]}",
            h_type=HypothesisType.PARALLEL_DEVELOPMENT,
            epoch=parent.epoch,
            source_possibility=parent.id,
            tags=["derivative", "alternative"],
        ))

        # Углубление: что если развить дальше?
        derivatives.append(self._create_hypothesis(
            title=f"Развитие: {parent.title}",
            title_ru=f"Развитие: {parent.title_ru}",
            description=f"Дальнейшее развитие: {parent.description[:100]}",
            h_type=HypothesisType.CASCADE_EFFECT,
            epoch=parent.epoch,
            source_possibility=parent.id,
            tags=["derivative", "deepening"],
        ))

        # Связывание: что если связать с другим периодом?
        other_epochs = [e for e in self._wm.get_epochs() if e.id != parent.epoch]
        if other_epochs:
            other = other_epochs[0]
            derivatives.append(self._create_hypothesis(
                title=f"Связь эпох: {parent.title} → {other.name_ru}",
                title_ru=f"Связь эпох: {parent.title_ru} → {other.name_ru}",
                description=f"Как {parent.title} повлияет на {other.name_ru}?",
                h_type=HypothesisType.CASCADE_EFFECT,
                epoch=other.id,
                source_possibility=parent.id,
                tags=["derivative", "cross_epoch"],
            ))

        return derivatives[:limit]

    def generate_proactive(
        self,
        epoch_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[Hypothesis]:
        """Проактивная генерация гипотез без пользовательского ввода."""
        if epoch_id:
            return self._generate_proactive_hypotheses(epoch_id)[:limit]

        # Для всех эпох
        all_hyps = []
        for epoch in self._wm.get_epochs():
            hyps = self._generate_proactive_hypotheses(epoch.id)
            all_hyps.extend(hyps)

        return all_hyps[:limit]

    def _generate_proactive_hypotheses(self, epoch_id: str) -> list[Hypothesis]:
        """Генерировать проактивные гипотезы для эпохи."""
        hypotheses = []

        # 1. Персонажи без завершённых арок
        chars = self._wm.get_characters_alive(epoch_id)
        for char in chars[:3]:
            hypotheses.append(self._create_hypothesis(
                title=f"Арка: {char.character_name}",
                title_ru=f"Арка: {char.character_name}",
                description=f"Развитие пути персонажа {char.character_name} ({char.status})",
                h_type=HypothesisType.PROACTIVE,
                epoch=epoch_id,
                tags=["proactive", "character", char.character_name.lower()],
                required_elements=[char.character_name],
            ))

        # 2. События без последствий
        events = self._wm.get_events(epoch_id)
        for event in events[:2]:
            hypotheses.append(self._create_hypothesis(
                title=f"Последствия: {event.title_ru}",
                title_ru=f"Последствия: {event.title_ru}",
                description=f"Что произойдёт после '{event.title_ru}'?",
                h_type=HypothesisType.CASCADE_EFFECT,
                epoch=epoch_id,
                tags=["proactive", "event", event.id],
            ))

        # 3. Свободные паттерны
        used_patterns = set()
        for event in events:
            for p_name in PATTERN_CHAINS:
                if p_name.lower() in event.title_ru.lower():
                    used_patterns.add(p_name)

        free_patterns = [p for p in PATTERN_CHAINS if p not in used_patterns]
        for pattern_name in free_patterns[:2]:
            hypotheses.append(self._create_hypothesis(
                title=f"Паттерн: {pattern_name}",
                title_ru=f"Паттерн: {pattern_name}",
                description=f"Применение паттерна '{pattern_name}' в эпохе",
                h_type=HypothesisType.PROACTIVE,
                epoch=epoch_id,
                tags=["proactive", "pattern", pattern_name.lower()],
            ))

        return hypotheses

    def _create_hypothesis(
        self,
        title: str,
        title_ru: str,
        description: str,
        h_type: HypothesisType,
        epoch: str = "",
        source_possibility: str = "",
        tags: list[str] = None,
        required_elements: list[str] = None,
    ) -> Hypothesis:
        """Создать гипотезу с уникальным ID."""
        self._hypothesis_counter += 1
        hyp_id = f"hyp_{self._hypothesis_counter:04d}"

        return Hypothesis(
            id=hyp_id,
            title=title,
            title_ru=title_ru,
            description=description,
            hypothesis_type=h_type,
            epoch=epoch,
            source_possibility=source_possibility,
            confidence=0.6,
            tags=tags or [],
            required_elements=required_elements or [],
        )

    def build_graph(
        self,
        epoch_id: str,
        depth: int = 2,
        limit_per_level: int = 5,
    ) -> HypothesisGraph:
        """Построить граф гипотез для эпохи."""
        # Уровень 0: базовые гипотезы
        base_hyps = self.generate_for_epoch(epoch_id, limit=limit_per_level)

        all_hyps = list(base_hyps)
        branches = []

        # Уровень 1: производные
        if depth > 1:
            for hyp in base_hyps[:3]:
                derivatives = self.generate_for_hypothesis(hyp, limit=3)
                for d in derivatives:
                    branches.append([hyp.id, d.id])
                all_hyps.extend(derivatives)

        # Уровень 2: производные от производных
        if depth > 2:
            for hyp in all_hyps[:5]:
                if hyp.id.startswith("hyp_") and int(hyp.id.split("_")[1]) > len(base_hyps):
                    derivatives = self.generate_for_hypothesis(hyp, limit=2)
                    for d in derivatives:
                        branches.append([hyp.id, d.id])
                    all_hyps.extend(derivatives)

        # Дедупликация
        seen = set()
        unique = []
        for h in all_hyps:
            if h.id not in seen:
                seen.add(h.id)
                unique.append(h)

        return HypothesisGraph(
            root_hypothesis=base_hyps[0] if base_hyps else None,
            hypotheses=unique,
            branches=branches,
            total_count=len(unique),
            epoch=epoch_id,
            summary=f"Граф гипотез для эпохи: {len(unique)} гипотез, {len(branches)} связей",
        )
