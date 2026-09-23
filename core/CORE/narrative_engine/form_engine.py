"""Form Engine — движок форм для визуализации мира."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); from FORM import get_form_library, FormLibrary

log = logging.getLogger("hermes.form_engine")


@dataclass
class VisualForm:
    """Визуальная форма объекта."""
    id: str
    name: str
    name_ru: str
    category: str
    description: str
    visual_prompt: str
    materials: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    mood: str = ""
    style: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_ru": self.name_ru,
            "category": self.category,
            "description": self.description,
            "visual_prompt": self.visual_prompt,
            "materials": self.materials,
            "colors": self.colors,
            "features": self.features,
            "mood": self.mood,
            "style": self.style,
        }


@dataclass
class FormContext:
    """Контекст формы для конкретного объекта."""
    entity_id: str
    entity_name: str
    forms: list[VisualForm]
    combined_prompt: str
    palette: list[str]
    materials: list[str]
    mood: str


class FormEngine:
    """Движок форм — предоставляет визуальные описания для генерации.
    
    Использует:
    - FormLibrary — библиотеку форм (55 форм, 11 категорий)
    - WorldModelExt — контекст мира
    - RelationGraph — связи между объектами
    
    Генерирует:
    - VisualForm — визуальная форма объекта
    - FormContext — контекст формы для генерации
    - Промпты для генерации изображений/видео
    """
    
    def __init__(self, world_engine=None):
        self._world_engine = world_engine
        self._form_library = get_form_library()
    
    def get_form(self, category: str, form_id: str) -> Optional[VisualForm]:
        """Получить форму по ID."""
        form_data = self._form_library.get_form(category, form_id)
        if not form_data:
            return None
        
        return VisualForm(
            id=form_data.get("id", ""),
            name=form_data.get("name", ""),
            name_ru=form_data.get("name_ru", ""),
            category=category,
            description=form_data.get("description", ""),
            visual_prompt=form_data.get("visual_prompt", ""),
            materials=form_data.get("materials", []),
            colors=form_data.get("colors", []),
            features=form_data.get("features", []),
            mood=form_data.get("mood", ""),
            style=form_data.get("style", ""),
        )
    
    def get_forms_for_entity(self, entity_id: str) -> list[VisualForm]:
        """Получить формы для сущности мира."""
        if not self._world_engine:
            return []
        
        entity = self._world_engine.get_entity(entity_id)
        if not entity:
            return []
        
        forms = []
        category = entity.get("category", "")
        
        # Маппинг категорий мира на категории форм
        category_mapping = {
            "geography": ["architecture", "weather", "lighting", "materials"],
            "architecture": ["architecture", "materials", "textures"],
            "civilizations": ["clothes", "faces", "body_language"],
            "technologies": ["materials", "textures"],
            "religion": ["rituals", "lighting", "colors"],
            "mythology": ["colors", "sounds", "rituals"],
            "social_structure": ["clothes", "faces", "body_language"],
            "daily_life": ["clothes", "materials", "textures"],
            "rituals": ["rituals", "lighting", "colors"],
        }
        
        form_categories = category_mapping.get(category, [])
        
        for form_cat in form_categories:
            forms_data = self._form_library.get_category(form_cat)
            for form_data in forms_data:
                forms.append(VisualForm(
                    id=form_data.get("id", ""),
                    name=form_data.get("name", ""),
                    name_ru=form_data.get("name_ru", ""),
                    category=form_cat,
                    description=form_data.get("description", ""),
                    visual_prompt=form_data.get("visual_prompt", ""),
                    materials=form_data.get("materials", []),
                    colors=form_data.get("colors", []),
                    features=form_data.get("features", []),
                    mood=form_data.get("mood", ""),
                    style=form_data.get("style", ""),
                ))
        
        return forms
    
    def build_form_context(self, entity_id: str) -> Optional[FormContext]:
        """Построить контекст формы для сущности."""
        if not self._world_engine:
            return None
        
        entity = self._world_engine.get_entity(entity_id)
        if not entity:
            return None
        
        forms = self.get_forms_for_entity(entity_id)
        
        # Объединяем промпты
        prompts = [f.visual_prompt for f in forms if f.visual_prompt]
        combined_prompt = ", ".join(prompts[:3])  # Максимум 3 промпта
        
        # Объединяем палитры
        all_colors = []
        for f in forms:
            all_colors.extend(f.colors)
        palette = list(dict.fromkeys(all_colors))[:5]  # Уникальные, максимум 5
        
        # Объединяем материалы
        all_materials = []
        for f in forms:
            all_materials.extend(f.materials)
        materials = list(dict.fromkeys(all_materials))[:5]  # Уникальные, максимум 5
        
        # Определяем настроение
        moods = [f.mood for f in forms if f.mood]
        mood = moods[0] if moods else "neutral"
        
        return FormContext(
            entity_id=entity_id,
            entity_name=entity.get("name", ""),
            forms=forms,
            combined_prompt=combined_prompt,
            palette=palette,
            materials=materials,
            mood=mood,
        )
    
    def generate_visual_prompt(self, entity_id: str, style: str = "cinematic") -> str:
        """Генерировать визуальный промпт для сущности."""
        context = self.build_form_context(entity_id)
        if not context:
            return ""
        
        parts = []
        
        # Стиль
        style_prefixes = {
            "cinematic": "cinematic fantasy, epic film still, dramatic lighting",
            "realistic": "photorealistic, natural lighting, detailed textures",
            "watercolor": "watercolor painting, soft edges, artistic",
            "ethereal": "ethereal dreamlike, soft glow, otherworldly",
        }
        parts.append(style_prefixes.get(style, style_prefixes["cinematic"]))
        
        # Объект
        parts.append(context.entity_name)
        
        # Описание
        if context.forms:
            parts.append(context.forms[0].description)
        
        # Материалы
        if context.materials:
            parts.append(", ".join(context.materials[:3]))
        
        # Палитра
        if context.palette:
            parts.append(f"colors: {', '.join(context.palette[:3])}")
        
        # Настроение
        if context.mood:
            parts.append(context.mood)
        
        # Качество
        parts.append("8k, masterpiece, highly detailed")
        
        return ", ".join(parts)
    
    def get_available_forms(self) -> dict:
        """Получить доступные формы по категориям."""
        result = {}
        for category in self._form_library.get_categories():
            items = self._form_library.get_category(category)
            result[category] = [
                {"id": item.get("id"), "name": item.get("name")}
                for item in items
            ]
        return result
    
    def summary(self) -> str:
        """Текстовая сводка."""
        stats = self._form_library.get_stats()
        return f"FormEngine: {stats['total_forms']} форм в {stats['total_categories']} категориях"


# ── Фабрика ────────────────────────────────────────────────────

_form_engine_cache: Optional[FormEngine] = None

def get_form_engine(world_engine=None) -> FormEngine:
    """Получить singleton FormEngine."""
    global _form_engine_cache
    if _form_engine_cache is None:
        _form_engine_cache = FormEngine(world_engine)
    return _form_engine_cache

def invalidate_form_engine():
    """Сбросить кэш."""
    global _form_engine_cache
    _form_engine_cache = None


