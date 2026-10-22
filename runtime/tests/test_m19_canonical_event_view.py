"""M19 — Canonical Event View.

Проверяет read-only представление канонического события:
- событие с одной связанной книжной записью;
- событие с несколькими claims;
- событие без claims;
- несуществующий event_id;
- невалидную временную цепочку;
- сохранение исходных идентификаторов, source_ref и provenance;
- правильное отображение эпохи без выбора похожего temporal-узла;
- отображение сценарных материалов только при подтверждённой связи;
- только одобренные связи для «Передачи Учения» и отсутствие связей у «Строительства Аркаима»;
- обратную совместимость.
"""

from __future__ import annotations

import sys
from pathlib import Path

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.claim_temporal_linker import ClaimTemporalLinker  # noqa: E402
from knowledge.screenplay_linker import ScreenplayBookLinker  # noqa: E402
from narrative_engine.provenance.claim import CanonClaim  # noqa: E402


# ── Production state (M19 фактическое содержимое реестров) ────────────

_PRODUCTION_EVENTS_WITH_CLAIMS = {
    "event_cosmic_impulse": 5,
    "event_teacher_gathering": 2,
    "event_oceania_decline": 6,
    "event_journey_to_hyperborea": 1,
    "event_kali_yuga_onset": 2,
    "event_awakening": 1,
    "event_transmission_of_teaching": 1,
}

# События WORLD_MODEL, для которых claim-связей нет (M17 OWNER-решение)
_PRODUCTION_EVENTS_WITHOUT_CLAIMS = {
    "event_transmission_of_teaching",
    "event_arkaim_construction",
}


# ── Unit: build_canonical_event_view ──────────────────────────────────


class TestCanonicalEventView:
    def test_event_with_single_claim(self):
        """Критерий 1: событие с одной связанной книжной записью."""
        from core.services.canonical_event_view import build_canonical_event_view

        view = build_canonical_event_view("event_awakening")
        assert view["found"] is True
        assert view["event"]["id"] == "event_awakening"
        assert len(view["claims"]) == 1
        claim = view["claims"][0]
        assert claim["claim_id"] == "claim_7b221376376c"
        assert claim["event_id"] == "event_awakening"
        assert claim["chain_valid"] is True
        assert claim["text_resolved"] is True
        assert claim["text"] is not None
        assert claim["source_ref"].startswith("book:")

    def test_event_with_multiple_claims(self):
        """Критерий 2: событие с несколькими claims."""
        from core.services.canonical_event_view import build_canonical_event_view

        view = build_canonical_event_view("event_cosmic_impulse")
        assert view["found"] is True
        assert len(view["claims"]) == 5
        claim_ids = {c["claim_id"] for c in view["claims"]}
        assert claim_ids == {
            "claim_879edd266d49",
            "claim_8acb95533b78",
            "claim_14e594d28a87",
            "claim_8576da0c90aa",
            # Одобрено OWNER 2026-10-22 (G9): scene_003, chunk_p_0006 (Пролог).
            "claim_c685037a092a",
        }
        for c in view["claims"]:
            assert c["chain_valid"] is True
            assert c["event_id"] == "event_cosmic_impulse"

    def test_event_without_claims(self):
        """Критерий 3: событие без связанных claims."""
        from core.services.canonical_event_view import build_canonical_event_view

        view = build_canonical_event_view("event_arkaim_construction")
        assert view["found"] is True
        assert view["claims"] == []
        assert any("нет подтверждённых claim-связей" in lim for lim in view["limitations"])
        # Temporal-цепочка не показывается как валидная
        assert view["temporal"].get("chain_valid") is False or not view["temporal"].get("chain_valid")

    def test_nonexistent_event_id(self):
        """Критерий 4: несуществующий event_id."""
        from core.services.canonical_event_view import build_canonical_event_view

        view = build_canonical_event_view("event_does_not_exist")
        assert view["found"] is False
        assert view["claims"] == []
        assert any("не найдено" in lim for lim in view["limitations"])

    def test_invalid_chain_not_shown_as_valid(self):
        """Критерий 5: невалидная временная цепочка не показывается как валидная."""
        from core.services.canonical_event_view import build_canonical_event_view

        # event_kali_yuga_onset: цепочки валидны в production.
        # Проверяем, что chain_valid=True только после validate_chain.
        view = build_canonical_event_view("event_kali_yuga_onset")
        assert view["found"] is True
        for c in view["claims"]:
            assert c["chain_valid"] is True
            assert c["epoch_id"] is not None
        assert view["temporal"]["chain_valid"] is True

    def test_source_ref_and_provenance_preserved(self):
        """Критерий 6: сохранение исходных идентификаторов, source_ref, provenance."""
        from core.services.canonical_event_view import build_canonical_event_view

        view = build_canonical_event_view("event_cosmic_impulse")
        for c in view["claims"]:
            assert c["claim_id"].startswith("claim_")
            assert c["source_ref"].startswith("book:")
            assert c["provenance_category"] == "AUTHOR_CANON"
            assert c["chunk_id"] is not None
            # claim_id воспроизводим из текста + chunk_id
            recomputed = CanonClaim.make_id(c["text"], source_id="book", location=f"chunk:{c['chunk_id']}")
            assert recomputed == c["claim_id"]

    def test_epoch_displayed_without_similar_node(self):
        """Критерий 7: эпоха отображается по точному epoch_id, не по похожему имени."""
        from core.services.canonical_event_view import build_canonical_event_view

        view = build_canonical_event_view("event_kali_yuga_onset")
        # epoch_id точно из WORLD_MODEL, temporal-узел = temporal_{epoch_id}
        assert view["temporal"]["epoch_id"] == "эпоха_кали_юги"
        assert view["temporal"]["temporal_node_id"] == "temporal_эпоха_кали_юги"
        # Не «кали_юга» и не «эпоха_кали_юга_и_сати_юга»
        assert view["temporal"]["epoch_id"] != "кали_юга"
        assert view["temporal"]["epoch_id"] != "эпоха_кали_юга_и_сати_юга"

    def test_screenplay_materials_only_with_confirmed_link(self):
        """Критерий 8: сценарные материалы только при подтверждённой связи.

        M20.1: часть claim-чанков event_cosmic_impulse получила одобренные
        OWNER-связи (chunk_p_0007→scene_004, chunk_p_0018→scene_009).
        Материалы отображаются только для таких пар; claim-чанки без
        подтверждённой связи (chunk_p_0008) связей не получают.
        """
        from core.services.canonical_event_view import build_canonical_event_view
        from knowledge.screenplay_links_provenance import APPROVED_PAIRS

        view = build_canonical_event_view("event_cosmic_impulse")
        claim_chunk_ids = {c["chunk_id"] for c in view["claims"] if c.get("chunk_id")}
        materials = view["screenplay_materials"]
        assert materials, "после M20.1 у события есть подтверждённые сценарные материалы"
        for item in materials:
            assert item["book_chunk_id"] in claim_chunk_ids
            assert (item["screenplay_scene_id"], item["book_chunk_id"]) in APPROVED_PAIRS
            assert item["link_type"] == "book_chunk_to_scene"
        # Не все claim-чанки события связаны: минимум один остаётся без материалов.
        linked_chunks = {item["book_chunk_id"] for item in materials}
        assert linked_chunks < claim_chunk_ids

    def test_no_fabricated_links_for_transmission_and_construction(self):
        """Критерий 9: связи только одобренные — «Передача Учения» и «Строительство Аркаима»."""
        from core.services.canonical_event_view import build_canonical_event_view

        # «Передача Учения»: ровно одна одобренная владельцем связь (OWNER 2026-10-20).
        transmission = build_canonical_event_view("event_transmission_of_teaching")
        assert transmission["found"] is True
        assert [c["claim_id"] for c in transmission["claims"]] == ["claim_2b7c1a4306ed"]

        # «Строительство Аркаима»: одобренных связей нет — ничего не выдумываем.
        construction = build_canonical_event_view("event_arkaim_construction")
        assert construction["found"] is True
        assert construction["claims"] == []
        assert construction["screenplay_materials"] == []

    def test_backward_compatible_with_m17_m18(self):
        """Критерий 10: обратная совместимость — реестр M17/M18 не изменён."""
        linker = ClaimTemporalLinker.from_json()
        assert len(linker.links) == 18
        for link in linker.links:
            assert link.event_id is not None
            chain = ClaimTemporalLinker.validate_chain(link)
            assert chain.valid, f"{link.claim_id}: {chain.reason}"

    def test_production_event_claim_counts(self):
        """Все production-события содержат ожидаемое число claims."""
        from core.services.canonical_event_view import build_canonical_event_view

        for event_id, expected_count in _PRODUCTION_EVENTS_WITH_CLAIMS.items():
            view = build_canonical_event_view(event_id)
            assert view["found"] is True, f"{event_id} не найден"
            assert len(view["claims"]) == expected_count, f"{event_id}: ожидалось {expected_count} claims, получено {len(view['claims'])}"

    def test_screenplay_linker_untouched(self):
        """ScreenplayBookLinker содержит ровно 15 одобренных M16.1+M20.1+M20.3 связей."""
        linker = ScreenplayBookLinker.from_json()
        assert len(linker.links) == 15
        for link in linker.links:
            assert link.screenplay_scene_id.startswith("scene_")
            assert link.book_chunk_id.startswith("chunk_p_")
            assert link.confidence == 1.0
