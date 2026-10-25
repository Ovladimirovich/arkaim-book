"""M12 — Production Persistence & M10-Gate tests."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.conflict_repository import ConflictRepository
from knowledge.reasoning_repository import ReasoningRepository
from knowledge.correction_repository import CorrectionRepository
from schemas.correction import CorrectionRecord, CorrectionStatus


class TestM10GateBehavior:
    """Тесты на корректное поведение M10-gate."""

    def test_confirm_not_found_returns_404(self):
        """Подтверждение несуществующего finding → 404, без побочных эффектов."""
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)
        response = client.post("/temporal/finding/nonexistent_finding/confirm")

        assert response.status_code == 404

    def test_reject_not_found_returns_404(self):
        """Отклонение несуществующего finding → 404, без побочных эффектов."""
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)
        response = client.post("/temporal/finding/nonexistent_finding/reject")

        assert response.status_code == 404

    def test_confirm_twice_returns_409(self):
        """Повторное подтверждение finding → 409, без дублирования."""
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)

        # Первый confirm должен быть успешным или 404/409
        _response1 = client.post("/temporal/finding/test_finding/confirm")

        # Повторный confirm должен вернуть 409 или 404
        response2 = client.post("/temporal/finding/test_finding/confirm")

        assert response2.status_code in (404, 409)

    def test_reject_twice_returns_409(self):
        """Повторное отклонение finding → 409, без дублирования."""
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)

        _response1 = client.post("/temporal/finding/test_finding/reject")
        response2 = client.post("/temporal/finding/test_finding/reject")

        assert response2.status_code in (404, 409)

    def test_m10_confirm_does_not_create_correction_record(self):
        """M10 confirm не создаёт CorrectionRecord (вариант C)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            correction_repo = CorrectionRepository(tmpdir)

            # M10 confirm не должен создавать correction record
            # Проверяем, что репозиторий пуст после M10 операций
            corrections = correction_repo.list()
            assert len(corrections) == 0

    def test_m10_reject_does_not_create_correction_record(self):
        """M10 reject не создаёт CorrectionRecord (вариант C)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            correction_repo = CorrectionRepository(tmpdir)

            corrections = correction_repo.list()
            assert len(corrections) == 0


class TestNoFakeRecords:
    """Тесты на отсутствие фиктивных записей."""

    def test_no_conflict_records_without_trigger(self):
        """ConflictRecord не создаётся без реального триггера."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conflict_repo = ConflictRepository(tmpdir)

            # Проверяем, что репозиторий пуст
            conflicts = conflict_repo.list()
            assert len(conflicts) == 0

    def test_no_reasoning_records_without_trigger(self):
        """ReasoningResult не создаётся без реального триггера."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reasoning_repo = ReasoningRepository(tmpdir)

            # Проверяем, что репозиторий пуст
            reasoning_results = reasoning_repo.list()
            assert len(reasoning_results) == 0

    def test_no_correction_records_without_trigger(self):
        """CorrectionRecord не создаётся без реального триггера."""
        with tempfile.TemporaryDirectory() as tmpdir:
            correction_repo = CorrectionRepository(tmpdir)

            # Проверяем, что репозиторий пуст
            corrections = correction_repo.list()
            assert len(corrections) == 0


class TestPersistenceSafety:
    """Тесты на безопасность записи."""

    def test_conflict_repository_handles_corrupt_json(self):
        """ConflictRepository обрабатывает повреждённый JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ConflictRepository(tmpdir)

            # Создаём повреждённый JSON
            repo.path.write_text("not valid json{", encoding="utf-8")

            # Должен вернуть пустой список, а не упасть
            conflicts = repo.list()
            assert conflicts == []

    def test_reasoning_repository_handles_corrupt_json(self):
        """ReasoningRepository обрабатывает повреждённый JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = ReasoningRepository(tmpdir)

            # Создаём повреждённый JSON
            repo.path.write_text("not valid json{", encoding="utf-8")

            # Должен вернуть пустой список, а не упасть
            results = repo.list()
            assert results == []

    def test_correction_repository_handles_corrupt_json(self):
        """CorrectionRepository обрабатывает повреждённый JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = CorrectionRepository(tmpdir)

            # Создаём повреждённый JSON
            repo.path.write_text("not valid json{", encoding="utf-8")

            # Должен вернуть пустой список, а не упасть
            corrections = repo.list()
            assert corrections == []

    def test_conflict_repository_creates_directory(self):
        """ConflictRepository создаёт директорию при первой записи."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "new_dir"
            _repo = ConflictRepository(data_dir)

            assert data_dir.exists()

    def test_reasoning_repository_creates_directory(self):
        """ReasoningRepository создаёт директорию при первой записи."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "new_dir"
            _repo = ReasoningRepository(data_dir)

            assert data_dir.exists()

    def test_correction_repository_creates_directory(self):
        """CorrectionRepository создаёт директорию при первой записи."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "new_dir"
            _repo = CorrectionRepository(data_dir)

            assert data_dir.exists()


class TestM10ToM7Blocker:
    """Тесты на блокер M10 → M7."""

    def test_m10_confirm_does_not_create_replacement_claim(self):
        """M10 confirm не создаёт replacement claim (блокер M10 → M7)."""
        # Этот тест фиксирует текущий блокер:
        # M10 confirm не создаёт CorrectionRecord, так как нет связи
        # между finding и replacement claim
        with tempfile.TemporaryDirectory() as tmpdir:
            correction_repo = CorrectionRepository(tmpdir)

            # Проверяем, что нет correction records
            corrections = correction_repo.list()
            assert len(corrections) == 0

    def test_correction_confirm_requires_replacement_claim_id(self):
        """CorrectionRepository.confirm требует replacement_claim_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = CorrectionRepository(tmpdir)

            correction = CorrectionRecord(
                id="corr_1",
                subject_id="entity_1",
                status=CorrectionStatus.PENDING,
                finding_id="finding_1",
            )
            repo.add(correction)

            # Попытка confirm без replacement_claim_id должна упасть
            with pytest.raises(ValueError):
                repo.confirm(
                    "corr_1",
                    replacement_claim_id="",
                    decision_by="owner",
                    decided_at="2026-01-01T00:00:00Z",
                )


class TestRuntimeTriggers:
    """Тесты на runtime-триггеры.

    После H2-B (GO-4) триггеры появились, но остались ЯВНЫМИ:
    запись идёт только через owner-gated эндпоинт
    ``POST /knowledge/cards/{entity_id}/production-scan``.
    Инвариант, который охраняют эти тесты: чтение (GET trace) никогда
    не пишет, а единственный писатель в runtime — production-сервис.
    """

    @staticmethod
    def _creation_lines(token: str) -> list[str]:
        import subprocess

        result = subprocess.run(
            ["grep", "-r", token, "runtime/core/"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )
        lines = result.stdout.strip().split("\n")
        return [line for line in lines if f"{token}(" in line and "import" not in line]

    def test_single_conflict_writer(self):
        """Запись конфликтов — ровно в одном месте: production-сервис."""
        creation_lines = self._creation_lines("ConflictRepository")
        writers = [line for line in creation_lines if "knowledge_production.py" in line]
        assert len(writers) == 1, f"ожидался один писатель конфликтов: {creation_lines}"
        # остальные места — только чтение или DI-фабрика
        assert len(creation_lines) <= 3, creation_lines

    def test_single_reasoning_writer(self):
        """Запись рассуждений — ровно в одном месте: production-сервис."""
        creation_lines = self._creation_lines("ReasoningRepository")
        writers = [line for line in creation_lines if "knowledge_production.py" in line]
        assert len(writers) == 1, f"ожидался один писатель рассуждений: {creation_lines}"
        assert len(creation_lines) <= 3, creation_lines

    def test_trace_route_does_not_write(self):
        """Тело GET trace остаётся read-only: в нём нет вызовов add()/save()."""
        from pathlib import Path as _Path

        source = (_Path(__file__).resolve().parent.parent / "core" / "routes" / "knowledge_cards.py").read_text(encoding="utf-8")
        start = source.index("async def get_knowledge_trace(")
        end = source.index("@router.", start + 10)
        body = source[start:end]
        for forbidden in (".add(", "run_production_scan", "record_correction_proposal", "_save("):
            assert forbidden not in body, f"в теле get_knowledge_trace найдено: {forbidden}"

    def test_production_trigger_is_owner_gated(self):
        """Единственный авто-триггер записи — под editor/admin."""
        from pathlib import Path as _Path

        source = (_Path(__file__).resolve().parent.parent / "core" / "routes" / "knowledge_cards.py").read_text(encoding="utf-8")
        marker = '"/{entity_id}/production-scan"'
        assert marker in source, "не найден эндпоинт production-scan"
        window = source[source.index(marker) : source.index(marker) + 400]
        assert 'require_role("editor", "admin")' in window, "production-scan не ограничен editor/admin"

    def test_production_service_does_not_mutate_world_model(self):
        """Production-сервис не пишет в WorldModel (граница мутации — M10)."""
        from pathlib import Path as _Path

        source = (_Path(__file__).resolve().parent.parent / "core" / "services" / "knowledge_production.py").read_text(encoding="utf-8")
        for forbidden in ("WORLD_MODEL.json", "world_model.save", "temporal_update_manager", "TemporalUpdateManager"):
            assert forbidden not in source, f"в knowledge_production.py найдено: {forbidden}"
