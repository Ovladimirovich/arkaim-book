# -*- coding: utf-8 -*-
"""EDM-RES pilot — Entity Description Model в production-швах /book/ask и /visualize.

OWNER-GATE: ``shared_config.settings.EDM_RES_PILOT_ENABLED`` (default False).
При flag off этот сервис не вызывается маршрутами — публичные контракты
byte-identичны legacy.

Модули ``core/CORE/ENTITY_MODEL`` (resolutions / operations / world_feed /
сущности) загружаются ИМПОРТ ПО ПУТИ через importlib: каталог имеет
регистрационный регистр (ENTITY_MODEL), поэтому штатный ``import
entity_model...`` нестабилен между платформами — тот же приём, что в
runtime-тестах EDM.

Внутри:
- :func:`get_entities` — индекс сущностей (pilot/ + examples/), mtime-кэш;
- :func:`match_entities` — строгий матчинг (id / имена / явные ids из запроса);
- :func:`resolve_scene_location` — E2 авто-матчинг: location-строка →
  engine/crosswalk → region_* → EDM (детерминированно, fail-closed);
- :func:`build_edm_dialogue_block` — слоистое описание для /book/ask;
- :func:`apply_edm_to_context` — наполнение VisualContext (world_feed.apply_edm);
- :func:`compose_provider` — composite t1+EDM провайдер Knowledge Context
  (инжекция через существующую цепь voice, без нового параллельного механизма);
- :func:`enabled` — гет флаг'а (читается на каждом вызове, как STAGE2).
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

log = logging.getLogger("hermes.edm_pilot")

# (filename, module-cache key)
_RESOLUTIONS = "resolutions.py"
_OPERATIONS = "operations.py"
_WORLD_FEED = "world_feed.py"

_module_cache: dict[str, tuple[float, object]] = {}
_entity_cache: dict[str, dict] = {"mtime": -1.0, "entities": {}}
_e2_resolver = None  # WorldKnowledgeResolver (M3) — ленивый инстанс, тест-хук _reset_cache


def enabled() -> bool:
    """OWNER-GATE для EDM-RES пилота (читается на каждом вызове)."""
    try:
        from shared_config import settings

        return bool(getattr(settings, "EDM_RES_PILOT_ENABLED", False))
    except Exception:
        return False


def _edm_dir() -> Path:
    try:
        from shared_config import settings

        return Path(getattr(settings, "EDM_RES_DIR", None) or settings.PROJECT_ROOT / "core" / "CORE" / "ENTITY_MODEL")
    except Exception:  # pragma: no cover - конфиг всегда доступен
        return Path(__file__).resolve().parents[3] / "core" / "CORE" / "ENTITY_MODEL"


def _load_module(filename: str):
    """Importlib-загрузка модуля ENTITY_MODEL с mtime-кэшем (перезагрузка при изменении)."""
    path = _edm_dir() / filename
    mtime = path.stat().st_mtime
    cached = _module_cache.get(filename)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    name = f"edm_pilot_rt_{Path(filename).stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    _module_cache[filename] = (mtime, module)
    return module


def _reset_cache() -> None:
    """Тест-хук: сброс кэшей модулей и сущностей (+ M3-резолвер E2)."""
    global _e2_resolver
    _module_cache.clear()
    _entity_cache["mtime"] = -1.0
    _entity_cache["entities"] = {}
    _e2_resolver = None


def get_entities() -> dict[str, dict]:
    """Индекс EDM-сущностей (pilot/*.json + examples/*.json) по canonical_id.

    МTIME-кэш: файлы перечитываются только при изменении (mtime).
    """
    files = sorted(_edm_dir().glob("pilot/*.json")) + sorted(_edm_dir().glob("examples/*.json"))
    mtime = max((p.stat().st_mtime for p in files), default=0.0)
    if _entity_cache["mtime"] >= 0 and _entity_cache["mtime"] == mtime and _entity_cache["entities"]:
        return _entity_cache["entities"]
    entities: dict[str, dict] = {}
    for p in files:
        try:
            data = json.loads(p.read_bytes().decode("utf-8-sig"))
        except Exception as exc:  # повреждённый файл не роняет прогон
            log.warning("edm_entity_load_failed file=%s error=%s", p.name, exc)
            continue
        eid = str(((data.get("identity") or {}).get("canonical_id")) or p.stem)
        # Order-ранг §4.1: pilot-карточка (ранг b) бьёт examples-карточку (ранг c)
        # при одинаковом canonical_id — согласовано с entity_sources() (setdefault).
        entities.setdefault(eid, data)
    _entity_cache["mtime"] = mtime
    _entity_cache["entities"] = entities
    return entities


def entity_sources() -> dict[str, str]:
    """EDM-сущности (identity.canonical_id) → источник: "pilot" / "examples".

    Order-ранг §4.1: engine-кандидат и pilot-карточка — ранг b, examples-
    карточка — ранг c. Источник читается из identity.canonical_id файла
    (stem используется только как запасной, как в get_entities).
    """
    sources: dict[str, str] = {}
    for p in sorted(_edm_dir().glob("pilot/*.json")):
        try:
            data = json.loads(p.read_bytes().decode("utf-8-sig"))
        except Exception as exc:  # повреждённый файл не роняет прогон
            log.warning("edm_entity_source_parse_failed file=%s error=%s", p.name, exc)
            continue
        eid = str(((data.get("identity") or {}).get("canonical_id")) or p.stem)
        sources.setdefault(eid, "pilot")
    for p in sorted(_edm_dir().glob("examples/*.json")):
        try:
            data = json.loads(p.read_bytes().decode("utf-8-sig"))
        except Exception as exc:
            log.warning("edm_entity_source_parse_failed file=%s error=%s", p.name, exc)
            continue
        eid = str(((data.get("identity") or {}).get("canonical_id")) or p.stem)
        sources.setdefault(eid, "examples")
    return sources


def _names_of(entity: dict) -> list[str]:
    identity = entity.get("identity") or {}
    names = [str(identity.get("canonical_id") or "").strip()]
    names += [str(n).strip() for n in (identity.get("names") or [])]
    names += [str(a).strip() for a in (identity.get("aliases") or [])]
    return [n.casefold() for n in names if len(n) >= 3]


def match_entities(
    location_id: str | None = None,
    location_name: str | None = None,
    scene_location: str | None = None,
    explicit_ids: list[str] | None = None,
    auto_matched_ids: list[str] | None = None,
) -> list[dict]:
    """Строгий матчинг EDM-сущности к сцене (без эвристик).

    Порядок: явные ids из запроса → точное совпадение location_id /
    location_name / scene.location с canonical_id или с именем/алиасом
    (case-insensitive). Ничего не угадывается: нет совпадения — пусто.
    E2: auto_matched_ids — canonical ids, которые уже разрешены
    engine/crosswalk-мостом (resolve_scene_location); добавляются только
    реально существующие в каталоге карточки (unknown-сущности не
    материализуются, B1 fail-closed).
    """
    entities = get_entities()
    out: list[dict] = []
    seen: set[str] = set()

    def _add(entity: dict) -> None:
        eid = str((entity.get("identity") or {}).get("canonical_id") or "")
        if eid and eid not in seen:
            seen.add(eid)
            out.append(entity)

    for eid in explicit_ids or []:
        if eid in entities:
            _add(entities[eid])

    keys = {k.strip().casefold() for k in (location_id, location_name, scene_location) if k and k.strip()}
    if keys:
        for entity in entities.values():
            if any(k in _names_of(entity) for k in keys):
                _add(entity)
    for eid in auto_matched_ids or []:
        if eid in entities:
            _add(entities[eid])
    return out


def _e2_world_resolver():
    """E2: M3-резолвер (WorldKnowledgeResolver) — ленивый инстанс.

    Сбрасывается в :func:`_reset_cache` (вместе с кэшем crosswalk'а
    WorldModel — snapshot ``_approved`` живёт в инстансе резолвера).
    """
    global _e2_resolver
    if _e2_resolver is None:
        from knowledge.world_resolver import WorldKnowledgeResolver

        _e2_resolver = WorldKnowledgeResolver()
    return _e2_resolver


def _engine_location_candidates(location: str) -> list[dict]:
    """E2-мост: location-строка → owner-утверждённые engine/crosswalk ids.

    Два моста, оба fail-closed (сбой/недоступность → []):
    - **crosswalk**: M3-резолвер — только owner-утверждённые canonical id
      (approved crosswalk / canonical_id, fuzzy-выводов не делает). Ru-ярлыки
      crosswalk'а хранятся casefolded, поэтому второй попытки — в casefold-
      форме (ложный негатив в естественном регистре — известный дефект M3);
    - **scorer**: детерминированный engine-скоринг по location-строке самой
      (resolve_related_entities, name coverage >= MIN_SCORE, RAG=None —
      никакого буста).
    """
    out: list[dict] = []
    try:
        from schemas.world_reference import WorldReferenceStatus

        resolver = _e2_world_resolver()
        for query in (location, location.casefold()):
            ref = resolver.resolve(query)
            if ref.status == WorldReferenceStatus.RESOLVED and ref.canonical_id:
                out.append({"entity_id": str(ref.canonical_id), "source": "engine_crosswalk", "entity_type": None})
                break
    except Exception as exc:  # мост недоступен — engine-scoring остаётся
        log.warning("edm_location_bridge_unavailable location=%s error=%s", location, exc)
    try:
        from core.services.related_entities import resolve_related_entities

        entities, _rationale = resolve_related_entities({"question": location, "answer": location})
        for e in entities:
            eid = str(e.get("entity_id") or "").strip()
            if eid:
                out.append({"entity_id": eid, "source": "engine_scored", "entity_type": e.get("entity_type")})
    except Exception as exc:  # engine недоступен — пусто, мир не выдумывается
        log.warning("edm_location_scorer_unavailable location=%s error=%s", location, exc)
    return out


def resolve_scene_location(
    scene_location: str | None = None,
    location_id: str | None = None,
    location_name: str | None = None,
) -> dict:
    """E2 авто-матчинг: location-строка → engine/crosswalk → region_* → EDM.

    Детерминированная цепочка (без LLM, без fuzzy-выводов, мир не мутируется):
    1. строгий уровень (E1): точные имена/алиасы EDM-каталога по
       location_id / location_name / scene.location — :func:`match_entities`;
    2. engine/crosswalk-мост (E2): M3-резолвер — только owner-утверждённые
       canonical id (второй попытки — casefold, см.
       :func:`_engine_location_candidates`);
    3. engine-скорер: детерминированный скоринг по location-строке.

    Возвращает::

        {"location": str,
         "candidates": [{entity_id, origin, entity_type, source}],
         "entity_ids": [...],        # дедупликация, порядок: строгие → мост → scorer
         "edm_entities": [...]}      # карточки каталога для найденных ids

    Ids без EDM-карточки не материализуются (B1 fail-closed): они остаются
    в candidates/entity_ids как trace (вниз — ``context_only`` W2 / отчёт),
    в edm_entities попадают только существующие карточки. Нет ни одного
    совпадения — candidate'в нет (строгий уровень тоже пуст).
    """
    location = str(scene_location or "").strip()
    catalog = get_entities()
    sources = entity_sources()
    candidates: list[dict] = []
    seen: set[str] = set()

    def _add(eid: str, origin: str, source: str, entity_type=None) -> None:
        eid = str(eid or "").strip()
        if eid and eid not in seen:
            seen.add(eid)
            candidates.append({"entity_id": eid, "origin": origin, "entity_type": entity_type, "source": source})

    for ent in match_entities(location_id=location_id, location_name=location_name, scene_location=scene_location):
        identity = ent.get("identity") or {}
        eid = str(identity.get("canonical_id") or "")
        _add(eid, sources.get(eid, "catalog"), "catalog", identity.get("type"))
    if location:
        for cand in _engine_location_candidates(location):
            _add(cand["entity_id"], "engine", cand["source"], cand.get("entity_type"))

    entity_ids = [c["entity_id"] for c in candidates]
    edm_entities = [catalog[i] for i in entity_ids if i in catalog]
    return {
        "location": location,
        "candidates": candidates,
        "entity_ids": entity_ids,
        "edm_entities": edm_entities,
    }


def _match_in_text(text: str) -> list[dict]:
    """Диалог: сущность считается затронутой, если её имя/алиас/id
    (длиной ≥ 3) встречается в вопросе (case-insensitive substring)."""
    entities = get_entities()
    q = text.casefold()
    out: list[dict] = []
    for entity in entities.values():
        if any(name in q for name in _names_of(entity)):
            out.append(entity)
    return out


def _fmt_claim_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    return str(value)


def build_edm_dialogue_block(
    question: str,
    layer_text: str = "",
    related_entities: list[dict] | None = None,
    explicit_ids: list[str] | None = None,
) -> dict | None:
    """Слоистое EDM-описание затронутых сущностей (world scope).

    Уровень 1 (кандидаты): related_entities (engine) + точные совпадения
    имён EDM-каталога в вопросе + явные ids (strict, без fuzzy). Уровень 2
    (context resolution, W1–W3, `core/services/edm_context.py`, утверждённый
    дизайн GATE A 2026-10-25): intent из ВОПРОСА (I4) → фильтр кандидатов
    по типу (R1–R4, бандл N=4, порядок §4.1) → отбор claims C1–C6.
    Tier-2 связи (W4, crosswalk v2.1) показываются как утверждённые связи с
    провенансом; нет утверждённой связи — свойства не материализуются
    (B1 fail-closed).

    Возвращает None, если в бандле нет ни одной EDM-сущности (GAP) — тогда
    и /book/ask, и composite-провайдер ведут себя byte-identично legacy.
    Сценарные/художественные значения (scope scene/media_plan) в блок НЕ
    попадают — только layer-isolation.
    """
    from core.services import edm_context

    catalog = get_entities()
    sources = entity_sources()

    # Уровень 1: пул кандидатов (strict: только названное/явное).
    pool: list[dict] = []
    seen: set[str] = set()

    def _add_candidate(eid, origin: str, entity_type=None) -> None:
        eid = str(eid or "").strip()
        if eid and eid not in seen:
            seen.add(eid)
            pool.append({"entity_id": eid, "origin": origin, "entity_type": entity_type})

    for cand in related_entities or []:
        _add_candidate(cand.get("entity_id"), "engine", cand.get("entity_type"))
    for entity in _match_in_text(question):
        eid = str((entity.get("identity") or {}).get("canonical_id") or "")
        _add_candidate(eid, sources.get(eid, "catalog"))
    for eid in explicit_ids or []:
        _add_candidate(eid, "explicit")

    bundle = edm_context.select_bundle(question, pool, catalog=catalog, explicit_ids=None)
    ids = [i for i in bundle["entity_ids"] if i in catalog]
    if not ids:
        return None
    lines = ["Сущности Entity Description Model (пилот EDM-RES) — слоистое описание с провенансом:"]
    if bundle["status"] == "AMBIGUOUS":
        lines.append(f"Под этим запросом соответствуют несколько объектов: {', '.join(ids)} — AMBIGUOUS-бандл (выбор одной сущности не делается, §4.3 D3).")
    for eid in ids:
        card = catalog[eid]
        identity = card.get("identity") or {}
        name = str((identity.get("names") or [eid])[:1][0])
        head = f"- {name} ({eid})"
        if identity.get("is_reconstruction"):
            head += " — вся карточка: реконструкция (C6)"
        lines.append(head)
        for c in edm_context.filter_claims(card, mode="dialogue"):
            path, rule = c.get("path"), c.get("c_rule")
            if rule == "C1":
                ref = (c.get("source_ref") or {}).get("ref") or ""
                lines.append(f"  • {path} = {_fmt_claim_value(c.get('value'))} (факт; {c.get('provenance_class')}, {ref})")
            elif rule == "C2":
                lines.append(f"  • {path} = {_fmt_claim_value(c.get('value'))} — реконструкция, не канон (допущение)")
            elif rule == "C3":
                lines.append(f"  • {path} = {_fmt_claim_value(c.get('value'))} — визуальный образ (допущение), не факт книги (C3)")
            elif rule == "C4":
                lines.append(f"  • {path} — не установлено в книге (явная граница знания, не дефолт)")
        for rel in bundle["relations"]:
            if rel.get("source_id") == eid or rel.get("target_id") == eid:
                other = rel.get("target_id") if rel.get("source_id") == eid else rel.get("source_id")
                lines.append(f"  • утверждённая связь: {rel.get('relation')} → {other} (Tier-2, owner-утверждено, {rel.get('id')})")
    for ctx_id in bundle.get("context_only") or []:
        lines.append(f"- контекст без EDM-карточки (v1): {ctx_id} — описание engine-категории, без claims-фильтрации")
    lines.append(
        "Граница слоёв: значения сценарного/художественного scope (scene/media_plan) "
        "в этот блок не попадают; «не установлено» — явная граница знания, не дефолт."
    )
    if bundle.get("gap"):
        lines.append(f"Граница знания: {bundle['gap']}")

    provenance: list[dict] = []
    for eid in ids:
        card = catalog[eid]
        for c in edm_context.filter_claims(card, mode="dialogue"):
            provenance.append(
                {
                    "entity": eid,
                    "path": c.get("path"),
                    "status": c.get("status"),
                    "provenance_class": c.get("provenance_class"),
                    "medium": bool(c.get("medium", False)),
                    "c_rule": c.get("c_rule"),
                }
            )
        for rel in bundle["relations"]:
            if rel.get("source_id") == eid:
                provenance.append(
                    {
                        "entity": eid,
                        "path": f"relations:{rel.get('relation')}->{rel.get('target_id')}",
                        "status": "approved_tier2",
                        "provenance_class": "owner_reviewed_crosswalk_v21",
                        "medium": False,
                    }
                )
    return {
        "entities": ids,
        "intent": bundle["intent"],
        "status": bundle["status"],
        "bundle": bundle["entity_ids"],
        "dropped": bundle.get("dropped", []),
        "relations": [{k: r.get(k) for k in ("id", "source_id", "relation", "target_id")} for r in bundle["relations"]],
        "context_only": bundle.get("context_only", []),
        "block": "\n".join(lines),
        "provenance": provenance,
    }


def apply_edm_to_context(
    ctx,
    entities: list[dict] | None = None,
    location_id: str | None = None,
    location_name: str | None = None,
    scene_location: str | None = None,
    explicit_ids: list[str] | None = None,
    scene_overrides: dict | None = None,
    auto_matched_ids: list[str] | None = None,
    location_matched: dict | None = None,
) -> dict:
    """Наполнить canonical Scene Context (VisualContext) из EDM-сущностей.

    Чистая механика: world_feed.apply_edm + инъектированный resolutions-решал.
    Мутации: только существующие поля ctx (architecture/landscape/environment)
    и source_refs.entity_refs («edm:<id>» — идентификатор, не копия данных).
    E2: auto_matched_ids — разрешённые engine/crosswalk-мостом ids уходят в
    строгий каталог (match_entities, только существующие карточки);
    location_matched (результат resolve_scene_location) добавляется в
    отчёт как additive-трасса ``report['location_matched']``.
    """
    ents = (
        entities
        if entities is not None
        else match_entities(
            location_id=location_id,
            location_name=location_name,
            scene_location=scene_location,
            explicit_ids=explicit_ids,
            auto_matched_ids=auto_matched_ids,
        )
    )
    resolver = _load_module(_RESOLUTIONS).resolve_description
    report = _load_module(_WORLD_FEED).apply_edm(ctx, ents, resolver, scene_overrides)
    if location_matched:
        report["location_matched"] = {
            "location": location_matched.get("location", ""),
            "candidates": location_matched.get("candidates", []),
            "entity_ids": location_matched.get("entity_ids", []),
        }
    return report


def compose_provider(base_provider):
    """Composite (t1 + EDM) провайдер Knowledge Context для Voice.

    Инжектится через существующий ``voice.set_knowledge_context_provider``:
    t1-материал (Knowledge Core) остаётся базой, EDM-блок ДОБАВЛЯЕТСЯ в
    facts_block. Нет EDM-материала (нет совпадения) — результат base
    провайдера без изменений (byte-identical). Сбой EDM-блока не роняет
    ответ: t1-часть возвращается как есть.
    """

    def _composite(query: str, layer_text: str):
        payload = base_provider(query, layer_text) if base_provider else None
        if not isinstance(payload, dict):
            payload = {}
        try:
            edm_block = build_edm_dialogue_block(query, layer_text)
        except Exception as exc:
            log.warning("edm_dialogue_block_failed error=%s", exc)
            edm_block = None
        if not edm_block:
            return payload if payload else None
        merged = dict(payload)
        merged["facts_block"] = f"{str(payload.get('facts_block') or '')}\n\n{edm_block['block']}".strip()
        return merged

    return _composite


__all__ = [
    "enabled",
    "get_entities",
    "match_entities",
    "resolve_scene_location",
    "build_edm_dialogue_block",
    "apply_edm_to_context",
    "compose_provider",
    "_reset_cache",
]
