# -*- coding: utf-8 -*-
"""
Stage 4A — пилотный явный цикл GAP → Stage 2 → World Model → Gap Recheck.

Точка входа: run_gap_pilot(gap, apply=False) — вызывается ТОЛЬКО явно (await).
Никакой автоматики: цикл не запускается из детектора Stage 3, роутов или cron.

apply=False (по умолчанию) — dry-run: план проекции + явный Stage 2 без записи.
apply=True — точечная запись одного entity_id в core/CORE/WORLD_MODEL/<CATEGORY>.json
с timestamped .bak-бэкапом (паттерн scripts/build_world_model.py), инвалидацией
singleton-кэшей WorldModelExt/WorldEngine и повторным сканом пробелов сущности.

Принципы пилота (Stage 4A):
- description проецируется детерминированно из KC claims (Knowledge Core) с
  provenance-фильтром: в description попадают только AUTHOR_CANON / CANON /
  EXTERNAL_SOURCE / DERIVED claims. HYPOTHESIS / USER_HYPOTHESIS /
  FUTURE_EXTRAPOLATION / SYSTEM_INTERPRETATION / RECONSTRUCTION в description
  НЕ попадают — каждое исключение фиксируется в excluded с причиной.
- Релевантность claims: скоуп claim на сущность (source_ref вида
  ARCHAEOLOGY.json:<ключ>:... / world_model:<entity_id>:...) ИЛИ наличие стема
  имени сущности в тексте. Нерелевантные цитаты отбрасываются (анти-ложность).
- description не пишется поверх непустого (gap-тип missing_description);
  повторный запуск идемпотентен.
- Provenance не апгрейдится: UNKNOWN/пустой provenance_category получает
  фактическую категорию доминирующего источника проекции; исходные
  provenance_notes сохраняются, запись пилота добавляется через " | ".
- Relationships пишутся ТОЛЬКО из явных book_connection-claims с категорией
  AUTHOR_CANON / CANON / EXTERNAL_SOURCE / RECONSTRUCTION (у каждого entry
  сохраняется provenance_category и source_ref). Hypothesis-связи не пишутся.
  Цель связи — реально существующая сущность WORLD_MODEL; неоднозначность
  имён разрешается детерминированным tie-break (короче id), без выдумывания.
- Stage 2 в пилоте запускается явно и параллельно: результат (ACCEPT/REVIEW/
  REJECT, storage в ASK_EXPANSIONS.json) фиксируется в отчёте. Автоматического
  переноса Stage 2 candidates в World Model НЕТ — проекция идёт только из
  верифицированных KC claims.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from narrative_engine.world_model_ext import (
    WORLD_MODEL_DIR,
    WorldModelExt,
    get_world_model_ext,
    invalidate_world_model_ext,
)
from narrative_engine.world_engine import (
    get_world_engine,
    invalidate_world_engine,
)

from core.services.ask_expansion_orchestrator import expand as stage2_expand
from core.services.knowledge_core_context import gather_knowledge_core_context
from core.services.world_gap_detector import WorldGap, WorldGapDetector

log = logging.getLogger("hermes.world_gap_pilot")

PILOT_NOTE_PREFIX = "Stage 4A pilot"

# Группы KC claims, из которых пилот может проецировать description.
PROJECTABLE_CLAIM_GROUPS: tuple[str, ...] = (
    "book_claims",
    "archaeology_claims",
)

# Категории provenance, допустимые в description (не смешивать происхождение).
DESCRIPTION_CATEGORIES: frozenset[str] = frozenset(("AUTHOR_CANON", "CANON", "EXTERNAL_SOURCE", "DERIVED"))

# Категории, из которых допустимо писать relationships (RECONSTRUCTION — с
# сохранением метки; HYPOTHESIS/USER_HYPOTHESIS/FUTURE/SYSTEM — не пишутся).
RELATIONSHIP_CATEGORIES: frozenset[str] = frozenset(("AUTHOR_CANON", "CANON", "EXTERNAL_SOURCE", "RECONSTRUCTION"))

# Лимиты книжных цитат в description.
DESCRIPTION_MAX_QUOTES = 2
DESCRIPTION_MAX_QUOTE_CHARS = 300
DESCRIPTION_MAX_TOTAL_CHARS = 1200

# Объединение категорий, которые вообще могут участвовать в проекции
# (description ИЛИ relationships); фильтр по назначению — в компоновщиках.
PROJECTABLE_ANY_CATEGORIES: frozenset[str] = DESCRIPTION_CATEGORIES | RELATIONSHIP_CATEGORIES


# ── Models ────────────────────────────────────────────────────────


@dataclass
class PlannedDescription:
    """Спланированное описание: детерминированная проекция KC claims."""

    text: str = ""
    source_refs: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


@dataclass
class PlannedRelationship:
    """Спланированная связь с сохранённым происхождением."""

    type: str
    target_id: str
    description: str
    provenance_category: str
    source_ref: str


@dataclass
class GapClosurePlan:
    """План точечного закрытия пробела одной сущности."""

    entity_id: str
    description: Optional[PlannedDescription] = None
    relationships: list[PlannedRelationship] = field(default_factory=list)
    provenance_category: Optional[str] = None  # только при апдейте UNKNOWN
    provenance_note: str = ""
    excluded_claims: list[dict[str, Any]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


# ── Relevance / provenance helpers ────────────────────────────────


def _name_stems(name: str) -> set[str]:
    """Стемы имени сущности (токены >=5 символов, префикс 5)."""
    stems: set[str] = set()
    for token in re.findall(r"[а-яёa-z0-9]+", str(name or "").lower()):
        if len(token) >= 5:
            stems.add(token[:5])
    return stems


def _claim_category(claim: dict[str, Any]) -> str:
    provenance = claim.get("provenance")
    if not isinstance(provenance, dict):
        return "UNKNOWN"
    return str(provenance.get("category") or "UNKNOWN").upper()


def _entity_key(entity_id: str) -> str:
    """Ключ сущности в ARCHAEOLOGY.json: id без категориального префикса."""
    _, _, key = str(entity_id).partition("_")
    return key


def _claim_is_entity_scoped(source_ref: str, entity_id: str, category: str) -> bool:
    ref = str(source_ref or "")
    if ref.startswith(f"world_model:{entity_id}:"):
        return True
    if category == "geography" and ref.startswith("ARCHAEOLOGY.json:"):
        parts = ref.split(":")
        return len(parts) >= 2 and parts[1] == _entity_key(entity_id)
    return False


def _claim_is_relevant(claim: dict[str, Any], entity_id: str, entity_name: str, category: str) -> bool:
    """Claim релевантен сущности: скоуп по source_ref или стем имени в тексте."""
    if _claim_is_entity_scoped(str(claim.get("source_ref") or ""), entity_id, category):
        return True
    text_low = str(claim.get("text") or "").lower()
    if not text_low:
        return False
    return any(stem in text_low for stem in _name_stems(entity_name))


def _arch_field(source_ref: str) -> str:
    """Поле археологического claim: 'ARCHAEOLOGY.json:<ключ>:<field>'."""
    parts = str(source_ref or "").split(":")
    return parts[2] if len(parts) >= 3 else ""


def _clean_fact_text(text: str) -> str:
    """'age: Одно из древнейших...' -> 'Одно из древнейших...'."""
    raw = str(text or "").strip()
    if ":" in raw:
        head, _, tail = raw.partition(":")
        if head.isascii() and head.strip() and tail.strip():
            return tail.strip()
    return raw


# ── Description projection ────────────────────────────────────────


def _collect_claims(
    gap: WorldGap,
    contexts: list[dict[str, Any]],
) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, Any]]]:
    """Разложить KC claims на (relevant, excluded) с причинами.

    excluded фиксирует каждую отброшенную claim: не-проектируемая категория
    (смешение происхождения запрещено) либо нерелевантность сущности.
    """
    relevant: list[tuple[str, dict[str, Any]]] = []
    excluded: list[dict[str, Any]] = []
    for context in contexts or []:
        for group in PROJECTABLE_CLAIM_GROUPS:
            for claim in context.get(group) or []:
                if not isinstance(claim, dict) or not str(claim.get("text") or "").strip():
                    continue
                category = _claim_category(claim)
                source_ref = str(claim.get("source_ref") or "")
                if category not in PROJECTABLE_ANY_CATEGORIES:
                    excluded.append(
                        {
                            "source_ref": source_ref,
                            "category": category,
                            "reason": "category_not_projectable_into_description",
                            "text_preview": str(claim.get("text"))[:120],
                        }
                    )
                    continue
                if not _claim_is_relevant(claim, gap.entity_id, gap.entity_name, gap.category):
                    excluded.append(
                        {
                            "source_ref": source_ref,
                            "category": category,
                            "reason": "not_relevant_to_entity",
                            "text_preview": str(claim.get("text"))[:120],
                        }
                    )
                    continue
                relevant.append((group, claim))
    return relevant, excluded


def compose_description(
    gap: WorldGap,
    relevant: list[tuple[str, dict[str, Any]]],
) -> Optional[PlannedDescription]:
    """Детерминированная компоновка description из релевантных claims.

    Два источника (оба верифицированы provenance-фильтром):
    1) археологические структурированные facts (location/dating/facts.*);
    2) книжные цитаты AUTHOR_CANON, упоминающие сущность (verbatim, лимиты).
    """
    parts: list[str] = []
    refs: list[str] = []
    categories: list[str] = []

    def _remember(ref: str, cat: str) -> None:
        if ref and ref not in refs:
            refs.append(ref)
        if cat and cat not in categories:
            categories.append(cat)

    fact_claims: list[tuple[str, dict[str, Any]]] = []
    for group, claim in relevant:
        if group != "archaeology_claims":
            continue
        if _claim_category(claim) not in DESCRIPTION_CATEGORIES:
            continue  # RECONSTRUCTION и т.п. — только для relationships
        field_name = _arch_field(str(claim.get("source_ref") or ""))
        if field_name.startswith("facts.") or field_name in (
            "location",
            "dating",
            "significance",
        ):
            fact_claims.append((field_name, claim))

    def _field_rank(item: tuple[str, dict[str, Any]]) -> tuple[int, str]:
        field_name = item[0]
        order = {"location": 0, "dating": 1, "significance": 3}
        if field_name in order:
            return (order[field_name], "")
        return (2, field_name)

    for field_name, claim in sorted(fact_claims, key=_field_rank):
        text = _clean_fact_text(str(claim.get("text") or ""))
        if not text:
            continue
        if field_name == "dating":
            parts.append(f"Датировка: {text}")
        else:
            parts.append(text)
        _remember(str(claim.get("source_ref") or ""), _claim_category(claim))

    quotes: list[str] = []
    for group, claim in relevant:
        if group != "book_claims":
            continue
        if _claim_category(claim) not in DESCRIPTION_CATEGORIES:
            continue
        text = str(claim.get("text") or "").strip()
        if not text or len(text) > DESCRIPTION_MAX_QUOTE_CHARS:
            continue
        if text in quotes:
            continue
        quotes.append(text)
        _remember(str(claim.get("source_ref") or ""), _claim_category(claim))
        if len(quotes) >= DESCRIPTION_MAX_QUOTES:
            break
    for quote in quotes:
        parts.append(f"«{quote}»")

    if not parts:
        return None

    text = " ".join(p.strip() for p in parts if p.strip())
    if len(text) > DESCRIPTION_MAX_TOTAL_CHARS:
        text = text[:DESCRIPTION_MAX_TOTAL_CHARS].rstrip() + "…"
    return PlannedDescription(text=text, source_refs=refs, categories=categories)


# ── Relationship planning ─────────────────────────────────────────


def _resolve_relationship_target(
    claim_text: str,
    gap: WorldGap,
    wm: Any,
) -> tuple[Optional[str], str]:
    """Разрешить цель связи по тексту claim против реальных сущностей WORLD_MODEL.

    Два уровня совпадения (детерминированные):
    1) exact_name — полное имя сущности (lower) как подстрока текста claim;
    2) word_stem — фолбэк на словоформы: 5-символьные префиксы токенов имени
       (_name_stems) совпадают с префиксами слов claim длиной >= 5 (например,
       «Синташту» (вин. п.) против имени «Синташта»).
    Exact-совпадения всегда имеют приоритет над stem-совпадениями. Внутри
    уровня — самое длинное имя, затем дубли имён (region_/geo_) ->
    детерминированный tie-break: короче id, затем лексикографический порядок.
    Возвращает (target_id | None, reason).
    """
    text_low = str(claim_text or "").lower()
    word_stems = {w[:5] for w in re.findall(r"[а-яёa-z0-9]+", text_low) if len(w) >= 5}
    matches: list[tuple[str, str, str]] = []
    for category in wm.get_categories():
        for entity in wm.get_category(category) or []:
            if not isinstance(entity, dict):
                continue
            other_id = str(entity.get("id") or "")
            name = str(entity.get("name") or "").strip()
            if not other_id or not name or other_id == gap.entity_id:
                continue
            name_low = name.lower()
            if len(name_low) >= 4 and name_low in text_low:
                matches.append((other_id, name, "exact_name"))
            elif _name_stems(name) & word_stems:
                matches.append((other_id, name, "word_stem"))
    if not matches:
        return None, "no_existing_entity_mentioned_in_claim"
    matches.sort(key=lambda m: (0 if m[2] == "exact_name" else 1, -len(m[1]), len(m[0]), m[0]))
    best_level = matches[0][2]
    best = [m for m in matches if m[2] == best_level]
    best.sort(key=lambda m: (len(m[0]), m[0]))
    reason = "resolved_by_exact_name_in_claim" if best_level == "exact_name" else "resolved_by_word_stem_in_claim"
    return best[0][0], reason


def plan_relationships(
    gap: WorldGap,
    relevant: list[tuple[str, dict[str, Any]]],
    wm: Any,
    excluded: list[dict[str, Any]],
) -> list[PlannedRelationship]:
    """Спланировать связи только из явных book_connection-claims.

    Пишутся claims категории AUTHOR_CANON / CANON / EXTERNAL_SOURCE /
    RECONSTRUCTION (метка provenance сохраняется в entry). Hypothesis-подобные
    категории фиксируются в excluded и НЕ пишутся в World Model.
    """
    plans: list[PlannedRelationship] = []
    seen: set[tuple[str, str]] = set()
    for _group, claim in relevant:
        source_ref = str(claim.get("source_ref") or "")
        if not source_ref.endswith(":book_connection"):
            continue
        category = _claim_category(claim)
        if category not in RELATIONSHIP_CATEGORIES:
            excluded.append(
                {
                    "source_ref": source_ref,
                    "category": category,
                    "reason": "hypothesis_relation_not_written",
                    "text_preview": str(claim.get("text"))[:120],
                }
            )
            continue
        target_id, reason = _resolve_relationship_target(str(claim.get("text") or ""), gap, wm)
        if target_id is None:
            excluded.append(
                {
                    "source_ref": source_ref,
                    "category": category,
                    "reason": reason,
                    "text_preview": str(claim.get("text"))[:120],
                }
            )
            continue
        key = ("historical", target_id)
        if key in seen:
            continue
        seen.add(key)
        plans.append(
            PlannedRelationship(
                type="historical",
                target_id=target_id,
                description=_clean_fact_text(str(claim.get("text") or "")),
                provenance_category=category,
                source_ref=source_ref,
            )
        )
    return plans


# ── Provenance planning ───────────────────────────────────────────


def plan_provenance(
    gap: WorldGap,
    entity: dict[str, Any],
    description: Optional[PlannedDescription],
    relationships: list[PlannedRelationship],
    stamp: str,
) -> tuple[Optional[str], str]:
    """Апдейт provenance БЕЗ апгрейда категории.

    UNKNOWN/пустой provenance_category -> фактическая категория доминирующего
    источника проекции description (ties: AUTHOR_CANON > CANON > EXTERNAL_SOURCE
    > DERIVED; пустая проекция -> SYSTEM_INTERPRETATION, т.е. происхождение
    самой записи, а не канон). Исходные notes сохраняются.
    Возвращает (new_category | None, note_to_append).
    """
    current = str(entity.get("provenance_category") or "").strip().upper()
    note_bits: list[str] = []
    if description is not None:
        note_bits.append(
            "описание проецировано из KC claims (%s; refs: %s)"
            % (
                ",".join(description.categories) or "no-category",
                ";".join(description.source_refs) or "-",
            )
        )
    if relationships:
        note_bits.append("связи из book_connection-claims: %s" % ";".join(f"{r.type}->{r.target_id}" for r in relationships))
    note = ""
    if note_bits:
        note = "%s (%s): %s" % (PILOT_NOTE_PREFIX, stamp, "; ".join(note_bits))

    if current not in ("", "UNKNOWN"):
        return None, note

    if description is not None and description.categories:
        order = ["AUTHOR_CANON", "CANON", "EXTERNAL_SOURCE", "DERIVED"]
        counter = Counter(description.categories)
        new_category = sorted(counter.items(), key=lambda kv: (-kv[1], order.index(kv[0]) if kv[0] in order else 99))[0][0]
    else:
        new_category = "SYSTEM_INTERPRETATION"
    return new_category, note


def build_gap_closure_plan(
    gap: WorldGap,
    contexts: list[dict[str, Any]],
    wm: Any,
    *,
    stamp: str,
) -> GapClosurePlan:
    """Собрать полный точечный план закрытия пробела (read-only)."""
    entity = wm.get_entity(gap.category, gap.entity_id)
    plan = GapClosurePlan(entity_id=gap.entity_id)
    if entity is None:
        plan.reasons.append("entity_not_found_in_world_model")
        return plan

    relevant, excluded = _collect_claims(gap, contexts)
    plan.excluded_claims = excluded
    if not relevant:
        plan.reasons.append("no_relevant_projectable_claims")
    else:
        if not str(entity.get("description") or "").strip():
            plan.description = compose_description(gap, relevant)
            if plan.description is None:
                plan.reasons.append("no_description_material_after_filters")
        else:
            plan.reasons.append("description_already_present_not_overwritten")
        plan.relationships = plan_relationships(gap, relevant, wm, plan.excluded_claims)

    new_category, note = plan_provenance(gap, entity, plan.description, plan.relationships, stamp)
    plan.provenance_category = new_category
    plan.provenance_note = note
    return plan


# ── Writer (точечная запись в WORLD_MODEL) ────────────────────────


def _world_model_file_for(category: str, world_model_dir: Optional[Path]) -> Path:
    base = Path(world_model_dir) if world_model_dir else WORLD_MODEL_DIR
    return base / f"{str(category).upper()}.json"


def apply_plan_to_world_model(
    gap: WorldGap,
    plan: GapClosurePlan,
    *,
    world_model_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Точечно применить план к одной сущности WORLD_MODEL (explicit-only).

    Идемпотентно: description пишется только если пуст; relationships
    дописываются с дедупом по (type, target_id); provenance_notes
    дописываются через " | ". Перед записью — timestamped .bak-бэкап
    (паттерн scripts/build_world_model.py). После записи инвалидируются
    singleton-кэши WorldModelExt и WorldEngine (перечитают файлы).
    """
    path = _world_model_file_for(gap.category, world_model_dir)
    if not path.exists():
        return {"written": False, "reason": f"file_not_found:{path}"}

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        return {"written": False, "reason": "unexpected_file_structure"}

    entity = None
    for item in data:
        if isinstance(item, dict) and item.get("id") == gap.entity_id:
            entity = item
            break
    if entity is None:
        return {"written": False, "reason": "entity_not_found"}

    changed_fields: list[str] = []

    if plan.description is not None and not str(entity.get("description") or "").strip():
        entity["description"] = plan.description.text
        changed_fields.append("description")

    if plan.relationships:
        existing = entity.get("relationships")
        if not isinstance(existing, list):
            existing = []
        known = {(str(r.get("type") or ""), str(r.get("target_id") or "")) for r in existing if isinstance(r, dict)}
        appended = 0
        for rel in plan.relationships:
            key = (rel.type, rel.target_id)
            if key in known:
                continue
            known.add(key)
            existing.append(
                {
                    "type": rel.type,
                    "target_id": rel.target_id,
                    "description": rel.description,
                    "provenance_category": rel.provenance_category,
                    "source_ref": rel.source_ref,
                }
            )
            appended += 1
        if appended:
            entity["relationships"] = existing
            changed_fields.append("relationships")

    if plan.provenance_category:
        entity["provenance_category"] = plan.provenance_category
        changed_fields.append("provenance_category")

    if plan.provenance_note:
        current_notes = str(entity.get("provenance_notes") or "").strip()
        # Идемпотентность: повторный пилотный запуск не плодит пометки.
        if plan.provenance_note not in current_notes and PILOT_NOTE_PREFIX not in current_notes:
            entity["provenance_notes"] = f"{current_notes} | {plan.provenance_note}" if current_notes else plan.provenance_note
            changed_fields.append("provenance_notes")

    if not changed_fields:
        return {"written": False, "reason": "no_changes_needed"}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.parent / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, backup)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Инвалидация singleton-кэшей: WorldModelExt/WorldEngine перечитают файлы.
    invalidate_world_model_ext()
    invalidate_world_engine()

    log.info(
        "world_gap_pilot_written entity=%s fields=%s backup=%s",
        gap.entity_id,
        ",".join(changed_fields),
        backup.name,
    )
    return {
        "written": True,
        "file": str(path),
        "backup": str(backup),
        "changed_fields": changed_fields,
    }


# ── Pilot cycle (explicit-only entry point) ───────────────────────


def _gaps_for_entity(
    entity: dict[str, Any],
    category: str,
    *,
    engine: Any = None,
    wm: Any = None,
) -> list[dict[str, Any]]:
    """Список пробелов сущности через правила Stage 3 детектора.

    Использует тот же _check_entity, что и detect_world_gaps(), без полного
    скана всей модели (пилот работает с одной сущностью).
    """
    detector = WorldGapDetector(engine=engine, wm=wm)
    return [{"gap_type": g.gap_type, "severity": g.severity, "description": g.description} for g in detector._check_entity(entity, category)]


async def run_gap_pilot(
    gap: WorldGap,
    *,
    apply: bool = False,
    world_model_dir: Optional[Path] = None,
    engine: Any = None,
    wm: Any = None,
) -> dict[str, Any]:
    """Явный пилотный цикл: GAP → Stage 2 → World Model → Gap Recheck.

    Не запускается автоматически. apply=False — dry-run (без записи).
    Stage 2 вызывается явно и его падение не роняет цикл (фиксируется
    в отчёте); проекция в World Model идёт только из верифицированных
    KC claims с provenance-фильтром.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    wm = wm or get_world_model_ext()
    report: dict[str, Any] = {
        "pilot": "stage4a_world_gap_pilot",
        "stamp": stamp,
        "apply": apply,
        "entity_id": gap.entity_id,
        "entity_name": gap.entity_name,
        "category": gap.category,
        "gap_type": gap.gap_type,
    }

    entity = wm.get_entity(gap.category, gap.entity_id)
    if entity is None:
        report["error"] = "entity_not_found_in_world_model"
        return report

    report["gaps_before"] = _gaps_for_entity(entity, gap.category, engine=engine, wm=wm)

    # KC-claims по entity_id (без name-поиска — чтобы не подхватить соседей).
    try:
        contexts = gather_knowledge_core_context([{"entity_id": gap.entity_id, "name": gap.entity_name}])
    except Exception as exc:  # noqa: BLE001
        contexts = []
        report["kc_gather_error"] = str(exc)

    # Явный Stage 2 (не автоматика; падение фиксируется, цикл продолжает).
    stage2_summary: dict[str, Any] = {"ran": False}
    if gap.can_auto_stage2:
        try:
            result = await stage2_expand(
                question=f"Расскажи о {gap.entity_name}",
                related_entities=[{"entity_id": gap.entity_id, "name": gap.entity_name}],
                knowledge_contexts=contexts,
            )
            stage2_summary = {
                "ran": True,
                "accepted": len(getattr(result, "accepted", []) or []),
                "review": len(getattr(result, "review", []) or []),
                "rejected": len(getattr(result, "rejected", []) or []),
                "summary": getattr(result, "summary", ""),
                "storage": getattr(result, "storage", {}) or {},
            }
        except Exception as exc:  # noqa: BLE001
            stage2_summary = {"ran": True, "error": str(exc)}
    else:
        stage2_summary = {"ran": False, "reason": "gap_not_stage2_eligible"}
    report["stage2"] = stage2_summary

    plan = build_gap_closure_plan(gap, contexts, wm, stamp=stamp)
    report["plan"] = {
        "description": (
            {
                "text": plan.description.text,
                "source_refs": plan.description.source_refs,
                "categories": plan.description.categories,
            }
            if plan.description
            else None
        ),
        "relationships": [
            {
                "type": r.type,
                "target_id": r.target_id,
                "description": r.description,
                "provenance_category": r.provenance_category,
                "source_ref": r.source_ref,
            }
            for r in plan.relationships
        ],
        "provenance_category": plan.provenance_category,
        "provenance_note": plan.provenance_note,
        "excluded_claims": plan.excluded_claims,
        "reasons": plan.reasons,
    }

    if apply:
        applied = apply_plan_to_world_model(gap, plan, world_model_dir=world_model_dir)
        report["applied"] = applied
        if applied.get("written"):
            if world_model_dir is not None:
                wm_after: Any = WorldModelExt(Path(world_model_dir))
            else:
                wm_after = get_world_model_ext()
            engine_after = engine if engine is not None else get_world_engine()
            entity_after = wm_after.get_entity(gap.category, gap.entity_id)
            report["gaps_after"] = _gaps_for_entity(entity_after, gap.category, engine=engine_after, wm=wm_after) if entity_after is not None else []
            before_types = {g["gap_type"] for g in report["gaps_before"]}
            after_types = {g["gap_type"] for g in report["gaps_after"]}
            report["gaps_closed"] = sorted(before_types - after_types)
            report["gaps_remaining"] = sorted(after_types)
            try:
                contexts_after = gather_knowledge_core_context([{"entity_id": gap.entity_id, "name": gap.entity_name}])
                report["kc_world_claims_after"] = sum(len(c.get("world_claims") or []) for c in contexts_after)
            except Exception as exc:  # noqa: BLE001
                report["kc_world_claims_after"] = None
                report["kc_recheck_error"] = str(exc)
    else:
        report["applied"] = {"written": False, "reason": "dry_run_apply_false"}

    return report


__all__ = [
    "GapClosurePlan",
    "PlannedDescription",
    "PlannedRelationship",
    "apply_plan_to_world_model",
    "build_gap_closure_plan",
    "compose_description",
    "plan_provenance",
    "plan_relationships",
    "run_gap_pilot",
]
