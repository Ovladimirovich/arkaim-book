"""
PresenceObserver — наблюдает за тем, что обсуждают читатели.

Источники:
- ReaderMemory: темы вопросов, их частота и глубина
- Telegram: ключевые слова в сообщениях читателей
- Обращения к книге: какие темы запрашивают чаще всего

Не делает ничего самостоятельно. Только собирает данные для Suggester.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from pulse.pulse import BookPulse
from core.memory.reader_memory import ReaderMemoryStore

log = logging.getLogger("hermes.presence.observer")


class PresenceObserver:
    """
    Наблюдатель. Смотрит, что обсуждают читатели.

    Не действует. Только собирает наблюдения.
    """

    def __init__(self, reader_memory: Optional[ReaderMemoryStore] = None, pulse: Optional[BookPulse] = None):
        self._memory = reader_memory
        self._pulse = pulse

        # Внутренний реестр наблюдений
        self._observations: dict[str, Observation] = {}

    def set_reader_memory(self, memory: ReaderMemoryStore):
        self._memory = memory

    def set_pulse(self, pulse: BookPulse):
        self._pulse = pulse

    # ── Наблюдения ────────────────────────────────

    async def observe_readers(self) -> list["Observation"]:
        """
        Посмотреть на ReaderMemory: какие темы обсуждают читатели.
        Возвращает список наблюдений — тем, которые набирают вес.
        """
        if not self._memory:
            return []

        stats = await self._memory.get_stats()
        total_questions = stats.get("total_questions", 0)
        if total_questions == 0:
            return []

        # Собрать наблюдения из ReaderMemory
        # (запрашиваем через эндпоинты — здесь используем прямой доступ)
        # Мы не имеем метода get_all_topics, так что идём через БД

        observations = []
        # Пока возвращаем пустой список — real-time наблюдение
        # будет через внешний вызов record_observation
        return observations

    def register_keyword_hit(self, keyword: str, source: str, context: str = ""):
        """
        Зарегистрировать, что кто-то упомянул тему из книги.

        Вызывается при обработке сообщений Telegram, вопросов через API и т.д.
        """
        if keyword not in self._observations:
            self._observations[keyword] = Observation(
                keyword=keyword,
                first_seen=datetime.now(tz=timezone.utc),
            )

        obs = self._observations[keyword]
        obs.hit_count += 1
        obs.last_seen = datetime.now(tz=timezone.utc)
        if source not in obs.sources:
            obs.sources.append(source)

    def register_topic_question(self, topic: str):
        """
        Зарегистрировать вопрос по теме.

        Вызывается при каждом /book/ask.
        """
        self.register_keyword_hit(topic, source="book_ask")

    async def get_trending_topics(self, min_hits: int = 3, hours: int = 24) -> list["Observation"]:
        """
        Получить «горячие» темы — те, которые набрали больше всего упоминаний.
        """
        now = datetime.now(tz=timezone.utc)
        now - timedelta(hours=hours)

        trending = []
        for obs in self._observations.values():
            if obs.hit_count >= min_hits:
                trending.append(obs)

        trending.sort(key=lambda o: o.hit_count, reverse=True)
        return trending


class Observation:
    """Одно наблюдение: тема, сколько раз упомянута, откуда."""

    def __init__(self, keyword: str, first_seen: Optional[datetime] = None):
        self.keyword = keyword
        self.first_seen = first_seen or datetime.now(tz=timezone.utc)
        self.last_seen = datetime.now(tz=timezone.utc)
        self.hit_count = 0
        self.sources: list[str] = []

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "hit_count": self.hit_count,
            "sources": self.sources,
        }
