"""Experience Engine — 8 режимов взаимодействия с миром."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

log = logging.getLogger("hermes.experience_engine")


class ExperienceMode(str, Enum):
    """Режимы взаимодействия с миром."""
    DIALOG = "dialog"              # Диалог с книгой
    STORY = "story"                # История
    MOVIE = "movie"                # Фильм
    QUEST = "quest"                # Квест
    GAME = "game"                  # Игра
    RESEARCH = "research"          # Исследование
    LESSON = "lesson"              # Урок
    TIMELINE = "timeline"          # Хронология
    DOCUMENTARY = "documentary"    # Документальный фильм
    ILLUSTRATION = "illustration"  # Иллюстрация


@dataclass
class ExperienceStep:
    """Шаг в опыте."""
    id: str
    action: str
    target: str
    result: dict = field(default_factory=dict)
    emotional_impact: float = 0.0


@dataclass
class ExperiencePath:
    """Путь пользователя через мир."""
    id: str
    mode: ExperienceMode
    steps: list[ExperienceStep] = field(default_factory=list)
    current_step: int = 0
    context: dict = field(default_factory=dict)


# ── Конфигурация режимов ───────────────────────────────────────

MODE_CONFIGS: dict[ExperienceMode, dict] = {
    ExperienceMode.DIALOG: {
        "name": "Диалог с книгой",
        "description": "Интерактивный диалог с миром книги",
        "available_engines": ["world_model", "relation_graph"],
        "output_types": ["text", "emotion"],
        "constraints": ["canon_only"],
    },
    ExperienceMode.STORY: {
        "name": "История",
        "description": "Рассказывание историй в мире книги",
        "available_engines": ["world_model", "relation_graph", "consistency"],
        "output_types": ["narrative", "dialogue"],
        "constraints": ["canon_only", "consistency_check"],
    },
    ExperienceMode.MOVIE: {
        "name": "Фильм",
        "description": "Кинематографическое представление мира",
        "available_engines": ["world_model", "form_library"],
        "output_types": ["visualization", "video"],
        "constraints": ["visual_consistency"],
    },
    ExperienceMode.QUEST: {
        "name": "Квест",
        "description": "Интерактивное приключение в мире",
        "available_engines": ["world_model", "relation_graph", "consistency"],
        "output_types": ["choices", "consequences"],
        "constraints": ["canon_only", "consistency_check"],
    },
    ExperienceMode.GAME: {
        "name": "Игра",
        "description": "Игровой режим с правилами",
        "available_engines": ["world_model", "relation_graph", "consistency"],
        "output_types": ["game_state", "choices"],
        "constraints": ["canon_only", "consistency_check", "balance"],
    },
    ExperienceMode.RESEARCH: {
        "name": "Исследование",
        "description": "Глубокое исследование мира",
        "available_engines": ["world_model", "relation_graph"],
        "output_types": ["analysis", "connections"],
        "constraints": [],
    },
    ExperienceMode.LESSON: {
        "name": "Урок",
        "description": "Образовательный контент о мире",
        "available_engines": ["world_model", "relation_graph"],
        "output_types": ["lesson", "quiz"],
        "constraints": ["accuracy"],
    },
    ExperienceMode.TIMELINE: {
        "name": "Хронология",
        "description": "Временная шкала событий",
        "available_engines": ["world_model", "relation_graph"],
        "output_types": ["timeline", "events"],
        "constraints": ["chronological_order"],
    },
    ExperienceMode.DOCUMENTARY: {
        "name": "Документальный фильм",
        "description": "Документальное повествование",
        "available_engines": ["world_model", "relation_graph"],
        "output_types": ["narration", "archive"],
        "constraints": ["factual"],
    },
    ExperienceMode.ILLUSTRATION: {
        "name": "Иллюстрация",
        "description": "Визуальное представление мира",
        "available_engines": ["world_model", "form_library"],
        "output_types": ["image", "prompt"],
        "constraints": ["visual_accuracy"],
    },
}


class ExperienceEngine:
    """Движок опытов — 8 режимов взаимодействия с миром.
    
    Каждый режим использует один и тот же WorldModel,
    но генерирует разный контент.
    """
    
    def __init__(self, world_engine=None):
        self._world_engine = world_engine
        self._paths: dict[str, ExperiencePath] = {}
    
    def get_mode_config(self, mode: ExperienceMode) -> dict:
        """Получить конфигурацию режима."""
        return MODE_CONFIGS.get(mode, {})
    
    def get_available_modes(self) -> list[dict]:
        """Получить список доступных режимов."""
        return [
            {
                "mode": mode.value,
                "name": config["name"],
                "description": config["description"],
            }
            for mode, config in MODE_CONFIGS.items()
        ]
    
    def create_path(self, mode: ExperienceMode, path_id: str | None = None) -> ExperiencePath:
        """Создать новый путь опыта."""
        import uuid
        path_id = path_id or str(uuid.uuid4())[:8]
        
        path = ExperiencePath(
            id=path_id,
            mode=mode,
        )
        self._paths[path_id] = path
        log.info("experience_path_created mode=%s id=%s", mode.value, path_id)
        return path
    
    def get_path(self, path_id: str) -> Optional[ExperiencePath]:
        """Получить путь по ID."""
        return self._paths.get(path_id)
    
    def add_step(self, path_id: str, action: str, target: str, result: dict | None = None) -> ExperienceStep:
        """Добавить шаг к пути."""
        path = self._paths.get(path_id)
        if not path:
            raise ValueError(f"Path '{path_id}' not found")
        
        import uuid
        step = ExperienceStep(
            id=str(uuid.uuid4())[:8],
            action=action,
            target=target,
            result=result or {},
        )
        path.steps.append(step)
        path.current_step = len(path.steps) - 1
        return step
    
    def get_entity_for_mode(self, entity_id: str, mode: ExperienceMode) -> dict:
        """Получить сущность в формате для конкретного режима."""
        if not self._world_engine:
            return {}
        
        entity = self._world_engine.get_entity(entity_id)
        if not entity:
            return {}
        
        config = self.get_mode_config(mode)
        
        # Фильтруем данные по режиму
        result = {
            "entity": entity,
            "mode": mode.value,
            "mode_name": config.get("name", ""),
        }
        
        # Добавляем связи
        if "relation_graph" in config.get("available_engines", []):
            relations = self._world_engine.get_entity_context(entity_id)
            result["relations"] = relations.get("relations", {})
        
        return result
    
    def summary(self) -> str:
        """Текстовая сводка."""
        return f"ExperienceEngine: {len(self._paths)} путей, {len(MODE_CONFIGS)} режимов"
