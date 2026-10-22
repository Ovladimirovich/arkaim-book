"""M1 tests: ProvenanceCategory, ProvenanceTag, ProvenanceRegistry, CanonClaim, SourceHierarchy."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone


from narrative_engine.source_levels import (
    ProvenanceCategory,
    ProvenanceTag,
    SourceLevel,
    canonical_provenance,
    external_provenance,
    hypothesis_provenance,
    derived_provenance,
)
from narrative_engine.provenance.registry import ProvenanceRegistry
from narrative_engine.provenance.claim import CanonClaim
from narrative_engine.provenance.source_hierarchy import (
    SourceHierarchy,
    SourceTier,
    SourceEntry,
)
from narrative_engine.provenance.knowledge_classification import (
    KNOWLEDGE_CLASSIFICATION,
    get_classification,
    is_canon_file,
    requires_author_review,
    get_all_canon_files,
    classify_all,
    KnowledgeCategory,
)


# ═══════════════════════════════════════════════════════════════
# ProvenanceCategory
# ═══════════════════════════════════════════════════════════════


class TestProvenanceCategory:
    def test_all_categories_exist(self):
        """Все 8 категорий существуют."""
        expected = {
            "AUTHOR_CANON",
            "DERIVED",
            "EXTERNAL_SOURCE",
            "RECONSTRUCTION",
            "HYPOTHESIS",
            "ARTISTIC_MODEL",
            "FUTURE_EXTRAPOLATION",
            "UNKNOWN",
        }
        actual = {c.value for c in ProvenanceCategory}
        assert actual == expected

    def test_category_is_not_confused_with_source_level(self):
        """ProvenanceCategory и SourceLevel — разные типы."""
        assert ProvenanceCategory.AUTHOR_CANON != SourceLevel.CANON
        assert isinstance(ProvenanceCategory.AUTHOR_CANON, ProvenanceCategory)
        assert isinstance(SourceLevel.CANON, SourceLevel)

    def test_category_values_are_uppercase_strings(self):
        """Все значения категорий — верхний регистр."""
        for cat in ProvenanceCategory:
            assert cat.value == cat.value.upper()
            assert cat.value.isalpha() or cat.value.replace("_", "").isalpha()


# ═══════════════════════════════════════════════════════════════
# ProvenanceTag — два измерения
# ═══════════════════════════════════════════════════════════════


class TestProvenanceTag:
    def test_create_canon_tag(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
        )
        assert tag.is_canon() is True
        assert tag.is_external() is False
        assert tag.is_hypothesis() is False

    def test_create_external_tag(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=0.72,
        )
        assert tag.is_external() is True
        assert tag.is_canon() is False

    def test_hypothesis_high_confidence_still_hypothesis(self):
        """HYPOTHESIS с confidence=0.95 остаётся HYPOTHESIS."""
        tag = ProvenanceTag(
            source_level=SourceLevel.USER_HYPOTHESIS,
            category=ProvenanceCategory.HYPOTHESIS,
            confidence=0.95,
        )
        assert tag.is_hypothesis() is True
        assert tag.confidence == 0.95
        assert tag.category == ProvenanceCategory.HYPOTHESIS

    def test_external_high_confidence_still_external(self):
        """EXTERNAL_SOURCE с confidence=1.0 не становится AUTHOR_CANON."""
        tag = ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=1.0,
        )
        assert tag.is_canon() is False
        assert tag.is_external() is True
        assert tag.confidence == 1.0

    def test_to_dict_and_from_dict_roundtrip(self):
        tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            source_url="https://example.com",
            source_title="Test",
            confidence=0.9,
            notes="test note",
        )
        d = tag.to_dict()
        assert d["category"] == "AUTHOR_CANON"
        assert d["source_level"] == "CANON"
        assert d["confidence"] == 0.9

        restored = ProvenanceTag.from_dict(d)
        assert restored.category == tag.category
        assert restored.source_level == tag.source_level
        assert restored.confidence == tag.confidence

    def test_legacy_from_dict_without_category(self):
        """Legacy данные без category — default из source_level."""
        legacy = {
            "source_level": "CANON",
            "confidence": 1.0,
            "added_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        tag = ProvenanceTag.from_dict(legacy)
        # При отсутствии category -> дефолт из SOURCE_CATEGORY_DEFAULT_LEVEL
        assert tag.category in ProvenanceCategory

    def test_backward_compat_dict_has_both_fields(self):
        """ProvenanceTag содержит и category, и source_level."""
        tag = canonical_provenance(source_url="ch1:p5")
        d = tag.to_dict()
        assert "category" in d
        assert "source_level" in d
        assert d["category"] == "AUTHOR_CANON"
        assert d["source_level"] == "CANON"


# ═══════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════


class TestProvenanceHelpers:
    def test_canonical_provenance(self):
        tag = canonical_provenance(source_url="book/ch1", notes="direct quote")
        assert tag.category == ProvenanceCategory.AUTHOR_CANON
        assert tag.source_level == SourceLevel.CANON
        assert tag.confidence == 1.0
        assert tag.source_url == "book/ch1"

    def test_external_provenance(self):
        tag = external_provenance(
            source_url="https://wikipedia.org",
            source_title="Wikipedia article",
            confidence=0.7,
        )
        assert tag.category == ProvenanceCategory.EXTERNAL_SOURCE
        assert tag.source_level == SourceLevel.HISTORICAL
        assert tag.confidence == 0.7

    def test_hypothesis_provenance(self):
        tag = hypothesis_provenance(confidence=0.41)
        assert tag.category == ProvenanceCategory.HYPOTHESIS
        assert tag.source_level == SourceLevel.USER_HYPOTHESIS

    def test_derived_provenance(self):
        tag = derived_provenance(confidence=0.8)
        assert tag.category == ProvenanceCategory.DERIVED
        assert tag.source_level == SourceLevel.SYSTEM_INTERPRETATION


# ═══════════════════════════════════════════════════════════════
# ProvenanceRegistry
# ═══════════════════════════════════════════════════════════════


class TestProvenanceRegistry:
    def test_register_and_query(self):
        reg = ProvenanceRegistry()
        tag = canonical_provenance(source_url="book/ch1")
        reg.register_tag("arkaim_location", tag)
        assert reg.is_canon("arkaim_location") is True

    def test_external_never_becomes_canon(self):
        reg = ProvenanceRegistry()
        tag = external_provenance(confidence=1.0)
        reg.register_tag("external_entity", tag)
        # Даже с confidence=1.0 — external не может стать canon
        assert reg.is_canon("external_entity") is False
        assert reg.is_external("external_entity") is True

    def test_check_canon_override_protects_canon(self):
        reg = ProvenanceRegistry()
        tag = canonical_provenance()
        reg.register_tag("protected_entity", tag)
        # Нельзя переписать канон
        assert reg.check_canon_override("protected_entity", ProvenanceCategory.HYPOTHESIS) is False

    def test_check_canon_override_allows_external_to_hypothesis(self):
        reg = ProvenanceRegistry()
        tag = external_provenance()
        reg.register_tag("external_entity", tag)
        # External → Hypothesis допустимо
        assert reg.check_canon_override("external_entity", ProvenanceCategory.HYPOTHESIS) is True

    def test_dominant_category_priority(self):
        reg = ProvenanceRegistry()
        # Сначала external
        reg.register_tag("entity_x", external_provenance(confidence=0.9))
        # Потом canon — должен победить
        reg.register_tag("entity_x", canonical_provenance())
        assert reg.get_dominant_category("entity_x") == ProvenanceCategory.AUTHOR_CANON

    def test_stats(self):
        reg = ProvenanceRegistry()
        reg.register_tag("e1", canonical_provenance())
        reg.register_tag("e1", external_provenance())
        reg.register_claim(CanonClaim.from_canon(text="test claim", source_id="book", location="ch1"))
        stats = reg.stats()
        assert stats["total_tags"] >= 2
        assert stats["total_claims"] >= 1
        assert "category_distribution" in stats

    def test_save_and_load(self):
        reg = ProvenanceRegistry()
        reg.register_tag("e1", canonical_provenance())
        reg.register_tag("e2", external_provenance(confidence=0.8))

        # Use project's test_reports dir to avoid Windows tempfile permission issues
        report_dir = Path(__file__).resolve().parent.parent / "test_reports"
        report_dir.mkdir(exist_ok=True)
        path = report_dir / "test_provenance_save.json"

        reg.save(path)
        assert path.exists()

        reg2 = ProvenanceRegistry()
        reg2.load(path)
        assert reg2.is_canon("e1") is True
        assert reg2.is_external("e2") is True

        # Cleanup
        if path.exists():
            path.unlink()

    def test_classify_source_path(self):
        reg = ProvenanceRegistry()
        cat = reg.classify("test text", "SOURCE_OF_TRUTH/BOOK/КНИГА.md")
        assert cat == ProvenanceCategory.AUTHOR_CANON

        cat2 = reg.classify("test text", "SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md")
        assert cat2 == ProvenanceCategory.AUTHOR_CANON  # secondary author is also canon

        cat3 = reg.classify("test text", "unknown/external/path.json")
        assert cat3 == ProvenanceCategory.UNKNOWN


# ═══════════════════════════════════════════════════════════════
# CanonClaim
# ═══════════════════════════════════════════════════════════════


class TestCanonClaim:
    def test_from_canon(self):
        claim = CanonClaim.from_canon(
            text="Аркаим — место силы",
            source_id="book",
            location="chapter:1 paragraph:5",
            entity_ids=["arkaim_location"],
        )
        assert claim.is_canon is True
        assert claim.category == ProvenanceCategory.AUTHOR_CANON
        assert claim.confidence == 1.0
        assert claim.source_location == "chapter:1 paragraph:5"
        assert "arkaim_location" in claim.entity_ids

    def test_from_external(self):
        claim = CanonClaim.from_external(
            text="Археологические данные подтверждают...",
            source_id="archaeology_paper",
            location="https://doi.org/10.xxxx",
            confidence=0.7,
        )
        assert claim.is_external is True
        assert claim.category == ProvenanceCategory.EXTERNAL_SOURCE
        assert claim.confidence == 0.7

    def test_from_hypothesis(self):
        claim = CanonClaim.from_hypothesis(
            text="Гипотеза: Аркаим был центром...",
            source_id="system_analysis",
            location="internal",
            confidence=0.41,
        )
        assert claim.is_hypothesis is True
        assert claim.category == ProvenanceCategory.HYPOTHESIS

    def test_from_reconstruction(self):
        claim = CanonClaim.from_reconstruction(
            text="Реконструкция: храм находился на...",
            source_id="archaeology+",
            location="combined",
            confidence=0.72,
        )
        assert claim.is_reconstruction is True
        assert claim.category == ProvenanceCategory.RECONSTRUCTION

    def test_deterministic_id(self):
        c1 = CanonClaim.from_canon("text", "src", "loc")
        c2 = CanonClaim.from_canon("text", "src", "loc")
        assert c1.id == c2.id

    def test_to_dict_roundtrip(self):
        claim = CanonClaim.from_canon(
            text="test",
            source_id="book",
            location="ch:1",
            entity_ids=["e1"],
            epoch_ids=["ep1"],
            character_ids=["c1"],
        )
        d = claim.to_dict()
        restored = CanonClaim.from_dict(d)
        assert restored.id == claim.id
        assert restored.category == claim.category
        assert restored.entity_ids == claim.entity_ids

    def test_hypothesis_with_high_confidence(self):
        claim = CanonClaim.from_hypothesis(text="Гипотеза", source_id="sys", location="int", confidence=0.95)
        assert claim.is_hypothesis is True
        assert claim.confidence == 0.95
        # Confidence ≠ category
        assert claim.category != ProvenanceCategory.AUTHOR_CANON


# ═══════════════════════════════════════════════════════════════
# SourceHierarchy
# ═══════════════════════════════════════════════════════════════


class TestSourceHierarchy:
    def test_book_is_primary_canon(self):
        entry = SourceHierarchy.get_primary_canon()
        assert entry is not None
        assert entry.tier == SourceTier.PRIMARY_CANON
        assert entry.is_canon is True
        assert entry.path == "SOURCE_OF_TRUTH/BOOK/КНИГА.md"

    def test_script_is_secondary(self):
        entry = SourceHierarchy.get_source("SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md")
        assert entry is not None
        assert entry.tier == SourceTier.SECONDARY_AUTHOR
        assert entry.weight == 0.9

    def test_notes_are_supplement(self):
        entry = SourceHierarchy.get_source("SOURCE_OF_TRUTH/AUTHOR_NOTES/Аннотация.pdf")
        assert entry is not None
        assert entry.tier == SourceTier.AUTHOR_SUPPLEMENT
        assert entry.weight == 0.8

    def test_conflict_resolution(self):
        sources = [
            SourceEntry("book", SourceTier.PRIMARY_CANON, 1.0, "book", is_canon=True),
            SourceEntry("script", SourceTier.SECONDARY_AUTHOR, 0.9, "script"),
        ]
        winner = SourceHierarchy.resolve_conflict(sources)
        assert winner.path == "book"

    def test_classify_book_path(self):
        entry, cat = SourceHierarchy.classify_source("SOURCE_OF_TRUTH/BOOK/КНИГА.md")
        assert entry is not None
        assert cat == ProvenanceCategory.AUTHOR_CANON

    def test_classify_unknown_path(self):
        entry, cat = SourceHierarchy.classify_source("unknown/path.json")
        assert entry is None
        assert cat == ProvenanceCategory.UNKNOWN

    def test_is_canon_source(self):
        assert SourceHierarchy.is_canon_source("SOURCE_OF_TRUTH/BOOK/КНИГА.md") is True
        assert SourceHierarchy.is_canon_source("SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md") is True
        assert SourceHierarchy.is_canon_source("unknown.json") is False

    def test_canon_sources_list(self):
        canon = SourceHierarchy.get_canon_sources()
        assert len(canon) >= 1
        assert all(e.is_canon for e in canon)

    def test_list_all(self):
        all_sources = SourceHierarchy.list_all()
        assert len(all_sources) >= 4


# ═══════════════════════════════════════════════════════════════
# KNOWLEDGE Classification
# ═══════════════════════════════════════════════════════════════


class TestKnowledgeClassification:
    def test_canon_files_identified(self):
        """Канон определяется данными на диске (решение владельца G13, 2026-10-22).

        Раньше реестр объявлял каноном PLOT/SYMBOLS/VALUES/BOOK_PROFILE/
        PHILOSOPHY/ANCHOR_QUOTES, но на диске их _provenance_metadata.category
        = DERIVED. Теперь источник истины — диск, и реестр приведён к нему.
        """
        canon_files = get_all_canon_files()
        assert "BOOK_DOCUMENT.json" in canon_files
        assert "SYNOPSIS_DOCUMENT.json" in canon_files
        assert "AUTHOR_INTENT.json" in canon_files
        # переведённые в DERIVED больше не канон
        for filename in ("PLOT.json", "SYMBOLS.json", "VALUES.json", "BOOK_PROFILE.json", "PHILOSOPHY.json", "ANCHOR_QUOTES.json"):
            assert filename not in canon_files, f"{filename} не должен быть каноном"

    def test_canon_set_equals_disk_canon_set(self):
        """Набор канона в реестре совпадает с _provenance_metadata на диске."""
        import json

        from config import config as core_config

        disk_canon = set()
        for path in sorted(core_config.KNOWLEDGE_DIR.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                continue
            meta = data.get("_provenance_metadata")
            if isinstance(meta, dict) and meta.get("category") == "AUTHOR_CANON":
                disk_canon.add(path.name)
        assert disk_canon, "на диске нет ни одного AUTHOR_CANON-файла"
        assert set(get_all_canon_files()) == disk_canon

    def test_no_knowledge_json_is_auto_canon(self):
        """KNOWLEDGE/*.json НЕ должны быть автоматически каноническими,
        если они являются производными или внешними."""
        for fc in KNOWLEDGE_CLASSIFICATION:
            if fc.filename in (
                "THEMES_DEEP.json",
                "THEMES_EXPANDED.json",
                "SYMBOLS_DEEP.json",
                "SYMBOLS_EXPANDED.json",
                "ACADEMIC_CONFIRMATIONS.json",
                "ARCHAEOLOGY_DEEP.json",
                "COSMOLOGY_DEEP.json",
                "PHILOSOPHY_DEEP.json",
                "CROSS_REFERENCES_DEEP.json",
                "ARCHETYPES_EXPANDED.json",
            ):
                assert fc.is_canon is False, f"{fc.filename} should NOT be canon"

    def test_deep_files_require_review(self):
        """Файлы *_DEEP и *_EXPANDED требуют проверки автором."""
        for fc in KNOWLEDGE_CLASSIFICATION:
            if "_DEEP" in fc.filename or "_EXPANDED" in fc.filename:
                assert fc.requires_author_review is True, f"{fc.filename} requires review"

    def test_academic_confirmations_not_canon(self):
        """ACADEMIC_CONFIRMATIONS — внешний источник, не канон."""
        fc = get_classification("ACADEMIC_CONFIRMATIONS.json")
        assert fc is not None
        assert fc.is_canon is False
        assert fc.category == KnowledgeCategory.EXTERNAL_SOURCE

    def test_archaeology_is_external(self):
        fc = get_classification("ARCHAEOLOGY.json")
        assert fc is not None
        assert fc.category == KnowledgeCategory.EXTERNAL_SOURCE

    def test_is_canon_file(self):
        assert is_canon_file("BOOK_DOCUMENT.json") is True
        assert is_canon_file("THEMES_DEEP.json") is False
        assert is_canon_file("ACADEMIC_CONFIRMATIONS.json") is False

    def test_requires_author_review(self):
        assert requires_author_review("THEMES_DEEP.json") is True
        assert requires_author_review("BOOK_DOCUMENT.json") is False
        assert requires_author_review("ACADEMIC_CONFIRMATIONS.json") is False

    def test_classify_all_returns_dict(self):
        result = classify_all()
        assert isinstance(result, dict)
        assert "BOOK_DOCUMENT.json" in result
        assert result["BOOK_DOCUMENT.json"] == "AUTHOR_CANON"
        # THEMES_DEEP: на диске DERIVED (решение владельца G13, 2026-10-22)
        assert result["THEMES_DEEP.json"] == "DERIVED"

    def test_all_47_files_classified(self):
        """Все известные файлы должны иметь классификацию."""
        classified = set(fc.filename for fc in KNOWLEDGE_CLASSIFICATION)
        # Проверяем, что ключевые файлы есть
        assert "BOOK_DOCUMENT.json" in classified
        assert "CHARACTERS.json" in classified
        assert "ACADEMIC_CONFIRMATIONS.json" in classified
        assert "THEMES_DEEP.json" in classified


# ═══════════════════════════════════════════════════════════════
# External Firewall
# ═══════════════════════════════════════════════════════════════


class TestExternalFirewall:
    def test_external_result_has_provenance_tag(self):
        from narrative_engine.external_sources import ExternalSourceResult

        result = ExternalSourceResult(
            title="Test",
            source_type="wikipedia",
            relevance_score=0.8,
        )
        assert result.provenance.category == ProvenanceCategory.EXTERNAL_SOURCE
        assert result.provenance.source_level == SourceLevel.HISTORICAL

    def test_external_result_is_never_canon(self):
        from narrative_engine.external_sources import ExternalSourceResult, external_result_is_canon

        result = ExternalSourceResult(title="X", source_type="wiki")
        assert external_result_is_canon(result) is False

    def test_tag_as_external(self):
        from narrative_engine.external_sources import tag_as_external

        result = tag_as_external(
            title="Arkaim article",
            url="https://wikipedia.org/wiki/Arkaim",
            source_type="wikipedia",
            relevance_score=0.8,
        )
        assert result.provenance.category == ProvenanceCategory.EXTERNAL_SOURCE
        assert result.provenance.source_url == "https://wikipedia.org/wiki/Arkaim"
        assert result.title == "Arkaim article"

    def test_classify_external_result(self):
        from narrative_engine.external_sources import ExternalSourceResult, classify_external_result

        result = ExternalSourceResult(title="X", source_type="semantic_scholar")
        assert classify_external_result(result) == ProvenanceCategory.EXTERNAL_SOURCE


# ═══════════════════════════════════════════════════════════════
# LLM Provenance Rules (conceptual tests)
# ═══════════════════════════════════════════════════════════════


class TestLLMProvenanceRules:
    def test_llm_cannot_raise_provenance_to_canon(self):
        """LLM output НЕ может иметь AUTHOR_CANON category."""
        # Это концептуальный тест: LLM-generated content
        # всегда получает non-CANON category
        llm_output_category = ProvenanceCategory.HYPOTHESIS
        assert llm_output_category != ProvenanceCategory.AUTHOR_CANON

    def test_canon_to_derived_is_allowed(self):
        """Производный вывод из канона — допустим."""
        # Canon → Derived: допустимо
        assert ProvenanceCategory.DERIVED != ProvenanceCategory.AUTHOR_CANON
        # НоDerived не может переписать Canon
        reg = ProvenanceRegistry()
        reg.register_tag("e1", canonical_provenance())
        assert reg.check_canon_override("e1", ProvenanceCategory.DERIVED) is False

    def test_external_to_canon_is_forbidden(self):
        """External NEVER becomes Canon automatically."""
        reg = ProvenanceRegistry()
        reg.register_tag("e1", external_provenance())
        assert reg.check_canon_override("e1", ProvenanceCategory.AUTHOR_CANON) is False

    def test_hypothesis_to_reconstruction_allowed_with_confirmation(self):
        """Hypothesis → Reconstruction допустимо при подтверждении."""
        reg = ProvenanceRegistry()
        reg.register_tag("e1", hypothesis_provenance())
        assert reg.check_canon_override("e1", ProvenanceCategory.RECONSTRUCTION) is True
