"""M8 — one full read-only integration journey through GET /knowledge/cards/trace/{entity_id}.

Chain under test: card claim -> evidence -> M5 conflict -> M6 reasoning -> M7 correction.
Scenario data is a distinct fixture (direct book/archaeology contradiction + temporal
incompatibility + resolved derivation + hypothesis + pending correction) built on real
source_ref values returned by the Knowledge Card builder — not a copy of M5/M6/M7 fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core" / "CORE"
for import_root in (ROOT, CORE_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

ENTITY = "region_arkaim"
EMPTY_ENTITY = "journey_entity_without_any_records"


def _client(*, authenticated: bool) -> TestClient:
    from core.routes import knowledge_cards as kc

    app = FastAPI()
    app.include_router(kc.router)
    if authenticated:
        checker = kc.router.dependencies[0].dependency  # require_role("reader") dependency
        app.dependency_overrides[checker] = lambda: {
            "user_id": "journey-reader",
            "role": "reader",
            "provider": "test",
            "username": "journey_reader",
            "display_name": "Journey Reader",
        }
    return TestClient(app)


@pytest.fixture()
def journey_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_CONFLICT_DIR", str(tmp_path))
    monkeypatch.setenv("KNOWLEDGE_REASONING_DIR", str(tmp_path))
    monkeypatch.setenv("KNOWLEDGE_CORRECTION_DIR", str(tmp_path))
    return tmp_path


def _trace(client: TestClient, entity_id: str, **params) -> dict:
    response = client.get(f"/knowledge/cards/trace/{entity_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _seed(chain_claims: list[dict], env: Path) -> dict:
    """Persist the M5/M6/M7 side using existing CanonClaim IDs."""
    from knowledge.conflict_repository import ConflictRepository
    from knowledge.correction_repository import CorrectionRepository
    from knowledge.reasoning_repository import ReasoningRepository
    from narrative_engine.source_levels import ProvenanceCategory
    from schemas.conflict import ConflictRecord, ConflictType
    from schemas.correction import CorrectionRecord
    from schemas.reasoning import ReasoningInput, ReasoningResult, ReasoningStatus

    from narrative_engine.provenance.claim import CanonClaim

    claim_a_record, claim_b_record = chain_claims[0], chain_claims[1]
    ref_a = claim_a_record["source_ref"]
    ref_b = claim_b_record["source_ref"]
    claim_a = CanonClaim.make_id(claim_a_record["text"], "book", f"chunk:{claim_a_record['chunk_id']}")
    claim_b = CanonClaim.make_id(claim_b_record["text"], "book", f"chunk:{claim_b_record['chunk_id']}")
    temporal_claim = "claim::temporal::region_arkaim_settlement_window"
    evidence_ids = [ref_a, ref_b]

    conflicts = ConflictRepository(env)
    conflicts.add(
        ConflictRecord(
            id="conflict_region_arkaim_direct",
            conflict_type=ConflictType.DIRECT_CONTRADICTION,
            subject_id=ENTITY,
            claim_ids=[claim_a, claim_b],
            evidence_ids=evidence_ids,
            explanation="Book canon and archaeology source assert incompatible settlement facts.",
        )
    )
    conflicts.add(
        ConflictRecord(
            id="conflict_region_arkaim_temporal",
            conflict_type=ConflictType.TEMPORAL_INCOMPATIBILITY,
            subject_id=ENTITY,
            claim_ids=[temporal_claim, claim_a],
            evidence_ids=[ref_a],
            explanation="Two temporal interpretations of the same site cannot both hold.",
        )
    )

    reasoning = ReasoningRepository(env)
    resolved = reasoning.add(
        ReasoningResult(
            id="reasoning_region_arkaim_derivation",
            status=ReasoningStatus.RESOLVED,
            output_claim_id="output_claim_region_arkaim_derivation",
            output_text="Synthesis over both source perspectives.",
            category=ProvenanceCategory.DERIVED,
            input_claims=[
                ReasoningInput(claim_id=claim_a, evidence_ids=[ref_a]),
                ReasoningInput(claim_id=claim_b, evidence_ids=[ref_b]),
            ],
            method_id="source_aggregation",
            method_version="v1",
            confidence=0.55,
            uncertainty_reasons=["sources disagree on scope", "single site sample"],
            metadata={"subjects": [{"subject_id": ENTITY}]},
        )
    )
    reasoning.add(
        ReasoningResult(
            id="reasoning_region_arkaim_hypothesis",
            status=ReasoningStatus.HYPOTHESIS,
            output_claim_id="output_claim_region_arkaim_hypothesis",
            output_text="Tentative ritual-use interpretation.",
            category=ProvenanceCategory.HYPOTHESIS,
            input_claims=[
                ReasoningInput(claim_id=claim_a, evidence_ids=[ref_a]),
                ReasoningInput(claim_id=temporal_claim, evidence_ids=[]),
            ],
            method_id="rule_hint",
            method_version="v0.2",
            confidence=0.35,
            metadata={"subjects": [{"subject_id": ENTITY}]},
        )
    )

    CorrectionRepository(env).add(
        CorrectionRecord(
            id="correction_region_arkaim_pending",
            finding_id="finding_region_arkaim_window",
            subject_id=ENTITY,
            superseded_claim_ids=[claim_b],
            evidence_ids=[ref_b],
            temporal_reference_ids=["temporal_region_arkaim"],
            affected_reasoning_ids=[resolved.id],
        )
    )
    return {"claim_a": claim_a, "claim_b": claim_b, "temporal_claim": temporal_claim, "evidence_ids": evidence_ids}


def test_trace_requires_reader_auth():
    response = _client(authenticated=False).get(f"/knowledge/cards/trace/{ENTITY}")
    assert response.status_code == 401


def test_full_journey_claim_to_evidence_to_conflict_to_reasoning_to_correction(journey_env):
    client = _client(authenticated=True)
    baseline = _trace(client, ENTITY)
    real_claims = [c for c in baseline["claims"] if c.get("source_ref", "").startswith("book:")]
    assert len(real_claims) >= 2, "entity card must expose at least two book claims"
    ids = _seed(real_claims, journey_env)
    ref_a, ref_b = real_claims[0]["source_ref"], real_claims[1]["source_ref"]

    data = _trace(client, ENTITY)

    # claim -> evidence: every journey ref is a claim source_ref AND an evidence entry
    claim_refs = {c.get("source_ref") for c in data["claims"]}
    evidence_refs = {e.get("source_ref") for e in data["evidence"]}
    assert ref_a in claim_refs and ref_b in claim_refs
    assert ref_a in evidence_refs and ref_b in evidence_refs
    # evidence is projected from claims, never fabricated: each evidence row matches a claim ref
    assert evidence_refs <= claim_refs

    # conflict -> exact claim/evidence IDs, both records persisted, competing claims untouched
    conflict_ids = {c["id"] for c in data["conflicts"]}
    assert {"conflict_region_arkaim_direct", "conflict_region_arkaim_temporal"} <= conflict_ids
    direct = next(c for c in data["conflicts"] if c["id"] == "conflict_region_arkaim_direct")
    assert direct["conflict_type"] == "DIRECT_CONTRADICTION"
    assert direct["claim_ids"] == [ids["claim_a"], ids["claim_b"]]
    assert direct["evidence_ids"] == ids["evidence_ids"]
    assert direct["status"] == "UNRESOLVED"
    temporal_conflict = next(c for c in data["conflicts"] if c["id"] == "conflict_region_arkaim_temporal")
    assert temporal_conflict["conflict_type"] == "TEMPORAL_INCOMPATIBILITY"

    # reasoning -> exact input lineage tied to the same claims/evidence as the conflict
    assert {r["id"] for r in data["reasoning"]} == {
        "reasoning_region_arkaim_derivation",
        "reasoning_region_arkaim_hypothesis",
    }
    resolved = next(r for r in data["reasoning"] if r["status"] == "RESOLVED")
    assert resolved["input_claims"][0]["claim_id"] == ids["claim_a"]
    assert resolved["input_claims"][1]["claim_id"] == ids["claim_b"]
    assert resolved["input_claims"][0]["evidence_ids"] == [ref_a]
    assert resolved["input_claims"][1]["evidence_ids"] == [ref_b]
    assert resolved["method_id"] == "source_aggregation" and resolved["method_version"] == "v1"
    assert resolved["category"] == "DERIVED" and resolved["uncertainty_reasons"]
    assert resolved["metadata"]["subjects"][0]["subject_id"] == ENTITY

    # correction -> superseded claim + affected reasoning close the chain
    assert len(data["corrections"]) == 1
    correction = data["corrections"][0]
    assert correction["status"] == "PENDING"
    assert correction["superseded_claim_ids"] == [ids["claim_b"]]
    assert correction["affected_reasoning_ids"] == ["reasoning_region_arkaim_derivation"]
    assert set(correction["evidence_ids"]) <= evidence_refs

    # totals are honest and match returned sections
    assert data["totals"]["conflicts"] == 2
    assert data["totals"]["reasoning"] == 2
    assert data["totals"]["corrections"] == 1
    assert data["totals"]["lineage"] == 2

    # M5 -> M6 -> M7 links are derived only from exact existing IDs.
    lineage = {item["conflict_id"]: item for item in data["lineage"]}
    direct_lineage = lineage["conflict_region_arkaim_direct"]
    assert direct_lineage["claim_links"] == sorted([ids["claim_a"], ids["claim_b"]])
    assert direct_lineage["evidence_ids"] == ids["evidence_ids"]
    assert {link["record_id"] for link in direct_lineage["evidence_links"]} >= set(ids["evidence_ids"])
    assert direct_lineage["reasoning_ids"] == [
        "reasoning_region_arkaim_derivation",
        "reasoning_region_arkaim_hypothesis",
    ]
    assert direct_lineage["corrections"] == [
        {
            "correction_id": "correction_region_arkaim_pending",
            "stale_reasoning_ids": ["reasoning_region_arkaim_derivation"],
        }
    ]
    assert "claim::book:book:missing" not in direct_lineage["claim_links"]

    # honest status rule (GO-1): COMPLETE iff no limitations and every evidence row is RESOLVED
    unresolved = [row for row in data["evidence"] if row.get("status") != "RESOLVED"]
    assert (data["status"] == "COMPLETE") == (data["limitations"] == [] and not unresolved)


def test_journey_pagination_walks_whole_chain(journey_env):
    client = _client(authenticated=True)
    baseline = _trace(client, ENTITY)
    book_claims = [c for c in baseline["claims"] if c.get("source_ref", "").startswith("book:")][:2]
    _seed(book_claims, journey_env)

    claims: dict = {}
    evidence: dict = {}
    conflicts: set = set()
    reasoning: set = set()
    corrections: set = set()
    offset = 0
    for _ in range(50):
        data = _trace(client, ENTITY, offset=offset, limit=1)
        for claim in data["claims"]:
            claims[(claim.get("source_ref"), claim.get("text"))] = True
        for item in data["evidence"]:
            evidence[item.get("source_ref")] = True
        conflicts.update(c["id"] for c in data["conflicts"])
        reasoning.update(r["id"] for r in data["reasoning"])
        corrections.update(c["id"] for c in data["corrections"])
        if data["next_offset"] is None:
            break
        offset = data["next_offset"]
    else:
        pytest.fail("pagination did not terminate")

    totals = data["totals"]
    assert len(claims) == totals["claims"], "pagination must not lose claims"
    assert len(evidence) == totals["evidence"], "pagination must not lose evidence"
    assert conflicts == {"conflict_region_arkaim_direct", "conflict_region_arkaim_temporal"}
    assert reasoning == {"reasoning_region_arkaim_derivation", "reasoning_region_arkaim_hypothesis"}
    assert corrections == {"correction_region_arkaim_pending"}


def test_journey_filters_narrow_sections_without_fabrication(journey_env):
    client = _client(authenticated=True)
    baseline = _trace(client, ENTITY)
    claims = [c for c in baseline["claims"] if c.get("source_ref", "").startswith("book:")][:2]
    _seed(claims, journey_env)

    only_resolved = _trace(client, ENTITY, reasoning_status="RESOLVED")
    assert [r["id"] for r in only_resolved["reasoning"]] == ["reasoning_region_arkaim_derivation"]
    only_hypothesis = _trace(client, ENTITY, reasoning_status="HYPOTHESIS")
    assert [r["id"] for r in only_hypothesis["reasoning"]] == ["reasoning_region_arkaim_hypothesis"]

    unresolved = _trace(client, ENTITY, conflict_status="UNRESOLVED")
    assert len(unresolved["conflicts"]) == 2
    resolved_filter = _trace(client, ENTITY, conflict_status="RESOLVED_WITH_EVIDENCE")
    assert resolved_filter["conflicts"] == [], "filter must exclude, not fabricate"

    pending = _trace(client, ENTITY, correction_status="PENDING")
    assert len(pending["corrections"]) == 1
    confirmed = _trace(client, ENTITY, correction_status="CONFIRMED")
    assert confirmed["corrections"] == []
    # filtered sections still expose full totals so callers see the unfiltered chain size
    assert confirmed["totals"]["corrections"] == 1

    # evidence_status filters real M2 resolver outcomes, never fabricating rows
    evidence_baseline = _trace(client, ENTITY)
    statuses = [e["status"] for e in evidence_baseline["evidence"]]
    assert statuses, "evidence projection must expose resolver outcomes"
    for status in sorted(set(statuses)):
        filtered = _trace(client, ENTITY, evidence_status=status)
        assert filtered["evidence"], f"status {status} exists in baseline and must survive filtering"
        assert all(e["status"] == status for e in filtered["evidence"])
        assert filtered["totals"]["evidence"] == len(statuses)
    not_a_status = _trace(client, ENTITY, evidence_status="NOT_A_STATUS")
    assert not_a_status["evidence"] == []
    assert not_a_status["totals"]["evidence"] == len(statuses)


def test_journey_region_arkaim_resolves_book_claims_through_evidence(journey_env, tmp_path, monkeypatch):
    """Canonical region identity reaches Book claims and the unchanged M2 resolver."""
    import json

    client = _client(authenticated=True)
    baseline = _trace(client, ENTITY)
    book_rows = [e for e in baseline["evidence"] if e["source_ref"].startswith("book:")]
    assert book_rows, "approved region_arkaim crosswalk must expose book evidence references"
    catalog_backed = [row for row in book_rows if str(row.get("chunk_id", "")).startswith("chunk_")]
    assert catalog_backed, "region identity must retrieve actual book chunks"
    assert all(row["status"] == "RESOLVED" and row["evidence_id"] for row in catalog_backed)

    resolved = _trace(client, ENTITY, evidence_status="RESOLVED")
    resolved_book_rows = [row for row in resolved["evidence"] if row["source_ref"].startswith("book:")]
    assert resolved_book_rows, "catalog-backed region book fragments must resolve to RESOLVED"
    for row in resolved_book_rows:
        assert row["status"] == "RESOLVED"
        assert row["evidence_id"], "RESOLVED row must carry the evidence record id"
        assert row["source_ref"].startswith("book:")

    # empty catalog extension point: same claim references become UNAVAILABLE, not RESOLVED
    empty_catalog = tmp_path / "empty_catalog.json"
    empty_catalog.write_text(json.dumps([]), encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_EVIDENCE_CATALOG", str(empty_catalog))

    unavailable = _trace(client, ENTITY, evidence_status="UNAVAILABLE")
    assert unavailable["evidence"], "missing catalog fragments must surface as UNAVAILABLE"
    assert all(row["status"] == "UNAVAILABLE" and row["evidence_id"] is None for row in unavailable["evidence"])
    assert all(row["source_ref"].startswith("book:") for row in unavailable["evidence"])
    still_resolved = _trace(client, ENTITY, evidence_status="RESOLVED")
    assert [row for row in still_resolved["evidence"] if row["source_ref"].startswith("book:")] == []
    assert still_resolved["totals"]["evidence"] == unavailable["totals"]["evidence"]


def test_card_claim_id_bridge_is_deterministic_and_fail_closed():
    from core.routes.knowledge_cards import _card_claim_id
    from narrative_engine.provenance.claim import CanonClaim

    claim = {"text": "Аркаим", "source_ref": "book:chunk_1", "chunk_id": "chunk_1"}
    expected = CanonClaim.make_id("Аркаим", "book", "chunk:chunk_1")
    assert _card_claim_id(claim) == expected
    assert _card_claim_id({**claim, "text": "Аркаим"}) == expected
    assert _card_claim_id({"text": "World", "source_ref": "world_model:region_1", "chunk_id": None}) is None
    assert _card_claim_id({"text": "No chunk", "source_ref": "book:unknown", "chunk_id": None}) is None


def test_card_claim_id_bridge_supports_canonical_external_locator():
    from core.routes.knowledge_cards import _card_claim_id
    from narrative_engine.provenance.claim import CanonClaim

    archaeology = {"text": "Древнее городище", "source_ref": "ARCHAEOLOGY.json:аркаим:location", "chunk_id": None}
    expected = CanonClaim.make_id(archaeology["text"], "archaeology", "external:archaeology:аркаим:location")
    assert _card_claim_id(archaeology) == expected
    academic = {"text": "Academic note", "source_ref": "external:academic:record:42"}
    assert _card_claim_id(academic) == CanonClaim.make_id(academic["text"], "academic", academic["source_ref"])
    assert _card_claim_id({"text": "Unknown", "source_ref": "OTHER.json:x", "chunk_id": None}) is None


def test_trace_exposes_archaeology_claim_id_without_fabrication():
    from core.routes.knowledge_cards import _card_claim_id

    client = _client(authenticated=True)
    data = _trace(client, ENTITY)
    archaeology_claims = [c for c in data["claims"] if c.get("source_ref", "").startswith("ARCHAEOLOGY.json:")]
    assert archaeology_claims, "region trace must expose archaeology claims"
    assert all(c.get("claim_id") == _card_claim_id(c) for c in archaeology_claims)
    assert all(c["claim_id"].startswith("claim_") for c in archaeology_claims)


def test_external_registry_is_versioned_and_read_only():
    from evidence.external_registry import build_external_locator_source

    knowledge_dir = ROOT / "core" / "KNOWLEDGE"
    source = build_external_locator_source(knowledge_dir)
    fragment = source.get_fragment("external:archaeology:аркаим:location")
    assert fragment is not None
    assert fragment["source_version"].startswith("ARCHAEOLOGY.json@")
    assert len(fragment["content_hash"]) == 64
    assert source.get_fragment("external:unknown:missing") is None


def test_trace_resolves_registered_archaeology_evidence(journey_env):
    client = _client(authenticated=True)
    data = _trace(client, ENTITY)
    archaeology_rows = [e for e in data["evidence"] if e["source_ref"].startswith("ARCHAEOLOGY.json:")]
    assert archaeology_rows
    assert all(row["status"] == "RESOLVED" for row in archaeology_rows)
    assert all(row["evidence_id"] for row in archaeology_rows)
    assert all(row["source_ref"].startswith("ARCHAEOLOGY.json:") for row in archaeology_rows)


def test_evidence_claim_ids_reuse_the_claims_section_identity(journey_env):
    """Real entity: evidence rows repeat claim identities and never invent new ones."""
    client = _client(authenticated=True)
    data = _trace(client, ENTITY)

    claims_section_ids = {c["claim_id"] for c in data["claims"] if c.get("claim_id")}
    evidence_claim_ids = {row["claim_id"] for row in data["evidence"] if row.get("claim_id")}
    assert evidence_claim_ids, "book/archaeology claims of the real entity must bridge"
    assert evidence_claim_ids <= claims_section_ids, "evidence must not invent claim identities"

    book_rows = [row for row in data["evidence"] if row.get("source_ref", "").startswith("book:")]
    assert book_rows, "real entity exposes book evidence rows"
    assert all(row.get("claim_id") for row in book_rows), "every book row has a stable bridged identity"

    claims_by_ref = {c.get("source_ref"): c["claim_id"] for c in data["claims"] if c.get("claim_id")}
    for row in book_rows:
        assert row["claim_id"] == claims_by_ref[row["source_ref"]], "one claim => one identity in both sections"

    supported_prefixes = ("book:", "ARCHAEOLOGY.json:", "external:")
    unsupported = [row for row in data["evidence"] if not row.get("source_ref", "").startswith(supported_prefixes)]
    assert unsupported, "real entity still carries unsupported refs (world_model and similar)"
    assert all(row.get("claim_id") is None for row in unsupported), "unsupported refs stay unlinked, not guessed"


def test_trace_lineage_omits_unmatched_records_without_fabrication():
    from core.routes.knowledge_cards import _trace_lineage

    lineage = _trace_lineage(
        claims=[{"claim_id": "card-claim-present", "source_ref": "book:present"}],
        evidence=[{"source_ref": "book:present", "evidence_id": "evidence-present"}],
        conflicts=[{"id": "conflict-unmatched", "claim_ids": ["claim-missing"], "evidence_ids": ["evidence-missing"]}],
        reasoning=[{"id": "reasoning-unmatched", "input_claims": [{"claim_id": "other", "evidence_ids": ["other"]}]}],
        corrections=[{"id": "correction-unmatched", "superseded_claim_ids": ["other"], "affected_reasoning_ids": ["other"]}],
    )

    assert lineage == [
        {
            "conflict_id": "conflict-unmatched",
            "claim_ids": ["claim-missing"],
            "evidence_ids": ["evidence-missing"],
            "claim_links": [],
            "evidence_links": [],
            "reasoning_ids": [],
            "corrections": [],
        }
    ]


def test_empty_entity_gets_partial_status_and_no_synthetic_records(journey_env):
    client = _client(authenticated=True)
    _seed(
        [
            {"source_ref": "book:chunk:ref_x", "text": "x", "chunk_id": "ref_x"},
            {"source_ref": "book:chunk:ref_y", "text": "y", "chunk_id": "ref_y"},
        ],
        journey_env,
    )

    data = _trace(client, EMPTY_ENTITY)
    assert data["conflicts"] == []
    assert data["reasoning"] == []
    assert data["corrections"] == []
    assert data["totals"]["conflicts"] == 0
    assert data["totals"]["reasoning"] == 0
    assert data["totals"]["corrections"] == 0
    assert data["status"] == "PARTIAL"
    assert data["limitations"], "missing data must surface as explicit limitations"
    # records persisted for another subject must not leak into this entity's trace
