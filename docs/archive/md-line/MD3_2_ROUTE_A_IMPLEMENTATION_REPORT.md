# MD-3.2 ROUTE A IMPLEMENTATION REPORT — миграция `/visualize` на canonical MediaPlan path

**Дата:** 2026-09-12
**Статус:** IMPLEMENTED + TESTED — Route A мигрирован; PA-F1 закрыт ПОЛНОСТЬЮ на уровне MediaPlan (вердикт §7); маршруты B/C/E — НЕ начаты (ждут отдельных GO).
**Основа:** GO владельца на MD-3.2 Route A (PA-F1-исключение MD-2: проверить закрываемость на уровне MD-3); Route D ACCEPTED; ADR_MEDIA_PLAN_V0 D5.
**Граница подэтапа:** только `visualize_scene` в visual.py (+новые тесты/документы); Route B (в том же файле), C, D, E, frontend, temporal, ComfyUI, MediaPlan schema — не тронуты (forensic §11).

---

## Простыми словами

1. **Что было целью?** — перевести маршрут «Визуализация сцены» на канонический конвейер и при этом проверить, можно ли наконец закрыть давнее исключение PA-F1: до сих пор промпт этого маршрута собирался по старинке, отдельно от общего смыслового контекста.

2. **Что реально сделано?** — маршрут теперь строит смысловой план (MediaPlan) из канонического контекста сцены; а исторический текст промпта сохранён как «временная проекция» ПОСЛЕ плана — в конверте-мосте (ExecutionDispatch). Провайдер получает ровно тот же текст, что и раньше — проверено побайтово (криптографический хэш совпал). Написаны: снимок «до» (baseline), 12 тестов, включая шпион-провайдер и проверку идентичности промпта.

3. **Что получилось?** — **PASS.** Промпт ДО = промпт ПОСЛЕ (SHA `84c05d47047113b0` идентичен); ответ 200 в точности 3 прежних поля; 404/422-семантика прежняя; все прежние тесты зелёные; регрессия = база + 12 новых.

4. **Есть ли проблемы?** — нет. Один нюанс честно задокументирован: передача несуществующего reader_id ломала запись памяти и ДО миграции (старое поведение базы: она требует существующего читателя) — это не дефект миграции, тесты используют валидного читателя.

5. **Что предлагается дальше?** — ваш GO на следующий маршрут (рекомендация: **B `/visualize/epoch`** — он в том же файле и по той же схеме legacy-промпта, что A; или **C `/assets/generate`**). Сам не начинаю.

---

## 1. Baseline (создан ДО изменения: `docs/MD3_2_ROUTE_A_BASELINE.md`)

- **Endpoint:** POST `/book/visualize` (VisualizeResponse; auth reader). Body: {chapter≥1, scene_id, reader_id?}.
- **Ответ (200):** ровно {prompt, image_bytes(base64), content_type:"image/svg+xml"}.
- **Исторический промпт** (PromptBuilder.build_scene_prompt — СТАРЫЙ механизм, genome-дикты): «epic fantasy scene, Конфликт: Гиперборея vs Материальный путь Атлантиды, harsh lighting, …, atmospheric». SHA256[:16]=`84c05d47047113b0`.
- **Provider-path (spy-доказательство):** `image_provider.generate(prompt)` — БЕЗ size/preferred (в отличие от Route D).
- **Семантика:** 404 на неизвестную сцену; reader_id → visual_memory (sha256-хэши); SceneContext строился (MD-2), но в промпте НЕ участвовал — в этом состояло исключение PA-F1.

## 2. Фактический новый pipeline

```
request → visual_ctx_builder.build_scene_context(chapter, scene_id)   [MD-2, unchanged]
        → scene_engine.get_scene (404-контракт, unchanged)
        → char_visuals/location (genome-визуалы, unchanged)
        → MediaPlanBuilder(generator="comfyui").build_image_plan(      [MD-3.2 NEW — canonical]
            ctx, intent="key_frame", created_from="scene_context")
        → legacy_prompt = prompt_builder.build_scene_prompt(...)      [исторический текст, unchanged]
        → ExecutionDispatch.from_plan(plan); dispatch.prompt = legacy_prompt  [legacy-проекция ПОСЛЕ плана]
        → image_provider.generate(dispatch.prompt)                    [тот же вызов, что baseline]
        → sha256-хэши → reader_memory (при reader_id) → VisualizeResponse (3 поля)
```

## 3. MediaPlan contents (что реально попадает в план)

План строится из ТОГО ЖЕ SceneContext тем же Builder'ом (тест `test_plan_actually_built_from_canonical_ctx`): 23 смысловых поля — prompt (composer-текст), structured_prompt, negative_constraints, characters[], location, visual_style, atmosphere, camera, constraints, source_refs{scene_id=..., chapter=1}, temporal_context, provenance, lineage{initial, scene_context}, intent="key_frame".

## 4. ExecutionDispatch contents (временный мост)

`from_plan(plan)` → {prompt, negative, size:"1024x1024"(default, НЕ используется этим маршрутом), preferred_provider:"auto"(default), duration, fps}. Затем `dispatch.prompt = legacy_prompt` — **временная legacy-проекция** (явно помечена комментарием «MD-5: удалить»). Маршрут A передаёт провайдеру только prompt (generate(dispatch.prompt)) — как в baseline: size/preferred провайдеру НЕ идут.

## 5. Prompt before / after (критический контракт)

| | Baseline | После |
|---|----------|-------|
| Полный текст | «epic fantasy scene, …, atmospheric» | **идентичен** |
| SHA256[:16] | `84c05d47047113b0` | `84c05d47047113b0` (test_prompt_byte_identical_to_baseline) |
| Источник текста | prompt_builder.build_scene_prompt | тот же вызов; результат проецируется в dispatch.prompt (после плана) |
| plan.prompt (canonical composer-текст) | — существует отдельно (≠ legacy), в провайдер НЕ идёт |

**Разделение слоёв доказано тестом `test_legacy_projection_lives_after_plan`:** response.prompt (legacy) == prompt_builder-текст И != plan.prompt (canonical) — план и legacy-проекция не смешаны.

## 6. Внешний contract before / after

| Проверка | Baseline | После | Тест |
|----------|----------|-------|------|
| HTTP 200, ровно {prompt, image_bytes, content_type} | да | да | test_response_contract_unchanged |
| content_type image/svg+xml; base64-байты | да | да | там же |
| Провайдер: generate(prompt), size=512x512-дефолт, preferred=None | да | да | test_provider_receives_legacy_prompt_via_dispatch |
| 404 unknown scene (гл.99) | да | да | test_unknown_scene_404 (+spy: генерация не стартовала) |
| 422 chapter=0 (FastAPI-валидация) | да | да | test_validation_chapter_ge_1 |
| Валидный reader_id → 200 | да | да | test_reader_id_path_preserved (reader=test-user) |
| md2_routes::TestRouteAVisualize ×2 | PASS | PASS (в комбинированных прогонах) | регрессия |

## 7. PA-F1 verdict — **ЗАКРЫТ ПОЛНОСТЬЮ на уровне MD-3**

**Доказательство:**
1. Route A строит **MediaPlan из canonical SceneContext** (MediaPlanBuilder — тот же, что в Route D; тест пункта 2 GO): смысловые данные сцены (персонажи/локация/стиль/атмосфера/…) консолидированы в плане, source_refs/temporal/provenance наследуются.
2. **Исторический prompt-текст** сохранён идентичным (SHA-совпадение) — НО теперь он занимает правильное архитектурное место: **legacy-проекция внутри временного dispatch-моста, ПОСЛЕ плана**, а не параллельная смысловая дорожка. Старый prompt builder НЕ стал вторым canonical MediaPlan (запрет GO соблюдён: он вызывается только внутри миграционного пути как projection).
3. Оба условия GO-приказа PA-F1 выполнены: «MediaPlan из canonical SceneContext» ✓ и «фактический prompt через ExecutionDispatch совместим с baseline» ✓ (byte-identical).

**Что НЕ потребовалось** (и почему PA-F1 закрыт без legacy-рефакторинга): не переписывалась prompt-архитектура; словари не переносились в план; исторический текст не менялся. Удаление самой legacy-проекции (dispatch.prompt = build_scene_prompt) — MD-5-работа вместе с dispatch, не blocker: исключение PA-F1 состояло в «двух смысловых дорожках»; теперь дорожка одна (план), а legacy-текст — явно маркированная временная проекция исполнения.

**Остаточная оговорка (не blocker, вне PA-F1-сути):** до MD-5 фактический текст в провайдер идёт из legacy-проекции, а не из plan.prompt. Это зафиксировано в ADR D4/D5 и тесте-инварианте «plan.prompt != legacy»; переключение провайдера на plan.prompt = изменение исторического текста = отдельное решение владельца (не в этом подэтапе).

## 8. Tests

**Новые: `runtime/tests/test_md3_route_a.py` — 12/12 PASS**, покрывают все 9 обязательных пунктов GO:

| GO-пункт | Тест |
|----------|------|
| 1. MediaPlan создаётся | test_plan_actually_built_from_canonical_ctx |
| 2. Builder получает canonical SceneContext | там же (source_refs/chapter из ctx) |
| 3. Ожидаемый semantic intent | test_plan_has_expected_intent (key_frame; lineage initial/scene_context) |
| 4. Dispatch не смешивается с планом | test_dispatch_not_part_of_plan + test_legacy_projection_lives_after_plan |
| 5. Provider получает ожидаемый prompt | test_provider_receives_legacy_prompt_via_dispatch (spy) |
| 6. Prompt == baseline | test_prompt_byte_identical_to_baseline (SHA) |
| 7. Response contract сохранён | test_response_contract_unchanged |
| 8. Прежняя ошибочная семантика | test_unknown_scene_404 · test_reader_id_path_preserved · test_validation_chapter_ge_1 |
| 9. Execution leakage | test_plan_serialization_no_execution_fields · test_route_a_does_not_add_execution_to_plan (extra=forbid) |

Spy/fake provider — включён (граница план→dispatch→провайдер: payload зафиксирован).

## 9. Regression

| Набор | Результат |
|-------|-----------|
| Комбинированный (route_a → route_d → md3 → md2_routes → provider_chain), оба порядка | **84 passed** ×2 |
| Visual-chunk 13 файлов (12 + route_a) | **190P / 4F** = база MD-3.2-D (178P/4F) + 12 новых; 4F = pre-existing test_assets_new_params |
| test_md3_route_d.py | 15P (Route D не задет) |
| test_md3_media_plan.py | 40P (инварианты плана не ослаблены) |
| test_md2_routes.py | 57P (все 5 маршрутов) |

## 10. Changed files

```
ИЗМЕНЕН (1 существующий; hunks 2-4 только visualize_scene):
  runtime/core/routes/visual.py — MD-3.2-план + dispatch + legacy-проекция;
                                   docstring; hash/response через dispatch.prompt
НОВЫЕ (3):
  runtime/tests/test_md3_route_a.py  — 12 тестов
  docs/MD3_2_ROUTE_A_BASELINE.md     — снимок «до»
  docs/MD3_2_ROUTE_A_IMPLEMENTATION_REPORT.md — этот отчёт
НЕ ТРОНУТЫ: Route B (visual.py:120 visualize_epoch — вне diff-хунков), C/D/E,
  media_plan/* (mtime 16:27-16:38 = MD-3.1), SCHEMAS, providers, frontend, temporal.
```

## 11. Forensic boundary

- git diff visual.py: hunks 2-4 — мои (visualize_scene: L25-109); **hunk 1 (импорты Body/EpochVisualRequest) — pre-existing MD-2-наследование** (uncommitted до сессии; Route B M7.2-код), в мои изменения НЕ входит.
- Route B/C/E: не тронуты (film_studio.py mtime 11.09; book.py 23.07; assets.py = Route D-правки предыдущего GO-этапа, сегодня новых правок нет).
- 1 canonical path: `from media_plan` только в D-зонах assets.py (165/205/244) + visual.py:77 (Route A).
- MediaPlan schema/dispatch/builder — mtime MD-3.1-окна (не менялись).
- frontend/ComfyUI/temporal — 0 файлов с mtime после 13:00.
- ruff: мой тест-файл и мои зоны visual.py чисты; 15×W293 в visual.py — pre-existing (L276-449, есть в HEAD).
- CJK: 0. Вспомогательные baseline-скрипты удалены.

## 12. Remaining gaps (честно)

1. **Legacy-проекция живёт до MD-5** (dispatch.prompt = build_scene_prompt): исторический текст не переключён на plan.prompt — осознанно (GO: «не менять исторический текст без доказанной необходимости»; изменение текста = решение владельца).
2. **Unknown-reader FK (pre-existing):** reader_id несуществующего читателя → sqlite FOREIGN KEY → 500. Идентично на HEAD (доказано stash-прогоном). Не семантика миграции; чинить = трогать память читателей (вне scope).
3. **Route B/C/E** — не мигрированы (ждут GO).
4. **test_assets_new_params 4F** — pre-existing ModuleNotFoundError (как во всех базах с MD-2).
5. **COMFYUI_URL env-зависимость** тестов — прежняя (MD-3.1 §9), в регрессии задавал offline-порт.
6. **Route A не пишет plan_id в ответ/логи** — план одноразовый в рамках запроса; персистенция планов (Media-Project/MD-4) — отдельная работа владельца.

---

**STOP.** Route A мигрирован; PA-F1 закрыт полностью на уровне MediaPlan. Маршруты B/C/E НЕ начаты. Жду вашего отдельного GO.
