# Миграционный план: ребазелинг идентичности World Model (черновик)

> [!WARNING]
> **HISTORICAL — отчёт на дату аудита.** Формулировки «STOP GATE», «миграция НЕ
> реализована», «2 approved», «EN/RU записи не удаляются» ниже — состояние на момент
> отчёта. С тех пор: crosswalk v2 реализован и подключён к runtime, одобрено **3**
> соответствия (`region_arkaim`, `region_hyperborea`, `region_oceania`), EN-дубли
> (`arkaim`, `hyperborea`) удалены, 21 зеркало `geo_*` удалено (GEOGRAPHY = **17** записей).
> Гейт G6 закрыт решением владельца от 2026-10-22: 7 несопоставленных регионов
> MAP_DATA остаются несопоставленными (`PRESERVE_UNCHANGED`, зафиксировано в crosswalk-
> артефакте). Текущая карта: `docs/CURRENT_DEVELOPMENT_STATE.md`.

## Статус: ЧЕРНОВИК. Миграция НЕ реализована (STOP GATE). Ожидает Owner-Go.

Цель: переход к языконезависимой стабильной идентичности, где EN/RU — только лейблы/алиасы, а CANON/DERIVED и provenance разделены.

---

## Область применения (scope)

Изменяется только идентичность геолокаций (регионы). Не затрагиваются события, цивилизации, технологии, если OWNER не расширит scope.

Текущее:
- Crosswalk утверждён только для 2 регионов: `Аркаим→region_arkaim`, `Гиперборея→region_hyperborea`.
- 8 регионов MAP_DATA не сопоставлены (`PRESERVE_UNCHANGED`).
- `entity_ids` заполняются только из approved crosswalk через `_entity_ids_for_epoch`.

---

## Список затрагиваемых файлов (без изменений пока)

### Backend (Runtime + CORE)

| Файл | Что меняется | Примечание |
|------|--------------|------------|
| `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` | Схема crosswalk v2: добавить `canonical_id`, `provenance`, `category`, `labels` | Статус APPROVED сохраняется |
| `core/CORE/narrative_engine/world_model.py` | `_load_approved_crosswalk`, `_entity_ids_for_epoch`, `get_temporal_node` | Переход на stable canonical_id |
| `core/CORE/knowledge/world_resolver.py` | Резолвер идентичности (уже частично разделяет статусы) | Добавить поддержку 언어-независимого ID |
| `core/CORE/knowledge_card/builder.py` | `_approved_rag_aliases` | Обратный алиас-кросс |
| `core/CORE/schemas/world_reference.py` | `WorldEntityReference` | Уже есть boundary контракт — проверить совместимость |
| `core/CORE/narrative_engine/source_levels.py` | `ProvenanceCategory`, `SourceLevel` | Уже есть двухмерная модель — без изменений |
| `core/CORE/narrative_engine/world_provenance.py` | `normalize_world_provenance` | Связать с crosswalk provenance |

### Frontend (arkaim-web)

| Файл | Что меняется |
|------|--------------|
| `arkaim-web/src/shared/api/contracts/temporal.ts` | `TemporalNode.entity_ids: string[]` (уже есть) |
| `arkaim-web/src/app/temporal/page.tsx` | Фильтрация по `entity_ids` — без изменений логики |
| `arkaim-web/src/app/world-engine/page.tsx` | Фильтрация по `entity_ids` — без изменений логики |
| `arkaim-web/src/shared/ui/EntityCard.tsx` | Отображение稳定 canonical_id + лейблов |
| `arkaim-web/src/shared/ui/WorldProvenanceCard.tsx` | Отображение provenance |
| `arkaim-web/src/shared/ui/KnowledgeTraceCard.tsx` | Отображение простынки идентичности |
| `arkaim-web/src/shared/ui/StateView.tsx` | Состояние идентичности |

### Тесты

| Тест | Что проверять после миграции |
|------|------------------------------|
| `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py` | Ожидания `entity_ids` (region_arkaim, region_hyperborea, остальные []) |
| `arkaim-web/tests/e2e/world-temporal.spec.ts` | Фильтрация узлов по `entity_ids` |
| `arkaim-web/tests/unit/world.test.ts` | Ожидания world entity |

---

## Этапы миграции (после Owner-Go)

### Этап 0 — Заморозка (уже выполнено)
- Crosswalk утверждён для 2 регионов. Остальные 8 — `PRESERVE_UNCHANGED`.
- EN/RU записи не удаляются.

### Этап 1 — Схема crosswalk v2
- Добавить в `WORLD_ENGINE_WORLD_MODEL.json` поля: `canonical_id` (stable, language-agnostic), `provenance` (category/source_level/confidence), `labels` (en/ru), `aliases`.
- Оставить `runtime_connected: false` до полной интеграции.
- Не добавлять 8 незамапленных регионов в canon пока.

### Этап 2 — Dual-write / совместимость
- Backend поддерживает и старые ru-ID, и новые stable canonical_id в期間 перехода.
- `get_temporal_node` возвращает `entity_ids` на основе stable ID.
- Фронтенд продолжает использовать `entity_ids` из контракта.

### Этап 3 — Заполнение provenance для 8 регионов
- OWNER утверждает provenance (EXTERNAL_SOURCE/HISTORICAL) и статус для 8 регионов MAP_DATA.
- После утверждения — возможно добавление в canon (отдельное решение).

### Этап 4 — Полный переход
- Убрать dual-write, оставить только stable canonical_id.
- Обновить все потребители crosswalk.
- Удалить устаревшие ru-ID из kanонических позиций (только после подтверждения OWNER).

---

## Критерии приёмки (Definition of Done)

1. Тесты `test_b3b_crosswalk.py` проходят (или обновлены согласованно с OWNER).
2. `make test-backend` и `make test-frontend` зелёные.
3. `make lint` проходит без ошибок.
4. Regression: `/book/temporal/chain` возвращает корректные `entity_ids` для утверждённых регионов.
5. Документация `_wm_audit_report.md` и `_wm_migration_plan.md` актуальны.

---

## Риски

- Сложность отображения старых ru-ID в UI во время dual-write.
- Возможные расхождения между `MAP_DATA.json` (EXTERNAL_SOURCE) и каноном WORLD_MODEL.json (CANON).
- Фронтенд может ждать `entity_ids` в формате, который изменится после миграции.

---

## Остановка (STOP GATE)

Никакие изменения в коде и данных не выполняются до получения Owner-Go по разделам:
1. Канонический stable ID (region_* vs новый).
2. Статус 8 незамапленных регионов.
3. Схема crosswalk v2.
4. Порядок миграции.
