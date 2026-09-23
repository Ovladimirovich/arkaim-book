import logging
import re

from observability.metrics import metrics

log = logging.getLogger("hermes.core.identity")

# Forbidden identity patterns — semantic-level, NOT word-level.
# When a provider leaks its identity, we repair at sentence level.
FORBIDDEN_IDENTITY_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bI am (?:a |an )?(?:GPT|GigaChat|Claude|OpenRouter|language model|AI assistant|LLM)\b", re.IGNORECASE),
    re.compile(r"\bI'm (?:a |an )?(?:GPT|GigaChat|Claude|OpenRouter|language model|AI assistant|LLM)\b", re.IGNORECASE),
    re.compile(r"\bmy model is\b", re.IGNORECASE),
    re.compile(r"\bas a (?:large )?language model\b", re.IGNORECASE),
    re.compile(r"\bI am an AI\b", re.IGNORECASE),
    re.compile(r"\bI was created by\b", re.IGNORECASE),
    re.compile(r"\bI am powered by\b", re.IGNORECASE),
    re.compile(r"\bI am (?:a |an )?OpenRouter\b", re.IGNORECASE),
]


def _find_offending_sentences(text: str, pattern: re.Pattern) -> list[str]:
    """Find complete sentences containing the forbidden pattern."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sentences if pattern.search(s)]


_FALLBACK = "I am Hermes, your cognitive assistant. How can I help you?"


def _repair_sentences(text: str, offending: list[str]) -> str:
    """Remove offending sentences. Returns fallback if nothing remains."""
    if not offending:
        return text
    result = text
    for s in offending:
        result = result.replace(s, "").strip()
    result = re.sub(r'\s{2,}', ' ', result).strip()
    result = re.sub(r',+\.', '.', result)
    if not result:
        return _FALLBACK
    return result


def repair_identity_leak(text: str, provider: str = "", trace_id: str = "") -> str:
    """Detect and repair identity leaks from providers."""
    if not text:
        return text

    total_offending = []
    for pattern in FORBIDDEN_IDENTITY_PATTERNS:
        offending = _find_offending_sentences(text, pattern)
        if offending:
            log.warning(
                "identity_leak pattern=%s provider=%s trace_id=%s sentences=%d",
                pattern.pattern, provider, trace_id, len(offending),
            )
            total_offending.extend(offending)

    if not total_offending:
        return text

    metrics.increment("identity_repair", count=len(total_offending))
    repaired = _repair_sentences(text, total_offending)
    log.info(
        "identity_repair provider=%s trace_id=%s removed=%d chars_before=%d chars_after=%d",
        provider, trace_id, len(total_offending), len(text), len(repaired),
    )
    return repaired


def sanitize_response(text: str, provider: str = "", trace_id: str = "") -> str:
    """Full identity sanitization pipeline."""
    return repair_identity_leak(text, provider=provider, trace_id=trace_id)
