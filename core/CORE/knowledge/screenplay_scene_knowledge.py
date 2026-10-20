"""Read-only обогащение сцен киносценария существующими знаниями.

Модуль не создаёт новых сущностей, не пишет в источники и не хранит
собственную копию знаний. Персонажи канонизируются только по явно
утверждённой таблице алиасов; отсутствующие данные остаются пустыми
с указанием причины в ``knowledge_missing``.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from .screenplay_scene_aliases import TERM_SPECS
from .screenplay_scene_world_links import build_world_links

_CORE_DIR = Path(__file__).resolve().parents[2]
_LINKS_PATH = _CORE_DIR / "KNOWLEDGE" / "screenplay_links.json"
_CHUNKS_PATH = _CORE_DIR / "KNOWLEDGE" / "enriched_chunks.json"
_LOCATION_VISUALS_PATH = (
    _CORE_DIR / "CORE" / "visual" / "VISUAL_KNOWLEDGE" / "LOCATION_VISUALS.json"
)

log = logging.getLogger("knowledge.screenplay_scene_knowledge")

_TIME_TOKEN_TO_VALUE = {
    "ДЕНЬ": "day",
    "НОЧЬ": "night",
    "УТРО": "morning",
    "ВЕЧЕР": "evening",
    "ЗАКАТ": "sunset",
    "РАССВЕТ": "dawn",
    "СУМЕРКИ": "dusk",
    "СМЕРКАЕТСЯ": "dusk",
}
_TIME_RE = re.compile(
    r"(?<!\w)(ДЕНЬ|НОЧЬ|УТРО|ВЕЧЕР|ЗАКАТ|РАССВЕТ|СУМЕРКИ|СМЕРКАЕТСЯ)(?!\w)",
    re.IGNORECASE,
)
_TIME_SPLIT_RE = re.compile(
    r"\s*[-–—.]\s*(?:ДЕНЬ|НОЧЬ|УТРО|ВЕЧЕР|ЗАКАТ|РАССВЕТ|СУМЕРКИ|СМЕРКАЕТСЯ)\b.*$",
    re.IGNORECASE,
)
_NUMBER_PREFIX_RE = re.compile(r"^\s*\d+\.?\s*")
_SCENE_MARKER_RE = re.compile(
    r"^\s*(?:INT|EXT|ИНТ|ЭКСТ|ВНУТРЕННИЙ|НАРУЖНЫЙ|ВНЕШНИЙ|MONTAGE|МОНТАЖ)\.?\s*",
    re.IGNORECASE,
)

_CHARACTER_PATTERNS: tuple[tuple[re.Pattern[str], str, bool], ...] = tuple(
    (
        re.compile(r"(?<![\w-])" + pattern + r"(?![\w-])", re.IGNORECASE),
        canonical,
        lowercase_ok,
    )
    for pattern, canonical, lowercase_ok in TERM_SPECS
)

_LOCATION_ROOT_TO_ID: tuple[tuple[str, str], ...] = (
    ("АТЛАНТИД", "Атлантида"),
    ("ОКЕАНИ", "Океания"),
    ("ГИПЕРБОРЕЯ", "Гиперборея"),
    ("АРКАИМ", "Аркаим"),
    ("ПОДЗЕМН", "Подземные города"),
    ("СВЯТИЛИЩ", "Святилища"),
)


def _scene_type(title: str) -> str:
    upper = title.upper()
    if re.search(r"\b(INT|ИНТ|ВНУТРЕННИЙ)\b", upper):
        return "INT"
    if re.search(r"\b(EXT|ЭКСТ|НАРУЖНЫЙ|ВНЕШНИЙ)\b", upper):
        return "EXT"
    if re.search(r"\b(MONTAGE|МОНТАЖ)\b", upper):
        return "MONTAGE"
    return ""


def _time_of_day(title: str) -> str:
    match = _TIME_RE.search(title)
    if match is None:
        return ""
    return _TIME_TOKEN_TO_VALUE.get(match.group(1).upper(), "")


def _clean_location(raw_location: str, scene_type: str) -> str:
    if scene_type == "MONTAGE":
        return ""
    value = _NUMBER_PREFIX_RE.sub("", raw_location.strip())
    value = _SCENE_MARKER_RE.sub("", value)
    value = _TIME_SPLIT_RE.sub("", value, count=1)
    value = re.sub(r"\s+", " ", value).strip(" .-–—")
    return value


def _location_id(location_name: str, known_keys: frozenset[str]) -> str:
    normalized = re.sub(r"[^А-ЯЁA-Z0-9]+", " ", location_name.upper()).strip()
    if not normalized:
        return ""
    for root, canonical_id in _LOCATION_ROOT_TO_ID:
        if root in normalized and canonical_id in known_keys:
            return canonical_id
    return ""


def extract_characters(*texts: str) -> list[str]:
    """Извлечь канонические имена персонажей из заголовка и текста сцены."""
    text = "\n".join(part for part in texts if part)
    if not text:
        return []

    matches: list[tuple[int, int, str]] = []
    for pattern, canonical, lowercase_ok in _CHARACTER_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if not lowercase_ok and not value[:1].isupper():
                continue
            matches.append((match.start(), match.end(), canonical))

    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    characters: list[str] = []
    last_end = -1
    for start, end, canonical in matches:
        if start < last_end:
            continue
        if canonical not in characters:
            characters.append(canonical)
        last_end = end
    return characters


@lru_cache(maxsize=1)
def _load_book_data_cached(
    links_mtime_ns: int,
    links_size: int,
    chunks_mtime_ns: int,
    chunks_size: int,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    links = json.loads(_LINKS_PATH.read_text(encoding="utf-8"))
    chunks = json.loads(_CHUNKS_PATH.read_text(encoding="utf-8"))

    links_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in links:
        if not isinstance(link, dict):
            continue
        scene_id = link.get("screenplay_scene_id")
        if isinstance(scene_id, str) and scene_id:
            links_by_scene[scene_id].append(link)

    chunks_by_id: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_id = chunk.get("id")
        if isinstance(chunk_id, str) and chunk_id:
            chunks_by_id[chunk_id] = chunk

    return dict(links_by_scene), chunks_by_id


def _load_book_data() -> tuple[
    dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]
]:
    try:
        links_stat = _LINKS_PATH.stat()
        chunks_stat = _CHUNKS_PATH.stat()
    except OSError as exc:
        log.warning("screenplay_book_knowledge_unavailable error=%s", exc)
        return {}, {}
    return _load_book_data_cached(
        links_stat.st_mtime_ns,
        links_stat.st_size,
        chunks_stat.st_mtime_ns,
        chunks_stat.st_size,
    )


@lru_cache(maxsize=1)
def _load_location_keys_cached(
    location_mtime_ns: int, location_size: int
) -> frozenset[str]:
    data = json.loads(_LOCATION_VISUALS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return frozenset()
    return frozenset(str(key) for key in data)


def _load_location_keys() -> frozenset[str]:
    try:
        stat = _LOCATION_VISUALS_PATH.stat()
    except OSError as exc:
        log.warning("location_visuals_unavailable error=%s", exc)
        return frozenset()
    return _load_location_keys_cached(stat.st_mtime_ns, stat.st_size)


def _book_links_for_scene(
    scene_id: str,
    links_by_scene: dict[str, list[dict[str, Any]]],
    chunks_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    links: list[dict[str, Any]] = []
    context: list[dict[str, Any]] = []
    for raw in links_by_scene.get(scene_id, []):
        metadata = raw.get("_provenance_metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        chunk_id = str(raw.get("book_chunk_id") or "")
        links.append(
            {
                "scene_id": scene_id,
                "chunk_id": chunk_id,
                "confidence": float(raw.get("confidence", 0.0) or 0.0),
                "notes": str(raw.get("notes", "")),
                "source_level": str(metadata.get("source_level", "")),
                "resolved_by": str(metadata.get("resolved_by", "")),
                "resolved_at": str(metadata.get("resolved_at", "")),
            }
        )
        chunk = chunks_by_id.get(chunk_id)
        if chunk is not None:
            context.append(
                {
                    "chunk_id": chunk_id,
                    "chapter_title": str(chunk.get("chapter_title", "")),
                    "text": str(chunk.get("text", "")),
                }
            )
    return links, context


def _world_links_provenance(summary: dict[str, Any]) -> str:
    """Сводит статусы связей с миром в одно значение происхождения.

    Учитываются только разрешённые связи: ``CONFIRMED`` и ``DERIVED``.
    Если разрешённых связей нет — значение ``ABSENT`` (связи не найдены,
    ничего не выдумано). Неразрешённые случаи описаны в ``world_link_missing``.
    """
    resolved = {
        status
        for status in ("CONFIRMED", "DERIVED")
        if summary.get(status.lower(), 0)
    }
    if not resolved:
        return "ABSENT"
    if len(resolved) == 1:
        return resolved.pop()
    return "MIXED"


def enrich_scene(scene: dict[str, Any], scene_text: str = "") -> dict[str, Any]:
    """Добавить к сцене только те знания, которые подтверждены источниками."""
    result = dict(scene)
    scene_id = str(result.get("scene_id", ""))
    title = str(result.get("title", ""))
    raw_location = str(result.get("location", ""))

    scene_type = _scene_type(title)
    time_of_day = _time_of_day(title)
    location_name = _clean_location(raw_location, scene_type)
    location_id = _location_id(location_name, _load_location_keys())
    characters = extract_characters(title, scene_text)

    links_by_scene, chunks_by_id = _load_book_data()
    book_links, book_context = _book_links_for_scene(
        scene_id, links_by_scene, chunks_by_id
    )

    result["characters"] = characters
    result["location_name"] = location_name
    result["location_id"] = location_id
    result["scene_type"] = scene_type
    result["time_of_day"] = time_of_day
    result["book_links"] = book_links
    result["book_context"] = book_context
    result["events"] = []
    result["emotion"] = result.get("emotion") or ""
    result["meaning_tags"] = result.get("meaning_tags") or []

    world = build_world_links(
        result, scene_text=scene_text, book_links=book_links, chunks=chunks_by_id
    )
    world_links = world["world_links"]
    world_summary = world["world_link_summary"]

    provenance = {
        "characters": "DERIVED_SCENE_TEXT" if characters else "ABSENT",
        "location": "DERIVED_SCENE_TITLE",
        "location_name": "DERIVED_SCENE_TITLE" if location_name else "ABSENT",
        "location_id": "KNOWLEDGE_CORE" if location_id else "ABSENT",
        "scene_type": "AUTHOR_CANON" if scene_type else "ABSENT",
        "time_of_day": "AUTHOR_CANON" if time_of_day else "ABSENT",
        "book_links": "AUTHOR_CANON" if book_links else "ABSENT",
        "book_context": "AUTHOR_CANON" if book_context else "ABSENT",
        "events": "ABSENT",
        "emotion": "ABSENT",
        "meaning_tags": "ABSENT",
        "world_links": _world_links_provenance(world_summary),
    }

    missing: dict[str, str] = {}
    if not characters:
        missing["characters"] = (
            "В заголовке и тексте сцены нет прямых упоминаний персонажей"
        )
    if not location_name:
        missing["location_name"] = "В заголовке сцены нет пригодной локации"
    if not location_id:
        missing["location_id"] = "Нет точного совпадения с LOCATION_VISUALS"
    if not scene_type:
        missing["scene_type"] = "В заголовке сцены нет маркера INT/EXT/MONTAGE"
    if not time_of_day:
        missing["time_of_day"] = "В заголовке сцены нет явного времени суток"
    if not book_links:
        missing["book_links"] = "Для сцены нет утверждённой связи с книгой"
    if not book_context:
        missing["book_context"] = (
            "Для утверждённых связей не найден текст книжных чанков"
        )
    missing["events"] = (
        "Нет scene-level источника событий; timeline/PLOT не используются"
    )
    missing["emotion"] = "Нет scene-level источника эмоции; значение не выводится"
    missing["meaning_tags"] = (
        "Нет scene-level источника тегов смысла; значение не выводится"
    )
    for link_type, reason in world["world_link_missing"].items():
        missing[f"world_{link_type}"] = reason

    result["world_links"] = world_links
    result["world_link_summary"] = world_summary
    result["world_link_missing"] = world["world_link_missing"]
    result["knowledge_provenance"] = provenance
    result["knowledge_missing"] = missing
    return result
