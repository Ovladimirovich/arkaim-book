# MD-3.3 IMPLEMENTATION REPORT — JSON Schema reconciliation + deprecation marks + documentation registry

**Дата:** 2026-09-12 (поздний вечер)
**Статус:** IMPLEMENTED + TESTED — минимальный утверждённый scope выполнен полностью; verdict: **ЗАКРЫТ ПОЛНОСТЬЮ** (§9).
**Основа:** GO владельца на минимальный MD-3.3; MD3_3_PRE_IMPLEMENTATION_AUDIT (ACCEPTED, scope §9).
**Тип изменений:** metadata-уровень — schema-параметры, docstrings, docs, contract-тесты. **0 изменений поведения, 0 новых контрактов, 0 миграций.**

---

## Простыми словами

1. **Что было целью?** — закрыть единственное реальное расхождение (файл внешнего описания плана не запрещал лишние поля, в отличие от самого плана) и поставить метки «устарело» ровно на две доказанно мёртвые функции.

2. **Что реально сделано?** — (а) в JSON-схему плана добавлен запрет посторонних полей и описания для двух видео-полей; (б) две мёртвые функции получили метки «устарело» с указанием замены (удаление — только в MD-5); (в) создан документ-реестр: что устарело, что НАМЕРЕННО живо, фактические словари intent/lineage; (г) 31 контракт-тест, включая главный: «исполнительное поле → внешняя валидация ПАДАЕТ».

3. **Что получилось?** — **PASS.** 31/31 новых; комбинированная регрессия всех этапов MD-3 (включая все 5 маршрутов) — **149/149 в обоих порядках**; визуальный чанк = прежняя база + 31 (4 старых падения — прежние); кино-зона 40/40; поведение кода не изменилось ни в одном месте (доказано тестами D1/D5 «прежнее поведение»).

4. **Есть ли проблемы?** — нет. Одна честная деталь: в проекте нет стандартной библиотеки JSON-валидации (и добавлять её — вне scope), поэтому тест использует минимальный встроенный валидатор, покрывающий ровно те проверки, что нужны контракту (запрет посторонних полей, обязательные ключи, типы, перечисления). Также зафиксировано: найденная при аудите «мёртвая DI-точка» оказалась фабрикой (функция-обёртка была удалена раньше — в списке экспорта осталась висячая строка, это старый факт, чистка — вне scope).

5. **Что дальше?** — ваш ACCEPT/CLOSE по MD-3.3. На этом MD-3 (контракт → 5 маршрутов → метки/схема/доки) завершён целиком. MD-4/MD-5 и любые findings — только по вашим отдельным решениям. **STOP.**

---

## 1. Что изменено (полный список, 5 файлов)

| Файл | Изменение | Тип |
|------|-----------|-----|
| `SCHEMAS/MEDIA_PLAN.schema.json` | `additionalProperties: false` (top-level) + описания video-only у `duration_sec`/`fps` + $comment/description-уточнения | M1 (schema) |
| `core/CORE/visualization/prompt_builder.py` | D1: docstring `build_full_prompt_pair` → DEPRECATED + canonical replacement (MD-3.3, audit D1) | M2 (метка) |
| `runtime/core/adc_deps.py` | D5: docstring `_factory_prompt_composer` → DEPRECATED + replacement (audit D5) | M2 (метка) |
| `runtime/tests/test_md3_route_deprecations.py` | НОВЫЙ: 31 контракт-тест | M1+M2 (тесты) |
| `docs/MD3_3_DEPRECATION_REGISTRY.md` | НОВЫЙ: реестр устареваний + живых механизмов + словари intent/created_from/derivation | M2 (docs) |

**Тестовые side-effects (не код, pre-existing поведение тест-прогонов):** genome/history-снапшоты, workflows/default.json (перезапись идентичным), analytics_data.json — тот же класс, что зафиксирован в отчёте MD-3.1 §8.

## 2. Что намеренно НЕ изменено

- **MediaPlan pydantic-схема / Builder / ExecutionDispatch** — 0 правок (mtime 16:27–16:38 = MD-3.1); семантика контракта НЕ расширена, новых полей НЕТ.
- **Routes A/B/C/D/E + pipeline** — 0 правок (mtime их собственных сессий, до 22:30).
- **Исторические промпт-проекции** (`build_scene_prompt`/`build_epoch_prompt`/`build_asset_prompt`/`build_shot_prompt`/STYLE_PRESETS), **PromptComposer**, **VisualAsset/GenerationParams** (asset-модель ответа), **ShotVersion/CameraSpec**, **очередь/batch/regenerate**, **SceneEngine dict-сцены**, **visual_context_builder.build*** — живые совместимые механизмы, deprecation НЕ поставлена (реестр §2).
- **quality/negative/camera/duration-поля, словари стилей, video-pipeline, `__all__`-висячие строки, F-12, frontend, ComfyUI, providers, WorldModel/temporal, SceneContext** — не тронуты (найденное = findings, §8).
- **required/optional схемы** — без изменений (аудит R2: намеренная строгость контракта).

## 3. Schema before/after

| Аспект | Before | After |
|--------|--------|-------|
| Посторонние поля | **НЕ запрещены** (JSON с `"model":"sdxl"` проходил внешнюю валидацию, хотя домен его отвергает — расхождение R1 аудита) | **`"additionalProperties": false`** — посторонние/execution-поля отвергаются схемой, как pydantic extra=forbid |
| `duration_sec` / `fps` | без описаний (R3 documentation-drift) | `"video-only: … задаётся при media_kind=video (semantic-поле, не execution)"` |
| $comment / description | без упоминания additionalProperties | дополнены фактом запрета (MD-3.3) |
| required (4) · properties (22) · enums · provenance/lineage-структуры · video-only-набор | — | **БЕЗ ИЗМЕНЕНИЙ** (несемантических правок нет; контракт не расширен) |

Главная пара инвариантов теперь зелёная в тестах: **execution field → JSON Schema FAILS** (13 execution-полей + произвольное постороннее) и **execution field → MediaPlan/Pydantic FAILS** (runtime-инвариант MD-3.1 сохранён).

## 4. Deprecation before/after

| ID | Before | After |
|----|--------|-------|
| **D1** `build_full_prompt_pair` | `"""Вернуть (positive_prompt, negative_prompt)."""` — без метки | `"""DEPRECATED (MD-3.3, audit D1): 0 production-потребителей. Canonical replacement: MediaPlanBuilder.build_image_plan(ctx) → план несёт prompt + negative_constraints… удаление — MD-5+. Историческое поведение: (positive, negative)."""` — **функция не удалена, тело без изменений** (тест D1 «прежнее поведение» = зелёный) |
| **D5** `_factory_prompt_composer` (registry-key `"prompt_composer"`) | безликая фабрика | `"""DEPRECATED (MD-3.3, audit D5): мёртвая DI-точка — 0 потребителей… Canonical replacement: MediaPlanBuilder(generator="comfyui")… удаление — MD-5+."""` — **тело без изменений** (тест D5 зелёный) |

Уточнение к D5 (честная фиксация): в аудите точка описана как `get_prompt_composer`; фактически такой функции НЕ существует (удалена ранее) — мёртвой является фабрика + registry-key, а в `__all__` осталась висячая строка-ссылка (pre-existing; чистка — finding F-33-4, вне scope). Метка поставлена на фактический мёртвый символ.

**DeprecationWarning НЕ ставился ни одной функции** — по аудиту живые пути (queue/batch/regenerate) граничат с deprecated-зонами; warning-логика = поведенческое изменение, вне минимального scope.

## 5. Tests — `runtime/tests/test_md3_route_deprecations.py`, 31/31 PASS

| GO-пункт | Тесты |
|----------|-------|
| 1. Schema отвергает execution | `test_execution_field_fails_validation` ×13 (model/checkpoint/steps/cfg/sampler/seed/workflow/nodes/provider/backend/quality/lora/denoise — каждый FAILS с «Additional properties are not allowed») + `test_arbitrary_unknown_field_fails` |
| 2. Schema принимает валидный план | `test_valid_image_plan_passes` · `test_all_four_required_keys_present` · `test_real_md2_scene_ctx_plan_passes` (план из РЕАЛЬНОГО genome-контекста) |
| 3. video-only | `test_valid_video_plan_passes` · `test_video_only_descriptions_present` · `test_wrong_type_duration_fails` |
| 4. provenance/lineage | `test_lineage_in_valid_plan_passes` · `test_regenerate_lineage_with_parent_passes` (immutable + parent) · `test_provenance_schema_shape` |
| 5. deprecated — прежнее поведение | `test_d1_build_full_prompt_pair_still_works` (идентично паттерну test_visualization) · `test_d1_has_deprecation_docstring` · `test_d5_factory_still_works` · `test_d5_factory_has_deprecation_docstring` |
| 6. нет execution leakage | `test_pydantic_runtime_invariant_still_green` (MediaPlan(**data_with_model) → ValidationError; verify_no_execution_fields()==[]) · `test_no_execution_properties_in_schema` |
| 7. структурная целостность | `test_additional_properties_false_top_level` · `test_schema_is_valid_draft7` |

Реализация валидации: `jsonschema`-пакет отсутствует в venv и requirements (добавление зависимости — вне scope) → минимальный draft-07-валидатор в тест-файле (object/array/type/required/additionalProperties/enum/const + обёртка .message) — покрывает ровно используемое подмножество контракта; тесты проверяют КОНТРАКТ, не реализацию.

## 6. Regression

| Набор | Результат | Вердикт |
|-------|-----------|---------|
| test_md3_route_deprecations.py | **31 passed** | новый набор зелёный |
| Combined: MD-3.3 + MD-3.1 + MD-3.2 (A+B+C+D+E) + md2_routes — прямой/обратный порядок | **149 passed ×2** | 118 прежних + 31; 0 задето |
| Visual-chunk 17 файлов (16 + md3.3) | **257P / 4F** = база E (226P/4F) + 31 | 4F = pre-existing test_assets_new_params (изолированно 4F — подтверждено) |
| test_film_endpoints.py (E-зона, смежная с D5) | **40 passed** | adc_deps-метка ничего не сломала |
| ruff: мой тест-файл | **чист** | — |

Ruff в production-файлах правок: `prompt_builder.py` F401 (`typing.Optional` unused) и `adc_deps.py` F822 (висячие `__all__`-строки: `get_visual_context_builder`/`get_prompt_composer`/`get_continuity_engine`) — **ВСЕ pre-existing** (существовали до MD-3.3; не мои строки; исправление вне scope — «никакого cleanup заодно»).

## 7. Forensic scope verification (финальный чек-лист GO)

| Проверка | Результат |
|----------|-----------|
| git diff / git status | Мои правки сессии: Schema (untracked-файл MD-3.1, проверен содержимым напрямую) + 2 docstring-вставки + 2 новых файла. В diff production-файлов (prompt_builder/adc_deps) мои строки — ТОЛЬКО DEPRECATED-docstrings |
| Production files — только разрешённые MD-3.3 места | ✅ 3 файла: Schema + 2 docstring (прочие diff-строки — pre-existing наследие принятых сессий: BOM, pollinations-удаление, MD-2-WorldModel, MD-2-метки) |
| SceneContext unchanged | ✅ scene_context.py 10.09; visual_context*.py — mtime MD-2-сессий |
| WorldModel/temporal unchanged | ✅ 05.09 |
| A/B/C/D/E route logic unchanged | ✅ visual.py 20:29 / assets.py 21:39 / film_studio.py 22:30 / pipeline.py 21:38 — mtime сессий маршрутов, 0 правок MD-3.3 |
| MediaPlan semantic contract не расширен | ✅ pydantic-схема 16:38 (0 правок); Schema: 22 properties / 4 required / enums — без изменений |
| ExecutionDispatch unchanged | ✅ 16:27 |
| provider/runtime unchanged | ✅ providers/ 0 правок (инцидентов нет) |
| frontend / ComfyUI unchanged | ✅ 0 файлов arkaim-web/comfyui в сессии |
| no second Builder / no second canonical path | ✅ `from media_plan` — те же 7 точек маршрутов; новых путей нет |
| no execution leakage | ✅ 31 тест (Schema+pydantic-барьеры) + BANNED-инвариант |
| no unrelated fixes | ✅ единственные production-правки — 2 docstring (по утверждённым D1/D5) |

## 8. Remaining findings (не исправлены — вне scope, решения владельца)

1. **F-33-1** (audit R5): Route C (video) строит video-план, но `generate_video` не принимает plan/dispatch — план одноразовый. Кандидат MD-4.
2. **F-33-2** (R6): `dispatch.negative` — поле-мост без consumers (MP-F2-семейство). Исчезнет в MD-5.
3. **F-33-4** (новый, из реализации): `__all__` adc_deps содержит висячие строки `get_visual_context_builder`/`get_prompt_composer`/`get_continuity_engine` (несуществующие функции; pre-existing; ruff F822). Чистка — MD-5+ (вне минимального scope).
4. **MP-F1** quality (dead; MD-4/5) · **MP-F2** negative до провайдера (MD-4/5) · **MP-F8** словари стилей ×3 · **MP-F10** dead-поля шота — прежние documented gaps.
5. **Pre-existing failures/lint:** test_assets_new_params ×4 (ModuleNotFoundError); TestFeedbackStore ×12 (TEMP-policy); COMFYUI_URL-зависимость test_visual_comfyui; W293×15 visual.py; F401/F822 (§6). Все — вне MD-3.3.

## 9. Final verdict

**MD-3.3 ЗАКРЫТ ПОЛНОСТЬЮ в утверждённом минимальном объёме:**
1. **Schema reconciliation:** R1 закрыт — `additionalProperties: false` (эквивалент extra="forbid" на уровне внешнего контракта) + R3 закрыт (video-only descriptions); семантика/required/поля — без изменений. Инварианты-пара зелёная: execution → Schema FAILS + execution → Pydantic FAILS.
2. **Deprecation:** ровно 2 доказанно мёртвые функции помечены (D1/D5) с canonical replacement; 0 удалений; 0 поведенческих изменений (тесты «прежнее поведение»); живые совместимые механизмы НЕ помечены (реестр §2).
3. **Documentation registry:** создан (deprecated/живые/словари intent·created_from·derivation/findings).
4. **Contract-тесты:** 31/31 по всем 7 GO-пунктам.
5. **Regression:** 149/149 combined ×2; чанк = база+31 (те же 4 pre-existing failures); ruff-правки мои чисты; forensic-чек-лист — 13/13 ✅.

**MD-3 (MediaPlan Contract v0) завершён целиком:** контракт (MD-3.1) → 5 маршрутов на каноническом пути (MD-3.2 A/B/C/D/E, все ACCEPTED) → schema/deprecation/docs reconciliation (MD-3.3).

---

**STOP.** MD-4/MD-5/finding-фиксы автоматически не начинаются. Жду вашего ACCEPT/CLOSE по MD-3.3.
