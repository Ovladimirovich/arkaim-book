"""
Knowledge Card API routes.

Endpoints:
- GET /knowledge/cards/search?q= — search entities
- GET /knowledge/cards/{entity_id} — full knowledge card

The literal ``/search`` route must be declared before ``/{entity_id}``; otherwise
FastAPI treats ``search`` as an entity identifier.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any

from auth.rbac import require_role
from core.dto.knowledge import KnowledgeTraceResponse, TraceabilityStatus

log = logging.getLogger("routes.knowledge_cards")

router = APIRouter(
    prefix="/knowledge/cards",
    tags=["Knowledge Cards"],
    dependencies=[Depends(require_role("reader"))],
)


@router.get("/search", summary="Поиск сущностей для карточки")
async def search_entities(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Поиск сущностей, по которым можно построить Knowledge Card.

    Ищет в WorldEngine и ARCHAEOLOGY.json.

    Семантика ``total`` (зафиксирована 2026-10-11, документация без изменения поведения):
    ``total`` — размер возвращённой страницы, а не глобальное число совпадений.
    Оно всегда равно ``len(entities)`` и не превышает ``limit`` (1..50, по умолчанию 10),
    потому что общий счётчик выборки не считается: сбор прекращается при достижении
    ``limit``, а добор из ARCHAEOLOGY.json (когда WorldEngine дал меньше ``limit``)
    не проверяет соответствие тексту ``q``.
    """
    from knowledge_card import get_card_builder

    builder = get_card_builder()
    seen: set[str] = set()
    unique: list[dict[str, str]] = []

    try:
        from narrative_engine.world_engine import get_world_engine

        engine = get_world_engine()
        engine.initialize()
        search_result = engine.search(q)
        matches = search_result.get("world_model", []) if isinstance(search_result, dict) else search_result
    except Exception:
        matches = []

    for item in matches:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "entity_id": str(item.get("id", "")),
                "name": name,
                "category": str(item.get("category", "")),
            }
        )
        if len(unique) >= limit:
            break

    if len(unique) < limit:
        for site in builder._iter_list(builder._load_json("ARCHAEOLOGY.json"), "sites"):
            name = str(site.get("name", "")).strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            unique.append(
                {
                    "entity_id": str(site.get("id", f"archaeology:{name.casefold().replace(' ', '_')}")),
                    "name": name,
                    "category": "archaeology",
                }
            )
            if len(unique) >= limit:
                break

    return {"query": q, "entities": unique, "total": len(unique)}


def _correction_projection(entity_id: str) -> list[dict]:
    """Load durable M7 corrections for one canonical subject."""
    from knowledge.correction_repository import CorrectionRepository

    data_dir = os.getenv(
        "KNOWLEDGE_CORRECTION_DIR",
        str(Path(__file__).resolve().parents[2] / "runtime_data" / "knowledge"),
    )
    try:
        return [record.model_dump(mode="json") for record in CorrectionRepository(data_dir).list(subject_id=entity_id)]
    except OSError, ValueError:
        return []


def _reasoning_projection(entity_id: str) -> list[dict]:
    """Load durable M6 reasoning results without inference or fabrication."""
    from knowledge.reasoning_repository import ReasoningRepository

    data_dir = os.getenv(
        "KNOWLEDGE_REASONING_DIR",
        str(Path(__file__).resolve().parents[2] / "runtime_data" / "knowledge"),
    )
    try:
        records = ReasoningRepository(data_dir).list(subject_id=entity_id)
    except OSError, ValueError:
        return []
    return [record.model_dump(mode="json") for record in records]


def _default_evidence_catalog() -> Path:
    """Repository root of the existing Book Intelligence fragment catalog."""
    return Path(__file__).resolve().parents[3] / "core" / "KNOWLEDGE" / "enriched_catalog.json"


_evidence_resolver_cache: dict[tuple[object, ...], Any] = {}


def _evidence_resolver():
    """Build the M2 EvidenceResolver over the existing book fragment catalog.

    Extension point: ``KNOWLEDGE_EVIDENCE_CATALOG`` overrides the catalog path
    (same env-boundary style as ``KNOWLEDGE_*_DIR`` repositories). The resolver
    is cached per (path, mtime); it never fabricates Evidence — missing chunks
    resolve to UNUPPORTED/UNAVAILABLE/UNKNOWN through the M2 resolver policy.
    """
    from evidence.external_registry import build_external_locator_source
    from evidence.resolver import BookChunkSource, EvidenceResolver

    catalog_path = Path(os.getenv("KNOWLEDGE_EVIDENCE_CATALOG", str(_default_evidence_catalog())))
    external_dir = catalog_path.parent if catalog_path.name == "enriched_catalog.json" else _default_evidence_catalog().parent
    external_paths = tuple(external_dir / name for name in ("ARCHAEOLOGY.json", "ACADEMIC_CONFIRMATIONS.json"))
    try:
        mtime = catalog_path.stat().st_mtime if catalog_path.is_file() else None
    except OSError:
        mtime = None
    key = (
        str(catalog_path),
        mtime,
        *((str(path), path.stat().st_mtime if path.is_file() else None) for path in external_paths),
    )
    cached = _evidence_resolver_cache.get(key)
    if cached is not None:
        return cached

    chunks: dict[str, dict] = {}
    if mtime is not None:
        try:
            entries = json.loads(catalog_path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            entries = None
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                chunk_id = str(entry.get("id") or entry.get("chunk_id") or "")
                if chunk_id:
                    record = dict(entry)
                    record["chunk_id"] = chunk_id
                    chunks[chunk_id] = record

    resolver = EvidenceResolver(
        chunk_source=BookChunkSource(chunks=chunks),
        external_source=build_external_locator_source(external_dir),
    )
    _evidence_resolver_cache.clear()
    _evidence_resolver_cache[key] = resolver
    return resolver


def _card_claim_id(claim: dict[str, Any]) -> str | None:
    """Bridge a card claim to the existing CanonClaim identity contract.

    Knowledge Card currently has no claim-id field. Only source claims with a
    stable Book chunk can be bridged deterministically; other card claims remain
    unidentified instead of receiving a guessed ID.
    """
    from evidence.external_registry import canonical_external_locator
    from narrative_engine.provenance.claim import CanonClaim

    source_ref = str(claim.get("source_ref") or "")
    chunk_id = str(claim.get("chunk_id") or "")
    text = str(claim.get("text") or "")
    if not text:
        return None
    if source_ref.startswith("book:"):
        if not chunk_id:
            return None
        return CanonClaim.make_id(text, source_id="book", location=f"chunk:{chunk_id}")
    external_locator = canonical_external_locator(source_ref)
    if external_locator:
        source_id = external_locator[len("external:") :].split(":", 1)[0]
        return CanonClaim.make_id(text, source_id=source_id, location=external_locator)
    return None


def _evidence_projection(payload: dict) -> list[dict]:
    """Resolve every card claim reference through the M2 EvidenceResolver.

    Statuses are honest resolver outcomes (RESOLVED / UNAVAILABLE / UNKNOWN);
    references outside the supported M2 locator schemes stay UNKNOWN instead
    of being silently upgraded to a resolved state.

    Each row also carries ``claim_id`` from the same ``_card_claim_id`` bridge
    used by the claims section, so claim/evidence rows of one claim agree on
    identity. When the bridge cannot establish an identity (no text, no stable
    chunk, unsupported locator scheme) the value stays ``None`` instead of a
    guessed id; the resolver status is never used to derive an identity.
    """
    from evidence.external_registry import canonical_external_locator
    from evidence.resolver import ResolutionResult, ResolutionStatus

    resolver = _evidence_resolver()
    rows: list[dict] = []
    for source in payload.get("sources", []):
        for claim in source.get("claims", []):
            source_ref = claim.get("source_ref") or ""
            chunk_id = claim.get("chunk_id")
            if not source_ref and not chunk_id:
                continue
            if chunk_id:
                result = resolver.resolve_chunk_id(str(chunk_id))
            elif source_ref.startswith("book:"):
                # A book claim without a chunk id cannot identify a fragment.
                result = ResolutionResult(
                    status=ResolutionStatus.UNKNOWN,
                    reason="book claim has no chunk_id",
                    locator=source_ref,
                )
            else:
                result = resolver.resolve_locator(canonical_external_locator(source_ref) or source_ref)
            rows.append(
                {
                    "source_ref": source_ref,
                    "chunk_id": claim.get("chunk_id"),
                    "source_title": (claim.get("provenance") or {}).get("source_title"),
                    "status": result.status.value,
                    "evidence_id": result.evidence.id if result.evidence is not None else None,
                    "reason": result.reason,
                    "claim_id": _card_claim_id(claim),
                }
            )
    return rows


def _matches(value: object, requested: str | None) -> bool:
    return requested is None or str(value or "").casefold() == requested.casefold()


def _page(items: list[dict], offset: int, limit: int) -> tuple[list[dict], int | None]:
    page = items[offset : offset + limit]
    next_offset = offset + len(page) if offset + len(page) < len(items) else None
    return page, next_offset


def _trace_lineage(
    claims: list[dict],
    evidence: list[dict],
    conflicts: list[dict],
    reasoning: list[dict],
    corrections: list[dict],
) -> list[dict[str, Any]]:
    """Project exact cross-record links without creating new lineage.

    Card claims/evidence are projected first; M5/M6/M7 records are then joined
    only by IDs already present in their contracts. Missing joins are omitted.
    """
    claim_ids = {str(item.get("claim_id")) for item in claims if isinstance(item, dict) and item.get("claim_id")}
    evidence_by_ref = {str(item.get("source_ref")): item for item in evidence if isinstance(item, dict) and item.get("source_ref")}
    evidence_ids = {str(item.get("evidence_id")) for item in evidence if isinstance(item, dict) and item.get("evidence_id")}
    reasoning_by_id = {str(item.get("id")): item for item in reasoning if isinstance(item, dict) and item.get("id")}
    result: list[dict[str, Any]] = []
    for conflict in conflicts:
        if not isinstance(conflict, dict) or not conflict.get("id"):
            continue
        conflict_claim_ids = {str(value) for value in conflict.get("claim_ids", []) if value}
        conflict_evidence_ids = {str(value) for value in conflict.get("evidence_ids", []) if value}
        linked_reasoning_ids: list[str] = []
        for reasoning_id, record in reasoning_by_id.items():
            input_claim_ids = {str(item.get("claim_id")) for item in record.get("input_claims", []) if isinstance(item, dict) and item.get("claim_id")}
            input_evidence_ids = {
                str(value) for item in record.get("input_claims", []) if isinstance(item, dict) for value in item.get("evidence_ids", []) if value
            }
            if input_claim_ids & conflict_claim_ids or input_evidence_ids & conflict_evidence_ids:
                linked_reasoning_ids.append(reasoning_id)
        linked_corrections: list[dict[str, Any]] = []
        for correction in corrections:
            if not isinstance(correction, dict) or not correction.get("id"):
                continue
            superseded_ids = {str(value) for value in correction.get("superseded_claim_ids", []) if value}
            affected_ids = {str(value) for value in correction.get("affected_reasoning_ids", []) if value}
            if superseded_ids & conflict_claim_ids or affected_ids & set(linked_reasoning_ids):
                linked_corrections.append(
                    {
                        "correction_id": str(correction["id"]),
                        "stale_reasoning_ids": sorted(affected_ids),
                    }
                )
        result.append(
            {
                "conflict_id": str(conflict["id"]),
                "claim_ids": sorted(conflict_claim_ids),
                "evidence_ids": sorted(conflict_evidence_ids),
                "claim_links": sorted(conflict_claim_ids & claim_ids),
                "evidence_links": [
                    {"record_id": value, "source_ref": value} for value in sorted(conflict_evidence_ids) if value in evidence_by_ref or value in evidence_ids
                ],
                "reasoning_ids": sorted(linked_reasoning_ids),
                "corrections": linked_corrections,
            }
        )
    return result


def _conflict_projection(entity_id: str) -> list[dict]:
    """Load M5 conflict records without changing Knowledge Card authority storage."""
    from knowledge.conflict_repository import ConflictRepository

    data_dir = os.getenv(
        "KNOWLEDGE_CONFLICT_DIR",
        str(Path(__file__).resolve().parents[2] / "runtime_data" / "knowledge"),
    )
    try:
        records = ConflictRepository(data_dir).list(subject_id=entity_id)
    except OSError, ValueError:
        return []
    return [record.model_dump(mode="json") for record in records]


def _world_reference_projection(entity_id: str) -> dict:
    """Resolve entity_id to a typed World reference using M3 resolver.

    Returns WorldEntityReference as dict with status RESOLVED/UNRESOLVED/
    AMBIGUOUS/CROSSWALK_UNAPPROVED. Read-only: does not mutate WorldModel
    or crosswalk.
    """
    try:
        from knowledge.world_resolver import WorldKnowledgeResolver

        resolver = WorldKnowledgeResolver()
        reference = resolver.resolve(entity_id)
        return reference.model_dump(mode="json")
    except Exception:
        return {
            "query": entity_id,
            "status": "UNRESOLVED",
            "reason": "world resolver failed",
            "resolution_method": "none",
        }


def _temporal_reference_projection(entity_id: str) -> dict:
    """Resolve temporal reference for entity using M4 resolver.

    Returns TemporalReference as dict with status RESOLVED/UNRESOLVED/UNKNOWN.
    Read-only: does not mutate Temporal state.
    """
    try:
        from knowledge.temporal_resolver import KnowledgeTemporalResolver
        from schemas.temporal_reference import TemporalTimeBasis

        resolver = KnowledgeTemporalResolver()
        reference = resolver.resolve(
            claim_id=entity_id,
            temporal_node_id=entity_id,
            time_basis=TemporalTimeBasis.WORLD,
        )
        return reference.model_dump(mode="json")
    except Exception:
        return {
            "claim_id": entity_id,
            "time_basis": "WORLD_TIME",
            "status": "UNKNOWN",
            "reason": "temporal resolver failed or no temporal node supplied",
            "resolution_method": "none",
        }


@router.get("/trace/{entity_id}", response_model=KnowledgeTraceResponse, summary="Полная трассировка знаний сущности")
async def get_knowledge_trace(
    entity_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    claim_category: str | None = Query(None, max_length=64),
    evidence_status: str | None = Query(None, max_length=32),
    conflict_status: str | None = Query(None, max_length=64),
    correction_status: str | None = Query(None, max_length=32),
    reasoning_status: str | None = Query(None, max_length=32),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
):
    """Read-only трассировка знаний сущности: посекционная пагинация, фильтры, правило статуса.

    Правило ``status`` (GO-1, зафиксировано 2026-10-11 по §2.5 SoT «если путь
    существенно утверждения обрывается — PARTIAL/UNKNOWN»): ``COMPLETE`` — есть
    claims, все evidence-строки ``RESOLVED`` и нет ``limitations``; иначе
    ``PARTIAL`` — обрыв пути (evidence ``UNAVAILABLE``/``UNKNOWN``, отсутствие
    resolvable-ссылок, несвязанные M5/M6/M7-записи, неразрешённая сущность).
    ``UNKNOWN`` остаётся зарезервированным значением словаря ``TraceabilityStatus``
    и сейчас не выдаётся.
    """
    from knowledge_card import get_card_builder

    builder = get_card_builder()
    card = builder.build(entity_id)
    payload = card.to_dict()
    claims = []
    for source in payload.get("sources", []):
        for raw_claim in source.get("claims", []):
            claim = dict(raw_claim)
            claim_id = _card_claim_id(claim)
            if claim_id:
                claim["claim_id"] = claim_id
            claims.append(claim)
    evidence = _evidence_projection(payload)
    temporal = []
    for claim in claims:
        source_ref = claim.get("source_ref", "")
        if source_ref.startswith("world_model:") and ":" in source_ref:
            temporal.append({"claim_ref": source_ref, "status": "PROJECTED_FROM_WORLD_REF"})
    all_conflicts = [*payload.get("contradictions", []), *_conflict_projection(entity_id)]
    all_corrections = _correction_projection(entity_id)
    reasoning = _reasoning_projection(entity_id)
    lineage = _trace_lineage(claims, evidence, all_conflicts, reasoning, all_corrections)
    world_reference = _world_reference_projection(entity_id)
    temporal_reference = _temporal_reference_projection(entity_id)
    lineage_has_links = any(item.get("claim_links") or item.get("evidence_links") or item.get("reasoning_ids") or item.get("corrections") for item in lineage)
    # totals are always the full unfiltered chain size; filters only narrow page contents
    evidence_has_refs = bool(evidence)
    evidence_unresolved = any(item.get("status") != "RESOLVED" for item in evidence)
    totals = {
        "claims": len(claims),
        "evidence": len(evidence),
        "conflicts": len(all_conflicts),
        "reasoning": len(reasoning),
        "corrections": len(all_corrections),
        "lineage": len(lineage),
    }
    if claim_category:
        claims = [claim for claim in claims if _matches((claim.get("provenance") or {}).get("category"), claim_category)]
    if min_confidence is not None:
        claims = [
            claim
            for claim in claims
            if (claim.get("provenance") or {}).get("confidence") is not None
            and float((claim.get("provenance") or {}).get("confidence")) >= min_confidence
        ]
    if evidence_status:
        evidence = [item for item in evidence if _matches(item.get("status"), evidence_status)]
    if conflict_status:
        all_conflicts = [item for item in all_conflicts if _matches(item.get("status"), conflict_status)]
    if correction_status:
        all_corrections = [item for item in all_corrections if _matches(item.get("status"), correction_status)]
    if reasoning_status:
        reasoning = [item for item in reasoning if _matches(item.get("status"), reasoning_status)]
    claims, next_claims = _page(claims, offset, limit)
    evidence, next_evidence = _page(evidence, offset, limit)
    all_conflicts, next_conflicts = _page(all_conflicts, offset, limit)
    all_corrections, next_corrections = _page(all_corrections, offset, limit)
    reasoning, next_reasoning = _page(reasoning, offset, limit)
    lineage, next_lineage = _page(lineage, offset, limit)
    limitations = []
    if not payload.get("primary_entity"):
        limitations.append("World entity not resolved")
    if not evidence_has_refs:
        limitations.append("No resolvable evidence references in current card projection")
    if (all_conflicts or reasoning or all_corrections) and not lineage_has_links:
        limitations.append("Knowledge records have no exact cross-record lineage")
    status = TraceabilityStatus.PARTIAL if (limitations or evidence_unresolved) else TraceabilityStatus.COMPLETE
    section_next = (next_claims, next_evidence, next_conflicts, next_corrections, next_reasoning, next_lineage)
    return KnowledgeTraceResponse(
        entity_id=entity_id,
        status=status,
        claims=claims,
        evidence=evidence,
        world=payload.get("primary_entity") or {},
        world_reference=world_reference,
        temporal=temporal,
        temporal_reference=temporal_reference,
        conflicts=all_conflicts,
        reasoning=reasoning,
        corrections=all_corrections,
        lineage=lineage,
        uncertainty=payload.get("uncertainty") or {},
        limitations=limitations,
        offset=offset,
        limit=limit,
        totals=totals,
        next_offset=next((n for n in section_next if n is not None), None) if any(n is not None for n in section_next) else None,
    )


@router.get("/holistic/{entity_id}", summary="Holistic Entity View (M15)")
async def get_holistic_view(
    entity_id: str,
    name: str = Query("", max_length=200),
):
    """Read-only агрегат доступных сведений о сущности (M15).

    Объединяет книжные и сценарные claims (раздельно), явные связи
    книга↔сценарий, конфликты, Evidence, типизированные мировую и
    временную́ ссылки. Отсутствие данных отображается явно через
    ``availability`` и ``limitations``. Не 404 для несущности: возвращает
    проекцию с пустыми секциями и перечнем ограничений.
    """
    from core.services.holistic_view import build_holistic_view

    return build_holistic_view(entity_id, entity_name=name)


@router.get("/{entity_id}", summary="Знания о сущности")
async def get_knowledge_card(
    entity_id: str,
):
    """
    Получить Knowledge Card для сущности.

    Карточка агрегирует знания из:
    - книги (AUTHOR_CANON)
    - археологии (EXTERNAL_SOURCE)
    - кросс-культурных параллелей (DERIVED)
    - академических подтверждений (EXTERNAL_SOURCE)

    Provenance каждого утверждения сохраняется отдельно.

    Семантика ``uncertainty.has_unknowns`` (зафиксирована 2026-10-11, документация без изменения поведения):
    это card-level агрегат ``bool(unknown_aspects)``; в ``unknown_aspects`` попадают только
    непокрытость источников карточки — сущность не найдена, нет book claims, нет archaeology claims
    и ``unsolved`` из данных сущности. Статусы evidence (RESOLVED / UNAVAILABLE / UNKNOWN) в эту секцию
    не входят и на значение не влияют; для несущности без данных endpoint возвращает 404, а та же секция
    с ``has_unknowns=true`` доступна в trace.
    """
    from knowledge_card import get_card_builder

    builder = get_card_builder()
    card = builder.build(entity_id)

    if not card.primary_entity and "Сущность не найдена" in card.metadata.coverage_note:
        raise HTTPException(404, f"Entity '{entity_id}' not found in any knowledge source")

    return card.to_dict()


@router.get("/events/{event_id}", summary="Read-only представление канонического события")
async def get_canonical_event_view(event_id: str):
    """M19: представление канонического события.

    Объединяет описание из WORLD_MODEL, подтверждённые claim-связи из
    claim_temporal_links.json, исходные фрагменты книги, provenance,
    эпоху/temporal-узел и утверждённые сценарные связи (если они
    действительно относятся к отображаемым материалам).

    Показываются только claims, для которых установлена связь с запрашиваемым
    event_id. Temporal-цепочка отображается только после успешной validate_chain().
    При отсутствии claims возвращается корректное представление с пустым
    списком и явным ограничением. Номер главы не считается доказательством
    принадлежности claim к событию.
    """
    from core.services.canonical_event_view import build_canonical_event_view

    view = build_canonical_event_view(event_id)
    if not view.get("found"):
        raise HTTPException(404, view.get("limitations", ["Событие не найдено"])[0])
    return view
