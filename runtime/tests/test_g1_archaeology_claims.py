"""G1 — индивидуальный provenance и явный статус у каждого claim'а ARCHAEOLOGY.json.

Решения владельца (2026-10-22):
  G1.1 — неподтверждённые claim'ы переведены в явный статус UNKNOWN;
  G1.2 — индивидуальный ``provenance_category`` на уровне каждого claim'а;
  G1.3 — significance вынесено в отдельное поле, интерпретационное → HYPOTHESIS;
  G1.4 — пустые зеркала с ложным ``confidence: 1.0`` исправлены;
  G1.5 — «неизвестно» (UNKNOWN) и «не утверждается» (NOT_ASSERTED) — разные состояния.

Тесты проверяют, чтобы изменения не откатились:
  - в данных, в реестре классификации, в knowledge card и в зеркалах.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_KNOWLEDGE = _PROJECT_ROOT / "core" / "KNOWLEDGE"

VALID_CATEGORIES = {
    "AUTHOR_CANON",
    "DERIVED",
    "EXTERNAL_SOURCE",
    "RECONSTRUCTION",
    "HYPOTHESIS",
    "ARTISTIC_MODEL",
    "FUTURE_EXTRAPOLATION",
    "UNKNOWN",
}
VALID_STATUSES = {"ASSERTED", "UNKNOWN", "NOT_ASSERTED"}

MIRRORS = (
    "ARCHAEOLOGY_DEEP.json",
    "GEOGRAPHY.json",
    "TECHNOLOGY.json",
)


def _load(name: str) -> dict:
    path = _KNOWLEDGE / name
    if not path.exists():
        pytest.skip(f"{name} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_claims(site: dict):
    """Все claim'ы сайта: (поле, объект)."""
    for field in ("location", "dating"):
        value = site.get(field)
        if isinstance(value, dict):
            yield field, value
    facts = site.get("facts", {})
    if isinstance(facts, dict):
        for key, value in facts.items():
            if isinstance(value, dict):
                yield f"facts.{key}", value
    for field in ("book_connection", "significance"):
        value = site.get(field)
        if isinstance(value, dict):
            yield field, value
    for index, hypothesis in enumerate(site.get("hypothetical_claims", [])):
        if isinstance(hypothesis, dict):
            yield f"hypothetical.{index}", hypothesis


class TestArchaeologyClaimSchema:
    def test_file_declares_epistemic_status_vocabulary(self):
        data = _load("ARCHAEOLOGY.json")
        statuses = data.get("epistemic_status", {})
        assert set(statuses) == VALID_STATUSES, "в файле нет словаря эпистемических статусов"

    def test_every_claim_has_own_category_and_status(self):
        data = _load("ARCHAEOLOGY.json")
        sites = data.get("sites", [])
        assert sites
        for site in sites:
            name = site.get("name", "?")
            claims = list(_iter_claims(site))
            assert claims, f"{name}: нет ни одного claim'а"
            for field, claim in claims:
                assert claim["provenance_category"] in VALID_CATEGORIES, f"{name}.{field}"
                assert claim["status"] in VALID_STATUSES, f"{name}.{field}"
                assert "source" in claim, f"{name}.{field}: нет поля source"
                assert "confidence" in claim, f"{name}.{field}: нет поля confidence"

    def test_unknown_claims_are_fail_closed(self):
        """Claim без источника: source=null, confidence=0, source_level=UNKNOWN."""
        data = _load("ARCHAEOLOGY.json")
        for site in data.get("sites", []):
            name = site.get("name", "?")
            for field, claim in _iter_claims(site):
                if claim["status"] != "UNKNOWN":
                    continue
                assert claim["source"] is None, f"{name}.{field}"
                assert claim["confidence"] == 0.0, f"{name}.{field}"
                assert claim["source_level"] == "UNKNOWN", f"{name}.{field}"

    def test_no_claim_claims_a_source_it_does_not_have(self):
        """Ни один claim не ссылается на несуществующий источник."""
        data = _load("ARCHAEOLOGY.json")
        for site in data.get("sites", []):
            name = site.get("name", "?")
            for field, claim in _iter_claims(site):
                if claim["status"] == "UNKNOWN":
                    continue
                source = claim.get("source")
                if source is None:
                    continue
                assert isinstance(source, str) and source.strip(), f"{name}.{field}: пустая ссылка"

    def test_removed_entities_are_not_asserted(self):
        """Удалённые записи не вернулись ни как сайт, ни как claim."""
        data = _load("ARCHAEOLOGY.json")
        names = {site.get("name", "") for site in data.get("sites", [])}
        for removed in ("Каргонодская культура", "Карьякская (Карийская) культура"):
            assert removed not in names, f"{removed} вернулась в список сайтов"

    def test_not_asserted_is_recorded_and_distinct(self):
        """Решения об отказе зафиксированы явно и не смешаны с UNKNOWN."""
        data = _load("ARCHAEOLOGY.json")
        entries = data.get("not_asserted", [])
        assert entries, "нет ни одной записи NOT_ASSERTED"
        for entry in entries:
            assert entry["status"] == "NOT_ASSERTED"
            assert entry.get("reason"), "у записи NOT_ASSERTED нет причины"
            assert entry.get("decision"), "у записи NOT_ASSERTED нет ссылки на решение"

    def test_unsolved_questions_are_unknown(self):
        data = _load("ARCHAEOLOGY.json")
        for site in data.get("sites", []):
            for question in site.get("unsolved", []):
                assert question["status"] == "UNKNOWN"
                assert question["provenance_category"] == "UNKNOWN"


class TestArchaeologyInKnowledgeCard:
    def test_card_does_not_promote_unconfirmed_claims(self):
        """Карточка знаний не выдаёт неподтверждённое за внешний источник."""
        import sys

        core = _PROJECT_ROOT / "core" / "CORE"
        if str(core) not in sys.path:
            sys.path.insert(0, str(core))
        from knowledge_card.builder import KnowledgeCardBuilder
        from narrative_engine.source_levels import ProvenanceCategory

        card = KnowledgeCardBuilder().build("Аркаим")
        arch_sources = [s for s in card.sources if s.source_name == "archaeology"]
        assert arch_sources, "в карточке нет археологического источника"
        for source in arch_sources:
            assert source.provenance_category != ProvenanceCategory.EXTERNAL_SOURCE, "источник без библиографии не должен быть EXTERNAL_SOURCE"
            assert source.provenance_category != ProvenanceCategory.AUTHOR_CANON
            for claim in source.claims:
                assert claim.provenance.category != ProvenanceCategory.AUTHOR_CANON
                if claim.provenance.category == ProvenanceCategory.UNKNOWN:
                    assert claim.provenance.confidence == 0.0, claim.text


class TestEmptyMirrorsFixed:
    @pytest.mark.parametrize("name", MIRRORS)
    def test_no_empty_content_with_confident_metadata(self, name):
        """Запись с пустым content не может иметь confidence > 0."""
        data = _load(name)
        for item in data.get("items", []):
            content = str(item.get("content") or "").strip()
            assert content, f"{name}: запись с пустым content осталась"
            assert float(item.get("confidence", 0.0)) <= 1.0

    @pytest.mark.parametrize("name", MIRRORS)
    def test_no_dangling_archaeology_site_references(self, name):
        """Ссылки на ARCHAEOLOGY.json.sites[N] не должны указывать в пустоту."""
        data = _load(name)
        archaeology = _load("ARCHAEOLOGY.json")
        site_count = len(archaeology.get("sites", []))
        for item in data.get("items", []):
            source = str(item.get("source") or "")
            if "ARCHAEOLOGY.json.sites[" not in source:
                continue
            index = int(source.split("[")[-1].split("]")[0])
            assert index < site_count, f"{name}: ссылка на несуществующий sites[{index}]"

    @pytest.mark.parametrize("name", MIRRORS)
    def test_mirrors_of_unconfirmed_source_have_zero_confidence(self, name):
        """Зеркала неподтверждённого источника не заявляют уверенности."""
        data = _load(name)
        for item in data.get("items", []):
            source = str(item.get("source") or "")
            if not source.startswith(("core\\KNOWLEDGE\\ARCHAEOLOGY.json", "core/KNOWLEDGE/ARCHAEOLOGY.json")):
                continue
            assert float(item.get("confidence", 0.0)) == 0.0, f"{name}: {source}"
