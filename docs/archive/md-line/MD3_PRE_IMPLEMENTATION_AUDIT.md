# MD-3 PRE-IMPLEMENTATION AUDIT — MediaPlan Contract v0 (Forensic/Architecture, БЕЗ кода)

**Дата:** 2026-09-11
**Статус:** DOCUMENTED — аудит завершён; реализация НЕ начата (ждёт отдельного GO/NO-GO владельца на MD-3 implementation).
**Основа:** команда владельца «MD-3 PRE-IMPLEMENTATION FORENSIC AUDIT — только аудит и архитектурное проектирование, без реализации» (после MD-2 CLOSED / FINAL GREEN). Roadmap: MD-1 ✅ → MD-2 ✅ → **MD-3 (аудит, этот документ)** → MD-4 → MD-5.
**Документы-предшественники:** `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` (ACCEPTED), `docs/MEDIA_DIRECTION_FOUNDATION.md` (MD-1), `docs/MD2_PRE_IMPLEMENTATION_AUDIT.md`, `docs/MD2_IMPLEMENTATION_REPORT.md`, `docs/MD2_POST_IMPLEMENTATION_FORENSIC_AUDIT.md` (MD-2 CLOSED; PA-F1 deferred to MD-3 design — учтён в §7).
**Код не менялся: ноль правок** (этап = чтение + документ).

---

## Простыми словами

1. **Что было целью?** — прежде чем создавать «Media Plan» — единый формат задания для генерации картинок/видео (что рисовать, в каком стиле, с какими ограничениями, с каким происхождением), честно посмотреть, как картинки и видео реально генерируются сегодня: какие параметры, откуда берутся, где теряются, что дублируется.

2. **Что реально сделано?** — прочитан весь путь каждого execution-параметра во всех 5 маршрутах MD-2 (от кнопки/параметра запроса до провайдера), все доменные схемы, провайдеры, DI, фронтенд. Обнаружено: **(а)** «quality» — мёртвый параметр: фронт и роуты его передают, в asset-запись он попадает, но до исполнителя (ComfyUI) не доходит — по цепочке провайдеров он теряется; **(б)** negative-prompt тоже обрывается на цепочке провайдеров (доходит только до ComfyUI «через tuples»); **(в)** поля планшетного видеоплана (VideoContext, ContinuityEngine, VideoIntelligence) — витринные: код есть, DI есть, а реальный видеопуть их не потребляет (видео = один промпт или кадры+ffmpeg); **(г)** 8 из 9 полей GenerationParams (model/steps/seed/quality…) не используются кодом вовсе — «мертвый груз» в доменной схеме; **(д)** model/seed/steps «используются» только внутри ComfyUI-провайдера как его внутренние предустановки — Аркаим их не выбирает.

3. **Что получилось?** — PASS: аудит завершён; спроектирован контракт MediaPlan v0 (двухуровневый: MediaPlan — задание; ExecutionDispatch — «конверт» передачи исполнителю; без model/steps/cfg/seed/provider) и модель lineage (родословная планов: план знает родителя, происхождение, версию); для каждого найденного компонента — вердикт; границы «что не трогаем» зафиксированы; план реализации в 3 подэтапа предложен.

4. **Есть ли проблемы?** — серьёзных нет. Контракт фактически **проецируется на уже живые потоки** (не выдуман «в вакууме» — риск R3 MD-1 снят: все поля плана происходят из фактических NOW-активов). Главная сложность — два «мёртвых» параметра (quality/negative) и витринная video-половина: контракт v0 фиксирует их как honest-поля (что реально работает), не фиксируя мёртвое.

5. **Что предлагается дальше?** — ваш GO/NO-GO на MD-3 implementation по плану из §9. Сам не начинаю.

---

## 1. Метод

Чтение кода без правок: `core/CORE/visual_assets/` (schemas, pipeline 438 стр., storage, prompt_builder), `core/CORE/visual/` (visual_context, scene_context, video_context, video_intelligence, continuity_engine, prompt_composer+templates, visual_context_builder MD-2-блок), `core/CORE/film_studio/` (schemas, store, shot_assembler), `core/CORE/providers/{image,video}/` (7 провайдеров, цепи), `core/CORE/narrative_engine/source_levels.py`, `core/CORE/narrative_engine/world_model.py` (get_temporal_context), `runtime/core/routes/{visual,assets,film_studio}.py`, `runtime/core/adc_deps.py`, `arkaim-web/src/shared/lib/useGenerateImage.ts` + `GenerationSettingsContext.tsx` + `GenerationSettingsPanel.tsx`, `core/GENOME/GENOME_v1.0.0.json` (style_presets), `SCHEMAS/` (прецедент JSON-Schema). Сверка с ADR Decision 1-5, MEDIA_DIRECTION_FOUNDATION §Target/GAP, MD-2-документами. Подтверждение GAP-2 (0 кода MediaPlan/MediaRequest в core/runtime).

## 2. INVENTORY — что существует (forensic-факты)

### 2.1 MediaPlan-кандидатская база (все типы, готовые к переиспользованию)

| Тип | Где | Поля | Вердикт для MD-3 |
|-----|-----|------|------------------|
| **VisualAsset** (pydantic) | `visual_assets/schemas.py:54-93` | intent/mood/style/palette/camera/characters/objects/symbols/composition + video: duration_sec/fps/shots/transition/audio + output: status/file_path/prompt_used | Прототип плана, НО: request+result в одном + execution-примеси (generation: GenerationParams) — разделяется в MD-3 |
| **GenerationParams** | `visual_assets/schemas.py:44-51` | provider/model/size/seed/steps/quality/negative_prompt | execution-конверт; 8/9 полей мертвы для Аркаима (см. MP-F3) |
| **CameraSpec** | `visual_assets/schemas.py:20-23` | shot_type/angle/movement | → camera/composition плана |
| **CharacterInAsset** | `schemas.py:26-32` | character_id/name/role/appearance/expression/pose | → characters[] плана |
| **ShotSpec** | `schemas.py:35-41` | id/prompt/duration_sec/camera/lighting/palette | → video.sequence[] плана |
| **TemporalSceneRef** (MD-2, dataclass) | `visual/scene_context.py:43-77` | epoch_id/name_ru/confidence/bounds/provenance/event_count | → temporal_context плана 1:1 |
| **ProvenanceRef** (MD-2) | `visual/scene_context.py:17-41` | category/source/confidence + from_tag | → provenance-наследование плана |
| **ProvenanceTag** | `narrative_engine/source_levels.py` | category(8)+confidence; RU-лейблы | канонический протокол (не дублировать) |
| **VideoContext-типы** | `visual/video_context.py:9-59` | CameraMovement/CharacterMotion/ObjectMotion/LightDynamics/TransitionSpec/RhythmSpec | video-поля плана (сейчас витринные — MP-F5) |
| **ContinuityState/Engine** | `visual/continuity_engine.py` | apply(ctx, project_id, shot_index) | temporal_consistency-механика (сейчас витринная) |
| **STYLE_PRESETS** (visual_assets) | `visual_assets/prompt_builder.py:17-26` | cinematic_fantasy/realistic/watercolor/dark_gothic/ethereal/ancient壁画(F-4!)/minimalist/oil_painting | фактический style-словарь роутов (строковый) |
| **genome style_presets** | `GENOME modules.style_presets` | 1 ключ (meaning_смирение) — смысловой, не визуальный | НЕ визуальный словарь (не путать) |
| **PromptComposer + 6 templates** | `visual/prompt_composer.py` + `prompt_templates/{base,comfyui,flux,runway,kling,hailuo}` | compose/compose_negative/compose_pair(VisualContext) | structured_prompt → prompt-проекция (переиспользовать) |

### 2.2 Фактический поток execution-параметров сегодня (главный forensic-результат)

Все 5 маршрутов MD-2 (A/B/C/D/E) как будущие «производители планов» + их фактическая передача параметров вниз (источник: routes → pipeline → chain → provider):

| Параметр | Маршрут (параметр запроса) | В VisualAsset | В ImageProviderChain.generate_with_metadata | В ComfyUIProvider.generate |
|----------|------------------------------|---------------|---------------------------------------------|------------------------------|
| **style** | C: `style=cinematic_fantasy` (assets.py:42); E: film_studio.py:302 | да (asset.style) | — (входит в текст промпта через STYLE_PRESETS-префикс, prompt_builder.py:129-130) | — (в тексте промпта) |
| **mood** | C: assets.py:43 | да (asset.mood) | — | — |
| **size** | C: assets.py:46 `1024x1024`; D: 1024x576; E: film 1024x576/1024x1024 | да (generation.size) | **да** (size=size) | да (_inject_size) |
| **provider** | C: assets.py:44 `auto`; фронт: 'auto'/'comfyui'/'mock' | да (generation.provider) | **да** (preferred_provider) | — (выбор в цепи) |
| **quality** | C/E: `draft/standard/high/ultra` (assets.py:48; film:346) | да (generation.quality) | **НЕТ** (не передаётся) | готов принять (kwargs.get("quality") → QUALITY_PRESETS steps/cfg/sampler), **но не получает** |
| **negative_prompt** | C: assets.py:49 (строка); фронт: negativePrompt | да (generation.negative_prompt[]) | **НЕТ** | tuple-механика (prompt,(pos,neg)) есть, но chain не вызывает |
| **seed/steps/model/cfg/sampler** | — (роуты НЕ принимают) | model/steps/seed дефолты схемы (sdxl/30/None) | НЕТ | внутренние QUALITY_PRESETS/DEFAULT_WF/_resolve_ckpt — закрытая механика провайдера |
| **duration_sec/fps** | video-C: assets.py:100 (8 сек/24 fps) | да | video-chain: да (generate(prompt, duration, size, fps)) | image_sequence: fps/duration в ffmpeg |
| **custom_prompt** | E: film shot (film_studio.py:302+ → pipeline custom_prompt) | prompt_used | — (входит в текст промпта) | — (в тексте) |
| **generator** (выбор шаблона промпта) | D: `base/flux/...` (assets.py:57) | — | preferred_provider=generator | — |

**Вывод:** фактический живой execution-конверт сегодня = `{prompt, negative(обрыв), size, preferred_provider, duration, fps}`. Quality — мёртв (MP-F1). Остальное — внутренняя механика провайдера, которой Аркаим не управляет (и не должен — ADR).

### 2.3 Provider-интерфейсы (что контракт должен покрывать с Media-стороны)

- `ImageProvider.generate(prompt, size)` + `health()` — ABC (providers/image/__init__.py:9-16); chain: `generate_with_metadata(prompt, size, preferred_provider)` → ProviderExecutionResult{name, kind, bytes}.
- `VideoProvider.generate(prompt, duration, size, fps)` + health; chain-обёртка.
- ComfyUIProvider: DEFAULT_WF (node-graph), _inject_prompt/_size/_seed/_quality (QUALITY_PRESETS), _resolve_ckpt (список моделей через API), health/poll.
- Video-fallback: ImageSequenceVideoProvider — кадры через image-provider → ffmpeg CLI (pipeline._generate_video_from_frames:263-302; _make_interpolated_shot:304+ — интерполяция движения камеры по прогрессу кадра).

### 2.4 Film studio как Scenario-прототип (E-путь)

- ShotVersion (film schemas:42-55): prompt/camera(CameraSpec)/duration_sec/negative_prompt[]/quality(pattern draft|standard|high|ultra) — по сути готовый **VideoPlan-per-shot**-прототип.
- FilmProjectStore SQLite (projects→scenes→shots→versions, assembly), ShotAssembler (ffmpeg ken-burns/concat). 17 роутов /film/*.
- E-маршрут: shot.custom_prompt + quality/size/overrides → pipeline.generate_image(scene_context) — camera/duration/negative из ShotVersion НЕ передаются (в asset идёт только custom_prompt/quality/size) — пред-плановая деградация (MP-F10).

### 2.5 Подтверждённые gap-факты

- **GAP-2 подтверждён:** `MediaPlan|MediaRequest|media_plan|media_request` в core/runtime — 0 вхождений в коде (только doc-упоминание MD-2 в schemas.py:61).
- **GAP-3 подтверждён (lineage):** `parent_request_id|lineage|derivation` — 0 в коде.
- **GAP-7 подтверждён:** temporal_context отсутствует в VisualAsset-записи; /visualize/epoch идёт prompt→provider без плана (MD-2 не менял: маршрут B потребляет temporal для 404-решения, но промпт прежний).
- **PA-F1 (MD-2, deferred):** Route A строит SceneContext (canonical entry), но данные промпта идут из legacy genome-dict — при MD-3 вход «сцена→план» должен опираться на SceneContext.
- **Audio:** только вход-индексация (book_os/multimodal.py) + VisualAsset.audio: dict (пустая заглушка) — AudioPlan = extension point (схему НЕ определяем).

## 3. КЛЮЧЕВЫЕ ФАКТЫ для дизайна MD-3

### 3.1 «Мёртвые» и «витринные» активы (что контракт НЕ должен фиксировать как живое)

1. **quality — мёртвый параметр** (MP-F1): фронт отправляет (useGenerateImage.ts:36), роуты принимают и пишут в GenerationParams, НО `pipeline.py:140-149` вызывает `generate_with_metadata(prompt, size, preferred_provider)` **без quality**; chain не передаёт; ComfyUIProvider готов принять (`kwargs.get("quality")`, comfyui.py:119-120) — и не получает. **Следствие для контракта:** quality — НЕ поле MediaPlan (это execution-механика Media-стороны); если владелец хочет управлять качеством — это отдельное решение (расширение конверта в MD-4/5), в v0 честно фиксируем факт обрыва.
2. **negative — полуобрыв** (MP-F2): строится честно (build_negative_prompt/composer.compose_pair), сохраняется в asset, но до провайдера доходит только через tuple-механику ComfyUI, которую chain не использует. В v0: negative_constraints — полноценное поле плана (это смысл), а пробитие его до исполнителя — вопрос MD-4/5 (execution-конверт).
3. **GenerationParams — витрина** (MP-F3): из 9 полей код фактически использует size/provider (+quality/negative как запись-без-действия). model/steps/seed/quality — дефолты, никогда не задаваемые роутами; steps/cfg/sampler — вообще не поля Аркаима (внутренность ComfyUI QUALITY_PRESETS). **MB-3-очистка VisualAsset** — в MD-3 scope (см. §9), но БЕЗ изменения legacy-поведения.
4. **VideoContext/VideoIntelligence/ContinuityEngine — витринные** (MP-F5): зарегистрированы в DI, но роуты/пайплайн их не вызывают; реальный видеопуть = build_asset_prompt → video_provider.generate(prompt, duration, size, fps) ИЛИ интерполированные кадры+ffmpeg. **Следствие:** video-поля плана (motion/transitions/rhythm) — проекция будущих потребностей, В v0 определяем их схемой (типы готовы), но НЕ подключаем consumers (по R3: не проектировать в вакууме — поля зафиксированы как ready-to-use, consumers подключаются при MD-4/5 или по решению владельца).
5. **model/seed/steps — не управляются Аркаимом** (MP-F4): DEFAULT_WF/QUALITY_PRESETS/_resolve_ckpt — закрытая механика исполнителя. ADR Decision 3 подтверждён фактом: Аркаим никогда не выбирал модель; выбор «модели» = выбор провайдера = уже вне домена.

### 3.2 Что живо и пойдёт в контракт как есть

- `structured_prompt`/`prompt`-проекция: PromptComposer (VisualContext→positive/negative по target) — единственный канонический рендер; 6 шаблонов (base/comfyui/flux/runway/kling/hailuo) = задел «target-словаря» Media-проекта.
- `intent`: в коде один дефолт `key_frame` (schemas.py:69); Foundation предлагал enum (key_frame|atmosphere|character_study|…) — v0 берёт фактический базис + расширяемость (MP-F7).
- `visual_style`: фактический словарь — строковые style (8 значений STYLE_PRESETS visual_assets + world_engine cinematic|realistic|watercolor…). v0: строковое поле + словарь стилей как knowledge (не enum, чтобы не ломать legacy).
- `temporal_context`: TemporalSceneRef (MD-2) — готов 1:1 (epoch_id/name_ru/confidence/bounds/provenance/счётчики) — РЕАЛЬНОЕ поле (маршрут B его потребляет).
- `provenance`: ProvenanceTag-протокол (category 8 значений + confidence) — стандарт; планы наследуют provenance сцены/эпохи (ADR-инвариант 7: RECONSTRUCTION-эпоха → RECONSTRUCTION-план).
- `characters[]`: CharacterInAsset (id/name/appearance/expression/pose) — готов; genome character_visuals=105 как источник.
- `location`: source_refs.location_id + LocationVisualContext — готов.
- `constraints/negative_constraints`: positive/negative-промпт-слои VisualContext — источник.
- `camera/composition`: CameraSpec(shot_type/angle/movement) — готов (в E: ShotVersion.camera).
- `sequence[]` (video): ShotSpec — готов; в E: ShotVersion — почти ShotSpec (двойник, MP-F10).
- `lineage`: 0 кода — проектируем (§4.3); id-прототип = generate_asset_id (pipeline.py:108).

### 3.3 Прецеденты формата

- **Pydantic → JSON-Schema:** SCHEMAS/{CHARACTER,ENTITY,QUOTE,THEME}.schema.json (draft-07) — прецедент экспорта контрактов; MediaPlan.schema.json встанет в этот ряд (при реализации).
- **Версии:** APP_VERSION/GENOME_VERSION (config.py) — строковые версии «1.0.0»; для контракта — `plan_version: str = "0.1.0"` + versioned-эволюция (ADR Decision 4г: «контракт эволюционирует отдельно от обоих проектов»).
- **Versioned-serialization-прецедент:** VisualContext.to_dict/summary (MD-2) — None-safe сериализация extras; тот же паттерн для MediaPlan.to_dict.

## 4. ЦЕЛЕВАЯ СХЕМА MD-3 (предложение, без реализации)

### 4.1 Двухуровневый контракт: MediaPlan (домен) + ExecutionDispatch (конверт)

```
SceneContext (MD-2: VisualContext + scene_extras)   ← ЕДИНСТВЕННЫЙ смысловой вход
        │
        ▼  MediaPlanBuilder (MD-3 NEW: проекция SceneContext → план)
┌─────────────────────────────────────────────────────────────────┐
│ MediaPlan (pydantic, media-neutral — НАШЕ ЗАДАНИЕ)               │
│  plan_id · plan_version="0.1.0" · media_kind(image|video)       │
│  intent · structured_prompt · prompt(проекция) · negative_constraints │
│  characters[] · location · visual_style · atmosphere · camera   │
│  constraints · source_refs · temporal_context(=TemporalSceneRef) │
│  provenance(наследование сцены/эпохи) · lineage                  │
│  video-only: duration · sequence[] · actions · camera_motion · │
│              transitions · temporal_consistency(continuity-ref) │
│  audio: НЕ ОПРЕДЕЛЯЕТСЯ (media_kind=audio — extension point)    │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼  dispatch(plan) — КОНВЕРТ (MD-3: проекция плана в НАЖИВУЮ механику)
┌─────────────────────────────────────────────────────────────────┐
│ ExecutionDispatch (dataclass, НЕ домен — временный конверт)     │
│  prompt · negative · size · preferred_provider · duration · fps │
│  (фактический живой конверт 2026-09-11; поля = ТО, что реально   │
│   доходит до провайдеров сегодня — см. §2.2)                     │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼  (MD-4/5: Media-проект примет план напрямую; конверт умрёт)
ImageProviderChain / VideoProviderChain → Provider → Backend → файл
```

**Почему два уровня:** MediaPlan — домен-контракт по ADR (без execution-полей); но сегодня планы должны исполняться СУЩЕСТВУЮЩИМИ провайдерами, чей интерфейс = (prompt, size, preferred_provider, duration, fps). ExecutionDispatch — честный мост «план→провайдер», который: (а) не пачкает домен; (б) фиксирует современный фактический конверт; (в) умирает в MD-5, когда Media-проект принимает план сам. Это ключевое решение v0 — предотвращает «контракт в вакууме» (R3) и «execution в домене» (MB-3) одновременно.

### 4.2 MediaPlan v0 — поля (полная спецификация для реализации)

```
MediaPlan (pydantic, core/CORE/visual_assets/… или core/CORE/media_plan/ — см. §9)
── идентификация ──
plan_id: str (uuid) · plan_version: str = "0.1.0"
media_kind: "image" | "video"  (audio — extension, НЕ реализуем)
── смысловая проекция SceneContext ──
intent: str = "key_frame"  (базис фактический; словарь значений — открытый knowledge)
structured_prompt: str  (machine-readable факты — из composer-механики)
prompt: str  (натуральный текст — то, что сегодня уходит провайдеру)
negative_constraints: list[str]  (смысловые запреты; НЕ execution)
characters: list[CharacterInAsset]  (id/name/appearance/expression/pose)
location: LocationRef {location_id, type?, architecture?, atmosphere?}
visual_style: str  (строка из фактического словаря: cinematic_fantasy/…)
atmosphere: str  (эмоция→атмосфера проекция)
camera: CameraSpec {shot_type, angle, movement}
constraints: list[str]  (positive-ограничения)
── ссылки и происхождение (наследование MD-2) ──
source_refs: SourceRefs (MD-2: scene_id/chapter/character_ids/location_id/entity_refs/rag_fallback)
temporal_context: TemporalSceneRef | None (MD-2 1:1)
provenance: list[ProvenanceRef]  (наследование: сцена/эпоха → план; ADR-инвариант 7)
── родословная ──
lineage: PlanLineage {parent_plan_id: str | None, derivation: str, created_from: str}
   (derivation: "initial"|"regenerate"|"variation"|"adaptation"…; created_from — класс источника)
── video-only (заполняется при media_kind=video) ──
duration_sec: float = 8.0 · fps: int = 24
sequence: list[ShotSpec]  (ShotSpec готов; E: ShotVersion→sequence — проекция)
actions: list[CharacterMotion] · camera_motion: CameraMovement
transitions: list[TransitionSpec] · temporal_consistency: ContinuityRef {project_id, shot_index}
── ЧЕГО НЕТ (запрет ADR Decision 3; тест-инвариант) ──
model · checkpoint · steps · cfg · seed · sampler · workflow · node_graph · provider · backend · loras · denoise
```

**Запрет-проверка (тест-инвариант реализации):** `set(dataclass/pydantic-fields(MediaPlan)) ∩ BANNED = ∅` — прямой перенос EXECUTION_FIELDS-теста MD-2 (test_md2_scene_context.py:168) на новый слой; + positive-тест «prompt/negative/size/duration/fps проходят из плана в dispatch 1:1».

### 4.3 Lineage-модель (GAP-3 — закрывается в v0)

```
PlanLineage:
  parent_plan_id: str | None   # None = initial (первый план сцены)
  derivation: str              # "initial" | "regenerate" | "variation" | ...
  created_from: str            # "scene_context" | "film_shot" | "epoch" | ...
      MediaPlan (v1, initial)
        │ regenerate(style=realistic)      → MediaPlan (v2, parent=v1, derivation="regenerate")
        │ variation(custom constraints)   → MediaPlan (v3, parent=v1, derivation="variation")
```

- Родословная пишется планом, читается всеми (аудит «откуда этот кадр»: сцена→эпоха→план→файл).
- Provenance-наследование отдельно от lineage: provenance = «насколько верен смысл», lineage = «кто чьей производной является». RECONSTRUCTION-эпоха → план с provenance RECONSTRUCTION (категория наследуется, не выдумывается).
- Idempotency: plan_id уникален; regenerate-запрос создаёт НОВЫЙ план с parent-ссылкой (не мутирует старый — паттерн immutable, как TemporalSceneRef в MD-2).
- Persistence: в v0 план сериализуется в JSON (to_dict-паттерн MD-2); хранение планов — Minimal-v0: в asset-записи как embedded (asset.plan), НОВЫХ таблиц НЕ создаём (см. §10 границы).

### 4.4 Как планы строит MediaPlanBuilder (проекция, не генерация)

```
build_image_plan(scene_context, intent?, style_override?, custom_prompt?) → MediaPlan(image)
   - structured_prompt/prompt: PromptComposer (target=base) от VisualContext — БЕЗ изменения текста
     (контракт промптов заморожен: сравнение до/после в тестах — паттерн MD-2)
   - characters/location/camera/atmosphere: проекция измерений VisualContext
   - temporal_context/provenance/source_refs: 1:1 из scene_extras (MD-2)
   - lineage: initial (или parent при regenerate)
build_video_plan(scene_context, duration?, fps?, shots?) → MediaPlan(video)
   - sequence: shots ИЛИ [ShotSpec(движение-интерполяция)] (сегодняшняя механика _make_interpolated_shot — вербализована в план)
   - actions/camera_motion/transitions: из VideoContext-типов (VideoIntelligence.create_video_context — первый живой consumer)
   - temporal_consistency: ContinuityRef (ContinuityEngine.apply — второй живой consumer)
   - duration/fps: фактические параметры маршрута
```

**Ключевое:** Builder — чистая проекция SceneContext (детерминированная, без LLM — архитектурный принцип «книга — источник истины»; формулы композера заморожены). PA-F1-учёт: Route A при переключении на план получает данные промпта ИЗ SceneContext (закрывает «консолидацию вызова без потока данных» — но БЕЗ изменения текста промпта: A продолжает рендерить через build_scene_prompt-контракт, пока владелец не решит сменить промпт-контракт).

### 4.5 Пять маршрутов → пять точек плана (миграционная карта)

| Маршрут | Что происходит в MD-3 | Контракты |
|---------|------------------------|-----------|
| A `/visualize` | план строится (PA-F1-closure), рендер промпта прежний (byte-identical контракт сохранён MD-2) | 200/тело ответа неизменны |
| B `/visualize/epoch/{id}` | temporal_context попадает в план (GAP-7-closure: temporal теперь в записи-плане, не только в 404-решении) | 200/404/тело неизменны |
| C `/assets/generate` (+batch/async/regenerate) | план → dispatch → существующий pipeline; overrides→plan-поля; regenerate = lineage-производная | asset-модель ответа неизменна; +plan в записи |
| D `/assets/generate-context*` | уже SceneContext-путь: plan = проекция того же ctx; composer-рендер как есть | 200/тело неизменны |
| E film `/shots/generate` | ShotVersion → план: custom_prompt + camera/duration/negative из ShotVersion (MP-F10-closure: поля шота доезжают до плана) | 200/тело неизменны |

### 4.6 ExecutionDispatch (конверт; монитор MB-3)

```
ExecutionDispatch (dataclass; в visual_assets/pipeline-слое, НЕ в домене):
  prompt: str · negative: str · size: str · preferred_provider: str · duration: float · fps: int
  from_plan(plan) → ExecutionDispatch   # проекция: plan.prompt/negative_constraints→negative/…
  → ImageProviderChain.generate_with_metadata(prompt, size, preferred_provider)
  → VideoProviderChain.generate(prompt, duration, size, fps)
```

- В v0 конверт = фактический живой набор (§2.2); quality НЕ входит (мёртв — MP-F1; не легитимизируем обрыв).
- MB-3-очистка: VisualAsset.generation (GenerationParams) становится deprecated-полем (DEPRECATED-метка, НЕ удаление — legacy-маршруты /assets/* читают его из ответов); новые записи используют plan+dispatch-информацию; модель ответа НЕ меняется (совместимость).
- Конверт умирает в MD-5 (Media-проект принимает план) — заложено в дизайн.

### 4.7 Аудитория плана (кто читает план в v0)

1. Pipeline (исполнение через dispatch) — основной consumer.
2. Asset-запись (asset.plan embedded — история «по какому плану сделан файл»).
3. Логи/observability (prompt_used + plan_id — трассировка).
4. (MD-4/5) Media-проект — внешний consumer (JSON-Schema-экспорт в SCHEMAS/).
5. Frontend (отображение provenance/lineage в UI картинок) — опционально, не в v0-scope (см. §10).

### 4.8 Версионирование контракта

- `plan_version: "0.1.0"` в каждом плане (semver-минимум: 0.x — v0-стадия).
- JSON-Schema-экспорт: `SCHEMAS/MEDIA_PLAN.schema.json` (draft-07, прецедент THEME.schema.json) — при реализации; контракт версионировать строкой + полем `$comment`.
- Эволюция: additive-поля → минор; несовместимые → мажор (MD-4/5 — точка пересмотра).

## 5. КЛАССИФИКАЦИЯ компонентов (REUSABLE / LEGACY / MIGRATION / FORBIDDEN)

### 5.1 REUSABLE (1:1, без изменений)

VisualContext+scene_extras (MD-2-канон) · SceneContextBuilder+build_scene_context* · TemporalSceneRef/ProvenanceRef/SourceRefs/SceneIntegrity (MD-2) · ProvenanceTag-протокол · PromptComposer+6 templates (рендер) · CameraSpec/CharacterInAsset/ShotSpec (пере-использование в плане) · VisualValidator · SceneEngine (утилита чтения genome; 404-контракт) · ImageProviderChain/VideoProviderChain (принимают dispatch-вызовы как сегодня) · genome+VISUAL_KNOWLEDGE · DI-registry.

### 5.2 LEGACY (живут до MD-4/5; MD-3 не добавляет новых зависимостей)

GenerationParams/VisualAsset.generation (MB-3 — deprecated в MD-3) · build_asset_prompt (E-путь до полной миграции) · /comfyui/* endpoints (MB-2 — де-публикация MD-5) · StableDiffusionProvider (не в DI-chain) · PromptBuilder-слой-1 (A/B-промпты — до пересогласования промпт-контракта) · film ShotVersion-двойник (→ проекция в sequence, дубликат не создаём).

### 5.3 MIGRATION (в scope MD-3)

| Что → Куда |
|------------|
| overrides-словари роутов → plan-поля (C/E) |
| custom_prompt (E) → plan.prompt override + lineage(created_from="film_shot") |
| negative-механика (build_negative_prompt/composer) → plan.negative_constraints (+dispatch.negative — пробитие до провайдера = MD-4/5, в v0 только фиксация) |
| temporal_context (GAP-7) → план B-маршрута |
| regenerate-семантика → lineage(derivation="regenerate") |
| VideoContext-типы → plan.video-поля (первые живые consumers: create_video_context, ContinuityEngine.apply) |
| PA-F1 (Route A) → plan строится из SceneContext (закрытие «потока данных» на уровне плана; промпт-рендер прежний) |

### 5.4 FORBIDDEN (ADR Decision 3 + расширения MD-3)

model/checkpoint/steps/cfg/seed/sampler/workflow/node_graph/provider/backend/loras/denoise — в MediaPlan (запрет-тест) · ComfyUI-знания (node-graph/ckpt-имена) в любом новом модуле · AudioPlan-поля (extension point — прямой запрет) · прямые HTTP-вызовы провайдеров из плана/билдера · LLM в MediaPlanBuilder (детерминированная проекция) · новые M-номера · второй параллельный план-класс (MediaPlan один; ShotVersion-миграция = проекция, не новый класс) · new DB-таблицы/миграции в v0 · mutations WorldModel/WORLD_MODEL/GENOME из плана-путей · изменение тел ответов A-E.

### 5.5 НЕ ТРОГАЕМ в MD-3

arkaim-web (frontend: план-отображение — вне v0; UI-настройки quality/provider работают на legacy-конверте) · providers/ (MD-4) · /comfyui/* (MD-5) · temporal-data/WORLD_MODEL/GENOME · C2 · film-БД F-12 (stale-db — отдельный pre-existing finding; MD-3 не мигрирует film-хранилище) · SharedSettings M8.1 · F3/arkaim-web-v2 · основной roadmap-мастер.

## 6. FINDINGS (новые, сверх MD-1/MD-2)

| # | Severity | Факт | Путь | Что делать |
|---|----------|------|------|-----------|
| MP-F1 | Medium | **quality — мёртвый параметр**: фронт/роуты передают, asset хранит, но pipeline→chain НЕ передают; ComfyUI готов принять — не получает. «Управление качеством» сегодня не работает end-to-end | useGenerateImage.ts:36 · assets.py:48,66-69 · pipeline.py:140-149 · providers/image/__init__.py:71-88 · comfyui.py:119-120 | НЕ фиксировать в плане (execution); решение о пробитии quality в конверт — владельцу (MD-4/5 или отдельно); отчёт владельцу: кнопка «качество» в UI сейчас не влияет на генерацию |
| MP-F2 | Medium | **negative-prompt обрывается**: строится/сохраняется, но chain не передаёт провайдеру (tuple-механика ComfyUI не активирована) | pipeline.py:133,140-149 · comfyui.py:115 | plan.negative_constraints (смысл) + dispatch.negative (конверт); пробитие до провайдера — MD-4/5; в v0 фиксируем честно |
| MP-F3 | Medium | **GenerationParams — витрина**: 8/9 полей не задаются кодом (model/steps/seed — дефолты; steps/cfg/sampler — вообще не поля Аркаима); используется фактически size/provider(+quality/negative как запись) | visual_assets/schemas.py:44-51 · §2.2 | MB-3: DEPRECATED-метка generation-поля (не удаление); чистка — после стабилизации плана |
| MP-F4 | Info | **model/seed выбор не управляем Аркаимом**: DEFAULT_WF/QUALITY_PRESETS/_resolve_ckpt — внутренняя механика ComfyUI-провайдера; подтверждает ADR Decision 3 фактом (Аркаим никогда не выбирал модель) | comfyui.py:16-75,83-106,118-127 | подтвердить ADR; никаких model-полей в контракте |
| MP-F5 | Medium | **Витринная video-половина**: VideoContext/VideoIntelligence/ContinuityEngine зарегистрированы в DI, но не потребляются production-роутами; видео = один промпт или интерполированные кадры+ffmpeg | video_context.py · video_intelligence.py · continuity_engine.py · adc_deps:202-208 · §2.2 | v0: plan.video-поля = проекция типов (готовых), consumers подключаются при MD-4/5 или отдельно; НЕ подключаю в v0 (R3-дисциплина) |
| MP-F6 | Low | **Ближайшие соседи плана — двойники**: ShotSpec(visual_assets) ↔ ShotVersion(film) — одинаковые поля (prompt/camera/duration/negative), разные классы; FilmProject↔VisualAsset частично | visual_assets/schemas.py:35-41 · film_studio/schemas.py:42-55 | v0: ShotSpec в plan.sequence; ShotVersion→sequence — проекция (без нового класса); консолидация — MD-4/5 |
| MP-F7 | Low | **intent-словарь не существует**: единственный фактический intent — key_frame (дефолт); Foundation-предложение (key_frame/atmosphere/…) — проекция, не факт | visual_assets/schemas.py:69 | v0: intent: str + открытый словарь значений knowledge (не enum-заморозка) |
| MP-F8 | Low | **style-словари размножены**: STYLE_PRESETS(visual_assets, 8 значений, вкл. CJK-ключ F-4) · STYLE_QUALITY_PRESETS(builder) · form_engine style_prefixes · world_engine pattern(cinematic/realistic/watercolor) — при одном фактическом UX-словаре | prompt_builder.py:17-26 · world_engine.py:42,114 | v0: visual_style: str (не enum); консолидация словарей — отдельный подэтап (как F-2 в MD-2, сделано; значения НЕ менять) |
| MP-F9 | Info | **GAP-3 подтверждён**: lineage — 0 кода; существующая regenerate-семантика (style/quality query) — родитель не фиксируется | grep §2.5 · assets.py:/regenerate | v0: PlanLineage — закрытие; regenerate → derivation-производная |
| MP-F10 | Medium | **E-деградация**: ShotVersion.camera/duration_sec/negative_prompt не доезжают до pipeline (передаётся только custom_prompt; quality/size/overrides) | film_studio.py:302-374 · pipeline.py:127-133 | v0: ShotVersion→plan-проекция (поля шота → план; pipeline читает из плана) — MP-F10-closure в MD-3 |
| MP-F11 | Info | **Сериализация плана — прецедент готов**: VisualContext.to_dict/summary (None-safe) — паттерн для MediaPlan.to_dict; SCHEMAS/*.schema.json — прецедент JSON-Schema-экспорта | visual_context.py:52-68 · SCHEMAS/THEME.schema.json | v0: to_dict + SCHEMAS/MEDIA_PLAN.schema.json (при реализации) |
| MP-F12 | Info | **A/B-промпты остаются на legacy-рендере** (PA-F1 MD-2): план A строится из SceneContext, но текст промпта рендерится прежним PromptBuilder-контрактом (byte-identical) | visual.py:44-68 · MD2-POST-AUDIT §0 | v0: так и проектируем (контракт MD-2 сохранён); смена промпт-контракта A — отдельное решение владельца (вне v0) |

## 7. Учёт PA-F1 (MD-2, deferred to MD-3 design) — как закрыт этим дизайном

Владелец принял PA-F1: «перевод downstream flow на Scene Context потребовал бы изменения промпт-контракта; сохранение контракта было обязательным». Дизайн MD-3 закрывает PA-F1 на уровне ПЛАНА, не ломая контракт: Route A строит MediaPlan ИЗ SceneContext (данные промпта теперь идут через план = поток данных консолидирован), но текст промпта рендерится прежним PromptBuilder-контрактом (byte-identical). Т.е. «смысл в плане — текст прежний». Смена промпт-контракта A (composer-рендер) остаётся отдельным решением владельца (не v0). Это единственный способ закрыть PA-F1 без нарушения вердикта владельца.

## 8. Риски MD-3

| Риск | Оценка | Митигация |
|------|--------|----------|
| R3' (MD-1 R3): контракт «в вакууме» | Низкий (снят дизайном) | каждое поле плана происходить из фактического NOW-актива (§3.2/§4.2 — происхождение каждого поля указано); витринные video-поля помечены ready-to-use, consumers не подключены |
| R2' (тест-семейство визуала) | Medium | маршруты не меняют контракты; новые plan-тесты инвариантов; параллельный прогон legacy/plan-путей на этапе миграции |
| Double-representation план↔asset | Medium | v0: план embedded в asset (asset.plan); чистка — MD-4/5 (R4 MD-1) |
| Расползание scope в MD-4/5 | Medium | §10-границы жёсткие: providers//comfyui//frontend/БД — НЕ трогаем |
| «Мёртвые» параметры легитимируются | Low | v0 НЕ вносит quality в конверт (обрыв честно задокументирован MP-F1; решение — владельцу) |
| Legacy-совместимость /assets/* | Medium | generation-поле deprecated (не удалено); модель ответа неизменна; тесты равенства ответов до/после |
| Новый parallel-класс (история слоёв) | Low | MediaPlan ОДИН; ShotVersion/VisualAsset — проекции, не новые классы |

## 9. План реализации MD-3 (предложение, к GO/NO-GO)

**Подэтап 1 — MediaPlan v0 + Builder (additive, ядро):**
`core/CORE/media_plan/schemas.py` (или visual_assets/media_plan.py — по решению реализации): MediaPlan/PlanLineage/LocationRef/ContinuityRef (pydantic; CharacterInAsset/CameraSpec/ShotSpec/TemporalSceneRef/ProvenanceRef — импорт, не копия) + `MediaPlanBuilder` (build_image_plan/build_video_plan — проекция SceneContext; без LLM; composer-механика заморожена) + `ExecutionDispatch.from_plan` (конверт) + unit-тесты: запрет-инвариант (BANNED∩fields=∅), lineage-инвариант, provenance-наследование (RECONSTRUCTION→RECONSTRUCTION), сериализация to_dict/None-safe.

**Подэтап 2 — подключение 5 маршрутов (по одному, с тестами):**
порядок: D (уже SceneContext — фиксация плана) → C (+batch/async/queue-обвязка; overrides→plan; regenerate→lineage) → E (ShotVersion→plan-проекция; MP-F10-closure) → B (temporal_context в план — GAP-7-closure) → A (план из SceneContext — PA-F1-closure; промпт-рендер прежний). Каждый шаг: контракт-тесты (тела ответов неизменны), plan-в asset-записи (embedded JSON).

**Подэтап 3 — deprecated-метки + документация:**
VisualAsset.generation → DEPRECATED (как вход; в ответах живёт до MD-4/5); SCHEMAS/MEDIA_PLAN.schema.json (draft-07); docs-обновление (MEDIA_DIRECTION: статус MediaPlan=IMPLEMENTED); отчёт владельцу.

**Оценка:** ~4-6 файлов глубоко (новый media_plan-модуль, pipeline-dispatch, 3 маршрута, storage-plan-embed), ~10 тест-файлов сопровождаются, 2-3 новых тест-файла, 1 JSON-Schema. Без ADR-нового (внутри ADR_ARKAIM_MEDIA_BOUNDARY Decision 4 — «контракт = единственная точка»; если владелец хочет — ADR на MediaPlan-v0 отдельно).

**GO-вопросы владельцу (решить при GO):**
1. Расположение: `core/CORE/media_plan/` (новый домен-модуль) или `core/CORE/visual_assets/media_plan.py` (внутри существующего слоя)? [рекомендую media_plan/ — отдельный контракт по ADR; visual_assets остаётся execution-legacy]
2. Пробивать ли quality до провайдера в MD-3 (добавление в конверт) или честно зафиксировать обрыв и решить в MD-4/5? [рекомендую НЕ пробивать: v0-минимальность; MP-F1-отчёт владельцу]
3. ADR на MediaPlan-v0 отдельным документом? [по вашему решению; дизайн уже внутри ADR_ARKAIM_MEDIA_BOUNDARY D4]
4. Frontend-отображение плана (provenance/lineage в UI картинок) — включать в v0? [рекомендую нет — после стабилизации, MD-5-этап]

## 10. Что НЕ входит в MD-3 (границы этапа)

Вынос providers/ComfyUI (MD-4) · де-публикация /comfyui/* (MD-5) · HTTP Arkaim↔Media-интеграция (MD-5) · AudioPlan-схема (later — прямой запрет) · новые DB-таблицы/migrations (план embedded в asset-запись; schema evolution — MD-4/5) · frontend (arkaim-web legacy + v2) · film-БД F-12 (stale — pre-existing; ShotVersion→plan читается из film-кода, не из БД-миграции) · temporal-data/WORLD_MODEL/GENOME · C2 · SharedSettings M8.1 · консолидация style-словарей (отдельный подэтап; v0 не требует) · смена промпт-контракта A/B (PA-F1-вердикт сохраняется) · legacy visual cleanup (F-1/F-2-масс-чистка).

## 11. Git-статус этого этапа

Аудит = только чтение. Единственный новый файл: `docs/MD3_PRE_IMPLEMENTATION_AUDIT.md` (этот документ). Код/тесты/данные/фронтенды/SCHEMAS — 0 правок. CJK-scan: 0 в новом документе (кроме цитаты F-4-ключа «ancient壁画» в §2.1/MP-F8 — намеренная ссылка на pre-existing finding).

---

**STOP.** Реализация MD-3 НЕ начата. Жду вашего **GO/NO-GO на MD-3 implementation** (план §9; GO-вопросы 1-4 — решения при GO). MD-4/Media-проект/C2/F-12-миграция — не начинаются автоматически.
