"""
Knowledge Expansion Pipeline — инфраструктура расширения знаний книги.

Единый пайплайн для обогащения ядра знаний:
Источник → Извлечение → LLM-анализ → Проверка → Связывание → Хранение

Использование:
    from knowledge_expansion import KnowledgeExpansionPipeline
    pipeline = KnowledgeExpansionPipeline()
    await pipeline.run_module("philosophy_deep")
"""
from .pipeline import KnowledgeExpansionPipeline
from .models import RawKnowledge, EnrichedKnowledge, LinkedKnowledge, ValidatedKnowledge

__all__ = [
    "KnowledgeExpansionPipeline",
    "RawKnowledge",
    "EnrichedKnowledge",
    "LinkedKnowledge",
    "ValidatedKnowledge",
]
