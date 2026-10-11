# MD-3.1 IMPLEMENTATION REPORT — MediaPlan v0 Contract + Builder (подэтап 1 из 3)

**Дата:** 2026-09-12
**Статус:** IMPLEMENTED + TESTED — подэтап MD-3.1 завершён; MD-3.2 (миграция маршрутов) НЕ начат — ждёт отдельного GO владельца.
**Основа:** GO владельца на MD-3 implementation (10 owner decisions зафиксированы); MD3_PRE_IMPLEMENTATION_AUDIT (принят); ADR_MEDIA_PLAN_V0 (создан, ACCEPTED — фиксация owner decisions).
**Граница подэтапа:** ТОЛЬКО контракт + Builder + Dispatch + тесты + JSON-Schema + ADR. Ни один маршрут/провайдер/схема существующего кода не изменён (forensic: §8).

---

## Простыми словами

1. **Что было целью?** — создать «MediaPlan» — единый формат задания на генерацию картинки/видео (кто/где/когда/стиль/ограничения/происхождение/родословная) — без единого «исполнительного» параметра, и построитель планов из канонического Scene Context.

2. **Что реально сделано?** — новый домен-модуль `core/CORE/media_plan/` (4 файла): контракт MediaPlan v0 (23 смысловых поля), Builder (детерминированная проекция SceneContext→план: без LLM, без HTTP), временный конверт ExecutionDispatch (план→существующие провайдеры; явно помечен «REMOVE IN MD-5»), запрет-механизм execution-полей (pydantic extra="forbid" + BANNED_FIELDS + функция-верификатор). Плюс ADR (10 owner decisions зафиксированы), JSON-Schema (draft-07, как THEME/CHARACTER), 40 unit-тестов инвариантов.

3. **Что получилось?** — PASS. 40/40 новых тестов; регрессия: MD-2-семейство 438+40=478 passed / 1 pre-existing fail; visual-чанк 163+40=203 passed / 4 pre-existing fails; 0 изменений существующего кода.

4. **Есть ли проблемы?** — серьёзных нет. Один нюанс найден при тестировании: тесты ComfyUI-провайдера зависят от того, запущен ли реальный ComfyUI на порту 8188 (сегодня он был запущен — тесты «висли», пытаясь сделать настоящую генерацию; при недоступном порте проходят за 22 секунды). Это pre-existing особенность тестов (файл от 23.07 не менялся), не MD-3-дефект; задокументирована в §9.

5. **Что предлагается дальше?** — ваш GO на MD-3.2 (миграция маршрутов A–E по одному, каждый со STOP). Сам не начинаю.

---

## 1. Owner decisions — как зафиксированы в коде/ADR

| # | Решение владельца | Реализация |
|---|-------------------|------------|
| 1 | MediaPlan — отдельный доменный контракт, НЕ новый SceneContext | `core/CORE/media_plan/` — новый модуль; VisualContext+scene_extras не тронуты (0 правок visual/) |
| 2 | Размещение: доменный слой, не execution/runtime | модуль импортирует ТОЛЬКО visual/ (SceneContext-слой); ни одного импорта providers/visual_assets/pipeline |
| 3 | НЕТ execution-полей (model/steps/…/quality) | `BANNED_FIELDS` (15 значений вкл. quality) + `verify_no_execution_fields()` + pydantic `extra="forbid"` (runtime-отвержение) + тесты |
| 4 | quality НЕ оживлять | отсутствует в плане, в dispatch, в JSON-Schema; тест `test_dispatch_carries_no_quality` фиксирует запрет |
| 5 | negative — поле плана; цепочку НЕ чинить | `negative_constraints: list[str]` (смысл); до провайдеров НЕ пробивается (dispatch.negative — только конверт-строка для будущей передачи) |
| 6 | Отдельный ADR | `docs/ADR/ADR_MEDIA_PLAN_V0.md` (ACCEPTED; 8 решений + forbidden-список) |
| 7 | Frontend не менять | 0 правок arkaim-web (forensic §8) |
| 8 | ExecutionDispatch — временный мост | docstring «TEMPORARY MIGRATION BRIDGE — REMOVE IN MD-5»; поля НЕ часть плана (тест `test_dispatch_is_not_part_of_plan`); quality отсутствует |
| 9 | Provenance+lineage обязательны | наследование 1:1 (тесты §4); PlanLineage{parent_plan_id, derivation, created_from}; regenerate обязан ссылаться на родителя (тест `test_regenerate_references_parent`); lineage — не execution-metadata (тест: поля = ровно 3) |
| 10 | PA-F1 закрыт на уровне MD-3 | Builder строит план ИЗ SceneContext (данные консолидированы); текст промпта — существующий composer-контракт (заморожен); полное включение A-маршрута — MD-3.2 |

## 2. Фактическая схема MediaPlan v0 (23 поля)

```
core/CORE/media_plan/schemas.py:
  MediaPlan (pydantic, extra="forbid"):
    идентификация:    plan_id (plan_<hex12>) · plan_version "0.1.0" · media_kind (image|video|audio-reserved)
    смысл:            intent · structured_prompt · prompt · negative_constraints[]
                      characters[CharacterPlan] · location[LocationRef] · visual_style
                      atmosphere · camera[CameraPlan] · constraints[]
    MD-2-наследование: source_refs[SourceRefs] · temporal_context[TemporalSceneRef|None]
                      provenance[ProvenanceRef] (1:1 из temporal.provenance)
    родословная:      lineage[PlanLineage]
    video-only:       duration_sec · fps · sequence[ShotPlan[]] · motion[MotionPlan]
                      temporal_consistency[ContinuityRef|None]
  MediaKind.AUDIO = "audio" — ЗАРЕЗЕРВИРОВАН, схема НЕ определена (extension point)

  Запрет: BANNED_FIELDS = {model, checkpoint, ckpt, steps, cfg, sampler, seed, workflow,
           node_graph, nodegraph, provider, backend, comfyui, comfy_url, lora, loras,
           denoise, scheduler, execution, execution_settings, quality}
  verify_no_execution_fields() — рекурсивная проверка BANNED ∩ поля = ∅ (вкл. вложенные модели)
```

**Отчуждение от execution-слоя:** модуль не знает ни одного провайдера; единственный «выход наружу» — ExecutionDispatch (отдельный файл, dataclass, не pydantic, не часть контракта).

## 3. Builder — детерминированная проекция

```
MediaPlanBuilder.build_image_plan(ctx: VisualContext, intent?, style_override?,
                                  custom_prompt?, parent_plan_id?, derivation?, created_from?)
  → промпты: PromptComposer (generator="comfyui" — фактический дефолт пути D;
             шаблона "base" не существует — найдено и исправлено в реализации)
  → смысловые проекции: characters/location/camera/atmosphere из 15 измерений
  → MD-2: source_refs/temporal/provenance 1:1 (scene_ref_from_context, read-only)
  → custom_prompt (E/film): замещает ТОЛЬКО текст; structured_prompt сохранён
  → lineage: initial | regenerate/variation (parent обязателен)

build_video_plan(... + duration_sec, fps, shots[], camera_motion[CameraMovement],
                 character_actions[CharacterMotion], transitions[TransitionSpec],
                 continuity[ContinuityRef])
  → video-поля — проекция VideoContext-типов (первые объявленные consumers;
    подключение — MD-3.2/MD-4, в v0 только контракт)
```

Без LLM, без HTTP, без мутации ctx (immutable-паттерн MD-2: regenerate → новый план).

## 4. Provenance-наследование (проверено тестами)

- эпоха RECONSTRUCTION → план с provenance RECONSTRUCTION (`test_reconstruction_epoch_yields_reconstruction_plan`);
- наследование строго 1:1: `plan.provenance == temporal.provenance` (`test_provenance_of_plan_equals_temporal_provenance`);
- без эпохи — честно пусто: план НЕ выдумывает provenance (`test_plan_does_not_invent_provenance`);
- source_refs — идентификаторы, не копии (`test_source_refs_reference_only`: нет title/description).

## 5. Lineage (проверено тестами)

- initial: parent=None, derivation="initial", is_derived=False;
- regenerate: parent=первый план, derivation="regenerate", is_derived=True, НОВЫЙ plan_id;
- immutable: родитель не мутируется (`test_regenerate_does_not_mutate_parent`);
- lineage = ровно {parent_plan_id, derivation, created_from} — без storage/execution-метаданных;
- created_from: "scene_context" | "film_shot" | "epoch" (класс источника).

## 6. ExecutionDispatch — почему временный

- Фактический живой конверт провайдеров 2026-09-12: {prompt, size, preferred_provider, duration, fps} (источник: MD3_PRE §2.2 — след всех параметров всех 5 маршрутов);
- `from_plan(plan, size?, preferred_provider?, duration?, fps?)` — проекция; `image_kwargs()`/`video_kwargs()` — формы вызовов существующих цепей;
- quality НЕ входит (owner decision 4; тест-фиксация);
- docstring: «TEMPORARY MIGRATION BRIDGE — REMOVE IN MD-5»; не домен (dataclass, отдельный файл); не сериализуется в план (тест).

## 7. Тесты — 40/40 (runtime/tests/test_md3_media_plan.py)

9 групп: запрет execution (4) · Builder-из-SceneContext (6) · provenance-наследование (6) · lineage (5) · video-план (4) · dispatch (5) · сериализация (4) · audio-extension-point (3) · JSON-Schema-файл (3). Ключевые:
- `test_banned_intersect_fields_empty` — BANNED ∩ поля = ∅ (рекурсивно, вкл. вложенные);
- `test_banned_not_in_serialized_plan` — execution-строки отсутствуют в JSON-сериализации;
- `test_media_plan_direct_construction_has_no_banned_field` — pydantic extra="forbid": MediaPlan(model="sdxl") отвергается;
- `test_serialized_plan_matches_schema_contract` — каждый ключ to_dict покрыт MEDIA_PLAN.schema.json.

## 8. Регрессия + forensic boundary

**Тесты (все прогоны свежие, из runtime/):**

| Чанк | Результат | Вердикт |
|------|-----------|---------|
| test_md3_media_plan.py | **40 passed** | новый слой зелёный |
| temporal-чанк (16 файлов = MD-2 15 + md3) | **478 passed / 1 failed** | 1 = m9-fallback pre-existing order-pollution (MD-2 §10: воспроизводится без md2/md3-файлов) |
| visual-чанк (12 файлов = MD-2 11 + md3) | **203 passed / 4 failed** | 4 = test_assets_new_params ModuleNotFoundError 'runtime.core' — pre-existing (MD-2 §10; изолированно 0.19с воспроизводится) |
| per-file md2/m7/archetype/… | 23+15+11+… all green | additive-эффект отсутствует |

**ComfyUI-тест-зависимость (pre-existing, важно знать):** `test_visual_comfyui.py` (файл от 23.07, не менялся) конструирует провайдер на offline-порт 18188, но провайдер при generate()/health() перечитывает env COMFYUI_URL (дефолт 8188 — comfyui.py:109-113 «Re-read URL in case Colab tunnel changed»). Сегодня на 8188 **живой ComfyUI Desktop** (подтверждено MCP comfy_status: v0.34.5, CPU) → «offline»-тесты попадали на живой сервер (health=True → 1 fail; generate() → реальная постановка в очередь → _poll 300s → hang). С env COMFYUI_URL=127.0.0.1:18188 файл проходит целиком: **24 passed in 22s**; чанки воспроизводят точные цифры MD-2 (163/4, 438/1). Вывод: сетевая зависимость тестов от живого окружения — pre-existing (не MD-3; не чинится — вне scope).

**Forensic-граница MD-3.1 (mtime-окно сессии 09-12 13:00+):**

| Категория | Файлы |
|-----------|-------|
| НОВЫЕ (MD-3.1) | core/CORE/media_plan/{__init__.py, schemas.py, builder.py, dispatch.py} · runtime/tests/test_md3_media_plan.py · SCHEMAS/MEDIA_PLAN.schema.json · docs/ADR/ADR_MEDIA_PLAN_V0.md · docs/MD3_1_IMPLEMENTATION_REPORT.md (этот файл) |
| ИЗМЕНЁННЫЕ существующие | **НЕТ** (git: M-файлы — все pre-existing F1-F3-наследие с mtime ≤ 09-10; 0 правок visual/, providers/, routes/, visual_assets/, arkaim-web) |
| Тестовые side-effects (не код) | runtime/.tmp_md2_filmdb/film_test_*.db (film-тесты, паттерн MD-2) · core/GENOME/workflows/default.json (перезаписан идентичным DEFAULT_WF — git clean) · genome/history-снапшоты (genome-тесты, untracked, pre-existing поведение) · analytics_data.json/logs/ruff_cache |

**Forbidden-зоны (проверено):** providers/ (0 правок) · ComfyUI integration (0) · /comfyui/* routes (0) · temporal/WORLD_MODEL/GENOME-данные (0) · frontend (0) · film-БД F-12 (не тронута) · SharedSettings/C2/MD-4/MD-5 (не начаты).

## 9. Findings MP-F1…MP-F12 — статус после MD-3.1

| Finding | Статус |
|---------|--------|
| MP-F1 quality мёртв | ЗАКРЫТ НА УРОВНЕ КОНТРАКТА: quality в BANNED_FIELDS, отсутствует в плане/dispatch/Schema; тест-фиксация. «Оживление» — вне MD-3 (owner decision 4); documented gap остаётся для MD-4/5 |
| MP-F2 negative обрыв | Частично закрыт: negative_constraints — полноценное поле плана; до провайдеров НЕ пробивается (owner decision 5 — цепочку не чинить); финальное закрытие — MD-4/5 |
| MP-F3 GenerationParams витрина | NOT TOUCHED (MD-3.3: deprecation-метки после отдельного GO) |
| MP-F4 model не управляем Аркаимом | Подтверждён контрактом: model/seed/steps в BANNED |
| MP-F5 video витринный | Частично закрыт: video-поля теперь в контракте (sequence/motion/continuity — проекция VideoContext-типов); consumers подключаются в MD-3.2/MD-4 |
| MP-F6 ShotSpec↔ShotVersion двойники | Подготовлено: ShotPlan — единая плановая форма; ShotVersion→sequence проекция — MD-3.2 (E) |
| MP-F7 intent-словарь | Реализовано: intent: str + фактический базис key_frame (без enum-заморозки) |
| MP-F8 style-словари ×3 | NOT TOUCHED (консолидация — вне v0; visual_style: str) |
| MP-F9 lineage 0 | ЗАКРЫТ: PlanLineage + immutable-regenerate + тесты |
| MP-F10 E-деградация | Подготовлено: created_from="film_shot" + custom_prompt-механика; полная проекция ShotVersion→plan — MD-3.2 (E) |
| MP-F11 сериализация-прецедент | ЗАКРЫТ: to_dict (None-safe) + SCHEMAS/MEDIA_PLAN.schema.json (draft-07) + тесты соответствия |
| MP-F12 A/B legacy-промпты | Подтверждён дизайном: builder-промпты = composer-контракт; A/B-рендер прежний (PA-F1-вердикт владельца); переключение A/B — MD-3.2 |

**PA-F1:** закрыт на уровне Builder (план строится ИЗ SceneContext — поток данных консолидирован; текст промпта — замороженный контракт). Полное закрытие маршрута A — MD-3.2 (документировано; вердикт владельца соблюдён: не переписываем prompt path).

## 10. Оставшиеся gaps (честно)

1. **Маршруты A–E ещё не строят планы** — MD-3.2 (каждый со своим STOP; GO владельца).
2. **VisualAsset.generation (MB-3)** — живёт до MD-3.3 deprecation.
3. **quality end-to-end** — мёртв и НЕ в контракте (documented gap для MD-4/5; решение владельца).
4. **negative до провайдера** — обрыв сохранён (смысловое поле есть; пробитие — MD-4/5).
5. **test_visual_comfyui сетевая зависимость** — pre-existing: при живом ComfyUI на 8188 «offline»-тесты ходят на реальный сервер (env-перечитывание провайдера). Зафиксировано; не чинится в MD-3 (вне scope). Рекомендация для будущего: тест-фиксура env COMFYUI_URL → offline-порт (кандидат в MD-3.2-сопровождение тестов или отдельный тест-инфра-этап по решению владельца).
6. **словари стилей/эмоций ×3** — консолидация вне v0 (MD-3.3+).

## 11. Self-review (честные ответы)

- **Есть ли второй canonical MediaPlan path?** НЕТ: единственный Builder (media_plan/builder.py); прямое конструирование MediaPlan возможно, но НЕ canonical (builder — единственный путь планов; маршруты получат планы только через него в MD-3.2).
- **Утёк ли execution в план?** НЕТ: 4 теста-барьера (рекурсивный verify, сериализация, extra="forbid", Schema-файл) + ручной grep. Один нюанс: `preferred_provider` — параметр ВЫЗОВА dispatch (не поля плана) — это осознанный мост, помеченный MD-5.
- **Сломано ли что-то существующее?** НЕТ: 0 правок существующего кода; все чанки воспроизводят цифры MD-2.
- **Не начал ли я MD-3.2?** НЕТ: ни один маршрут не импортирует media_plan (проверено ниже grep'ом).
- **Шаблон "base":** при реализации найдено: у PromptComposer нет шаблона "base" (есть comfyui/flux/runway/kling/hailuo; дефолт пути D — comfyui). Исправлено до тестов; зафиксировано здесь как факт проектирования (не нарушение: дизайном предполагался base — фактический дефолт comfyui).

## 12. Changed files (полный список)

```
НОВЫЕ:
  core/CORE/media_plan/__init__.py      (export-контракт модуля)
  core/CORE/media_plan/schemas.py       (MediaPlan v0 + BANNED + verify)
  core/CORE/media_plan/builder.py       (MediaPlanBuilder)
  core/CORE/media_plan/dispatch.py      (ExecutionDispatch — TEMPORARY, MD-5)
  runtime/tests/test_md3_media_plan.py  (40 тестов)
  SCHEMAS/MEDIA_PLAN.schema.json       (draft-07)
  docs/ADR/ADR_MEDIA_PLAN_V0.md         (ADR — фиксация owner decisions)
  docs/MD3_1_IMPLEMENTATION_REPORT.md  (этот отчёт)
ИЗМЕНЁННЫЕ СУЩЕСТВУЮЩИЕ: НЕТ (0)
```

---

**STOP.** MD-3.1 завершён. MD-3.2 (миграция A–E по одному) НЕ начат — жду вашего отдельного GO. Первый кандидат миграции по плану MD3_PRE §9: маршрут D (уже SceneContext-путь — наименьший риск).
