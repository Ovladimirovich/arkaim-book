"""SynopsisBuilder — генератор производных структур сценария.

Строит два производных файла в KNOWLEDGE из исходного киносценария:
  - SYNOPSIS_DOCUMENT.json — структурированный сценарий (raw_text + сцены + абзацы);
  - SYNOPSIS_PROFILE.json  — профиль/метрики сценария.

Разбиение на сцены делегируется единому ScreenplayChunker (intelligence.chunker),
поэтому структура индексации, API (/book/screenplay) и эти производные файлы
всегда согласованы.

Смещения (char_start/char_end) отсчитываются от позиции в raw_text (полный текст
исходного файла), то есть raw_text[char_start:char_end] == text.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import config
from intelligence.chunker import ScreenplayChunker

# Маркеры сцен, попадающие в structure.chapter_markers (латиница + русские + монтаж).
SCENE_MARKERS = ["INT.", "EXT.", "ВНУТРЕННИЙ", "НАРУЖНЫЙ", "ВНЕШНИЙ", "ИНТ.", "ЭКСТ.", "MONTAGE", "МОНТАЖ"]

# Разделитель абзацев внутри сцены — одна и более пустых строк.
_PARAGRAPH_SPLIT_RE = re.compile(r"\n[ \t]*\n+")

# Скорость чтения для оценки времени (как в BOOK_PROFILE.json): ~300 знаков/мин.
_CHARS_PER_MINUTE = 300

# Провенанс сохраняется как в исходных артефактах (не переопределяется генератором).
_DOCUMENT_PROVENANCE = {
    "category": "AUTHOR_CANON",
    "source_level": "CANON",
    "notes": "Direct synopsis from book",
    "enriched_at": "Milestone B",
}
_PROFILE_PROVENANCE = {
    "category": "DERIVED",
    "source_level": "SYSTEM_INTERPRETATION",
    "notes": "Synopsis profile from GENOME",
    "enriched_at": "Milestone B",
}

DEFAULT_SCREENPLAY_REL = Path("SOURCE_OF_TRUTH") / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"


def _resolve_screenplay_path(screenplay_path: Optional[Path] = None) -> Path:
    if screenplay_path is not None:
        return Path(screenplay_path)
    return Path(config.SOURCE_OF_TRUTH) / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"


def _relative_source_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path(config.PROJECT_ROOT).resolve()).as_posix()
    except ValueError:
        return str(path)


def _split_paragraphs(scene_text: str) -> List[str]:
    blocks = _PARAGRAPH_SPLIT_RE.split(scene_text)
    return [b.strip() for b in blocks if b.strip()]


def _find_offsets(raw_text: str, texts: List[str], start: int, end: int) -> List[Tuple[int, int]]:
    """Абсолютные (start, end) каждого текста в raw_text в пределах [start, end).

    Тексты идут по порядку (как в исходнике), поэтому поиск ведётся «бегущим
    курсором» — это корректно обрабатывает повторяющиеся фрагменты.
    """
    offsets: List[Tuple[int, int]] = []
    cursor = start
    for text in texts:
        idx = raw_text.find(text, cursor, end)
        if idx < 0:  # запасной поиск, если граница end оказалась слишком строгой
            idx = raw_text.find(text, cursor)
        if idx < 0:
            offsets.append((-1, -1))
            continue
        offsets.append((idx, idx + len(text)))
        cursor = idx + len(text)
    return offsets


def build_synopsis_document(
    screenplay_path: Optional[Path] = None,
    created_at: Optional[str] = None,
) -> Dict:
    """Собрать структуру SYNOPSIS_DOCUMENT.json из киносценария."""
    path = _resolve_screenplay_path(screenplay_path)
    if not path.exists():
        raise FileNotFoundError(f"Сценарий не найден: {path}")

    raw_text = path.read_text(encoding="utf-8")
    scenes = ScreenplayChunker(screenplay_path=path).chunk_by_scene()

    chapters: List[Dict] = []
    paragraphs: List[Dict] = []
    cursor = 0
    para_index = 0

    for i, scene in enumerate(scenes):
        content = scene["text"]
        idx = raw_text.find(content, cursor)
        if idx < 0:
            idx = raw_text.find(content)
        scene_start = idx
        scene_end = idx + len(content)
        cursor = max(cursor, scene_end)

        scene_id = scene["scene_id"]
        scene_paras = _split_paragraphs(content)
        para_offsets = _find_offsets(raw_text, scene_paras, scene_start, scene_end)

        for p_text, (p_start, p_end) in zip(scene_paras, para_offsets):
            para_index += 1
            paragraphs.append(
                {
                    "id": f"sp_{para_index:04d}",
                    "scene_id": scene_id,
                    "char_start": p_start,
                    "char_end": p_end,
                    "text": p_text,
                }
            )

        chapters.append(
            {
                "id": scene_id,
                "number": i,
                "title": scene["scene_title"],
                "char_start": scene_start,
                "char_end": scene_end,
                "paragraphs_count": len(scene_paras),
                "text": content,
            }
        )

    return {
        "_provenance_metadata": dict(_DOCUMENT_PROVENANCE),
        "document_id": "doc_synopsis_001",
        "format_version": "1.0.0",
        "source": {
            "file": _relative_source_ref(path),
            "type": "md",
            "total_chars": len(raw_text),
            "total_lines": len(raw_text.splitlines()),
        },
        "structure": {
            "type": "scenes",
            "has_chapters": True,
            "chapter_markers": list(SCENE_MARKERS),
        },
        "content": {
            "raw_text": raw_text,
            "chapters": chapters,
            "paragraphs": paragraphs,
        },
        "metadata": {
            "language": "ru",
            "encoding": "utf-8",
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        },
    }


def build_synopsis_profile(document: Dict) -> Dict:
    """Собрать SYNOPSIS_PROFILE.json по структуре документа."""
    raw_text = document["content"]["raw_text"]
    chapters = document["content"]["chapters"]
    paragraphs = document["content"]["paragraphs"]
    total_chars = len(raw_text)

    return {
        "_provenance_metadata": dict(_PROFILE_PROVENANCE),
        "book_id": "nasledie-arkaima-synopsis",
        "title": "Наследие Аркаима (сценарий)",
        "author": "ОВладимирович",
        "source_type": "secondary",
        "metrics": {
            "total_chars": total_chars,
            "total_chapters": len(chapters),
            "total_paragraphs": len(paragraphs),
            "estimated_read_time_minutes": total_chars // _CHARS_PER_MINUTE,
            "unique_entities_count": 0,
            "themes_count": 0,
        },
        "status": {
            "reader_completed": True,
            "understanding_completed": False,
            "genome_completed": False,
            "validation_completed": False,
        },
        "versions": {
            "book_version": "1.0.0",
            "analysis_version": "1.0.0",
            "genome_version": None,
        },
    }


def generate(
    screenplay_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
) -> Dict:
    """Сгенерировать SYNOPSIS_DOCUMENT.json и SYNOPSIS_PROFILE.json.

    Возвращает сводку: число сцен/абзацев и пути записанных файлов.
    """
    document = build_synopsis_document(screenplay_path=screenplay_path)
    profile = build_synopsis_profile(document)

    out_dir = Path(output_dir) if output_dir is not None else Path(config.KNOWLEDGE_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc_path = out_dir / "SYNOPSIS_DOCUMENT.json"
    profile_path = out_dir / "SYNOPSIS_PROFILE.json"
    doc_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "scenes": len(document["content"]["chapters"]),
        "paragraphs": len(document["content"]["paragraphs"]),
        "files": [str(doc_path), str(profile_path)],
    }
