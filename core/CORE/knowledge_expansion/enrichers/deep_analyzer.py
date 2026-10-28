"""
Deep Analyzer — углублённый анализ тем через LLM.
"""

import json
import logging
from typing import Optional

from . import BaseEnricher
from ..models import RawKnowledge, EnrichedKnowledge

log = logging.getLogger("hermes.knowledge_expansion.deep_analyzer")

# Промпт для глубокого анализа
ANALYSIS_PROMPT = """Проанализируй тему из книги «Наследие Аркаима» и раскрой её на трёх уровнях.

Тема: {topic}
Исходное описание: {content}

Существующие связи: {cross_references}

Верни JSON с полями:
- layers: {{"literal": "буквальный смысл", "metaphorical": "метафорический смысл", "cosmic": "космический смысл"}}
- cross_references: ["связи с другими темами"]
- patterns: ["обнаруженные паттерны"]
- connections: [{{"target": "целевая тема", "type": "тип связи", "description": "описание"}}]

Будь глубоким, но точным. Опираться на текст книги."""


class DeepAnalyzer(BaseEnricher):
    """Углублённый анализ тем через LLM."""

    #: Provenance LLM-кандидата: не канон, не факт книги — системная
    #: интерпретация, которая обязана пройти проверку автора.
    LLM_PROVENANCE = {
        "category": "DERIVED",
        "provenance_category": "SYSTEM_INTERPRETATION",
        "source_level": "SYSTEM_INTERPRETATION",
        "source": "LLM",
        "requires_author_review": True,
        "status": "PENDING_REVIEW",
        "notes": "LLM deep analysis; авторская проверка обязательна",
    }

    def __init__(self, llm_client=None):
        self._llm = llm_client

    async def enrich(self, raw: list[RawKnowledge]) -> list[EnrichedKnowledge]:
        """Обогатить знания через глубокий анализ."""
        results = []

        for item in raw:
            try:
                enriched = await self._analyze_item(item)
                results.append(enriched)
            except Exception as e:
                log.error("enrich_error topic=%s error=%s", item.topic, e)
                # Возвращаем оригинал без обогащения
                results.append(
                    EnrichedKnowledge(
                        source=item.source,
                        topic=item.topic,
                        content=item.content,
                        metadata=item.metadata,
                        confidence=item.confidence,
                    )
                )

        return results

    async def _analyze_item(self, item: RawKnowledge) -> EnrichedKnowledge:
        """Проанализировать один элемент."""
        used_llm = False
        if self._llm:
            # Используем LLM для анализа
            prompt = ANALYSIS_PROMPT.format(
                topic=item.topic,
                content=item.content[:500],
                cross_references=item.metadata.get("cross_references", []),
            )
            response = await self._llm.generate(prompt)
            if isinstance(response, str) and response.strip():
                analysis = self._parse_response(response)
                used_llm = True
            else:
                # Пустой ответ LLM — не выдаём его за LLM-анализ.
                log.warning("llm_empty_response topic=%s", item.topic)
                analysis = self._basic_analysis(item)
        else:
            # Без LLM — базовый анализ
            analysis = self._basic_analysis(item)

        if not isinstance(analysis, dict):
            log.warning("llm_response_not_object topic=%s", item.topic)
            analysis = self._basic_analysis(item)
            used_llm = False

        metadata = dict(item.metadata)
        if used_llm:
            metadata["_provenance_metadata"] = dict(self.LLM_PROVENANCE)

        return EnrichedKnowledge(
            source=item.source,
            topic=item.topic,
            content=item.content,
            layers=analysis.get("layers", {}),
            cross_references=analysis.get("cross_references", []),
            patterns=analysis.get("patterns", []),
            connections=analysis.get("connections", []),
            metadata=metadata,
            confidence=item.confidence,
        )

    def _basic_analysis(self, item: RawKnowledge) -> dict:
        """Базовый анализ без LLM."""
        layers = item.metadata.get("layers", {})
        if not layers:
            layers = {
                "literal": item.content[:200] if item.content else "",
                "metaphorical": "",
                "cosmic": "",
            }

        return {
            "layers": layers,
            "cross_references": item.metadata.get("cross_references", []),
            "patterns": [],
            "connections": [],
        }

    def _parse_response(self, response: str) -> dict:
        """Парсинг ответа LLM."""
        try:
            # Попробовать найти JSON в ответе
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        # Fallback — вернуть базовую структуру
        return {
            "layers": {"literal": response[:500]},
            "cross_references": [],
            "patterns": [],
            "connections": [],
        }
