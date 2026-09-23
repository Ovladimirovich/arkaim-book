"""Расширенные модели World Model для новых категорий мира."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field


# ── Базовая модель для извлечённых данных ──────────────────────

class WorldEntity(BaseModel):
    """Единица знания о мире из WORLD_MODEL/*.json."""
    id: str
    name: str
    name_ru: str = ""
    category: str
    description: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)
    relationships: list[str] = Field(default_factory=list)
    source: str = ""
    confidence: float = 1.0


# ── География ──────────────────────────────────────────────────

class GeoRegion(BaseModel):
    """Регион мира."""
    id: str
    name: str
    name_ru: str = ""
    type: str = ""  # region, city, sacred_site, ruins, natural
    description: str = ""
    coordinates: Optional[dict] = None
    era: str = ""
    color: str = ""
    icon: str = ""
    energy_level: str = ""
    related_entities: list[str] = Field(default_factory=list)


class GeoRoute(BaseModel):
    """Маршрут."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    from_location: str = ""
    to_location: str = ""
    distance: str = ""
    energy_lines: list[str] = Field(default_factory=list)


class GeoEnergyLine(BaseModel):
    """Энергетическая линия."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    direction: str = ""
    power: str = ""


# ── Цивилизации ────────────────────────────────────────────────

class CivilizationInfo(BaseModel):
    """Информация о цивилизации."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    epoch: str = ""
    values: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    religion: str = ""
    social_structure: str = ""
    related_locations: list[str] = Field(default_factory=list)


# ── Архитектура ────────────────────────────────────────────────

class ArchitectureStyle(BaseModel):
    """Стиль архитектуры."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    materials: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    era: str = ""
    location: str = ""


# ── Технологии ─────────────────────────────────────────────────

class TechnologyInfo(BaseModel):
    """Технология."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    epoch_first: str = ""
    civilization_origin: str = ""
    category: str = ""  # energy, construction, agriculture, etc.
    materials: list[str] = Field(default_factory=list)


# ── Религия ────────────────────────────────────────────────────

class ReligionInfo(BaseModel):
    """Религия."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    practices: list[str] = Field(default_factory=list)
    key_figures: list[str] = Field(default_factory=list)
    epochs: list[str] = Field(default_factory=list)
    sacred_places: list[str] = Field(default_factory=list)


# ── Философия ──────────────────────────────────────────────────

class PhilosophyConcept(BaseModel):
    """Философская концепция."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    related_concepts: list[str] = Field(default_factory=list)
    applications: list[str] = Field(default_factory=list)


# ── Язык ───────────────────────────────────────────────────────

class LanguageTerm(BaseModel):
    """Термин языка мира."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    translation: str = ""
    category: str = ""  # word, phrase, concept, name
    usage: list[str] = Field(default_factory=list)


# ── Мифология ──────────────────────────────────────────────────

class MythSymbol(BaseModel):
    """Мифологический символ."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    literal: str = ""
    metaphorical: str = ""
    spiritual: str = ""
    archetypal: str = ""
    colors: list[str] = Field(default_factory=list)
    visual_elements: list[str] = Field(default_factory=list)


# ── Астрономия ─────────────────────────────────────────────────

class AstronomicalObject(BaseModel):
    """Астрономический объект."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    type: str = ""  # star, constellation, planet, moon
    significance: str = ""
    related_myths: list[str] = Field(default_factory=list)


# ── Флора ──────────────────────────────────────────────────────

class PlantSpecies(BaseModel):
    """Растение."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    uses: list[str] = Field(default_factory=list)
    symbolism: str = ""
    location: str = ""


# ── Фауна ──────────────────────────────────────────────────────

class AnimalSpecies(BaseModel):
    """Животное."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    uses: list[str] = Field(default_factory=list)
    symbolism: str = ""
    totem_significance: str = ""


# ── Транспорт ──────────────────────────────────────────────────

class TransportType(BaseModel):
    """Тип транспорта."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    materials: list[str] = Field(default_factory=list)
    usage: list[str] = Field(default_factory=list)


# ── Климат ─────────────────────────────────────────────────────

class ClimateInfo(BaseModel):
    """Климат."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    seasons: list[str] = Field(default_factory=list)
    temperature_range: str = ""
    precipitation: str = ""


# ── Социальная структура ──────────────────────────────────────

class SocialRole(BaseModel):
    """Социальная роль."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    status: str = ""  # high, medium, low
    count: int = 0


# ── Быт ────────────────────────────────────────────────────────

class DailyLifeActivity(BaseModel):
    """Бытовая деятельность."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    category: str = ""  # housing, food, clothing, family, etc.
    details: dict[str, Any] = Field(default_factory=dict)


# ── Ритуалы ────────────────────────────────────────────────────

class RitualPractice(BaseModel):
    """Ритуальная практика."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    type: str = ""  # initiation, wedding, funeral, seasonal
    participants: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)


# ── Образование ────────────────────────────────────────────────

class EducationMethod(BaseModel):
    """Метод образования."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    methods: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    teachers: list[str] = Field(default_factory=list)


# ── Военное дело ──────────────────────────────────────────────

class WarfareInfo(BaseModel):
    """Военное дело."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    weapons: list[str] = Field(default_factory=list)
    tactics: list[str] = Field(default_factory=list)
    defenses: list[str] = Field(default_factory=list)


# ── Ремёсла ────────────────────────────────────────────────────

class CraftType(BaseModel):
    """Тип ремесла."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    materials: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)


# ── Хронология ─────────────────────────────────────────────────

class ChronologicalEvent(BaseModel):
    """Хронологическое событие."""
    id: str
    name: str
    name_ru: str = ""
    description: str = ""
    epoch: str = ""
    chapter: int = 0
    order: int = 0
    characters: list[str] = Field(default_factory=list)
    location: str = ""


# ── Фабрика моделей ───────────────────────────────────────────

def create_entity_from_dict(category: str, data: dict) -> WorldEntity:
    """Создать WorldEntity из словаря."""
    return WorldEntity(
        id=data.get("id", ""),
        name=data.get("name", ""),
        name_ru=data.get("name_ru", data.get("name", "")),
        category=category,
        description=data.get("description", ""),
        properties=data.get("properties", {}),
        relationships=data.get("relationships", []),
        source=data.get("source", ""),
        confidence=data.get("confidence", 1.0),
    )
