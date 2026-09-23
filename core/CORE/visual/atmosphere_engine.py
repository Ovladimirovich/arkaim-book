"""AtmosphereEngine — библиотека атмосфер."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from .visual_models import AtmosphereContext

log = logging.getLogger("visual.atmosphere_engine")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"


class AtmosphereEngine:
    """Возвращает AtmosphereContext по имени атмосферы."""

    def __init__(self, knowledge_path: Path | None = None):
        self._knowledge = self._load(knowledge_path or _KNOWLEDGE_DIR)

    def _load(self, path: Path) -> dict:
        f = path / "ATMOSPHERES.json"
        if f.exists():
            return json.loads(f.read_text("utf-8-sig"))
        return {}

    def get_atmosphere(self, name: str) -> AtmosphereContext:
        if name in self._knowledge:
            a = self._knowledge[name]
            return AtmosphereContext(
                name=name,
                light=a.get("light", ""),
                fog=a.get("fog", ""),
                wind=a.get("wind", ""),
                particles=a.get("particles", ""),
                sound=a.get("sound", ""),
                color_temperature=a.get("color_temperature", ""),
                contrast=a.get("contrast", ""),
                camera_dynamics=a.get("camera_dynamics", ""),
            )
        return AtmosphereContext(name=name)

    def resolve_from_emotion(self, emotion: str) -> str:
        emotion = emotion.lower()
        if "conflict" in emotion or "конфликт" in emotion:
            return "military"
        if "sacred" in emotion or "ceremonial" in emotion or "ritual" in emotion:
            return "sacred"
        if "catastrophic" in emotion or "disaster" in emotion:
            return "catastrophic"
        if "festive" in emotion or "celebration" in emotion:
            return "festive"
        if "fear" in emotion or "anxious" in emotion or "тревог" in emotion:
            return "anxious"
        return "neutral"

    def list_atmospheres(self) -> list[str]:
        return list(self._knowledge.keys())
