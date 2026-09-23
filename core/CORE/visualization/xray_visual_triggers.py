"""X-Ray Visual Triggers — data-driven наполнение Visual Genome.

Анализирует вопросы читателей (из X-Ray/ReaderMemory),
находит темы, по которым нет визуала,
создаёт задачи через PresenceSuggester.
"""
import logging
import re
from typing import Optional

log = logging.getLogger("hermes.visualization.xray_triggers")

# Паттерны вопросов о визуальных деталях
VISUAL_QUESTION_PATTERNS = [
    (r"(?:как\s+)?выгляд", "general_visual"),
    (r"как\s+(?:выглядит|выглядят)", "visual_description"),
    (r"опиш(?:и|ывай)\s+(?:внешность|вид)", "visual_appearance"),
    (r"во\s+что\s+одет", "clothing"),
    (r"какого\s+цвет", "color"),
    (r"как\s+(?:выглядит|выглядят)\s+(.+?)(?:\?|$)", "entity_visual"),
]

TOPIC_PATTERNS = {
    "location": [
        r"аркаим", r"гиперборея", r"атлантида", r"пещера",
        r"храм", r"город", r"святилище", r"гора",
    ],
    "character": [
        r"велик", r"славный", r"световит", r"вера",
        r"влад", r"учитель", r"радомир",
    ],
    "symbol": [
        r"амулет", r"символ", r"знак", r"руна",
    ],
}

MISSING_VISUAL_THRESHOLD = 5  # после скольких вопросов создавать задачу


class XRayVisualTriggers:
    """Анализирует вопросы и определяет, каких визуалов не хватает."""

    def __init__(self, threshold: int = MISSING_VISUAL_THRESHOLD):
        self._threshold = threshold
        self._missing_visuals: dict[str, int] = {}  # entity_key → count
        self._entity_types: dict[str, str] = {}     # entity_key → type

    def analyze_question(self, question: str):
        """Проанализировать вопрос читателя.

        Определяет, спрашивает ли пользователь о визуальном аспекте,
        и о какой именно сущности.
        """
        q = question.lower().strip()
        is_visual = False

        for pattern, kind in VISUAL_QUESTION_PATTERNS:
            if re.search(pattern, q):
                is_visual = True
                break

        if not is_visual:
            return

        # Определить, о какой сущности спрашивают
        for etype, patterns in TOPIC_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, q)
                if match:
                    entity_key = match.group(0)
                    self._missing_visuals[entity_key] = self._missing_visuals.get(entity_key, 0) + 1
                    self._entity_types[entity_key] = etype
                    log.debug("xray_trigger_visual entity=%s type=%s count=%d",
                              entity_key, etype, self._missing_visuals[entity_key])

    def get_missing_visuals(self) -> dict[str, dict]:
        """Вернуть список сущностей, превысивших порог.

        Формат: {entity_key: {"type": str, "count": int}}
        """
        result = {}
        for key, count in self._missing_visuals.items():
            if count >= self._threshold:
                result[key] = {
                    "type": self._entity_types.get(key, "unknown"),
                    "count": count,
                }
        return result

    def has_visual_in_genome(self, genome: dict, entity_key: str, entity_type: str) -> bool:
        """Проверить, есть ли уже visual для сущности в genome."""
        modules = genome.get("modules", {})

        if entity_type == "character":
            visuals = modules.get("character_visuals", [])
            for v in visuals:
                if entity_key.lower() in v.get("character_id", "").lower():
                    return True
            chars = modules.get("characters", [])
            for c in chars:
                if entity_key.lower() in c.get("name", "").lower():
                    return False
            return True  # если такого персонажа нет — не создавать задачу

        if entity_type == "location":
            visuals = modules.get("location_visuals", [])
            for v in visuals:
                if entity_key.lower() in v.get("location_id", "").lower():
                    return True
            return False

        return True

    def get_triggers_for_suggester(self, genome: dict) -> list[dict]:
        """Получить список триггеров для PresenceSuggester.

        Возвращает список dict-ов с полями:
        topic, reason, evidence, suggested_action.
        """
        triggers = []
        missing = self.get_missing_visuals()
        for key, info in missing.items():
            if self.has_visual_in_genome(genome, key, info["type"]):
                continue
            triggers.append({
                "topic": f"visual_missing:{info['type']}:{key}",
                "reason": (
                    f"Читатели спросили о визуальном аспекте «{key}» "
                    f"{info['count']} раз. Визуального описания нет."
                ),
                "suggested_action": "add_visual",
                "evidence": {
                    "entity_key": key,
                    "entity_type": info["type"],
                    "question_count": info["count"],
                    "source": "xray_visual_trigger",
                },
            })
        return triggers

    def reset(self):
        """Сбросить счётчики (после обработки)."""
        processed = dict(self._missing_visuals)
        self._missing_visuals.clear()
        self._entity_types.clear()
        return processed
