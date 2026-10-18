"""Continuity (Studio Phase 1): связность планов, сцен и эпизодов.

Offline (сеть не используется). Два уровня:
  - unit-тесты чистых функций studio.continuity (детерминированные);
  - интеграционные тесты маршрутов /studio/scenes/{id}/continuity,
    /studio/continuity/decisions, /studio/{session_id}/continuity/match-context.

Покрытые сценарии:
  1. Нет сопоставимых данных → «проверка не выполнена», без догадок.
  2. Согласованные соседние сцены → consistent.
  3. Смена локации/времени → намеренное отличие (info), не ложное предупреждение.
  4. Противоречие внешности персонажа при одинаковой локации → mismatch.
  5. Разный свет/палитра у соседних планов одной сцены → mismatch.
  6. Решение режиссёра закрывает отличие (waived) и переживает перезагрузку;
     при изменении утверждённого кадра решение устаревает.
  7. Кросс-эпизодная связь (кандидат по meaning_tags) — без ложных предупреждений.

Запуск (из runtime/):
  python -m pytest tests/test_studio_continuity.py -v
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

# Индексы сцен генома: 0..5 — глава 1, 6..9 — главы 2..5.
SCENE_MEETING = "test_meeting"  # глава 1, index 4, location "Аркаим", chars [Велик, Учитель]
SCENE_PREV = "conflict_кали_юга_сати_юга"  # глава 1, index 3, location "граница миров"
SCENE_CH2 = "meaning_auto_ch2"  # глава 2, общие meaning_tags с ch1/ch3/ch4/ch5

from studio.continuity import ACTION_APPLIED, RELATION_ADJACENT, applied_link_key  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def isolated_session_store(tmp_path, monkeypatch):
    from studio import store as studio_store_mod

    monkeypatch.setattr(studio_store_mod, "_DB_PATH", tmp_path / "studio_continuity_test.db")
    yield


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from core.main import app

    return TestClient(app)


def _run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _make_session(user_id: str, scene_id: str, *, shots: bool = True, approved: str | None = None) -> str:
    from studio.scenario_schemas import ScenarioShot, VideoScenario
    from studio.store import StudioStore

    async def _inner():
        store = StudioStore()
        try:
            session = await store.create_session(user_id=user_id, title="continuity-тест", chapter=1, scene_id=scene_id)
            scenario = None
            if shots:
                scenario = VideoScenario(
                    scenario_id="sc_cont",
                    scene_id=scene_id,
                    title="Сцена связности",
                    shots=[
                        ScenarioShot(shot_id="s1", order=0, lighting_note="warm side light"),
                        ScenarioShot(shot_id="s2", order=1, lighting_note="warm side light"),
                    ],
                )
            await store.create_version(
                session_id=session.session_id,
                version_number=1,
                video_scenario=scenario,
                created_by="system",
                note="initial",
            )
            if approved:
                await store.set_approved_image(session.session_id, approved)
            return session.session_id
        finally:
            await store.close()

    return _run(_inner())


def _vc(char_id="Велик", name="Велик", appearance="tall, grey beard", time_of_day="dawn", lighting="east, low", palette=("gold",)):
    """Минимальный визуальный контекст (SimpleNamespace) для unit-тестов."""
    return SimpleNamespace(
        characters=[SimpleNamespace(character_id=char_id, name=name, appearance_summary=appearance, clothing="robe")],
        environment=SimpleNamespace(time_of_day=time_of_day, season="late summer", weather="clear"),
        lighting=SimpleNamespace(direction=lighting, color="golden"),
        location=SimpleNamespace(palette=list(palette)),
    )


def _scene(scene_id: str, chapter: int, location: str = "", characters=None, tags=None) -> dict:
    return {
        "scene_id": scene_id,
        "chapter": chapter,
        "title": scene_id,
        "location": location,
        "characters": characters or [],
        "meaning_tags": tags or [],
    }


# ── Unit: снимок и сравнение ─────────────────────────────────────


class TestSnapshotUnit:
    def test_snapshot_marks_only_known_fields(self):
        from studio.continuity import build_scene_snapshot

        snap = build_scene_snapshot(_scene("s1", 1, location="Аркаим"), order_global=0)
        assert "location" in snap.known_fields
        assert "time_of_day" not in snap.known_fields
        assert snap.time_of_day == ""  # неизвестное не выдумывается

    def test_snapshot_enriched_by_visual_context(self):
        from studio.continuity import build_scene_snapshot

        snap = build_scene_snapshot(
            _scene("s1", 1, location="Аркаим", characters=["Велик"]),
            order_global=0,
            visual_context=_vc(),
        )
        assert snap.time_of_day == "dawn"
        assert snap.lighting_direction == "east, low"
        assert snap.characters[0].appearance == "tall, grey beard"
        assert snap.provenance["time_of_day"] == "visual_context"


class TestCompareScenesUnit:
    def test_unchecked_when_nothing_to_compare(self):
        """Сценарий 1: нет сопоставимых данных → проверка не выполнена."""
        from studio.continuity import STATUS_UNCHECKED, build_scene_snapshot, compare_scenes

        a = build_scene_snapshot(_scene("a", 1), order_global=0)
        b = build_scene_snapshot(_scene("b", 1), order_global=1)
        link = compare_scenes(a, b)
        assert link.status == STATUS_UNCHECKED
        assert link.findings == []

    def test_consistent_when_same_conditions(self):
        """Сценарий 2: согласованные сцены → consistent."""
        from studio.continuity import STATUS_CONSISTENT, build_scene_snapshot, compare_scenes

        a = build_scene_snapshot(_scene("a", 1, location="Аркаим", characters=["Велик"]), order_global=0, visual_context=_vc())
        b = build_scene_snapshot(_scene("b", 1, location="Аркаим", characters=["Велик"]), order_global=1, visual_context=_vc())
        link = compare_scenes(a, b)
        assert link.status == STATUS_CONSISTENT
        assert link.findings == []

    def test_location_change_is_info_not_warning(self):
        """Сценарий 3: смена локации — намеренное отличие (info), не ложное предупреждение."""
        from studio.continuity import STATUS_CONSISTENT, build_scene_snapshot, compare_scenes

        a = build_scene_snapshot(_scene("a", 1, location="Аркаим"), order_global=0)
        b = build_scene_snapshot(_scene("b", 1, location="граница миров"), order_global=1)
        link = compare_scenes(a, b)
        assert link.status == STATUS_CONSISTENT
        assert [f.field for f in link.findings] == ["location"]
        assert link.findings[0].severity == "info"
        assert link.findings[0].kind == "change"

    def test_character_appearance_mismatch_is_warning(self):
        """Сценарий 4: разная внешность персонажа при одинаковой локации → mismatch."""
        from studio.continuity import STATUS_MISMATCH, build_scene_snapshot, compare_scenes

        a = build_scene_snapshot(_scene("a", 1, location="Аркаим", characters=["Велик"]), order_global=0, visual_context=_vc(appearance="tall, grey beard"))
        b = build_scene_snapshot(_scene("b", 1, location="Аркаим", characters=["Велик"]), order_global=1, visual_context=_vc(appearance="short, black hair"))
        link = compare_scenes(a, b)
        assert link.status == STATUS_MISMATCH
        assert any(f.field == "character_appearance" and f.severity == "warning" for f in link.findings)

    def test_cross_episode_candidate_is_not_alarm(self):
        """Сценарий 7: кросс-эпизодный кандидат не поднимает ложное предупреждение."""
        from studio.continuity import STATUS_CONSISTENT, build_scene_snapshot, compare_scenes, mark_candidate

        a = build_scene_snapshot(_scene("a", 2, location="Аркаим", characters=["Велик"]), order_global=6, visual_context=_vc(appearance="tall, grey beard"))
        b = build_scene_snapshot(_scene("b", 3, location="Аркаим", characters=["Велик"]), order_global=7, visual_context=_vc(appearance="short"))
        link = compare_scenes(a, b, relation="cross_episode", certainty="candidate", reason="tag")
        mark_candidate(link)
        assert link.certainty == "candidate"
        assert link.status == STATUS_CONSISTENT
        assert all(f.severity == "info" for f in link.findings)


class TestCompareShotsUnit:
    def test_lighting_mismatch_between_adjacent_shots(self):
        """Сценарий 5: разный свет у соседних планов одной сцены → mismatch."""
        from studio.continuity import STATUS_MISMATCH, build_shot_snapshot, compare_shots
        from studio.scenario_schemas import ScenarioShot

        a = ScenarioShot(shot_id="s1", order=0, lighting_note="warm side light")
        b = ScenarioShot(shot_id="s2", order=1, lighting_note="cold backlight")
        link = compare_shots(build_shot_snapshot(a), build_shot_snapshot(b))
        assert link.status == STATUS_MISMATCH
        assert link.findings[0].field == "lighting"

    def test_palette_mismatch_between_adjacent_shots(self):
        from studio.continuity import STATUS_MISMATCH, build_shot_snapshot, compare_shots
        from studio.scenario_schemas import ScenarioShot

        a = ScenarioShot(shot_id="s1", order=0, palette_override=["gold"])
        b = ScenarioShot(shot_id="s2", order=1, palette_override=["blue"])
        link = compare_shots(build_shot_snapshot(a), build_shot_snapshot(b))
        assert link.status == STATUS_MISMATCH
        assert any(f.field == "palette" for f in link.findings)

    def test_unchecked_when_no_comparable_fields(self):
        from studio.continuity import STATUS_UNCHECKED, build_shot_snapshot, compare_shots
        from studio.scenario_schemas import ScenarioShot

        a = ScenarioShot(shot_id="s1", order=0, shot_type="wide")
        b = ScenarioShot(shot_id="s2", order=1, shot_type="close")
        link = compare_shots(build_shot_snapshot(a), build_shot_snapshot(b))
        assert link.status == STATUS_UNCHECKED


class TestDecisionsUnit:
    def test_decision_waives_and_reports_stale(self):
        """Сценарий 6 (unit): решение закрывает связь; при смене кадра — устаревает."""
        from studio.continuity import (
            STATUS_MISMATCH,
            STATUS_WAIVED,
            ContinuityDecision,
            ContinuityFinding,
            ContinuityLink,
            apply_decisions,
            make_basis,
        )

        link = ContinuityLink(
            link_id="adjacent_scenes:a->b",
            link_key="adjacent_scenes:a->b",
            status=STATUS_MISMATCH,
        )
        link.findings = [ContinuityFinding(field="location", severity="info", message="x")]
        basis = make_basis(scene_id="b", art_direction_revision=2, from_approved="img_old", to_approved="img_new")
        link.basis = basis

        decision = ContinuityDecision(decision_id="d1", link_key=link.link_key, basis=dict(basis))
        apply_decisions([link], {link.link_key: decision})
        assert link.status == STATUS_WAIVED
        assert decision.stale is False

        # Новый утверждённый кадр меняет basis → решение устарело, связь снова открыта.
        link.status = STATUS_MISMATCH
        basis2 = make_basis(scene_id="b", art_direction_revision=2, from_approved="img_old", to_approved="img_newer")
        link.basis = basis2
        stale_decision = ContinuityDecision(decision_id="d1", link_key=link.link_key, basis=dict(basis))
        apply_decisions([link], {link.link_key: stale_decision})
        assert stale_decision.stale is True
        assert link.status == STATUS_MISMATCH

    def test_clip_boundary_contract_uses_declared_frames(self):
        from studio.continuity import build_scene_snapshot, clip_boundary_for

        a = build_scene_snapshot(_scene("a", 1, location="Аркаим"), order_global=0, session=SimpleNamespace(session_id="x", approved_image_asset_id="img_a"))
        b = build_scene_snapshot(_scene("b", 1, location="Аркаим"), order_global=1, session=SimpleNamespace(session_id="y", approved_image_asset_id="img_b"))
        cb = clip_boundary_for(a, b)
        assert cb.end_frame_asset_id == "img_a"
        assert cb.start_frame_asset_id == "img_b"
        assert cb.status == "declared"


# ── Интеграция: маршрут continuity ───────────────────────────────


class TestContinuityRoute:
    def test_unknown_scene_404(self, client, isolated_session_store):
        resp = client.get("/studio/scenes/нет_такой_сцены/continuity", params={"with_context": False})
        assert resp.status_code == 404

    def test_scene_without_session_is_unchecked(self, client, isolated_session_store):
        """Сценарий 1 (маршрут): нет сессии → планы не проверены, отчёт не падает."""
        resp = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scene"]["has_scenario"] is False
        assert any("плана" in lim for lim in data["limitations"])

    def test_location_change_is_info_and_not_mismatch(self, client, isolated_session_store):
        """Сценарий 3 (маршрут): смена локации с предыдущей сценой — info, не mismatch."""
        resp = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        adjacent = next(link for link in data["links"] if link["relation"] == "adjacent_scenes")
        assert adjacent["from_ref"] == SCENE_PREV
        location_findings = [f for f in adjacent["findings"] if f["field"] == "location"]
        assert location_findings and location_findings[0]["severity"] == "info"
        assert adjacent["status"] != "mismatch"

    def test_within_scene_shot_links_present(self, client, isolated_session_store):
        _make_session("test-user", SCENE_MEETING)
        resp = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False})
        data = resp.json()["data"]
        shot_links = [link for link in data["links"] if link["relation"] == "shots_within_scene"]
        assert len(shot_links) == 1  # два плана → одна связь

    def test_cross_episode_candidate_link(self, client, isolated_session_store):
        """Сценарий 7 (маршрут): кандидат по meaning_tags, без ложного предупреждения."""
        resp = client.get(f"/studio/scenes/{SCENE_CH2}/continuity", params={"with_context": False})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        cross = [link for link in data["links"] if link["relation"] == "cross_episode"]
        assert cross, "ожидалась хотя бы одна кросс-эпизодная связь-кандидат"
        assert all(link["certainty"] == "candidate" for link in cross)
        assert all(link["status"] != "mismatch" for link in cross)

    def test_scene_route_not_shadowed(self, client, isolated_session_store):
        # /studio/scenes/{id}/continuity не должен попадать в /studio/{session_id}.
        resp = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False})
        assert resp.status_code == 200
        assert "links" in resp.json()["data"]

    def test_with_context_does_not_crash(self, client, isolated_session_store):
        # Визуальный контекст может быть недоступен — маршрут всё равно отвечает 200.
        resp = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity")
        assert resp.status_code == 200, resp.text


# ── Интеграция: решения режиссёра ────────────────────────────────


class TestDecisionRoute:
    def test_decision_persists_and_waives(self, client, isolated_session_store):
        """Сценарий 6 (маршрут): решение закрывает связь и переживает перезагрузку."""
        data = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False}).json()["data"]
        adjacent = next(link for link in data["links"] if link["relation"] == "adjacent_scenes")

        resp = client.post(
            "/studio/continuity/decisions",
            json={"link_key": adjacent["link_key"], "note": "смена локации по сюжету", "basis": adjacent["basis"]},
        )
        assert resp.status_code == 200, resp.text
        decision_id = resp.json()["data"]["decision_id"]

        # Перечитать отчёт → связь закрыта режиссёром.
        data2 = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False}).json()["data"]
        adjacent2 = next(link for link in data2["links"] if link["relation"] == "adjacent_scenes")
        assert adjacent2["status"] == "waived"
        assert adjacent2["decision"]["decision_id"] == decision_id
        assert adjacent2["decision"]["stale"] is False

        # Удаление решения возвращает связь в исходное состояние.
        del_resp = client.delete(f"/studio/continuity/decisions/{decision_id}")
        assert del_resp.status_code == 200
        data3 = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False}).json()["data"]
        adjacent3 = next(link for link in data3["links"] if link["relation"] == "adjacent_scenes")
        assert adjacent3["status"] != "waived"

    def test_stale_decision_does_not_waive(self, client, isolated_session_store):
        data = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False}).json()["data"]
        adjacent = next(link for link in data["links"] if link["relation"] == "adjacent_scenes")

        # Решение с устаревшим отпечатком (иной утверждённый кадр) — не закрывает связь.
        stale_basis = dict(adjacent["basis"])
        stale_basis["to_approved"] = "img_другой_кадр"
        client.post("/studio/continuity/decisions", json={"link_key": adjacent["link_key"], "basis": stale_basis})

        data2 = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False}).json()["data"]
        adjacent2 = next(link for link in data2["links"] if link["relation"] == "adjacent_scenes")
        assert adjacent2["decision"]["stale"] is True
        assert adjacent2["status"] != "waived"

    def test_delete_unknown_decision_404(self, client, isolated_session_store):
        resp = client.delete("/studio/continuity/decisions/cont_нет")
        assert resp.status_code == 404


# ── Интеграция: «Согласовать со сценой» ──────────────────────────


class TestMatchContextRoute:
    def test_preview_lists_constraints_without_writing(self, client, isolated_session_store):
        session_id = _make_session("test-user", SCENE_MEETING)
        resp = client.get(f"/studio/{session_id}/continuity/match-context")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["available"] is True
        assert data["from_scene_id"] == SCENE_PREV
        assert data["to_scene_id"] == SCENE_MEETING
        assert data["applied"] is False
        assert data["constraints"].get("location") == "граница миров"
        assert data["sources"].get("location")
        # предпросмотр промптов: по одному на план, исходные промпты не изменены
        assert len(data["prompt_changes"]) == 2
        assert all("before" in pc and "after" in pc for pc in data["prompt_changes"])

    def test_preview_unavailable_without_previous_scene(self, client, isolated_session_store):
        """Первая сцена главы: предыдущей сцены нет → предпросмотр недоступен, без ошибок."""
        session_id = _make_session("test-user", "conflict_гиперборея_материальный_путь_атлантиды")
        resp = client.get(f"/studio/{session_id}/continuity/match-context")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["available"] is False

    def test_preview_session_not_found_404(self, client, isolated_session_store):
        resp = client.get("/studio/session_нет/continuity/match-context")
        assert resp.status_code == 404


class TestSummaryRoute:
    def test_summary_covers_all_scenes(self, client, isolated_session_store):
        resp = client.get("/studio/continuity/summary")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["with_context"] is False
        assert SCENE_MEETING in data["scenes"]
        assert SCENE_CH2 in data["scenes"]
        entry = data["scenes"][SCENE_MEETING]
        assert set(entry) >= {"overall_status", "mismatch_count", "waived_count", "pending_count", "link_count"}

    def test_summary_reflects_waive_decision(self, client, isolated_session_store):
        _make_session("test-user", SCENE_MEETING)
        before = client.get("/studio/continuity/summary").json()["data"]["scenes"][SCENE_MEETING]
        scene = client.get(f"/studio/scenes/{SCENE_MEETING}/continuity", params={"with_context": False}).json()["data"]
        link = next(link for link in scene["links"] if link["relation"] == RELATION_ADJACENT)
        client.post("/studio/continuity/decisions", json={"link_key": link["link_key"], "basis": link["basis"]})
        after = client.get("/studio/continuity/summary").json()["data"]["scenes"][SCENE_MEETING]
        assert after["waived_count"] >= before["waived_count"]


# ── Фаза 2: применение переноса ограничений ──────────────────────


class TestApplyUnit:
    def test_transfer_constraints_uses_known_fields_only(self):
        from studio.continuity import build_scene_snapshot, transfer_constraints

        snap = build_scene_snapshot(
            _scene("prev", 1, location="Аркаим", characters=["Велик"]),
            order_global=0,
        )
        constraints, sources = transfer_constraints(snap)
        assert constraints["location"] == "Аркаим"
        assert constraints["characters"] == ["Велик"]
        assert "time_of_day" not in constraints  # неизвестное не переносится
        assert "time_of_day" not in sources
        assert sources.get("location")

    def test_find_applied_decision_respects_basis(self):
        from studio.continuity import ContinuityDecision, find_applied_decision, make_apply_basis

        scene_id = "s1"
        applied = ContinuityDecision(
            decision_id="cont_a",
            link_key=applied_link_key(scene_id),
            action=ACTION_APPLIED,
            constraints={"location": "Аркаим"},
            basis=make_apply_basis(scene_id=scene_id, art_direction_revision=3),
        )
        fresh, stale = find_applied_decision([applied], scene_id, make_apply_basis(scene_id=scene_id, art_direction_revision=3))
        assert fresh is applied and stale is False
        stale_d, is_stale = find_applied_decision([applied], scene_id, make_apply_basis(scene_id=scene_id, art_direction_revision=4))
        assert stale_d is None and is_stale is True

    def test_find_applied_decision_ignores_waived(self):
        from studio.continuity import ContinuityDecision, find_applied_decision, make_apply_basis

        scene_id = "s1"
        waived = ContinuityDecision(
            decision_id="cont_w",
            link_key=applied_link_key(scene_id),
            action="waived",
            basis=make_apply_basis(scene_id=scene_id, art_direction_revision=0),
        )
        d, stale = find_applied_decision([waived], scene_id, make_apply_basis(scene_id=scene_id, art_direction_revision=0))
        assert d is None and stale is False


class TestApplyRoute:
    def test_apply_persists_and_match_context_reports_applied(self, client, isolated_session_store):
        session_id = _make_session("test-user", SCENE_MEETING)
        resp = client.post(f"/studio/{session_id}/continuity/apply", json={"note": "подогнать под сцену"})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["applied"] is True
        assert data["constraints"].get("location") == "граница миров"
        assert data["decision"]["action"] == ACTION_APPLIED
        assert data["decision"]["constraints"].get("location") == "граница миров"

        ctx = client.get(f"/studio/{session_id}/continuity/match-context").json()["data"]
        assert ctx["applied"] is True
        assert ctx["applied_stale"] is False
        assert ctx["applied_decision"]["decision_id"] == data["decision"]["decision_id"]

    def test_apply_requires_previous_scene(self, client, isolated_session_store):
        session_id = _make_session("test-user", "conflict_гиперборея_материальный_путь_атлантиды")
        resp = client.post(f"/studio/{session_id}/continuity/apply", json={})
        assert resp.status_code == 409

    def test_apply_session_not_found_404(self, client, isolated_session_store):
        resp = client.post("/studio/session_нет/continuity/apply", json={})
        assert resp.status_code == 404

    def test_revoke_removes_applied(self, client, isolated_session_store):
        session_id = _make_session("test-user", SCENE_MEETING)
        client.post(f"/studio/{session_id}/continuity/apply", json={})
        resp = client.delete(f"/studio/{session_id}/continuity/apply")
        assert resp.status_code == 200
        assert resp.json()["data"]["revoked"] is True
        ctx = client.get(f"/studio/{session_id}/continuity/match-context").json()["data"]
        assert ctx["applied"] is False

    def test_prepared_update_uses_applied_continuity(self, client, isolated_session_store):
        session_id = _make_session("test-user", SCENE_MEETING)
        before = client.post(f"/studio/{session_id}/prepared-updates", json={"shot_id": "s1"}).json()["data"]
        assert before["continuity"]["applied"] is False
        assert "continuity:" not in before["resolved"]["resolved_prompt"]

        client.post(f"/studio/{session_id}/continuity/apply", json={})
        after = client.post(f"/studio/{session_id}/prepared-updates", json={"shot_id": "s1"}).json()["data"]
        assert after["continuity"]["applied"] is True
        assert "continuity:" in after["resolved"]["resolved_prompt"]
        assert "граница миров" in after["resolved"]["resolved_prompt"]

    def test_applied_becomes_stale_after_rules_change(self, client, isolated_session_store):
        session_id = _make_session("test-user", SCENE_MEETING)
        client.post(f"/studio/{session_id}/continuity/apply", json={})

        # Меняем общие правила фильма → revision растёт → перенос устаревает.
        ad = client.get("/studio/art-direction").json()["data"]
        ad["reference_asset_ids"] = list(ad.get("reference_asset_ids") or []) + ["ref_new_x"]
        put = client.put("/studio/art-direction", json=ad)
        assert put.status_code == 200, put.text

        ctx = client.get(f"/studio/{session_id}/continuity/match-context").json()["data"]
        assert ctx["applied"] is False
        assert ctx["applied_stale"] is True

        prepared = client.post(f"/studio/{session_id}/prepared-updates", json={"shot_id": "s1"}).json()["data"]
        assert prepared["continuity"]["applied"] is False
        assert "continuity:" not in prepared["resolved"]["resolved_prompt"]
