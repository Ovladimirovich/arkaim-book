# -*- coding: utf-8 -*-
"""M25 regression: покрытие вопросных тем контекстом Knowledge Core.

Проверяет, что все темы, названные в мультитематических вопросах /book/ask,
попадают в related_entities и затем в контекст Knowledge Core
(gather_knowledge_core_context). Срезы MAX_RESULTS (были 3, стать 10) не
должны отрезать вопросные темы.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # .../arkaim
for p in (str(REPO / "runtime"), str(REPO / "core" / "CORE"), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)


from core.services.question_coverage import measure_batch  # noqa: E402

M25_QUESTIONS = [
    {
        "id": "q1_hyperborea_energy",
        "question": "Как Гиперборея связана с Энергетикой Аркаима и Ландшафтной энергетикой?",
        "expected": ["Гиперборея", "Энергетика Аркаима", "Ландшафтная энергетика"],
    },
    {
        "id": "q2_teacher",
        "question": "Как Миссия учителя связана с Учительом и учениками и Передачей знаний?",
        "expected": ["Миссия учителя", "Учитель и ученики", "Передача знаний"],
    },
    {
        "id": "q3_battle",
        "question": "Как Великая Битва связана с Иерархией Света и Ролью Посвящённых?",
        "expected": ["Великая Битва", "Иерархия Света", "Роль Посвящённых"],
    },
    {
        "id": "q4_hyperborea_four",
        "question": "Как Гиперборея связана с Миграциею Гипербореев, Закрытием эры Гипербореи и Эмиграциею Гипербореев?",
        "expected": ["Гиперборея", "Миграция Гипербореев", "Закрытие эры Гипербореи", "Эмиграция Гипербореев"],
    },
    {
        "id": "q5_heritage",
        "question": "Как Культурное наследие связано со Связью поколений и Преемственностью культурного наследия?",
        "expected": ["Культурное наследие", "Связь поколений", "Преемственность культурного наследия"],
    },
]


def test_m25_all_question_topics_reach_knowledge_core():
    """Все вопросные темы должны попасть в контекст Knowledge Core (100% покрытия)."""
    report = measure_batch(M25_QUESTIONS)
    assert report.overall_percent == 100.0, f"ожидалось 100% покрытия, получилось {report.overall_percent}% ({report.total_covered}/{report.total_expected})"
    for q in report.questions:
        assert q.percent == 100.0, f"{q.id}: {q.percent}% ({q.covered_count}/{q.expected_count})"
        for t in q.topics:
            assert t.in_context, f"{q.id}: тема '{t.topic}' не попала в контекст Knowledge Core"
            assert t.in_related, f"{q.id}: тема '{t.topic}' не попала в related_entities"


def test_m25_no_topic_is_capped_out():
    """Ни одна вопросная тема не должна выпадать из related_entities из-за среза."""
    report = measure_batch(M25_QUESTIONS)
    for q in report.questions:
        related_names = set(q.related_names)
        context_names = set(q.context_names)
        for exp in q.expected:
            assert exp in related_names, f"{q.id}: '{exp}' нет в related_entities"
            assert exp in context_names, f"{q.id}: '{exp}' нет в контексте Knowledge Core"
