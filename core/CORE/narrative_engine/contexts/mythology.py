"""Mythology Context — мифологический контекст для темы."""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

log = logging.getLogger("hermes.narrative.contexts.mythology")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "KNOWLEDGE"


class ThemeAnalysis(BaseModel):
    name: str
    description: str = ""
    layers: list[str] = Field(default_factory=list)  # 3-слойный анализ


class SymbolicLink(BaseModel):
    symbol: str
    meaning: str = ""
    connected_themes: list[str] = Field(default_factory=list)


class MythParallel(BaseModel):
    culture: str
    myth: str
    detail: str = ""


class StoryPattern(BaseModel):
    name: str
    description: str = ""
    hidden_meaning: str = ""


class MythologyContext(BaseModel):
    relevant_themes: list[ThemeAnalysis] = Field(default_factory=list)
    symbolic_connections: list[SymbolicLink] = Field(default_factory=list)
    spiritual_stage: str = ""
    mythological_parallels: list[MythParallel] = Field(default_factory=list)
    applicable_patterns: list[StoryPattern] = Field(default_factory=list)


class MythologyContextBuilder:
    def __init__(self):
        self._themes_deep = self._load("THEMES_DEEP.json")
        self._symbols_exp = self._load("SYMBOLS_EXPANDED.json")
        self._esoteric = self._load("ESOTERIC_CONNECTIONS.json")
        self._hierarchy = self._load("HIERARCHY_OF_LIGHT.json")
        self._spiritual = self._load("SPIRITUAL_TRANSFORMATION.json")
        self._patterns = self._load("PATTERNS.json")

    def _load(self, filename: str) -> dict:
        path = KNOWLEDGE_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def build(self, query: str = "", theme: str = "") -> MythologyContext:
        query_lower = query.lower()

        themes = []
        for t in self._themes_deep.get("themes", []):
            t_name = t.get("name", "")
            t_desc = t.get("description", "")
            if (not theme or theme.lower() in t_name.lower() or theme.lower() in t_desc.lower()
                    or any(kw in query_lower for kw in t_name.lower().split() if len(kw) > 3)):
                layers = []
                if t.get("layers"):
                    for layer_name, layer_val in t["layers"].items():
                        layers.append(f"{layer_name}: {layer_val[:100]}")
                themes.append(ThemeAnalysis(
                    name=t_name,
                    description=t_desc[:200] if t_desc else "",
                    layers=layers,
                ))

        symbols = []
        for s in self._symbols_exp.get("symbols", []):
            s_name = s.get("name", "")
            if any(kw in query_lower for kw in [s_name.lower()] + [a.lower() for a in s.get("aliases", [])]):
                symbols.append(SymbolicLink(
                    symbol=s_name,
                    meaning=s.get("meaning", ""),
                    connected_themes=s.get("connected_themes", []),
                ))

        parallels = []
        for conn in self._esoteric.get("connections", []):
            if any(kw in query_lower for kw in conn.get("keywords", [])):
                parallels.append(MythParallel(
                    culture=conn.get("culture", ""),
                    myth=conn.get("myth", ""),
                    detail=conn.get("detail", ""),
                ))

        patterns = []
        for p in self._patterns.get("patterns", []):
            p_name = p.get("name", "")
            p_desc = p.get("description", "")
            keywords = p_name.lower().split() + p_desc.lower().split()[:5]
            if any(kw in query_lower for kw in keywords if len(kw) > 3):
                patterns.append(StoryPattern(
                    name=p_name,
                    description=p_desc,
                    hidden_meaning=p.get("hidden_meaning", ""),
                ))

        spiritual_stage = ""
        for stage in self._spiritual.get("stages", []):
            if any(kw in query_lower for kw in stage.get("keywords", [])):
                spiritual_stage = stage.get("name", "")
                break

        return MythologyContext(
            relevant_themes=themes[:5],
            symbolic_connections=symbols[:5],
            spiritual_stage=spiritual_stage,
            mythological_parallels=parallels[:5],
            applicable_patterns=patterns[:3],
        )
