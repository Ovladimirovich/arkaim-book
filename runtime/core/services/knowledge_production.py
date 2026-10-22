"""Production-сервис M5/M6/M7 — H2-B (GO-4).

Собирает карточку знаний сущности, прогоняет через неё production-производители
и сохраняет результаты в durable-репозитории.

Свойства:
  * идемпотентность — повторный прогон даёт те же id и не плодит записи;
  * WorldModel не мутируется (единственная граница мутации — M10);
  * HYPOTHESIS не повышается: категория вывода выводится из категорий входов;
  * ничего не выдумывается: конфликт требует реально различающихся значений.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("hermes.services.knowledge_production")


def _repositories():
    from config import config
    from knowledge.conflict_repository import ConflictRepository
    from knowledge.reasoning_repository import ReasoningRepository

    return (
        ConflictRepository(data_dir=config.knowledge_repo_dir("KNOWLEDGE_CONFLICT_DIR")),
        ReasoningRepository(data_dir=config.knowledge_repo_dir("KNOWLEDGE_REASONING_DIR")),
    )


def _build_card(entity_id: str) -> dict[str, Any] | None:
    from knowledge_card.builder import KnowledgeCardBuilder

    try:
        card = KnowledgeCardBuilder().build(entity_id)
    except Exception:
        log.warning("production_card_build_failed entity=%s", entity_id, exc_info=True)
        return None
    if card is None:
        return None
    data = card.to_dict()
    coverage = str((data.get("metadata") or {}).get("coverage_note") or "")
    if "не найдена" in coverage:
        return None
    return data


def run_production_scan(entity_id: str) -> dict[str, Any]:
    """Прогнать production-производители по сущности и сохранить результат.

    Возвращает сводку: сколько конфликтов и рассуждений записано (новых и
    всего), и идентификатор канонической сущности.
    """
    from knowledge.production_producers import build_reasoning, detect_conflicts

    card = _build_card(entity_id)
    if card is None:
        return {
            "entity_id": entity_id,
            "ok": False,
            "reason": "card not built",
            "conflicts": 0,
            "reasoning": 0,
        }

    canonical_id = str((card.get("metadata") or {}).get("entity_id") or entity_id)
    conflicts_repo, reasoning_repo = _repositories()

    existing_conflicts = {record.id for record in conflicts_repo.list()}
    existing_reasoning = {record.id for record in reasoning_repo.list()}

    new_conflicts = 0
    for record in detect_conflicts(canonical_id, card):
        if record.id in existing_conflicts:
            continue
        conflicts_repo.add(record)
        new_conflicts += 1

    new_reasoning = 0
    for result in build_reasoning(canonical_id, card):
        if result.id in existing_reasoning:
            continue
        reasoning_repo.add(result)
        new_reasoning += 1

    log.info(
        "production_scan entity=%s conflicts_new=%d reasoning_new=%d",
        canonical_id,
        new_conflicts,
        new_reasoning,
    )
    return {
        "entity_id": canonical_id,
        "ok": True,
        "conflicts": new_conflicts,
        "reasoning": new_reasoning,
        "conflicts_total": len(conflicts_repo.list()),
        "reasoning_total": len(reasoning_repo.list()),
    }


def record_correction_proposal(
    *,
    finding_id: str,
    subject_id: str,
    superseded_claim_ids: list[str] | None = None,
    evidence_ids: list[str] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Сохранить предложение исправления (M7) из finding'а M10.

    Идемпотентно: повторное предложение с тем же finding не дублируется.
    """
    from config import config
    from knowledge.correction_repository import CorrectionRepository
    from knowledge.production_producers import propose_correction

    repo = CorrectionRepository(data_dir=config.knowledge_repo_dir("KNOWLEDGE_CORRECTION_DIR"))
    record = propose_correction(
        finding_id=finding_id,
        subject_id=subject_id,
        superseded_claim_ids=superseded_claim_ids,
        evidence_ids=evidence_ids,
        reason=reason,
    )
    if repo.get(record.id) is not None:
        return {"created": False, "correction": repo.get(record.id).model_dump(mode="json")}
    repo.add(record)
    return {"created": True, "correction": record.model_dump(mode="json")}


__all__ = ["run_production_scan", "record_correction_proposal"]
