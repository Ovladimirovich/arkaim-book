"""
TelegramPresence — книга слушает, что говорят в Telegram-чате.

Извлекает ключевые слова из сообщений (персонажи, темы, символы),
регистрирует в PresenceObserver и создаёт предложения автору.
"""
import logging
import re
from typing import Optional

from pulse.pulse import BookPulse
from presence.suggester import PresenceSuggester

log = logging.getLogger("hermes.telegram_presence")


class TelegramPresence:
    """
    Слушатель Telegram-чата.

    При каждом сообщении проверяет, не упомянута ли тема из книги.
    Если да — регистрирует наблюдение и (при пороге) создаёт предложение.
    """

    def __init__(self, pulse: Optional[BookPulse] = None, observer=None, suggester: Optional[PresenceSuggester] = None):
        self._pulse = pulse
        self._observer = observer
        self._suggester = suggester
        self._keywords: list[dict] = []  # кеш ключевых слов из генома
        self._keyword_pattern: Optional[re.Pattern] = None
        self._min_hits_for_suggestion = 5

    def set_pulse(self, pulse: BookPulse):
        self._pulse = pulse
        self._build_keywords()

    def set_observer(self, observer):
        self._observer = observer

    def set_suggester(self, suggester: PresenceSuggester):
        self._suggester = suggester

    def _build_keywords(self):
        """Построить список ключевых слов из генома."""
        if not self._pulse or not self._pulse.is_loaded:
            return
        self._keywords = []
        genome = self._pulse.genome

        for ch in genome.get("modules", {}).get("characters", []):
            names = [ch["name"]] + ch.get("aliases", [])
            for n in names:
                if len(n) > 2:
                    self._keywords.append({"word": n, "type": "character", "entity": ch["name"]})
        for th in genome.get("modules", {}).get("themes", []):
            if len(th["name"]) > 2:
                self._keywords.append({"word": th["name"], "type": "theme", "entity": th["name"]})
        for sym in genome.get("modules", {}).get("symbols", []):
            if len(sym["name"]) > 2:
                self._keywords.append({"word": sym["name"], "type": "symbol", "entity": sym["name"]})
        for we in genome.get("world_entities", []):
            if len(we["name"]) > 2:
                self._keywords.append({"word": we["name"], "type": "world_entity", "entity": we["name"]})

        # Построить regex для быстрого поиска
        if self._keywords:
            escaped = [re.escape(k["word"]) for k in self._keywords]
            self._keyword_pattern = re.compile("|".join(escaped), re.IGNORECASE)
        log.info("telegram_presence_keywords count=%d", len(self._keywords))

    def process_message(self, text: str, chat_id: str = "", user_id: str = "") -> list[str]:
        """
        Обработать одно сообщение из Telegram.

        Возвращает список найденных ключевых слов.
        """
        if not self._keyword_pattern or not text:
            return []

        found = set()
        for match in self._keyword_pattern.finditer(text):
            word = match.group(0)
            # Найти оригинальное имя (с учётом регистра из генома)
            for kw in self._keywords:
                if kw["word"].lower() == word.lower():
                    found.add(kw["entity"])
                    break

        found_list = list(found)

        # Зарегистрировать в Observer
        if self._observer and found_list:
            for entity in found_list:
                self._observer.register_keyword_hit(entity, source="telegram", context=text[:200])

        # Проверить порог и создать предложение
        if self._suggester and self._observer:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._check_suggestions())
            except RuntimeError:
                pass

        return found_list

    async def _check_suggestions(self):
        """Проверить, не пора ли создать предложения на основе наблюдений."""
        if not self._observer or not self._suggester:
            return
        trending = await self._observer.get_trending_topics(min_hits=self._min_hits_for_suggestion)
        for obs in trending:
            if "telegram" in obs.sources:
                self._suggester.suggest(
                    topic=obs.keyword,
                    reason=f"Тема упоминается в Telegram-чате ({obs.hit_count} раз)",
                    suggested_action="write_post",
                    evidence={
                        "hits": obs.hit_count,
                        "sources": obs.sources,
                        "last_seen": obs.last_seen.isoformat(),
                    },
                )

    @property
    def keyword_count(self) -> int:
        return len(self._keywords)
