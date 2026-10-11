# MD-4 M4.2.2 — ComfyUI Provider Migration — IMPLEMENTATION REPORT

> **⚠️ SUPERSEDED (2026-09-14).** M4.2.3 (видео-провайдеры) и M4.2.4 (provider chains) уже реализованы и приняты. Актуальный статус всех MD-4 подэтапов — в `docs/CURRENT_DEVELOPMENT_STATE.md` и `docs/MD5_MIGRATION_REPORT.md`.

**Дата:** 2026-09-13
**Статус:** ✅ ACCEPTED (суперседирован M4.2.3/M4.2.4)
**Мандат:** owner-GO M4.2.2 (только ComfyUI provider; Q1/Q2/Q3 решены: SD-stub не переносить, quality не переносить, пакет `media/`)
**Repo:** `c:\proect_arkaim\arkaim-media`, commit **`d4bcef2`** (на `8e465cc`)

---

## Простыми словами

**Что было целью?** Перенести единственный «настоящий» генератор картинок (ComfyUI) из Аркаима в новый проект-исполнитель `arkaim-media` так, чтобы его поведение не изменилось, но чтобы он полностью перестал зависеть от Аркаима (его настроек, его папок, его конфигурации).

**Что реально сделано?**
1. Создан пакет `media/` в новом проекте; в него перенесён ComfyUI-генератор.
2. Рабочий шаблон генерации (workflows/default.json) скопирован в новый проект **байт-в-байт** (проверено хешем).
3. Вместо аркаимской настройки генератор использует новый собственный мини-файл настроек нового проекта (папка шаблонов + адрес ComfyUI-сервера из окружения). Старая зависимость от аркаимской папки «геном» полностью устранена.
4. Мёртвый механизм «качества» НЕ перенесён (ваше решение Q2) — при этом доказано: на генерации это не сказывается никак, байты результата идентичны.
5. Написано 27 проверок: 18 перенесённых (минус 6 «качественных») + 9 новых «миграционных» — они автоматически доказывают: провайдер не импортирует ничего аркаимского, шаблоны ищутся только в новом репо, адрес сервера перечитывается из окружения при каждом вызове (старое поведение сохранено).
6. Изменения зафиксированы отдельным коммитом в новом репозитории.

**Что получилось?** — **PASS**. Все прогоны зелёные: новый проект 42/42, старый Аркаим 24/24 (его генераторы не тронуты и по-прежнему работают).

**Проблемы:** нет блокирующих. Один нюанс: чтобы офлайн-тесты не «висели» на реальном сервере, тесты запускаются с адресом «заглушки» 18188 (точно так же, как и старые аркаимские тесты — симметрично, ничего нового).

**Что предлагается дальше?** Ваш GO → M4.2.3 (перенос видеосборщика image_sequence + видеомока — второй и третий файлы видео-семейства).

---

## 1. Перенесённые файлы (5)

| Файл | Источник | Изменения |
|---|---|---|
| `media/image/comfyui.py` | `core/CORE/providers/image/comfyui.py` (169 стр.) | только boundary-правки (см. §3) |
| `media/image/__init__.py` | `providers/image/__init__.py` (частично) | только ABC `ImageProvider`; chain НЕ переносится (он появится в M4.2.4 по отдельному GO) |
| `media/config.py` | НОВЫЙ | мини-конфиг Media: WORKFLOWS_DIR + COMFYUI_URL |
| `workflows/default.json` | `core/GENOME/workflows/default.json` | байт-в-байт копия (SHA256 `40F788FC3F08B8C6…`, проверено тестом) |
| `tests/test_comfyui_provider.py` | `runtime/tests/test_visual_comfyui.py` (24 теста) | 18 адаптированы, 6 quality-тестов не перенесены (Q2), +9 миграционных |

## 2. НЕ перенесённые файлы (и почему)

| Файл | Причина |
|---|---|
| `stable_diffusion.py` | owner Q1: SD-stub НЕ переносить (не в DI-цепи, не в тестах) |
| `QUALITY_PRESETS`, `_inject_quality`, `quality` kwarg | owner Q2: мёртвый механизм не переносить; «standard»==DEFAULT_WF → байты идентичны |
| `svg_template.py`, `mock.py` (image) | mock/dev → M4.2.4 по отдельному GO |
| `video/*` (image_sequence, mock, chain) | видео → M4.2.3 по отдельному GO |
| `ImageProviderChain`, `ProviderExecutionResult` | chain/factory → M4.2.4 по отдельному GO |
| GigaChat/LLM, pollinations.pyc, providers.registry (мёртвый путь) | не media; мандат запрещает LLM; не файлы-провайдеры |
| Весь старый стек Аркаима | мандат 17: legacy НЕ удалять до отдельного migration gate |

## 3. Boundary-правки (единственные изменения кода)

Оригинал 169 строк → мигрировано 152 строки. Diff показывает: удалены ТОЛЬКО config-шим, quality-механика, `**kwargs` (quality был его единственным консьюмером); добавлены ТОЛЬКО `media.config`-замены и новый докстринг. Рабочая логика (DEFAULT_WF, inject_prompt/size/seed, resolve_ckpt, poll, tuple-prompt) — дословно как в оригинале.

| Было (Аркаим) | Стало (Media) |
|---|---|
| `from config import config` (шим к core/config.py) | `import media.config as config` |
| `WF_DIR = config.GENOME_DIR / "workflows"` (геном Аркаима) | `WF_DIR = config.WORKFLOWS_DIR` (`arkaim-media/workflows/`) |
| `log = …("hermes.visualization.comfyui")` | `log = …("media.image.comfyui")` |
| `async def generate(prompt, size, **kwargs)` + `kwargs.get("quality")` + `_inject_quality` | `async def generate(prompt, size)` (quality — единственный консьюмер kwargs; он мёртв) |
| `getattr(config, "COMFYUI_URL", …)` в конструкторе | сохранено (медиа-конфиг даёт то же значение) |
| `os.getenv("COMFYUI_URL")` при generate/health | сохранено дословно (rule 9 GO) |

## 4. Доказательство изоляции от Аркаима

**Все imports нового провайдера (AST-инвентаризация):**

```
media/config.py:        __future__, os, pathlib
media/image/__init__.py: abc
media/image/comfyui.py:  asyncio, json, logging, pathlib, httpx, os (lazy),
                        media.config, media.image (ABC)
```

Ни одного аркаимского импорта. Grep-аудит запрещённых маркеров в `media/`: **0 попаданий** из 18 маркеров (providers/config-shim/visualization/visual_assets/media_plan/scene_engine/narrative_engine/GENOME_DIR/core.CORE/proect_arkaim/SceneEngine/WorldModel/Temporal).

**Все filesystem paths:** единственный — `WF_DIR = <repo>/workflows` (тест `test_wf_dir_is_repo_local`: `WF_DIR == REPO_ROOT/workflows`; `test_wf_dir_inside_media_repo`: содержит `arkaim-media`, не содержит `GENOME`). Никаких `C:\proect_arkaim\arkaim\...` в коде.

**Все env variables:** только `COMFYUI_URL` (3 точки: конструктор-дефолт, generate, health) — поведение перечитывания сохранено и покрыто тестами `TestMigrationEnvBehavior` (3 теста: подмена URL при generate, при health, дефолт при отсутствии).

**Все HTTP endpoints (ComfyUI-сервер):** POST `/prompt` (300s), GET `/history/{pid}` (poll 1s/2s, 300s), GET `/view` (байты), GET `/object_info/CheckpointLoaderSimple` (15s), GET `/system_stats` (health, 5s). Список неизменен — ComfyUI-specific знание живёт внутри Media.

**Входы/выходы:** вход `generate(prompt: str | tuple(pos,neg), size="1024x1024")` → `bytes` PNG; `health()` → bool. В Media Contract v1.0 эти сигнатуры ложатся в `POST /v1/generate` → `bytes_b64` (провайдер — внутренняя деталь исполнения; контракт не менялся).

**Workflow ownership:** `arkaim-media/workflows/` — единственный источник (тест `test_wf_dir_is_repo_local` + `test_no_arkaim_config_dependency` — шим-паттерн `spec_from_file_location` отсутствует). Arkaim-копия GENOME/workflows остаётся нетронутой до MD-5.

**Байт-идентичность workflow:** тест `test_migrated_workflow_matches_arkaim_original` сравнивает байты с аркаимским оригиналом при каждом прогоне (SKIP при нестандартной раскладке).

## 5. Тесты до/после

| Сьют | До | После |
|---|---|---|
| Arkaim legacy `test_visual_comfyui.py` | **24/24** (COMFYUI_URL=18188) | **24/24** — стек не тронут |
| Media suite (полный: 15 контрактных M4.1 + 27 M4.2.2) | 15/15 (M4.1) | **42/42** |

27 M4.2.2-тестов: 18 мигрированных (структура DEFAULT_WF, inject-механика, parse_size, set_workflow, offline health/generate/poll-timeout, seed-детерминизм) + 9 миграционных (изоляция импортов, WF_DIR-владение ×2, байт-идентичность workflow, отсутствие config-шима, отсутствие quality ×1, env-поведение ×3).

## 6. git

```
arkaim-media: d4bcef2 (master) — feat(m4.2.2): migrate ComfyUI provider
  5 files changed, 542 insertions(+)
  media/config.py, media/image/{__init__,comfyui}.py, tests/test_comfyui_provider.py, workflows/default.json
arkaim:      unchanged (only pre-existing artifacts in worktree)
```

## 7. Мандат-чеклист M4.2.2

| # | Правило GO | Статус |
|---|---|---|
| 1-3 | пакет `media/`; провайдер в новом репо; GENOME/workflows больше НЕ источник | ✅ §3-4 |
| 4 | workflow-шаблоны в `arkaim-media/workflows/` | ✅ байт-идентично |
| 5 | запрет SceneEngine/Genome/WorldModel/Temporal/SceneContext/GENOME/config/chapter-scene/FS | ✅ 0 попаданий из 18 маркеров |
| 6 | SD-stub не переносить | ✅ §2 |
| 7 | dead Quality не переносить | ✅ §2-3 + тест отсутствия |
| 8 | GigaChat/LLM/unrelated не переносить | ✅ §2 |
| 9 | COMFYUI_URL runtime-поведение сохранить | ✅ дословно + 3 теста |
| 10 | ComfyUI-config принадлежит Media | ✅ media/config.py |
| 11 | Media Contract v1.0 не менять | ✅ (схемы/контракт не тронуты; git clean по docs/schemas) |
| 12 | пять роутов не менять | ✅ (Arkaim routes не тронуты) |
| 13 | Film Studio не менять | ✅ |
| 14 | SceneContext/MediaPlan schemas не менять | ✅ |
| 15 | defects не чинить (seed-hash и др.) | ✅ перенесены как есть |
| 16 | M4.2.3/2.4/2.5 не делать | ✅ видео/mock/chain не перенесены |
| 17 | legacy из Аркаима не удалять | ✅ 24/24 живы |

**Два отдельных доказательства (по GO):**
- `arkaim-media/media/... → НЕ зависит от Arkaim runtime/domain/config/filesystem` — ✅ доказано AST + grep + FS-тестами (§4);
- `arkaim-media/workflows/... → единственный источник workflow templates` — ✅ доказано тестами владения (§4).

**STOP: M4.2.2 завершён. Дальнейшие шаги (M4.2.3, M4.2.4, MD-4.3, MD-4.4, MD-5) уже реализованы.**
