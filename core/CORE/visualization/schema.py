"""Pydantic-схемы для Visualization Layer."""
from pydantic import BaseModel


class VisualGenomeEntry(BaseModel):
    """Запись визуального генома."""
    book_id: str
    entity_type: str  # scene, character, location, style
    entity_id: str
    spec: dict
    version: int = 1
    source_hash: str = ""


class CharacterVisual(BaseModel):
    """Визуальная spec персонажа."""
    character_id: str
    age_range: str
    build: str
    hair: str
    eyes: str
    clothing: str
    accessories: list[str] = []
    color_palette: list[str]
    style_constants: list[str]


class LocationVisual(BaseModel):
    """Визуальная spec локации."""
    location_id: str
    type: str
    architecture: str
    atmosphere: str
    lighting: str
    palette: list[str]


class SceneVisualSpec(BaseModel):
    """Полная визуальная спецификация сцены."""
    chapter: int
    scene_id: str
    characters: dict[str, CharacterVisual]
    location: LocationVisual
    emotion: str
    style_preset: str
    prompt_template: str = ""


class VisualMemoryEntry(BaseModel):
    """Запись в visual memory."""
    reader_id: str
    scene_id: str
    character_id: str
    image_hash: str
    visual_spec_hash: str
    cached_until: str