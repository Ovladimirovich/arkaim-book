# MD-3.2 ROUTE B IMPLEMENTATION REPORT — миграция `/visualize/epoch` на canonical MediaPlan path

**Дата:** 2026-09-12
**Статус:** IMPLEMENTED + TESTED — Route B мигрирован; verdict: **ЗАКРЫТ ПОЛНОСТЬЮ** (§Verdict); маршруты C/E — НЕ начаты (ждут отдельных GO).
**Основа:** GO владельца на MD-3.2 Route B; Route A ACCEPTED (PA-F1 закрыт); ADR_MEDIA_PLAN_V0 D5.
**Граница подэтапа:** только `visualize_epoch` в visual.py (+новые тесты/документы); Route A/C/D/E, WorldModel, temporal-слой, frontend, MediaPlan schema/builder/dispatch — не тронуты (forensic §10).

---

## Простыми словами

1. **Что было целью?** — перевести маршрут «Визуализация эпохи» на канонический конвейер (план → временный конверт → генератор), полностью сохранив исторический результат и не трогая временную модель мира (она только читается).

2. **Что реально сделано?** — маршрут теперь строит смысловой план (MediaPlan) из канонического контекста эпохи (тот же Builder, что в A/D); исторический текст промпта сохранён как временная проекция ПОСЛЕ плана — в конверте-мосте. Временн́ые данные (эпоха, границы, происхождение) попадают в план только из существующего источника — модели мира, только на чтение. Написаны: снимок «до» с крипто-хэшем, 10 тестов, включая шпион-провайдер и проверку «неизвестная эпоха не выдумывается».

3. **Что получилось?** — **PASS.** Промпт ДО = ПОСЛЕ (SHA `f460318283a4cbf8`); ответ — те же 3 поля; 404 на неизвестную эпоху; модель мира не изменена (тест-инвариант); все прежние тесты зелёные; регрессия = база + 10 новых.

4. **Есть ли проблемы?** — нет. Один факт источника задокументирован (не дефект): идентификатор эпохи внутри временной ссылки — это ID узла модели мира («temporal_arkaim_era»), а не параметр запроса; у этой эпохи список происхождения пуст — наследуется честно пустым, не выдумывается.

5. **Что дальше?** — ваш GO на **Route C `/assets/generate`** или **E `/shots/generate`** (последние два немигрированных). Сам не начинаю.

---

## 1. Baseline (создан ДО изменения: `docs/MD3_2_ROUTE_B_BASELINE.md`)

- **Endpoint:** POST `/book/visualize/epoch/{epoch_id}` (VisualizeResponse; auth reader). Body: {reader_id?}.
- **Ответ (200):** ровно {prompt, image_bytes(base64), content_type:"image/svg+xml"}.
- **Исторический промпт** (arkaim_era): «epic fantasy scene, Эпоха Аркаима, Эпоха расцвета Аркаима — центра духовного знания., dramatic lighting, …, beautiful detailed environment». **SHA256[:16]=`f460318283a4cbf8`**.
- **Temporal input (существующий, read-only):** WorldModel.get_temporal_context → {epoch{name_ru,description,civilizations_active}, characters, events, technologies, temporal_node}; canonical-билдер build_scene_context_for_epoch → SceneContext + scene_extras (temporal из _temporal_ref_from_epoch: provenance — готовая из TemporalNode, bounds/счётчики как есть).
- **Provider-path:** `generate(prompt)` — БЕЗ size/preferred. **До execution доходит ТОЛЬКО prompt** (единственный параметр).
- **Ошибки:** unknown epoch → 404 «Epoch '…' not found».

## 2. Изменённые файлы

```
ИЗМЕНЕН (1 существующий; вставка MD-3.2-блока в visualize_epoch):
  runtime/core/routes/visual.py — план + dispatch + legacy-проекция; docstring
НОВЫЕ (3):
  runtime/tests/test_md3_route_b.py   — 10 тестов
  docs/MD3_2_ROUTE_B_BASELINE.md      — снимок «до»
  docs/MD3_2_ROUTE_B_IMPLEMENTATION_REPORT.md — этот отчёт
НЕ ТРОНУТЫ: Route A/C/D/E, WorldModel/temporal (world_model.py mtime 05.09;
  visual_context_builder.py 11.09 — до сессии), media_plan/* (16:27-16:38 =
  MD-3.1), SCHEMAS, providers, frontend.
```
Forensic-нюанс: git diff показывает Route B «целиком новым» — потому что visualize_epoch отсутствует в HEAD (это uncommitted MD-2-код); МОЯ вставка — только MD-3.2-блок (план/проекция/вызов), что подтверждено построчным разбором диффа.

## 3. Тесты — `runtime/tests/test_md3_route_b.py`, 10/10 PASS

| GO-пункт | Тест |
|----------|------|
| 1. План из canonical SceneContext | test_plan_actually_built_from_canonical_epoch_ctx (entity_refs=[epoch_id], created_from="epoch") |
| 2. Epoch/temporal из существующего источника | test_epoch_temporal_flows_from_existing_source (temporal_context из WorldModel; provenance 1:1; epoch_id=temporal_узла) |
| 3. Provider получает dispatch из плана | test_provider_receives_legacy_prompt_via_dispatch (spy) |
| 4. Spy получает исторический prompt | там же (prompt == response.prompt) |
| 5. Response contract сохранён | test_response_contract_unchanged (ровно 3 ключа) |
| 6. Prompt до/после идентичен | test_prompt_byte_identical_to_baseline (SHA) |
| 7. Нет второго canonical path | test_dispatch_not_part_of_plan_and_projection_after_plan (план ≠ legacy; проекция после плана) |
| 8. Нет execution leakage | test_plan_serialization_no_execution_fields + verify_no_execution_fields |
| 9. Unknown epoch не выдумывает temporal | test_unknown_epoch_404_no_invented_temporal (404; spy пуст; is_temporal=False на уровне источника) |
| 10. Existing behavior regression-free | test_world_model_not_mutated + комбинированные прогоны |

## 4. Regression

| Набор | Результат |
|-------|-----------|
| test_md3_route_b.py | **10 passed** |
| Combined B→A→D→md3→md2_routes (обе последовательности) | **92 passed** ×2 |
| Visual-chunk 14 файлов (13 + route_b) | **200P / 4F** = база A (190P/4F) + 10; 4F = pre-existing test_assets_new_params |
| Temporal-chunk (temporal_model + world_engine + narrative_world_model + m7) | **95 passed** — WorldModel/temporal целы |
| test_md3_route_a.py / route_d.py / media_plan | 12P / 15P / 40P (не задеты) |
| ruff (мой тест + мои зоны visual.py) | чист (15×W293 в visual.py — pre-existing, есть в HEAD, чужие зоны) |

## 5. Prompt compatibility

Исторический промпт `build_epoch_prompt(epoch_id, context)` — сохранён **byte-identical** (SHA-совпадение; тест п.6). Prompt-архитектура/словари не переписаны; текст не «переведён» на новый формат. Legacy-текст — проекция ПОСЛЕ плана (`dispatch.prompt = legacy_prompt`, комментарий «MD-5: удалить»), не второй смысловой источник: план несёт СВОЙ canonical composer-промпт (≠ legacy), тест-доказательство `test_dispatch_not_part_of_plan_and_projection_after_plan`.

## 6. Temporal provenance flow (read-only, без изменений)

```
WorldModel (TemporalNode: id="temporal_arkaim_era", provenance=[], bounds, confidence)
  → wm.get_temporal_context("arkaim_era") — READ-ONLY (load, не mutate)
  → build_scene_context_for_epoch: _temporal_ref_from_epoch (provenance → ProvenanceRef
    1:1, дедуп по категории — существующий механизм C1, НЕ новый)
  → SceneContext.scene_extras.temporal
  → MediaPlan.temporal_context + plan.provenance (наследование 1:1)
```
- Тест-инвариант: WorldModel до/после двух запросов (успех+404) идентичен (`test_world_model_not_mutated`).
- temporal_nodes/edges/provenance/confidence/temporal_today/temporal_arkaim_era/C2/temporal-factories — 0 правок (mtime-forensic).
- **Факт источника (не дефект):** `temporal.epoch_id` = ID узла («temporal_arkaim_era»), provenance эпохи пуст → в плане честно пустой список (проверено тестом).

## 7. Execution leakage check

- План — MediaPlan v0 без изменений (schema/builder/dispatch mtime = MD-3.1-окно; 40 тестов MD-3.1 зелёные).
- Сериализация плана B без banned-полей (тест п.8); extra="forbid" действует.
- До execution доходит только prompt (spy: size=512x512-дефолт провайдера, preferred=None) — ровно как в baseline; миграция не добавила ни одного execution-параметра.

## 8. Forensic scope

- visual.py: MD-3.2-блок ТОЛЬКО в visualize_epoch (L136-181) + принятая зона A; Route A-код не изменён в этой сессии.
- 1 canonical path: `from media_plan` = assets.py×3 (D) + visual.py:77 (A) + visual.py:164 (B) — все через один MediaPlanBuilder.
- WorldModel/temporal/scene_context/builder — mtime до сессии; frontend — 0 правок после 19:30; providers — 0.
- CJK 0; baseline-скрипт удалён после фиксации; git status — новые только test_md3_route_b.py + 2 документа.

## 9. Pre-existing failures (не связанные с B)

- test_assets_new_params ×4 (ModuleNotFoundError runtime.core) — во всех базах с MD-2.
- TestFeedbackStore ×12 (policy-артефакт сессии, TEMP) — вне visual-chunk, документирован в Route D-отчёте.
- 15×W293 в visual.py — pre-existing (чужие зоны, есть в HEAD).
- Unknown-reader FK-500 (Route A §12) — общий pre-existing, не Route B.

## 10. Verdict по Route B

**Route B ЗАКРЫТ ПОЛНОСТЬЮ:**
1. Канонический путь построен: SceneContext (существующий epoch-вход) → MediaPlan (существующий Builder, intent="era_establishing", created_from="epoch") → ExecutionDispatch (существующий) → существующий provider — **без единого нового типа/контракта** (все ограничения GO соблюдены).
2. Внешний контракт и исторический результат сохранены байт-в-байт (SHA-доказательство) — регрессии нулевые (92/92 combined, 200P/4F chunk, temporal 95P).
3. Temporal-архитектура не тронута: только чтение из существующего WorldModel (тест-инвариант + mtime-forensic).
4. PA-F1-схема Route A применена к B: план — смысловой канон, legacy-промпт — явно маркированная временная проекция исполнения (MD-5).
5. Ограничения соблюдены: нет второго canonical path, нет execution leakage, нет выдуманного temporal (404-семантика + is_temporal=False).

**Остаточные оговорки (не blockers):** (а) legacy-проекция живёт до MD-5 (вместе с dispatch — по плану владельца); (б) Route B не пишет план в ответ — план одноразовый в рамках запроса (персистенция = MD-4/Media-Project, решение владельца); (в) provenance эпохи arkaim_era в WorldModel пуст — план наследует пустоту честно (наполнение provenance = работа temporal-этапов, НЕ MD-3.2).

---

**STOP.** Route B мигрирован и закрыт. Маршруты C/E НЕ начаты. Жду вашего отдельного GO.
