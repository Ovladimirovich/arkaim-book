"""M11 — Screenplay-Book Event Linking resolver.

Read-only resolver для связей между книжными фрагментами и сценарными сценами.
Использует только явные связи из screenplay_links.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"
SCREENPLAY_LINKS_PATH = KNOWLEDGE_DIR / "screenplay_links.json"


@dataclass
class ScreenplayBookLink:
    """Связь между книжным фрагментом и сценарной сценой.

    Первые 4 поля — исходный read-only контракт (M11), он неизменён.
    ``provenance`` — опциональные аудитные данные
    (``_provenance_metadata`` из screenplay_links.json, M16.3/M10-M12);
    ``None`` для записей в чистом 4-полевом формате.
    """

    screenplay_scene_id: str
    book_chunk_id: str
    confidence: float = 1.0
    notes: str = ""
    provenance: Optional[dict] = None


@dataclass
class ScreenplayBookLinker:
    """Read-only resolver связей между книгой и сценарием."""

    links: list[ScreenplayBookLink] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: Optional[Path] = None) -> "ScreenplayBookLinker":
        """Загрузить связи из JSON файла."""
        path = path or SCREENPLAY_LINKS_PATH
        if not path.exists():
            return cls(links=[])

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return cls(links=[])

        links = []
        for item in data:
            meta = item.get("_provenance_metadata")
            link = ScreenplayBookLink(
                screenplay_scene_id=str(item.get("screenplay_scene_id", "")),
                book_chunk_id=str(item.get("book_chunk_id", "")),
                confidence=float(item.get("confidence", 1.0)),
                notes=str(item.get("notes", "")),
                provenance=meta if isinstance(meta, dict) else None,
            )
            if link.screenplay_scene_id and link.book_chunk_id:
                links.append(link)

        return cls(links=links)

    def get_links_for_scene(self, scene_id: str) -> list[ScreenplayBookLink]:
        """Получить связи для сценарной сцены."""
        return [link for link in self.links if link.screenplay_scene_id == scene_id]

    def get_links_for_chunk(self, chunk_id: str) -> list[ScreenplayBookLink]:
        """Получить связи для книжного фрагмента."""
        return [link for link in self.links if link.book_chunk_id == chunk_id]

    def get_links_for_entity(self, entity_id: str) -> list[ScreenplayBookLink]:
        """Получить связи для entity (если entity_id используется как scene_id или chunk_id)."""
        scene_links = self.get_links_for_scene(entity_id)
        chunk_links = self.get_links_for_chunk(entity_id)
        return scene_links + chunk_links
