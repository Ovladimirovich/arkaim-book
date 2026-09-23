"""
Knowledge Store — сохранение знаний в JSON + обновление Knowledge Graph.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from . import BaseStore
from ..models import ValidatedKnowledge, SaveResult

log = logging.getLogger("hermes.knowledge_expansion.knowledge_store")


class KnowledgeStore(BaseStore):
    """Сохраняет знания в JSON-файлы и обновляет Knowledge Graph."""

    def __init__(self, knowledge_dir: Path = None):
        self._dir = knowledge_dir or Path("core/KNOWLEDGE")

    async def save(self, validated: list[ValidatedKnowledge], output_path: Path) -> SaveResult:
        """Сохранить знания в JSON."""
        items_saved = 0
        items_skipped = 0

        # Загрузить существующие данные
        existing = []
        if output_path.exists():
            try:
                existing = json.loads(output_path.read_text(encoding="utf-8"))
            except Exception as e:
                log.warning("load_existing_error path=%s error=%s", output_path, e)

        # Добавить новые знания
        for item in validated:
            entry = {
                "topic": item.topic,
                "content": item.content,
                "layers": item.layers,
                "cross_references": item.cross_references,
                "patterns": item.patterns,
                "connections": item.connections,
                "graph_links": item.graph_links,
                "source": item.source,
                "validation_score": item.validation_score,
                "confidence": item.confidence,
                "metadata": item.metadata,
                "added_at": datetime.now(tz=timezone.utc).isoformat(),
            }

            # Проверка на дубли (по теме)
            is_duplicate = any(
                existing_item.get("topic") == item.topic
                for existing_item in existing
            )

            if is_duplicate:
                items_skipped += 1
                log.info("duplicate_skipped topic=%s", item.topic)
            else:
                existing.append(entry)
                items_saved += 1

        # Сохранить
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        log.info("knowledge_saved path=%s saved=%d skipped=%d",
                 output_path, items_saved, items_skipped)

        # Update knowledge graph with new items
        graph_updates = 0
        try:
            from book_os.entity_store import EntityStore
            from book_os.relationship_store import RelationshipStore
            from book_os.fact_store import FactStore
            from book_os.models import Entity, Relationship, Fact

            entity_store = EntityStore()
            rel_store = RelationshipStore()
            fact_store = FactStore()

            for item in validated:
                # Add knowledge topic as entity
                entity_id = f"knowledge_{item.topic.lower().replace(' ', '_')}"
                entity = Entity(
                    id=entity_id,
                    type="knowledge_topic",
                    name=item.topic,
                    description=item.content[:500] if item.content else "",
                )
                entity_store.add(entity)
                graph_updates += 1

                # Add connections as relationships
                for conn in item.connections:
                    target_id = f"knowledge_{conn.lower().replace(' ', '_')}"
                    rel = Relationship(
                        source_id=entity_id,
                        target_id=target_id,
                        type="related_to",
                        weight=0.8,
                    )
                    rel_store.add(rel)
                    graph_updates += 1

                # Add graph links as facts
                for link in item.graph_links:
                    fact = Fact(
                        entity_id=entity_id,
                        content=link,
                        source="knowledge_expansion",
                    )
                    fact_store.add(fact)
                    graph_updates += 1

            log.info("graph_updated items=%d updates=%d", items_saved, graph_updates)
        except Exception as e:
            log.warning("graph_update_failed: %s", e)

        return SaveResult(
            success=True,
            items_saved=items_saved,
            items_skipped=items_skipped,
            output_path=str(output_path),
            graph_updates=graph_updates,
        )
