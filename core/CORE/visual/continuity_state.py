"""ContinuityState — хранит визуальное состояние между кадрами."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContinuityState:
    """Хранит визуальное состояние между кадрами для консистентности."""
    architecture_style: str = ""
    character_appearances: dict[str, str] = field(default_factory=dict)  # char_id → appearance_hash
    weather: str = ""
    season: str = ""
    lighting_angle: str = ""
    color_temperature: str = ""
    props: list[str] = field(default_factory=list)
    symbol_visibility: dict[str, bool] = field(default_factory=dict)
    palette_primary: list[str] = field(default_factory=list)
    atmosphere_name: str = ""

    def snapshot_from_context(self, ctx) -> None:
        """Сделать снимок из VisualContext."""
        self.architecture_style = ctx.architecture.style
        self.weather = ctx.environment.weather
        self.season = ctx.environment.season
        self.lighting_angle = ctx.lighting.direction
        self.color_temperature = ctx.atmosphere.color_temperature
        self.palette_primary = ctx.palette.primary
        self.atmosphere_name = ctx.atmosphere.name

        for char in ctx.characters:
            self.character_appearances[char.character_id] = char.appearance_summary

        for sym in ctx.symbols:
            self.symbol_visibility[sym.name] = True
