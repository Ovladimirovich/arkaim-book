"""
adc_deps — FastAPI зависимости для ADC-компонентов.

Использует ServiceRegistry вместо @functools.cache для управления
 жизненным циклом экземпляров.
"""

import logging

from fastapi import Depends
from core.services.registry import registry

log = logging.getLogger("hermes.adc_deps")


# ── Фабрики (регистрируются один раз при импорте модуля) ──────


def _factory_pulse():
    from core.pulse_manager import get_pulse as _gp

    return _gp()


def _factory_voice():
    from core.pulse_manager import get_voice as _gv

    return _gv()


def _factory_config():
    from config import config

    return config


def _factory_retriever():
    from intelligence.retriever import BookRetriever

    return BookRetriever()


def _factory_keeper():
    from agents.keeper import KeeperAgent

    return KeeperAgent(pulse=registry.get("pulse"), voice=registry.get("voice"))


def _factory_herald():
    from agents.keeper import HeraldAgent

    return HeraldAgent(pulse=registry.get("pulse"))


def _factory_diplomat():
    from agents.keeper import DiplomatAgent

    return DiplomatAgent(pulse=registry.get("pulse"))


def _factory_scene_engine():
    from visualization.scene_engine import SceneEngine

    return SceneEngine(genome=registry.get("pulse").genome, retriever=registry.get("retriever"))


def _factory_prompt_builder():
    from visualization.prompt_builder import PromptBuilder

    return PromptBuilder(pulse=registry.get("pulse"))


# image_provider removed (Arkaim Media Boundary). Factory was: ComfyUIProvider chain.


# video_provider removed (Arkaim Media Boundary). Factory was: ImageSequence+MediaClient chain.


def _factory_asset_store():
    from visual_assets.storage import AssetStorage

    return AssetStorage()


# generation_pipeline removed (Arkaim Media Boundary). No local execution pipeline.


def _factory_film_store():
    from film_studio.store import FilmProjectStore

    return FilmProjectStore()


# generation_queue removed (Arkaim Media Boundary). No local generation workers.


def _factory_event_logger():
    from core_memory.logger import EventLogger

    return EventLogger()


def _factory_xray():
    from core_memory.analyzer import XRayObserver

    return XRayObserver()


def _factory_drafts():
    from community.telegram import DraftManager

    return DraftManager()


def _factory_telegram_stub():
    from community.telegram import TelegramBotStub

    return TelegramBotStub()


def _factory_reader_memory():
    from core.pulse_manager import get_reader_memory as _grm

    return _grm()


def _factory_graph_engine():
    from book_os.entity_store import EntityStore
    from book_os.relationship_store import RelationshipStore
    from book_os.fact_store import FactStore
    from knowledge_graph.graph_engine import GraphEngine

    entity_store = EntityStore()
    rel_store = RelationshipStore()
    fact_store = FactStore()
    engine = GraphEngine(entity_store, rel_store, fact_store)
    engine.build()
    return engine


# ── Регистрация ─────────────────────────────────────────────


def _factory_world_engine():
    from narrative_engine.world_model import WorldModel

    return WorldModel.load()


def _factory_story_engine():
    from narrative_engine.constraint_engine import parse_prompt
    from narrative_engine.canon_validator import CanonValidator
    from narrative_engine.context_assembler import ContextAssembler
    from narrative_engine.planner import UnifiedPlanner
    from narrative_engine.story.composer import compose_prompt, format_composer_prompt
    from narrative_engine.story.post_validator import validate_story
    from narrative_engine.world_model import WorldModel

    return {
        "parse": parse_prompt,
        "CanonValidator": CanonValidator,
        "ContextAssembler": ContextAssembler,
        "UnifiedPlanner": UnifiedPlanner,
        "compose_prompt": compose_prompt,
        "format_composer_prompt": format_composer_prompt,
        "validate": validate_story,
        "WorldModel": WorldModel,
    }


def _factory_research_engine():
    from narrative_engine.research.api_routes import _extract_simple

    return {"extract": _extract_simple}


# ── Visual Intelligence (core/CORE/visual/) ────────────────────


def _factory_visual_context_builder():
    from visual.visual_context_builder import VisualContextBuilder

    # MD-2: WorldModel подключается как read-only источник temporal-данных
    # (единственный источник; builder ничего не синтезирует сам).
    try:
        from narrative_engine.world_model import WorldModel

        wm = WorldModel.load()
    except Exception:
        wm = None
    return VisualContextBuilder(genome=registry.get("pulse").genome, retriever=registry.get("retriever"), world_model=wm)


def _factory_prompt_composer():
    """DEPRECATED (MD-3.3, audit D5): мёртвая DI-точка — 0 потребителей.

    Registry-key "prompt_composer" не запрашивается ни одним маршрутом
    (composer-рендер текста выполняется внутри MediaPlanBuilder —
    canonical path MD-3; см. ADR_MEDIA_PLAN_V0). Фабрика сохранена без
    изменения поведения для внешних/legacy-вызовов; удаление — MD-5+.
    """
    from visual.prompt_composer import PromptComposer

    return PromptComposer(generator="comfyui")


def _factory_continuity_engine():
    from visual.continuity_engine import ContinuityEngine

    return ContinuityEngine()


def _factory_video_intelligence():
    from visual.video_intelligence import VideoIntelligence

    return VideoIntelligence()


registry.register("pulse", _factory_pulse)
registry.register("voice", _factory_voice)
registry.register("config", _factory_config)
registry.register("retriever", _factory_retriever)
registry.register("keeper", _factory_keeper)
registry.register("herald", _factory_herald)
registry.register("diplomat", _factory_diplomat)
registry.register("scene_engine", _factory_scene_engine)
registry.register("prompt_builder", _factory_prompt_builder)
registry.register("asset_store", _factory_asset_store)
registry.register("film_store", _factory_film_store)
registry.register("event_logger", _factory_event_logger)
registry.register("xray", _factory_xray)
registry.register("drafts", _factory_drafts)
registry.register("telegram_stub", _factory_telegram_stub)
registry.register("reader_memory", _factory_reader_memory)
registry.register("graph_engine", _factory_graph_engine)
registry.register("world_engine", _factory_world_engine)
registry.register("story_engine", _factory_story_engine)
registry.register("research_engine", _factory_research_engine)
registry.register("visual_context_builder", _factory_visual_context_builder)
registry.register("prompt_composer", _factory_prompt_composer)
registry.register("continuity_engine", _factory_continuity_engine)
registry.register("video_intelligence", _factory_video_intelligence)


# ── Публичный API (совместимый с существующими роутами) ────────


def get_world_engine():
    return registry.get("world_engine")


def get_story_engine():
    return registry.get("story_engine")


def get_research_engine():
    return registry.get("research_engine")


def get_pulse():
    return registry.get("pulse")


def get_voice():
    return registry.get("voice")


def get_config():
    return registry.get("config")


def get_retriever():
    return registry.get("retriever")


def get_keeper():
    return registry.get("keeper")


def get_herald():
    return registry.get("herald")


def get_diplomat():
    return registry.get("diplomat")


def get_scene_engine():
    return registry.get("scene_engine")


def get_prompt_builder():
    return registry.get("prompt_builder")


# get_image_provider / get_video_provider removed (Arkaim Media Boundary).


def get_asset_store():
    return registry.get("asset_store")


# get_generation_pipeline removed (Arkaim Media Boundary).


def get_film_store():
    return registry.get("film_store")


# get_generation_queue removed (Arkaim Media Boundary).


def get_event_logger():
    return registry.get("event_logger")


def get_xray():
    return registry.get("xray")


def get_drafts():
    return registry.get("drafts")


def get_telegram_stub():
    return registry.get("telegram_stub")


def get_reader_memory():
    return registry.get("reader_memory")


def get_graph_engine():
    return registry.get("graph_engine")


# ── FastAPI Depends (для BOOK_DEPS) ──────────────────────────

BOOK_DEPS = {
    "config": Depends(get_config),
    "retriever": Depends(get_retriever),
    "keeper": Depends(get_keeper),
    "herald": Depends(get_herald),
    "diplomat": Depends(get_diplomat),
    "event_logger": Depends(get_event_logger),
    "xray": Depends(get_xray),
    "drafts": Depends(get_drafts),
    "telegram_stub": Depends(get_telegram_stub),
    "pulse": Depends(get_pulse),
    "voice": Depends(get_voice),
}


__all__ = [
    "get_config",
    "get_retriever",
    "get_keeper",
    "get_herald",
    "get_diplomat",
    "get_event_logger",
    "get_xray",
    "get_drafts",
    "get_telegram_stub",
    "get_pulse",
    "get_voice",
    "get_reader_memory",
    "get_world_engine",
    "get_story_engine",
    "get_research_engine",
    "get_scene_engine",
    "get_prompt_builder",
    "get_asset_store",
    "get_film_store",
    "BOOK_DEPS",
]
