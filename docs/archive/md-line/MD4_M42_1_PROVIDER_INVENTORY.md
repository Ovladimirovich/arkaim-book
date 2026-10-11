# MD-4 M4.2.1 — Forensic Provider Inventory — ОТЧЁТ

**Дата:** 2026-09-13
**Статус:** DOCUMENTED (инвентаризация; код НЕ перенесён)
**Мандат:** owner-GO M4.2 → этап M4.2.1: forensic inventory конкретных providers перед переносом. STOP после отчёта.
**База:** прочитаны полностью ВСЕ файлы provider-стека (не выборочно): 7 .py + 1 workflow + 4 тест-файла + фабрики + роуты.

---

## Простыми словами

**Что было целью?** До переноса «генераторов картинок и видео» в новый проект — составить их точную опись: из каких файлов состоят, что импортируют, какие настройки/пути/сети используют, и главное — нет ли у них скрытых связей со «знанием книги» Аркаима.

**Что реально сделано?** Прочитан каждый файл генераторов (7 штук: ComfyUI, mock, SVG-шаблон, Stable Diffusion, видеосборщик, видеомок, две «цепи»). Проверено всё: импорты, настройки окружения, доступ к файлам, сетевые вызовы, входы/выходы, скрытые зависимости. Плюс: фабрики сборки, роуты, тесты (24 теста ComfyUI + 2 цепи), конфиги.

**Что получилось?** — **PASS** (инвентаризация полная).

**Ключевые находки простым языком:**
1. **Провайдеры чистые от «знания книги»** — ни один не читает сцены, геном, мировую модель, время. Единственная незаконная связь: ComfyUI-провайдер читает свои рабочие шаблоны (workflows) из папки «генома» Аркаима — при переносе эта папка переедет в новый проект (обязательная правка, без неё граница нарушена).
2. Найден «мёртвый груз», который переносить НЕ нужно: Stable Diffusion-заглушка (не подключена ни к чему живому), пресеты «качества» (тот самый мёртвый Quality — де-факто никогда не вызывается снаружи), остатки старых импортов.
3. Перезапуск URL «Colab-туннеля» прямо посреди генерации — провайдер перечитывает настройку адреса из окружения при каждом вызове; поведение сохранить.
4. Один нюанс для будущего моста: служебные роуты Аркаима `/comfyui/*` заглядывают в приватный атрибут провайдера `_base_url` — мост должен его продолжать выставлять, чтобы ничего не сломалось.

**Проблемы:** нет блокирующих. Три решения нужны от вас (в конце отчёта, §10) — все с моими рекомендациями.

**Дальше (предложение, не автоматически):** ваш GO → M4.2.2 (перенос ComfyUI-провайдера в arkaim-media).

---

## 1. Состав стека (полное дерево)

```
core/CORE/providers/
├── image/                          ← МЕДИА-семейство (перенос в M4.2)
│   ├── __init__.py        (4590 b) ← ABC + ImageProviderChain + импорт всех 4
│   ├── comfyui.py         (8217 b) ← единственный «настоящий» генератор
│   ├── mock.py            (1109 b) ← SVG-заглушка (dev/тесты)
│   ├── svg_template.py    (1251 b) ← SVG-шаблон (fallback-семейство)
│   └── stable_diffusion.py(1689 b) ← ЗАГЛУШКА, вне DI-цепи (кандидат на неперенос, §10-Q1)
├── video/                          ← МЕДИА-семейство (перенос в M4.2)
│   ├── __init__.py        (1242 b) ← ABC + VideoProviderChain
│   ├── image_sequence.py  (3483 b) ← кадры→ffmpeg
│   └── mock.py            (1187 b) ← SVG-заглушка
├── gigachat.py            (453 b)  ← LLM-семейство — НЕ МЕДИА, НЕ переносится (мандат: LLM запрещён)
├── gigachat_token_refresh.py (1354 b) ← LLM — НЕ переносится
└── [пустоши: pollinations.pyc — STALE байт-код несуществующего файла; registry.py НЕ существует — импорты на него в narrative_engine мертвы/fallback]

Рабочий шаблон: core/GENOME/workflows/default.json (1434 b) — KSampler/CheckpointLoader/EmptyLatent/CLIP×2/VAEDecode/SaveImage, ckpt=cyberrealistic_v80.safetensors
```

**Фабрики (DI, adc_deps.py L63–83):** image = `Chain[ComfyUIProvider(base_url=config.COMFYUI_URL), MockImageProvider()]`; video = `Chain[ImageSequenceVideoProvider(image_provider=цепь_изображений), MockVideoProvider()]`. Stable Diffusion и SVGTemplate НЕ в живой цепи — только в import-списке `__init__`.

## 2. ComfyUIProvider (comfyui.py, 169 строк) — главный

| Аспект | Факт (строки) |
|---|---|
| **Импорты** | asyncio, json, logging, pathlib.Path, httpx, `providers.image` (ABC), `config` (L10) |
| **Config** | `config.GENOME_DIR / "workflows"` → WF_DIR (L13); модульный side-effect `WF_DIR.mkdir(parents, exist_ok)` при ИМПОРТЕ (L14); `config.COMFYUI_URL` дефолт при конструировании (L30) |
| **Env** | `os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")` — ПЕРЕЧИТЫВАЕТСЯ при каждом `generate()` (L111) и `health()` (L139), комментарий «in case Colab tunnel changed»; автоматическая подмена `self._base_url` при изменении |
| **Filesystem** | чтение `WF_DIR/<name>.json` (L36–39); запись `default.json` при отсутствии (L41–44, из DEFAULT_WF); WF_DIR = **core/GENOME/workflows Аркаима** (см. §6-К1) |
| **HTTP (ComfyUI)** | POST `/prompt` (timeout 300, L129–131); GET `/history/{pid}` (poll 1с локально / 2с remote, timeout 300, L155–157); GET `/view` (байты результата, L161–162); GET `/object_info/CheckpointLoaderSimple` (динамический выбор чекпоинта, timeout 15, L89); GET `/system_stats` (health, timeout 5, L144) |
| **Вход** | `generate(prompt, size="1024x1024", **kwargs)`; prompt может быть `tuple(pos, neg)` (L115); kwargs: только `quality` (дефолт "standard", L119) |
| **Выход** | `bytes` (PNG) |
| **Внутренняя логика** | DEFAULT_WF (L16–24); `_inject_prompt` (первый CLIPTextEncode=+, второй=−, fallback "blurry, low quality", L46–51); `_inject_size` (EmptyLatentImage, L53); `_inject_seed` = `hash(prompt) & 0x7FFFFFFF` (L118 — детерминирован в рамках процесса, НЕ между рестартами — известный дефект, не чинить); QUALITY_PRESETS + `_inject_quality` (L68–81 — живёт, но никто снаружи не передаёт quality → де-факто всегда standard; см. §10-Q2); `_resolve_ckpt` (приоритет: sd_xl/sdxl/realistic/cyberrealistic/juggernaut/dreamshaper/v1-5/sd15, иначе первый, L99–104); `_parse_size` fallback 1024×1024 (L166) |
| **Скрытые зависимости Arkaim** | 1) `config.GENOME_DIR` — чтение workflows из доменной зоны GENOME (ЕДИНСТВЕННАЯ настоящая FS-связь с Аркаимом); 2) геномный workflows/default.json — контент (см. §6) |

## 3. Остальные image-провайдеры

**ImageProviderChain (`__init__.py`):** ABC (`generate(prompt,size)/health`); `ProviderExecutionResult(provider_name, provider_kind, bytes)`; `_provider_name` (attr `provider_name`/`name` → имя класса без «Provider/Image», lower); `_provider_kind` (mock/svg/template в имени → «fallback», иначе «real»); алиасы `comfy→comfyui`, `svg→mock` (L47–56); порядок: `auto`=как задан, `real`=real+fallback, точное имя=first (L58–69); `generate_with_metadata(prompt, size, preferred_provider)` — health-check каждого, лог, `traceback.print_exc()` в stdout при падении (L95), финал `RuntimeError("All image providers failed…")`. В конце — импорт ВСЕХ 4 провайдеров (L104–107), включая непрошиваемые SD/SVG.

**MockImageProvider (mock.py):** чистый SVG (`#1a1a1a`, «Mock Visualization»), BytesIO-импорт мёртв; ноль внешних зависимостей; `health()=True`.

**SVGTemplateProvider (svg_template.py):** чистый SVG-каркас («Scene Visualization»); ноль зависимостей; `health()=True`. Не в DI-цепи; импортируется `__init__` и scripts/visual_scene.py.

**StableDiffusionProvider (stable_diffusion.py):** заглушка над A1111 `/sdapi/v1/txt2img` (localhost:7860, timeout 60) + base64-decode; **health() возвращает False при пустом списке моделей**; НЕ в DI-цепи, НЕ в тестах — только import в `__init__`. Кандидат на неперенос (§10-Q1).

## 4. Video-семейство

**VideoProviderChain:** ABC `generate(prompt, duration=8.0, size="1024x576", fps=24)/health`; chain: health→generate каждого по порядку; финал `RuntimeError`. Импорт image_sequence+mock в конце.

**ImageSequenceVideoProvider (image_sequence.py):** входы — prompt/duration/size/fps; total_frames=fps*duration (8с×24=192 кадра!); каждый кадр — вызов `image_provider.generate(frame_prompt, size)` c суффиксом `, frame N of M, cinematic` (L31); fallback — SVG-placeholder при падении кадра; ffmpeg через `asyncio.create_subprocess_shell` (`-framerate {fps} -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart`); health = `ffmpeg -version` exit 0; ФС — только `tempfile.TemporaryDirectory`; внешнего HTTP нет; `shutil`-импорт мёртв. **Сквозная зависимость: берёт ЛЮБОЙ объект с методом `generate(prompt, size)`** — в DI это вся image-цепь (ComfyUI→Mock). Это означает: видео-провайдер в Media будет использовать Media-собственную image-цепь — граница замыкается внутри Media. ✔

**MockVideoProvider (mock.py):** SVG с анимацией круга; `prompt[:50]` в текст; asyncio-импорт мёртв; `health()=True`.

## 5. Кто использует providers (полная карта потребителей)

| Потребитель | Что берёт | Миграционный статус |
|---|---|---|
| `runtime/core/adc_deps.py` L64–80 | фабрики цепей (image/video) | единственная точка подмены (M4.4) |
| `core/CORE/visual_assets/pipeline.py` | `generate_with_metadata(**dispatch.image_kwargs())` {prompt,size,preferred_provider} (L161–163, 470); `image_provider.generate(prompt, size)` fallback (L168–180, 310); video: `generate(prompt, duration, size, fps)` (L274) | Arkaim, не переносится; ПОСРЕДНИК |
| `runtime/core/routes/visual.py` L339–460 | `/comfyui/status` (health + **приватный `_base_url`** L349), `/comfyui/config` GET/POST (env + запись runtime/.env), `/providers/list` (`_base_url` L397), `/providers/status` (health каждого) | Arkaim; не меняется; риск моста §8-R2 |
| `core/CORE/visualization/__init__.py` L18 | реэкспорт ImageProvider/Chain | audit B4 → D-6 debt MD-5 |
| scripts/ (generate_scenes*.py, visualize_scene.py) | прямые импорты провайдеров | dev-утилиты Arkaim; в M4.2 не трогаем |
| runtime/tests/ (см. §7) | импорты провайдеров | остаются против СТАРОГО стека |
| narrative_engine (story/api_routes, research/*) | `from providers.registry import …` | **МЁРТВЫЙ путь** (файла нет → try/except fallback). LLM-семантика, к media не относится. Не переносится. |

## 6. Критические находки (K) для GO M4.2.2

| # | Находка | Следствие для переноса |
|---|---|---|
| **K1** | `WF_DIR = config.GENOME_DIR/"workflows"` = `core/GENOME/workflows` — ComfyUI-провайдер читает шаблоны из ГЕНОМНОЙ зоны Аркаима | **Обязательная правка при переносе**: Media читает workflows из СВОЕГО каталога (напр. `arkaim-media/workflows/`), default.json копируется туда. Это не «новая возможность», а разрыв единственной незаконной FS-связи (мандат: провайдер не читает Arkaim filesystem). Модульный `WF_DIR.mkdir` при импорте сохраняется как есть (безвреден на новом пути) |
| **K2** | `config`-импорт провайдера — 10-строчный шим `core/CORE/config.py`, реэкспортирующий аркаимский `core/config.py` (GENOME_DIR, COMFYUI_URL из env) | Media получает СОБСТВЕННЫЙ мини-config (WORKFLOWS_DIR + COMFYUI_URL через `os.getenv`) — «минимальная общая утилита» по мандату п.5, без доменной семантики |
| **K3** | Seed = `hash(prompt)` — недетерминирован между рестартами процесса (Python hash randomization) | Дефект исторический; мандат 6: НЕ чинить. Переносится как есть |
| **K4** | COMFYUI_URL перечитывается из env при каждом generate/health (Colab-tunnel) + автоподмена base_url | Поведение сохранить: Media тоже перечитывает env при вызове |
| **K5** | `quality`-параметр и QUALITY_PRESETS: живой код, но pipeline/dispatch НИКОГДА не передаёт quality → всегда "standard", а standard-preset ставит те же 25/7.0/euler, что уже в DEFAULT_WF → **inject_quality("standard") идемпотентен DEFAULT_WF** | Убедительное основание НЕ переносить quality-механику: генерация байт-идентична и без неё (§10-Q2 — рекомендация) |
| **K6** | pollinations: STALE .pyc без .py; providers/registry.py не существует (мёртвые импорты narrative_engine под try/except) | Не переносить ни то, ни другое (не файлы-провайдеры вообще) |
| **K7** | GigaChat-файлы в providers/ — LLM-семейство | НЕ переносить (мандат: LLM запрещён; имя каталога совпадает — разные семьи) |
| **K8** | default.json в Аркаиме существует (1434 b, DEFAULT_WF-эквивалент с реальным чекпоинтом cyberrealistic_v80) | Копировать в Media-workflows при M4.2.2; Arkaim-копия остаётся до MD-5 |

## 7. Тестовое покрытие (что переедет/останется)

| Тест | Зона | Что проверяет | M4.2-судьба |
|---|---|---|---|
| `runtime/tests/test_visual_comfyui.py` (24 теста) | ComfyUI | inject_prompt/size/seed, parse_size, offline health/generate (порт 18188), DEFAULT_WF-структура, timeout poll, set_workflow, **TestComfyUIQuality (6 тестов на пресеты)** | Адаптировать в Media-тесты (WF_DIR→новый путь; порт 18188 для offline; seed-hash поведение). Quality-тесты — если Q2 решено «не переносить», их в Media не будет |
| `runtime/tests/test_visual_assets_provider_chain.py` (2) | Chain+pipeline | chain metadata (preferred= comfyui), pipeline пишет provider в asset | Остаётся в Arkaim (тестирует pipeline+старый стек — не удаляем); Media получает свой аналог chain-теста |
| `runtime/tests/test_visualization.py` (mock import) | mock | генерация mock-ответа | Остаётся; Media повторяет логику в своих тестах |
| `runtime/tests/test_assets_new_params.py` (providers_status) | роуты | статус-роуты через registry | Остаётся (роуты не меняются) |
| `test_contract.py` L28/L43, `test_isolation.py` L124 | архитектура | gateway/telegram/business НЕ импортируют core.providers | Остаётся, не затрагивается |

## 8. Риски переноса (для будущих GO)

| # | Риск | Митигация |
|---|---|---|
| R1 | Байт-идентичность генерации: seed-hash, inject-порядок, negative-fallback, poll-интервалы | Перенос кода «как есть», менять только config-путь (K1/K2); Media-тесты зеркалят offline-случаи аркаим-теста |
| R2 | Роуты `/comfyui/*`, `/providers/*` читают `provider._base_url` (приватный атрибут) и `providers[0]` (порядок цепи!) | Будущий мост MediaClient (M4.4) обязан: выставлять `_base_url`, поддерживать `health()`, стоять первым в цепи — иначе поведение роутов меняется. Задокументировано; сами роуты НЕ трогаем |
| R3 | `dispatch.image_kwargs()` = {prompt,size,preferred_provider} — плана НЕ содержит; контракт требует {plan, execution} | Мост собирается в точке, где план уже есть (pipeline Route C, generate_image сигнатура содержит plan+dispatch) — M4.4-деталь, не M4.2 |
| R4 | ImageSequenceVideoProvider тянет image-цепь (внутри Media — своя); 192 кадра×ComfyUI на 1 GB VRAM — медленно | Поведение сохранено как есть; производительность не менялась и не меняется |
| R5 | Обе копии workflows (Arkaim GENOME + Media) разъедутся по содержимому | Пока Arkaim-стек не удалён (мандат 9), источник для живой работы Аркаима — его GENOME-копия; Media-копия обслуживает Media. Синхронизация не требуется (одинаковый старт); фиксация единственного источника — MD-5 |

## 9. Предлагаемый состав переноса M4.2.2–M4.2.4 (для решения owner)

```
arkaim-media/  (после M4.2)
├── media/                          ← новый пакет (имя — на решение M4.2.2)
│   ├── image/
│   │   ├── __init__.py            ← ABC + Chain + ProviderExecutionResult (как есть, БЕЗ правок логики)
│   │   ├── comfyui.py             ← как есть, КРОМЕ: WF_DIR → Media-workflows; config → media-config
│   │   ├── mock.py                ← как есть
│   │   └── svg_template.py        ← как есть (вопрос Q1b решает судьбу import-строки)
│   ├── video/
│   │   ├── __init__.py            ← как есть
│   │   ├── image_sequence.py      ← как есть (ffmpeg-логика не меняется)
│   │   └── mock.py                ← как есть
│   └── config.py                  ← НОВЫЙ мини-конфиг: WORKFLOWS_DIR + COMFYUI_URL=os.getenv(...) (K2)
├── workflows/default.json         ← КОПИЯ аркаимского (K8)
└── tests/                          ← адаптация comfyui/chain-тестов
```

НЕ переносится (и остаётся в Arkaim нетронутым до MD-5): весь старый стек на месте (мандат 9), gigachat-семейство (K7), pollinations.pyc (K6), scripts-утилиты, visualization-реэкспорт (D-6 debt), роуты.

## 10. Открытые вопросы (нужны решения в GO на M4.2.2)

| # | Вопрос | Рекомендация |
|---|---|---|
| **Q1** | Переносить ли `stable_diffusion.py` (заглушка A1111-API, вне DI-цепи, вне тестов)? | **НЕ переносить**: мёртвый код, не в мандате (мандат называет ComfyUI/video/mock). Если не переносим — в Media-`__init__` убираем его import-строку (единственная правка, поведение живой цепи не меняется — SD не в DI) |
| **Q1b** | Переносить ли `svg_template.py`? | **Переносить**: это живой dev-fallback (импортируется `__init__` и dev-scripts), «mock/dev provider» по духу мандата; правка не нужна |
| **Q2** | Переносить ли QUALITY_PRESETS/_inject_quality/параметр quality? | **НЕ переносить**: owner «Quality мёртв» (§16-2) + мандат «не оживлять Quality» + K5 доказал идемпотентность standard к DEFAULT_WF → генерация без quality-механики байт-идентична. Хвост-правка: `generate(**kwargs)` теряет параметр — единственное поведенческое изменение: передача quality теперь невозможна (она и так никогда не происходила) |
| **Q3** | Имя python-пакета в Media | `media/` (короткое, без доменной семантики) |

## 11. Мандат-чеклист M4.2.1

- [x] файлы — §1 (полное дерево, размеры);
- [x] imports — §2–4 (по каждому файлу, включая мёртвые импорты);
- [x] зависимости — §2–4 (httpx/ffmpeg/ABC/цепь);
- [x] env/config — §2 (COMFYUI_URL×3 точки, GENOME_DIR, .env: `COMFYUI_URL=http://127.0.0.1:8188` + закомментированный colab-tunnel);
- [x] filesystem access — §2–4 (GENOME/workflows — K1; tempdir — §4; НИКАКИХ других путей);
- [x] external HTTP — §2 (5 эндпоинтов ComfyUI), §3 (A1111×2 — мёртвый);
- [x] входные параметры — §2–4 (включая tuple-prompt и **kwargs);
- [x] выходные параметры — §2–4 (bytes везде, ProviderExecutionResult у цепи);
- [x] скрытые зависимости от Arkaim — §2 (K1/K2 — только GENOME-workflows+config-шим; доменных зависимостей НЕ найдено: ни SceneEngine, ни Genome-контент, ни WorldModel, ни temporal — провайдеры получают ТОЛЬКО prompt/size/duration/fps).

## 12. Проверка мандата M4.2 на этом этапе

- Код не перенесён ✔ (0 файлов скопировано);
- Arkaim не изменён ✔ (git status: только 3 предыдущих док-артефакта + тест-фикс Этапа 1);
- Пять маршрутов не тронуты ✔ (роуты только читались);
- Quality не оживлён ✔ (только описан; рекомендация Q2 — против переноса).

**STOP: M4.2.1 завершён. Жду owner-GO на M4.2.2 (и решения Q1/Q2/Q3).**
