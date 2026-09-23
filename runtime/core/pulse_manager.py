"""
pulse_manager — FastAPI-интеграция BookPulse + ReaderMemory в Runtime.

Живёт в runtime/core/ и предоставляет Pulse, Voice, ReaderMemory как зависимости.
CORE/ добавляется в sys.path один раз при старте (core/main.py).
"""
import logging
from pathlib import Path

from pulse.pulse import BookPulse
from pulse.voice import BookVoice
from core.memory.reader_memory import ReaderMemoryStore

log = logging.getLogger("hermes.pulse_manager")

_pulse: BookPulse | None = None
_voice: BookVoice | None = None
_reader_memory: ReaderMemoryStore | None = None


def init_pulse(genome_path: str | Path | None = None, retriever=None) -> BookPulse:
    """Создать и загрузить Pulse при старте Core. Инициализировать память читателей."""
    global _pulse, _voice, _reader_memory

    _pulse = BookPulse(genome_path=Path(genome_path) if genome_path else None)
    if retriever:
        _pulse.set_retriever(retriever)
    loaded = _pulse.load()

    _reader_memory = ReaderMemoryStore()

    _voice = BookVoice(_pulse)
    _voice.set_reader_memory(_reader_memory)

    # Подключить LLM как микрофон для Voice
    log.info("voice_llm_starting")
    try:
        from llm_client import LLMClient
        log.info("voice_llm_imported OK")
        _llm_client = LLMClient()
        log.info("voice_llm_created OK url=%s model=%s", _llm_client.url, _llm_client.model)
        _voice.set_llm(_llm_client)
        log.info("voice_llm_set OK voice._llm=%s", type(_voice._llm).__name__)
    except Exception as e:
        log.error("voice_llm_error %s: %s", type(e).__name__, e)

    if loaded:
        log.info("pulse_initialized version=%s", _pulse.state.genome_version)
    else:
        log.warning("pulse_not_loaded — genome file not found")
    return _pulse


def get_pulse() -> BookPulse:
    if _pulse is None:
        init_pulse()
    return _pulse


def get_voice() -> BookVoice:
    global _voice
    if _voice is None:
        _pulse = get_pulse()
        _voice = BookVoice(_pulse)
        # Подключить LLM к новому Voice
        try:
            from llm_client import LLMClient
            _llm_client = LLMClient()
            _voice.set_llm(_llm_client)
            log.info("voice_created_fresh_with_llm")
        except Exception as e:
            log.warning("voice_created_fresh_no_llm %s", e)
    return _voice


def get_reader_memory() -> ReaderMemoryStore:
    global _reader_memory
    if _reader_memory is None:
        init_pulse()
    return _reader_memory


def set_llm_for_voice(llm_client):
    v = get_voice()
    v.set_llm(llm_client)


def pulse_beat():
    """Сделать такт жизни Pulse. Вызывается периодически."""
    p = get_pulse()
    if p and p.is_loaded:
        beat = p.beat()
        log.debug("pulse_beat count=%d", beat.state.beats_count)


__all__ = [
    "init_pulse", "get_pulse", "get_voice", "get_reader_memory",
    "set_llm_for_voice", "pulse_beat",
]
