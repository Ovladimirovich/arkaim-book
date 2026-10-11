"""M8 — durable M6 reasoning read-only boundary for Knowledge Trace."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core" / "CORE"
for import_root in (ROOT, CORE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from knowledge.reasoning_repository import ReasoningRepository
from narrative_engine.source_levels import ProvenanceCategory
from schemas.reasoning import ReasoningInput, ReasoningResult, ReasoningStatus


def _resolved(subject_id: str, ident: str, *, method_version: str = "v1") -> ReasoningResult:
    return ReasoningResult(
        id=ident,
        status=ReasoningStatus.RESOLVED,
        output_claim_id=f"output_{ident}",
        output_text=f"Derived synthesis {ident}",
        category=ProvenanceCategory.DERIVED,
        input_claims=[
            ReasoningInput(claim_id=f"{ident}_claim_a", evidence_ids=[f"{ident}_ev_1"]),
            ReasoningInput(claim_id=f"{ident}_claim_b", evidence_ids=[f"{ident}_ev_2"]),
        ],
        method_id="source_aggregation",
        method_version=method_version,
        confidence=0.6,
        uncertainty_reasons=["sources disagree on scope"],
        metadata={"subjects": [{"subject_id": subject_id}]},
    )


def _hypothesis(subject_id: str) -> ReasoningResult:
    return ReasoningResult(
        id=f"hyp_{subject_id}",
        status=ReasoningStatus.HYPOTHESIS,
        output_claim_id=f"output_hyp_{subject_id}",
        output_text="Tentative interpretation.",
        category=ProvenanceCategory.HYPOTHESIS,
        input_claims=[
            ReasoningInput(claim_id="h_claim_1"),
            ReasoningInput(claim_id="h_claim_2"),
        ],
        method_id="rule_hint",
        method_version="v0.1",
        confidence=0.4,
        metadata={"subjects": [{"subject_id": subject_id}]},
    )


def test_repository_round_trip_preserves_lineage(tmp_path):
    repo = ReasoningRepository(tmp_path)
    repo.add(_resolved("entity_a", "reason_1"))
    loaded = repo.get("reason_1")
    assert loaded is not None
    assert loaded.input_claim_ids == ["reason_1_claim_a", "reason_1_claim_b"]
    assert loaded.input_evidence_ids == ["reason_1_ev_1", "reason_1_ev_2"]
    assert loaded.method_id == "source_aggregation"
    assert loaded.method_version == "v1"
    assert loaded.category is ProvenanceCategory.DERIVED
    assert loaded.confidence == 0.6
    assert loaded.uncertainty_reasons == ["sources disagree on scope"]


def test_repository_filters_by_subject_and_status(tmp_path):
    repo = ReasoningRepository(tmp_path)
    repo.add(_resolved("entity_a", "reason_a"))
    repo.add(_resolved("entity_b", "reason_b"))
    repo.add(_hypothesis("entity_a"))
    subject_a = repo.list(subject_id="entity_a")
    assert {record.id for record in subject_a} == {"reason_a", "hyp_entity_a"}
    assert [record.id for record in repo.list(subject_id="entity_a", status="HYPOTHESIS")] == ["hyp_entity_a"]
    assert repo.list(subject_id="entity_missing") == []


def test_repository_ignores_corrupt_storage_without_fabrication(tmp_path):
    (tmp_path / "reasoning.json").write_text("not json", encoding="utf-8")
    assert ReasoningRepository(tmp_path).list() == []


def test_trace_projection_includes_durable_reasoning(tmp_path, monkeypatch):
    from core.routes.knowledge_cards import _reasoning_projection

    ReasoningRepository(tmp_path).add(_resolved("entity_1", "reason_1"))
    ReasoningRepository(tmp_path).add(_hypothesis("entity_2"))
    monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path))

    projected = _reasoning_projection("entity_1")
    assert len(projected) == 1
    assert projected[0]["id"] == "reason_1"
    assert projected[0]["status"] == "RESOLVED"
    assert projected[0]["input_claims"][0]["claim_id"] == "reason_1_claim_a"
    assert projected[0]["method_version"] == "v1"
    assert _reasoning_projection("entity_unknown") == []


def test_trace_projection_returns_empty_for_missing_storage(tmp_path, monkeypatch):
    from core.routes.knowledge_cards import _reasoning_projection

    monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path / "absent"))
    assert _reasoning_projection("entity_1") == []
