"""MD-2 Scene Context v2 — канонические поля поверх VisualContext.

Расширение существующего VisualContext (НЕ новый параллельный класс):
  temporal     — read-only ссылка на эпоху из WorldModel (без синтеза);
  source_refs  — ссылки на genome-данные (без дублирования содержимого);
  integrity    — архитектурный инвариант «связи не синтезируются».

MD-2 (Scene Context Consolidation). Слой media-neutral: никаких
execution-полей (model/steps/seed/cfg/workflow/provider) здесь НЕТ
и добавлять их запрещено (ADR_ARKAIM_MEDIA_BOUNDARY Decision 3).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProvenanceRef:
    """Доказательство происхождения — ПРОЕКЦИЯ ProvenanceTag.

    Копирует только поля существующего narrative_engine-тега;
    не создаёт новых категорий и не присваивает их сама.
    """

    category: str = ""
    source: str = ""
    confidence: float = 0.0

    @classmethod
    def from_tag(cls, tag) -> "ProvenanceRef":
        """Спроецировать существующий ProvenanceTag (narrative_engine.source_levels)."""
        source = ""
        if tag.source is not None:
            source = str(tag.source)
        confidence = float(getattr(tag, "confidence", 0.0) or 0.0)
        return cls(
            category=str(tag.category.value if hasattr(tag.category, "value") else tag.category),
            source=source,
            confidence=confidence,
        )


@dataclass
class TemporalSceneRef:
    """Временная ссылка сцены — read-only проекция эпохи из WorldModel.

    Наполняется ТОЛЬКО из WorldModel.get_temporal_context(...) /
    соответствующего существующего API. Класс не строит relations,
    не синтезирует Present→Arkaim и не угадывает эпоху.
    """

    epoch_id: str = ""
    name_ru: str = ""
    confidence: float = 0.0
    bounds_start: str = ""
    bounds_end: str = ""
    bounds_uncertainty: str = ""
    provenance: list[ProvenanceRef] = field(default_factory=list)
    event_count: int = 0
    character_count: int = 0
    technology_count: int = 0

    @property
    def is_temporal(self) -> bool:
        """True, если ссылка указывает на реальную эпоху."""
        return bool(self.epoch_id)

    def provenance_categories(self) -> list[str]:
        """Категории provenance (порядок сохраняется, дубликата нет)."""
        seen: set[str] = set()
        result: list[str] = []
        for ref in self.provenance:
            if ref.category and ref.category not in seen:
                seen.add(ref.category)
                result.append(ref.category)
        return result


@dataclass
class SourceRefs:
    """Ссылки на существующие genome/world данные (без дублирования содержимого).

    Хранит ИДЕНТИФИКАТОРЫ (scene_id/character_id/location_id/chapter),
    а не копии описаний — единственный источник данных остаётся genome.
    """

    scene_id: str = ""
    chapter: int = 0
    character_ids: list[str] = field(default_factory=list)
    location_id: str = ""
    entity_refs: list[str] = field(default_factory=list)
    rag_fallback: bool = False

    def to_dict(self) -> dict:
        """Сериализация ссылок (для логов/трансформаций)."""
        return {
            "scene_id": self.scene_id,
            "chapter": self.chapter,
            "character_ids": list(self.character_ids),
            "location_id": self.location_id,
            "entity_refs": list(self.entity_refs),
            "rag_fallback": self.rag_fallback,
        }


@dataclass
class SceneIntegrity:
    """Архитектурный инвариант Scene Context.

    links_synthesized = False фиксирует, что связи/relations внутри
    контекста НЕ пересчитаны и НЕ созданы фронтендом/слоем —
    инвариант ADR_TEMPORAL_WORLD_MODEL (время read-only, связи из
    канона). Поле intentionally-denormalized честно помечает
    деградировавшие проекции (например, устаревшие поля VisualAsset).
    """

    links_synthesized: bool = False
    temporal_read_only: bool = True
    provenance_inherited: bool = False
    intentionally_denormalized: bool = False


@dataclass
class SceneContextExtras:
    """MD-2 дополнения VisualContext (aggregate-поле, additive non-breaking).

    VisualContext получает поле scene_extras этого типа: существующие
    15 измерений не переименовываются и не удаляются.
    """

    temporal: TemporalSceneRef = field(default_factory=TemporalSceneRef)
    source_refs: SourceRefs = field(default_factory=SourceRefs)
    integrity: SceneIntegrity = field(default_factory=SceneIntegrity)

    def to_dict(self) -> dict:
        """Сериализация extras (для логов и legacy-моста)."""
        from dataclasses import asdict
        return asdict(self)


def extend_visual_context(ctx, temporal: TemporalSceneRef | None = None,
                          source_refs: SourceRefs | None = None) -> None:
    """Расширить существующий VisualContext полями MD-2 (in-place, additive).

    Единственная точка, через которую MD-2-поля попадают в контекст.
    Работает с VisualContext из core/CORE/visual/visual_context.py:
    создаёт scene_extras при отсутствии, НЕ трогает остальные поля.
    """
    extras = getattr(ctx, "scene_extras", None)
    if not isinstance(extras, SceneContextExtras):
        extras = SceneContextExtras()
        ctx.scene_extras = extras
    if temporal is not None:
        extras.temporal = temporal
    if source_refs is not None:
        extras.source_refs = source_refs
    # Инвариант «связи не синтезируются» фиксируется всегда.
    extras.integrity = SceneIntegrity(
        links_synthesized=False,
        temporal_read_only=True,
        provenance_inherited=bool(extras.temporal.provenance),
    )
