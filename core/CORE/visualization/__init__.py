"""Visualization Layer — сцены, персонажи, визуальный геном."""
from visualization.scene_engine import SceneEngine
from visualization.visual_genome import VisualGenomeStore
from visualization.character_visualizer import CharacterVisualizer
from visualization.world_visualizer import WorldVisualizer
from visualization.archetype_visuals import (
    archetype_to_visual, fill_missing_archetype_visuals,
    ARCHETYPE_VISUAL_TEMPLATES,
)
from visualization.conflict_palettes import (
    generate_all_conflict_scenes, generate_conflict_scene,
    CONFLICT_TEMPLATES,
)
from visualization.meaning_to_visual import (
    generate_visuals_from_meaning, EMOTION_MAP, PALETTE_MAP,
)
from visualization.xray_visual_triggers import XRayVisualTriggers
from providers.image import ImageProvider, ImageProviderChain

__all__ = [
    "SceneEngine",
    "VisualGenomeStore",
    "CharacterVisualizer",
    "WorldVisualizer",
    "archetype_to_visual",
    "fill_missing_archetype_visuals",
    "ARCHETYPE_VISUAL_TEMPLATES",
    "generate_all_conflict_scenes",
    "generate_conflict_scene",
    "CONFLICT_TEMPLATES",
    "generate_visuals_from_meaning",
    "EMOTION_MAP",
    "PALETTE_MAP",
    "XRayVisualTriggers",
    "ImageProvider",
    "ImageProviderChain",
]
