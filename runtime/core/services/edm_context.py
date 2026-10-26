# -*- coding: utf-8 -*-
"""EDM-RES уровень 2 (Context Resolution) — детерминированные правила.

Реализует W1–W3 wiring'а (docs/ENTITY_RESOLUTION_RULES_2026-10-25.md §6)
утверждённого дизайна (GATE A CLOSED, 2026-10-25):

- **W1.** :func:`extract_intent` — чистая детерминированная функция
  (таблица intents §3, правила I1–I4). Без LLM: намерение определяется
  ВОПРОСОМ (I4), не ответом Pulse.
- **W2.** :func:`select_bundle` — фильтр кандидатов уровня 1
  (resolve_related_entities + явные ids + точные совпадения имён
  EDM-каталога) по желательным типам intent; правила R1–R4; бандл N=4 (D2);
  детерминированный порядок §4.1 (a: crosswalk-approved canonical_id,
  b: engine-кандидат/pilot-карточка, c: examples-карточка, e: entity_id
  asc); пустой пул + конкретный тип — детерминированный fallback по
  каталогу-индексу типа (v1, §5.4: единственный представитель = R1
  single); 0 — explicit gap (R3/B2), никогда «не той» сущности,
  никогда best guess.
- **W3.** :func:`filter_claims` — правила C1–C6 как фильтры над
  СУЩЕСТВУЮЩИМИ полями EDM-карточек (по §1.3): C1 факты (known +
  canon/author_canon/external_source), C2 реконструкции, C3
  medium/ai_model_artistic — только «визуальный образ (допущение)» в
  dialogue, C4 explicit UNKNOWN (required_unknown), C5 скрытие unknown
  вне required_unknown, C6 is_reconstruction — вся карточка = реконструкция.
- **W4.** :func:`approved_relations` — Tier-2 связи из crosswalk v2.1
  (`_load_approved_relations`, fail-closed B1).

Используется ТОЛЬКО за OWNER-GATE флагом ``EDM_RES_PILOT_ENABLED``
(edm_pilot.build_edm_dialogue_block / apply_edm_to_context). Флаг off —
модуль не вызывается, публичные контракты byte-идентичны legacy.
Мир не мутируется: только чтение каталога/кроссвоков.
"""

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger("hermes.edm_context")

#: Приоритет I2 (§3): конкретнее вопрос wins. `about` — финальный
#: fallback (I3).
INTENT_PRIORITY: tuple[str, ...] = (
    "where",
    "appearance",
    "clothing",
    "climate",
    "language",
    "character",
    "culture",
    "era",
    "cause",
    "about",
)

# Триггеры §3 (детерминированные regex по question, casefold). Без LLM.
_INTENT_TRIGGERS: dict[str, tuple[str, ...]] = {
    "where": (r"\bгде\b", r"располож", r"местност"),
    "appearance": (r"выглядел", r"внешн", r"стены", r"постройк", r"укрепл", r"архитектур"),
    "clothing": (r"\bобраз\b", r"одежд", r"носи", r"одет", r"\bв (чём|чем)\b"),
    "climate": (r"погод", r"климат", r"\bжар", r"\bзим", r"дожд", r"осадк"),
    "language": (r"язык",),
    "character": (r"\bкто\b", r"личност"),
    "culture": (r"верил", r"религи", r"ценност", r"обича", r"устройств", r"культур"),
    "era": (r"\bкогда\b", r"эпох", r"период", r"\bвремя"),
    "cause": (r"\bпочему\b", r"\bзачем\b"),
    "about": (r"расскаж", r"опиши", r"объясни", r"что (есть|такое)"),
}
_COMPILED: dict[str, tuple["re.Pattern[str]", ...]] = {
    intent: tuple(re.compile(p) for p in pats) for intent, pats in _INTENT_TRIGGERS.items()
}

#: §3 желательные типы по intent (None — нет type-маппинга: about/cause —
#: бандл всех названных (R4); era — special rule по time.epoch_ref).
INTENT_TYPES: dict[str, frozenset[str] | None] = {
    "where": frozenset({"location"}),
    "appearance": frozenset({"building", "location"}),
    "clothing": frozenset({"clothing"}),
    "climate": frozenset({"climate"}),
    "language": frozenset({"language"}),
    "character": frozenset({"character"}),
    "culture": frozenset({"culture"}),
    "era": None,
    "cause": None,
    "about": None,
}

#: §4.1 маппинг engine-категория → EDM-type (v1). Остальные категории
#: EDM-type в v1 не имеют: участвуют в бандле только как «контекст без
#: карточки» (описание engine-категории, без claims-фильтрации §4.2).
ENGINE_CATEGORY_TO_EDM_TYPE: dict[str, str] = {
    "geography": "location",
    "architecture": "building",
    "climate": "climate",
    "civilizations": "culture",
    "language": "language",
}

#: D2: бандл ограничен N=4.
BUNDLE_LIMIT = 4

#: C1: факты только из утверждённых provenance-классов.
KNOWN_PROVENANCE = frozenset({"canon", "author_canon", "external_source"})

#: Intent'ы без type-маппинга, где fallback по каталогу-индексу НЕ
#: применяется (только названные кандидаты; пусто — explicit gap, R3).
_NO_FALLBACK_INTENTS = frozenset({"about", "cause"})


def extract_intent(question: str) -> str:
    """W1: намерение вопроса (I1–I4, таблица §3). Чистая детерминированная функция.

    I1: совпал ровно один тип — он; I2: несколько — приоритет
    INTENT_PRIORITY (конкретнее wins); I3: ни одного — `about`;
    I4: только по ВОПРОСУ (ответ не влияет).
    """
    q = (question or "").strip().casefold()
    if not q:
        return "about"
    for intent in INTENT_PRIORITY:
        for pattern in _COMPILED.get(intent, ()):
            if pattern.search(q):
                return intent
    return "about"


def engine_type_to_edm(engine_type: str | None) -> str | None:
    """§4.1: engine-категория → EDM-type (v1-маппинг; None — нет маппинга)."""
    if not engine_type:
        return None
    return ENGINE_CATEGORY_TO_EDM_TYPE.get(str(engine_type).casefold())


def _card_edm_type(card: dict | None) -> str | None:
    if not card:
        return None
    t = (card.get("identity") or {}).get("type")
    return str(t).casefold() if t else None


def _card_has_epoch(card: dict | None) -> bool:
    """Special rule intent `era`: эпоха установлена, если time.epoch_ref непусто."""
    if not card:
        return False
    return bool((card.get("time") or {}).get("epoch_ref"))


def _origin_rank(eid: str, origin: str, approved_ids: set[str]) -> int:
    """§4.1 порядок бандла: (a) crosswalk-approved canonical_id — первым;
    (b) engine-кандидат (включая pilot-карточки — engine-поисходные);
    (c) examples-карточка. (d) name_coverage публичным контрактом
    resolve_related_entities не отдаётся — детерминированный tie-breaker
    (e) entity_id asc."""
    if eid in approved_ids:
        return 0
    return 2 if origin == "examples" else 1


def approved_relations() -> list[dict]:
    """W4: Tier-2 owner-утверждённые связи (crosswalk v2.1, fail-closed B1)."""
    try:
        from narrative_engine.world_model import _load_approved_relations

        return _load_approved_relations()
    except Exception as exc:  # crosswalk недоступен — связей нет, мир не выдумывается
        log.warning("edm_context_relations_unavailable error=%s", exc)
        return []


def _approved_canonical_ids() -> set[str]:
    """approved mapping'и crosswalk v2 → set canonical_id (ранг (a) порядка §4.1)."""
    try:
        from narrative_engine.world_model import _load_approved_crosswalk

        ids: set[str] = set()
        for target_list in _load_approved_crosswalk().values():
            ids.update(target_list)
        return ids
    except Exception as exc:  # fail-closed: без кросскока нет rank-0 позиций
        log.warning("edm_context_crosswalk_unavailable error=%s", exc)
        return set()


def select_bundle(
    question: str,
    candidates: list[dict[str, Any]],
    catalog: dict[str, dict] | None = None,
    explicit_ids: list[str] | None = None,
) -> dict[str, Any]:
    """W2: фильтрует кандидатов уровня 1 по §3/§4 → бандл/одиночка/gap.

    candidates — уровень 1: ``resolve_related_entities`` ({entity_id,
    entity_type (категория engine), name, description}), точные совпадения
    имён EDM-каталога и явные ids — что передаёт вызывающий (strict match,
    никакого fuzzy). Возвращает dict: intent, status (RESOLVED/AMBIGUOUS/
    GAP — D1), entity_ids (порядок §4.1, ≤ N=4), dropped (срез N=4),
    relations (Tier-2 связи, задевающие бандл — W4/B1), context_only
    (engine-кандидаты без EDM-карточки: «контекст без карточки», без
    claims-фильтрации §4.2) и gap (explicit граница знания, B2).
    """
    intent = extract_intent(question)
    catalog = catalog if catalog is not None else {}
    desired = INTENT_TYPES.get(intent)

    # Пул: названные кандидаты (уровень 1) — без fuzzy, без best guess (B1).
    pool: dict[str, dict[str, Any]] = {}
    for cand in candidates or []:
        eid = str((cand or {}).get("entity_id") or "").strip()
        if not eid:
            continue
        engine_type = cand.get("entity_type")
        card = catalog.get(eid)
        edm_type = _card_edm_type(card) or engine_type_to_edm(engine_type)
        if _qualifies(intent, desired, engine_type, edm_type, card):
            pool[eid] = {
                "entity_id": eid,
                "origin": cand.get("origin") or ("catalog" if card else "engine"),
            }
    for eid in explicit_ids or []:
        eid = str(eid).strip()
        if eid:
            pool.setdefault(eid, {"entity_id": eid, "origin": "explicit"})

    # Fallback (v1, §5.4): пустой пул + конкретный тип → детерминированный
    # индекс каталога по желательному типу (about/cause — только названные;
    # era — special rule по time.epoch_ref).
    if not pool and intent not in _NO_FALLBACK_INTENTS and (desired is not None or intent == "era"):
        catalog_entities = catalog or _default_catalog()
        for eid in sorted(catalog_entities):
            card = catalog_entities[eid]
            if intent == "era" and not _card_has_epoch(card):
                continue
            if intent != "era" and _card_edm_type(card) not in desired:
                continue
            pool[eid] = {"entity_id": eid, "origin": _origin_of(eid, catalog_entities)}

    approved_ids = _approved_canonical_ids()
    ordered = sorted(
        pool.values(),
        key=lambda c: (_origin_rank(c["entity_id"], c["origin"], approved_ids), c["entity_id"]),
    )
    bundle_ids = [c["entity_id"] for c in ordered]
    dropped = bundle_ids[BUNDLE_LIMIT:]
    bundle_ids = bundle_ids[:BUNDLE_LIMIT]

    if not bundle_ids:
        status, gap = "GAP", _gap_note(intent, desired)
    elif len(bundle_ids) == 1:
        status, gap = "RESOLVED", None
    else:
        status, gap = "AMBIGUOUS", None

    return {
        "intent": intent,
        "status": status,
        "entity_ids": bundle_ids,
        "dropped": dropped,
        "context_only": [i for i in bundle_ids if i not in catalog],
        "relations": _relations_for_bundle(bundle_ids),
        "gap": gap,
    }


def _qualifies(intent: str, desired, engine_type, edm_type: str | None, card: dict | None) -> bool:
    """§4.1: кандидат «подходит по типу» (identity.type EDM-карточки или
    engine-категория-маппинг входит в желательные типы intent)."""
    if intent in ("about", "cause"):
        return True  # R4: бандл всех названных кандидатов
    if intent == "era":
        return bool(card and _card_has_epoch(card))
    if desired is None:
        return True
    return edm_type in desired


def _gap_note(intent: str, desired) -> str:
    """B2: граница знания — explicit формулировка, не дефолт."""
    type_names = ", ".join(sorted(desired)) if desired else "подходящая"
    return (
        f"Для намерения {intent!r} подходящая сущность (типы: {type_names}) "
        "не установлена в утверждённых данных — связи не выводятся (B1 fail-closed)."
    )


def _default_catalog() -> dict[str, dict]:
    try:
        from core.services.edm_pilot import get_entities

        return get_entities()
    except Exception as exc:
        log.warning("edm_context_catalog_unavailable error=%s", exc)
        return {}


def _origin_of(eid: str, catalog: dict[str, dict]) -> str:
    try:
        from core.services.edm_pilot import entity_sources

        return entity_sources().get(eid, "catalog")
    except Exception:
        return "catalog"


def _relations_for_bundle(bundle_ids: list[str]) -> list[dict]:
    """Tier-2 связи, задевающие бандл (source или target в бандле).
    B1: нет утверждённой связи — связи нет; default не порождается."""
    rels = []
    for r in approved_relations():
        if r.get("source_id") in bundle_ids or r.get("target_id") in bundle_ids:
            rels.append(r)
    return rels


def filter_claims(entity: dict[str, Any], mode: str = "dialogue") -> list[dict[str, Any]]:
    """W3: правила C1–C6 как фильтры над СУЩЕСТВУЮЩИМИ полями EDM-карточки.

    Возвращает claims с меткой ``c_rule`` (C1/C2/C3/C4) и ``show`` —
    проекцией на режим (dialogue: medium → «визуальный образ (допущение)»
    (G10); visual: допускается с явной меткой). C5 — unknown вне
    required_unknown НЕ возвращается. C6 — card-level флаг
    ``card_reconstruction`` (вся карточка входит как реконструкция).
    """
    identity = entity.get("identity") or {}
    required_unknown = set(((entity.get("constraints") or {}).get("required_unknown")) or [])
    card_reconstruction = bool(identity.get("is_reconstruction"))  # C6
    out: list[dict[str, Any]] = []
    for c in entity.get("claims") or []:
        if not isinstance(c, dict):
            continue
        status = c.get("status")
        pc = c.get("provenance_class")
        medium = bool(c.get("medium"))
        if medium or pc == "ai_model_artistic":
            # C3: art-model — никогда как факт книги
            view = "visual_image" if mode == "dialogue" else "labeled_visual"
            out.append({**c, "c_rule": "C3", "show": view})
        elif status == "known" and pc in KNOWN_PROVENANCE:
            out.append({**c, "c_rule": "C1", "show": "fact"})
        elif status == "reconstructed":
            out.append({**c, "c_rule": "C2", "show": "reconstruction"})
        elif status == "unknown" and c.get("path") in required_unknown:
            out.append({**c, "c_rule": "C4", "show": "explicit_unknown"})
        # C5: unknown вне required_unknown — не показывается (не выдумывать)
    for c in out:
        c["card_reconstruction"] = card_reconstruction
    return out


__all__ = [
    "INTENT_PRIORITY",
    "INTENT_TYPES",
    "ENGINE_CATEGORY_TO_EDM_TYPE",
    "BUNDLE_LIMIT",
    "KNOWN_PROVENANCE",
    "extract_intent",
    "engine_type_to_edm",
    "select_bundle",
    "filter_claims",
    "approved_relations",
]
