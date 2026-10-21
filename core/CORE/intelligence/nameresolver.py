"""
NameResolver — реестр имён и алиасов персонажей для RAG-слоя.

Источник истины для СЕМАНТИЧЕСКИХ соответствий («это написание означает
того же персонажа») — утверждённая владельцем таблица
``knowledge.screenplay_scene_aliases.APPROVED_ALIASES``. Здесь она не
дублируется: группы собираются из неё, поэтому две таблицы не могут
разойтись. Сверх неё добавляется только морфология — падежные формы того
же имени, — и явно перечисленные расширения.

Намеренно НЕ склеиваются (правила владельца, см. screenplay_scene_aliases):
  - «Слава» и «Всеслав» — обычные слова, а не имя персонажа;
  - «Архат» и «Высшее Существо» / «Основатель Иерархии Света»;
  - «Наставники» и «Посвящённые».

Модуль не хранит состояния и не читает файлы.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set

from knowledge.screenplay_scene_aliases import APPROVED_ALIASES

BASE = Path(__file__).resolve().parents[2]
GENOME_PATH = BASE / "GENOME" / "GENOME_v1.0.0.json"

#: Минимальная длина написания, пригодного для поиска подстрокой.
#: «Вел» (3 символа) для RAG-слоя не годится: вхождение внутри «великий»,
#: «свели» и т.п. даёт ложные упоминания персонажа. В сценарной таблице
#: «Вел» остаётся — там написание ловится регулярным выражением с
#: границами слова, а не подстрокой.
MIN_SUBSTRING_ALIAS_LENGTH = 4

#: Падежные формы того же имени. Идентичность сущности не меняют.
MORPHOLOGICAL_FORMS: dict[str, tuple[str, ...]] = {
    "Велик": ("Великосветом", "Велиусмусом"),
    "Славный": ("Славного", "Славным"),
    "Световит": ("Световитом",),
    "Учитель": ("Учителем", "Учителю", "Учителя"),
    "Архат": ("Архата", "Архатом"),
    "Влад": ("Владиславом",),
    "Вера": ("Вероникой", "Веры"),
    "Наставники": ("Наставников", "Наставникам"),
}

#: Расширения поверх утверждённых правил — те же сущности, другие
#: словоформы. Не склейка по смыслу: сущность не меняется.
EXTENSION_ALIASES: dict[str, tuple[str, ...]] = {
    "Гипербореи": ("гиперборейский народ",),
}

#: Каноны без утверждённых соответствий.
SOLO_CANONICALS: tuple[str, ...] = (
    "Велика",
    "Любомир",
    "Святослав",
    "Яснобор",
    "Коловед",
    "Радомир",
)


def _build_canonical_map() -> dict[str, set[str]]:
    """Собрать реестр из утверждённой таблицы + морфологии + расширений."""
    groups: dict[str, set[str]] = {}

    for canonical, surfaces in APPROVED_ALIASES.items():
        group = groups.setdefault(canonical, {canonical})
        for surface in surfaces:
            if len(surface) >= MIN_SUBSTRING_ALIAS_LENGTH:
                group.add(surface)

    for canonical, forms in MORPHOLOGICAL_FORMS.items():
        groups.setdefault(canonical, {canonical}).update(forms)

    for canonical, forms in EXTENSION_ALIASES.items():
        groups.setdefault(canonical, {canonical}).update(forms)

    for canonical in SOLO_CANONICALS:
        groups.setdefault(canonical, {canonical})

    return groups


#: Канонические имена и все их варианты. Собирается автоматически из
#: утверждённой владельцем таблицы — расхождение с ней невозможно по
#: построению. Добавлять новое написание — только в
#: screenplay_scene_aliases.APPROVED_ALIASES.
CANONICAL_MAP: dict[str, set[str]] = _build_canonical_map()


class NameResolver:
    def __init__(self):
        self._alias_to_canonical: Dict[str, str] = {}
        self._canonical_to_aliases: Dict[str, Set[str]] = {}
        self._build_index()

    def _build_index(self):
        """Строит обратный индекс: любой алиас -> каноническое имя."""
        for canonical, aliases in CANONICAL_MAP.items():
            self._canonical_to_aliases[canonical] = aliases
            for alias in aliases:
                self._alias_to_canonical[alias.lower()] = canonical

    def resolve(self, name: str) -> str:
        """Возвращает каноническое имя для любого варианта."""
        return self._alias_to_canonical.get(name.lower(), name)

    def get_all_aliases(self, canonical: str) -> Set[str]:
        """Возвращает все варианты имени."""
        return self._canonical_to_aliases.get(canonical, {canonical})

    def get_all_canonical(self) -> List[str]:
        """Все канонические имена."""
        return list(self._canonical_to_aliases.keys())

    def resolve_text(self, text: str) -> str:
        """
        Нормализует все имена в тексте до канонических.

        Замена идёт по границам слова: «Велик» внутри «Великий» — другое
        слово и подменяться не должно. Регистр не учитывается, поэтому
        написание заменяется в любом регистре.
        """
        result = text
        for alias, canonical in sorted(
            self._alias_to_canonical.items(), key=lambda x: -len(x[0])
        ):
            pattern = re.compile(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)", re.IGNORECASE
            )
            result = pattern.sub(canonical, result)
        return result

    def expand_query(self, query: str) -> List[str]:
        """
        Расширяет поисковый запрос: если слово — алиас, добавляет все варианты.
        Пример: "Великосвет" -> ["Великосвет", "Велик", "Велиусмус", "Велом"]
        """
        words = query.split()
        expanded = set()
        for w in words:
            canonical = self.resolve(w)
            if canonical != w:
                expanded.update(self.get_all_aliases(canonical))
            else:
                expanded.add(w)
        return list(expanded)

    def get_stats(self) -> Dict:
        return {
            "canonical_names": len(self._canonical_to_aliases),
            "total_aliases": len(self._alias_to_canonical),
            "largest_group": max(len(v) for v in self._canonical_to_aliases.values()),
            "largest_group_name": max(
                self._canonical_to_aliases.keys(),
                key=lambda k: len(self._canonical_to_aliases[k]),
            ),
        }
