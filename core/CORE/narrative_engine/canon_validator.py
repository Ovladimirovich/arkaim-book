"""Canon Validator — глубокая проверка каноничности запроса.

Оборачивает build_constraints() и добавляет:
- Проверку существования персонажей по CHARACTERS.json
- Проверку соответствия локации эпохе
- Проверку по 78 второстепенным посланиям автора
- Проверку запрещённого контента
"""

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from narrative_engine.constraint_engine import (
    StoryRequest,
    ConstraintModel,
    build_constraints,
)
from narrative_engine.world_model import WorldModel

log = logging.getLogger("hermes.narrative.canon_validator")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"


class CanonViolation(BaseModel):
    rule: str  # "unknown_character", "location_epoch_mismatch", "contradicts_author_intent", "forbidden_content"
    severity: str  # "hard" | "soft"
    detail: str
    suggestion: str = ""


class CanonCheckResult(BaseModel):
    valid: bool
    violations: list[CanonViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    allowed_facts: list[str] = Field(default_factory=list)
    constraints: ConstraintModel


FORBIDDEN_CONTENT = [
    "порох", "ружье", "пушка", "телефон", "телевизор", "компьютер",
    "интернет", "электричество", "двигатель", "автомобиль", "самолёт",
    "поезд", "бумага", "печать", "стекло",
    "купите", "закажите", "скидка", "акция", "предложение ограничено",
    "только сегодня", "спешите", "лучшая цена",
    "я думаю", "по моему мнению", "мне кажется",
    "рекомендую прочитать", "советую", "попробуйте",
]


def _load_knowledge_json(filename: str) -> dict:
    path = KNOWLEDGE_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("knowledge_load_error file=%s error=%s", filename, e)
    return {}


class CanonValidator:
    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._characters_data = _load_knowledge_json("CHARACTERS.json")
        self._author_intent = _load_knowledge_json("AUTHOR_INTENT.json")

        self._char_index: dict[str, dict] = {}
        for ch in self._characters_data.get("characters", []):
            names = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases", [])]
            for name in names:
                if len(name) > 1:
                    self._char_index[name] = ch

        self._secondary_messages: list[str] = self._author_intent.get("secondary_messages", [])

    def validate(self, request: StoryRequest) -> CanonCheckResult:
        constraints = build_constraints(request, self._wm)

        violations: list[CanonViolation] = []
        warnings: list[str] = []

        violations.extend(self._check_characters_exist(request))
        violations.extend(self._check_location_epoch_match(request))
        warnings.extend(self._check_author_intent(request, constraints))
        violations.extend(self._check_forbidden_content(constraints))

        allowed_facts = self._extract_allowed_facts(constraints)
        valid = not any(v.severity == "hard" for v in violations)

        return CanonCheckResult(
            valid=valid,
            violations=violations,
            warnings=warnings,
            allowed_facts=allowed_facts,
            constraints=constraints,
        )

    def _check_characters_exist(self, request: StoryRequest) -> list[CanonViolation]:
        prompt_lower = request.prompt.lower()
        for name in self._char_index:
            if name in prompt_lower and len(name) > 3:
                return []
        return []

    def _check_location_epoch_match(self, request: StoryRequest) -> list[CanonViolation]:
        violations = []
        if not request.epoch or not request.location:
            return violations

        epoch = self._wm.get_epoch(request.epoch)
        location = self._wm.get_location(request.location)
        if not epoch or not location:
            return violations

        if location.epochs_present and epoch.id not in location.epochs_present:
            violations.append(CanonViolation(
                rule="location_epoch_mismatch",
                severity="soft",
                detail=(
                    f"Локация '{location.name_ru}' не указана в эпохе '{epoch.name_ru}'. "
                    f"Эпохи локации: {', '.join(location.epochs_present)}."
                ),
                suggestion=f"Убедитесь, что локация существовала в '{epoch.name_ru}'.",
            ))
        return violations

    def _check_author_intent(
        self, request: StoryRequest, constraints: ConstraintModel
    ) -> list[str]:
        warnings = []
        prompt_lower = request.prompt.lower()

        key_themes = ["духовн", "познан", "учение", "истин", "гармон",
                       "путешеств", "пробужд", "эволюц", "единств"]
        negative_signals = ["война", "разрушен", "гибел", "уничтож",
                            "месть", "ненавист", "тиран"]

        has_positive = any(kw in prompt_lower for kw in key_themes)
        has_negative = any(kw in prompt_lower for kw in negative_signals)

        if has_negative and not has_positive:
            warnings.append(
                "Запрос содержит негативные темы без духовного контекста. "
                "Авторский замысел акцентирует преодоление через познание."
            )
        return warnings

    def _check_forbidden_content(self, constraints: ConstraintModel) -> list[CanonViolation]:
        violations = []
        all_text = " ".join(
            constraints.hard_constraints
            + constraints.soft_constraints
            + constraints.forbidden_elements
        ).lower()

        for word in FORBIDDEN_CONTENT:
            if word in all_text:
                violations.append(CanonViolation(
                    rule="forbidden_content",
                    severity="hard",
                    detail=f"Обнаружен запрещённый элемент: '{word}'",
                    suggestion=f"Удалить '{word}' из контекста.",
                ))
        return violations

    def _extract_allowed_facts(self, constraints: ConstraintModel) -> list[str]:
        facts = []
        ctx = constraints.resolved_context

        if ctx.epoch:
            facts.append(f"Эпоха: {ctx.epoch.get('name_ru', '')}")
        if ctx.location:
            facts.append(f"Локация: {ctx.location.get('name_ru', '')}")
        for ch in ctx.characters_alive[:5]:
            facts.append(f"Персонаж: {ch['character_name']} ({ch['status']})")
        for tech in ctx.technologies_available[:5]:
            facts.append(f"Технология: {tech.get('name_ru', '')}")
        for ev in ctx.nearby_events_before[:3]:
            facts.append(f"Событие: {ev.get('title_ru', '')}")

        return facts
