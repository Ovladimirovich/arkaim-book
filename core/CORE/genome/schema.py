"""
Pydantic-схемы для Генома Книги (Book Genome).
Синхронизированы с реальной структурой GENOME_v1.0.0.json.
Строгая валидация всех структурных элементов.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# ── Базовые сущности ─────────────────────────────────

class Character(BaseModel):
    id: str = Field(description="Уникальный идентификатор")
    name: str = Field(description="Имя персонажа")
    aliases: List[str] = Field(default_factory=list, description="Псевдонимы")
    type: str = Field(default="secondary", description="Тип: main, secondary, cameo")
    archetype: str = Field(default="", description="Архетип персонажа")
    description: str = Field(default="", description="Описание")
    values: List[str] = Field(default_factory=list, description="Ценности персонажа")
    first_chapter: Optional[int] = Field(default=None, description="Первая глава")
    last_chapter: Optional[int] = Field(default=None, description="Последняя глава")


class Theme(BaseModel):
    id: str = Field(description="Уникальный идентификатор")
    name: str = Field(description="Название темы")
    description: str = Field(default="", description="Описание")
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Сила темы (0-1)")


class Value(BaseModel):
    id: str = Field(description="Уникальный идентификатор")
    name: str = Field(description="Название ценности")
    description: str = Field(default="", description="Описание")
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Сила ценности (0-1)")


class Symbol(BaseModel):
    id: str = Field(description="Уникальный идентификатор")
    name: str = Field(description="Название символа")
    meaning: str = Field(default="", description="Значение символа")
    chapters: List[int] = Field(default_factory=list, description="Главы, где встречается")


class Conflict(BaseModel):
    id: str = Field(description="Уникальный идентификатор")
    name: str = Field(description="Название конфликта")
    type: str = Field(default="internal", description="Тип: internal, external, moral")


class TimelineEvent(BaseModel):
    id: str = Field(description="Уникальный идентификатор")
    event: str = Field(description="Описание события")
    chapter: int = Field(default=0, description="Номер главы")
    title: str = Field(default="", description="Заголовок")


class WorldEntity(BaseModel):
    name: str = Field(description="Название сущности")
    type: str = Field(description="Тип: civilization, concept, location, artifact")
    description: str = Field(description="Описание")
    values: List[str] = Field(default_factory=list, description="Ценности")
    related_to: List[str] = Field(default_factory=list, description="Связанные сущности")
    conflict_with: Optional[List[str]] = Field(default=None, description="С чем конфликтует")


class CatalogText(BaseModel):
    text: str = Field(description="Текст фрагмента")
    source: str = Field(default="book", description="Источник")
    chapter: str = Field(default="", description="Название главы")
    characters: List[str] = Field(default_factory=list, description="Персонажи в фрагменте")


class AuthorIntent(BaseModel):
    main_message: str = Field(default="", description="Главное послание")
    secondary_messages: List[str] = Field(default_factory=list, description="Второстепенные послания")
    desired_reader_transformation: List[str] = Field(default_factory=list, description="Желаемая трансформация")
    questions_for_reader: List[str] = Field(default_factory=list, description="Вопросы для читателя")
    core_values: List[str] = Field(default_factory=list, description="Ключевые ценности")
    misinterpretation_risks: List[str] = Field(default_factory=list, description="Риски неверной интерпретации")


# ── Narrative Arc Layer ──────────────────────────────

class Beat(BaseModel):
    """Один сюжетный такт — состояние сущности в главе."""
    chapter: int = Field(description="Номер главы")
    state: str = Field(description="Состояние: introduction, rise, peak, fall, resolution")
    emotion: str = Field(default="", description="Эмоциональная окраска такта")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Интенсивность/напряжение")
    description: str = Field(default="", description="Что произошло с сущностью в этой главе")


class NarrativeArc(BaseModel):
    """Сюжетная дуга — развитие сущности через главы."""
    type: str = Field(description="Тип дуги: character_arc, plot_arc, thematic_arc")
    entity_id: str = Field(description="ID сущности (character, conflict, theme)")
    name: str = Field(default="", description="Название дуги")
    arc_type: str = Field(default="rise_fall", description="Форма дуги: rise_fall, hero_journey, transformation, tragedy, comedy")
    beats: List[Beat] = Field(default_factory=list, description="Такты по главам")
    resolution: str = Field(default="", description="Чем завершилась дуга")
    provenance: List[str] = Field(default_factory=list, description="Происхождение дуги (модуль генома + сущность)")
    incomplete: bool = Field(default=False, description="Связь неполна (нет id/границ глав/архетипа)")
    incomplete_reason: str = Field(default="", description="Причина неполноты связи")


CHARACTER_ARC_TYPES = {
    "Искатель": "hero_journey",
    "Мудрец": "transformation",
    "Хранитель": "rise_fall",
    "Проводник": "hero_journey",
    "Архат": "transformation",
    "Наставник": "rise_fall",
    "Лидер": "rise_fall",
    "Учёный": "transformation",
}

ARC_STATE_LABELS = {
    "introduction": "Введение",
    "rise": "Подъём",
    "peak": "Кульминация",
    "fall": "Спад",
    "resolution": "Развязка",
}

EMOTION_TO_ARC_STATE = {
    "warm_intimate": "introduction",
    "melancholic_dark": "fall",
    "hopeful_golden": "rise",
    "dark_mystical": "rise",
    "dramatic_contrast": "peak",
    "ethereal_light": "resolution",
    "sepia_flashback": "fall",
    "ceremonial_warm": "peak",
    "sacred_glow": "resolution",
    "conflict": "peak",
    "bright_warm": "rise",
    "calm_acceptance": "resolution",
}


# ── Структура генома ─────────────────────────────────

class GenomeModules(BaseModel):
    themes: List[Theme] = Field(default_factory=list)
    values: List[Value] = Field(default_factory=list)
    characters: List[Character] = Field(default_factory=list)
    symbols: List[Symbol] = Field(default_factory=list)
    philosophy: List[dict] = Field(default_factory=list, description="Концепты философии (плоские)")
    conflicts: List[Conflict] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    narrative_arcs: List[NarrativeArc] = Field(default_factory=list, description="Сюжетные дуги")


class GenomeValidation(BaseModel):
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    passed: Optional[bool] = Field(default=None)


class BookGenome(BaseModel):
    """Полный геном книги — один в один с GENOME_v1.0.0.json."""
    version: str = Field(default="1.0.0")
    book_id: str = Field(default="nasledie-arkaima")
    title: str = Field(default="Наследие Аркаима")
    author: str = Field(default="ОВладимирович")
    created_at: str = Field(default="")

    modules: GenomeModules = Field(default_factory=GenomeModules)
    author_intent: AuthorIntent = Field(default_factory=AuthorIntent)
    world_entities: List[WorldEntity] = Field(default_factory=list)

    catalog_texts: List[CatalogText] = Field(default_factory=list, description="RAG-тексты для Pulse")
    validation: GenomeValidation = Field(default_factory=GenomeValidation)


class BookGenomeProfile(BaseModel):
    """Профиль генома — мета-данные для быстрой проверки."""
    book_id: str = "nasledie-arkaima"
    title: str = "Наследие Аркаима"
    author: str = "ОВладимирович"
    genome_version: str = "1.0.0"
    analysis_version: str = "1.0.0"
    created_at: str = ""
    metrics: dict = Field(default_factory=dict)


# ── Visualization Layer ──────────────────────────────

class VisualStylePreset(BaseModel):
    """Визуальный стиль по умолчанию для книги."""
    preset_id: str
    name: str
    prompt_suffix: str
    aspect_ratio: str = "16:9"
    guidance_scale: float = 7.5
    negative_prompt: str = ""


class Scene(BaseModel):
    """Сцена произведения."""
    chapter: int
    scene_id: str
    title: str
    characters: list[str]
    location: str
    emotion: str
    meaning_tags: list[str]
    visual_style_hint: str = "default"


class CharacterVisual(BaseModel):
    """Визуальная идентичность персонажа."""
    character_id: str
    age: str
    clothing: str
    symbols: list[str]
    color_palette: list[str]
    visual_constants: list[str]


class LocationVisual(BaseModel):
    """Визуальная спецификация локации."""
    location_id: str
    type: str  # indoor/outdoor
    architecture: str
    atmosphere: str
    lighting: str
    details: list[str] = []


class VisualGenome(BaseModel):
    """Визуальный геном произведения."""
    book_id: str
    scenes: dict[str, Scene] = {}
    characters: dict[str, CharacterVisual] = {}
    locations: dict[str, LocationVisual] = {}
    style_presets: dict[str, VisualStylePreset] = {}
