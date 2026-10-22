# MEDIA PRODUCTION MASTERPLAN — согласование с владельцем

**Тип:** документ для принятия решения владельцем (decision support)
**Дата:** 2026-10-22
**Статус документа:** PROPOSED — подготовлен для OWNER-REVIEW. **Этот документ НЕ меняет статус генерального плана:** `docs/MEDIA_PRODUCTION_MASTERPLAN.md` остаётся **PROPOSED** до отдельного OWNER-GO (решение O1).
**Предмет:** `docs/MEDIA_PRODUCTION_MASTERPLAN.md` (PROPOSED, 2026-10-14) и комплект из 4 документов
**Метод:** read-only сверка документации с фактическим кодом на 2026-10-22. Код не менялся, производство не запускалось.

**Ограничения, заданные владельцем 2026-10-22 (соблюдены в этом документе):**

| # | Ограничение | Как соблюдено |
|---|---|---|
| 1 | MediaPlan остаётся производным от World Model и существующего контракта | §2 — показана существующая цепочка World Model → SceneContext → MediaPlan; новый источник знаний не предлагается |
| 2 | НЕ создавать отдельный источник знаний | §7 — MediaPlan = проекция существующего SceneContext (`docs/ADR/ADR_MEDIA_PLAN_V0.md:25`), без новых данных |
| 3 | НЕ уводить проект в сторону генерации медиа | §7 — ядро остаётся media-agnostic (`docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:106`) |
| 4 | Статус остаётся `PROPOSED` до отдельного OWNER-GO | Шапка документа; §8 — решения не приняты за владельца |
| 5 | НЕ запускать производство | §5 — отмечено, что Этап 0 не выполнен; документ не инициирует ни одного вызова |

---

## Простыми словами

1. **Что было целью?** — Разобрать план «как делаем видео из книги» по фактическому коду и подготовить владельцу честную картину: что уже есть, чего нет, сколько это стоит и что именно нужно решить. Ничего не запускать и ничего не менять.

2. **Что реально сделано?** — Прочитаны четыре документа комплекта (`MEDIA_PRODUCTION_MASTERPLAN.md`, `MEDIA_EXECUTORS_SPEC.md`, `PILOT_FILM_PLAN.md`, `ARKAIM_STUDIO_SPEC.md`), оба ADR (`ADR_MEDIA_PLAN_V0.md`, `ADR_ARKAIM_MEDIA_BOUNDARY.md`), код `core/CORE/media_plan/`, `core/CORE/studio/`, `core/CORE/film_studio/`, роуты `runtime/core/routes/studio.py` и `film_studio.py`, мост `runtime/core/media_client.py`, соседний репозиторий `arkaim-media` (цепочки провайдеров) и тесты границы. Найдено расхождение между планом от 2026-10-14 и кодом на 2026-10-22 — §9.

3. **Что получилось?** — **PARTIAL.** План остаётся PROPOSED. План технически реализуем по замыслу, но **три опорных предпосылки не выполнены**: замер железа (Этап 0) не сделан, аппаратной базы для Wan 2.1 нет, озвучка юридически заблокирована. Реально подключённых исполнителей — **три** (Agnes — картинки, бесплатно; локальный ComfyUI — картинки; ComfyICU — видео, платно) плюс два тестовых `mock` и локальный ffmpeg-путь `image_sequence` для видео. Локального Wan 2.1, TTS и сборки по контракту нет.

4. **Есть ли проблемы?** — Да, четыре, и все они требуют решения владельца, а не инженера:
   - **Стоимость платного видео-исполнителя не зафиксирована.** Реально подключённый платный путь (ComfyICU, LTX 2.5 I2V) не имеет цены ни в одном документе репозитория.
   - **В плане нет ни одной рублёвой/долларовой сметы пилота.** В репозитории указано только «Этап 0 ~2–4 ч», остальное — TBD.
   - **Локального Wan 2.1 не существует.** На фактическом железе (AMD RX 570, 4 ГБ, PyTorch CPU) локальное видео не выполняется вовсе.
   - **План частично устарел** (записан 2026-10-14): два из десяти его «пробелов» к 2026-10-22 уже закрыты кодом, а цифры цен в двух документах расходятся.

5. **Что предлагается дальше?** — Владельцу: прочитать §4 (кто реально может генерировать), §5 (сколько это стоит) и §8 (что нужно решить). Ничего не запускать до O1. Если решение — «утвердить», следующий шаг остаётся **Этап 0** (замер одной сцены), и он требует целевого NVIDIA 8 ГБ — это отдельное решение §8.

---

## 1. Что такое MediaPlan сегодня

### 1.1. Статус — фиксируем явно

| Что | Статус | Где зафиксировано |
|---|---|---|
| `docs/MEDIA_PRODUCTION_MASTERPLAN.md` | **PROPOSED** — ожидает OWNER-GO (O1) | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:5`; реестр `docs/DOCUMENTATION_INDEX.md:66` |
| `docs/MEDIA_EXECUTORS_SPEC.md` | DRAFT (зависит от O1, O3 и результатов Этапа 0) | `docs/MEDIA_EXECUTORS_SPEC.md:5`; `docs/DOCUMENTATION_INDEX.md:68` |
| `docs/PILOT_FILM_PLAN.md` | DRAFT (зависит от O1–O4 и Этапа 0) | `docs/PILOT_FILM_PLAN.md:5`; `docs/DOCUMENTATION_INDEX.md:69` |
| `docs/ARKAIM_STUDIO_SPEC.md` | DRAFT | `docs/DOCUMENTATION_INDEX.md:67` |
| Реализация плана | не начата | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:317` |
| `docs/MEDIA_PRODUCTION_MASTERPLAN.md` в списке открытых решений владельца | открыт | `docs/ARKAIM_PROJECT_STATE.md:110`; `docs/PROJECT_REBASELINE_2026-10-18.md:270` |

**Этот документ статус не меняет.** Он только перечисляет факты, которых не хватает для решения.

### 1.2. MediaPlan — это код, а не отдельный документ

| Аспект | Факт | Где |
|---|---|---|
| Что это | Единственный канонический доменный контракт «задания на генерацию» (image\|video) | `core/CORE/media_plan/schemas.py:131-172` |
| Версия | `plan_version = "0.1.0"` | `core/CORE/media_plan/schemas.py:28` |
| Строгость | `extra="forbid"` — постороннее поле (в т.ч. execution) отвергается конструктором | `core/CORE/media_plan/schemas.py:33` |
| Запрет execution-семантики | `BANNED_FIELDS` — model, checkpoint, steps, cfg, sampler, seed, workflow, node_graph, provider, backend, comfyui, quality и др. | `core/CORE/media_plan/schemas.py:191-196` |
| Проверка запрета | `verify_no_execution_fields()` — тест-хук | `core/CORE/media_plan/schemas.py:218-256` |
| Построитель | `MediaPlanBuilder.build_image_plan()` / `.build_video_plan()` — детерминированная проекция, без LLM, без HTTP, без providers | `core/CORE/media_plan/builder.py:44-125` |
| JSON-схема | `SCHEMAS/MEDIA_PLAN.schema.json` (draft-07) | `docs/ADR/ADR_MEDIA_PLAN_V0.md:64` |
| `media_kind=audio` | зарезервирован как extension point; схема AudioPlan **не определена и не реализуется** | `core/CORE/media_plan/schemas.py:36-46`; `docs/ADR/ADR_MEDIA_PLAN_V0.md:60` |
| Кто строит в рантайме | `runtime/core/routes/visual.py:228,237`, `runtime/core/routes/assets.py:56`, `runtime/core/routes/studio.py:2744,2753` | — |

### 1.3. Этапы плана

**Уточнение по числу этапов:** в плане **девять** этапов (нумерация с нуля: 0–8), а не восемь. «Этапы 0–8» — формулировка самого плана (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:290`, сводка зависимостей `:266-271`).

| Этап | Цель | Ключевое содержание | Критерий готовности (цитата из плана) | Зависит от |
|---|---|---|---|---|
| **0** | Технический замер (спайк, без правок кода Arkaim) | ComfyUI + Wan2.1 (T2V-1.3B, umt5, VAE); одна репрезентативная сцена через workflow `text_to_video_wan`; образец Silero TTS; проверка ffmpeg | Заполнена таблица фактов «модель / параметры / VRAM / время / качество» (`:194`) | оборудование (NVIDIA 8 ГБ) (`:193`) |
| **1** | Утверждение направления и контрактов | OWNER-GO (O1); новый `ADR_AUDIO_PLAN_V0` (O2); MEDIA_CONTRACT v1.0→v1.1 (O3); починка висящих вызовов фронта | ADR принят, контракт v1.1 согласован, `runtime/tests` зелёный (`:203`) | Этап 0 (`:205`) |
| **2** | Производственный контур видео | Видео-провайдер Wan2.1 в arkaim-media; `MEDIA_BACKEND_URL`; механизм статусов задания (G5) | «Сгенерировать шот» → файл клипа в `data/visual_assets/`, статус `completed`, при ошибке — `failed` с текстом (`:212`) | Этапы 0, 1 (`:214`) |
| **3** | Аудиоконтур (диктор) | AudioPlan v0 (новый ADR); TTS-провайдер Silero (v5_ru, до 5 голосов, 48 кГц); привязка WAV к сценам | по каждой сцене пилота есть WAV + тайминг (`:221`) | Этап 1 (`:223`) |
| **4** | Сборка, QC и первый MP4 | assemble по контракту; аудиомикс диктор+атмосфера+музыка; титры/субтитры; экспорт | MP4 60–90 с проходит чек-лист QC и принят владельцем (**ACCEPTED**) (`:230`) | Этапы 2, 3 (`:232`) |
| **5** | Arkaim Studio как рабочее место | Страница Studio из трёх представлений; статусная модель; регенерация отдельных шотов | владелец создаёт новый ролик целиком через UI (`:239`) | Этапы 2–4 (`:241`) |
| **6** | Постоянство персонажей и качество | Утверждённые кадры как референсы (I2V / Fun InP); связка ContinuityEngine ↔ референсы | 10-шотовый ролик сохраняет внешность персонажа и палитру между соседними шотами (оценка владельца) (`:247`) | Этап 5 (`:248`) |
| **7** | Полное аудиопроизводство | Голоса персонажей; музыкальная дорожка; автоматическое сведение; опционально lip-sync | ролик с диалоговой сценой и музыкой, сведённый автоматически (`:254`) | Этап 4 (`:255`) |
| **8** | Масштабирование и альтернативные исполнители | Реестр возможностей в Studio; облачные адаптеры; возобновление работы; учёт кредитов | один и тот же шот выполняется и локально, и через облачный backend без изменения смысла задания (`:261`) | Этапы 5, 1 (`:262`) |

**Порядок строго последовательный** между этапами; первый MP4 закрывается на Этапе 4 (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:186`).

### 1.4. От чего зависит план целиком

| Зависимость | Статус | Где зафиксировано |
|---|---|---|
| OWNER-GO по O1 (утвердить план как направление) | **не дан** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:290` |
| OWNER-GO по O2 (ADR `ADR_AUDIO_PLAN_V0` — снять запрет D2) | **не дан** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:291`; `docs/ADR/ADR_MEDIA_PLAN_V0.md:60` |
| OWNER-GO по O3 (MEDIA_CONTRACT v1.0 → v1.1: audio + assemble + видео-провайдер) | **не дан** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:292`; `arkaim-media/docs/MEDIA_CONTRACT.md:144` |
| OWNER-решение по O4 (фрагмент книги для пилота) | **не дан** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:293` |
| OWNER-решение по O5 (политика расходов) | **не дан**, требуется только при нехватке локальной базы | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:294` |
| Результаты Этапа 0 (VRAM / скорость / качество) | **не выполнен** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:188-196`; `docs/PILOT_FILM_PLAN.md:243` |
| Целевое оборудование NVIDIA 8 ГБ VRAM | **отсутствует** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:139` |
| MEDIA_CONTRACT v1.0 | ACCEPTED, замёрз | `arkaim-media/docs/MEDIA_CONTRACT.md:163`; `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:144` |
| ADR_MEDIA_PLAN_V0 / ADR_ARKAIM_MEDIA_BOUNDARY | ACCEPTED | `docs/ADR/ADR_MEDIA_PLAN_V0.md:5`; `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:5` |

---

## 2. Зависимости: откуда MediaPlan берётся

### 2.1. Цепочка происхождения (проверена по коду)

```
World Model (read-only) ─┐
Геном книги (canonical) ─┼→ VisualContextBuilder → VisualContext (+ scene_extras)
VISUAL_KNOWLEDGE (JSON)  ─┘        core/CORE/visual/visual_context_builder.py:661-679
                                              │
                                              ↓  extend_visual_context (temporal / source_refs / integrity)
                                       SceneContext (canonical)
                                              │
                                              ↓  MediaPlanBuilder._build_plan
                                       MediaPlan v0  ← core/CORE/media_plan/builder.py:129-198
                                              │
                    ┌─────────────────────────┼──────────────────────────┐
                    ↓                         ↓                          ↓
             VideoScenarioBuilder   VideoContext/VideoIntelligence   Studio-экспорт
             (шоты, ритм, звук)        (движение камеры)             (артефакты)
```

| Слой | Что берётся | Где в коде |
|---|---|---|
| **World Model** | Только read-only: `wm.get_temporal_context(epoch_id)` → эпоха, границы, provenance, счётчики | `core/CORE/visual/visual_context_builder.py:703,712`; `core/CORE/narrative_engine/world_model.py:585` |
| **Геном книги** | Сцены, персонажи, локации (через `scene_engine`) | `core/CORE/visual/visual_context_builder.py:17-20`; `core/CORE/knowledge/screenplay_scene_catalog.py` |
| **VISUAL_KNOWLEDGE (JSON)** | `ATMOSPHERES`, `CAMERA_LIBRARY`, `CHARACTER_VISUALS`, `LOCATION_VISUALS`, `SHOT_LIBRARY`, `STYLE_LIBRARY`, `VIDEO_RULES`, `VISUAL_SYMBOLS` | `core/CORE/visual/VISUAL_KNOWLEDGE/`; загрузка — `core/CORE/visual/visual_context_builder.py:27,154-162` |
| **Ключевые сцены/палитры/извлечения** | `core/KNOWLEDGE/SCENE_PROMPTS.json`, `core/KNOWLEDGE/EPOCH_PALETTES.json`, `core/KNOWLEDGE/screenplay_extracts.json` | каталог `core/KNOWLEDGE/` |
| **MD-2 scene_extras** | `temporal`, `source_refs`, `integrity` — приклеиваются к VisualContext | `core/CORE/visual/scene_context.py:141` (`extend_visual_context`) |
| **MediaPlan** | Проекция SceneContext; `source_refs`/`temporal`/`provenance` наследуются 1:1 | `core/CORE/media_plan/builder.py:170,190-197` |

**Вывод для владельца:** MediaPlan не «придумывает» содержание — он проецирует уже существующий канон сцены. Новый источник знаний не требуется и не предлагается.

### 2.2. Граница Arkaim ↔ Media (что где живёт)

| Правило | Факт | Где зафиксировано |
|---|---|---|
| Arkaim = смысл, Media = исполнение | Цепочка `World Model → Temporal Context → Scene Context → {Image/Video Plan} → внешний Media Project → Execution → Asset` | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:46` |
| Ядро media-agnostic | Ни один модуль `core/CORE/` не знает о ComfyUI/workflow/node-graph/checkpoint'ах | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:106` |
| Никаких прямых `Arkaim → ComfyUI HTTP` | Интеграция только через внешний Media-контракт | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:107` |
| LLM не управляет ComfyUI | LLM — голос, не архитектура | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:108` |
| Scene Context — единственный источник истины для всех планов | Новые генераторы строятся от контекста, не параллельно ему | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:111` |
| Temporal-модель не меняется ради media | MediaPlan потребляет temporal read-only | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:112` |
| MediaPlan ≠ Workflow ≠ Provider | Разделение понятий зафиксировано словарём | `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:63-72` |
| Контракт меняется только с owner-GO | Любые новые поля/эндпоинты — ADR + owner-GO | `arkaim-media/docs/MEDIA_CONTRACT.md:144` |
| Граница закреплена тестом | 5 классов проверок | `runtime/tests/test_media_boundary.py:39,99,129,219,250` |

### 2.3. Мост Arkaim → Media (единственная точка выхода)

| Аспект | Факт | Где |
|---|---|---|
| Класс | `MediaClient` — временный мост, помечен «REMOVE IN MD-5» | `runtime/core/media_client.py:1,50` |
| Адрес по умолчанию | `http://127.0.0.1:8200`, переопределяется env `MEDIA_BACKEND_URL` | `runtime/core/media_client.py:66,165` |
| Таймаут | 620 с (видео ≤ 600 с по контракту §4 + запас) | `runtime/core/media_client.py:161-166` |
| Регистрация в DI | `media_client` зарегистрирован **безусловно**; при отсутствии сервиса вызов падает `media_backend_unreachable` | `runtime/core/adc_deps.py:97-107,234`; `runtime/core/media_client.py:296-299` |
| Тело запроса | `{plan: <минимальный MediaPlan>, execution: {media_kind, size, preferred_backend}}`; для видео — `duration_sec`, `fps`, опционально `input_image` | `runtime/core/media_client.py:318-365` |
| Ответ | `media_id`, `backend`, `workflow_used`, байты | `runtime/core/media_client.py:138-148,310-316` |
| Словарь backend | `auto \| comfyui \| comfy \| mock \| fallback \| agnes` | `runtime/core/media_client.py:124-131` |

### 2.4. Что запрещено и чего нет

| Ограничение | Факт | Где |
|---|---|---|
| Audio вне контракта v1 | `audio` — extension point без реализации; в `§8` контракта перечислен как сознательное исключение | `arkaim-media/docs/MEDIA_CONTRACT.md:113,148`; `docs/ADR/ADR_MEDIA_PLAN_V0.md:60` |
| Сборка (assemble) вне контракта v1 | «Film Studio-сборка в Media» — сознательное исключение v1 | `arkaim-media/docs/MEDIA_CONTRACT.md:148` |
| `shot_assembler` — migration debt | Читает файлы по сырым путям в общем `data/`; D-2 «не чинить в MD-4» | `arkaim-media/docs/MEDIA_CONTRACT.md:136,155` |
| Нет механизма очереди/заданий | `GenerationQueue`, `AssetGenerationPipeline` не регистрируются в DI; тест требует их отсутствия | `runtime/core/adc_deps.py:76,85,110`; `runtime/tests/test_media_boundary.py:117-123` |
| Async нет | `/v1/generate` синхронный; async — только при превышении таймаута, и это контрактное решение владельца | `docs/MEDIA_EXECUTORS_SPEC.md:351,362-364` |

---

## 3. Ожидаемый результат: артефакты, файлы, эндпоинты

### 3.1. Что производит MediaPlan

| Артефакт | Форма | Где рождается | Куда попадает |
|---|---|---|---|
| `MediaPlan` (image) | JSON: `plan_id` (`plan_<hex12>`), `plan_version` 0.1.0, `media_kind`, `intent`, `prompt`, `structured_prompt`, `negative_constraints`, `characters[]`, `location`, `visual_style`, `atmosphere`, `camera`, `constraints[]`, `source_refs`, `temporal_context`, `provenance[]`, `lineage` | `core/CORE/media_plan/builder.py:177-198` | в JSON-ответе API (`/book/visualize`, `/book/assets/generate-context`, `/book/studio-describe`) |
| `MediaPlan` (video) | то же + `duration_sec`, `fps`, `sequence[]` (ShotPlan), `motion` (MotionPlan), `temporal_consistency` (ContinuityRef) | `core/CORE/media_plan/builder.py:105-125` | там же |
| JSON-схема контракта | draft-07 | — | `SCHEMAS/MEDIA_PLAN.schema.json` |
| `VideoScenario` | `SCENARIO_VERSION = "0.1.0"`; шоты, ритм, `sound_design`, provenance | `core/CORE/studio/scenario_schemas.py`; сборка — `core/CORE/studio/scenario_builder.py` | `video_scenario` в ответах Studio |

### 3.2. Файлы и хранилища (фактические)

| Хранилище | Что лежит | Код |
|---|---|---|
| `data/studio.db` | `studio_sessions`, `studio_messages`, `studio_versions`, `studio_references`, `studio_art_direction`, `studio_prepared_updates`, `studio_continuity_decisions` | `core/CORE/studio/store.py:35,75-143` |
| `data/film_studio.db` | `film_projects`, `film_scenes`, `film_shots` | `core/CORE/film_studio/store.py:17-18,53-101` |
| `data/visual_assets.db` | метаданные ассетов (`media_id`, lineage, provenance, `generation.plan_id`, `shot_id`, `reference_image_id`, `input_image_sha256`) | `core/CORE/visual_assets/storage.py` |
| `data/visual_assets/` | файлы кадров и клипов | `core/CORE/film_studio/shot_assembler.py:36-52`; `runtime/core/routes/studio.py:2441,2495` |
| `data/film_output/<project_id>/output.mp4` | собранное видео | `core/CORE/film_studio/shot_assembler.py:17-18,83-86` |

**Факт по фактическим MP4 на диске (замер ffprobe, 2026-10-22):** в `data/film_output/` лежат 5 файлов `output.mp4` — все **1920×1080, 24 fps, h264, длительность 7–30 с, аудиодорожки нет**. Это подтверждает: сборщик кода работает, но озвучки/субтитров в нём нет (пробел G9, `docs/MEDIA_PRODUCTION_MASTERPLAN.md:66`). Каталог `data/` не в git (`.gitignore:77`).

### 3.3. Эндпоинты (фактические)

**Studio — 44 роута** (`runtime/core/routes/studio.py`, префикс `/studio/*`); ключевые для производства:

| Метод | Путь | Что делает | Код |
|---|---|---|---|
| GET | `/studio/{session_id}/export` | Финальный экспорт: `export_id`, `image_description`, `video_description`, `video_scenario`, `references[]`, `version_lineage[]`. Требует статус сессии `approved` | `runtime/core/routes/studio.py:3205-3263` |
| POST | `/studio/{session_id}/prepared-updates` | **Черновик производственного пакета без генерации**: итоговый промпт/негатив (resolve_shot), снимок применённых правил, референсы, выбранный исполнитель | `runtime/core/routes/studio.py:1722-1809` |
| GET | `/studio/{session_id}/prepared-updates` | Список подготовленных заданий | `runtime/core/routes/studio.py:1820` |
| PATCH | `/studio/{session_id}/prepared-updates/{prepared_id}` | Продвижение статуса задания | `runtime/core/routes/studio.py:1840` |
| POST | `/studio/{session_id}/prepared-updates/{prepared_id}/approve` | Утверждение задания шотом | `runtime/core/routes/studio.py:1873` |
| POST | `/studio/image-jobs` | Задание на изображение: ассет `generating` → фоном `MediaClient` → `completed`/`failed`; ответ сразу с `asset_id` | `runtime/core/routes/studio.py:2599-2657`, исполнитель `:2470-2506` |
| POST | `/studio/video-jobs` | Задание на видео; опционально `image_asset_id` = i2v (кадр → байты → `execution.input_image`) | `runtime/core/routes/studio.py:2509-2593`, исполнитель `:2370-2467` |
| POST | `/studio/{session_id}/approve-image` | Утверждение кадра (только `image` + `status=completed`) | `runtime/core/routes/studio.py:2663-2696` |
| GET | `/studio/reel` | Лента фильма: Эпизод → Сцена → План → Кадр → Клип (read-only) | `runtime/core/routes/studio.py:627`; `core/CORE/studio/reel.py:1-22` |
| GET | `/studio/sequence` | Режиссёрский план сборки: тайминги, разрывы, переходы, сводка по исполнителям (read-only, **не монтаж**) | `runtime/core/routes/studio.py:654`; `core/CORE/studio/sequence.py:1-20` |
| GET/PUT | `/studio/art-direction` | Общие правила фильма (стиль, палитра, персонажи, локации, композиция, свет) | `runtime/core/routes/studio.py:1325,1337`; `core/CORE/studio/art_direction.py:1-19` |
| GET | `/studio/scenes/{scene_id}/continuity` | Связность соседних сцен/шотов | `runtime/core/routes/studio.py:844`; `core/CORE/studio/continuity.py:1-27` |

**Film Studio — 15 роутов** (`runtime/core/routes/film_studio.py`, префикс `/book/film/*`):

| Метод | Путь | Что делает | Код |
|---|---|---|---|
| POST | `/book/film/create` | Создать проект фильма | `runtime/core/routes/film_studio.py:36` |
| POST | `/book/film/{project_id}/scenes/{scene_db_id}/shots` | Добавить шот (prompt, duration, camera) | `runtime/core/routes/film_studio.py:195` |
| POST | `.../shots/new-version` | Новая версия шота | `runtime/core/routes/film_studio.py:229` |
| PUT | `/book/film/shots/{shot_id}` | Обновить шот (в т.ч. `quality`: draft\|standard\|high\|ultra) | `runtime/core/routes/film_studio.py:277` |
| GET | `/book/film/{project_id}/output` | Скачать собранное видео — **всегда 404**, если `output_path` не задан: «assemble the project in the external media project first» | `runtime/core/routes/film_studio.py:116-130` |

**Пробелы в API (факт):** маршрута `/book/film/*/assemble` нет — его отсутствие **закреплено тестом** (`runtime/tests/test_media_boundary.py:88-90`). `ShotAssembler` вызывается только из тестов и ручных прогонов.

### 3.4. Фронтенд (фактическое состояние)

| Факт | Где |
|---|---|
| Страница Studio существует: 19 файлов в `arkaim-web/src/app/studio/` | `arkaim-web/src/app/studio/page.tsx` и др. |
| Production-вызовы идут на существующие роуты: `POST /api/studio/image-jobs` | `arkaim-web/src/app/studio/image-panel.tsx:72`; `arkaim-web/src/app/studio/affected-panel.tsx:653` |
| `POST /api/studio/video-jobs` | `arkaim-web/src/app/studio/video-panel.tsx:218`; `arkaim-web/src/app/studio/story-reel.tsx:435` |
| 11 unit-тестов Studio во фронтенде | `arkaim-web/tests/unit/studio-*.test.tsx` (11 файлов) |

---

## 4. Доступные исполнители — реальный список

### 4.1. Кто реально подключён в коде

**Источник истины — цепочки провайдеров соседнего репозитория** `arkaim-media/media/server.py:98-117` (репозиторий `C:\proect_arkaim\arkaim-media`, отдельный, HEAD `f0327cd`):

| media_kind | preferred_backend | Провайдер | Файл | Стоимость | Статус |
|---|---|---|---|---|---|
| image | `comfyui` | `ComfyUIProvider` (SD-checkpoint, `workflows/default.json`) | `arkaim-media/media/image/comfyui.py` | локально, $0 | рабочий |
| image | `mock` | `MockImageProvider` | `arkaim-media/media/image/mock.py` | тестовые ответы | рабочий |
| image | `agnes` | `ComfyUIProvider` с шаблоном `workflows/agnes_image.json` (граф `AgnesImage → SaveImage`) | `arkaim-media/media/image/comfyui.py`; `arkaim-media/workflows/agnes_image.json` | **free**, кредитов нет | рабочий, проверен 2026-10-14 |
| video | `auto` | `ImageSequenceVideoProvider` (кадры → ffmpeg) | `arkaim-media/media/video/image_sequence.py` | локально, $0 | рабочий |
| video | `mock` | `MockVideoProvider` | `arkaim-media/media/video/mock.py` | тестовые ответы | рабочий |
| video | `comfyicu` | `ComfyICUProvider` — облачный API, workflow LTX 2.5 I2V (50 узлов) | `arkaim-media/media/video/comfyicu.py`; `arkaim-media/workflows/comfyicu_ltx25_i2v.json` | **платный, цена в репозитории не указана** | рабочий, но **код не закоммичен** |

Словари выбора: `_BACKENDS_IMAGE = {"comfyui": 0, "mock": 1, "agnes": 2}`, `_BACKENDS_VIDEO = {"mock": 1, "comfyicu": 2}` — `arkaim-media/media/server.py:116-117`. `image_sequence` по имени не выбирается (только auto-путь).

**Что НЕ подключено нигде:** Wan 2.1 T2V (видео-провайдера нет — `docs/MEDIA_EXECUTORS_SPEC.md:394`), Silero TTS / любой TTS (`docs/MEDIA_EXECUTORS_SPEC.md:395`), assemble по контракту (`docs/MEDIA_EXECUTORS_SPEC.md:396`), Runway / RunComfy / Comfy Router (только в реестре как `optional`, `docs/MEDIA_EXECUTORS_SPEC.md:134-136`).

### 4.2. Справочники исполнителей в самом Arkaim

| Справочник | Значения | Где |
|---|---|---|
| `IMAGE_EXECUTORS` (бэкенд) | `mock`, `agnes`, `auto` | `core/CORE/studio/prepared_updates.py:34-62` |
| `IMAGE_EXECUTORS` (фронтенд) | `agnes`, `mock`, `auto` | `arkaim-web/src/app/studio/types.ts:326-330` |
| `VIDEO_EXECUTORS` (фронтенд) | `mock`, `auto`, `comfyicu` («облачный LTX 2.5 (кредиты)») | `arkaim-web/src/app/studio/types.ts:332-336` |
| `VIDEO_SIZES` (фронтенд) | `1024x576`, `576x1024`, `1024x1024` | `arkaim-web/src/app/studio/types.ts:339-343` |
| Словарь моста | `auto`, `comfyui`, `comfy`, `mock`, `fallback`, `agnes` | `runtime/core/media_client.py:124-131` |

**Расхождение, требующее внимания:** бэкенд-справочник изображений (`core/CORE/studio/prepared_updates.py:34-62`) содержит `agnes`, но **не содержит `comfyui`**, хотя провайдер `comfyui` в цепочке arkaim-media есть и в мосте есть (`runtime/core/media_client.py:127`). То есть выбор «локальный ComfyUI SD» через Studio-сценарий сейчас недоступен.

### 4.3. Реальные ограничения исполнителей

| Исполнитель | Ограничение | Где зафиксировано |
|---|---|---|
| Все | Таймаут моста 620 с; ComfyICU — 600 с по контракту §4 | `runtime/core/media_client.py:161-166`; `arkaim-media/media/video/comfyicu.py:14` |
| ComfyUI (локальный) | URL `http://127.0.0.1:8188`; шаблоны — только в `arkaim-media/workflows/` (аркаимские `core/GENOME/workflows` не используются) | `arkaim-media/media/config.py:20-26` |
| ComfyUI (фактическое железо) | AMD Radeon RX 570, **4 ГБ**; PyTorch 2.12.1 **+cpu** (CUDA нет); ComfyUI 0.34.5 в режиме `--cpu`, порт 8188 | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:139-141` |
| **Wan 2.1 T2V (целевая основа)** | Локально **не выполняется**: нет NVIDIA, 4 ГБ < 8 ГБ. Официальный ориентир: 1.3B T2V требует **8 ГБ VRAM** | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:142`; `docs/MEDIA_EXECUTORS_SPEC.md:46` |
| Wan 2.1 (модели) | Диффузия `wan2.1_t2v_1.3B_fp16.safetensors`; `umt5_xxl` (fp8 ~4.9 ГБ / fp16 9.8 ГБ — для 8 ГБ брать fp8); `wan_2.1_vae` | `docs/MEDIA_EXECUTORS_SPEC.md:50-55` |
| Wan 2.1 (режим) | `text_to_video_wan` — только T2V; **I2V требует отдельной модели 14B** (тяжёлая) | `docs/MEDIA_EXECUTORS_SPEC.md:57` |
| Agnes | Только text2img; **negative не поддерживается** (отбрасывается с warning); запрошенный WxH **не гарантируется** (маппинг приближённый, отклонение >5% → warning); локальный GPU не требуется; seed = `hash(prompt)` (недетерминирован между процессами) | `docs/MEDIA_EXECUTORS_SPEC.md:150,155`; `arkaim-media/media/server.py:93-96` |
| ComfyICU | Конфигурация **только env**: `COMFYICU_API_KEY`, `COMFYIU_WORKFLOW_ID`, опционально `COMFYICU_INPUT_IMAGE`; workflow LTX 2.5 I2V — шаблон 50 узлов; `size` **не инжектится** (шаблон 16:9, отклонение >5% → warning); таймаут 600 с; их CDN отдаёт ~1–2 КБ/с → файл собирается параллельными Range-чанками | `arkaim-media/media/video/comfyicu.py:6-18,30-33,50-52` |
| ComfyICU (состояние в git) | Файл `media/video/comfyicu.py` — **uncommitted** (`git status` arkaim-media: `?? media/video/comfyicu.py`); также не закоммичены `workflows/comfyicu_ltx25_i2v.json`, `workflows/agnes_image.json` | `git -C ../arkaim-media status` |
| Сборка (assemble) | Требуется установленный **ffmpeg**; проверяется `shutil.which("ffmpeg")` → ошибка «ffmpeg не установлен» | `docs/MEDIA_EXECUTORS_SPEC.md:44`; `core/CORE/film_studio/shot_assembler.py:107-109` |
| Сборка (возможности) | Сейчас: ffmpeg concat + Ken Burns. **Нет**: аудиомикса, субтитров, титров | `core/CORE/film_studio/shot_assembler.py:1,132-194,206-269`; `docs/MEDIA_EXECUTORS_SPEC.md:292-299` |
| Silero TTS (планируемый) | Лицензия моделей **CC BY-NC (некоммерческая)**; пакет MIT; альтернатива `v5_cis_base` — MIT; до 5 голосов, 8/24/48 кГц | `docs/MEDIA_EXECUTORS_SPEC.md:232-245` |
| Облачный TTS (опция) | Runway `eleven_multilingual_v2` — 1 кредит / 50 символов; ElevenLabs — varies; Piper rus-medium — free (локально, качество ниже) | `docs/MEDIA_EXECUTORS_SPEC.md:257-263` |
| Облачные видео-API (опция) | Runway Dev, RunComfy, Comfy Router — только `optional` в реестре; подключены быть не могут без O5 | `docs/MEDIA_EXECUTORS_SPEC.md:134-136,182-218` |
| Лёгкие альтернативы Wan | LTX-Video, Stable Video Diffusion, AnimateDiff — «проверить в Этапе 0», не подключены | `docs/MEDIA_EXECUTORS_SPEC.md:220-226` |

### 4.4. Правила выбора и фолбэка (уже зафиксированы)

| Правило | Факт | Где |
|---|---|---|
| Переключение — только между исполнителями, реально поддерживающими `media_kind` | Запрещено молча подставлять несовместимый | `docs/MEDIA_EXECUTORS_SPEC.md:329` |
| Изменение качества/скорости/стоимости показывается пользователю | Обязательное условие | `docs/MEDIA_EXECUTORS_SPEC.md:330` |
| Авто-фолбэк на платный backend запрещён без O5 | Платные вызовы — только по явной политике | `docs/MEDIA_EXECUTORS_SPEC.md:331`; `docs/MEDIA_PRODUCTION_MASTERPLAN.md:294` |
| Записи `discovering` в выборе не участвуют | Реестр: `available`/`unavailable`/`degraded`/`discovering` | `docs/MEDIA_EXECUTORS_SPEC.md:122,157,332` |
| Нет подходящего исполнителя → «исполнитель недоступен», без фиктивного результата | Уровень 4 фолбэка | `docs/MEDIA_EXECUTORS_SPEC.md:325,333` |
| Уровни фолбэка | 1) локальный ComfyUI Wan2.1 → 2) иной локальный workflow → 3) удалённый/облачный (по O5) → 4) «исполнитель недоступен» | `docs/MEDIA_EXECUTORS_SPEC.md:318-325` |

---

## 5. Стоимость

### 5.1. Что репозиторий говорит прямо

| Параметр | Значение | Где зафиксировано |
|---|---|---|
| Локальная основа | `cost = {"type": "local", "credits_per_second": 0}` — денег не стоит, стоит время | `docs/MEDIA_EXECUTORS_SPEC.md:121` |
| Agnes (image) | `{"type": "free", "credits": 0}` — «Free. No token billing, no credit system» (README пакета, проверено 2026-10-14) | `docs/MEDIA_EXECUTORS_SPEC.md:152` |
| Время Этапа 0 | **~2–4 ч** (установка + замер) | `docs/PILOT_FILM_PLAN.md:208` |
| Время Этапов 1–4 | **TBD после Этапа 0** (зависит от скорости генерации) | `docs/PILOT_FILM_PLAN.md:209` |
| Время разработки | не обещается | `docs/PILOT_FILM_PLAN.md:211` |
| Runway Dev (если понадобится) | 1 кредит = $0.01; kling 3.0 ~13 cr/s (~$0.13/s); wan3 (720p) ~10 cr/s (~$0.10/s); veo3.1_fast ~10 cr/s (~$0.10/s); TTS `eleven_multilingual_v2` — 1 cr / 50 символов. Дата проверки 2026-10-14 | `docs/MEDIA_EXECUTORS_SPEC.md:186-198` |
| RunComfy / Comfy Router | «Pay-per-request» — конкретной цены нет | `docs/MEDIA_EXECUTORS_SPEC.md:200-218` |
| Облачный TTS (опция) | Runway 1 cr/50 симв.; ElevenLabs — varies; Piper — free (локально) | `docs/MEDIA_EXECUTORS_SPEC.md:257-263` |
| Локальный TTS Silero | $0, но лицензия CC BY-NC | `docs/MEDIA_EXECUTORS_SPEC.md:241-245` |
| Ориентиры O5 в masterplan | «Runway Dev 1 кредит = $0.01, Kling 3.0 ~9–17 кр/с, Wan3 ~5–20 кр/с, Veo3.1-fast 10–15 кр/с (проверено 2026-10-14)» | `docs/MEDIA_PRODUCTION_MASTERPLAN.md:294` |

### 5.2. Чего в репозитории НЕТ (важно для решения)

| Вопрос | Ответ |
|---|---|
| Сколько стоит пилот целиком (в рублях или долларах)? | **В репозитории не указано.** Ни в одном документе нет сметы пилота в деньгах. |
| Сколько стоит ComfyICU (единственный реально подключённый платный видео-исполнитель)? | **В репозитории не указано.** Поиск по `arkaim-media/docs/*.md` не находит ни упоминаний кредитов, ни цен. |
| Сколько стоит локальный Wan 2.1? | Денег — 0. Время — **неизвестно**: Этап 0 не выполнен, время клипа не измерено (`docs/PILOT_FILM_PLAN.md:211`). |
| Есть ли смета разработки Этапов 1–4? | **Нет** — «TBD после Этапа 0» (`docs/PILOT_FILM_PLAN.md:209`). |
| Есть ли разбивка по этапам в человеко-часах? | **Нет.** Единственная цифра — «~2–4 ч» на Этап 0 (`docs/PILOT_FILM_PLAN.md:208`). |

### 5.3. Расхождение в цифрах, которое надо свести

| Модель | masterplan O5 (`:294`) | MEDIA_EXECUTORS_SPEC §4.1 (`:188-196`) | Расхождение |
|---|---|---|---|
| Kling 3.0 | ~9–17 кр/с | ~13 cr/s (~$0.13/s) | диапазон vs точка |
| Wan3 (720p) | ~5–20 кр/с | ~10 cr/s (~$0.10/s) | диапазон vs точка |
| Veo 3.1 fast | 10–15 кр/с | ~10 cr/s (~$0.10/s) | диапазон vs точка |

Оба документа датированы 2026-10-14. Источник истины для расходов должен быть один — иначе «предварительные ориентиры» нельзя использовать в решении.

### 5.4. Что надо измерить, прежде чем называть стоимость

Протокол Этапа 0 — уже описан, надо его заполнить (`docs/PILOT_FILM_PLAN.md:37-45,54-64`):

| Параметр | Критерий «хорошо» | Инструмент |
|---|---|---|
| ComfyUI запускается, модели загружены | Нет ошибок | `GET /system_stats` |
| Wan2.1 T2V 1.3B даёт клип 480p | Клип ~5 с, без артефактов | workflow `text_to_video_wan` |
| Пик VRAM | ≤ 8 ГБ, без OOM | `nvidia-smi` |
| Время генерации клипа | ≤ 620 с (таймаут MediaClient) | замер от submit до готовности |
| Silero TTS | WAV чистый, текст разборчив | v5_ru, 48 кГц |
| ffmpeg | Есть | `ffmpeg -version` |
| Качество | оценка 1–5 | владелец |
| Размер файлов моделей | фиксировать при скачивании | `docs/MEDIA_EXECUTORS_SPEC.md:46` |

**Отдельно нужно замерить (нет ни в одном документе):** сколько стоит один прогон ComfyICU в кредитах/деньгах, и сколько прогонов требуется на 6–10 шотов пилота. Без этой цифры решение O5 принимать не на чем.

---

## 6. Критерии приёмки

### 6.1. Критерии УТВЕРЖДЕНИЯ плана (что должно быть верно, чтобы владелец сказал «да»)

| # | Критерий | Как проверяется | Тип проверки | Статус на 2026-10-22 |
|---|---|---|---|---|
| A1 | MediaPlan не содержит ни одного запрещённого execution-поля | `verify_no_execution_fields()` + `SCHEMAS/MEDIA_PLAN.schema.json` | **механическая** (`core/CORE/media_plan/schemas.py:191-196,218`; `runtime/tests/test_md3_media_plan.py`) | ✅ выполнено |
| A2 | Граница Arkaim ↔ Media соблюдена: нет прямых вызовов ComfyUI, нет execution-DI, нет запрещённых роутов | `runtime/tests/test_media_boundary.py` (5 классов) | **механическая** (`:39,99,129,219,250`) | ✅ выполнено |
| A3 | Подготовка кадра не запускает генерацию (черновик ≠ производство) | `POST /studio/{id}/prepared-updates` → `status=prepared` | **механическая** (`runtime/core/routes/studio.py:1722-1809`; `runtime/tests/test_studio_prepared_updates.py`) | ✅ выполнено |
| A4 | Подготовка задаётся по существующим правилам фильма, а не отдельным промпт-стеком | `resolve_shot()` от `FilmArtDirection` + `VISUAL_KNOWLEDGE` | **механическая** (`runtime/core/routes/studio.py:1777-1786`) | ✅ выполнено |
| A5 | Происхождение плана прослеживается до источника | `provenance[]`, `source_refs`, `lineage.parent_plan_id` | **механическая** (`core/CORE/media_plan/schemas.py:48-65,160-165`) | ✅ выполнено |
| A6 | Заказы выполняются в разумный срок и статус виден | Image/Video job → `generating` → `completed`/`failed` + текст ошибки | **механическая** (`runtime/tests/test_studio_image_job.py`, `test_studio_video_job.py`, `test_studio_video_i2v.py`) | ✅ выполнено |
| A7 | Лента и план последовательности не выдумывают порядок | `core/CORE/studio/reel.py`, `sequence.py` (чистые модули) | **механическая** (`runtime/tests/test_studio_reel.py`, `test_studio_sequence.py`) | ✅ выполнено |
| A8 | Связность сцен считается, а не выдумывается | `core/CORE/studio/continuity.py` | **механическая** (`runtime/tests/test_studio_continuity.py`, `test_studio_art_direction.py`) | ✅ выполнено |
| A9 | Фронтенд не вызывает несуществующие адреса | vitest + ручной проход | **механическая** (`arkaim-web/tests/unit/studio-*.test.tsx`) | ✅ выполнено (расхождений в живом коде нет — §9) |
| A10 | Утверждение не создаёт второго источника знаний и не уводит ядро в медиа | инварианты 1–8 ADR + тест границы | **механическая** (`docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:106-113`) | ✅ выполнено |
| A11 | Реалистичность аппаратной базы (NVIDIA 8 ГБ) | наличие железа у владельца | **человеческое решение** | ❌ не решено |
| A12 | Реалистичность плана озвучки с учётом лицензии | выбор Silero `v5_ru` (CC BY-NC) vs `v5_cis_base` (MIT) vs облако | **человеческое решение** | ❌ не решено |
| A13 | План озвучки легален (ADR на AudioPlan) | наличие `ADR_AUDIO_PLAN_V0` | **человеческое решение** (O2) | ❌ не решено |
| A14 | Стоимость пилота укладывается в бюджет владельца | смета, которой в репозитории нет (§5.2) | **человеческое решение** (O5) | ❌ не решено |
| A15 | Оценка «а это вообще нужно?» | выбор фрагмента книги (O4) | **человеческое решение** | ❌ не решено |

### 6.2. Критерии ПРИЁМКИ пилота (из `docs/PILOT_FILM_PLAN.md`)

Формальная цель пилота: **MP4 60–90 с, 6–10 шотов, русская озвучка, звуковая атмосфера, титры/субтитры, 480p, принятый владельцем (ACCEPTED)** — `docs/PILOT_FILM_PLAN.md:23`.

**6.2.1. Технические проверки — частично механические**

| Проверка | Критерий | Инструмент | Тип | Готово ли в репозитории |
|---|---|---|---|---|
| Разрешение | 480p (например, 832×480) | `ffprobe` | механическая | инструмент есть; **скрипта QC в репозитории нет** |
| fps | 16 (стандарт Wan2.1) или agreed | `ffprobe` | механическая | то же |
| Длительность | 60–90 с | `ffprobe` | механическая | то же |
| Аудиодорожки | WAV, 48 кГц | `ffprobe` | механическая | то же |
| Субтитры | SRT синхронизирован | Просмотр | **человеческая** | — |
| Размер файла | < 500 МБ | filesystem | механическая | то же |

Источник: `docs/PILOT_FILM_PLAN.md:154-163`. **Вывод:** техническая часть QC сводится к одной команде `ffprobe`, но готового скрипта/теста в репозитории нет — это небольшая задача, которую можно выполнить после Этапа 0.

**6.2.2. Субъективные проверки — только человек**

| Проверка | Критерий | Источник |
|---|---|---|
| Визуал | Нет заметных артефактов; стиль/палитра соответствуют эпохе | `docs/PILOT_FILM_PLAN.md:167-169` |
| Персонажи | Внешность узнаваема между шотами (ContinuityEngine) | `:170` |
| Камера | Движения плавные, без «плясок» | `:171` |
| Озвучка | Текст разборчивый, ритм естественный, нет обрывов | `:172` |
| Атмосфера | Фон не перекрывает диктора; громкости сбалансированы | `:173` |
| Титры/субтитры | Читаемы, синхронизированы | `:174` |
| Целостность | Фильм «складывается», нет ощущения набора клипов | `:175` |
| Соответствие книге | Каждая сцена/реплика ссылается на главу; локации/персонажи соответствуют VISUAL_KNOWLEDGE; текст не искажает замысел автора (IdentityLayer.validate) | `:177-183` |

**6.2.3. Формальные критерии приёмки пилота (6 пунктов)**

| # | Критерий | Тип |
|---|---|---|
| 1 | MP4 готов (60–90 с, 480p, озвучка, атмосфера, титры/субтитры) | смешанный |
| 2 | QC пройден (§5: технические + субъективные + provenance) | смешанный |
| 3 | Владелец принял (status: **ACCEPTED**) | **человеческая** |
| 4 | Протокол Этапа 0 заполнен (реальные VRAM/скорость/качество) | **человеческая** (заполняется владельцем: качество 1–5) |
| 5 | Нет нарушений границы (Arkaim не вызывает ComfyUI напрямую; assemble — на media-стороне) | **механическая** (`runtime/tests/test_media_boundary.py`) |
| 6 | Воспроизводимо: lineage полный (книга → сценарий → планы → клипы → MP4) | **механическая** (`provenance`/`lineage` в `core/CORE/media_plan/schemas.py:48-65,160-165`) |

Источник: `docs/PILOT_FILM_PLAN.md:228-235`.

**6.2.4. Критерии готовности Этапа 2 (производственный контур)** — `docs/MEDIA_EXECUTORS_SPEC.md:381-387`:

| # | Критерий | Тип |
|---|---|---|
| 1 | Видео-провайдер Wan работает: шот → MediaPlan → ComfyUI → MP4 → `media_id` | механическая |
| 2 | Статус задания виден (`completed`/`failed` + текст ошибки) | механическая |
| 3 | Реестр показывает статус backend | механическая |
| 4 | Фолбэк на `image_sequence` работает | механическая |
| 5 | Нет прямых вызовов ComfyUI из Arkaim | механическая (тест границы) |

---

## 7. Что остаётся за пределами

| # | За пределами | Факт и где зафиксировано |
|---|---|---|
| 1 | **Новый источник знаний** | MediaPlan = проекция существующего SceneContext, а не новый источник: `docs/ADR/ADR_MEDIA_PLAN_V0.md:25`; `core/CORE/media_plan/builder.py:129-198`. Данные берутся из генома, World Model и `VISUAL_KNOWLEDGE` — ничего нового не заводится |
| 2 | **Знание об исполнителях внутри домена** | Execution-поля (model/steps/seed/workflow/provider/backend) запрещены в MediaPlan: `core/CORE/media_plan/schemas.py:191-196`; инвариант 5 ADR: `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:110` |
| 3 | **Генерация медиа в ядре знаний** | Инвариант 1: `core/CORE/` не знает о ComfyUI/workflow/node-graph — `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:106`. Закреплено тестом `runtime/tests/test_media_boundary.py:219-244` (провайдеры — заглушки) |
| 4 | **Локальный исполнитель в Arkaim** | `image_provider`, `video_provider`, `generation_pipeline`, `generation_queue` не регистрируются: `runtime/core/adc_deps.py:76,85,110`; `runtime/tests/test_media_boundary.py:109-123` |
| 5 | **Прямые вызовы ComfyUI из Arkaim** | Запрещено: `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md:107`; единственная точка выхода — `POST /v1/generate` через `MediaClient` |
| 6 | **Автономное производство** | Подготовка ≠ генерация: `POST /studio/{id}/prepared-updates` создаёт черновик, запуск — только отдельной командой `POST /studio/image-jobs` (`runtime/core/routes/studio.py:1728-1734`). Тот же принцип в `docs/ARKAIM_STUDIO_SPEC.md:51-52` |
| 7 | **Автономная публикация/рассылка** | В репозитории **нет ни одного** эндпоинта публикации или рассылки медиа (поиск по `runtime/core/routes/` — совпадений нет). Медиа остаётся локальным артефактом |
| 8 | **Озвучка без решения владельца** | `media_kind=audio` — extension point; схема AudioPlan не определена; вне scope MD-3: `core/CORE/media_plan/schemas.py:36-46`; `docs/ADR/ADR_MEDIA_PLAN_V0.md:60`; `arkaim-media/docs/MEDIA_CONTRACT.md:148` |
| 9 | **Сборка внутри контракта v1** | «Film Studio-сборка в Media» — сознательное исключение v1: `arkaim-media/docs/MEDIA_CONTRACT.md:148`; `shot_assembler` — migration debt D-2: `:136,155` |
| 10 | **Слияние Film Studio и Studio** | Базы и роуты не сливаются: `docs/STUDIO_BOUNDARIES.md:34-39` |
| 11 | **Автоматический фолбэк на платного исполнителя** | Запрещён без O5: `docs/MEDIA_EXECUTORS_SPEC.md:331` |
| 12 | **Публикация результата без утверждения владельцем** | Сессия должна быть в статусе `approved`, иначе экспорт возвращает 409: `runtime/core/routes/studio.py:3218-3219` |

---

## 8. Что нужно от владельца

**Ниже — только решения, которые не может принять инженер.** Ни одно из них не принято в этом документе. Для каждого указаны варианты и последствия; ответ можно дать одной строкой на пункт.

### 8.1. Решения, уже сформулированные в masterplan (O1–O5)

| # | Решение | Варианты | Что получится |
|---|---|---|---|
| **O1** | Утвердить генеральный план как направление | (a) утвердить · (b) отклонить · (c) утвердить с правками | (a) — этапы 0–8 получают легитимность; (b) — план остаётся PROPOSED, работа не начинается; (c) — нужны ваши правки по тексту плана |
| **O2** | GO на новый `ADR_AUDIO_PLAN_V0` (официальный пересмотр запрета D2) | (a) GO · (b) отказ до коммерческого запуска | (a) — озвучка легальна, открывается Этап 3; (b) — Этап 3 заблокирован, пилот возможен только без звука |
| **O3** | GO на эволюцию MEDIA_CONTRACT v1.0 → v1.1 (audio + видео-провайдер Wan + `POST /v1/assemble`) | (a) GO · (b) частичный GO (только assemble) · (c) отказ | (a) — film-цепочка замыкается по контракту; (b) — сборка разрешена, озвучка нет; (c) — пилот собирается вручную либо нарушается границу |
| **O4** | Выбрать фрагмент книги для первого пилота | (a) предложить 2–3 варианта из `core/KNOWLEDGE/SCENE_PROMPTS.json` на выбор · (b) назвать свой | (a) — выбираете из подготовленного; (b) — берёте любой свой фрагмент |
| **O5** | Решение о расходах | (a) не тратить (только локальная база + бесплатный Agnes) · (b) разрешить платный исполнитель с лимитом · (c) отложить | (a) — блокирует видео-часть без NVIDIA 8 ГБ; (b) — открывает ComfyICU/облако, нужна цена (§5.4); (c) — Этап 0 остаётся единственной допустимой активностью |

### 8.2. Дополнительные решения, обнаруженные при сверке 2026-10-22

| # | Решение | Почему нужно от вас | Варианты |
|---|---|---|---|
| **N1** | Целевое оборудование: покупать / арендовать / не покупать NVIDIA 8 ГБ | Без него Wan 2.1 локально не выполняется (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:142`), а видео-этапы 2–4 на этом зависают | (a) приобрести · (b) арендовать на время пилота · (c) не приобретать → работать через облако по O5 |
| **N2** | ComfyICU: допустим ли платный облачный видео-исполнитель и с каким лимитом | Это **единственный** реально подключённый видео-исполнитель, и его цена в репозитории **не указана** (§5.2). Без цифры O5 принимать не на чём | (a) разрешить с лимитом N кредитов на пилот · (b) не разрешать до появления цены · (c) запретить |
| **N3** | Лицензия Silero (CC BY-NC) | `v5_ru` некоммерческая (`docs/MEDIA_EXECUTORS_SPEC.md:241`). Для пилота ОК, для коммерческого проекта — нет | (a) `v5_cis_base` (MIT) · (b) облачный TTS · (c) купить лицензию · (d) не влияет на пилот |
| **N4** | Где живёт финальная сборка: в Arkaim (`ShotAssembler`) или в arkaim-media (по контракту) | Contract debt D-2 (`arkaim-media/docs/MEDIA_CONTRACT.md:155`), смена — только с owner-GO (§7, п.5) | (a) оставить в Arkaim и нарастить возможности · (b) перенести в arkaim-media по O3 · (c) решить на этапе O3 |
| **N5** | Актуализировать устаревшую часть masterplan §1.2 | Два пробела из десяти закрыты кодом (§9), часть путей в документах не существует | (a) обновить план отдельной правкой · (b) учесть замечания в этом документе и не трогать план · (c) переписать §1.2 целиком |
| **N6** | Свести цены Runway к одному источнику | masterplan O5 и `MEDIA_EXECUTORS_SPEC.md` §4.1 расходятся по одним моделям (§5.3) | (a) оставить более новый документ как источник истины · (b) перепроверить цены и обновить оба · (c) не использовать цифры Runway вообще |
| **N7** | Формат пилота: подтвердить 60–90 с / 480p / 6–10 шотов | Это зафиксировано в плане, но не вашим решением (`docs/PILOT_FILM_PLAN.md:23`) | (a) подтвердить как есть · (b) изменить (укажите) |
| **N8** | Что считать «принятием пилота» | Сейчас это субъективная оценка + 6 критериев из `docs/PILOT_FILM_PLAN.md:228-235` | (a) оставить как есть · (b) задать дополнительные количественные пороги |

### 8.3. Что НЕ требует решения владельца

Выбор рабочих библиотек и структуры кода; починка несуществующих вызовов фронта; способ отслеживания статусов; параметры workflow; формат хранения версий; реализация `resolve_shot`/сборщика QC — `docs/MEDIA_PRODUCTION_MASTERPLAN.md:296`.

---

## 9. Расхождения между планом (2026-10-14) и кодом (2026-10-22)

Это не критика плана — это факты, которые влияют на решение.

| # | Что записано в плане | Факт на 2026-10-22 | Влияние на решение |
|---|---|---|---|
| R1 | G1: «11 вызовов фронтенда ведут в 404» (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:58`) | Живых вызовов этих адресов в `arkaim-web/src` нет; остались только в сгенерированном OpenAPI-артефакте `arkaim-web/src/shared/api/generated/schema.d.ts` (строки 1218, 1324, 1344, 1387, 1407, 1427, 1571, 1842). Живой код ходит на существующие `POST /api/studio/image-jobs` и `/api/studio/video-jobs` (`arkaim-web/src/app/studio/image-panel.tsx:72`, `video-panel.tsx:218`, `story-reel.tsx:435`, `affected-panel.tsx:653`) | Пробел G1 **закрыт**; работа из Этапа 1 по «починке 11 вызовов» уже не нужна |
| R2 | G2: «Нет страницы Studio» (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:59`) | Страница существует: 19 файлов в `arkaim-web/src/app/studio/` (включая `page.tsx`) | Пробел G2 **закрыт**; Этап 5 частично уже сделан |
| R3 | G3: «Сборка не в API» (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:60`) | Подтверждается: `/book/film/{id}/assemble` отсутствует (закреплено тестом `runtime/tests/test_media_boundary.py:88-90`); `GET /book/film/{id}/output` — 404 без `output_path` (`runtime/core/routes/film_studio.py:116-130`). При этом на диске лежат **5 реальных MP4** (1920×1080, 7–30 с, без аудио) — сборщик кода работает | Пробел G3 **открыт** (решение N4) |
| R4 | G6: «Мост выключен по умолчанию: генерация возможна только при заданном `MEDIA_BACKEND_URL`» (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:63`) | `MediaClient` зарегистрирован в DI **безусловно** и по умолчанию идёт на `http://127.0.0.1:8200` (`runtime/core/adc_deps.py:97-107,234`; `runtime/core/media_client.py:66`). Фактически «выключен» означает «сервиса по этому адресу нет» → ошибка `media_backend_unreachable` (`runtime/core/media_client.py:296-299`) | Формулировка неточна; на решение не влияет, но при Этапе 1 её стоит уточнить |
| R5 | `docs/PILOT_FILM_PLAN.md:88-89`: `core/KNOWLEDGE/CHARACTER_VISUALS.json`, `core/KNOWLEDGE/LOCATION_VISUALS.json` | Таких файлов по этому пути **нет**. Реальные: `core/CORE/visual/VISUAL_KNOWLEDGE/CHARACTER_VISUALS.json` и `core/CORE/visual/VISUAL_KNOWLEDGE/LOCATION_VISUALS.json` | Косметика; но выбор материала пилота (O4) не должен опираться на несуществующие пути |
| R6 | Реестр исполнителей: `comfyui_local` как «основа пилота» (`docs/MEDIA_EXECUTORS_SPEC.md:130`) | Локального видео-провайдера Wan в `arkaim-media` нет; `comfyui` существует только для **image** (SD-checkpoint) — `arkaim-media/media/server.py:98-104`. Фактический «основа-видео» сейчас — облачный ComfyICU (LTX 2.5 I2V), и он **не закоммичен** | Существенно: «основа плана» в репозитории пока не существует ни в каком виде. Связано с N1 и N2 |
| R7 | Сбор документов комплекта (`docs/MEDIA_PRODUCTION_MASTERPLAN.md:277-282`) | Не учтено, что с 2026-10-14 в репозитории появились `core/CORE/studio/{art_direction,continuity,reel,sequence,prepared_updates}.py`, `POST /studio/image-jobs`, `POST /studio/video-jobs`, i2v через `image_asset_id` | Существенно: часть Этапов 2, 5, 6 в коде уже продвинута |

---

## Приложение A. Проверенные источники

Все пути ниже проверены на существование 2026-10-22.

| Область | Файлы |
|---|---|
| Комплект плана | `docs/MEDIA_PRODUCTION_MASTERPLAN.md`, `docs/MEDIA_EXECUTORS_SPEC.md`, `docs/PILOT_FILM_PLAN.md`, `docs/ARKAIM_STUDIO_SPEC.md` |
| ADR | `docs/ADR/ADR_MEDIA_PLAN_V0.md`, `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` |
| Реестры/состояние | `docs/DOCUMENTATION_INDEX.md`, `docs/DOCUMENTATION_INVENTORY.md`, `docs/ARKAIM_PROJECT_STATE.md`, `docs/STUDIO_BOUNDARIES.md`, `docs/OWNER_DECISION_SHEET.md`, `docs/PROJECT_REBASELINE_2026-10-18.md` |
| MediaPlan | `core/CORE/media_plan/schemas.py`, `core/CORE/media_plan/builder.py`, `SCHEMAS/MEDIA_PLAN.schema.json` |
| Studio | `core/CORE/studio/art_direction.py`, `scenario_builder.py`, `scenario_schemas.py`, `session_models.py`, `sequence.py`, `reel.py`, `continuity.py`, `prepared_updates.py`, `store.py` |
| Film Studio | `core/CORE/film_studio/store.py`, `core/CORE/film_studio/schemas.py`, `core/CORE/film_studio/shot_assembler.py` |
| Визуальный слой | `core/CORE/visual/visual_context_builder.py`, `core/CORE/visual/scene_context.py`, `core/CORE/visual/VISUAL_KNOWLEDGE/*.json` |
| Роуты и мост | `runtime/core/routes/studio.py`, `runtime/core/routes/film_studio.py`, `runtime/core/routes/visual.py`, `runtime/core/routes/assets.py`, `runtime/core/media_client.py`, `runtime/core/adc_deps.py` |
| Тесты | `runtime/tests/test_media_boundary.py`, `test_md3_media_plan.py`, `test_studio_prepared_updates.py`, `test_studio_image_job.py`, `test_studio_video_job.py`, `test_studio_video_i2v.py`, `test_studio_reel.py`, `test_studio_sequence.py`, `test_studio_continuity.py`, `test_studio_art_direction.py`, `test_comfyicu_media_client.py`; `arkaim-web/tests/unit/studio-*.test.tsx` |
| Данные | `data/studio.db`, `data/film_studio.db`, `data/visual_assets.db`, `data/film_output/` |
| Соседний репозиторий `arkaim-media` (отдельный, HEAD `f0327cd`) | `media/server.py`, `media/config.py`, `media/image/__init__.py`, `media/image/comfyui.py`, `media/video/__init__.py`, `media/video/comfyicu.py`, `media/video/image_sequence.py`, `media/video/mock.py`, `docs/MEDIA_CONTRACT.md`, `workflows/agnes_image.json`, `workflows/comfyicu_ltx25_i2v.json` |

---

## Статус документа

- **Документ:** PROPOSED — материал для OWNER-REVIEW. Решений не содержит, ничего не инициирует.
- **Генеральный план:** статус **не меняется** — `docs/MEDIA_PRODUCTION_MASTERPLAN.md` остаётся PROPOSED до отдельного OWNER-GO (O1).
- **Производство:** не запускалось. Этап 0 не выполнен.
- **Код:** не изменялся (режим read-only). Изменён один новый файл — этот документ.
- **Срез фактов:** 2026-10-22, репозиторий `C:\proect_arkaim\arkaim` (HEAD `0bf5cc6`) + `C:\proect_arkaim\arkaim-media` (HEAD `f0327cd`, рабочее дерево содержит незакоммиченные `media/video/comfyicu.py` и `workflows/*`).
- **Что дальше:** решение владельца по §8.1 (O1–O5) и §8.2 (N1–N8). До O1 никаких этапов не начинать.
