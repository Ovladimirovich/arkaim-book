# Аудит идентичности World Model — промежуточный отчёт

> [!WARNING]
> **HISTORICAL — отчёт на дату аудита.** Формулировки «STOP GATE», «миграция НЕ
> реализована», «2 approved», «EN/RU записи не удаляются» ниже — состояние на момент
> отчёта. С тех пор: crosswalk v2 реализован и подключён к runtime, одобрено **3**
> соответствия (`region_arkaim`, `region_hyperborea`, `region_oceania`), EN-дубли
> (`arkaim`, `hyperborea`) удалены, 21 зеркало `geo_*` удалено (GEOGRAPHY = **17** записей).
> **Открытым остаётся** статус 7 несопоставленных регионов MAP_DATA (гейт G6) —
> см. `docs/OWNER_DECISION_SHEET.md`. Текущая карта: `docs/CURRENT_DEVELOPMENT_STATE.md`.

## Статус: ЗАВЕРШЕН сбор доказательств. Миграция НЕ реализована (STOP GATE).

---

## 1. ДОНЕ (DONE)

- Создан и выполнен аудитный скрипт `core/_wm_audit.py` (инвентаризация `WORLD_MODEL.json`, `MAP_DATA.json`, `GEOGRAPHY.json`, `WORLD_ENGINE_WORLD_MODEL.json`).
- Собраны артефакты: `_wm_audit_out.txt`, `_wm_grep_out.txt`, `_meta_out.txt`, `_wm_mid.txt`.
- Прочитаны: `world_resolver.py`, `world_model_data.py`, `world_model.py` (разделы crosswalk и `_entity_ids_for_epoch`), `source_levels.py`, `world_reference.py`, `world_engine.py`, `builder.py` (knowledge_card), `world_references.py` (роута), `test_b3b_crosswalk.py`.
- Устранены проблемы кодировки PowerShell/Кириллица — вывод через Python с `-X utf8` и `Out-File -Encoding utf8`.

---

## 2. ТЕКУЩЕЕ СОСТОЯНИЕ (CURRENT STATE)

### 2.1 Crosswalk (`core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`)

- schema_version: 1.0, status: APPROVED, scope: `B3-CW first batch`, owner_decision: `russian_canonical_location_ids`, runtime_connected: false.
- Approved mapping — только 2 записи (target_type `canonical_location`, status APPROVED, owner_reviewed true):
  1. `Аркаим` → `region_arkaim` (событие `event_arkaim_construction`, эра `arkaim_era`, гл. 11)
  2. `Гиперборея` → `region_hyperborea` (событие `event_journey_to_hyperborea`, эра `satya_yuga`, гл. 3)
- unmapped: status `PRESERVE_UNCHANGED`, policy `Do not infer mappings from similar names.` (остальные 8 регионов MAP_DATA не сопоставлены).
- В каждом approved mapping доказательства: `world_engine_source` (GEOGRAPHY.json), `external_source` (MAP_DATA.json), `canonical_location` (WORLD_MODEL.json), `canonical_event_link` (WORLD_MODEL.json).

### 2.2 MAP_DATA (`core/KNOWLEDGE/MAP_DATA.json`)

- `_provenance_metadata`: `{category: EXTERNAL_SOURCE, source_level: HISTORICAL, notes: "Map data from external sources", enriched_at: "Milestone B"}`.
- 10 регионов: `hyperborea`, `arkaim`, `gardarika`, `sintashta`, `oceania`, `mehenjo`, `sumer`, `gobekli`, `bolgar`, `lepeni_vir` (код IDs — латиница, имена — кириллица).

### 2.3 GEOGRAPHY (`core/CORE/WORLD_MODEL/GEOGRAPHY.json`)

- 10 сущностей `region_*`: `region_arkaim`, `region_bolgar`, `region_gardarika`, `region_gobekli`, `region_hyperborea`, `region_lepeni_vir`, `region_mehenjo`, `region_oceania`, `region_sintashta`, `region_sumer`.
- `region_arkaim` и `region_hyperborea` утверждены в crosswalk; остальные 8 — нет.

### 2.4 Логика заполнения `entity_ids` (`world_model.py:_entity_ids_for_epoch`)

- Используется только `_load_approved_crosswalk()` (файл crosswalk, статус APPROVED, target_type canonical_location).
- Если crosswalk пуст → `[]`.
- По событиям: если `ev.epoch == epoch_id` и `ev.location_id` есть в crosswalk → добавляются `mapping[ev.location_id]`; результат сортируется.
- Никаких выводов по названию, нет опоры на пустое `Location.epochs_present`.
- Результат:
  - `arkaim_era` → `[region_arkaim]` (событие `event_arkaim_construction` → `Аркаим`)
  - `satya_yuga` → `[region_hyperborea]` (событие `event_journey_to_hyperborea` → `Гиперборея`)
  - все остальные эпохи → `[]`.

### 2.5 Потребители crosswalk в рантайме

1. `world_model._load_approved_crosswalk()` → `_entity_ids_for_epoch()` → `get_temporal_node()` → `get_temporal_chain()` → эндпоинты `/book/temporal/*` (TemporalChain/TemporalNode, контракт `arkaim-web/src/shared/api/contracts/temporal.ts`).
2. `knowledge_card/builder.py:_approved_rag_aliases(canonical_id)` — обратный поиск: ищет `target_id`, где `canonical_id` входит в `world_engine_ids` crosswalk; используется при RAG-запросах без создания новой идентичности.
3. `runtime/core/routes/world_references.py:POST /knowledge/world/resolve` → `WorldKnowledgeResolver.resolve(query)` → approved crosswalk (не создаёт идентичности, не расширяет crosswalk).

### 2.6 Тесты, завязанные на `entity_ids` / crosswalk

- `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`:
  - `test_real_data_contains_only_approved_links`: `arkaim_node["entity_ids"] == ["region_arkaim"]`, `satya_yuga == ["region_hyperborea"]`, остальные `[]`.
  - `test_model_uses_only_supplied_approved_mapping`: монкепатч crosswalk → `{"аркаим": ["region_arkaim"]}`.
  - `test_empty_crosswalk_fails_closed`: пустой crosswalk → `[]`.
- Фронтенд (`arkaim-web`): `temporal/page.tsx`, `world-engine/page.tsx` фильтруют узлы по `node.entity_ids?.includes(entityId)`; контракт `temporal.ts: entity_ids: string[]`.

---

## 3. ЦЕЛЕВАЯ МОДЕЛЬ ИДЕНТИЧНОСТИ (TARGET IDENTITY MODEL)

Принят третий вариант: **стабильная языконезависимая идентичность**; русский текстовый ID не является каноническим.

- CANON / DERIVED и provenance разделяются.
- EN/RU — это метки/алиасы (labels/aliases), а не ID.
- Русский текстовый ID — не канон.
- 7 регионов из MAP_DATA не добавляются в canon пока; provenance/status устанавливаются отдельно.
- EN/RU записи не удаляются сейчас.

Пример целевой структуры сущности:
```json
{
  "canonical_id": "region_arkaim",
  "provenance": { "category": "AUTHOR_CANON", "source_level": "CANON", "confidence": 1.0 },
  "labels": { "en": "Arkaim", "ru": "Аркаим" },
  "aliases": ["аркаим", "Arkaim"],
  "crosswalk_status": "APPROVED"
}
```

---

## 4. ВЛИЯНИЕ МИГРАЦИИ (MIGRATION IMPACT)

### 4.1 Файлы, подлежащие изменению (без реализации миграции)

Backend:
- `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` — схема crosswalk: добавить поля про standings (CANON/DERIVED), provenance, language-agnostic stable ID.
- `core/CORE/narrative_engine/world_model.py` — `_load_approved_crosswalk()`, `_entity_ids_for_epoch()`, `get_temporal_node()` — перейти на stable canonical_id вместо ru-ID.
- `core/CORE/knowledge/world_resolver.py` — резолвер идентичности (уже разделяет RESOLVED/UNRESOLVED/AMBIGUOUS/CROSSWALK_UNAPPROVED).
- `core/CORE/knowledge_card/builder.py` — `_approved_rag_aliases()` — обратный алиас-кроссу.
- `core/CORE/schemas/world_reference.py` — `WorldEntityReference` (уже есть boundary контракт).
- `core/CORE/narrative_engine/source_levels.py` — `ProvenanceCategory` / `SourceLevel` (уже есть двухмерная модель).

Frontend:
- `arkaim-web/src/shared/api/contracts/temporal.ts` — `TemporalNode.entity_ids: string[]`.
- `arkaim-web/src/app/temporal/page.tsx`, `world-engine/page.tsx` — фильтрация по `entity_ids`.
- `arkaim-web/src/shared/ui/*` (EntityCard, KnowledgeTraceCard, WorldProvenanceCard, StateView) — отображение provenance/metки.

Тесты:
- `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py` — ожидания `entity_ids`.
- `arkaim-web/tests/e2e/world-temporal.spec.ts`, `tests/unit/world.test.ts` — ожидания `entity_ids`.

### 4.2 Что НЕ трогать в этом этапе

- Не удалять EN/RU записи.
- Не добавлять 7 оставшихся регионов MAP_DATA в canon (provenance/status отдельно).
- Не реализовывать автомиграцию данных (STOP GATE).
- Не менять публичный API contract без решения OWNER.

---

## 5. OWNER-GATE

Требуется решение владельца по следующим вопросам:

1. **Канонический stable ID**: оставить `region_*` (из GEOGRAPHY) или ввести новый language-agnostic ID (например, UUID/slug без привязки к языку).
2. **Статус 7 незамапленных регионов MAP_DATA**: утвердить provenance (EXTERNAL_SOURCE/HISTORICAL) и статус (PRESERVE_UNCHANGED vs 후보 для canon).
3. **Схема crosswalk v2**: добавить ли поля `provenance`, `category`, `canonical_id`, `labels` в `WORLD_ENGINE_WORLD_MODEL.json`.
4. **Порядок миграции**: поэтапно (сперва дуализм ID → poi только new records) или полный ребазелинг.

Пока gate открыт — код и данные не мигрируются.

---

## 6. БЛИЖАЙШИЕ ШАГЫ (до Owner-Go)

1. Подготовить черновик миграционного плана (см. файл `_wm_migration_plan.md`): перечень изменений, карта зависимостей, тесты, критерии приёмки.
2. Согласовать с OWNER пункты Owner-Gate (раздел 5).
3. После одобрения — реализовать миграцию и обновить тесты.
4. Прогон regression: `make test-backend`, `make test-frontend`, `make lint`.

---

## 7. ДАЛЬНЯЯ ПЕРСПЕКТИВА

- Полный ребазелинг Arkaim к языконезависимой стабильной идентичности World Model.
- EN/RU = только labels/aliases; CANON/DERIVED + provenance отдельно.
- Вся запись идентичности через crosswalk v2 с provenance.
- Фронтенд отображает stable canonical_id + локализованные лейблы.
