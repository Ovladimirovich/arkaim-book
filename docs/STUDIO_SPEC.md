# STUDIO_SPEC — Arkaim Studio v2 Design Specification (SUPERSEDED)

**Тип:** Проектная документация (design specification) — **УСТАРЕВШАЯ**
**Дата:** 2026-09-15
**Ревизия:** 4 (Phase 1B implementation: models + store + API + tests)
**Статус:** SUPERSEDED — заменена на `docs/ARKAIM_STUDIO_SPEC.md`
**Примечание:** Это старая спецификация Studio v2. Актуальная спецификация — `docs/ARKAIM_STUDIO_SPEC.md`. Не используется как источник текущих требований.
**Предшественники:** ADR_ARKAIM_MEDIA_BOUNDARY (ACCEPTED), ADR_MEDIA_PLAN_V0 (ACCEPTED), Media Boundary Verification (ACCEPTED)
**Связанные документы:** `docs/forensic_investigation_studio.md`, `IMAGE_DESCRIPTION_FORENSIC_ANALYSIS.md`, `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md`, `docs/ADR/ADR_MEDIA_PLAN_V0.md`

---

## Простыми словами

1. **Что такое Studio?** — Рабочая комната корректировки. Аркаим сначала формирует богатое описание сцены на основе World Model, книги, временного контекста и существующих механизмов описаний. Studio получает этот результат и позволяет автору: обсуждать, корректировать, уточнять элементы, редактировать вручную, добавлять reference-изображения, создавать варианты, сравнивать версии и финализировать.

2. **Три результата описания.** Для одной сцены Studio работает с тремя связанными, но различными слоями: **Image Description** (описание изображения), **Video Description** (описание видео), **Full Video Scenario** (полный видеосценарий). Это не три генерации — это три разных результата проектирования одной сцены.

3. **Studio НЕ генерирует контент.** Всё исходное описание приходит из системы описаний Arkaim. LLM в Studio — инструмент для понимания и применения корректировок пользователя, а не самостоятельная система описаний.

4. **Финальный результат:** StudioExport = три описания + reference asset references. Передаётся в arkaim-media, который сам решает, как исполнять.

5. **Ключевая граница:**
```
Система описаний Arkaim → исходное описание → Studio (корректировка) → Final StudioExport → arkaim-media
```

---

## 1. Назначение Studio

Studio — это **collaborative editing workspace** (рабочее пространство совместной доработки) внутри Arkaim.

### 1.1 Главный принцип

**Вся исходная «магия описания» приходит из существующей системы описаний Arkaim.**

Arkaim сначала формирует богатое, содержательно обоснованное описание сцены:
- `VisualContextBuilder` → `VisualContext` (15 измерений контекста)
- `MediaPlanBuilder` → `MediaPlan` (смысловой Prompt Package)
- `PromptComposer` → текст промпта (рендер для конкретного генератора)
- `VideoContext` → видео-расширение (камера, движение, переходы)

Studio **получает** этот результат и является пространством корректировки, обсуждения и финализации.

Studio **не заменяет и не дублирует** систему описаний Arkaim.

### 1.2 Что Studio позволяет пользователю

- Обсуждать полученное описание с Arkaim (LLM-диалог)
- Давать корректировки («более мрачно», «добавить туман»)
- Уточнять отдельные элементы (атмосфера, камера, стиль, персонажи)
- Вручную редактировать текст промпта
- Добавлять reference-изображение как визуальный ориентир
- Создавать варианты («ещё 2 варианта»)
- Сравнивать и переключать версии
- Финализировать выбранный вариант

### 1.3 Ключевая граница

```
Studio заканчивается на: Final StudioExport (три описания + references)
Дальше: StudioExport → arkaim-media (отдельный проект)
```

**Никакой генерации image/video/audio в Studio и вообще в Arkaim.**

---

## 2. Три результата описания сцены

### 2.1 Зачем три результата

Одна сцена может быть описана по-разному для разных целей:
- **Image Description** — для генерации одного кадра (изображения)
- **Video Description** — для генерации видео-клипа (динамика, движение, время)
- **Full Video Scenario** — для постановки полного видеосценария (режиссёрская логика, последовательность планов, развитие сцены)

Это **не три генерации**. Это три разных результата проектирования одной сцены. Каждый строится из одного и того же SceneContext, но с разной глубиной и разными акцентами.

### 2.2 A. IMAGE DESCRIPTION

Описание будущего изображения. **Источник:** `VisualContext` (15 измерений) + `MediaPlanBuilder.build_image_plan()`.

| Элемент | Источник в Arkaim |
|---------|------------------|
| Композиция | `VisualContext.camera.composition` |
| Окружение | `VisualContext.environment`, `VisualContext.landscape` |
| Персонажи | `VisualContext.characters` (appearance, expression, pose) |
| Свет | `VisualContext.lighting` (source, direction, color, intensity) |
| Атмосфера | `VisualContext.atmosphere` (fog, wind, particles, color_temperature) |
| Стиль | `VisualContext.style` |
| Палитра | `VisualContext.palette` |
| Символика | `VisualContext.symbols` |
| Исторический контекст | `VisualContext.historical` |
| Negative constraints | `VisualContext.negative_prompt` |

**Формат в Studio:** `MediaPlan` (media_kind="image") — существующий контракт, не расширяется.

### 2.3 B. VIDEO DESCRIPTION

Описание будущего видео. **Источник:** `VideoContext` (VisualContext + видео-расширения) + `MediaPlanBuilder.build_video_plan()`.

| Элемент | Источник в Arkaim |
|---------|------------------|
| Движение камеры | `VideoContext.camera_movement` (type, speed, direction, effect) |
| Движение персонажей | `VideoContext.character_motion` (action, speed, emotion) |
| Движение среды | `VideoContext.object_motion` (fire, fog, wind, water) |
| Динамика света | `VideoContext.light_dynamics` (color temperature shift, intensity change) |
| Переходы | `VideoContext.transitions` (cut, dissolve, fade) |
| Ритм | `VideoContext.rhythm` (pace, beat_duration) |
| Длительность | `VideoContext.duration_sec` |
| Кадры (sequence) | `MediaPlan.sequence: list[ShotPlan]` |
| Движение (motion) | `MediaPlan.motion: MotionPlan` |

**Формат в Studio:** `MediaPlan` (media_kind="video") — существующий контракт, не расширяется.

### 2.4 C. FULL VIDEO SCENARIO

Полный видеосценарий сцены. **Источник:** всё выше + режиссёрская логика.

Full Video Scenario — это **наиболее полное описание**, которое включает:
- Последовательность событий в сцене
- Действия персонажей в каждый момент
- Планы (wide → medium → close-up → detail)
- Камерные переходы между планами
- Развитие сцены во времени (завязка → развитие → кульминация)
- Режиссёрские указания (темп, паузы, акценты)
- Звуковые указания (атмосферные звуки, тишина)
- Необходимые детали постановки

**Формат в Studio:** `VideoScenario` — **новый контракт**, описанный в §4.4. Это НЕ execution-контракт (нет model/steps/seed), а **сценарное описание** для arkaim-media.

**Критически важно:** Full Video Scenario строится из SceneContext + VideoContext + данных World Model. LLM может помочь сформулировать сценарий из этих данных, но **не должен выдумывать содержание** — оно приходит из системы описаний Arkaim.

### 2.5 Связь трёх результатов

```
Система описаний Arkaim
    │
    ├── VisualContext (15 измерений)
    │       │
    │       ├── MediaPlanBuilder.build_image_plan()
    │       │       → A. IMAGE DESCRIPTION (MediaPlan, media_kind="image")
    │       │
    │       └── VideoContext.from_visual_context()
    │               │
    │               ├── MediaPlanBuilder.build_video_plan()
    │               │       → B. VIDEO DESCRIPTION (MediaPlan, media_kind="video")
    │               │
    │               └── VideoScenarioBuilder.build() [NEW]
    │                       → C. FULL VIDEO SCENARIO (VideoScenario)
    │
    └── Studio: корректировка / обсуждение / варианты / финализация
            │
            └── StudioExport = { image_description, video_description, video_scenario, references }
```

---

## 2.6 Forensic Audit: что существующая система РЕАЛЬНО производит

Перед проектированием Studio проведён forensic существующей системы описаний. Результаты определяют, что Studio может получить «из коробки», а что является gap.

### A. IMAGE DESCRIPTION — ✅ PARTIALLY FORMED

**Пipeline:** `VisualContextBuilder.build_scene_context()` → `VisualContext` (15 измерений) → `MediaPlanBuilder.build_image_plan()` → `MediaPlan` (media_kind="image")

**Что реально формируется (когда VISUAL_KNOWLEDGE содержит данные для сцены):**

| Поле | Источник | Качество | Пример |
|------|----------|----------|--------|
| scene.title, emotion, meaning_tags | Genome | Rich | "Встреча у костра", "sacred" |
| location.name, type, architecture | LOCATION_VISUALS.json | Rich | "Аркаим", "Bronze Age settlement" |
| landscape.terrain, vegetation | LOCATION_VISUALS.json | Rich | "Ural steppe, rolling hills" |
| atmosphere.fog, wind, particles, light | ATMOSPHERES.json | Rich | "golden sacred light, gentle fog" |
| characters[].appearance, name | CHARACTER_VISUALS.json | Rich | "wise elder, silver beard, ritual robes" |
| style.name, prefix | STYLE_LIBRARY.json | Rich | "cinematic_fantasy" |
| symbols | VISUAL_SYMBOLS.json | Medium | symbolic meanings |
| lighting | ATMOSPHERES.json + LOCATION_VISUALS | Medium | derived from atmosphere |
| prompt (текст промпта) | PromptComposer | Rich | ~500 char structured prompt |
| negative_constraints | PromptComposer | Medium | list of exclusions |

**Что НЕ формируется (gaps):**

| Поле | Статус | Причина |
|------|--------|---------|
| camera.composition | Всегда пустое | Не генерируется автоматически |
| palette.description | Всегда пустое | Не генерируется автоматически |
| historical.cultural_notes | Пустое если нет world_entities | Нет fallback |
| characters[].expression | Пустое | Не определяется из контекста |
| characters[].pose | Пустое | Не определяется из контекста |
| location.architecture_style | Пустое если нет в LOCATION_VISUALS | Нет RAG/fallback |

**Проблема «тонких» сцен:** Если сцена не имеет явной записи в VISUAL_KNOWLEDGE, промпт получается ~150 символов (только title + стиль + default lighting). Система — **faithful renderer** существующих данных, а не generator missing content.

**Вывод:** Image Description **существует** в production, но качество зависит от покрытия VISUAL_KNOWLEDGE. Studio может использовать его как исходную точку.

---

### B. VIDEO DESCRIPTION — ⚠️ INFRASTRUCTURE EXISTS, NOT IN PRODUCTION

**Существующая инфраструктура:**

| Компонент | Файл | Статус |
|-----------|------|--------|
| `VideoContext` | `core/CORE/visual/video_context.py` | Определён (7 полей: camera_movement, character_motion, object_motion, light_dynamics, transitions, rhythm, duration_sec) |
| `VideoIntelligence` | `core/CORE/visual/video_intelligence.py` | 158 строк, реальная логика (emotion→camera, character→motion, atmosphere→objects, light dynamics, transitions, rhythm) |
| `VIDEO_RULES.json` | `core/CORE/visual/VISUAL_KNOWLEDGE/` | rhythm, continuity_rules, transition_rules, motion_rules, quality_rules |
| `CAMERA_LIBRARY.json` | `core/CORE/visual/VISUAL_KNOWLEDGE/` | shot types, movements, transitions, compositions |
| `build_video_plan()` | `core/CORE/media_plan/builder.py` | Определён, принимает VideoContext-типы |
| DI registration | `runtime/core/adc_deps.py` | `_factory_video_intelligence` зарегистрирован |

**Критический finding:**

| Проверка | Результат |
|----------|-----------|
| `build_video_plan` вызывается из production routes? | **НЕТ** — только в тестах |
| `VideoIntelligence` вызывается из production? | **НЕТ** — зарегистрирован в DI, но 0 consumers |
| `VideoContext` создаётся в production? | **НЕТ** — `from_visual_context()` только в VideoIntelligence |
| Какой endpoint возвращает video MediaPlan? | **НИКАКОЙ** — все routes используют `build_image_plan` |

**Вывод:** Video Description **не формируется** в production. Инфраструктура (модели, knowledge base, builder) существует, но production path = 0. Для Studio нужно **подключить** существующую инфраструктуру, а не создавать с нуля.

**Что нужно сделать:**
1. Создать route/endpoint, который вызывает `VideoIntelligence.create_video_context()` → `build_video_plan()`
2. Это **не** новая система описаний — это подключение существующей к production path
3. `VideoIntelligence` уже содержит реальную логику (emotion→camera, character→motion, atmosphere→objects)

---

### C. FULL VIDEO SCENARIO — ❌ DOES NOT EXIST

**Что существует:**

| Компонент | Что он делает | Подходит для Video Scenario? |
|-----------|--------------|------------------------------|
| `ScenarioModeler` | Моделирует альтернативные развития (World Explorer) | ❌ Это narrative branches, не video scenarios |
| `ScreenplayLayer` | Keyword-matching по screenplay_extracts.json | ❌ Это поиск по тексту, не builder |
| `FilmStudio` | CRUD проектов/шотов/версий | ❌ Это storage, не description generator |
| `screenplay_extracts.json` | Содержит диалоги и описания персонажей | ⚠️ Есть данные, но нет формирования сценария |

**Что НЕ существует:**

| Элемент сценария | Статус | Доказательство |
|------------------|--------|----------------|
| Последовательность событий | ❌ Empty | Нет temporal ordering в VisualContext |
| Действия персонажей во времени | ❌ Empty | VisualContext описывает статичные позы, не динамику |
| Режиссёрская логика | ❌ Empty | Нет reasoning для порядка планов |
| Планы (wide→medium→close-up) | ❌ Empty | Нет sequence-level shot planning |
| Развитие сцены во времени | ❌ Empty | Нет scene evolution logic |
| Звуковые указания | ❌ Empty | Нет audio design |
| Ритм на уровне последовательности | ⚠️ Thin | `VideoIntelligence` имеет per-shot rhythm, но не sequence-level |

**Вывод:** Full Video Scenario **не существует** ни в какой форме. Система описывает **ЧТО** находится в сцене (статичное описание), но не может описать **ЧТО ПРОИСХОДИТ ПО ПОРЯДКУ** (динамический сценарий).

**Это Variant C** (из задания): существующая система описаний не производит Full Video Scenario.

---

### Итоговая таблица forensic

| Результат | Статус | Существующий pipeline | Что нужно для Studio |
|-----------|--------|----------------------|---------------------|
| **A. Image Description** | ✅ Partially formed | `VisualContextBuilder` → `VisualContext` → `MediaPlanBuilder` → `MediaPlan` | Использовать как есть. Studio = корректировка |
| **B. Video Description** | ⚠️ Infrastructure, no production | `VideoIntelligence` (exists, 158 lines, real logic) + `build_video_plan` (exists) — never called | Подключить существующий `VideoIntelligence` к production path |
| **C. Full Video Scenario** | ❌ Does not exist | Нет pipeline. Нет builder. Нет temporal sequence data. | **Gap.** Требует отдельного архитектурного решения |

---

### Архитектурный gap: Full Video Scenario

**Статус:** ЗАФИКСИРОВАН КАК GAP. Не реализовывать автоматически.

**Что есть:**
- `VideoIntelligence` — per-shot context (camera, motion, rhythm, transitions)
- `VIDEO_RULES.json` — правила ритма, переходов, непрерывности
- `screenplay_extracts.json` — диалоги и описания персонажей
- `MediaPlan.sequence: list[ShotPlan]` — контейнер для последовательности кадров
- `MediaPlan.motion: MotionPlan` — контейнер для движения

**Что отсутствует:**
- Temporal sequence builder (что происходит 1-м, 2-м, 3-м)
- Directorial logic (почему этот план за этим)
- Scene evolution (как сцена развивается от начала к концу)
- Character arc over time (как поведение персонажа меняется)
- Sound design (атмосферные звуки, тишина)

**Минимальное решение (предлагается, НЕ реализуется автоматически):**
1. `VideoScenarioBuilder` строит сценарий из: `VisualContext` + `VideoIntelligence` output + `MediaPlan.sequence` + LLM (для формулировки directorial logic из данных)
2. LLM **не выдумывает** содержание — формулирует сценарий из существующих данных
3. Входные данные: scene title, characters, location, atmosphere, emotion, existing shot plan
4. Выход: `VideoScenario` (секвенция планов с directorial notes)

**Это единственный компонент, который Studio должна создать заново.** Остальное — переиспользование существующего.

---

## 3. Архитектурная граница

### 3.1 Что Studio использует из Arkaim

| Компонент | Роль в Studio | Переиспользование |
|-----------|--------------|-------------------|
| `VisualContextBuilder` | Строит SceneContext → VisualContext | ✅ 100%, без изменений |
| `MediaPlanBuilder.build_image_plan()` | Строит Image Description (MediaPlan) | ✅ 100%, без изменений |
| `MediaPlanBuilder.build_video_plan()` | Строит Video Description (MediaPlan) | ✅ 100%, без изменений |
| `PromptComposer` | Рендерит текст промпта из VisualContext | ✅ 100%, без изменений |
| `VisualContext` | Канонический контекст сцены (15 измерений) | ✅ 100%, без изменений |
| `VideoContext` | Видео-расширение контекста | ✅ 100%, без изменений |
| `SceneContextExtras` | Provenance + source_refs + integrity | ✅ 100%, без изменений |
| `WorldModel` | Данные о мире (эпохи, события, персонажи) | ✅ 100%, без изменений |
| `WorldEngine` | Навигация, temporal chain | ✅ 100%, без изменений |
| `AssetStorage` | Хранение файлов (reference images) | ⚠️ +source_type |
| `BookVoice` / LLM | Генерация ответов на вопросы | ⚠️ Новый system prompt для Studio |
| `FilmProjectStore` pattern | Паттерн версионирования | ⚠️ Паттерн, не класс |

### 3.2 Что Studio создаёт новое

| Компонент | Описание | Forensic статус |
|-----------|----------|----------------|
| `VideoScenarioBuilder` | Строит Full Video Scenario | **Единственный truly новый компонент** (gap C) |
| `VideoScenario` | Контракт видеосценария | Новый контракт |
| `ScenarioShot` | План в сценарии | Новый контракт |
| `StudioSession` | Модель сессии | Новый |
| `StudioMessage` | Сообщение в discussion | Новый |
| `StudioVersion` | Версия трёх описаний | Новый |
| `ReferenceAsset` | Reference-изображение | Новый |
| `StudioExport` + `ExportedReference` | Финальный результат | Новый |
| Studio API endpoints | `/studio/*` | Новый |
| Studio frontend page | `/studio` | Новый |

**Критически:** Подключение `VideoIntelligence` к production path — это **не** создание новой системы. `VideoIntelligence` уже существует (158 строк, реальная логика), зарегистрирован в DI, но не вызывается ни одним route. Studio подключает его, а не создаёт заново.

### 3.3 Что Studio НЕ содержит

- ❌ ComfyUI / StableDiffusion / любых генераторов
- ❌ Generation pipeline / queue / workers
- ❌ Image/video/audio execution
- ❌ Provider selection / provider status
- ❌ Model/steps/cfg/sampler/seed/workflow/node-graph
- ❌ Video assembly / render
- ❌ Media backend integration (это делает arkaim-media)
- ❌ Самостоятельную систему описаний (всё приходит из Arkaim)

---

## 4. Модель данных

### 4.1 StudioSession

```python
class StudioSessionStatus(str, Enum):
    DRAFT = "draft"            # Только создана
    DISCUSSING = "discussing"   # Идёт обсуждение
    APPROVED = "approved"       # Пользователь утвердил
    REJECTED = "rejected"       # Пользователь отклонил
    SENT = "sent"               # Отправлена в media-проект

class StudioSession(BaseModel):
    session_id: str
    user_id: str
    title: str                       # Авто-заголовок из scene.title

    # Источник
    chapter: int
    scene_id: str
    context_type: str                # "scene" | "epoch" | "character" | "location"
    scene_context_id: str            # ID VisualContext, из которого построена сессия

    # Текущее состояние
    active_version_id: str | None    # Текущая активная версия
    status: StudioSessionStatus = DRAFT

    # Связи
    reference_assets: list[str] = [] # asset_id reference-изображений

    # Метаданные
    created_at: str
    updated_at: str
    finalized_at: str | None = None
```

### 4.2 StudioMessage (Discussion)

Discussion — история разговора. Это НЕ содержание Prompt Version. Обсуждение — это процесс, Prompt Version — конкретное состояние.

```python
class StudioMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"           # Автоматические (создание версии, изменение статуса)

class StudioMessage(BaseModel):
    message_id: str
    session_id: str
    role: StudioMessageRole
    content: str

    # Опционально: если сообщение создало новую версию
    created_version_id: str | None = None

    created_at: str
```

### 4.3 StudioVersion (Три описания)

Каждая версия — это снимок **трёх описаний** одной сцены. Это НЕ MediaPlan и НЕ PromptVersion — это обёртка, содержащая три результата.

```python
class StudioVersion(BaseModel):
    version_id: str
    session_id: str
    version_number: int

    # ── Три описания сцены ──

    # A. Image Description — проекция VisualContext → MediaPlan (media_kind="image")
    image_description: MediaPlan | None = None

    # B. Video Description — проекция VideoContext → MediaPlan (media_kind="video")
    video_description: MediaPlan | None = None

    # C. Full Video Scenario — сценарное описание (VideoScenario)
    video_scenario: VideoScenario | None = None

    # ── Lineage ──
    parent_version_id: str | None = None
    derivation: str = "initial"  # initial | variation | adaptation

    # ── Пользовательские модификации ──
    user_modifications: list[UserModification] = []

    # ── Статус ──
    is_active: bool = False
    is_final: bool = False

    # ── Метаданные ──
    created_by: str               # "system" | "user" | "assistant"
    created_at: str
    note: str = ""                # Комментарий
```

### 4.4 VideoScenario (Новый контракт)

Full Video Scenario — сценарное описание, НЕ execution-контракт. Содержит режиссёрскую логику, последовательность планов, развитие сцены во времени.

```python
class VideoScenario(BaseModel):
    """Full Video Scenario — полное сценарное описание сцены.

    НЕ execution-контракт: нет model/steps/seed/workflow/provider.
    Это режиссёрское описание для arkaim-media, который сам решает,
    как его исполнять.

    Строится из SceneContext + VideoContext + World Model.
    LLM формулирует сценарий из этих данных, но НЕ выдумывает содержание.
    """
    scenario_id: str = ""
    scene_id: str = ""                # Ссылка на сцену в genome

    # ── Общее описание ──
    title: str = ""
    synopsis: str = ""                # Краткое описание сцены (2-3 предложения)
    duration_sec: float = 30.0        # Общая длительность

    # ── Последовательность планов ──
    shots: list[ScenarioShot] = []    # Планы (wide → medium → close-up → detail)

    # ── Режиссёрские указания ──
    direction_notes: str = ""         # Общие режиссёрские указания
    rhythm: str = "medium"            # Темп: slow | medium | fast
    mood_arc: str = ""                # Дуга настроения: "от спокойствия к тревоге"

    # ── Звук ──
    sound_notes: str = ""             # Атмосферные звуки, тишина

    # ── Provenance ──
    source_refs: SourceRefs = Field(default_factory=SourceRefs)
    temporal_context: TemporalSceneRef | None = None
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    lineage: PlanLineage = Field(default_factory=PlanLineage)

class ScenarioShot(BaseModel):
    """Один план в видеосценарии."""
    shot_id: str = ""
    order: int = 0
    shot_type: str = "medium_shot"    # wide | medium | close-up | detail
    description: str = ""             # Что происходит в этом плане
    camera_action: str = ""           # Действие камеры (slow dolly in, pan left, static)
    character_actions: str = ""       # Что делают персонажи
    duration_sec: float = 3.0
    transition_to_next: str = "cut"   # Переход к следующему: cut | dissolve | fade
    notes: str = ""                   # Дополнительные указания
```

### 4.5 UserModification

```python
class UserModification(BaseModel):
    """Трекинг одного изменения пользователем."""
    target: str                   # "image_description" | "video_description" | "video_scenario"
    field_path: str               # Путь к полю (например, "atmosphere", "camera.shot_type")
    old_value: str                # Предыдущее значение (serialized)
    new_value: str                # Новое значение (serialized)
    reason: str = ""              # Причина (из discussion или введена вручную)
    timestamp: str
```

### 4.6 ReferenceAsset

```python
class ReferenceAsset(BaseModel):
    asset_id: str                 # Ссылка на AssetStorage
    session_id: str               # Ссылка на Studio-сессию
    description: str = ""         # Описание пользователя ("такой свет", "такая композиция")
    source_type: str = "user_reference"
    created_at: str
```

### 4.7 StudioExport (Финальный результат)

```python
class StudioExport(BaseModel):
    """Export-контракт Studio → arkaim-media.

    Содержит три финальных описания + reference asset references.
    MediaPlan v0 не расширяется. VideoScenario — отдельный контракт.
    Никаких execution-полей (model/steps/seed/workflow/provider).
    """
    session_id: str
    export_id: str

    # ── Три финальных описания ──
    image_description: MediaPlan | None = None     # A
    video_description: MediaPlan | None = None     # B
    video_scenario: VideoScenario | None = None    # C

    # ── Reference assets (внешние ссылки, НЕ поля описаний) ──
    references: list[ExportedReference] = []

    # ── Метаданные ──
    exported_at: str

class ExportedReference(BaseModel):
    """Reference asset в export-контракте."""
    asset_id: str
    description: str = ""
    file_url: str = ""
```

### 4.8 Связи между моделями

```
StudioSession (1) ──── (N) StudioMessage       # История обсуждения
StudioSession (1) ──── (N) StudioVersion        # Версии описаний
StudioSession (1) ──── (N) ReferenceAsset       # Reference-изображения
StudioVersion  (1) ──── (0..1) MediaPlan        # A. Image Description
StudioVersion  (1) ──── (0..1) MediaPlan        # B. Video Description
StudioVersion  (1) ──── (0..1) VideoScenario    # C. Full Video Scenario
StudioVersion  (N) ──── (1) StudioVersion       # Lineage (parent → child)
StudioSession  (1) ──── (0..1) StudioExport     # Финальный результат
```

---

## 5. Разделение Discussion / StudioVersion / Final Export

### 5.1 Discussion (история разговора)

- **Свободный текст** между пользователем и Arkaim.
- Хранится как `list[StudioMessage]`.
- Может содержать вопросы, объяснения, обсуждения контекста.
- **Не меняет описания автоматически** — только если LLM предлагает конкретные изменения и пользователь принимает их.

### 5.2 StudioVersion (снимок трёх описаний)

- **Структурированные данные**: три описания (Image Description, Video Description, Video Scenario).
- Каждое изменение описаний создаёт новую версию (immutable pattern).
- Версии связаны через `parent_version_id` (lineage).
- Пользователь может вернуться к любой предыдущей версии.

### 5.3 Final StudioExport (утверждённый результат)

- **Одна конкретная StudioVersion** с `is_final=True`.
- Статус сессии = `approved`.
- Содержит три финальных описания + reference asset references.

### 5.4 Ключевое различие

```
Discussion:     "Сделай сцену более мрачной"  →  текст разговора
StudioVersion:  {image: MediaPlan, video: MediaPlan, scenario: VideoScenario}  →  структурированный снимок
Final Export:   StudioExport(version=final, references=[...])  →  готовый к отправке
```

---

## 6. Пользовательские сценарии

### S1 — Создание Studio-сессии

**Пользователь:** Заходит в `/studio`, выбирает сцену (или эпоху, или персонажа).

**Система:**
1. Вызывает `VisualContextBuilder.build_scene_context(chapter, scene_id)` → VisualContext
2. Строит **Image Description**: `MediaPlanBuilder.build_image_plan(ctx)` → MediaPlan (media_kind="image")
   - Forensic: production pipeline, partially formed (зависит от VISUAL_KNOWLEDGE)
3. Строит **Video Description**: `VideoIntelligence.create_video_context(ctx)` → VideoContext → `MediaPlanBuilder.build_video_plan(vctx)` → MediaPlan (media_kind="video")
   - Forensic: infrastructure exists (158 lines, real logic), NOT in production — Studio подключает
4. Строит **Full Video Scenario**: `VideoScenarioBuilder.build(ctx, vctx)` → VideoScenario
   - Forensic: gap C — единственный truly new builder
5. Создаёт `StudioSession` со статусом `draft`
6. Сохраняет исходные три описания как `StudioVersion` (version_number=1, is_active=true)
7. Возвращает сессию с превью трёх описаний

**Результат:** Пользователь видит исходные три описания, построенные Arkaim из знаний о мире. Image Description — из существующего pipeline. Video Description — из существующего VideoIntelligence. Video Scenario — из нового builder.

---

### S2 — Обсуждение (Discussion)

**Пользователь:** Пишет, например:
> «Сделай сцену более мрачной, но не меняй исторические факты.»

**Система:**
1. Сохраняет сообщение пользователя в `discussion_history`
2. Формирует контекст для LLM:
   - Текущие три описания (Image/Video/Scenario)
   - SceneContext (для понимания «исторических фактов»)
   - Последние 10 сообщений обсуждения
   - System prompt: «Ты помощник автора. Помогаешь уточнять описание сцены. Всё исходное описание сформировано системой описаний Arkaim — ты НЕ придумываешь содержание заново, а корректируешь существующее. Не меняешь исторические факты. Не предлагаешь execution-параметры (model, steps, seed).»
3. LLM генерирует ответ + предложение изменений
4. Если LLM предлагает изменения → система создаёт новую `StudioVersion` с `derivation="variation"` и `parent_version_id` = предыдущей версии
5. Сохраняет ответ в `discussion_history`
6. Возвращает ответ + (опционально) обновлённые описания

**Контроль:** LLM не выдумывает содержание — он применяет корректировки пользователя к существующим описаниям, сохраняя смысловую целостность SceneContext.

---

### S3 — Ручное изменение (Manual Edit)

**Пользователь:** Сам редактирует текст промпта или меняет параметры.

**Система:**
1. Принимает изменённые поля + указание, какой слой редактируется (image/video/scenario)
2. Создаёт новую `StudioVersion` с `derivation="adaptation"`, `parent_version_id` = текущей версии
3. Фиксирует изменение в `user_modifications` (target, field_path, old_value, new_value)
4. Обновляет `active_version_id` сессии
5. Возвращает обновлённые описания

**Контроль:** Пользователь может редактировать только смысловые поля. Execution-поля заблокированы на уровне схемы (`extra="forbid"`).

---

### S4 — Reference Image

**Пользователь:** Загружает собственную картинку как визуальный ориентир.

**Система:**
1. Сохраняет файл через `AssetStorage.save_file()` с `source_type="user_reference"`
2. Создаёт `ReferenceAsset` с описанием (пользователь пишет, что на картинке важно)
3. Привязывает reference к текущей Studio-сессии
4. В discussion Arkaim может учитывать reference при предложениях

**Важно:** Reference-изображение — это входные данные для обсуждения. Оно НЕ входит ни в одно из трёх описаний. При финализации reference передаётся как `ExportedReference` — внешняя ссылка для arkaim-media.

---

### S5 — Варианты (Variants)

**Пользователь:** «Сделай ещё два варианта.»

**Система:**
1. Создаёт 2 новых `StudioVersion` с `derivation="variation"`, `parent_version_id` = текущей активной версии
2. Варианты могут отличаться по одному или нескольким слоям (image/video/scenario)
3. Пользователь видит список вариантов и выбирает лучший
4. Выбранный вариант становится `is_active=true`

**Лимит:** До 5 вариантов за операцию (O6).

---

### S6 — Финализация (Finalize)

**Пользователь:** Утверждает финальный вариант.

**Система:**
1. Меняет статус сессии на `approved`
2. Помечает активную версию как финальную (`is_final=True`)
3. Формирует `StudioExport`: три финальных описания + связанные Reference Assets
4. Возвращает `StudioExport` через `/studio/{id}/export`
5. После этого Studio **не делает ничего** с media execution

**Дальше:** arkaim-media получает `StudioExport` и сам решает, как исполнять: какие описания использовать, какие reference учитывать, какие параметры генерации применять.

---

## 7. MediaPlan v0 — проверка пригодности

### 7.1 MediaPlan = Description + Metadata

**MediaPlan** содержит:
- **Description-поля** (семантическое содержание): `prompt`, `structured_prompt`, `characters`, `location`, `visual_style`, `atmosphere`, `camera`, `constraints`, `negative_constraints`
- **Metadata-поля** (контрактные): `plan_id`, `plan_version`, `media_kind`, `intent`, `source_refs`, `temporal_context`, `provenance`, `lineage`
- **Video-поля** (опциональные): `duration_sec`, `fps`, `sequence`, `motion`, `temporal_consistency`

**Вывод:** MediaPlan — правильный контейнер для Image и Video Description. Он содержит и описание, и метаданные provenance/lineage. Описание — это поля, которые arkaim-media использует для генерации. Метаданные — это provenance и lineage, которые путешествуют с описанием.

### 7.2 Результат: MediaPlan подходит для Image и Video Description

| Требование | Есть в MediaPlan v0? | Forensic | Оценка |
|------------|---------------------|----------|--------|
| Image Description | ✅ media_kind="image" + все смысловые поля | Production pipeline существует (partially formed) | Готов к использованию |
| Video Description | ✅ media_kind="video" + sequence + motion | Infrastructure exists, NOT in production. `VideoIntelligence` (158 lines) registered but never called | Нужно подключить existing `VideoIntelligence` |
| Full Video Scenario | ❌ Нет режиссёрской логики | Does NOT exist. Gap C. | Нужен `VideoScenarioBuilder` |
| Execution fields banned | ✅ extra="forbid" | Verified | Полностью |
| Provenance + lineage | ✅ | Verified | Полностью |

### 7.3 Решение

- **MediaPlan v0 НЕ расширяется** — Image Description и Video Description используют существующий контракт.
- **VideoScenario** — новый отдельный контракт для Full Video Scenario (gap C). Не execution-контракт.
- **VideoIntelligence** — существующий класс (158 строк, реальная логика), зарегистрирован в DI. Studio подключает его к production path, а не создаёт заново.

### 7.4 Что MediaPlan уже умеет для видео

- `media_kind="video"` — маркер
- `sequence: list[ShotPlan]` — последовательность кадров (shot_id, prompt, duration_sec, camera, lighting, palette)
- `motion: MotionPlan` — движение камеры/персонажей/переходы (camera_motion, character_actions, transitions)
- `duration_sec`, `fps` — длительность и частота кадров
- `temporal_consistency` — непрерывность между шотами

**Forensic:** Эти поля **никогда не заполняются в production** (build_video_plan не вызывается). Но infrastructure существует. Studio подключает `VideoIntelligence` → `build_video_plan()` для заполнения этих полей.

---

## 8. Источник содержания Studio

### 8.1 Принцип

Studio **не генерирует** исходное содержание. Всё исходит из системы описаний Arkaim:

```
World Model + Genome + Temporal Context
        ↓
VisualContextBuilder → VisualContext (15 измерений)
        ↓
┌───────────────────────────────────────────────────────┐
│  MediaPlanBuilder.build_image_plan() → Image Descrip. │
│  MediaPlanBuilder.build_video_plan() → Video Descrip. │
│  VideoScenarioBuilder.build()        → Video Scenario │
└───────────────────────────────────────────────────────┘
        ↓
Studio: корректировка / обсуждение / варианты / финализация
```

### 8.2 Роль LLM в Studio

LLM используется **только** для:
- Понимания корректировок пользователя («более мрачно» → какие поля менять)
- Применения корректировок к существующим описаниям
- Формулировки ответов на вопросы пользователя
- Помощи в формировании VideoScenario из SceneContext + VideoContext

LLM **НЕ используется** для:
- Выдумывания содержания описаний с нуля
- Замены системы описаний Arkaim
- Выбора execution-параметров (model, steps, seed)

### 8.3 O2 (пересмотрено)

Контекст LLM для discussion = **текущие три описания + SceneContext + последние 10 сообщений**. Это технический механизм контекстного диалога. Источником содержания является система описаний Arkaim, а не LLM.

---

## 9. Reference Image — детальная модель

### 9.1 Жизненный цикл reference

```
1. Пользователь загружает картинку → POST /studio/{id}/upload-reference
2. Файл сохраняется в AssetStorage (source_type="user_reference")
3. Создаётся ReferenceAsset (связь сессии с asset_id)
4. Пользователь добавляет описание: "Обрати внимание на освещение"
5. В discussion Arkaim видит reference и учитывает его
6. Reference НЕ входит ни в одно из трёх описаний
7. При финализации → ExportedReference (asset_id, description, file_url)
```

### 9.2 Расширение AssetStorage

```sql
ALTER TABLE visual_assets ADD COLUMN source_type TEXT DEFAULT 'generated';
-- Значения: 'generated' | 'user_reference'
```

---

## 10. Persistence

### 10.1 Таблицы Studio в существующей SQLite

```sql
CREATE TABLE IF NOT EXISTS studio_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    chapter INTEGER,
    scene_id TEXT,
    context_type TEXT DEFAULT 'scene',
    scene_context_id TEXT DEFAULT '',
    active_version_id TEXT,
    status TEXT DEFAULT 'draft',
    reference_assets TEXT DEFAULT '[]',
    created_at TEXT,
    updated_at TEXT,
    finalized_at TEXT
);

CREATE TABLE IF NOT EXISTS studio_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_version_id TEXT,
    created_at TEXT,
    FOREIGN KEY (session_id) REFERENCES studio_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS studio_versions (
    version_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    image_description_json TEXT,         -- MediaPlan JSON (nullable)
    video_description_json TEXT,         -- MediaPlan JSON (nullable)
    video_scenario_json TEXT,            -- VideoScenario JSON (nullable)
    parent_version_id TEXT,
    derivation TEXT DEFAULT 'initial',
    user_modifications_json TEXT DEFAULT '[]',
    is_active BOOLEAN DEFAULT 0,
    is_final BOOLEAN DEFAULT 0,
    created_by TEXT DEFAULT 'system',
    created_at TEXT,
    note TEXT DEFAULT '',
    FOREIGN KEY (session_id) REFERENCES studio_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_studio_sessions_user ON studio_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_studio_sessions_status ON studio_sessions(status);
CREATE INDEX IF NOT EXISTS idx_studio_messages_session ON studio_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_studio_versions_session ON studio_versions(session_id);
```

---

## 11. Provenance / Lineage

### 11.1 Provenance

Каждая StudioVersion наследует provenance от исходного SceneContext (ADR_MEDIA_PLAN_V0 Decision 3). Provenance **не меняется** при обсуждении/редактировании.

### 11.2 Lineage

Каждая StudioVersion ссылается на `parent_version_id`:

```
v1 (initial, from scene_context)
  └─ v2 (variation, "Более мрачная атмосфера")
       └─ v3 (adaptation, "Добавлен туман")
            └─ v4 (final, approved)
```

Immutable pattern: каждое изменение создаёт новую версию, физическое удаление запрещено (O7).

---

## 12. API Contract

### 12.1 Переиспользуемые существующие endpoints

| Endpoint | Роль в Studio |
|----------|--------------|
| `POST /book/visualize` | Получить исходный MediaPlan (image) для сцены |
| `POST /book/visualize/epoch/{epoch_id}` | Получить MediaPlan для эпохи |
| `POST /book/assets/generate-context` | Получить MediaPlan из SceneContext |

### 12.2 Новые endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/studio/create` | POST | Создать сессию (строит три описания из SceneContext) |
| `/studio/list` | GET | Список сессий пользователя |
| `/studio/{id}` | GET | Сессия + версии + сообщения |
| `/studio/{id}/discuss` | POST | Отправить сообщение в discussion |
| `/studio/{id}/modify` | POST | Ручное изменение (target + field_path + new_value) |
| `/studio/{id}/variant` | POST | Создать варианты (до 5) |
| `/studio/{id}/activate-version` | POST | Активировать версию |
| `/studio/{id}/upload-reference` | POST | Загрузить reference-изображение |
| `/studio/{id}/approve` | POST | Финализировать |
| `/studio/{id}/reject` | POST | Отклонить |
| `/studio/{id}/export` | GET | Экспорт StudioExport (три описания + references) |

### 12.3 Conventions

- **RBAC (O4):** Создание/модификация/финализация — только `editor` + `admin`.
- **Чтение:** Только владелец сессии (проверка `user_id` из JWT).
- Response format: `SuccessResponse(data=...)` (enveloped); `direct` для `/export`.

---

## 13. Frontend UX

### 13.1 Принцип

Studio — **collaborative editing workspace**, а не Film Studio. Минимальная логика интерфейса:

**Исходное описание → три области результата → обсуждение/корректировка → версии → финализация.**

### 13.2 Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Studio — [Сцена: Конфликт Гиперборея vs Атлантида]          │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                 │
│ Слои       │  Discussion                                     │
│ ─────      │  ──────────                                     │
│            │                                                 │
│ [A] Image  │  🧑 Сделай сцену более мрачной                 │
│ [B] Video  │  🤖 Обновляю атмосферу во всех трёх слоях...   │
│ [C] Scenario│    → Новая версия #2 создана                   │
│            │                                                 │
│ ─────      │  [Введите сообщение...]                   [➤]   │
│            │                                                 │
│ Versions   ├─────────────────────────────────────────────────┤
│ ──────     │                                                 │
│ v1 ✓       │  Reference Images                               │
│ v2 ← active│  ────────────────                               │
│ v3         │  [+ Загрузить]                                  │
│            │  [img1.jpg] "такой свет"                         │
│ ─────      │                                                 │
│            ├─────────────────────────────────────────────────┤
│ [Финализировать]  [Отклонить]                                │
│            │                                                 │
└────────────┴─────────────────────────────────────────────────┘
```

### 13.3 Ключевые области

| Область | Содержание |
|---------|-----------|
| **Слои (A/B/C)** | Переключение между Image Description / Video Description / Full Video Scenario |
| **Содержимое слоя** | Текущее описание выбранного слоя (превью промпта, персонажи, камера, стиль, атмосфера; для Scenario — планы, режиссёрские указания) |
| **Discussion** | Chat-интерфейс для обсуждения с Arkaim |
| **Versions** | Список версий с возможностью переключения |
| **Reference Images** | Галерея reference-изображений с описаниями |
| **Действия** | Финализировать / Отклонить |

### 13.4 Пользователь видит

- Что предложила система (исходные три описания)
- Что изменил он (user_modifications подсвечены)
- Какая версия сейчас активна
- Какой результат утверждён

---

## 14. Что переиспользуется (итого)

| Компонент | Степень | Изменения | Phase 1A статус |
|-----------|---------|-----------|-----------------|
| `VisualContextBuilder` | 100% | Без изменений | ✅ Подтверждено |
| `MediaPlanBuilder` | 100% | Без изменений | ✅ Подтверждено |
| `PromptComposer` | 100% | Без изменений | ✅ Подтверждено |
| `VisualContext` | 100% | Без изменений | ✅ Подтверждено |
| `VideoContext` | 100% | Без изменений | ✅ Подтверждено |
| `VideoIntelligence` | 100% | Подключение к production path | ✅ Подключено (studio-describe) |
| `MediaPlan` schema | 100% | Без изменений (не расширять!) | ✅ Подтверждено |
| `AssetStorage` | 90% | +1 поле `source_type` | Phase 1B |
| `FilmProjectStore` pattern | 70% | Паттерн версионирования | Phase 1B |
| `BookVoice` / LLM | 60% | Новый system prompt | Phase 1B |
| Frontend patterns | 80% | World Explorer как шаблон | Phase 2 |

---

## 15. Что требуется добавить (итого)

### Новые компоненты

| Компонент | Тип | Сложность | Forensic | Phase 1A |
|-----------|-----|-----------|----------|----------|
| `VideoScenario` model | Pydantic schema | Низкая | Новый контракт (gap C) | ✅ `core/CORE/studio/scenario_schemas.py` |
| `ScenarioShot` model | Pydantic schema | Низкая | Новый контракт (gap C) | ✅ `core/CORE/studio/scenario_schemas.py` |
| `VideoScenarioBuilder` | Builder | Средняя | **Единственный truly new builder** (gap C) | ✅ `core/CORE/studio/scenario_builder.py` |
| `StudioSession` model | Pydantic schema | Низкая | Новый | Phase 1B | ✅ `studio/session_models.py` |
| `StudioMessage` model | Pydantic schema | Низкая | Новый | Phase 1B | ✅ `studio/session_models.py` |
| `StudioVersion` model | Pydantic schema | Низкая | Новый | Phase 1B | ✅ `studio/session_models.py` |
| `ReferenceAsset` model | Pydantic schema | Низкая | Новый | Phase 1B | ✅ `studio/session_models.py` |
| `UserModification` model | Pydantic schema | Низкая | Новый | Phase 1B | ✅ `studio/session_models.py` |
| `StudioExport` + `ExportedReference` models | Pydantic schema | Низкая | Новый | Phase 1B | ✅ `studio/session_models.py` |
| `StudioStore` | SQLite store (существующая БД) | Средняя | Новый | Phase 1B | ✅ `studio/store.py` |
| Studio API routes | 11 endpoints | Средняя | Новый | Phase 1B | ✅ `runtime/core/routes/studio.py` |
| Studio discussion logic | LLM integration | Средняя | Новый | Phase 1B | ✅ via `voice.act()` |
| `source_type` в AssetStorage | +1 поле | Низкая | Расширение | Phase 1B | ⏳ Phase 2 (not required for backend) |
| Frontend Studio page | React page | Средняя | Новый | Phase 2 | ⏳ Phase 2 |

### Подключение существующего (НЕ новое)

| Компонент | Что делается | Forensic | Phase 1A |
|-----------|-------------|----------|----------|
| `VideoIntelligence` → production path | Подключён к `/visual/studio-describe` (вызов `create_video_context()` + `build_video_plan()`) | **Уже существует** (158 строк, реальная логика). | ✅ Подключён |
| `VisualContextBuilder` → Studio | Используется `build_scene_context()` для создания initial descriptions | **Уже существует**. Production path работает. | ✅ Подтверждено |
| `MediaPlanBuilder` → Studio | Используется `build_image_plan()` + `build_video_plan()` | **Уже существует**. | ✅ Подтверждено |

---

## 16. Что запрещено

1. ❌ Добавлять в MediaPlan execution-поля
2. ❌ Расширять MediaPlan Studio-полями
3. ❌ Создавать параллельную систему описаний
4. ❌ Подключать arkaim-media
5. ❌ Добавлять execution-поля в VideoScenario (model/steps/seed/workflow/provider)
6. ❌ Использовать LLM для выдумывания содержания описаний (только корректировка)
7. ❌ Использовать PromptBuilder (legacy) — только PromptComposer
8. ❌ Автоматически запускать генерацию после финализации
9. ❌ Хранить reference-изображения в описаниях (они — внешние ссылки)
10. ❌ Создавать отдельную БД (таблицы в существующей SQLite)

---

## 17. Архитектурные решения (утверждены owner-GO)

| # | Решение | Owner GO |
|---|---------|----------|
| O1 | Reference в AssetStorage с `source_type` | ✅ |
| O2 | LLM-контекст = три описания + SceneContext + последние 10 сообщений (технический механизм; источник содержания — система описаний Arkaim) | ✅ Пересмотрено |
| O3 | Отдельная БД НЕ вводится | ✅ |
| O4 | Только editor + admin | ✅ |
| O5 | Export = три описания + references (внешние asset references) | ✅ Пересмотрено |
| O6 | До 5 вариантов | ✅ |
| O7 | Версии immutable | ✅ |
| O8 | Последние 10 сообщений | ✅ (MVP) |

### Новые решения (v2):

| # | Решение |
|---|---------|
| N1 | Три результата: Image Description (MediaPlan image), Video Description (MediaPlan video), Full Video Scenario (VideoScenario) |
| N2 | Принцип: система описаний Arkaim → исходное содержание → Studio-корректировка |
| N3 | VideoScenario — новый отдельный контракт (не execution, не расширение MediaPlan) |
| N4 | LLM в Studio — корректировка существующих описаний, а не самостоятельная генерация |

### Новые решения (v3, на основе forensic):

| # | Решение | Forensic основание |
|---|---------|-------------------|
| N5 | **VideoIntelligence** (158 строк, реальная логика) подключается к production path, а не создаётся заново. | `VideoIntelligence` зарегистрирован в DI, но 0 production consumers. Studio = первый consumer. |
| N6 | **Image Description** = существующий pipeline `VisualContextBuilder` → `MediaPlanBuilder.build_image_plan()`. Studio использует как есть, не переписывает. | Forensic: partially formed, работает когда VISUAL_KNOWLEDGE имеет данные. |
| N7 | **Full Video Scenario = GAP C.** Единственный truly new builder (`VideoScenarioBuilder`). Не реализовывать автоматически — требует owner-GO. | Forensic: система описывает ЧТО в сцене, но не ЧТО ПРОИСХОДИТ ПО ПОРЯДКУ. Нет temporal sequence, нет directorial logic. |
| N8 | **MediaPlan = Description + Metadata.** Правильный контейнер для Image/Video Description. Не расширять, не создавать параллельный Description-контракт. | Forensic: содержит и description-поля (prompt, characters, location, style, atmosphere, camera), и metadata-поля (provenance, lineage, source_refs). |

---

## 18. Влияние на существующие ADR

| Документ | Требует изменения? | Причина |
|----------|--------------------|---------|
| ADR_ARKAIM_MEDIA_BOUNDARY | **НЕТ** | Studio не нарушает ни одного инварианта. VideoScenario — не execution-контракт. |
| ADR_MEDIA_PLAN_V0 | **НЕТ** | MediaPlan не расширяется. VideoScenario — отдельный контракт. |
| Другие ADR | **НЕТ** | Studio — additive, не меняет существующие решения. |

**Новые ADR не требуются.** VideoScenario — это часть Studio (prompt workspace), а не изменение существующих контрактов. Если позже понадобится стандартизировать VideoScenario как внешний контракт — это будет отдельный ADR.

---

## Итог

Studio v2 пересмотрен с учётом forensic audit существующей системы описаний.

### Forensic findings:

1. **Image Description** — ✅ partially formed. `VisualContextBuilder` → `MediaPlanBuilder.build_image_plan()` работает в production. Studio использует как есть.
2. **Video Description** — ⚠️ infrastructure exists, NOT in production. `VideoIntelligence` (158 строк, реальная логика) зарегистрирован в DI но не вызывается. Studio подключает его к production path.
3. **Full Video Scenario** — ❌ does not exist. Нет temporal sequence, нет directorial logic. **Gap C.** Единственный truly new builder (`VideoScenarioBuilder`). Требует owner-GO.

### Что Studio реально создаёт:

| Компонент | Статус |
|-----------|--------|
| StudioSession/Message/Version/ReferenceAsset/Export | Новые модели (Studio-specific) |
| StudioStore + API routes + frontend | Новая инфраструктура |
| `VideoScenarioBuilder` + `VideoScenario` | **Единственный новый builder** (gap C) |
| Подключение `VideoIntelligence` к production | Подключение существующего (не новое) |
| Подключение `VisualContextBuilder` + `MediaPlanBuilder` | Использование существующего (не новое) |

### Ключевой архитектурный gap:

Full Video Scenario не существует. Система описывает **ЧТО** находится в сцене (статичное описание), но не **ЧТО ПРОИСХОДИТ ПО ПОРЯДКУ** (динамический сценарий). `VideoScenarioBuilder` — единственный компонент, который нужно создавать с нуля. Все остальные building blocks уже существуют.

---

## 17. Phase 1B — Studio Backend Contracts (Rev 4)

### Discussion Contract (/discuss)

| Свойство | Значение |
|----------|----------|
| LLM input | Контекст трёх описаний + история discussion |
| LLM output | Plain text (proposal / explanation / question) |
| Создаёт StudioVersion? | **НЕТ** |
| Меняет описания? | **НЕТ** |
| Меняет World Model? | **НЕТ** |
| Меняет SceneContext? | **НЕТ** |
| Добавляет execution params? | **НЕТ** |

Чтобы применить изменение — пользователь вызывает `/modify` (explicit confirmation).

### Modify Contract (/modify)

| Свойство | Значение |
|----------|----------|
| Создаёт новую версию? | Да (immutable) |
| Мутирует parent? | Нет |
| Сохраняет UserModification? | Да (target, field_path, old_value, new_value) |
| Сохраняет parent_version_id? | Да |
| Сохраняет lineage? | Да |
| Допустимые targets | `image_description`, `video_description`, `video_scenario` |
| Может менять World Model? | Нет (нет доступа) |
| Может менять execution fields? | Нет (`extra="forbid"` на MediaPlan/VideoScenario) |

### Variant Contract (/variant)

| Свойство | Значение |
|----------|----------|
| Генерирует новые описания? | **НЕТ** — копирует из active version |
| Вызывает Description System? | **НЕТ** |
| Сохраняет lineage? | Да (parent_version_id → active version) |
| Максимум вариантов | 5 |

### Initial Creation Contract (/studio/create)

Initial три описания получаются через существующую Description System:
1. `VisualContextBuilder.build_scene_context()` → VisualContext
2. `MediaPlanBuilder.build_image_plan()` → Image Description
3. `VideoIntelligence.create_video_context()` → VideoContext
4. `MediaPlanBuilder.build_video_plan()` → Video Description
5. `VideoScenarioBuilder.build()` → Full Video Scenario

Studio **не является** четвёртым Description Engine.

### Export Contract (/studio/export)

StudioExport содержит:
- `image_description` (MediaPlan v0, без расширений)
- `video_description` (MediaPlan v0, без расширений)
- `video_scenario` (VideoScenario, Phase 1A)
- `references` (external asset links)
- `version_lineage` (цепочка version_id)

Все три описания, MediaPlan и VideoScenario — `extra="forbid"`.
Нет execution fields: model, steps, cfg, sampler, seed, workflow, provider.

**STOP. Требуется owner-GO на Phase 2 (Frontend) или Phase 1C (arkaim-media integration).**
3. GO на Phase 1 implementation
