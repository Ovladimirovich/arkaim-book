"""
Pipeline — оркестратор Knowledge Expansion Pipeline.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from .models import (
    RawKnowledge, EnrichedKnowledge, LinkedKnowledge,
    ValidatedKnowledge, EnrichmentModule, SaveResult
)
from .extractors.json_extractor import JSONExtractor
from .enrichers.deep_analyzer import DeepAnalyzer
from .linkers.graph_linker import GraphLinker
from .validators.schema_validator import SchemaValidator
from .store.knowledge_store import KnowledgeStore

log = logging.getLogger("hermes.knowledge_expansion.pipeline")

KNOWLEDGE_DIR = Path("core/KNOWLEDGE")


class KnowledgeExpansionPipeline:
    """
    Оркестратор пайплайна расширения знаний.
    
    Единый контракт для всех модулей обогащения:
    Источник → Извлечение → LLM-анализ → Проверка → Связывание → Хранение
    """

    def __init__(self, llm_client=None, graph_engine=None):
        self.extractor = JSONExtractor()
        self.enricher = DeepAnalyzer(llm_client=llm_client)
        self.linker = GraphLinker(graph_engine=graph_engine)
        self.validator = SchemaValidator()
        self.store = KnowledgeStore(knowledge_dir=KNOWLEDGE_DIR)
        self._modules: dict[str, dict] = {}

    def register_module(self, name: str, config: dict):
        """Зарегистрировать модуль обогащения."""
        self._modules[name] = config
        log.info("module_registered name=%s", name)

    async def run_module(self, module_name: str) -> SaveResult:
        """Запустить конкретный модуль обогащения."""
        if module_name not in self._modules:
            raise ValueError(f"Module '{module_name}' not registered")

        config = self._modules[module_name]
        source_files = config.get("source_files", [])
        output_file = Path(config.get("output_file", f"core/KNOWLEDGE/{module_name.upper()}.json"))

        log.info("module_started name=%s sources=%d", module_name, len(source_files))

        # 1. Извлечение
        raw = []
        for source_file in source_files:
            extracted = await self.extractor.extract(source_file)
            raw.extend(extracted)
        log.info("extraction_complete count=%d", len(raw))

        if not raw:
            log.warning("no_knowledge_extracted module=%s", module_name)
            return SaveResult(
                success=True, items_saved=0, items_skipped=0,
                output_path=str(output_file), graph_updates=0,
            )

        # 2. Обогащение
        enriched = await self.enricher.enrich(raw)
        log.info("enrichment_complete count=%d", len(enriched))

        # 3. Связывание с графом
        linked = await self.linker.link(enriched)
        log.info("linking_complete count=%d", len(linked))

        # 4. Валидация
        validated = await self.validator.validate(linked)
        log.info("validation_complete count=%d", len(validated))

        # 5. Сохранение
        result = await self.store.save(validated, output_file)
        log.info("module_complete name=%s saved=%d skipped=%d",
                 module_name, result.items_saved, result.items_skipped)

        return result

    async def run_all(self) -> dict[str, SaveResult]:
        """Запустить все зарегистрированные модули."""
        results = {}
        for module_name in self._modules:
            try:
                result = await self.run_module(module_name)
                results[module_name] = result
            except Exception as e:
                log.error("module_failed name=%s error=%s", module_name, e)
                results[module_name] = SaveResult(
                    success=False, items_saved=0, items_skipped=0,
                    output_path="", graph_updates=0,
                )
        return results

    def get_status(self) -> dict:
        """Получить статус пайплайна."""
        return {
            "modules": list(self._modules.keys()),
            "module_count": len(self._modules),
            "knowledge_dir": str(KNOWLEDGE_DIR),
        }


def create_default_pipeline(llm_client=None, graph_engine=None) -> KnowledgeExpansionPipeline:
    """Создать пайплайн с дефолтными модулями."""
    pipeline = KnowledgeExpansionPipeline(llm_client=llm_client, graph_engine=graph_engine)

    # Зарегистрировать модули
    pipeline.register_module("philosophy_deep", {
        "description": "Глубокий анализ философских концепций",
        "source_files": [KNOWLEDGE_DIR / "PHILOSOPHY.json"],
        "output_file": KNOWLEDGE_DIR / "PHILOSOPHY_DEEP.json",
    })

    pipeline.register_module("themes_deep", {
        "description": "Глубокий анализ тем",
        "source_files": [KNOWLEDGE_DIR / "THEMES_DEEP.json"],
        "output_file": KNOWLEDGE_DIR / "THEMES_EXPANDED.json",
    })

    pipeline.register_module("symbols_expanded", {
        "description": "Расширенные толкования символов",
        "source_files": [KNOWLEDGE_DIR / "SYMBOLS_EXPANDED.json"],
        "output_file": KNOWLEDGE_DIR / "SYMBOLS_DEEP.json",
    })

    pipeline.register_module("cross_references", {
        "description": "Кросс-референсы с мировыми культурами",
        "source_files": [KNOWLEDGE_DIR / "CROSS_REFERENCES.json"],
        "output_file": KNOWLEDGE_DIR / "CROSS_REFERENCES_DEEP.json",
    })

    pipeline.register_module("archaeology", {
        "description": "Археологические данные",
        "source_files": [KNOWLEDGE_DIR / "ARCHAEOLOGY.json"],
        "output_file": KNOWLEDGE_DIR / "ARCHAEOLOGY_DEEP.json",
    })


    pipeline.register_module("cosmology", {
        "description": "Космологические знания",
        "source_files": [KNOWLEDGE_DIR / "THEMES_DEEP.json", KNOWLEDGE_DIR / "ESOTERIC_CONNECTIONS.json"],
        "output_file": KNOWLEDGE_DIR / "COSMOLOGY.json",
    })

    pipeline.register_module("geography", {
        "description": "География и энергетика мест",
        "source_files": [KNOWLEDGE_DIR / "MAP_DATA.json", KNOWLEDGE_DIR / "ARCHAEOLOGY.json"],
        "output_file": KNOWLEDGE_DIR / "GEOGRAPHY.json",
    })

    pipeline.register_module("psychology", {
        "description": "Психология персонажей",
        "source_files": [KNOWLEDGE_DIR / "THEMES_DEEP.json", KNOWLEDGE_DIR / "SYMBOLS_EXPANDED.json"],
        "output_file": KNOWLEDGE_DIR / "PSYCHOLOGY.json",
    })

    pipeline.register_module("language", {
        "description": "Язык и терминология",
        "source_files": [KNOWLEDGE_DIR / "PHILOSOPHY.json", KNOWLEDGE_DIR / "CROSS_REFERENCES.json"],
        "output_file": KNOWLEDGE_DIR / "LANGUAGE.json",
    })

    pipeline.register_module("rituals", {
        "description": "Ритуалы и практики",
        "source_files": [KNOWLEDGE_DIR / "ESOTERIC_CONNECTIONS.json"],
        "output_file": KNOWLEDGE_DIR / "RITUALS.json",
    })

    pipeline.register_module("technology", {
        "description": "Технологии гипербореев",
        "source_files": [KNOWLEDGE_DIR / "ARCHAEOLOGY.json", KNOWLEDGE_DIR / "THEMES_DEEP.json"],
        "output_file": KNOWLEDGE_DIR / "TECHNOLOGY.json",
    })

# Screenplay modules
    pipeline.register_module("screenplay_dialogues", {
        "description": "Анализ ключевых диалогов сценария",
        "source_files": [KNOWLEDGE_DIR / "screenplay_extracts.json"],
        "output_file": KNOWLEDGE_DIR / "SCREENPLAY_DIALOGUES.json",
    })

    pipeline.register_module("screenplay_characters", {
        "description": "Анализ персонажей сценария и их речевых паттернов",
        "source_files": [KNOWLEDGE_DIR / "screenplay_extracts.json"],
        "output_file": KNOWLEDGE_DIR / "SCREENPLAY_CHARACTERS.json",
    })

    pipeline.register_module("screenplay_visual", {
        "description": "Визуальные описания и кинематографический язык",
        "source_files": [KNOWLEDGE_DIR / "screenplay_extracts.json"],
        "output_file": KNOWLEDGE_DIR / "SCREENPLAY_VISUAL.json",
    })

    return pipeline

