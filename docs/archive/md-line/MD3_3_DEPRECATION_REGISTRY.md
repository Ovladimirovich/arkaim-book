# MD-3.3 — DEPRECATION & CONTRACT REGISTRY

**Статус:** DOCUMENTED (MD-3.3; GO владельца на минимальный scope).
**Основа:** docs/MD3_3_PRE_IMPLEMENTATION_AUDIT.md (ACCEPTED) — все метки ниже = только доказанно мёртвые символы (audit §7); живые совместимости НЕ помечены.
**Правило:** deprecation-метка = docstring + canonical replacement. 0 удалений, 0 изменений поведения. Удаление любых элементов — MD-5+ (решение владельца).

---

## 1. Deprecated (MD-3.3 — метки поставлены)

| ID | Symbol (path) | Причина (доказательство аудита) | Canonical replacement | Метка | Удаление |
|----|---------------|----------------------------------|----------------------|-------|----------|
| **D1** | `PromptBuilder.build_full_prompt_pair` — `core/CORE/visualization/prompt_builder.py:356` | 0 production-потребителей (call-graph: bot/scripts/notebooks = 0; только self-вызов `build_negative_prompt`) | `MediaPlanBuilder.build_image_plan(ctx)` → план несёт `prompt` + `negative_constraints` | docstring «DEPRECATED (MD-3.3, audit D1)» + replacement | MD-5+ |
| **D5** | `_factory_prompt_composer` / registry-key `"prompt_composer"` — `runtime/core/adc_deps.py:196` | Мёртвая DI-точка: 0 Depends-потребителей (composer-рендер выполняется внутри MediaPlanBuilder; прямой import в pipeline — legacy fallback) | `MediaPlanBuilder(generator="comfyui")` (канонический путь плана) | docstring «DEPRECATED (MD-3.3, audit D5)» + replacement | MD-5+ |

**Важно (pre-existing факт, не метка):** строка `"get_prompt_composer"` в `__all__` adc_deps ссылается на несуществующую функцию (висячая ссылка, была до MD-3.3). Чистка `__all__` — вне минимального scope (finding, см. §4).

## 2. Намеренно НЕ помечены deprecated (живые совместимые механизмы)

Каждый пункт — живой контракт, необходимый до MD-5; помечать = нарушать принятые решения владельца:

| Механизм | Почему живой |
|----------|--------------|
| `PromptBuilder.build_scene_prompt` / `build_epoch_prompt` | **Исторические legacy-проекции промптов Routes A/B** (byte-identical, PA-F1-вердикт владельца). Не dead — держат замороженный внешний контракт. |
| `build_asset_prompt` / `build_shot_prompt` / `build_negative_prompt` / `STYLE_PRESETS` (visual_assets/prompt_builder) | Legacy-проекции C/E + video-fallback + очередь/batch/regenerate — все ЖИВЫЕ вызовы. |
| `PromptComposer` (visual/prompt_composer.py) | **Canonical renderer плана** (внутри MediaPlanBuilder) + legacy fallback pipeline (без плана). |
| `ExecutionDispatch` | Уже помечен «TEMPORARY MIGRATION BRIDGE — REMOVE IN MD-5» (ADR D4). Не трогать. |
| `VisualAsset` (результат) + `GenerationParams` | Внешние response-контракты `/assets/*` (29 ключей) + asset-store; legacy-источник промпт-проекции C/E. Semantic-вход — уже MD-2-метка. |
| `ShotVersion` / `CameraSpec` / `CameraMotion` (film_studio) | Живой film-контракт (create/update/generate). |
| Очередь (`GenerationQueue`), batch, `/assets/{id}/regenerate` | Живые пути без плана; async/batch migration — запрещена (решение владельца). |
| `visual_context_builder.build()` / `build_for_character` / `build_for_location` | Внутренняя основа `build_scene_context*` (MD-2-метки уже стоят; НЕ dead). |
| dict-сцены SceneEngine (get_scene) | Живой вход legacy-промпта A/B + pipeline/очередь. |

## 3. Словари фактических значений (документация контракта)

### intent (фактические значения 5 маршрутов, MD-3.2)

| Значение | Маршрут | Смысл |
|----------|---------|-------|
| `key_frame` | A `/visualize` · C `/assets/generate` (image) · D (3 подмаршрута) | ключевой кадр сцены (default Builder) |
| `era_establishing` | B `/visualize/epoch` | устанавливающий кадр эпохи |
| `character_study` | D `/assets/generate-character` | портретное изучение персонажа |
| `location_study` | D `/assets/generate-location` | изучение локации |
| `scene_motion` | C (asset_type=video) | движение сцены (video-intent) |
| `film_shot` | E `/film/…/shots/{id}/generate` | кадр киносъёмки |

intent — `str` без enum-заморозки (MP-F7: намеренно открытый словарь; новые значения = additive).

### lineage.created_from (фактические)

| Значение | Где | Источник плана |
|----------|-----|----------------|
| `scene_context` | A, C, D×3 | `build_scene_context(chapter, scene_id)` |
| `epoch` | B | `build_scene_context_for_epoch(epoch_id)` |
| `film_shot` | E | `build_scene_context(chapter, scene.scene_id)` + `custom_prompt=shot.prompt` |

### lineage.derivation

`initial` (все текущие планы маршрутов) · `regenerate` / `variation` / `adaptation` — контракт Builder (`parent_plan_id` обязателен для производных; immutable — новый plan_id; ADR D3). Фактические производные планы пока не создаются маршрутами (regenerate-эндпоинт — legacy-путь без плана); контракт готов.

## 4. Remaining findings (вне MD-3.3 — решения владельца)

| ID | Finding | Класс |
|----|---------|-------|
| F-33-1 | Route C (video): план строится build_video_plan, но pipeline.generate_video не принимает plan/dispatch — план одноразовый, до видеопайплайна не доходит | переходный пробел video-ветки (кандидат MD-4) |
| F-33-2 | `dispatch.negative` — без consumers (image_kwargs/video_kwargs не содержат negative; MP-F2-семейство) | transitional (исчезнет в MD-5) |
| F-33-4 | `__all__` adc_deps содержит висячую строку `"get_prompt_composer"` (несуществующая функция; pre-existing) | документационный мусор (чистка — MD-5+; в MD-3.3 не тронуто: правка `__all__` не входит в утверждённые 2 метки) |
| MP-F1 | quality — dead (не оживляется; в BANNED; решение MD-4/5) | documented gap |
| MP-F2 | negative до провайдера не доходит | documented gap (MD-4/5) |
| MP-F8 | словари стилей ×3 разрознены (Route C vs pipeline STYLE_PRESETS) | вне MD-3.3 |
| MP-F10 | dead-поля шота E (camera/duration/negative) | showcase (решение владельца) |

## 5. Контракт MediaPlan v0 (краткая сводка после MD-3.3)

- **Pydantic** (`core/CORE/media_plan/schemas.py`): 22 поля, `extra="forbid"`, BANNED-инвариант (тест-барьеры MD-3.1 — без изменений в MD-3.3).
- **JSON Schema** (`SCHEMAS/MEDIA_PLAN.schema.json`, MD-3.3): draft-07, `additionalProperties: false` (≡ pydantic extra="forbid"), 4 required (plan_id/plan_version/media_kind/prompt), video-only описания duration_sec/fps, enum media_kind (image|video|audio-reserved), provenance {category, source, confidence}, lineage {parent_plan_id, derivation, created_from}.
- **Contract-тесты MD-3.3** (`runtime/tests/test_md3_route_deprecations.py`, 31): execution→Schema FAIL (13 полей + произвольное); валидный план→PASS (вкл. реальный genome-ctx); video-only (+типизация); provenance/lineage (вкл. regenerate с parent); deprecated-поведение D1/D5 неизменно; runtime-инвариант extra=forbid зелёный.
