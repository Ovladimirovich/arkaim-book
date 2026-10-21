# -*- coding: utf-8 -*-
"""Guard: единый реестр имён персонажей.

Ранее существовали две несогласованные таблицы:
  - core/CORE/intelligence/nameresolver.py (CANONICAL_MAP) — RAG-слой;
  - core/CORE/knowledge/screenplay_scene_aliases.py — сценарная таблица,
    утверждённая владельцем.

Они противоречили друг другу: nameresolver склеивал «Слава»/«Всеслав» с
«Славным» и «Архат» с «Высшим Существом», тогда как утверждённая
владельцем таблица это запрещает. Теперь nameresolver СОБИРАЕТСЯ из
утверждённой таблицы, поэтому расхождение невозможно по построению — а
тест ниже фиксирует это свойство.

Тесты:
  1. каждое утверждённое написание разрешается одинаково в обоих слоях;
  2. запрещённые владельцем склейки отсутствуют;
  3. короткие написания исключены из RAG-слоя осознанно (границы слова);
  4. resolve_text подменяет имя только по границам слова.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_ROOT = REPO_ROOT / "core" / "CORE"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from intelligence.nameresolver import (  # noqa: E402
    CANONICAL_MAP,
    MIN_SUBSTRING_ALIAS_LENGTH,
    NameResolver,
)
from knowledge.screenplay_scene_aliases import (  # noqa: E402
    APPROVED_ALIASES,
    canonical_for_surface,
)


@pytest.fixture()
def resolver() -> NameResolver:
    return NameResolver()


# ── 1. Утверждённые написания разрешаются одинаково ────────────────────


@pytest.mark.parametrize("canonical", sorted(APPROVED_ALIASES))
def test_approved_surfaces_resolve_to_approved_canonical(canonical: str, resolver: NameResolver) -> None:
    """Каждое утверждённое написание ведёт в канон сценарной таблицы."""
    for surface in APPROVED_ALIASES[canonical]:
        expected = canonical_for_surface(surface)
        assert expected == canonical, f"{surface!r} должен вести в {canonical!r}"
        if len(surface) < MIN_SUBSTRING_ALIAS_LENGTH:
            continue  # короткие написания исключены осознанно (тест 3)
        assert resolver.resolve(surface) == canonical, f"{surface!r} разрешается иначе в RAG-слое"


def test_canonical_map_is_derived_from_approved_table() -> None:
    """Реестр RAG-слоя не содержит соответствий, которых нет в утверждённой таблице."""
    approved_surfaces = {s for surfaces in APPROVED_ALIASES.values() for s in surfaces}
    from intelligence.nameresolver import EXTENSION_ALIASES, MORPHOLOGICAL_FORMS

    known = set(approved_surfaces)
    for forms in MORPHOLOGICAL_FORMS.values():
        known.update(forms)
    for forms in EXTENSION_ALIASES.values():
        known.update(forms)

    for canonical, aliases in CANONICAL_MAP.items():
        for alias in aliases:
            if alias == canonical:
                continue
            assert alias in known, f"алиас {alias!r} (канон {canonical!r}) не имеет источника в утверждённой таблице"


# ── 2. Запрещённые владельцем склейки отсутствуют ──────────────────────


@pytest.mark.parametrize(
    "surface",
    [
        "Слава",
        "Всеслав",
        "Высшее Существо",
        "Основатель Иерархии Света",
        "Посвящённые",
    ],
)
def test_forbidden_merges_are_absent(surface: str, resolver: NameResolver) -> None:
    """Правила владельца: эти написания не склеиваются с персонажами."""
    assert resolver.resolve(surface) == surface, f"{surface!r} не должен склеиваться с именем персонажа"


def test_arkhat_and_teacher_stay_separate(resolver: NameResolver) -> None:
    assert resolver.resolve("Архат") == "Архат"
    assert resolver.resolve("Учитель") == "Учитель"
    assert resolver.resolve("Учитель Человечества") == "Учитель Человечества"


def test_arkhat_group_has_no_titles(resolver: NameResolver) -> None:
    aliases = resolver.get_all_aliases("Архат")
    assert "Высшее Существо" not in aliases
    assert "Основатель Иерархии Света" not in aliases


# ── 3. Короткие написания исключены осознанно ──────────────────────────


def test_short_surfaces_excluded_from_rag_layer(resolver: NameResolver) -> None:
    """«Вел» не используется в RAG-слое: подстрока даёт ложные упоминания."""
    assert len("Вел") < MIN_SUBSTRING_ALIAS_LENGTH
    assert "Вел" not in resolver.get_all_aliases("Велик")
    # при этом в утверждённой сценарной таблице «Вел» остаётся
    assert "Вел" in APPROVED_ALIASES["Велик"]


# ── 4. resolve_text подменяет только по границам слова ──────────────────


def test_resolve_text_respects_word_boundaries(resolver: NameResolver) -> None:
    """«Велик» внутри «Великий» — другое слово, подмены быть не должно."""
    text = "Великий путь и Велик из славы"
    result = resolver.resolve_text(text)
    assert "Великий путь" in result
    assert "Велик из" in result


def test_resolve_text_is_case_insensitive(resolver: NameResolver) -> None:
    assert resolver.resolve_text("велик пришёл") == "Велик пришёл"
