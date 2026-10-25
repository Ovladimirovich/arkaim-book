# EDM-RES Pilot — интеграция resolvers в production-швы /book/ask и /visualize (25.10.2026)

Продолжение `docs/EDM_PILOT_2026-10-25.md`: EDM-каталог (5 пилотных + examples)
подключён к живым эндпоинтам через OWNER-GATE.

## Простыми словами

1. **Цель.** EDM стал не только «положен в JSON», а реально работает в продукте:
   на `/visualize` — описания сущностей наполняют визуальный контекст сцены
   (стиль/материалы архитектуры → MediaPlan), на `/book/ask` — в ответ
   добавляется слоистый EDM-блок с провенансом.
2. **Сделано.** Флаг `EDM_RES_PILOT_ENABLED` (по умолчанию выключен)
   переключает поведение обоих эндпоинтов. Выключен — ответы байт-в-байт
   как раньше (проверено SHA-промптом и отсутствием ключа `edm`);
   включен — EDM-значение появляется в плане, а «не установлено» —
   явно `UNKNOWN`, а не умолчание «clear».
3. **Итог.** PASS: 21 тест в `runtime/tests/test_edm_res_pilot.py`
   (включая 4 e2e на реальных данных) + 98 тестов регрессионного
   батча зелёные.

## Архитектура шва

| Файл | Роль |
|---|---|
| `core/CORE/ENTITY_MODEL/resolutions.py` | чистый RES-резолвер: `(entity, scope) → resolution` (world / scene / media_plan / frame / time) |
| `core/CORE/ENTITY_MODEL/world_feed.py` | `apply_edm(ctx, entities, resolver, scene_overrides)` — заполняет только существующие поля VisualContext, мутации только ctx, world-model не трогает; layer isolation: world-scope не видит scene/media_plan-claims без явного task-scope |
| `runtime/core/services/edm_pilot.py` | runtime-обвязка: mtime-кэш сущностей (pilot/ + examples/), строгий матчинг (id / имена / явные `edm_entity_ids`), dialogue-блок, composite t1+EDM провайдер; модули ENTITY_MODEL грузятся importlib по пути (каталог не импортируемый пакет) |
| `runtime/shared_config.py` | `EDM_RES_PILOT_ENABLED: bool = False`, `EDM_RES_DIR` |
| `runtime/core/routes/visual.py` | `/book/visualize`: при флаге — `apply_edm_to_context` ДО MediaPlanBuilder; при `applied` — блок `edm` в ответе + `edm:<id>` в source_refs плана |
| `runtime/core/routes/book.py` | `/book/ask`: при флаге — опциональный `edm`-metadata-блок (нет совпадения — ключ не появляется; сбой блока не ломает ответ) |

Правила шва (не нарушать):
- мир не мутируется: resolver чистый, входные сущности не модифицируются;
- unknown/knowledge-gap не материализуется — явная граница знания;
- без флага публичный контракт неизменен.

## Результаты live-проверки (e2e, `TestEndToEndRealRegistry`)

- Флаг off: `/visualize` — промпт MediaPlan SHA-идентичен legacy baseline
  (`test_md3_route_a`), ключа `edm` нет; `/book/ask` — без ключа `edm`.
- Флаг on + явные `edm_entity_ids` (region_arkaim, arkaim_settlement, arkaim):
  реальный MediaPlan несёт `circular fortified` / `stone, timber, thatch, clay`;
  `environment.weather/season` — явная граница `UNKNOWN` (не fail-open «clear»);
  provenance `edm:<id>` в source_refs плана.
- Флаг on + auto-matching без применимых claims (civ_hyperborea, culture.values):
  ctx не мутирован → промпт SHA-идентичен legacy, ключа `edm` нет (layer isolation
  на реальных данных).
- `/book/ask` «Что такое Аркаим?» — в `data` блок `edm` (entities, слоистый
  dialogue-текст, provenance-таблица); флаг off — того же вопроса без ключа.

## Известные ограничения (не блокер, зафиксировано)

- `VisualizeRequest.chapter` — DTO-контракт `ge=1`, поэтому каталог-сцены
  (`CATALOG_CHAPTER=0`, например `scene_09` «Строительство Аркаима» с location
  Аркаим) недоступны `/visualize`; на них авто-матчинг по локации не запускается.
  Определяющий вход пилота — явные `edm_entity_ids` (работают на любой допустимой сцене).
- Реальные каталог-сцены не несут location в VisualContext (builder ставит
  «unknown»), поэтому авто-матчинг по `location` в production пока не
  реализуется на реальных данных; расширение автоматического матчинга
  (по RAG/локациям) — следующий технический шаг.

## Аудит автоматического entity resolution (2026-10-25, read-only)

`docs/ENTITY_RESOLUTION_AUDIT_2026-10-25.md` — исследование текущего
автоматического разрешения сущностей (вопрос/сцена → WorldEngine / crosswalk /
EDM) без изменения кода: 5 существующих механизмов, ID-пространства, живые
probe-результаты. Ключевые выводы:

- основной автоматический механизм уже существует — детерминированный
  `related_entities` (все 13 категорий production-engine); его ID
  совпадают с canonical_id EDM-пилота и approved crosswalk;
- «Аркаим» — трёхсторонняя коллизия (architecture `arkaim_settlement`,
  language `lang_аркаим`, geography `region_arkaim` × 3 EDM-карточки);
  разрешение коллизий — продуктовое/смысловое решение владельца;
- расширение approved crosswalk (сейчас 3 mapping'а) на `steppe_climate` и
  остальные категории — OWNER-артефакт.

**Обновление 2026-10-25 (OWNER):** смысл разрешения коллизий и расширения
crosswalk зафиксирован в правилах: `docs/ENTITY_RESOLUTION_RULES_2026-10-25.md`
— Context Resolution (intents §3, правила R1–R4/C1–C6 §4, Tier-1/Tier-2
связи + v1-батч из 10 утверждаемых связей §4.4, примеры на реальных
сущностях §5). До утверждения этих правил и wiring'а W1–W4
`EDM_RES_PILOT_ENABLED` НЕ включается.

## Stop Gate

- **CLOSED** для пилота интеграции: швы реализованы, проверены (21 + 98 тестов),
  backward-compat доказан (SHA-промпт + отсутствие ключей без флага).
- Флаг выключен по умолчанию; **переключение production-поведения = OWNER-GO**
  (заведение `EDM_RES_PILOT_ENABLED=true` в конфиге окружения).
- OWNER-решение 2026-10-25: GO на флаг приостановлено до утверждения
  `docs/ENTITY_RESOLUTION_RULES_2026-10-25.md` (S1–S5) и wiring'а W1–W4 —
  иначе EDM начнёт автоматически применять неоднозначные связи
  (кейс «Аркаим»).
