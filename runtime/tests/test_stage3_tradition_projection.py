# -*- coding: utf-8 -*-
"""
Этап 3 плана — Декомпозиция «10 традиций»: 1 источник + производные проекции.

Покрытие:
- проектор KNOWLEDGE -> WORLD_MODEL наполняет 10+10+37 «пустых оболочек»
  (RELIGION/RITUALS/MYTHOLOGY) содержательными производными;
- provenance честный: SYSTEM_INTERPRETATION, НЕ UNKNOWN, НЕ AUTHOR_CANON;
- каждая производная запись имеет разрешаемую DERIVED_FROM-ссылку;
- внешняя традиция в mythology-проекции называется традицией, а не «мифом книги»;
- B16: запись «Непервоначальная Традиция (Элиаде)» не содержит текстов Генона;
- зеркала KNOWLEDGE/RITUALS.json и KNOWLEDGE/COSMOLOGY.json переписаны в
  mirrors_from без дублирования контента; наполненные THEMES-items не тронуты;
- точечность: несвязанные/непустые записи не изменяются.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = REPO_ROOT / "core" / "CORE"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from world_extraction.modules.traditions import (  # noqa: E402
    mirrorize_knowledge,
    project_world_model,
)

WORLD_MODEL_DIR = CORE_DIR / "WORLD_MODEL"
KNOWLEDGE_DIR = REPO_ROOT / "core" / "KNOWLEDGE"


# ─────────────────────────────────────────────────────────────────
# Вспомогательные: временное рабочее пространство с копиями
# ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path: Path):
    """Скопировать WORLD_MODEL/*.json и KNOWLEDGE/*.json во временную папку."""
    wm = tmp_path / "WORLD_MODEL"
    kw = tmp_path / "KNOWLEDGE"
    wm.mkdir()
    kw.mkdir()
    for name in ("RELIGION.json", "RITUALS.json", "MYTHOLOGY.json"):
        shutil.copy2(WORLD_MODEL_DIR / name, wm / name)
    for name in (
        "ESOTERIC_CONNECTIONS.json",
        "SYMBOLS_DEEP.json",
        "COSMOLOGY.json",
        "RITUALS.json",
    ):
        shutil.copy2(KNOWLEDGE_DIR / name, kw / name)
    return tmp_path, wm, kw


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────
# 1. Проектор WORLD_MODEL: де-заглушка всех оболочек
# ─────────────────────────────────────────────────────────────────


class TestProjectionFillsShells:
    def test_all_blank_shells_filled(self, workspace):
        _, wm, kw = workspace
        project_world_model(wm, kw)
        for name, expected in (("RELIGION.json", 10), ("RITUALS.json", 10), ("MYTHOLOGY.json", 37)):
            data = _load(wm / name)
            blank = [r for r in data if not (r.get("description") or "").strip()]
            assert len(data) == expected, name
            assert blank == [], f"{name}: остались пустые описания: {[r['id'] for r in blank]}"

    def test_provenance_is_system_interpretation_not_canon(self, workspace):
        _, wm, kw = workspace
        project_world_model(wm, kw)
        for name in ("RELIGION.json", "RITUALS.json", "MYTHOLOGY.json"):
            data = _load(wm / name)
            for record in data:
                prov = record.get("provenance_category")
                assert prov == "SYSTEM_INTERPRETATION", f"{name}:{record['id']}: {prov}"
                assert prov != "AUTHOR_CANON"

    def test_derived_from_present_and_resolvable(self, workspace):
        _, wm, kw = workspace
        project_world_model(wm, kw)
        for name in ("RELIGION.json", "RITUALS.json", "MYTHOLOGY.json"):
            data = _load(wm / name)
            for record in data:
                derived = record.get("derived_from")
                assert derived, f"{name}:{record['id']}: нет derived_from"
                # Формат: "FILE#key[N]" или исторический "FILE.key[N]".
                assert "[" in derived and (".json" in derived), derived
                filepart, _, anchor = derived.partition("#")
                if not anchor:
                    assert ".json" in derived
                    continue
                key, _, idx = anchor.partition("[")
                idx = idx.rstrip("]")
                assert idx.isdigit(), derived
                source = _load(kw / filepart)
                entries = source.get(key, []) if isinstance(source, dict) else source
                assert int(idx) < len(entries), f"derived_from не разрешается: {derived}"

    def test_tradition_in_mythology_not_called_myth_of_book(self, workspace):
        """Внешняя традиция в mythology-проекции помечена как традиция."""
        _, wm, kw = workspace
        project_world_model(wm, kw)
        data = _load(wm / "MYTHOLOGY.json")
        for record in data:
            if record["id"].startswith("cosmo_myth_") and ("герметизм" in record["id"] or "каббала" in record["id"]):
                notes = record.get("provenance_notes", "")
                assert "внешняя эзотерическая традиция" in notes, record["id"]
            if record["id"].startswith("myth_"):
                notes = record.get("provenance_notes", "")
                assert "тема книги" in notes, record["id"]


# ─────────────────────────────────────────────────────────────────
# 2. B16: Элиаде не смешивается с Геноном
# ─────────────────────────────────────────────────────────────────


class TestB16Attribution:
    def test_eliade_record_does_not_contain_guenon_texts(self, workspace):
        _, wm, kw = workspace
        project_world_model(wm, kw)
        data = _load(wm / "MYTHOLOGY.json")
        rec = next(r for r in data if r["id"] == "cosmo_myth_непервоначальная_традиция_(элиаде)")
        desc = rec.get("description") or ""
        # Тексты Генона не должны попасть в описание «Элиаде».
        for forbidden in ("Кризис современного мира", "Царство количества", "Генон"):
            assert forbidden not in desc

    def test_esoteric_source_still_has_separate_guenon_record(self, workspace):
        """В источнике истины Б16 уже разделён: Элиаде и Генон — отдельные записи."""
        esoteric = _load(KNOWLEDGE_DIR / "ESOTERIC_CONNECTIONS.json")
        names = [t.get("name", "") for t in esoteric.get("traditions", [])]
        assert "Непервоначальная Традиция (Элиаде)" in names
        assert "Традиционализм (Генон)" in names


# ─────────────────────────────────────────────────────────────────
# 3. Зеркала KNOWLEDGE -> mirrors_from
# ─────────────────────────────────────────────────────────────────


class TestKnowledgeMirrors:
    def test_rituals_mirrored_without_duplicating_content(self, workspace):
        _, wm, kw = workspace
        mirrorize_knowledge(kw)
        data = _load(kw / "RITUALS.json")
        mirrors = [it for it in data["items"] if "mirrors_from" in it]
        assert len(mirrors) == 11  # 11 традиций — зеркала ESOTERIC
        for it in mirrors:
            assert it["mirrors_from"].startswith("ESOTERIC_CONNECTIONS.json#traditions[")
            # Контент не дублируется.
            assert not it.get("content")
            assert not (it.get("layers") or {}).get("literal")
        # Преамбула (items[0]) не является зеркалом и сохранилась.
        assert data["items"][0]["topic"] == ""

    def test_cosmology_themes_kept_and_traditions_mirrored(self, workspace):
        _, wm, kw = workspace
        mirrorize_knowledge(kw)
        data = _load(kw / "COSMOLOGY.json")
        # THEMES (0..13) сохранили контент.
        themes = data["items"][:14]
        assert all(((t.get("layers") or {}).get("literal") for t in themes if t.get("topic")))
        mirrors = [it for it in data["items"] if "mirrors_from" in it]
        assert len(mirrors) == 11
        assert all(m["mirrors_from"].startswith("ESOTERIC_CONNECTIONS.json#traditions[") for m in mirrors)

    def test_mirrors_reference_resolves(self, workspace):
        _, wm, kw = workspace
        for name in ("RITUALS.json", "COSMOLOGY.json"):
            data = _load(kw / name)
            esoteric = _load(kw / "ESOTERIC_CONNECTIONS.json")
            for it in data["items"]:
                if "mirrors_from" in it:
                    ref = it["mirrors_from"]
                    key, _, idx = ref.partition("#")[2].partition("[")
                    idx = idx.rstrip("]")
                    assert int(idx) < len(esoteric.get(key, []))
            # До применения детерминированности: проверить идемпотентность.
            snapshot = json.dumps(data, ensure_ascii=False)
            mirrorize_knowledge(kw)
            data2 = _load(kw / name)
            assert json.dumps(data2, ensure_ascii=False) == snapshot


# ─────────────────────────────────────────────────────────────────
# 4. Точечность: несвязанные/непустые записи не трогаются
# ─────────────────────────────────────────────────────────────────


class TestTargetedProjection:
    def test_non_blank_records_untouched(self, workspace):
        _, wm, kw = workspace
        # Добавим «непустую» запись в MYTHOLOGY, чтобы проверить, что её не трогают.
        path = wm / "MYTHOLOGY.json"
        data = _load(path)
        custom = {
            "id": "myth_собственный_миф",
            "name": "Собственный миф",
            "name_ru": "Собственный миф",
            "category": "mythology",
            "description": "Уже заполненное описание, не трогать.",
            "properties": {},
            "relationships": [],
            "source": "BOOK",
            "confidence": 0.9,
            "provenance_category": "AUTHOR_CANON",
            "provenance_notes": "",
            "source_level": "CANON",
        }
        data.append(custom)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        project_world_model(wm, kw)
        out = _load(path)
        rec = next(r for r in out if r["id"] == "myth_собственный_миф")
        assert rec["description"] == "Уже заполненное описание, не трогать."
        assert rec["provenance_category"] == "AUTHOR_CANON"
        assert "derived_from" not in rec

    def test_projection_idempotent(self, workspace):
        _, wm, kw = workspace
        project_world_model(wm, kw)
        for name in ("RELIGION.json", "RITUALS.json", "MYTHOLOGY.json"):
            snapshot = json.dumps(_load(wm / name), ensure_ascii=False)
            project_world_model(wm, kw)
            assert json.dumps(_load(wm / name), ensure_ascii=False) == snapshot
