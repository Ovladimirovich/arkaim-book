<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL — НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> B4-A/B4-B реализованы и протестированы; B4-C реализован и протестирован в `arkaim-web`. `SourceBadge` относится к B3 и не является frontend provenance для World entity. Browser smoke B4-C ещё не выполнен. Актуальный статус: `docs/CURRENT_DEVELOPMENT_STATE.md`.

# B4 — план: источники и provenance в World

Статус: **PLAN — OWNER-GO REQUIRED. B4 не запущена.**

## Простыми словами

**Что было целью?** Подготовить отдельный план показа источников и доказательности утверждений в World Engine.

**Что реально установлено по текущему коду?**
- `GET /world/entity/{entity_id}` возвращает сущность из индекса World Engine.
- `GET /world/entity/{entity_id}/context` возвращает `entity`, `relations` и `form_context`.
- `WorldModelExt` загружает категории из `core/CORE/WORLD_MODEL/*.json` без отдельной нормализации provenance.
- В данных World Engine уже встречаются поля источника: `source`, `provenance_category`, `provenance_notes`, `source_level` и связанные metadata.
- Для canonical WorldModel и Temporal существует отдельный provenance-контракт; его нельзя автоматически приписывать World Engine сущностям.
- B3b baseline зафиксирован в `docs/B3B_BASELINE_BEFORE_B4.md`.

**Что предлагается?** Разделить B4 на небольшие шаги: сначала read-only backend-контракт provenance, затем отдельная frontend-задача на отображение источника в карточке сущности. Не смешивать B4 с crosswalk и не расширять approved mappings.

**Что получится в итоге?** Пользователь сможет увидеть, откуда взялась конкретная сущность/связь, каков статус источника и чего системе неизвестно. Система не будет придумывать источник при отсутствии данных.

## Границы B4

### Можно

- Читать существующие provenance/source поля.
- Нормализовать их в стабильный read-only API-контракт.
- Показывать честное пустое состояние, если provenance отсутствует.
- Добавить unit/API-тесты и документацию контракта.
- Отдельно, после backend-проверки, показать provenance в World UI.

### Нельзя

- Придумывать источник, URL, автора, главу или уверенность.
- Считать `source_level` доказательством истины без явного контракта.
- Автоматически объединять World Engine и canonical WorldModel provenance.
- Расширять B3 crosswalk.
- Менять значения в `WORLD_MODEL/*.json` или `WORLD_MODEL.json`.
- Делать cross-source reasoning, разрешение конфликтов или LLM-интерпретацию в B4; это отдельные задачи Knowledge/Provenance.
- Менять UI до отдельной B4-UI задачи и OWNER-GO.

## Предлагаемый контракт

API должен возвращать provenance отдельно от внутренних raw-полей, например:

```json
{
  "provenance": {
    "status": "available",
    "source_level": "HISTORICAL",
    "source_category": "EXTERNAL_SOURCE",
    "source": "MAP_DATA.json",
    "source_file": "core/CORE/WORLD_MODEL/GEOGRAPHY.json",
    "notes": null,
    "confidence": null
  }
}
```

Правила контракта:

- `status = available` только если найден хотя бы один реальный provenance/source marker.
- `status = missing` если маркеры отсутствуют.
- `confidence` не выдумывается: `null`, если в данных нет confidence.
- `source_file` — путь/имя реально загруженного файла, не внешний URL.
- `source_level` сохраняется как исходное значение, без новой интерпретации.
- `raw` поля не удаляются и не подменяются.

Итоговый shape должен быть зафиксирован Pydantic-схемой или DTO и покрыт тестами.

## Шаги B4

### B4-A — инвентаризация и контракт

1. Перечислить реальные provenance-поля по всем категориям `WORLD_MODEL/*.json`.
2. Зафиксировать, какие значения реально встречаются.
3. Определить минимальный DTO без потери raw-данных.
4. Добавить backend-тесты для `available`, `missing` и неполного provenance.
5. Не подключать UI.

### B4-B — read-only API

1. Добавить нормализацию provenance в backend-слой.
2. Включить её только в согласованный response contract.
3. Проверить `/world/entity/{id}` и `/world/entity/{id}/context`.
4. Убедиться, что неизвестные/неполные поля дают `missing`, а не выдуманные значения.
5. Проверить, что `/world/search` не ломает существующий контракт.

### B4-C — frontend provenance

Отдельная задача после B4-B:

1. Показать источник и статус в карточке сущности.
2. Добавить честное состояние «Источник не указан».
3. Не показывать provenance у relation без provenance.
4. Не менять переходы World/Temporal и crosswalk.
5. Добавить component/API tests и smoke-проверку.

## Критерии приёмки B4

- API отдаёт только реально найденные provenance fields.
- `missing` не превращается в fabricated source.
- `confidence` отсутствует, если его нет в источнике.
- Raw entity fields не потеряны.
- `region_arkaim` и `region_hyperborea` не получают новых автоматических связей.
- `WORLD_MODEL/*.json` и `WORLD_MODEL.json` не изменены.
- Unit/API tests проходят.
- Ruff/ESLint проходят для затронутых файлов.
- UI не включается в backend-only задачу без отдельного решения.
- После каждого шага — OWNER REVIEW, затем следующий шаг.

## Порядок и контрольная точка

`B3b baseline → B4 plan → OWNER-GO → B4-A → OWNER REVIEW → B4-B → OWNER REVIEW → B4-C → OWNER REVIEW`

Текущая точка: **B4-A/B4-B implemented/tested. B4-C implemented/tested: `WorldProvenanceCard`, typed contract, интеграция в карточку World entity и unit/API contract tests добавлены; browser smoke pending.**
