# -*- coding: utf-8 -*-
"""EDM validator (Entity Description Model) — standalone, без зависимости от production-кода.

Проверяет карточку сущности (json) против:
  1. JSON Schema (entity_description.schema.json);
  2. семантических правил модели:
     - unknown-claims: value=null, medium=false, provenance_class=none;
     - reconstructed/hypothesis/artistic_model/fiction => medium=true (только как допущение);
     - medium=true => AI-класс provenance;
     - known/inferred => source_ref обязателен;
     - inferred => created_from обязателен (из каких фактов вывод — контракт EDM-RES);
     - constraints.required_unknown: пути обязаны присутствовать в claims со статусом unknown;
     - дубликаты: одно свойство (path) МОЖЕТ нести несколько claim разных статусов/scope
       (много-статусный ledger, EDM-RES); запрещён только полный дубль
       (path + status + scope level + scope id) — одно и то же утверждение не может
       существовать дважды, в том числе с разными значениями;
     - relations: «wears» -> target_type=character.

Запуск:
    python core/CORE/ENTITY_MODEL/entity_model_validate.py [--strict] [examples/...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    sys.stderr.write(
        "EDM validator требует пакет jsonschema (есть в runtime/.venv: pip install jsonschema)\n"
    )
    raise SystemExit(2) from exc

BASE = Path(__file__).resolve().parent
SCHEMA_PATH = BASE / "entity_description.schema.json"

_AI_CLASSES = {"ai_model", "ai_model_artistic", "reconstruction", "artistic_model", "fiction"}
_MEDIUM_STATUSES = {"reconstructed", "hypothesis", "artistic_model", "fiction"}


class EdmError(ValueError):
    """Ошибка валидации EDM-карточки."""


def load_schema() -> dict:
    raw = SCHEMA_PATH.read_bytes().decode("utf-8-sig")
    return json.loads(raw)


def load_entity(path: Path) -> dict:
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def _schema_errors(entity: dict, schema: dict) -> list[str]:
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    return [f"schema: {e.message}" for e in sorted(validator.iter_errors(entity), key=str)]


def _semantic_errors(entity: dict) -> list[str]:
    errors: list[str] = []
    claims: list[dict] = entity.get("claims", [])
    seen_keys: set[tuple] = set()
    forbid_medium = set(entity.get("constraints", {}).get("forbid_medium", []))

    for claim in claims:
        path = claim.get("path")
        status = claim.get("status")
        medium = bool(claim.get("medium", False))
        pclass = claim.get("provenance_class")

        # EDM-RES ledger: одно свойство МОЖЕТ нести несколько claim разных статусов/scope
        # (например, weather=UNKNOWN + weather=clear@artistic_model@media_plan).
        # Запрещён только полный дубль (path, status, scope level, scope id) — одно и то же
        # утверждение не может существовать дважды, в том числе с разными значениями.
        applies = claim.get("applies_to") or {}
        key = (path, status, applies.get("level", "world"), applies.get("id"))
        if key in seen_keys:
            errors.append(f"duplicate claim: {path} @ status={status} scope={key[2]}:{key[3]} "
                         f"(одна карточка не может нести два claim с одинаковым status+scope)")
        seen_keys.add(key)

        if status == "unknown" and claim.get("value") is not None:
            errors.append(f"claim {path}: unknown requires value=null (got {claim.get('value')!r})")
        if status == "unknown" and medium:
            errors.append(f"claim {path}: unknown requires medium=false")
        if status == "unknown" and pclass not in {"none", None}:
            errors.append(f"claim {path}: unknown must have provenance_class=none")

        if status in _MEDIUM_STATUSES and not medium:
            errors.append(f"claim {path}: {status} claims must be medium=true")
        if medium and pclass not in _AI_CLASSES:
            errors.append(f"claim {path}: medium=true requires AI provenance class, got {pclass!r}")
        if medium and path in forbid_medium:
            errors.append(f"claim {path}: constraints.forbid_medium запрещает medium-рендер этого пути")
        if status in {"known", "inferred"} and not claim.get("source_ref"):
            errors.append(f"claim {path}: {status} requires source_ref")
        if status == "inferred" and not claim.get("created_from"):
            errors.append(f"claim {path}: inferred requires created_from (фактовая база вывода)")
        if status in {"artistic_model", "fiction"} and not claim.get("applies_to"):
            errors.append(f"claim {path}: {status} requires applies_to (scope художественного решения)")

    for req in entity.get("constraints", {}).get("required_unknown", []):
        if req.startswith("time."):
            time_block = entity.get("time") or {}
            field = time_block.get(req.split(".", 1)[1], "MISSING")
            if field not in (None, [], {}):
                errors.append(f"constraint: {req} must be empty/unknown (got {field!r})")
        else:
            matching = [c for c in claims if c.get("path") == req]
            if not any(c.get("status") in {"unknown", "not_applicable"} for c in matching):
                errors.append(f"constraint: required_unknown {req!r} absent or not unknown")

    for rel in entity.get("relations", []):
        rtype = rel.get("type")
        ttype = rel.get("target_type")
        if rtype == "wears" and ttype != "character":
            errors.append(f"relation {rtype} -> target_type must be character, got {ttype!r}")
        conf = rel.get("confidence")
        if conf is not None and not (0.0 <= conf <= 1.0):
            errors.append(f"relation {rtype}: confidence out of range")

    return errors


def validate_entity(entity: dict, schema: dict) -> list[str]:
    """Возвращает список ошибок (пустой — валидно)."""
    if not isinstance(entity, dict):
        return [f"entity must be a JSON object, got {type(entity).__name__}"]
    return _schema_errors(entity, schema) + _semantic_errors(entity)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate EDM entity cards")
    parser.add_argument("paths", nargs="*", default=[str(BASE / "examples")])
    parser.add_argument("--strict", action="store_true", help="any error -> exit 1")
    args = parser.parse_args(argv)

    schema = load_schema()
    targets: list[Path] = []
    for p in args.paths:
        pp = Path(p)
        if pp.is_dir():
            targets.extend(sorted(pp.glob("*.json")))
        else:
            targets.append(pp)

    failed = 0
    for target in targets:
        try:
            entity = load_entity(target)
        except Exception as exc:
            print(f"[FAIL] {target}: cannot load: {exc}")
            failed += 1
            continue
        if not isinstance(entity, dict):
            # Не EDM-карточка (например, ROUNDTRIP_REPORT.json) — пропускаем.
            print(f"[SKIP] {target.name}: not an EDM entity object ({type(entity).__name__})")
            continue
        errors = validate_entity(entity, schema)
        if errors:
            print(f"[FAIL] {target.name}:")
            for e in errors:
                print(f"   - {e}")
            failed += 1
        else:
            print(f"[OK]   {target.name}")
    if args.strict and failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

