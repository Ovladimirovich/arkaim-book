"""Asset Generation Pipeline — оркестрация генерации изображений и видео."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .schemas import VisualAsset, AssetType, AssetStatus, GenerationParams, CameraSpec, CharacterInAsset
from .prompt_builder import build_asset_prompt, build_shot_prompt, build_negative_prompt, STYLE_PRESETS
from .storage import AssetStorage, generate_asset_id

if TYPE_CHECKING:
    from visualization.scene_engine import SceneEngine

log = logging.getLogger("visual_assets.pipeline")


class AssetGenerationPipeline:
    """Пайплайн: genome scene → prompt → image/video → save."""

    def __init__(
        self,
        scene_engine: "SceneEngine",
        prompt_builder: Any,
        image_provider: Any,
        video_provider: Any | None = None,
        asset_store: AssetStorage | None = None,
    ):
        self._scene_engine = scene_engine
        self._prompt_builder = prompt_builder
        self._image_provider = image_provider
        self._video_provider = video_provider
        self._store = asset_store or AssetStorage()

    async def generate_image(
        self,
        chapter: int,
        scene_id: str,
        overrides: dict | None = None,
        custom_prompt: str | None = None,
        scene_context=None,
        plan=None,  # MD-3.2 Route C: MediaPlan (canonical; из MediaPlanBuilder)
    ) -> VisualAsset:
        """Полный пайплайн: сцена → промпт → изображение → сохранение.

        MD-2: параметр scene_context (канонический VisualContext+scene_extras)
        — единый смысловой вход. При его передаче сцена/персонажи/локация
        берутся ИЗ контекста (source_refs — те же genome-идентификаторы);
        legacy-поведение без scene_context сохранено (DEPRECATED как
        способ НОВОГО входа: все маршруты передают scene_context).

        MD-3.2 (Route C): при plan смысловой план построен
        MediaPlanBuilder'ом из этого же ctx; исторический промпт —
        legacy-проекция (build_asset_prompt, PA-F1-схема A/B).
        Без plan — прежнее поведение (byte-identical).
        MD-5: ExecutionDispatch удалён, dispatch-параметр убран.
        """
        # 1. Существование сцены — прежний 404-контракт (SceneEngine —
        #    утилита чтения genome, REUSABLE по MD-2-аудиту). При
        #    scene_context данные берутся из контекста, но факт
        #    существования проверяется тем же механизмом, что и в HEAD.
        found = self._scene_engine.get_scene(chapter, scene_id) if self._scene_engine else None
        if not found:
            raise ValueError(f"Scene not found: chapter={chapter}, scene_id={scene_id}")

        if scene_context is not None:
            # MD-2: проекция SceneContext → прежняя data-модель ассета
            # (идентификаторы из source_refs; смысловые поля из измерений).
            scene = {
                "chapter": scene_context.scene.chapter or chapter,
                "scene_id": (
                    scene_context.scene_extras.source_refs.scene_id
                    if scene_context.scene_extras is not None
                    else scene_id
                ) or scene_id,
                "title": scene_context.scene.title or found.get("title", ""),
                "characters": [
                    c.character_id for c in scene_context.characters
                ] or list(scene_context.scene.characters) or found.get("characters", []),
                "location": (
                    scene_context.scene_extras.source_refs.location_id
                    if scene_context.scene_extras is not None
                    else ""
                ) or found.get("location", ""),
                "emotion": scene_context.emotion.name
                if scene_context.emotion.name != "neutral"
                else scene_context.scene.emotion or found.get("emotion", "neutral"),
                "meaning_tags": list(scene_context.scene.meaning_tags) or found.get("meaning_tags", []),
            }
        else:
            scene = found

        # 2. Собрать персонажей и локацию
        char_visuals = {}
        characters_in_asset = []
        for char_id in scene.get("characters", []):
            cv = self._scene_engine.get_character_visual(char_id)
            if cv:
                char_visuals[char_id] = cv
                characters_in_asset.append(CharacterInAsset(
                    character_id=char_id,
                    name=char_id,
                    appearance=cv.get("visual_description", ""),
                ))

        location = self._scene_engine.get_location_visual(scene.get("location", ""))
        if not location:
            location = {"type": "unknown", "atmosphere": "", "architecture": "", "lighting": ""}

        # 3. Создать VisualAsset
        generation_overrides = dict((overrides or {}).get("generation", {}))
        provider_name = (overrides or {}).get("provider") or generation_overrides.get("provider", "auto")
        generation_overrides["provider"] = provider_name

        asset = VisualAsset(
            asset_id=generate_asset_id(),
            asset_type=AssetType.IMAGE,
            chapter=chapter,
            scene_id=scene_id,
            title=scene.get("title", ""),
            mood=scene.get("emotion", "neutral"),
            style=(overrides or {}).get("style", "cinematic_fantasy"),
            palette=scene.get("color_palette", []) or [],
            characters=characters_in_asset,
            objects=scene.get("objects", []) if isinstance(scene.get("objects"), list) else [],
            symbols=scene.get("meaning_tags", []) or [],
            generation=GenerationParams(**generation_overrides),
            reader_id=(overrides or {}).get("reader_id"),
        )
        asset.status = AssetStatus.GENERATING
        await self._store.save(asset)

        try:
            # 4. Собрать промпт
            if plan is not None:
                # MD-3.2: план canonical; исторический текст — legacy-
                # проекция ПОСЛЕ плана (PA-F1-схема A/B).
                if custom_prompt:
                    style_prefix = STYLE_PRESETS.get(asset.style, "")
                    prompt = f"{style_prefix}, {custom_prompt}" if style_prefix else custom_prompt
                else:
                    prompt = build_asset_prompt(asset)
                log.info("md32_route_c_plan_path plan_id=%s media_kind=%s",
                         getattr(plan, "plan_id", "?"), getattr(plan, "media_kind", "?"))
            elif custom_prompt:
                # Используем кастомный промпт (из сценария/шота) + стиль
                style_prefix = STYLE_PRESETS.get(asset.style, "")
                prompt = f"{style_prefix}, {custom_prompt}" if style_prefix else custom_prompt
            else:
                prompt = build_asset_prompt(asset)
            negative = build_negative_prompt(asset)
            asset.prompt_used = prompt

            # 5. Сгенерировать изображение
            size = asset.generation.size
            log.debug("PIPELINE_DEBUG provider=%s size=%s prompt=%.80s", asset.generation.provider, size, prompt)
            if hasattr(self._image_provider, "generate_with_metadata"):
                provider_result = await self._image_provider.generate_with_metadata(
                    prompt,
                    size=size,
                    preferred_provider=asset.generation.provider,
                )
                image_bytes = provider_result.bytes
                asset.generation.provider = provider_result.provider_name
                log.debug("PIPELINE_DEBUG result_provider=%s bytes=%d", provider_result.provider_name, len(image_bytes))
            else:
                image_bytes = await self._image_provider.generate(prompt, size=size)

            # 6. Сохранить файл
            rel_path = self._store.save_file(asset.asset_id, AssetType.IMAGE, image_bytes)
            asset.file_path = rel_path
            asset.status = AssetStatus.COMPLETED

        except Exception as e:
            log.error("image_gen_error asset=%s error=%s", asset.asset_id, e)
            asset.status = AssetStatus.FAILED
            asset.error = str(e)

        await self._store.save(asset)
        return asset

    async def generate_video(
        self,
        chapter: int,
        scene_id: str,
        overrides: dict | None = None,
        scene_context=None,
    ) -> VisualAsset:
        """Полный пайплайн: сцена → шоты → видео → сохранение.

        MD-2: scene_context — канонический вход (см. generate_image);
        без него — прежнее поведение. Существование сцены (404-контракт)
        проверяется SceneEngine, как в HEAD.
        """
        found = self._scene_engine.get_scene(chapter, scene_id) if self._scene_engine else None
        if not found:
            raise ValueError(f"Scene not found: chapter={chapter}, scene_id={scene_id}")

        if scene_context is not None:
            scene = {
                "chapter": scene_context.scene.chapter or chapter,
                "scene_id": (
                    scene_context.scene_extras.source_refs.scene_id
                    if scene_context.scene_extras is not None
                    else scene_id
                ) or scene_id,
                "title": scene_context.scene.title or found.get("title", ""),
                "characters": [
                    c.character_id for c in scene_context.characters
                ] or list(scene_context.scene.characters) or found.get("characters", []),
                "location": (
                    scene_context.scene_extras.source_refs.location_id
                    if scene_context.scene_extras is not None
                    else ""
                ) or found.get("location", ""),
                "emotion": scene_context.emotion.name
                if scene_context.emotion.name != "neutral"
                else scene_context.scene.emotion or found.get("emotion", "neutral"),
                "meaning_tags": list(scene_context.scene.meaning_tags) or found.get("meaning_tags", []),
            }
        else:
            scene = found

        char_visuals = {}
        characters_in_asset = []
        for char_id in scene.get("characters", []):
            cv = self._scene_engine.get_character_visual(char_id)
            if cv:
                char_visuals[char_id] = cv
                characters_in_asset.append(CharacterInAsset(
                    character_id=char_id,
                    name=char_id,
                    appearance=cv.get("visual_description", ""),
                ))

        # Создать ассет
        ov = overrides or {}
        asset = VisualAsset(
            asset_id=generate_asset_id(),
            asset_type=AssetType.VIDEO,
            chapter=chapter,
            scene_id=scene_id,
            title=scene.get("title", ""),
            mood=scene.get("emotion", "neutral"),
            style=ov.get("style", "cinematic_fantasy"),
            palette=scene.get("color_palette", []) or [],
            characters=characters_in_asset,
            duration_sec=ov.get("duration_sec", 8),
            fps=ov.get("fps", 24),
            generation=GenerationParams(**ov.get("generation", {})),
            reader_id=ov.get("reader_id"),
        )
        asset.status = AssetStatus.GENERATING
        await self._store.save(asset)

        try:
            if self._video_provider and await self._video_provider.health():
                # Попробовать специализированный видео-провайдер
                prompt = build_asset_prompt(asset)
                asset.prompt_used = prompt
                video_bytes = await self._video_provider.generate(
                    prompt, duration=asset.duration_sec,
                    size=asset.generation.size, fps=asset.fps,
                )
            else:
                # Fallback: сгенерировать кадры через ImageProvider → ffmpeg
                video_bytes = await self._generate_video_from_frames(asset, scene, char_visuals)

            rel_path = self._store.save_file(asset.asset_id, AssetType.VIDEO, video_bytes)
            asset.file_path = rel_path
            asset.status = AssetStatus.COMPLETED

        except Exception as e:
            log.error("video_gen_error asset=%s error=%s", asset.asset_id, e)
            asset.status = AssetStatus.FAILED
            asset.error = str(e)

        await self._store.save(asset)
        return asset

    async def _generate_video_from_frames(
        self, asset: VisualAsset, scene: dict, char_visuals: dict
    ) -> bytes:
        """Генерация видео из последовательности кадров через ImageProvider + ffmpeg."""
        import asyncio
        import tempfile
        import os

        fps = asset.fps
        duration = asset.duration_sec
        total_frames = int(fps * duration)

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(total_frames):
                shot = self._make_interpolated_shot(i, total_frames, asset, scene)
                prompt = build_shot_prompt(shot, asset)
                frame_bytes = await self._image_provider.generate(prompt, size=asset.generation.size)
                frame_path = os.path.join(tmpdir, f"frame_{i:04d}.png")
                with open(frame_path, "wb") as f:
                    f.write(frame_bytes)

            output_path = os.path.join(tmpdir, f"{asset.asset_id}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", os.path.join(tmpdir, "frame_%04d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                output_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {stderr.decode()[:500]}")

            with open(output_path, "rb") as f:
                return f.read()

    def _make_interpolated_shot(self, frame_idx: int, total_frames: int, asset: VisualAsset, scene: dict):
        """Создать интерполированный кадр для видео."""
        from .schemas import ShotSpec, CameraSpec

        progress = frame_idx / max(total_frames - 1, 1)

        if progress < 0.3:
            movement = "slow_dolly_in"
        elif progress < 0.7:
            movement = "slow_pan"
        else:
            movement = "slow_zoom_out"

        return ShotSpec(
            id=f"frame_{frame_idx:04d}",
            prompt=scene.get("title", ""),
            duration_sec=asset.duration_sec / total_frames,
            camera=CameraSpec(shot_type="medium_shot", angle="eye_level", movement=movement),
            lighting=scene.get("emotion", ""),
            palette=asset.palette,
        )

    async def generate_batch(
        self,
        chapter: int | None = None,
        asset_type: AssetType = AssetType.IMAGE,
        limit: int = 20,
    ) -> list[VisualAsset]:
        """Пакетная генерация для сцен в главе."""
        results = []
        scenes = self._scene_engine.get_scenes_by_chapter(chapter) if chapter else []
        if not chapter:
            for ch in range(1, 20):
                ch_scenes = self._scene_engine.get_scenes_by_chapter(ch)
                if not ch_scenes:
                    break
                scenes.extend(ch_scenes)

        for scene in scenes[:limit]:
            try:
                if asset_type == AssetType.IMAGE:
                    asset = await self.generate_image(scene["chapter"], scene["scene_id"])
                else:
                    asset = await self.generate_video(scene["chapter"], scene["scene_id"])
                results.append(asset)
            except Exception as e:
                log.error("batch_gen_error scene=%s error=%s", scene.get("scene_id"), e)
        return results

    async def generate_image_from_context(
        self,
        visual_context,  # VisualContext from visual module
        generator: str = "comfyui",
        size: str = "1024x576",
        reader_id: str | None = None,
        plan=None,  # MD-3.2: MediaPlan (canonical; из MediaPlanBuilder)
    ) -> VisualAsset:
        """Генерировать изображение из VisualContext (новый пайплайн).

        Использует PromptComposer для сборки промпта из VisualContext.

        MD-3.2 (Route D): канонический путь — SceneContext → MediaPlan
        (MediaPlanBuilder, отдельный модуль) → ExecutionDispatch → этот
        метод. При передаче plan смысловые данные промпта
        берутся ИЗ плана (единый canonical path), legacy-аргументы
        generator/size остаются совместимым fallback (без плана —
        прежнее поведение, byte-identical).
        MD-5: ExecutionDispatch удалён, dispatch-параметр убран.
        """
        # MD-2/F-11 fix: было `from ..visual...` — relative-beyond-top-level
        # ломал этот маршрут при любых запусках (pre-existing дефект пути D:
        # absolute imports — тот же паттерн, что весь visual-стек).
        from visual.prompt_composer import PromptComposer
        from visual.visual_validator import VisualValidator

        # 1. Валидация
        validator = VisualValidator()
        validation = validator.validate(visual_context)
        if not validation.ok:
            log.error("validation_failed errors=%s", validation.errors)
            raise ValueError(f"VisualContext validation failed: {validation.errors}")

        # 2. Промпт: из MediaPlan (MD-3.2 canonical) или composer (legacy)
        if plan is not None:
            # MD-3.2: план построен MediaPlanBuilder'ом из этого же ctx.
            prompt = plan.prompt
            negative = ", ".join(plan.negative_constraints)
            log.info("md32_plan_path plan_id=%s lineage=%s",
                     getattr(plan, "plan_id", "?"),
                     getattr(plan, "lineage", None) and plan.lineage.derivation)
        else:
            composer = PromptComposer(generator=generator)
            prompt, negative = composer.compose_pair(visual_context)

        # 3. Создать ассет
        asset = VisualAsset(
            asset_id=generate_asset_id(),
            asset_type=AssetType.IMAGE,
            chapter=visual_context.scene.chapter,
            scene_id=visual_context.scene.scene_id,
            title=visual_context.scene.title,
            mood=visual_context.emotion.name,
            style=visual_context.style.name,
            palette=visual_context.palette.primary,
            camera=CameraSpec(
                shot_type=visual_context.camera.shot_type,
                angle=visual_context.camera.angle,
                movement=visual_context.camera.movement,
            ),
            characters=[
                CharacterInAsset(
                    character_id=c.character_id,
                    name=c.name,
                    appearance=c.appearance_summary,
                )
                for c in visual_context.characters
            ],
            generation=GenerationParams(
                provider=generator,
                size=size,
                negative_prompt=[negative] if isinstance(negative, str) else negative,
            ),
            reader_id=reader_id,
        )
        asset.status = AssetStatus.GENERATING
        asset.prompt_used = prompt
        await self._store.save(asset)

        try:
            # 4. Генерация — единый вызов (plan → prompt из плана,
            #    без dispatch; legacy-путь сохранён для queue/batch).
            if hasattr(self._image_provider, "generate_with_metadata"):
                result = await self._image_provider.generate_with_metadata(
                    prompt, size=size, preferred_provider=generator,
                )
                image_bytes = result.bytes
                asset.generation.provider = result.provider_name
            else:
                image_bytes = await self._image_provider.generate(prompt, size=size)

            # 5. Сохранение
            rel_path = self._store.save_file(asset.asset_id, AssetType.IMAGE, image_bytes)
            asset.file_path = rel_path
            asset.status = AssetStatus.COMPLETED

        except Exception as e:
            log.error("context_gen_error asset=%s error=%s", asset.asset_id, e)
            asset.status = AssetStatus.FAILED
            asset.error = str(e)

        await self._store.save(asset)
        log.info("image_from_context_done asset=%s prompt=%.100s", asset.asset_id, prompt)
        return asset
