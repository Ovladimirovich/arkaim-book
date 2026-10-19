"""External Sources — поиск во внешних источниках (Wikipedia, Semantic Scholar, OpenAlex).

Реализует архитектура World Explorer: Этап 10 — Внешние источники.

M1: все результаты автоматически маркируются как EXTERNAL_SOURCE.
Внешние данные НЕ могут автоматически стать AUTHOR_CANON.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)

log = logging.getLogger("hermes.narrative.external_sources")


class ExternalSourceResult(BaseModel):
    """Результат поиска во внешнем источнике."""

    title: str
    url: Optional[str] = None
    snippet: str = ""
    source_type: str  # wikipedia, semantic_scholar, openalex
    relevance_score: float = 0.5
    year: Optional[int] = None
    authors: list[str] = Field(default_factory=list)
    provenance: ProvenanceTag = Field(
        default_factory=lambda: ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=0.7,
            notes="external_source_auto_tagged",
        )
    )
    """M1: каждый внешний источник автоматически получает EXTERNAL_SOURCE category."""


# ── Wikipedia API ──────────────────────────────────────────


async def search_wikipedia(query: str, limit: int = 5) -> list[ExternalSourceResult]:
    """Поиск в Wikipedia API (бесплатно, без ключа)."""
    try:
        import aiohttp

        url = f"https://ru.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        ExternalSourceResult(
                            title=data.get("title", query),
                            url=data.get("content_urls", {})
                            .get("desktop", {})
                            .get("page"),
                            snippet=data.get("extract", "")[:500],
                            source_type="wikipedia",
                            relevance_score=0.8,
                        )
                    ]
    except Exception as e:
        log.debug("wikipedia_search_failed query=%s error=%s", query, e)

    # Fallback: поиск через Wikipedia search API
    try:
        import aiohttp

        search_url = f"https://ru.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(query)}&format=json&srlimit={limit}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                search_url, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for item in data.get("query", {}).get("search", [])[:limit]:
                        results.append(
                            ExternalSourceResult(
                                title=item.get("title", ""),
                                url=f"https://ru.wikipedia.org/wiki/{quote(item.get('title', ''))}",
                                snippet=item.get("snippet", "")[:500],
                                source_type="wikipedia",
                                relevance_score=0.7,
                            )
                        )
                    return results
    except Exception as e:
        log.debug("wikipedia_search_failed query=%s error=%s", query, e)

    return []


# ── Provenance helpers ─────────────────────────────────────


def tag_as_external(
    title: str,
    url: Optional[str] = None,
    snippet: str = "",
    source_type: str = "external",
    relevance_score: float = 0.7,
    year: Optional[int] = None,
    authors: Optional[list[str]] = None,
) -> ExternalSourceResult:
    """Создать ExternalSourceResult с автоматической EXTERNAL_SOURCE маркировкой."""
    provenance = ProvenanceTag(
        source_level=SourceLevel.HISTORICAL,
        category=ProvenanceCategory.EXTERNAL_SOURCE,
        source_url=url,
        source_title=title,
        confidence=relevance_score,
        notes=f"external_source:{source_type}",
    )
    return ExternalSourceResult(
        title=title,
        url=url,
        snippet=snippet,
        source_type=source_type,
        relevance_score=relevance_score,
        year=year,
        authors=authors or [],
        provenance=provenance,
    )


def external_result_is_canon(result: ExternalSourceResult) -> bool:
    """Внешний результат НИКОГДА не может быть каноническим."""
    return False


def classify_external_result(result: ExternalSourceResult) -> ProvenanceCategory:
    """Классифицировать результат — всегда EXTERNAL_SOURCE."""
    return ProvenanceCategory.EXTERNAL_SOURCE


# ── Wikipedia API ──────────────────────────────────────────


async def search_semantic_scholar(
    query: str, limit: int = 5
) -> list[ExternalSourceResult]:
    """Поиск в Semantic Scholar API (бесплатно, rate-limit 100 req/5min)."""
    try:
        import aiohttp

        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}&limit={limit}&fields=title,abstract,year,authors,url"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for paper in data.get("data", [])[:limit]:
                        authors = [
                            a.get("name", "") for a in paper.get("authors", [])[:3]
                        ]
                        results.append(
                            ExternalSourceResult(
                                title=paper.get("title", ""),
                                url=paper.get("url"),
                                snippet=(paper.get("abstract") or "")[:500],
                                source_type="semantic_scholar",
                                relevance_score=0.75,
                                year=paper.get("year"),
                                authors=authors,
                            )
                        )
                    return results
    except Exception as e:
        log.debug("semantic_scholar_search_failed query=%s error=%s", query, e)

    return []


# ── OpenAlex API ───────────────────────────────────────────


async def search_openalex(query: str, limit: int = 5) -> list[ExternalSourceResult]:
    """Поиск в OpenAlex API (бесплатно, без ключа)."""
    try:
        import aiohttp

        url = f"https://api.openalex.org/works?search={quote(query)}&per_page={limit}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for work in data.get("results", [])[:limit]:
                        title = work.get("title", "")
                        # OpenAlex sometimes returns null title
                        if not title:
                            continue
                        results.append(
                            ExternalSourceResult(
                                title=title,
                                url=work.get("id"),
                                snippet=(work.get("abstract_inverted_index") or {})
                                and "",
                                source_type="openalex",
                                relevance_score=0.7,
                                year=work.get("publication_year"),
                            )
                        )
                    return results
    except Exception as e:
        log.debug("openalex_search_failed query=%s error=%s", query, e)

    return []


# ── Единый интерфейс ──────────────────────────────────────


async def search_all_sources(
    query: str,
    limit_per_source: int = 3,
    sources: Optional[list[str]] = None,
) -> list[ExternalSourceResult]:
    """Поиск во всех внешних источниках параллельно.

    Args:
        query: Поисковый запрос
        limit_per_source: Максимум результатов с одного источника
        sources: Список источников для поиска (None = все)
    """
    all_sources = sources or ["wikipedia", "semantic_scholar", "openalex"]

    tasks = []
    if "wikipedia" in all_sources:
        tasks.append(search_wikipedia(query, limit_per_source))
    if "semantic_scholar" in all_sources:
        tasks.append(search_semantic_scholar(query, limit_per_source))
    if "openalex" in all_sources:
        tasks.append(search_openalex(query, limit_per_source))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Собираем результаты, исключая исключения
    all_results = []
    for result in results:
        if isinstance(result, list):
            all_results.extend(result)
        elif isinstance(result, Exception):
            log.warning("source_search_error error=%s", result)

    # Сортируем по relevance_score
    all_results.sort(key=lambda r: r.relevance_score, reverse=True)

    return all_results


def search_local_knowledge(
    query: str,
    knowledge_dir: Optional[Path] = None,
    limit: int = 5,
) -> list[ExternalSourceResult]:
    """Поиск в локальных KNOWLEDGE файлах."""

    if knowledge_dir is None:
        knowledge_dir = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"

    results = []
    query_lower = query.lower()

    # Ищем в ключевых файлах
    key_files = [
        "ARCHAEOLOGY.json",
        "CROSS_REFERENCES.json",
        "ESOTERIC_CONNECTIONS.json",
        "HIERARCHY_OF_LIGHT.json",
        "ACADEMIC_CONFIRMATIONS.json",
        "COSMOLOGY.json",
    ]

    for filename in key_files:
        filepath = knowledge_dir / filename
        if not filepath.exists():
            continue

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            # Ищем совпадения по ключевым словам
            data_str = json.dumps(data, ensure_ascii=False).lower()
            if any(word in data_str for word in query_lower.split() if len(word) > 3):
                # Извлекаем релевантные фрагменты
                snippets = _extract_snippets(data, query_lower, max_snippets=2)
                for snippet in snippets:
                    results.append(
                        ExternalSourceResult(
                            title=f"{filename}: {query}",
                            snippet=snippet,
                            source_type="local_knowledge",
                            relevance_score=0.6,
                            provenance=ProvenanceTag(
                                source_level=SourceLevel.CANON,
                                category=ProvenanceCategory.AUTHOR_CANON,
                                confidence=0.85,
                                notes=f"local_knowledge:{filename}",
                            ),
                        )
                    )
        except Exception:
            continue

    return results[:limit]


def _extract_snippets(data: dict, query: str, max_snippets: int = 2) -> list[str]:
    """Извлечь релевантные фрагменты из JSON данных."""
    snippets = []
    data_str = json.dumps(data, ensure_ascii=False)

    # Простой поиск по предложениям
    sentences = data_str.replace("\\n", " ").split(". ")
    for sentence in sentences:
        if any(word in sentence.lower() for word in query.split() if len(word) > 3):
            clean = sentence.strip().strip('"').strip("'")
            if len(clean) > 20 and len(snippets) < max_snippets:
                snippets.append(clean[:300])

    return snippets
