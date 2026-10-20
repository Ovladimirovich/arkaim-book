"""Read-only каталог сцен киносценария для Studio.

Источник — существующий ``SYNOPSIS_DOCUMENT.json`` (каноническая проекция
``SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md``).
Модуль ничего не пишет, не создаёт сцен и не хранит собственную копию.

OWNER-GO (2026-10-20): ``.md`` заморожен. При осознанной правке сценария
нужно пересобрать ``SYNOPSIS_DOCUMENT.json`` и обновить
``EXPECTED_SOURCE_SHA256``. Иначе каталог падает с ``SceneCatalogError``:
молчаливое расхождение источников запрещено.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, NoReturn

from .screenplay_scene_knowledge import enrich_scene

CORE_DIR = Path(__file__).resolve().parents[2]
SOURCE_MD_PATH = (
    CORE_DIR / "SOURCE_OF_TRUTH" / "SYNOPSIS" / "Наследие_Аркаима_Сценарий_Full.md"
)
SYNOPSIS_DOCUMENT_PATH = CORE_DIR / "KNOWLEDGE" / "SYNOPSIS_DOCUMENT.json"

CATALOG_CHAPTER = 0
CATALOG_CONTAINER_TITLE = "Сценарий"
CATALOG_SOURCE = "screenplay"

EXPECTED_SCENE_COUNT = 119
EXPECTED_SOURCE_SHA256 = (
    "9e0f8edbbd9d2256f1f13fbd1fa5c2e1c221de0c6c81fc33c34d64d9f38541db"
)
EXPECTED_SOURCE_CHARS = 149323
EXPECTED_SOURCE_LINES = 4192
EXPECTED_DOCUMENT_ID = "doc_synopsis_001"
EXPECTED_FORMAT_VERSION = "1.0.0"
EXPECTED_PROVENANCE_CATEGORY = "AUTHOR_CANON"
EXPECTED_PROVENANCE_SOURCE_LEVEL = "CANON"


class SceneCatalogError(RuntimeError):
    """Каталог нельзя построить без риска выдать неверные сцены."""


@dataclass(frozen=True, slots=True)
class CatalogScene:
    scene_id: str
    order_global: int
    title: str
    location: str
    text: str


def _fail(message: str) -> NoReturn:
    raise SceneCatalogError(message)


def _location_from_title(title: str) -> str:
    """DERIVED-локация тем же правилом, что и ScreenplayChunker."""
    from intelligence.chunker import _screenplay_location

    return _screenplay_location(title)


def _validate_document(
    document: dict[str, Any], md_text: str, source_sha256: str
) -> list[dict[str, Any]]:
    """Проверить проекцию против замороженного источника и вернуть сцены."""
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        _fail(
            f"screenplay source sha256 mismatch: expected {EXPECTED_SOURCE_SHA256}, got {source_sha256}"
        )
    if len(md_text) != EXPECTED_SOURCE_CHARS:
        _fail(
            f"screenplay source chars mismatch: expected {EXPECTED_SOURCE_CHARS}, got {len(md_text)}"
        )
    if len(md_text.splitlines()) != EXPECTED_SOURCE_LINES:
        _fail(
            f"screenplay source lines mismatch: expected {EXPECTED_SOURCE_LINES}, got {len(md_text.splitlines())}"
        )

    if document.get("document_id") != EXPECTED_DOCUMENT_ID:
        _fail(f"unexpected synopsis document_id: {document.get('document_id')!r}")
    if str(document.get("format_version")) != EXPECTED_FORMAT_VERSION:
        _fail(f"unexpected synopsis format_version: {document.get('format_version')!r}")

    provenance = document.get("_provenance_metadata")
    if not isinstance(provenance, dict):
        _fail("synopsis provenance is missing")
    if provenance.get("category") != EXPECTED_PROVENANCE_CATEGORY:
        _fail(
            f"unexpected synopsis provenance category: {provenance.get('category')!r}"
        )
    if provenance.get("source_level") != EXPECTED_PROVENANCE_SOURCE_LEVEL:
        _fail(f"unexpected synopsis source level: {provenance.get('source_level')!r}")

    source = document.get("source")
    if not isinstance(source, dict):
        _fail("synopsis source metadata is missing")
    if source.get("type") != "md":
        _fail(f"unexpected synopsis source type: {source.get('type')!r}")
    if source.get("total_chars") != EXPECTED_SOURCE_CHARS:
        _fail(f"synopsis total_chars mismatch: {source.get('total_chars')!r}")
    if source.get("total_lines") != EXPECTED_SOURCE_LINES:
        _fail(f"synopsis total_lines mismatch: {source.get('total_lines')!r}")

    content = document.get("content")
    scenes = content.get("chapters") if isinstance(content, dict) else None
    if not isinstance(scenes, list):
        _fail("synopsis content.chapters is not a list")
    if len(scenes) != EXPECTED_SCENE_COUNT:
        _fail(
            f"screenplay scene count mismatch: expected {EXPECTED_SCENE_COUNT}, got {len(scenes)}"
        )

    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            _fail(f"scene at index {index} is not an object")
        expected_id = f"scene_{index:03d}"
        if scene.get("id") != expected_id:
            _fail(
                f"unexpected scene id at index {index}: {scene.get('id')!r}, expected {expected_id!r}"
            )
        if scene.get("number") != index:
            _fail(f"unexpected scene number for {expected_id}: {scene.get('number')!r}")

        title = scene.get("title")
        text = scene.get("text")
        if not isinstance(title, str) or not title.strip():
            _fail(f"scene {expected_id} has no title")
        if not isinstance(text, str) or not text:
            _fail(f"scene {expected_id} has no text")

        start = scene.get("char_start")
        end = scene.get("char_end")
        if not isinstance(start, int) or not isinstance(end, int):
            _fail(f"scene {expected_id} has invalid char offsets")
        if start < 0 or end <= start or end > len(md_text):
            _fail(f"scene {expected_id} char offsets out of range: {start}:{end}")
        if md_text[start:end] != text:
            _fail(
                f"scene {expected_id} text does not match screenplay source at {start}:{end}"
            )

    return scenes


def _read_source() -> tuple[str, str]:
    try:
        source_bytes = SOURCE_MD_PATH.read_bytes()
    except OSError as exc:
        raise SceneCatalogError(
            f"screenplay source unavailable: {SOURCE_MD_PATH}"
        ) from exc
    try:
        source_text = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SceneCatalogError(
            f"screenplay source is not valid UTF-8: {SOURCE_MD_PATH}"
        ) from exc
    return source_text, hashlib.sha256(source_bytes).hexdigest()


@lru_cache(maxsize=1)
def _load_catalog_cached(
    md_mtime_ns: int, md_size: int, doc_mtime_ns: int, doc_size: int
) -> tuple[CatalogScene, ...]:
    source_text, source_sha256 = _read_source()
    try:
        document = json.loads(SYNOPSIS_DOCUMENT_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SceneCatalogError(
            f"synopsis document unavailable: {SYNOPSIS_DOCUMENT_PATH}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise SceneCatalogError(
            f"synopsis document is not valid JSON: {SYNOPSIS_DOCUMENT_PATH}"
        ) from exc

    scenes = _validate_document(document, source_text, source_sha256)
    catalog: list[CatalogScene] = []
    for index, scene in enumerate(scenes):
        title = scene["title"].strip()
        try:
            location = _location_from_title(title)
        except Exception as exc:
            raise SceneCatalogError(
                f"cannot derive location for {scene['id']}: {exc}"
            ) from exc
        catalog.append(
            CatalogScene(
                scene_id=scene["id"],
                order_global=index,
                title=title,
                location=location,
                text=scene["text"],
            )
        )
    return tuple(catalog)


def _load_catalog() -> tuple[CatalogScene, ...]:
    try:
        md_stat = SOURCE_MD_PATH.stat()
        doc_stat = SYNOPSIS_DOCUMENT_PATH.stat()
    except OSError as exc:
        raise SceneCatalogError(
            f"screenplay catalog source unavailable: {exc}"
        ) from exc
    return _load_catalog_cached(
        md_stat.st_mtime_ns, md_stat.st_size, doc_stat.st_mtime_ns, doc_stat.st_size
    )


def _scene_dict(scene: CatalogScene) -> dict[str, Any]:
    base = {
        "scene_id": scene.scene_id,
        "chapter": CATALOG_CHAPTER,
        "title": scene.title,
        "location": scene.location,
        "characters": [],
        "emotion": "",
        "meaning_tags": [],
        "source": CATALOG_SOURCE,
        "order_global": scene.order_global,
        "provenance": {
            "title": "AUTHOR_CANON",
            "text": "AUTHOR_CANON",
            "location": "DERIVED",
            "characters": "ABSENT",
            "emotion": "ABSENT",
            "meaning_tags": "ABSENT",
        },
    }
    return enrich_scene(base, scene.text)


def list_scenes() -> list[dict[str, Any]]:
    """Возвращает сцены каталога в порядке, едином для Studio-контуров."""
    return [_scene_dict(scene) for scene in _load_catalog()]


def get_scene(scene_id: str) -> dict[str, Any] | None:
    """Возвращает одну сцену по каноническому ID или None."""
    for scene in _load_catalog():
        if scene.scene_id == scene_id:
            return _scene_dict(scene)
    return None
