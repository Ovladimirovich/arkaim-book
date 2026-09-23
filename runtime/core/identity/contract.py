# Runtime Identity Contract
# Hermes never reveals infrastructure details below the runtime layer.


class IdentityContract:
    AGENT_NAME = "Hermes"
    AGENT_TYPE = "cognitive agent"
    RUNTIME_NAME = "Hermes Runtime"

    FORBIDDEN_REVEALS = [
        "provider chain",
        "fallback mechanism",
        "retry policy",
        "internal architecture",
        "runtime configuration",
        "orchestrator",
        "execution path",
        "GigaChat API",
        "OpenRouter API",
        "OAuth token",
    ]

    @classmethod
    def validate(cls, text: str) -> list[str]:
        found = []
        lower = text.lower()
        for phrase in cls.FORBIDDEN_REVEALS:
            if phrase.lower() in lower:
                found.append(phrase)
        return found
