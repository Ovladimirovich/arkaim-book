# -*- coding: utf-8 -*-
"""M22 — Event-Aware Holistic View.

Проверяет, что build_holistic_view() показывает канонические события,
обоснованно связанные с claims сущности, через механизм M21
(gather_canonical_event_views). Основание — только валидная цепочка
claim → event → epoch → temporal node; эвристики запрещены.

Критерии приёмки OWNER: одно событие; несколько claims одного события без
дублей; несколько разных событий; сущность без связей; невалидная
цепочка; ошибка компонента не ломает view; книжные и сценарные материалы
с раздельным происхождением сохраняются; контракт Ask/RAG (M21) не
изменён.
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

# Production-claims (claim_temporal_links.json).
CLAIM_COSMIC = ("claim_8acb95533b78", "chunk_p_0008_4a4f27f88a99")
CLAIM_COSMIC_2 = ("claim_879edd266d49", "chunk_p_0007_b812dfae0ff4")
CLAIM_COSMIC_3 = ("claim_14e594d28a87", "chunk_p_0018_89a09e6d3d55")
CLAIM_KALI = ("claim_8ebb1ec3ae30", "chunk_p_0529_abdcaff6f8bd")
CLAIM_AWAKENING = ("claim_7b221376376c", "chunk_p_0799_57e67fec2309")

TEXT_COSMIC = "Рожденный в неизмеримых глубинах пространства импульс послужил сигналом к действию начала преобразования."
TEXT_COSMIC_2 = "Настал момент, когда космические сроки и законы совпали и пришло время возникновения импульса"
TEXT_COSMIC_3 = "Возникновение импульса было сигналом к переходу сознания в материю физического тела."
TEXT_KALI = "— Наступление нынешней эпохи Кали Юги, когда приходит время темных сил на всей Земле, потребует от человечества полной самоотверженной самоотдачи и вы должны подготовиться для встречи и прохождения по ней во всеоружии."
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
                        with patch("core.routes.knowledge_cards._evidence_projection", return_value=[]):
                            yield


def _view(card_dict: dict, *, links=None, use_production_linker: bool = False):
    from core.services.holistic_view import build_holistic_view

    with _patched_env(card_dict, links=links, use_production_linker=use_production_linker):
        return build_holistic_view("arkaim", "Аркаим")


# ── Одно событие и дедупликация ────────────────────────────────────────


class TestSingleEventAndDedup:
    def test_entity_with_one_canonical_event(self):
        view = _view(_card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)]), use_production_linker=True)
        events = view["canonical_events"]
        assert [e["event_id"] for e in events] == ["event_kali_yuga_onset"]
        assert events[0]["found"] is True
        assert events[0]["temporal"]["chain_valid"] is True
        assert view["availability"]["canonical_events"] is True

    def test_three_claims_same_event_not_duplicated(self):
        card = _card_dict(
            [
                _book_claim(CLAIM_COSMIC[1], TEXT_COSMIC),
                _book_claim(CLAIM_COSMIC_2[1], TEXT_COSMIC_2),
                _book_claim(CLAIM_COSMIC_3[1], TEXT_COSMIC_3),
            ]
        )
        view = _view(card, use_production_linker=True)
        assert [e["event_id"] for e in view["canonical_events"]] == ["event_cosmic_impulse"]


# ── Несколько событий, отсутствие связей, невалидная цепочка ───────────


class TestMultipleEventsForbiddenAndEmpty:
    def test_two_distinct_events_sorted(self):
        card = _card_dict(
            [
                _book_claim(CLAIM_AWAKENING[1], TEXT_AWAKENING),
                _book_claim(CLAIM_KALI[1], TEXT_KALI),
            ]
        )
        view = _view(card, use_production_linker=True)
        ids = [e["event_id"] for e in view["canonical_events"]]
        assert ids == sorted(ids)
        assert set(ids) == {"event_awakening", "event_kali_yuga_onset"}

    def test_entity_without_event_links_has_empty_list(self):
        view = _view(_card_dict([_book_claim("chunk_p_0999_deadbeef0000", TEXT_NO_LINK)]), links=[])
        assert view["canonical_events"] == []
        assert view["availability"]["canonical_events"] is False

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
        view = _view(card, links=links)
        assert view["canonical_events"] == []
        assert view["claim_temporal_references"][0]["status"] == "CHAIN_INVALID"


# ── Ошибки компонентов и обратная совместимость ────────────────────────


class TestFaultToleranceAndCompatibility:
    def test_component_failure_does_not_break_view(self):
        card = _card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)])
        from core.services.holistic_view import build_holistic_view

        with _patched_env(card, use_production_linker=True):
            with patch(
                "core.services.knowledge_core_context.gather_canonical_event_views",
                side_effect=RuntimeError("boom"),
            ):
                view = build_holistic_view("arkaim", "Аркаим")

        assert view["canonical_events"] == []
        assert view["view_type"] == "ENTITY_AGGREGATE"
        assert view["book_claims"], "book_claims потеряны при сбое canonical_events"

    def test_unavailable_event_skipped_others_survive(self):
        card = _card_dict(
            [
                _book_claim(CLAIM_AWAKENING[1], TEXT_AWAKENING),
                _book_claim(CLAIM_KALI[1], TEXT_KALI),
            ]
        )
        from core.services.canonical_event_view import build_canonical_event_view as real_build
        from core.services.holistic_view import build_holistic_view

        def _fail_awakening(event_id: str):
            if event_id == "event_awakening":
                raise RuntimeError("view build failed")
            return real_build(event_id)

        with _patched_env(card, use_production_linker=True):
            with patch(
                "core.services.canonical_event_view.build_canonical_event_view",
                side_effect=_fail_awakening,
            ):
                view = build_holistic_view("arkaim", "Аркаим")

        assert [e["event_id"] for e in view["canonical_events"]] == ["event_kali_yuga_onset"]
        assert view["view_type"] == "ENTITY_AGGREGATE"

    def test_book_and_screenplay_materials_keep_separate_provenance(self):
        view = _view(_card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)]), use_production_linker=True)
        event = view["canonical_events"][0]
        claim = event["claims"][0]
        assert claim["source_ref"] == f"book:{CLAIM_KALI[1]}"
        assert claim["provenance_category"] is not None
        material = next(m for m in event["screenplay_materials"] if m["screenplay_scene_id"] == "scene_081")
        assert material["link_type"] == "book_chunk_to_scene"
        assert material["book_chunk_id"] == CLAIM_KALI[1]
        assert material["notes"]

    def test_existing_fields_and_ask_contract_unchanged(self):
        view = _view(_card_dict([_book_claim(CLAIM_KALI[1], TEXT_KALI)]), use_production_linker=True)
        for key in (
            "view_type",
            "entity_id",
            "book_claims",
            "screenplay_links",
            "claim_temporal_references",
            "evidence",
            "world_reference",
            "temporal_reference",
            "availability",
            "limitations",
        ):
            assert key in view, f"поле {key} потеряно"

        import inspect

        from core.routes import book

        source = inspect.getsource(book.ask)
        assert 'result["canonical_events"]' in source
        assert "gather_canonical_event_views" in source
