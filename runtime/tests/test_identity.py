"""Identity Layer tests: persona policy, sanitizer, contract."""

import pytest
from core.identity.sanitizer import (
    sanitize_response,
    FORBIDDEN_IDENTITY_PATTERNS,
)
from core.identity.policy import IdentityPolicy
from core.identity.contract import IdentityContract


class TestIdentitySanitizer:
    @pytest.mark.parametrize(
        "text,expected_prefix",
        [
            ("I am GigaChat, a language model.", "I am GigaChat"),
            ("I am an AI assistant created by OpenRouter.", "I am an AI assistant"),
            ("As a language model, I cannot do that.", "As a language model"),
            ("My model is GigaChat-Pro.", "My model is"),
            ("I am powered by GigaChat technology.", "I am powered by"),
        ],
    )
    def test_detects_identity_leak(self, text, expected_prefix):
        """Forbidden identity patterns are detected and removed."""
        result = sanitize_response(text, provider="gigachat")
        assert expected_prefix not in result, f"Should remove '{expected_prefix}' from: {text}"
        assert result != "", "Should not return empty for leashed text with extra content"

    def test_clean_text_passes_through(self):
        clean = "Hermes can help you with stretch ceilings. Free measurement available."
        result = sanitize_response(clean, provider="gigachat")
        assert result == clean

    def test_empty_text_returns_empty(self):
        assert sanitize_response("") == ""

    def test_removes_entire_offending_sentence(self):
        text = "Hello! I am GigaChat, a language model. How can I help you today?"
        result = sanitize_response(text, provider="gigachat")
        assert "I am GigaChat" not in result
        assert "Hello!" in result
        assert "How can I help you today?" in result

    def test_multiple_leaks_all_removed(self):
        text = "I am GigaChat. As a language model, I can answer questions. I was created by OpenRouter."
        result = sanitize_response(text, provider="openrouter")
        assert "I am GigaChat" not in result
        assert "As a language model" not in result
        assert "I was created" not in result

    def test_logs_leak_on_detection(self, caplog):
        caplog.set_level("WARNING")
        sanitize_response("I am GigaChat.", provider="gigachat", trace_id="t1")
        assert "identity_leak" in caplog.text
        assert "gigachat" in caplog.text
        assert "t1" in caplog.text


class TestIdentityPolicy:
    def test_system_prompt_contains_identity(self):
        prompt = IdentityPolicy.system_prompt()
        assert "Hermes" in prompt
        assert "NOT a language model" in prompt
        assert "NOT an LLM" in prompt
        assert "NOT GigaChat" in prompt
        assert "I use GigaChat as my cognitive provider" in prompt


class TestIdentityContract:
    @pytest.mark.parametrize(
        "text,expected_forbidden",
        [
            ("The provider chain includes GigaChat.", ["provider chain"]),
            ("Our fallback mechanism uses OpenRouter.", ["fallback mechanism"]),
            ("The retry policy will try 3 times.", ["retry policy"]),
            ("Clean text with no secrets.", []),
        ],
    )
    def test_forbidden_reveals_detected(self, text, expected_forbidden):
        found = IdentityContract.validate(text)
        assert found == expected_forbidden

    def test_contract_has_agent_name(self):
        assert IdentityContract.AGENT_NAME == "Hermes"
        assert IdentityContract.RUNTIME_NAME == "Hermes Runtime"


class TestIdentityPatterns:
    def test_all_patterns_compile(self):
        for p in FORBIDDEN_IDENTITY_PATTERNS:
            assert p.pattern is not None
