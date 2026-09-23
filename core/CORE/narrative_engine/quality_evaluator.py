"""Quality Evaluator — оценка качества альтернативных развитие.

Реализует архитектуру World Explorer: Quality Evaluator (Этап 4).

Оценивает по 5 критериям:
1. Canon Alignment (Каноничность) — вес 0.30
2. Logical Consistency (Логичность) — вес 0.25
3. Thematic Depth (Тематическая глубина) — вес 0.20
4. Dramatic Potential (Драматический потенциал) — вес 0.15
5. Originality (Оригинальность) — вес 0.10
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_model import WorldModel
from narrative_engine.compatibility_checker import CompatibilityChecker, CompatibilityReport
from narrative_engine.planners.cause_effect import CauseEffectTree
from narrative_engine.contradiction_detector import ContradictionDetector, ContradictionReport
from narrative_engine.impact_assessor import ImpactReport
from narrative_engine.scenario_modeler import ScenarioBranch

log = logging.getLogger("hermes.narrative.quality_evaluator")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"


# ── Веса критериев (из архитектуры) ──────────────────────

CRITERIA_WEIGHTS = {
    "canon_alignment": 0.30,
    "logical_consistency": 0.25,
    "thematic_depth": 0.20,
    "dramatic_potential": 0.15,
    "originality": 0.10,
}


class CriterionScore(BaseModel):
    """Оценка по одному критерию."""
    criterion: str
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=1.0)
    explanation: str = ""


class QualityReport(BaseModel):
    """Полный отчёт о качестве."""
    overall_score: float = Field(ge=0.0, le=1.0, description="Взвешенная сумма [0, 1]")
    criteria_scores: list[CriterionScore] = Field(default_factory=list)
    rank: int = 0  # Позиция в ранжировании
    total_evaluated: int = 0  # Всего оценено
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class QualityEvaluator:
    """Оценивает качество альтернативных развитие.

    Критерии:
    1. Canon Alignment (0.30) — соответствие канону мира
    2. Logical Consistency (0.25) — непротиворечивость причинно-следственных цепочек
    3. Thematic Depth (0.20) — раскрытие тем мира
    4. Dramatic Potential (0.15) — драматический потенциал
    5. Originality (0.10) — оригинальность и свежесть
    """

    def __init__(self, world_model: WorldModel):
        self._wm = world_model
        self._compatibility_checker = CompatibilityChecker(world_model)
        self._contradiction_detector = ContradictionDetector(world_model)
        self._themes = self._load_themes()

    def _load_themes(self) -> list[dict]:
        path = KNOWLEDGE_DIR / "THEMES_DEEP.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get("themes", [])
            except Exception:
                return []
        return []

    def evaluate(
        self,
        branch: ScenarioBranch,
        hypothesis_text: str = "",
    ) -> QualityReport:
        """Оценить качество ветви сценария."""
        criteria_scores = []

        # 1. Canon Alignment
        canon_score = self._evaluate_canon_alignment(branch)
        criteria_scores.append(canon_score)

        # 2. Logical Consistency
        logic_score = self._evaluate_logical_consistency(branch)
        criteria_scores.append(logic_score)

        # 3. Thematic Depth
        depth_score = self._evaluate_thematic_depth(branch, hypothesis_text)
        criteria_scores.append(depth_score)

        # 4. Dramatic Potential
        drama_score = self._evaluate_dramatic_potential(branch)
        criteria_scores.append(drama_score)

        # 5. Originality
        originality_score = self._evaluate_originality(branch)
        criteria_scores.append(originality_score)

        # Рассчитываем общий балл
        overall_score = sum(cs.weighted_score for cs in criteria_scores)
        overall_score = round(min(1.0, max(0.0, overall_score)), 3)

        # Определяем сильные и слабые стороны
        strengths = self._identify_strengths(criteria_scores)
        weaknesses = self._identify_weaknesses(criteria_scores)
        recommendations = self._generate_recommendations(criteria_scores, overall_score)

        # Генерируем сводку
        summary = self._generate_summary(overall_score, strengths, weaknesses)

        return QualityReport(
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )

    def evaluate_branches(
        self,
        branches: list[ScenarioBranch],
    ) -> list[QualityReport]:
        """Оценить качество нескольких ветвей и отранжировать."""
        reports = []

        for branch in branches:
            report = self.evaluate(branch)
            reports.append(report)

        # Сортируем по общему баллу
        reports.sort(key=lambda r: r.overall_score, reverse=True)

        # Присваиваем ранг
        for i, report in enumerate(reports):
            report.rank = i + 1
            report.total_evaluated = len(reports)

        return reports

    def rank_alternatives(
        self,
        branches: list[ScenarioBranch],
    ) -> list[QualityReport]:
        """Ранжировать альтернативы по качеству."""
        return self.evaluate_branches(branches)

    # ── Оценка по критериям ───────────────────────────────

    def _evaluate_canon_alignment(self, branch: ScenarioBranch) -> CriterionScore:
        """Оценка соответствия канону."""
        score = 0.5  # Базовый балл

        # Если есть отчёт о совместимости
        if branch.contradiction_report:
            cr = branch.contradiction_report
            if cr.is_consistent:
                score += 0.3
            else:
                score -= 0.2 * cr.hard_count

        # Если есть дерево причин-следствий
        if branch.cause_effect_tree:
            tree = branch.cause_effect_tree
            # Проверяем количество constraint узлов (хорошо, если есть)
            constraints = [n for n in tree.nodes if n.type == "constraint"]
            if constraints:
                score += 0.1

        # Если есть world_delta
        if branch.world_delta:
            wd = branch.world_delta
            if wd.impact_magnitude < 0.5:
                score += 0.1  # Умеренное влияние — хорошо для канона

        score = max(0.0, min(1.0, score))

        return CriterionScore(
            criterion="canon_alignment",
            score=score,
            weight=CRITERIA_WEIGHTS["canon_alignment"],
            weighted_score=score * CRITERIA_WEIGHTS["canon_alignment"],
            explanation=self._explain_canon(score, branch),
        )

    def _evaluate_logical_consistency(self, branch: ScenarioBranch) -> CriterionScore:
        """Оценка логической непротиворечивости."""
        score = 0.5

        if branch.contradiction_report:
            cr = branch.contradiction_report
            if cr.is_consistent:
                score = 0.9
            else:
                score = max(0.1, 0.9 - 0.2 * cr.hard_count)

        if branch.cause_effect_tree:
            tree = branch.cause_effect_tree
            # Проверяем, что есть цепочка
            if len(tree.nodes) >= 3:
                score += 0.1
            # Проверяем temporal_order
            if tree.temporal_order:
                score += 0.05

        score = max(0.0, min(1.0, score))

        return CriterionScore(
            criterion="logical_consistency",
            score=score,
            weight=CRITERIA_WEIGHTS["logical_consistency"],
            weighted_score=score * CRITERIA_WEIGHTS["logical_consistency"],
            explanation=self._explain_logic(score, branch),
        )

    def _evaluate_thematic_depth(
        self,
        branch: ScenarioBranch,
        hypothesis_text: str,
    ) -> CriterionScore:
        """Оценка тематической глубины."""
        score = 0.5

        # Проверяем, упоминаются ли ключевые темы
        key_themes = ["познание", "гармония", "служение", "мудрость", "любовь",
                       "духовн", "пробужд", "трансформац"]

        text = (branch.description + " " + hypothesis_text).lower()
        theme_hits = sum(1 for t in key_themes if t in text)

        if theme_hits >= 3:
            score = 0.9
        elif theme_hits >= 2:
            score = 0.75
        elif theme_hits >= 1:
            score = 0.6

        # Если есть value_impacts в world_delta
        if branch.world_delta and branch.world_delta.value_deltas:
            score += 0.1

        score = max(0.0, min(1.0, score))

        return CriterionScore(
            criterion="thematic_depth",
            score=score,
            weight=CRITERIA_WEIGHTS["thematic_depth"],
            weighted_score=score * CRITERIA_WEIGHTS["thematic_depth"],
            explanation=self._explain_depth(score, theme_hits),
        )

    def _evaluate_dramatic_potential(self, branch: ScenarioBranch) -> CriterionScore:
        """Оценка драматического потенциала."""
        score = 0.5

        # Проверяем количество узлов (больше — драматичнее)
        if branch.cause_effect_tree:
            node_count = len(branch.cause_effect_tree.nodes)
            if node_count >= 6:
                score = 0.8
            elif node_count >= 4:
                score = 0.7
            elif node_count >= 2:
                score = 0.6

        # Проверяем наличие конфликтов
        if branch.cause_effect_tree:
            effects = [n for n in branch.cause_effect_tree.nodes if n.type == "effect"]
            if len(effects) >= 3:
                score += 0.1

        # Проверяем тип ветви
        if branch.branch_type == "radical":
            score += 0.1
        elif branch.branch_type == "unexpected":
            score += 0.15

        score = max(0.0, min(1.0, score))

        return CriterionScore(
            criterion="dramatic_potential",
            score=score,
            weight=CRITERIA_WEIGHTS["dramatic_potential"],
            weighted_score=score * CRITERIA_WEIGHTS["dramatic_potential"],
            explanation=self._explain_drama(score, branch),
        )

    def _evaluate_originality(self, branch: ScenarioBranch) -> CriterionScore:
        """Оценка оригинальности."""
        score = 0.5

        # Проверяем тип ветви
        type_scores = {
            "conservative": 0.4,
            "moderate": 0.6,
            "radical": 0.8,
            "unexpected": 0.9,
        }
        score = type_scores.get(branch.branch_type, 0.5)

        # Проверяем наличие неожиданных элементов
        if branch.world_delta:
            wd = branch.world_delta
            if len(wd.character_deltas) > 2:
                score += 0.1
            if len(wd.location_deltas) > 1:
                score += 0.05
            if len(wd.civilization_deltas) > 0:
                score += 0.05

        score = max(0.0, min(1.0, score))

        return CriterionScore(
            criterion="originality",
            score=score,
            weight=CRITERIA_WEIGHTS["originality"],
            weighted_score=score * CRITERIA_WEIGHTS["originality"],
            explanation=self._explain_originality(score, branch),
        )

    # ── Объяснения ────────────────────────────────────────

    def _explain_canon(self, score: float, branch: ScenarioBranch) -> str:
        if score >= 0.8:
            return "Высокое соответствие канону мира"
        elif score >= 0.6:
            return "Хорошее соответствие канону, есть незначительные отклонения"
        elif score >= 0.4:
            return "Среднее соответствие, возможны противоречия с каноном"
        else:
            return "Низкое соответствие канону, требуется корректировка"

    def _explain_logic(self, score: float, branch: ScenarioBranch) -> str:
        if score >= 0.8:
            return "Цепочка причин-следствий непротиворечива"
        elif score >= 0.6:
            return "В целом логично, есть незначительные нестыковки"
        elif score >= 0.4:
            return "Возможны логические противоречия"
        else:
            return "Обнаружены серьёзные логические противоречия"

    def _explain_depth(self, score: float, theme_hits: int) -> str:
        if theme_hits >= 3:
            return "Глубокое раскрытие ключевых тем мира"
        elif theme_hits >= 2:
            return "Хорошее раскрытие тем"
        elif theme_hits >= 1:
            return "Частичное раскрытие тем"
        else:
            return "Тематическая глубина недостаточна"

    def _explain_drama(self, score: float, branch: ScenarioBranch) -> str:
        if score >= 0.8:
            return "Высокий драматический потенциал"
        elif score >= 0.6:
            return "Хороший драматический потенциал"
        elif score >= 0.4:
            return "Умеренный драматический потенциал"
        else:
            return "Низкий драматический потенциал"

    def _explain_originality(self, score: float, branch: ScenarioBranch) -> str:
        if score >= 0.8:
            return "Высокая оригинальность, неожиданные решения"
        elif score >= 0.6:
            return "Хорошая оригинальность"
        elif score >= 0.4:
            return "Умеренная оригинальность"
        else:
            return "Низкая оригинальность, типичные решения"

    # ── Сильные и слабые стороны ──────────────────────────

    def _identify_strengths(self, criteria_scores: list[CriterionScore]) -> list[str]:
        strengths = []
        for cs in criteria_scores:
            if cs.score >= 0.8:
                strengths.append(f"{cs.criterion}: {cs.explanation}")
        return strengths

    def _identify_weaknesses(self, criteria_scores: list[CriterionScore]) -> list[str]:
        weaknesses = []
        for cs in criteria_scores:
            if cs.score < 0.5:
                weaknesses.append(f"{cs.criterion}: {cs.explanation}")
        return weaknesses

    def _generate_recommendations(
        self,
        criteria_scores: list[CriterionScore],
        overall_score: float,
    ) -> list[str]:
        recommendations = []

        for cs in criteria_scores:
            if cs.score < 0.5:
                if cs.criterion == "canon_alignment":
                    recommendations.append("Усилить соответствие канону мира")
                elif cs.criterion == "logical_consistency":
                    recommendations.append("Исправить логические противоречия")
                elif cs.criterion == "thematic_depth":
                    recommendations.append("Добавить тематическую глубину")
                elif cs.criterion == "dramatic_potential":
                    recommendations.append("Усилить драматический потенциал")
                elif cs.criterion == "originality":
                    recommendations.append("Предложить более оригинальные решения")

        if overall_score < 0.3:
            recommendations.append("Общий балл очень низкий — рекомендуется переработка")
        elif overall_score < 0.6:
            recommendations.append("Общий балл средний — есть потенциал для улучшения")

        return recommendations

    # ── Сводка ────────────────────────────────────────────

    def _generate_summary(
        self,
        overall_score: float,
        strengths: list[str],
        weaknesses: list[str],
    ) -> str:
        parts = [f"Общий балл: {overall_score:.3f}"]

        if strengths:
            parts.append(f"Сильные стороны: {len(strengths)}")
        if weaknesses:
            parts.append(f"Слабые стороны: {len(weaknesses)}")

        return "; ".join(parts)
