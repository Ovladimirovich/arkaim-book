"""Visual Genome — CRUD + versioning визуального генома."""
from pathlib import Path
from typing import Optional
import hashlib
import json

from visualization.schema import VisualGenomeEntry, CharacterVisual, LocationVisual


class VisualGenomeStore:
    """Хранилище визуального генома."""

    def __init__(self, db_path: Path | None = None):
        # Пока in-memory; потом заменить на SQLite/CHROMA
        self._entries: dict[str, VisualGenomeEntry] = {}

    def add_entry(self, entry: VisualGenomeEntry) -> VisualGenomeEntry:
        key = f"{entry.book_id}:{entry.entity_type}:{entry.entity_id}"
        existing = self._entries.get(key)
        if existing:
            entry.version = existing.version + 1
            entry.source_hash = existing.source_hash
        self._entries[key] = entry
        return entry

    def get_entry(self, book_id: str, entity_type: str, entity_id: str) -> VisualGenomeEntry | None:
        key = f"{book_id}:{entity_type}:{entity_id}"
        return self._entries.get(key)

    def list_entries(self, book_id: str) -> list[VisualGenomeEntry]:
        return [e for e in self._entries.values() if e.book_id == book_id]

    def compute_source_hash(self, source_text: str) -> str:
        return hashlib.sha256(source_text.encode()).hexdigest()[:16]

    def invalidate_by_source_hash(self, book_id: str, old_hash: str):
        """Пометить все записи с source_hash как устаревшие."""
        for key, entry in list(self._entries.items()):
            if entry.book_id == book_id and entry.source_hash == old_hash:
                entry.version = 0