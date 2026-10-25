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
    """Тест-хук: сброс кэшей модулей и сущностей."""
    _module_cache.clear()
    _entity_cache["mtime"] = -1.0
    _entity_cache["entities"] = {}


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
        entities[eid] = data
    _entity_cache["mtime"] = mtime
    _entity_cache["entities"] = entities
    return entities


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
) -> list[dict]:
    """Строгий матчинг EDM-сущности к сцене (без эвристик).

    Порядок: явные ids из запроса → точное совпадение location_id /
    location_name / scene.location с canonical_id или с именем/алиасом
    (case-insensitive). Ничего не угадывается: нет совпадения — пусто.
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
    return out


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


def build_edm_dialogue_block(question: str, layer_text: str = "") -> dict | None:
    """Слоистое EDM-описание затронутых сущностей (world scope).

    Возвращает None, если ни одна сущность не затронута (тогда и /book/ask,
    и composite-провайдер ведут себя byte-identично legacy). Сценарные/
    художественные значения (scope scene/media_plan) в блок НЕ попадают —
    только layer-isolation, честные границы знания.
    """
    entities = _match_in_text(question)
    if not entities:
        return None
    resolutions = _load_module(_RESOLUTIONS)
    lines = ["Сущности Entity Description Model (пилот EDM-RES) — слоистое описание с провенансом:"]
    for entity in entities:
        lines.append(f"- {resolutions.to_dialogue(entity)}")
    lines.append(
        "Граница слоёв: значения сценарного/художественного scope (scene/media_plan) "
        "в этот блок не попадают; «не установлено» — явная граница знания, не дефолт."
    )
    provenance = []
    for entity in entities:
        eid = str((entity.get("identity") or {}).get("canonical_id"))
        for claim in entity.get("claims", []):
            provenance.append(
                {
                    "entity": eid,
                    "path": claim.get("path"),
                    "status": claim.get("status"),
                    "provenance_class": claim.get("provenance_class"),
                    "medium": bool(claim.get("medium", False)),
                }
            )
    return {
        "entities": [str((e.get("identity") or {}).get("canonical_id")) for e in entities],
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
) -> dict:
    """Наполнить canonical Scene Context (VisualContext) из EDM-сущностей.

    Чистая механика: world_feed.apply_edm + инъектированный resolutions-решал.
    Мутации: только существующие поля ctx (architecture/landscape/environment)
    и source_refs.entity_refs («edm:<id>» — идентификатор, не копия данных).
    """
    ents = entities if entities is not None else match_entities(
        location_id=location_id,
        location_name=location_name,
        scene_location=scene_location,
        explicit_ids=explicit_ids,
    )
    resolver = _load_module(_RESOLUTIONS).resolve_description
    report = _load_module(_WORLD_FEED).apply_edm(ctx, ents, resolver, scene_overrides)
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
    "build_edm_dialogue_block",
    "apply_edm_to_context",
    "compose_provider",
    "_reset_cache",
]

