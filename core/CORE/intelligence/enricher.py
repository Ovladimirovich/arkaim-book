"""
GenomeEnricher — обогащение чанков метаданными из полного генома (GENOME_v1.0.0.json).
Для каждого чанка определяет: темы, персонажи, символы, ценности, конфликты.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional

BASE = Path(__file__).resolve().parents[2]
GENOME_PATH = BASE / "GENOME" / "GENOME_v1.0.0.json"


class GenomeEnricher:
    def __init__(self, genome_path: Optional[Path] = None, nameresolver=None):
        self.genome_path = genome_path or GENOME_PATH
        self._genome = None
        self._nameresolver = nameresolver
        self._load_genome()
        self._build_index()

    def _load_genome(self):
        if self.genome_path.exists():
            self._genome = json.loads(self.genome_path.read_text(encoding="utf-8"))

    def _build_index(self):
        """
        Строит обратные индексы для быстрого поиска:
        - keyword -> list of (type, id, name, description)
        """
        self._keywords = []
        if not self._genome:
            return

        m = self._genome.get("modules", {})

        # Themes
        for t in m.get("themes", []):
            words = self._extract_keywords(t["name"])
            for w in words:
                self._keywords.append({
                    "word": w.lower(),
                    "type": "theme",
                    "id": t["id"],
                    "name": t["name"],
                    "description": t.get("description", ""),
                })

        # Characters — с учётом NameResolver
        resolved_char_names = set()
        for c in m.get("characters", []):
            cname = c["name"]
            resolved_char_names.add(cname)
            words = self._extract_keywords(cname)
            for alias in c.get("aliases", []):
                words.extend(self._extract_keywords(alias))
            # Добавляем все алиасы из NameResolver
            if self._nameresolver:
                canonical = self._nameresolver.resolve(cname)
                all_aliases = self._nameresolver.get_all_aliases(canonical)
                for a in all_aliases:
                    if a != cname:
                        words.extend(self._extract_keywords(a))
            for w in sorted(set(words)):
                self._keywords.append({
                    "word": w.lower(),
                    "type": "character",
                    "id": c["id"],
                    "name": cname,
                    "description": c.get("description", ""),
                })

        # Symbols
        for s in m.get("symbols", []):
            words = self._extract_keywords(s["name"])
            for w in words:
                self._keywords.append({
                    "word": w.lower(),
                    "type": "symbol",
                    "id": s["id"],
                    "name": s["name"],
                    "meaning": s.get("meaning", ""),
                })

        # Conflicts
        for cf in m.get("conflicts", []):
            words = self._extract_keywords(cf["name"])
            for w in words:
                self._keywords.append({
                    "word": w.lower(),
                    "type": "conflict",
                    "id": cf["id"],
                    "name": cf["name"],
                })

        # Values (from author_intent)
        ai = self._genome.get("author_intent", {})
        for v in ai.get("core_values", []):
            self._keywords.append({
                "word": v.lower(),
                "type": "value",
                "id": f"val_{hash(v) % 10000:04d}",
                "name": v,
            })

    def _extract_keywords(self, text: str) -> List[str]:
        """Извлекает значимые слова из текста."""
        text = text.lower()
        words = re.findall(r"[а-яёa-z]+", text)
        result = set()
        for w in words:
            if len(w) >= 3:
                result.add(w)
        return list(result)

    def enrich_chunk(self, chunk_text: str) -> Dict:
        """
        Определяет, какие элементы генома релевантны для текста чанка.
        Возвращает словарь со списками найденных тем, персонажей, символов, ценностей.
        """
        text_lower = chunk_text.lower()
        found_themes = {}
        found_characters = {}
        found_symbols = {}
        found_conflicts = {}
        found_values = {}

        for kw in self._keywords:
            if kw["word"] in text_lower:
                if kw["type"] == "theme":
                    found_themes[kw["id"]] = {"id": kw["id"], "name": kw["name"], "description": kw.get("description", "")}
                elif kw["type"] == "character":
                    found_characters[kw["id"]] = {"id": kw["id"], "name": kw["name"], "description": kw.get("description", "")}
                elif kw["type"] == "symbol":
                    found_symbols[kw["id"]] = {"id": kw["id"], "name": kw["name"], "meaning": kw.get("meaning", "")}
                elif kw["type"] == "conflict":
                    found_conflicts[kw["id"]] = {"id": kw["id"], "name": kw["name"]}
                elif kw["type"] == "value":
                    found_values[kw["id"]] = {"id": kw["id"], "name": kw["name"]}

        return {
            "themes": list(found_themes.values()),
            "characters": list(found_characters.values()),
            "symbols": list(found_symbols.values()),
            "conflicts": list(found_conflicts.values()),
            "values": list(found_values.values()),
        }

    def _deduplicate_by_canonical(self, items: List[Dict]) -> List[Dict]:
        """
        Удаляет дубликаты персонажей, объединяя алиасы в одно каноническое имя.
        """
        if not self._nameresolver:
            return items
        seen = set()
        result = []
        for item in items:
            canonical = self._nameresolver.resolve(item["name"])
            if canonical not in seen:
                seen.add(canonical)
                result.append(item)
        return result

    def enrich_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Обогащает список чанков метаданными из генома.
        Модифицирует каждый chunk, добавляя enriched_* поля.
        """
        result = []
        for chunk in chunks:
            enrichment = self.enrich_chunk(chunk["text"])
            # Дедикаплицируем персонажей через NameResolver
            chars = self._deduplicate_by_canonical(enrichment["characters"])
            chunk["enriched_themes"] = [t["name"] for t in enrichment["themes"]]
            chunk["enriched_characters"] = [c["name"] for c in chars]
            chunk["enriched_symbols"] = [s["name"] for s in enrichment["symbols"]]
            chunk["enriched_conflicts"] = [cf["name"] for cf in enrichment["conflicts"]]
            chunk["enriched_values"] = [v["name"] for v in enrichment["values"]]
            chunk["enrichment_count"] = (
                len(enrichment["themes"]) +
                len(chars) +
                len(enrichment["symbols"]) +
                len(enrichment["conflicts"]) +
                len(enrichment["values"])
            )
            result.append(chunk)
        return result

    def get_genome_stats(self) -> Dict:
        if not self._genome:
            return {"status": "not_loaded"}
        m = self._genome.get("modules", {})
        ai = self._genome.get("author_intent", {})
        return {
            "themes_count": len(m.get("themes", [])),
            "characters_count": len(m.get("characters", [])),
            "symbols_count": len(m.get("symbols", [])),
            "conflicts_count": len(m.get("conflicts", [])),
            "timeline_events": len(m.get("timeline", [])),
            "core_values": len(ai.get("core_values", [])),
            "status": "loaded",
        }
