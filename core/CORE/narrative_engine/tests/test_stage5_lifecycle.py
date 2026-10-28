"""Этап 5: персистентность гипотез/сценариев + apply-gate WorldDelta.

Проверяется:
  - ``HypothesisStore``/``ScenarioStore`` переживают перезапуск;
  - accept/reject/supersede — только явные решения, без auto-apply;
  - ``WorldDelta.apply_delta()`` без ``accepted=True`` мир не меняет;
  - apply-gate блокирует невозможные дельты (3 правила + ContradictionDetector).
"""

import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[4] / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from narrative_engine.branch_manager import ScenarioStore
from narrative_engine.hypothesis_generator import (
    Hypothesis,
    HypothesisStore,
    HypothesisType,
)
from narrative_engine.planners.cause_effect import CauseEffectNode, CauseEffectTree
from narrative_engine.scenario_modeler import ScenarioBranch
from narrative_engine.world_delta import (
    CharacterDelta,
    TimelineDelta,
    WorldDelta,
    WorldDeltaApplyGate,
)
from narrative_engine.world_explorer import WorldExplorer
from narrative_engine.world_model import WorldModel


def _world_model() -> WorldModel:
    return WorldModel(
        {
            "epochs": [
                {"id": "past", "name": "Past", "name_ru": "Прошлое", "order": 1},
                {"id": "future", "name": "Future", "name_ru": "Будущее", "order": 2},
            ],
            "locations": [
                {"id": "loc_a", "name": "A", "name_ru": "А"},
                {"id": "loc_b", "name": "B", "name_ru": "Б"},
            ],
        }
    )


def _hypothesis(hypothesis_id: str = "hyp_0001", title: str = "Тест") -> Hypothesis:
    return Hypothesis(
        id=hypothesis_id,
        title=title,
        title_ru=title,
        hypothesis_type=HypothesisType.PROACTIVE,
        epoch="past",
    )


def _valid_tree() -> CauseEffectTree:
    return CauseEffectTree(
        root="Событие",
        nodes=[CauseEffectNode(id="n0", type="cause", description="Причина", order=0)],
    )


class TestHypothesisStorePersistence:
    def test_proposed_hypothesis_survives_restart(self, tmp_path: Path):
        store = HypothesisStore(tmp_path)
        store.propose(_hypothesis())

        assert (tmp_path / "hypotheses" / "hyp_0001.json").exists()

        reopened = HypothesisStore(tmp_path)
        record = reopened.get("hyp_0001")
        assert record is not None
        assert record.status == "proposed"
        assert reopened.hypothesis("hyp_0001").title_ru == "Тест"

    def test_accept_survives_restart(self, tmp_path: Path):
        HypothesisStore(tmp_path).propose(_hypothesis())
        decision = HypothesisStore(tmp_path).accept("hyp_0001")
        assert decision.ok
        assert decision.record.status == "accepted"

        after_restart = HypothesisStore(tmp_path).get("hyp_0001")
        assert after_restart is not None
        assert after_restart.status == "accepted"
        assert after_restart.decided_at is not None

    def test_reject_is_final(self, tmp_path: Path):
        store = HypothesisStore(tmp_path)
        store.propose(_hypothesis())
        assert store.reject("hyp_0001", reason="не по канону").ok

        assert not store.accept("hyp_0001").ok
        assert store.get("hyp_0001").status == "rejected"
        assert store.get("hyp_0001").decision_note == "не по канону"

    def test_supersede_keeps_history(self, tmp_path: Path):
        store = HypothesisStore(tmp_path)
        store.propose(_hypothesis("hyp_0001"))
        store.propose(_hypothesis("hyp_0002", title="Замена"))

        decision = store.supersede("hyp_0001", "hyp_0002", reason="уточнение")
        assert decision.ok
        record = store.get("hyp_0001")
        assert record.status == "superseded"
        assert record.superseded_by == "hyp_0002"
        assert store.get("hyp_0002").status == "proposed"

    def test_supersede_requires_target(self, tmp_path: Path):
        store = HypothesisStore(tmp_path)
        store.propose(_hypothesis())
        assert not store.supersede("hyp_0001", "").ok

    def test_next_id_continues_after_restart(self, tmp_path: Path):
        HypothesisStore(tmp_path).propose(_hypothesis("hyp_0007"))
        assert HypothesisStore(tmp_path).next_id() == "hyp_0008"

    def test_duplicate_fingerprint_does_not_reset_accepted_status(self, tmp_path: Path):
        store = HypothesisStore(tmp_path)
        store.propose(_hypothesis("hyp_0001"))
        store.accept("hyp_0001")

        duplicate = store.propose(_hypothesis("hyp_0002", title="Тест"))
        assert duplicate.record_id == "hyp_0001"
        assert duplicate.status == "accepted"
        assert store.count() == 1


class TestScenarioStorePersistence:
    def _branch(self) -> ScenarioBranch:
        return ScenarioBranch(
            id="hyp_0001_conservative",
            hypothesis_id="hyp_0001",
            title="Conservative",
            title_ru="Консервативная ветвь",
            branch_type="conservative",
            cause_effect_tree=_valid_tree(),
            world_delta=WorldDelta(
                event_description="Событие",
                total_changes=1,
                impact_magnitude=0.3,
                summary="ok",
            ),
        )

    def test_branch_survives_restart(self, tmp_path: Path):
        ScenarioStore(tmp_path).propose(self._branch())
        assert (tmp_path / "scenarios" / "hyp_0001_conservative.json").exists()

        reopened = ScenarioStore(tmp_path)
        branch = reopened.scenario("hyp_0001_conservative")
        assert branch is not None
        assert branch.title_ru == "Консервативная ветвь"
        assert branch.cause_effect_tree.root == "Событие"
        assert branch.world_delta.total_changes == 1

    def test_accept_and_supersede(self, tmp_path: Path):
        store = ScenarioStore(tmp_path)
        store.propose(self._branch())
        assert store.accept("hyp_0001_conservative").ok
        assert ScenarioStore(tmp_path).get("hyp_0001_conservative").status == "accepted"

        assert store.supersede(
            "hyp_0001_conservative",
            "hyp_0002_conservative",
        ).ok
        assert store.get("hyp_0001_conservative").status == "superseded"


class TestWorldDeltaApplyGate:
    def test_explicit_accept_is_required(self, tmp_path: Path):
        wm = _world_model()
        delta = WorldDelta(
            event_description="Событие",
            total_changes=1,
            impact_magnitude=0.4,
        )

        result = delta.apply_delta(
            wm,
            accepted=False,
            world_model_path=tmp_path / "WORLD_MODEL.json",
        )

        assert not result.ok
        assert result.reason == "explicit_accept_required"
        assert "applied_world_deltas" not in wm.data
        assert not (tmp_path / "WORLD_MODEL.json").exists()

    def test_causal_rule_blocks_delta_without_cause(self):
        delta = WorldDelta(total_changes=1, impact_magnitude=0.4, summary="без причины")
        report = WorldDeltaApplyGate(_world_model()).check(delta, epoch_id="past")

        assert not report.is_valid
        assert any("причин" in v for v in report.violations)

    def test_spatial_rule_blocks_two_locations(self):
        delta = WorldDelta(
            event_description="Перемещение",
            total_changes=2,
            impact_magnitude=0.4,
            character_deltas=[
                CharacterDelta(
                    character_name="Герой",
                    after="loc_a",
                    change_type="location_change",
                ),
                CharacterDelta(
                    character_name="Герой",
                    after="loc_b",
                    change_type="location_change",
                ),
            ],
        )
        report = WorldDeltaApplyGate(_world_model()).check(delta, epoch_id="past")

        assert not report.is_valid
        assert any("двух" in v or "несколько локаций" in v for v in report.violations)

    def test_temporal_rule_blocks_future_epoch(self):
        delta = WorldDelta(
            event_description="Влияние",
            total_changes=1,
            impact_magnitude=0.4,
            timeline_deltas=[TimelineDelta(affected_epochs=["future"])],
        )
        report = WorldDeltaApplyGate(_world_model()).check(delta, epoch_id="past")

        assert not report.is_valid
        assert any("будущую эпоху" in v for v in report.violations)

    def test_contradiction_detector_blocks_hard_contradiction(self):
        bad_tree = CauseEffectTree(
            root="Событие",
            nodes=[
                CauseEffectNode(
                    id="n0",
                    type="effect",
                    description="Следствие",
                    order=1,
                    depends_on=["n1"],
                ),
                CauseEffectNode(
                    id="n1",
                    type="effect",
                    description="Причина-следствие",
                    order=0,
                ),
            ],
            temporal_order=["n0", "n1"],
        )
        delta = WorldDelta(
            event_description="Событие",
            total_changes=1,
            impact_magnitude=0.4,
        )

        report = WorldDeltaApplyGate(_world_model()).check(
            delta,
            epoch_id="past",
            tree=bad_tree,
        )

        assert not report.is_valid
        assert report.tree_checked
        assert report.contradiction_hard_count >= 1

    def test_valid_delta_applies_and_persists_only_after_accept(self, tmp_path: Path):
        wm = _world_model()
        delta = WorldDelta(
            event_description="Событие",
            total_changes=1,
            impact_magnitude=0.4,
            summary="допустимое изменение",
        )
        save_path = tmp_path / "WORLD_MODEL.json"

        result = delta.apply_delta(
            wm,
            accepted=True,
            epoch_id="past",
            tree=_valid_tree(),
            world_model_path=save_path,
        )

        assert result.ok
        assert result.applied
        assert result.world_model_saved
        assert len(wm.data["applied_world_deltas"]) == 1
        assert (
            wm.data["applied_world_deltas"][0]["provenance_category"]
            == "SYSTEM_INTERPRETATION"
        )

        reloaded = WorldModel.load(save_path, use_cache=False)
        assert len(reloaded.data["applied_world_deltas"]) == 1
        assert (
            reloaded.data["applied_world_deltas"][0]["delta_id"]
            == result.applied_delta_id
        )


class TestWorldExplorerLifecycle:
    def test_hypothesis_accept_survives_new_explorer(self, tmp_path: Path):
        wm = _world_model()
        explorer = WorldExplorer(
            wm,
            hypothesis_store=HypothesisStore(tmp_path),
            scenario_store=ScenarioStore(tmp_path),
        )

        hypotheses = explorer.get_hypotheses("past", limit=3)
        assert hypotheses
        hypothesis_id = hypotheses[0].id

        assert explorer.accept_hypothesis(hypothesis_id).ok

        # Новый explorer = имитация перезапуска сервера (in-memory состояние сброшено).
        reopened = WorldExplorer(
            wm,
            hypothesis_store=HypothesisStore(tmp_path),
            scenario_store=ScenarioStore(tmp_path),
        )
        reopened_ids = [h.id for h in reopened.get_hypotheses("past", limit=10)]

        assert hypothesis_id in reopened_ids
        record = reopened.hypothesis_record(hypothesis_id)
        assert record is not None
        assert record.status == "accepted"
