# -*- coding: utf-8 -*-
"""M25 — замер покрытия вопросных тем контекстом Knowledge Core.

Измеряет, какая доля тем, названных в мультитематическом вопросе,
действительно попадает в related_entities и затем в контекст
Knowledge Core (gather_knowledge_core_context), используемый маршрутом
/book/ask.

Модуль читаемый: не мутирует WorldModel/Temporal, не создаёт записи.
Вывод безопасен для консолей с не-UTF-8 кодировкой (Cyrillic не ломается),
т.к. все отчёты серийлизуются с ensure_ascii=True.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]  # .../arkaim
GENOME_PATH = REPO / "core" / "GENOME" / "GENOME_v1.0.0.json"

# Импортируем реальные production-функции, чтобы замер всегда был
# синхронен с тем, что делает /book/ask (никакой дублирующей логики).
from core.services.related_entities import (  # noqa: E402
    MIN_SCORE,
    _iter_entities,
    _score_entity,
    _stems,
    resolve_related_entities,
)
from core.services.knowledge_core_context import (  # noqa: E402
    gather_knowledge_core_context,
)


def norm(v: str) -> str:
    """Нормализовать строку для сравнения имён тем (регистр, Ё→Е, пробелы)."""
    return " ".join((v or "").lower().replace("ё", "е").split())


def _entity_name(item: dict[str, Any], category: str) -> tuple[str, str, str]:
    """Вернуть (entity_id, name, description) из элемента world-модели."""
    entity_id = str(item.get("id") or "")
    name = str(item.get("name") or "")
    description = str(item.get("description") or "")
    return entity_id, name, description


@dataclass
class TopicResult:
    topic: str
    expected_normalized: str
    in_genome_themes: bool
    carrier_count: int
    carrier_ids: list[str] = field(default_factory=list)
    in_related: bool = False
    in_context: bool = False
    uncapped_rank: int | None = None
    uncapped_score: int | None = None


@dataclass
class QuestionReport:
    id: str
    question: str
    expected: list[str]
    related_ids: list[str]
    related_names: list[str]
    context_ids: list[str]
    context_names: list[str]
    expected_count: int
    covered_count: int
    percent: float
    topics: list[TopicResult] = field(default_factory=list)
    scored_top12: list[dict[str, Any]] = field(default_factory=list)


def _uncapped_scored(question: str, engine: Any) -> list[dict[str, Any]]:
    """Все сущности с score >= MIN_SCORE, отсортированные как в production,
    без применения MAX_RESULTS (для замера 'где бы тема оказалась без среза')."""
    query_stems = _stems(question)
    answer_stems: set[str] = set()
    answer_text = ""
    scored: list[dict[str, Any]] = []
    for category, item in _iter_entities(engine):
        entity_id, name, description = _entity_name(item, category)
        cand = _score_entity(
            entity_id=entity_id,
            entity_type=category,
            name=name,
            description=description,
            query_stems=query_stems,
            answer_stems=answer_stems,
            answer_text=answer_text,
        )
        if cand.score >= MIN_SCORE:
            scored.append(
                {
                    "entity_id": cand.entity_id,
                    "name": cand.name,
                    "score": cand.score,
                    "specificity": cand.specificity,
                    "in_question": cand.in_question,
                    "name_coverage": cand.name_coverage,
                    "description": cand.description,
                }
            )
    scored.sort(
        key=lambda c: (
            not c["in_question"],
            -c["name_coverage"],
            -c["score"],
            -c["specificity"],
            c["name"],
            c["entity_id"],
        )
    )
    return scored


def measure_question(
    question: str,
    expected_topics: list[str],
    qid: str | None = None,
    engine: Any | None = None,
) -> QuestionReport:
    """Замер покрытия для одного вопроса.

    expected_topics — имена тем, которые вопрос называет (в любой падеже;
    сопоставление по нормализованному имени).
    """
    from narrative_engine.world_engine import get_world_engine

    if engine is None:
        engine = get_world_engine()

    theme_names = _load_theme_names()
    qid = qid or f"q_{abs(hash(question)) % 100000}"

    related = resolve_related_entities({"question": question, "answer": ""})
    contexts = gather_knowledge_core_context(related)

    related_names = [norm(r.get("name", "")) for r in related]
    related_ids = [r.get("entity_id") for r in related]
    context_names = [norm(c.get("entity_name", "")) for c in contexts]
    context_ids = [c.get("entity_id") for c in contexts]

    entities: list[dict[str, str]] = [
        {"category": c, "id": i.get("id"), "name": i.get("name"), "description": i.get("description")} for c, i in _iter_entities(engine)
    ]
    by_name: dict[str, list[dict[str, str]]] = {}
    for e in entities:
        by_name.setdefault(norm(e["name"]), []).append(e)

    scored = _uncapped_scored(question, engine)

    topics: list[TopicResult] = []
    for exp in expected_topics:
        exp_norm = norm(exp)
        carriers = by_name.get(exp_norm, [])
        best_rank: int | None = None
        best_score: int | None = None
        for rank, c in enumerate(scored):
            if norm(c["name"]) == exp_norm:
                best_rank = rank
                best_score = c["score"]
                break
        topics.append(
            TopicResult(
                topic=exp,
                expected_normalized=exp_norm,
                in_genome_themes=exp_norm in theme_names,
                carrier_count=len(carriers),
                carrier_ids=[c["id"] for c in carriers][:6],
                in_related=exp_norm in related_names,
                in_context=exp_norm in context_names,
                uncapped_rank=best_rank,
                uncapped_score=best_score,
            )
        )

    covered = [t for t in topics if t.in_context]
    return QuestionReport(
        id=qid,
        question=question,
        expected=[norm(t) for t in expected_topics],
        related_ids=related_ids,
        related_names=related_names,
        context_ids=context_ids,
        context_names=context_names,
        expected_count=len(expected_topics),
        covered_count=len(covered),
        percent=round(100.0 * len(covered) / len(expected_topics), 2) if expected_topics else 0.0,
        topics=topics,
        scored_top12=[{k: c[k] for k in ("entity_id", "name", "score", "in_question", "name_coverage", "specificity")} for c in scored[:12]],
    )


@dataclass
class BatchReport:
    questions: list[QuestionReport] = field(default_factory=list)
    themes_total: int = 0
    entities_total: int = 0
    total_expected: int = 0
    total_covered: int = 0

    @property
    def overall_percent(self) -> float:
        if not self.total_expected:
            return 0.0
        return round(100.0 * self.total_covered / self.total_expected, 2)


def measure_batch(
    questions: list[dict[str, Any]],
) -> BatchReport:
    """Замер покрытия для списка вопросов.

    Каждый элемент questions: {"id", "question", "expected": [...]}.
    """
    from narrative_engine.world_engine import get_world_engine

    engine = get_world_engine()
    report = BatchReport(themes_total=len(_load_theme_names()), entities_total=0)
    for q in questions:
        r = measure_question(
            question=q["question"],
            expected_topics=q["expected"],
            qid=q.get("id"),
            engine=engine,
        )
        report.questions.append(r)
        report.total_expected += r.expected_count
        report.total_covered += r.covered_count
    report.entities_total = len([e for c, _ in _iter_entities(engine) for e in [1]])
    return report


def to_json(report: BatchReport) -> str:
    """Серийлизовать отчёт в ASCII-safe JSON (кириллица экранируется)."""

    def _default(o: Any) -> Any:
        if isinstance(o, TopicResult):
            return {
                "topic": o.topic,
                "expected_normalized": o.expected_normalized,
                "in_genome_themes": o.in_genome_themes,
                "carrier_count": o.carrier_count,
                "carrier_ids": o.carrier_ids,
                "in_related": o.in_related,
                "in_context": o.in_context,
                "uncapped_rank": o.uncapped_rank,
                "uncapped_score": o.uncapped_score,
            }
        if isinstance(o, QuestionReport):
            return {
                "id": o.id,
                "question": o.question,
                "expected": o.expected,
                "related_ids": o.related_ids,
                "related_names": o.related_names,
                "context_ids": o.context_ids,
                "context_names": o.context_names,
                "expected_count": o.expected_count,
                "covered_count": o.covered_count,
                "percent": o.percent,
                "topics": o.topics,
                "scored_top12": o.scored_top12,
            }
        if isinstance(o, BatchReport):
            return {
                "questions": o.questions,
                "themes_total": o.themes_total,
                "entities_total": o.entities_total,
                "total_expected": o.total_expected,
                "total_covered": o.total_covered,
                "overall_percent": o.overall_percent,
            }
        raise TypeError(f"not serializable: {type(o)!r}")

    return json.dumps(report, default=_default, ensure_ascii=True, indent=2)


def _load_theme_names() -> dict[str, dict[str, Any]]:
    """Имена тем из GENOME modules.themes (ключ — нормализованное имя)."""
    try:
        genome = json.loads(GENOME_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    themes = (genome.get("modules") or {}).get("themes") or []
    return {norm(t.get("name", "")): t for t in themes if isinstance(t, dict)}
