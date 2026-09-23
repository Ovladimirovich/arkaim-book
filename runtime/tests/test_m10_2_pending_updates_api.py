"""M10.2 tests: Pending Updates API (тонкая обёртка над M10 TemporalUpdateManager).

Проверяет контракт утверждённого SPEC:
1. Все 7 endpoint'ов работают по конвенции {"ok": ...}
2. RBAC: reader — только просмотр; editor — scan/confirm/reject; 401 без авторизации
3. Scan идемпотентен (без изменения книги → 0 новых)
4. Confirm через API = путь менеджера M10 (validation → apply → save → refresh)
5. Reject не меняет WorldModel
6. Канонические данные не изменены (hash-проверка)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.main import app
from auth.rbac import get_current_user

# ── Пути и импорты ──────────────────────────────────────────

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
WM_PATH = CORE_DIR / "narrative_engine" / "data" / "WORLD_MODEL.json"

from core.routes import temporal_updates as tu


# ── Фикстуры ───────────────────────────────────────────────


@pytest.fixture
def client():
    return TestClient(app)


def _role_user(role: str):
    async def _user():
        return {
            "user_id": f"test-{role}",
            "role": role,
            "provider": "test",
            "username": role,
            "display_name": f"Test {role}",
        }
    return _user


@pytest.fixture(autouse=True)
def _restore_auth_override():
    """Восстанавливать admin-override после каждого теста (conftest ставит admin)."""
    yield
    app.dependency_overrides[get_current_user] = _role_user("admin")


@pytest.fixture
def isolated_manager(tmp_path_unused=None):
    """Изолированный менеджер: WorldModel копия + test-local save path.

    Канонический WORLD_MODEL.json НЕ затрагивается: singleton роута
    подменяется тестовым менеджером с явным world_model_path.
    """
    from narrative_engine.world_model import WorldModel
    from narrative_engine.research.temporal_update_manager import TemporalUpdateManager
    from narrative_engine.research.temporal_extractor import TemporalFinding

    d = Path(__file__).resolve().parent / "tmp_m10_2"
    d.mkdir(exist_ok=True)
    save_path = d / "world_model_test_output.json"

    # Реальная структура (копия канонической), изолированное хранилище
    wm_data = {
        "epochs": [
            {
                "id": "kali_yuga",
                "name": "Kali Yuga",
                "name_ru": "Кали Юга",
                "description": "",
                "order": 1,
                "duration_years": None,
                "provenance": [],
            },
        ]
    }
    from narrative_engine.world_model import WorldModel as _WM
    wm = _WM(wm_data)

    mgr = TemporalUpdateManager(world_model=wm, world_model_path=save_path)
    yield mgr, save_path

    if save_path.exists():
        save_path.unlink()
    try:
        d.rmdir()
    except OSError:
        pass


# ── Helpers ────────────────────────────────────────────────


def _make_finding(id_suffix: str = "1", category: str = "AUTHOR_CANON") -> object:
    from narrative_engine.research.temporal_extractor import TemporalFinding
    from narrative_engine.source_levels import ProvenanceCategory

    return TemporalFinding(
        id=f"test_finding_{id_suffix}",
        kind="absolute_date",
        raw_text="в эпоху Кали Юги",
        value="epoch:kali_yuga",
        line_number=1,
        category=getattr(ProvenanceCategory, category),
    )


def _swap_singleton(mgr):
    """Подменить singleton-менеджер роута на тестовый."""
    tu._manager = mgr


# ═══════════════════════════════════════════════════════════
# 1. Доступность endpoint'ов (конвенция ok:true)
# ═══════════════════════════════════════════════════════════


class TestEndpointAvailability:

    def test_all_seven_endpoints_in_openapi(self, client):
        schema = client.get("/openapi.json").json()
        found = [p for p in schema["paths"] if "pending-updates" in p]
        assert len(found) == 7, f"Expected 7 endpoints, got {len(found)}: {found}"

    def test_list_pending_ok_convention(self, client, isolated_manager):
        """GET /pending-updates отвечает {"ok": true, "data": [...]}."""
        _swap_singleton(isolated_manager[0])
        resp = client.get("/book/temporal/pending-updates")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "data" in body and "total" in body

    def test_stats_endpoint(self, client, isolated_manager):
        _swap_singleton(isolated_manager[0])
        resp = client.get("/book/temporal/pending-updates/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert set(body["data"].keys()) == {"pending", "confirmed", "rejected"}


# ═══════════════════════════════════════════════════════════
# 2. RBAC-границы (утверждённая матрица)
# ═══════════════════════════════════════════════════════════


class TestRBAC:

    def test_reader_cannot_confirm(self, client, isolated_manager):
        """reader → 403 на confirm (никогда не может изменить WorldModel)."""
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("r1")])
        _swap_singleton(mgr)
        app.dependency_overrides[get_current_user] = _role_user("reader")

        resp = client.post("/book/temporal/pending-updates/test_finding_r1/confirm")
        assert resp.status_code == 403

    def test_reader_cannot_reject(self, client, isolated_manager):
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("r2")])
        _swap_singleton(mgr)
        app.dependency_overrides[get_current_user] = _role_user("reader")

        resp = client.post(
            "/book/temporal/pending-updates/test_finding_r2/reject", json={"reason": "no"}
        )
        assert resp.status_code == 403

    def test_reader_cannot_scan(self, client):
        app.dependency_overrides[get_current_user] = _role_user("reader")
        resp = client.post("/book/temporal/pending-updates/scan")
        assert resp.status_code == 403

    def test_reader_can_view(self, client, isolated_manager):
        """reader может смотреть список/детали/статистику."""
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("r3")])
        _swap_singleton(mgr)
        app.dependency_overrides[get_current_user] = _role_user("reader")

        assert client.get("/book/temporal/pending-updates").status_code == 200
        assert client.get("/book/temporal/pending-updates/stats").status_code == 200
        assert client.get("/book/temporal/pending-updates/history").status_code == 200
        detail = client.get("/book/temporal/pending-updates/test_finding_r3")
        assert detail.status_code == 200
        assert detail.json()["data"]["status"] == "pending"

    def test_editor_can_confirm(self, client, isolated_manager):
        """editor → 200 на confirm (утверждённая граница)."""
        mgr, save_path = isolated_manager
        mgr.submit_findings([_make_finding("e1")])
        _swap_singleton(mgr)
        app.dependency_overrides[get_current_user] = _role_user("editor")

        resp = client.post("/book/temporal/pending-updates/test_finding_e1/confirm")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["applied"] is True
        assert body["data"]["world_model_saved"] is True

    def test_editor_can_reject(self, client, isolated_manager):
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("e2")])
        _swap_singleton(mgr)
        app.dependency_overrides[get_current_user] = _role_user("editor")

        resp = client.post(
            "/book/temporal/pending-updates/test_finding_e2/reject", json={"reason": "human says no"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["applied"] is False

    def test_editor_can_scan(self, client):
        app.dependency_overrides[get_current_user] = _role_user("editor")
        resp = client.post("/book/temporal/pending-updates/scan")
        assert resp.status_code == 200

    def test_no_auth_401(self, client):
        """Без авторизации — 401 на всех защищённых endpoint'ах."""
        app.dependency_overrides.pop(get_current_user, None)
        assert client.post("/book/temporal/pending-updates/scan").status_code == 401
        assert client.get("/book/temporal/pending-updates").status_code == 401
        assert client.post("/book/temporal/pending-updates/x/confirm").status_code == 401

    def test_reader_never_modifies_world_model(self, client, isolated_manager):
        """КРИТИЧЕСКИЙ инвариант: reader не имеет НИ ОДНОГО пути изменить WorldModel."""
        mgr, save_path = isolated_manager
        mgr.submit_findings([_make_finding("r9")])
        _swap_singleton(mgr)
        app.dependency_overrides[get_current_user] = _role_user("reader")

        # Все mutating endpoint'ы → 403
        for url in [
            "/book/temporal/pending-updates/test_finding_r9/confirm",
            "/book/temporal/pending-updates/test_finding_r9/reject",
            "/book/temporal/pending-updates/scan",
        ]:
            method = "post"
            resp = getattr(client, method)(url, json={} if "reject" in url else None)
            assert resp.status_code == 403, f"{url} should be 403 for reader, got {resp.status_code}"

        # Файл не появился (save не вызывался)
        assert not save_path.exists(), "reader triggered a save somewhere!"


# ═══════════════════════════════════════════════════════════
# 3. Scan-цепочка (детектор → извлечение → submit)
# ═══════════════════════════════════════════════════════════


class TestScanChain:

    def test_scan_no_book_change_zero_new(self, client, isolated_manager):
        """Без изменения книги → book_changed=false, 0 новых (идемпотентность)."""
        mgr, _ = isolated_manager
        _swap_singleton(mgr)
        # detector singleton уже инициализирован conftest? нет — инициализируем baseline
        tu._detector = None  # форсируем lazy init при первом scan → baseline
        resp = client.post("/book/temporal/pending-updates/scan")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["book_changed"] is False
        assert body["data"]["new_findings"] == 0

    def test_scan_twice_idempotent(self, client, isolated_manager):
        """Второй scan без изменения книги → снова 0 новых."""
        mgr, _ = isolated_manager
        _swap_singleton(mgr)
        tu._detector = None
        r1 = client.post("/book/temporal/pending-updates/scan").json()
        r2 = client.post("/book/temporal/pending-updates/scan").json()
        assert r1["data"]["book_changed"] is False
        assert r2["data"]["book_changed"] is False
        assert r2["data"]["new_findings"] == 0

    def test_scan_real_book_no_crash(self, client, isolated_manager):
        """Scan на реальной книге не падает и возвращает корректную структуру."""
        mgr, _ = isolated_manager
        _swap_singleton(mgr)
        tu._detector = None
        resp = client.post("/book/temporal/pending-updates/scan")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "book_changed" in body["data"]
        assert "total_pending" in body["data"]


# ═══════════════════════════════════════════════════════════
# 4. Confirm/Reject через API = путь менеджера M10
# ═══════════════════════════════════════════════════════════


class TestConfirmRejectViaAPI:

    def test_confirm_full_cycle(self, client, isolated_manager):
        """Confirm через API: applied=true, saved=true, refresh вызван."""
        mgr, save_path = isolated_manager
        mgr.submit_findings([_make_finding("c1")])
        _swap_singleton(mgr)

        resp = client.post("/book/temporal/pending-updates/test_finding_c1/confirm")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["applied"] is True
        assert data["world_model_saved"] is True
        assert data["temporal_refreshed"] is False  # world_engine не передан в тестовом менеджере

        # Файл сохранён в изолированный путь
        assert save_path.exists()

        # Manager: pending пуст, confirmed содержит находку
        assert mgr.stats()["pending"] == 0
        assert mgr.stats()["confirmed"] == 1

    def test_confirm_not_found_404(self, client, isolated_manager):
        _swap_singleton(isolated_manager[0])
        resp = client.post("/book/temporal/pending-updates/nonexistent/confirm")
        assert resp.status_code == 404

    def test_confirm_twice_409(self, client, isolated_manager):
        """Повторный confirm уже подтверждённой → 409 (не pending)."""
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("c2")])
        _swap_singleton(mgr)

        first = client.post("/book/temporal/pending-updates/test_finding_c2/confirm")
        assert first.status_code == 200
        second = client.post("/book/temporal/pending-updates/test_finding_c2/confirm")
        assert second.status_code == 409

    def test_reject_keeps_world_model_untouched(self, client, isolated_manager):
        """Reject через API: WorldModel не тронут (файл не сохранён)."""
        mgr, save_path = isolated_manager
        mgr.submit_findings([_make_finding("j1")])
        _swap_singleton(mgr)

        resp = client.post(
            "/book/temporal/pending-updates/test_finding_j1/reject", json={"reason": "test"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["applied"] is False
        assert not save_path.exists()  # save НЕ вызывался

    def test_invalid_category_409(self, client, isolated_manager):
        """Невалидная категория → менеджер reject → HTTP 409 с reason.

        Формат ошибки — конвенция проекта: {"ok": false, "error": {"code", "message"}}.
        """
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("bad", category="UNKNOWN")])
        _swap_singleton(mgr)

        resp = client.post("/book/temporal/pending-updates/test_finding_bad/confirm")
        assert resp.status_code == 409
        assert "invalid_category" in resp.json()["error"]["message"]

    def test_canonical_world_model_untouched_by_api_cycle(self, client, isolated_manager):
        """КРИТИЧЕСКИЙ: полный API-цикл не трогает канонический WORLD_MODEL.json."""
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("iso")])
        _swap_singleton(mgr)

        wm_hash_before = hashlib.sha256(WM_PATH.read_bytes()).hexdigest()

        client.post("/book/temporal/pending-updates/test_finding_iso/confirm")
        client.get("/book/temporal/pending-updates/history")
        client.post("/book/temporal/pending-updates/scan")

        wm_hash_after = hashlib.sha256(WM_PATH.read_bytes()).hexdigest()
        assert wm_hash_before == wm_hash_after


# ═══════════════════════════════════════════════════════════
# 5. История и детали
# ═══════════════════════════════════════════════════════════


class TestHistoryAndDetails:

    def test_history_shows_confirmed_and_rejected(self, client, isolated_manager):
        mgr, _ = isolated_manager
        f1 = _make_finding("h1")
        f2 = _make_finding("h2")
        mgr.submit_findings([f1, f2])
        _swap_singleton(mgr)

        client.post("/book/temporal/pending-updates/test_finding_h1/confirm")
        client.post(
            "/book/temporal/pending-updates/test_finding_h2/reject", json={"reason": "nope"}
        )

        resp = client.get("/book/temporal/pending-updates/history")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["confirmed"]) == 1
        assert len(data["rejected"]) == 1
        assert data["rejected"][0]["reason"] == "nope"

    def test_finding_detail_status_pending(self, client, isolated_manager):
        mgr, _ = isolated_manager
        mgr.submit_findings([_make_finding("d1")])
        _swap_singleton(mgr)

        resp = client.get("/book/temporal/pending-updates/test_finding_d1")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "pending"
        assert resp.json()["data"]["category"] == "AUTHOR_CANON"

    def test_finding_detail_not_found(self, client, isolated_manager):
        _swap_singleton(isolated_manager[0])
        resp = client.get("/book/temporal/pending-updates/ghost")
        assert resp.status_code == 404
