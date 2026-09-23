"""
Валидатор Генома Книги.
Проверяет JSON-файлы на соответствие Pydantic-схемам.
Поддерживает catalog_texts, philosophy, новую структуру modules.
"""
import json
from pathlib import Path
from typing import List, Tuple, Optional
from pydantic import ValidationError

from genome.schema import (
    BookGenome, Theme, Value, Character, Symbol, Conflict, WorldEntity,
    CatalogText,
)
from config import config

KNOWLEDGE = config.KNOWLEDGE_DIR
GENOME_DIR = config.GENOME_DIR


def _extract_errors(e: ValidationError) -> List[str]:
    return [f"{err['loc']}: {err['msg']}" for err in e.errors()]


def validate_module(data: list, model_class, name: str) -> Tuple[list, List[str]]:
    errors = []
    items = []
    for i, item in enumerate(data):
        try:
            items.append(model_class(**item))
        except ValidationError as e:
            errors.extend(f"{name}[{i}].{e}" for e in _extract_errors(e))
    return items, errors


def validate_genome(data: dict) -> Tuple[bool, List[str], Optional[BookGenome]]:
    """
    Валидирует весь геном через Pydantic.
    Возвращает (passed, errors, genome).
    """
    errors = []

    # Валидация модулей по отдельности (с понятными ошибками)
    modules = data.get("modules", {})

    themes, te = validate_module(modules.get("themes", []), Theme, "theme")
    errors.extend(te)

    values, ve = validate_module(modules.get("values", []), Value, "value")
    errors.extend(ve)

    characters, ce = validate_module(modules.get("characters", []), Character, "character")
    errors.extend(ce)

    symbols, se = validate_module(modules.get("symbols", []), Symbol, "symbol")
    errors.extend(se)

    conflicts, coe = validate_module(modules.get("conflicts", []), Conflict, "conflict")
    errors.extend(coe)

    world_entities, we = validate_module(data.get("world_entities", []), WorldEntity, "world_entity")
    errors.extend(we)

    catalog_texts, cte = validate_module(data.get("catalog_texts", []), CatalogText, "catalog_text")
    errors.extend(cte)

    # Валидация полного генома
    try:
        genome = BookGenome(**data)
        if errors:
            genome.validation.score = max(0.0, 1.0 - (len(errors) * 0.1))
            genome.validation.passed = genome.validation.score >= 0.7
        else:
            genome.validation.score = 1.0
            genome.validation.passed = True
    except ValidationError as e:
        genome = None
        errors.extend(f"genome: {e}" for e in _extract_errors(e))

    passed = genome is not None and genome.validation.passed if genome else False
    return passed, errors, genome


def validate_genome_file(path: Path) -> Tuple[bool, List[str], Optional[BookGenome]]:
    """Загрузить и валидировать файл генома."""
    if not path.exists():
        return False, [f"File not found: {path}"], None
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate_genome(data)


def main():
    """Запуск валидации сохранённого генома."""
    print("=" * 60)
    print("BOOK GENOME VALIDATOR")
    print("=" * 60)

    genome_path = GENOME_DIR / "GENOME_v1.0.0.json"
    all_ok = True

    if genome_path.exists():
        print(f"\nValidating: {genome_path.name}")
        passed, errors, genome = validate_genome_file(genome_path)
        if passed:
            print(f"  VALIDATION PASSED: score={genome.validation.score}")
            print(f"  Characters: {len(genome.modules.characters)}")
            print(f"  Themes: {len(genome.modules.themes)}")
            print(f"  Symbols: {len(genome.modules.symbols)}")
            print(f"  Conflicts: {len(genome.modules.conflicts)}")
            print(f"  World entities: {len(genome.world_entities)}")
            print(f"  Catalog texts: {len(genome.catalog_texts)}")
        else:
            all_ok = False
            print(f"  VALIDATION FAILED: {len(errors)} errors")
            for e in errors[:15]:
                print(f"    - {e}")
            if len(errors) > 15:
                print(f"    ... and {len(errors) - 15} more")
    else:
        print(f"\n  Genome not found: {genome_path}")
        all_ok = False

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE." if all_ok else "VALIDATION NEEDS WORK.")
    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    main()
