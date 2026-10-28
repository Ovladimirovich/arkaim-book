# -*- coding: utf-8 -*-
"""
AskExpansionOrchestrator - управляемый путь Source -> Candidate -> Validation
для /book/ask (Stage 2).

Последовательность (expand):
  1. Source Search: книжные чанки (enriched_chunks.json) - приоритет BOOK;
     внешние источники (source_searcher, rule-based) - только fallback,
     их кандидаты всегда REVIEW (никогда не авто-принимается).
  2. Candidate Extraction: JSONExtractor превращает находки в RawKnowledge.
  3. Entity Resolution: related_entities (WorldModel) + NameResolver;
     неоднозначные/неизвестные сущности -> REVIEW, не автосоздание.
  4. Relation Resolution: операторы-маркеры. 'рядом с' НЕ означает
     'participates_in' - более сильная связь извлекается только если
     подтверждена текстом источника (no invented fact).
  5. Validation: schema_validator + проверка конфликта с Knowledge Core.
  6. Editorial Gate: ACCEPT / REVIEW / REJECT.
  7. Storage: KnowledgeStore, изолированный файл, идемпотентно.
  8. Gap Recheck: детектор повторно проверяет заполненность gap.

Безопасность: LLM не участвует в авто-принятии. Auto-ACCEPT только для
детерминированных evidence-backed фактов из канонического источника;
реконструкции/гипотезы и внешние источники -> REVIEW.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("hermes.ask_expansion_orchestrator")


# Стоп-слова для извлечения содержательных слов субъекта.
_STOP_WORDS: frozenset[str] = frozenset(
    (
        "как",
        "кто",
        "что",
        "где",
        "когда",
        "почему",
        "зачем",
        "какой",
        "какая",
        "какое",
        "какие",
        "этот",
        "эта",
        "это",
        "эти",
        "такой",
        "книга",
        "книги",
        "книге",
        "о",
        "об",
        "и",
        "в",
        "на",
        "по",
        "с",
        "из",
        "для",
        "к",
        "около",
        "рядом",
    )
)


# ── Models ─────────────────────────────────────────────────────────────


@dataclass
class EditorialDecision:
    """Решение редакции: ACCEPT / REVIEW / REJECT."""

    status: str
    reason: str
    validated: Optional[dict[str, Any]] = None


@dataclass
class CandidateClaim:
    """Кандидат остаётся кандидатом до валидации и editor decision."""

    subject: str
    predicate: str
    object: str
    source: str
    evidence: str
    provenance: dict[str, Any]
    temporal_context: dict[str, Any]
    confidence: float = 0.5
    evidence_fingerprint: str = ""


@dataclass
class ExpansionResult:
    """Результат расширения знаний для вопроса."""

    question: str
    decisions: list[EditorialDecision] = field(default_factory=list)
    accepted: list[CandidateClaim] = field(default_factory=list)
    review: list[CandidateClaim] = field(default_factory=list)
    rejected: list[CandidateClaim] = field(default_factory=list)
    source_search_results: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[CandidateClaim] = field(default_factory=list)
    storage: dict[str, Any] = field(default_factory=dict)
    gap_recheck: dict[str, Any] = field(default_factory=dict)
    summary: str = ""


# ── Entity / Relation resolution ───────────────────────────────────────

# Нейтральные маркеры: близость/упоминание НЕ доказывают участие, причину.
_NEUTRAL_RELATION_MARKERS: tuple[str, ...] = (
    "рядом",
    "возле",
    "около",
    "среди",
    "вблизи",
    "на фоне",
)
# Маркеры явной связи: при их наличии связь извлекается из текста,
# а не додумывается.
_POSITIVE_RELATION_MARKERS: tuple[str, ...] = (
    "участвовал",
    "принял участие",
    "участие",
    "основал",
    "создал",
    "причина",
    "послужило причиной",
    "привёл к",
    "привело к",
    "убил",
    "защитил",
    "научил",
    "спас",
    "являлся",
    "есть",
)
# Сильные предикаты, требующие явного подтверждения в тексте.
_STRONG_PREDICATES: frozenset[str] = frozenset(
    (
        "participates_in",
        "caused_by",
        "causes",
        "precedes",
        "follows",
        "located_in",
        "found_in",
        "founded_by",
    )
)


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    low = (text or "").lower()
    return any(m in low for m in markers)


def resolve_subject_entity(
    subject: str,
    related_entities: list[dict[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    """Разрешить субъект кандидата: (entity_id, method, flags).

    - world_model_match: имя совпало с сущностью WorldModel;
    - ambiguous_candidates: несколько сущностей совпали -> флаг ambiguous;
    - name_resolver: каноническое имя из NameResolver (без авторитетного
      entity_id -> флаг unresolved_entity, кандидат идёт на REVIEW);
    - none: имя неизвестно -> флаг unknown_entity (REVIEW).
    """
    from intelligence.nameresolver import NameResolver

    resolver = NameResolver()
    canonical = resolver.resolve(subject)
    known = canonical in resolver.get_all_canonical()

    aliases = resolver.get_all_aliases(canonical)
    # Stem-matching: русские падежные варианты ('Гиперборея' ~ 'Гипербореи')
    # не различаются по 8-символьному корню. Ищем каноник, чей stem
    # совпадает со stem вопроса - без новых алиасов в NameResolver.
    subject_stem = _stem(subject)
    stem_matched: Optional[str] = None
    if not known:
        for canon in resolver.get_all_canonical():
            if _stem(canon) == subject_stem:
                stem_matched = canon
                break
    effective_canonical = stem_matched if stem_matched is not None else canonical
    effective_known = known or stem_matched is not None
    aliases = aliases if stem_matched is None else resolver.get_all_aliases(stem_matched)

    flags: dict[str, Any] = {
        "canonical_name": effective_canonical,
        "known_alias": effective_known,
        "aliases": sorted(aliases),
    }
    matches = [
        e
        for e in (related_entities or [])
        if e.get("name")
        and (e.get("name") == subject or e.get("name") == effective_canonical or subject in str(e.get("name", "")) or str(e.get("name", "")) in subject)
    ]
    if len(matches) > 1:
        flags["ambiguous"] = True
        return matches[0].get("entity_id", ""), "ambiguous_candidates", flags
    if matches:
        flags["matched_name"] = matches[0].get("name")
        return matches[0].get("entity_id", ""), "world_model_match", flags
    if effective_known:
        return (effective_canonical.lower().replace(" ", "_"), "name_resolver", flags)
    flags["unknown_entity"] = True
    return "", "none", flags


def resolve_relation(
    evidence_text: str,
    candidate_predicate: str,
) -> dict[str, Any]:
    """Решить, подтверждается ли предикат кандидата текстом источника.

    Правило безопасности: если в тексте есть только нейтральные маркеры
    ('рядом', 'около'...) и кандидат утверждает сильное отношение,
    отношение НЕ подтверждается -> кандидат на REVIEW (no invented fact).
    """
    neutral_only = _has_marker(evidence_text, _NEUTRAL_RELATION_MARKERS)
    positive = _has_marker(evidence_text, _POSITIVE_RELATION_MARKERS)
    strong = candidate_predicate in _STRONG_PREDICATES
    supported = positive or (not (neutral_only and strong))
    reason = ""
    if not supported:
        reason = "Текст содержит только маркеры близости/упоминания; сильное отношение '" + candidate_predicate + "' не подтверждено - REVIEW"
    return {
        "supported": bool(supported),
        "neutral_markers_only": neutral_only,
        "reason": reason,
    }


# ── Source Search ──────────────────────────────────────────────────────

# Верхний предел книжных находок за вопрос (латентность ask-пути).
MAX_BOOK_SOURCE_HITS = 8
MIN_CHUNK_HIT_SCORE = 2


async def load_book_chunks() -> list[dict[str, Any]]:
    """Загрузить книжные чанки (приоритетный источник BOOK).

    Использует готовый артефакт enriched_chunks.json (тот же, что
    использует /book/text и Knowledge Core). Чистое чтение.
    Результат кэшируется в core.cache.chunks_cache: файл ~1 МБ (824 чанка),
    повторное чтение на каждый /book/ask недопустимо.
    """
    from shared_config import settings as shared_settings

    path = shared_settings.KNOWLEDGE_DIR / "enriched_chunks.json"
    if not path.exists():
        return []

    from core.cache import chunks_cache

    async def _factory() -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("chunks", []) or []
        return data if isinstance(data, list) else []

    return await chunks_cache.get_or_set("ask_expansion:enriched_chunks", _factory, ttl=600)


def _stem(term: str, length: int = 8) -> str:
    """Корневой префикс для case-insensitive prefix-матчинга."""
    t = str(term or "").lower().strip()
    return t[:length] if len(t) >= length else t


def _content_terms(question: str) -> list[str]:
    """Содержательные слова вопроса (>=4 символа, без стоп-слов)."""
    return [w for w in re.findall(r"[а-яa-z0-9]{4,}", str(question or "").lower()) if w not in _STOP_WORDS]


def _chunk_score(chunk: dict[str, Any], terms: list[str]) -> int:
    """Детерминированный скоринг: stem-попадание термина в текст чанка.

    Prefix-матчинг (первые 8 символов) покрывает падежные формы
    ('Гиперборея' ~ 'Гипербореи' ~ 'гипербореев').
    """
    text = str(chunk.get("text", "")).lower()
    score = 0
    for term in terms:
        s = _stem(term)
        if s and s in text:
            score += 1
    # Бонус за метаданные обогащения (сущность попала в enrichment).
    for key in ("enriched_characters", "enriched_themes", "enriched_symbols"):
        values = [str(v) for v in (chunk.get(key) or [])]
        if any(_stem(t) in v.lower() for v in values for t in terms if _stem(t)):
            score += 1
            break
    return score


async def search_book_sources(
    terms: list[str],
    limit: int = MAX_BOOK_SOURCE_HITS,
) -> list[dict[str, Any]]:
    """Поиск книжных источников по терминам (приоритет BOOK)."""
    chunks = await load_book_chunks()
    scored = []
    for chunk in chunks:
        s = _chunk_score(chunk, terms)
        if s >= MIN_CHUNK_HIT_SCORE:
            scored.append((s, chunk))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("id", ""))))
    return [
        {
            "kind": "book_chunk",
            "priority": "BOOK",
            "score": s,
            "chunk_id": str(c.get("id", "")),
            "source_ref": "book:chunk:" + str(c.get("id", "")),
            "chapter_title": c.get("chapter_title", ""),
            "text": c.get("text", ""),
        }
        for s, c in scored[:limit]
    ]


def search_external_sources(
    entity_name: str,
    entity_type: str = "concept",
) -> list[dict[str, Any]]:
    """Rule-based внешние источники (fallback, NIKOGDA не авто-ACCEPT).

    Реализация существует в narrative_engine.research.source_searcher —
    переиспользуем её (внешний provenance отслеживается отдельно).
    """
    try:
        from narrative_engine.research.source_searcher import search_sources
    except Exception as exc:
        log.warning("external_source_search_unavailable error=%s", exc)
        return []
    return [
        {
            "kind": "external",
            "priority": "EXTERNAL",
            "score": s.relevance_score,
            "source_ref": "external:" + s.source_type,
            "title": s.title,
            "snippet": s.snippet,
        }
        for s in search_sources(entity_name, entity_type)
    ]


# ── Candidate Extraction (JSONExtractor) ──────────────────────────────


async def extract_candidates_from_hit(
    hit: dict[str, Any],
    question: str,
) -> list[dict[str, Any]]:
    """Прогнать книжную находку через JSONExtractor -> кандидаты.

    Один кандидат на находку: подтверждённые content-слова вопроса
    (те, что реально встретились в тексте чанка) описаны в источнике.
    Предикат "mentioned_in" - нейтральный, не додумывает связей.
    Внешние находки - кандидаты только под REVIEW.
    """
    from knowledge_expansion.extractors.json_extractor import JSONExtractor

    # Текст находки: у книжного чанка - text, у внешнего - snippet/title.
    text_blob = " ".join(str(hit.get(k, "")) for k in ("text", "snippet", "title")).lower()
    terms = _content_terms(question)
    confirmed = [t for t in terms if _stem(t) and (_stem(t) in text_blob or t in text_blob)]
    if not confirmed:
        # Термина вопроса нет в тексте - кандидат не подтверждён.
        return []
    extractor = JSONExtractor()
    payload: dict[str, Any] = {
        "name": question,
        "description": hit.get("text", hit.get("snippet", "")),
        "source_ref": hit.get("source_ref", ""),
        "priority": hit.get("priority", ""),
    }
    raw_items = await extractor.extract(payload)
    candidates: list[dict[str, Any]] = []
    for raw in raw_items[:1]:
        candidates.append(
            {
                "subject": " ".join(confirmed),
                "predicate": "mentioned_in",
                "evidence": str(raw.content)[:600],
                "source_ref": hit.get("source_ref", ""),
                "priority": hit.get("priority", "BOOK"),
                "kind": hit.get("kind", "book_chunk"),
                "chapter_title": hit.get("chapter_title", ""),
            }
        )
    return candidates


# ── Validation + Editorial Gate ────────────────────────────────────────

ACCEPT_SCORE_THRESHOLD = 0.8
REVIEW_SCORE_THRESHOLD = 0.5


def validate_candidate(
    candidate: dict[str, Any],
    related_entities: list[dict[str, Any]],
    knowledge_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Валидация кандидата: локальные проверки + конфликт с Knowledge Core.

    Считает validation_score и собирает причины. Конфликт с
    Knowledge Core (contradictions) снижает score и идёт на gate.
    """
    reasons: list[str] = []
    score = 1.0

    if not candidate.get("subject"):
        score *= 0.3
        reasons.append("no_subject")
    if not candidate.get("evidence"):
        score *= 0.3
        reasons.append("no_evidence")

    entity_id, method, flags = resolve_subject_entity(
        str(candidate.get("subject", "")),
        related_entities,
    )
    if flags.get("ambiguous"):
        score *= 0.4
        reasons.append("ambiguous_entity")
    if flags.get("unknown_entity"):
        score *= 0.5
        reasons.append("unknown_entity")

    # Проверка, что субъект референцирован в evidence (не домысел).
    evidence_low = str(candidate.get("evidence", "")).lower()
    aliases = {a.lower() for a in (flags.get("aliases") or []) if a}
    if flags.get("canonical_name"):
        aliases.add(flags.get("canonical_name", "").lower())
    # Содержательные слова субъекта (4+ символ, без стоп-слов).
    subject_terms = {w for w in re.findall(r"[а-яa-z0-9]{4,}", str(candidate.get("subject", "")).lower())}
    subject_terms -= _STOP_WORDS
    # Субъект считается подтверждённым, если stem хотя бы одного
    # содержательного слова есть в evidence ИЛИ совпало с каноническим
    # алиасом (покрывает падежные формы: 'гиперборея' ~ 'Гипербореи').
    subject_stems = {_stem(t) for t in subject_terms}
    alias_stems = {_stem(a) for a in aliases if a}
    term_hit = any(s in evidence_low for s in subject_stems) or (subject_stems & alias_stems)
    if not term_hit:
        # Связь подтверждена только тем, что субъект назван в вопросе,
        # но не найдена в evidence - снижаем score.
        score *= 0.8
        reasons.append("subject_not_evidenced_in_source")

    relation = resolve_relation(
        str(candidate.get("evidence", "")),
        str(candidate.get("predicate", "described_in")),
    )
    if not relation.get("supported"):
        score *= 0.5
        reasons.append("relation_not_supported_by_evidence")

    conflict = _detect_conflict(candidate, knowledge_contexts)
    if conflict:
        score *= 0.3
        reasons.append("conflict_with_knowledge_core")

    return {
        "validation_score": round(score, 3),
        "reasons": reasons,
        "entity_id": entity_id,
        "entity_method": method,
        "entity_flags": flags,
        "relation": relation,
        "conflict_with_knowledge_core": conflict,
    }


def _detect_conflict(
    candidate: dict[str, Any],
    knowledge_contexts: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Проверить кандидата против contradictions Knowledge Core."""
    contradictions = [c for ctx in (knowledge_contexts or []) for c in (ctx.get("contradictions", []) or [])]
    if not contradictions:
        return None
    subject_low = str(candidate.get("subject", "")).lower()
    for note in contradictions:
        blob = " ".join(str(note.get(k, "")) for k in ("description", "source_1_claim", "source_2_claim")).lower()
        if subject_low and subject_low in blob:
            return {
                "note": note,
                "resolution": note.get("resolution", "UNRESOLVED"),
            }
    return None


def make_decision(
    validation: dict[str, Any],
    candidate: dict[str, Any],
) -> EditorialDecision:
    """Editorial gate: ACCEPT / REVIEW / REJECT."""
    score = float(validation.get("validation_score", 0.0))
    reasons = list(validation.get("reasons", []))

    if "no_evidence" in reasons and "no_subject" in reasons:
        return EditorialDecision("REJECT", "Нет ни субъекта, ни evidence.", validation)

    # Внешний источник: никогда не авто-ACCEPT.
    if candidate.get("priority") == "EXTERNAL":
        if score >= REVIEW_SCORE_THRESHOLD:
            return EditorialDecision(
                "REVIEW",
                "Внешний источник: авто-принятие запрещено, требуется editor decision.",
                validation,
            )
        return EditorialDecision("REJECT", "Внешний источник с низкой валидацией.", validation)

    # Конфликт с Knowledge Core всегда -> REVIEW (не гасим конфликты).
    if "conflict_with_knowledge_core" in reasons:
        return EditorialDecision(
            "REVIEW",
            "Кандидат конфликтует с существующим Knowledge Core - требуется редакторское решение.",
            validation,
        )

    if score >= ACCEPT_SCORE_THRESHOLD and "relation_not_supported_by_evidence" not in reasons and "ambiguous_entity" not in reasons:
        return EditorialDecision("ACCEPT", "Валидация и evidence подтверждают кандидата.", validation)

    if score >= REVIEW_SCORE_THRESHOLD:
        return EditorialDecision(
            "REVIEW",
            "Score ниже порога ACCEPT: " + ", ".join(reasons) + ".",
            validation,
        )
    return EditorialDecision("REJECT", "Валидация не пройдена: " + ", ".join(reasons) + ".", validation)


# ── Storage (KnowledgeStore, изолированный файл) ───────────────────────

# Аккумулирующий файл ask-расширений. Лежит в runtime-пространстве
# (shared_config.ASK_EXPANSIONS_DIR), НЕ в канонической папке core/KNOWLEDGE:
# это очередь предложений, а не знания книги. Дедедупликация по
# (subject, predicate) вписана в KnowledgeStore.save через topic-matching.
ASK_EXPANSIONS_FILENAME = "ASK_EXPANSIONS.json"


def _fingerprint(candidate: dict[str, Any]) -> str:
    import hashlib

    blob = "|".join(
        (
            str(candidate.get("subject", "")),
            str(candidate.get("predicate", "")),
            str(candidate.get("source_ref", "")),
        )
    )
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def _to_validated(cand: CandidateClaim, validation: dict[str, Any]):
    """Candidate -> ValidatedKnowledge (формат KnowledgeStore)."""
    from knowledge_expansion.models import ValidatedKnowledge

    # Derive provenance metadata from the candidate's preserved provenance,
    # falling back to defaults only if nothing was upstream.
    prov = cand.provenance or {}
    prov_category = prov.get("category") or prov.get("epistemic_status") or "DERIVED"
    prov_source_level = prov.get("source_level") or "CANON"
    default_notes = (
        "Ask-expansion claim, извлечённый из канонического текста книги "
        "(Stage 2 pipeline)."
    )
    prov_notes = prov.get("notes") or default_notes

    return ValidatedKnowledge(
        source=cand.source,
        # Unique topic per claim: includes source_ref so KnowledgeStore
        # dedup (by topic) keeps one entry per evidence chunk,
        # не схлопывает все чанки в одну запись.
        topic=f"{cand.subject} :: {cand.predicate} :: {cand.source}",
        content=cand.evidence,
        layers={},
        cross_references=[],
        patterns=[],
        connections=[],
        graph_links=[],
        validation_score=float(validation.get("validation_score", 0.0)),
        duplicates_found=[],
        metadata={
            "provenance": cand.provenance,
            "temporal_context": cand.temporal_context,
            "editorial_decision": "ACCEPT",
            "evidence_fingerprint": cand.evidence_fingerprint,
            "source_ref": cand.source,
            # M16.3 record-level provenance: KnowledgeStore повторяет этот
            # блок на уровне записи ASK_EXPANSIONS.json (как в
            # screenplay_links.json). ACCEPT-кандидаты берутся только из
            # BOOK (первичный канон), поэтому category=DERIVED,
            # source_level=CANON — извлекено из канонического текста книги.
            "_provenance_metadata": {
                "category": prov_category,
                "source_level": prov_source_level,
                "notes": prov_notes,
                "evidence_ref": cand.source,
                "validation_score": float(validation.get("validation_score", 0.0)),
            },
        },
        confidence=cand.confidence,
    )


# ── Gap Recheck ────────────────────────────────────────────────────────


def recheck_gap(
    question: str,
    accepted: list[CandidateClaim],
    related_entities: list[dict[str, Any]],
    knowledge_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Повторная проверка: закрывают ли принятые кандидаты gap.

    Детектор пересчитывает статус с учётом уже сохранённых ASK_EXPANSIONS
    (читаются как структурированный knowledge context) и сравнения с
    исходным статусом.
    """
    from core.services.ask_gap_detector import detect_gap

    before = detect_gap(
        question,
        related_entities=related_entities,
        existing_knowledge_core=knowledge_contexts,
    )

    # Сформировать контекст, в который заложены принятые кандидаты,
    # и пересчитать статус с ним.
    enriched_contexts = list(knowledge_contexts or [])
    if accepted:
        enriched_contexts.append(_synth_context_from_accepted(question, accepted))
    after = detect_gap(
        question,
        related_entities=related_entities,
        existing_knowledge_core=enriched_contexts,
    )
    gap_closed = after.status in ("KNOWN", "PARTIALLY_KNOWN") and before.status in ("MISSING", "CONFLICTING", "PARTIALLY_KNOWN") and len(accepted) >= 1
    return {
        "before_status": before.status,
        "after_status": after.status,
        "before_evidence": before.evidence_available,
        "after_evidence": after.evidence_available,
        "accepted_count": len(accepted),
        "gap_closed": gap_closed,
        "note": ("Gap закрыт: принятые кандидаты дали structured evidence." if gap_closed else "Gap не закрыт: structured knowledge по-прежнему ограничен."),
    }


def _synth_context_from_accepted(question: str, accepted: list[CandidateClaim]) -> dict[str, Any]:
    """Синтезировать knowledge context из принятых кандидатов (для recheck)."""
    book_claims = [
        {
            "text": c.evidence,
            "source_ref": c.source,
            "provenance": {
                "type": "source",
                "doc_id": c.source,
                "label": "ask_expansion",
                "evidence_fingerprint": c.evidence_fingerprint,
            },
        }
        for c in accepted
    ]
    return {
        "entity_id": "ask_expansion:" + question[:60],
        "entity_name": question,
        "book_claims": book_claims,
        "screenplay_claims": [],
        "genome_claims": [],
        "world_claims": [],
        "archaeology_claims": [],
        "contradictions": [],
        "screenplay_links": [],
        "claim_temporal_references": [],
    }


# ── Orchestrator entry point ──────────────────────────────────────────


async def expand(
    question: str,
    related_entities: list[dict[str, Any]],
    knowledge_contexts: list[dict[str, Any]],
    constraints: Optional[list[dict[str, Any]]] = None,
) -> ExpansionResult:
    """Запустить управляемый путь Source -> Candidate -> Validation.

    1. Source Search (книжные чанки; внешние источники как fallback)
    2. Candidate Extraction (JSONExtractor)
    3. Entity / Relation Resolution
    4. Validation + Editorial Gate
    5. Storage (KnowledgeStore, ACCEPT только)
    6. Gap Recheck
    """
    from core.services.ask_gap_detector import detect_gap

    result = ExpansionResult(question=question)
    gap_report = detect_gap(
        question,
        related_entities=related_entities,
        existing_knowledge_core=knowledge_contexts,
        constraints=constraints,
    )
    if gap_report.status == "KNOWN":
        result.summary = "Знание уже достаточное (status=KNOWN) - расширение не требуется."
        result.gap_recheck = recheck_gap(question, [], related_entities, knowledge_contexts or [])
        return result

    # ── 1. Source Search ─────────────────────────────────────────────
    entity_names = [str(e.get("name", "")) for e in (related_entities or []) if e.get("name")][:5]
    terms = [question] + entity_names
    hits = await search_book_sources(terms)
    result.source_search_results = [{k: v for k, v in h.items() if k != "text"} for h in hits]
    # Если книжных находок нет - внешние источники (только REVIEW-кандидаты).
    external: list[dict[str, Any]] = []
    if not hits:
        external = search_external_sources(
            question,
            entity_type=str(related_entities[0].get("entity_type", "concept")) if related_entities else "concept",
        )

    # ── 2. Candidate Extraction ─────────────────────────────────────
    raw_candidates: list[dict[str, Any]] = []
    for hit in hits or external:
        raw_candidates.extend(await extract_candidates_from_hit(hit, question))

    # ── 3-4. Validation + Editorial Gate ────────────────────────────
    for raw_cand in raw_candidates:
        validation = validate_candidate(raw_cand, related_entities, knowledge_contexts or [])
        decision = make_decision(validation, raw_cand)
        result.decisions.append(decision)

        cand = CandidateClaim(
            subject=str(raw_cand.get("subject", question)),
            predicate=str(raw_cand.get("predicate", "described_in")),
            object=str(raw_cand.get("source_ref", "")),
            source=str(raw_cand.get("source_ref", "")),
            evidence=str(raw_cand.get("evidence", "")),
            provenance={
                "source_ref": raw_cand.get("source_ref", ""),
                "priority": raw_cand.get("priority", ""),
                "chapter_title": raw_cand.get("chapter_title", ""),
                "question": question,
                "validation": validation,
                # Preserve epistemic_status / provenance category from original claim
                "epistemic_status": raw_cand.get("epistemic_status", raw_cand.get("provenance", {}).get("category")),
                "source_level": raw_cand.get("source_level", raw_cand.get("provenance", {}).get("source_level")),
                "derived_from": raw_cand.get("derived_from", raw_cand.get("provenance", {}).get("derived_from")),
                "origin": raw_cand.get("origin", raw_cand.get("provenance", {}).get("origin")),
                "entity_ids": raw_cand.get("entity_ids", raw_cand.get("provenance", {}).get("entity_ids")),
                "notes": raw_cand.get("notes", raw_cand.get("provenance", {}).get("notes")),
            },
            temporal_context={},
            confidence=float(validation.get("validation_score", 0.0)),
            evidence_fingerprint=_fingerprint(raw_cand),
        )
        result.candidates.append(cand)
        if decision.status == "ACCEPT":
            result.accepted.append(cand)
        elif decision.status == "REVIEW":
            result.review.append(cand)
        else:
            result.rejected.append(cand)

    # ── 5. Storage (только ACCEPT) ─────────────────────────────────
    if result.accepted:
        await _store_accepted(result, related_entities)

    # ── 6. Gap Recheck ──────────────────────────────────────────────
    result.gap_recheck = recheck_gap(question, result.accepted, related_entities, knowledge_contexts or [])
    result.summary = "accepted=%d review=%d rejected=%d gap_closed=%s" % (
        len(result.accepted),
        len(result.review),
        len(result.rejected),
        result.gap_recheck.get("gap_closed"),
    )
    return result


async def _store_accepted(result: ExpansionResult, related_entities) -> None:
    """Сохранить принятые кандидаты как ПРЕДЛОЖЕНИЯ (вне канона).

    Файл пишется в runtime-пространство (ASK_EXPANSIONS_DIR), а не в
    core/KNOWLEDGE: система предлагает — автор решает (принцип №4).
    В канонические знания эти записи попадают только отдельным решением
    владельца, а не по факту читательского вопроса.
    """
    try:
        from pathlib import Path

        from shared_config import settings as shared_settings
        from knowledge_expansion.store.knowledge_store import KnowledgeStore

        proposals_dir = Path(shared_settings.ASK_EXPANSIONS_DIR)
        output_path = proposals_dir / ASK_EXPANSIONS_FILENAME
        store = KnowledgeStore(knowledge_dir=proposals_dir)

        validated_items = [_to_validated(c, c.provenance.get("validation", {})) for c in result.accepted]
        save_result = await store.save(validated_items, output_path)
        result.storage = {
            "output_path": str(output_path),
            "scope": "proposal_queue",
            "items_saved": save_result.items_saved,
            "items_skipped": save_result.items_skipped,
            "graph_updates": save_result.graph_updates,
        }
    except Exception as exc:
        log.error("ask_expansion_storage_failed error=%s", exc)
        result.storage = {"error": str(exc)}
