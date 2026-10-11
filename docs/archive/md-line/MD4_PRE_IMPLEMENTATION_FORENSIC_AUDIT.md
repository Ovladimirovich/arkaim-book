# MD-4 — Media Project Bootstrap — PRE-IMPLEMENTATION FORENSIC AUDIT

**Дата:** 2026-09-13
**Статус:** DOCUMENTED (audit-only; реализация не начата)
**Вход:** owner-мандат «Этап 2» (после Этапа 1 — test-isolation fix, commit `6f25114`)
**Правило:** НИКАКОГО кода. Аудит не предполагает, что Foundation спроектировал MD-4 верно — он проверяет фактический код.

---

## Простыми словами

**Цель:** перед созданием отдельного Media-проекта проверить по реальному коду — что именно можно безопасно вынести, что должно остаться в «Аркаиме», и не развалит ли это существующие пять маршрутов генерации.

**Сделано:** полная инвентаризация исполнительного слоя (провайдеры, пайплайн, хранилища, очередь, ComfyUI-интеграция), карта зависимостей, сверка всех 11 пунктов долга MD-3, два варианта миграции с оценкой рисков.

**Главный вывод:** Media-слой в коде **уже физически отделён** (6 модулей в `core/CORE/`, единственная точка сборки — `adc_deps`), но связан с Аркаимом **тремя скрытыми нитями**, каждая из которых при переносе «в лоб» порвётся:

1. **Файловое хозяйство** — генерации пишут файлы в один общий каталог `data/` (ассеты, видео, film-output), а读取 происходит по сырым путям на диске. При выносе в другой проект файлы начнут «жить в двух домах».
2. **Semantic-зависимость пайплайна** — генерационный пайплайн читает book-сущности (genome-сцены/персонажи/локации) напрямую через SceneEngine, а не через план. Media-проект без Аркаима не сможет проверять «сцена существует».
3. **Execution-словарь Аркаима** — workflow/чекпоинты/сэмплеры ComfyUI и `.env`-настройки лежат в config Аркаима (`GENOME_DIR/workflows`, `COMFYUI_URL`) — знание о бэкенде проникло в домен.

**Результат:** PASS (аудит завершён; реализация не выполнялась).
**GO/NO-GO:** **рекомендую GO на вариант A (минимальный bootstrap)** — при условиях из §16.

---

## 1. Current-state inventory (по фактическому коду)

### 1.1 Исполнительный слой — файлы и назначение

| Компонент | Файл (core/CORE/) | Строк | Роль |
|---|---|---|---|
| Image-провайдер ComfyUI | `providers/image/comfyui.py` | 169 | HTTP-клиент ComfyUI: POST /prompt, poll /history, GET /view; workflow-инъекции (prompt/negative/size/seed/quality); динамический resolve чекпоинта |
| Image-провайдер SD (legacy) | `providers/image/stable_diffusion.py` | 41 | Legacy SD-генерация (не ComfyUI) |
| Image-провайдер SVG | `providers/image/svg_template.py` | — | SVG-шаблоны (не network) |
| Image-провайдер Mock | `providers/image/mock.py` | — | Тестовый |
| Image-ABC + цепь | `providers/image/__init__.py` | 107 | `ImageProvider.generate(prompt,size)`+health; `ImageProviderChain.generate_with_metadata(prompt,size,preferred_provider)` → ProviderExecutionResult{name,kind,bytes} |
| Video-ABC + цепь | `providers/video/__init__.py` | 24+ | `VideoProvider.generate(prompt,duration,size,fps)`+health; цепь |
| Video из кадров | `providers/video/image_sequence.py` | 73 | Кадры через ImageProvider → ffmpeg |
| Video-мок | `providers/video/mock.py` | — | Тестовый |
| Пайплайн ассетов | `visual_assets/pipeline.py` | 497 | Оркестрация: сцена→промпт→провайдер→сохранение; image/video/batch; MD-3.2 plan/dispatch-параметры |
| Промпт-построитель ассетов | `visual_assets/prompt_builder.py` | ~250 | legacy-проекция текста (build_asset_prompt/negative; STYLE_PRESETS) |
| Схемы ассетов | `visual_assets/schemas.py` | ~200 | VisualAsset/GenerationParams/ShotSpec/CameraSpec (execution-поля) |
| Хранилище ассетов | `visual_assets/storage.py` | 238 | SQLite `data/visual_assets.db` + файлы `data/visual_assets/{images,videos,thumbnails}` |
| Очередь генерации | `visual_assets/queue.py` | 134 | asyncio-очередь + 2 воркера; enqueue/enqueue_batch/get_status (БЕЗ плана) |
| Film Studio store | `film_studio/store.py` | ~180 | SQLite `data/film_studio.db` (проекты/сцены/шоты) |
| Film Studio сборка | `film_studio/shot_assembler.py` | ~350 | ffmpeg: конкатенация ассетов-шотов в mp4; Ken Burns; чтение файлов ассетов с диска |
| Film Studio схемы | `film_studio/schemas.py` | ~120 | FilmProject/SceneShot/ShotVersion (двойник ShotSpec — MP-F6) |
| MediaPlan (домен) | `media_plan/{schemas,builder,dispatch}.py` | 331+ | v0-контракт (KEEP в Arkaim — семантический); dispatch — TEMPORARY (MD-5) |
| Prompt-шаблоны генераторов | `visual/prompt_templates/{base,comfyui,flux,hailuo,kling,runway}.py` | ~500 | Семантические шаблоны промптов per-generator (comfyui.py — 87 строк) |

### 1.2 Точки входа HTTP (маршруты MD-3 A–E)

| Роут | Файл:строка | Канонический путь |
|---|---|---|
| **A** POST `/book/visualize` | visual.py:25 | ctx→plan→dispatch(prompt=legacy)→`image_provider.generate(dispatch.prompt)` |
| **B** POST `/book/visualize-epoch` (M7) | visual.py:114 | ctx(epoch)→plan→dispatch→generate |
| **C** POST `/book/assets/generate` (image|video) | assets.py:37 (plan L88–105) | ctx→plan→dispatch→`pipeline.generate_image(+plan,+dispatch)`; **video: plan строится, но `generate_video` не принимает plan/dispatch** (F-33-1 подтверждён: сигнатура pipeline.py:195–201 без plan) |
| **D** `/book/assets/generate-context` (+character L197, location L237) | assets.py:163/218/257 | ctx→plan→dispatch→`pipeline.generate_image_from_context(+plan,+dispatch)` |
| **E** POST `/book/film/{id}/scenes/{sid}/shots/{shot}/generate` | film_studio.py:~368 | ctx→plan(intent=film_shot)→dispatch→`pipeline.generate_image(+plan,+dispatch)` |
| Настройка ComfyUI | `/book/comfyui/{status,config}` (visual.py:339–368) | чтение/правка COMFYUI_URL (env + in-memory) |
| Провайдеры | `/book/providers/{list,status}` (visual.py:407–438) | health-чек всех image-провайдеров |
| Асинхрон/очередь | `/book/assets/{generate-async,batch,queue/*}` (assets.py:124–157, 296–313, 442–455) | `queue.enqueue` (без плана) |
| Regenerate | `/book/assets/{id}/regenerate` (assets.py:411) | **без плана**; legacy-параметры style/quality |
| Ассеты-чтение | `/book/assets`, `/{id}`, `/{id}/file`, `/{id}/thumbnail`, DELETE (assets.py:317–410) | чтение SQLite + файлов |
| Film Studio | `/book/film/*` (13 роутов, film_studio.py:31–470) | CRUD проектов/шотов + assemble(ffmpeg) |

### 1.3 DI-сборка (единственная точка инстанцирования)

`runtime/core/adc_deps.py` (фабрики, все media-импорты локализованы в фабриках):
- `_factory_image_provider_chain` (L64–67): ImageProviderChain([ComfyUIProvider, MockImageProvider]) — **SD/SVG не зарегистрированы**;
- `_factory_video_provider_chain` (L76–80): VideoProviderChain([MockVideoProvider, ImageSequenceVideoProvider(image_prov)]);
- `_factory_asset_store` (L87), `_factory_generation_pipeline` (L91–98: scene_engine+prompt_builder+image_provider+video_provider+asset_store), `_factory_generation_queue` (L107–109: max_concurrent=2), `_factory_film_store` (L102).
- Регистрация в `ServiceRegistry` (L230): asset_store/generation_pipeline/generation_queue/film_store.

### 1.4 Configuration/env-зависимости

- `core/config.py`: `COMFYUI_URL` (L64, env), `GENOME_DIR` (L21) — **ComfyUI-провайдер берёт workflows из `GENOME_DIR/workflows`** (comfyui.py:13) и пишет default.json туда же (L43) — каталог книги используется как хранилище конфигурации бэкенда.
- `comfyui.py` L109–113/L139: **повторное чтение `os.getenv("COMFYUI_URL")` при каждом generate/health** (поддержка Colab-туннеля) — env-зависимость в рантайме, не только в config.
- `runtime/requirements.txt`: httpx, aiosqlite — зависимости Media-слоя замешаны в общие.

### 1.5 Database/Filesystem

- SQLite: `data/visual_assets.db` (ассеты), `data/film_studio.db` (film-проекты) — обе в общем `data/` Аркаима.
- Файлы: `data/visual_assets/{images,videos,thumbnails}`, `data/film_output` (собранные фильмы) — общий корень `data/` Аркаима.
- `shot_assembler._get_asset_path` читает ассеты **напрямую с диска** (L37–46: 4 варианта пути, legacy-fallback) — вторая точка ownership поверх SQLite-хранилища.

---

## 2. Dependency map (фактическая)

### 2.1 Прямой поток (вниз)

```
Arkaim HTTP (5 маршрутов A–E)
  → SceneContext-билдер (visual/visual_context_builder.py; M7-мост: WorldModel.read-only)
  → MediaPlanBuilder (media_plan/builder.py; PromptComposer — semantic-рендер)
  → MediaPlan (media_plan/schemas.py — домен, без execution)
  → ExecutionDispatch (media_plan/dispatch.py — TEMPORARY MD-5)
  → AssetGenerationPipeline (visual_assets/pipeline.py)
     ├─ SceneEngine (visualization/scene_engine.py — ЧТЕНИЕ genome: сцены/персонажи/локации)
     ├─ build_asset_prompt (visual_assets/prompt_builder.py — legacy-проекция текста)
     └─ ImageProviderChain / VideoProviderChain (providers/)
          └─ ComfyUIProvider (HTTP → ComfyUI; ImageSequenceVideoProvider → ffmpeg)
  → AssetStorage (SQLite + files)
```

### 2.2 Обратные и скрытые зависимости (главные находки)

| # | Зависимость | Где в коде | Класс риска |
|---|---|---|---|
| B1 | **Pipeline → book-домен напрямую**: SceneEngine читает genome-сцены для 404-проверки и персонажей/локации для промпта (pipeline.py:62, 97, 106) | semantic-leak в execution | HIGH |
| B2 | **shot_assembler → файлы ассетов по сырым путям** (не через storage-API) | duplicate ownership | HIGH |
| B3 | **ComfyUIProvider → config Аркаима** (GENOME_DIR/workflows, COMFYUI_URL, getenv в рантайме) | backend-knowledge в Arkaim | HIGH |
| B4 | **visualization/__init__.py:18 реэкспортит провайдеров** (`from providers.image import …`) — домен-слой визуализации знает провайдерные типы | accidental coupling | MEDIUM |
| B5 | **Пайплайн хранит plan-промпт в dispatch-поле** (`dispatch.prompt = prompt`, pipeline.py:143; routes A:95) — домен-объект с мутацией текста | bridge-долг MD-5 | MEDIUM |
| B6 | **GenerationParams в VisualAsset** содержит execution-поля (provider/size/quality/negative_prompt) — execution «проживает» в домен-модели ассета | двойное представление | MEDIUM |
| B7 | **Queue/regenerate/batch обходят план** (queue.py:44–62 — только chapter/scene_id/overrides; assets.py:411 — style/quality) | долг MD-3 (реестр §2) | MEDIUM |
| B8 | **prompt_templates/{flux,hailuo,kling,runway} — «внешние» video-бэкенды как semantic-шаблоны**, фактически не подключённые провайдеры | гипотетические backend'ы в домене | LOW |

**Циклических зависимостей не найдено** (media_plan → visual → (config); visual_assets → visualization/visual; providers → config; замкнутых петель нет).

### 2.3 Кто-кого-знает (сводка)

- **ComfyUI импортируют:** только `adc_deps` (регистрация) и 2 тест-файла. Production-роуты ComfyUI-класс НЕ импортируют — знают только цепь. ✅ узкая точка.
- **Providers импортируют:** `adc_deps`, сам `providers/*` (внутренние), `visualization/__init__` (реэкспорт B4), тесты.
- **MediaPlan знают:** 3 роут-файла (visual/assets/film_studio) + pipeline (параметр) + 7 MD-3 тест-файлов. Не шире.
- **SceneContext знают:** 3 роут-файла + pipeline (неявно, через поля) + media_plan/builder + тесты.
- **Asset пишут:** pipeline (generate_image/video/from_context), queue (воркеры), regenerate.
- **Asset читают:** роуты чтения (assets.py:317–410), shot_assembler (с диска — B2), film_studio-роуты (store.update_shot).

---

## 3. MOVE / KEEP / BRIDGE / DELETE-LATER / UNKNOWN

| Компонент | Класс | Основание |
|---|---|---|
| `providers/image/comfyui.py` | **MOVE** | Чистый execution-клиент; семантику получает только текстом промпта |
| `providers/image/{__init__,mock,svg_template}.py` | **MOVE** | ABC/цепь — контракт Media-стороны; mock/svg — провайдерные реализации |
| `providers/image/stable_diffusion.py` | **MOVE** (или DELETE-LATER) | Legacy; не зарегистрирован в DI |
| `providers/video/*` (ABC+chain, image_sequence, mock) | **MOVE** | Полностью execution |
| `visual_assets/pipeline.py` | **BRIDGE → затем MOVE** (по варианту A: остаётся, обрастает адаптером) | Оркестратор execution, но тянет SceneEngine (B1) — при переносе требует замены на plan-only |
| `visual_assets/{prompt_builder,schemas}.py` | **SPLIT**: prompt_builder (legacy-проекция) — **DELETE-LATER** (MD-5); schemas — **BRIDGE** | Текст-проекция — временный мост; VisualAsset — домен-представление Аркаима |
| `visual_assets/storage.py` | **BRIDGE** (v1: Arkaim-сторона владеет) | Файловый ownership; см. §8 |
| `visual_assets/queue.py` | **MOVE** (в Media) либо **KEEP** (временный) | Очередь задач — execution; но её API без плана (B7) — переносить «как есть» нельзя |
| `film_studio/*` (store, shot_assembler, schemas) | **UNKNOWN → owner-решение** | Проекты/шоты — домен сценария (Аркаим: концепт), сборка ffmpeg — execution (Media). Граница режет модуль пополам |
| `media_plan/*` | **KEEP** (всё в Arkaim) | Домен-контракт по ADR; dispatch — DELETE-LATER (MD-5) |
| `visual/*` (context/engines/templates) | **KEEP** | Семантика (PromptComposer, движки) — это «голос книги» |
| `visualization/*` | **KEEP** (кроме реэкспорта провайдеров B4 — DELETE-LATER) | genome-знание, book-домен |
| `/comfyui/*` роуты (visual.py:339–368) | **KEEP → де-публикация MD-5** | Настройка бэкенда — должна уйти из Arkaim-API |
| `/providers/*` роуты (visual.py:407–438) | **KEEP → BRIDGE** (v1: health-прокси) | Фронт показывает статусы; позже — прокси к Media |
| COMFYUI_URL/GENOME_DIR-workflows в config | **BRIDGE → MOVE** | Backend-config должен переехать к Media |
| httpx/aiosqlite в requirements | **BRIDGE** | Разделение зависимостей при bootstrap-репо |

## 4. Proposed Media Project boundary (минимальная)

**Уходит из Arkaim (Media Project):**
- `providers/image/*` (ABC/chain/comfyui/mock/svg; SD — опционально);
- `providers/video/*` (ABC/chain/image_sequence/mock);
- execution-половина: HTTP-comfy-клиент, workflow-знание (DEFAULT_WF, QUALITY_PRESETS, resolve_ckpt), ffmpeg-сборка кадров;
- workflows-каталог (сегодня `core/GENOME/workflows/default.json` — **облачение ComfyUI в каталоге genome книги** — переносится в Media-repo);
- env `COMFYUI_URL` → `MEDIA_BACKEND_URL` (имя владельцу на решение).

**Остается в Arkaim:**
- весь semantic-стек: visual/*, visualization/*, media_plan/* (план = смысл);
- HTTP-маршруты A–E (входы), Film Studio CRUD-домен (проекты/шоты как «сценарная» сущность);
- AssetStorage: метаданные ассетов (SQLite) и файлы — **v1: Arkaim остаётся владельцем** (см. §8 — иначе двойной ownership);
- GenerationQueue — v1 остаётся в Arkaim (обход плана B7 не чинится в bootstrap), Media-проект принимает **синхронный** generate-вызов.

**Минимальный внешний контракт (v1):**

Достаточно ли `MediaPlan → Media`? **Фактически — НЕТ, одним планом не обойтись**, потому что:
1. план не содержит execution-полей (size/provider/duration/fps) — они сегодня в dispatch (MD-3.3 §2.2);
2. Аркаиму нужно **возвращать байты** (роуты отдают файл ассета немедленно).

Контракт v1 = **plan + execution-envelope + response**:

```
Arkaim → Media:
  POST /generate
  {
    "plan": <MediaPlan v0 JSON — байт-в-байт SCHEMAS/MEDIA_PLAN.schema.json>,
    "execution": { "media_kind": "image|video",
                   "size": "1024x1024", "preferred_backend": "auto",
                   "duration_sec": 8, "fps": 24 }   ← бывш. dispatch-поля; НЕ расширяется
  }
Media → Arkaim:
  200 { "media_id": "...", "kind": "image", "bytes_b64": "...", "backend": "comfyui",
        "workflow": "default.json" }
  4xx/5xx { "error": { "code": "...", "message": "..." } }
```

**Сознательные ограничения v1-контракта (не расширять без owner-решения):**
- нет quality (MP-F1 — мёртв; решение в §11/§16);
- нет negative до провайдера (MP-F2/F-33-2 — остаётся смысловым полем плана; Media решит отдельно);
- нет async/queue/batch/regenerate (долг MD-3 §2; v1 — только синхронный generate);
- один endpoint (без /workflows, /backends-каталогов — словарь capability/workflow/provider/backend из Foundation НЕ материализуется в v1; ADR отдельно).

## 5. External contract boundary — проверка «достаточно ли плана»

См. §4: ответ **нет** — нужен execution-envelope (бывшие dispatch-поля) и byte-response.
Проекция однозначна: `ExecutionDispatch.from_plan(plan, size, preferred_provider, duration, fps)` сегодня уже строит ровно этот конверт (dispatch.py:42–64) — **контракт v1 = сериализация dispatch + plan**. Никаких новых полей изобретать не нужно (R3-дисциплина).

## 6. ComfyUI boundary

**Где живёт ComfyUI-знание (исчерпывающе):**
- HTTP-механика + workflow: `providers/image/comfyui.py` (DEFAULT_WF: KSampler/CheckpointLoaderSimple/EmptyLatentImage/CLIPTextEncode/VAEDecode/SaveImage; `_inject_*` seed/steps/cfg/sampler/negative/size; `_resolve_ckpt` — автоподбор модели);
- workflow-файлы: `core/GENOME/workflows/default.json` (+ автозапись DEFAULT_WF при отсутствии, comfyui.py:43);
- endpoint: `COMFYUI_URL` из config Аркаима (config.py:64) + **getenv при каждом вызове** (comfyui.py:111/139 — Colab-туннель);
- WebSocket: **в Arkaim-коде отсутствует** — polling через /history (comfyui.py:147–164). «WebSocket/history» из мандата: история — poll, WS — нет;
- `/comfyui/{status,config}` роуты (visual.py:339–368) — Arkaim-API для управления бэкендом.

**Можно переносить без semantic leakage:** весь `comfyui.py` + workflows-каталог + управление URL (получает текст промпта, отдаёт байты — семантики не видит). ✅
**Нельзя без ADR:** (а) чтение workflows из GENOME_DIR (переезд пути = решение о структуре Media-repo); (б) Colab-getenv-механика (устойчивость к туннелям — сохранить?); (в) QUALITY_PRESETS (взаимодействует с мёртвым MP-F1 — перенос оживит словарь — только с owner-решением).

**Соответствие ComfyUI Agent v1 (отдельный проект `C:\cd\ComfyUI_AMD\comfyui_mcp_server.py`, MCP-обёртка):** Media Project **не поглощает** Agent v1 и не заменяет его; это два разных слоя (Agent v1 — MCP-инструментарий для DSH-сессии; Media Project — сервис Аркаима). В bootstrap их интерфейсы НЕ смешиваются: Media-проект говорит HTTP plan-контрактом, Agent v1 остаётся отдельным инструментом. Общая точка — сам ComfyUI-сервер (один и тот же endpoint может обслуживать обоих).

## 7. Provider boundary (по каждому)

| Provider | Интерфейс | Конфигурация | Execution-поля | Output | Errors | Persistence | Deps | Вердикт |
|---|---|---|---|---|---|---|---|---|
| ComfyUI | generate(prompt,(pos,neg)), health | COMFYUI_URL (config+env-перечитывание) | seed(steps/cfg/sampler/ckpt — внутренне) | bytes (jpeg/png) | raise_for_status→fail-asset | нет (байты наружу) | httpx | **Media** |
| MockImage | generate, health | — | — | bytes | — | — | — | **Media** (тестовый) |
| SVGTemplate | generate | — | — | svg-bytes | — | — | — | **Media** (или удалить — owner) |
| StableDiffusion (legacy) | generate | — | — | bytes | — | — | — | **DELETE-LATER** (не в DI) |
| ImageSequenceVideo | generate(prompt,duration,size,fps) | — | fps/duration | mp4-bytes | ffmpeg-exit | — | ffmpeg, ImageProvider | **Media** |
| MockVideo | generate, health | — | — | bytes | — | — | — | **Media** (тестовый) |
| GigaChat/OpenRouter (runtime/core/providers) | LLM-провайдеры текста | env-ключи | — | текст | — | — | httpx | **НЕ Media** (текстовый слой книги; не трогать) |

## 8. Storage / Asset boundary (lifecycle)

```
generation request → plan → dispatch → pipeline → provider → bytes
  → AssetStorage.save_file (data/visual_assets/images|videos/)
  → AssetStorage.save (SQLite visual_assets.db: метаданные+prompt_used)
  → response (SuccessResponse c asset JSON)
```

- **Semantic Asset** = VisualAsset-метаданные (title/mood/style/scene_id/prompt_used/lineage-зародыш) — **Аркаим**;
- **Execution storage** = файлы-байты + внутренние бэкенд-артефакты (workflow-состояния, tmp-кадры ffmpeg) — **Media**;
- **Lineage** — сегодня нигде не персистится (plan_id одноразовый, долг MD-3; MP-F9);
- **Ownership файлов:** v1 — **Arkaim владеет файлами ассетов** (роуты `/assets/{id}/file` отдают их из data/); Media возвращает байты, Arkaim сохраняет. Тогда двойного владельца НЕТ. Альтернатива (Media хранит файлы, Arkaim — только ссылки) — ломает 6 работающих роутов чтения и frontend → **отвергнута** для v1;
- **shot_assembler (B2)** читает файлы мимо storage — при v1-разделении остаётся рабочим (те же диски), но попадает в долг: при реальном разъезде репо потребует file-API или общий том — **явный риск R-D2, решение владельцу**.

## 9. Queue / async / batch / regenerate (только анализ)

| Путь | План? | Привязка | Вердикт для bootstrap |
|---|---|---|---|
| `/assets/generate-async` → queue.enqueue | **нет** (chapter/scene_id/overrides) | asyncio+воркеры in-process | **KEEP в Arkaim v1** (не чинить; Media — только sync) |
| `/assets/batch` → queue.enqueue_batch | нет | тот же | KEEP |
| `/assets/{id}/regenerate` | нет (style/quality) | pipeline напрямую | KEEP (долг §11-п.8) |
| `/film/assemble` (shot_assembler) | нет | ffmpeg + файлы | KEEP в Arkaim v1 (диск общий); Media-перенос — MD-5+ |

Все 4 пути — в реестре долга MD-3 (§2-строка «Regenerate/async/batch без плана»); в bootstrap **не мигрируют** (миграция была запрещена в MD-3 и остаётся отдельным решением).

## 10. Reconciliation: 11 пунктов долга MD-3 → судьба в MD-4

| # | Пункт (MD3_STAGE_CLOSURE §5) | Судьба в MD-4 | Комментарий |
|---|---|---|---|
| 1 | ExecutionDispatch + legacy-проекции (A/B/C/E) | **MD-5** (не закрывается в MD-4) | Bootstrap строит контракт из dispatch-полей, но dispatch в Аркаиме живёт до переключения роутов |
| 2 | Quality (MP-F1) | **требует owner-решения до реализации** | Перенос QUALITY_PRESETS в Media «оживит» мёртвый словарь; без решения — в контракт не входит (v1-запрет) |
| 3 | Negative до провайдера (MP-F2/F-33-2) | **MD-4/5 частично**: Media-сторона получает `plan.negative_constraints` в плане — уже может потреблять; Arkaim-часть (dispatch.negative consumers) — MD-5 |
| 4 | Video-план Route C не доходит (F-33-1) | **остаётся сознательно** в bootstrap | Сигнатура generate_video не меняется (запрет правок); фикс — MD-5 или отдельный мини-этап |
| 5 | Словари стилей ×3 (MP-F8) | **не относится к bootstrap v1**; отдельное решение | Перенос не консолидирует автоматически |
| 6 | Dead-поля шота E (MP-F10) | **остаётся сознательно** | Owner-решение из Route E-отчёта не получено |
| 7 | Висячие `__all__` (F-33-4) + lint | **не относится** | MD-5+/cleanup |
| 8 | Queue/async/batch/regenerate без плана | **не входит в bootstrap** (§9) | Отдельное решение после MD-4 |
| 9 | Персистенция планов | **закрывается частично в MD-4**: Media-сторона = `media_id` в ответе + лог планов (Media-репозиторий владеет execution-историей); Arkaim-персистенция планов — по-прежнему открытая (plan_id одноразовый) | Живого потребителя нет; не расширять |
| 10 | test_assets_new_params ×4 · TestFeedbackStore ×12 (TEMP) · COMFYUI_URL-зависимость тестов | **частично**: COMFYUI_URL-зависимость уходит с провайдером (Media-тесты в Media-repo); test_assets_new_params (ModuleNotFoundError runtime.core) — тест-инфра Аркаима, не MD-4 | |
| 11 | Git-фиксация MD-2/MD-3 | **закрыта до аудита** (9 коммитов, HEAD 6f25114) | Не актуально |

## 11. Migration options

### Вариант A — минимальный bootstrap (синхронный конверт)

**Переносится (Media-repo):** providers/image/*, providers/video/*, comfyui-workflows, ffmpeg-механика, env backend-URL; контракт = §4 (plan+execution-envelope → bytes-ответ).
**Остается (Arkaim):** все роуты, pipeline, storage, queue, film_studio (полностью), media_plan, весь visual/visualization.
**Bridge:** в adc_deps цепь провайдеров заменяется на MediaClient (тот же интерфейс `generate(prompt,size)/(prompt,duration,size,fps)` → bytes) — **единая точка подмены** (adc_deps L64–80).
**Риски:** R-A1 ComfyUI недоступен → 6 роутов отдают fail-ассеты (как сегодня при лежащем ComfyUI — поведение НЕ хуже); R-A2 Colab-туннель: getenv-механика переезжает в Media (URL в env Media-сервиса).
**Обратимость:** высокая — bridge за DI, откат = вернуть фабрику на локальную цепь.
**Тесты:** контрактные тесты Media (plan-fixture → bytes); Arkaim-тесты без изменений (DI-подмена моком MediaClient); 134 MD-3 + 207 temporal зелёные как gate.
**Критерии успеха:** (1) 5 маршрутов byte-identical поведению с локальной цепью; (2) 134/134 + 207/207; (3) ComfyUI-знание отсутствует в Arkaim-core (grep-гейт: comfyui.py, DEFAULT_WF, COMFYUI_URL не в core/CORE/providers Аркаима).

### Вариант B — полный перенос исполнительного слоя

**Переносится:** всё из A + pipeline + storage-файлы + queue + ffmpeg-сборка film_studio (execution-половина).
**Остается:** роуты-входы, media_plan, VisualAsset-схемы, film-домен.
**Риски:** R-B1 pipeline тянет SceneEngine (B1) — требует plan-only-переписывания 404-проверки и визуалов персонажей → ломает byte-identical промпты; R-B2 двойной ownership файлов (Arkaim-роуты чтения vs Media-хранилище); R-B3 queue без плана (B7) — перенос заявок «как есть» закрепляет долг; R-B4 film_studio режется пополам (домен/сборка).
**Обратимость:** низкая (массовое движение файлов).
**Тесты:** перенос 10+ тест-файлов, дублирование фикстур.
**Вердикт:** **отвергнут для v1** — нарушения сразу трёх инвариантов MD-3 (маршруты, byte-identical, scope).

## 12. Recommended option

**Вариант A.** Основания: (1) единственная точка подмены уже существует (DI-фабрика adc_deps) — миграция не трогает ни один из 5 маршрутов; (2) все HIGH-риски B1–B3 либо не задеты (B1 — pipeline остаётся), либо решаются переездом (B3 — уходит целиком), либо изолируются (B2 — не меняется); (3) обратимость полная; (4) R1 (главный риск Foundation — «соблазн продлить ComfyUI-путь в core») закрывается именно выносом провайдера, не пайплайна.

## 13. Risks

| Риск | Оценка | Митигация |
|---|---|---|
| R1 (Foundation, High): продление ComfyUI-путь в core | — | **закрывается MD-4-A**: comfyui.py покидает core |
| R3 (Foundation, Medium): контракт v0 «в вакууме» | — | **снимается**: v1-контракт = сериализация живого dispatch (§5) — не выдуман |
| Contract expansion (сверх v0) | Medium | §4-запреты; каждое новое поле — ADR |
| Duplicate ownership (Asset) | Medium | v1: Arkaim — единственный владелец файлов/метаданных; Media — stateless-байты |
| Duplicate storage | Low | Media не персистит ассеты (только media_id-лог) |
| Circular dependency | Low | не найдено (§2); контроль grep-гейтом |
| Semantic/execution leakage | Medium | B1 остаётся в Arkaim (pipeline с SceneEngine) — сознательно, план-only — MD-5; B4-реэкспорт — в долг |
| Breaking 5 routes | High при B / **Low при A** | A: DI-подмена; byte-гейты промптов |
| Breaking frontend | Low | ответы роутов неизменны (media_id не показывается фронту в v1) |
| Breaking temporal | — | не задет (temporal — read-only источник ctx) |
| Accidental ComfyUI coupling | Low | workflows+URL уезжают; Agent v1 — отдельный проект, не смешивать |
| Local/remote execution | Low | getenv-механика сохраняется в Media; health-роут — прокси |
| Migration rollback | Low при A | вернуть фабрику = 1 коммит |

## 14. Explicit forbidden scope (этот bootstrap НЕ делает)

Quality-оживление; negative-to-provider в Аркаиме; video-план до generate_video (F-33-1); правки MediaPlan/SceneContext/WorldModel/temporal; удаление legacy (dispatch/prompt-проекции/dead-поля); переносы queue/batch/regenerate/async; frontend; audio; изменение 5 маршрутов; правки film_studio-домена; консолидация словарей стилей; прикосновение к ComfyUI Agent v1.

## 15. Proposed MD-4 milestones (по варианту A; НЕ реализовано)

| # | Milestone | Содержание | Gate |
|---|---|---|---|
| M4.1 | Media-repo skeleton | пустой репо + pyproject (httpx) + контракт-схема (§4) | ADR одобрен владельцем |
| M4.2 | Провайдеры переезжают | git-mv providers/image+video → Media; Arkaim-core чист от comfyui.py | grep-гейт: 0 упоминаний ComfyUI в core/CORE Аркаима |
| M4.3 | MediaClient-bridge | в Arkaim adc_deps: цепь → MediaClient (тот же интерфейс); env MEDIA_BACKEND_URL | 134/134 MD-3 зелёные с моком |
| M4.4 | Живой прогон | Media-сервис + ComfyUI: сквозная генерация 5 маршрутов | byte-гейт промптов + 207/207 temporal |
| M4.5 | Workflows/env переезд | GENOME/workflows → Media; /comfyui-роуты — заглушка-прокси (де-публикация — MD-5) | e2e-дым |

Каждый milestone — отдельный owner-GO (как MD-3.2-маршруты).

## 16. Open decisions requiring owner GO

1. **GO/NO-GO на MD-4 вариант A** (рекомендую GO — §12).
2. **Quality (MP-F1):** переносить ли QUALITY_PRESETS в Media (оживит словарь) или оставить мёртвым (рекомендую: оставить; оживление — отдельный этап с owner-решением).
3. **Film Studio:** film_studio остаётся целиком в Arkaim в v1 (рекомендую) — или резать сборку в Media сразу (не рекомендую).
4. **Имя Media-репо и место** (рядом с arkaim/ или внутрь монорепо как отдельный сервис) — решение владельца.
5. **media_id в ответе:** показывать ли в SuccessResponse Аркаима (v1 — рекомендую скрытое поле, не в публичном контракте).
6. **B2 (shot_assembler сырые пути):** чинить file-API сейчас (не рекомендую) или оставить до MD-5 (рекомендую).

---

## Validation (выполнено)

- MD-3 неизменен: MediaPlan/маршруты/SceneContext/WorldModel/temporal/frontend — **0 изменений** (git diff: только Этап-1 тест-фикс + этот документ).
- ComfyUI Agent v1: не тронут.
- No production changes; no migration performed; no code moved.
- Git: HEAD `6f25114` (после Этапа-1 фикс отдельно); рабочий набор = `runtime/tests/test_m8_1_present_anchor.py` (Этап 1) + `docs/M8_1_TEST_ISOLATION_FIX_REPORT.md` + `docs/MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md` (этот файл).

## GO / NO-GO recommendation for MD-4 implementation

**GO** — на вариант A (минимальный bootstrap), при условиях:
1. milestone-гейты §15 (каждый — отдельный GO);
2. решения §16-2..6 приняты владельцем до M4.1;
3. R1/R3-инварианты Foundation остаются активными (grep-гейт ComfyUI в Arkaim-core).

Основание: доказанная единственность точки инстанцирования (adc_deps), контракта-двойника достаточно (dispatch), обратимость полной (DI-подмена), нулевое касание 5 маршрутов и тестов (134/134, 207/207 зелёные).

**STOP. Реализация не начата. Жду отдельного owner-GO.**
