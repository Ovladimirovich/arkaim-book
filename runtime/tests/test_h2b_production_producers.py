"""H2-B (GO-4) — production-производители M5/M6/M7.

Проверяется инкремент «production-производители»:
  - единый путь хранения production-записей (``runtime/runtime_data/knowledge/``);
  - производители дают детерминированные записи на реальных данных;
  - запись идемпотентна;
  - WorldModel не мутируется (граница мутации — M10);
  - HYPOTHESIS не повышается;
  - M10-находка порождает предложение исправления M7 (всегда PENDING).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from narrative_engine.source_levels import ProvenanceCategory  # noqa: E402
from schemas.conflict import ConflictStatus  # noqa: E402
from schemas.reasoning import ReasoningStatus  # noqa: E402


@pytest.fixture(scope="module")
def config():
    from config import config as _config

    return _config


class TestUnifiedStoragePath:
    def test_knowledge_runtime_data_dir_inside_repo(self, config):
        path = config.KNOWLEDGE_RUNTIME_DATA_DIR
        assert path == _PROJECT_ROOT / "runtime" / "runtime_data" / "knowledge"
        assert path.is_relative_to(_PROJECT_ROOT)

    def test_read_and_write_use_the_same_directory(self, config):
        """DI-фабрики записи и чтения указывают в один каталог."""
        from core.routes.conflicts import get_conflict_repository
        from core.routes.reasoning import get_reasoning_repository

        assert get_conflict_repository().data_dir == config.KNOWLEDGE_RUNTIME_DATA_DIR
        assert get_reasoning_repository().data_dir == config.KNOWLEDGE_RUNTIME_DATA_DIR


class TestProducersOnRealData:
    def test_conflicts_detected_for_real_entity(self):
        from knowledge.production_producers import detect_conflicts
        from knowledge_card.builder import KnowledgeCardBuilder

        card = KnowledgeCardBuilder().build("Аркаим")
        assert card is not None
        records = detect_conflicts("arkaim_settlement", card.to_dict())
        assert records, "на реальных данных конфликт не найден"
        for record in records:
            assert record.status is ConflictStatus.UNRESOLVED
            assert record.subject_id == "arkaim_settlement"
            assert len(record.claim_ids) >= 2
            assert record.explanation

    def test_reasoning_built_for_real_entity(self):
        from knowledge.production_producers import build_reasoning
        from knowledge_card.builder import KnowledgeCardBuilder

        card = KnowledgeCardBuilder().build("Аркаим")
        results = build_reasoning("arkaim_settlement", card.to_dict())
        assert results, "на реальных данных рассуждение не построено"
        for result in results:
            assert result.status in {ReasoningStatus.RESOLVED, ReasoningStatus.HYPOTHESIS}
            assert len(result.input_claims) >= 2
            assert result.uncertainty_reasons
            assert result.subject_id == "arkaim_settlement"

    def test_producers_are_deterministic(self):
        from knowledge.production_producers import build_reasoning, detect_conflicts
        from knowledge_card.builder import KnowledgeCardBuilder

        card = KnowledgeCardBuilder().build("Аркаим").to_dict()
        first_conflicts = [r.id for r in detect_conflicts("arkaim_settlement", card)]
        second_conflicts = [r.id for r in detect_conflicts("arkaim_settlement", card)]
        first_reasoning = [r.id for r in build_reasoning("arkaim_settlement", card)]
        second_reasoning = [r.id for r in build_reasoning("arkaim_settlement", card)]
        assert first_conflicts == second_conflicts
        assert first_reasoning == second_reasoning

    def test_hypothesis_is_not_promoted(self):
        """HYPOTHESIS на входе — HYPOTHESIS на выходе."""
        from knowledge.production_producers import build_reasoning

        card = {
            "metadata": {"entity_id": "x"},
            "sources": [
                {
                    "source_name": "book",
                    "claims": [
                        {
                            "text": "Утверждение книги.",
                            "source_ref": "book:chunk_1",
                            "chunk_id": "chunk_1",
                            "provenance": {"category": "HYPOTHESIS", "confidence": 0.9},
                        }
                    ],
                },
                {
                    "source_name": "world_model",
                    "claims": [
                        {
                            "text": "Другое утверждение.",
                            "source_ref": "world_model:x:description",
                            "provenance": {"category": "HYPOTHESIS", "confidence": 0.8},
                        }
                    ],
                },
            ],
        }
        results = build_reasoning("x", card)
        assert results
        for result in results:
            assert result.category is ProvenanceCategory.HYPOTHESIS
            assert result.status is ReasoningStatus.HYPOTHESIS


class TestProductionScan:
    def test_scan_writes_and_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path / "conflicts"))
        monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path / "reasoning"))

        from core.services.knowledge_production import run_production_scan

        first = run_production_scan("Аркаим")
        assert first["ok"] is True
        assert first["conflicts"] >= 1
        assert first["reasoning"] >= 1

        second = run_production_scan("Аркаим")
        assert second["ok"] is True
        assert second["conflicts"] == 0, "повторный скан продублировал записи"
        assert second["reasoning"] == 0, "повторный скан продублировал записи"
        assert second["conflicts_total"] == first["conflicts"]
        assert second["reasoning_total"] == first["reasoning"]

    def test_scan_does_not_touch_world_model(self, tmp_path, monkeypatch):
        import hashlib

        monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path / "conflicts"))
        monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path / "reasoning"))

        world_model = _PROJECT_ROOT / "core" / "CORE" / "narrative_engine" / "data" / "WORLD_MODEL.json"
        crosswalk = _PROJECT_ROOT / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json"

        def digests() -> dict[str, str]:
            return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (world_model, crosswalk)}

        from core.services.knowledge_production import run_production_scan

        before = digests()
        run_production_scan("Аркаим")
        assert digests() == before, "production-скан изменил WorldModel/crosswalk"

    def test_unknown_entity_is_reported(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path / "conflicts"))
        monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path / "reasoning"))

        from core.services.knowledge_production import run_production_scan

        result = run_production_scan("__no_such_entity__")
        assert result["ok"] is False


class TestCorrectionProposal:
    def test_proposal_is_pending_and_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("KNOWLEDGE_CORRECTION_DIR", str(tmp_path / "corrections"))

        from core.services.knowledge_production import record_correction_proposal

        first = record_correction_proposal(
            finding_id="finding_1",
            subject_id="region_arkaim",
            reason="Проверка связи M10 → M7.",
        )
        assert first["created"] is True
        assert first["correction"]["status"] == "PENDING"
        assert first["correction"]["finding_id"] == "finding_1"
        assert first["correction"]["subject_id"] == "region_arkaim"

        second = record_correction_proposal(
            finding_id="finding_1",
            subject_id="region_arkaim",
            reason="Проверка связи M10 → M7.",
        )
        assert second["created"] is False, "повторное предложение продублировано"

    def test_proposal_file_is_written(self, tmp_path, monkeypatch):
        target = tmp_path / "corrections"
        monkeypatch.setenv("KNOWLEDGE_CORRECTION_DIR", str(target))

        from core.services.knowledge_production import record_correction_proposal

        record_correction_proposal(finding_id="finding_2", subject_id="region_arkaim")
        assert (target / "corrections.json").is_file()
        data = json.loads((target / "corrections.json").read_text(encoding="utf-8"))
        assert data
        for record in data.values():
            assert record["status"] == "PENDING"
