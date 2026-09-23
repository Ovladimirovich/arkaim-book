"""
Базовый класс для всех агентов системы.
Обеспечивает единый интерфейс: system_prompt, action, memory.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import json


from config import config

BASE = config.BASE_DIR


class BaseAgent(ABC):
    """
    Абстрактный базовый агент.
    Все агенты наследуются от него.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._load_genome()

    def _load_genome(self):
        genome_path = BASE / "GENOME" / "GENOME_v1.0.0.json"
        if genome_path.exists():
            self._genome = json.loads(genome_path.read_text(encoding="utf-8"))
        else:
            self._genome = {"modules": {}, "author_intent": {}}

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Возвращает system_prompt для агента."""
        pass

    @abstractmethod
    async def act(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основной метод действия агента.
        Принимает входные данные, возвращает результат.
        """
        pass

    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
        }
