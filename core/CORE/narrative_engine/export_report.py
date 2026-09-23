"""Export Report — генерация отчётов о результатах исследования.

Реализует архитектура World Explorer: Этап 15 — Экспорт результатов.

Генерирует:
- Markdown отчёт о результатах исследования
- Сводка по ветвям, критериям, влиянию
- Рекомендации
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.world_explorer import ExplorationResult, RankedBranch

log = logging.getLogger("hermes.narrative.export_report")


class ExportReport(BaseModel):
    """Отчёт об исследовании для экспорта."""
    title: str = ""
    created_at: str = ""
    prompt: str = ""
    epoch: Optional[str] = None
    branch_count: int = 0
    best_score: float = 0.0
    duration_ms: float = 0.0
    branches_summary: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    markdown: str = ""


def generate_markdown_report(result: ExplorationResult) -> ExportReport:
    """Сгенерировать Markdown отчёт о результатах исследования."""
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Заголовок
    title = f"Исследование мира: {result.request.prompt[:50]}"
    if result.request.epoch:
        title += f" ({result.request.epoch})"

    # Сводка по ветвям
    branches_summary = []
    for rb in result.ranked_branches:
        branches_summary.append({
            "rank": rb.rank,
            "type": rb.branch.branch_type,
            "title": rb.branch.title_ru,
            "quality_score": rb.quality_report.overall_score,
            "strengths": rb.quality_report.strengths,
            "weaknesses": rb.quality_report.weaknesses,
            "impact_score": rb.impact_report.overall_impact_score if rb.impact_report else 0.0,
            "contradictions": rb.contradiction_report.hard_count if rb.contradiction_report else 0,
            "delta_changes": rb.world_delta.total_changes if rb.world_delta else 0,
        })

    # Лучший балл
    best_score = result.ranked_branches[0].quality_report.overall_score if result.ranked_branches else 0.0

    # Рекомендации
    recommendations = _generate_recommendations(result)

    # Генерируем Markdown
    markdown = _build_markdown(
        title=title,
        created_at=now,
        result=result,
        branches_summary=branches_summary,
        recommendations=recommendations,
    )

    return ExportReport(
        title=title,
        created_at=now,
        prompt=result.request.prompt,
        epoch=result.request.epoch,
        branch_count=len(result.ranked_branches),
        best_score=best_score,
        duration_ms=result.duration_ms,
        branches_summary=branches_summary,
        recommendations=recommendations,
        markdown=markdown,
    )


def _generate_recommendations(result: ExplorationResult) -> list[str]:
    """Сгенерировать рекомендации на основе результатов."""
    recommendations = []

    if not result.ranked_branches:
        recommendations.append("Нет ветвей для анализа. Попробуйте увеличить branch_count.")
        return recommendations

    best = result.ranked_branches[0]

    # Рекомендации по качеству
    if best.quality_report.overall_score >= 0.8:
        recommendations.append("Высокое качество исследования. Рекомендуется к реализации.")
    elif best.quality_report.overall_score >= 0.6:
        recommendations.append("Среднее качество. Рекомендуется дополнительная проверка.")
    else:
        recommendations.append("Низкое качество. Рекомендуется переработка идеи.")

    # Рекомендации по противоречиям
    total_contradictions = sum(
        rb.contradiction_report.hard_count if rb.contradiction_report else 0
        for rb in result.ranked_branches
    )
    if total_contradictions > 0:
        recommendations.append(f"Обнаружено {total_contradictions} противоречий. Требуется проверка.")

    # Рекомендации по влиянию
    high_impact = [rb for rb in result.ranked_branches
                   if rb.impact_report and rb.impact_report.overall_impact_score > 0.5]
    if high_impact:
        recommendations.append(f"{len(high_impact)} ветвей с высоким влиянием на мир.")

    # Рекомендации по генерации текста
    recommendations.append("Для генерации текста используйте POST /generate-from-branch.")

    return recommendations


def _build_markdown(
    title: str,
    created_at: str,
    result: ExplorationResult,
    branches_summary: list[dict],
    recommendations: list[str],
) -> str:
    """Построить Markdown отчёт."""
    parts = [
        f"# {title}",
        "",
        f"**Дата**: {created_at}",
        f"**Запрос**: {result.request.prompt}",
    ]

    if result.request.epoch:
        parts.append(f"**Эпоха**: {result.request.epoch}")

    parts.extend([
        f"**Ветвей**: {len(result.ranked_branches)}",
        f"**Время**: {result.duration_ms:.0f}ms",
        "",
        "---",
        "",
        "## Результаты исследования",
        "",
    ])

    # Лучшая ветвь
    if result.ranked_branches:
        best = result.ranked_branches[0]
        parts.extend([
            "### Лучшая ветвь",
            "",
            f"- **Тип**: {best.branch.branch_type}",
            f"- **Название**: {best.branch.title_ru}",
            f"- **Качество**: {best.quality_report.overall_score:.3f}",
            f"- **Влияние**: {best.impact_report.overall_impact_score:.3f}" if best.impact_report else "",
            "",
        ])

    # Все ветви
    parts.extend([
        "### Все ветви",
        "",
        "| # | Тип | Название | Качество | Влияние | Противоречия |",
        "|---|-----|----------|----------|---------|--------------|",
    ])

    for b in branches_summary:
        parts.append(
            f"| {b['rank']} | {b['type']} | {b['title'][:30]} | "
            f"{b['quality_score']:.3f} | {b['impact_score']:.3f} | {b['contradictions']} |"
        )

    parts.append("")

    # Сильные и слабые стороны лучшей ветви
    if result.ranked_branches:
        best = result.ranked_branches[0]
        if best.quality_report.strengths:
            parts.extend([
                "### Сильные стороны",
                "",
            ])
            for s in best.quality_report.strengths:
                parts.append(f"- {s}")
            parts.append("")

        if best.quality_report.weaknesses:
            parts.extend([
                "### Слабые стороны",
                "",
            ])
            for w in best.quality_report.weaknesses:
                parts.append(f"- {w}")
            parts.append("")

    # Рекомендации
    parts.extend([
        "## Рекомендации",
        "",
    ])
    for r in recommendations:
        parts.append(f"- {r}")

    parts.extend([
        "",
        "---",
        "",
        f"*Отчёт сгенерирован World Explorer {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')}*",
    ])

    return "\n".join(parts)
