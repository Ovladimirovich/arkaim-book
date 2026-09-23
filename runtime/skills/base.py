from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillContext:
    messages: list[dict]
    user: str
    session_id: str
    user_text: str
    memory: object
    trace_id: str


@dataclass
class SkillResult:
    handled: bool = False
    response: Optional[str] = None
    context: str = ""
    system_prompt: str = ""
    metadata: dict = field(default_factory=dict)


class Skill(ABC):
    name: str = ""
    priority: int = 0

    @abstractmethod
    async def execute(self, ctx: SkillContext) -> SkillResult:
        ...

    async def post_process(self, response: str, ctx: SkillContext) -> str:
        return response
