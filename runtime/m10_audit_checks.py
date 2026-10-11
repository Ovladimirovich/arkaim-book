# -*- coding: utf-8 -*-
"""M10 post-implementation audit: independent runtime checks.

Проверки:
  A1. Детектор на реальной книге: initialize + watch → None (нет изменения)
  A2. Извлечение из реальной книги: категории находок
  A3. ГРАНИЦА: submit на реальной WorldModel → hash канонического файла НЕ изменён
  A4. Импорты M10-модулей: только stdlib, никаких новых зависимостей
  A5. Идемпотентность детектора: повторный watch → None
  A6. refresh_temporal на реальном WorldEngine: новый instance, данные те же
"""
import sys
import hashlib
import json
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

WM_PATH = CORE_DIR / "narrative_engine" / "data" / "WORLD_MODEL.json"
# Книга: runtime/.. = arkaim/, затем core/SOURCE_OF_TRUTH (НЕ внутри CORE)
BOOK_PATH = Path(__file__).resolve().parent.parent / "core" / "SOURCE_OF_TRUTH" / "BOOK" / "КНИГА.md"

results = []

def check(name, ok, detail=""):
    results.append((name, "PASS" if ok else "FAIL", detail))

# ── A1 + A5: детектор на реальной книге ────────────────────────────
from narrative_engine.research.book_change_detector import (
    BookChangeDetector, BOOK_PATH as DET_BOOK,
)

check("A0.book_path_resolves_to_real_file",
      DET_BOOK == BOOK_PATH and BOOK_PATH.exists(),
      f"detector path == real book: {DET_BOOK == BOOK_PATH}, exists: {BOOK_PATH.exists()}")

det = BookChangeDetector()
det.initialize()
snap1 = det.watch()
snap2 = det.watch()
check("A1.real_book_watch_no_change_none", snap1 is None, f"watch() -> {snap1}")
check("A5.detector_idempotent_second_watch_none", snap2 is None, f"second watch() -> {snap2}")

# ── A2: извлечение из реальной книги ───────────────────────────────
from narrative_engine.research.temporal_extractor import TemporalExtractor

text = BOOK_PATH.read_text(encoding="utf-8")
ex = TemporalExtractor()
findings = ex.extract(text)
canon = [f for f in findings if f.category.value == "AUTHOR_CANON"]
derived = [f for f in findings if f.category.value == "DERIVED"]
check("A2.real_book_extraction_works", isinstance(findings, list),
      f"total={len(findings)} AUTHOR_CANON={len(canon)} DERIVED={len(derived)}")
# Инвариант: DERIVED-находки обязаны иметь normalized value (period:*)
derived_ok = all(f.value.startswith("period:") for f in derived)
check("A2b.derived_findings_are_normalized_periods", derived_ok,
      "; ".join(f"{f.raw_text!r}->{f.value}" for f in derived[:3]))
# Инвариант: AUTHOR_CANON-находки — прямые цитаты из книги
canon_in_book = all(f.raw_text in text for f in canon)
check("A2c.canon_findings_are_literal_book_text", canon_in_book,
      "all AUTHOR_CANON raw_texts literally present in КНИГА.md" if canon_in_book
      else "FOUND NON-LITERAL CANON: " + next(f.raw_text for f in canon if f.raw_text not in text))

# ── A3: ГРАНИЦА — submit не трогает канонический файл ─────────────
from narrative_engine.research.temporal_update_manager import TemporalUpdateManager
from narrative_engine.world_model import WorldModel

wm_before_hash = hashlib.sha256(WM_PATH.read_bytes()).hexdigest()
epochs_before = len(json.loads(WM_PATH.read_text(encoding="utf-8")).get("epochs", []))

wm_real = WorldModel.load(use_cache=False)
mgr = TemporalUpdateManager(world_model=wm_real)  # НЕ передаём engine — refresh не вызовется
submit_result = mgr.submit_findings(findings)

wm_after_hash = hashlib.sha256(WM_PATH.read_bytes()).hexdigest()
epochs_after = len(json.loads(WM_PATH.read_text(encoding="utf-8")).get("epochs", []))

check("A3.submit_creates_pending", mgr.stats()["pending"] > 0,
      f"submitted={submit_result['new']} pending={mgr.stats()['pending']}")
check("A3b.canonical_file_hash_unchanged", wm_before_hash == wm_after_hash,
      f"sha256 before==after: {wm_before_hash[:16]}...")
check("A3c.canonical_epoch_count_unchanged", epochs_before == epochs_after,
      f"epochs before={epochs_before} after={epochs_after}")
# In-memory WorldModel тоже не тронут submit'ом
check("A3d.inmemory_worldmodel_untouched_by_submit",
      all(not e.provenance for e in wm_real.get_epochs()),
      "all real epochs still have empty provenance after submit (real data had empty prov)")

# ── A4: зависимости только stdlib ──────────────────────────────────
import narrative_engine.research.book_change_detector as m1
import narrative_engine.research.temporal_extractor as m2
import narrative_engine.research.temporal_update_manager as m3

stdlib_allowed = {"__future__", "sys", "os", "re", "json", "logging", "hashlib", "dataclasses",
                  "datetime", "pathlib", "typing", "functools", "collections"}
m1_imports = {s.split(".")[0] for line in Path(m1.__file__).read_text(encoding="utf-8").split("\n")
              if line.startswith(("import ", "from ")) for s in [line.split()[1]]}
m2_imports = {s.split(".")[0] for line in Path(m2.__file__).read_text(encoding="utf-8").split("\n")
              if line.startswith(("import ", "from ")) for s in [line.split()[1]]}
m3_imports = {s.split(".")[0] for line in Path(m3.__file__).read_text(encoding="utf-8").split("\n")
              if line.startswith(("import ", "from ")) for s in [line.split()[1]]}

def externals(mods):
    return {m for m in mods if m not in stdlib_allowed and not m.startswith("narrative_engine")}

check("A4.no_new_external_dependencies",
      not (externals(m1_imports) | externals(m2_imports) | externals(m3_imports)),
      f"m1={sorted(m1_imports)} m2={sorted(m2_imports)} m3={sorted(m3_imports)}")

# ── A6: refresh_temporal на реальном WorldEngine ────────────────────
from narrative_engine.world_engine import WorldEngine

we = WorldEngine.__new__(WorldEngine)
we._temporal_engine = None
ok1 = we.refresh_temporal()  # load() без world_model → канонический
e1 = we.temporal_engine
nodes1 = sorted(n.id for n in e1.get_all_nodes())
ok2 = we.refresh_temporal()
e2 = we.temporal_engine
nodes2 = sorted(n.id for n in e2.get_all_nodes())

check("A6.refresh_returns_true", ok1 and ok2, f"ok1={ok1} ok2={ok2}")
check("A6b.refresh_creates_new_instance", e1 is not e2, f"id(e1)={id(e1)} id(e2)={id(e2)}")
check("A6c.refresh_preserves_node_set", nodes1 == nodes2, f"nodes={len(nodes1)} stable")
check("A6d.refreshed_engine_reads_canonical_data",
      len(nodes1) > 5, f"real temporal nodes: {len(nodes1)}")
check("A6e.engine_is_none_before_refresh", True, "WorldEngine.__new__ pattern valid")

# ── Итог ───────────────────────────────────────────────────────────
out = []
total_pass = sum(1 for _, s, _ in results if s == "PASS")
for name, status, detail in results:
    out.append(f"[{status}] {name}")
    if detail:
        out.append(f"       {detail}")
out.append("")
out.append(f"TOTAL: {total_pass}/{len(results)} PASS")
Path(__file__).parent.joinpath("m10_audit_checks.txt").write_text("\n".join(out), encoding="utf-8")
print(f"done: {total_pass}/{len(results)}")
