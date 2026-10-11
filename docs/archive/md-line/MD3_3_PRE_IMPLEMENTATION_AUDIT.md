# MD-3.3 PRE-IMPLEMENTATION AUDIT — forensic inventory + проектирование deprecation/schema/docs

**Дата:** 2026-09-12 (вечер, после закрытия Route E)
**Статус:** AUDIT ONLY — 0 изменений production-кода (проверено git status + mtime: ни один файл не менялся после начала аудита; все production-правки репозитория — принятые сессии MD-2/MD-3.1/MD-3.2).
**Основа:** MD-3.2 CLOSED (все 5 маршрутов A/B/C/D/E ACCEPTED); ADR_MEDIA_PLAN_V0; MD3_PRE_IMPLEMENTATION_AUDIT; MEDIA_DIRECTION_FOUNDATION.
**Вывод аудита:** GO-рекомендация на МИНИМАЛЬНЫЙ объём MD-3.3 — см. §12.

---

## Простыми словами

1. **Что было целью?** — без единой правки кода провести ревизию: что в проекте осталось «старого» после перевода всех пяти маршрутов на новый конвейер, и что из этого можно безопасно пометить «устаревшим», а что трогать нельзя.

2. **Что реально сделано?** — прочитаны все опорные документы (ADR, схема, отчёты); построена полная карта вызовов всех промпт-генераторов, семантических структур и исполнительных полей; каждый кандидат проверен на ЖИВЫХ потребителей (не по возрасту файла, а по фактическим вызовам); сверены четыре описания контракта MediaPlan (ADR / Pydantic / Builder / JSON Schema / 5 маршрутов) поле за полем.

3. **Что получилось?** — **PASS (аудит завершён).** Главная находка: JSON Schema не выражает запрет лишних полей (в Pydantic он есть, а в Schema — нет) — это единственное реальное расхождение, которое стоит чинить. Найдено 2 функции без потребителей (кандидаты на метку «устарело»), 2 переходных факта (видео-план маршрута C строится, но до видеопайплайна не доходит; негатив в конверте не используется провайдерами) — всё задокументировано, ничего не чинилось.

4. **Есть ли проблемы?** — нет блокеров. Важно понимать: почти всё «старое» — это ЖИВЫЕ мосты совместимости (исторические промпты, очередь, перегенерация, модель ассета в ответах) — их НЕЛЬЗЯ помечать устаревшими, они держат принятые исторические контракты. Устаревшими можно пометить только действительно мёртвое (2 функции + 2 поля-витрины).

5. **Что дальше?** — ваш GO на минимальный MD-3.3: (а) запрет лишних полей в JSON Schema + описания video-полей; (б) метки «устарело» на 2 мёртвые функции; (в) документационный реестр устареваний. Ничего большего не предлагаю. STOP.

---

## 1. Current State

- **Все 5 маршрутов** (A `/visualize`, B `/visualize/epoch`, C `/assets/generate`, D `/assets/generate-context|character|location`, E `/film/…/shots/{id}/generate`) строят MediaPlan из canonical SceneContext через единственный MediaPlanBuilder; провайдер получает данные через ExecutionDispatch; исторические промпты — byte-identical legacy-проекции ПОСЛЕ плана (SHA-доказательства в отчётах маршрутов).
- MediaPlan v0 (22 поля): `core/CORE/media_plan/{schemas,builder,dispatch}.py` + `SCHEMAS/MEDIA_PLAN.schema.json` (draft-07) — не менялись с MD-3.1 (mtime 16:27–16:38).
- 118 тестов MD-3 (40 контрактных + 12+10+12+15+14 маршрутов) зелёные; регрессия = база + новые.

## 2. Canonical Path (фактический, единый)

```
request → build_scene_context* (MD-2, 4 варианта: scene/character/location/epoch)
  → MediaPlanBuilder(generator="comfyui"|<gen>).build_image_plan|build_video_plan
      (intent, created_from, style_override?, custom_prompt?)          [единственный Builder]
  → MediaPlan (extra="forbid", BANNED-инвариант)
  → ExecutionDispatch.from_plan(plan, size?, preferred_provider?)      [TEMPORARY → MD-5]
  → legacy prompt projection: dispatch.prompt = исторический текст     [A/B/C/E]
  → существующий provider/pipeline (generate_with_metadata | generate)
Точки входа канонического пути (git-grep `from media_plan`, 7 мест):
  visual.py:77 (A) · visual.py:164 (B) · assets.py:88 (C) · assets.py:197/237/276 (D) ·
  film_studio.py:368 (E). Второго canonical path НЕТ.
```

## 3. Legacy/Semantic Inventory (call-graph, не возраст файлов)

### 3.1 Prompt generators — фактические потребители

| Path → symbol | Потребители (production) | Живой? | Класс |
|---|---|---|---|
| `visualization/prompt_builder.py` → `PromptBuilder.build_scene_prompt` | Route A (visual.py:86 — legacy-проекция после плана) | ДА | **legacy projection (живой контракт)** |
| → `PromptBuilder.build_epoch_prompt` | Route B (visual.py:173 — проекция) | ДА | legacy projection |
| → `PromptBuilder.build_negative_prompt` | только `build_full_prompt_pair` (внутри того же класса) | косвенно | transitional |
| → `PromptBuilder.build_full_prompt_pair` | **0 в production** (bot/scripts/notebooks — 0; только self) | НЕТ | **dead → deprecation candidate D1** |
| `visual_assets/prompt_builder.py` → `build_asset_prompt` | pipeline.generate_image (Route C/E проекция: L142/151), generate_video (L272), очередь, regenerate, batch | ДА | legacy projection (живой контракт) |
| → `build_shot_prompt` | pipeline `_generate_video_from_frames` (L309 — video-fallback) | ДА | legacy (video-ветка) |
| → `build_negative_prompt` | pipeline L152 (asset-модель) | ДА | legacy витрина |
| → `STYLE_PRESETS` | pipeline (префиксы стилей) | ДА | legacy словарь (MP-F8) |
| `visual/prompt_composer.py` → `PromptComposer` | MediaPlanBuilder (canonical, builder.py:52) + pipeline fallback (L427, без плана) | ДА | **canonical renderer + legacy fallback** |
| `runtime/core/adc_deps.py` → registry-фабрика `"visual_prompt_composer"` / `get_prompt_composer` (L197/359) | **0 Depends-consumers** (маршруты composer получают через Builder; grep = только экспорт) | НЕТ | **dead DI-точка → deprecation candidate D5** |

### 3.2 Semantic структуры

| Path → symbol | Потребители | Класс |
|---|---|---|
| `VisualContext` + `scene_extras` (MD-2) | все 5 маршрутов, Builder, pipeline | **canonical SceneContext** |
| `VisualAsset` (visual_assets/schemas) | РЕЗУЛЬТАТ пайплайна: внешние контракты ответов `/assets/*` (29 ключей), asset-store, film-проекция; legacy-проекция промпта C/E строится из asset-модели | **живой контракт результата** (semantic-поля дублируют план — transitional до MD-4/5; MD-2-метка «deprecated как ВХОД» уже стоит, корректна) |
| `GenerationParams` (внутри VisualAsset) | asset-ответ, pipeline (provider/size реально работают) | **execution-витрина MP-F3** (см. §4) |
| `ShotSpec` (visual_assets) | asset.shots (video) | legacy video-витрина (MP-F6: дубль ShotVersion) |
| `ShotVersion`/`CameraSpec`/`CameraMotion` (film_studio/schemas) | film-БД + маршруты E (create/update) | **живой film-контракт** (showcase-поля — §4) |
| dict-сцены SceneEngine (get_scene → dict) | Routes A/B (вход legacy-промпта), pipeline, очередь | legacy data-структура (живая — держит исторический промпт A/B) |
| `visual_context_builder.build()/build_for_character/build_for_location` | внутренние вызовы build_scene_context* (L641/655/663) | **внутренняя основа** (MD-2-метки уже стоят; НЕ кандидаты) |

### 3.3 Немигрированные генерационные пути (живые, вне 5 маршрутов)

| Путь | Что вызывает | Статус |
|---|---|---|
| `/assets/generate-async` + `/assets/batch` → `GenerationQueue` (queue.py:125-135) | `pipeline.generate_image/generate_video` **без SceneContext и без плана** (dict-сцены, build_asset_prompt) | живой legacy-путь (async/batch migration — ЗАПРЕЩЕНА в MD-3.3) |
| `/assets/{id}/regenerate` (assets.py:429) | `pipeline.generate_image(chapter, scene_id, overrides)` без ctx/плана | живой legacy-путь |
| `pipeline.generate_batch` (L376-378) | generate_image/generate_video без плана | живой (очередь) |
| `pipeline.generate_video` (все видеовызовы) | build_asset_prompt; **plan/dispatch НЕ принимает** (сигнатура без параметров) | живой legacy; см. Finding F-33-1 |

## 4. Execution Leakage Inventory (классификация; ничего не менялось)

| Место | Поле | Класс | Комментарий |
|---|---|---|---|
| GenerationParams | `provider` | execution, ЖИВОЙ | asset-ответ + до провайдера (dispatch.preferred) — корректно |
| GenerationParams | `size` | execution, ЖИВОЙ | до провайдера (dispatch.size) |
| GenerationParams | `model` ("sdxl"), `steps` (30), `seed` (None) | **dead/showcase** | никогда не управляют генерацией (MP-F4; константные значения в ответе) |
| GenerationParams | `quality` | **dead (MP-F1)** | не оживляется; решение MD-4/5 |
| GenerationParams | `negative_prompt` | semantic→план (negative_constraints); в asset — витрина до провайдера НЕ доходит (MP-F2) | корректно разделено |
| Route-параметры C/E | `provider`, `size` | execution | после MD-3.2 идут ТОЛЬКО через dispatch — правильно |
| Route-параметры C/E | `quality`, `mood` | dead (quality — MP-F1; mood — emotion из ctx, Route C/E отчёты) | задокументировано |
| Шот E | `camera`, `duration_sec`, `negative` | **dead/showcase (MP-F10)** | в film-БД/ответе, до pipeline не доходили и не доходят |
| MediaPlan | `camera`, `duration_sec`, `fps`, `sequence`, `motion`, `temporal_consistency` | **semantic** (композиция/video-intent контракта MD-3.1) | НЕ execution — до провайдера не идут (spy-доказательства E) |
| ExecutionDispatch | `prompt`, `negative` | semantic-проекция / transitional | см. F-33-2 |
| ExecutionDispatch | `size`, `preferred_provider`, `duration`, `fps` | execution bridge (TEMPORARY → MD-5) | корректно вне плана |

**Вывод: execution в MediaPlan НЕ протекает** (BANNED-инвариант + extra=forbid + 4 тест-барьера; подтверждено спиями всех 5 маршрутов). Обратных утечек нет.

## 5. MediaPlan Contract Reconciliation (ADR / Pydantic / Builder / Schema / 5 маршрутов)

Сверены все 22 поля. Полная матрица:

| Поле | ADR | Pydantic | Builder | JSON Schema | A/B/C/D/E | Статус |
|---|---|---|---|---|---|---|
| plan_id | D8 (uuid) | `str=""` (default) | всегда `plan_<hex12>` | required, `^plan_[a-f0-9]+$` | все | ✅ (R2: pydantic default "" vs schema required — осознанная строгость контракта, builder гарантирует; зафиксировать в docs) |
| plan_version | D8 | `"0.1.0"` | наследует | required, const 0.1.0 | все | ✅ |
| media_kind | D1/D2 | image\|video\|audio-reserved | IMAGE/VIDEO | enum ✓ | image везде; video: C(video-запрос) | ✅ |
| intent | MP-F7 (str, без enum) | str="key_frame" | параметр | string | key_frame×5, era_establishing(B), character_study/location_study(D), scene_motion(C-video), film_shot(E) | ✅; фактический словарь — в §9 docs-план |
| structured_prompt | PA-F1 (заморожен) | str | composer | string | — (execution = проекция) | ✅ |
| prompt | D5 (текст заморожен; custom E) | str | custom_prompt замещает | required | A/B/C/D=проекция legacy; E=shot.prompt | ✅ |
| negative_constraints | D2 (semantic) | list[str] | из composer_negative | array ✓ | — (не до провайдера, MP-F2) | ✅ |
| characters/location/camera/constraints | проекции ctx | ✓ | из 15 измерений ctx | object-схемы ✓ | наследуются | ✅ |
| visual_style / atmosphere | проекции | ✓ | style_override or ctx | ✓ | C/E: override; A/B/D: ctx | ✅ |
| source_refs / temporal_context / provenance | D3 (1:1) | dataclass-refs | scene_ref_from_context (read-only) | ✓ (вкл. rag_fallback) | наследуются (B: temporal_arkaim_era, provenance=[]) | ✅ |
| lineage | D3 | {parent, derivation, created_from} | initial/regenerate | ✓ | created_from: scene_context×7, epoch, film_shot | ✅ |
| duration_sec / fps | video-семантика | 8.0 / 24 | build_video_plan | number/integer **без description** | C-video | ⚠ R3: schema-описание «video-only» отсутствует — documentation drift |
| sequence / motion / temporal_consistency | video-only | ShotPlan/MotionPlan/ContinuityRef | build_video_plan | ✓ (описания есть) | пока без потребителей | ✅ |

**Расхождения (полный список, ничего не чинилось):**
- **R1 (ЕДИНСТВЕННОЕ реальное schema-drift):** JSON Schema НЕ содержит `"additionalProperties": false` — pydantic `extra="forbid"` в схеме не выражен: JSON с execution-полем пройдёт schema-валидацию, хотя домен его отвергает. → кандидат №1 MD-3.3.
- **R2:** schema `required` строже pydantic-default'ов (все поля имеют defaults) — intentional: контракт требует ID у валидного плана, builder гарантирует. Не менять; отразить в docs.
- **R3:** `duration_sec`/`fps` в Schema без пометки «video-only» (у sequence/motion — есть) — documentation drift → кандидат MD-3.3 (описания).
- **R4:** MD3_1-отчёт заявляет «23 поля», фактически 22 — мелкий documentation drift (не критично; в MD-3.3 docs поправить число).
- **R5 → Finding F-33-1:** Route C при asset_type=video строит video-план (`build_video_plan`, intent=scene_motion), но `pipeline.generate_video` не принимает plan/dispatch — план одноразовый, до pipeline не доходит. Поведение byte-identical (тест C), вреда нет; это переходный пробел video-ветки. Чинить = менять сигнатуру pipeline (production) — ЗАПРЕЩЕНО в MD-3.3. Фиксация → решение владельца (кандидат MD-4).
- **R6 → Finding F-33-2:** `dispatch.negative` проецируется из плана, но НИ ОДИН провайдер его не получает (image_kwargs/video_kwargs не содержат negative; провайдеры не принимают) — поле-мост без consumer (MP-F2 следствие). Поле корректно как переходное; исчезнет в MD-5 вместе с dispatch. Не менять.
- **R7 → Finding F-33-3:** registry-фабрика `"visual_prompt_composer"`/`get_prompt_composer` (adc_deps) — 0 Depends-потребителей (маршруты получают composer через MediaPlanBuilder; прямой import в pipeline) — мёртвая DI-точка. Кандидат deprecation-метки (после контрольной проверки тестов/скриптов на GO-этапе).

## 6. JSON Schema Reconciliation (что делать MD-3.3)

1. **Добавить `"additionalProperties": false`** — привести schema в соответствие pydantic extra="forbid" (R1). Единственное функциональное изменение Schema; contract-тест: объект с execution-полем НЕ валиден по Schema.
2. **Добавить descriptions** `duration_sec`/`fps`: «video-only: задаётся при media_kind=video» (R3).
3. **required/optional** — соответствует (4 required; остальные optional-with-defaults: семантика «валидный план обязан иметь ID/версию/вид/текст») — НЕ менять.
4. **enums/provenance/lineage/video-only/regenerate-parent** — соответствуют ADR (проверено поле за полем §5); regenerate-семантика (parent_plan_id при derivation≠initial) — в pydantic-контракте и ADR D3; в Schema выражена типом, дополнительно не требуется.
5. Иного Schema НЕ требует. «Не менять ради изменения» — соблюдено: только 2 точечных правки.

## 7. Deprecation Candidate Matrix

| # | Path → symbol | Почему | Canonical replacement | Живые consumers | Метка безопасна? | Удалять сейчас? |
|---|---|---|---|---|---|---|
| D1 | visualization/prompt_builder → `build_full_prompt_pair` | 0 production-потребителей | план: prompt+negative_constraints (или PromptComposer) | 0 (только self-вызов build_negative_prompt) | ДА: docstring DEPRECATED + DeprecationWarning | НЕТ (MD-5+) |
| D2 | visual_assets/schemas → GenerationParams.{model, seed, steps} | dead/showcase: никогда не управляют (MP-F3/MP-F4) | — (execution решает Media-проект, MD-4/5) | внешний контракт ответа (29 ключей) — читают, но не управляют | ТОЛЬКО docstring-метка полей «showcase»; БЕЗ warning (внешний контракт) | НЕТ |
| D3 | GenerationParams.quality | dead MP-F1 | documented gap MD-4/5 | asset-ответ | docstring «dead (MP-F1)» | НЕТ |
| D4 | VisualAsset как смысловой ВХОД | уже помечен MD-2; остаётся результатом | SceneContext → MediaPlan | pipeline C/E (источник legacy-проекции промпта) — живой | метка уже стоит; дополнить: «проекция-источник legacy-промпта до MD-5» | НЕТ |
| D5 | adc_deps → `get_prompt_composer` / registry `"visual_prompt_composer"` | 0 Depends-потребителей | MediaPlanBuilder(generator=…) | 0 маршрутов (контрольная проверка тестов на GO-этапе) | ДА (docstring DEPRECATED; warning — по результату проверки) | НЕТ |
| D6 | pipeline.generate_image — legacy-ветка (без plan) | все 5 маршрутов передают план; очередь/regenerate/batch — нет | MediaPlan path | ОЧЕРЕДЬ (queue.py:125), REGENERATE (assets.py:429), BATCH (L376) — ЖИВЫЕ | НЕТ warning (живые пути!) — только docstring-комментарий «legacy entry (queue/batch/regenerate) до MD-4/5» | НЕТ |

**Категорически НЕ помечать deprecated (живые контракты совместимости):**
- `PromptBuilder.build_scene_prompt` / `build_epoch_prompt` — это НЕ dead: byte-identical-проекции исторического текста A/B (PA-F1-вердикт владельца); живут до MD-5.
- `build_asset_prompt` / `build_shot_prompt` / `build_negative_prompt` / STYLE_PRESETS — живые проекции C/E/video/очереди.
- `ExecutionDispatch` — уже помечен «REMOVE IN MD-5» (не трогать).
- `VisualAsset` (результат), `ShotVersion`/`CameraSpec` (film-контракт), dict-сцены SceneEngine (вход legacy-промпта A/B), queue-пути, `visual_context_builder.build*` (внутренняя основа) — живые; только фактические dead-поля задокументированы.

## 8. Compatibility Constraints (что держит принятое)

1. **Внешние response-контракты всех 5 маршрутов** — заморожены (29 ключей C, 3 ключа A/B, 4 ключа E, asset-модель D): GenerationParams/quality/model/steps/seed — часть ответов → только docstring-метки, никак не warning/удаление.
2. **Исторические промпты** (SHA A/B/C/E) — держатся legacy-билдерами → они живые compatibility projections, не deprecated.
3. **Очередь/batch/regenerate** — живые пути без плана; миграция async/batch запрещена (owner).
4. **MediaPlan schema/builder/dispatch** — менять только Schema-файл (R1/R3); pydantic/builder/dispatch — 0 правок.
5. **MP-F8 (словари стилей ×3), MP-F2 (negative до провайдера), MP-F10 (dead camera/duration шота), F-33-1/R5 (video-план)** — вне MD-3.3 (findings, решения владельца).

## 9. Exact MD-3.3 Scope (предложение, только после GO)

1. **JSON Schema** (`SCHEMAS/MEDIA_PLAN.schema.json`, 2 правки): `additionalProperties: false` + descriptions duration_sec/fps («video-only»); $comment дополнить фактом additionalProperties.
2. **Deprecation-метки** (docstrings, минимально):
   - D1 `build_full_prompt_pair` — DEPRECATED docstring + DeprecationWarning (0 потребителей);
   - D5 `get_prompt_composer`/фабрика — DEPRECATED docstring (warning только если контрольный прогон тестов/скриптов подтвердит 0 вызовов);
   - D2/D3 — docstring-метки полей GenerationParams («showcase»/«dead MP-F1»), БЕЗ поведенческих изменений;
   - D6 — docstring-комментарий на pipeline.generate_image о живых legacy-точках (queue/batch/regenerate), БЕЗ warning;
   - D4 — дополнение существующей MD-2-метки VisualAsset.
3. **Документационная reconciliation** (docs/, без кода): реестр deprecations (матрица §7 с вердиктами); фактические словари intent (6 значений) и created_from (3 значения) + lineage-семантика regenerate; фиксация findings F-33-1/2/3; число полей плана (22) в сводке; статус-обзор 5 маршрутов.
4. **Contract-тесты** (1 файл `test_md3_route_deprecations.py` или расширение test_md3_media_plan.py): Schema отвергает execution-поле (additionalProperties); Schema отвергает постороннее поле; to_dict() всегда содержит 4 required-ключа; duration_sec/fps описания присутствуют (schema-структурный smoke); deprecation-метки D1/D5 присутствуют (inspect docstring) — только факт наличия, не поведение.

**Оценка объёма:** 1 schema-файл + docstrings в ≤5 файлах + 1 docs-файл + 1 тест-файл. 0 изменений поведения, 0 новых контрактов, 0 миграций.

## 10. Forbidden Scope (MD-3.3 — подтверждено владельцем, включено в план)

MD-4/MD-5 · перенос ComfyUI · Media Project · удаление legacy-слоёв/промпт-генераторов/ExecutionDispatch · изменение SceneContext/WorldModel/temporal/C2 · frontend · provider redesign · film-studio redesign · DB · F-12 · quality revival · audio · async/batch migration · SharedSettings · оживление dead-поля (camera/duration/negative/mood/quality) · изменение исторических контрактов · unrelated fixes · «cleanup заодно». Findings F-33-1/2/3 и MP-F2/F8/F10 — фиксация, НЕ исправление.

## 11. Proposed Test Plan (MD-3.3, после GO)

| Тест | Что доказывает |
|---|---|
| schema_additional_properties_forbidden | JSON с `"model": "sdxl"` (и любым посторонним ключом) НЕ валиден по Schema — R1 закрыт |
| pydantic_schema_parity_smoke | ключи to_dict() ⊆ properties Schema; 4 required присутствуют всегда |
| schema_video_only_descriptions_present | duration_sec/fps имеют video-only description — R3 закрыт |
| deprecation_marks_present (D1/D5) | docstring-метки существуют (inspect), warnings не ломают импорт |
| Регрессия: md3-набор 40+63 + visual-chunk 16 файлов + film 40 | поведение не изменилось (те же цифры: 226P/4F и т.д.) |
| ruff + git diff-обзор | только запланированные файлы |

## 12. GO / NO-GO recommendation

**GO — на минимальный объём §9 (4 пункта):** все изменения — metadata-уровень (schema-параметры + docstrings + docs + contract-тесты); рисков для живых контрактов нет; R1 — реальное расхождение, стоит закрыть; D1/D5 — доказанно мёртвые, метки честны.

**NO-GO (отложено, отдельно владельцу):** любые правки behavior — R5/F-33-1 (video-план до pipeline), R6/F-33-2 (negative до провайдера), R7-проверка внешних вызовов composer-фабрики за пределами репо, MP-F8 (словари стилей), миграция queue/regenerate. Для каждого требуется отдельное решение и отдельный GO.

---

**Финальная верификация аудита (выполнена):** git status — 0 новых production-правок за сессию аудита (все M-файлы — принятые сессии MD-2/MD-3.1/MD-3.2, uncommitted по политике владельца); MediaPlan schema/builder/dispatch — mtime MD-3.1 (16:27–16:38); SceneContext 10.09, WorldModel 05.09, temporal/frontend/providers/ComfyUI — 0 изменений. Изменённые файлы этой сессии: **1 — этот отчёт**.

**STOP.** Жду вашего решения по объёму MD-3.3 (GO/NO-GO/правка scope).
