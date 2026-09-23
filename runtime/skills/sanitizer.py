import logging
import re

log = logging.getLogger(__name__)

_FORBIDDEN_PATTERNS = [
    (re.compile(r"\bGigaChat\b", re.IGNORECASE), "Hermes"),
    (r"\bI am a language model\b", "I am Hermes"),
    (r"\bI am an AI assistant\b", "I am Hermes"),
    (r"\bas a language model\b", "as Hermes"),
    (r"\bI am an LLM\b", "I am Hermes"),
    (r"\bI'm an AI\b", "I'm Hermes"),
]


def sanitize_response(text: str, trace_id: str = "") -> str:
    result = text
    for pattern, replacement in _FORBIDDEN_PATTERNS:
        if isinstance(pattern, str):
            if pattern.lower() in result.lower():
                log.info("sanitizer_leak pattern=%s trace_id=%s", pattern, trace_id)
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        else:
            if pattern.search(result):
                log.info("sanitizer_leak pattern=%s trace_id=%s", pattern.pattern, trace_id)
                result = pattern.sub(replacement, result)
    return result
