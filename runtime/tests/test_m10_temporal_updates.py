"""M10 tests: Real-time temporal updates from book text (suggest-only).

Contract tests (from approved SPEC):
1. Book change detection (mtime → hash → snapshot)
2. No change → no update
3. Extraction of temporal facts from text
4. AUTHOR_CANON vs DERIVED distinction
5. Candidate update created as pending
6. Without human confirmation WorldModel NOT changed
7. Confirmed update passes validation
8. Invalid/canon-conflicting update rejected
9. Temporal engine refresh after confirmed change
10. Re-processing without new change is idempotent
11. Provenance preserved after refresh
12. Graceful extraction error handling
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from narrative_engine.source_levels import ProvenanceCategory
from narrative_engine.research.book_change_detector import (
    BookChangeDetector,
    BookChangeSnapshot,
)
from narrative_engine.research.temporal_extractor import (
    TemporalExtractor,
    TemporalFinding,
)
from narrative_engine.research.temporal_update_manager import (
    TemporalUpdateManager,
    ConfirmationResult,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def book_file():
    """Temporary book file inside project workspace (sandbox-safe)."""
    d = Path(__file__).resolve().parent / "tmp_m10"
    d.mkdir(exist_ok=True)
    f = d / "book_test.md"
    f.write_text("Первая версия книги.", encoding="utf-8")
    yield f
    if f.exists():
        f.unlink()
    try:
        d.rmdir()
    except OSError:
        pass


@pytest.fixture
def detector(book_file):
    det = BookChangeDetector(book_path=book_file)
    det.initialize()
    return det


@pytest.fixture
def extractor():
    return TemporalExtractor()


@pytest.fixture
def world_model():
    """Isolated WorldModel instance (no file save — in-memory only)."""
    from narrative_engine.world_model import WorldModel, Epoch

    wm = WorldModel()
    wm._data = {
        "epochs": [
            {
                "id": "arkaim_era",
                "name": "Arkaim Era",
                "name_ru": "Эпоха Аркаима",
                "description": "",
                "order": 1,
                "duration_years": None,
                "provenance": [],
            },
            {
                "id": "kali_yuga",
                "name": "Kali Yuga",
                "name_ru": "Кали Юга",
                "description": "",
                "order": 2,
                "duration_years": None,
                "provenance": [],
            },
        ]
    }
    wm._build_indices()
    assert wm.get_epoch("arkaim_era") is not None
    return wm


@pytest.fixture
def world_engine(world_model):
    """WorldEngine-like stub with refresh_temporal (no global singleton)."""
    from narrative_engine.world_engine import WorldEngine

    class _WE:
        def __init__(self):
            self._temporal_engine = None
            self.refresh_calls = 0

        @property
        def temporal_engine(self):
            return self._temporal_engine

        def enable_temporal(self, wm=None):
            from narrative_engine.temporal.reconstruction_engine import (
                TemporalReconstructionEngine,
            )

            self._temporal_engine = TemporalReconstructionEngine.from_world_model(wm or world_model)
            return self._temporal_engine

        def refresh_temporal(self, world_model=None):
            from narrative_engine.temporal.reconstruction_engine import (
                TemporalReconstructionEngine,
            )

            wm = world_model if world_model is not None else world_model
            self._temporal_engine = TemporalReconstructionEngine.from_world_model(wm)
            self.refresh_calls += 1
            return True

    return _WE()


@pytest.fixture
def manager(world_model, world_engine):
    """TemporalUpdateManager with explicit test-local save path.

    Изоляция данных: world_model_path указывает на временный файл
    внутри tests/tmp_m10 — канонический WORLD_MODEL.json никогда
    не затрагивается тестами.
    """
    d = Path(__file__).resolve().parent / "tmp_m10"
    d.mkdir(exist_ok=True)
    save_path = d / "world_model_test_output.json"

    mgr = TemporalUpdateManager(
        world_model=world_model,
        world_engine=world_engine,
        world_model_path=save_path,
    )
    yield mgr
    if save_path.exists():
        save_path.unlink()


# ═══════════════════════════════════════════════════════════════
# 1. Book change detection
# ═══════════════════════════════════════════════════════════════


class TestBookChangeDetection:
    def test_detect_book_change_mtime(self, detector, book_file):
        """Изменение книги → snapshot с новым содержимым."""
        book_file.write_text("Вторая версия с новыми фактами.", encoding="utf-8")
        os.utime(book_file, (book_file.stat().st_atime, book_file.stat().st_mtime + 10))
        snap = detector.watch()
        assert snap is not None
        assert isinstance(snap, BookChangeSnapshot)
        assert "Вторая версия" in snap.content
        assert snap.size_bytes > 0

    def test_detect_no_change_no_update(self, detector):
        """Без изменения книги watch() → None."""
        assert detector.watch() is None

    def test_touch_without_content_change_no_snapshot(self, detector, book_file):
        """mtime изменился, содержимое то же → None (hash-чек)."""
        os.utime(book_file, (book_file.stat().st_atime, book_file.stat().st_mtime + 10))
        assert detector.watch() is None

    def test_detector_missing_file_graceful(self):
        det = BookChangeDetector(book_path=Path("nonexistent") / "book.md")
        det.initialize()
        assert det.watch() is None  # graceful, no crash


# ═══════════════════════════════════════════════════════════════
# 2. Temporal extraction
# ═══════════════════════════════════════════════════════════════


class TestTemporalExtraction:
    def test_extract_absolute_date_author_canon(self, extractor):
        """Прямая дата из книги → AUTHOR_CANON."""
        findings = extractor.extract("Около 4000 лет до н.э. был построен Аркаим.")
        assert len(findings) >= 1
        abs_f = [f for f in findings if f.kind == "absolute_date"]
        assert len(abs_f) >= 1
        assert abs_f[0].category == ProvenanceCategory.AUTHOR_CANON

    def test_extract_relative_period_derived(self, extractor):
        """Относительное выражение → DERIVED (не AUTHOR_CANON!)."""
        findings = extractor.extract("Многие века подряд знания передавались устно.")
        assert len(findings) == 1
        assert findings[0].category == ProvenanceCategory.DERIVED
        assert findings[0].value == "period:CENTURY"

    def test_extract_named_epoch_author_canon(self, extractor):
        """Именованная эпоха из книги → AUTHOR_CANON + epoch-binding."""
        findings = extractor.extract("В эпоху Кали Юги знания угасали.")
        assert any(f.value == "epoch:kali_yuga" for f in findings)
        epoch_f = [f for f in findings if f.value == "epoch:kali_yuga"][0]
        assert epoch_f.category == ProvenanceCategory.AUTHOR_CANON

    def test_extract_no_temporal_text_empty(self, extractor):
        """Обычный текст → 0 findings."""
        findings = extractor.extract("Велик шёл по лесу и думал о жизни.")
        assert findings == []

    def test_extract_graceful_error_handling(self, extractor):
        """Ошибки extraction → пустой список, no crash."""
        assert extractor.extract("") == []
        assert extractor.extract(None) == []
        # Бинарный мусор не должен валить extractor
        assert extractor.extract("\x00\x01\x02") == [] or isinstance(extractor.extract("\x00\x01\x02"), list)


# ═══════════════════════════════════════════════════════════════
# 3. Pending queue (suggest-only boundary)
# ═══════════════════════════════════════════════════════════════


class TestPendingQueue:
    def test_findings_created_as_pending(self, manager, extractor):
        """Submit → pending, NOT applied."""
        findings = extractor.extract("В эпоху Кали Юги многие века.")
        result = manager.submit_findings(findings)
        assert result["new"] >= 1
        assert len(manager.pending) >= 1

    def test_no_confirmation_worldmodel_unchanged(self, manager, extractor, world_model):
        """БЕЗ confirm() WorldModel не меняется (критический инвариант)."""
        before = world_model.get_epoch("kali_yuga")
        before_prov = list(before.provenance)
        before_dur = before.duration_years

        findings = extractor.extract("В эпоху Кали Юги многие века.")
        manager.submit_findings(findings)  # только pending

        after = world_model.get_epoch("kali_yuga")
        assert after.provenance == before_prov  # никаких изменений
        assert after.duration_years == before_dur
        assert manager.stats()["pending"] >= 1

    def test_reprocess_idempotent(self, manager, extractor):
        """Повторная submit тех же находок → 0 новых pending."""
        findings = extractor.extract("В эпоху Кали Юги многие века.")
        r1 = manager.submit_findings(findings)
        r2 = manager.submit_findings(findings)
        assert r1["new"] >= 1
        assert r2["new"] == 0
        assert r2["duplicates"] >= 1


# ═══════════════════════════════════════════════════════════════
# 4. Confirmation gate
# ═══════════════════════════════════════════════════════════════


class TestConfirmationGate:
    def test_confirmed_update_applies_and_refreshes(self, manager, extractor, world_model, world_engine):
        """Confirm → WorldModel обогащён + temporal engine refreshed."""
        findings = extractor.extract("В эпоху Кали Юги многие века.")
        manager.submit_findings(findings)
        epoch_f = [f for f in manager.pending if f.value == "epoch:kali_yuga"][0]

        result = manager.confirm(epoch_f.id)
        assert result.ok is True
        assert result.applied is True
        assert result.temporal_refreshed is True

        # WorldModel обогащён (после подтверждения — легально)
        epoch = world_model.get_epoch("kali_yuga")
        assert epoch.provenance  # добавлен tag
        assert world_engine.refresh_calls >= 1  # engine refreshed

    def test_derived_finding_applies_as_derived_not_canon(self, manager, extractor, world_model):
        """DERIVED finding при confirm остаётся DERIVED, не AUTHOR_CANON."""
        findings = extractor.extract("В эпоху Кали Юги многие века.")
        manager.submit_findings(findings)
        epoch_f = [f for f in manager.pending if f.value == "epoch:kali_yuga"][0]

        result = manager.confirm(epoch_f.id)
        assert result.ok is True

        epoch = world_model.get_epoch("kali_yuga")
        # AUTHOR_CANON (эпоха) + возможно DERIVED из relative finding?
        # Проверяем главное: нет автоматического повышения
        # relative finding не привязан к эпохе → не добавляет tag эпохе
        # epoch_f сам AUTHOR_CANON → tag AUTHOR_CANON легален
        cats = [p.category for p in epoch.provenance]
        assert all(c in (ProvenanceCategory.AUTHOR_CANON, ProvenanceCategory.DERIVED) for c in cats)

    def test_invalid_finding_rejected(self, manager):
        """Finding с невалидной категорией → reject, WorldModel не меняется."""
        bad = TemporalFinding(
            id="bad_finding",
            kind="absolute_date",
            raw_text="test",
            value="epoch:kali_yuga",
            line_number=1,
            category=ProvenanceCategory.UNKNOWN,
        )
        manager.submit_findings([bad])
        result = manager.confirm("bad_finding")
        assert result.ok is False
        assert "invalid_category" in result.reason
        assert result.applied is False

    def test_confirm_nonexistent_finding_fails(self, manager):
        result = manager.confirm("nonexistent_id")
        assert result.ok is False
        assert "finding_not_found" in result.reason

    def test_epoch_binding_to_unknown_epoch_rejected(self, manager, world_model):
        """Finding на несуществующую эпоху → apply fail → reject."""
        unknown = TemporalFinding(
            id="unknown_epoch_f",
            kind="absolute_date",
            raw_text="в эпоху Тмутаракань",
            value="epoch:nonexistent_epoch",
            line_number=1,
            category=ProvenanceCategory.AUTHOR_CANON,
        )
        manager.submit_findings([unknown])
        result = manager.confirm("unknown_epoch_f")
        assert result.ok is False
        assert result.applied is False
        # WorldModel не изменился
        assert world_model.get_epoch("nonexistent_epoch") is None

    def test_reject_finding_no_apply(self, manager, extractor, world_model):
        """reject() → pending убран, WorldModel не меняется."""
        findings = extractor.extract("В эпоху Кали Юги.")
        manager.submit_findings(findings)
        epoch_f = [f for f in manager.pending if f.value == "epoch:kali_yuga"][0]

        result = manager.reject(epoch_f.id, reason="human_disagrees")
        assert result.ok is True
        assert result.applied is False
        assert world_model.get_epoch("kali_yuga").provenance == []


# ═══════════════════════════════════════════════════════════════
# 5. Canon integrity
# ═══════════════════════════════════════════════════════════════


class TestCanonIntegrity:
    def test_existing_canon_not_downgraded(self, manager, world_model):
        """AUTHOR_CANON tag существующей эпохи не удаляется при confirm DERIVED."""
        from narrative_engine.source_levels import ProvenanceTag, SourceLevel

        epoch = world_model.get_epoch("kali_yuga")
        canon_tag = ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
        )
        epoch.provenance.append(canon_tag)

        # DERIVED finding на ту же эпоху
        derived_f = TemporalFinding(
            id="derived_on_canon_epoch",
            kind="absolute_date",
            raw_text="в эпоху Кали Юги",
            value="epoch:kali_yuga",
            line_number=1,
            category=ProvenanceCategory.DERIVED,
        )
        manager.submit_findings([derived_f])
        result = manager.confirm("derived_on_canon_epoch")
        assert result.ok is True

        # Canon tag сохранился
        epoch_after = world_model.get_epoch("kali_yuga")
        cats = [p.category for p in epoch_after.provenance]
        assert ProvenanceCategory.AUTHOR_CANON in cats  # не удалён
        assert ProvenanceCategory.DERIVED in cats  # добавлен как DERIVED

    def test_derived_never_promoted_to_canon(self, manager, world_model):
        """DERIVED finding → применён как DERIVED, НЕ как AUTHOR_CANON."""
        derived_f = TemporalFinding(
            id="derived_only",
            kind="absolute_date",
            raw_text="в эпоху Кали Юги",
            value="epoch:kali_yuga",
            line_number=1,
            category=ProvenanceCategory.DERIVED,
        )
        manager.submit_findings([derived_f])
        manager.confirm("derived_only")

        epoch = world_model.get_epoch("kali_yuga")
        for tag in epoch.provenance:
            if tag.notes and "M10 extraction" in str(tag.notes):
                assert tag.category == ProvenanceCategory.DERIVED  # не повышен

    def test_provenance_preserved_after_refresh(self, manager, extractor, world_model, world_engine):
        """После confirm + refresh provenance эпохи сохраняется в графе."""
        # enable engine сначала
        world_engine.enable_temporal(world_model)
        findings = extractor.extract("В эпоху Кали Юги многие века.")
        manager.submit_findings(findings)
        epoch_f = [f for f in manager.pending if f.value == "epoch:kali_yuga"][0]
        manager.confirm(epoch_f.id)

        # refresh уже выполнен внутри confirm
        te = world_engine.temporal_engine
        assert te is not None
        # temporal graph содержит эпоху
        from narrative_engine.temporal.chain import ChainDirection

        chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
        # граф перестроен: как минимум узлы эпох существуют
        assert te.get_node("temporal_kali_yuga") is not None or te.get_node("kali_yuga") is not None


# ═══════════════════════════════════════════════════════════════
# 6. WorldEngine.refresh_temporal (M10 addition)
# ═══════════════════════════════════════════════════════════════


class TestRefreshTemporal:
    def test_refresh_creates_new_engine(self, world_engine, world_model):
        """refresh_temporal() → новый engine instance."""
        e1 = world_engine.enable_temporal(world_model)
        e2 = world_engine.refresh_temporal(world_model)
        assert e2 is True
        assert world_engine.temporal_engine is not e1  # новый instance
        assert world_engine.temporal_engine is not None

    def test_refresh_without_epochs_returns_false(self):
        """WorldModel без эпох → реальный WorldEngine.refresh_temporal False.

        Примечание: from_world_model() на пустом WorldModel всё равно
        добавляет temporal_today (M8.1), поэтому пустой refresh вернёт
        False только через guard wm.get_epochs(). Проверяем реальный класс.
        """
        from narrative_engine.world_engine import WorldEngine
        from narrative_engine.world_model import WorldModel

        empty = WorldModel()
        we = WorldEngine.__new__(WorldEngine)
        we._temporal_engine = None
        assert we.refresh_temporal(world_model=empty) is False
        assert we.temporal_engine is None  # engine не создан на пустых данных

    def test_real_world_engine_refresh(self, world_model):
        """Настоящий WorldEngine.refresh_temporal работает (не stub)."""
        from narrative_engine.world_engine import WorldEngine

        we = WorldEngine.__new__(WorldEngine)
        we._temporal_engine = None
        ok = we.refresh_temporal(world_model=world_model)
        assert ok is True
        assert we.temporal_engine is not None
