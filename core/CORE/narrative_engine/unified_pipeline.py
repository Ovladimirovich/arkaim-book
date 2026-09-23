"""Unified Pipeline — связка World Explorer + Story Engine.

Реализует архитектура World Explorer: Этап 14 — Интеграция со Story Engine.

Единый pipeline:
  Explore → Select Branch → Generate Story → Validate → Result

Связывает:
- World Explorer: исследование мира, генерация гипотез, моделирование сценариев
- Story Engine: генерация текста через LLM, валидация
"""

import logging
import time
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.world_explorer import WorldExplorer, ExplorationRequest, ExplorationResult
from narrative_engine.story_from_branch import build_story_from_branch, BranchToStoryRequest, StoryFromBranchResult
from narrative_engine.compatibility_checker import CompatibilityChecker
from narrative_engine.quality_evaluator import QualityEvaluator

log = logging.getLogger("hermes.narrative.unified_pipeline")


class UnifiedRequest(BaseModel):
    """Единый запрос на исследование + генерацию."""
    prompt: str
    epoch: Optional[str] = None
    location: Optional[str] = None
    branch_count: int = Field(default=3, ge=1, le=10)
    style: str = "literary"
    max_length: int = 2000
    generate_story: bool = True  # Генерировать ли текст после исследования
    select_best: bool = True  # Выбрать лучшую ветвь автоматически


class UnifiedResult(BaseModel):
    """Единый результат: исследование + сгенерированный текст."""
    exploration: Optional[ExplorationResult] = None
    story: Optional[StoryFromBranchResult] = None
    selected_branch_rank: int = 0
    total_duration_ms: float = 0.0
    pipeline_steps: list[str] = Field(default_factory=list)
    summary: str = ""


class UnifiedPipeline:
    """Единый pipeline: Explore → Select → Generate → Validate → Result.

    Использование:
        pipeline = UnifiedPipeline(world_model)
        result = await pipeline.run(request)
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._explorer = WorldExplorer(world_model)
        self._compatibility_checker = CompatibilityChecker(world_model)
        self._quality_evaluator = QualityEvaluator(world_model)

    def run(self, request: UnifiedRequest) -> UnifiedResult:
        """Полный pipeline: исследование + генерация текста."""
        start_time = time.time()
        pipeline_steps = []

        # 1. Исследование мира
        pipeline_steps.append("exploration")
        exploration_request = ExplorationRequest(
            prompt=request.prompt,
            epoch=request.epoch,
            location=request.location,
            branch_count=request.branch_count,
        )
        exploration = self._explorer.explore(exploration_request)

        if not exploration.ranked_branches:
            return UnifiedResult(
                exploration=exploration,
                total_duration_ms=(time.time() - start_time) * 1000,
                pipeline_steps=pipeline_steps,
                summary="Нет ветвей для генерации",
            )

        # 2. Выбор лучшей ветви
        pipeline_steps.append("branch_selection")
        if request.select_best:
            selected_branch = exploration.ranked_branches[0]
            selected_rank = selected_branch.rank
        else:
            # Берём первую ветвь
            selected_branch = exploration.ranked_branches[0]
            selected_rank = selected_branch.rank

        # 3. Генерация текста (если запрошено)
        story = None
        if request.generate_story:
            pipeline_steps.append("story_generation")
            branch_request = BranchToStoryRequest(
                exploration_prompt=request.prompt,
                branch_title=selected_branch.branch.title_ru,
                branch_type=selected_branch.branch.branch_type,
                epoch=request.epoch,
                location=request.location,
                style=request.style,
                max_length=request.max_length,
                quality_score=selected_branch.quality_report.overall_score,
                strengths=selected_branch.quality_report.strengths,
                weaknesses=selected_branch.quality_report.weaknesses,
            )
            story = build_story_from_branch(branch_request, self._wm)

        # 4. Формируем результат
        total_duration = (time.time() - start_time) * 1000
        best_score = exploration.ranked_branches[0].quality_report.overall_score

        summary = (
            f"Исследование: {len(exploration.ranked_branches)} ветвей, "
            f"лучшая: {best_score:.3f}, "
            f"текст: {'сгенерирован' if story else 'не запрошен'}, "
            f"время: {total_duration:.0f}ms"
        )

        return UnifiedResult(
            exploration=exploration,
            story=story,
            selected_branch_rank=selected_rank,
            total_duration_ms=total_duration,
            pipeline_steps=pipeline_steps,
            summary=summary,
        )

    def explore_only(self, request: UnifiedRequest) -> ExplorationResult:
        """Только исследование без генерации текста."""
        exploration_request = ExplorationRequest(
            prompt=request.prompt,
            epoch=request.epoch,
            location=request.location,
            branch_count=request.branch_count,
        )
        return self._explorer.explore(exploration_request)

    def generate_from_branch(
        self,
        exploration: ExplorationResult,
        branch_rank: int = 1,
        style: str = "literary",
        max_length: int = 2000,
    ) -> StoryFromBranchResult:
        """Генерация текста из конкретной ветви."""
        # Находим ветвь по рангу
        branch = None
        for rb in exploration.ranked_branches:
            if rb.rank == branch_rank:
                branch = rb
                break

        if not branch:
            branch = exploration.ranked_branches[0] if exploration.ranked_branches else None

        if not branch:
            raise ValueError("Нет ветвей для генерации")

        branch_request = BranchToStoryRequest(
            exploration_prompt=exploration.request.prompt,
            branch_title=branch.branch.title_ru,
            branch_type=branch.branch.branch_type,
            epoch=exploration.request.epoch,
            location=exploration.request.location,
            style=style,
            max_length=max_length,
            quality_score=branch.quality_report.overall_score,
            strengths=branch.quality_report.strengths,
            weaknesses=branch.quality_report.weaknesses,
        )

        return build_story_from_branch(branch_request, self._wm)
