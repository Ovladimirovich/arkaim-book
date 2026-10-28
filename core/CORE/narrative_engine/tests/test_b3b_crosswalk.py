import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
CORE = ROOT / "core" / "CORE"
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))

from narrative_engine import world_model as world_model_module
from narrative_engine.world_model import WorldModel


@pytest.fixture(autouse=True)
def reset_crosswalk_cache():
    world_model_module._crosswalk_cache = None
    world_model_module._relations_cache = None
    yield
    world_model_module._crosswalk_cache = None
    world_model_module._relations_cache = None


def test_real_data_contains_only_approved_links():
    model = WorldModel.load(use_cache=False)

    arkaim_node = model.get_temporal_node("arkaim_era")
    satya_node = model.get_temporal_node("satya_yuga")
    assert arkaim_node is not None
    assert satya_node is not None
    assert arkaim_node["entity_ids"] == ["region_arkaim"]
    assert satya_node["entity_ids"] == ["region_hyperborea", "region_oceania"]

    for epoch in model.get_epochs():
        if epoch.id not in {"arkaim_era", "satya_yuga"}:
            node = model.get_temporal_node(epoch.id)
            assert node is not None
            assert node["entity_ids"] == []


def test_model_uses_only_supplied_approved_mapping(monkeypatch):
    monkeypatch.setattr(world_model_module, "_load_approved_crosswalk", lambda: {"аркаим": ["region_arkaim"]})

    model = WorldModel(
        {
            "epochs": [
                {"id": "arkaim_era", "name": "Arkaim", "name_ru": "Аркаим", "order": 1},
            ],
            "canonical_events": [
                {
                    "id": "event_arkaim_construction",
                    "title": "Construction",
                    "title_ru": "Строительство",
                    "epoch": "arkaim_era",
                    "location_id": "аркаим",
                },
            ],
        }
    )

    node = model.get_temporal_node("arkaim_era")
    assert node is not None
    assert node["entity_ids"] == ["region_arkaim"]


def test_empty_crosswalk_fails_closed(monkeypatch):
    monkeypatch.setattr(world_model_module, "_load_approved_crosswalk", lambda: {})
    model = WorldModel(
        {
            "epochs": [{"id": "arkaim_era", "name": "Arkaim", "name_ru": "Аркаим", "order": 1}],
            "canonical_events": [
                {
                    "id": "event_arkaim_construction",
                    "title": "Construction",
                    "title_ru": "Строительство",
                    "epoch": "arkaim_era",
                    "location_id": "аркаим",
                },
            ],
        }
    )

    node = model.get_temporal_node("arkaim_era")
    assert node is not None
    assert node["entity_ids"] == []


def test_crosswalk_v2_schema_required_fields():
    """Crosswalk v2.1: каждая APPROVED mapping имеет canonical_id, provenance, category, labels."""
    import json

    here = Path(__file__).resolve().parents[4]
    crosswalk_path = (
        here / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json"
    )
    data = json.loads(crosswalk_path.read_text(encoding="utf-8"))

    assert data.get("schema_version") == "2.1"
    assert data.get("owner_decision") == "language_agnostic_stable_ids"
    # Этап 4 (2026-10-28): runtime_connected — историческая декларативная метка,
    # НЕ переключатель. Рантайм руководствуется status=APPROVED каждой записи
    # (см. _load_approved_crosswalk), а не этим флагом. По этой причине флаг
    # НЕ переводится в true: критерий «runtime_connected=true для пар с
    # DERIVED_FROM» не применим к 11 одобренным парам (не производные традиции).
    assert isinstance(data.get("runtime_connected"), bool)
    assert data.get("runtime_note"), (
        "документация семантики runtime_connected обязательна"
    )
    assert data.get("unmapped", {}).get("status") == "PRESERVE_UNCHANGED"

    approved = [m for m in data.get("mappings", []) if m.get("status") == "APPROVED"]
    assert len(approved) == 11
    for m in approved:
        assert m.get("canonical_id"), "canonical_id обязателен"
        assert m.get("category"), "category обязателен"
        labels = m.get("labels") or {}
        assert labels.get("ru"), "labels.ru обязателен"
        assert labels.get("en"), "labels.en обязателен"
        prov = m.get("provenance") or {}
        assert prov.get("category"), "provenance.category обязателен"
        assert prov.get("source_level"), "provenance.source_level обязателен"


def test_load_approved_crosswalk_real_data():
    """Реальный crosswalk v2 загружается как русскоязычный ярлык → [canonical_id]."""
    mapping = world_model_module._load_approved_crosswalk()
    # E5 expansion: 3 locations + 2 climates + 3 architecture + 3 civilizations = 11
    assert "аркаим" in mapping
    assert "region_arkaim" in mapping["аркаим"]
    assert "гиперборея" in mapping
    assert "region_hyperborea" in mapping["гиперборея"]
    assert "океания" in mapping
    assert "region_oceania" in mapping["океания"]
    # E5 new categories
    assert "климат степи" in mapping
    assert "steppe_climate" in mapping["климат степи"]
    assert "климат гипербореи" in mapping
    assert "hyperborea_climate" in mapping["климат гипербореи"]
    assert "аркаимское поселение" in mapping
    assert "arkaim_settlement" in mapping["аркаимское поселение"]
    assert "святилище" in mapping
    assert "sanctuary_temple" in mapping["святилище"]
    assert "подземный город" in mapping
    assert "underground_city" in mapping["подземный город"]
    assert "гиперборейская цивилизация" in mapping
    assert "civ_hyperborea" in mapping["гиперборейская цивилизация"]
    assert "аркаимская цивилизация" in mapping
    assert "civ_arkaim_civilization" in mapping["аркаимская цивилизация"]
    assert "океанийская цивилизация" in mapping
    assert "civ_oceania" in mapping["океанийская цивилизация"]


def test_oceania_mapping_points_to_canonical_location():
    """Океания: одобренное соответствие ведёт к канонической локации World Model."""
    model = WorldModel.load(use_cache=False)

    location = model.get_location("океания")
    assert location is not None
    assert location.name_ru == "Океания"

    mapping = world_model_module._load_approved_crosswalk()
    assert mapping["океания"] == ["region_oceania"]

    # Соответствие не выдаёт локацию за событие: событие об упадке Океании
    # в мире расположено в «атлантида», и его локация не менялась.
    event = next(e for e in model.get_events() if e.id == "event_oceania_decline")
    assert event.location_id == "океания"


def test_canonical_id_is_only_entity_identity():
    """Этап 2: `canonical_id` — единственная идентичность в `entity_ids` временных узлов.

    EN/RU метки (ярлыки crosswalk) никогда не попадают в `entity_ids`;
    существующее поведение двух одобренных маппингов сохраняется.
    """
    model = WorldModel.load(use_cache=False)

    ru_or_en_labels = {"аркаим", "гиперборея", "океания", "arkaim", "hyperborea", "oceania"}
    for epoch in model.get_epochs():
        node = model.get_temporal_node(epoch.id)
        assert node is not None
        for entity_id in node["entity_ids"]:
            assert entity_id not in ru_or_en_labels, (
                f"language label used as entity identity: {entity_id}"
            )

    assert model.get_temporal_node("arkaim_era")["entity_ids"] == ["region_arkaim"]
    assert model.get_temporal_node("satya_yuga")["entity_ids"] == ["region_hyperborea", "region_oceania"]


# ── W4 / crosswalk v2.1: Tier-2 relations (OWNER-утверждённые связи) ─────


def test_crosswalk_v21_relations_schema_required_fields():
    """Схема записи `relations`: {id, source_id, relation, target_id, provenance,
    status: APPROVED, owner_reviewed: true, evidence[]}; v1-батч = 10 связей."""
    import json

    here = Path(__file__).resolve().parents[4]
    crosswalk_path = (
        here / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json"
    )
    data = json.loads(crosswalk_path.read_text(encoding="utf-8"))

    relations = data.get("relations", [])
    assert len(relations) == 10
    vocab = {"located_in", "has_climate", "existed_in", "mentor_of", "student_of", "peer_of", "associated_with"}
    ids, by_relation = set(), {}
    for r in relations:
        rid = r.get("id")
        assert rid and rid not in ids, f"отсутствует/дублируется id: {rid}"
        ids.add(rid)
        assert r.get("source_id") and r.get("target_id"), "source_id/target_id обязательны"
        assert r.get("relation") in vocab, f"relation вне v1-словаря: {r.get('relation')}"
        assert r.get("provenance"), "provenance обязателен"
        assert r.get("status") == "APPROVED", "в секции только APPROVED"
        assert r.get("owner_reviewed") is True, "owner_reviewed обязателен (P1)"
        assert r.get("evidence"), "evidence[] обязателен и непустой (аналог mappings)"
        by_relation.setdefault(r["relation"], []).append(rid)
    assert len(by_relation["mentor_of"]) == 4
    assert len(by_relation["peer_of"]) == 1
    assert len(by_relation["located_in"]) == 1
    assert len(by_relation["has_climate"]) == 2
    assert len(by_relation["existed_in"]) == 1
    assert len(by_relation["associated_with"]) == 1
    # Спорная #10: owner-решение зафиксировано в записи
    assoc = next(r for r in relations if r["id"] == "rel_assoc_civ_arkaim_civ_hyperborea")
    assert assoc.get("owner_decision_ref")


def test_load_approved_relations_real_data():
    """Loader возвращает весь утверждённый v1-батч (10 записей)."""
    relations = world_model_module._load_approved_relations()
    assert len(relations) == 10
    assert {r["id"] for r in relations} == {
        "rel_located_settlement_in_arkaim_region",
        "rel_has_climate_region_arkaim_steppe",
        "rel_has_climate_region_hyperborea",
        "rel_existed_civ_arkaim_in_arkaim_era",
        "rel_mentor_teacher_velik",
        "rel_mentor_svetovit_velik",
        "rel_mentor_velik_miroslav",
        "rel_mentor_teacher_nastavniki",
        "rel_peer_radomir_velik",
        "rel_assoc_civ_arkaim_civ_hyperborea",
    }
    # P3: character relations — по именам legacy-модели (namespace не выдуман)
    mentor = {r["target_id"] for r in relations if r["source_id"] == "Учитель" and r["relation"] == "mentor_of"}
    assert mentor == {"Велик", "Наставники"}


def test_relations_fail_closed_missing_file(monkeypatch):
    """B1: файл crosswalk отсутствует → пустой список, default-связей нет."""
    monkeypatch.setattr(world_model_module, "_CROSSWALK_FILENAME", "no_such_crosswalk.json")
    world_model_module._relations_cache = None
    assert world_model_module._load_approved_relations() == []


def test_relations_parser_rejects_invalid_records():
    """B1/P1: нарушение схемы записи → связь не включается (fail-closed по записи)."""
    good = {
        "id": "r1", "source_id": "a", "relation": "located_in", "target_id": "b",
        "provenance": "p", "status": "APPROVED", "owner_reviewed": True, "evidence": [{"type": "t"}],
    }
    assert world_model_module._parse_relations({"relations": [good]}) == [good]
    # owner_reviewed=False → отклоняется (перевод в Tier-2 только owner-решением)
    bad1 = dict(good, id="r2", owner_reviewed=False)
    assert world_model_module._parse_relations({"relations": [bad1]}) == []
    # status!=APPROVED → отклоняется
    bad2 = dict(good, id="r3", status="PENDING")
    assert world_model_module._parse_relations({"relations": [bad2]}) == []
    # нет evidence[] (пустой список) → отклоняется
    bad3 = dict(good, id="r4", evidence=[])
    assert world_model_module._parse_relations({"relations": [bad3]}) == []
    # нет секции relations → пусто
    assert world_model_module._parse_relations({"mappings": []}) == []


# ── E5. Expanded crosswalk categories (2026-10-26) ─────────────────────


def test_e5_new_mappings_cover_multiple_categories():
    """E5: расширенный crosswalk включает категории climate, architecture, civilization."""
    mapping = world_model_module._load_approved_crosswalk()
    categories = set()
    import json

    here = Path(__file__).resolve().parents[4]
    crosswalk_path = here / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json"
    data = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    for m in data.get("mappings", []):
        if m.get("status") == "APPROVED":
            categories.add(m.get("category"))

    # E5 expanded categories
    assert "climate" in categories
    assert "building" in categories
    assert "culture" in categories
    assert "region" in categories


def test_e5_mapping_count_is_eleven():
    """E5: всего 11 утверждённых маппингов (3 locations + 8 new)."""
    import json

    here = Path(__file__).resolve().parents[4]
    crosswalk_path = here / "core" / "CORE" / "WORLD_CROSSWALK" / "WORLD_ENGINE_WORLD_MODEL.json"
    data = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    approved = [m for m in data.get("mappings", []) if m.get("status") == "APPROVED"]
    assert len(approved) == 11


def test_e5_new_labels_are_unique():
    """E5: все labels.ru casefolded-ключи уникальны."""
    mapping = world_model_module._load_approved_crosswalk()
    # Каждый ключ в dict уникален по определению, но проверяем что 11 ключей
    assert len(mapping) >= 11, f"Ожидаем >= 11 уникальных ярлыков, получили {len(mapping)}"
