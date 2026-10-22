"""G11 — typed-резолверы: контракт, типизация и read-only гарантия.

Проверяет инкремент «следующий безопасный объём»:
  - fallback-проекции собираются из типизированных моделей и проходят валидацию;
  - DTO ``KnowledgeTraceResponse`` типизирует ссылки (а не ``dict[str, Any]``);
  - разрешение сущности НЕ меняет crosswalk, World Model и реестр claim-связей
    (критерий приёмки H2-C из roadmap).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _PROJECT_ROOT / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from schemas.temporal_reference import TemporalReference
from schemas.world_reference import WorldEntityReference

#: Файлы, которые резолверы не имеют права изменять.
READ_ONLY_FILES: tuple[Path, ...] = (
    _PROJECT_ROOT / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json",
    _PROJECT_ROOT / "core" / "CORE" / "narrative_engine" / "data" / "WORLD_MODEL.json",
    _PROJECT_ROOT / "core" / "KNOWLEDGE" / "claim_temporal_links.json",
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot() -> dict[str, str]:
    return {str(path): _digest(path) for path in READ_ONLY_FILES if path.exists()}


# ── Fallback-проекции валидны по типизированным схемам ────────────────────


class TestFallbacksAreSchemaValid:
    def test_world_fallback_validates_against_world_entity_reference(self):
        from core.routes.knowledge_cards import _world_reference_projection

        result = _world_reference_projection("entity-that-does-not-exist")
        reference = WorldEntityReference.model_validate(result)

        assert reference.status.value == "UNRESOLVED"
        assert reference.query == "entity-that-does-not-exist"

    def test_temporal_fallback_validates_against_temporal_reference(self):
        """Fallback-сборка (резолвер упал) валидна по схеме TemporalReference."""
        from unittest.mock import patch

        from core.routes.knowledge_cards import _temporal_reference_projection
        from knowledge.temporal_resolver import KnowledgeTemporalResolver

        with patch.object(KnowledgeTemporalResolver, "resolve", side_effect=RuntimeError("engine down")):
            result = _temporal_reference_projection("entity-that-does-not-exist")

        reference = TemporalReference.model_validate(result)

        assert reference.status.value == "UNKNOWN"
        assert reference.precision.value == "UNKNOWN"
        assert reference.temporal_node_id is None
        assert reference.event_id is None
        assert reference.era_id is None

    def test_temporal_projection_for_unknown_entity_is_unresolved(self):
        """Несуществующая сущность даёт UNRESOLVED (резолвер отработал штатно)."""
        from core.routes.knowledge_cards import _temporal_reference_projection

        result = _temporal_reference_projection("entity-that-does-not-exist")
        reference = TemporalReference.model_validate(result)

        assert reference.status.value in {"UNRESOLVED", "UNKNOWN"}
        assert reference.temporal_node_id is None

    def test_empty_query_fallback_is_still_schema_valid(self):
        """Пустой вход — тоже валидная типизированная ссылка, а не сырой dict."""
        from core.routes.knowledge_cards import _world_reference_projection

        result = _world_reference_projection("")
        reference = WorldEntityReference.model_validate(result)

        assert reference.status.value == "UNRESOLVED"
        assert reference.query  # непустой плейсхолдер вместо пустой строки

    def test_fallback_keeps_full_contract_shape(self):
        """Fallback содержит те же ключи, что и настоящая ссылка."""
        from core.routes.knowledge_cards import _world_reference_projection

        result = _world_reference_projection("ghost")
        expected = set(WorldEntityReference.model_fields.keys())

        assert set(result.keys()) == expected


# ── DTO типизирует ссылки ─────────────────────────────────────────────────


class TestTraceDtoTyping:
    def test_dto_fields_use_typed_models(self):
        from core.dto.knowledge import KnowledgeTraceResponse

        annotations = KnowledgeTraceResponse.model_fields["world_reference"].annotation
        temporal_annotation = KnowledgeTraceResponse.model_fields["temporal_reference"].annotation

        assert WorldEntityReference in _union_members(annotations)
        assert TemporalReference in _union_members(temporal_annotation)

    def test_empty_dict_reference_is_treated_as_absent(self):
        from core.dto.knowledge import KnowledgeTraceResponse

        response = KnowledgeTraceResponse(entity_id="x", status="PARTIAL", world_reference={}, temporal_reference={})

        assert response.world_reference is None
        assert response.temporal_reference is None

    def test_typed_reference_survives_serialisation(self):
        from core.dto.knowledge import KnowledgeTraceResponse

        response = KnowledgeTraceResponse(
            entity_id="x",
            status="PARTIAL",
            world_reference={"query": "x", "status": "UNRESOLVED"},
        )

        payload = response.model_dump(mode="json")
        assert payload["world_reference"]["status"] == "UNRESOLVED"
        assert payload["world_reference"]["query"] == "x"

    def test_status_is_constrained_to_known_vocabulary(self):
        from pydantic import ValidationError

        from core.dto.knowledge import KnowledgeTraceResponse

        with pytest.raises(ValidationError):
            KnowledgeTraceResponse(entity_id="x", status="NONSENSE")


def _union_members(annotation) -> tuple:
    """Возвращает члены union-аннотации (или сам тип, если union'а нет)."""
    import types
    import typing

    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        return typing.get_args(annotation)
    return (annotation,)


# ── Read-only гарантия (критерий приёмки H2-C) ────────────────────────────


class TestResolverIsReadOnly:
    def test_trace_request_does_not_modify_world_artifacts(self):
        """Запрос trace не меняет crosswalk, World Model и реестр claim-связей."""
        from core.routes import knowledge_cards as kc
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(kc.router)
        checker = kc.router.dependencies[0].dependency
        app.dependency_overrides[checker] = lambda: {
            "user_id": "g11-tester",
            "role": "reader",
            "provider": "test",
            "username": "g11_tester",
            "display_name": "G11 Tester",
        }
        client = TestClient(app)

        before = _snapshot()
        assert before, "Не найдены файлы для проверки read-only"

        response = client.get("/knowledge/cards/trace/region_arkaim")
        assert response.status_code == 200

        after = _snapshot()
        assert after == before, "Резолвер изменил read-only артефакты мира"

    def test_direct_world_resolution_does_not_modify_world_artifacts(self):
        from knowledge.world_resolver import WorldKnowledgeResolver

        before = _snapshot()
        assert before

        WorldKnowledgeResolver().resolve("region_arkaim")

        assert _snapshot() == before

    def test_direct_temporal_resolution_does_not_modify_world_artifacts(self):
        from knowledge.temporal_resolver import KnowledgeTemporalResolver
        from schemas.temporal_reference import TemporalTimeBasis

        before = _snapshot()
        assert before

        KnowledgeTemporalResolver().resolve(
            claim_id="region_arkaim",
            temporal_node_id="region_arkaim",
            time_basis=TemporalTimeBasis.WORLD,
        )

        assert _snapshot() == before
