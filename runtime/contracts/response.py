from dataclasses import dataclass, field


@dataclass
class ChatResponse:
    id: str
    object: str = "chat.completion"
    model: str = ""
    choices: list[dict] = field(default_factory=list)
    error: str = ""


@dataclass
class StreamEvent:
    id: str
    event: str = "token"
    data: str = ""
