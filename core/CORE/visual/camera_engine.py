"""CameraEngine — библиотека операторских решений."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from .visual_models import CameraContext

log = logging.getLogger("visual.camera_engine")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"


class CameraEngine:
    """Возвращает CameraContext для шота."""

    def __init__(self, knowledge_path: Path | None = None):
        self._knowledge = self._load(knowledge_path or _KNOWLEDGE_DIR)

    def _load(self, path: Path) -> dict:
        f = path / "CAMERA_LIBRARY.json"
        if f.exists():
            return json.loads(f.read_text("utf-8-sig"))
        return {}

    def get_camera(self, shot_type: str = "wide", movement: str = "static") -> CameraContext:
        shots = self._knowledge.get("shot_types", {})
        movements = self._knowledge.get("movements", {})

        shot = shots.get(shot_type, {})
        move = movements.get(movement, {})

        return CameraContext(
            shot_type=shot_type,
            lens=shot.get("lens", "50mm"),
            movement=movement,
            composition=shot.get("framing", ""),
            depth_of_field="deep" if shot_type in ("extreme_wide", "wide") else "shallow",
            cinematic_style=move.get("effect", ""),
        )

    def get_transition(self, name: str) -> dict:
        transitions = self._knowledge.get("transitions", {})
        return transitions.get(name, {"duration": "0", "use": "standard"})

    def list_shot_types(self) -> list[str]:
        return list(self._knowledge.get("shot_types", {}).keys())

    def list_movements(self) -> list[str]:
        return list(self._knowledge.get("movements", {}).keys())
