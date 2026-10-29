"""Тесты: гейт применения находок Research Engine к World Model.

Проверяют:
  1. RBAC: пользователь без роли editor/admin не может вызвать apply.
  2. Gate: неодобренные находки не изменяют World Model.
  3. Gate: одобренная находка (approved_by) проходит только через
     канонический абсолютный путь.
  4. Сохранение направляется в канонический файл, независимо от CWD.
  5. Пустой результат (findings: []) остаётся безопасным no-op.
  6. Существующий изолированный сценарий не регрессировал.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Подключаем CORE в sys.path для импорта narrative_engine
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE_DIR = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from narrative_engine.research.api_routes import (  # noqa: E402
    _apply_findings_internal,
    ApplyRequest,
)
from narrative_engine.research.world_model_writer import (  # noqa: E402
    _canonical_world_model_path,
    apply_findings as writer_apply_findings,
)
from narrative_engine.world_model import WorldModel  # noqa: E402
from narrative_engine.research.cross_referencer import ResearchFinding  # noqa: E402
from narrative_engine.research.entity_extractor import ExtractedEntity  # noqa: E402
from narrative_engine.research.source_searcher import ExternalSource  # noqa: E402


def _make_finding(entity_type: str = "location", entity_name: str = "Тестовая Земля") -> ResearchFinding:
    """Создать ResearchFinding для тестов."""
    entity = ExtractedEntity(
        name=entity_name,
        entity_type=entity_type,
        context_snippet="Тестовый контекст",
    )
    return ResearchFinding(
        id=f"finding_{entity_name.lower().replace(' ', '_')}",
        entity=entity,
        external_sources=[],
        suggested_fact={
            "entity_type": entity_type,
            "entity_name": entity_name,
            "description": "Описание для теста",
        },
    )


# ── 1. RBAC: без editor/admin → 403 ──────────────────────────


def test_rbac_reader_cannot_apply():
    """Пользователь с ролью reader не может применить находки."""
    from auth.rbac import ROLE_HIERARCHY, require_role

    reader_user = {"user_id": "reader-1", "role": "reader"}
    try:
        require_role("editor", "admin")
        # require_role возвращает корутину-обёртку; вызов _checker
        # с role=reader должен бросить 403.
        import asyncio

        checker = require_role("editor", "admin")

        async def _call():
            return await checker(user=reader_user)

        asyncio.run(_call())
        assert False, "Ожидался HTTPException 403"
    except Exception as exc:
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException) and exc.status_code == 403, f"Ожидался 403, получен: {exc}"


# ── 2. Gate: неодобренная находка не изменяет World Model ─────


def test_unapproved_finding_does_not_modify_world_model(tmp_path):
    """Находка без approved_by не попадает в World Model."""
    finding = _make_finding()
    wm = WorldModel({})
    job = {"approved_by": ""}  # пустое → не одобрено

    result = writer_apply_findings([finding], wm, job=job)
    assert result["applied"] == 0
    assert result["failed"] == 1
    assert result["total"] == 1


def test_none_job_does_not_modify_world_model(tmp_path):
    """job=None → также не применяется (conservative default)."""
    finding = _make_finding()
    wm = WorldModel({})

    result = writer_apply_findings([finding], wm, job=None)
    assert result["applied"] == 0
    assert result["failed"] == 1


# ── 3. Gate: одобренная находка проходит через канонический путь


def test_approved_finding_uses_canonical_path(tmp_path, monkeypatch):
    """Одобренная находка записывается в канонический абсолютный путь."""
    finding = _make_finding()

    # Временная копия WorldModel для теста
    test_wm_path = tmp_path / "test_wm.json"
    test_wm_path.write_text(json.dumps({"version": "test", "epochs": [], "locations": []}), encoding="utf-8")
    wm = WorldModel.load(path=test_wm_path, use_cache=False)

    # Монки-патчим канонический путь на временный
    from narrative_engine.research import world_model_writer as writer_mod

    monkeypatch.setattr(writer_mod, "_CANONICAL_WM_PATH", test_wm_path)

    job = {"approved_by": "owner-123"}
    result = writer_apply_findings([finding], wm, job=job)
    assert result["applied"] == 1

    # Проверяем, что файл был сохранён в тестовый путь
    saved = json.loads(test_wm_path.read_text(encoding="utf-8"))
    assert any(loc.get("name_ru") == "Тестовая Земля" for loc in saved.get("locations", []))


# ── 4. Канонический путь стабилен из разных CWD ────────────────


def test_canonical_path_is_absolute():
    """_canonical_world_model_path() возвращает абсолютный путь."""
    path = _canonical_world_model_path()
    assert path.is_absolute(), f"Путь не абсолютный: {path}"
    assert path.name == "WORLD_MODEL.json"
    assert "narrative_engine" in str(path)
    assert "data" in str(path)


def test_canonical_path_independent_of_cwd(monkeypatch):
    """Путь не зависит от текущего рабочего каталога."""
    import os

    original_cwd = os.getcwd()
    try:
        # Изменяем CWD на случайный каталог
        os.chdir("/")
        path1 = _canonical_world_model_path()
        os.chdir("\\")
        path2 = _canonical_world_model_path()
        assert path1 == path2, "Путь зависит от CWD — ошибка"
    finally:
        os.chdir(original_cwd)


# ── 5. Пустой результат (findings=[]) — безопасный no-op ──────


def test_empty_findings_is_noop(tmp_path):
    """Пустой список находок не изменяет World Model и не сохраняет файл."""
    test_wm_path = tmp_path / "empty_wm.json"
    original_data = {"version": "test", "epochs": [], "locations": []}
    test_wm_path.write_text(json.dumps(original_data), encoding="utf-8")
    wm = WorldModel.load(path=test_wm_path, use_cache=False)

    from narrative_engine.research import world_model_writer as writer_mod

    original_mpath = writer_mod._CANONICAL_WM_PATH
    writer_mod._CANONICAL_WM_PATH = test_wm_path
    try:
        result = writer_apply_findings([], wm, job={"approved_by": "owner"})
        assert result == {"applied": 0, "failed": 0, "total": 0}
        # Файл не должен быть перезаписан (updated_at не изменился)
        saved = json.loads(test_wm_path.read_text(encoding="utf-8"))
        assert "updated_at" not in saved or saved["updated_at"] is None
    finally:
        writer_mod._CANONICAL_WM_PATH = original_mpath


# ── 6. _apply_findings_internal: интеграционный тест ───────────


def test_apply_findings_internal_no_approval(tmp_path):
    """_apply_findings_internal с approved_by='' возвращает no_approval."""
    from narrative_engine.research import api_routes as ar

    # Создаём job с пустыми findings
    job_id = "test-job-1"
    ar._research_jobs.append(
        {
            "id": job_id,
            "status": "completed",
            "entity": "Тест",
            "entity_type": "concept",
            "findings": [],
        }
    )
    user = {"user_id": "owner-1", "role": "admin"}
    body = ApplyRequest(approved_by="")  # пустое → нет одобрения
    result = _apply_findings_internal(job_id, user, body)
    assert result["ok"] is True
    assert result["data"]["reason"] == "no_approval"
    assert result["data"]["applied"] == 0


def test_apply_findings_internal_with_approval(tmp_path, monkeypatch):
    """_apply_findings_internal с approved_by='owner' применяет находки."""
    from narrative_engine.research import api_routes as ar
    from narrative_engine.research import world_model_writer as writer_mod

    test_wm_path = tmp_path / "internal_wm.json"
    test_wm_path.write_text(json.dumps({"version": "test", "epochs": [], "locations": []}), encoding="utf-8")
    monkeypatch.setattr(writer_mod, "_CANONICAL_WM_PATH", test_wm_path)

    finding = _make_finding()
    job_id = "test-job-2"
    ar._research_jobs.append(
        {
            "id": job_id,
            "status": "completed",
            "entity": "Тестовая Земля",
            "entity_type": "location",
            "findings": [finding],
        }
    )
    user = {"user_id": "owner-1", "role": "admin"}
    body = ApplyRequest(approved_by="owner-1")
    result = _apply_findings_internal(job_id, user, body)
    assert result["ok"] is True
    assert result["data"]["applied"] == 1

    # Чистим
    ar._research_jobs.clear()


def test_apply_findings_internal_job_not_found():
    """Несуществующий job_id → 404."""
    from fastapi import HTTPException

    user = {"user_id": "owner-1", "role": "admin"}
    with pytest.raises(HTTPException) as exc_info:
        _apply_findings_internal("nonexistent", user)
    assert exc_info.value.status_code == 404
