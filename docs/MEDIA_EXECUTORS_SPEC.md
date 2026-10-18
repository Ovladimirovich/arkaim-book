# MEDIA EXECUTORS SPEC — спецификация мультимедийных исполнителей и workflow

**Тип:** спецификация (документ 3 из комплекта)
**Дата:** 2026-10-14
**Статус:** DRAFT — зависит от OWNER-GO (O1, O3) и результатов Этапа 0
**Главный документ:** `docs/MEDIA_PRODUCTION_MASTERPLAN.md`
**Внешние контракты (источники истины):** `arkaim-media/docs/MEDIA_CONTRACT.md` v1.0, `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md`, `docs/ADR/ADR_MEDIA_PLAN_V0.md`

---

## Простыми словами

1. **Что было целью?** — Описать, как именно Arkaim будет генерировать медиа: гибкую систему исполнителей (без привязки к одной модели/GPU/сервису), реестр возможностей, цепочку резервных способов и правила подключения новых возможностей.
2. **Что реально сделано?** — Спецификация написана поверх проверенных фактов: официальные документы ComfyUI (Wan2.1), Runway Dev, RunComfy, Comfy Router, Silero TTS — все данные с датой проверки **2026-10-14**; зафиксирована гибкая архитектура (реестр, фолбэк 4 уровней, постепенное подключение). Дополнительно (OWNER-GO 2026-10-14): нода **Agnes** исследована, подключена к arkaim-media и проверена одним сквозным запуском — запись реестра `available`.
3. **Что получилось?** — DRAFT (ожидает OWNER-GO и результатов замера).
4. **Есть ли проблемы?** — Видео-провайдера для Wan в arkaim-media пока нет (только image-провайдеры ComfyUI/Agnes); реальные VRAM/скорость/качество на 8 ГБ не проверены (Этап 0); аудио юридически заблокировано (D2 → O2). Нода Agnes **проверена и подключена** 2026-10-14 (статус `available`, сквозной запуск успешен) — но фактическое железо (AMD, CPU-режим) отличается от целевого профиля NVIDIA 8 ГБ.
5. **Что предлагается дальше?** — После O1/O3 и Этапа 0 — реализовать видео-провайдер Wan (Этап 2), TTS-провайдер (Этап 3), assemble (Этап 4) на стороне arkaim-media; новые возможности (Agnes и др.) подключать по фактической проверке.

---

## 1. Принципы

1. **Гибкость без жёсткой привязки.** Не привязывать архитектуру к одной модели, одному workflow, одному GPU или одному облачному сервису. Arkaim Studio выбирает исполнителя по производственной задаче и доступным возможностям; конкретный генератор **не зашивается** в логику фильма. Смена исполнителя сохраняет сценарий, утверждённые параметры сцены, референсы, provenance и историю генераций; преобразование параметров под другой workflow — через явное сопоставление контрактов.
2. **Исполнение — только на стороне arkaim-media.** Arkaim описывает (MediaPlan/AudioPlan), arkaim-media исполняет (`POST /v1/generate`). Прямые вызовы ComfyUI/провайдеров из Arkaim запрещены (boundary ADR, тест `test_media_boundary.py`).
3. **Основа — локальный; совместимость проверяется фактом.** Основная целевая конфигурация — локальный ComfyUI + NVIDIA GPU (8 ГБ VRAM), модель Wan 2.1 T2V-1.3B, клипы 480p. Совместимость **не считается доказанной** по заявленным минимальным требованиям: для каждого рабочего варианта фиксируются фактические VRAM, разрешение, длительность клипа и скорость (Этап 0).
4. **Не обещать непроверенное.** Реальные VRAM/скорость/качество фиксируются замером, не в спецификации; каждая запись реестра несёт дату последней проверки.
5. **Единый реестр возможностей.** Каждый подключённый workflow описывается CapabilityDescriptor (§3): тип задачи, входы/выходы, модели/ноды/оборудование, ограничения, локальный/удалённый, стоимость, версия, последняя проверка. Выбор/фолбэк — по реестру (§7).
6. **Резервные способы.** Цепочка фолбэка (§7.2): основной локальный → иной локальный → удалённый/облачный/API (только при разрешённой политике расходов) → «исполнитель недоступен» (без фиктивного результата). Переключение — только между исполнителями, реально поддерживающими операцию; изменение качества/скорости/стоимости показывается пользователю.
7. **Подключение по мере обнаружения.** Новые исполнители/workflow добавляются постепенно: пользователь предлагает возможность → инженер изучает фактические входы/выходы/зависимости/способ выполнения → проверяет → подключает к реестру. **Фиктивные адаптеры не создаются** заранее и не предполагаются непроверенные функции. Первый отработанный пример процесса — нода Agnes (заявлена → изучена → проверена сквозным запуском → запись `available`, 2026-10-14).
8. **Платные вызовы — только по явной политике.** Автоматический фолбэк на платный backend запрещён без заранее разрешённой политики расходов (решение O5).

---

## 2. Локальный ComfyUI + Wan 2.1 (основа)

### 2.1 Установка и конфигурация

| Параметр | Значение | Источник/проверка |
|---|---|---|
| URL | `http://127.0.0.1:8188` | `arkaim-media/media/config.py` (`COMFYUI_URL`), стандарт ComfyUI |
| API | `POST /prompt` (submit), `GET /history/{id}` (poll), файлы через `/view` | Официальные документы ComfyUI |
| Железо | NVIDIA GPU, 8 ГБ VRAM (ориентир владельца) | Решение 2026-10-14 |
| ОС/бэкенд | Windows/Linux + CUDA | Требование ComfyUI |
| ffmpeg | Нужен для assemble (image_sequence, Ken Burns, concat) | `ShotAssembler` использует ffmpeg |

**Установка (Etап 0):** ComfyUI + модели Wan2.1 + umt5_xxl + VAE. Точные размеры файлов фиксировать при скачивании (fp8-текстовый энкодер ~5 ГБ; fp16-диффузия 1.3B — порядка 3 ГБ; итог — с учётом offload). Официальный ориентир ComfyUI: **1.3B T2V требует только 8 ГБ VRAM** (документация Wan2.1, проверено 2026-10-14).

### 2.2 Модели Wan 2.1 (T2V)

| Компонент | Файл (ориентир) | Назначение | Примечание |
|---|---|---|---|
| Диффузия 1.3B | `wan2.1_t2v_1.3B_fp16.safetensors` | Text-to-video, 480p | Основа пилота |
| Текстовый энкодер | `umt5_xxl` (fp8 ~4.9 ГБ / fp16 9.8 ГБ) | Промпт | fp8 для 8 ГБ |
| VAE | `wan_2.1_vae` | Декодирование | Общий для Wan2.1 |
| (опция) 14B | для image-to-video | Тяжёлая модель | Только если 1.3B не хватит и хватит VRAM |

**Ограничение 1.3B (из документации):** официальный workflow `text_to_video_wan` — T2V; **I2V (14B) — отдельная модель**. Для I2V на 8 ГБ — см. альтернативы (§4.3).

### 2.3 Workflow (стандартный T2V)

| Параметр | Ориентир | Примечание |
|---|---|---|
| Workflow | `text_to_video_wan` (официальный шаблон ComfyUI) | Адаптируется под MediaPlan |
| Вход | prompt, negative, width/height (480p), length (кадры), seed | Из MediaPlan (без execution-полей в самом плане; execution — в envelope arkaim-media) |
| Выход | MP4/WebM (видеоклип ~5 с) | Сохраняется в AssetStorage, возвращается `media_id` |
| Разрешение | 480p (например, 832×480) | Решение владельца; точные размеры фиксируются в Этапе 0 |
| Длительность | Базовый клип ~5 с (81 кадр @16fps — стандарт Wan2.1) | Уточняется в Этапе 0 (зависит от VRAM/скорости) |
| Offload | CPU offloading при нехватке VRAM | Настройка ComfyUI; влияет на скорость |

**Примечание:** точные значения width/height/length/frame_rate — предмет Этапа 0; спецификация фиксирует только «480p, короткий клип».

### 2.4 Контракт входа/выхода (arkaim-media → ComfyUI)

```
Вход (arkaim-media внутренне):
  MediaPlan (image|video) + execution-envelope:
    preferred_backend = "comfyui"
    workflow_name / workflow_version
    params (seed, steps, cfg — технические)

  ComfyUIProvider(video) собирает prompt из MediaPlan:
    prompt = visual_prompt + style + character + location + light + camera
    negative = plan.negative_constraints
    size/length = из execution (или дефолт 480p/~5s)

Выход:
  видеофайл → AssetStorage → media_id (lineage: media_plan_id)
  Arkaim получает media_id через /v1/generate response
```

### 2.5 Что уже есть в arkaim-media

| Компонент | Файл | Статус |
|---|---|---|
| ComfyUIProvider (image) | `media/image/comfyui.py` | Работает (M4.2.2); SD-checkpoint, `/prompt`, DEFAULT_WF |
| ImageSequenceProvider | `media/video/image_sequence.py` | Работает; ffmpeg-фолбэк для видео из кадров |
| VideoMock | `media/video/mock.py` | Заглушка |
| Config | `media/config.py` | `COMFYUI_URL`, `WORKFLOWS_DIR` |
| Контракт | `schemas/media_generate_request.schema.json` | v1.0; `execution.media_kind` enum `["image","video"]` (audio — extension point) |

**Что нужно (Этап 2):** `ComfyUIProvider(video)` для Wan2.1 T2V (workflow `text_to_video_wan`), маппинг MediaPlan → prompt/params, poll `/history/{id}`, извлечение MP4, сохранение.

---

## 3. Единый реестр возможностей (CapabilityDescriptor)

Для каждого подключённого workflow фиксируется:

| Поле | Тип | Описание | Пример (Wan локальный) |
|---|---|---|---|
| `backend_id` | string | Идентификатор исполнителя | `comfyui_local` |
| `media_kind` | enum | Тип задачи: `image` / `video` / `audio` | `video` |
| `model` | string | Модель | `wan2.1_t2v_1.3b` |
| `workflow_name` | string | Имя workflow | `text_to_video_wan` |
| `workflow_version` | string | Версия workflow (для воспроизводимости) | `v1` |
| `inputs` | object | Входные параметры и формат | prompt, negative, width, height, length, seed |
| `outputs` | object | Формат результата | video_url / video_bytes, media_id |
| `requirements` | object | Требуемые модели, ноды, оборудование | models: [wan…, umt5, vae]; nodes: [KSampler…]; hardware: nvidia_gpu |
| `limits` | object | Ограничения VRAM, разрешения, длительности, качества | vram_required_gb, max_resolution, max_duration_s, max_quality |
| `execution_location` | enum | Способ исполнения: `local` / `remote` | `local` |
| `cost` | object | Стоимость (если есть) | `{"type": "local", "credits_per_second": 0}` |
| `status` | enum | Статус | `available` / `unavailable` / `degraded` / `discovering` |
| `last_checked` | datetime | Дата последней проверки | 2026-10-14 |
| `notes` | string | Заметки (условия, quirks) | offload включён; качество зависеть от seed |

**Пример реестра (на 2026-10-14):**

| backend_id | media_kind | model | workflow | execution | cost | status | Проверено |
|---|---|---|---|---|---|---|---|
| `comfyui_local` | video | wan2.1_t2v_1.3b | text_to_video_wan | local | local | expected (Этап 0) | Офиц. доки ComfyUI |
| `comfyui_local` | image | sd (cyberrealistic) | default | local | local | available | Код arkaim-media |
| `comfyui_local` | image_sequence | ffmpeg | — | local | local | available | Код arkaim-media |
| `silero_tts` | audio | v5_ru | — | local | local | planned (Этап 3) | PyPI Silero |
| `runway_dev` | video | kling3.0/wan3/veo3.1 | API | remote | paid | optional | Runway Dev API |
| `runcomfy` | video | свои workflow | Serverless/Model API | remote | paid | optional | RunComfy docs |
| `comfy_router` | video | партнёрские модели | один endpoint | remote | paid | optional | Comfy Router docs |
| `agnes` (ComfyUI-Agnes-AI) | image | agnes-image-2.5-flash | agnes_image.json | hybrid (submit local → gen remote) | free (без кредитов) | `available` | **2026-10-14, сквозной запуск: `/book/visualize` → MediaClient → arkaim-media → ComfyUI → Agnes → AssetStorage, PNG 1024×1024** |

**Запись CapabilityDescriptor (подключено 2026-10-14, по фактической проверке §3.1):**

| Поле | Значение |
|---|---|
| `backend_id` | `agnes` (выбор: `execution.preferred_backend="agnes"` → arkaim-media → ComfyUIProvider с `workflows/agnes_image.json`; auto-порядок цепи не менялся — agnes только по явному выбору) |
| `media_kind` | `image` (text2img) |
| `model` | `agnes-image-2.5-flash` (облачный, Agnes AI; ключ — только внутри ComfyUI: env `AGNES_API_KEY` / `agnes_config.json`; в Arkaim/workflow не копируется) |
| `workflow_name` / `workflow_version` | `agnes_image.json` / `v1` — API-граф `AgnesImage(7) → SaveImage(8)`, снят с фактически выполненного прогона (ComfyUI_01018) |
| `inputs` | `prompt` (STRING ноды); `size` `WxH` → `quality` (1K/2K/3K/4K по длинной стороне) + `aspect_ratio` (auto, 1:1, 2:3, 3:4, 4:5, 9:16, 9:21, 3:2, 4:3, 5:4, 16:9, 21:9 — ближайшее, отклонение >5% → warning в логе); `seed` = `hash(prompt)&0x7FFFFFFF` (правило провайдера); `negative` отсутствует у ноды → отбрасывается с warning |
| `outputs` | PNG-байты (MediaResult.bytes_b64, content_format=png) |
| `requirements` | локальный ComfyUI 0.34.5+ с `custom_nodes/ComfyUI-Agnes-AI` v1.2.1; сеть до apihub.agnes-ai.com; локальный GPU не требуется (CPU-режим достаточен) |
| `limits` | итоговый размер выбирает Agnes по quality/aspect_ratio (запрошенный WxH не гарантирован, маппинг приближённый); только text2img (без reference-изображений); negative не поддерживается |
| `execution_location` | `hybrid`: submit local (ComfyUI 8188) → gen remote (Agnes cloud) |
| `cost` | `{"type": "free", "credits": 0}` — README пакета: «Free. No token billing, no credit system» (проверено 2026-10-14) |
| `status` | `available` |
| `last_checked` | 2026-10-14 |
| `notes` | seed-квирк `hash(prompt)` недетерминирован между процессами Python (PYTHONHASHSEED); в `/history` ComfyUI видны выполненные входы (доказательство прогона); AgnesVideo НЕ подключён |

**Правило реестра:** запись `discovering` означает «возможность заявлена пользователем, но не проверена инженером» — она не участвует в выборе исполнителя до фактической проверки входов/выходов/зависимостей.

### 3.1 Подключение возможностей по мере обнаружения

Новые исполнители и workflow добавляются **постепенно**, в ходе разработки — не все одновременно.

**Процесс:**

1. **Пользователь предлагает** найденную возможность (название, ссылку, workflow, ноду).
2. **Инженер изучает** фактические возможности: что делает, входы, выходы, зависимости, способ выполнения, ограничения.
3. **Инженер проверяет** на целевом железе/в окружении (VRAM, стабильность, качество).
4. **Запись в реестр** (§3) со статусом `available` и датой `last_checked`; при необходимости — адаптер в arkaim-media.
5. **Становится доступна** в производственном процессе (выбор Studio, фолбэк).

**Первый пример — нода Agnes (генерация изображений): ПОДКЛЮЧЕНА 2026-10-14.**

- Заявлена пользователем → инженер изучил: пакет ComfyUI-Agnes-AI v1.2.1, нода `AgnesImage` (prompt/quality/aspect_ratio/seed), облачная генерация `agnes-image-2.5-flash`, стоимость — free (без кредитов).
- Шаблон `workflows/agnes_image.json` снят с фактически выполненного графа (`AgnesImage → SaveImage`); параметры size/quality/aspect_ratio/seed сопоставлены явно (`map_size_to_agnes`), неподдерживаемые параметры (negative) — с warning, не молча.
- Проверено сквозным запуском 2026-10-14: `/book/visualize` → MediaClient (`preferred_backend="agnes"`) → arkaim-media → ComfyUI → Agnes → PNG → AssetStorage (scene_id + provenance) → `GET /book/assets/{id}/file`; входы прогона подтверждены в `/history` ComfyUI. Запись в реестре — `available` (§3).
- Фактическое железо проверки: AMD Radeon RX 570 4 ГБ, PyTorch CPU, ComfyUI `--cpu` — локальный GPU не понадобился (генерация облачная); отличие от целевого профиля NVIDIA 8 ГБ зафиксировано в masterplan (§2.3).

**Ограничение:** не начинать реализацию всех исполнителей одновременно; подключать по мере обнаружения и практической проверки.

---

## 4. Дополнительные исполнители (опции, платные — НЕ обязательны)

Все цены/лимиты — **с датой проверки 2026-10-14**; перед подключением — перепроверка.

### 4.1 Runway Dev API (`docs.dev.runwayml.com`)

| Модель | Тип | Стоимость (credits) | Доллары (1 cr = $0.01) | Звук |
|---|---|---|---|---|
| kling 3.0 | T2V/I2V | ~13 cr/s | ~$0.13/s | Да (sync/async) |
| wan3 (720p) | T2V/I2V | ~10 cr/s | ~$0.10/s | Нет |
| veo3.1_fast | T2V/I2V | ~10 cr/s | ~$0.10/s | Нет |
| gen4.5 | T2V/I2V | varies | varies | Нет |
| seedance | T2V | varies | varies | Нет |
| hailuo3 | T2V | varies | varies | Нет |

**TTS:** `eleven_multilingual_v2` — 1 cr / 50 символов (~$0.002/символ), русский.
**Дополнительно:** Characters (аватары), custom voices, seed-audio.

### 4.2 RunComfy (`docs.runcomfy.com`)

| Продукт | Назначение | Оплата |
|---|---|---|
| Model API | Hosted модели (Wan и др.) | Pay-per-request |
| Serverless API | Свои ComfyUI-workflow в облаке | Pay-per-request |
| Serverless LoRA | Тонкая настройка | Pay-per-request |
| Trainer (LoRA) | Обучение персонажей | Pay-per-request |

**Флоу:** submit workflow → `request_id` → poll status → download. Есть MCP, CLI.

### 4.3 Comfy Router / Comfy Cloud (`docs.comfy.org`)

| Возможность | Описание |
|---|---|
| Один API endpoint | Доступ к партнёрским моделям (единый интерфейс) |
| Run Workflows | Деплой своего ComfyUI-workflow |
| Cloud MCP | Управление через MCP |
| CLI | `comfy generate` |

### 4.4 Лёгкие альтернативы (если Wan не подходит по VRAM/скорости)

| Модель | Зачем | Примечание |
|---|---|---|
| LTX-Video | Более лёгкая T2V | Проверить VRAM/качество в Этапе 0 |
| Stable Video Diffusion | I2V из кадра | Для 8 ГБ — вариант; нужен входной кадр |
| AnimateDiff | Анимация из SD-кадров | Фолбэк image_sequence |

---

## 5. Аудиоисполнители (Этап 3, зависит от O2/O3)

### 5.1 Silero TTS (основа, локально)

| Параметр | Значение | Источник |
|---|---|---|
| Пакет | `silero` (PyPI), v0.5.5 (релиз 2026-02-03) | PyPI |
| Модель | `v5_ru` (русский) | Официальный README |
| Спикеры | aidar, baya, kseniya, xenia, eugene | v5_ru |
| Частота | 8 / 24 / 48 кГц | README |
| SSML | Поддержка | README |
| Лицензия моделей | **CC BY-NC** (некоммерческая!) | README |
| Лицензия пакета | MIT | PyPI |
| Альтернатива | `v5_cis_base` — **MIT** (коммерчески безопасно) | README |

**Важно для владельца:** если проект будет коммерческим — либо использовать `v5_cis_base` (MIT), либо облачный TTS (Runway/другой), либо купить лицензию.

**Контракт входа/выхода:**

```
Вход (AudioPlan):
  text (реплика), speaker (aidar/...), sample_rate (48000), prosody (опционально)

Выход:
  WAV → AssetStorage → media_id (lineage: audio_plan_id)
```

### 5.2 Облачный TTS (опция, платно)

| Сервис | Модель | Стоимость | Русский |
|---|---|---|---|
| Runway Dev | eleven_multilingual_v2 | 1 cr / 50 символов | Да |
| ElevenLabs (напрямую) | multilingual v2 | varies | Да |
| Piper (self-hosted) | rus-medium | free (local) | Да (качество ниже Silero) |

---

## 6. Сборка (assemble, Этап 4, зависит от O3)

### 6.1 Где выполняется

По контракту (MEDIA_CONTRACT §6): **assemble — execution → arkaim-media.** ShotAssembler в Arkaim (код работает, к API не подключён — G3) переносится/адаптируется на сторону media.

### 6.2 Контракт `POST /v1/assemble` (новый, v1.1)

```
Вход:
  project_id (Arkaim FilmProjectStore)
  shots: [{media_id, duration_s, camera_motion, transition}]
  audio:  [{media_id (WAV), type: narrator|ambience|music, volume, offset_s}]
  subtitles: [{text, start_s, end_s}]
  title/credits

Выход:
  video_url / video_bytes (MP4 H.264)
  audio_tracks: [narrator.wav, ambience.wav, music.wav]
  subtitles.srt
  qc_report: {duration_s, resolution, fps, issues[]}
```

### 6.3 Что включает (на базе ShotAssembler + расширение)

| Функция | Назначение | Статус |
|---|---|---|
| ffmpeg concat | Склейка клипов | Есть в ShotAssembler |
| Ken Burns | Анимация статичных кадров | Есть |
| Аудиомикс | Диктор + атмосфера + музыка (громкости, offset) | Нет (Этап 4) |
| Субтитры | Встраивание/внешний SRT | Нет (Этап 4) |
| Титры | Начало/конец | Нет (Этап 4) |
| Экспорт | MP4 H.264 + аудио + SRT | Есть (частично) |

---

## 7. Выбор и фолбэк исполнителя

### 7.1 Логика выбора (arkaim-media)

```
1. Получить MediaPlan/AudioPlan + execution-envelope
2. Определить media_kind (image|video|audio)
3. Выбрать backend по preferred_backend или дефолт (comfyui_local)
4. Проверить реестр (§3): статус, media_kind, execution_location, cost
5. Если unavailable / не подходит media_kind → цепочка фолбэк (§7.2)
6. Вызвать провайдер → получить media_id → вернуть Arkaim
```

**Важно:** выбор — по производственной задаче и доступным возможностям реестра, а не по зашитому в логику фильма генератору. При смене исполнителя сохраняются сценарий, утверждённые параметры сцены, референсы, provenance и история генераций; параметры под другой workflow преобразуются через явное сопоставление контрактов.

### 7.2 Цепочка резервных способов (4 уровня)

| Уровень | Способ | Когда используется | Примечание |
|---|---|---|---|
| 1 | Основной локальный ComfyUI workflow (Wan2.1 T2V 1.3B) | Дефолт для video; основа пилота | Проверенная конфигурация (Этап 0) |
| 2 | Иной совместимый локальный workflow/нода (LTX-Video, AnimateDiff, по обнаружению — Agnes и др.) | Level 1 недоступен/не хватает VRAM/качество; или другая media_kind | Только после фактической проверки и записи в реестр |
| 3 | Удалённый ComfyUI / облачный workflow / API внешнего исполнителя (RunComfy, Comfy Router, Runway) | Levels 1–2 недоступны **и** разрешена политика расходов (O5) | Показать пользователю изменение качества/скорости/стоимости |
| 4 | **«Испполнитель недоступен»** | Нет подходящего варианта | Понятное состояние, **без фиктивного результата** |

**Правила переключения:**

1. Переключение **только** между исполнителями, реально поддерживающими требуемую операцию (`media_kind`).
2. Изменение качества, скорости, ограничений и стоимости **показывается пользователю** до/при выполнении.
3. Автоматический фолбэк на **платный** backend — **запрещён** без явного подтверждения владельца (O5).
4. Записи `discovering` (не проверенные) в выборе не участвуют.
5. При недоступности всех уровней → статус `failed` с причиной «исполнитель недоступен» (не «выполнено»).

### 7.3 Типовые ситуации

| Ситуация | Цепочка | Примечание |
|---|---|---|
| `comfyui_local` нет GPU/модели | L2 (image_sequence / иной локальный) → L3 (по O5) → L4 | |
| `comfyui_local` не хватает VRAM | offload CPU (медленно) → L2 (лёгкая модель) → L4 | Решение по результатам Этапа 0 |
| `silero_tts` недоступен | Piper (local, L2) → облачный TTS (L3, по O5) → L4 | |
| Платный backend без кредита | Ошибка `INSUFFICIENT_CREDIT` (не авто-фолбэк) | Деньги — только по O5 |
| Agnes заявлена, но не проверена | Не участвует (status `discovering`) | Ждёт фактической проверки |

---

## 8. Отслеживание выполнения

### 8.1 Текущее состояние

- `/v1/generate` — **синхронный**, таймаут 620 с (`MediaClient`).
- Механизм заданий/очереди — **нет** (G5: `GenerationQueue` — мёртвый код, тесты требуют отсутствия).

### 8.2 Целевая модель (Этап 2)

| Уровень | Механизм | Примечание |
|---|---|---|
| Статус задания | `pending → running → completed/failed` | В arkaim-media; Arkaim опрашивает |
| Прогресс | % (если ComfyUI сообщает) или heartbeat | WebSocket в Studio |
| Длительная генерация | Если > таймаута 620 с → async (submit + poll) | Требует расширения контракта (решение владельца) |

### 8.3 Когда нужен async

Если Этап 0 покажет: время клипа > 620 с → ввести `POST /v1/generate/async` + `GET /v1/jobs/{id}` (расширение контракта, OWNER-GO). До тех пор — синхронный режим.

---

## 9. Хранение результатов

| Тип | Где | Формат |
|---|---|---|
| Видеоклипы | `data/visual_assets/` (AssetStorage) | MP4/WebM |
| Аудио | `data/visual_assets/` (AssetStorage) | WAV |
| Итоговый фильм | `data/film_output/` | MP4 |
| Метаданные | SQLite (`film_studio.db`, `visual_assets.db`) | media_id, lineage, provenance |

**Lineage:** каждый ассет ссылается на `media_plan_id` / `audio_plan_id`; каждый план — на `scene_context_id` / `video_scenario_id`; каждый сценарий — на главы/сцены книги (provenance).

---

## 10. Критерии готовности (Этап 2)

1. Видео-провайдер Wan работает: шот из FilmProject → MediaPlan → ComfyUI → MP4 → `media_id`.
2. Статус задания виден (`completed`/`failed` + текст ошибки).
3. Реестр показывает статус backend (§3).
4. Фолбэк на `image_sequence` работает (если ComfyUI недоступен).
5. Нет прямых вызовов ComfyUI из Arkaim (boundary соблюдён).

---

## Статус документа

- **DOCUMENTED** (по факту исследования кода и внешних источников 2026-10-14).
- Видео-провайдер Wan: **не реализован** (по условию — только спецификация).
- TTS-провайдер: **не реализован** (ждёт O2/O3).
- assemble: **не реализован** (ждёт O3).
- Зависит от: O1, O2, O3; результатов Этапа 0 (VRAM/скорость/качество).
