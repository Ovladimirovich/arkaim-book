"""ProvenanceRegistry — единый реестр всех provenance тегов и claims.

M1: централизованное управление provenance.
Не singleton — используется как сервис, передаваемый через DI.

Функции:
  - register(category, tag) — добавить тег
  - get(entity_id) — получить все теги сущности
  - is_canon(entity_id) — проверить, является ли сущность канонической
  - is_external(entity_id) — проверить, внешний ли источник
  - classify(text, source_path) — классифицировать новый факт
  - check_canon_override(entity_id) — проверить, можно ли переписать канон
  - get_canon_claims() — получить все канонические claims
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
)
from narrative_engine.provenance.claim import CanonClaim
from narrative_engine.provenance.source_hierarchy import SourceHierarchy

log = logging.getLogger("hermes.provenance.registry")


class ProvenanceRegistry:
    """Реестр provenance для всех фактов системы.

    Хранит:
      - tags: entity_id → list[ProvenanceTag]
      - claims: list[CanonClaim]
    """

    def __init__(self):
        self._tags: dict[str, list[ProvenanceTag]] = {}
        self._claims: list[CanonClaim] = []
        self._entity_categories: dict[str, ProvenanceCategory] = {}

    # ── Register ─────────────────────────────────────────────────────────

    def register_tag(self, entity_id: str, tag: ProvenanceTag) -> None:
        """Зарегистрировать тег provenance для сущности."""
        if entity_id not in self._tags:
            self._tags[entity_id] = []
        self._tags[entity_id].append(tag)
        # Обновить доминирующую категорию сущности
        self._update_dominant_category(entity_id, tag)

    def register_claim(self, claim: CanonClaim) -> None:
        """Зарегистрировать claim."""
        self._claims.append(claim)
        for eid in claim.entity_ids:
            self.register_tag(eid, ProvenanceTag(
                source_level=SourceLevel.CANON if claim.is_canon else SourceLevel.SYSTEM_INTERPRETATION,
                category=claim.category,
                source_url=claim.source_location,
                confidence=claim.confidence,
                notes=f"claim:{claim.id}",
            ))

    def _update_dominant_category(self, entity_id: str, tag: ProvenanceTag) -> None:
        """Обновить доминирующую категорию сущности.

        Приоритет: AUTHOR_CANON > RECONSTRUCTION > HYPOTHESIS > EXTERNAL_SOURCE > UNKNOWN
        """
        priority = {
            ProvenanceCategory.AUTHOR_CANON: 7,
            ProvenanceCategory.DERIVED: 6,
            ProvenanceCategory.RECONSTRUCTION: 5,
            ProvenanceCategory.HYPOTHESIS: 4,
            ProvenanceCategory.ARTISTIC_MODEL: 3,
            ProvenanceCategory.FUTURE_EXTRAPOLATION: 2,
            ProvenanceCategory.EXTERNAL_SOURCE: 1,
            ProvenanceCategory.UNKNOWN: 0,
        }
        current = self._entity_categories.get(entity_id)
        if current is None or priority.get(tag.category, 0) > priority.get(current, 0):
            self._entity_categories[entity_id] = tag.category

    # ── Query ────────────────────────────────────────────────────────────

    def get_tags(self, entity_id: str) -> list[ProvenanceTag]:
        """Все теги provenance для сущности."""
        return self._tags.get(entity_id, [])

    def get_dominant_category(self, entity_id: str) -> ProvenanceCategory:
        """Доминирующая категория сущности."""
        return self._entity_categories.get(entity_id, ProvenanceCategory.UNKNOWN)

    def is_canon(self, entity_id: str) -> bool:
        """Является ли сущность канонической (хотя бы один AUTHOR_CANON тег)."""
        tags = self._tags.get(entity_id, [])
        return any(t.category == ProvenanceCategory.AUTHOR_CANON for t in tags)

    def is_external(self, entity_id: str) -> bool:
        """Является ли сущность внешним источником."""
        tags = self._tags.get(entity_id, [])
        return any(t.category == ProvenanceCategory.EXTERNAL_SOURCE for t in tags)

    def is_hypothesis(self, entity_id: str) -> bool:
        """Является ли сущность гипотезой."""
        tags = self._tags.get(entity_id, [])
        return any(t.category == ProvenanceCategory.HYPOTHESIS for t in tags)

    def has_canon_tag(self, entity_id: str) -> bool:
        """Есть ли у сущности хотя бы один канонический тег."""
        return self.is_canon(entity_id)

    def check_canon_override(self, entity_id: str, new_category: ProvenanceCategory) -> bool:
        """Можно ли переписать provenance сущности.

        Правила:
          - AUTHOR_CANON нельзя переписать ничем
          - EXTERNAL_SOURCE нельзя переписать в AUTHOR_CANON
          - HYPOTHESIS можно повысить до RECONSTRUCTION при подтверждении
        """
        current = self.get_dominant_category(entity_id)

        # AUTHOR_CANON — неприкосновенен
        if current == ProvenanceCategory.AUTHOR_CANON:
            return False

        # EXTERNAL_SOURCE не может стать AUTHOR_CANON
        if current == ProvenanceCategory.EXTERNAL_SOURCE and new_category == ProvenanceCategory.AUTHOR_CANON:
            return False

        # HYPOTHESIS → RECONSTRUCTION допустимо при подтверждении
        if current == ProvenanceCategory.HYPOTHESIS and new_category == ProvenanceCategory.RECONSTRUCTION:
            return True

        return True

    # ── Classification ───────────────────────────────────────────────────

    def classify(self, text: str, source_path: str, confidence: float = 1.0) -> ProvenanceCategory:
        """Классифицировать факт по пути источника.

        Возвращает ProvenanceCategory на основе SourceHierarchy.
        """
        entry, category = SourceHierarchy.classify_source(source_path)
        if entry is not None:
            return category
        # Fallback: если путь не в иерархии — UNKNOWN
        return ProvenanceCategory.UNKNOWN

    # ── Canon claims ─────────────────────────────────────────────────────

    def get_canon_claims(self) -> list[CanonClaim]:
        """Все канонические claims."""
        return [c for c in self._claims if c.is_canon]

    def get_claims_by_entity(self, entity_id: str) -> list[CanonClaim]:
        """Claims, связанные с сущностью."""
        return [c for c in self._claims if entity_id in c.entity_ids]

    def get_external_claims(self) -> list[CanonClaim]:
        """Все claims из внешних источников."""
        return [c for c in self._claims if c.is_external]

    def get_hypothesis_claims(self) -> list[CanonClaim]:
        """Все claims-гипотезы."""
        return [c for c in self._claims if c.is_hypothesis]

    # ── Statistics ───────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Статистика по реестру."""
        from collections import Counter
        cat_counts = Counter(t.category for tags in self._tags.values() for t in tags)
        claim_cat_counts = Counter(c.category for c in self._claims)
        return {
            "total_tags": sum(len(v) for v in self._tags.values()),
            "total_entities": len(self._tags),
            "total_claims": len(self._claims),
            "category_distribution": {k.value: v for k, v in cat_counts.items()},
            "claim_distribution": {k.value: v for k, v in claim_cat_counts.items()},
        }

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        """Сохранить реестр в JSON."""
        import json
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tags": {
                eid: [t.to_dict() for t in tags]
                for eid, tags in self._tags.items()
            },
            "claims": [c.to_dict() for c in self._claims],
            "entity_categories": {
                eid: cat.value for eid, cat in self._entity_categories.items()
            },
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("provenance_registry_saved path=%s tags=%d claims=%d", path, len(self._tags), len(self._claims))

    def load(self, path: Path) -> None:
        """Загрузить реестр из JSON."""
        import json
        if not path.exists():
            log.warning("provenance_registry_not_found path=%s", path)
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for eid, tags_data in data.get("tags", {}).items():
            self._tags[eid] = [ProvenanceTag.from_dict(t) for t in tags_data]
        for claim_data in data.get("claims", []):
            self._claims.append(CanonClaim.from_dict(claim_data))
        for eid, cat_val in data.get("entity_categories", {}).items():
            self._entity_categories[eid] = ProvenanceCategory(cat_val)
        log.info("provenance_registry_loaded path=%s tags=%d claims=%d", path, len(self._tags), len(self._claims))
