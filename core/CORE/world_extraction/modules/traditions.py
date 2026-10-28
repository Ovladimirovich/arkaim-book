"""Проектор «Производные записи» KNOWLEDGE -> WORLD_MODEL (Этап 3 плана).

Расширение существующего ``world_extraction`` (не новый пайплайн): наполняет
«пустые оболочки» в ``core/CORE/WORLD_MODEL/{RELIGION,RITUALS,MYTHOLOGY}.json``
содержательными производными записями из единых источников KNOWLEDGE.

Карта производности (решение владельца, Этап 3):
- ``WORLD_MODEL/RELIGION.json`` / ``RITUALS.json`` (10+10) — из
  ``ESOTERIC_CONNECTIONS.json#traditions[*]``;
- ``WORLD_MODEL/MYTHOLOGY.json`` ``myth_*`` (15) — из ``SYMBOLS_DEEP.json#items[*]``;
- ``WORLD_MODEL/MYTHOLOGY.json`` ``cosmo_myth_*`` (22) — из ``COSMOLOGY.json#items[*]``,
  причём если item в COSMOLOGY.json — пустое зеркало (``mirrors_from`` в сторону
  ``ESOTERIC_CONNECTIONS.json``), содержимое резолвится по цепочке зеркал.

Правила честного провенанса (контракт Этапа 2 — ADR_EXTERNAL_KNOWLEDGE_CONTRACT):
- производная запись не может претендовать на AUTHOR_CANON;
- ``provenance_category=SYSTEM_INTERPRETATION`` (не UNKNOWN, не CANON);
- обязательная разрешаемая ссылка ``derived_from`` на KNOWLEDGE-источник;
- внешняя/эзотерическая традиция, попавшая в mythology-проекцию, по-прежнему
  называется традицией (не «мифом книги»);
- зеркала (KNOWLEDGE/RITUALS.json, пустые items COSMOLOGY.json) НЕ дублируют
  содержимое источника — только ``mirrors_from``.

Точечная запись: меняется только содержимое «чисто пустых» оболочек
(description, provenance, derived_from); id, структура, несвязанные записи,
confidence не трогаются.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ..models import SYSTEM_INTERPRETATION

log = logging.getLogger("hermes.world_extraction.projection")

# Единые источники истины.
ESOTERIC_FILE = "ESOTERIC_CONNECTIONS.json"
SYMBOLS_DEEP_FILE = "SYMBOLS_DEEP.json"
COSMOLOGY_FILE = "COSMOLOGY.json"


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        log.error("json_read_error path=%s error=%s", path, exc)
        return None


def _parse_mirror_ref(ref: str):
    """Разобрать зеркальную ссылку на элемент KNOWLEDGE.

    Принимает форматы:
      "ESOTERIC_CONNECTIONS.json#traditions[7]"
      "ESOTERIC_CONNECTIONS.json#items[3]"
      "core\\KNOWLEDGE\\ESOTERIC_CONNECTIONS.json.traditions[7]"   (исторический)

    Returns (filename, key, index) или None.
    """
    ref = ref.strip()
    if not ref:
        return None
    # Убираем возможный префикс пути.
    ref = ref.replace("\\", "/")
    if "KNOWLEDGE/" in ref:
        ref = ref.split("KNOWLEDGE/", 1)[-1]
    if "#" not in ref and ".json" not in ref:
        return None
    filename = ""
    key = ""
    index = -1
    if "#" in ref:
        filepart, _, anchor = ref.partition("#")
        filename = filepart.strip()
        if "[" not in anchor:
            return None
        key, _, idx = anchor.partition("[")
        idx = idx.rstrip("]") if idx else ""
        if not idx.isdigit():
            return None
        index = int(idx)
    else:
        # исторический формат: ESOTERIC_CONNECTIONS.json.traditions[N]
        try:
            prefix, _, anchor = ref.rpartition(".json.")
            filename = prefix + ".json"
            key, _, idx = anchor.rpartition("[")
            idx = idx.rstrip("]") if idx else ""
            if not idx.isdigit():
                return None
            index = int(idx)
        except Exception:  # noqa: BLE001
            return None
    if not filename.endswith(".json"):
        filename += ".json"
    return filename, key, index


def _tradition_text(trad: dict) -> str:
    """Содержимое традиции (для резолва зеркал): учение + связь с книгой."""
    parts = []
    if trad.get("core_teaching"):
        parts.append(trad["core_teaching"].strip())
    bc = (trad.get("book_connection") or "").strip()
    if bc and bc.upper() != "UNKNOWN":
        parts.append(f"Связь с книгой: {bc}")
    return " ".join(parts).strip()


def _resolve_blank_item_content(item: dict, knowledge_dir: Path, seen: set) -> str:
    """Резолв содержимого item'а, если сам он пуст, но является зеркалом.

    Каскад зеркал: если у item'а пуст ``layers.literal`` и есть ``mirrors_from``
    (или исторический ``source``-указатель на элемент KNOWLEDGE), берём
    содержимое целевого отмеченного элемента. Возвращает пустую строку,
    если резолв невозможен.
    """
    ref = (
        item.get("mirrors_from") or item.get("MIRRORS_FROM") or item.get("source") or ""
    )
    parsed = _parse_mirror_ref(ref)
    if parsed is None:
        return ""
    filename, target_key, index = parsed
    if ref in seen:
        log.warning("mirror_cycle_detected ref=%s", ref)
        return ""
    seen = seen | {ref}

    source = _read_json(knowledge_dir / filename)
    if not source:
        return ""
    entries = source.get(target_key, [])
    if index >= len(entries):
        return ""
    target = entries[index]
    if not isinstance(target, dict):
        return ""

    # Элемент источника может быть традицией (учение + связь) или item'ом с layers.
    if target_key.endswith("traditions") and target.get("core_teaching") is not None:
        text = _tradition_text(target)
        if text:
            return text
    literal = (target.get("layers") or {}).get("literal")
    if literal and literal.strip():
        return literal.strip()
    # ... либо это снова зеркало (каскад).
    return _resolve_blank_item_content(target, knowledge_dir, seen)


def _make_notes(record: dict, derived_from: str, context: str, source_text: str) -> str:
    """Честная заметка о происхождении производной записи."""
    kind = "внешняя эзотерическая традиция" if context == "tradition" else "тема книги"
    return f"Производная запись от {derived_from} ({kind}). Обоснование: {source_text}"


def _fill_blank(
    record: dict, *, description: str, derived_from: str, context: str
) -> dict:
    """Заполнить содержание «чисто пустой» оболочки, сохранив структуру."""
    filled = dict(record)
    filled["description"] = description
    filled["provenance_category"] = SYSTEM_INTERPRETATION
    filled["provenance_notes"] = _make_notes(
        record, derived_from, context, description[:200]
    )
    filled["derived_from"] = derived_from
    filled["source_level"] = SYSTEM_INTERPRETATION
    return filled


def _is_blank_shell(record: dict) -> bool:
    """«Чисто пустая» оболочка (фильтр из плана, Этап 3): пустой description
    И провенанс в (UNKNOWN, SYSTEM_INTERPRETATION) И производности нет."""
    desc = (record.get("description") or "").strip()
    prov = record.get("provenance_category")
    derived = record.get("derived_from") or record.get("DERIVED_FROM")
    return bool(
        not desc and prov in ("UNKNOWN", "SYSTEM_INTERPRETATION") and not derived
    )


def _items_by_topic(source: dict) -> dict:
    """Индекс источника по topic (для SYMBOLS_DEEP/COSMOLOGY items)."""
    result = {}
    for idx, item in enumerate(source.get("items", [])):
        if isinstance(item, dict) and item.get("topic"):
            result[item["topic"].strip()] = (item, idx)
        result.setdefault(f"#{idx}", (item, idx))
    return result


def project_world_model(
    world_model_dir: Path,
    knowledge_dir: Path,
    *,
    dry_run: bool = False,
) -> dict:
    """Применить проекцию к *трём* WORLD_MODEL-файлам (точечно, идемпотентно).

    Returns:
        dict-отчёт: file -> {"before", "after", "updated": [id...], "errors": [...]}
    """
    esoteric = _read_json(knowledge_dir / ESOTERIC_FILE) or {}
    symbols = _read_json(knowledge_dir / SYMBOLS_DEEP_FILE)
    cosmology = _read_json(knowledge_dir / COSMOLOGY_FILE)

    report: dict = {}

    # ── 1. RELIGION.json / RITUALS.json: традиции из ESOTERIC_CONNECTIONS ──
    trad_lookup = {}
    for idx, trad in enumerate(esoteric.get("traditions", [])):
        if not isinstance(trad, dict) or not trad.get("name"):
            continue
        parts = []
        if trad.get("core_teaching"):
            parts.append(trad["core_teaching"].strip())
        bc = (trad.get("book_connection") or "").strip()
        if bc and bc.upper() != "UNKNOWN":
            parts.append(f"Связь с книгой: {bc}")
        data = {
            "description": " ".join(parts).strip(),
            "derived_from": f"{ESOTERIC_FILE}#traditions[{idx}]",
            "context": "tradition",
        }
        name = trad["name"].strip()
        slug = name.lower().replace(" ", "_")
        trad_lookup[name] = data
        trad_lookup.setdefault(slug, data)

    # ── 2. MYTHOLOGY: myth_* из SYMBOLS_DEEP, cosmo_myth_* из COSMOLOGY ──
    # Ключ = имя в записи; значение = (description, derived_from).
    myth_lookup = {}
    if symbols:
        for item, idx in _items_by_topic(symbols).values():
            if isinstance(item, dict) and item.get("topic"):
                literal = (item.get("layers") or {}).get("literal") or ""
                metaphor = (item.get("layers") or {}).get("metaphorical") or ""
                desc = " ".join(x.strip() for x in (literal, metaphor) if x.strip())
                myth_lookup[item["topic"].strip()] = {
                    "description": desc,
                    "derived_from": f"{SYMBOLS_DEEP_FILE}#items[{idx}]",
                    "context": "theme",
                }

    cosmo_lookup = {}
    if cosmology:
        for item, idx in _items_by_topic(cosmology).values():
            if isinstance(item, dict) and item.get("topic"):
                literal = (item.get("layers") or {}).get("literal") or ""
                is_mirror = not literal.strip()
                if is_mirror:
                    # Пустое зеркало — резолвим по цепочке mirrors_from/source.
                    literal = _resolve_blank_item_content(item, knowledge_dir, set())
                metaphor = (item.get("layers") or {}).get("metaphorical") or ""
                desc = " ".join(x.strip() for x in (literal, metaphor) if x.strip())
                # Зеркала на ESOTERIC — внешние традиции; прямой контент — темы книги.
                context = "tradition" if is_mirror else "theme"
                cosmo_lookup[item["topic"].strip()] = {
                    "description": desc,
                    "derived_from": f"{COSMOLOGY_FILE}#items[{idx}]",
                    "context": context,
                }

    # Спец. обработка: `cosmo_myth_*` традиций идут в mythology-проекцию.
    # Для традиций, не представленных темами в COSMOLOGY, производное берём из ESOTERIC.
    for key, data in trad_lookup.items():
        cosmo_lookup.setdefault(key, data)

    # Маппинг файл -> (категория, префикс, lookup)
    projections = [
        ("RELIGION.json", "religion", "ritual_", trad_lookup),
        ("RITUALS.json", "rituals", "ritual_", trad_lookup),
    ]

    for filename, category, prefix, lookup in projections:
        path = world_model_dir / filename
        if not path.exists():
            report[filename] = {"error": "not_found"}
            continue
        records = _read_json(path)
        if not isinstance(records, list):
            report[filename] = {"warning": "не список — не трогаем"}
            continue

        before = len(records)
        updated = []
        out = []
        for record in records:
            rid = record.get("id", "")
            if not (prefix and rid.startswith(prefix) and _is_blank_shell(record)):
                out.append(record)
                continue
            key = record.get("name", "").strip() or rid[len(prefix) :]
            data = lookup.get(key) or lookup.get(rid[len(prefix) :])
            if not data or not data.get("description"):
                out.append(record)  # нет производного материала — оболочка остаётся
                continue
            filled_data = dict(data)
            context = filled_data.pop("context", "theme")
            out.append(_fill_blank(record, context=context, **filled_data))
            updated.append(rid)

        report[filename] = {
            "before": before,
            "after": len(out),
            "category": category,
            "updated": updated,
        }

        if not dry_run and updated:
            path.write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log.info("world_model_projected file=%s updated=%d", filename, len(updated))

    # ── MYTHOLOGY: единый проход, myth_* и cosmo_myth_* вместе ──────────
    path = world_model_dir / "MYTHOLOGY.json"
    if not path.exists():
        report["MYTHOLOGY.json"] = {"error": "not_found"}
        return report
    records = _read_json(path)
    if not isinstance(records, list):
        report["MYTHOLOGY.json"] = {"warning": "не список — не трогаем"}
        return report

    before = len(records)
    updated = []
    out = []
    for record in records:
        rid = record.get("id", "")
        matched = False
        for prefix, lookup in (("myth_", myth_lookup), ("cosmo_myth_", cosmo_lookup)):
            if not (rid.startswith(prefix) and _is_blank_shell(record)):
                continue
            key = record.get("name", "").strip() or rid[len(prefix) :]
            data = lookup.get(key) or lookup.get(rid[len(prefix) :])
            if not data or not data.get("description"):
                break  # нечем наполнить — оболочка остаётся
            filled_data = dict(data)
            context = filled_data.pop("context", "theme")
            out.append(_fill_blank(record, context=context, **filled_data))
            updated.append(rid)
            matched = True
            break
        if not matched:
            out.append(record)

    report["MYTHOLOGY.json"] = {
        "before": before,
        "after": len(out),
        "category": "mythology",
        "updated": updated,
    }

    if not dry_run and updated:
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("world_model_projected file=MYTHOLOGY.json updated=%d", len(updated))

    return report


# ── Зеркала KNOWLEDGE ───────────────────────────────────────────────────────
# KNOWLEDGE/RITUALS.json и пустые части KNOWLEDGE/COSMOLOGY.json — это зеркала
# ESOTERIC_CONNECTIONS.json (см. "_provenance_metadata" и "source" каждого item).
# По плану (Этап 3) они не должны дублировать содержимое: переписываются в
# "mirrors_from: ESOTERIC_CONNECTIONS.json#traditions[N]" (без копии контента).

ESOTERIC_MIRROR_FILES = ("RITUALS.json", "COSMOLOGY.json")


def _is_esoteric_mirror_item(item: dict) -> bool:
    """Является ли item «пустым зеркалом» ESOTERIC_CONNECTIONS.json.

    Признаки: source-ссылка вида "…ESOTERIC_CONNECTIONS.json.traditions[N]"
    (или "#traditions[N]") И layers.literal пуст (нет собственного контента).
    """
    src = item.get("source") or ""
    if "ESOTERIC_CONNECTIONS.json" not in src:
        return False
    anchor = src.split("ESOTERIC_CONNECTIONS.json", 1)[-1] or ""
    if "traditions[" not in anchor:
        return False
    literal = ((item.get("layers") or {}).get("literal") or "").strip()
    return not literal


def mirrorize_knowledge(
    knowledge_dir: Path,
    *,
    dry_run: bool = False,
) -> dict:
    """Переписать пустые зеркала ESOTERIC в KNOWLEDGE-файлах в ``mirrors_from``.

    Args:
        knowledge_dir: core/KNOWLEDGE.
        dry_run: только отчёт, не писать.

    Returns:
        dict-отчёт: файл -> {"items_before", "items_after", "mirrored": [topic...]}.
    """
    report: dict = {}
    for filename in ESOTERIC_MIRROR_FILES:
        path = knowledge_dir / filename
        if not path.exists():
            report[filename] = {"error": "not_found"}
            continue
        data = _read_json(path)
        if not isinstance(data, dict) or "items" not in data:
            report[filename] = {"warning": "нет items — не трогаем"}
            continue

        items = data["items"]
        before = len(items)
        mirrored: list[str] = []
        out: list[dict] = []
        for item in items:
            if _is_esoteric_mirror_item(item):
                # Только имя/тему + каноническую ссылку на источник;
                # контент не дублируем. Исторический `source` вида
                # "...ESOTERIC_CONNECTIONS.json.traditions[N]" нормализуем в
                # "#traditions[N]" (формат MIRRORS_FROM из плана, Этап 3).
                anchor = ""
                src = item.get("source", "")
                if "ESOTERIC_CONNECTIONS.json" in src:
                    anchor = src.split("ESOTERIC_CONNECTIONS.json", 1)[-1]
                    if anchor.startswith("."):
                        anchor = "#" + anchor[1:]
                out.append(
                    {
                        "topic": item.get("topic", ""),
                        "mirrors_from": "ESOTERIC_CONNECTIONS.json" + anchor,
                    }
                )
                mirrored.append(item.get("topic", ""))
            else:
                out.append(item)

        new_data = dict(data)
        new_data["items"] = out
        if "item_count" in new_data:
            new_data["item_count"] = len(out)
        # Фиксируем назначение файла как зеркала.
        new_data.setdefault("_mirrors_from", "ESOTERIC_CONNECTIONS.json#traditions[*]")

        report[filename] = {
            "items_before": before,
            "items_after": len(out),
            "mirrored": mirrored,
        }
        if not dry_run and mirrored:
            path.write_text(
                json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log.info(
                "knowledge_mirrorized file=%s mirrored=%d", filename, len(mirrored)
            )

    return report
