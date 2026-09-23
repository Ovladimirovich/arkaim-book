"""
NameResolver — единый реестр имён и алиасов персонажей.
Устраняет путаницу: Велик=Велиусмус=Великосвет=Велом, Славный=Мирослав=Всеслав и т.д.
"""

from pathlib import Path
from typing import Dict, List, Set

BASE = Path(__file__).resolve().parents[2]
GENOME_PATH = BASE / "GENOME" / "GENOME_v1.0.0.json"


# Канонические имена и все их варианты.
# Заполнено на основе анализа GENOME_v1.0.0.json и книги.
# При обнаружении новых алиасов — добавлять сюда.
CANONICAL_MAP = {
    "Велик": {"Велик", "Велиусмус", "Великосвет", "Велом", "Великосветом", "Велиусмусом"},
    "Велика": {"Велика"},
    "Славный": {"Славный", "Мирослав", "Всеслав", "Слава", "Славик", "Славного", "Славным"},
    "Световит": {"Световит", "Световитом"},
    "Учитель": {"Учитель", "Учителем", "Учителю", "Учителя"},
    "Архат": {"Архат", "Архата", "Архатом", "Высшее Существо", "Основатель Иерархии Света"},
    "Влад": {"Влад", "Владислав", "Владиславом"},
    "Вера": {"Вера", "Вероника", "Вероникой", "Веры"},
    "Наставники": {"Наставники", "Наставников", "Наставникам", "Посвящённые"},
    "Гипербореи": {"Гипербореи", "гиперборейцы", "гиперборейский народ"},
    "Любомир": {"Любомир"},
    "Святослав": {"Святослав"},
    "Яснобор": {"Яснобор"},
    "Коловед": {"Коловед"},
    "Радомир": {"Радомир"},
}


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
        Заменяет каждое вхождение любого алиаса на каноническое имя.
        """
        result = text
        for alias, canonical in sorted(
            self._alias_to_canonical.items(),
            key=lambda x: -len(x[0]),  # longer first to avoid partial replacements
        ):
            result = result.replace(alias, canonical)
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
