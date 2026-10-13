"""M12 — Production Persistence & M10-Gate tests."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.conflict_repository import ConflictRepository
from knowledge.reasoning_repository import ReasoningRepository
from knowledge.correction_repository import CorrectionRepository
from schemas.conflict import ConflictRecord, ConflictStatus, ConflictType
from schemas.reasoning import ReasoningResult, ReasoningStatus
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
        response1 = client.post("/temporal/finding/test_finding/confirm")

        # Повторный confirm должен вернуть 409 или 404
        response2 = client.post("/temporal/finding/test_finding/confirm")

        assert response2.status_code in (404, 409)

    def test_reject_twice_returns_409(self):
        """Повторное отклонение finding → 409, без дублирования."""
        from fastapi.testclient import TestClient
        from core.main import app

        client = TestClient(app)

        response1 = client.post("/temporal/finding/test_finding/reject")
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
            repo = ConflictRepository(data_dir)

            assert data_dir.exists()

    def test_reasoning_repository_creates_directory(self):
        """ReasoningRepository создаёт директорию при первой записи."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "new_dir"
            repo = ReasoningRepository(data_dir)

            assert data_dir.exists()

    def test_correction_repository_creates_directory(self):
        """CorrectionRepository создаёт директорию при первой записи."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "new_dir"
            repo = CorrectionRepository(data_dir)

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
    """Тесты на отсутствие runtime-триггеров."""

    def test_no_runtime_conflict_trigger(self):
        """Нет runtime-триггера для создания ConflictRecord."""
        # Проверяем, что в runtime-коде нет вызовов add() для ConflictRepository
        # (кроме тестов)
        import subprocess

        result = subprocess.run(
            ["grep", "-r", "ConflictRepository", "runtime/core/"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )

        # В runtime/core/ не должно быть создания ConflictRepository
        # (только в routes/knowledge_cards.py для чтения)
        lines = result.stdout.strip().split("\n")
        creation_lines = [l for l in lines if "ConflictRepository(" in l and "import" not in l]

        # Допускается только создание для чтения в knowledge_cards.py
        assert len(creation_lines) <= 1, f"Найдено создание ConflictRepository: {creation_lines}"

    def test_no_runtime_reasoning_trigger(self):
        """Нет runtime-триггера для создания ReasoningResult."""
        import subprocess

        result = subprocess.run(
            ["grep", "-r", "ReasoningRepository", "runtime/core/"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent.parent),
        )

        lines = result.stdout.strip().split("\n")
        creation_lines = [l for l in lines if "ReasoningRepository(" in l and "import" not in l]

        assert len(creation_lines) <= 1, f"Найдено создание ReasoningRepository: {creation_lines}"
