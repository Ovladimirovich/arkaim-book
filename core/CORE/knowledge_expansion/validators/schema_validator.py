"""
Schema Validator — проверка формата и непротиворечивости знаний.
"""
import logging
from . import BaseValidator
from ..models import LinkedKnowledge, ValidatedKnowledge

log = logging.getLogger("hermes.knowledge_expansion.schema_validator")


class SchemaValidator(BaseValidator):
    """Проверяет формат, непротиворечивость и полноту знаний."""

    async def validate(self, linked: list[LinkedKnowledge]) -> list[ValidatedKnowledge]:
        """Валидировать знания."""
        results = []

        for item in linked:
            score = 1.0
            duplicates = []

            # Проверка наличия темы
            if not item.topic:
                score *= 0.5
                log.warning("missing_topic source=%s", item.source)

            # Проверка наличия контента
            if not item.content:
                score *= 0.7
                log.warning("missing_content topic=%s", item.topic)

            # Проверка наличия слоёв
            if not item.layers:
                score *= 0.8
                log.warning("missing_layers topic=%s", item.topic)

            # Проверка на дубли (упрощённая)
            # В реальной системе — сравнение с существующими знаниями

            # Проверка confidentity
            if item.confidence < 0.5:
                score *= 0.8
                log.warning("low_confidence topic=%s score=%.2f", item.topic, item.confidence)

            results.append(ValidatedKnowledge(
                source=item.source,
                topic=item.topic,
                content=item.content,
                layers=item.layers,
                cross_references=item.cross_references,
                patterns=item.patterns,
                connections=item.connections,
                graph_links=item.graph_links,
                validation_score=score,
                duplicates_found=duplicates,
                metadata=item.metadata,
                confidence=item.confidence,
            ))

        return results
