# -*- coding: utf-8 -*-
"""
Stage 4A targeted tests — пилотный цикл GAP → Stage 2 → World Model → Recheck.

Покрытие:
- provenance-фильтр: HYPOTHESIS/RECONSTRUCTION не попадают в description;
- релевантность: нерелевантные цитаты отбрасываются, скоуп claims по entity;
- детерминированная компоновка description (arch facts + книжные цитаты);
- relationships только из book_connection-claims с сохранением provenance;
- tie-break неоднозначных имён (region_/geo_ дубликаты) — короче id;
- provenance не апгрейдится (UNKNOWN -> фактическая категория; EXTERNAL не тронут);
- writer: точечная запись, .bak, round-trip UTF-8, идемпотентность;
- run_gap_pilot: dry-run не мутирует; apply закрывает missing_description;
- Stage 2 вызывается явно и его падение не роняет цикл;
- автоматики нет: модуль ничего не запускает при импорте.
"""

import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "core" / "CORE"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.services.world_gap_detector import (  # noqa: E402
    GapSeverity,
    GapType,
    WorldGap,
)
from core.services.world_gap_pilot import (  # noqa: E402
    apply_plan_to_world_model,
    build_gap_closure_plan,
    compose_description,
    plan_provenance,
    plan_relationships,
    run_gap_pilot,
)
from narrative_engine.world_model_ext import WorldModelExt  # noqa: E402


# ─────────────────────────────────────────────────────────────────
# Синтетические заглушки (аналог Stage 3 тестов)
# ─────────────────────────────────────────────────────────────────


class FakeRelationGraph:
    def __init__(self, links: dict[str, tuple[int, int]] | None = None):
        self._links = links or {}

    def get_entity_context(self, entity_id: str) -> dict:
        out_c, in_c = self._links.get(entity_id, (0, 0))
        return {
            "entity_id": entity_id,
            "outgoing": [],
            "incoming": [],
            "outgoing_count": out_c,
            "incoming_count": in_c,
        }

    def get_stats(self) -> dict:
        return {
            "total_relations": sum(o + i for o, i in self._links.values()),
            "by_type": {},
            "entities_with_relations": len(self._links),
        }


class FakeEngine:
    def __init__(self, graph: FakeRelationGraph | None = None):
        self._relation_graph = graph or FakeRelationGraph()


class FakeWorldModel:
    def __init__(self, categories: dict[str, list[dict]]):
        self._categories = categories

    def get_categories(self) -> list[str]:
        return list(self._categories.keys())

    def get_category(self, category: str) -> list[dict]:
        return self._categories.get(category.lower(), [])

    def get_entity(self, category: str, entity_id: str) -> dict | None:
        for item in self.get_category(category):
            if item.get("id") == entity_id:
                return item
        return None


def make_gap(**overrides) -> WorldGap:
    params = dict(
        entity_id="geo_мехенго",
        entity_name="Мехенго",
        category="geography",
        gap_type=GapType.MISSING_DESCRIPTION.value,
        severity=GapSeverity.HIGH.value,
        description="d",
        reason="r",
        can_auto_stage2=True,
    )
    params.update(overrides)
    return WorldGap(**params)


def arch_claim(field: str, text: str, category: str = "EXTERNAL_SOURCE") -> dict:
    return {
        "text": text,
        "source_ref": f"ARCHAEOLOGY.json:мехенго:{field}",
        "provenance": {"category": category},
    }


def book_claim(chunk: str, text: str, category: str = "AUTHOR_CANON") -> dict:
    return {
        "text": text,
        "source_ref": f"book:{chunk}",
        "provenance": {"category": category},
    }


def context_with(**groups) -> dict:
    return {"entity_id": "geo_мехенго", "entity_name": "Мехенго", **groups}


GEO_FIXTURE = [
    {
        "id": "geo_мехенго",
        "name": "Мехенго",
        "category": "geography",
        "description": "",
        "properties": {},
        "relationships": [],
        "source": "GEOGRAPHY.json",
        "confidence": 0.8,
        "provenance_category": "EXTERNAL_SOURCE",
        "provenance_notes": "Картографические данные",
        "source_level": "HISTORICAL",
    },
    {
        "id": "geo_синташта",
        "name": "Синташта",
        "category": "geography",
        "description": "x",
        "properties": {},
        "relationships": [],
        "source": "GEOGRAPHY.json",
        "provenance_category": "EXTERNAL_SOURCE",
    },
    {
        "id": "region_синташта",
        "name": "Синташта",
        "category": "geography",
        "description": "x",
        "properties": {},
        "relationships": [],
        "source": "GEOGRAPHY.json",
        "provenance_category": "EXTERNAL_SOURCE",
    },
]


# ─────────────────────────────────────────────────────────────────
# Проvenance-фильтр и релевантность
# ─────────────────────────────────────────────────────────────────


class TestCollectClaims:
    def test_hypothesis_and_reconstruction_excluded_from_description(self):
        gap = make_gap()
        contexts = [
            context_with(
                archaeology_claims=[
                    arch_claim("location", "Республика Коми"),
                    arch_claim(
                        "book_connection",
                        "Потенциально связанное с гиперборейской культурой",
                        category="HYPOTHESIS",
                    ),
                ]
            )
        ]
        plan = build_gap_closure_plan(gap, contexts, FakeWorldModel({"geography": GEO_FIXTURE}), stamp="t")
        reasons = {e["reason"] for e in plan.excluded_claims}
        assert "category_not_projectable_into_description" in reasons
        assert all(
            e["category"] != "HYPOTHESIS" or e["reason"].startswith("category_not") or e["reason"] == "hypothesis_relation_not_written"
            for e in plan.excluded_claims
        )
        if plan.description:
            assert "гиперборейской" not in plan.description.text

    def test_irrelevant_book_quotes_excluded(self):
        gap = make_gap()
        contexts = [
            context_with(
                book_claims=[
                    book_claim("chunk_p_0001_x", "Мне необходимо быть в другом месте."),
                    book_claim("chunk_p_0002_x", "Мехенго стоял на берегу реки."),
                ]
            )
        ]
        plan = build_gap_closure_plan(gap, contexts, FakeWorldModel({"geography": GEO_FIXTURE}), stamp="t")
        assert plan.description is not None
        assert "Мехенго стоял" in plan.description.text
        assert "другом месте" not in plan.description.text
        not_rel = [e for e in plan.excluded_claims if e["reason"] == "not_relevant_to_entity"]
        assert len(not_rel) == 1

    def test_no_relevant_material_flagged(self):
        gap = make_gap()
        contexts = [context_with(book_claims=[book_claim("chunk_p_0001_x", "Совсем иная фраза без имени.")])]
        plan = build_gap_closure_plan(gap, contexts, FakeWorldModel({"geography": GEO_FIXTURE}), stamp="t")
        assert plan.description is None
        assert "no_relevant_projectable_claims" in plan.reasons


# ─────────────────────────────────────────────────────────────────
# Компоновка description
# ─────────────────────────────────────────────────────────────────


class TestComposeDescription:
    def test_structured_arch_facts_order_and_no_book_connection(self):
        gap = make_gap()
        relevant = [
            ("archaeology_claims", arch_claim("significance", "Мехенго показывает, что Север был заселён.")),
            ("archaeology_claims", arch_claim("facts.age", "age: Древнейшее поселение")),
            ("archaeology_claims", arch_claim("dating", "~7000-5000 до н.э.")),
            ("archaeology_claims", arch_claim("location", "Республика Коми, Россия")),
            (
                "archaeology_claims",
                arch_claim("book_connection", "HYPOTHESIS text", category="HYPOTHESIS"),
            ),
        ]
        plan = compose_description(gap, relevant)
        assert plan is not None
        text = plan.text
        assert text.index("Республика Коми") < text.index("Датировка")
        assert text.index("Датировка") < text.index("Древнейшее поселение")
        assert "HYPOTHESIS text" not in text
        assert "ARCHAEOLOGY.json:мехенго:location" in plan.source_refs

    def test_book_quotes_verbatim_capped(self):
        gap = make_gap()
        relevant = [
            ("book_claims", book_claim("chunk_p_0001_x", "Мехенго первый.")),
            ("book_claims", book_claim("chunk_p_0002_x", "Мехенго второй.")),
            ("book_claims", book_claim("chunk_p_0003_x", "Мехенго третий.")),
        ]
        plan = compose_description(gap, relevant)
        assert plan is not None
        assert "«Мехенго первый.»" in plan.text
        assert "«Мехенго третий.»" not in plan.text

    def test_none_without_material(self):
        assert compose_description(make_gap(), []) is None


# ─────────────────────────────────────────────────────────────────
# Планировщик связей
# ─────────────────────────────────────────────────────────────────


class TestPlanRelationships:
    def test_reconstruction_book_connection_resolves_shorter_id(self):
        """Дубль имён 'Синташта' (region_/geo_) -> tie-break: короче id."""
        gap = make_gap()
        wm = FakeWorldModel({"geography": GEO_FIXTURE})
        relevant = [
            (
                "archaeology_claims",
                arch_claim(
                    "book_connection",
                    "Культура, сменившая Синташту — потенциально результат миграции.",
                    category="RECONSTRUCTION",
                ),
            )
        ]
        plans = plan_relationships(gap, relevant, wm, excluded=[])
        assert len(plans) == 1
        rel = plans[0]
        assert rel.target_id == "geo_синташта"
        assert rel.provenance_category == "RECONSTRUCTION"
        assert rel.source_ref.endswith(":book_connection")
        assert rel.type == "historical"

    def test_hypothesis_book_connection_not_written(self):
        gap = make_gap()
        wm = FakeWorldModel({"geography": GEO_FIXTURE})
        relevant = [
            (
                "archaeology_claims",
                arch_claim(
                    "book_connection",
                    "Потенциально связанное с гиперборейской культурой",
                    category="HYPOTHESIS",
                ),
            )
        ]
        excluded: list = []
        plans = plan_relationships(gap, relevant, wm, excluded=excluded)
        assert plans == []
        assert any(e["reason"] == "hypothesis_relation_not_written" for e in excluded)

    def test_no_existing_entity_mentioned(self):
        gap = make_gap()
        wm = FakeWorldModel({"geography": GEO_FIXTURE})
        relevant = [
            (
                "archaeology_claims",
                arch_claim(
                    "book_connection",
                    "Связь с несуществующей сущностью Нарния",
                    category="RECONSTRUCTION",
                ),
            )
        ]
        excluded: list = []
        plans = plan_relationships(gap, relevant, wm, excluded=excluded)
        assert plans == []
        assert any(e["reason"] == "no_existing_entity_mentioned_in_claim" for e in excluded)

    def test_word_form_resolves_by_word_stem(self):
        """Склонённая словоформа имени («Синташту» — вин. п.) разрешается по стеме."""
        from core.services.world_gap_pilot import _resolve_relationship_target

        gap = make_gap()
        wm = FakeWorldModel({"geography": GEO_FIXTURE})
        target, reason = _resolve_relationship_target("Культура, сменившая Синташту.", gap, wm)
        assert target == "geo_синташта"
        assert reason == "resolved_by_word_stem_in_claim"

    def test_exact_name_has_priority_over_word_stem(self):
        from core.services.world_gap_pilot import _resolve_relationship_target

        gap = make_gap()
        wm = FakeWorldModel({"geography": GEO_FIXTURE})
        # Точное имя в тексте -> exact-уровень даже при наличии словоформы.
        target, reason = _resolve_relationship_target("Синташта и Синташту.", gap, wm)
        assert target == "geo_синташта"
        assert reason == "resolved_by_exact_name_in_claim"


# ─────────────────────────────────────────────────────────────────
# Provenance-план
# ─────────────────────────────────────────────────────────────────


class TestPlanProvenance:
    def test_unknown_upgraded_to_dominant_claim_category(self):
        from core.services.world_gap_pilot import PlannedDescription

        entity = {
            "provenance_category": "UNKNOWN",
            "provenance_notes": "Пустое описание",
        }
        desc = PlannedDescription(
            text="t",
            source_refs=["book:chunk_p_0138_a2bbe6afad73"],
            categories=["AUTHOR_CANON", "AUTHOR_CANON"],
        )
        new_cat, note = plan_provenance(make_gap(), entity, desc, [], "stamp")
        assert new_cat == "AUTHOR_CANON"
        assert "Stage 4A pilot" in note
        assert "Пустое описание" not in note  # notes не трогаем здесь

    def test_existing_category_not_upgraded(self):
        from core.services.world_gap_pilot import PlannedDescription

        entity = {"provenance_category": "EXTERNAL_SOURCE"}
        desc = PlannedDescription(text="t", source_refs=["r"], categories=["AUTHOR_CANON"])
        new_cat, note = plan_provenance(make_gap(), entity, desc, [], "stamp")
        assert new_cat is None

    def test_unknown_without_material_falls_back_to_system_interpretation(self):
        entity = {"provenance_category": ""}
        new_cat, note = plan_provenance(make_gap(), entity, None, [], "stamp")
        assert new_cat == "SYSTEM_INTERPRETATION"


# ─────────────────────────────────────────────────────────────────
# Writer (точечная запись)
# ─────────────────────────────────────────────────────────────────


def write_fixture_wm(tmp_path: Path) -> Path:
    wm_dir = tmp_path / "WORLD_MODEL"
    wm_dir.mkdir(parents=True, exist_ok=True)
    (wm_dir / "GEOGRAPHY.json").write_text(
        json.dumps(copy.deepcopy(GEO_FIXTURE), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return wm_dir


class TestApplyWriter:
    def test_apply_writes_description_and_backup(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap()
        contexts = [
            context_with(
                archaeology_claims=[
                    arch_claim("location", "Республика Коми, Россия"),
                    arch_claim("dating", "~7000-5000 до н.э."),
                ]
            )
        ]
        wm = WorldModelExt(wm_dir)
        plan = build_gap_closure_plan(gap, contexts, wm, stamp="t")
        assert plan.description is not None

        result = apply_plan_to_world_model(gap, plan, world_model_dir=wm_dir)
        assert result["written"] is True
        assert "description" in result["changed_fields"]
        assert Path(result["backup"]).exists()

        data = json.loads((wm_dir / "GEOGRAPHY.json").read_text(encoding="utf-8"))
        entity = next(e for e in data if e["id"] == "geo_мехенго")
        assert "Республика Коми" in entity["description"]
        # Другие сущности не тронуты.
        sintashta = next(e for e in data if e["id"] == "geo_синташта")
        assert sintashta["description"] == "x"
        # Round-trip UTF-8 без ASCII-экранирования.
        raw = (wm_dir / "GEOGRAPHY.json").read_text(encoding="utf-8")
        assert "Республика Коми" in raw

    def test_apply_idempotent_and_no_overwrite(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap()
        contexts = [context_with(book_claims=[book_claim("chunk_p_0001_x", "Мехенго стоял на берегу.")])]
        wm = WorldModelExt(wm_dir)
        plan = build_gap_closure_plan(gap, contexts, wm, stamp="t")
        r1 = apply_plan_to_world_model(gap, plan, world_model_dir=wm_dir)
        assert r1["written"] is True

        # Повторный запуск: description уже есть — не перезаписывается.
        wm2 = WorldModelExt(wm_dir)
        plan2 = build_gap_closure_plan(gap, contexts, wm2, stamp="t2")
        assert plan2.description is None
        assert "description_already_present_not_overwritten" in plan2.reasons
        r2 = apply_plan_to_world_model(gap, plan2, world_model_dir=wm_dir)
        assert r2["written"] is False

        data = json.loads((wm_dir / "GEOGRAPHY.json").read_text(encoding="utf-8"))
        entity = next(e for e in data if e["id"] == "geo_мехенго")
        assert entity["description"].count("Мехенго стоял") == 1

    def test_relationships_dedup_on_reapply(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap()
        contexts = [
            context_with(
                archaeology_claims=[
                    arch_claim("location", "Республика Коми"),
                    arch_claim(
                        "book_connection",
                        "Культура, сменившая Синташту.",
                        category="RECONSTRUCTION",
                    ),
                ]
            )
        ]
        wm = WorldModelExt(wm_dir)
        plan = build_gap_closure_plan(gap, contexts, wm, stamp="t")
        assert len(plan.relationships) == 1
        apply_plan_to_world_model(gap, plan, world_model_dir=wm_dir)

        # Симуляция повторного запуска: убрать description, оставить связь.
        path = wm_dir / "GEOGRAPHY.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        entity = next(e for e in data if e["id"] == "geo_мехенго")
        entity["description"] = ""
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        wm2 = WorldModelExt(wm_dir)
        plan2 = build_gap_closure_plan(gap, contexts, wm2, stamp="t2")
        apply_plan_to_world_model(gap, plan2, world_model_dir=wm_dir)
        data2 = json.loads(path.read_text(encoding="utf-8"))
        entity2 = next(e for e in data2 if e["id"] == "geo_мехенго")
        targets = [r["target_id"] for r in entity2["relationships"]]
        assert targets.count("geo_синташта") == 1


# ─────────────────────────────────────────────────────────────────
# Полный цикл run_gap_pilot
# ─────────────────────────────────────────────────────────────────


def fake_contexts() -> list[dict]:
    return [
        context_with(
            archaeology_claims=[
                arch_claim("location", "Республика Коми, Россия"),
                arch_claim("dating", "~7000-5000 до н.э."),
                arch_claim("facts.age", "age: Древнейшее поселение"),
                arch_claim("significance", "Мехенго показывает, что Север был заселён."),
            ],
            world_claims=[],
        )
    ]


class TestRunGapPilot:
    @pytest.mark.asyncio
    async def test_dry_run_never_mutates(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        before = (wm_dir / "GEOGRAPHY.json").read_bytes()
        gap = make_gap()
        stage2 = SimpleNamespace(accepted=[], review=[], rejected=[], summary="s", storage={})
        with (
            patch(
                "core.services.world_gap_pilot.stage2_expand",
                new_callable=AsyncMock,
                return_value=stage2,
            ),
            patch(
                "core.services.world_gap_pilot.gather_knowledge_core_context",
                return_value=fake_contexts(),
            ),
        ):
            report = await run_gap_pilot(
                gap,
                apply=False,
                world_model_dir=wm_dir,
                engine=FakeEngine(),
                wm=WorldModelExt(wm_dir),
            )
        assert report["applied"] == {"written": False, "reason": "dry_run_apply_false"}
        assert report["plan"]["description"] is not None
        assert (wm_dir / "GEOGRAPHY.json").read_bytes() == before

    @pytest.mark.asyncio
    async def test_apply_closes_missing_description(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap()
        stage2 = SimpleNamespace(accepted=[], review=[], rejected=[], summary="s", storage={})
        with (
            patch(
                "core.services.world_gap_pilot.stage2_expand",
                new_callable=AsyncMock,
                return_value=stage2,
            ),
            patch(
                "core.services.world_gap_pilot.gather_knowledge_core_context",
                return_value=fake_contexts(),
            ),
        ):
            report = await run_gap_pilot(
                gap,
                apply=True,
                world_model_dir=wm_dir,
                engine=FakeEngine(),
                wm=WorldModelExt(wm_dir),
            )
        assert report["applied"]["written"] is True
        assert "missing_description" in {g["gap_type"] for g in report["gaps_before"]}
        assert "missing_description" not in {g["gap_type"] for g in report["gaps_after"]}
        assert "missing_description" in report["gaps_closed"]
        assert "kc_world_claims_after" in report

    @pytest.mark.asyncio
    async def test_stage2_called_explicitly_with_gap_entity(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap()
        stage2 = SimpleNamespace(accepted=[1], review=[2], rejected=[3], summary="s", storage={"items_saved": 1})
        with (
            patch(
                "core.services.world_gap_pilot.stage2_expand",
                new_callable=AsyncMock,
                return_value=stage2,
            ) as mock_expand,
            patch(
                "core.services.world_gap_pilot.gather_knowledge_core_context",
                return_value=fake_contexts(),
            ),
        ):
            report = await run_gap_pilot(
                gap,
                apply=False,
                world_model_dir=wm_dir,
                engine=FakeEngine(),
                wm=WorldModelExt(wm_dir),
            )
        mock_expand.assert_awaited_once()
        kwargs = mock_expand.call_args.kwargs
        assert "Мехенго" in kwargs["question"]
        assert kwargs["related_entities"] == [{"entity_id": "geo_мехенго", "name": "Мехенго"}]
        assert report["stage2"]["accepted"] == 1
        assert report["stage2"]["review"] == 1
        assert report["stage2"]["rejected"] == 1

    @pytest.mark.asyncio
    async def test_stage2_failure_does_not_break_cycle(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap()
        with (
            patch(
                "core.services.world_gap_pilot.stage2_expand",
                new_callable=AsyncMock,
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "core.services.world_gap_pilot.gather_knowledge_core_context",
                return_value=fake_contexts(),
            ),
        ):
            report = await run_gap_pilot(
                gap,
                apply=True,
                world_model_dir=wm_dir,
                engine=FakeEngine(),
                wm=WorldModelExt(wm_dir),
            )
        assert report["stage2"].get("error")
        assert report["applied"]["written"] is True

    @pytest.mark.asyncio
    async def test_non_stage2_gap_skips_expansion(self, tmp_path):
        wm_dir = write_fixture_wm(tmp_path)
        gap = make_gap(
            gap_type=GapType.UNKNOWN_PROVENANCE.value,
            severity=GapSeverity.HIGH.value,
            can_auto_stage2=False,
        )
        with (
            patch(
                "core.services.world_gap_pilot.stage2_expand",
                new_callable=AsyncMock,
            ) as mock_expand,
            patch(
                "core.services.world_gap_pilot.gather_knowledge_core_context",
                return_value=fake_contexts(),
            ),
        ):
            report = await run_gap_pilot(
                gap,
                apply=False,
                world_model_dir=wm_dir,
                engine=FakeEngine(),
                wm=WorldModelExt(wm_dir),
            )
        mock_expand.assert_not_called()
        assert report["stage2"] == {
            "ran": False,
            "reason": "gap_not_stage2_eligible",
        }


class TestPilotIsExplicitOnly:
    """Пилот не должен попасть в автоматический контур приложения.

    Stage 4A пишет в World Model только при apply=True; сам apply=True —
    решение владельца. Поэтому пилот не импортируется ни одним роутом и не
    вызывается из /book/ask: единственная точка входа — явный вызов из кода.
    """

    def test_no_route_imports_world_gap_pilot(self):
        routes_dir = Path(__file__).resolve().parent.parent / "core" / "routes"
        offenders = []
        for path in routes_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "world_gap_pilot" in text:
                offenders.append(path.name)
        assert not offenders, "роуты не должны импортировать пилот: %s" % offenders

    def test_ask_pipeline_does_not_import_world_gap_pilot(self):
        book_py = Path(__file__).resolve().parent.parent / "core" / "routes" / "book.py"
        assert "world_gap_pilot" not in book_py.read_text(encoding="utf-8")

    def test_apply_defaults_to_false(self):
        import inspect

        sig = inspect.signature(run_gap_pilot)
        assert sig.parameters["apply"].default is False
