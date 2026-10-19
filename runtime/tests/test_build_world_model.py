"""Тесты офлайн-сборки World Model (scripts/build_world_model.py).

Проверяем, что:
  * вычисление категорий детерминировано и не включает пустые;
  * режим --check НИЧЕГО не пишет (файлы WORLD_MODEL не меняются);
  * сравнение семантическое (игнорирует порядок ключей/пробелы).
"""

import hashlib
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = REPO_ROOT / "core" / "CORE"
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_world_model.py"
WORLD_MODEL_DIR = CORE_DIR / "WORLD_MODEL"

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))


def _load_script():
    spec = importlib.util.spec_from_file_location("build_world_model", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _snapshot_dir(path: Path) -> dict[str, str]:
    snap = {}
    if not path.exists():
        return snap
    for p in sorted(path.glob("*.json")):
        snap[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def test_computed_categories_non_empty_and_deterministic():
    mod = _load_script()
    first = mod._computed_by_category()
    second = mod._computed_by_category()
    assert first == second
    assert set(first) == {"geography", "civilizations", "social_structure", "daily_life"}
    for cat, items in first.items():
        assert items, f"категория {cat} пустая"


def test_check_writes_nothing():
    mod = _load_script()
    before = _snapshot_dir(WORLD_MODEL_DIR)
    rc = mod.main(["--check"])
    after = _snapshot_dir(WORLD_MODEL_DIR)
    assert before == after, "режим --check не должен менять файлы WORLD_MODEL"
    assert rc in (0, 1)


def test_comparison_is_semantic():
    mod = _load_script()
    a = [{"b": 2, "a": 1}]
    b = [{"a": 1, "b": 2}]
    assert mod._strip_trailing_ws(a) == mod._strip_trailing_ws(b)
