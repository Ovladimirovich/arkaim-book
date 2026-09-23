"""Story Composer — LLM-композитор, оформляет модель как художественный текст.

Замена writer.py. Принимает NarrativePlan (не промпт!) и формирует
богатый промпт для LLM с полным контекстом мира.
"""

import logging
from typing import Optional

from narrative_engine.constraint_engine import ConstraintModel
from narrative_engine.context_assembler import FullContext
from narrative_engine.planner import NarrativePlan

log = logging.getLogger("hermes.narrative.composer")


def compose_prompt(
    constraints: ConstraintModel,
    context: FullContext,
    plan: NarrativePlan,
    style: str = "literary",
    max_length: int = 2000,
) -> dict:
    """
    Сформировать промпт для LLM на основе NarrativePlan.

    Возвращает dict с system_instruction и user_prompt.
    """
    req = constraints.story_request
    ctx = constraints.resolved_context

    # ── Системная инструкция ──
    system_parts = [
        "Ты — писатель, создающий историю в мире книги «Наследие Аркаима».",
        "Ты НЕ создаёшь мир — ты пишешь ВНУТРИ него.",
        "Ты получаешь готовую модель истории. Твоя задача — оформить её художественным текстом.",
        "Строго следуй всем ограничениям и структуре.",
        "",
        "ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:",
    ]
    for i, rule in enumerate(constraints.hard_constraints, 1):
        system_parts.append(f"{i}. {rule}")

    if constraints.forbidden_elements:
        system_parts.append("")
        system_parts.append("ЗАПРЕЩЕНО:")
        for f in constraints.forbidden_elements:
            system_parts.append(f"- {f}")

    if plan.constraints_for_llm:
        system_parts.append("")
        system_parts.append("ДОПОЛНИТЕЛЬНЫЕ ОГРАНИЧЕНИЯ ИЗ ПЛАНА:")
        for c in plan.constraints_for_llm:
            system_parts.append(f"- {c}")

    # ── Контекст мира ──
    world_parts = []
    if ctx.epoch:
        world_parts.append(f"ЭПОХА: {ctx.epoch.get('name_ru', '')}")
        world_parts.append(f"  Описание: {ctx.epoch.get('description', '')}")
    if ctx.location:
        world_parts.append(f"ЛОКАЦИЯ: {ctx.location.get('name_ru', '')}")
        world_parts.append(f"  Описание: {ctx.location.get('description', '')}")
    if ctx.characters_alive:
        world_parts.append("ПЕРСОНАЖИ В ЭТОЙ ЭПОХЕ:")
        for ch in ctx.characters_alive[:8]:
            world_parts.append(f"  - {ch.get('character_name', '')} ({ch.get('status', '')})")
    if ctx.technologies_available:
        world_parts.append("ТЕХНОЛОГИИ:")
        for tech in ctx.technologies_available[:5]:
            world_parts.append(f"  - {tech.get('name_ru', '')}")

    # ── Дерево причин-следствий ──
    cause_effect_parts = []
    if plan.cause_effect.nodes:
        cause_effect_parts.append("ДЕРЕВО ПРИЧИННО-СЛЕДСТВЕННЫХ СВЯЗЕЙ:")
        for node in plan.cause_effect.nodes:
            prefix = "→" if node.type == "effect" else "•"
            cause_effect_parts.append(f"  {prefix} [{node.type}] {node.description[:150]}")
        if plan.cause_effect.matched_pattern:
            cause_effect_parts.append(f"  Паттерн: {plan.cause_effect.matched_pattern}")

    # ── Арки персонажей ──
    character_parts = []
    if plan.character_arcs:
        character_parts.append("АРКИ ПЕРСОНАЖЕЙ:")
        for arc in plan.character_arcs:
            character_parts.append(f"  {arc.character}:")
            character_parts.append(f"    Начало: {arc.starting_state}")
            character_parts.append(f"    Конец: {arc.ending_state}")
            character_parts.append(f"    Мотивация: {arc.motivation}")
            character_parts.append(f"    Препятствие: {arc.obstacle}")
            character_parts.append(f"    Трансформация: {arc.transformation}")

    # ── Конфликтная дуга ──
    conflict_parts = []
    if plan.conflicts:
        conflict_parts.append("КОНФЛИКТНАЯ ДУГА:")
        for conflict in plan.conflicts[:1]:
            conflict_parts.append(f"  Тип: {conflict.conflict_type}")
            conflict_parts.append(f"  Источник напряжения: {conflict.tension_source}")
            conflict_parts.append(f"  Ставки: {conflict.stakes[:200]}")
            conflict_parts.append("  Структура:")
            for step in conflict.arc_structure:
                conflict_parts.append(f"    {step}")

    # ── Структура истории ──
    structure_parts = []
    if plan.story_structure:
        structure_parts.append("СТРУКТУРА ИСТОРИИ:")
        for i, step in enumerate(plan.story_structure, 1):
            structure_parts.append(f"  {i}. {step}")

    # ── Релевантные книжные отрывки ──
    book_parts = []
    if context.relevant_chunks:
        book_parts.append("ОТРЫВКИ ИЗ КНИГИ (для стиля и атмосферы):")
        for chunk in context.relevant_chunks[:3]:
            book_parts.append(f"  «{chunk[:200]}...»")

    # ── Сборка user_prompt ──
    user_parts = [
        "МИР:",
        "\n".join(world_parts) if world_parts else "Контекст мира не определён.",
        "",
        "ИСТОРИЯ:",
        "\n".join(cause_effect_parts) if cause_effect_parts else "Дерево причин не построено.",
        "",
        "ПЕРСОНАЖИ:",
        "\n".join(character_parts) if character_parts else "Арки не определены.",
        "",
        "КОНФЛИКТ:",
        "\n".join(conflict_parts) if conflict_parts else "Конфликт не определён.",
        "",
        "СТРУКТУРА:",
        "\n".join(structure_parts) if structure_parts else "Структура не определена.",
        "",
        f"СТИЛЬ: {style}. Максимум слов: {max_length}.",
        "",
        "ЗАДАНИЕ:",
        req.prompt,
        "",
        "Напиши историю, строго следуя всем ограничениям и структуре.",
        "Не нарушай канон мира. Не придумывай то, чего нет в контексте.",
        "Используй атмосферу и стиль из приведённых отрывков книги.",
    ]

    if book_parts:
        user_parts.extend(["", "\n".join(book_parts)])

    return {
        "system_instruction": "\n".join(system_parts),
        "user_prompt": "\n".join(user_parts),
    }


def format_composer_prompt(composed: dict) -> str:
    """Сформировать полный промпт для LLM из composed dict."""
    return f"{composed['system_instruction']}\n\n{composed['user_prompt']}"
