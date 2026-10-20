"""Read-only связи сцен сценария с World Model и Knowledge Core.

Модуль не создаёт новых сущностей, не расширяет реестры и не пишет в данные.
Каждая связь получает статус, источник и основание сопоставления:

  - ``CONFIRMED`` — цель и её идентичность подтверждены владельцем:
    одобренная связь сценарию/книге (``screenplay_links.json``), одобренная
    claim-связь (``claim_temporal_links.json``) с валидной цепочкой до
    канонического события ``WORLD_MODEL.json``, либо точное совпадение имени
    персонажа/локации с сущностью World Model.
  - ``DERIVED`` — связь вычислена по точному, задокументированному правилу
    над существующими данными (например: идентификатор локации из
    ``LOCATION_VISUALS.json`` дословно совпадает с ``name_ru`` локации World
    Model; оба участника подтверждённой связи персонажей присутствуют в
    сцене; обогащение одобренного книжного чанка).
  - ``UNRESOLVED`` — точного основания нет; причина фиксируется явно.
  - ``AMBIGUOUS`` — на одну цель претендуют несколько сущностей; выбор не
    выполняется.

Смысловые догадки, нечёткий поиск и расширение таблицы алиасов запрещены.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from .screenplay_scene_aliases import alias_surfaces

log = logging.getLogger("knowledge.screenplay_scene_world_links")

STATUS_CONFIRMED = "CONFIRMED"
STATUS_DERIVED = "DERIVED"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_AMBIGUOUS = "AMBIGUOUS"

LINK_LOCATION = "location"
LINK_LOCATION_MENTION = "location_mention"
LINK_CHARACTER = "character"
LINK_CHARACTER_RELATION = "character_relation"
LINK_EVENT = "event"
LINK_EPOCH = "epoch"
LINK_BOOK_ENTITY = "book_entity"

_SOURCE_FILES = {
    "place_mention_forms": "core/KNOWLEDGE/place_mention_forms.json",
    "screenplay_links": "core/KNOWLEDGE/screenplay_links.json",
    "claim_temporal_links": "core/KNOWLEDGE/claim_temporal_links.json",
    "enriched_chunks": "core/KNOWLEDGE/enriched_chunks.json",
    "world_model": "core/CORE/narrative_engine/data/WORLD_MODEL.json",
    "world_crosswalk": "core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json",
}

_BOOK_ENTITY_FIELDS: tuple[tuple[str, str], ...] = (
    ("enriched_characters", "book_character"),
    ("enriched_themes", "book_theme"),
    ("enriched_symbols", "book_symbol"),
    ("enriched_conflicts", "book_conflict"),
    ("enriched_values", "book_value"),
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _crosswalk_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "WORLD_CROSSWALK"
        / "WORLD_ENGINE_WORLD_MODEL.json"
    )


def _place_mentions_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "KNOWLEDGE"
        / "place_mention_forms.json"
    )


@lru_cache(maxsize=1)
def _load_place_mention_records_cached(mtime_ns: int, size: int) -> tuple[dict[str, Any], ...]:
    """Записи реестра форм-упоминаний (только APPROVED, fail-closed)."""
    data = json.loads(_place_mentions_path().read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("status") != "APPROVED":
        return ()
    places = data.get("places")
    if not isinstance(places, list):
        return ()
    return tuple(place for place in places if isinstance(place, dict) and place.get("forms"))


def _load_place_mention_records() -> tuple[dict[str, Any], ...]:
    """Утверждённые владельцем формы упоминаний мест (пусто — если реестра нет)."""
    path = _place_mentions_path()
    try:
        stat = path.stat()
    except OSError as exc:
        log.warning("place_mention_forms_unavailable path=%s error=%s", path, exc)
        return ()
    try:
        return _load_place_mention_records_cached(stat.st_mtime_ns, stat.st_size)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("place_mention_forms_load_failed error=%s", exc)
        return ()


@lru_cache(maxsize=1)
def _load_crosswalk_records() -> tuple[dict[str, Any], ...]:
    """Только одобренные владельцем записи crosswalk (fail closed)."""
    path = _crosswalk_path()
    if not path.exists():
        log.warning("world_crosswalk_missing path=%s", path)
        return ()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("world_crosswalk_load_failed error=%s", exc)
        return ()
    records = [
        record
        for record in data.get("mappings", [])
        if record.get("status") == "APPROVED"
    ]
    return tuple(records)


def _crosswalk_for_label(label: str) -> list[dict[str, Any]]:
    query = label.casefold().strip()
    if not query:
        return []
    found = []
    for record in _load_crosswalk_records():
        labels = record.get("labels") or {}
        ru_label = str(labels.get("ru") or "").strip().casefold()
        if ru_label and ru_label == query:
            found.append(record)
    return found


def _world_model():
    from narrative_engine.world_model import WorldModel

    return WorldModel.load()


@lru_cache(maxsize=1)
def _claim_links():
    from .claim_temporal_linker import ClaimTemporalLinker

    return tuple(ClaimTemporalLinker.from_json().links)


def _link(
    link_type: str,
    status: str,
    target_kind: str,
    target_id: str,
    basis: str,
    *,
    target_label: str = "",
    provenance: dict[str, Any] | None = None,
    source_files: list[str] | None = None,
    chain: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "link_type": link_type,
        "status": status,
        "target_kind": target_kind,
        "target_id": target_id,
        "target_label": target_label,
        "basis": basis,
        "provenance": provenance or {},
        "source_files": source_files or [],
    }
    if chain:
        record["chain"] = chain
    if extra:
        record.update(extra)
    return record


def _location_candidates(locations: list[Any], query: str) -> list[Any]:
    normalized = query.casefold().strip()
    if not normalized:
        return []
    return [
        location
        for location in locations
        if location.id.casefold() == normalized
        or location.name_ru.casefold() == normalized
    ]


def _location_link(location: Any, status: str, basis: str) -> dict[str, Any]:
    crosswalk = _crosswalk_for_label(location.name_ru) or _crosswalk_for_label(
        location.id
    )
    extra: dict[str, Any] = {"location_id": location.id}
    if crosswalk:
        record = crosswalk[0]
        extra["world_entity_id"] = record.get("canonical_id", "")
        extra["crosswalk_provenance"] = record.get("provenance", {})
    return _link(
        LINK_LOCATION,
        status,
        "world_location",
        location.id,
        basis,
        target_label=location.name_ru,
        provenance={
            "category": "AUTHOR_CANON",
            "source_level": "CANON",
            "confidence": 1.0,
        },
        source_files=[_SOURCE_FILES["world_model"]],
        extra=extra,
    )


def _location_mention_links(scene_text: str) -> list[dict[str, Any]]:
    """Упоминания одобренных меток crosswalk в тексте сцены.

    Только дословное вхождение одобренной метки целым словом. Упоминание —
    это не место действия сцены, поэтому связь помечается как DERIVED и
    помечается флагом ``mention_only``.
    """
    links: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    if not scene_text:
        return links
    for record in _load_crosswalk_records():
        labels = record.get("labels") or {}
        ru_label = str(labels.get("ru") or "").strip()
        if not ru_label:
            continue
        if not re.search(r"(?<!\w)" + re.escape(ru_label) + r"(?!\w)", scene_text, re.IGNORECASE):
            continue
        canonical_location_id = ""
        for evidence in record.get("evidence") or []:
            if isinstance(evidence, dict) and evidence.get("type") == "canonical_location":
                canonical_location_id = str(evidence.get("location_id") or "")
                break
        target_id = canonical_location_id or str(record.get("canonical_id") or "")
        if target_id in seen_targets:
            continue
        seen_targets.add(target_id)
        links.append(
            _link(
                LINK_LOCATION_MENTION,
                STATUS_DERIVED,
                "world_location",
                target_id,
                f"одобренная метка crosswalk «{ru_label}» дословно встречается в тексте сцены (упоминание, не место действия)",
                target_label=ru_label,
                provenance={"category": "DERIVED", "source_level": "EXTERNAL_SOURCE", "confidence": 0.8},
                source_files=[_SOURCE_FILES["world_crosswalk"]],
                extra={
                    "world_entity_id": str(record.get("canonical_id") or ""),
                    "crosswalk_provenance": record.get("provenance", {}),
                    "mention_only": True,
                },
            )
        )

    # Формы-упоминания, утверждённые владельцем (core/KNOWLEDGE/place_mention_forms.json).
    for place in _load_place_mention_records():
        location_id = str(place.get("location_id") or "")
        if not location_id or location_id in seen_targets:
            continue
        forms = [str(form) for form in place.get("forms") or [] if str(form).strip()]
        matched = [
            form
            for form in forms
            if re.search(r"(?<!\w)" + re.escape(form) + r"(?!\w)", scene_text, re.IGNORECASE)
        ]
        if not matched:
            continue
        seen_targets.add(location_id)
        links.append(
            _link(
                LINK_LOCATION_MENTION,
                STATUS_DERIVED,
                "world_location",
                location_id,
                "утверждённая владельцем форма упоминания места: "
                + ", ".join(f"«{form}»" for form in matched)
                + " (упоминание, не место действия)",
                target_label=str(place.get("location_name_ru") or location_id),
                provenance={"category": "DERIVED", "source_level": "AUTHOR_INTERPRETATION", "confidence": 1.0},
                source_files=[_SOURCE_FILES["place_mention_forms"], _SOURCE_FILES["world_model"]],
                extra={
                    "world_entity_id": str(place.get("world_entity_id") or ""),
                    "matched_forms": matched,
                    "mention_only": True,
                },
            )
        )
    return links


def _resolve_location(scene: dict[str, Any], locations: list[Any]) -> dict[str, Any]:
    location_name = str(scene.get("location_name") or "")
    location_id = str(scene.get("location_id") or "")

    by_name = _location_candidates(locations, location_name)
    if len(by_name) == 1:
        return _location_link(
            by_name[0],
            STATUS_CONFIRMED,
            "точное совпадение location_name с name_ru/id локации World Model",
        )
    if len(by_name) > 1:
        return _link(
            LINK_LOCATION,
            STATUS_AMBIGUOUS,
            "world_location",
            "",
            f"location_name '{location_name}' соответствует нескольким локациям World Model: "
            + ", ".join(sorted(location.id for location in by_name)),
            source_files=[_SOURCE_FILES["world_model"]],
            extra={"candidates": sorted(location.id for location in by_name)},
        )

    by_id = _location_candidates(locations, location_id)
    if len(by_id) == 1:
        return _location_link(
            by_id[0],
            STATUS_DERIVED,
            "location_id сцены (LOCATION_VISUALS) дословно совпадает с name_ru локации World Model",
        )
    if len(by_id) > 1:
        return _link(
            LINK_LOCATION,
            STATUS_AMBIGUOUS,
            "world_location",
            "",
            f"location_id '{location_id}' соответствует нескольким локациям World Model: "
            + ", ".join(sorted(location.id for location in by_id)),
            source_files=[_SOURCE_FILES["world_model"]],
            extra={"candidates": sorted(location.id for location in by_id)},
        )

    return _link(
        LINK_LOCATION,
        STATUS_UNRESOLVED,
        "world_location",
        "",
        f"у локации сцены ('{location_name}') нет точного соответствия в World Model",
        source_files=[_SOURCE_FILES["world_model"]],
    )


def _presence_index(world) -> dict[str, list[tuple[str, Any]]]:
    index: dict[str, list[tuple[str, Any]]] = {}
    for epoch in world.get_epochs():
        for presence in world.get_characters_alive(epoch.id):
            index.setdefault(presence.character_name, []).append((epoch.id, presence))
    return index


def _character_links(
    scene: dict[str, Any], world
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    links: list[dict[str, Any]] = []
    resolved: dict[str, str] = {}
    presence_index = _presence_index(world)

    for character in scene.get("characters") or []:
        name = str(character)
        presences = presence_index.get(name)
        if presences:
            epochs = sorted({epoch_id for epoch_id, _ in presences})
            source_level = presences[0][1].source_level
            level_value = getattr(source_level, "value", str(source_level))
            links.append(
                _link(
                    LINK_CHARACTER,
                    STATUS_CONFIRMED,
                    "world_character",
                    name,
                    "точное совпадение имени персонажа сцены с записью characters_living в World Model",
                    target_label=name,
                    provenance={
                        "category": "AUTHOR_CANON",
                        "source_level": level_value,
                        "confidence": 1.0,
                    },
                    source_files=[_SOURCE_FILES["world_model"]],
                    extra={"epochs": epochs, "presence_status": presences[0][1].status},
                )
            )
            resolved[name] = name
            continue

        alias_hit = next(
            (alias for alias in alias_surfaces(name) if alias in presence_index),
            None,
        )
        if alias_hit is not None:
            epochs = sorted({epoch_id for epoch_id, _ in presence_index[alias_hit]})
            links.append(
                _link(
                    LINK_CHARACTER,
                    STATUS_DERIVED,
                    "world_character",
                    alias_hit,
                    f"утверждённая таблица алиасов: написание '{alias_hit}' соответствует каноническому имени '{name}'",
                    target_label=alias_hit,
                    provenance={
                        "category": "DERIVED",
                        "source_level": "CANON",
                        "confidence": 1.0,
                    },
                    source_files=[_SOURCE_FILES["world_model"]],
                    extra={"canonical_name": name, "epochs": epochs},
                )
            )
            resolved[name] = alias_hit
            continue

        links.append(
            _link(
                LINK_CHARACTER,
                STATUS_UNRESOLVED,
                "world_character",
                "",
                f"персонаж '{name}' не найден в World Model точным совпадением имени",
                target_label=name,
                source_files=[_SOURCE_FILES["world_model"]],
                extra={"character": name},
            )
        )

    return links, resolved


def _relation_links(world, resolved: dict[str, str]) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for relation in world.get_character_relations():
        source = resolved.get(relation.character)
        target = resolved.get(relation.target)
        if not source or not target:
            continue
        links.append(
            _link(
                LINK_CHARACTER_RELATION,
                STATUS_DERIVED,
                "world_character_relation",
                f"{relation.character} {relation.relation} {relation.target}",
                "оба участника подтверждённой связи персонажей присутствуют в сцене (точное совпадение имён)",
                target_label=f"{relation.character} {relation.relation} {relation.target}",
                provenance={
                    "category": "DERIVED",
                    "source_level": "CANON",
                    "confidence": 1.0,
                },
                source_files=[_SOURCE_FILES["world_model"]],
                extra={
                    "character": relation.character,
                    "target": relation.target,
                    "relation": relation.relation,
                    "relation_provenance": [
                        tag.model_dump(mode="json") for tag in relation.provenance
                    ],
                },
            )
        )
    return links


def _event_links(
    book_links: list[dict[str, Any]], chunks: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    from narrative_engine.provenance.claim import CanonClaim

    from .claim_temporal_linker import ClaimTemporalLinker

    world = _world_model()
    links: list[dict[str, Any]] = []

    for book_link in book_links:
        chunk_id = str(book_link.get("chunk_id") or "")
        chunk = chunks.get(chunk_id) or {}
        text = str(chunk.get("text") or "")
        if not chunk_id or not text:
            continue
        claim_id = CanonClaim.make_id(
            text, source_id="book", location=f"chunk:{chunk_id}"
        )
        claim_links = [link for link in _claim_links() if link.claim_id == claim_id]
        if not claim_links:
            links.append(
                _link(
                    LINK_EVENT,
                    STATUS_UNRESOLVED,
                    "world_event",
                    "",
                    f"одобренная книжная связь {chunk_id} есть, подтверждённой claim→event связи нет",
                    source_files=[
                        _SOURCE_FILES["screenplay_links"],
                        _SOURCE_FILES["claim_temporal_links"],
                    ],
                    extra={"book_chunk_id": chunk_id, "claim_id": claim_id},
                )
            )
            continue

        for claim_link in claim_links:
            validation = ClaimTemporalLinker.validate_chain(claim_link)
            if not validation.valid:
                links.append(
                    _link(
                        LINK_EVENT,
                        STATUS_UNRESOLVED,
                        "world_event",
                        "",
                        f"цепочка claim→event не прошла валидацию: {validation.reason}",
                        source_files=[
                            _SOURCE_FILES["claim_temporal_links"],
                            _SOURCE_FILES["world_model"],
                        ],
                        extra={
                            "book_chunk_id": chunk_id,
                            "claim_id": claim_id,
                            "event_id": validation.event_id or "",
                            "temporal_node_id": validation.temporal_node_id,
                        },
                    )
                )
                continue

            event = next(
                (item for item in world.get_events() if item.id == validation.event_id),
                None,
            )
            epoch = (
                world.get_epoch(validation.epoch_id) if validation.epoch_id else None
            )
            links.append(
                _link(
                    LINK_EVENT,
                    STATUS_CONFIRMED,
                    "world_event",
                    str(validation.event_id),
                    "одобренная связь сценарию/книге → подтверждённая claim-связь → валидная цепочка до канонического события",
                    target_label=event.title_ru if event else "",
                    provenance={
                        "category": "AUTHOR_CANON",
                        "source_level": "CANON",
                        "confidence": 1.0,
                    },
                    source_files=[
                        _SOURCE_FILES["screenplay_links"],
                        _SOURCE_FILES["enriched_chunks"],
                        _SOURCE_FILES["claim_temporal_links"],
                        _SOURCE_FILES["world_model"],
                    ],
                    chain=[
                        {
                            "step": "screenplay_scene",
                            "ref": str(book_link.get("scene_id") or ""),
                        },
                        {"step": "book_chunk", "ref": chunk_id},
                        {"step": "claim", "ref": claim_id},
                        {
                            "step": "temporal_node",
                            "ref": validation.temporal_node_id or "",
                        },
                        {"step": "world_event", "ref": str(validation.event_id)},
                    ],
                    extra={
                        "book_chunk_id": chunk_id,
                        "claim_id": claim_id,
                        "epoch_id": validation.epoch_id or "",
                        "epoch_name_ru": epoch.name_ru if epoch else "",
                        "temporal_node_id": validation.temporal_node_id or "",
                        "event_location_id": event.location_id if event else "",
                        "event_characters": list(event.characters_involved)
                        if event
                        else [],
                    },
                )
            )
    return links


def _epoch_links(event_links: list[dict[str, Any]], world) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event_link in event_links:
        if (
            event_link["link_type"] != LINK_EVENT
            or event_link["status"] != STATUS_CONFIRMED
        ):
            continue
        epoch_id = str(event_link.get("epoch_id") or "")
        if not epoch_id or epoch_id in seen:
            continue
        seen.add(epoch_id)
        epoch = world.get_epoch(epoch_id)
        links.append(
            _link(
                LINK_EPOCH,
                STATUS_CONFIRMED,
                "world_epoch",
                epoch_id,
                "эпоха канонического события, подтверждённого цепочкой от сцены",
                target_label=epoch.name_ru if epoch else "",
                provenance={
                    "category": "AUTHOR_CANON",
                    "source_level": "CANON",
                    "confidence": 1.0,
                },
                source_files=[_SOURCE_FILES["world_model"]],
                extra={"temporal_node_id": f"temporal_{epoch_id}"},
            )
        )
    return links


def _book_entity_links(
    book_links: list[dict[str, Any]], chunks: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    for book_link in book_links:
        chunk_id = str(book_link.get("chunk_id") or "")
        chunk = chunks.get(chunk_id)
        if not chunk:
            continue
        for field, kind in _BOOK_ENTITY_FIELDS:
            for value in chunk.get(field) or []:
                text = str(value).strip()
                if not text:
                    continue
                links.append(
                    _link(
                        LINK_BOOK_ENTITY,
                        STATUS_DERIVED,
                        kind,
                        text,
                        f"обогащение одобренного книжного чанка {chunk_id} (поле {field})",
                        target_label=text,
                        provenance={
                            "category": "DERIVED",
                            "source_level": "SYSTEM_INTERPRETATION",
                            "confidence": 0.8,
                        },
                        source_files=[
                            _SOURCE_FILES["enriched_chunks"],
                            _SOURCE_FILES["screenplay_links"],
                        ],
                        extra={"book_chunk_id": chunk_id, "source_field": field},
                    )
                )
    return links


def _summarize(links: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    counts = {
        STATUS_CONFIRMED: 0,
        STATUS_DERIVED: 0,
        STATUS_UNRESOLVED: 0,
        STATUS_AMBIGUOUS: 0,
    }
    for link in links:
        by_type[link["link_type"]] = by_type.get(link["link_type"], 0) + 1
        counts[link["status"]] = counts.get(link["status"], 0) + 1
    return {
        "total": len(links),
        "confirmed": counts[STATUS_CONFIRMED],
        "derived": counts[STATUS_DERIVED],
        "unresolved": counts[STATUS_UNRESOLVED],
        "ambiguous": counts[STATUS_AMBIGUOUS],
        "by_type": by_type,
    }


def _missing(
    world_links: list[dict[str, Any]], scene: dict[str, Any]
) -> dict[str, str]:
    def has_resolved(link_type: str) -> bool:
        return any(
            link["link_type"] == link_type
            and link["status"] in {STATUS_CONFIRMED, STATUS_DERIVED}
            for link in world_links
        )

    missing: dict[str, str] = {}
    if not has_resolved(LINK_LOCATION):
        missing[LINK_LOCATION] = (
            "у локации сцены нет точного соответствия в World Model"
        )
    if not has_resolved(LINK_EVENT):
        missing[LINK_EVENT] = (
            "нет подтверждённой цепочки сцена → книжный чанк → claim → каноническое событие"
        )
    if not has_resolved(LINK_EPOCH):
        missing[LINK_EPOCH] = (
            "эпоха сцены не выводится: нет подтверждённой связи с каноническим событием"
        )
    if not scene.get("characters"):
        missing[LINK_CHARACTER] = "в сцене нет прямых упоминаний персонажей"
    elif not has_resolved(LINK_CHARACTER):
        missing[LINK_CHARACTER] = (
            "персонажи сцены не найдены в World Model точным совпадением имени"
        )
    if not has_resolved(LINK_BOOK_ENTITY):
        missing[LINK_BOOK_ENTITY] = (
            "нет одобренных книжных связей, дающих знание о мире"
        )
    return missing


def build_world_links(
    scene: dict[str, Any],
    *,
    scene_text: str = "",
    book_links: list[dict[str, Any]] | None = None,
    chunks: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Собрать связи сцены с World Model и Knowledge Core (только чтение)."""
    world = _world_model()
    chunks = chunks or {}
    book_links = list(book_links or [])

    links: list[dict[str, Any]] = []
    links.append(_resolve_location(scene, world.get_locations()))
    links.extend(_location_mention_links(scene_text))

    character_links, resolved = _character_links(scene, world)
    links.extend(character_links)
    links.extend(_relation_links(world, resolved))
    links.extend(_event_links(book_links, chunks))
    links.extend(_epoch_links(links, world))
    links.extend(_book_entity_links(book_links, chunks))

    return {
        "world_links": links,
        "world_link_summary": _summarize(links),
        "world_link_missing": _missing(links, scene),
    }


__all__ = [
    "STATUS_AMBIGUOUS",
    "STATUS_CONFIRMED",
    "STATUS_DERIVED",
    "STATUS_UNRESOLVED",
    "build_world_links",
]
