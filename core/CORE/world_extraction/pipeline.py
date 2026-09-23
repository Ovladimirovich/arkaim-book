"""World Extraction Pipeline — оркестратор извлечения знаний о мире."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from .models import WorldKnowledge, ExtractionResult, WorldModelManifest

log = logging.getLogger("hermes.world_extraction")

KNOWLEDGE_DIR = Path("core/KNOWLEDGE")
WORLD_MODEL_DIR = Path("core/CORE/WORLD_MODEL")


class WorldExtractionPipeline:
    """Пайплайн извлечения знаний о мире из книги.
    
    Этап 1: Extractor — извлекает знания из существующих JSON-файлов
    Этап 2: Model — структурирует в WorldKnowledge
    Этап 3: Save — сохраняет в WORLD_MODEL/*.json
    """
    
    def __init__(self, knowledge_dir: Path | None = None, output_dir: Path | None = None):
        self._knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self._output_dir = output_dir or WORLD_MODEL_DIR
        self._extractors: dict[str, Callable] = {}
        self._manifest = WorldModelManifest()
    
    def register_extractor(self, category: str, extractor_fn: Callable):
        """Зарегистрировать экстрактор для категории."""
        self._extractors[category] = extractor_fn
        log.info("extractor_registered category=%s", category)
    
    def extract_category(self, category: str) -> ExtractionResult:
        """Извлечь знания для одной категории."""
        if category not in self._extractors:
            return ExtractionResult(
                category=category,
                success=False,
                error=f"No extractor registered for category '{category}'",
            )
        
        try:
            extractor = self._extractors[category]
            result = extractor()
            log.info("extraction_complete category=%s items=%d", category, result.items_count)
            return result
        except Exception as e:
            log.error("extraction_failed category=%s error=%s", category, e)
            return ExtractionResult(
                category=category,
                success=False,
                error=str(e),
            )
    
    def extract_all(self) -> WorldModelManifest:
        """Извлечь знания для всех категорий."""
        manifest = WorldModelManifest()
        
        for category in self._extractors:
            result = self.extract_category(category)
            manifest.add_result(result)
        
        self._manifest = manifest
        log.info("extraction_complete total=%d categories=%d", 
                 manifest.total_items, manifest.total_categories)
        return manifest
    
    def save_category(self, result: ExtractionResult) -> Path:
        """Сохранить результат для одной категории."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = self._output_dir / f"{result.category.upper()}.json"
        data = [item.to_dict() for item in result.items]
        
        output_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info("saved category=%s path=%s items=%d", 
                 result.category, output_file, result.items_count)
        return output_file
    
    def save_all(self, manifest: WorldModelManifest | None = None) -> dict[str, Path]:
        """Сохранить все результаты."""
        manifest = manifest or self._manifest
        saved = {}
        
        for category, result in manifest.categories.items():
            if result.success and result.items_count > 0:
                path = self.save_category(result)
                saved[category] = path
        
        log.info("save_complete saved=%d", len(saved))
        return saved
    
    def load_knowledge_file(self, filename: str) -> list[dict]:
        """Загрузить JSON-файл из KNOWLEDGE."""
        filepath = self._knowledge_dir / filename
        if not filepath.exists():
            log.warning("knowledge_file_not_found path=%s", filepath)
            return []
        try:
            data = json.loads(filepath.read_text(encoding="utf-8-sig"))
            if isinstance(data, list):
                return data
            return [data]
        except Exception as e:
            log.error("knowledge_file_error path=%s error=%s", filepath, e)
            return []
    
    def get_manifest(self) -> WorldModelManifest:
        return self._manifest


def create_world_pipeline(knowledge_dir: Path | None = None) -> WorldExtractionPipeline:
    """Создать пайплайн с дефолтными экстракторами."""
    from .modules.geography import extract_geography
    from .modules.civilizations import extract_civilizations
    from .modules.architecture import extract_architecture
    from .modules.technologies import extract_technologies
    from .modules.economy import extract_economy
    from .modules.religion import extract_religion
    from .modules.philosophy import extract_philosophy
    from .modules.language import extract_language
    from .modules.mythology import extract_mythology
    from .modules.astronomy import extract_astronomy
    from .modules.flora import extract_flora
    from .modules.fauna import extract_fauna
    from .modules.transport import extract_transport
    from .modules.climate import extract_climate
    from .modules.chronology import extract_chronology
    from .modules.social_structure import extract_social_structure
    from .modules.daily_life import extract_daily_life
    from .modules.rituals import extract_rituals
    from .modules.education import extract_education
    from .modules.warfare import extract_warfare
    from .modules.crafts import extract_crafts
    
    pipeline = WorldExtractionPipeline(knowledge_dir=knowledge_dir)
    
    # Зарегистрировать экстракторы
    pipeline.register_extractor("geography", extract_geography)
    pipeline.register_extractor("civilizations", extract_civilizations)
    pipeline.register_extractor("architecture", extract_architecture)
    pipeline.register_extractor("technologies", extract_technologies)
    pipeline.register_extractor("economy", extract_economy)
    pipeline.register_extractor("religion", extract_religion)
    pipeline.register_extractor("philosophy", extract_philosophy)
    pipeline.register_extractor("language", extract_language)
    pipeline.register_extractor("mythology", extract_mythology)
    pipeline.register_extractor("astronomy", extract_astronomy)
    pipeline.register_extractor("flora", extract_flora)
    pipeline.register_extractor("fauna", extract_fauna)
    pipeline.register_extractor("transport", extract_transport)
    pipeline.register_extractor("climate", extract_climate)
    pipeline.register_extractor("chronology", extract_chronology)
    pipeline.register_extractor("social_structure", extract_social_structure)
    pipeline.register_extractor("daily_life", extract_daily_life)
    pipeline.register_extractor("rituals", extract_rituals)
    pipeline.register_extractor("education", extract_education)
    pipeline.register_extractor("warfare", extract_warfare)
    pipeline.register_extractor("crafts", extract_crafts)
    
    return pipeline

