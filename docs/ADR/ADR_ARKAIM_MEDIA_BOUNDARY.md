# ADR — ARKAIM ↔ MEDIA BOUNDARY

**Тип:** Architecture Decision Record
**Дата:** 2026-09-09
**Статус:** ✅ ACCEPTED (2026-09-14) — границы проведены в коде: `arkaim-media` существует, ComfyUI перенесён (commit `d4bcef2`), ExecutionDispatch удалён (MD-5, commit `d73d29a`).
**Контекст:** micro-stage MEDIA DIRECTION FOUNDATION (после принятия TEMPORAL API ALIGNMENT как PASS WITH FINDINGS). Никакой код не менялся; это архитектурная фиксация границы, чтобы дальнейшая разработка Arkaim не потребовала дорогостоящей перестройки.
**Сопутствующий документ:** `docs/MEDIA_DIRECTION_FOUNDATION.md` (forensic-аудит NOW/GAP/TARGET + контракт MediaPlan + roadmap delta).

---

## Простыми словами

1. **Цель** — провести границу между двумя разными проектами: «Аркаим» (понимает книгу: мир, время, сцены, смысл) и «Media-проект» (делает картинки/видео/звук). Сегодня эта граница размыта: внутри кода Аркаима лежит знание о внутреннем устройстве ComfyUI. Пока это не зафиксировано — каждый новый этап визуала будет углублять связанность, и разъединить проекты потом будет дорого.

2. **Решение** — Аркаим формирует **смысловое задание** (Scene Context → Media Plan); Media-проект **исполняет** его (Workflow → Provider → Backend → Execution → Asset). Между ними — единственный стабильный внешний контракт (MediaRequest/MediaPlan). Ни Аркаим, ни Media-проект не знают внутренностей друг друга.

3. **Что уже хорошо** — в Аркаиме уже есть почти всё для «смысловой» стороны: единый VisualContext (15 видов контекста), геном визуалов (105 персонажей/локаций/сцен), временная модель (M8.1), provenance-протокол (метки происхождения). 

4. **Что плохо (найдено аудитом, НЕ исправляется сейчас)** — ComfyUI-провайдер с знанием node-graph живёт прямо в ядре Аркаима; публичные /comfyui/* endpoints; SD-параметры (модель/steps/cfg) в доменной схеме ассета; три параллельных prompt-генератора. Всё это — legacy-наследие Sprint 0/M6/M7, зафиксировано как findings с путями миграции.

5. **Дальше** — жду ACCEPTED. Реализация границы (вынос провайдера, контракт) — отдельные будущие этапы по roadmap delta; здесь только архитектура.

---

## Decision 1 — Два независимых проекта

**Project A — Arkaim** (существующий репозиторий `arkaim/`). Домен: Книга → Knowledge/World Model → Temporal Context → Scene Context → Scenario → **Media Plan**. Отвечает за: понимание книги, World Model, временной контекст, персонажей, места, события, реконструкции, гипотезы, художественный контекст, сцену, сценарий, формирование содержательно богатого задания для media generation. **Не является media execution engine.**

**Project B — Media / ComfyUI** (отдельный самостоятельный проект, сегодня не существует как отдельный repo). Домен: Media Request → Planning/Workflow → Provider → Backend → Execution → Asset. Перспективно Image / Video / Audio. Не знает внутреннюю модель книги.

**Граница** = стабильный внешний контракт (Decision 4). Не `Arkaim → ComfyUI HTTP` напрямую; не `Arkaim → ComfyUI workflow/node graph`.

**Rationale.** Смысловое задание и исполнение — разные компетенции с разной скоростью изменений: модель книги меняется с каноном, media-стек меняется с технологиями. Связанность делает оба хрупкими.

**Evidence.** Сегодня граница нарушена: `core/CORE/providers/image/comfyui.py` содержит DEFAULT_WF (ComfyUI node graph: KSampler/CheckpointLoaderSimple + имя checkpoint'а `cyberrealistic_v80.safetensors`), `_inject_prompt` знает про CLIPTextEncode-ноды, `_resolve_ckpt` ходит в ComfyUI API за списком моделей; `runtime/core/routes/visual.py:258-277` публикует `/comfyui/status`, `/comfyui/config`.

**Consequences.** Arkaim можно использовать без Media Project (контракт — единственная точка отсечения; literary rendering и все доменные сценарии работают без media). Media Project можно использовать без Arkaim (контракт самодостаточен). Каждый развивается независимо.

**Rejected.** (а) «Оставить провайдеры в core» — уже показало цену: три слоя визуала, provider-специфика в доменных схемах; (б) «Arkaim вызывает Media по HTTP с workflow-параметрами» — это утечка знаний об исполнении обратно в Аркаим.

---

## Decision 2 — Цепочка и место ветвления

```
World Model → Temporal Context → Scene Context → { Literary rendering | Image Plan | Video Plan | Audio Plan (future) } → внешний Media Project → Execution → Asset
```

**Один Scene Context потенциально порождает все виды планов.** Ветвление происходит ПОСЛЕ контекста, не через независимые prompt-генераторы с отдельными входами.

**Scene Context ≠ Media Prompt.** Scene Context — доменная правда о сцене (кто/где/когда/эмоция/символы/provenance); Media Prompt — одна из ПРОЕКЦИЙ контекста для конкретного media_kind, собираемая на стороне плана (или Media-проекта по структурированному заданию).

**Rationale.** Архитектура вокруг отдельных prompt-генераторов ведёт к потере общего контекста сцены. Аудит нашёл три параллельных prompt-генератора (`visualization/prompt_builder.py` [dict-based, Sprint 0], `visual/prompt_composer.py` [VisualContext-based, не используется роутами], `visual_assets/prompt_builder.py` [обёртка первого]) — живое подтверждение риска.

**Evidence.** `core/CORE/visual/visual_context.py` — VisualContext (scene/location/architecture/landscape/environment/lighting/palette/atmosphere/symbols/historical/camera/style/emotion/characters/negative_prompt) — готовая основа Scene Context; зарегистрирован в DI (`visual_context_builder`), но роуты пока используют старый PromptBuilder. Genome: scenes=10, character_visuals=105, location_visuals=5, style_presets. M7.2 (`routes/visual.py::visualize_epoch`) — живой Temporal→Visual мост (WorldModel.get_temporal_context → build_epoch_prompt → image_provider) — но без Media Plan: prompt идёт прямо в провайдер.

**Consequences.** Сценарий «одна сцена → литературное описание + кадр + видеофрагмент» реализуется одним контекстом с тремя планами; consistency (ContinuityEngine) работает на уровне контекста, не промптов.

---

## Decision 3 — Словарь понятий (разграничение)

| Понятие | Проект | Смысл |
|---------|--------|-------|
| Scene Context | Arkaim | доменная правда о сцене (не промпт) |
| Media Prompt | Arkaim (план) / Media (детализация) | проекция Scene Context для media_kind |
| **Media Plan ≠ Workflow** | Arkaim / Media | План — задание; Workflow — способ исполнения в Media |
| **Media Plan ≠ ComfyUI Node Graph** | — | План не содержит нод, samplers, checkpoint'ов |
| **Capability ≠ Media Plan** | Media | Capability — класс задач, которые Media умеет (напр. `image.generate`); План — конкретное задание |
| **Provider ≠ Media Plan** | Media | Provider — источник исполнения; не поле плана |
| **Asset ≠ Media Request** | Media | Asset — результат исполнения (с метаданными/lineage); запрос — вход |
| Asset ≠ File | Media | Asset — сущность с provenance/lineage; файл — носитель |

**Rationale.** Проверка на конфликты с замороженными AD владельца (Asset≠File, Capability≠Workflow, Provider≠Model, Provider≠Backend, Workflow≠Node Graph, ComfyUI≠Agent, LLM не имеет прямого доступа к ComfyUI, Agent не управляет ComfyUI напрямую, PromptBuilder не выбирает capability, media-execution-backend не входит в domain logic, core media-agnostic) — **направление совместимо со всеми**: эти AD зафиксированы здесь впервые как канон (в docs/ADR ранее не существовали). Конфликты КОДА с ними — см. Findings (не исправляются).

**Consequences.** Доменные схемы Arkaim не содержат полей бэкенда (model/steps/cfg/seed/checkpoint/workflow) — планы выражают интент (`media_kind`, `intent`, `visual_style`, `constraints`), исполнение выбирает механику.

---

## Decision 4 — Единственная точка интеграции: внешний контракт

**Контракт уровня MediaRequest/MediaPlan** (концептуальная схема — без production-классов на этом этапе; полная схема в `MEDIA_DIRECTION_FOUNDATION.md` §Target):

```
request_id · scene_context (ref|embedded) · media_kind (image|video|audio=future)
intent · structured_prompt · prompt
characters[] · location · temporal_context (epoch + provenance)
visual_style · atmosphere · camera/composition
constraints · negative_constraints
source/provenance (ProvenanceTag — протокол уже существует)
lineage (parent_request_id · derivation chain)
video: duration · sequence[] · actions · camera_motion · transitions · temporal_consistency
audio: AudioPlan — extension point (схема НЕ определяется сейчас)
```

Обязательные свойства контракта: (а) self-contained — Media не должен знать Arkaim-модель; (б) provenance-first — каждый план несёт метки происхождения сцены/эпохи; (в) без media-backend полей; (г) versioned (контракт эволюционирует отдельно от обоих проектов).

**Rationale.** Контракт — единственный.surface соприкосновения: он может меняться медленно, а реализации с обеих сторон — быстро. Provenance уже стандартизован (source_levels.py: ProvenanceTag category+confidence) — переиспользуем, не изобретаем.

**Evidence.** Существующие ингредиенты: VisualAsset (`visual_assets/schemas.py`) — 70% полей совпадают с планом; VideoContext (`visual/video_context.py`) — CameraMovement/CharacterMotion/LightDynamics/TransitionSpec (video-поля); ProvenanceTag — готов; lineage — отсутствует (0 упоминаний в коде).

---

## Decision 5 — Инварианты (что дальнейшая разработка НЕ должна нарушать)

1. **Core Arkaim — media-agnostic.** Ни один модуль `core/CORE/` (кроме исторических findings до миграции) не знает о ComfyUI/workflow/node-graph/checkpoint'ах.
2. **Никаких прямых `Arkaim → ComfyUI HTTP`** из доменной логики; интеграция — только через внешний Media-контракт.
3. **LLM не имеет прямого доступа к ComfyUI; агент не управляет ComfyUI напрямую** (LLM — голос, не архитектура; media-execution — не его компетенция).
4. **PromptBuilder не выбирает capability** — выбор capability принадлежит Media-планированию; Arkaim-строители только проектируют контекст в поля задания.
5. **Media execution backend не является частью domain logic** — Provider/Backend/Workflow живут в Media-проекте.
6. **Scene Context — единственный источник истины для всех планов** (image/video/audio/literary) — новые генераторы строятся от контекста, не параллельно ему.
7. **Temporal model не меняется ради media** — Media Plan потребляет temporal read-only (эпоха + provenance), как зафиксировано в ADR_TEMPORAL_WORLD_MODEL §5 (инвариант фронтенда расширяем на все потребители).
8. **Данные плана наследуют provenance сцены/эпохи** — «кадр по реконструированной эпохе» обязан нести метку RECONSTRUCTION в lineage цепочке актива.

## Findings кода (нарушения существующие, НЕ исправляются в этом ADR)

| # | Severity | Нарушение | Evidence | Путь (в будущих этапах) |
|---|----------|-----------|----------|--------------------------|
| MB-1 | High (architectural debt) | ComfyUI node-graph знание в core: DEFAULT_WF с KSampler/checkpoint-именем, `_inject_prompt` (CLIPTextEncode), `_resolve_ckpt` | `core/CORE/providers/image/comfyui.py:13-46` | Вынос ComfyUI-провайдера в Media-проект при реализации контракта; Arkaim остаётся с контрактом |
| MB-2 | Medium | Публичные ComfyUI-эндпоинты в Arkaim API | `runtime/core/routes/visual.py:258-277` (`/comfyui/status|config`) | Де-публикация при миграции; статус media-бэкенда — забота Media-проекта |
| MB-3 | Medium | Media-параметры исполнения в доменной схеме: `GenerationParams(model="sdxl", steps=30, seed, cfg)` + `provider` | `core/CORE/visual_assets/schemas.py:44-51` | Схема MediaPlan не наследует эти поля; execution-параметры уезжают в Media-проект |
| MB-4 | Low (structural) | Три параллельных prompt-генератора; новый PromptComposer не используется роутами | visualization/prompt_builder · visual/prompt_composer · visual_assets/prompt_builder | Консолидация вокруг Scene Context при реализации |
| MB-5 | Informational | Media-стек дублируется слоями (visualization Sprint 0 / visual 23.07 / visual_assets 23.07 + film_studio) — все живы в DI | adc_deps.py:53-110, 184-229 | Единая целевая карта в MEDIA_DIRECTION_FOUNDATION.md |

Миграция этих находок — предмет roadmap-этапов (см. PROPOSED ROADMAP DELTA), не текущего micro-stage и не F3.

## Backward compatibility

ADR ничего не меняет в runtime. Существующие endpoints/assets продолжают работать (legacy-слой сохраняется до отдельных этапов миграции). Новые разработки: (а) не углубляют violations (инвариант «не хуже»); (б) новые доменные схемы следуют Decision 3.

## Итог

Граница зафиксирована: Arkaim = смысл (до Media Plan), Media = исполнение (от Media Request). Контракт — единственная точка соприкосновения. Инварианты защищают от дрейфа. Существующие нарушения каталогизированы с путями миграции, не исправлены (вне scope).
