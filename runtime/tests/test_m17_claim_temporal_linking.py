"""M17 — Claim-Level Temporal Linking.

Проверяет, что подтверждённые связи claim→temporal-узел из
claim_temporal_links.json разрешаются в честные типизированные ссылки
(RESOLVED / UNRESOLVED / AMBIGUOUS / NO_LINK), entity-level temporal_reference
остаётся отдельным полем, а production-реестр содержит ровно девять
одобренных OWNER (M17.2/M17.3) связей на шесть канонических событий.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.claim_temporal_linker import ClaimTemporalLink, ClaimTemporalLinker
from narrative_engine.provenance.claim import CanonClaim
from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)
from narrative_engine.temporal.node import TemporalBounds, TemporalNode
from narrative_engine.temporal.precision import TemporalPrecision
from schemas.temporal_reference import (
    TemporalReference,
    TemporalReferenceStatus,
    TemporalTimeBasis,
)
from schemas.world_reference import WorldEntityReference, WorldReferenceStatus

CHUNK_A = "chunk_p_0010_77326a31efd2"
CHUNK_B = "chunk_p_0047_387817db08e3"
TEXT_A = "Аркаим был основан в начале II тысячелетия до нашей эры."
TEXT_B = "Город погиб в результате катастрофического пожара."
NODE_FOUNDING = "temporal_arkaim_founding"
NODE_FIRE = "temporal_arkaim_fire"
UNKNOWN_NODE = "temporal_does_not_exist"


# ── Helpers ────────────────────────────────────────────────────────────


def _claim_id(text: str, chunk_id: str) -> str:
    return CanonClaim.make_id(text, source_id="book", location=f"chunk:{chunk_id}")


def _book_claim(chunk_id: str, text: str) -> dict:
    return {
        "text": text,
        "source_ref": f"book:{chunk_id}",
        "chunk_id": chunk_id,
        "provenance": {"category": "AUTHOR_CANON", "confidence": 1.0},
    }


def _card_dict(book_claims: list[dict]) -> dict:
    return {
        "metadata": {"entity_id": "arkaim", "entity_name": "Аркаим"},
        "primary_entity": {"entity_id": "arkaim", "name": "Аркаим"},
        "sources": [{"source_name": "book", "claims": book_claims}],
        "contradictions": [],
        "screenplay_links": [],
    }


def _node(node_id: str, label: str) -> TemporalNode:
    return TemporalNode(
        id=node_id,
        label=label,
        precision=TemporalPrecision.CENTURY,
        era_id="arkaim_era",
        entity_ids=["arkaim"],
        event_ids=[f"evt_{node_id}"],
        provenance=[
            ProvenanceTag(
                source_level=SourceLevel.CANON,
                category=ProvenanceCategory.AUTHOR_CANON,
                confidence=1.0,
                notes="каноническая эпоха",
            )
        ],
        bounds=TemporalBounds(start="2100 BCE", end="2000 BCE", uncertainty="±100 лет"),
    )


def _world_ref(status: WorldReferenceStatus = WorldReferenceStatus.UNRESOLVED):
    if status is WorldReferenceStatus.RESOLVED:
        return WorldEntityReference(
            query="Аркаим",
            canonical_id="arkaim",
            name="Аркаим",
            status=status,
            resolution_method="canonical_id",
        )
    return WorldEntityReference(query="Аркаим", status=status, resolution_method="none")


@contextmanager
def _patched_env(
    card_dict: dict,
    *,
    links: list[ClaimTemporalLink] | None = None,
    nodes: dict[str, TemporalNode] | None = None,
):
    """Патчит builder, world-resolver, temporal-engine и claim-реестр."""
    mock_card = MagicMock()
    mock_card.to_dict.return_value = card_dict
    mock_builder = MagicMock()
    mock_builder.build.return_value = mock_card

    fake_engine = MagicMock()
    fake_engine.get_node.side_effect = lambda node_id: (nodes or {}).get(node_id)
    fake_world = MagicMock()
    fake_world.enable_temporal.return_value = fake_engine

    mock_linker = ClaimTemporalLinker(links=links or [])

    with patch("knowledge_card.get_card_builder", return_value=mock_builder):
        with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
            mock_wr.return_value.resolve.return_value = _world_ref()
            with patch("narrative_engine.world_engine.get_world_engine", return_value=fake_world):
                with patch.object(ClaimTemporalLinker, "from_json", return_value=mock_linker):
                    with patch("core.routes.knowledge_cards._evidence_projection", return_value=[]):
                        yield


# ── Unit: linker ───────────────────────────────────────────────────────


class TestClaimTemporalLinker:
    def test_from_json_loads_valid_links(self):
        import json

        payload = [
            {"claim_id": "claim_a", "temporal_node_id": "node_a", "notes": "n1"},
            {"claim_id": "", "temporal_node_id": "node_b"},
            {"claim_id": "claim_c", "temporal_node_id": ""},
        ]
        with NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
            path = Path(fh.name)
        try:
            linker = ClaimTemporalLinker.from_json(path)
        finally:
            path.unlink(missing_ok=True)

        assert len(linker.links) == 1
        assert linker.links[0].claim_id == "claim_a"
        assert linker.has_links()

    def test_from_json_missing_file_returns_empty(self):
        linker = ClaimTemporalLinker.from_json(Path("nonexistent_claim_links.json"))
        assert linker.links == []
        assert not linker.has_links()

    def test_get_links_for_claim_filters_by_id(self):
        linker = ClaimTemporalLinker(
            links=[
                ClaimTemporalLink(claim_id="c1", temporal_node_id="n1"),
                ClaimTemporalLink(claim_id="c2", temporal_node_id="n2"),
                ClaimTemporalLink(claim_id="c2", temporal_node_id="n3"),
            ]
        )
        assert len(linker.get_links_for_claim("c1")) == 1
        assert len(linker.get_links_for_claim("c2")) == 2
        assert linker.get_links_for_claim("c9") == []


# ── Service: _claim_temporal_references ────────────────────────────────


class TestClaimTemporalReferences:
    def test_claim_with_confirmed_link_resolves(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FOUNDING, notes="подтверждено")]
        nodes = {NODE_FOUNDING: _node(NODE_FOUNDING, "Основание Аркаима")}

        with _patched_env(card, links=links, nodes=nodes):
            entries = _claim_temporal_references(card)

        assert len(entries) == 1
        entry = entries[0]
        assert entry["claim_id"] == claim_id
        assert entry["status"] == "RESOLVED"
        ref = entry["temporal_reference"]
        assert ref["temporal_node_id"] == NODE_FOUNDING
        assert ref["time_basis"] == "WORLD_TIME"
        assert ref["precision"] == "CENTURY"
        assert ref["bounds"]["start"] == "2100 BCE"
        assert ref["temporal_provenance"]

    def test_source_ref_and_provenance_preserved(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FOUNDING, notes="n")]
        nodes = {NODE_FOUNDING: _node(NODE_FOUNDING, "label")}

        with _patched_env(card, links=links, nodes=nodes):
            entries = _claim_temporal_references(card)

        assert entries[0]["source_ref"] == f"book:{CHUNK_A}"
        assert entries[0]["notes"] == "n"
        assert entries[0]["temporal_reference"]["temporal_provenance"][0]["category"] == "AUTHOR_CANON"

    def test_claim_without_link_is_no_link(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        with _patched_env(card, links=[], nodes={}):
            entries = _claim_temporal_references(card)

        assert len(entries) == 1
        assert entries[0]["status"] == "NO_LINK"
        assert entries[0]["temporal_reference"] is None

    def test_ambiguous_links_return_ambiguous_without_autopick(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [
            ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FOUNDING),
            ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FIRE),
        ]
        nodes = {
            NODE_FOUNDING: _node(NODE_FOUNDING, "Основание"),
            NODE_FIRE: _node(NODE_FIRE, "Пожар"),
        }

        with _patched_env(card, links=links, nodes=nodes):
            entries = _claim_temporal_references(card)

        assert entries[0]["status"] == "AMBIGUOUS"
        assert entries[0]["temporal_reference"] is None
        assert set(entries[0]["candidate_node_ids"]) == {NODE_FOUNDING, NODE_FIRE}

    def test_unknown_node_returns_unresolved(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=UNKNOWN_NODE)]

        with _patched_env(card, links=links, nodes={}):
            entries = _claim_temporal_references(card)

        assert entries[0]["status"] == "UNRESOLVED"
        ref = entries[0]["temporal_reference"]
        assert ref["status"] == "UNRESOLVED"
        assert ref["temporal_node_id"] is None

    def test_multiple_claims_different_temporal_nodes(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        id_a = _claim_id(TEXT_A, CHUNK_A)
        id_b = _claim_id(TEXT_B, CHUNK_B)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A), _book_claim(CHUNK_B, TEXT_B)])
        links = [
            ClaimTemporalLink(claim_id=id_a, temporal_node_id=NODE_FOUNDING),
            ClaimTemporalLink(claim_id=id_b, temporal_node_id=NODE_FIRE),
        ]
        nodes = {
            NODE_FOUNDING: _node(NODE_FOUNDING, "Основание"),
            NODE_FIRE: _node(NODE_FIRE, "Пожар"),
        }

        with _patched_env(card, links=links, nodes=nodes):
            entries = _claim_temporal_references(card)

        by_id = {e["claim_id"]: e for e in entries}
        assert by_id[id_a]["temporal_reference"]["temporal_node_id"] == NODE_FOUNDING
        assert by_id[id_b]["temporal_reference"]["temporal_node_id"] == NODE_FIRE
        assert by_id[id_a]["temporal_reference"]["temporal_node_id"] != by_id[id_b]["temporal_reference"]["temporal_node_id"]

    def test_placeholder_chunk_and_non_book_claims_skipped(self):
        from core.services.knowledge_core_context import _claim_temporal_references

        card = {
            "sources": [
                {
                    "source_name": "book",
                    "claims": [
                        {"text": "x", "source_ref": "book:chunk", "chunk_id": "chunk"},
                        {"text": "y", "source_ref": "book:", "chunk_id": ""},
                    ],
                },
                {
                    "source_name": "screenplay",
                    "claims": [{"text": "z", "source_ref": "screenplay:scene:scene_000"}],
                },
            ]
        }
        with _patched_env(card, links=[], nodes={}):
            entries = _claim_temporal_references(card)

        assert entries == []


# ── Integration: entity vs claim separation ────────────────────────────


class TestEntityAndClaimSeparation:
    def test_entity_temporal_and_claim_no_link_are_separate(self):
        from core.services.knowledge_core_context import gather_knowledge_core_context

        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        entity_node = _node("arkaim", "Аркаим (entity)")
        with _patched_env(card, links=[], nodes={"arkaim": entity_node}):
            ctx = gather_knowledge_core_context([{"entity_id": "arkaim", "name": "Аркаим"}])[0]

        assert ctx["temporal_reference"]["status"] == "RESOLVED"
        assert ctx["temporal_reference"]["temporal_node_id"] == "arkaim"
        claim_entries = ctx["claim_temporal_references"]
        assert len(claim_entries) == 1
        assert claim_entries[0]["status"] == "NO_LINK"
        assert claim_entries[0]["temporal_reference"] is None

    def test_entity_and_claim_resolve_to_different_nodes(self):
        from core.services.knowledge_core_context import gather_knowledge_core_context

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FOUNDING)]
        nodes = {
            "arkaim": _node("arkaim", "Аркаим (entity)"),
            NODE_FOUNDING: _node(NODE_FOUNDING, "Основание"),
        }
        with _patched_env(card, links=links, nodes=nodes):
            ctx = gather_knowledge_core_context([{"entity_id": "arkaim", "name": "Аркаим"}])[0]

        assert ctx["temporal_reference"]["temporal_node_id"] == "arkaim"
        assert ctx["claim_temporal_references"][0]["temporal_reference"]["temporal_node_id"] == NODE_FOUNDING


# ── Integration: Holistic View + Ask/RAG ───────────────────────────────


class TestHolisticViewAndAsk:
    def test_holistic_view_includes_claim_temporal_references(self):
        from core.services.holistic_view import build_holistic_view

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FOUNDING)]
        nodes = {NODE_FOUNDING: _node(NODE_FOUNDING, "Основание")}

        with _patched_env(card, links=links, nodes=nodes):
            view = build_holistic_view("arkaim", "Аркаим")

        entries = view["claim_temporal_references"]
        assert len(entries) == 1
        assert entries[0]["status"] == "RESOLVED"
        assert view["availability"]["claim_temporal_links"] is True
        assert view["availability"]["claim_temporal_resolved"] is True
        assert not any("claim-level temporal linking отсутствует" in lim for lim in view["limitations"])

    def test_holistic_view_limitations_when_no_claim_links(self):
        from core.services.holistic_view import build_holistic_view

        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        with _patched_env(card, links=[], nodes={}):
            view = build_holistic_view("arkaim", "Аркаим")

        assert view["availability"]["claim_temporal_links"] is False
        assert view["availability"]["claim_temporal_resolved"] is False
        assert any("подтверждённых связей claims↔temporal-узлы" in lim for lim in view["limitations"])
        assert not any("claim-level temporal linking отсутствует" in lim for lim in view["limitations"])

    def test_holistic_view_limitations_when_links_unresolved(self):
        from core.services.holistic_view import build_holistic_view

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=UNKNOWN_NODE)]
        with _patched_env(card, links=links, nodes={}):
            view = build_holistic_view("arkaim", "Аркаим")

        assert view["availability"]["claim_temporal_links"] is True
        assert view["availability"]["claim_temporal_resolved"] is False
        assert any("ни одна не разрешилась" in lim for lim in view["limitations"])

    def test_ask_context_includes_claim_temporal_references(self):
        from core.services.knowledge_core_context import gather_knowledge_core_context

        claim_id = _claim_id(TEXT_A, CHUNK_A)
        card = _card_dict([_book_claim(CHUNK_A, TEXT_A)])
        links = [ClaimTemporalLink(claim_id=claim_id, temporal_node_id=NODE_FOUNDING)]
        nodes = {NODE_FOUNDING: _node(NODE_FOUNDING, "Основание")}

        with _patched_env(card, links=links, nodes=nodes):
            ctx = gather_knowledge_core_context([{"entity_id": "arkaim", "name": "Аркаим"}])[0]

        assert "claim_temporal_references" in ctx
        assert ctx["claim_temporal_references"][0]["status"] == "RESOLVED"


# ── Production state documentation ─────────────────────────────────────

_PRODUCTION_APPROVED_LINKS = {
    ("claim_879edd266d49", "temporal_pre_arkaim"),
    ("claim_8acb95533b78", "temporal_pre_arkaim"),
    ("claim_14e594d28a87", "temporal_pre_arkaim"),
    ("claim_7c245020a9db", "temporal_satya_yuga"),
    ("claim_38b5c7d6fc94", "temporal_satya_yuga"),
    ("claim_33e02918f53e", "temporal_satya_yuga"),
    ("claim_8ebb1ec3ae30", "temporal_эпоха_кали_юги"),
    ("claim_365f11560938", "temporal_эпоха_кали_юги"),
    ("claim_7b221376376c", "temporal_переход_к_новой_эре_(кали_юга)"),
}


class TestProductionRegistryState:
    def test_production_registry_has_nine_approved_links(self):
        linker = ClaimTemporalLinker.from_json()
        pairs = {(link.claim_id, link.temporal_node_id) for link in linker.links}
        assert len(linker.links) == 9
        assert pairs == _PRODUCTION_APPROVED_LINKS
        assert linker.has_links()

    def test_resolver_contract_is_read_only(self):
        ref = TemporalReference(
            claim_id="claim_x",
            time_basis=TemporalTimeBasis.WORLD,
            status=TemporalReferenceStatus.UNKNOWN,
            reason="no link",
            resolution_method="none",
        )
        assert not ref.is_resolved
        assert ref.temporal_node_id is None
