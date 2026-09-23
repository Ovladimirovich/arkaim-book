"""
ExpansionLoader — загрузчик расширенных знаний для Pulse ExpansionLayer.
"""
import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("hermes.knowledge_expansion.expansion_loader")

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "core" / "KNOWLEDGE"


class ExpansionLoader:
    """Загружает расширенные знания из JSON-файлов пайплайна."""

    def __init__(self, knowledge_dir: Path = None):
        self._dir = knowledge_dir or KNOWLEDGE_DIR
        self._knowledge: dict[str, dict] = {}

    def load(self) -> dict[str, dict]:
        """Загрузить все расширенные знания."""
        self._knowledge.clear()

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

        log.info("expansion_loaded topics=%d", len(self._knowledge))
        return self._knowledge

    def _load_file(self, path: Path):
        """Загрузить один файл."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    topic = item.get("topic", "").lower()
                    if topic:
                        self._knowledge[topic] = item
            elif isinstance(data, dict) and "themes" in data:
                # Формат THEMES_DEEP.json - массив тем внутри объекта
                for item in data["themes"]:
                    topic = item.get("name", item.get("topic", "")).lower()
                    if topic:
                        self._knowledge[topic] = item
        except Exception as e:
            log.warning("load_error path=%s error=%s", path, e)

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
