"""VisualKnowledgeBase — загрузчик и кэш всех визуальных библиотек."""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger("visual.knowledge_base")

_BASE_DIR = Path(__file__).parent


class VisualKnowledgeBase:
    """Загружает и кэширует все JSON-библиотеки из VISUAL_KNOWLEDGE/."""

    def __init__(self, base_path: Path | None = None):
        self._base = base_path or _BASE_DIR
        self._cache: dict[str, dict] = {}

    def load(self, name: str) -> dict:
        """Загрузить библиотеку по имени (без .json)."""
        if name not in self._cache:
            path = self._base / f"{name}.json"
            if path.exists():
                try:
                    self._cache[name] = json.loads(path.read_text("utf-8-sig"))
                    log.info("knowledge_loaded name=%s", name)
                except Exception as e:
                    log.error("knowledge_load_failed name=%s error=%s", name, e)
                    self._cache[name] = {}
            else:
                log.warning("knowledge_not_found name=%s", name)
                self._cache[name] = {}
        return self._cache[name]

    @property
    def locations(self) -> dict:
        return self.load("LOCATION_VISUALS")

    @property
    def characters(self) -> dict:
        return self.load("CHARACTER_VISUALS")

    @property
    def atmospheres(self) -> dict:
        return self.load("ATMOSPHERES")

    @property
    def symbols(self) -> dict:
        return self.load("VISUAL_SYMBOLS")

    @property
    def camera(self) -> dict:
        return self.load("CAMERA_LIBRARY")

    @property
    def styles(self) -> dict:
        return self.load("STYLE_LIBRARY")

    @property
    def shots(self) -> dict:
        return self.load("SHOT_LIBRARY")

    @property
    def video_rules(self) -> dict:
        return self.load("VIDEO_RULES")

    def list_libraries(self) -> list[str]:
        """Список доступных библиотек."""
        result = []
        for name in ("LOCATION_VISUALS", "CHARACTER_VISUALS", "ATMOSPHERES",
                      "VISUAL_SYMBOLS", "CAMERA_LIBRARY", "STYLE_LIBRARY",
                      "SHOT_LIBRARY", "VIDEO_RULES"):
            if (self._base / f"{name}.json").exists():
                result.append(name)
        return result

    def stats(self) -> dict:
        """Статистика по библиотекам."""
        return {
            name: len(self.load(name))
            for name in self.list_libraries()
        }


# Singleton
knowledge_base = VisualKnowledgeBase()
