# -*- coding: utf-8 -*-
"""M21 — Event-Aware Ask/RAG.

Проверяет, что для валидных claim→event связей найденных книжных claims
контекст Ask/RAG включает представления канонических событий через
build_canonical_event_view. Основание — только проверенная связь
claim→event (claim_temporal_links.json); эвристики запрещены.

Критерии приёмки OWNER: события event_cosmic_impulse, event_kali_yuga_onset
и event_awakening разрешаются по реальным production-claims; несколько
claims одного события не дублируют его; claim без связи и невалидная
цепочка не добавляют событие; сценарные материалы появляются только при
наличии утверждённых связей; provenance, source_ref, event_id, epoch_id и
статусы сохраняются; пустой Knowledge Core не ломает Ask/RAG.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO = Path(__file__).resolve().parent.parent.parent
_CORE = _REPO / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.claim_temporal_linker import ClaimTemporalLink, ClaimTemporalLinker  # noqa: E402
from narrative_engine.provenance.claim import CanonClaim  # noqa: E402
from schemas.world_reference import WorldEntityReference, WorldReferenceStatus  # noqa: E402

# Production-claims (claim_temporal_links.json, OWNER M17.2/M17.3).
CLAIM_COSMIC = ("claim_8acb95533b78", "chunk_p_0008_4a4f27f88a99")
CLAIM_COSMIC_2 = ("claim_879edd266d49", "chunk_p_0007_b812dfae0ff4")
CLAIM_COSMIC_3 = ("claim_14e594d28a87", "chunk_p_0018_89a09e6d3d55")
CLAIM_KALI = ("claim_8ebb1ec3ae30", "chunk_p_0529_abdcaff6f8bd")
CLAIM_KALI_2 = ("claim_365f11560938", "chunk_p_0570_e94101594d2f")
CLAIM_AWAKENING = ("claim_7b221376376c", "chunk_p_0799_57e67fec2309")

TEXT_COSMIC = "Рожденный в неизмеримых глубинах пространства импульс послужил сигналом к действию начала преобразования."
TEXT_COSMIC_2 = "Настал момент, когда космические сроки и законы совпали и пришло время возникновения импульса"
TEXT_COSMIC_3 = "Возникновение импульса было сигналом к переходу сознания в материю физического тела."
TEXT_KALI = "— Наступление нынешней эпохи Кали Юги, когда приходит время темных сил на всей Земле, потребует от человечества полной самоотверженной самоотдачи и вы должны подготовиться для встречи и прохождения по ней во всеоружии."
TEXT_KALI_2 = "— Наступающая эпоха Кали Юги, время чрезвычайно жёсткое и суровое."
TEXT_AWAKENING = (
    "Зажжётся беззаветный огонь сердечного энтузиазма развивая голос сердца, пробуждая тем самым сознание человечества в преданном служении общему благу."
)
TEXT_NO_LINK = "Совершенно неподтверждённое утверждение без связи с событиями мира."


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


def _resolved_ref(claim_id: str, node_id: str):
    ref = MagicMock()
    ref.status = MagicMock()
    ref.status.value = "RESOLVED"
    ref.model_dump.return_value = {
        "claim_id": claim_id,
        "temporal_node_id": node_id,
        "status": "RESOLVED",
        "time_basis": "WORLD_TIME",
    }
    return ref


def _world_ref():
    return WorldEntityReference(
        query="Аркаим",
        canonical_id="arkaim",
        name="Аркаим",
        status=WorldReferenceStatus.RESOLVED,
        resolution_method="canonical_id",
    )


@contextmanager
def _patched_env(card_dict: dict, *, links: list[ClaimTemporalLink] | None = None, use_production_linker: bool = False):
    """Патчит builder/resolvers; claim-реестр — production или переданный список."""
    mock_card = MagicMock()
    mock_card.to_dict.return_value = card_dict
    mock_builder = MagicMock()
    mock_builder.build.return_value = mock_card

    fake_engine = MagicMock()
    fake_engine.get_node.return_value = None
    fake_world = MagicMock()
    fake_world.enable_temporal.return_value = fake_engine

    mock_linker = ClaimTemporalLinker.from_json() if use_production_linker else ClaimTemporalLinker(links=links or [])

    resolver = MagicMock()
    resolver.resolve.side_effect = lambda claim_id, temporal_node_id, time_basis: _resolved_ref(claim_id, temporal_node_id)

    with patch("knowledge_card.get_card_builder", return_value=mock_builder):
        with patch("knowledge.world_resolver.WorldKnowledgeResolver") as mock_wr:
            mock_wr.return_value.resolve.return_value = _world_ref()
            with patch("narrative_engine.world_engine.get_world_engine", return_value=fake_world):
                with patch.object(ClaimTemporalLinker, "from_json", return_value=mock_linker):
                    with patch("knowledge.temporal_resolver.KnowledgeTemporalResolver", return_value=resolver):
                        yield


def _gather_views(card_dict: dict, *, links=None, use_production_linker: bool = False):
    from core.services.knowledge_core_context import (
        gather_canonical_event_views,
        gather_knowledge_core_context,
    )

    with _patched_env(card_dict, links=links, use_production_linker=use_production_linker):
        contexts = gather_knowledge_core_context([{"entity_id": "arkaim", "name": "Аркаим"}])
        views = gather_canonical_event_views(contexts)
    return contexts, views


# ── Unit: сбор event_id из контекстов ──────────────────────────────────


class TestCollectEventIds:
    def _context_with(self, *entries):
        return [{"claim_temporal_references": list(entries)}]

    def test_resolved_valid_chain_included(self):
        from core.services.knowledge_core_context import _collect_event_ids

        entry = {
            "claim_id": "c1",
            "status": "RESOLVED",
            "event": {"event_id": "event_a", "chain_valid": True},
        }
        assert _collect_event_ids(self._context_with(entry)) == ["event_a"]

    def test_no_link_chain_invalid_unresolved_ambiguous_excluded(self):
        from core.services.knowledge_core_context import _collect_event_ids

        entries = [
            {"claim_id": "c1", "status": "NO_LINK", "event": None},
            {
                "claim_id": "c2",
                "status": "CHAIN_INVALID",
                "event": {"event_id": "event_b", "chain_valid": False},
            },
            {
                "claim_id": "c3",
                "status": "UNRESOLVED",
                "event": {"event_id": "event_c", "chain_valid": True},
            },
            {"claim_id": "c4", "status": "AMBIGUOUS", "candidate_node_ids": ["n1", "n2"]},
            {
                "claim_id": "c5",
                "status": "RESOLVED",
                "event": {"event_id": "event_d", "chain_valid": None},
            },
        ]
        assert _collect_event_ids(self._context_with(*entries)) == []

    def test_duplicates_squashed_and_sorted(self):
        from core.services.knowledge_core_context import _collect_event_ids

        e1 = {"claim_id": "c1", "status": "RESOLVED", "event": {"event_id": "event_z", "chain_valid": True}}
        e2 = {"claim_id": "c2", "status": "RESOLVED", "event": {"event_id": "event_a", "chain_valid": True}}
        e3 = {"claim_id": "c3", "status": "RESOLVED", "event": {"event_id": "event_z", "chain_valid": True}}
        contexts = [{"claim_temporal_references": [e1, e2]}, {"claim_temporal_references": [e3]}]
        assert _collect_event_ids(contexts) == ["event_a", "event_z"]

    def test_empty_contexts(self):
        from core.services.knowledge_core_context import _collect_event_ids

        assert _collect_event_ids([]) == []
        assert _collect_event_ids([{}]) == []


# ── Integration: production-claims → события ───────────────────────────


class TestProductionEventClaims:
    def test_cosmic_impulse_event_included(self):
        card = _card_dict([_book_claim(CLAIM_COSMIC[1], TEXT_COSMIC)])
        _, views = _gather_views(card, use_production_linker=True)
        ids = [v["event_id"] for v in views]
        assert ids == ["event_cosmic_impulse"]
        view = views[0]
        assert view["found"] is True
        assert view["temporal"]["epoch_id"] is not None
        assert view["temporal"]["chain_valid"] is True
        assert any(c["claim_id"] == CLAIM_COSMIC[0] for c in view["claims"])

    def test_kali_yuga_onset_event_included(self):
        card = _card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)])
        _, views = _gather_views(card, use_production_linker=True)
        assert [v["event_id"] for v in views] == ["event_kali_yuga_onset"]
        view = views[0]
        claim = next(c for c in view["claims"] if c["claim_id"] == CLAIM_KALI[0])
        assert claim["source_ref"] == f"book:{CLAIM_KALI[1]}"
        assert claim["chunk_id"] == CLAIM_KALI[1]
        assert claim["text_resolved"] is True
        assert claim["event_id"] == "event_kali_yuga_onset"

    def test_awakening_event_included(self):
        card = _card_dict([_book_claim(CLAIM_AWAKENING[1], TEXT_AWAKENING)])
        _, views = _gather_views(card, use_production_linker=True)
        assert [v["event_id"] for v in views] == ["event_awakening"]


# ── Дедупликация, запреты, пустой контекст ─────────────────────────────


class TestDedupForbiddenAndEmpty:
    def test_three_cosmic_claims_yield_one_event(self):
        card = _card_dict(
            [
                _book_claim(CLAIM_COSMIC[1], TEXT_COSMIC),
                _book_claim(CLAIM_COSMIC_2[1], TEXT_COSMIC_2),
                _book_claim(CLAIM_COSMIC_3[1], TEXT_COSMIC_3),
            ]
        )
        _, views = _gather_views(card, use_production_linker=True)
        assert [v["event_id"] for v in views] == ["event_cosmic_impulse"]

    def test_two_kali_claims_yield_one_event(self):
        card = _card_dict(
            [
                _book_claim(CLAIM_KALI[1], TEXT_KALI),
                _book_claim(CLAIM_KALI_2[1], TEXT_KALI_2),
            ]
        )
        _, views = _gather_views(card, use_production_linker=True)
        assert [v["event_id"] for v in views] == ["event_kali_yuga_onset"]

    def test_claim_without_link_adds_no_foreign_event(self):
        card = _card_dict([_book_claim("chunk_p_0999_deadbeef0000", TEXT_NO_LINK)])
        contexts, views = _gather_views(card, links=[])
        assert views == []
        statuses = [e["status"] for e in contexts[0]["claim_temporal_references"]]
        assert statuses == ["NO_LINK"]

    def test_invalid_chain_yields_no_confirmed_event(self):
        claim_id = _claim_id(TEXT_COSMIC, CLAIM_COSMIC[1])
        card = _card_dict([_book_claim(CLAIM_COSMIC[1], TEXT_COSMIC)])
        links = [
            ClaimTemporalLink(
                claim_id=claim_id,
                temporal_node_id="temporal_pre_arkaim",
                event_id="event_does_not_exist",
            )
        ]
        contexts, views = _gather_views(card, links=links)
        assert views == []
        assert contexts[0]["claim_temporal_references"][0]["status"] == "CHAIN_INVALID"

    def test_empty_knowledge_core_keeps_ask_working(self):
        from core.services.knowledge_core_context import (
            gather_canonical_event_views,
            gather_knowledge_core_context,
        )

        assert gather_knowledge_core_context([]) == []
        assert gather_canonical_event_views([]) == []
        assert gather_canonical_event_views([{}]) == []


# ── Сценарные материалы и provenance ───────────────────────────────────


class TestScreenplayMaterialsAndProvenance:
    def test_kali_event_exposes_approved_screenplay_materials(self):
        card = _card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)])
        _, views = _gather_views(card, use_production_linker=True)
        materials = views[0]["screenplay_materials"]
        pairs = {(m["screenplay_scene_id"], m["book_chunk_id"]) for m in materials}
        assert ("scene_081", "chunk_p_0529_abdcaff6f8bd") in pairs

    def test_cosmic_event_exposes_approved_screenplay_materials(self):
        card = _card_dict(
            [
                _book_claim(CLAIM_COSMIC_2[1], TEXT_COSMIC_2),
                _book_claim(CLAIM_COSMIC_3[1], TEXT_COSMIC_3),
            ]
        )
        _, views = _gather_views(card, use_production_linker=True)
        pairs = {(m["screenplay_scene_id"], m["book_chunk_id"]) for m in views[0]["screenplay_materials"]}
        assert ("scene_004", "chunk_p_0007_b812dfae0ff4") in pairs
        assert ("scene_009", "chunk_p_0018_89a09e6d3d55") in pairs

    def test_materials_come_only_from_approved_registry(self):
        # Сценарные материалы — только из подтверждённого screenplay_links
        # по chunk_id claims события (никаких эвристик).
        card = _card_dict([_book_claim(CLAIM_AWAKENING[1], TEXT_AWAKENING)])
        _, views = _gather_views(card, use_production_linker=True)
        materials = views[0]["screenplay_materials"]
        assert all(m["book_chunk_id"] == CLAIM_AWAKENING[1] for m in materials)
        assert all(m["screenplay_scene_id"].startswith("scene_") for m in materials)

    def test_provenance_and_ids_preserved(self):
        card = _card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)])
        _, views = _gather_views(card, use_production_linker=True)
        view = views[0]
        assert view["event"]["id"] == "event_kali_yuga_onset"
        assert view["event"]["provenance"], "provenance события отсутствует"
        claim = view["claims"][0]
        assert claim["source_ref"].startswith("book:")
        assert claim["provenance_category"] is not None
        assert view["temporal"]["temporal_node_id"]
        assert view["limitations"] == []


# ── Маршрут /book/ask ─────────────────────────────────────────────────


class TestAskRouteWiring:
    def test_ask_route_attaches_canonical_events(self):
        import inspect

        from core.routes import book

        source = inspect.getsource(book.ask)
        assert "gather_canonical_event_views" in source
        assert 'result["canonical_events"]' in source
