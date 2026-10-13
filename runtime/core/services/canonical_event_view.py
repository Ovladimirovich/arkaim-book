"""M19 — Canonical Event View.

Read-only представление канонического события: объединяет описание из
WORLD_MODEL, подтверждённые claim-связи из claim_temporal_links.json,
исходные фрагменты книги, provenance, эпоху/temporal-узел и утверждённые
сценарные связи (если они действительно относятся к отображаемым материалам).

Не создаёт новых событий, claims, связей или временных узлов.
Не считает номер главы доказательством принадлежности claim к событию.
Не объявляет сценарную сцену описанием события — сохраняет исходное
обоснование текстового соответствия.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("services.canonical_event_view")


def _load_catalog_index() -> dict[str, dict[str, Any]]:
    """Индекс enriched_catalog: claim_id → {text, chunk_id, chapter_title, ...}.

    claim_id = CanonClaim.make_id(text, source_id="book", location=f"chunk:{chunk_id}").
    Тот же контракт, что в knowledge_cards._card_claim_id и
    knowledge_core_context._claim_temporal_references.
    """
    from config import config
    from narrative_engine.provenance.claim import CanonClaim

    import json

    catalog_path = config.KNOWLEDGE_DIR / "enriched_catalog.json"
    if not catalog_path.exists():
        return {}
    try:
        catalog = json.loads(catalog_path.read_bytes())
    except Exception as exc:
        log.warning("canonical_event_catalog_load_failed error=%s", exc)
        return {}

    index: dict[str, dict[str, Any]] = {}
    for entry in catalog:
        text = str(entry.get("text") or "")
        chunk_id = str(entry.get("id") or entry.get("chunk_id") or "")
        if not text or not chunk_id:
            continue
        claim_id = CanonClaim.make_id(text, source_id="book", location=f"chunk:{chunk_id}")
        index[claim_id] = {
            "text": text,
            "chunk_id": chunk_id,
            "chapter_title": entry.get("chapter_title", ""),
            "chapter_number": entry.get("chapter_number", -1),
            "source_ref": f"book:{chunk_id}",
            "provenance_category": "AUTHOR_CANON",
        }
    return index


def build_canonical_event_view(event_id: str) -> dict[str, Any]:
    """Собрать read-only представление канонического события.

    Путь данных: event_id → WORLD_MODEL event → epoch → temporal-узел;
    event_id → claim_temporal_links → claim_id → enriched_catalog (текст,
    source_ref) → screenplay_links (если подтверждена связь с chunk).

    Возвращает словарь с полями:
      - event: идентификатор, заголовок, описание, эпоха, provenance
      - temporal: epoch_id, temporal_node_id, chain_valid (только после
        успешной validate_chain())
      - claims: список связанных claims (только те, для которых установлена
        связь с запрашиваемым event_id)
      - screenplay_materials: утверждённые сценарные связи, если они
        относятся к отображаемым книжным фрагментам
      - limitations: явные ограничения
      - found: False, если событие не найдено
    """
    from narrative_engine.world_model import WorldModel
    from knowledge.claim_temporal_linker import ClaimTemporalLinker
    from knowledge.screenplay_linker import ScreenplayBookLinker

    result: dict[str, Any] = {
        "event_id": event_id,
        "found": False,
        "event": {},
        "temporal": {},
        "claims": [],
        "screenplay_materials": [],
        "limitations": [],
    }

    # 1. Загрузить WORLD_MODEL и найти событие
    try:
        wm = WorldModel.load()
    except Exception as exc:
        result["limitations"].append(f"WORLD_MODEL недоступен: {exc}")
        return result

    event = next((e for e in wm.get_events() if e.id == event_id), None)
    if event is None:
        result["limitations"].append(f"Событие {event_id} не найдено в WORLD_MODEL")
        return result

    result["found"] = True
    result["event"] = {
        "id": event.id,
        "title": event.title,
        "title_ru": event.title_ru,
        "description": event.description,
        "epoch": event.epoch,
        "location_id": event.location_id,
        "characters_involved": event.characters_involved,
        "chapter": event.chapter,
        "order_in_epoch": event.order_in_epoch,
        "source_level": event.source_level.value if hasattr(event.source_level, "value") else str(event.source_level),
        "provenance": [p.model_dump(mode="json") if hasattr(p, "model_dump") else str(p) for p in event.provenance],
    }

    # 2. Эпоха и temporal-узел
    epoch = wm.get_epoch(event.epoch)
    temporal_node_id = f"temporal_{event.epoch}"
    result["temporal"] = {
        "epoch_id": event.epoch,
        "epoch_name": epoch.name if epoch else None,
        "temporal_node_id": temporal_node_id,
        "epoch_found": epoch is not None,
    }
    if epoch is None:
        result["limitations"].append(f"Эпоха {event.epoch} события {event_id} не найдена в WORLD_MODEL")

    # 3. Claim-связи из реестра (только с этим event_id)
    try:
        linker = ClaimTemporalLinker.from_json()
    except Exception as exc:
        result["limitations"].append(f"Реестр claim_temporal_links недоступен: {exc}")
        return result

    matching_links = [link for link in linker.links if link.event_id == event_id]
    if not matching_links:
        result["limitations"].append(f"Для события {event_id} нет подтверждённых claim-связей в claim_temporal_links.json")
        return result

    # 4. Индекс каталога для разрешения claim_id → текст/source_ref
    catalog_index = _load_catalog_index()

    # 5. Для каждой связи: валидация цепочки + разрешение текста
    for link in matching_links:
        chain = ClaimTemporalLinker.validate_chain(link)
        claim_entry: dict[str, Any] = {
            "claim_id": link.claim_id,
            "event_id": link.event_id,
            "temporal_node_id": link.temporal_node_id,
            "chain_valid": chain.valid,
            "chain_reason": chain.reason,
            "epoch_id": chain.epoch_id,
            "notes": link.notes,
            "text": None,
            "source_ref": None,
            "provenance_category": None,
            "chunk_id": None,
            "chapter_title": None,
            "text_resolved": False,
        }

        # Разрешить claim_id → текст через enriched_catalog
        catalog_entry = catalog_index.get(link.claim_id)
        if catalog_entry:
            claim_entry["text"] = catalog_entry["text"]
            claim_entry["source_ref"] = catalog_entry["source_ref"]
            claim_entry["provenance_category"] = catalog_entry["provenance_category"]
            claim_entry["chunk_id"] = catalog_entry["chunk_id"]
            claim_entry["chapter_title"] = catalog_entry["chapter_title"]
            claim_entry["text_resolved"] = True
        else:
            result["limitations"].append(f"claim_id {link.claim_id} не разрешён в исходный текст через enriched_catalog (ссылка сохранена, текст недоступен)")

        result["claims"].append(claim_entry)

    # 6. Temporal-цепочка: показывать только после успешной validate_chain
    valid_chains = [c for c in result["claims"] if c["chain_valid"]]
    if valid_chains:
        # Все валидные цепочки для одного события указывают на одну эпоху
        # (validate_chain проверяет temporal_node_id == temporal_{event.epoch})
        result["temporal"]["chain_valid"] = True
    else:
        result["temporal"]["chain_valid"] = False
        invalid_reasons = sorted({c["chain_reason"] for c in result["claims"] if not c["chain_valid"]})
        result["limitations"].append(f"Ни одна claim-цепочка не прошла валидацию (reasons={invalid_reasons})")

    # 7. Сценарные материалы: только при наличии подтверждённой связи
    # с соответствующим книжным фрагментом (не «сцена = описание события»)
    try:
        screenplay_linker = ScreenplayBookLinker.from_json()
    except Exception as exc:
        result["limitations"].append(f"Реестр screenplay_links недоступен: {exc}")
        screenplay_linker = None

    if screenplay_linker:
        resolved_chunk_ids = {c["chunk_id"] for c in result["claims"] if c.get("chunk_id")}
        for chunk_id in sorted(resolved_chunk_ids):
            for slink in screenplay_linker.get_links_for_chunk(chunk_id):
                result["screenplay_materials"].append(
                    {
                        "screenplay_scene_id": slink.screenplay_scene_id,
                        "book_chunk_id": slink.book_chunk_id,
                        "confidence": slink.confidence,
                        "notes": slink.notes,
                        "link_type": "book_chunk_to_scene",
                    }
                )

    if not result["screenplay_materials"]:
        result["limitations"].append("Сценарные материалы не отображаются: нет подтверждённых связей screenplay_links с книжными фрагментами этого события")

    return result
