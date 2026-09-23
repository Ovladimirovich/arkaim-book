from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedRequest:
    messages: list[dict]
    session_id: str
    provider: str = ""
    model: str = ""
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatRequest:
    messages: list[dict]
    session_id: str = ""
    provider: str = ""
    model: str = ""
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize(body: dict) -> NormalizedRequest:
    return NormalizedRequest(
        messages=body.get("messages", []),
        session_id=body.get("session_id", ""),
        provider=body.get("provider", ""),
        model=body.get("model", ""),
        stream=body.get("stream", False),
        metadata=body.get("metadata", {}),
    )
