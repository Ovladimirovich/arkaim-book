# MD-3.2 ROUTE C IMPLEMENTATION REPORT — миграция `/assets/generate` на canonical MediaPlan path

**Дата:** 2026-09-12
**Статус:** IMPLEMENTED + TESTED — Route C мигрирован; verdict: **ЗАКРЫТ ПОЛНОСТЬЮ** (§Verdict); Route E — НЕ начат (ждёт отдельного GO).
**Основа:** GO владельца на MD-3.2 Route C; Routes A/B/D ACCEPTED; ADR_MEDIA_PLAN_V0.
**Граница подэтапа:** маршрут `generate_asset` (assets.py) + pipeline-метод `generate_image` (опц. plan/dispatch); A/B/D/E-зоны, frontend, temporal, MediaPlan schema/builder/dispatch — не тронуты (forensic §10).

---

## Простыми словами

1. **Что было целью?** — перевести «Генерацию ассета для сцены» (маршрут с самыми богатыми параметрами: стиль, настроение, размер, провайдер, негатив, качество) на канонический конвейер, правильно разложив параметры: смысловые — в план, исполнительные — во временный конверт.

2. **Что реально сделано?** — маршрут строит MediaPlan из канонического контекста сцены (стиль/настроение/негатив — смысловые поля плана); провайдер, размер и «качество» остались исполнительными деталями и проходят ТОЛЬКО через временный конверт (в план не попадают; мёртвое «качество» не оживлено — как приказано). Исторический промпт сохранён байт-в-байт. 12 тестов, включая шпион-провайдер.

3. **Что получилось?** — **PASS.** Оба исторических промпта (дефолт и со стилем) идентичны ДО/ПОСЛЕ по крипто-хэшам; ответ — те же 29 полей; 404/422-семантика прежняя; 12/12 новых; 104/104 комбинированных; чанк = база + 12.

4. **Есть ли проблемы?** — нет. По пути честно задокументированы ДВА pre-existing-факта (не дефекты миграции): (а) параметр «настроение» никогда не доходил до ассета — пайплайн берёт эмоцию сцены из контекста (мёртвый параметр; поведение ДО = ПОСЛЕ); (б) видео-ветка маршрута падает на старой ошибке провайдера видео — существующий дефект вне моих полномочий, зафиксирован.

5. **Что дальше?** — ваш ACCEPT по Route C, затем GO на **Route E `/shots/generate`** — последний немигрированный. Сам не начинаю.

---

## 1. Baseline (создан ДО изменения: `docs/MD3_2_ROUTE_C_BASELINE.md`)

- **Endpoint:** POST `/book/assets/generate` (SuccessResponse; editor). Параметры: chapter, scene_id, asset_type(image|video), style, mood, provider, reader_id, size, negative_prompt, quality(draft|standard|high|ultra).
- **Ответ (200):** 29 ключей asset-модели; status completed; prompt_used; generation={provider, model:"sdxl", size, seed:None, steps:30, quality, negative_prompt[...]}.
- **Исторические промпты + хэши:** дефолт → SHA `e5e41db21768c86e`; с style=mythic_realism, mood=трепет → SHA `29443ace06ff8894` (style ВЛИЯЕТ на текст через STYLE_PRESETS).
- **Provider-path (spy):** `generate_with_metadata(prompt, size, preferred_provider)` — до execution доходят prompt, size, preferred_provider.
- **Классификация параметров (выполнена в baseline):** style/mood/negative_prompt/asset_type — смысловые; provider/size/quality — ИСПОЛНИТЕЛЬНЫЕ (в план не идут); reader_id — метаданные.

## 2. Exact changed files

```
ИЗМЕНЕНЫ (2 существующих; зоны только Route C):
  runtime/core/routes/assets.py    — generate_asset: план (build_image_plan /
                                      build_video_plan по asset_type) + dispatch;
                                      docstring. НЕ тронуты: generate_asset_async
                                      (очередь — отдельный путь), D-зоны, batch.
  core/CORE/visual_assets/pipeline.py — generate_image: +plan/+dispatch (опц.);
                                      legacy-промпт как проекция в dispatch;
                                      провайдер через dispatch.image_kwargs();
                                      без plan — прежний путь byte-identical.
НОВЫЕ (3):
  runtime/tests/test_md3_route_c.py — 12 тестов
  docs/MD3_2_ROUTE_C_BASELINE.md   — снимок «до»
  docs/MD3_2_ROUTE_C_IMPLEMENTATION_REPORT.md — этот отчёт
НЕ ТРОНУТЫ: A/B (visual.py — правки прежних принятых сессий), D-зоны assets.py,
  queue.py (async-вариант — вне GO), film_studio.py (E, mtime 11.09),
  media_plan/* (16:27-16:38), SCHEMAS, providers, frontend, temporal.
```

## 3. Tests — `runtime/tests/test_md3_route_c.py`, 12/12 PASS

| GO-пункт | Тест |
|----------|------|
| 1. План из canonical SceneContext | test_plan_built_from_canonical_ctx (source_refs, visual_style=style_override, intent) |
| 2. Provider через ExecutionDispatch | test_provider_receives_via_dispatch (spy: size/preferred из конверта) |
| 3. Spy получает исторический prompt | там же (prompt == asset.prompt_used) |
| 4. Prompt до/после идентичен | test_prompt_identical_default (SHA e5e41db21768c86e) + test_prompt_identical_with_params (SHA 29443ace06ff8894) |
| 5. Response contract | test_response_contract_29_keys |
| 6. Asset semantics | test_asset_semantics_preserved (style/size/quality/negative/provider в asset-модели; mood-факт baseline) |
| 7. Execution fields вне плана | test_no_execution_fields_in_plan (пров./размер/качество отсутствуют в сериализации) + test_negative_prompt_is_plan_constraint |
| 8. Unknown input без синтеза | test_unknown_scene_404_no_synthesis (404, spy пуст) |
| 9. Existing error behavior | test_invalid_asset_type_422 · test_video_path_preexisting_behavior · 404-тест |
| 10. Нет второго canonical path | test_no_second_canonical_path (dispatch вне плана) |

## 4. Regression

| Набор | Результат |
|-------|-----------|
| test_md3_route_c.py | **12 passed** |
| Combined C→B→A→D→md3→md2_routes (обе последовательности) | **104 passed** ×2 |
| Visual-chunk 15 файлов (14 + route_c) | **212P / 4F** = база B (200P/4F) + 12; 4F = pre-existing test_assets_new_params |
| md2_routes::TestRouteCGenerateAsset (существующие C-тесты) | 2P |
| Route A/B/D tests | 12P / 10P / 15P (не задеты) |
| MD-3.1 tests | 40P |
| ruff (мой тест; мои зоны) | чист (pre-existing F401/F841 в assets/pipeline — есть в HEAD, чужие зоны) |

## 5. Prompt compatibility

Исторический промпт `build_asset_prompt(asset)` — **byte-identical** (оба SHA-совпадения: дефолт и параметризованный). Prompt-архитектура/словари не переписаны; legacy cleanup не проводился. Механика: маршрут строит план → pipeline строит исторический текст из asset-модели → **проекция в dispatch** (`dispatch.prompt = prompt`, метка «MD-5: удалить») → провайдер. План несёт СВОЙ canonical composer-промпт — слои разделены (как A/B/D). Изменений промпта НЕТ — поэтому не требовалось отдельного решения по п.4 GO.

## 6. Asset semantics

Asset-модель ответа (29 полей) — прежняя: style (влияет на текст), mood (факт: emotion сцены из ctx — см. Findings), generation.size/quality/negative_prompt/provider, status/asset_id/file_path/prompt_used — вся семантика ДО = ПОСЛЕ (побайтные сверки в базовом и параметризованном сценариях).

## 7. Execution-dispatch flow

```
SceneContext → MediaPlanBuilder.build_image_plan(ctx, style_override=style, …)
  → MediaPlan (смысловые: style/atmosphere/negative_constraints/media_kind…)
  → ExecutionDispatch.from_plan(plan, size=<size-param>, preferred_provider=<provider-param>)
  → pipeline.generate_image(…, plan, dispatch)
  → dispatch.prompt = build_asset_prompt(asset)   [legacy-проекция, ПОСЛЕ плана]
  → provider.generate_with_metadata(**dispatch.image_kwargs())
  → asset.generation заполняется фактическим ответом провайдера (как раньше)
```
До execution доходят: prompt, size, preferred_provider — ровно как в baseline (spy-сверка). quality — остаётся только в legacy-asset-модели (generation.quality), в dispatch/план НЕ добавлен (MP-F1: не оживлять).

## 8. Execution leakage

- Сериализованный план не содержит model/steps/seed/cfg/sampler/workflow/provider/backend/quality/checkpoint/lora/**size** (тест).
- `verify_no_execution_fields()` = [] ; extra="forbid" действует (40 MD-3.1-тестов зелёные).
- provider/size прошли ТОЛЬКО через dispatch-параметры (from_plan-аргументы), в план не попали (построчная сверка вставки).
- MediaPlan schema/builder/dispatch — mtime MD-3.1-окна (0 правок).

## 9. Forensic scope

- assets.py: моя вставка — ТОЛЬКО generate_asset (hunks @@ -47/-64 → L50-115); D-зоны (163-289) — прежние принятые правки; generate_asset_async (очередь) НЕ тронут; hunk @@ -1 (BOM) и @@ -116 (async-docstring) — pre-existing MD-2-наследие.
- pipeline.py: мои вставки — generate_image (Route C) + generate_image_from_context (Route D, принятая); остальные hunks — pre-existing MD-2.
- 1 canonical path: `from media_plan` = assets.py:88 (C!) /197/237/276 (D) + visual.py:77 (A) /164 (B) — все через один MediaPlanBuilder.
- film_studio.py (E) — mtime 11.09; frontend — 0 правок после 21:30; world_model.py — 05.09; media_plan/* — 16:27-16:38.
- CJK 0; baseline-скрипт удалён; git status: новые = test_md3_route_c.py + 2 документа.

## 10. Pre-existing failures / Findings (вне scope — только зафиксированы)

1. **dead-параметр mood (Route C):** параметр запроса mood НЕ доходит до asset.mood — пайплайн всегда берёт emotion сцены из SceneContext; overrides["mood"] игнорируется. Поведение идентично ДО/ПОСЛЕ (baseline-снимок это доказывает: mood="трепет" → asset.mood="конфликт" и до, и после). Семья MP-F3 (dead GenerationParams-поля). НЕ чинил (вне scope).
2. **VideoProviderChain.health (Route C video-ветка):** asset_type=video → 200 + asset, генерация падает `'VideoProviderChain' object has no attribute 'health'` → status failed. Pre-existing (наблюдался в baseline ДО миграции). НЕ чинил (provider-слой = forbidden-зона).
3. **test_assets_new_params ×4** (ModuleNotFoundError) — во всех базах.
4. **TestFeedbackStore ×12 / TEMP-policy, 15×W293 visual.py, unknown-reader FK** — прежние зафиксированные (см. Route B/D-отчёты).

## 11. Verdict по Route C

**Route C ЗАКРЫТ ПОЛНОСТЬЮ:**
1. Канонический путь: SceneContext (существующий) → MediaPlan (существующий Builder; image- и video-варианты) → ExecutionDispatch (существующий; provider/size — только здесь) → существующий pipeline/provider — без новых типов/контрактов/Builder'ов.
2. Классификация параметров выполнена (п.3 GO): смысловые (style/mood/negative/asset_type) — в плане; исполнительные (provider/size) — только dispatch; **quality НЕ оживлён** (dead MP-F1: остался в legacy-asset-ответе, в план/dispatch не добавлен).
3. Внешний контракт и исторические промпты — байт-в-байт (два SHA-доказательства); регрессии нулевые (104/104 combined ×2; 212P/4F chunk; существующие C-тесты зелёные).
4. Ограничения соблюдены: нет второго canonical path; нет execution leakage; 404/422/error-семантика прежняя; без синтеза SceneContext-данных.

**Остаточные оговорки (не blockers):** (а) legacy-промпт-проекция живёт до MD-5 (план владельца); (б) generate_asset_async (очередь) и batch — НЕ мигрированы (в маршруте только sync-`/assets/generate` по GO; очередь — кандидат отдельного решения); (в) два Findings (dead-mood, VideoProviderChain) — переданы владельцу как зафиксированные pre-existing.

---

**STOP.** Route C мигрирован и закрыт. Route E НЕ начат. Жду вашего ACCEPT по Route C и отдельного GO на Route E.
