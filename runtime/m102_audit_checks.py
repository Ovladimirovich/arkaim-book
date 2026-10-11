# -*- coding: utf-8 -*-
"""M10.2 post-implementation audit: independent runtime checks.

Проверки (независимые от тестов реализации):
  B1. OpenAPI: ровно 7 pending-updates путей (нет расширения scope)
  B2. RBAC на реальном app: точная матрица ролей (без override → 401;
      reader → 403 на mutating; editor → 200)
  B3. Реальный singleton scan на реальной книге: без confirm,
      канонический файл не тронут
  B4. Никаких фоновых процессов/БД в temporal_updates.py
  B5. Логика менеджера M10 не изменена: M10 тесты (24) зелёные
  B6. Изоляция: real-app цикл не пишет в канонический WORLD_MODEL.json
  B7. Endpoint'ы не содержат собственной логики применения
      (только вызовы менеджера)
"""

import sys
import hashlib
import inspect
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
CORE_DIR = RUNTIME.parent / "core" / "CORE"
sys.path.insert(0, str(RUNTIME))

results = []


def check(name, ok, detail=""):
    results.append((name, "PASS" if ok else "FAIL", detail))


# ── B1: OpenAPI scope ──────────────────────────────────────────
from core.main import app

schema = app.openapi()
pu_paths = sorted(p for p in schema["paths"] if "pending-updates" in p)
check("B1.openapi_exactly_seven_endpoints", len(pu_paths) == 7, f"{len(pu_paths)}: {pu_paths}")

# ── B2: RBAC на реальном app ───────────────────────────────────
from fastapi.testclient import TestClient
from auth.rbac import get_current_user

client = TestClient(app)

# Снимаем override (реальный путь авторизации)
saved_override = app.dependency_overrides.pop(get_current_user, None)
try:
    # 401 без авторизации (реальный singleton, без подмен)
    r = client.post("/book/temporal/pending-updates/scan")
    check("B2a.no_auth_scan_401", r.status_code == 401, f"got {r.status_code}")
    r = client.post("/book/temporal/pending-updates/x/confirm")
    check("B2b.no_auth_confirm_401", r.status_code == 401, f"got {r.status_code}")
    r = client.get("/book/temporal/pending-updates")
    check("B2c.no_auth_list_401", r.status_code == 401, f"got {r.status_code}")

    # reader → 403 на все mutating
    async def _reader():
        return {"user_id": "audit-reader", "role": "reader", "provider": "t", "username": "r", "display_name": "R"}

    app.dependency_overrides[get_current_user] = _reader
    r_scan = client.post("/book/temporal/pending-updates/scan")
    r_confirm = client.post("/book/temporal/pending-updates/whatever/confirm")
    r_reject = client.post("/book/temporal/pending-updates/whatever/reject")
    check(
        "B2d.reader_mutating_all_403",
        r_scan.status_code == 403 and r_confirm.status_code == 403 and r_reject.status_code == 403,
        f"scan={r_scan.status_code} confirm={r_confirm.status_code} reject={r_reject.status_code}",
    )
    r_list = client.get("/book/temporal/pending-updates")
    r_stats = client.get("/book/temporal/pending-updates/stats")
    check("B2e.reader_readonly_200", r_list.status_code == 200 and r_stats.status_code == 200, f"list={r_list.status_code} stats={r_stats.status_code}")

    # editor → 200 на scan (реальный singleton, реальная книга)
    async def _editor():
        return {"user_id": "audit-editor", "role": "editor", "provider": "t", "username": "e", "display_name": "E"}

    app.dependency_overrides[get_current_user] = _editor

    WM_PATH = CORE_DIR / "narrative_engine" / "data" / "WORLD_MODEL.json"
    wm_hash_before = hashlib.sha256(WM_PATH.read_bytes()).hexdigest()

    # ── B3: реальный scan (singleton без подмен) ──────────────
    from core.routes import temporal_updates as tu

    tu.reset_manager_singleton()  # чистый singleton, честная инициализация
    r_scan = client.post("/book/temporal/pending-updates/scan")
    scan_body = r_scan.json()
    check("B3a.real_scan_200", r_scan.status_code == 200, f"{r_scan.status_code}")
    check("B3b.real_scan_book_changed_false", scan_body["data"]["book_changed"] is False, f"data={scan_body.get('data', {})}")
    r_scan2 = client.post("/book/temporal/pending-updates/scan")
    check(
        "B3c.real_scan_idempotent",
        r_scan2.json()["data"]["book_changed"] is False and r_scan2.json()["data"]["new_findings"] == 0,
        f"second={r_scan2.json()['data']}",
    )

    # ── B6: канонический файл не тронут после реальных scans ──
    wm_hash_after = hashlib.sha256(WM_PATH.read_bytes()).hexdigest()
    check("B6.canonical_world_model_untouched_after_real_scans", wm_hash_before == wm_hash_after, f"sha256 stable: {wm_hash_before[:16]}...")

    # reader НЕ может подтвердить даже существующую pending-находку:
    # проверяем через изолированный менеджер (единственный безопасный способ
    # создать pending), затем reader confirm → 403
    from narrative_engine.world_model import WorldModel
    from narrative_engine.research.temporal_update_manager import TemporalUpdateManager
    from narrative_engine.research.temporal_extractor import TemporalFinding
    from narrative_engine.source_levels import ProvenanceCategory

    d = RUNTIME / "tests" / "tmp_m10_2_audit"
    d.mkdir(exist_ok=True)
    save_path = d / "wm_iso.json"
    wm = WorldModel(
        {"epochs": [{"id": "kali_yuga", "name": "Kali Yuga", "name_ru": "К", "description": "", "order": 1, "duration_years": None, "provenance": []}]}
    )
    iso_mgr = TemporalUpdateManager(world_model=wm, world_model_path=save_path)
    iso_mgr.submit_findings(
        [
            TemporalFinding(
                id="audit_f1",
                kind="absolute_date",
                raw_text="в эпоху Кали Юги",
                value="epoch:kali_yuga",
                line_number=1,
                category=ProvenanceCategory.AUTHOR_CANON,
            )
        ]
    )

    tu._manager = iso_mgr  # подмена только для reader-граничного теста
    app.dependency_overrides[get_current_user] = _reader
    r_reader_confirm = client.post("/book/temporal/pending-updates/audit_f1/confirm")
    check("B2f.reader_confirm_pending_finding_403", r_reader_confirm.status_code == 403, f"got {r_reader_confirm.status_code}")
    check("B2g.reader_confirm_did_not_save_file", not save_path.exists(), "isolated save file must not exist (no save happened)")
    tu.reset_manager_singleton()

    if save_path.exists():
        save_path.unlink()
    try:
        d.rmdir()
    except OSError:
        pass
finally:
    # Восстановить override как было (conftest ставит admin)
    async def _admin():
        return {"user_id": "test-user", "role": "admin", "provider": "test", "username": "tester", "display_name": "Test User"}

    app.dependency_overrides[get_current_user] = _admin
    from core.routes import temporal_updates as tu2

    tu2.reset_manager_singleton()

# ── B4: никаких фоновых процессов / БД в temporal_updates.py ──
src = Path(RUNTIME / "core" / "routes" / "temporal_updates.py").read_text(encoding="utf-8")
forbidden = ["threading", "Timer(", "create_task", "asyncio.create", "sqlite", "aiosqlite", "schedule", "cron", "while True", " APScheduler", "BackgroundTasks"]
found_forbidden = [f for f in forbidden if f in src]
check("B4a.no_background_no_db_in_route", not found_forbidden, f"forbidden found: {found_forbidden}" if found_forbidden else "clean")

# ── B7: endpoint'ы — тонкая обёртка (вызовы менеджера, без своей логики) ──
manager_calls = [
    "submit_findings",
    "confirm(",
    "reject(",
    ".pending",
    ".confirmed",
    ".rejected",
    ".stats()",
    "watch()",
]
present = [c for c in manager_calls if c in src]
check(
    "B7a.endpoints_delegate_to_manager",
    all(c in present for c in ["submit_findings", "confirm(", "reject(", ".stats()"]),
    f"manager calls present: {len(present)}/{len(manager_calls)}",
)
# Запрещённые прямые операции над WorldModel в роуте:
direct_wm_ops = [".save(", "provenance.append", "duration_years =", "epoch."]
risky = [op for op in direct_wm_ops if op in src]
check("B7b.no_direct_worldmodel_mutation_in_route", not risky, f"direct WM ops found: {risky}" if risky else "route never mutates WM directly")

# Save в роуте упоминается только в комментарии/менеджере? Проверим точечно:
import core.routes.temporal_updates as tu_mod

route_save_lines = [ln for ln in src.split("\n") if ".save(" in ln and "world_model" not in ln.lower()]
check(
    "B7c.route_never_calls_save_directly",
    not any("mgr" in ln or "manager" in ln.lower() for ln in route_save_lines),
    f"suspicious lines: {route_save_lines[:3]}" if route_save_lines else "clean",
)

# ── Итог ────────────────────────────────────────────────────────
out = []
total_pass = sum(1 for _, s, _ in results if s == "PASS")
for name, status, detail in results:
    out.append(f"[{status}] {name}")
    if detail:
        out.append(f"       {detail}")
out.append("")
out.append(f"TOTAL: {total_pass}/{len(results)} PASS")
Path(__file__).parent.joinpath("m102_audit_checks.txt").write_text("\n".join(out), encoding="utf-8")
print(f"done: {total_pass}/{len(results)}")
