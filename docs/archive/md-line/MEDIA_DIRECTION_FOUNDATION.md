# MEDIA DIRECTION FOUNDATION — Forensic Audit & Architecture

**Дата:** 2026-09-09
**Статус:** DOCUMENTED — архитектурный micro-stage (audit + architecture + ADR + roadmap proposal). Ничего не реализовано: ни endpoints, ни классы, ни persistence, ни F3.
**ADR:** `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` (граница двух проектов + инварианты).

---

## Простыми словами

1. **Задача** — не строить Media Engine, а честно посмотреть, что в Аркаиме уже есть для генерации визуала/видео, и провести границу: где кончается «понимание книги» и начинается «производство медиа» — чтобы потом не переписывать.

2. **Что нашёл** — Аркаим уже богат на «смысловую» половину: единый контекст сцены из 15 измерений, геном визуалов (105 описаний персонажей, сцены, локации, стили), временная модель с метками происхождения, континуити-движок для видеосогласованности, даже учебный film-studio со шотами. При этом всё это втрое продублировано (три слоя визуала, три генератора промптов), а знание о внутреннем устройстве ComfyUI (ноды, чекпоинты, samplers) вросло прямо в ядро — это главный долг.

3. **Что предлагаю** — границу зафиксировать документально: Аркаим производит Scene Context и Media Plan (задание: кто/где/когда/какой стиль/какая камера/какая атмосфера/откуда знаем), Media-проект исполняет (workflow/provider/backend/asset). Схема задания спроектирована и ждёт реализации в будущих этапах; roadmap-дельта прилагается (без правки мастера).

4. **Результат** — два документа, ноль изменений кода. Главные риски названы с точными путями файлов.

5. **Дальше** — ваше ACCEPTED на ADR; затем по основной дорожной карте — F3 (возвращаемся к Arkaim). Media-контракт — отдельный будущий этап, когда решите.

---

## NOW — что уже существует (forensic-факты)

Обследование: чтение кода всех media-смежных модулей + DI-smoke (все 11 сервисов зарегистрированы и живы) + genome-census + chronology (mtime). Читайте — это карта активов.

### Слой 1 — visualization/ (Sprint 0, июль 2026)
| Компонент | Файл | Состояние | Оценка |
|-----------|------|-----------|--------|
| SceneEngine | `core/CORE/visualization/scene_engine.py` (103 стр.) | **production-ready** (в DI, в роутах): сцены из genome + RAG-fallback, get_character_visual/get_location_visual | Переиспользуется |
| PromptBuilder | `core/CORE/visualization/prompt_builder.py` (394 стр., самый свежий 05.09) | **production-ready** как генератор; НО — SD-image-ориентированный (EMOTION_TO_VISUAL, QUALITY_SUFFIXES "8k", NEGATIVE_PROMPT): image-specific | Legacy-кандидат → проекция поверх Scene Context |
| VisualGenomeStore | `visualization/visual_genome.py` | SQLite persistence визуальных спецификаций (M6) | Переиспользуется |
| World/Character visualizer, archetypes, meaning_to_visual, conflict_palettes | visualization/* | Данные и маппинги смысла → визуала | Переиспользуются |

### Слой 2 — visual/ (23.07.2026, самый зрелый архитектурно)
| Компонент | Состояние | Оценка |
|-----------|-----------|--------|
| **VisualContext** (`visual_context.py`) — единый контекст 15-измерений (scene/location/architecture/landscape/environment/lighting/palette/atmosphere/symbols/historical/camera/style/emotion/characters/negative_prompt) | В DI (`visual_context_builder`), **media-neutral** — ни одного поля бэкенда | **Готовая основа Scene Context** — главный переиспользуемый актив |
| PromptComposer (`prompt_composer.py`) + prompt_templates (base/comfyui/flux/runway/kling/hailuo) | В DI; рендерит VisualContext в промпты под разные targets | ComfyUI-шаблон — violation MB-1' (template-уровень); flux/runway/kling — заделы video-провайдеров |
| **VideoContext** (`video_context.py`): CameraMovement/CharacterMotion/ObjectMotion/LightDynamics/TransitionSpec/RhythmSpec | В коде; **VideoIntelligence** создаёт VideoContext из VisualContext (движение камеры/персонажей/света по знаниям) | **Готовая video-половина MediaPlan-контракта** |
| ContinuityEngine (`continuity_engine.py`): continuity-состояние между шотами проекта | В DI | temporal_consistency для video-планов |
| AtmosphereEngine/CameraEngine/LocationEngine/SymbolEngine/VisualValidator | В слое | Данные для планов |
| **Legacy-парадокс:** роуты visual.py НЕ используют этот слой — сидят на слое 1 | adc_deps: оба зарегистрированы | Архитектурный gaps (см. GAP-1) |

### Слой 3 — visual_assets/ (23.07.2026, runtime-парадигма)
| Компонент | Состояние | Оценка |
|-----------|-----------|--------|
| **VisualAsset** (`schemas.py`, pydantic) — самый близкий к MediaPlan: intent/mood/style/palette/camera/characters/symbols/composition + video: duration_sec/fps/shots[]/transition + asset lifecycle (PENDING→GENERATING→COMPLETED/FAILED) | production-ready, используется /assets/* | Прототип MediaPlan (с violation MB-3: generation.model/steps/seed) |
| AssetGenerationPipeline (322 стр.): genome-scene → prompt → image **или** video → save; video-fallback = кадры через image-provider → ffmpeg | В DI + queue (max_concurrent=2) | Image/Video-branching уже существует (asset_type) |
| AssetStorage (214 стр.) + GenerationQueue (134 стр.) + async-генерация | В DI; 16 роутов /assets/* (editor-гейты) | Execution-механика — кандидат на переезд в Media-проект |
| prompt_builder.py (обёртка слоя 1) | используется pipeline | Дубль-генератор (MB-4) |

### Providers (image: 4 бэкенда; video: 2)
| Провайдер | Класс | Оценка |
|-----------|-------|--------|
| ComfyUIProvider | `providers/image/comfyui.py`: DEFAULT_WF node-graph (KSampler+CheckpointLoaderSimple+`cyberrealistic_v80.safetensors`), _inject_prompt (CLIPTextEncode), _inject_seed/size/quality, _resolve_ckpt (API-список моделей), health | **Готов к переносу в Media-проект как есть** (его логика = execution, не смысл). Сегодня — главный violation MB-1 |
| ImageProviderChain | `providers/image/__init__.py`: ABC (generate/health) + chain (auto/preferred; mock/svg=fallback, остальные=real) | Контракт provider-цепи — пригодится Media-проекту |
| MockImageProvider + SVGTemplateProvider | Offline-генерация | Останутся как Arkaim-фолбэк? нет — тоже execution; но дёшево |
| StableDiffusionProvider | `providers/image/stable_diffusion.py` | Ещё один execution-бэкенд (legacy, не в DI-chain?) |
| ImageSequenceVideoProvider | `providers/video/image_sequence.py`: кадры → **ffmpeg** CLI | Video-fallback-execution |
| MockVideoProvider | offline-видео | Тестовый |

### Сцены/контексты знаний
- **Genome**: modules = themes/values/characters/symbols/philosophy/conflicts/timeline/character_visuals(105)/location_visuals(5)/scenes(10)/style_presets.
- **M7.2 Temporal→Visual мост** (живой): `POST /visualize/epoch/{epoch_id}` — WorldModel.get_temporal_context(epoch) → PromptBuilder.build_epoch_prompt → image_provider.generate → base64. **Read-only от temporal** — идеальный шаблон Media-плана «эпоха+provenance → визуал».
- **film_studio** (core/CORE/film_studio + runtime/core/routes/film_studio.py): Project→Scene→Shot→ShotVersion (prompt/camera/duration/negative), assembly, 11 роутов /film/*, stats. Production-ready прототип сценария Video-плана.
- **ExperienceEngine** (`narrative_engine/experience_engine.py`): 10 режимов взаимодействия, ExperiencePath/Step — **M25-домен (Experience)**, к media имеет отношение через «режимы», но это домен чтения/исследования, не media (см. Roadmap).
- **Audio**: только вход-индексация (`book_os/multimodal.py` — извлечение текста из audio-файлов) + `VisualAsset.audio: dict` (пустая заглушка). **Audio-генерации не существует** — корректно для extension point.
- **Provenance-протокол**: `source_levels.py` (ProvenanceTag: category 8 значений + confidence; RU-лейблы) — готов для планов (каждый план знает происхождение сцены/эпохи).
- **Lineage**: **не существует** (0 упоминаний в core) — gap.

### Тесты (production-readiness)
`test_visualization, test_visual_comfyui, test_visual_assets_provider_chain, test_visual_conflict, test_visual_meaning, test_visual_archetype, test_m7_epoch_visual, test_assets_new_params, test_film_endpoints` + world_engine* — слои прикрыты; comfyui-тесты существуют (значит провайдер testable).

### Хронология (эволюция замысла)
июль Sprint 0 (visualization: genome→SD-prompt→ComfyUI) → 23.07 (visual_assets: assets+pipeline+queue+film_studio; visual: VisualContext-парадигма) → 05-07.08 (providers: ComfyUI chain) → 05.09 (M7.2: temporal→visual). Замысел уже дрейфовал к контекст-центричности, но роуты застряли на слое 1.

---

## GAP — что отсутствует

| # | Gap | Значение |
|---|-----|----------|
| GAP-1 | **Единый media-neutral Scene Context как обязательный вход всех генераций** | VisualContext существует, но роуты/pipeline обходят его; три генератора промптов с разными входами (dict-scene / VisualContext / VisualAsset) — контекст теряется |
| GAP-2 | **Media Plan contract** | Нет формального MediaRequest/MediaPlan (pydantic/JSON-Schema). VisualAsset — результат+запрос в одном; execution-поля примешаны (MB-3) |
| GAP-3 | **Lineage** | Нет: request→plan→execution→asset цепочки с provenance-наследованием (parent_request_id, derivation). ProvenanceTag есть, lineage-обвязки нет |
| GAP-4 | **Capability-словарь Media-проекта** | Нигде не формализовано, какие классы задач Media умеет (image.generate/video.generate/audio=future) — только фактические классы провайдеров |
| GAP-5 | **Отдельный Media-проект/repo** | ComfyUI-стек живёт в Arkaim-core (MB-1); Media-проекта как независимой единицы не существует |
| GAP-6 | **AudioPlan** | Сознательно: extension point (schema не определяется) |
| GAP-7 | **Temporal→Media формализация** | M7.2 делает эпоху→промпт→кадр, но БЕЗ плана: prompt идёт прямо в провайдер; temporal_context (epoch+provenance) не присутствует в asset-записи |

## TARGET — к чему идём

Целевая архитектура (детали в ADR):

```
ARKAIM                                    │  MEDIA / COMFYUI (отдельный проект)
Book · Knowledge/World Model              │  Capability (image.generate/video.generate/…)
  → Temporal Context (M8.1, provenance)   │  Workflow · Provider · Backend
  → Scene Context (единый: VisualContext+) │  Execution · Verification
  → Scenario (film_studio-наследник)       │  Asset (≠File, с lineage)
  → Media Planning                        │
       ├ Image Plan ──── MediaRequest ────┼→ Planning/Workflow → Execution → Asset
       ├ Video Plan                        │
       └ Audio Plan (extension point)     │
```

### MediaPlan — концептуальный контракт (не production-схема!)

**Общие поля:** `request_id` (idempotency) · `scene_context` (ref на Scene Context | embedded — self-contained) · `media_kind` (image|video|audio=future) · `intent` (key_frame|atmosphere|character_study|…) · `structured_prompt` (machine-readable факты) · `prompt` (натуральный текст-проекция) · `characters[]` (id+name+appearance+expression+pose из genome-visuals) · `location` (id+type+architecture+atmosphere) · `temporal_context` (epoch_id+provenance сцены — из M8.1/ADR_TEMPORAL) · `visual_style` (style-presets genome) · `atmosphere` (emotion→atmosphere mapping) · `camera/composition` (shot/angle/movement) · `constraints` (positive) · `negative_constraints` · `source/provenance` (ProvenanceTag — готовый протокол) · `lineage` (parent_request_id, derivation-chain).

**Video-only:** `duration` · `sequence[]` (ShotSpec: prompt/duration/camera/lighting/palette) · `actions` (CharacterMotion из VideoContext) · `camera_motion` (CameraMovement) · `transitions` (TransitionSpec) · `temporal_consistency` (continuity-требование: проект/шот-ссылка для ContinuityEngine).

**Audio:** `AudioPlan` — **extension point**: поле media_kind=audio зарезервировано, схема НЕ определяется (нет designs, нет полей — по прямому запрету).

**Чего в контракте НЕТ (по ADR Decision 3):** model/checkpoint/steps/cfg/seed/sampler/workflow/node-graph/provider — всё это Media-сторона.

Реализация контракта — будущий этап (см. Roadmap Delta), не сейчас.

## DEFERRED — сознательно не реализуем сейчас

1. Вынос ComfyUI-провайдера из core (MB-1) — до отдельного этапа миграции (после стабилизации контракта).
2. Де-публикация /comfyui/* endpoints (MB-2).
3. Чистка GenerationParams из доменных схем (MB-3).
4. Консолидация трёх prompt-генераторов (MB-4) — при реализации Scene Context-входа.
5. AudioPlan-схема — до появления аудио-домена.
6. Capability-словарь — до старта Media-проекта.
7. Lineage-механизм (GAP-3) — с контрактом вместе.
8. Интеграция visual_assets/film_studio под целевую архитектуру — при миграции.

## NON-GOALS — что НЕ входит в направление

Media API production endpoints · Image/Video/Audio API · новые Provider/Workflow · ComfyUI-integration · очереди/persistence · frontend · database tables · M25-implementation · M30-implementation · правка legacy /visual,/assets,/film · перенос prompt_builder'ов · любые изменения кода в этом micro-stage.

## DEPENDENCIES — от чего зависит реализация

| Зависимость | Статус | Что даёт |
|-------------|--------|----------|
| **ADR_TEMPORAL_WORLD_MODEL (ACCEPTED)** | ✅ закрыт | temporal_context в планах: эпоха+provenance готовы; инвариант «temporal read-only» |
| **C2 (deferred)** | ⏳ owner | Provenance-категории на рёбрах — слабая зависимость (планам нужны только узловые provenance) |
| **F3 «Время мира»** | ⏳ не начат | Frontend-потребитель temporal-контекста; НЕ зависит от Media (параллельные ветки) |
| **Scene Context-консолидация** | ⏳ будущий этап | Единый вход генераторов (GAP-1) — предусловие качественных планов |
| **Media-проект bootstrap** | ⏳ решение владельца | Отдельный repo + ComfyUI-стек-переезд (GAP-5) |
| **M25 Experience** | ⏳ | Experience-режимы — источник интентов для планов («интерактивная карта»→image-планы), но не блокер |

## INVARIANTS — что нельзя нарушать

(Полный список — ADR_ARKAIM_MEDIA_BOUNDARY Decision 5; здесь сводка.)

1. Core Arkaim — media-agnostic (никаких ComfyUI/workflow/node полей в доменных схемах и core-модулях новых).
2. Интеграция — только через внешний Media-контракт; никаких прямых Arkaim→ComfyUI HTTP/workflow.
3. LLM/агент не управляет media-execution.
4. PromptBuilder не выбирает capability.
5. Media execution backend — не доменная логика.
6. Scene Context — единственный источник для всех планов (image/video/audio/literary).
7. Temporal model — read-only для media; планы наследуют provenance сцены/эпохи (RECONSTRUCTION-эпоха → RECONSTRUCTION-план в lineage).
8. Media Plan ≠ Workflow ≠ Node Graph ≠ Capability ≠ Provider; Asset ≠ Media Request ≠ File.

---

## PROPOSED ROADMAP DELTA (предложение — MASTER ROADMAP не меняется без approval)

Контекст: в docs нет M-нумерации выше M12 (M25/M30 не существуют как документы — только в голове владельца; registry подтверждён). World-Engine-роадмап и PROJECT_STATUS не покрывают media-архитектуру. Предлагаемая логика этапов (нумерация условна — за владельцем):

| Этап | Название | Что входит | Предусловия |
|------|----------|------------|-------------|
| **MD-1 (media-direction, уже сделан)** | Media Direction Foundation | этот документ + ADR | — |
| **MD-2** | Scene Context Consolidation | Единый вход: VisualContext → все генераторы; Deprecate-пути старых входов (MB-4); временная мина: роуты переключаются на prompt_composer | MD-1 accepted |
| **MD-3** | MediaPlan Contract v0 | pydantic/JSON-Schema контракта (image+video; audio=extension); lineage-модель; provenance-наследование; версии | MD-2 |
| **MD-4** | Media Project Bootstrap | Отдельный repo; перенос ComfyUI/SD/video-провайдеров + execution/queue/storage; Media-словарь (capability/workflow/provider/backend) | MD-3 + owner-решение |
| **MD-5** | Arkaim↔Media Integration | Adapter на контракте; де-публикация /comfyui/*; переключение /assets,/film на контракт | MD-4 |
| Позже | Audio Domain | AudioPlan-схема + audio-capability | Media-проект готов |

**Что НЕ считаю нужным двигать:** F3 (фронт «Время мира») — параллелен и независим: его контракты (/book/temporal/*) уже media-agnostic (доказано аудитом TA). После MD-1 логичный порядок: **F3 → MD-2 → MD-3 → (MD-4/5 по решению владельца)**. M25-Experience — отдельная ветка (не media); M30 «Media Intelligence» — по смыслу покрывается MD-2..MD-5 (предложение: не вводить отдельный M30, а использовать MD-нумерацию).

**Риски (архитектурные):**
1. **R1 (High):** до выноса провайдера (MD-4) каждое новое media-требование соблазнит продлить ComfyUI-путь в core → долг растёт. Митигция: инвариант 1 + ревью.
2. **R2 (Medium):** MD-2 консолидация может сломать 9 тест-файлов визуала → миграция по роутам, поэтапно.
3. **R3 (Medium):** контракт v0 без реального Media-проекта рискует спроектироваться «в вакууме» → v0 держать минимальным (поля NOW-активов), расширять при MD-4.
4. **R4 (Low):** дублирование VisualAsset↔MediaPlan в переходный период → MD-5 убирает.

---

## Сводка forensic-выводов

1. **Переиспользовать:** VisualContext (основа Scene Context) · VideoContext/VideoIntelligence (video-поля плана) · ProvenanceTag (source/provenance) · genome-visuals (characters/locations/style) · SceneEngine · M7.2 temporal-мост (как паттерн) · film_studio (как прототип Scenario) · provider-ABC/chain (переедут в Media) · ContinuityEngine (temporal_consistency).
2. **Legacy/историческое:** visualization/prompt_builder (SD-промпты) · GenerationParams в VisualAsset · /comfyui/* endpoints · PromptComposer-комfyui-шаблон.
3. **Production-ready:** SceneEngine, VisualAsset-pipeline (image+video с branching), provider-цепи, film_studio, M7.2-мост, genome-стек, DI-регистрация всех 11 сервисов (smoke OK).
4. **Только концептуально:** AudioPlan (по запрету) · Capability-словарь · Media-проект как repo · lineage.
5. **Image-branching:** визуально весь стек image-oriented (EMOTION_TO_VISUAL, steps/seed, 1024x1024); явный image-ветвление в pipeline (asset_type=IMAGE; provider-chain image).
6. **Video-branching:** AssetType.VIDEO + shots/duration/fps/transition + VideoProviderChain + ImageSequenceVideoProvider (ffmpeg) + film_studio (проекты/шоты/сборка) + VisualContext video-слой.
7. **Media-neutral Scene Context:** VisualContext есть, но НЕ обязателен для входа генераторов (GAP-1) — главная дыра к закрытию.
8. **Media Plan contract:** отсутствует (GAP-2); ближайший — VisualAsset (с execution-примесями).
9. **M25/M30:** M25=Experience (experience_engine, 10 режимов — не media, отдельная ветка); M30 в docs не существует; MD-предложение покрывает его смысл.

**STOP.** Документы созданы; ничего не реализовано; roadmap не менялся; F3 не начат. Жду решения владельца по ADR + Roadmap Delta (MD-порядок), затем — возврат к основной дорожной карте (F3).
