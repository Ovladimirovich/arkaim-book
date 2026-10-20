"""VisualContextBuilder — собирает VisualContext из Genome + VISUAL_KNOWLEDGE."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .visual_context import VisualContext
from .scene_context import SourceRefs, extend_visual_context  # MD-2
from .visual_models import (
    SceneContext, LocationContext, ArchitectureContext, LandscapeContext,
    EnvironmentContext, LightingContext, PaletteContext, AtmosphereContext,
    SymbolContext, HistoricalContext, CameraContext, StyleContext,
    EmotionContext, CharacterVisualContext, NegativePromptContext,
)
from knowledge.screenplay_scene_catalog import (
    CATALOG_CHAPTER,
    get_scene as get_catalog_scene,
)

if TYPE_CHECKING:  # MD-2: тип для аннотаций (runtime-импорт не нужен)
    from .scene_context import TemporalSceneRef

log = logging.getLogger("visual.context_builder")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"

# ── Русско-английский маппинг для обратной совместимости ────────
_EMOTION_RU_TO_EN = {
    "конфликт": "conflict",
    "конфликт_цивилизаций": "conflict_civilizations",
    "смена_эпох": "era_transition",
    "дуальность_бытия": "duality_of_existence",
    "борьба_противоположностей": "struggle_of_opposites",
}

def _normalize_emotion(emotion: str) -> str:
    """Нормализовать эмоцию: русские ключи → английские."""
    return _EMOTION_RU_TO_EN.get(emotion, emotion)


# ── Маппинг эмоций в визуальные описания ─────────────────────────
EMOTION_TO_VISUAL = {
    "warm_intimate": "warm firelight, intimate atmosphere, soft golden glow",
    "melancholic_dark": "dim lighting, deep shadows, melancholic blue-grey tones",
    "hopeful_golden": "golden hour, warm sunlight, hopeful atmosphere, ray of light",
    "dark_mystical": "deep purples and blues, misty, mystical glow, moonlight",
    "dramatic_contrast": "strong chiaroscuro, dramatic shadows, high contrast lighting",
    "ethereal_light": "soft divine glow, translucent light, heavenly radiance",
    "sepia_flashback": "warm sepia tones, vintage atmosphere, faded memories",
    "ceremonial_warm": "warm torchlight, ceremonial glow, amber tones, ritual atmosphere",
    "sacred_glow": "divine golden light, halo effect, sacred radiance, luminous",
    "conflict": "harsh lighting, stormy atmosphere, clashing colors, tension",
    "melancholic_hopeful": "soft dawn light, warm tones emerging from cool shadows, hope after sorrow",
    "neutral": "balanced natural lighting, clear visibility, neutral tones",
    "bright_warm": "bright sunny day, warm cheerful atmosphere, vibrant colors",
    "calm_acceptance": "soft evening light, peaceful atmosphere, gentle warm tones",
    "duality_contrast": "split lighting, warm vs cool, dual atmosphere, conflicting elements",
    "conflict_civilizations": "epic scale, clashing civilizations, contrasting color temperatures",
    "era_transition": "transitional lighting, old meets new, dramatic sky transformation",
    "progressive_light": "evolving illumination, dynamic light shifts, forward momentum glow, gradual illumination, emerging radiance",
    "warm_devotion": "soft amber glow, devoted warmth, gentle radiance, service light, spiritual atmosphere, reverent glow",
    "epic_reveal": "dramatic unveiling, golden spotlight, grand discovery illumination, epic revelation scene",
    "harmonious_blend": "seamless color fusion, balanced tones, unified light spectrum, harmonious colors, unified atmosphere",
    "metamorphosis": "shifting colors, transformation glow, chrysalis light, emergence radiance, dynamic atmosphere",
    "determined_purposeful": "steady focused light, resolute atmosphere, purposeful beam",
    "awe_wonder": "sublime vastness, overwhelming scale, celestial radiance, breathless glow",
    "tense_anticipatory": "flickering uncertainty, charged atmosphere, pre-storm tension light",
    "duality_of_existence": "ethereal meets earthly, translucent overlays, dual reality",
    "struggle_of_opposites": "chaotic lighting, clashing elements, dynamic tension",
}

EMOTION_SUFFIX = {
    "warm_intimate": "intimate and personal, close atmosphere",
    "hopeful_golden": "hopeful and inspiring, optimistic tone",
    "ceremonial_warm": "sacred and ritualistic, reverent atmosphere",
    "sacred_glow": "divine and holy, transcendent radiance",
    "conflict": "tense and volatile, unstable energy",
    "neutral": "peaceful and clear, undisturbed",
    "progressive_light": "evolving and dynamic, forward-moving energy",
    "warm_devotion": "devoted and selfless, gentle service warmth",
    "epic_reveal": "grand and momentous, dramatic unveiling",
    "harmonious_blend": "unified and balanced, seamless integration",
    "metamorphosis": "transformative and shifting, emergence energy",
    "determined_purposeful": "focused and resolute, unwavering purpose",
    "awe_wonder": "overwhelmed and sublime, breathless vastness",
    "tense_anticipatory": "charged and waiting, pre-event tension",
}

# ── Маппинг типов локаций ───────────────────────────────────────
LOCATION_TYPE_VISUALS = {
    "ancient_settlement": "ancient circular fortified settlement, Bronze Age stone walls",
    "ancient_temple": "ancient stone temple, weathered pillars, sacred geometry, moss-covered stones",
    "forest": "dense ancient forest, towering trees, dappled sunlight through canopy",
    "mountain": "towering mountain peaks, rocky terrain, dramatic clouds, alpine atmosphere, misty peaks",
    "river": "flowing river, misty banks, reflections on water, riverbank, gentle current",
    "steppe": "vast open steppe, rolling grasslands, infinite sky",
    "underground": "underground chamber, torchlit tunnels, carved stone",
    "city": "ancient city center, bustling market, stone buildings, winding streets, market squares",
    "coastal": "dramatic coastline, crashing waves, sea cliffs",
    "ruins": "ancient ruins, crumbling walls, nature reclaiming stone",
    "stone_gateway": "megalithic stone gateway, standing stones, ancient portal, dolmen",
    "cave": "dark cave system, crystalline formations, underground river, stalactites",
    "hall": "grand hall, high ceilings, torchlight on stone walls, tapestries",
    "altar": "sacred altar, offerings, ceremonial space, ancient symbols",
    "border": "boundary between worlds, ethereal transition, misty divide",
    "unknown": "mystical landscape, ancient world, timeless setting",
}

# ── Качество и negative-промпт (единый источник значений) ───────
QUALITY_SUFFIXES = [
    "cinematic lighting",
    "highly detailed",
    "intricate details",
    "epic composition",
    "atmospheric",
    "professional photography",
    "8k",
    "sharp focus",
    "dramatic lighting",
    "beautiful detailed environment",
]

NEGATIVE_PROMPT_DEFAULT = (
    "blurry, low quality, cartoon, anime, oversaturated, "
    "ugly, deformed, distorted, bad anatomy, watermark, text, "
    "extra limbs, fused fingers, too many fingers, "
    "worst quality, low resolution, grainy, jpeg artifacts"
)

# ── Камера ───────────────────────────────────────────────────────
CAMERA_SHOTS = {
    "extreme_wide": {"lens": "14mm", "composition": "vast establishing shot, small figures in landscape"},
    "wide": {"lens": "24mm", "composition": "full scene visible, environment context"},
    "medium": {"lens": "50mm", "composition": "waist-up, standard cinematic framing"},
    "close_up": {"lens": "85mm", "composition": "face detail, emotional depth"},
    "extreme_close_up": {"lens": "100mm macro", "composition": "eye or hand detail, symbolic"},
}


class VisualContextBuilder:
    """Собирает VisualContext из Genome + VISUAL_KNOWLEDGE JSON."""

    def __init__(self, genome: dict, retriever=None, world_model=None):
        self._genome = genome
        self._retriever = retriever
        # MD-2: опциональный WorldModel — единственный источник temporal-данных
        # (read-only). None → temporal-ссылка просто не заполняется.
        self._world_model = world_model
        self._knowledge = self._load_knowledge()

    def _load_knowledge(self) -> dict:
        """Загрузить все JSON-библиотеки из VISUAL_KNOWLEDGE/."""
        knowledge = {}
        for name in ("LOCATION_VISUALS", "CHARACTER_VISUALS", "ATMOSPHERES",
                      "VISUAL_SYMBOLS", "CAMERA_LIBRARY", "STYLE_LIBRARY",
                      "SHOT_LIBRARY", "VIDEO_RULES"):
            path = _KNOWLEDGE_DIR / f"{name}.json"
            if path.exists():
                try:
                    knowledge[name] = json.loads(path.read_text("utf-8-sig"))
                except Exception as e:
                    log.warning("knowledge_load_failed name=%s error=%s", name, e)
                    knowledge[name] = {}
            else:
                knowledge[name] = {}
        return knowledge

    async def build(self, chapter: int, scene_id: str, time_of_day: str = "dawn") -> VisualContext:
        """Собрать полный VisualContext для сцены.

        MD-2 DEPRECATED как точка НОВОГО входа: маршруты используют
        build_scene_context (visual_context + scene_extras). Метод
        сохранён: (а) как внутренняя основа build_scene_context;
        (б) для legacy-совместимости любых внешних вызовов. НЕ УДАЛЁН.
        """
        ctx = VisualContext()

        # 1. Сцена из genome
        ctx.scene = self._build_scene(chapter, scene_id)

        # 2. Локация
        ctx.location = self._build_location(ctx.scene)

        # 3. Архитектура и ландшафт из локации
        ctx.architecture = ctx.location.architecture
        ctx.landscape = ctx.location.landscape

        # 4. Окружение
        ctx.environment = self._build_environment(time_of_day)

        # 5. Освещение
        ctx.lighting = self._build_lighting(ctx.location, time_of_day)

        # 6. Палитра
        ctx.palette = self._build_palette(ctx.location, ctx.scene)

        # 7. Атмосфера
        ctx.atmosphere = self._build_atmosphere(ctx.scene.emotion, time_of_day)

        # 8. Символы
        ctx.symbols = self._build_symbols(ctx.scene.meaning_tags)

        # 9. Исторический контекст
        ctx.historical = self._build_historical(ctx.location)

        # 10. Камера
        ctx.camera = self._build_camera(ctx.scene)

        # 11. Стиль
        ctx.style = self._build_style(ctx.scene)

        # 12. Эмоция
        ctx.emotion = self._build_emotion(ctx.scene.emotion)

        # 13. Персонажи
        ctx.characters = self._build_characters(ctx.scene)

        # 14. Negative prompt
        ctx.negative_prompt = NegativePromptContext()

        log.info("context_built %s", ctx.summary())
        return ctx

    def _build_scene(self, chapter: int, scene_id: str) -> SceneContext:
        """Найти сцену в genome."""
        if chapter == CATALOG_CHAPTER:
            catalog_scene = get_catalog_scene(scene_id)
            if catalog_scene is not None:
                return SceneContext(
                    chapter=CATALOG_CHAPTER,
                    scene_id=scene_id,
                    title=catalog_scene.get("title", ""),
                    description=catalog_scene.get("title", ""),
                    emotion=catalog_scene.get("emotion", ""),
                    meaning_tags=catalog_scene.get("meaning_tags", []),
                    location=catalog_scene.get("location", ""),
                    characters=catalog_scene.get("characters", []),
                )
            return SceneContext(chapter=CATALOG_CHAPTER, scene_id=scene_id)

        scenes = self._genome.get("modules", {}).get("scenes", [])
        for scene in scenes:
            if scene.get("chapter") == chapter and scene.get("scene_id") == scene_id:
                return SceneContext(
                    chapter=chapter,
                    scene_id=scene_id,
                    title=scene.get("title", ""),
                    description=scene.get("title", ""),
                    emotion=scene.get("emotion", "neutral"),
                    meaning_tags=scene.get("meaning_tags", []),
                )
        # Fallback: создать базовую сцену
        return SceneContext(chapter=chapter, scene_id=scene_id, title=f"Scene {scene_id}")

    def _build_location(self, scene: SceneContext) -> LocationContext:
        """Найти локацию в genome + обогатить из VISUAL_KNOWLEDGE."""
        location_id = scene.location or ""
        if not location_id:
            scenes = self._genome.get("modules", {}).get("scenes", [])
            for s in scenes:
                if s.get("scene_id") == scene.scene_id:
                    location_id = s.get("location", "")
                    break

        if not location_id:
            return LocationContext(name="unknown")

        # Обогащение из VISUAL_KNOWLEDGE (приоритет)
        knowledge_locs = self._knowledge.get("LOCATION_VISUALS", {})
        if location_id in knowledge_locs:
            k = knowledge_locs[location_id]
            arch_data = k.get("architecture", {})
            land_data = k.get("landscape", {})
            arch = ArchitectureContext(
                style=arch_data.get("style", ""),
                materials=arch_data.get("materials", ""),
                features=arch_data.get("features", []),
                age=arch_data.get("age", ""),
            )
            land = LandscapeContext(
                terrain=land_data.get("terrain", ""),
                vegetation=land_data.get("vegetation", ""),
                water=land_data.get("water", ""),
                sky=land_data.get("sky", ""),
            )
            return LocationContext(
                location_id=location_id,
                name=location_id,
                type=k.get("type", "unknown"),
                architecture=arch,
                landscape=land,
                palette=k.get("palette", []),
                atmosphere_default=k.get("atmosphere", {}).get("default", ""),
                atmosphere_by_time=k.get("atmosphere", {}).get("time_variants", {}),
                sound=k.get("sound", ""),
                symbols=k.get("symbols", []),
            )

        # Fallback: world_entities
        for we in self._genome.get("world_entities", []):
            if we.get("name", "").lower() == location_id.lower():
                return LocationContext(
                    location_id=location_id,
                    name=location_id,
                    architecture=ArchitectureContext(style=we.get("description", "")[:100]),
                )

        return LocationContext(location_id=location_id, name=location_id)

    def _build_environment(self, time_of_day: str) -> EnvironmentContext:
        """Окружение на основе времени дня."""
        return EnvironmentContext(time_of_day=time_of_day)

    def _build_lighting(self, location: LocationContext, time_of_day: str) -> LightingContext:
        """Освещение на основе локации и времени дня."""
        # Попробовать из атмосферы локации
        if location.atmosphere_by_time and time_of_day in location.atmosphere_by_time:
            desc = location.atmosphere_by_time[time_of_day]
            return LightingContext(description=desc, source="natural")

        # Fallback по времени дня
        time_lighting = {
            "dawn": LightingContext(source="natural", direction="east, low", color="golden", intensity="soft", description="golden hour, first rays"),
            "day": LightingContext(source="natural", direction="overhead", color="bright white", intensity="strong", description="bright daylight"),
            "dusk": LightingContext(source="natural", direction="west, low", color="amber", intensity="fading", description="golden hour, long shadows"),
            "night": LightingContext(source="artificial", direction="ambient", color="cool blue", intensity="dim", description="moonlight, torchlight"),
        }
        return time_lighting.get(time_of_day, LightingContext())

    def _build_palette(self, location: LocationContext, scene: SceneContext) -> PaletteContext:
        """Палитра из локации и сцены."""
        primary = location.palette if location.palette else ["#DAA520", "#8B4513", "#708090"]
        return PaletteContext(
            primary=primary,
            contrast="warm",
            description=f"palette of {location.name or 'ancient world'}",
        )

    def _build_atmosphere(self, emotion: str, time_of_day: str) -> AtmosphereContext:
        """Атмосфера из библиотеки атмосфер."""
        atmospheres = self._knowledge.get("ATMOSPHERES", {})

        # Определить имя атмосферы
        atmo_name = "neutral"
        if "conflict" in _normalize_emotion(emotion):
            atmo_name = "military"
        elif "sacred" in emotion or "ceremonial" in emotion or "ritual" in emotion:
            atmo_name = "sacred"
        elif "dawn" in time_of_day or "pre_dawn" in time_of_day:
            atmo_name = "pre_dawn"
        elif "fear" in emotion or "anxious" in emotion:
            atmo_name = "anxious"

        if atmo_name in atmospheres:
            a = atmospheres[atmo_name]
            return AtmosphereContext(
                name=atmo_name,
                light=a.get("light", ""),
                fog=a.get("fog", ""),
                wind=a.get("wind", ""),
                particles=a.get("particles", ""),
                sound=a.get("sound", ""),
                color_temperature=a.get("color_temperature", ""),
                contrast=a.get("contrast", ""),
                camera_dynamics=a.get("camera_dynamics", ""),
            )

        return AtmosphereContext(name=atmo_name)

    def _build_symbols(self, meaning_tags: list[str]) -> list[SymbolContext]:
        """Символы из meaning_tags + VISUAL_SYMBOLS."""
        symbols_db = self._knowledge.get("VISUAL_SYMBOLS", {})
        result = []
        for tag in meaning_tags:
            tag_clean = tag.split(":")[-1] if ":" in tag else tag
            if tag_clean in symbols_db:
                s = symbols_db[tag_clean]
                result.append(SymbolContext(
                    name=tag_clean,
                    literal=s.get("literal", ""),
                    metaphorical=s.get("metaphorical", ""),
                    spiritual=s.get("spiritual", ""),
                    archetypal=s.get("archetypal", ""),
                    colors=s.get("colors", []),
                    visual_elements=s.get("visual_elements", []),
                ))
            else:
                result.append(SymbolContext(name=tag_clean, literal=tag_clean))
        return result

    def _build_historical(self, location: LocationContext) -> HistoricalContext:
        """Исторический контекст из genome world_entities."""
        for we in self._genome.get("world_entities", []):
            if we.get("name", "").lower() == (location.name or "").lower():
                return HistoricalContext(
                    civilization=we.get("name", ""),
                    cultural_notes=we.get("description", "")[:200],
                )
        return HistoricalContext()

    def _build_camera(self, scene: SceneContext) -> CameraContext:
        """Камера по умолчанию для сцены."""
        camera_lib = self._knowledge.get("CAMERA_LIBRARY", {})
        shot_types = camera_lib.get("shot_types", {})

        # Определить тип шота по эмоции
        if "conflict" in _normalize_emotion(scene.emotion):
            shot = "medium"
        elif "epic" in scene.title.lower() or "панорам" in scene.title.lower():
            shot = "extreme_wide"
        else:
            shot = "wide"

        shot_data = shot_types.get(shot, {})
        return CameraContext(
            shot_type=shot,
            lens=shot_data.get("lens", "50mm"),
            composition=shot_data.get("composition", ""),
        )

    def _build_style(self, scene: SceneContext) -> StyleContext:
        """Стиль по умолчанию."""
        return StyleContext(name="cinematic_fantasy", prefix="cinematic fantasy, epic film still, dramatic lighting")

    def _build_emotion(self, emotion: str) -> EmotionContext:
        """Эмоция → визуальное описание."""
        visual = EMOTION_TO_VISUAL.get(emotion, emotion.replace("_", " "))
        suffix = EMOTION_SUFFIX.get(emotion, "")
        return EmotionContext(name=emotion, visual=visual, suffix=suffix)

    def _build_characters(self, scene: SceneContext) -> list[CharacterVisualContext]:
        """Персонажи из genome + VISUAL_KNOWLEDGE."""
        char_visuals = self._knowledge.get("CHARACTER_VISUALS", {})
        result = []
        for char_id in scene.characters:
            if char_id in char_visuals:
                cv = char_visuals[char_id]
                result.append(CharacterVisualContext(
                    character_id=char_id,
                    name=char_id,
                    age_range=cv.get("age_range", ""),
                    face=cv.get("face", ""),
                    hair=cv.get("hair", ""),
                    eyes=cv.get("eyes", ""),
                    build=cv.get("build", ""),
                    clothing=str(cv.get("clothing", "")),
                    accessories=cv.get("accessories", []),
                    mannerisms=cv.get("mannerisms", ""),
                    movement=cv.get("movement", ""),
                    appearance_summary=f"{char_id}, {cv.get('build', '')}, {cv.get('hair', '')}",
                ))
            else:
                # Fallback: genome character_visuals
                for gcv in self._genome.get("modules", {}).get("character_visuals", []):
                    if gcv.get("character_id") == char_id:
                        result.append(CharacterVisualContext(
                            character_id=char_id,
                            name=char_id,
                            build=gcv.get("build", ""),
                            clothing=gcv.get("clothing", ""),
                            appearance_summary=gcv.get("clothing", "")[:100],
                        ))
                        break
        return result

    # ── Прямая генерация по character_id / location_id ──────────────

    def _build_single_character(self, character_id: str) -> CharacterVisualContext | None:
        """Найти одного персонажа по ID."""
        char_visuals = self._knowledge.get("CHARACTER_VISUALS", {})
        if character_id in char_visuals:
            cv = char_visuals[character_id]
            return CharacterVisualContext(
                character_id=character_id,
                name=character_id,
                age_range=cv.get("age_range", ""),
                face=cv.get("face", ""),
                hair=cv.get("hair", ""),
                eyes=cv.get("eyes", ""),
                build=cv.get("build", ""),
                clothing=str(cv.get("clothing", "")),
                accessories=cv.get("accessories", []),
                mannerisms=cv.get("mannerisms", ""),
                movement=cv.get("movement", ""),
                appearance_summary=f"{character_id}, {cv.get('build', '')}, {cv.get('hair', '')}",
            )
        # Fallback: genome character_visuals
        for gcv in self._genome.get("modules", {}).get("character_visuals", []):
            if gcv.get("character_id") == character_id:
                return CharacterVisualContext(
                    character_id=character_id,
                    name=character_id,
                    build=gcv.get("build", ""),
                    clothing=gcv.get("clothing", ""),
                    appearance_summary=gcv.get("visual_description", "")[:200],
                )
        return None

    def _build_location_from_id(self, location_id: str) -> LocationContext:
        """Найти локацию по ID (аналог _build_location, но без сцены)."""
        knowledge_locs = self._knowledge.get("LOCATION_VISUALS", {})
        if location_id in knowledge_locs:
            k = knowledge_locs[location_id]
            arch_data = k.get("architecture", {})
            land_data = k.get("landscape", {})
            arch = ArchitectureContext(
                style=arch_data.get("style", ""),
                materials=arch_data.get("materials", ""),
                features=arch_data.get("features", []),
                age=arch_data.get("age", ""),
            )
            land = LandscapeContext(
                terrain=land_data.get("terrain", ""),
                vegetation=land_data.get("vegetation", ""),
                water=land_data.get("water", ""),
                sky=land_data.get("sky", ""),
            )
            return LocationContext(
                location_id=location_id,
                name=location_id,
                type=k.get("type", "unknown"),
                architecture=arch,
                landscape=land,
                palette=k.get("palette", []),
                atmosphere_default=k.get("atmosphere", {}).get("default", ""),
                atmosphere_by_time=k.get("atmosphere", {}).get("time_variants", {}),
                sound=k.get("sound", ""),
                symbols=k.get("symbols", []),
            )
        # Fallback: world_entities
        for we in self._genome.get("world_entities", []):
            if we.get("name", "").lower() == location_id.lower():
                return LocationContext(
                    location_id=location_id,
                    name=location_id,
                    architecture=ArchitectureContext(style=we.get("description", "")[:100]),
                )
        return LocationContext(location_id=location_id, name=location_id)

    async def build_for_character(self, character_id: str, time_of_day: str = "dawn") -> VisualContext:
        """Собрать VisualContext для одного персонажа (портрет).

        MD-2 DEPRECATED как точка НОВОГО входа: маршруты используют
        build_scene_context_for_character. Метод сохранён как
        внутренняя основа и для legacy-совместимости. НЕ УДАЛЁН.
        """
        ctx = VisualContext()
        ctx.scene = SceneContext()
        ctx.characters = [c for c in [self._build_single_character(character_id)] if c]
        ctx.environment = self._build_environment(time_of_day)
        ctx.camera = CameraContext(shot_type="close_up", lens="85mm", composition="portrait framing")
        ctx.style = self._build_style(ctx.scene)
        ctx.emotion = self._build_emotion("neutral")
        ctx.atmosphere = self._build_atmosphere("neutral", time_of_day)
        ctx.negative_prompt = NegativePromptContext()
        log.info("context_built_character character_id=%s", character_id)
        return ctx

    async def build_for_location(self, location_id: str, time_of_day: str = "dawn") -> VisualContext:
        """Собрать VisualContext для локации (пейзаж/архитектура).

        MD-2 DEPRECATED как точка НОВОГО входа: маршруты используют
        build_scene_context_for_location. Метод сохранён как
        внутренняя основа и для legacy-совместимости. НЕ УДАЛЁН.
        """
        ctx = VisualContext()
        ctx.scene = SceneContext()
        ctx.location = self._build_location_from_id(location_id)
        ctx.architecture = ctx.location.architecture
        ctx.landscape = ctx.location.landscape
        ctx.environment = self._build_environment(time_of_day)
        ctx.lighting = self._build_lighting(ctx.location, time_of_day)
        ctx.palette = self._build_palette(ctx.location, ctx.scene)
        ctx.atmosphere = self._build_atmosphere("neutral", time_of_day)
        ctx.historical = self._build_historical(ctx.location)
        ctx.camera = CameraContext(shot_type="extreme_wide", lens="24mm", composition="establishing shot")
        ctx.style = self._build_style(ctx.scene)
        ctx.emotion = self._build_emotion("neutral")
        ctx.characters = []
        ctx.negative_prompt = NegativePromptContext()
        log.info("context_built_location location_id=%s", location_id)
        return ctx

    # ── MD-2: Scene Context Consolidation ─────────────────────────

    def _resolve_epoch_for_chapter(self, chapter: int) -> str | None:
        """Найти epoch_id для главы по СУЩЕСТВУЮЩИМ данным WorldModel.

        Никакого угадывания: единственная фактическая связь «глава→эпоха»
        в проекте — canonical_events WorldModel (поле chapter). Если у
        главы нет событий или WorldModel не подключён — None (сцена
        остаётся вне temporal-оси; это честное состояние, не ошибка).
        """
        wm = self._world_model
        if wm is None or not chapter:
            return None
        try:
            for event in wm.get_events():
                if event.chapter == chapter and event.epoch and event.epoch != "unknown":
                    return event.epoch
        except Exception as e:
            log.warning("epoch_resolve_failed chapter=%s error=%s", chapter, e)
            return None
        return None

    def _temporal_ref_from_epoch(self, epoch_id: str) -> "TemporalSceneRef":
        """TemporalSceneRef из СУЩЕСТВУЮЩЕГО WorldModel.get_temporal_context.

        Read-only проекция: TemporalNode.provenance → ProvenanceRef (дедуп
        по категории — тот же паттерн, что C1-enrichment), bounds/счётчики
        берутся как есть. Никаких новых provenance-значений не создаётся.
        """
        from .scene_context import TemporalSceneRef, ProvenanceRef

        wm = self._world_model
        context = wm.get_temporal_context(epoch_id) if wm is not None else {}
        node = (context or {}).get("temporal_node") or {}
        epoch = (context or {}).get("epoch") or {}
        bounds = node.get("bounds") or {}

        provenance: list[ProvenanceRef] = []
        seen_cats: set[str] = set()
        for tag in node.get("provenance", []):
            cat = str(tag.get("category", ""))
            if cat and cat not in seen_cats:
                seen_cats.add(cat)
                provenance.append(ProvenanceRef(
                    category=cat,
                    source=str(tag.get("source", "")),
                    confidence=float(tag.get("confidence", 0.0) or 0.0),
                ))

        return TemporalSceneRef(
            epoch_id=str(node.get("id") or epoch_id),
            name_ru=str(epoch.get("name_ru") or node.get("label", "")),
            confidence=float(node.get("confidence", 0.0) or 0.0),
            bounds_start=str(bounds.get("start") or ""),
            bounds_end=str(bounds.get("end") or ""),
            bounds_uncertainty=str(bounds.get("uncertainty") or ""),
            provenance=provenance,
            event_count=int(context.get("event_count", 0) or 0),
            character_count=int(context.get("character_count", 0) or 0),
            technology_count=int(context.get("technology_count", 0) or 0),
        )

    def _apply_scene_extras(self, ctx: VisualContext, scene_refs: "SourceRefs",
                           epoch_id: str | None) -> None:
        """Заполнить MD-2-поля контекста (temporal/source_refs/integrity)."""
        from .scene_context import extend_visual_context

        temporal = self._temporal_ref_from_epoch(epoch_id) if epoch_id else None
        extend_visual_context(ctx, temporal=temporal, source_refs=scene_refs)
        log.info(
            "scene_extras_applied epoch=%s scene=%s temporal=%s",
            epoch_id or "-", scene_refs.scene_id or "-",
            bool(temporal and temporal.is_temporal),
        )

    async def build_scene_context(self, chapter: int, scene_id: str,
                                  time_of_day: str = "dawn",
                                  epoch_id: str | None = None) -> VisualContext:
        """MD-2: канонический вход «сцена» — build + scene_extras.

        Аналог build(...), но с MD-2-полями: source_refs (genome-ссылки),
        temporal (epoch_id явно или по главе через canonical_events — БЕЗ
        угадывания), integrity (связи не синтезируются).
        """
        ctx = await self.build(chapter, scene_id, time_of_day)
        refs = SourceRefs(
            scene_id=scene_id,
            chapter=chapter,
            character_ids=list(ctx.scene.characters),
            location_id=ctx.location.location_id or ctx.location.name or "",
        )
        resolved_epoch = epoch_id or self._resolve_epoch_for_chapter(chapter)
        self._apply_scene_extras(ctx, refs, resolved_epoch)
        return ctx

    async def build_scene_context_for_character(self, character_id: str,
                                                time_of_day: str = "dawn") -> VisualContext:
        """MD-2: канонический вход «персонаж» — build_for_character + scene_extras."""
        ctx = await self.build_for_character(character_id, time_of_day)
        refs = SourceRefs(character_ids=[character_id])
        self._apply_scene_extras(ctx, refs, None)
        return ctx

    async def build_scene_context_for_location(self, location_id: str,
                                               time_of_day: str = "dawn") -> VisualContext:
        """MD-2: канонический вход «локация» — build_for_location + scene_extras."""
        ctx = await self.build_for_location(location_id, time_of_day)
        refs = SourceRefs(location_id=location_id)
        self._apply_scene_extras(ctx, refs, None)
        return ctx

    async def build_scene_context_for_epoch(self, epoch_id: str,
                                            time_of_day: str = "dawn") -> VisualContext:
        """MD-2: канонический вход «эпоха» (миграция M7.2-моста B).

        Эпоха как сцена: смысловые измерения — из данных эпохи WorldModel
        (name_ru/description/civilizations/technologies), временные —
        ИСКЛЮЧИТЕЛЬНО из WorldModel.get_temporal_context (read-only).
        Relations НЕ строятся; temporal_today не добавляется;
        provenance берётся готовой из TemporalNode.

        Для НЕСУЩЕСТВУЮЩЕЙ эпохи temporal остаётся пустым
        (is_temporal=False): вызывающий маршрут обязан сам ответить
        404 по факту отсутствия эпохи в WorldModel (как до миграции).
        """
        wm = self._world_model
        context = wm.get_temporal_context(epoch_id) if wm is not None else {}
        epoch = (context or {}).get("epoch") or {}
        if not epoch:
            ctx = VisualContext()
            ctx.scene = SceneContext(title=epoch_id)
            self._apply_scene_extras(ctx, SourceRefs(entity_refs=[epoch_id]), None)
            return ctx

        ctx = VisualContext()
        ctx.scene = SceneContext(title=str(epoch.get("name_ru", epoch_id)))
        # Описание эпохи в атмосферу/пейзаж (бесплатные измерения из данных)
        description = str(epoch.get("description", ""))
        if description:
            ctx.scene.description = description[:200]
        # Цивилизации эпохи → historical (существующее измерение)
        civilizations = [str(c) for c in epoch.get("civilizations_active", [])]
        ctx.historical = HistoricalContext(
            civilization=", ".join(civilizations) if civilizations else "",
            cultural_notes=description[:200],
        )
        ctx.environment = self._build_environment(time_of_day)
        ctx.lighting = self._build_lighting(ctx.location, time_of_day)
        ctx.palette = self._build_palette(ctx.location, ctx.scene)
        ctx.atmosphere = self._build_atmosphere("neutral", time_of_day)
        ctx.camera = CameraContext(shot_type="wide", lens="24mm",
                                    composition="establishing shot of the era")
        ctx.style = self._build_style(ctx.scene)
        ctx.emotion = self._build_emotion("neutral")
        ctx.characters = []
        ctx.negative_prompt = NegativePromptContext()

        temporal = self._temporal_ref_from_epoch(epoch_id)
        refs = SourceRefs(entity_refs=[epoch_id], character_ids=[
            str(c.get("character_name", "")) for c in (context or {}).get("characters", [])
            if c.get("character_name")
        ])
        extend_visual_context(ctx, temporal=temporal, source_refs=refs)
        log.info("context_built_epoch epoch_id=%s events=%d chars=%d",
                 epoch_id, temporal.event_count, temporal.character_count)
        return ctx
