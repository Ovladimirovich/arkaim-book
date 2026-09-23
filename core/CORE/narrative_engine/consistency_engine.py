"""Consistency Engine — проверка допустимости построений в мире."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

log = logging.getLogger("hermes.consistency_engine")


class RuleType(str, Enum):
    """Типы правил."""
    TEMPORAL = "temporal"      # временные
    SPATIAL = "spatial"        # пространственные
    CAUSAL = "causal"          # причинные
    CULTURAL = "cultural"      # культурные
    METAPHYSICAL = "metaphysical"  # метафизические


class RuleSeverity(str, Enum):
    """Серьёзность нарушения."""
    HARD = "hard"      # нарушение = ошибка
    SOFT = "soft"      # нарушение = предупреждение
    INFO = "info"      # informational


@dataclass
class ConsistencyRule:
    """Правило консистентности мира."""
    id: str
    name: str
    name_ru: str
    description: str
    description_ru: str
    rule_type: RuleType
    severity: RuleSeverity
    condition_text: str
    recovery_suggestion: str = ""
    examples: list[str] = field(default_factory=list)


@dataclass
class ConsistencyViolation:
    """Нарушенное правило."""
    rule_id: str
    rule_name: str
    severity: RuleSeverity
    description: str
    involved_entities: list[str] = field(default_factory=list)
    suggested_fix: str = ""


@dataclass
class ConsistencyReport:
    """Отчёт о консистентности."""
    is_valid: bool
    violations: list[ConsistencyViolation] = field(default_factory=list)
    warnings: list[ConsistencyViolation] = field(default_factory=list)
    score: float = 1.0  # 0.0 - 1.0
    
    def summary(self) -> str:
        if self.is_valid:
            return f"Валидно (score: {self.score:.2f})"
        return f"Невалидно (score: {self.score:.2f}, violations: {len(self.violations)}, warnings: {len(self.warnings)})"


# ── Предустановленные правила ──────────────────────────────────

DEFAULT_RULES: list[ConsistencyRule] = [
    ConsistencyRule(
        id="temporal_no_future",
        name="No Future Knowledge",
        name_ru="Запрет знания будущего",
        description="Characters cannot know events that haven't happened yet.",
        description_ru="Персонажи не могут знать события, которые ещё не произошли.",
        rule_type=RuleType.TEMPORAL,
        severity=RuleSeverity.HARD,
        condition_text="Character knowledge cannot include future events",
        recovery_suggestion="Remove future knowledge from character context",
    ),
    ConsistencyRule(
        id="spatial_single_location",
        name="Single Location",
        name_ru="Единственная локация",
        description="A character cannot be in two places at the same time.",
        description_ru="Персонаж не может находиться в двух местах одновременно.",
        rule_type=RuleType.SPATIAL,
        severity=RuleSeverity.HARD,
        condition_text="Each character has exactly one location at any time",
        recovery_suggestion="Resolve to most likely location",
    ),
    ConsistencyRule(
        id="causal_no_effect_without_cause",
        name="No Effect Without Cause",
        name_ru="Нет действия без причины",
        description="Every significant change must have a documented cause.",
        description_ru="Каждое значительное изменение должно иметь причину.",
        rule_type=RuleType.CAUSAL,
        severity=RuleSeverity.HARD,
        condition_text="WorldDelta must reference at least one cause",
        recovery_suggestion="Add causal link or mark as 'unexplained mystery'",
    ),
    ConsistencyRule(
        id="technology_epoch_restriction",
        name="Technology Epoch Restriction",
        name_ru="Ограничение технологий по эпохе",
        description="Technologies cannot appear before their epoch of origin.",
        description_ru="Технологии не могут появиться до эпохи своего возникновения.",
        rule_type=RuleType.TEMPORAL,
        severity=RuleSeverity.HARD,
        condition_text="Technology.epoch_first must be <= current epoch",
        recovery_suggestion="Remove anachronistic technology",
    ),
    ConsistencyRule(
        id="symbol_meaning_consistency",
        name="Symbol Meaning Consistency",
        name_ru="Согласованность значений символов",
        description="A symbol cannot have contradictory meanings in the same context.",
        description_ru="Символ не может иметь противоречивых значений в одном контексте.",
        rule_type=RuleType.METAPHYSICAL,
        severity=RuleSeverity.SOFT,
        condition_text="Symbol meanings must not contradict each other",
        recovery_suggestion="Clarify primary meaning or add 'multi-layered meaning' note",
    ),
]


class ConsistencyEngine:
    """Движок проверки консистентности мира.
    
    Проверяет:
    - Временные ограничения
    - Пространственные ограничения
    - Причинные связи
    - Культурные нормы
    - Метафизические правила
    """
    
    def __init__(self, world_engine=None):
        self._world_engine = world_engine
        self._rules: list[ConsistencyRule] = DEFAULT_RULES.copy()
    
    def add_rule(self, rule: ConsistencyRule):
        """Добавить правило."""
        self._rules.append(rule)
    
    def get_rules(self) -> list[ConsistencyRule]:
        """Получить все правила."""
        return self._rules.copy()
    
    def validate_entity(self, entity: dict) -> ConsistencyReport:
        """Проверить сущность на соответствие правилам."""
        violations = []
        warnings = []
        
        for rule in self._rules:
            # Простая проверка для демонстрации
            if rule.rule_type == RuleType.TEMPORAL:
                # Проверка: персонаж не может знать будущее
                if entity.get("category") == "character":
                    # Упрощённая проверка
                    pass
            
            elif rule.rule_type == RuleType.SPATIAL:
                # Проверка: персонаж в одном месте
                if entity.get("category") == "character":
                    # Упрощённая проверка
                    pass
            
            elif rule.rule_type == RuleType.CAUSAL:
                # Проверка: у события есть причина
                if entity.get("category") == "event":
                    if not entity.get("cause"):
                        violations.append(ConsistencyViolation(
                            rule_id=rule.id,
                            rule_name=rule.name_ru,
                            severity=rule.severity,
                            description=f"Событие '{entity.get('name')}' не имеет явной причины",
                            involved_entities=[entity.get("id", "")],
                            suggested_fix=rule.recovery_suggestion,
                        ))
        
        # Вычисляем score
        total_checks = len(self._rules)
        violations_count = len(violations)
        warnings_count = len(warnings)
        
        if total_checks == 0:
            score = 1.0
        else:
            score = max(0.0, 1.0 - (violations_count * 0.2) - (warnings_count * 0.1))
        
        is_valid = violations_count == 0
        
        return ConsistencyReport(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            score=score,
        )
    
    def validate_world_state(self, world_state: dict) -> ConsistencyReport:
        """Проверить состояние мира."""
        all_violations = []
        all_warnings = []
        
        # Проверяем каждую сущность
        for category, items in world_state.items():
            if isinstance(items, list):
                for item in items:
                    report = self.validate_entity(item)
                    all_violations.extend(report.violations)
                    all_warnings.extend(report.warnings)
        
        # Вычисляем общий score
        total_entities = sum(
            len(items) if isinstance(items, list) else 1
            for items in world_state.values()
        )
        
        if total_entities == 0:
            score = 1.0
        else:
            score = max(0.0, 1.0 - (len(all_violations) * 0.1) - (len(all_warnings) * 0.05))
        
        return ConsistencyReport(
            is_valid=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings,
            score=score,
        )
    
    def summary(self) -> str:
        """Текстовая сводка."""
        return f"ConsistencyEngine: {len(self._rules)} правил"
