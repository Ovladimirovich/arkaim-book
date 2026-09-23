"""
ReaderAwarePulse — Pulse, который знает читателя.

Обогащает запрос контекстом из ReaderMemoryStore.
Понимает «расскажи подробнее» — находит последнюю тему.
"""
from typing import Optional
from pulse.pulse import BookPulse, PulseResponse


class ReaderAwarePulse:
    """
    Обёртка над BookPulse, которая добавляет память читателя.

    Перед тем как ответить:
    1. Проверяет, не «расскажи подробнее» ли это
    2. Если да — находит последнюю тему читателя и углубляет
    3. Если нет — обычный listen(), но с контекстом читателя
    """

    def __init__(self, pulse: BookPulse, reader_memory=None):
        self._pulse = pulse
        self._memory = reader_memory

    def set_reader_memory(self, reader_memory):
        self._memory = reader_memory

    def _is_deepen_request(self, query: str) -> bool:
        q = query.lower().strip()
        deepen = [
            "расскажи подробнее", "подробнее", "ещё", "продолжи",
            "расскажи ещё", "дальше", "что ещё", "уточни",
            "расскажи больше", "можно подробнее",
        ]
        return any(d == q or q.startswith(d) or q.endswith(d) for d in deepen)

    def _extract_topic(self, query: str) -> str:
        """Извлечь тему из вопроса, если явно указана."""
        q = query.lower()
        # Проверяем по известным персонажам/темам (через genome)
        if self._pulse.is_loaded:
            for ch in self._pulse.genome.get("modules", {}).get("characters", []):
                names = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases", [])]
                for name in names:
                    if name in q and len(name) > 2:
                        return ch["name"]
            for th in self._pulse.genome.get("modules", {}).get("themes", []):
                if th["name"].lower() in q:
                    return th["name"]
            for we in self._pulse.genome.get("world_entities", []):
                if we["name"].lower() in q:
                    return we["name"]
        return ""

    async def listen(self, query: str, reader_id: str = "") -> tuple[Optional[PulseResponse], dict]:
        """
        Выслушать вопрос с учётом памяти читателя.

        Возвращает (response, reader_context).
        reader_context — мета-информация о читателе.
        """
        reader_ctx = {}

        if not reader_id or not self._memory:
            return self._pulse.listen(query), reader_ctx

        # Получить профиль читателя (с fallback при ошибке БД)
        try:
            profile = await self._memory.get_or_create(reader_id)
        except Exception:
            return self._pulse.listen(query), reader_ctx

        # Проверить, не запрос ли это на углубление
        if self._is_deepen_request(query) and profile.last_topic:
            # Читатель хочет углубиться в последнюю тему
            topic = profile.last_topic
            reader_ctx["deepen_topic"] = topic
            reader_ctx["last_question"] = profile.last_question
            reader_ctx["last_answer"] = profile.last_answer
            reader_ctx["depth"] = profile.topics.get(topic, None)

            # Сформулировать вопрос для Pulse: «расскажи о [тема] глубже»
            enriched_query = f"Расскажи подробнее о {topic}"
            response = self._pulse.listen(enriched_query)
            if response:
                response.confidence = min(1.0, response.confidence + 0.1)
                return response, reader_ctx

        # Извлечь тему из вопроса
        topic = self._extract_topic(query)
        if topic:
            reader_ctx["topic"] = topic

        # Обычный ответ
        response = self._pulse.listen(query)
        return response, reader_ctx

    async def record(self, reader_id: str, question: str, answer: str, topic: str = "", pulse_source: str = "", provenance: list | None = None):
        """Записать взаимодействие в память читателя."""
        if self._memory and reader_id:
            # Если provenance содержит имя сущности — использовать её как тему
            if provenance:
                for p in provenance:
                    name = p.get("name", "")
                    if name and len(name) > 2:
                        topic = name
                        break
            await self._memory.record_interaction(reader_id, question, answer, topic, pulse_source)

    def __getattr__(self, name):
        return getattr(self._pulse, name)
