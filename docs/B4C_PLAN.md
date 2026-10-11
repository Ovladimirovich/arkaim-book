<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL — НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> B4-C реализован и протестирован в единственном frontend `arkaim-web`: добавлены `WorldProvenanceCard`, typed contract, подключение к карточке World entity и unit/API contract tests. Browser smoke ещё не выполнен. `SourceBadge` относится к B3 и не является World entity provenance UI. Ссылки ниже на `arkaim-web-v2` и `:3001` исторические. Актуальный статус: `docs/CURRENT_DEVELOPMENT_STATE.md`.

# B4-C — план: provenance в frontend World

Статус: **IMPLEMENTED / TESTED; browser smoke pending.**

## Простыми словами

**Цель:** показать в карточке сущности World реальный источник и статус provenance, не придумывая данные и не меняя backend.

**Что уже проверено:** B4-A/B4-B прошли unit/API и live-проверку; оба endpoint возвращают нормализованный provenance.

**Результат B4-C:** один минимальный read-only блок в `` и тесты. Никаких новых API-запросов, изменений данных или LLM-интерпретации.

## Зафиксированные входные данные

Целевой frontend после трансформации — `arkaim-web-v2`; старый `arkaim-web` в B4-C не меняется.

Фактический API:

- `GET /book/world/entity/{entity_id}`;
- `GET /book/world/entity/{entity_id}/context`;
- ответ `entity` уже содержит `provenance`;
- endpoint `/book/world/search` в B4-C не расширяется.

Подтверждённый live-пример `region_arkaim`:

- `status: available`;
- `source: MAP_DATA.json`;
- `source_category: EXTERNAL_SOURCE`;
- `source_level: HISTORICAL`;
- `notes: Картографические данные`;
- `confidence: 0.8`;
- `source_file: null`.

## Решение по контракту

В `arkaim-web-v2/src/shared/api/contracts/world.ts` добавить отдельный интерфейс:

- `WorldProvenanceStatus = 'available' | 'missing'`;
- `WorldEntityProvenance` с полями backend-контракта;
- `provenance?: WorldEntityProvenance` в `WorldEntityDetail`.

Не использовать index signature `WorldEntity` как замену явному контракту. `source_category` и `source_level` остаются строками, а не превращаются в frontend-enum: словарь и fallback принадлежат backend.

## Минимальный scope

1. Создать read-only presentational-компонент `src/entities/world/ui/WorldProvenanceCard.tsx`.
2. Переиспользовать `ProvenanceBadge` и `categoryMeta` из `shared/ui/ProvenanceBadge.tsx`.
3. Вывести только реально пришедшие поля.
4. Встроить компонент в карточку выбранной сущности в `src/app/(main)/world/page.tsx`.
5. Не делать отдельный запрос: использовать уже загруженный `entityDetail`.

Компонент принимает `provenance` из `WorldEntityDetail`; page отвечает только за размещение и состояния загрузки/ошибки.

## Предлагаемое отображение

- Заголовок: `Источник данных`.
- `source`: текстом; если отсутствует — `не указан`.
- `source_category`: через существующий `ProvenanceBadge`.
- `source_level`: текстом без утверждения, что это истина; если отсутствует — `не указан`.
- `confidence`: только если число в диапазоне 0..1, с процентным форматированием через существующий паттерн.
- `notes`: только если непустая строка.
- `source_file`: только если непустая строка; в B4-C это текст, не кликабельная ссылка.
- `status: missing`: показать единое состояние `Источник не указан` и не рендерить нулевые проценты.

## Файлы, которые предлагается изменить

### Обязательные

- `arkaim-web-v2/src/shared/api/contracts/world.ts` — typed provenance contract.
- `arkaim-web-v2/src/entities/world/ui/WorldProvenanceCard.tsx` — новый read-only компонент.
- `arkaim-web-v2/src/app/(main)/world/page.tsx` — встроить блок в детали выбранной сущности.
- `arkaim-web-v2/tests/unit/world.test.ts` — API contract cases для `available` и `missing`.
- `arkaim-web-v2/tests/unit/world-provenance-card.test.tsx` — component cases для доступного и отсутствующего provenance.

### Не менять

- `arkaim-web/` — старый frontend вне B4-C.
- `core/CORE/WORLD_MODEL/*.json` и `core/CORE/WORLD_MODEL.json`.
- `core/CORE/WORLD_CROSSWALK/`.
- `runtime/core/` и B4 backend-код.
- `/book/world/search` и его response contract.
- World/Temporal/Ask navigation и session state.

## Тест-матрица

### API contract

1. `available`: возвращаются все поля, включая `confidence: 0.8` и `source_file: null`.
2. `missing`: `status` равен `missing`, nullable-поля не превращаются в `''`, `0` или выдуманный источник.
3. Частичный provenance: отсутствующие поля остаются `undefined`/`null`, а TypeScript не требует их наличие.
4. Запрос использует ровно `/book/world/entity/{id}`.

### Component

1. `available`: видны `Источник данных`, `MAP_DATA.json`, `Внешний источник`, `HISTORICAL`, `Картографические данные`, `80%`.
2. `source_file: null`: строка источника-файла не рендерится.
3. `missing`: видно `Источник не указан`, нет `NaN%`, `0%` или fabricated badge.
4. Пустые строки в `notes`/`source` считаются отсутствующими.
5. Компонент не мутирует переданный объект.

### Интеграционный smoke

1. Открыть `/world?entity_id=region_arkaim`.
2. Дождаться загрузки карточки.
3. Проверить, что provenance-блок виден под описанием сущности.
4. Проверить, что переходы `World → Temporal`, закрытие карточки и возврат по query state не изменились.
5. Проверить, что перезагрузка страницы не теряет выбранную сущность и не вызывает новый endpoint.

## Проверки после реализации

- `npm run typecheck`;
- `npm run lint`;
- `npm test` или целевой `npx vitest run tests/unit/world.test.ts tests/unit/world-provenance-card.test.ts`;
- production build должен пройти, если это предусмотрено текущим frontend pipeline;
- `git diff --check`.

UI-проверка выполняется в браузере с авторизованным reader, потому что backend закрывает World routes.

## Критерии приёмки

- На карточке виден provenance только при наличии нормализованного поля.
- `missing` имеет честный empty state.
- `confidence` не показывается без реального числа.
- `source_category` использует существующий backend-зеркальный `ProvenanceBadge`.
- `source_level` не называется доказательством истины.
- `source_file` не превращается в URL или link.
- Связи, Temporal и Ask не получают provenance автоматически.
- Не появляются новые запросы к backend.
- `WORLD_MODEL` и crosswalk не изменены.
- B4-C не включает Knowledge Cards, конфликты, cross-source reasoning или LLM.

## Порядок и горизонты
1. Контракт → компонент → card → tests → browser smoke → OWNER REVIEW.
2. Горизонт 1: принять frontend-контракт и проверить 2–3 сущности.
3. Горизонт 2: отдельный OWNER-GO на Knowledge/Provenance.

Текущая точка: **B4-C IMPLEMENTED / TESTED; browser smoke pending.** `WorldProvenanceCard` интегрирован в карточку World entity, unit/API contract tests добавлены. `SourceBadge` — компонент B3, не B4-C.
