"""
KnowledgeCardBuilder вЂ” aggregates knowledge about an entity from multiple sources.

Sources (in priority order):
1. WorldEngine (canonical entity model)
2. BookRetriever (author canon from РљРќРР“Рђ.md)
3. ARCHAEOLOGY.json (external archaeological data)
4. CROSS_REFERENCES.json (cultural parallels)
5. ACADEMIC_CONFIRMATIONS.json (academic confirmations)

Provenance rules:
- Book text в†’ AUTHOR_CANON
- Archaeology facts в†’ EXTERNAL_SOURCE
- Author hypotheses в†’ HYPOTHESIS
- Reconstruction links в†’ RECONSTRUCTION
- Academic parallels в†’ DERIVED
- Cross-reference parallels в†’ DERIVED
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import config
from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)
from pulse.layers import UncertaintyFlag

from .models import (
    KnowledgeCard,
    CardClaim,
    SourceAggregation,
    ContradictionNote,
    CardMetadata,
)

log = logging.getLogger("hermes.knowledge_card")

# Paths to knowledge sources
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "KNOWLEDGE"
ARCHAEOLOGY_PATH = KNOWLEDGE_DIR / "ARCHAEOLOGY.json"
CROSS_REFS_PATH = KNOWLEDGE_DIR / "CROSS_REFERENCES.json"
ACADEMIC_PATH = KNOWLEDGE_DIR / "ACADEMIC_CONFIRMATIONS.json"


class KnowledgeCardBuilder:
    """РЎРѕР±РёСЂР°РµС‚ Knowledge Card РёР· РЅРµСЃРєРѕР»СЊРєРёС… РёСЃС‚РѕС‡РЅРёРєРѕРІ."""

    def __init__(self):
        self._world_engine = None
        self._retriever = None

    def _get_world_engine(self):
        if self._world_engine is None:
            from narrative_engine.world_engine import get_world_engine
            self._world_engine = get_world_engine()
        return self._world_engine

    def _get_retriever(self):
        if self._retriever is None:
            from intelligence.retriever import BookRetriever
            self._retriever = BookRetriever()
        return self._retriever

    # в”Ђв”Ђ Entry point в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def build(self, entity_id: str) -> KnowledgeCard:
        """
        РЎРѕР±СЂР°С‚СЊ РєР°СЂС‚РѕС‡РєСѓ РґР»СЏ СЃСѓС‰РЅРѕСЃС‚Рё.

        Steps:
        1. Find entity in WorldEngine
        2. Aggregate from all sources
        3. Detect contradictions
        4. Compute uncertainty
        """
        metadata = CardMetadata(
            entity_id=entity_id,
            entity_name=entity_id,  # Will be updated if found
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        card = KnowledgeCard(metadata=metadata)

        # Step 1: Lookup entity
        entity_data = self._resolve_entity(entity_id)
        if not entity_data:
            # Entity not found in any system вЂ” return minimal card
            card.metadata.coverage_note = "РЎСѓС‰РЅРѕСЃС‚СЊ РЅРµ РЅР°Р№РґРµРЅР° РЅРё РІ РѕРґРЅРѕР№ СЃРёСЃС‚РµРјРµ"
            return card

        card.metadata.entity_name = entity_data.get("name", entity_id)
        card.primary_entity = entity_data

        # Step 2: Aggregate from sources
        card.sources = self._aggregate_sources(entity_id, entity_data)

        # Step 3: Relations
        card.relations = self._get_relations(entity_id)

        # Step 4: Contradictions
        card.contradictions = self._detect_contradictions(card.sources)

        # Step 5: Uncertainty
        card.uncertainty = self._compute_uncertainty(card.sources)

        # Step 6: Search suggestions
        card.search_suggestions = self._suggestions(entity_id, card.sources)

        # Step 7: Related entities
        card.related_entities = self._related_entities(entity_id)

        log.info(
            "card_built entity=%s sources=%d contradictions=%d",
            entity_id, len(card.sources), len(card.contradictions),
        )
        return card

    # в”Ђв”Ђ Entity Resolution в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _resolve_entity(self, entity_id: str) -> Optional[dict]:
        """
        Resolve entity across systems.

        Priority:
        1. WorldEngine by ID
        2. WorldEngine by search (name match)
        3. ARCHAEOLOGY.json by name
        """
        # 1. Direct lookup
        engine = self._get_world_engine()
        entity = engine.get_entity(entity_id)
        if entity:
            return entity

        # 2. Search by name
        search_result = engine.search(entity_id)
        results = search_result.get("world_model", []) if isinstance(search_result, dict) else search_result
        if results:
            best = results[0]
            return {
                "id": best.get("id", entity_id),
                "name": best.get("name", entity_id),
                "category": best.get("category", "unknown"),
                "source": "world_engine_search",
                **best,
            }

        # 3. Try ARCHAEOLOGY.json by name
        archaeology = self._load_json(ARCHAEOLOGY_PATH)
        if archaeology:
            sites = archaeology.get("sites", [])
            for site in sites:
                if site.get("name", "").lower() == entity_id.lower() or \
                   entity_id.lower() in site.get("name", "").lower():
                    return {
                        "id": f"archaeology:{site.get('name', '')}",
                        "name": site.get("name", entity_id),
                        "category": "archaeology",
                        "source": "archaeology",
                        **site,
                    }

        # 4. Try CROSS_REFERENCES.json
        cross_refs = self._load_json(CROSS_REFS_PATH)
        if cross_refs:
            refs = cross_refs.get("references", [])
            for ref in refs:
                theme = ref.get("theme", "").lower()
                if entity_id.lower() in theme:
                    return {
                        "id": f"crossref:{theme}",
                        "name": ref.get("theme", entity_id),
                        "category": "cross_reference",
                        "source": "cross_references",
                        **ref,
                    }

        return None

    # в”Ђв”Ђ Source Aggregation в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _aggregate_sources(
        self, entity_id: str, entity_data: dict
    ) -> list[SourceAggregation]:
        sources = []

        # Source 1: Book (author canon via RAG)
        book_agg = self._aggregate_book(entity_id, entity_data)
        sources.append(book_agg)

        # Source 2: Archaeology
        arch_agg = self._aggregate_archaeology(entity_id, entity_data)
        sources.append(arch_agg)

        # Source 3: Cross-references
        cr_agg = self._aggregate_cross_references(entity_id, entity_data)
        sources.append(cr_agg)

        # Source 4: Academic confirmations
        acad_agg = self._aggregate_academic(entity_id, entity_data)
        sources.append(acad_agg)

        return sources

    def _aggregate_book(self, entity_id: str, entity_data: dict) -> SourceAggregation:
        """Book claims via BookRetriever."""
        try:
            retriever = self._get_retriever()
            results = retriever.search(entity_id, n_results=5)

            claims = []
            for r in results[:3]:
                chunk_id = r.get("chunk_id", "")
                # AUTHOR_CANON claims always have confidence=1.0 regardless of RAG score
                prov = ProvenanceTag(
                    source_level=SourceLevel.CANON,
                    category=ProvenanceCategory.AUTHOR_CANON,
                    confidence=1.0,
                    notes=f"book retrieval: {r.get('source', 'book')}",
                )
                claims.append(CardClaim(
                    text=r.get("text", "")[:500],
                    provenance=prov,
                    source_ref=f"book:chunk_{chunk_id}",
                    chunk_id=chunk_id,
                    chapter_title=r.get("chapter_title", ""),
                ))

            return SourceAggregation(
                source_name="book",
                provenance_category=ProvenanceCategory.AUTHOR_CANON,
                claim_count=len(claims),
                claims=claims,
                summary=f"РљРЅРёРіР°: {len(claims)} СѓС‚РІРµСЂР¶РґРµРЅРёР№",
                confidence=0.9 if claims else 0.0,
            )
        except Exception as e:
            log.warning("book_aggregation_failed entity=%s error=%s", entity_id, e)
            return SourceAggregation(
                source_name="book",
                provenance_category=ProvenanceCategory.AUTHOR_CANON,
                claim_count=0,
                summary="РћС€РёР±РєР° Р°РіСЂРµРіР°С†РёРё РєРЅРёР¶РЅС‹С… РґР°РЅРЅС‹С…",
                confidence=0.0,
            )

    def _aggregate_archaeology(
        self, entity_id: str, entity_data: dict
    ) -> SourceAggregation:
        """Archaeology data from ARCHAEOLOGY.json."""
        data = self._load_json(ARCHAEOLOGY_PATH)
        if not data:
            return SourceAggregation(
                source_name="archaeology",
                provenance_category=ProvenanceCategory.EXTERNAL_SOURCE,
                claim_count=0,
                summary="РђСЂС…РµРѕР»РѕРіРёС‡РµСЃРєРёРµ РґР°РЅРЅС‹Рµ РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚",
            )

        sites = data.get("sites", [])
        claims = []
        raw_refs = []

        for site in sites:
            name = site.get("name", "").lower()
            if entity_id.lower() in name or name in entity_id.lower():
                raw_refs.append(site)

                # Facts
                facts = site.get("facts", {})
                for k, v in facts.items():
                    prov = ProvenanceTag(
                        source_level=SourceLevel.HISTORICAL,
                        category=ProvenanceCategory.EXTERNAL_SOURCE,
                        confidence=0.8,
                        notes=f"archaeology fact: {k}",
                    )
                    claims.append(CardClaim(
                        text=f"{k}: {v}",
                        provenance=prov,
                        source_ref=f"archaeology:sites[{len(claims)}]",
                        notes=f"Р¤Р°РєС‚ РёР· {site.get('name', '')}",
                    ))

                # Book connection (RECONSTRUCTION)
                book_conn = site.get("book_connection", {})
                if book_conn:
                    prov = ProvenanceTag(
                        source_level=SourceLevel.AUTHOR_INTERPRETATION,
                        category=ProvenanceCategory.RECONSTRUCTION,
                        confidence=0.7,
                        notes=book_conn.get("notes", ""),
                    )
                    claims.append(CardClaim(
                        text=f"РљРЅРёРіР°: {book_conn.get('text', '')}",
                        provenance=prov,
                        source_ref=f"archaeology:sites[{len(claims)}-book]",
                    ))

                # Hypothetical claims
                for hc in site.get("hypothetical_claims", []):
                    prov = ProvenanceTag(
                        source_level=SourceLevel.USER_HYPOTHESIS,
                        category=ProvenanceCategory.HYPOTHESIS,
                        confidence=0.5,
                        notes=hc.get("notes", ""),
                    )
                    claims.append(CardClaim(
                        text=hc.get("text", ""),
                        provenance=prov,
                        source_ref=f"archaeology:hypothesis:{len(claims)}",
                    ))

        return SourceAggregation(
            source_name="archaeology",
            provenance_category=ProvenanceCategory.EXTERNAL_SOURCE,
            claim_count=len(claims),
            claims=claims,
            summary=f"РђСЂС…РµРѕР»РѕРіРёСЏ: {len(claims)} СѓС‚РІРµСЂР¶РґРµРЅРёР№",
            confidence=0.8 if claims else 0.0,
            raw_refs=raw_refs[:3],
        )

    def _aggregate_cross_references(
        self, entity_id: str, entity_data: dict
    ) -> SourceAggregation:
        """Cross-cultural parallels from CROSS_REFERENCES.json."""
        data = self._load_json(CROSS_REFS_PATH)
        if not data:
            return SourceAggregation(
                source_name="cross_references",
                provenance_category=ProvenanceCategory.DERIVED,
                claim_count=0,
            )

        refs = data.get("references", [])
        claims = []
        raw_refs = []

        for ref in refs:
            theme = ref.get("theme", "").lower()
            if entity_id.lower() in theme or theme in entity_id.lower():
                raw_refs.append(ref)
                book_ctx = ref.get("book_context", "")
                if book_ctx:
                    prov = ProvenanceTag(
                        source_level=SourceLevel.SYSTEM_INTERPRETATION,
                        category=ProvenanceCategory.DERIVED,
                        confidence=0.6,
                        notes="cross-reference: book context",
                    )
                    claims.append(CardClaim(
                        text=f"РљРѕРЅС‚РµРєСЃС‚ РІ РєРЅРёРіРµ: {book_ctx}",
                        provenance=prov,
                        source_ref=f"crossref:{theme}",
                    ))

                for par in ref.get("parallels", [])[:3]:
                    culture = par.get("culture", "")
                    source = par.get("source", "")
                    detail = par.get("detail", "")
                    if detail:
                        prov = ProvenanceTag(
                            source_level=SourceLevel.HISTORICAL,
                            category=ProvenanceCategory.EXTERNAL_SOURCE,
                            confidence=0.6,
                            notes=f"parallel: {culture}",
                        )
                        claims.append(CardClaim(
                            text=f"{culture} ({source}): {detail}",
                            provenance=prov,
                            source_ref=f"crossref:parallel:{culture}",
                        ))

        return SourceAggregation(
            source_name="cross_references",
            provenance_category=ProvenanceCategory.DERIVED,
            claim_count=len(claims),
            claims=claims,
            summary=f"РљСЂРѕСЃСЃ-СЂРµС„РµСЂРµРЅСЃС‹: {len(claims)} РїР°СЂР°Р»Р»РµР»РµР№",
            confidence=0.6 if claims else 0.0,
            raw_refs=raw_refs[:3],
        )

    def _aggregate_academic(
        self, entity_id: str, entity_data: dict
    ) -> SourceAggregation:
        """Academic confirmations from ACADEMIC_CONFIRMATIONS.json."""
        data = self._load_json(ACADEMIC_PATH)
        if not data:
            return SourceAggregation(
                source_name="academic",
                provenance_category=ProvenanceCategory.EXTERNAL_SOURCE,
                claim_count=0,
            )

        confirmations = data.get("confirmations", [])
        claims = []
        raw_refs = []

        for conf in confirmations:
            category = conf.get("category", "").lower()
            book_theme = conf.get("book_theme", "").lower()
            if entity_id.lower() in category or entity_id.lower() in book_theme:
                raw_refs.append(conf)

                for src in conf.get("academic_sources", []):
                    culture = src.get("culture", "")
                    text = src.get("text", "")
                    if text:
                        prov = ProvenanceTag(
                            source_level=SourceLevel.HISTORICAL,
                            category=ProvenanceCategory.EXTERNAL_SOURCE,
                            confidence=0.7,
                            notes=f"academic: {culture}",
                        )
                        claims.append(CardClaim(
                            text=f"{culture}: {text}",
                            provenance=prov,
                            source_ref=f"academic:{culture}",
                        ))

        return SourceAggregation(
            source_name="academic",
            provenance_category=ProvenanceCategory.EXTERNAL_SOURCE,
            claim_count=len(claims),
            claims=claims,
            summary=f"РђРєР°РґРµРјРёС‡РµСЃРєРёРµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ: {len(claims)}",
            confidence=0.7 if claims else 0.0,
            raw_refs=raw_refs[:3],
        )

    # в”Ђв”Ђ Relations в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _get_relations(self, entity_id: str) -> list[dict]:
        """Get relations from WorldEngine's RelationGraph."""
        try:
            engine = self._get_world_engine()
            context = engine.get_entity_context(entity_id)
            relations = context.get("relations", {})
            # Flatten to simple list
            result = []
            for rel_type, items in relations.items():
                if isinstance(items, list):
                    for item in items[:5]:
                        if isinstance(item, dict):
                            result.append({
                                "type": rel_type,
                                "target": item.get("target", item.get("name", "")),
                                "provenance": item.get("provenance", []),
                            })
                elif isinstance(items, dict):
                    result.append({
                        "type": rel_type,
                        "details": items,
                    })
            return result
        except Exception as e:
            log.warning("relations_failed entity=%s error=%s", entity_id, e)
            return []

    # в”Ђв”Ђ Contradictions в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _detect_contradictions(
        self, sources: list[SourceAggregation]
    ) -> list[ContradictionNote]:
        """
        Detect potential contradictions between sources.

        Heuristic: if one source has AUTHOR_CANON claim about X
        and another has EXTERNAL_SOURCE claim that contradicts X.
        """
        contradictions = []
        canon_claims = []
        external_claims = []

        for source in sources:
            for claim in source.claims:
                if claim.provenance.category == ProvenanceCategory.AUTHOR_CANON:
                    canon_claims.append(claim)
                elif claim.provenance.category == ProvenanceCategory.EXTERNAL_SOURCE:
                    external_claims.append(claim)

        # Check for keyword conflicts between canon and external
        for cc in canon_claims[:5]:
            for ec in external_claims[:5]:
                if self._may_conflict(cc.text, ec.text):
                    contradictions.append(ContradictionNote(
                        description=f"РљРЅРёРіР°: В«{cc.text[:80]}...В» vs РСЃС‚РѕС‡РЅРёРє: В«{ec.text[:80]}...В»",
                        source_1_claim=f"AUTHOR_CANON: {cc.text[:60]}",
                        source_2_claim=f"EXTERNAL_SOURCE: {ec.text[:60]}",
                        resolution="DIFFERENT_PERSPECTIVES",
                    ))

        return contradictions

    @staticmethod
    def _may_conflict(text1: str, text2: str) -> bool:
        """Simple heuristic: do the texts contain conflicting keywords?"""
        # Look for negation markers
        negations = {"РЅРµ", "РЅРµС‚", "Р±РµР·", "Р»РѕР¶СЊ", "РѕС€РёР±Рє", "РїСЂРѕС‚РёРІРѕСЂРµС‡"}
        t1_lower = text1.lower()
        t2_lower = text2.lower()

        # If one contains negation and the other affirms same topic
        for neg in negations:
            if neg in t1_lower and neg not in t2_lower:
                # Check for shared topic words
                words1 = set(t1_lower.split())
                words2 = set(t2_lower.split())
                if len(words1 & words2) >= 2:
                    return True
        return False

    # в”Ђв”Ђ Uncertainty в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _compute_uncertainty(
        self, sources: list[SourceAggregation]
    ) -> Optional[dict]:
        """Compute uncertainty based on source coverage and conflicts."""
        total_claims = sum(s.claim_count for s in sources)
        canon_count = sum(
            s.claim_count for s in sources
            if s.provenance_category == ProvenanceCategory.AUTHOR_CANON
        )
        hyp_count = sum(
            s.claim_count for s in sources
            if s.provenance_category == ProvenanceCategory.HYPOTHESIS
        )

        unknown_aspects = []
        if total_claims == 0:
            unknown_aspects.append("РЅРµС‚ РґР°РЅРЅС‹С… РЅРё РёР· РѕРґРЅРѕРіРѕ РёСЃС‚РѕС‡РЅРёРєР°")
        if hyp_count > 0:
            unknown_aspects.append(f"{hyp_count} РіРёРїРѕС‚РµР·(Р°) С‚СЂРµР±СѓСЋС‚ РїСЂРѕРІРµСЂРєРё")

        confidence_breakdown = []
        for s in sources:
            if s.claim_count > 0:
                confidence_breakdown.append({
                    "aspect": s.source_name,
                    "category": s.provenance_category.value,
                    "confidence": s.confidence,
                    "claims": s.claim_count,
                })

        if not unknown_aspects:
            return None

        flag = UncertaintyFlag(
            has_unknowns=True,
            unknown_aspects=unknown_aspects,
            confidence_breakdown=confidence_breakdown,
        )
        return {
            "has_unknowns": flag.has_unknowns,
            "unknown_aspects": flag.unknown_aspects,
            "confidence_breakdown": flag.confidence_breakdown,
        }

    # в”Ђв”Ђ Suggestions & Related в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _suggestions(
        self, entity_id: str, sources: list[SourceAggregation]
    ) -> list[str]:
        """Generate search suggestions based on what was found."""
        suggestions = []
        for source in sources:
            for claim in source.claims[:2]:
                # Extract key terms as suggestions
                words = claim.text.split()[:3]
                for w in words:
                    if len(w) > 3 and w not in suggestions:
                        suggestions.append(w)
        return suggestions[:5]

    def _related_entities(self, entity_id: str) -> list[dict]:
        """Find related entities from relations."""
        engine = self._get_world_engine()
        context = engine.get_entity_context(entity_id)
        relations = context.get("relations", {})
        related = []
        for rel_type, targets in relations.items():
            if isinstance(targets, list):
                for t in targets[:3]:
                    if isinstance(t, dict):
                        related.append({
                            "entity_id": t.get("target", t.get("id", "")),
                            "relation": rel_type,
                        })
        return related

    # в”Ђв”Ђ Helpers в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    @staticmethod
    def _load_json(path: Path) -> Optional[dict]:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("json_load_failed path=%s error=%s", path, e)
        return None


# Singleton
_card_builder: Optional[KnowledgeCardBuilder] = None

def get_card_builder() -> KnowledgeCardBuilder:
    global _card_builder
    if _card_builder is None:
        _card_builder = KnowledgeCardBuilder()
    return _card_builder

