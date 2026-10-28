"""
Graph Linker — связывание знаний с существующим Knowledge Graph.
"""
import logging
from typing import Optional

from . import BaseLinker
from ..models import EnrichedKnowledge, LinkedKnowledge

log = logging.getLogger("hermes.knowledge_expansion.graph_linker")

# Предел связей на один элемент, чтобы результат оставался обозримым.
MAX_GRAPH_LINKS = 20


class GraphLinker(BaseLinker):
    """Связывает обогащённые знания с Knowledge Graph."""

    def __init__(self, graph_engine=None):
        self._graph = graph_engine

    async def link(self, enriched: list[EnrichedKnowledge]) -> list[LinkedKnowledge]:
        """Связать знания с графом."""
        results = []

        for item in enriched:
            linked = LinkedKnowledge(
                source=item.source,
                topic=item.topic,
                content=item.content,
                layers=item.layers,
                cross_references=item.cross_references,
                patterns=item.patterns,
                connections=item.connections,
                graph_links=[],
                metadata=item.metadata,
                confidence=item.confidence,
            )

            # Найти связи с существующими сущностями
            if self._graph:
                links = await self._find_graph_links(item)
                linked.graph_links = links

            results.append(linked)

        return results

    async def _find_graph_links(self, item: EnrichedKnowledge) -> list[dict]:
        """Найти связи с существующими сущностями в графе.

        Результат — не факты книги, а системная интерпретация: каждая
        связь помечена ``SYSTEM_INTERPRETATION`` и ``requires_author_review``.
        ``topic`` — имя сущности, поэтому оно резолвится в ``entity_id``
        (все одноимённые узлы; выбор одного случайного недопустим).
        """
        links: list[dict] = []

        if not self._graph:
            return links

        seen: set[tuple[str, str]] = set()

        def add_link(
            *,
            source_id: str | None,
            source_ambiguous: bool,
            target: str,
            target_id: str | None,
            rel_type: str,
            depth: int,
        ) -> None:
            if len(links) >= MAX_GRAPH_LINKS:
                return
            key = (target_id or target or "", rel_type)
            if key in seen:
                return
            seen.add(key)
            links.append(
                {
                    "source": item.topic,
                    "source_id": source_id,
                    "source_ambiguous": source_ambiguous,
                    "target": target,
                    "target_id": target_id,
                    "type": rel_type,
                    "depth": depth,
                    "provenance_category": "SYSTEM_INTERPRETATION",
                    "source_level": "SYSTEM_INTERPRETATION",
                    "requires_author_review": True,
                }
            )

        source_ids = self._resolve_entities(item.topic)
        source_ambiguous = len(source_ids) > 1

        # BFS по реальному графу от каждого одноимённого узла.
        for source_id in source_ids:
            if len(links) >= MAX_GRAPH_LINKS:
                break
            try:
                neighbors = self._graph.get_neighbors(source_id, max_depth=2)
            except Exception as e:
                log.warning(
                    "graph_link_error topic=%s entity_id=%s error=%s",
                    item.topic,
                    source_id,
                    e,
                )
                continue
            for neighbor in neighbors:
                nid = neighbor.get("entity_id") or ""
                name = neighbor.get("name") or nid
                if not (nid or name):
                    continue
                add_link(
                    source_id=source_id,
                    source_ambiguous=source_ambiguous,
                    target=name,
                    target_id=nid or None,
                    rel_type=neighbor.get("relationship_type") or "related_to",
                    depth=neighbor.get("depth", 1),
                )

        # Cross-references: тоже интерпретация, но не граф (depth=0).
        for ref in item.cross_references[:5]:
            if not ref:
                continue
            ref_ids = self._resolve_entities(ref)
            add_link(
                source_id=source_ids[0] if len(source_ids) == 1 else None,
                source_ambiguous=source_ambiguous,
                target=ref,
                target_id=ref_ids[0] if len(ref_ids) == 1 else None,
                rel_type="cross_reference",
                depth=0,
            )

        return links

    def _resolve_entities(self, value: str) -> list[str]:
        """Резолв имени в список entity_id (мягкий фолбэк для старых движков)."""
        if not value:
            return []
        resolver = getattr(self._graph, "resolve_entity_ids", None)
        if callable(resolver):
            try:
                return list(resolver(value))
            except Exception as e:
                log.warning("graph_resolve_error value=%s error=%s", value, e)
                return []
        # Движок без множественного резолва: строгий id/имя.
        strict = getattr(self._graph, "resolve_entity_id", None)
        if callable(strict):
            try:
                resolved = strict(value)
            except Exception:
                resolved = None
            return [resolved] if resolved else []
        checker = getattr(self._graph, "has_entity", None)
        if callable(checker):
            try:
                return [value] if checker(value) else []
            except Exception:
                return []
        return [value]
