"""SymbolEngine — визуальная интерпретация символов."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from .visual_models import SymbolContext

log = logging.getLogger("visual.symbol_engine")

_KNOWLEDGE_DIR = Path(__file__).parent / "VISUAL_KNOWLEDGE"


class SymbolEngine:
    """Возвращает SymbolContext для символов мира книги."""

    def __init__(self, knowledge_path: Path | None = None):
        self._knowledge = self._load(knowledge_path or _KNOWLEDGE_DIR)

    def _load(self, path: Path) -> dict:
        f = path / "VISUAL_SYMBOLS.json"
        if f.exists():
            return json.loads(f.read_text("utf-8-sig"))
        return {}

    def get_symbols(self, tags: list[str]) -> list[SymbolContext]:
        result = []
        for tag in tags:
            tag_clean = tag.split(":")[-1] if ":" in tag else tag
            if tag_clean in self._knowledge:
                s = self._knowledge[tag_clean]
                result.append(SymbolContext(
                    name=tag_clean,
                    literal=s.get("literal", ""),
                    metaphorical=s.get("metaphorical", ""),
                    spiritual=s.get("spiritual", ""),
                    archetypal=s.get("archetypal", ""),
                    colors=s.get("colors", []),
                    visual_elements=s.get("visual_elements", []),
                ))
            else:
                result.append(SymbolContext(name=tag_clean, literal=tag_clean))
        return result
