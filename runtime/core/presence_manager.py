"""
presence_manager — интеграция Presence (наблюдение + предложения) в Runtime.

Инициализирует Observer, Suggester, TelegramPresence и Email.
TelegramPresence подключается к адаптеру отдельно, через wire_telegram_presence(),
чтобы не нарушать контракт core → integrations.
"""
import logging

from core.pulse_manager import get_pulse

log = logging.getLogger("hermes.presence_manager")

_observer = None
_suggester = None
_telegram_presence = None
_email_store = None


def init_presence():
    """Создать Observer, Suggester и EmailStore при старте Core."""
    global _observer, _suggester, _email_store

    from presence.observer import PresenceObserver
    from presence.suggester import PresenceSuggester
    from presence.email import SubscriberStore

    _observer = PresenceObserver()
    _suggester = PresenceSuggester()
    _email_store = SubscriberStore()

    log.info("presence_initialized")
    return _observer, _suggester


def init_telegram_presence():
    """Создать TelegramPresence (вызывается при старте Telegram адаптера)."""
    global _telegram_presence

    from presence.telegram_presence import TelegramPresence

    pulse = get_pulse()
    _telegram_presence = TelegramPresence(
        pulse=pulse,
        observer=get_observer(),
        suggester=get_suggester(),
    )
    log.info("telegram_presence_initialized keywords=%d", _telegram_presence.keyword_count)
    return _telegram_presence


def get_observer():
    if _observer is None:
        init_presence()
    return _observer


def get_suggester():
    if _suggester is None:
        init_presence()
    return _suggester


def get_telegram_presence():
    global _telegram_presence
    if _telegram_presence is None:
        init_telegram_presence()
    return _telegram_presence


def get_email_store():
    global _email_store
    if _email_store is None:
        init_presence()
    return _email_store


async def periodic_suggest():
    """Периодически создавать предложения из наблюдений. Вызывается по таймеру."""
    observer = get_observer()
    suggester = get_suggester()
    try:
        created = await suggester.suggest_from_observations(observer)
        if created:
            log.info("presence_suggestions_created count=%d", len(created))
    except Exception as e:
        log.error("presence_periodic_error %s", e)


def register_question(topic: str, question: str, answer: str):
    """Зарегистрировать вопрос читателя. Вызывается из /book/ask."""
    observer = get_observer()
    observer.register_topic_question(topic)


def register_keyword(keyword: str, source: str = "external"):
    """Зарегистрировать упоминание ключевого слова."""
    observer = get_observer()
    observer.register_keyword_hit(keyword, source)


def wire_presence_routes(router):
    """Подключить presence API роуты к book_routes."""
    from presence.api_routes import router as presence_router, set_deps
    set_deps(get_observer(), get_suggester())
    router.include_router(presence_router)

    from presence.email_api import router as email_router
    router.include_router(email_router)

    from community.crowdfunding_api import router as crowdfunding_router
    router.include_router(crowdfunding_router)


__all__ = [
    "init_presence", "init_telegram_presence",
    "get_observer", "get_suggester",
    "get_telegram_presence", "get_email_store",
    "get_pulse",
    "periodic_suggest", "register_question", "register_keyword",
    "wire_presence_routes",
]
