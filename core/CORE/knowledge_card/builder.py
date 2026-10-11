"""Cross-source Knowledge Card aggregation with claim-level provenance."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)

from .models import KnowledgeCard, CardClaim, SourceAggregation, CardMetadata

log = logging.getLogger("hermes.knowledge_card")

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"
_NOT_FOUND_NOTE = "Сущность не найдена ни в одной системе"

_CATEGORY_TO_LEVEL = {
    ProvenanceCategory.AUTHOR_CANON: SourceLevel.CANON,
    ProvenanceCategory.DERIVED: SourceLevel.SYSTEM_INTERPRETATION,
    ProvenanceCategory.EXTERNAL_SOURCE: SourceLevel.HISTORICAL,
    ProvenanceCategory.HYPOTHESIS: SourceLevel.USER_HYPOTHESIS,
    ProvenanceCategory.RECONSTRUCTION: SourceLevel.AUTHOR_INTERPRETATION,
}


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "_", str(value or "").strip().lower()).strip("_")
    return value or "unknown"


def _normal(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _parse_category(
    value: Any,
    default: ProvenanceCategory = ProvenanceCategory.EXTERNAL_SOURCE,
) -> ProvenanceCategory:
    text = str(value or "").strip().upper()
    try:
        return ProvenanceCategory(text)
    except ValueError:
        return default


def _tag(
    category: ProvenanceCategory,
    confidence: float = 0.7,
    *,
    source_title: str | None = None,
    notes: str | None = None,
) -> ProvenanceTag:
    return ProvenanceTag(
        source_level=_CATEGORY_TO_LEVEL[category],
        category=category,
        source_title=source_title,
        confidence=max(0.0, min(1.0, float(confidence))),
        notes=notes,
    )


class KnowledgeCardBuilder:
    """Builds a card while preserving each claim's provenance."""

    def __init__(self) -> None:
        self._world_engine: Any = None
        self._retriever: Any = None
        self._retriever_initialized = False
        self._json_cache: dict[str, tuple[float, Any]] = {}

    def _engine(self) -> Any:
        if self._world_engine is None:
            try:
                from narrative_engine.world_engine import get_world_engine

                engine = get_world_engine()
                engine.initialize()
                self._world_engine = engine
            except Exception:
                log.exception("knowledge_card_world_engine_failed")
                self._world_engine = False
        return self._world_engine or None

    def _retriever_or_none(self) -> Any:
        if not self._retriever_initialized:
            self._retriever_initialized = True
            try:
                from intelligence.retriever import BookRetriever

                self._retriever = BookRetriever()
            except Exception:
                log.exception("knowledge_card_retriever_failed")
                self._retriever = None
        return self._retriever

    @staticmethod
    def _iter_list(data: Any, *keys: str) -> Iterable[dict[str, Any]]:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item
            return
        if not isinstance(data, dict):
            return
        for key in keys:
            items = data.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        yield item

    @staticmethod
    def _root_category(data: Any, default: ProvenanceCategory) -> ProvenanceCategory:
        if isinstance(data, dict):
            metadata = data.get("_provenance_metadata")
            if isinstance(metadata, dict):
                return _parse_category(metadata.get("category"), default)
        return default

    def _load_json(self, name: str | Path) -> Any:
        path = Path(name)
        if not path.is_absolute():
            path = KNOWLEDGE_DIR / name
        if not path.is_file():
            return None
        mtime = path.stat().st_mtime
        cached = self._json_cache.get(str(path))
        if cached is not None and cached[0] == mtime:
            return cached[1]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            log.warning("knowledge_card_json_failed path=%s", path, exc_info=True)
            data = None
        self._json_cache[str(path)] = (mtime, data)
        return data

    def _resolve_entity(self, entity_id: str) -> dict[str, Any] | None:
        query = str(entity_id or "").strip()
        lower = _normal(query)
        if not lower:
            return None

        engine = self._engine()
        if engine is not None:
            try:
                direct = engine.get_entity(query)
                if isinstance(direct, dict):
                    return {
                        "id": direct.get("id", query),
                        "name": direct.get("name", query),
                        "category": direct.get("category", "world_model"),
                        "source": "world_model",
                        "entity": direct,
                    }
            except Exception:
                log.debug("knowledge_card_entity_lookup_failed entity=%s", query, exc_info=True)

            for item in self._search_engine(engine, query):
                exact_names = {_normal(item.get("id", "")), _normal(item.get("name", ""))}
                if lower in exact_names:
                    return {
                        "id": item.get("id", query),
                        "name": item.get("name", query),
                        "category": item.get("category", "world_model"),
                        "source": "world_model",
                        "entity": item,
                    }

        for site in self._iter_list(self._load_json("ARCHAEOLOGY.json"), "sites"):
            names = {
                _normal(site.get("name", "")),
                _normal(site.get("location", "")),
                _normal(site.get("id", "")),
            }
            if lower in names:
                site_id = site.get("id") or f"archaeology:{_slug(site.get('name', 'site'))}"
                return {
                    "id": site_id,
                    "name": site.get("name", query),
                    "category": "archaeology",
                    "source": "archaeology",
                    "entity": site,
                }

        for character in self._iter_list(self._load_json("CHARACTERS.json"), "characters", "items"):
            if lower in {_normal(character.get("name", "")), _normal(character.get("id", ""))}:
                character_id = character.get("id") or f"character:{_slug(character.get('name', query))}"
                return {
                    "id": character_id,
                    "name": character.get("name", query),
                    "category": character.get("role", "character"),
                    "source": "characters",
                    "entity": character,
                }

        if engine is not None:
            for item in self._search_engine(engine, query):
                haystack = _normal(f"{item.get('name', '')} {item.get('id', '')}")
                if lower in haystack:
                    return {
                        "id": item.get("id", query),
                        "name": item.get("name", query),
                        "category": item.get("category", "world_model"),
                        "source": "world_model",
                        "entity": item,
                    }

        for site in self._iter_list(self._load_json("ARCHAEOLOGY.json"), "sites"):
            site_name = _normal(site.get("name", ""))
            haystack = _normal(" ".join(str(site.get(key, "")) for key in ("name", "location", "id")))
            if lower in haystack or site_name in lower:
                site_id = site.get("id") or f"archaeology:{_slug(site.get('name', query))}"
                return {
                    "id": site_id,
                    "name": site.get("name", query),
                    "category": "archaeology",
                    "source": "archaeology",
                    "entity": site,
                }

        return None

    @staticmethod
    def _search_engine(engine: Any, query: str) -> list[dict[str, Any]]:
        try:
            raw_matches = engine.search(query)
            matches = raw_matches.get("world_model", []) if isinstance(raw_matches, dict) else raw_matches
        except Exception:
            log.debug("knowledge_card_engine_search_failed query=%s", query, exc_info=True)
            return []
        return [item for item in matches if isinstance(item, dict)] if isinstance(matches, list) else []

    @staticmethod
    def _claim(
        seen: set[str],
        claims: list[CardClaim],
        text: str,
        category: ProvenanceCategory,
        *,
        source_ref: str,
        confidence: float = 0.7,
        chunk_id: str | None = None,
        source_title: str | None = None,
        notes: str | None = None,
    ) -> None:
        normalized = _normal(text)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        claims.append(
            CardClaim(
                text=str(text).strip(),
                provenance=_tag(
                    category,
                    confidence,
                    source_title=source_title,
                    notes=notes,
                ),
                chunk_id=chunk_id,
                source_ref=source_ref,
                notes=notes or "",
            )
        )

    @staticmethod
    def _approved_rag_aliases(canonical_id: str) -> list[str]:
        """Return owner-approved canonical aliases for a World Engine ID.

        The B3 crosswalk maps canonical WorldModel locations to World Engine IDs.
        It is already the only approved identity bridge in the project, so Book
        retrieval may use its canonical target ID as an additional query without
        creating an identity or changing WorldModel data.
        """
        from narrative_engine.world_model import _load_approved_crosswalk

        entity_id = str(canonical_id or "").strip()
        if not entity_id:
            return []
        aliases = [
            str(target_id).strip()
            for target_id, world_engine_ids in _load_approved_crosswalk().items()
            if entity_id in world_engine_ids and str(target_id or "").strip()
        ]
        return list(dict.fromkeys(aliases))

    def _book_claims(self, queries: str | list[str]) -> list[CardClaim]:
        claims: list[CardClaim] = []
        seen: set[str] = set()
        retriever = self._retriever_or_none()
        if retriever is None:
            return claims
        query_terms = [queries] if isinstance(queries, str) else queries
        results: list[dict[str, Any]] = []
        for query in dict.fromkeys(str(query or "").strip() for query in query_terms if str(query or "").strip()):
            try:
                results.extend(retriever.search(query, n_results=5) or [])
            except Exception:
                log.warning("knowledge_card_book_search_failed query=%s", query, exc_info=True)
        for item in results:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            if str(item.get("source") or "") == "genome":
                continue
            chunk_id = str(item.get("chunk_id") or "") or None
            self._claim(
                seen,
                claims,
                text,
                ProvenanceCategory.AUTHOR_CANON,
                source_ref=f"book:{chunk_id or 'chunk'}",
                confidence=1.0,
                chunk_id=chunk_id,
                source_title="Наследие Аркаима",
                notes=str(item.get("chapter_title") or "").strip() or None,
            )
        return claims

    def _genome_claims(self, queries: str | list[str]) -> list[CardClaim]:
        """Project genome fallback results without treating them as book evidence."""
        claims: list[CardClaim] = []
        seen: set[str] = set()
        retriever = self._retriever_or_none()
        if retriever is None:
            return claims
        query_terms = [queries] if isinstance(queries, str) else queries
        results: list[dict[str, Any]] = []
        for query in dict.fromkeys(str(query or "").strip() for query in query_terms if str(query or "").strip()):
            try:
                results.extend(retriever.search(query, n_results=5) or [])
            except Exception:
                log.warning("knowledge_card_genome_search_failed query=%s", query, exc_info=True)
        for item in results:
            if item.get("source") != "genome":
                continue
            text = str(item.get("text", "")).strip()
            chunk_id = str(item.get("chunk_id") or "") or None
            if not text:
                continue
            theme_id = chunk_id.removeprefix("genome_theme_") if chunk_id else "unknown"
            self._claim(
                seen,
                claims,
                text,
                ProvenanceCategory.DERIVED,
                source_ref=f"genome:theme:{theme_id}",
                confidence=0.7,
                source_title="Book Genome",
                notes="Derived theme projection; not a book source fragment",
            )
        return claims

    def _world_claims(
        self,
        resolved: dict[str, Any] | None,
    ) -> tuple[list[CardClaim], list[dict[str, Any]]]:
        claims: list[CardClaim] = []
        seen: set[str] = set()
        relations: list[dict[str, Any]] = []
        if not resolved:
            return claims, relations

        entity = resolved.get("entity") if isinstance(resolved.get("entity"), dict) else {}
        entity_id = str(resolved.get("id", ""))

        for field in ("description", "summary", "meaning", "significance"):
            value = entity.get(field)
            if isinstance(value, str):
                self._claim(
                    seen,
                    claims,
                    value,
                    ProvenanceCategory.DERIVED,
                    source_ref=f"world_model:{entity_id}:{field}",
                    confidence=0.8,
                    source_title=resolved.get("name"),
                )

        facts = entity.get("facts", entity.get("attributes", {}))
        if isinstance(facts, dict):
            for key, value in facts.items():
                self._claim(
                    seen,
                    claims,
                    f"{key}: {value}",
                    ProvenanceCategory.DERIVED,
                    source_ref=f"world_model:{entity_id}:facts.{key}",
                    confidence=0.8,
                    source_title=resolved.get("name"),
                )

        engine = self._engine()
        if engine is not None:
            try:
                context = engine.get_entity_context(entity_id)
                raw_relations = context.get("relations", {}) if isinstance(context, dict) else {}
                if isinstance(raw_relations, dict):
                    for relation_type, items in raw_relations.items():
                        relations.append(
                            {
                                "type": relation_type,
                                "items": items,
                                "source_ref": f"world_model:{entity_id}:relations",
                            }
                        )
                elif isinstance(raw_relations, list):
                    relations.extend(item for item in raw_relations if isinstance(item, dict))
            except Exception:
                log.debug("knowledge_card_relations_failed entity=%s", entity_id, exc_info=True)

        return claims, relations

    def _archaeology_claims(
        self,
        resolved: dict[str, Any] | None,
        queries: str | list[str],
    ) -> list[CardClaim]:
        claims: list[CardClaim] = []
        seen: set[str] = set()
        terms = {
            _normal(query)
            for query in ([queries] if isinstance(queries, str) else queries)
            if _normal(query)
        }
        resolved_name = _normal((resolved or {}).get("name", ""))

        for root_name in ("ARCHAEOLOGY.json", "ARCHAEOLOGY_DEEP.json"):
            data = self._load_json(root_name)
            for site in self._iter_list(data, "sites"):
                resolved_match = bool(resolved_name and _normal(site.get("name", "")) == resolved_name)
                haystack = _normal(" ".join(str(site.get(key, "")) for key in ("name", "location", "id")))
                site_name = _normal(site.get("name", ""))
                if not resolved_match and not any(term in haystack or site_name in term for term in terms):
                    continue

                site_id = str(site.get("id") or _slug(site.get("name", "site")))
                base = f"{root_name}:{site_id}"
                default_category = _parse_category(
                    site.get("facts_provenance"),
                    ProvenanceCategory.EXTERNAL_SOURCE,
                )

                for field in ("location", "dating"):
                    if site.get(field):
                        self._claim(
                            seen,
                            claims,
                            site[field],
                            default_category,
                            source_ref=f"{base}:{field}",
                            confidence=0.8,
                            source_title=site.get("name"),
                        )

                facts = site.get("facts", {})
                if isinstance(facts, dict):
                    for key, value in facts.items():
                        if isinstance(value, (list, tuple, set)):
                            value = ", ".join(str(item) for item in value)
                        self._claim(
                            seen,
                            claims,
                            f"{key}: {value}",
                            default_category,
                            source_ref=f"{base}:facts.{key}",
                            confidence=0.8,
                            source_title=site.get("name"),
                        )

                connection = site.get("book_connection")
                if isinstance(connection, dict) and connection.get("text"):
                    self._claim(
                        seen,
                        claims,
                        connection["text"],
                        _parse_category(
                            connection.get("provenance"),
                            ProvenanceCategory.RECONSTRUCTION,
                        ),
                        source_ref=f"{base}:book_connection",
                        confidence=0.7,
                        source_title=site.get("name"),
                        notes=connection.get("notes"),
                    )

                for index, hypothesis in enumerate(site.get("hypothetical_claims", [])):
                    if not isinstance(hypothesis, dict):
                        continue
                    self._claim(
                        seen,
                        claims,
                        hypothesis.get("text", ""),
                        _parse_category(
                            hypothesis.get("provenance"),
                            ProvenanceCategory.HYPOTHESIS,
                        ),
                        source_ref=f"{base}:hypothetical.{index}",
                        confidence=0.5,
                        source_title=site.get("name"),
                        notes=hypothesis.get("notes"),
                    )

                significance = site.get("significance")
                if isinstance(significance, dict):
                    self._claim(
                        seen,
                        claims,
                        significance.get("text", ""),
                        _parse_category(
                            significance.get("provenance"),
                            ProvenanceCategory.EXTERNAL_SOURCE,
                        ),
                        source_ref=f"{base}:significance",
                        confidence=0.8,
                        source_title=site.get("name"),
                        notes=significance.get("notes"),
                    )

        return claims

    def _cross_reference_claims(self, queries: str | list[str]) -> list[CardClaim]:
        claims: list[CardClaim] = []
        seen: set[str] = set()
        terms = {
            _normal(query)
            for query in ([queries] if isinstance(queries, str) else queries)
            if _normal(query)
        }
        for root_name in ("CROSS_REFERENCES.json", "CROSS_REFERENCES_DEEP.json"):
            data = self._load_json(root_name)
            default_category = self._root_category(data, ProvenanceCategory.DERIVED)
            for index, reference in enumerate(self._iter_list(data, "references", "cross_references")):
                haystack = _normal(
                    " ".join(str(reference.get(key, "")) for key in ("theme", "book_context", "significance"))
                )
                if not any(term in haystack for term in terms):
                    continue
                theme = str(reference.get("theme", f"reference_{index}"))
                base = f"{root_name}:{_slug(theme)}"
                self._claim(
                    seen,
                    claims,
                    reference.get("book_context", ""),
                    default_category,
                    source_ref=f"{base}:book_context",
                    confidence=0.75,
                    source_title=theme,
                )
                for parallel_index, parallel in enumerate(reference.get("parallels", [])):
                    if not isinstance(parallel, dict):
                        continue
                    self._claim(
                        seen,
                        claims,
                        f"{parallel.get('culture', 'Культура')} — {parallel.get('source', '')}: {parallel.get('detail', '')}",
                        default_category,
                        source_ref=f"{base}:parallel.{parallel_index}",
                        confidence=0.7,
                        source_title=theme,
                    )
        return claims

    def _academic_claims(self, queries: str | list[str]) -> list[CardClaim]:
        claims: list[CardClaim] = []
        seen: set[str] = set()
        terms = {
            _normal(query)
            for query in ([queries] if isinstance(queries, str) else queries)
            if _normal(query)
        }
        data = self._load_json("ACADEMIC_CONFIRMATIONS.json")
        default_category = self._root_category(data, ProvenanceCategory.EXTERNAL_SOURCE)
        for index, confirmation in enumerate(self._iter_list(data, "confirmations")):
            haystack = _normal(
                " ".join(str(confirmation.get(key, "")) for key in ("category", "book_theme"))
            )
            if not any(term in haystack for term in terms):
                continue
            title = str(confirmation.get("category", f"academic_{index}"))
            base = f"ACADEMIC_CONFIRMATIONS.json:{_slug(title)}"
            for source_index, source in enumerate(confirmation.get("academic_sources", [])):
                if not isinstance(source, dict):
                    continue
                self._claim(
                    seen,
                    claims,
                    f"{source.get('culture', 'Источник')}: {source.get('text', '')}",
                    default_category,
                    source_ref=f"{base}:source.{source_index}",
                    confidence=0.75,
                    source_title=title,
                )
        return claims

    @staticmethod
    def _source(
        name: str,
        category: ProvenanceCategory,
        claims: list[CardClaim],
        summary: str,
        confidence: float,
    ) -> SourceAggregation:
        return SourceAggregation(
            source_name=name,
            provenance_category=category,
            claim_count=len(claims),
            summary=summary,
            confidence=round(confidence, 4),
            claims=claims,
        )

    def _unknown_aspects(
        self,
        resolved: dict[str, Any] | None,
        resolved_entity: dict[str, Any] | None,
        book_claims: list[CardClaim],
        archaeology_claims: list[CardClaim],
    ) -> list[str]:
        unknowns: list[str] = []
        if resolved is None:
            unknowns.append("Сущность не найдена ни в одном структурном источнике")
        if not book_claims:
            unknowns.append("Нет подтверждений из текста книги")
        if not archaeology_claims:
            unknowns.append("Нет подтверждений из археологических источников")
        if isinstance(resolved_entity, dict):
            unknowns.extend(
                aspect for aspect in resolved_entity.get("unsolved", []) if isinstance(aspect, str)
            )
        return unknowns

    @staticmethod
    def _related_entities(relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        related: list[dict[str, Any]] = []
        for relation in relations:
            items = relation.get("items", [])
            relation_type = str(relation.get("type", ""))
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                target = item.get("target") or item.get("id") or item.get("name")
                if target:
                    related.append({"entity_id": str(target), "relation": relation_type})
        return related[:20]

    def build(self, entity_id: str) -> KnowledgeCard:
        query = str(entity_id or "").strip()
        resolved = self._resolve_entity(query)
        resolved_name = resolved.get("name", query) if resolved else query
        resolved_entity = resolved.get("entity", {}) if resolved else {}
        canonical_id = resolved.get("id", query) if resolved else query

        knowledge_queries = list(
            dict.fromkeys(
                term
                for term in (
                    *self._approved_rag_aliases(canonical_id),
                    resolved_name,
                    query,
                )
                if str(term or "").strip()
            )
        )
        book_claims = self._book_claims(knowledge_queries)
        genome_claims = self._genome_claims(knowledge_queries)
        world_claims, relations = self._world_claims(resolved)
        archaeology_claims = self._archaeology_claims(resolved, knowledge_queries)
        cross_claims = self._cross_reference_claims(knowledge_queries)
        academic_claims = self._academic_claims(knowledge_queries)

        sources = [
            self._source(
                "book",
                ProvenanceCategory.AUTHOR_CANON,
                book_claims,
                f"{len(book_claims)} утверждений из текста книги",
                1.0 if book_claims else 0.0,
            ),
            self._source(
                "genome",
                ProvenanceCategory.DERIVED,
                genome_claims,
                f"{len(genome_claims)} derived genome theme projections",
                0.7 if genome_claims else 0.0,
            ),
            self._source(
                "world_model",
                ProvenanceCategory.DERIVED,
                world_claims,
                f"{len(world_claims)} утверждений модели мира",
                0.8 if world_claims else 0.0,
            ),
            self._source(
                "archaeology",
                ProvenanceCategory.EXTERNAL_SOURCE,
                archaeology_claims,
                f"{len(archaeology_claims)} утверждений археологии",
                0.8 if archaeology_claims else 0.0,
            ),
            self._source(
                "cross_references",
                ProvenanceCategory.DERIVED,
                cross_claims,
                f"{len(cross_claims)} кросс-культурных связей",
                0.75 if cross_claims else 0.0,
            ),
            self._source(
                "academic",
                ProvenanceCategory.EXTERNAL_SOURCE,
                academic_claims,
                f"{len(academic_claims)} академических подтверждений",
                0.75 if academic_claims else 0.0,
            ),
        ]

        unknowns = self._unknown_aspects(
            resolved,
            resolved_entity,
            book_claims,
            archaeology_claims,
        )
        metadata = CardMetadata(
            entity_id=query,
            entity_name=resolved_name,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            coverage_note=(
                _NOT_FOUND_NOTE
                if resolved is None
                else "Карточка собрана из доступных источников"
            ),
        )
        primary_entity = dict(resolved_entity) if isinstance(resolved_entity, dict) else None
        if primary_entity:
            primary_entity["resolved_id"] = canonical_id

        card = KnowledgeCard(
            metadata=metadata,
            primary_entity=primary_entity,
            sources=sources,
            relations=relations,
            contradictions=[],
            uncertainty={
                "has_unknowns": bool(unknowns),
                "unknown_aspects": unknowns,
            },
            search_suggestions=[],
            related_entities=self._related_entities(relations),
        )
        log.info(
            "card_built entity=%s canonical_id=%s claims=%d",
            query,
            canonical_id,
            sum(source.claim_count for source in card.sources),
        )
        return card


_builder: KnowledgeCardBuilder | None = None


def get_card_builder() -> KnowledgeCardBuilder:
    global _builder
    if _builder is None:
        _builder = KnowledgeCardBuilder()
    return _builder