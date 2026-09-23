"""Pydantic-модели для Visual Intelligence."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SceneContext(BaseModel):
    chapter: int = 0
    scene_id: str = ""
    title: str = ""
    description: str = ""
    emotion: str = "neutral"
    emotion_intensity: float = 0.5
    meaning_tags: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    location: str = ""

class ArchitectureContext(BaseModel):
    style: str = ""
    materials: str = ""
    features: list[str] = Field(default_factory=list)
    age: str = ""
    condition: str = ""


class LandscapeContext(BaseModel):
    terrain: str = ""
    vegetation: str = ""
    water: str = ""
    sky: str = ""


class LocationContext(BaseModel):
    location_id: str = ""
    name: str = ""
    type: str = ""
    architecture: ArchitectureContext = ArchitectureContext()
    landscape: LandscapeContext = LandscapeContext()
    palette: list[str] = Field(default_factory=list)
    atmosphere_default: str = ""
    atmosphere_by_time: dict[str, str] = Field(default_factory=dict)
    sound: str = ""
    symbols: list[str] = Field(default_factory=list)


class EnvironmentContext(BaseModel):
    weather: str = "clear"
    season: str = "late summer"
    time_of_day: str = "dawn"
    temperature: str = "cool"
    wind: str = "still"


class LightingContext(BaseModel):
    source: str = "natural"
    direction: str = "east, low"
    color: str = "golden"
    intensity: str = "soft"
    contrast: str = "medium"
    description: str = ""


class PaletteContext(BaseModel):
    primary: list[str] = Field(default_factory=list)
    accents: list[str] = Field(default_factory=list)
    contrast: str = "warm"
    description: str = ""


class AtmosphereContext(BaseModel):
    name: str = "neutral"
    light: str = ""
    fog: str = ""
    wind: str = ""
    particles: str = ""
    sound: str = ""
    color_temperature: str = ""
    contrast: str = ""
    camera_dynamics: str = ""


class SymbolContext(BaseModel):
    name: str = ""
    literal: str = ""
    metaphorical: str = ""
    spiritual: str = ""
    archetypal: str = ""
    colors: list[str] = Field(default_factory=list)
    visual_elements: list[str] = Field(default_factory=list)


class HistoricalContext(BaseModel):
    era: str = "Bronze Age"
    civilization: str = "Hyperborean"
    year_approx: str = "3500 BC"
    cultural_notes: str = ""


class CameraContext(BaseModel):
    shot_type: str = "wide"
    angle: str = "eye_level"
    movement: str = "static"
    lens: str = "50mm"
    composition: str = ""
    depth_of_field: str = "deep"
    cinematic_style: str = ""


class StyleContext(BaseModel):
    name: str = "cinematic_fantasy"
    prefix: str = "cinematic fantasy, epic film still, dramatic lighting"
    references: list[str] = Field(default_factory=list)
    quality_suffixes: list[str] = Field(default_factory=list)


class EmotionContext(BaseModel):
    name: str = "neutral"
    visual: str = "balanced natural lighting, clear visibility"
    suffix: str = "peaceful and clear"
    intensity: float = 0.5


class CharacterVisualContext(BaseModel):
    character_id: str = ""
    name: str = ""
    age_range: str = ""
    face: str = ""
    hair: str = ""
    eyes: str = ""
    build: str = ""
    clothing: str = ""
    accessories: list[str] = Field(default_factory=list)
    mannerisms: str = ""
    movement: str = ""
    appearance_summary: str = ""


class NegativePromptContext(BaseModel):
    base: list[str] = Field(default_factory=lambda: [
        "blurry", "low quality", "deformed", "ugly", "bad anatomy",
        "watermark", "text", "signature", "modern elements",
        "anachronistic", "out of period"
    ])
    extra: list[str] = Field(default_factory=list)
