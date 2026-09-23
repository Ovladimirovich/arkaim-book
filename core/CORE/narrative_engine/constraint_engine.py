"""Constraint Engine — построение модели ограничений для Story Engine."""

import re
import logging
from typing import Optional
from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel, Epoch, Location, CharacterPresence

log = logging.getLogger("hermes.narrative.constraints")


class StoryRequest(BaseModel):
    """Запрос пользователя на создание истории."""
    prompt: str
    epoch: Optional[str] = None
    location: Optional[str] = None
    character_type: Optional[str] = None
    time_offset: Optional[str] = None
    max_length: int = 2000
    style: str = "literary"  # literary, documentary, poetic


class ResolvedContext(BaseModel):
    """Разрешённый контекст из World Model."""
    epoch: Optional[dict] = None
    location: Optional[dict] = None
    characters_alive: list[dict] = Field(default_factory=list)
    technologies_available: list[dict] = Field(default_factory=list)
    active_civilizations: list[dict] = Field(default_factory=list)
    nearby_events_before: list[dict] = Field(default_factory=list)
    nearby_events_after: list[dict] = Field(default_factory=list)
    applicable_rules: list[dict] = Field(default_factory=list)


class ConstraintModel(BaseModel):
    """Полная модель ограничений для генерации."""
    story_request: StoryRequest
    resolved_context: ResolvedContext
    hard_constraints: list[str] = Field(default_factory=list)
    soft_constraints: list[str] = Field(default_factory=list)
    forbidden_elements: list[str] = Field(default_factory=list)
    required_elements: list[str] = Field(default_factory=list)


# ── Парсинг промпта ──────────────────────────────────────

EPOCH_KEYWORDS = {
    "сатья юга": "satya_yuga", "сатья юге": "satya_yuga", "золотой век": "satya_yuga",
    "трета юга": "treta_yuga", "трета юге": "treta_yuga", "серебряный век": "treta_yuga",
    "двапара юга": "dvapara_yuga", "двапара юге": "dvapara_yuga", "бронзовый век": "dvapara_yuga",
    "кали юга": "kali_yuga", "кали юге": "kali_yuga", "тёмный век": "kali_yuga",
    "до аркаима": "pre_arkaim", "эпоха аркаима": "arkaim_era",
}

LOCATION_KEYWORDS = {
    "гиперборея": "hyperborea", "гиперборее": "hyperborea", "гиперборею": "hyperborea",
    "аркаим": "arkaim", "аркаима": "arkaim", "аркаиме": "arkaim",
    "тмутаракань": "tmutarakan", "шумер": "sumer",
    "индия": "india", "древняя русь": "rus",
}


def parse_prompt(prompt: str) -> StoryRequest:
    """Извлечь параметры из текстового промпта."""
    request = StoryRequest(prompt=prompt)
    prompt_lower = prompt.lower()

    # Определяем эпоху
    for keyword, epoch_id in EPOCH_KEYWORDS.items():
        if keyword in prompt_lower:
            request.epoch = epoch_id
            break

    # Определяем локацию
    for keyword, loc_id in LOCATION_KEYWORDS.items():
        if keyword in prompt_lower:
            request.location = loc_id
            break

    # Определяем тип персонажа
    char_patterns = [
        (r"гиперборее?ц", "hyperborean"),
        (r"жрец", "priest"),
        (r"воин", "warrior"),
        (r"учител", "teacher"),
        (r"мудрец", "sage"),
        (r"странник", "wanderer"),
        (r"ученик", "student"),
        (r"царь|князь", "ruler"),
    ]
    for pattern, char_type in char_patterns:
        if re.search(pattern, prompt_lower):
            request.character_type = char_type
            break

    # Определяем смещение времени
    offset_patterns = [
        r"за (\d+) лет до",
        r"через (\d+) лет после",
        r"(\d+) лет назад",
        r"в время",
        r"до появления",
        r"после событий",
    ]
    for pattern in offset_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            request.time_offset = match.group(0)
            break

    return request


# ── Построение ограничений ────────────────────────────────

def build_constraints(request: StoryRequest, world_model: WorldModel) -> ConstraintModel:
    """Построить модель ограничений из запроса и World Model."""
    # Разрешаем контекст
    context = _resolve_context(request, world_model)

    # Формируем ограничения
    hard_constraints = []
    soft_constraints = []
    forbidden = []
    required = []

    # Жёсткие ограничения по эпохе
    if context.epoch:
        ep = context.epoch
        hard_constraints.append(
            f"История происходит в эпоху {ep['name_ru']}. "
            f"Доступные технологии: {', '.join(t['name'] for t in context.technologies_available[:5])}."
        )
        if context.characters_alive:
            names = [c['character_name'] for c in context.characters_alive[:10]]
            hard_constraints.append(
                f"В этой эпохе живут: {', '.join(names)}. "
                f"Другие персонажи не могут появиться."
            )

    # Жёсткие ограничения по локации
    if context.location:
        loc = context.location
        hard_constraints.append(
            f"Действие происходит в {loc['name_ru']}. "
            f"География должна соответствовать описанию: {loc.get('description', '')}."
        )

    # Причинно-следственные правила
    for rule in context.applicable_rules:
        hard_constraints.append(f"Правило: {rule['description']}")

    # Мягкие ограничения
    if request.style == "literary":
        soft_constraints.append("Стиль: литературный, с описаниями природы и эмоций.")
    elif request.style == "documentary":
        soft_constraints.append("Стиль: документальный, фактический.")
    elif request.style == "poetic":
        soft_constraints.append("Стиль: поэтический, метафоричный.")

    if request.character_type:
        required.append(f"Главный герой — {request.character_type}.")

    # Запрещённые элементы
    forbidden.append("Нельзя упоминать события, которых ещё не было в этой эпохе.")
    forbidden.append("Нельзя нарушать географию мира.")
    forbidden.append("Нельзя использовать технологии, которых нет в этой эпохе.")

    return ConstraintModel(
        story_request=request,
        resolved_context=context,
        hard_constraints=hard_constraints,
        soft_constraints=soft_constraints,
        forbidden_elements=forbidden,
        required_elements=required,
    )


def _resolve_context(request: StoryRequest, world_model: WorldModel) -> ResolvedContext:
    """Разрешить контекст из World Model."""
    context = ResolvedContext()

    # Эпоха
    if request.epoch:
        epoch = world_model.get_epoch(request.epoch)
        if epoch:
            context.epoch = epoch.model_dump()

    # Если эпоха не задана, ищем по тексту
    if not context.epoch and request.prompt:
        epoch = world_model.find_epoch_by_text(request.prompt)
        if epoch:
            context.epoch = epoch.model_dump()

    # Локация
    if request.location:
        location = world_model.get_location(request.location)
        if location:
            context.location = location.model_dump()

    if not context.location and request.prompt:
        location = world_model.find_location_by_text(request.prompt)
        if location:
            context.location = location.model_dump()

    # Персонажи, живые в эпоху
    if context.epoch:
        epoch_id = context.epoch["id"]
        context.characters_alive = [
            p.model_dump() for p in world_model.get_characters_alive(epoch_id)
        ]
        context.technologies_available = [
            t.model_dump() for t in world_model.get_technologies(epoch_id)
        ]

    # События
    if context.epoch:
        events = world_model.get_events(context.epoch["id"])
        context.nearby_events_before = [e.model_dump() for e in events[:5]]

    # Правила
    context.applicable_rules = [r.model_dump() for r in world_model.get_rules()]

    return context

