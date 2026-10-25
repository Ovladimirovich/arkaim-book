# ENTITY DESCRIPTION MODEL — единая модель описательного знания (EDM v0.1)

Дата: 2026-10-25. Статус: **дизайн-блок B (схема + 3 примера + валидатор) — TESTED**, без правок production-кода, без массовой популяции данных.

## Простыми словами

**Цель.** У нас о мире книги одновременно знали 6 разных баз данных (канон, ext-model, art-model, FORM, визуальные карточки, автогенерация) — и они расходились: одна писала «Аркаим — камень», другая не знала про погоду, третья додумывала детали от себя. Задача: заменить шестерку на **одну книгу записей** с правилами честности.

**Что сделано.** Спроектирована модель «карточка сущности» (место/персонаж/одежда/постройка): каждая карточка хранит **отдельные факты**, а не готовые описания. У каждого факта — откуда он (канон автора / история / художественное допущение / реконструкция), насколько он уверен (0–1) и помечен ли как «выдумка» (medium). Проверено на трёх реальных сущностях: **Аркаим, Световит, Одежда воина**. Автопроверщик не пропустил бы, например, «погоду = ясно» как факт — это должно значить «не известно».

**Что получилось.** PASS: схема + 3 контрольные карточки + 15 автотестов (все зелёные). Production не тронут.

**Проблемы.** Существенных нет. Мелочь: в автогенерациях (WORLD_MODEL.json/CLIMATE.json) факты и их уверенность уже перепутаны — там «уверенность 0.60» стоит на самой фразе, а не на знании; в новой модели это исправлено структурно, но старые файлы остаются как есть до отдельной задачи по миграции.

**Дальше (предложение, не автомат):** после приёмки — (1) миграционный загрузчик ext/form/visual → EDM (пока по одному слою), (2) проекция EDM → MediaPlan и dialogue, (3) фикс fail-open в EnvironmentContext через эту же модель.

---

## 1. Зачем (связь с аудитом)

Исходный документ: `docs/DESCRIPTIVE_WORLD_KNOWLEDGE_AUDIT_2026-10-25.md`. Главные зафиксированные пробелы, которые закрывает EDM:

| Пробел | Как закрывает EDM |
|---|---|
| 6 параллельных слоёв, 4 разных формата сущностей | Один формат (эта модель), слои = только `source_ref` |
| 0 полей «unknown/несуществует» | `status: unknown` + `constraints.required_unknown` — явная граница знания |
| fail-open default `weather="clear"` | unknown-claim обязан иметь `value=null`; тест `test_unknown_with_value_fails` |
| нет per-fact provenance | у каждого факта `provenance_class` + `confidence` + `source_ref` |
| art-model не отделён от канона (петля галлюцинаций G10) | `medium=true` + AI-классы provenance; `forbid_medium` на базовых путях |
| одежда/культура как строки, а не сущности | `type: clothing/culture`, одежда со своими claims и relations (`wears`, `uses`) |
| нет связей (location↔climate↔architecture↔materials) | `relations` с типами, provenance и confidence |
| эпоха/темпоральность в описании отсутствует | блок `time` + `time.epoch_ref` в required_unknown |

## 2. Анатомия карточки

```
Entity
├─ model:       {model_id, model_version, created_at, note}
├─ identity:    {canonical_id, type, names[], aliases[], one_line, is_reconstruction}
├─ time:        {epoch_ref[], start, end, temporal_links[], note}   # может быть null
├─ claims[]:    {path, value, status, provenance_class, source_ref?, confidence?, medium?, note?}
├─ relations[]: {type, target, target_type, label?, provenance_class, confidence?, note?}
├─ constraints: {required_unknown[], forbid_medium[], note?}
└─ verify:       {dialogue_sentence, mediaplan_fragment, ...}       # optional self-test
```

### Статусы (status)

| status | Смысл | Валидность value | medium |
|---|---|---|---|
| `known` | подтверждённый факт (канон/история/визуальная карточка) | обязателен, `source_ref` обязателен | по классу |
| `inferred` | выведено из данных книги (related_entities и т.п.) | `source_ref` обязателен, confidence < 1 | по классу |
| `unknown` | **осознанная граница знания** — не отсутствие поля | `null`, provenance `none` | `false` |
| `reconstructed` | реконструкция (археология/лор) | `medium=true` обязательно | `true` |
| `hypothesis` | гипотеза низкой уверенности | `medium=true`, confidence обычно ≤ 0.4 | `true` |
| `not_applicable` | для типа сущности не существует | `null` | `false` |

### Классы provenance

| класс | Класс (по плану) | medium обязателен? |
|---|---|---|
| `author_canon` | AUTHOR_CANON | нет |
| `external_source` | EXT_MODEL (история) | нет |
| `derived` | выведено из канона | нет |
| `ai_model`, `ai_model_artistic` | ARTISTIC_MODEL | да |
| `reconstruction` | RECONSTRUCTION | да |
| `none` | — (для unknown) | нет |

Правило G10 зафиксировано валидатором: `medium=true` ⇒ класс из `{ai_model, ai_model_artistic, reconstruction}`; `status ∈ {reconstructed, hypothesis}` ⇒ `medium=true`.

## 3. Сущности-примеры (реальные данные, без вымысла)

Файлы в `core/CORE/ENTITY_MODEL/examples/`:

| Пример | type | Что доказывает |
|---|---|---|
| `arkaim_location.json` | location | смешанный provenance (канон+история+art), `required_unknown: [weather, season, time.epoch_ref]`, `forbid_medium` на базовых фактах, relations к Гиперборее/Стене Города/материалам |
| `svetovit_character.json` | character | персонаж из «визуального профиля»: ВСЕ внешние поля `ai_model_artistic`/medium=true; в dialogue — только «художественный образ, не факт книги» |
| `warrior_clothing.json` | clothing | одежда как сущность: FORM-карточка → claims; эпоха = RECONSTRUCTION (0.4); носитель = `unknown` claim + relation `wears` (гипотеза 0.2, не канон) |

Происхождение каждого факта в примерах — в `source_ref` (layer+ref+path). Вымышленных значений нет: unknown-поля реально не установлены в книге.

## 4. Потребители (6 представлений)

Все — проекции с одной карточки:

1. **dialogue** — текст: только `known/inferred` non-medium; `reconstructed` — с пометкой «реконструкция»; `unknown` — формулируется как «книга не говорит».
2. **explorer** — таблица: path | value | status | provenance_class | confidence.
3. **reconstruction** — заполнение `unknown`/`reconstructed`/`hypothesis` в лоре с явным уровнем.
4. **mediaplan** — structured: `value` + статусы; `environment.weather=UNKNOWN` приходит в MediaPlan (fail-open снят).
5. **image_prompt** — medium-факты как фразировка; non-medium-факты как якоря; `forbid_medium` пути не заполняются medium.
6. **video_plan** — временные слайсы `time.epoch_ref` + relations.

`verify`-блок в примерах — эталонные проекции для контроля.

## 5. Валидация

- Схема: `core/CORE/ENTITY_MODEL/entity_description.schema.json` (JSON Schema 2020-12).
- Валидатор: `core/CORE/ENTITY_MODEL/entity_model_validate.py` (standalone, нужен только `jsonschema`, есть в runtime venv).
- Запуск: `runtime\.venv\Scripts\python core\CORE\ENTITY_MODEL\entity_model_validate.py --strict core\CORE\ENTITY_MODEL\examples` → 3× `[OK]`.
- Тесты: `runtime/tests/test_entity_description_model.py` — 16 тестов (включая v0.2: полный дубль запрещён, multi-status на одном path разрешён), все PASS.

## 6. Границы блока B (что НЕ сделано)

- Не изменены: pulse/knowledge layers, `core/CORE/KNOWLEDGE/**`, `core/CORE/FORM/**`, `core/CORE/EXTENSION/**`, `EnvironmentContext`, `runtime/core/**`.
- Нет массового заполнения: только 3 контрольные сущности.
- Нет миграционного загрузчика 6 слоёв → EDM (следующая задача после OWNER-GO).
- Нет переделывания ID-реестра (task B3A): `target` в relations — строковый канонический id, реестр будет отдельным artefact'ом.

## 7. Стоп-контроль (STOP GATE)

- `CLOSED`: модель спроектирована, провалидирована на реальных данных, зафиксирована документом.
- Требуется OWNER-GO только на переход к блоку C (миграционный загрузчик + проекции в MediaPlan/dialogue), т.к. это первая правка данных/контакта с production-режимом.

## 8. Послесловие (25.10.2026): блок B принят, пилот выполнен

- **B — ACCEPTED** (решение владельца, 25.10.2026).
- Массовая миграция шести слоёв — **NO-GO** по решению владельца; сначала проверка
  EDM как рабочей модели мира на ограниченном наборе.
- Выполнен **пилот**: `extended_world` → EDM для 5 реальных карточек с обратным
  сравнением (ничего не потеряно / provenance / relations / temporal / UNKNOWN /
  ARTISTIC_MODEL≠CANON) и проекциями в dialogue + MediaPlan.
  Отчёт и доказательства: `docs/EDM_PILOT_2026-10-25.md` +
  `core/CORE/ENTITY_MODEL/pilot/` + `runtime/tests/test_edm_pilot.py`.
- Зафиксирован принцип роли EDM: EDM — НЕ новая главная база фактов; это
  структурированное описание сущности, собранное из WORLD MODEL + Knowledge Core +
  FORM + визуальных источников с provenance и статусом. Проекции (dialogue/MediaPlan/
  reconstruction) берут из EDM; истина «что и откуда» — в Knowledge Core,
  «с чем связано и когда» — в World Model.
- Следующий шаг (массовая миграция остальных источников) — по OWNER-GO.

## 9. Послесловие (25.10.2026): EDM-RES — механизм резолвинга описаний

Схема поднята до **v0.2** и добавлены операционные функции и резолвер (только внутри
`core/CORE/ENTITY_MODEL/`, production-контакта нет):

- **`entity_description.schema.json` v0.2**: новые типы сущностей (animal, plant,
  technology, weather, landscape); новые статусы `artistic_model` и `fiction`
  (и одноимённые классы provenance); `medium=true` обязателен для всех
  не-фактических статусов; у claim'а появились `applies_to` (scope:
  world/era/place/scene/media_plan/frame + `temporal_ref`) и `created_from`
  (фактовая база вывода). Семантика ledger: одно свойство МОЖЕТ нести несколько
  claim разных статусов/scope; запрещён только полный дубль
  (path + status + scope level + scope id).
- **`operations.py`** — чистые функции `derive` (DERIVE, status=inferred,
  `created_from` обязательна; противоречие с фактом = `EdmConflict`),
  `reconstruct` (RECONSTRUCT, medium), `artistic_fill` (ARTISTIC FILL,
  всегда со scope), `fiction` (FICTION, scope обязательный). Все функции
  возвращают НОВУЮ карточку: вход не мутируется, факты не перезаписываются —
  художественные значения добавляются как отдельные scoped claim'ы.
- **`resolutions.py`** — RESOLVER + проекции:
  `resolve_description(entity, scope)` (priorities: CANON > EXTERNAL > DERIVED >
  RECONSTRUCTION > HYPOTHESIS > ARTISTIC_MODEL > FICTION > UNKNOWN; в одном
  уровне приоритета побеждает более узкий scope; temporal_ref-несовпадение
  исключает claim; known+medium (art-model) решается как ARTISTIC, не факт),
  `to_mediaplan` (материалы: facts / derived / reconstructions /
  artistic_choices / unknown + structured_prompt с (MEDIUM)-метками и UNKNOWN),
  `to_dialogue` (честные layered-формулировки: факт / «(вывод)» /
  «(реконструкция, художественное допущение)» / «(художественный выбор,
  scope …)» / «Не установлено» + relations с метками),
  `to_llm_brief` (блок-материалы FACTS/DERIVED/RECONSTRUCTIONS/
  ARTISTIC_CHOICES/UNKNOWN + инструкция «не выдумывать UNKNOWN, метить
  допущения» — EDM решает что можно сказать, LLM формулирует).
- **Валидатор** обновлён под v0.2 (rules: duplicate только по полному key,
  inferred → created_from, artistic_model/fiction → medium + applies_to).
- **Тесты**: `runtime/tests/test_edm_resolution.py` (32 теста: контракт v0.2,
  purity операций, priority chain, сценарии владельца Arkaim/Svetovit/
  warrior clothing, негативный тест «weather=clear не попадает в World Model»,
  LLM brief) + обновлён `test_entity_description_model.py` под семантику v0.2
  (multi-status на одном path разрешён, полный дубль запрещён). Все PASS.
- **Данные не тронуты**: ни одна карточка examples/pilot не несёт
  `artistic_model`/`fiction` — механизм реализован, миграция/популяция нет
  (контрольный тест `test_no_artistic_or_fiction_claims_migrated_into_data`).

STOP GATE: механизм **TESTED** (юнит + негативные тесты зелёные, валидатор на
examples/pilot — OK). Подключение RESOLVER к production-потребителям
(Pulse/BookVoice, MediaPlan routes) и массовая популяция художественных
значений — отдельные шаги, требуют OWNER-GO.

