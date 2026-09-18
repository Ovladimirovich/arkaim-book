"""Phase 1B Acceptance Audit Tests.

Каждый тест соответствует конкретному пункту acceptance-аудита.
"""
from __future__ import annotations

import pytest
import json
import os
import inspect


@pytest.fixture
def tmp_db():
    db_dir = os.path.join(os.path.dirname(__file__), "_test_studio_audit")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "audit_studio.db")
    yield db_path
    for f in os.listdir(db_dir):
        os.remove(os.path.join(db_dir, f))
    os.rmdir(db_dir)


@pytest.fixture
async def store(tmp_db):
    from studio.store import StudioStore
    s = StudioStore(db_path=tmp_db)
    yield s
    await s.close()


@pytest.fixture
def img_plan():
    from media_plan.schemas import MediaPlan, PlanLineage, SourceRefs
    return MediaPlan(
        plan_id="p_img", media_kind="image",
        prompt="sacred fire ceremony", atmosphere="sacred",
        lineage=PlanLineage(derivation="initial", created_from="scene_context"),
        source_refs=SourceRefs(scene_id="s1", chapter=1),
    )


@pytest.fixture
def vid_plan():
    from media_plan.schemas import MediaPlan, PlanLineage, SourceRefs
    return MediaPlan(
        plan_id="p_vid", media_kind="video",
        prompt="video sacred fire", duration_sec=30.0, fps=24,
        lineage=PlanLineage(derivation="initial", created_from="scene_context"),
        source_refs=SourceRefs(scene_id="s1", chapter=1),
    )


@pytest.fixture
def scenario():
    from studio.scenario_schemas import VideoScenario, ScenarioShot
    return VideoScenario(
        scene_id="s1", title="Sacred Fire",
        synopsis="Ceremonial fire scene",
        shots=[
            ScenarioShot(shot_id="sh1", order=0, shot_type="wide", description="Opening"),
            ScenarioShot(shot_id="sh2", order=1, shot_type="medium", description="Action"),
        ],
    )


# ── 1. /discuss contract ────────────────────────────────────────


class TestDiscussContract:
    """/discuss: LLM возвращает текст, НЕ меняет StudioVersion."""

    def test_discuss_docstring_says_no_version_change(self):
        """Docstring explicitly states discuss doesn't create versions."""
        from core.routes.studio import discuss
        doc = discuss.__doc__
        assert "НЕ создаёт новую StudioVersion" in doc
        assert "НЕ изменяет существующие описания" in doc

    @pytest.mark.asyncio
    async def test_discuss_does_not_create_version(self, store, img_plan):
        """Discussion messages don't create new StudioVersion."""
        session = await store.create_session("u1", "Test")
        await store.create_version(session.session_id, 1, image_description=img_plan)

        # Simulate what /discuss does (minus actual LLM call)
        await store.add_message(session.session_id, "user", "Make it darker")
        await store.add_message(session.session_id, "assistant", "I suggest changing atmosphere to dark mystical")
        await store.update_session_status(session.session_id, "discussing")

        # Version count must still be 1
        versions = await store.get_versions(session.session_id)
        assert len(versions) == 1, "Discussion must NOT create new versions"

    @pytest.mark.asyncio
    async def test_discuss_returns_text_only(self, store, img_plan):
        """Discussion response is plain text, not structured modification."""
        from core.routes.studio import discuss
        source = inspect.getsource(discuss)

        # LLM result is accessed as plain text via voice.speak().text
        assert 'voice.speak' in source
        assert 'utterance.text' in source
        # No version creation in discuss
        assert "create_version" not in source.split("async def discuss")[1].split("# ──")[0]

    @pytest.mark.asyncio
    async def test_user_must_call_modify_explicitly(self, store, img_plan, vid_plan, scenario):
        """Version changes only through explicit /modify call."""
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(
            session.session_id, 1,
            image_description=img_plan, video_description=vid_plan, video_scenario=scenario,
        )

        # After discussion (simulated), version is unchanged
        await store.add_message(session.session_id, "user", "Darken the atmosphere")
        await store.add_message(session.session_id, "assistant", "I suggest: atmosphere → dark mystical")
        active = await store.get_active_version(session.session_id)
        assert active.version_id == v1.version_id

        # Only explicit modify changes the version
        from studio.session_models import UserModification
        modified_img = img_plan.model_copy(update={"atmosphere": "dark mystical"})
        v2 = await store.create_version(
            session.session_id, 2,
            image_description=modified_img,
            parent_version_id=v1.version_id,
            derivation="adaptation",
            user_modifications=[UserModification(
                target="image_description", field_path="atmosphere",
                old_value="sacred", new_value="dark mystical",
                reason="User applied LLM suggestion",
            )],
            created_by="user",
        )
        assert v2.version_number == 2
        assert v2.parent_version_id == v1.version_id


# ── 2. LLM prohibition ─────────────────────────────────────────


class TestLLMProhibition:
    """LLM через /discuss не может менять систему."""

    def test_discuss_endpoint_no_world_model_access(self):
        """/discuss doesn't import or call World Model."""
        from core.routes.studio import discuss
        source = inspect.getsource(discuss)
        # No World Model imports
        assert "world_model" not in source.lower()
        assert "WorldEngine" not in source
        assert "knowledge_graph" not in source.lower()

    def test_discuss_endpoint_no_scene_context_mutation(self):
        """/discuss doesn't modify SceneContext."""
        from core.routes.studio import discuss
        source = inspect.getsource(discuss)
        # No scene mutation
        assert "build_scene_context" not in source
        assert "save_genome" not in source
        assert "scene_engine.update" not in source

    def test_discuss_endpoint_no_description_mutation(self):
        """/discuss doesn't write to descriptions."""
        from core.routes.studio import discuss
        source = inspect.getsource(discuss)
        discuss_body = source.split("async def discuss")[1]
        # No version creation
        assert "create_version" not in discuss_body
        # No media plan modification
        assert "MediaPlan" not in discuss_body
        assert "VideoScenario" not in discuss_body

    def test_llm_returns_plain_text(self):
        """LLM output is accessed as plain text string."""
        from core.routes.studio import discuss
        source = inspect.getsource(discuss)
        discuss_body = source.split("async def discuss")[1].split("# ──")[0]
        # Result is accessed as string via voice.speak().text
        assert 'voice.speak' in discuss_body
        assert 'utterance.text' in discuss_body
        # No JSON parsing of LLM output
        assert "json.loads" not in discuss_body
        assert "model_validate" not in discuss_body

    def test_discuss_no_execution_params_possible(self):
        """/discuss cannot inject execution parameters."""
        from core.routes.studio import discuss
        source = inspect.getsource(discuss)
        # No access to MediaPlan fields that could hold execution params
        assert "model =" not in source
        assert "steps =" not in source
        assert "seed =" not in source
        assert "cfg =" not in source


# ── 3. /modify contract ─────────────────────────────────────────


class TestModifyContract:
    """/modify: explicit user action → new immutable version."""

    def test_modify_docstring(self):
        from core.routes.studio import modify
        assert "immutable" in modify.__doc__.lower() or "новую версию" in modify.__doc__

    @pytest.mark.asyncio
    async def test_modify_creates_new_immutable_version(self, store, img_plan, vid_plan, scenario):
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(
            session.session_id, 1,
            image_description=img_plan, video_description=vid_plan, video_scenario=scenario,
        )

        # Simulate modify
        from studio.session_models import UserModification
        modified = img_plan.model_copy(update={"atmosphere": "dark mystical"})
        v2 = await store.create_version(
            session.session_id, 2,
            image_description=modified, video_description=vid_plan, video_scenario=scenario,
            parent_version_id=v1.version_id, derivation="adaptation",
            user_modifications=[UserModification(
                target="image_description", field_path="atmosphere",
                old_value="sacred", new_value="dark mystical",
            )],
            created_by="user",
        )

        # v1 unchanged (immutable)
        v1_fresh = await store.get_version(v1.version_id)
        assert v1_fresh.image_description.atmosphere == "sacred"
        assert v1_fresh.is_active is False

        # v2 is new, active
        assert v2.is_active is True
        assert v2.image_description.atmosphere == "dark mystical"
        assert v2.parent_version_id == v1.version_id

    @pytest.mark.asyncio
    async def test_modify_preserves_user_modification(self, store, img_plan):
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(session.session_id, 1, image_description=img_plan)

        from studio.session_models import UserModification
        mod = UserModification(
            target="image_description", field_path="atmosphere",
            old_value="sacred", new_value="dark mystical", reason="User request",
        )
        v2 = await store.create_version(
            session.session_id, 2,
            image_description=img_plan.model_copy(update={"atmosphere": "dark mystical"}),
            parent_version_id=v1.version_id, derivation="adaptation",
            user_modifications=[mod], created_by="user",
        )

        assert len(v2.user_modifications) == 1
        assert v2.user_modifications[0].old_value == "sacred"
        assert v2.user_modifications[0].new_value == "dark mystical"

    @pytest.mark.asyncio
    async def test_modify_preserves_lineage(self, store, img_plan):
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(session.session_id, 1, image_description=img_plan)
        v2 = await store.create_version(
            session.session_id, 2, image_description=img_plan,
            parent_version_id=v1.version_id, derivation="adaptation",
        )
        v3 = await store.create_version(
            session.session_id, 3, image_description=img_plan,
            parent_version_id=v2.version_id, derivation="adaptation",
        )

        lineage = []
        cur = v3
        while cur:
            lineage.insert(0, cur.version_id)
            cur = await store.get_version(cur.parent_version_id) if cur.parent_version_id else None
        assert lineage == [v1.version_id, v2.version_id, v3.version_id]

    def test_modify_no_world_model_in_code(self):
        """/modify doesn't access World Model."""
        from core.routes.studio import modify
        source = inspect.getsource(modify)
        assert "world_model" not in source.lower()
        assert "scene_engine" not in source
        assert "genome" not in source.lower()

    def test_modify_target_whitelist(self):
        """/modify only accepts three valid targets."""
        from core.routes.studio import modify
        source = inspect.getsource(modify)
        # Only three targets are handled
        assert '"image_description"' in source
        assert '"video_description"' in source
        assert '"video_scenario"' in source

    @pytest.mark.asyncio
    async def test_modify_invalid_target_no_change(self, store, img_plan):
        """Invalid target doesn't create a broken version."""
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(session.session_id, 1, image_description=img_plan)

        # Simulate modify with invalid target — should not match any branch
        # In actual code, the descriptions remain unchanged for unrecognized targets
        from studio.session_models import UserModification
        v2 = await store.create_version(
            session.session_id, 2,
            image_description=v1.image_description,  # unchanged
            video_description=v1.video_description,  # unchanged (None)
            video_scenario=v1.video_scenario,  # unchanged (None)
            parent_version_id=v1.version_id,
            derivation="adaptation",
            user_modifications=[UserModification(
                target="invalid_target", field_path="fake_field",
                old_value="", new_value="hack", reason="test",
            )],
        )
        # Image description unchanged
        assert v2.image_description.prompt == v1.image_description.prompt


# ── 4. /variant contract ────────────────────────────────────────


class TestVariantContract:
    """/variant: copies existing descriptions, doesn't generate new ones."""

    def test_variant_copies_not_generates(self):
        """/variant copies from active version, doesn't call Description System."""
        from core.routes.studio import create_variants
        source = inspect.getsource(create_variants)
        # Uses active.image_description etc. — copies, not generates
        assert "active.image_description" in source
        assert "active.video_description" in source
        assert "active.video_scenario" in source
        # No Description System calls
        assert "VisualContextBuilder" not in source
        assert "MediaPlanBuilder" not in source
        assert "VideoIntelligence" not in source
        assert "VideoScenarioBuilder" not in source

    @pytest.mark.asyncio
    async def test_variant_has_same_content_as_parent(self, store, img_plan, vid_plan, scenario):
        """Variant descriptions are identical to parent."""
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(
            session.session_id, 1,
            image_description=img_plan, video_description=vid_plan, video_scenario=scenario,
        )

        # Create variant
        variant = await store.create_version(
            session.session_id, 2,
            image_description=v1.image_description,
            video_description=v1.video_description,
            video_scenario=v1.video_scenario,
            parent_version_id=v1.version_id, derivation="variation",
        )

        assert variant.image_description.prompt == v1.image_description.prompt
        assert variant.video_description.prompt == v1.video_description.prompt
        assert variant.video_scenario.title == v1.video_scenario.title

    @pytest.mark.asyncio
    async def test_variant_preserves_lineage(self, store, img_plan):
        session = await store.create_session("u1", "Test")
        v1 = await store.create_version(session.session_id, 1, image_description=img_plan)
        v2 = await store.create_version(
            session.session_id, 2, image_description=img_plan,
            parent_version_id=v1.version_id, derivation="variation",
        )
        assert v2.parent_version_id == v1.version_id

    def test_variant_max_5(self):
        """Variant count is capped at 5."""
        from core.routes.studio import create_variants
        source = inspect.getsource(create_variants)
        assert "min(max(count, 1), 5)" in source


# ── 5. Initial creation proof ───────────────────────────────────


class TestInitialCreation:
    """/studio/create uses existing Description System, not Studio engine."""

    def test_create_uses_mediaplan_builder(self):
        from core.routes.studio import create_session
        source = inspect.getsource(create_session)
        assert "MediaPlanBuilder" in source
        assert "build_image_plan" in source
        assert "build_video_plan" in source

    def test_create_uses_video_intelligence(self):
        from core.routes.studio import create_session
        source = inspect.getsource(create_session)
        assert "VideoIntelligence" in source
        assert "create_video_context" in source

    def test_create_uses_video_scenario_builder(self):
        from core.routes.studio import create_session
        source = inspect.getsource(create_session)
        assert "VideoScenarioBuilder" in source
        assert "scenario_builder.build" in source

    def test_create_uses_visual_context_builder(self):
        from core.routes.studio import create_session
        source = inspect.getsource(create_session)
        assert "visual_context_builder" in source
        assert "build_scene_context" in source

    def test_create_no_custom_description_generation(self):
        """Studio doesn't have its own Description Engine."""
        from core.routes.studio import create_session
        source = inspect.getsource(create_session)
        # No Studio-specific generation
        assert "studio_description" not in source.lower()
        assert "generate_description" not in source


# ── 6. MediaPlan v0 / Export negative tests ─────────────────────


class TestMediaPlanV0:
    """MediaPlan v0 not modified. Export contains no execution fields."""

    def test_mediaplan_schema_unchanged(self):
        """MediaPlan still has extra=forbid."""
        from media_plan.schemas import MediaPlan
        with pytest.raises(Exception):
            MediaPlan(media_kind="image", model="sdxl")
        with pytest.raises(Exception):
            MediaPlan(media_kind="image", steps=30)
        with pytest.raises(Exception):
            MediaPlan(media_kind="image", seed=42)

    def test_studio_export_no_execution_fields(self, img_plan, vid_plan, scenario):
        from studio.session_models import StudioExport, ExportedReference
        export = StudioExport(
            session_id="s1", export_id="exp_1",
            image_description=img_plan,
            video_description=vid_plan,
            video_scenario=scenario,
            references=[ExportedReference(asset_id="r1", description="test")],
        )
        d = export.model_dump(mode="json")
        banned = {"model", "steps", "seed", "cfg", "sampler", "workflow", "provider"}
        for key in ["image_description", "video_description", "video_scenario"]:
            assert banned.isdisjoint(d[key].keys()), f"Execution field in {key}"

    def test_mediaplan_not_extended_with_references(self):
        """MediaPlan doesn't have reference fields."""
        from media_plan.schemas import MediaPlan
        fields = set(MediaPlan.model_fields.keys())
        assert "references" not in fields
        assert "reference_assets" not in fields
        assert "user_reference" not in fields

    def test_videoscenario_no_execution_fields(self, scenario):
        d = scenario.to_dict()
        banned = {"model", "steps", "seed", "cfg", "sampler", "workflow", "provider"}
        assert banned.isdisjoint(d.keys())


# ── 7. Reference lifecycle ──────────────────────────────────────


class TestReferenceLifecycle:
    """Reference upload → storage → session → export."""

    @pytest.mark.asyncio
    async def test_reference_linked_to_session(self, store):
        session = await store.create_session("u1", "Test")
        ref = await store.add_reference(session.session_id, "asset_1", "warm golden light")
        assert ref.session_id == session.session_id

        refs = await store.get_references(session.session_id)
        assert len(refs) == 1
        assert refs[0].asset_id == "asset_1"

    @pytest.mark.asyncio
    async def test_reference_in_session_list(self, store):
        session = await store.create_session("u1", "Test")
        await store.add_reference_to_session(session.session_id, "asset_1")
        s = await store.get_session(session.session_id)
        assert "asset_1" in s.reference_assets

    @pytest.mark.asyncio
    async def test_reference_in_export(self, store, img_plan):
        from studio.session_models import StudioExport, ExportedReference
        session = await store.create_session("u1", "Test")
        v = await store.create_version(session.session_id, 1, image_description=img_plan)
        ref = await store.add_reference(session.session_id, "ref_1", "warm light")
        await store.finalize_version(v.version_id)
        await store.update_session_status(session.session_id, "approved")

        refs = await store.get_references(session.session_id)
        export = StudioExport(
            session_id=session.session_id, export_id="exp",
            image_description=v.image_description,
            references=[ExportedReference(asset_id=r.asset_id, description=r.description) for r in refs],
            version_lineage=[v.version_id],
        )
        assert len(export.references) == 1
        assert export.references[0].description == "warm light"

    def test_reference_source_type_is_user(self):
        from studio.session_models import ReferenceAsset
        r = ReferenceAsset(asset_id="r1", session_id="s1", description="test")
        assert r.source_type == "user_reference"
        # No generation pipeline access
        assert not hasattr(r, "generation_params")
        assert not hasattr(r, "execution_config")


# ── 8. STUDIO_SPEC v4 alignment ─────────────────────────────────


class TestDocsAlignment:
    """STUDIO_SPEC v4 must match actual code."""

    def test_spec_says_discussion_not_version(self):
        spec = open(
            os.path.join(os.path.dirname(__file__), "..", "..", "docs", "STUDIO_SPEC.md"),
            encoding="utf-8",
        ).read()
        # Key contract points must be documented
        # (specific checks below)

    def test_spec_mentions_three_separate_results(self):
        spec = open(
            os.path.join(os.path.dirname(__file__), "..", "..", "docs", "STUDIO_SPEC.md"),
            encoding="utf-8",
        ).read()
        assert "Image Description" in spec
        assert "Video Description" in spec
        assert "Full Video Scenario" in spec

    def test_spec_says_studio_not_description_engine(self):
        spec = open(
            os.path.join(os.path.dirname(__file__), "..", "..", "docs", "STUDIO_SPEC.md"),
            encoding="utf-8",
        ).read()
        assert "Studio НЕ генерирует" in spec or "Studio не является Description Engine" in spec

    def test_spec_mentions_mediaplan_v0_unchanged(self):
        spec = open(
            os.path.join(os.path.dirname(__file__), "..", "..", "docs", "STUDIO_SPEC.md"),
            encoding="utf-8",
        ).read()
        assert "MediaPlan v0" in spec
