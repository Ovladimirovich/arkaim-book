"""Read-only временная линия сцен сценария по подтверждённым эпохам.

Линия строится поверх уже посчитанного слоя связей
(``core/CORE/knowledge/screenplay_scene_world_links.py``). Эпоха сцены
проставляется ТОЛЬКО из подтверждённой цепочки:

    одобренная связь сценарий↔книга → одобренная claim-связь →
    каноническое событие World Model → эпоха и temporal-узел

Сцены без такой цепочки получают честную отметку «эпоха не установлена»
с причиной. Эпоха не выводится по главам, по порядку сцен и не додумывается.

Модуль ничего не пишет и не создаёт новых сущностей.
"""

from __future__ import annotations

from typing import Any

from .screenplay_scene_catalog import list_scenes

STATUS_CONFIRMED = "CONFIRMED"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_AMBIGUOUS = "AMBIGUOUS"

_BASIS = (
    "подтверждённая цепочка: одобренная связь сценарий↔книга → одобренная "
    "claim-связь → каноническое событие World Model → эпоха"
)


def _epoch_index() -> dict[str, dict[str, Any]]:
    """Метаданные эпох World Model (id → имя и порядок)."""
    from narrative_engine.world_model import WorldModel

    world = WorldModel.load()
    return {
        epoch.id: {"name_ru": epoch.name_ru, "order": epoch.order}
        for epoch in world.get_epochs()
    }


def _scene_entry(
    scene: dict[str, Any], epochs: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    links = scene.get("world_links") or []
    confirmed = [
        link
        for link in links
        if link.get("link_type") == "event" and link.get("status") == STATUS_CONFIRMED
    ]
    event_ids = sorted(
        {
            str(link.get("target_id") or "")
            for link in confirmed
            if link.get("target_id")
        }
    )
    epoch_ids = sorted(
        {str(link.get("epoch_id") or "") for link in confirmed if link.get("epoch_id")}
    )

    missing = scene.get("world_link_missing") or {}
    reason = str(missing.get("event") or "")

    if len(epoch_ids) > 1:
        return {
            "scene_id": scene.get("scene_id", ""),
            "order_global": scene.get("order_global", 0),
            "title": scene.get("title", ""),
            "epoch_id": "",
            "epoch_name_ru": "",
            "temporal_node_id": "",
            "event_ids": event_ids,
            "epoch_status": STATUS_AMBIGUOUS,
            "reason": "подтверждённые события относятся к разным эпохам: "
            + ", ".join(epoch_ids),
        }

    epoch_id = epoch_ids[0] if epoch_ids else ""
    meta = epochs.get(epoch_id) or {}
    return {
        "scene_id": scene.get("scene_id", ""),
        "order_global": scene.get("order_global", 0),
        "title": scene.get("title", ""),
        "epoch_id": epoch_id,
        "epoch_name_ru": str(meta.get("name_ru") or ""),
        "temporal_node_id": f"temporal_{epoch_id}" if epoch_id else "",
        "event_ids": event_ids,
        "epoch_status": STATUS_CONFIRMED if epoch_id else STATUS_UNRESOLVED,
        "reason": ""
        if epoch_id
        else (reason or "нет подтверждённой цепочки до канонического события"),
    }


def build_scene_timeline() -> dict[str, Any]:
    """Собрать временную линию сцен сценария по подтверждённым эпохам."""
    epochs = _epoch_index()
    scenes = list_scenes()
    entries = [_scene_entry(scene, epochs) for scene in scenes]

    by_epoch: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        if entry["epoch_id"]:
            by_epoch.setdefault(entry["epoch_id"], []).append(entry)

    epoch_blocks: list[dict[str, Any]] = []
    for epoch_id, scene_entries in by_epoch.items():
        meta = epochs.get(epoch_id) or {}
        epoch_blocks.append(
            {
                "epoch_id": epoch_id,
                "epoch_name_ru": str(meta.get("name_ru") or ""),
                "order": int(meta.get("order") or 0),
                "temporal_node_id": f"temporal_{epoch_id}",
                "scene_count": len(scene_entries),
                "scene_ids": [entry["scene_id"] for entry in scene_entries],
            }
        )
    epoch_blocks.sort(key=lambda block: (block["order"], block["epoch_id"]))

    with_epoch = sum(1 for entry in entries if entry["epoch_id"])
    without_epoch = len(entries) - with_epoch
    coverage = round(with_epoch / len(entries), 4) if entries else 0.0

    return {
        "scenes": entries,
        "epochs": epoch_blocks,
        "summary": {
            "scene_count": len(entries),
            "scenes_with_epoch": with_epoch,
            "scenes_without_epoch": without_epoch,
            "epoch_count": len(epoch_blocks),
            "coverage": coverage,
        },
        "basis": _BASIS,
        "limitations": [
            "Эпоха проставляется только по подтверждённой цепочке до канонического события.",
            f"Сцен без подтверждённой эпохи: {without_epoch} из {len(entries)} — эпоха для них не установлена и не выводится.",
            "Порядок сцен — канонический порядок замороженного сценария, а не восстановленная хронология.",
        ],
    }


__all__ = ["build_scene_timeline"]
