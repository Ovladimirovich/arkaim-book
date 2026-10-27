"""Тесты гейта на вход внешнего знания (Этап 2 плана).

Проверяем контракт «Единый источник истины для внешних знаний»:
- обязательные поля source / origin_layer / book_link_status;
- запись, претендующая на AUTHOR_CANON вне первичного канонического файла,
  отклоняется (факт-чек гейт, тип B16);
- пример «Элиаде/Генон» (производная традиция с заявкой на канон) ловится.
"""

import sys
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from narrative_engine.provenance.external_gate import (  # noqa: E402
    BOOK_LINK_STATUSES,
    OriginLayer,
    check_external_record,
    validate_external_record,
)


# ── Helpers ───────────────────────────────────────────────────────────────


def _valid_record(**overrides) -> dict:
    record = {
        "name": "Новая традиция",
        "source": "ESOTERIC_CONNECTIONS.json#traditions[11]",
        "origin_layer": OriginLayer.EXTERNAL_FACT.value,
        "provenance_category": "EXTERNAL_SOURCE",
    }
    record.update(overrides)
    return record


# ── Правило 1: source обязателен ──────────────────────────────────────────


class TestSourceRequired:
    def test_missing_source_rejected(self):
        result = validate_external_record(_valid_record(source=None), target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False

    def test_empty_source_rejected(self):
        result = validate_external_record(_valid_record(source="   "), target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False

    def test_unknown_source_accepted(self):
        """Честный UNKNOWN допустим — гейт не требует придуманную ссылку."""
        result = validate_external_record(_valid_record(source="UNKNOWN"), target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is True

    def test_real_source_accepted(self):
        result = validate_external_record(_valid_record(source="ARCHAEOLOGY.json#site[5]"), target_file="ARCHAEOLOGY.json")
        assert result.valid is True


# ── Правило 4: origin_layer обязателен и из допустимого набора ────────────


class TestOriginLayer:
    def test_missing_origin_layer_rejected(self):
        result = validate_external_record(_valid_record(origin_layer=None), target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False

    def test_invalid_origin_layer_rejected(self):
        result = validate_external_record(_valid_record(origin_layer="SOMETHING"), target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False

    def test_valid_layers_accepted(self):
        for layer in OriginLayer:
            # BOOK_LINK по контракту требует book_link_status — добавляем его.
            record = _valid_record(origin_layer=layer.value)
            if layer == OriginLayer.BOOK_LINK:
                record["book_link_status"] = "VERIFIED"
            result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
            assert result.valid is True, f"origin_layer={layer} должен быть принят"


# ── Правило 2: book_link_status для BOOK_LINK ─────────────────────────────


class TestBookLinkStatus:
    def test_book_link_requires_status(self):
        record = _valid_record(origin_layer=OriginLayer.BOOK_LINK.value)
        record.pop("book_link_status", None)
        result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False

    def test_book_link_null_status_rejected(self):
        record = _valid_record(origin_layer=OriginLayer.BOOK_LINK.value, book_link_status=None)
        result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False

    def test_book_link_valid_status_accepted(self):
        for status in BOOK_LINK_STATUSES:
            record = _valid_record(
                origin_layer=OriginLayer.BOOK_LINK.value,
                book_link_status=status,
            )
            result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
            assert result.valid is True, f"book_link_status={status} должен быть принят"

    def test_non_book_link_no_status_ok(self):
        """EXTERNAL_FACT / SYSTEM_INTERPRETATION не требуют book_link_status."""
        for layer in (OriginLayer.EXTERNAL_FACT, OriginLayer.SYSTEM_INTERPRETATION):
            record = _valid_record(origin_layer=layer.value)
            record.pop("book_link_status", None)
            result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
            assert result.valid is True


# ── Правило 3 + B16: заявка на CANON вне канонического файла ──────────────


class TestFalseCanonGate:
    def test_canon_claim_in_external_file_rejected(self):
        """Запись в ESOTERIC_CONNECTIONS (не канон) не может претендовать на AUTHOR_CANON."""
        record = _valid_record(
            provenance_category="AUTHOR_CANON",
            book_link_status="VERIFIED",
        )
        result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False
        assert any("AUTHOR_CANON" in e for e in result.errors())

    def test_canon_claim_unknown_file_rejected(self):
        """Файл не известен реестру — заявка на канон отклоняется (файл-канон неизвестен)."""
        record = _valid_record(provenance_category="AUTHOR_CANON")
        result = validate_external_record(record, target_file="UNKNOWN_FILE.json")
        assert result.valid is False

    def test_canon_claim_in_canon_file_accepted(self):
        """В первичном каноническом файле AUTHOR_CANON допустим."""
        record = _valid_record(
            provenance_category="AUTHOR_CANON",
            origin_layer=OriginLayer.EXTERNAL_FACT.value,
        )
        result = validate_external_record(record, target_file="BOOK_DOCUMENT.json")
        assert result.valid is True

    def test_eliade_genon_example_caught(self):
        """Б16: производная традиция 'Элиаде' со ссылкой на Генона — пример записи,
        которая НЕ является первичным каноном и должна быть отклонена при заявке на канон."""
        record = _valid_record(
            name="Непервоначальная Традиция (Элиаде)",
            key_text="Рене Генон: «Кризис современного мира»",
            provenance_category="AUTHOR_CANON",
            origin_layer=OriginLayer.EXTERNAL_FACT.value,
        )
        result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is False, "Заявка на канон производной традиции должна быть отклонена гейтом"

    def test_derived_interp_record_accepted(self):
        """Честная системная интерпретация с source и DERIVED — принимается."""
        record = _valid_record(
            provenance_category="DERIVED",
            origin_layer=OriginLayer.SYSTEM_INTERPRETATION.value,
        )
        result = validate_external_record(record, target_file="ESOTERIC_CONNECTIONS.json")
        assert result.valid is True


# ── Вспомогательные интерфейсы ────────────────────────────────────────────


class TestHelpers:
    def test_check_external_record_bool(self):
        assert check_external_record(_valid_record(), "ESOTERIC_CONNECTIONS.json") is True
        assert check_external_record(_valid_record(source=None), "ESOTERIC_CONNECTIONS.json") is False

    def test_warnings_returned_not_fatal(self):
        """UNKNOWN-категория — предупреждение, не блокировка."""
        result = validate_external_record(
            _valid_record(provenance_category="UNKNOWN"),
            target_file="ESOTERIC_CONNECTIONS.json",
        )
        assert result.valid is True
        assert len(result.warnings()) >= 1

    def test_target_file_type_checked(self):
        with pytest.raises(TypeError):
            validate_external_record(_valid_record(), target_file=123)
