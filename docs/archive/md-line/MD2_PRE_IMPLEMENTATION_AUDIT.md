# MD-2 PRE-IMPLEMENTATION AUDIT — Scene Context Consolidation (Forensic/Architecture, БЕЗ кода)

**Дата:** 2026-09-11
**Статус:** DOCUMENTED — аудит завершён; реализация НЕ начата (ждёт отдельного GO/NO-GO владельца на MD-2 implementation).
**Основа:** GO владельца на «MD-2 PRE-IMPLEMENTATION FORENSIC AUDIT — без кода» (после F3 CLOSED + Recovery ACCEPTED + MD-1 ACCEPTED). Roadmap: MD-1 ✅ → **MD-2 (аудит, этот документ)** → MD-3 → MD-4 → MD-5.
**Документы-предшественники:** `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` (ACCEPTED), `docs/MEDIA_DIRECTION_FOUNDATION.md` (MD-1, ACCEPTED), ADR_TEMPORAL_WORLD_MODEL (ACCEPTED), `docs/F3_POST_AUDIT_FOLLOWUP_REPORT.md` (F3 CLOSED).
**Код не менялся: ноль правок** (этап = чтение + документ).

---

## Простыми словами

1. **Что было целью?** — прежде чем объединять «контекст сцены» в единый объект для всех генераций картинок/видео, честно посмотреть, что уже есть в Аркаиме: какие слои, какие объекты-контексты, кто что дублирует и что с чем не связано.

2. **Что реально сделано?** — прочитан весь визуальный код Аркаима (три живых слоя + четвёртый маршрут «эпоха→картинка», все роуты, DI-регистрации, геном, тесты). Обнаружено: контекстов-кандидатов четыре (VisualContext — лучший, VisualAsset, dict-сцена genome, FormContext), генераторов промптов ЧЕТЫРЕ (аудит MD-1 говорил про три — нашёл ещё один в World Engine), временная модель в визуальный слой **не входит вообще** (единственный мост — маршрут эпохи, который идёт в обход сцены), и несколько мелких дефектов (включая один живой CJK-мусор в коде). Ничего не исправлял — всё каталогизировано.

3. **Что получилось?** — PASS: аудит завершён; целевая схема предложена; для каждого существующего компонента дан вердикт (переиспользовать / legacy / кандидат на миграцию / недопустимо в новом слое); границы «Scene Context ≠ Media Plan» зафиксированы; точный список «что не трогаем» составлен.

4. **Есть ли проблемы?** — серьёзных нет. Главная сложность уже была известна (дублирование), но она глубже, чем считал MD-1: повторяются не только генераторы, но и словари эмоций, стилей и камер. Плюс одна деталь, которую нельзя терять: сцены генома НЕ привязаны к эпохам — эту связь придётся строить в MD-2 аккуратно и без выдумывания данных.

5. **Что предлагается дальше?** — ваш GO/NO-GO на MD-2 implementation по плану из §9 (три подэтапа: расширение VisualContext → переключение генераторов на него → deprecate старых входов). Сам не начинаю.

---

## 1. Метод

Чтение кода всех визуально-смежных модулей Arkaim (без запуска, без правок): `core/CORE/visualization/` (10 файлов), `core/CORE/visual/` (15), `core/CORE/visual_assets/` (6), `core/CORE/film_studio/` (4), `core/CORE/providers/{image,video}/` (7), `core/CORE/narrative_engine/{temporal,world_model,form_engine,source_levels}` (выборочно), `runtime/core/routes/{visual,assets,film_studio,world_engine,temporal}.py`, `runtime/core/adc_deps.py` (DI), `core/GENOME/GENOME_v1.0.0.json`, `WORLD_MODEL.json`, `runtime/tests/` (инвентаризация визуальных тестов). Сверка с MD-1 (Foundation) и ADR_ARKAIM_MEDIA_BOUNDARY. Проверка актуальности `docs/TEMPORAL_CHAIN_ARCHITECTURE_AUDIT.md` (исторический снимок до ADR_TEMPORAL — см. §3.6).

## 2. INVENTORY — что существует (forensic-факты)

### 2.1 Четыре живых «контекстных» объекта (кандидаты на роль входа генерации)

| # | Объект | Где | Что содержит | Медиа-нейтрален? | Вердикт |
|---|--------|-----|--------------|------------------|---------|
| 1 | **VisualContext** (dataclass, 15 измерений) | `visual/visual_context.py` (47 стр.) | scene/location/architecture/landscape/environment/lighting/palette/atmosphere/symbols/historical/camera/style/emotion/characters/negative_prompt | **Да** — ни одного поля провайдера/бэкенда | **ОСНОВА будущего Scene Context** |
| 2 | **VisualAsset** (pydantic) | `visual_assets/schemas.py` (85 стр.) | смысловые поля (title/mood/style/palette/camera/characters/objects/symbols/shots) **+ execution-примеси** (GenerationParams: model=sdxl/steps/seed/quality; status/file_path/error/prompt_used) | Нет (MB-3: SD-параметры в доменной схеме) | Legacy → результат генерации; вход — миграция |
| 3 | **genome scene dict** | `GENOME_v1.0.0.json → modules.scenes` (10 сцен) | chapter/scene_id/title/characters/location/emotion/meaning_tags/color_palette/palette_a/palette_b/visual_style_hint/source | Да | Источник данных, НЕ вход (остаётся как есть) |
| 4 | **FormContext** (form_engine) | `narrative_engine/form_engine.py` | entity_name/forms/materials/palette/mood (55 форм World Engine) | Да | Отдельная ветка World Explorer; кандидат на включение полей, не на роль Scene Context |

**Ещё три частичных контекста** (не претенденты, но задействованы): ShotSpec (visual_assets, 1 кадр видео), ContinuityState (снимок для континуити), VisualGenomeEntry (CRUD-обёртка genome-визуалов, store in-memory).

### 2.2 ЧЕТЫРЕ живых генератора промптов (MD-1 считал три — фактическое число 4)

| # | Генератор | Вход | Куда идёт промпт | Оценка |
|---|-----------|------|------------------|--------|
| 1 | **PromptBuilder** (visualization/, 394 стр.) | genome scene dict + char_visuals + location | `/visualize`, `/visualize/epoch/{id}` (M7.2), `/assets/generate*` (через pipeline) | production; SD-oriented; «остающийся» на время миграции |
| 2 | **PromptComposer + templates** (visual/, 22+30 стр.) | **VisualContext** | `/assets/generate-context,-character,-location` | **Целевой путь** (единственный, кто ест VisualContext); comfyui-template — MB-1' violation |
| 3 | **build_asset_prompt** (visual_assets/, 185 стр.) | **VisualAsset** | `/assets/generate`, `/assets/generate-async`, film_studio `/shots/generate` (через pipeline) | Legacy-кандидат: вход = домен-схема с execution-примесями |
| 4 | **FormEngine.generate_visual_prompt** (narrative_engine/) | FormContext (сущность мира) | `/book/world/entity/{id}/visual-prompt` | Вне media-стека; вернуть строку без генерации; MD-2 НЕ трогает (см. §7.4) |

**Дублирование словарей (сверх генераторов):** EMOTION_TO_VISUAL + QUALITY_SUFFIXES + NEGATIVE_PROMPT определены **дважды** (visualization/prompt_builder.py **и** visual/visual_context_builder.py — копипаста); STYLE_PRESETS — трижды (visual_assets/prompt_builder.py:17-26, visual_context_builder STYLE_QUALITY_PRESETS, form_engine style_prefixes); словари камер — дважды (visual_context_builder CAMERA_SHOTS + VISUAL_KNOWLEDGE/CAMERA_LIBRARY.json). MOTION_DESCRIPTIONS (visual_assets) ≈ video_context camera_movement.

### 2.3 Три слоя визуала (подтверждено; + время рождения)

| Слой | Даты (git-история/факты) | Компоненты | Роуты-потребители |
|------|--------------------------|------------|-------------------|
| visualization/ (Sprint 0) | июль 2026 | SceneEngine, PromptBuilder, VisualGenomeStore, archetype/meaning/conflict/xray-маппинги | /visualize, /visualize/epoch, visual-genome CRUD, /assets/generate (как данные) |
| visual/ (23.07.2026) | наиболее зрелый архитектурно | VisualContext/Builder, PromptComposer+6 templates (comfyui/flux/runway/kling/hailuo), VideoContext/VideoIntelligence, ContinuityEngine, атмосфера/камера/символы-движки | /assets/generate-context,-character,-location |
| visual_assets/ (23.07.2026) | M6/M7 | AssetGenerationPipeline, prompt_builder, queue, storage, schemas (VisualAsset) | /assets/*, film_studio /shots/generate |
| (+) film_studio | M-series | FilmProjectStore (SQLite: проекты/сцены/шоты/версии), ShotAssembler (ffmpeg-сборка ken-burns/concat) | /film/* (17 эндпоинтов) |
| (+) providers | M6/M7 | image: comfyui (153 стр., node-graph), stable_diffusion, svg_template, mock; video: image_sequence (ffmpeg), mock | через image_provider/video_provider DI |

### 2.4 DI-регистрации (adc_deps.py:203-230) — все живы одновременно

`scene_engine`, `prompt_builder` (слой 1), `image_provider`, `video_provider`, `asset_store`, `generation_pipeline`, `film_store`, `generation_queue` (visual_assets+film), `visual_context_builder`, `prompt_composer` (слой 2), `continuity_engine`, `video_intelligence` (слой 2 video). **Оба параллельных мира зарегистрированы и загружаются при старте** — подтверждение «трёх живых слоёв» из MD-1.

### 2.5 Ключевые живые маршруты до изображения (пять фактических путей)

```
A) /visualize                  genome-scene → SceneEngine.get_scene → PromptBuilder.build_scene_prompt → image_provider
B) /visualize/epoch/{id}       WorldModel.get_temporal_context → PromptBuilder.build_epoch_prompt → image_provider   ← ЕДИНСТВЕННЫЙ temporal-мост
C) /assets/generate(+batch)    genome-scene → pipeline → VisualAsset → build_asset_prompt → image/video provider
D) /assets/generate-context    genome-scene → VisualContextBuilder.build → VisualContext → PromptComposer → pipeline.generate_image_from_context
E) film /shots/generate        film-store shot → pipeline (custom_prompt) → build_asset_prompt-ветка / custom
```
(Плюс `/visual-genome/*` CRUD — пишет в genome; `/book/world/entity/{id}/visual-prompt` — строка без генерации.)

### 2.6 Данные

- **Genome**: modules.scenes = **10 сцен** (ключи: chapter/scene_id/title/characters/location/emotion/meaning_tags/color_palette/palette_a/palette_b/visual_style_hint/source; **нет epoch_id**), character_visuals = **105**, location_visuals = **5**; world_entities (сущности с values/related_to/conflict_with).
- **WORLD_MODEL.json** (mtime 16.07, не менялся): epochs=12, locations=12, civilizations=4, technologies=3, religions=2, canonical_events=17 (16 с chapter), characters_living, causal_rules=4.
- **VISUAL_KNOWLEDGE/** (слой 2): 7 JSON-библиотек (ATMOSPHERES/CAMERA_LIBRARY/CHARACTER_VISUALS/LOCATION_VISUALS/SHOT_LIBRARY/STYLE_LIBRARY/VIDEO_RULES/VISUAL_SYMBOLS).
- **data/visual_assets/**: images/videos/thumbnails — файловые ассеты.

### 2.7 Визуальные тесты (runtime/tests)

10 файлов с прямым визуальным содержанием: test_visualization (62), test_visual_archetype (48), test_visual_assets_provider_chain (27), test_visual_comfyui (19), test_visual_conflict (40), test_visual_meaning (27), test_m7_epoch_visual (53), test_assets_new_params (25), test_film_endpoints (112), world_engine-интеграция. → Риск R2 MD-1 подтверждён: миграция маршрутов затронет это семейство; см. §8.

## 3. КЛЮЧЕВЫЕ ФАКТЫ для дизайна MD-2

### 3.1 VisualContext НЕ обязателен ни для одного входа (GAP-1 подтверждён дословно)
Только путь D (generate-context) ест VisualContext. Пути A, B, C, E обходят его. `build_image` в VisualContextBuilder **возвращает VisualAsset-слепок**: `generate_image_from_context` (pipeline.py:284-366) тут же пересобирает смысловые данные обратно в VisualAsset — двойное представление (VisualContext → промпт → VisualAsset-запись). Это главный «двойник», который MD-2 должен устранить на входе, а MD-3 — на контракте.

### 3.2 Temporal НЕ входит в Scene Context вообще
- VisualContext **не имеет поля эпохи**; `HistoricalContext` (era/civilization/year_approx) — свободная строка про «Bronze Age» из world_entities, без provenance, без связи с TemporalNode.
- Слой 2 (visual/) не импортирует WorldModel (проверено grep — ноль упоминаний).
- Единственный temporal→visual мост — путь B (M7.2): `get_temporal_context(epoch_id)` → `build_epoch_prompt` (prompt_builder.py:298-346). Мост идёт **мимо сцены** (у genome-сцен нет epoch_id) и **без плана** (GAP-7): промпт сразу в провайдер, temporal_context не попадает в VisualAsset-запись.
- Мост B — фактически пятый «генератор»-маршрут с собственным входом (dict от WorldModel).

### 3.3 Сцены генома не привязаны к эпохам
10 сцен не содержат epoch_id; события WORLD_MODEL (canonical_events, 16/17 с chapter) дают единственную фактическую привязку «глава→эпоха». Данные для полного scene→epoch маппинга **нет** — MD-2 должен строить temporal-вход опционально (epoch_id по главе через events), а не выдумывать его.

### 3.4 Деградация на пути D: VisualContext → VisualAsset
`generate_image_from_context` копирует смысловые поля в VisualAsset (title/mood/style/palette/camera/characters) и добавляет execution-поля. Двухступенчатая проекция «15 измерений → плоский ассет → промпт» теряет symbols/architecture/landscape/lighting/atmosphere/environment/historical (они не переносятся в VisualAsset). Путь D саботирует собственную идею VisualContext.

### 3.5 Четвёртый генератор (FormEngine) — вне media-стека
`/book/world/entity/{id}/visual-prompt` — про World Explorer (сущности мира: философии/языки/география), возвращает строку-промпт без генерации. Не media-путь, но тоже источник «промпт-заготовок». В целевой схеме — потребитель Scene Context только при явном решении владельца (§7.4).

### 3.6 TEMPORAL_CHAIN_ARCHITECTURE_AUDIT.md (355 стр.) — исторический, НЕ переоткрывать
Снимок ДО ADR_TEMPORAL_WORLD_MODEL/B1/C1. Его открытые вопросы уже решены: TODAY = методологический якорь (не в графе — by design), связь Present→Arkaim отсутствует by design, двойной anchor разрешён C1-enrichment (temporal_arkaim_era получает AUTHOR_CANON+EXTERNAL_SOURCE на выходе API). Для MD-2 из него берём только: provenance-наследование уже спроектировано (ADR §5), temporal-слой read-only для media.

## 4. ЦЕЛЕВАЯ СХЕМА MD-2 (предложение, без реализации)

### 4.1 Единый Scene Context = VisualContext v2 (расширение, не новый объект)

```
Book/Genome (сцены, персонажи, локации, стили)
WorldModel (эпохи, события, цивилизации, технологии)   ← read-only
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│ SceneContextBuilder (эволюция VisualContextBuilder)       │
│  build(scene_ref, temporal_ref?) → SceneContext           │
│    scene_ref:  chapter+scene_id | character_id | location_id | epoch_id
│    temporal_ref: epoch_id (опц.) ← WorldModel.get_temporal_context
└──────────────────────────────────────────────────────────┘
        │
        ▼
SceneContext (VisualContext v2) — ЕДИНСТВЕННЫЙ вход всех генераций
  ├─ все 15 измерений VisualContext (как есть)
  ├─ NEW: temporal: TemporalSceneRef { epoch_id, provenance[], confidence, bounds } (read-only, из TemporalNode/Epoch)
  ├─ NEW: source_refs { genome scene_id/character_id/location_id, chapter }
  └─ NEW: integrity { not_synthesized: true } — флаг «связи не пересчитываются» (инвариант F3)
        │
        ├──► literary rendering (текст)   — потребитель только-чтением
        ├──► Image Plan (MD-3)            — проекция SceneContext
        ├──► Video Plan (MD-3)            — VideoContext.from_visual_context + motion (готово)
        └──► Audio Plan (later)           — extension point (поля НЕ определяем)
```

**Почему VisualContext, а не новый класс:** он media-neutral (проверено: ноль execution-полей), в DI, питается genome+знанием, уже 15 измерений, и PromptComposer рендерит его. Новый объект умножил бы четвёртый слой. Критично: v2 = **расширение** существующего (стратегия «additive, non-breaking»).

### 4.2 Граница Scene Context ≠ Media Plan (по ADR Decision 1-3)

| Scene Context (Arkaim, смысл) | Media Plan (MD-3, задание) |
|-------------------------------|----------------------------|
| ВСЁ о сцене: кто/где/когда/эмоция/символы/камера/стиль/**эпоха+provenance** | ПРОЕКЦИЯ сцены на один носитель: intent, structured_prompt, constraints, target-специфика |
| Не знает, как генерировать | Не знает, почему сцена такова |
| Один на сцену | N на сцену (image/video/audio/варианты) |
| Мутируется только автором/каноном | Создаётся из SceneContext + наследует provenance |
| **НЕТ:** model/steps/seed/workflow/provider | **НЕТ:** смыслов книги (только ссылки/проекции) |

Lineage-направление: SceneContext →(MD-3)→ MediaPlan →(MD-4/5)→ Execution/Asset; provenance сцены/эпохи наследуется планом (ADR-инвариант 7).

### 4.3 Как входит Temporal Context (существующий API, без изменений)

- `SceneContextBuilder.build(scene_ref, temporal_ref?)`: temporal_ref опционален (см. факт 3.3 — у 10 сцен нет эпохи; глава→epoch берётся из canonical_events, где есть chapter, иначе None и поле temporal отсутствует → UX/план получают «вне оси времён»);
- данные только read-only из готового `WorldModel.get_temporal_context(epoch_id)` (возвращает TemporalNode+Epoch+events+characters+technologies — готово);
- provenance — из TemporalNode.provenance (AUTHOR_CANON/EXTERNAL_SOURCE/HYPOTHESIS/RECONSTRUCTION — протокол существует и протестирован F3);
- **НЕ** добавляется temporal_today и relations в SceneContext (инварианты ADR_TEMPORAL: today — точка наблюдателя, не сцена; связи не синтезируются);
- M7.2-мост (путь B) мигрирует последним: epoch_id как scene_ref — легитимный вход билдера (эпоха-«сцена»), промпт через composer.

### 4.4 Входы трёх видов (единые для всех генераторов)

| Вид входа | Что подаётся | Сегодня (разброс) | В MD-2 |
|-----------|--------------|-------------------|--------|
| Сцена | chapter+scene_id | A: dict, D: VisualContext, C: VisualAsset | SceneContext (build) |
| Персонаж | character_id | D: build_for_character | SceneContext (build_for_character) |
| Локация | location_id | D: build_for_location | SceneContext (build_for_location) |
| Эпоха | epoch_id | B: dict WorldModel | SceneContext (build_for_epoch — NEW) |

## 5. КЛАССИФИКАЦИЯ существующих компонентов (главный запрос владельца)

### 5.1 REUSABLE — переиспользовать как есть

| Компонент | Почему |
|-----------|--------|
| `visual/visual_context.py` VisualContext | основа SceneContext v2 (media-neutral, 15 измерений) |
| `visual/visual_models.py` (14 контекстов) | модели измерений; добавить temporal-ref не сломает |
| `visual/visual_context_builder.py` (ядро build/_build_*) | эволюционирует в SceneContextBuilder; знания VISUAL_KNOWLEDGE остаются |
| `visual/prompt_composer.py` + templates base/flux/runway/kling/hailuo | целевой рендер SceneContext→промпт; comfyui-template помечен (MD-4/5) |
| `visual/video_context.py` + `video_intelligence.py` | video-поля будущего Video Plan (motion/transitions/rhythm) |
| `visual/continuity_engine.py` + `continuity_state.py` | temporal_consistency плана (ADR: для Video Plan) |
| `visual/visual_validator.py` | проверка контекста до плана |
| `visualization/scene_engine.py` SceneEngine | извлечение genome-данных (тонкая обёртка); билдер уже использует genome напрямую — оставить как утилиту чтения |
| `visualization/visual_genome.py` store + `schema.py` (CharacterVisual/LocationVisual) | persistence визуальных спецификаций |
| `visualization/{archetype_visuals, meaning_to_visual, conflict_palettes, character_visualizer, world_visualizer}` | данные смысл→визуал |
| `narrative_engine/source_levels.py` ProvenanceTag/SOURCE_CATEGORY_LABELS | готовый provenance-протокол (F3 1:1) |
| `narrative_engine/world_model.py` get_temporal_context | единственный правильный вход temporal в сцену |
| `film_studio/store.py` FilmProjectStore | прототип Scenario-слоя (проекты/сцены/шоты/версии) — по ADR «film_studio-наследник» |
| genome-стек (scenes/character_visuals=105/location_visuals=5) + VISUAL_KNOWLEDGE 7 JSON | данные |
| DI-паттерн registry (adc_deps) | без изменений, добавить scene_context_builder поверх |

### 5.2 LEGACY — оставить работающим, новых входов не давать

| Компонент | Судьба |
|-----------|--------|
| `visualization/prompt_builder.py` (слой 1, 394 стр.) | работает для A/B/C до конца миграции; затем MB-4-консолидация (его маппинги EMOTION_TO_VISUAL/LOCATION_TYPE_VISUALS — кандидаты на переезд в единый словарь знаний) |
| `visual_assets/prompt_builder.py` (build_asset_prompt) | legacy: вход VisualAsset; после MD-2 новых вызовов не добавлять |
| `visual_assets/schemas.py` VisualAsset+GenerationParams | legacy-результат; execution-поля — до MB-3/MD-3 (MediaPlan заменит запись-запрос) |
| `visual_assets/pipeline.py` generate_image/generate_video (пути C) | legacy-пути; `generate_image_from_context` (путь D) — эволюционирует в единый |
| `/visualize`, `/assets/generate*` (без -context), film `/shots/generate` | работают как есть; переключение — поэтапно с тестами (R2) |
| `/visual-genome/*` CRUD | не трогать (это genome-редактирование, не генерация) |
| `/comfyui/*` endpoints (visual.py:258-287) | MB-2: де-публикация в MD-5 (не MD-2!) |

### 5.3 MIGRATION CANDIDATE — кандидат на миграцию в MD-2

| Что | Куда мигрирует |
|-----|----------------|
| Путь B: `/visualize/epoch/{id}` + `build_epoch_prompt` | на `SceneContextBuilder.build_for_epoch` + composer (temporal-мост становится сценой-эпохой) |
| Путь A: `/visualize` | на build(chapter, scene_id) + composer (клиентский контракт — тело ответа сохраняется) |
| Путь C: `/assets/generate` (+batch, +regenerate) | на SceneContext-вход (внутри — legacy-pipeline до MD-3) |
| Путь D: `/assets/generate-context,-character,-location` | уже SceneContext-совместим; в MD-2 — единственный канонический вход (rename-семантика, не код) |
| Путь E: film `/shots/generate` | shot.custom_prompt → SceneContext источника (film-сцена ссылается на genome-сцену; деталь — на этапе реализации) |
| Дубли словарей (§2.2) | консолидация в ОДИН источник (VISUAL_KNOWLEDGE + один re-export-модуль); EMOTION_TO_VISUAL и пр. — без изменения значений |

### 5.4 FORBIDDEN для нового слоя — недопустимы в Scene Context/MD-2

| Что | Почему |
|-----|-------|
| Поля model/checkpoint/steps/cfg/seed/sampler/workflow/node/provider | ADR Decision 3: execution — Media-сторона |
| Прямые вызовы ComfyUI/HTTP-провайдерам из SceneContext/билдера | ADR-инвариант 2 |
| Синтез temporal-relations, добавление temporal_today в сцену | ADR_TEMPORAL-инварианты (F3: связи не пересчитываются, today — точка наблюдателя) |
| Новый parallel «SceneContext»-класс ВНЕ visual/ (третья ветка) | воспроизвёл бы историю трёх слоёв |
| LLM в билдере | Архитектурный принцип: книга — источник истины; билдер детерминирован |
| AudioPlan-поля | по прямому запрету (extension point, MD-3+) |
| Mutation WorldModel/WORLD_MODEL.json из media-путей | temporal read-only (ADR-инвариант 7) |
| Новые M-номера (M30 и т.п.) | MD-нумерация уже принята |

### 5.5 НЕ ТРОГАЕМ в MD-2 (чтобы не повторить историю параллельных слоёв)

1. **arkaim-web-v2/** — весь (F3-заморожен; temporal-контракты media-agnostic, фронт не потребитель media).
2. **runtime/core/routes/temporal*, research/, provenance/** — B1/C1/M10.x закрыты; media их только читает.
3. **providers/** — переезд в Media-проект = MD-4; в MD-2 ни строки (инвариант «не углублять» = не трогать вовсе).
4. **/comfyui/*** де-публикация — MD-5 (раньше сломает test_visual_comfyui и legacy-UI).
5. **VisualAsset-схему/GenerationParams** — только потребление; чистка = MB-3 вместе с MD-3-контрактом.
6. **film_studio/store+schemas** — работает; интеграция = отдельный подэтап после MD-3 (Scenario-слой).
7. **Genome-данные + WORLD_MODEL.json** — чтение только (у scenes нет epoch_id — не «дочинивать» данные в MD-2; глава→эпоха через events, остальное optional).
8. **TEMPORAL_CHAIN_ARCHITECTURE_AUDIT.md-вопросы** — закрыты ADR; не переоткрывать.
9. **F3-продукция (12 эпох/13 узлов/anchor)** — не пересматривать.
10. **frontend legacy arkaim-web/** — его страницы (/visual, /film-studio, /editor) работают на legacy-роутах; трогать = MD-5.

## 6. FINDINGS (новые, сверх MD-1)

| # | Severity | Факт | Путь | Что делать |
|---|----------|------|------|-----------|
| F-1 | Medium | **ЧЕТЫРЕ генератора промптов** (MD-1 зафиксировал 3; FormEngine — четвёртый) | narrative_engine/form_engine.py:181-220 | вне MD-2-scope; учитывать в карте консолидации (MD-3+) |
| F-2 | Medium | Словарь-дубли: EMOTION_TO_VISUAL/QUALITY/NEGATIVE ×2, STYLE ×3, CAMERA ×2 | prompt_builder.py ↔ visual_context_builder.py ↔ form_engine | консолидация в MD-2 (один источник значений; значений НЕ менять) |
| F-3 | Medium | **GAP-1 глубже**: путь D деградирует VisualContext→VisualAsset, теряя 7 измерений (symbols/architecture/landscape/lighting/atmosphere/environment/historical не переносятся) | visual_assets/pipeline.py:284-366 | главный мотиватор MD-2; устраняется каноническим входом |
| F-4 | Low | **Живой CJK-мусор в коде**: ключ словаря `"ancient壁画"` (китайские иероглифы) в STYLE_PRESETS | visual_assets/prompt_builder.py:23 | почистить при консолидации словарей (MD-2, одна строка; тестов на ключ нет) |
| F-5 | Low | HistoricalContext в VisualContext — свободные строки («Bronze Age»/«Hyperborean»), без provenance, дублируют смысл TemporalNode | visual/visual_models.py:92-96 + builder | заменить на temporal-ref в v2 (старое поле — deprecated, не удалять) |
| F-6 | Low | `_build_camera` (слой 2) содержит **кириллические литералы** («панорам») в коде-условиях | visual_context_builder.py:540+ | не менять сейчас (работает); при консолидации — учесть |
| F-7 | Info | SceneEngine._parse_scene_from_rag создаёт сцену с `chapter=0, scene_id=rag_*` — «призрачные» входы | visualization/scene_engine.py:81-92 | в MD-2: SceneContext из RAG-fallback помечается source_ref.rag=true (честный provenance) |
| F-8 | Info | film_studio `/shots/generate` — 7 query-параметров (style/mood/quality...) исполняются минуя смысловой контекст | routes/film_studio.py | кандидат на SceneContext-вход; детали — этап реализации |
| F-9 | Info | genome-сцены имеют color_palette/palette_a/palette_b/visual_style_hint, но VisualContextBuilder их не читает (palette из location) | builder + GENOME | в MD-2: использовать данные сцены (они уже в genome) — уточнить на реализации |
| F-10 | Info | EMOTION_RU_TO_EN-маппинг существует в двух слоях (совместимость русских эмоций genome) | оба prompt_builder'а | сохранить при консолидации (данные genome на русском) |

## 7. Целевые инварианты MD-2 (для реализации)

1. **Один вход**: все генерации изображений/видео внутри Arkaim принимают SceneContext (v2) — новых входов dict/VisualAsset/WorldModel-dict не появляется.
2. **Additive, non-breaking**: VisualContext расширяется (temporal/source_refs/integrity), существующие поля не переименовываются/не удаляются; legacy-пути продолжают работать до конца миграции.
3. **Temporal read-only**: SceneContext только читает WorldModel; никакие media-пути не пишут в WORLD_MODEL.json/relations/today.
4. **Provenance-наследование**: temporal.provenance сцены = provenance эпохи TemporalNode (дедуп по категории — паттерн C1); FUTURE_EXTRAPOLATION — только у сценариев будущего (M8), не у сцен.
5. **Словарь один**: EMOTION/STYLE/CAMERA/LOCATION-маппинги — один источник (VISUAL_KNOWLEDGE + re-export); значения не меняются (сравнение до/после в тестах).
6. **Граница**: SceneContext не содержит execution-полей; MediaPlan не содержит book-смыслов (MD-3 проверит).
7. **Роуты-контракты стабильны**: тела запросов/ответов A-E не меняются (переключается внутренность).
8. **Тесты**: каждый мигрированный маршрут сохраняет зелёные тесты; новые тесты инвариантов 1-6.

## 8. Риски MD-2

| Риск | Оценка | Митигция |
|------|--------|----------|
| R2' (из MD-1 R2): 10 визуальных тест-файлов | Medium | поэтапная миграция (один путь за шагом), test-fixture для SceneContext, тесты сравнения промптов до/после |
| Словарь-дрейф при консолидации | Medium | тест-равенство словарей до/после (значения заморожены) |
| Ретро-совместимость legacy-роутов | Medium | инвариант 7; параллельный прогон обоих путей на этапе миграции |
| Сцены без эпох (3.3) | Low | temporal optional; UX не требует эпоху для генерации сцены |
| Расширение scope до MD-3/MD-4 | Low | жёсткий boundary: MediaPlan/контракт/провайдеры — вне MD-2 |

## 9. План реализации MD-2 (предложение, к GO/NO-GO)

**Подэтап 1 — SceneContext v2 (backend, additive):**
расширить VisualContext (temporal: TemporalSceneRef, source_refs, integrity) + SceneContextBuilder (build/build_for_character/build_for_location/**build_for_epoch** NEW: эпоха-как-сцена через get_temporal_context) + консолидация словарей (один источник, значения неизменны; чистка F-4 CJK-ключа) + unit-тесты инвариантов.

**Подэтап 2 — переключение генераторов (по одному маршруту, с тестами):**
порядок: D (уже готов — фиксация как канонический) → A `/visualize` → B `/visualize/epoch` (build_for_epoch) → C `/assets/generate` (внутри legacy-pipeline) → E film `/shots/generate` (custom_prompt-проекция). Каждый шаг: тесты маршрута зелёные + сравнение промптов.

**Подэтап 3 — deprecate старых входов (MB-4-старт):**
deprecation-метки (без удаления!) на dict/VisualAsset-входах генераторов; документация; VisualAsset остаётся результатом (до MD-3). Возврат к владельцу с отчётом.

**Оценка объёма:** ~3 файла правятся глубоко (visual_context.py, visual_context_builder.py, pipeline.py), ~6 роутов переключаются, ~10 тест-файлов сопровождаются, 2-3 новых тест-файла. Без нового ADR (работает внутри ADR_ARKAIM_MEDIA_BOUNDARY Decision 1-3; если владелец хочет — ADR на SceneContext-v2).

## 10. Что НЕ входит в MD-2 (границы этапа)

MediaPlan/JSON-Schema контракта (MD-3) · вынос ComfyUI/providers (MD-4) · де-публикация /comfyui/* (MD-5) · HTTP Arkaim↔Media (MD-5) · AudioPlan (later) · любые изменения arkaim-web-v2/F3 · temporal-data/WORLD_MODEL · C2 (precedes→provenance; отдельный маленький этап по решению владельца) · frontend legacy · новый ADR (по умолчанию) · изменения semantics provenance/auth.

## 11. Git-статус этого этапа

Аудит = только чтение. Единственный новый файл: `docs/MD2_PRE_IMPLEMENTATION_AUDIT.md` (этот документ). Код/тесты/данные/фронтенды — 0 правок (сессия аудита). CJK-скан: см. отчёт.

---

**STOP.** Реализация MD-2 НЕ начата. Жду вашего **GO/NO-GO на MD-2 implementation** (план §9). C2 — по вашему отдельному решению (не блокирует MD-2 и Media Direction).
