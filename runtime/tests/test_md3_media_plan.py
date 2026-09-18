"""MD-3.1 MediaPlan v0 — unit-тесты контракта/Builder.

Инварианты (ADR_MEDIA_PLAN_V0 + MD3_PRE_IMPLEMENTATION_AUDIT §4):
  1. MediaPlan — домен без execution-полей (BANNED ∩ fields = ∅);
  2. Builder строит план ТОЛЬКО из canonical Scene Context;
  3. provenance/temporal/source_refs наследуются 1:1 из scene_extras;
  4. lineage: derived/regenerate обязателен parent; is_derived;
  5. immutable-план: regenerate — новый план, старый не мутируется;
  6. video-поля — проекция VideoContext-типов;

  8. to_dict — JSON-сериализуемое представление (None-safe);
  9. audio — extension point: builder НЕ строит audio-планы.

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_media_plan.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from media_plan import (  # noqa: E402
    BANNED_FIELDS,
    PLAN_VERSION,
    MediaKind,
    MediaPlan,
    MediaPlanBuilder,
    verify_no_execution_fields,
)
from media_plan.schemas import (  # noqa: E402
    ContinuityRef,
    PlanLineage,
)
from visual.scene_context import (  # noqa: E402
    ProvenanceRef,
    SourceRefs,
    TemporalSceneRef,
    extend_visual_context,
)
from visual.video_context import (  # noqa: E402
    CameraMovement,
    CharacterMotion,
    TransitionSpec,
)
from visual.visual_context import VisualContext  # noqa: E402


# ── Фикстуры ──


def make_ctx(
    epoch: str = "",
    provenance: list[ProvenanceRef] | None = None,
    scene_id: str = "s1",
    chapter: int = 1,
) -> VisualContext:
    """Canonical Scene Context с MD-2-расширениями (как в MD-2-тестах)."""
    ctx = VisualContext()
    temporal = (
        TemporalSceneRef(epoch_id=epoch, name_ru="Эпоха теста", provenance=provenance or [])
        if epoch
        else None
    )
    extend_visual_context(
        ctx,
        temporal=temporal,
        source_refs=SourceRefs(
            scene_id=scene_id,
            chapter=chapter,
            character_ids=["hero"],
            location_id="loc_arkaim",
        ),
    )
    return ctx


@pytest.fixture
def builder() -> MediaPlanBuilder:
    return MediaPlanBuilder()


# ── 1. Инвариант: домен без execution-семантики ──


class TestNoExecutionFields:
    def test_banned_intersect_fields_empty(self):
        violations = verify_no_execution_fields()
        assert violations == [], f"execution-утечка в MediaPlan: {violations}"

    def test_banned_fields_frozen_contract(self):
        # Контракт запрета заморожен (ADR Decision 3 + owner decision 3 + MP-F1 quality).
        for field in (
            "model", "checkpoint", "steps", "cfg", "sampler", "seed",
            "workflow", "node_graph", "provider", "backend", "comfyui",
            "loras", "denoise", "quality",
        ):
            assert field in BANNED_FIELDS, f"запрет ослаблен: {field}"

    def test_banned_not_in_serialized_plan(self):
        plan = MediaPlanBuilder().build_image_plan(make_ctx(epoch="e1"))
        data = json.dumps(plan.to_dict(), ensure_ascii=False)
        for banned in ("\"model\"", "\"steps\"", "\"seed\"", "\"cfg\"", "\"sampler\"",
                        "\"workflow\"", "\"provider\"", "\"backend\"", "\"quality\"",
                        "\"checkpoint\"", "\"node_graph\""):
            assert banned not in data, f"execution-поле {banned} в сериализованном плане"

    def test_media_plan_direct_construction_has_no_banned_field(self):
        # Прямое конструирование плана не позволяет задать execution-поле.
        with pytest.raises(Exception):
            MediaPlan(model="sdxl")  # type: ignore[call-arg]


# ── 2. Builder из canonical Scene Context ──


class TestBuilderFromSceneContext:
    def test_image_plan_basic(self, builder):
        plan = builder.build_image_plan(make_ctx())
        assert plan.media_kind == MediaKind.IMAGE
        assert plan.plan_id.startswith("plan_")
        assert plan.plan_version == PLAN_VERSION == "0.1.0"
        assert plan.prompt and plan.structured_prompt
        assert plan.lineage.derivation == "initial"
        assert plan.lineage.parent_plan_id is None

    def test_scene_context_only_source(self, builder):
        # Builder принимает только VisualContext (+scene_extras): dict-сцены
        # и VisualAsset как вход — вне контракта (typing-уровень: вызов
        # с другим типом ломается на атрибутах ctx.*).
        plan = builder.build_image_plan(make_ctx(scene_id="sx", chapter=7))
        assert plan.source_refs.scene_id == "sx"
        assert plan.source_refs.chapter == 7

    def test_style_override(self, builder):
        ctx = make_ctx()
        ctx.style.name = "realistic"
        plan_default = builder.build_image_plan(ctx)
        plan_override = builder.build_image_plan(ctx, style_override="watercolor")
        assert plan_default.visual_style == "realistic"
        assert plan_override.visual_style == "watercolor"

    def test_custom_prompt_replaces_text_only(self, builder):
        ctx = make_ctx()
        plan = builder.build_image_plan(ctx, custom_prompt="film shot text")
        assert plan.prompt == "film shot text"
        # structured_prompt (composer-механика) сохранён отдельно.
        assert plan.structured_prompt and plan.structured_prompt != "film shot text"
        # Смысловые поля остаются из контекста.
        assert plan.source_refs.scene_id == "s1"

    def test_without_custom_prompt_uses_composer_projection(self, builder):
        plan = builder.build_image_plan(make_ctx())
        assert plan.prompt == plan.structured_prompt

    def test_negative_constraints_from_composer(self, builder):
        plan = builder.build_image_plan(make_ctx())
        assert isinstance(plan.negative_constraints, list)
        # composer_negative рендерит базу NEGATIVE_PROMPT_DEFAULT — непусто.
        assert len(plan.negative_constraints) > 0
        assert all(isinstance(x, str) for x in plan.negative_constraints)


# ── 3. Provenance / temporal наследование ──


class TestProvenanceInheritance:
    def test_temporal_inherited_1to1(self, builder):
        refs = [ProvenanceRef(category="RECONSTRUCTION", source="canon_events", confidence=0.7)]
        plan = builder.build_image_plan(make_ctx(epoch="temporal_arkaim_era", provenance=refs))
        assert plan.temporal_context is not None
        assert plan.temporal_context.epoch_id == "temporal_arkaim_era"
        assert plan.temporal_context.provenance == refs

    def test_provenance_of_plan_equals_temporal_provenance(self, builder):
        refs = [
            ProvenanceRef(category="AUTHOR_CANON", source="book", confidence=1.0),
            ProvenanceRef(category="EXTERNAL_SOURCE", source="wiki", confidence=0.5),
        ]
        plan = builder.build_image_plan(make_ctx(epoch="e9", provenance=refs))
        assert plan.provenance == refs  # наследование 1:1 (ADR-инвариант 7)

    def test_reconstruction_epoch_yields_reconstruction_plan(self, builder):
        refs = [ProvenanceRef(category="RECONSTRUCTION", source="events", confidence=0.7)]
        plan = builder.build_image_plan(make_ctx(epoch="e_recon", provenance=refs))
        categories = [p.category for p in plan.provenance]
        assert "RECONSTRUCTION" in categories  # RECONSTRUCTION-эпоха → RECONSTRUCTION-план

    def test_no_epoch_no_temporal(self, builder):
        plan = builder.build_image_plan(make_ctx(epoch=""))
        assert plan.temporal_context is None
        assert plan.provenance == []

    def test_plan_does_not_invent_provenance(self, builder):
        # План не выдумывает provenance: без эпохи — пусто.
        plan = builder.build_image_plan(make_ctx())
        assert plan.provenance == []
        assert plan.temporal_context is None

    def test_source_refs_reference_only(self, builder):
        plan = builder.build_image_plan(make_ctx())
        sr = plan.source_refs
        # Идентификаторы, не копии описаний (MD-2-инвариант).
        assert sr.scene_id == "s1"
        assert sr.character_ids == ["hero"]
        assert sr.location_id == "loc_arkaim"
        assert not hasattr(sr, "title") and not hasattr(sr, "description")


# ── 4-5. Lineage ──


class TestLineage:
    def test_initial_plan_has_no_parent(self, builder):
        plan = builder.build_image_plan(make_ctx())
        assert plan.lineage.parent_plan_id is None
        assert plan.lineage.derivation == "initial"
        assert not plan.lineage.is_derived

    def test_regenerate_references_parent(self, builder):
        ctx = make_ctx()
        first = builder.build_image_plan(ctx)
        second = builder.build_image_plan(
            ctx, parent_plan_id=first.plan_id, derivation="regenerate"
        )
        assert second.lineage.parent_plan_id == first.plan_id
        assert second.lineage.derivation == "regenerate"
        assert second.lineage.is_derived
        assert second.plan_id != first.plan_id

    def test_regenerate_does_not_mutate_parent(self, builder):
        ctx = make_ctx()
        first = builder.build_image_plan(ctx)
        first_id_before = first.plan_id
        builder.build_image_plan(ctx, parent_plan_id=first.plan_id, derivation="regenerate")
        assert first.plan_id == first_id_before  # immutable-паттерн MD-2
        assert first.lineage.parent_plan_id is None  # родитель остался initial

    def test_lineage_is_not_execution_metadata(self):
        # PlanLineage не содержит storage/execution-полей.
        lineage_fields = set(PlanLineage.model_fields.keys())
        assert lineage_fields == {"parent_plan_id", "derivation", "created_from"}

    def test_created_from_marks_source_class(self, builder):
        plan = builder.build_image_plan(make_ctx(), created_from="film_shot")
        assert plan.lineage.created_from == "film_shot"


# ── 6. Video-план ──


class TestVideoPlan:
    def test_video_plan_fields(self, builder):
        plan = builder.build_video_plan(make_ctx(), duration_sec=5.0, fps=30)
        assert plan.media_kind == MediaKind.VIDEO
        assert plan.duration_sec == 5.0
        assert plan.fps == 30

    def test_video_motion_projection(self, builder):
        plan = builder.build_video_plan(
            make_ctx(),
            camera_motion=CameraMovement(type="slow_dolly_in", speed="slow"),
            character_actions=[CharacterMotion(character_id="hero", action="walks", emotion="grief")],
            transitions=[TransitionSpec(type="crossfade", duration_sec=0.5)],
        )
        assert plan.motion.camera_motion == "slow_dolly_in"
        assert plan.motion.character_actions[0]["character_id"] == "hero"
        assert plan.motion.character_actions[0]["emotion"] == "grief"
        assert plan.motion.transitions[0]["type"] == "crossfade"

    def test_video_continuity_ref(self, builder):
        plan = builder.build_video_plan(
            make_ctx(), continuity=ContinuityRef(project_id="p1", shot_index=2)
        )
        assert plan.temporal_consistency is not None
        assert plan.temporal_consistency.project_id == "p1"
        assert plan.temporal_consistency.shot_index == 2

    def test_video_sequence_default_empty(self, builder):
        plan = builder.build_video_plan(make_ctx())
        assert plan.sequence == []


# ── 7. Сериализация ──


class TestSerialization:
    def test_to_dict_json_serializable(self, builder):
        plan = builder.build_image_plan(make_ctx(epoch="e1", provenance=[
            ProvenanceRef(category="AUTHOR_CANON", source="book", confidence=1.0)
        ]))
        data = json.dumps(plan.to_dict(), ensure_ascii=False)
        assert isinstance(data, str) and len(data) > 0

    def test_to_dict_temporal_none_safe(self, builder):
        plan = builder.build_image_plan(make_ctx())
        d = plan.to_dict()
        assert d["temporal_context"] is None

    def test_to_dict_video_fields(self, builder):
        plan = builder.build_video_plan(make_ctx(), duration_sec=4.0, fps=30)
        d = plan.to_dict()
        assert d["media_kind"] == "video"
        assert d["duration_sec"] == 4.0
        assert d["fps"] == 30

    def test_plan_version_stamped(self, builder):
        assert builder.build_image_plan(make_ctx()).plan_version == "0.1.0"


# ── 9. Audio — extension point ──


class TestAudioExtensionPoint:
    def test_builder_has_no_audio_method(self):
        # Схема AudioPlan не определяется; builder не строит audio-планы.
        assert not hasattr(MediaPlanBuilder, "build_audio_plan")

    def test_media_kind_audio_reserved_only(self):
        # Значение зарезервировано, но план с ним не строится builder'ом.
        assert MediaKind.AUDIO == "audio"
        # Прямое конструирование — НЕ canonical путь (builder не выпускает audio).

    def test_audio_fields_not_defined(self):
        # В контракте нет audio-специфичных полей (схема не определена).
        fields = set(MediaPlan.model_fields.keys())
        for audio_field in ("audio", "audio_plan", "voice", "music", "speech"):
            assert audio_field not in fields


# ── Schema-файл (SCHEMAS/MEDIA_PLAN.schema.json) ──


class TestSchemaFile:
    def test_schema_file_exists_and_valid_json(self):
        path = Path(__file__).resolve().parent.parent.parent / "SCHEMAS" / "MEDIA_PLAN.schema.json"
        assert path.exists(), "SCHEMAS/MEDIA_PLAN.schema.json не создан"
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["title"] == "MEDIA_PLAN"
        assert schema["required"] == ["plan_id", "plan_version", "media_kind", "prompt"]

    def test_schema_bans_execution_properties(self):
        path = Path(__file__).resolve().parent.parent.parent / "SCHEMAS" / "MEDIA_PLAN.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        props = set(schema["properties"].keys())
        for banned in ("model", "checkpoint", "steps", "cfg", "sampler", "seed",
                       "workflow", "node_graph", "provider", "backend", "quality"):
            assert banned not in props, f"execution-свойство {banned} в JSON-Schema"

    def test_serialized_plan_matches_schema_contract(self, builder):
        # Структурная сверка: ключи to_dict покрыты schema-properties
        # (или известными dataclass-подключами).
        plan = builder.build_image_plan(make_ctx(epoch="e1", provenance=[
            ProvenanceRef(category="HYPOTHESIS", source="x", confidence=0.4)
        ]))
        data = plan.to_dict()
        schema_path = Path(__file__).resolve().parent.parent.parent / "SCHEMAS" / "MEDIA_PLAN.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema_props = set(schema["properties"].keys())
        for key in data.keys():
            assert key in schema_props, f"поле {key} плана отсутствует в JSON-Schema"
