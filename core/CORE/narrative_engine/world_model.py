"""World Model — структурированная модель мира для Narrative Engine."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from narrative_engine.source_levels import SourceLevel, ProvenanceTag

log = logging.getLogger("hermes.narrative.world_model")


# ── Модели данных ──────────────────────────────────────────────

class Epoch(BaseModel):
    id: str
    name: str
    name_ru: str
    description: str = ""
    order: int = 0
    duration_years: Optional[int] = None
    start_event: Optional[str] = None
    end_event: Optional[str] = None
    technologies_available: list[str] = Field(default_factory=list)
    civilizations_active: list[str] = Field(default_factory=list)
    source_level: SourceLevel = SourceLevel.CANON
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class Location(BaseModel):
    id: str
    name: str
    name_ru: str
    type: str = "other"  # city, region, sacred_site, ruins, natural, other
    description: str = ""
    coordinates: Optional[dict] = None
    region_id: Optional[str] = None
    epochs_present: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    source_level: SourceLevel = SourceLevel.CANON
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class Civilization(BaseModel):
    id: str
    name: str
    name_ru: str
    description: str = ""
    epochs: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    religion_ids: list[str] = Field(default_factory=list)
    related_locations: list[str] = Field(default_factory=list)
    source_level: SourceLevel = SourceLevel.CANON
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class Technology(BaseModel):
    id: str
    name: str
    name_ru: str
    description: str = ""
    epoch_first: Optional[str] = None
    civilization_origin: Optional[str] = None
    source_level: SourceLevel = SourceLevel.CANON
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class Religion(BaseModel):
    id: str
    name: str
    name_ru: str
    description: str = ""
    epochs: list[str] = Field(default_factory=list)
    practices: list[str] = Field(default_factory=list)
    key_figures: list[str] = Field(default_factory=list)
    source_level: SourceLevel = SourceLevel.CANON
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class CharacterPresence(BaseModel):
    character_name: str
    epoch: str
    location_id: Optional[str] = None
    status: str = "alive"  # alive, awakened, departed, mythic
    notes: str = ""
    source_level: SourceLevel = SourceLevel.CANON
    relations: list[dict] = Field(default_factory=list)  # [{"type": "mentor_of", "target": "name", "provenance": "AUTHOR_CANON"}]


class CanonicalEvent(BaseModel):
    id: str
    title: str
    title_ru: str
    description: str = ""
    epoch: str
    location_id: Optional[str] = None
    characters_involved: list[str] = Field(default_factory=list)
    chapter: Optional[int] = None
    order_in_epoch: int = 0
    source_level: SourceLevel = SourceLevel.CANON
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class CausalRule(BaseModel):
    id: str
    description: str
    rule_type: str = "exclusion"  # prerequisite, exclusion, dependency
    condition: str = ""
    related_events: list[str] = Field(default_factory=list)
    related_characters: list[str] = Field(default_factory=list)
    source_level: SourceLevel = SourceLevel.SYSTEM_INTERPRETATION


class EpochParallel(BaseModel):
    """Параллель/зеркальность между двумя эпохами. Не причинная связь."""
    source: str       # epoch ID
    target: str       # epoch ID
    description: str = ""
    provenance: list[ProvenanceTag] = Field(default_factory=list)


class CharacterRelation(BaseModel):
    """Связь между персонажами (mentor/student/peer)."""
    character: str     # character name
    relation: str      # mentor_of, student_of, peer_of, predecessor_of
    target: str        # target character name
    provenance: list[ProvenanceTag] = Field(default_factory=list)


# ── World Model ──────────────────────────────────────────────

_world_model_cache: Optional["WorldModel"] = None

# ── Approved crosswalk (read-only, B3b) ────────────────────────
# Связывает сущности World Engine с каноническими локациями ТОЛЬКО на основе
# владелец-утверждённого crosswalk-артефакта. Fail closed: отсутствие/ошибка
# файла → пустой mapping, то есть никаких выдуманных связей.
_CROSSWALK_FILENAME = "WORLD_ENGINE_WORLD_MODEL.json"
_crosswalk_cache: Optional[dict[str, list[str]]] = None


def _load_approved_crosswalk() -> dict[str, list[str]]:
    """stable language-agnostic canonical_id (region_*) → список World Engine entity_ids.

    Читает crosswalk v2 (WORLD_ENGINE_WORLD_MODEL.json). Каждая утверждённая
    mapping имеет canonical_id (не зависит от языка) и labels.ru/aliases.
    Возвращает mapping русского ярлыка (casefold) → [canonical_id] для обратной
    совместимости с _entity_ids_for_epoch (ищет по event.location_id) и резолвером.
    Fail closed: отсутствие/ошибка файла → пустой mapping.
    """
    global _crosswalk_cache
    if _crosswalk_cache is not None:
        return _crosswalk_cache
    here = Path(__file__).parent
    candidates = [
        here.parent / "WORLD_CROSSWALK" / _CROSSWALK_FILENAME,
        Path("core") / "CORE" / "WORLD_CROSSWALK" / _CROSSWALK_FILENAME,
        Path("CORE") / "WORLD_CROSSWALK" / _CROSSWALK_FILENAME,
    ]
    mapping: dict[str, list[str]] = {}
    for p in candidates:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("crosswalk_load_error path=%s error=%s", p, e)
            continue
        for m in data.get("mappings", []):
            if m.get("status") != "APPROVED":
                continue
            canonical_id = m.get("canonical_id")
            if not canonical_id:
                continue
            labels = m.get("labels") or {}
            ru_label = str(labels.get("ru") or "").strip().casefold()
            if not ru_label:
                log.warning(
                    "crosswalk_mapping_missing_ru_label canonical_id=%s",
                    canonical_id,
                )
                continue
            ids = mapping.setdefault(ru_label, [])
            if canonical_id not in ids:
                ids.append(canonical_id)
        break
    _crosswalk_cache = mapping
    if mapping:
        log.info("crosswalk_loaded targets=%s", sorted(mapping))
    return mapping


class WorldModel:
    """
    Структурированная модель мира.
    Хранит эпохи, локации, цивилизации, технологии, события, правила.
    Загружается из WORLD_MODEL.json, пополняется Research Engine.
    """

    def __init__(self, data: Optional[dict] = None):
        self._data: dict = data or {}
        self._epochs: list[Epoch] = []
        self._locations: list[Location] = []
        self._civilizations: list[Civilization] = []
        self._technologies: list[Technology] = []
        self._religions: list[Religion] = []
        self._events: list[CanonicalEvent] = []
        self._rules: list[CausalRule] = []
        self._characters_living: dict[str, list[CharacterPresence]] = {}
        self._epoch_parallels: list[EpochParallel] = []
        self._character_relations: list[CharacterRelation] = []
        self._build_indices()

    @classmethod
    def load(cls, path: Optional[Path] = None, use_cache: bool = True) -> "WorldModel":
        global _world_model_cache
        if use_cache and _world_model_cache is not None:
            return _world_model_cache
        if path and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return cls(data)
            except Exception as e:
                log.error("world_model_load_error error=%s", e)
                return cls({})
        # Search in multiple locations
        search_paths = [
            Path("core/CORE/narrative_engine/data/WORLD_MODEL.json"),
            Path("narrative_engine/data/WORLD_MODEL.json"),
            Path("core/narrative_engine/data/WORLD_MODEL.json"),
        ]
        # Also try relative to this file's directory
        here = Path(__file__).parent
        search_paths.append(here / "data" / "WORLD_MODEL.json")
        for p in search_paths:
            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    log.info("world_model_loaded path=%s", p)
                    instance = cls(data)
                    if use_cache:
                        _world_model_cache = instance
                    return instance
                except Exception:
                    continue
        log.warning("world_model_not_found")
        return cls({})

    def _build_indices(self):
        """Построить индексы для быстрого поиска."""
        self._epochs = [Epoch(**e) for e in self._data.get("epochs", [])]
        self._locations = [Location(**location) for location in self._data.get("locations", [])]
        self._civilizations = [Civilization(**c) for c in self._data.get("civilizations", [])]
        self._technologies = [Technology(**t) for t in self._data.get("technologies", [])]
        self._religions = [Religion(**r) for r in self._data.get("religions", [])]
        self._events = [CanonicalEvent(**e) for e in self._data.get("canonical_events", [])]
        self._rules = [CausalRule(**r) for r in self._data.get("causal_rules", [])]
        self._characters_living = {}
        for epoch_id, presences in self._data.get("characters_living", {}).items():
            self._characters_living[epoch_id] = [CharacterPresence(**p) for p in presences]
        self._epoch_parallels = [EpochParallel(**p) for p in self._data.get("epoch_parallels", [])]
        self._character_relations = [CharacterRelation(**r) for r in self._data.get("character_relations", [])]

    def reload(self, path: Optional[Path] = None):
        """Перезагрузить модель из файла."""
        path = path or Path("core/CORE/narrative_engine/data/WORLD_MODEL.json")
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))
            self._build_indices()

    def save(self, path: Optional[Path] = None):
        """Сохранить модель в файл."""
        path = path or Path("core/CORE/narrative_engine/data/WORLD_MODEL.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._data["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    @property
    def data(self) -> dict:
        return self._data

    # ── Запросы ──────────────────────────────────────────────

    def get_epochs(self) -> list[Epoch]:
        return sorted(self._epochs, key=lambda e: e.order)

    def get_epoch(self, epoch_id: str) -> Optional[Epoch]:
        for e in self._epochs:
            if e.id == epoch_id:
                return e
        return None

    def get_locations(self, epoch_id: Optional[str] = None) -> list[Location]:
        if epoch_id:
            return [location for location in self._locations if epoch_id in location.epochs_present]
        return self._locations

    def get_location(self, location_id: str) -> Optional[Location]:
        for location in self._locations:
            if location.id == location_id:
                return location
        return None

    def get_characters_alive(self, epoch_id: str) -> list[CharacterPresence]:
        return self._characters_living.get(epoch_id, [])

    def get_technologies(self, epoch_id: Optional[str] = None) -> list[Technology]:
        if epoch_id:
            epoch = self.get_epoch(epoch_id)
            if epoch:
                tech_ids = set(epoch.technologies_available)
                return [t for t in self._technologies if t.id in tech_ids]
        return self._technologies

    def get_events(self, epoch_id: Optional[str] = None) -> list[CanonicalEvent]:
        if epoch_id:
            return [e for e in self._events if e.epoch == epoch_id]
        return sorted(self._events, key=lambda e: (e.epoch, e.order_in_epoch))

    def get_rules(self) -> list[CausalRule]:
        return self._rules

    def get_constraints_for(self, epoch_id: Optional[str] = None,
                            location_id: Optional[str] = None) -> dict:
        """Получить ограничения для сценария."""
        constraints = {
            "epochs": [],
            "locations": [],
            "characters_alive": [],
            "technologies": [],
            "events_before": [],
            "events_after": [],
            "rules": [],
        }
        if epoch_id:
            ep = self.get_epoch(epoch_id)
            if ep:
                constraints["epochs"].append(ep.model_dump())
            constraints["characters_alive"] = [
                p.model_dump() for p in self.get_characters_alive(epoch_id)
            ]
            constraints["technologies"] = [
                t.model_dump() for t in self.get_technologies(epoch_id)
            ]
            constraints["events_before"] = [
                e.model_dump() for e in self.get_events(epoch_id)
            ]
        if location_id:
            loc = self.get_location(location_id)
            if loc:
                constraints["locations"].append(loc.model_dump())
        constraints["rules"] = [r.model_dump() for r in self._rules]
        return constraints

    def find_epoch_by_text(self, text: str) -> Optional[Epoch]:
        """Найти эпоху по тексту запроса."""
        text_lower = text.lower()
        for ep in self._epochs:
            if (ep.name.lower() in text_lower or
                ep.name_ru.lower() in text_lower or
                ep.id.replace("_", " ") in text_lower):
                return ep
        return None

    def find_location_by_text(self, text: str) -> Optional[Location]:
        """Найти локацию по тексту запроса."""
        text_lower = text.lower()
        for loc in self._locations:
            if (loc.name.lower() in text_lower or
                loc.name_ru.lower() in text_lower or
                loc.id.replace("_", " ") in text_lower):
                return loc
            # Partial match for Russian case variations
            for word in text_lower.split():
                if len(word) >= 4 and word.startswith(loc.name_ru.lower()[:4]):
                    return loc
        return None

    @staticmethod
    def invalidate_cache():
        """Сбросить кэш (после обновления Research Engine)."""
        global _world_model_cache, _crosswalk_cache
        _world_model_cache = None
        _crosswalk_cache = None

    def get_epoch_parallels(self) -> list[EpochParallel]:
        """Все параллели/зеркальности между эпохами."""
        return self._epoch_parallels

    def get_character_relations(self, character_name: Optional[str] = None) -> list[CharacterRelation]:
        """Связи персонажей. Если указано имя — только для этого персонажа."""
        if character_name:
            return [r for r in self._character_relations if r.character == character_name]
        return self._character_relations

    def get_character_mentors(self, character_name: str) -> list[str]:
        """Имена наставников персонажа."""
        return [r.character for r in self._character_relations
                if r.target == character_name and r.relation == "mentor_of"]

    def get_character_students(self, character_name: str) -> list[str]:
        """Имена учеников персонажа."""
        return [r.target for r in self._character_relations
                if r.character == character_name and r.relation == "mentor_of"]

    def summary(self) -> str:
        """Краткая сводка модели мира."""
        return (
            f"Мир: {len(self._epochs)} эпох, {len(self._locations)} локаций, "
            f"{len(self._events)} событий, {len(self._rules)} правил, "
            f"{len(self._technologies)} технологий, {len(self._civilizations)} цивилизаций, "
            f"{len(self._epoch_parallels)} параллелей, {len(self._character_relations)} связей персонажей"
        )

    # ── Temporal Integration (M4) ────────────────────────────────────

    def _entity_ids_for_epoch(self, epoch_id: str) -> list[str]:
        """World Engine entity_ids, подтверждённо связанные с эпохой.

        Только approved crosswalk + реальные canonical events (event.epoch и
        event.location_id). Никаких выводов по названию и никакой опоры на
        пустой Location.epochs_present.
        """
        mapping = _load_approved_crosswalk()
        if not mapping:
            return []
        ids: set[str] = set()
        for ev in self._events:
            if ev.epoch == epoch_id and ev.location_id in mapping:
                ids.update(mapping[ev.location_id])
        return sorted(ids)

    def get_temporal_node(self, epoch_id: str) -> Optional[dict]:
        """Convert Epoch to TemporalNode dict.

        M4: мост между WorldModel и Temporal Model.
        НЕ создаёт новых узлов — только транслирует существующие Epoch.
        """
        epoch = self.get_epoch(epoch_id)
        if not epoch:
            return None

        from narrative_engine.temporal.precision import TemporalPrecision
        from narrative_engine.source_levels import canonical_provenance

        return {
            "id": f"temporal_{epoch_id}",
            "label": epoch.name_ru,
            "precision": TemporalPrecision.RELATIVE.value,
            "era_id": epoch.id,
            "entity_ids": self._entity_ids_for_epoch(epoch_id),
            "event_ids": [e.id for e in self.get_events(epoch_id)],
            "provenance": [canonical_provenance().to_dict()] if epoch.provenance else [],
            "confidence": 0.8,
            "bounds": {
                "start": epoch.start_event,
                "end": epoch.end_event,
            } if epoch.start_event or epoch.end_event else None,
            "notes": f"Epoch order: {epoch.order}",
            "is_anchor": epoch_id == "arkaim_era",
        }

    def get_temporal_chain(self, direction: str = "BACKWARD") -> dict:
        """Build TemporalChain from all WorldModel epochs.

        M4: строит temporal chain из существующих эпох.
        НЕ создаёт новых узлов и связей.
        """
        from narrative_engine.temporal.chain import TemporalChain, ChainDirection
        from narrative_engine.temporal.relation import TemporalRelation
        from narrative_engine.temporal.gap import TemporalGap, EvidenceStatus

        epochs = self.get_epochs()
        if not epochs:
            return TemporalChain(
                id="empty_chain",
                label="Empty Temporal Chain",
                direction=ChainDirection.BACKWARD,
            ).to_dict()

        chain = TemporalChain(
            id=f"chain_{direction.lower()}",
            label=f"Temporal Chain ({direction})",
            direction=ChainDirection(direction),
        )

        # Add nodes from epochs
        for ep in epochs:
            node_data = self.get_temporal_node(ep.id)
            if node_data:
                from narrative_engine.temporal.node import TemporalNode
                node = TemporalNode.from_dict(node_data)
                chain.add_node(node)

        # Add PRECEDES relations between consecutive epochs
        for i in range(len(epochs) - 1):
            src = f"temporal_{epochs[i].id}"
            tgt = f"temporal_{epochs[i+1].id}"
            chain.add_relation(TemporalRelation.precedes(src, tgt))

        # Add gaps where epochs have no explicit connection
        for i in range(len(epochs) - 1):
            src_epoch = epochs[i]
            tgt_epoch = epochs[i + 1]
            # Check if there's an explicit temporal link
            has_link = any(
                r.source_id == f"temporal_{src_epoch.id}" and r.target_id == f"temporal_{tgt_epoch.id}"
                for r in chain.relations
            )
            if not has_link:
                chain.add_gap(TemporalGap(
                    id=f"gap_{src_epoch.id}_{tgt_epoch.id}",
                    from_node=f"temporal_{src_epoch.id}",
                    to_node=f"temporal_{tgt_epoch.id}",
                    reason=f"No explicit temporal link between {src_epoch.name_ru} and {tgt_epoch.name_ru}",
                    evidence_status=EvidenceStatus.PARTIALLY_DOCUMENTED,
                ))

        return chain.to_dict()

    def get_temporal_context(self, epoch_id: str) -> dict:
        """Get rich temporal context for an epoch.

        M4: возвращает TemporalNode + события + персонажи + технологии.
        """
        node_data = self.get_temporal_node(epoch_id)
        if not node_data:
            return {}

        epoch = self.get_epoch(epoch_id)
        events = self.get_events(epoch_id)
        characters = self.get_characters_alive(epoch_id)
        technologies = self.get_technologies(epoch_id)

        return {
            "temporal_node": node_data,
            "epoch": epoch.model_dump() if epoch else None,
            "events": [e.model_dump() for e in events],
            "characters": [c.model_dump() for c in characters],
            "technologies": [t.model_dump() for t in technologies],
            "event_count": len(events),
            "character_count": len(characters),
            "technology_count": len(technologies),
        }

    def get_temporal_summary(self) -> dict:
        """Get summary of temporal model from WorldModel.

        M4: сводка temporal-aware world.
        """
        epochs = self.get_epochs()
        return {
            "total_epochs": len(epochs),
            "epochs": [
                {
                    "id": e.id,
                    "name_ru": e.name_ru,
                    "order": e.order,
                    "event_count": len(self.get_events(e.id)),
                    "character_count": len(self.get_characters_alive(e.id)),
                }
                for e in epochs
            ],
            "temporal_chain_available": len(epochs) > 0,
        }






