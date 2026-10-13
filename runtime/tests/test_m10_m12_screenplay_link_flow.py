# -*- coding: utf-8 -*-
"""M10-M12 — функциональный путь связей сценарий↔книга: обнаружение → подтверждение → сохранение → перечитывание.

Сценарии на реальных данных проекта:
- обнаружение кандидатов: детерминированное сопоставление 119 сцен
  SYNOPSIS_DOCUMENT.json и 824 чанков enriched_chunks.json (suggest-only);
- разрешение неоднозначностей: top-k кандидатов на сцену;
- подтверждение и сохранение: approve_link (реестр с _provenance_metadata,
  атомарная запись, merge без потери owner-notes);
- перечитывание после перезагрузки: ScreenplayBookLinker (4-полевой
  контракт + опциональная provenance);
- self-heal: repair_provenance после внешнего отката файла в 4-полевой формат.

Реестр core/KNOWLEDGE/screenplay_links.json в тестах НЕ меняется:
операции записи выполняются только на tmp-копиях.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_CORE = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
if str(_CORE) not in sys.path:
    sys.path.insert(0, str(_CORE))

from knowledge.screenplay_link_candidates import (  # noqa: E402
    SUGGEST_STATUS,
    candidates_for_scene,
    detect_candidates,
)
from knowledge.screenplay_linker import ScreenplayBookLinker  # noqa: E402
from knowledge.screenplay_links_provenance import (  # noqa: E402
    APPROVED_PAIRS,
    M16_1_APPROVED_PAIRS,
    SCREENPLAY_LINKS_PATH,
    approve_link,
    build_approved_link_records,
    load_existing_records,
    repair_provenance,
    save_screenplay_links,
    validate_screenplay_links,
)


def _real_data() -> list[dict]:
    return json.loads(SCREENPLAY_LINKS_PATH.read_text(encoding="utf-8"))


def _copy_registry(tmp_path: Path) -> Path:
    out = tmp_path / "screenplay_links.json"
    out.write_text(SCREENPLAY_LINKS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return out


def _registry_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Кэш детекции на уровне модуля теста: полный проход 119×824 — несколько
# секунд, не нужно пересчитывать его в каждом тесте.
_DETECTION_CACHE: dict[tuple[int, float], list] = {}


def _all_candidates(top_k: int = 5, min_coverage: float = 0.05) -> list:
    key = (top_k, min_coverage)
    if key not in _DETECTION_CACHE:
        _DETECTION_CACHE[key] = detect_candidates(top_k=top_k, min_coverage=min_coverage)
    return _DETECTION_CACHE[key]


def _scene_candidates(scene_id: str, top_k: int = 5) -> list:
    """Кэшированные кандидаты сцены из полного прохода (без повторного подсчёта)."""
    return [cand for cand in _all_candidates(top_k=top_k) if cand.screenplay_scene_id == scene_id]


# ── Обнаружение кандидатов (M10, suggest-only) ─────────────────────────


class TestCandidateDetectionRealData:
    """Детерминированное обнаружение на реальных данных проекта."""

    def test_all_approved_pairs_are_top_candidates(self):
        """Все 9 пар, одобренных M16.1, обнаруживаются детектором как top-1.

        Пары M20.1 (scene_004/009/020/086/117) входят в реестр по
        OWNER-решению и проверяются в test_m20_1 (разрешение линкером +
        дословный текст), а не ранжированием детектора.
        """
        by_scene: dict[str, list[str]] = {}
        for cand in _all_candidates(top_k=5):
            by_scene.setdefault(cand.screenplay_scene_id, []).append(cand.book_chunk_id)
        for scene_id, chunk_id in M16_1_APPROVED_PAIRS:
            ranked = by_scene.get(scene_id, [])
            assert ranked, f"нет кандидатов для одобренной сцены {scene_id}"
            assert ranked[0] == chunk_id, f"{scene_id}: top-1 = {ranked[0]}, ожидалось {chunk_id}"

    def test_scene_without_approved_link_gets_candidates(self):
        """scene_000 не входит в реестр M16.1, но у неё есть кандидаты."""
        found = candidates_for_scene("scene_000", top_k=5)
        assert found, "у scene_000 не найдено ни одного кандидата"
        top = found[0]
        assert top.status == SUGGEST_STATUS
        assert top.coverage > 0
        assert "suggest-only" in top.notes

    def test_ambiguity_surface_multiple_chunks_for_scene(self):
        """Разрешение неоднозначностей: у одной сцены несколько конкурирующих чанков."""
        found = candidates_for_scene("scene_047", top_k=5)
        chunks = {cand.book_chunk_id for cand in found}
        assert len(chunks) >= 3, f"ожидалось >=3 конкурирующих чанков, получено {len(chunks)}"

    def test_detection_is_deterministic(self):
        """Два запуска дают идентичный набор кандидатов (нет случайности)."""
        first = [c.to_dict() for c in detect_candidates(top_k=5)]
        second = [c.to_dict() for c in detect_candidates(top_k=5)]
        assert first == second
        assert first, "пустой набор кандидатов на реальных данных"

    def test_detection_is_suggest_only_no_writes(self):
        """Обнаружение не трогает реестр (suggest-only gate)."""
        before = _registry_hash(SCREENPLAY_LINKS_PATH)
        detect_candidates(top_k=3)
        candidates_for_scene("scene_006")
        assert _registry_hash(SCREENPLAY_LINKS_PATH) == before, "обнаружение изменило реестр"

    def test_unknown_scene_returns_empty(self):
        assert candidates_for_scene("scene_999") == []


# ── Подтверждение и сохранение (M10-M12 owner gate, только tmp-реестры) ─


class TestApprovalPersistence:
    """approve_link: подтверждение кандидата сохраняется с provenance."""

    def test_approve_candidate_appends_and_reads_back(self, tmp_path: Path):
        """Сценарий из M16.1-notes: scene_000 цитирует chunk p_0006 (общий с scene_003)."""
        reg = _copy_registry(tmp_path)
        found = _scene_candidates("scene_000", top_k=5)
        assert found, "у scene_000 не найдено ни одного кандидата"
        candidate = found[0]
        # Общий chunk (одобрен для scene_003 в M16.1) — допустимое повторное
        # связывание: ограничение реестра — уникальность ПАРЫ (scene, chunk),
        # не chunk и не сцена (M20.1: у одной сцены может быть несколько связей).
        approve_link("scene_000", candidate.book_chunk_id, notes="TEST-CONFIRMATION (M10-M12)", path=reg)
        new_data = json.loads(reg.read_text(encoding="utf-8"))

        # сохранение: 15 записей (14 базовых + подтверждённая), валидатор доволен
        assert len(new_data) == len(APPROVED_PAIRS) + 1
        assert validate_screenplay_links(new_data) == []
        extra = next(r for r in new_data if r["screenplay_scene_id"] == "scene_000")
        assert extra["book_chunk_id"] == candidate.book_chunk_id
        assert extra["_provenance_metadata"]["resolved_by"].startswith("M10-M12 owner confirmation")
        assert extra["_provenance_metadata"]["evidence_ref"] == f"book:{candidate.book_chunk_id}"

        # перечитывание после «перезагрузки»: read-only линкер видит связку с provenance
        linker = ScreenplayBookLinker.from_json(reg)
        link = next(item for item in linker.links if item.screenplay_scene_id == "scene_000")
        assert link.book_chunk_id == candidate.book_chunk_id
        assert isinstance(link.provenance, dict) and link.provenance["category"] == "AUTHOR_CANON"

    def test_regeneration_keeps_confirmed_extra_links(self, tmp_path: Path):
        """Обычная регенерация базовых пар не уничтожает подтверждённые доп. связи."""
        reg = _copy_registry(tmp_path)
        approve_link("scene_000", "chunk_p_0006_104f39f72f26", notes="extra confirmed", path=reg)
        approve_link("scene_001", "chunk_p_0006_104f39f72f26", notes="another scene, shared chunk", path=reg)

        save_screenplay_links(build_approved_link_records(existing=load_existing_records()), reg)
        data = json.loads(reg.read_text(encoding="utf-8"))
        by_scene = {r["screenplay_scene_id"]: r for r in data}
        assert by_scene["scene_000"]["notes"] == "extra confirmed", "owner-notes потеряны при регенерации"
        assert by_scene["scene_001"]["notes"] == "another scene, shared chunk"
        assert by_scene["scene_000"]["_provenance_metadata"]["resolved_by"].startswith("M10-M12")
        assert validate_screenplay_links(data) == []

    def test_duplicate_scene_rejected(self, tmp_path: Path):
        reg = _copy_registry(tmp_path)
        with pytest.raises(ValueError, match="уже имеет подтверждённую связь"):
            approve_link("scene_003", "chunk_p_0006_104f39f72f26", path=reg)

    def test_unknown_scene_id_rejected(self, tmp_path: Path):
        reg = _copy_registry(tmp_path)
        with pytest.raises(ValueError, match="отсутствует в нормативном источнике"):
            approve_link("scene_999", "chunk_p_0006_104f39f72f26", path=reg)

    def test_unknown_chunk_id_rejected(self, tmp_path: Path):
        reg = _copy_registry(tmp_path)
        with pytest.raises(ValueError, match="отсутствует в книжном реестре"):
            approve_link("scene_000", "chunk_p_9999_deadbeef0000", path=reg)

    def test_bad_formats_rejected(self, tmp_path: Path):
        reg = _copy_registry(tmp_path)
        with pytest.raises(ValueError, match="не соответствует формату"):
            approve_link("scene_6", "chunk_p_0001", path=reg)
        with pytest.raises(ValueError, match="не соответствует формату"):
            approve_link("scene_000", "chunk_x", path=reg)


# ── Self-heal: регенерация и откат не уничтожают provenance ────────────


def _stripped_registry(tmp_path: Path, keep_notes: bool = True) -> Path:
    """Реестр в чистом 4-полевом формате (имитация отката на старую ревизию)."""
    data = _real_data()
    for rec in data:
        rec.pop("_provenance_metadata", None)
        if not keep_notes:
            rec["notes"] = ""
    out = tmp_path / "stripped.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


class TestRepairAfterRevert:
    """Внешний откат файла в 4-полевой формат восстанавливается без потерь."""

    def test_repair_reattaches_metadata_and_keeps_notes(self, tmp_path: Path):
        reg = _stripped_registry(tmp_path, keep_notes=True)
        # Ключ — пара (scene, chunk): у scene_020 в реестре две связи с разными notes
        original_notes = {(r["screenplay_scene_id"], r["book_chunk_id"]): r["notes"] for r in _real_data()}

        repaired = repair_provenance(reg)
        assert repaired == len(APPROVED_PAIRS)

        data = json.loads(reg.read_text(encoding="utf-8"))
        assert len(data) == len(APPROVED_PAIRS)
        assert validate_screenplay_links(data) == []
        for rec in data:
            assert rec["_provenance_metadata"]["category"] == "AUTHOR_CANON"
            assert rec["notes"] == original_notes[(rec["screenplay_scene_id"], rec["book_chunk_id"])], "owner-notes не пережили self-heal"

    def test_reread_after_reload_after_repair(self, tmp_path: Path):
        reg = _stripped_registry(tmp_path)
        repair_provenance(reg)
        linker = ScreenplayBookLinker.from_json(reg)  # «перезагрузка» процесса
        assert len(linker.links) == len(APPROVED_PAIRS)
        for link in linker.links:
            assert link.provenance is not None, "provenance не перечитана после reload"

    def test_repair_is_noop_on_healthy_registry(self, tmp_path: Path):
        reg = _copy_registry(tmp_path)
        snapshot = reg.read_text(encoding="utf-8")
        assert repair_provenance(reg) == 0
        assert reg.read_text(encoding="utf-8") == snapshot, "здоровый файл не должен переписываться"

    def test_saving_plain_records_into_bare_file_heals_it(self, tmp_path: Path):
        """save() с базовыми записями в «обнажённый» файл восстанавливает метаданные."""
        reg = _stripped_registry(tmp_path)
        save_screenplay_links(build_approved_link_records(existing=load_existing_records()), reg)
        data = json.loads(reg.read_text(encoding="utf-8"))
        assert validate_screenplay_links(data) == []
        for rec in data:
            assert "_provenance_metadata" in rec


class TestFourFieldBackCompat:
    """Обратная совместимость: старый 4-полевой формат читается без изменений."""

    def test_bare_four_field_records_read_with_none_provenance(self, tmp_path: Path):
        reg = _stripped_registry(tmp_path)
        linker = ScreenplayBookLinker.from_json(reg)
        assert len(linker.links) == len(APPROVED_PAIRS)
        for link in linker.links:
            assert link.provenance is None
            assert (link.screenplay_scene_id, link.book_chunk_id) in APPROVED_PAIRS

    def test_linker_getters_unaffected(self, tmp_path: Path):
        linker = ScreenplayBookLinker.from_json(_copy_registry(tmp_path))
        links = linker.get_links_for_chunk("chunk_p_0006_104f39f72f26")
        assert {item.screenplay_scene_id for item in links} == {"scene_003"}
        assert linker.get_links_for_entity("scene_006") and links, "getters 4-полевого контракта нарушены"
