"""World Model Writer — применение находок к World Model."""

import logging
from pathlib import Path

from narrative_engine.world_model import WorldModel
from narrative_engine.research.cross_referencer import ResearchFinding

log = logging.getLogger("hermes.narrative.world_model_writer")

# Абсолютный путь к каноническому WORLD_MODEL.json (независимый от CWD).
# core/CORE/narrative_engine/research/ → parents[2] = core/CORE/
_CANONICAL_WM_PATH = (
    Path(__file__).resolve().parents[2]
    / "narrative_engine"
    / "data"
    / "WORLD_MODEL.json"
)


def _canonical_world_model_path() -> Path:
    """Возвращает абсолютный путь к каноническому WORLD_MODEL.json."""
    return _CANONICAL_WM_PATH


def apply_finding_to_world_model(
    finding: ResearchFinding, world_model: WorldModel
) -> bool:
    """Применить находку к World Model."""
    if not finding.suggested_fact:
        return False

    fact = finding.suggested_fact
    entity_type = fact.get("entity_type", "")
    entity_name = fact.get("entity_name", "")
    description = fact.get("description", "")

    if entity_type == "location":
        # Добавляем локацию, если её нет
        loc_id = entity_name.lower().replace(" ", "_")
        existing = world_model.get_location(loc_id)
        if not existing and any(
            location.name_ru.casefold() == entity_name.strip().casefold()
            for location in world_model.get_locations()
        ):
            # Место с таким именем уже есть (в т.ч. под другим id) —
            # новая запись создала бы дубль идентичности.
            log.info("location_duplicate_skipped name=%s", entity_name)
            existing = True
        if not existing:
            from narrative_engine.world_model import Location as _Loc

            loc_data = {
                "id": loc_id,
                "name": entity_name,
                "name_ru": entity_name,
                "type": "other",
                "description": description,
                "epochs_present": [],
                "source_level": finding.source_level,
                "provenance": [],
            }
            world_model._data.setdefault("locations", []).append(loc_data)
            world_model._locations.append(_Loc(**loc_data))
            log.info("location_added id=%s", loc_id)

    elif entity_type == "character":
        # Добавляем персонажа в characters_living
        # Try to determine epoch from context
        epoch = "unknown"
        if hasattr(finding, "context") and finding.context:
            epoch = finding.context.get("epoch", "unknown")

        if epoch not in world_model._characters_living:
            world_model._characters_living[epoch] = []

        # Check if character already exists
        existing_chars = {
            c.character_name for c in world_model._characters_living[epoch]
        }
        if entity_name not in existing_chars:
            from narrative_engine.world_model import CharacterPresence

            char_data = {
                "character_name": entity_name,
                "epoch": epoch,
                "status": "alive",
                "notes": description[:500] if description else "",
                "source_level": finding.source_level,
            }
            world_model._data.setdefault("characters_living", {}).setdefault(
                epoch, []
            ).append(char_data)
            world_model._characters_living[epoch].append(CharacterPresence(**char_data))
            log.info("character_added name=%s epoch=%s", entity_name, epoch)

    elif entity_type == "technology":
        tech_id = entity_name.lower().replace(" ", "_")
        existing_techs = {t.id for t in world_model._technologies}
        if tech_id not in existing_techs:
            from narrative_engine.world_model import Technology

            tech_data = {
                "id": tech_id,
                "name": entity_name,
                "name_ru": entity_name,
                "description": description,
                "source_level": finding.source_level,
            }
            world_model._data.setdefault("technologies", []).append(tech_data)
            world_model._technologies.append(Technology(**tech_data))
            log.info("technology_added id=%s", tech_id)

    elif entity_type == "concept":
        # Концепции добавляются как описания в causal_rules
        concept_id = entity_name.lower().replace(" ", "_")
        existing_rules = {r.id for r in world_model._causal_rules}
        if concept_id not in existing_rules:
            from narrative_engine.world_model import CausalRule

            rule_data = {
                "id": concept_id,
                "description": f"{entity_name}: {description[:500] if description else ''}",
                "rule_type": "dependency",
                "condition": f"concept_{concept_id}",
                "source_level": finding.source_level,
            }
            world_model._data.setdefault("causal_rules", []).append(rule_data)
            world_model._causal_rules.append(CausalRule(**rule_data))
            log.info("concept_added id=%s", concept_id)

    return True


def apply_findings(
    findings: list[ResearchFinding],
    world_model: WorldModel,
    job: dict | None = None,
) -> dict:
    """Применить список находок к World Model.

    Gate: ``job`` с ``approved_by`` требуется для каждой находки —
    без явного человеческого одобрения World Model не изменяется.
    Сохранение происходит только в канонический абсолютный путь
    (независимо от CWD процесса).
    """
    approved = job is not None and bool(job.get("approved_by"))
    applied = 0
    failed = 0
    for finding in findings:
        try:
            if not approved:
                log.info("finding_rejected_no_approval finding=%s", finding.id)
                failed += 1
                continue
            if apply_finding_to_world_model(finding, world_model):
                applied += 1
            else:
                failed += 1
        except Exception as e:
            log.error("apply_finding_error finding=%s error=%s", finding.id, e)
            failed += 1

    # Сохраняем обновлённую модель только в канонический абсолютный путь
    if applied > 0:
        canonical_path = _canonical_world_model_path()
        world_model.save(path=canonical_path)
        world_model.reload(path=canonical_path)
        log.info(
            "world_model_saved path=%s applied=%d failed=%d",
            canonical_path,
            applied,
            failed,
        )

    return {"applied": applied, "failed": failed, "total": len(findings)}
