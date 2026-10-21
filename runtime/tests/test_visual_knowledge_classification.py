"""Классификационный реестр покрывает визуальный слой.

Решение владельца 2026-10-21: слой ``core/CORE/visual/VISUAL_KNOWLEDGE``
внесён в реестр как ARTISTIC_MODEL с пометкой источника (план Visual
Intelligence, 19.07.2026). Основание — ``docs/VISUAL_CARDS_ATLANTIDA_OCEANIA_2026-10-21.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from narrative_engine.provenance.knowledge_classification import (  # noqa: E402
    KNOWLEDGE_CLASSIFICATION,
    KnowledgeCategory,
    classify_all,
    get_classification,
    is_canon_file,
    requires_author_review,
)

VISUAL_DIR = _CORE / "visual" / "VISUAL_KNOWLEDGE"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _visual_files() -> list[Path]:
    return sorted(path for path in VISUAL_DIR.glob("*.json"))


def test_every_visual_file_is_classified():
    """Каждый файл визуального слоя классифицирован."""
    files = _visual_files()
    assert files, "визуальный слой пуст — проверка неактуальна"

    for path in files:
        classification = get_classification(path.name)
        assert classification is not None, f"{path.name} не классифицирован"


def test_visual_files_are_artistic_models_not_canon():
    """Визуальный слой — художественная модель, а не канон."""
    for path in _visual_files():
        classification = get_classification(path.name)
        assert classification is not None
        assert classification.category == KnowledgeCategory.ARTISTIC_MODEL
        assert classification.is_canon is False
        assert classification.requires_author_review is True
        assert is_canon_file(path.name) is False
        assert requires_author_review(path.name) is True


def test_visual_files_carry_source_path():
    """Пометка источника: где файл лежит и чем он наполнен."""
    for path in _visual_files():
        classification = get_classification(path.name)
        assert classification is not None
        assert classification.source_path == f"core/CORE/visual/VISUAL_KNOWLEDGE/{path.name}"
        assert (PROJECT_ROOT / classification.source_path).exists()
        assert "Visual Intelligence" in classification.description


def test_classification_filenames_are_unique():
    """Одно имя — одна запись реестра (коллизия папок невозможна)."""
    filenames = [item.filename for item in KNOWLEDGE_CLASSIFICATION]

    assert len(filenames) == len(set(filenames))


def test_classify_all_covers_visual_layer():
    """Полная классификация включает визуальный слой."""
    result = classify_all()

    for path in _visual_files():
        assert result[path.name] == "ARTISTIC_MODEL"
