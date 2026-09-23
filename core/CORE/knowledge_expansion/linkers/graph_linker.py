"""
Graph Linker — связывание знаний с существующим Knowledge Graph.
"""
import logging
from typing import Optional

from . import BaseLinker
from ..models import EnrichedKnowledge, LinkedKnowledge

log = logging.getLogger("hermes.knowledge_expansion.graph_linker")


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
        """Найти связи с существующими сущностями в графе."""
        links = []

        if not self._graph:
            return links

        # Поиск по теме
        try:
            # Используем BFS для поиска связанных сущностей
            neighbors = self._graph.get_neighbors(item.topic, max_depth=2)
            for neighbor in neighbors:
                links.append({
                    "target": neighbor.get("name", ""),
                    "type": "related_to",
                    "source": "graph_search",
                    "depth": neighbor.get("depth", 1),
                })
        except Exception as e:
            log.warning("graph_link_error topic=%s error=%s", item.topic, e)

        # Связи из cross_references
        for ref in item.cross_references[:5]:  # Ограничиваем 5 ссылками
            links.append({
                "target": ref,
                "type": "cross_reference",
                "source": "enrichment",
            })

        return links
