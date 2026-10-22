"""
ExpansionLoader — загрузчик расширенных знаний для Pulse ExpansionLayer.
"""

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.knowledge_expansion.expansion_loader")

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "core" / "KNOWLEDGE"

#: Контейнеры, в которых пайплайн складывает записи, и ключ темы в них.
#: Формат ``items`` — универсальный вывод пайплайна (тема в ``topic``,
#: текст в ``content``). Форматы ``themes``/``symbols``/``archetypes`` —
#: именованные списки (тема в ``name``, текст в ``layers.literal``).
#: Ключ ``cosmology`` не входит: это одна запись, разложенная по полям,
#: а не список тем.
ENTRY_CONTAINERS: tuple[tuple[str, str], ...] = (
    ("themes", "name"),
    ("items", "topic"),
    ("symbols", "name"),
    ("archetypes", "name"),
)


def _entry_has_content(item: dict) -> bool:
    """Есть ли в записи содержание.

    Пустая оболочка (есть тема, но нет ни текста, ни слоёв) — это не знание.
    Такие записи не попадают в ExpansionLayer: иначе слой насчитывал бы темы,
    которых в нём нет (та же ошибка, что была с пустыми зеркалами).
    """
    if str(item.get("content") or "").strip():
        return True
    layers = item.get("layers")
    if isinstance(layers, dict):
        return any(str(value or "").strip() for value in layers.values())
    return False


class ExpansionLoader:
    """Загружает расширенные знания из JSON-файлов пайплайна."""

    def __init__(self, knowledge_dir: Path = None):
        self._dir = knowledge_dir or KNOWLEDGE_DIR
        self._knowledge: dict[str, dict] = {}
        self._skipped_empty = 0
        self._skipped_untitled = 0

    def load(self) -> dict[str, dict]:
        """Загрузить все расширенные знания."""
        self._knowledge.clear()
        self._skipped_empty = 0
        self._skipped_untitled = 0

        # Собираем все DEEP файлы
        deep_files = list(self._dir.glob("*_DEEP.json"))

        # Сначала загружаем обычные DEEP файлы (не THEMES_DEEP)
        for f in deep_files:
            if f.name != "THEMES_DEEP.json":
                self._load_file(f)

        # Потом THEMES_DEEP.json (перезаписывает предыдущие данные для тех же тем)
        themes_file = self._dir / "THEMES_DEEP.json"
        if themes_file.exists():
            self._load_file(themes_file)

        # EXPANDED файлы
        for f in self._dir.glob("*_EXPANDED.json"):
            self._load_file(f)

        # Академические подтверждения
        academic_file = self._dir / "ACADEMIC_CONFIRMATIONS.json"
        if academic_file.exists():
            self._load_academic(academic_file)

        log.info(
            "expansion_loaded topics=%d skipped_empty=%d skipped_untitled=%d",
            len(self._knowledge),
            self._skipped_empty,
            self._skipped_untitled,
        )
        return self._knowledge

    @property
    def stats(self) -> dict:
        """Счётчики загрузки: сколько тем и сколько пропущено."""
        return {
            "topics": len(self._knowledge),
            "skipped_empty": self._skipped_empty,
            "skipped_untitled": self._skipped_untitled,
        }

    def _add_item(self, item: object, topic_key: str) -> None:
        """Добавить запись в реестр, если у неё есть тема и содержание."""
        if not isinstance(item, dict):
            return
        topic = str(
            item.get(topic_key) or item.get("name") or item.get("topic") or ""
        ).strip()
        if not topic:
            self._skipped_untitled += 1
            return
        if not _entry_has_content(item):
            self._skipped_empty += 1
            return
        self._knowledge[topic.lower()] = item

    def _load_file(self, path: Path):
        """Загрузить один файл."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("load_error path=%s error=%s", path, e)
            return

        if isinstance(data, list):
            for item in data:
                self._add_item(item, "topic")
            return
        if not isinstance(data, dict):
            return
        for container, topic_key in ENTRY_CONTAINERS:
            items = data.get(container)
            if not isinstance(items, list):
                continue
            for item in items:
                self._add_item(item, topic_key)

    def get(self, topic: str) -> Optional[dict]:
        """Получить знания по теме."""
        return self._knowledge.get(topic.lower())

    def _load_academic(self, path: Path):
        """Загрузить академические подтверждения."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for conf in data.get("confirmations", []):
                topic = conf.get("category", "").lower()
                if topic:
                    self._knowledge[topic] = conf
        except Exception as e:
            log.warning("load_academic_error path=%s error=%s", path, e)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Поиск по запросу."""
        query_lower = query.lower()
        results = []
        for topic, data in self._knowledge.items():
            score = 0
            if query_lower in topic:
                score = 10
            else:
                query_words = set(query_lower.split())
                topic_words = set(topic.split())
                overlap = len(query_words & topic_words)
                if overlap > 0:
                    score = overlap / max(len(query_words), len(topic_words)) * 5
            if score > 0:
                results.append({"topic": topic, "data": data, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
