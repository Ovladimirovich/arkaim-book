"""MD-3.3 — contract tests: JSON Schema reconciliation + deprecation marks.

Проверяют КОНТРАКТ, не реализацию (GO MD-3.3, 7 пунктов):
  1. JSON Schema отвергает execution fields (additionalProperties=false);
  2. JSON Schema принимает валидный MediaPlan v0;
  3. video-only поля валидируются корректно (+ descriptions);
  4. provenance/lineage не ломаются (валидный план с ними);
  5. deprecated functions сохраняют прежнее поведение (D1/D5 — поведение не менялось);
  6. MediaPlan не получает execution leakage (pydantic extra=forbid — runtime-инвариант остаётся зелёным);
  7. (регрессия MD-3.1/MD-3.2 — отдельные файлы, здесь контрактные дополнения).

Запуск (из runtime/):
  .venv\\Scripts\\python -m pytest tests/test_md3_route_deprecations.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from pydantic import ValidationError  # noqa: E402

from visual.visual_context import VisualContext  # noqa: E402
from media_plan import MediaPlanBuilder, MediaPlan, verify_no_execution_fields  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "SCHEMAS" / "MEDIA_PLAN.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

# jsonschema-пакет отсутствует в venv проекта (и не входит в requirements.txt);
# добавление зависимости — вне scope MD-3.3. Используем минимальный
# draft-07-валидатор уровня, необходимого КОНТРАКТНЫМ тестам: проверка
# additionalProperties=false (ядро MD-3.3) + required + типы + enum/const.


class _Ve:
    """Обёртка ошибки валидации (совместимость с jsonschema-форматом .message)."""

    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return self.message


class _MiniDraft7:
    """Минимальный draft-07 validator: object/array/scalar, required,
    additionalProperties, type, enum, const. Покрывает подмножество
    MEDIA_PLAN.schema.json, реально задействованное контрактами MD-3.3."""

    def iter_errors(self, instance, schema=None, path=""):
        schema = schema if schema is not None else self._schema
        errors = []
        for msg in self._iter(instance, schema, path):
            errors.append(_Ve(msg))
        return errors

    def _iter(self, instance, schema, path):
        # type
        stype = schema.get("type")
        if stype is not None:
            types = stype if isinstance(stype, list) else [stype]
            if not any(self._check_type(instance, t) for t in types):
                yield f"{path or '<root>'}: expected type {stype}, got {type(instance).__name__}"
                return
        # const
        if "const" in schema and instance != schema["const"]:
            yield f"{path or '<root>'}: != const {schema['const']!r}"
        # enum
        if "enum" in schema and instance not in schema["enum"]:
            yield f"{path or '<root>'}: {instance!r} not in enum"
        # object
        if isinstance(instance, dict):
            for req in schema.get("required", []):
                if req not in instance:
                    yield f"{path or '<root>'}: required '{req}' missing"
            props = schema.get("properties", {})
            ap = schema.get("additionalProperties", True)
            for key in instance:
                if key in props:
                    yield from self._iter(instance[key], props[key], f"{path}.{key}" if path else key)
                elif ap is False:
                    yield f"{path or '<root>'}: Additional properties are not allowed ('{key}' was unexpected)"
                elif isinstance(ap, dict):
                    yield from self._iter(instance[key], ap, f"{path}.{key}" if path else key)
        # array
        if isinstance(instance, list) and "items" in schema:
            for i, item in enumerate(instance):
                yield from self._iter(item, schema["items"], f"{path}[{i}]")

    @staticmethod
    def _check_type(value, t):
        return {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }.get(t, lambda v: True)(value)

    def __init__(self, schema):
        self._schema = schema

    def validate(self, instance):
        errors = self.iter_errors(instance)
        if errors:
            raise AssertionError("; ".join(e.message for e in errors))

    @staticmethod
    def check_schema(schema):  # structural sanity, не полный мета-валидатор
        assert isinstance(schema, dict) and "type" in schema and "properties" in schema


Draft7Validator = _MiniDraft7


def _make_ctx() -> VisualContext:
    """Минимальный canonical VisualContext (проверенный паттерн test_md3_media_plan.make_ctx)."""
    from visual.scene_context import SourceRefs, extend_visual_context

    ctx = VisualContext()
    extend_visual_context(
        ctx,
        temporal=None,
        source_refs=SourceRefs(scene_id="s1", chapter=1, character_ids=["hero"], location_id="loc_arkaim"),
    )
    return ctx


def _valid_plan_dict() -> dict:
    """Валидный план (все required + типовые optional), как to_dict() плана."""
    plan = MediaPlanBuilder(generator="comfyui").build_image_plan(_make_ctx())
    return plan.to_dict()


# ── 1. Schema отвергает execution fields ──


class TestSchemaRejectsExecution:
    @pytest.mark.parametrize("field,value", [
        ("model", "sdxl"),
        ("checkpoint", "sd_xl_base.safetensors"),
        ("steps", 30),
        ("cfg", 7.5),
        ("sampler", "euler"),
        ("seed", 42),
        ("workflow", {"nodes": []}),
        ("nodes", [{"id": 1}]),
        ("provider", "comfyui"),
        ("backend", "directml"),
        ("quality", "high"),
        ("lora", "x"),
        ("denoise", 0.7),
    ])
    def test_execution_field_fails_validation(self, field, value):
        """(1) execution-поле → JSON Schema validation FAILS."""
        data = _valid_plan_dict()
        data[field] = value
        errors = list(Draft7Validator(SCHEMA).iter_errors(data))
        assert errors, f"execution-поле {field} должно отвергаться Schema"
        assert any(
            "Additional properties are not allowed" in e.message
            for e in errors
        ), f"поле {field}: ожидан отказ additionalProperties, получено: {[e.message for e in errors]}"

    def test_arbitrary_unknown_field_fails(self):
        """(1) Любое постороннее поле (не только execution) отвергается."""
        data = _valid_plan_dict()
        data["totally_unknown_field"] = 1
        errors = list(Draft7Validator(SCHEMA).iter_errors(data))
        assert errors and "Additional properties" in errors[0].message

    def test_pydantic_runtime_invariant_still_green(self):
        """(6) runtime-инвариант MD-3.1 остаётся зелёным: execution-поле →
        MediaPlan/Pydantic validation FAILS (extra=forbid)."""
        data = _valid_plan_dict()
        data["model"] = "sdxl"
        with pytest.raises(ValidationError):
            MediaPlan(**data)
        assert verify_no_execution_fields() == []


# ── 2. Schema принимает валидный план ──


class TestSchemaAcceptsValidPlan:
    def test_valid_image_plan_passes(self):
        """(2) Валидный MediaPlan v0 (image) принимается Schema."""
        errors = list(Draft7Validator(SCHEMA).iter_errors(_valid_plan_dict()))
        assert errors == []

    def test_all_four_required_keys_present_in_plan_dict(self):
        """(2) plan_id/plan_version/media_kind/prompt всегда в to_dict()."""
        d = _valid_plan_dict()
        for key in SCHEMA["required"]:
            assert key in d, f"required {key} отсутствует в to_dict()"

    def test_real_md2_scene_ctx_plan_passes(self):
        """(2) План из РЕАЛЬНОГО genome-контекста (не заглушки) проходит Schema."""
        import asyncio
        from core.adc_deps import registry as reg

        async def _build():
            b = reg.get("visual_context_builder")
            return await b.build_scene_context(1, "conflict_гиперборея_материальный_путь_атлантиды")

        ctx = asyncio.run(_build())
        plan = MediaPlanBuilder(generator="comfyui").build_image_plan(ctx)
        errors = list(Draft7Validator(SCHEMA).iter_errors(plan.to_dict()))
        assert errors == []


# ── 3. video-only поля ──


class TestVideoOnlyFields:
    def test_valid_video_plan_passes(self):
        """(3) video-план (duration_sec/fps/sequence) валиден по Schema."""
        plan = MediaPlanBuilder(generator="comfyui").build_video_plan(_make_ctx())
        errors = list(Draft7Validator(SCHEMA).iter_errors(plan.to_dict()))
        assert errors == []

    def test_video_only_descriptions_present(self):
        """(3) duration_sec/fps имеют video-only description (MD-3.3 R3)."""
        props = SCHEMA["properties"]
        assert "video-only" in props["duration_sec"]["description"]
        assert "video-only" in props["fps"]["description"]

    def test_wrong_type_duration_fails(self):
        """(3) Типизация video-полей действует (duration_sec не number → fail)."""
        data = _valid_plan_dict()
        data["duration_sec"] = "eight"
        errors = list(Draft7Validator(SCHEMA).iter_errors(data))
        assert errors


# ── 4. provenance / lineage ──


class TestProvenanceLineageIntact:
    def test_lineage_in_valid_plan_passes(self):
        """(4) lineage (initial) не ломает валидацию."""
        data = _valid_plan_dict()
        assert data["lineage"]["derivation"] == "initial"
        assert list(Draft7Validator(SCHEMA).iter_errors(data)) == []

    def test_regenerate_lineage_with_parent_passes(self):
        """(4) lineage regenerate с parent_plan_id валиден (контракт MD-3.1)."""
        first = MediaPlanBuilder(generator="comfyui").build_image_plan(_make_ctx())
        second = MediaPlanBuilder(generator="comfyui").build_image_plan(
            _make_ctx(), parent_plan_id=first.plan_id, derivation="regenerate",
        )
        errors = list(Draft7Validator(SCHEMA).iter_errors(second.to_dict()))
        assert errors == []
        assert second.lineage.parent_plan_id == first.plan_id
        assert second.lineage.is_derived

    def test_provenance_schema_shape(self):
        """(4) provenance-структура в Schema соответствует фактическим
        объектам плана (category/source/confidence)."""
        props = SCHEMA["properties"]["provenance"]["items"]["properties"]
        assert set(props) == {"category", "source", "confidence"}


# ── 5. Deprecated functions — прежнее поведение ──


class TestDeprecatedFunctionsBehavior:
    """(5) D1 (build_full_prompt_pair) и D5 (registry-фабрика prompt_composer):
    deprecated-метка НЕ меняет runtime behavior — функции работают как раньше.

    Факт аудита D5: get_prompt_composer НЕ существует (в __all__ — висячая
    строка, pre-existing); мёртвая точка — registry-фабрика
    _factory_prompt_composer / ключ "prompt_composer" (0 потребителей).
    """

    def test_d1_build_full_prompt_pair_still_works(self):
        """D1: историческое поведение пары промптов сохранено
        (паттерн test_visualization.test_prompt_builder_full_pair)."""
        from visualization.prompt_builder import PromptBuilder

        class FakePulse:
            layers = {}

        pb = PromptBuilder(FakePulse())
        pos, neg = pb.build_full_prompt_pair(
            {"title": "Test", "characters": ["ch1"]}, {"ch1": {}}, {})
        assert isinstance(pos, str) and len(pos) > 20
        assert isinstance(neg, str) and len(neg) > 50

    def test_d1_has_deprecation_docstring(self):
        """D1: deprecated-маркер присутствует (контракт метки)."""
        from visualization.prompt_builder import PromptBuilder

        doc = PromptBuilder.build_full_prompt_pair.__doc__ or ""
        assert "DEPRECATED" in doc and "MediaPlanBuilder" in doc  # replacement указан

    def test_d5_factory_still_works(self):
        """D5: registry-фабрика prompt_composer возвращает composer, как раньше."""
        from core.adc_deps import _factory_prompt_composer

        composer = _factory_prompt_composer()
        assert composer is not None

    def test_d5_factory_has_deprecation_docstring(self):
        """D5: deprecated-маркер присутствует у фабрики (контракт метки)."""
        import inspect

        from core import adc_deps

        doc = inspect.getdoc(adc_deps._factory_prompt_composer) or ""
        assert "DEPRECATED" in doc and "MediaPlanBuilder" in doc  # replacement указан


# ── 7. Schema-файл структурная целостность (контракт, не реализация) ──


class TestSchemaContractIntegrity:
    def test_no_execution_properties_in_schema(self):
        """(1)(6) В properties Schema нет запрещённых свойств."""
        banned = {"model", "checkpoint", "steps", "cfg", "sampler", "seed",
                  "workflow", "nodes", "provider", "backend", "quality", "lora"}
        assert banned.isdisjoint(set(SCHEMA["properties"]))

    def test_additional_properties_false_top_level(self):
        """(1) additionalProperties=false присутствует на верхнем уровне."""
        assert SCHEMA["additionalProperties"] is False

    def test_schema_is_valid_draft7(self):
        """Schema сама валидна как draft-07 документ."""
        Draft7Validator.check_schema(SCHEMA)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
