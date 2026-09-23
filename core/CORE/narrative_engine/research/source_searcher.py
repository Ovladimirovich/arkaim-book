"""Source Searcher — поиск внешних источников по сущностям."""

import logging
from typing import Optional
from pydantic import BaseModel, Field

log = logging.getLogger("hermes.narrative.source_searcher")


class ExternalSource(BaseModel):
    title: str
    url: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    relevance_score: float = 0.5
    snippet: str = ""
    source_type: str = "web"  # web, academic, archaeological, mythological


# Source databases for different entity types
SOURCE_DATABASES = {
    "location": [
        {"title": "Археологические исследования", "source_type": "archaeological"},
        {"title": "Исторические карты", "source_type": "historical"},
        {"title": "Географические описания", "source_type": "geographical"},
    ],
    "character": [
        {"title": "Мифологические параллели", "source_type": "mythological"},
        {"title": "Исторические источники", "source_type": "historical"},
    ],
    "concept": [
        {"title": "Философские исследования", "source_type": "academic"},
        {"title": "Религиозные тексты", "source_type": "mythological"},
    ],
    "technology": [
        {"title": "Археологические находки", "source_type": "archaeological"},
        {"title": "Научные публикации", "source_type": "academic"},
    ],
}


def search_sources(entity_name: str, entity_type: str = "concept") -> list[ExternalSource]:
    """Поиск внешних источников по сущности (rule-based)."""
    sources = []
    db = SOURCE_DATABASES.get(entity_type, [])

    for item in db:
        sources.append(ExternalSource(
            title=f"{item['title']}: {entity_name}",
            url=None,
            authors=["Системный анализ"],
            year=None,
            relevance_score=0.6,
            snippet=f"Информация о {entity_name} в контексте {item['source_type']}.",
            source_type=item["source_type"],
        ))

    return sources


async def search_sources_llm(entity_name: str, entity_type: str = "concept") -> list[ExternalSource]:
    """Поиск источников через LLM (fallback на rule-based)."""
    try:
        from providers.registry import ProviderRegistry

        search_prompt = f"""Найди реальные источники информации о сущности "{entity_name}" (тип: {entity_type}).

Для каждого источника укажи:
- title: название
- url: URL если есть (или null)
- authors: авторы
- year: год публикации (или null)
- snippet: краткое описание (50-100 слов)
- source_type: archaeological/academic/mythological/historical

Верни JSON-массив объектов. Максимум 5 источников."""

        provider = ProviderRegistry.get("gigachat") or ProviderRegistry.get("openrouter")
        if not provider:
            return search_sources(entity_name, entity_type)

        messages = [{"role": "user", "content": search_prompt}]
        response = ""
        async for token in provider.stream(messages):
            if token and not token.startswith("data:"):
                response += token

        import json
        import re
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if match:
            items = json.loads(match.group())
            sources = []
            for item in items:
                sources.append(ExternalSource(
                    title=item.get("title", f"Источник: {entity_name}"),
                    url=item.get("url"),
                    authors=item.get("authors", []),
                    year=item.get("year"),
                    relevance_score=0.7,
                    snippet=item.get("snippet", ""),
                    source_type=item.get("source_type", "web"),
                ))
            return sources

    except Exception as e:
        log.warning("llm_source_search_failed entity=%s error=%s", entity_name, e)

    return search_sources(entity_name, entity_type)
