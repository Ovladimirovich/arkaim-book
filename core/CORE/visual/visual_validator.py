"""VisualValidator — валидация VisualContext перед генерацией."""
from __future__ import annotations

import logging
from .visual_context import VisualContext

log = logging.getLogger("visual.validator")


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def __repr__(self):
        return f"ValidationResult(errors={len(self.errors)}, warnings={len(self.warnings)})"


class VisualValidator:
    """Валидирует VisualContext перед генерацией."""

    def validate(self, ctx: VisualContext) -> ValidationResult:
        result = ValidationResult()

        if not ctx.scene.title and not ctx.scene.scene_id:
            # Skip error for character portrait or location landscape
            has_portrait = bool(ctx.characters)
            has_location = bool(ctx.location and ctx.location.name and ctx.location.name != "unknown")
            if not has_portrait and not has_location:
                result.add_error("Scene has no title or scene_id")

        if not ctx.location.name and not ctx.location.location_id:
            result.add_warning("Location is unknown — prompt may be generic")

        if not ctx.palette.primary:
            result.add_warning("No color palette — using defaults")

        if ctx.emotion.name == "neutral" and ctx.emotion.intensity < 0.3:
            result.add_warning("Very low emotion intensity — image may lack atmosphere")

        if ctx.camera.shot_type not in ("extreme_wide", "wide", "medium", "medium_shot", "close_up", "extreme_close_up"):
            result.add_warning(f"Unknown shot type: {ctx.camera.shot_type}")

        if not ctx.style.prefix:
            result.add_warning("No style prefix — using generic")

        log.info("validate %s", result)
        return result
