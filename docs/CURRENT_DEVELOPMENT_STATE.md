# CURRENT DEVELOPMENT STATE — фактическая карта проекта «Наследие Аркаима»

**Дата аудита:** 2026-09-14 · **Обновлено:** 2026-09-18 (после MD-6 + решений D1-D3: F3 ACCEPTED; F4 ACCEPTED & CLOSED 2026-09-18; fresh-start не merge)
**Тип документа:** восстановление контекста существующей разработки (audit-only; никакой новый код/архитектура не проектировались)
**Аудитор:** ИИ-агент (DSH), по мандату владельца «полное восстановление контекста, ничего нового»
**Метод:** чтение реальных файлов/кода/git-истории обеих реп; фактические запуски тест-сьютов (pytest, node-runner); хеш-сверки; live-проверка ComfyUI-сервера. Наличие файла НЕ считалось доказательством работы; каждый существенный факт снабжён источником.

---

## Простыми словами (для владельца)

1. **Что было целью?** — Остановить реализацию и восстановить полную фактическую карту всего, что уже сделано, чтобы любой новый инженер/ИИ понял проект без истории переписки.

2. **Что реально сделано?** — Проверены два репозитория (arkaim и arkaim-media), весь git-журнал, все ADR, ~45 milestone-отчётов, ключевые модули кода; фактически запущены 10 тест-сьютов (все основные зелёные: 141/141 MD-3+MD-4, 237/237 temporal, 42/42 media, 85/85 web-v2 и др.); собраны 14 технических долгов и 15 несоответствий документации/кода. **MD-5 завершён** (commit `d73d29a`): ExecutionDispatch удалён, /comfyui/* депубликованы, все 5 маршрутов A–E работают напрямую через MediaPlan. **MD-6 закрыт** (commit `4be2a40`): 24 файла восстановлены в git (routes/providers/media_plan/tests).

3. **Что получилось?** — PASS: этот документ — фактическая карта. Самое важное: **текущая точка = MD-6 CLOSED / F4 ACCEPTED & CLOSED**. Все MD-этапы (1–6) и F1–F4 реализованы и приняты. F4: 5 capabilities (community fix + presence/email/drafts/moderation), 80 тестов green, 5 страниц в next build, backend не тронут. **STOP после F4, ждёт owner-GO на следующий этап**.

4. **Есть ли проблемы?** — Да, перечислены в §13–14. Главная: часть документов в корне repo (README/AGENTS/PROJECT_STATE) описывает состояние на август 2026 и не знает о MD-линии и arkaim-media; 4 теста падают по старой причине (не связаны с текущей работой). **Одно новое:** mtime-flaky тест `test_routes_abcd_files_untouched` — исправлен допуском 0.5s (pre-existing, падал и на чистом HEAD).

5. **Что предлагается дальше?** — Ничего не делаю. Жду вашего GO (варианты в §16).

---

## 1. Executive Summary

**Проект** — «Наследие Аркаима»: цифровое сознание книги. Backend FastAPI (:8642) + «BookPulse» (ядро знаний без LLM) + World Engine (547 сущностей) + temporal-модель мира (12 эпох + Present + экстраполяция будущего) + визуальная генерация (5 маршрутов через MediaPlan v0) + 2 фронтенда (legacy `arkaim-web` на 34 страницы; новый `arkaim-web-v2` на 10 страниц) + мобильное приложение (React Native, заготовка).

**Текущая фаза разработки** — MD-6 «Legacy cleanup + contract hardening» завершён (commit `4be2a40`). Внутри MD-5 ExecutionDispatch удалён, /comfyui/* депубликованы. F3 «Время мира» ACCEPTED/CLOSED (85/85 тестов). F4 «Предложения/Очереди» ACCEPTED & CLOSED 2026-09-18 (5 capabilities, 80 тестов, 5 страниц, backend 0 изменений). Внутри MD-4 завершены все подэтапы включая M4.2.3 (video-провайдеры, `0256140`), M4.2.4 (chains+mock+svg, `4ccfd8e`), M4.3 (MediaClient bridge, `81612b7`), M4.4 (live route gate, `b5d399d`), M4.5 (частично в MD-5). **MEDIA_CONTRACT v1.0 ACCEPTED** (arkaim-media `f0327cd`). Следующий этап требует отдельного owner-GO.

**Git-факт (arkaim):** branch `master`, HEAD `4be2a40` (MD-6), рабочий набор: только `core/CORE/genome/history/index.json` (автозапись). **Git-факт (arkaim-media):** branch `master`, HEAD `d4bcef2`, рабочее дерево чистое. **Frontend v2:** arkaim-web-v2/src/ — 19 страниц (14 F1-F3 в fresh-start + 5 F4 ACCEPTED); F4-код untracked на master (не закоммичен). Полный F1-F4 ACCEPTED.

**Ключевые решения, не требующие повторного обсуждения:** ADR_ARKAIM_MEDIA_BOUNDARY (граница двух проектов), ADR_MEDIA_PLAN_V0 (контракт MediaPlan + 10 owner-decisions), ADR_TEMPORAL_WORLD_MODEL (4 решения A–D о времени мира), ADR M8.1 (Present-якорь). Все — ACCEPTED/канонические.

**Тесты (фактические прогоны этого аудита):** MD-3+MD-4 suite 141/141 PASS (после MD-5); temporal chunk 237/237 PASS; md2/m7/m10.x 74/74 PASS; visual-family 45 passed/4 skipped; visual+assets+film+md2 114 passed/4 failed (4 pre-existing `ModuleNotFoundError: runtime.core`); arkaim-media 42/42 PASS (при полной ФС; 1 sandbox-артефакт); arkaim-web-v2 85/85 PASS.

---

## 2. Project Purpose

| Вопрос | Факт | Источник |
|---|---|---|
| Исходная цель | «Цифровое сознание книги „Наследие Аркаима“ (О Владимирович)»: система с живым ядром (Pulse), знающим книгу **без LLM**; LLM — только «голос» (микрофон) | README.md:1–53; AGENTS.md «Обзор проекта» |
| Конечная пользовательская задача | Читатель спрашивает книгу → Pulse ищет ответ в слоях → BookVoice формулирует (LLM при низкой уверенности) → IdentityLayer.validate() — финальная проверка; плюс исследование мира/времени, визуализация сцен, сообщество | AGENTS.md «Архитектурные принципы»; docs/AI_ENGINEER_GUIDE.md:18–39 |
| Главный продукт | Монорепо `arkaim` (backend + ядро + фронтенды + данные книги) | структура репо; git remote `github.com/Ovladimirovich/arkaim` |
| Отдельный проект/подсистема | **arkaim-media** — исполнитель генерации изображений/видео (выделен из Аркаима по ADR MEDIA BOUNDARY) | ADR_ARKAIM_MEDIA_BOUNDARY Decision 1; arkaim-media/docs/MEDIA_CONTRACT.md |
| Проекты рядом | ComfyUI-сервер (`C:\cd\ComfyUI_AMD\`, порт 8188 — работает, проверено HTTP 200) и ComfyUI Agent v1 (MCP-обёртка `comfyui_mcp_server.py`) — **не часть** ни Аркаима, ни Media-проекта; DSH-инструментарий, границы не смешивать | MD4_PRE §6; live-проверка этого аудита |
| Текущий этап | **MD-6 CLOSED** (2026-09-18, коммит `4be2a40`). MD-5 ACCEPTED (2026-09-14, `d73d29a`). **F4 ACCEPTED & CLOSED** (2026-09-18). Весь MD-4 закрыт включая M4.2.3/M4.2.4/M4.3/M4.4. Следующий — требует отдельного owner-GO. | MD5_MIGRATION_REPORT §STOP; arkaim-media `f0327cd` |
| Сознательно отложено | F5+ фронт; audio; quality-оживление; queue/batch/regenerate-миграция; C2 завершён; D-10 завершён | MD3_STAGE_CLOSURE §5; ADR_TEMPORAL §6; MEDIA_DIRECTION_FOUNDATION §DEFERRED |
| F4 статус | **ACCEPTED & CLOSED 2026-09-18** (5 capabilities: community fix + presence/email/drafts/moderation; 80 тестов green; 5 страниц в next build; backend 0 изменений; 4 misplaced WIP-page → F2/F3/F5/separate) | Owner-GO ПРИНЯТО |

---

## 3. Project Boundaries

**Аркаим владеет (домен книги):** Pulse-слои, World Engine, Knowledge Graph, RAG, temporal-модель, genome, SceneContext, MediaPlan (смысловое задание), все HTTP-маршруты A–E, Film Studio (целиком, owner-решение §16-3), AssetStorage (файлы ассетов + SQLite-метаданные), queue, оба фронтенда, mobile.

**Media-проект владеет (исполнение):** провайдеры генерации (сейчас только ComfyUI перенесён), workflows-каталог, ffmpeg-механика (частично: image_sequence ещё в Аркаиме), backend-config (COMFYUI_URL), `media_id`-реестр.

**Запрещено связывать:** (ADR_ARKAIM_MEDIA_BOUNDARY Decision 5, инварианты)
1. Core Аркаим — media-agnostic: ни ComfyUI/workflow/node/checkpoint в новых доменных модулях.
2. Никаких прямых Arkaim→ComfyUI HTTP вне Media-контракта.
3. LLM не управляет media-execution; агент не управляет ComfyUI.
4. PromptBuilder не выбирает capability.
5. Scene Context — единственный источник всех планов.
6. Temporal — read-only для media; планы наследуют provenance.
7. Media Plan ≠ Workflow ≠ Node Graph ≠ Capability ≠ Provider; Asset ≠ Media Request ≠ File.

**Временные мосты (легальные до MD-5):** ExecutionDispatch (`core/CORE/media_plan/dispatch.py` — «TEMPORARY MIGRATION BRIDGE — REMOVE IN MD-5»); legacy prompt-проекции A/B/C/E; MediaPlan-конверт в контракте v1 (5 execution-полей).

---

## 4. Repository Map

| Репозиторий | Путь | Branch/HEAD | Назначение |
|---|---|---|---|
| **arkaim** (монорепо) | `c:\proect_arkaim\arkaim` | master / `4be2a40` | Всё, кроме исполнения генерации; F4 ACCEPTED (код untracked, не закоммичен); fresh-start (`48c19c9`) — reference |
| **arkaim-media** | `c:\proect_arkaim\arkaim-media` | master / `d4bcef2` ← `8e465cc` (root) | Исполнитель генерации (Media Contract v1.0 DRAFT + ComfyUI-провайдер) |
| ComfyUI-сервер (вне реп) | `C:\cd\ComfyUI_AMD\` | — | Генерация, HTTP :8188, DirectML 1GB VRAM |
| ComfyUI Agent v1 (вне реп) | `C:\cd\ComfyUI_AMD\comfyui_mcp_server.py` | — | MCP-инструмент DSH-сессий; НЕ часть Media-проекта |

**arkaim (ключевые каталоги):**

| Путь | Что это |
|---|---|
| `runtime/` | FastAPI-бэкенд: `core/main.py` (app), `core/adc_deps.py` (DI, 24+ сервиса), `core/routes/` (9 роут-файлов), `auth/`, `bot/`, `memory/`, `tests/` (66 тест-файлов) |
| `core/CORE/` | Ядро знаний: `pulse/` (слои, voice), `narrative_engine/` (world_engine, temporal/, story/, research/), `knowledge_graph/`, `intelligence/` (RAG), `visualization/` (слой 1), `visual/` (слой 2, SceneContext), `visual_assets/` (слой 3, pipeline), `media_plan/` (MediaPlan v0), `film_studio/`, `providers/` (image/video + gigachat-LLM), `genome/`, `GENOME/` (данные + workflows/), `KNOWLEDGE/` (50+ JSON), `CHROMA_DB/` |
| `arkaim-web/` | Legacy-фронтенд: Next.js 16, React 19, AntD 6, 34 страницы, FSD, vitest+playwright. **Заморожен** (не развивается до завершения arkaim-web-v2, FRONTEND_ARCHITECTURE §12) |
| `arkaim-web-v2/` | Новый фронтенд (F1–F4 ACCEPTED; 14 страниц в `fresh-start:48c19c9` + 5 F4 страниц untracked); typed-контракты из OpenAPI (289 путей), RBAC-матрица (298 маршрутов), 27+ test-файлов на диске |
| `arkaim-mobile/` | React Native + Expo, 8 экранов (chat, reading, login, profile…), общий API-слой. Не отдельный git-репо |
| `docs/` | 100+ документов: ADR/ (3), MD-серия, M-серия (0–10.2), F-серия (1–3), temporal-серия, старые гайды |
| `SCHEMAS/` | 5 JSON-Schema: MEDIA_PLAN, CHARACTER, ENTITY, QUOTE, THEME |
| `ADR/` (корень) | **ПУСТАЯ директория** — ADR-файлы фактически в `docs/ADR/` (несоответствие AGENTS.md) |

**arkaim-media (13+ файлов, по git + тестовый прогон):**
`docs/MEDIA_CONTRACT.md` (v1.0 **ACCEPTED**, arkaim-media `f0327cd`), `schemas/` (4 схемы), `examples/` (3), `tests/` (2 файла, 42+ теста), `media/config.py`, `media/image/{__init__,comfyui}.py`, `workflows/default.json` (SHA256 = аркаимскому, проверено).

---

## 5. Architecture Map

### 5.1 Слои (фактические, runtime-путь)

```
Читатель → arkaim-web(-v2) (:3000/:3001) → Next rewrites → FastAPI (:8642)
  → auth (JWT cookie / API-key) → routes/* (9 роутеров: book, visual, assets,
    film_studio, reader, temporal, temporal_updates, world_engine)
  → adc_deps ServiceRegistry (DI) → core/CORE/*
      Pulse (слои знаний, без LLM) ↔ BookVoice (LLM: GigaChat→OpenRouter)
      WorldEngine (547 сущностей) · WorldModel (temporal, 12 эпох+today)
      KnowledgeGraph · RAG (ChromaDB) · ReaderMemory (SQLite)
  Визуальный контур (канонический путь MD-3):
    request → VisualContextBuilder.build_scene_context* (SceneContext =
      VisualContext + scene_extras{temporal,source_refs,integrity})
      → MediaPlanBuilder → MediaPlan (pydantic extra=forbid, 22 поля)
      → ExecutionDispatch (TEMPORARY)
      → legacy prompt projection (byte-identical)
      → AssetGenerationPipeline → ImageProviderChain [ComfyUI, Mock]
        / VideoProviderChain [ImageSequence(ffmpeg), Mock]
      → AssetStorage (SQLite data/visual_assets.db + files data/visual_assets/)
```

### 5.2 Зависимости и точки сопряжения

- **Единая точка DI:** `runtime/core/adc_deps.py` — все media-сервисы инстанцируются только в фабриках (L63–109: image/video chain, pipeline, store, queue, film_store; L184–193: visual_context_builder с world_model). Это же — назначенная точка подмены цепи на MediaClient в M4.4 (MD4_PRE §11).
- **Media-модуль `core/CORE/media_plan/`** импортирует ТОЛЬКО visual/ (SceneContext-слой) — ни providers, ни visual_assets (ADR_MEDIA_PLAN_V0 Decision 1; проверено структурой файлов).
- **ComfyUI знает только:** adc_deps (регистрация), 2 тест-файла, visualization/__init__ (реэкспорт B4), scripts/. Роуты знают только цепь (MD4_PRE §2.3).
- **Циклических зависимостей нет** (MD4_PRE §2.2).

### 5.3 Стабильное / мосты / legacy

| Класс | Компоненты |
|---|---|
| **Стабильное (канон, заморожено контрактами)** | MediaPlan v0 (22 поля + BANNED-инвариант), SceneContext (extras 3), 5 маршрутов A–E, temporal-модель (M8.1 + B1/C1), M10.2 pending-updates, Voice-протокол, genome, Media Contract v1.0 DRAFT (в arkaim-media), миркосхемы SCHEMAS/ |
| **Временные мосты (умирают в MD-5)** | ExecutionDispatch; legacy-промпт-проекции (PromptBuilder A/B, build_asset_prompt C/E); dispatch-конверт в контракте v1; `visualization/__init__.py:18` реэкспорт провайдеров (B4/D-6); `/comfyui/*` роуты (D-5); GENOME/workflows-копия в Аркаиме |
| **Legacy/debt** | visualization/prompt_builder (SD-промпты, словарь 1); GenerationParams в VisualAsset (execution-поля в домене); stable_diffusion.py (не в DI); pollinations.pyc (stale); providers.registry-импорты (мёртвые, 4 файла); PromptComposer как DI-точка (D5, мёртвая); словари стилей ×3 (MP-F8) |

---

## 6. Implemented Milestones

Формат статусов: CLOSED (принят владельцем) / ACCEPTED (принят, ждёт финальной фиксации) / IMPLEMENTED+TESTED (ждёт owner-решения) / DEFERRED.

### 6.1 Ранняя линейка (июль 2026, зафиксирована CHANGELOG 1.0.0/2.0.0)

| Milestone | Что сделано | Commit-ориентир | Статус |
|---|---|---|---|
| BookPulse v1 | 4 слоя Pulse, BookVoice, ReaderMemory, Presence, EvolutionTracker, 349 тестов | `CHANGELOG.md` [1.0.0] 2026-07-09 | CLOSED |
| World Engine v2 | 547 сущностей, 287 связей, 55 форм, 10 режимов, 10 API; слои Pulse → 10; 34 страницы | `CHANGELOG.md` [2.0.0] 2026-07-20; commits 635868e, 0d393cb | CLOSED |
| World Explorer (15 этапов) | Подсистема исследования мира: 111 тестов, 24 роута, история в SQLite, WebSocket | commits a9f251e…f888913 (Этапы 1–16) | CLOSED |
| Community/Enhanced | Уведомления, комментарии, профиль, расширенный поиск, crowdfunding | commits 23ac86b…e4179be | CLOSED |
| GigaChat→OpenRouter цепь | LLM-провайдеры; HF/Pollinations удалены | commits 9a7f3dd, c38f64d; удаление: 963322a | CLOSED |

### 6.2 Temporal-линейка M0–M10.2 (сентябрь 2026)

| Milestone | Задумано | Реализовано | Тесты (по отчётам) | Статус | Документ |
|---|---|---|---|---|---|
| M0 audit | Карта архитектуры перед temporal | аудит 0 кода | — | CLOSED | M0_ARCHITECTURE_AUDIT.md |
| M1 canon+provenance | Иерархия источников, 8 категорий ProvenanceCategory | SourceHierarchy, ProvenanceTag | — | CLOSED | M1_CANON_PROVENANCE.md |
| M2 temporal model | TemporalNode/Relation/Graph | модель + WorldModel-мост | — | CLOSED | M2_TEMPORAL_MODEL.md |
| M3 reconstruction | BACKWARD-реконструкция путей | TemporalReconstructionEngine | — | CLOSED | M3_TEMPORAL_RECONSTRUCTION_MODEL.md |
| M4 integration | WorldModel.get_temporal_chain (M4-мост) | цепочка PRECEDES в API | — | CLOSED | M4_INTEGRATION_MODEL.md |
| M5 temporal integration | API-роуты /book/temporal/* | 7 роутов temporal.py | 41 тест | CLOSED | M5_TEMPORAL_INTEGRATION_MODEL.md; commit 1f7c5db |
| M7.2 epoch visual | POST /visualize/epoch — temporal→visual мост | роут B | test_m7_epoch_visual | CLOSED | M7_2_PRE_AUDIT |
| M8 future extrapolation | Сценарии будущего от якоря | FutureExtrapolator, FUTURE_EXTRAPOLATION-маркировка | test_m8_future_extrapolation | CLOSED | M8_FUTURE_EXTRAPOLATOR_IMPLEMENTATION.md |
| **M8.1 present anchor** | PRESENT=методологический узел, HYPOTHESIS; orphan-удаление; enrichment якоря | reconstruction_engine 563–621; node.present_anchor | 13/13 PASS (отчёт) | CLOSED | M8_1_ARCHITECTURE_DECISION.md |
| M9 temporal-aware Expansion | ExpansionLayer отвечает на temporal-запросы через facade | intent-detection, provenance-теги | 28/28 audit, 38/38 | CLOSED | M9_SPEC.md «ACCEPTED & CLOSED» |
| M10 pending updates | Детектор→pending→confirm/reject (in-memory) | temporal_update_manager | 432/432 | CLOSED | M10_* |
| **M10.2 API-обёртка** | 7 HTTP-эндпоинтов очереди, RBAC editor/admin | routes/temporal_updates.py | 16/16 audit | **ACCEPTED & CLOSED 2026-09-08** | M10_2_POST_AUDIT.md |

### 6.3 Frontend-линейка F1–F3 (arkaim-web-v2, сентябрь 2026)

| Milestone | Реализовано | Тесты (факт аудита) | Статус |
|---|---|---|---|
| FRONTEND_ARCHITECTURE | Проект нового фронтенда (не код) | — | DOCUMENTED |
| F1 фундамент | arkaim-web-v2: каркас, auth, RBAC-матрица 298, typed-контракты (OpenAPI 289), WS/SSE, 33 теста | 85/85 (текущий прогон) | ACCEPTED |
| F2 «Диалог с книгой» | Экраны /, /reading, /profile, /status; SourceBadge; B1/B2-фиксы | (входят в 85/85) | ACCEPTED & CLOSED |
| F3 «Время мира» | /temporal (12 эпох, provenance-бейджи, today-карточка, сценарии будущего) + /temporal/queue (M10.2 UI); ProvenanceBadge; path-param-контракты; F2-A1/A2-фиксы | 85/85 суммарно (14/14 live-smoke по отчёту) | **ACCEPTED & CLOSED 2026-09-18** (owner-GO D1) |
| F4 «Предложения/Очереди» | Clean F4: 5 capabilities — community (fix BLOCKER+MEDIUM+LOW) + presence/email/drafts/moderation (4 new pages + 26 tests). Misplaced WIP disposition: ask/graph/world-explorer→F2; upload→F3; admin→F5; analytics→separate milestone. `/proposals/temporal` УЖЕ В F3 (temporal/queue). Backend: 0 изменений. TS: 0 ошибок в F4-коде. next build: 5/5 маршрутов green. Tests: 80 F4-suite green. | 9 test-файлов (60 pre-existing + 26 new), 5 страниц (1 fix + 4 new), 3 контракта, envelope +16 записей | **ACCEPTED & CLOSED 2026-09-18** (owner-GO ПРИНЯТО) |
| **F-12 film-studio БД** | Production DB repair: `_migrate_schema()` idempotent guard for `film_shots.quality` column; 5 regression tests (real SQLite schema); backup verified; 3 shots preserved; PUT quality API confirmed; commit `c022e77` | 5 tests PASS; 45 film-related tests PASS; 1117 lines committed (scope contamination: `shot_assembler.py` +342 restored from `48c19c9`, not F-12 scope) | **FUNCTIONALLY ACCEPTED / CLOSED 2026-09-23** (forensic audit: SCOPE CONTAMINATION partial — `shot_assembler.py` out of F-12 scope but byte-identical to pre-deletion state) |

### 6.4 MD-линейка (media-контур, сентябрь 2026)

| Milestone | Реализовано | Файлы | Тесты | Статус |
|---|---|---|---|---|
| **MD-1 Foundation** | Forensic-аудит визуального стека + ADR границы | MEDIA_DIRECTION_FOUNDATION.md, docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md | 0 (документы) | CLOSED (основа линейки) |
| **MD-2 Scene Context** | SceneContext=VisualContext+extras{temporal,source_refs,integrity}; 5 маршрутов на единый вход; DEPRECATED-метки; F-11 fix | scene_context.py (new), visual_context*.py, pipeline.py, routes/{visual,assets,film_studio}.py, adc_deps.py | 23+15 новых; **контроль аудита: MD-2-family 438/1 pre-existing** | **CLOSED / FINAL GREEN 2026-09-11** (MD2_POST_AUDIT §0) |
| **MD-3 MediaPlan v0** | Контракт (22 поля, BANNED), Builder, Dispatch; все 5 маршрутов мигрированы (3.2 A/B/C/D/E по одному, SHA-сверки промптов); SCHEMAS/MEDIA_PLAN.schema.json; 2 deprecation-метки (D1/D5); реестр | media_plan/{schemas,builder,dispatch}.py; routes; pipeline; тесты 7 файлов (134) | **134/134 PASS (этот аудит)** | **CLOSED 2026-09-12** (MD3_STAGE_CLOSURE) |
| **MD-4 bootstrap** | Вариант A (минимальный): отдельный репо arkaim-media; M4.1–M4.5 все закрыты | см. §6.5 | — | **CLOSED** |
| **MD-5 integration** | ✅ ACCEPTED (2026-09-14, commit `d73d29a`): ExecutionDispatch удалён, /comfyui/* депубликованы, все 5 маршрутов A–E через MediaPlan | 141/141 | **CLOSED** |

### 6.5 MD-4 подэтапы (текущая работа)

| Подэтап | Что сделано | Артефакты | Тесты (факт) | Статус |
|---|---|---|---|---|
| Pre-audit | Инвентаризация исполнительного слоя, MOVE/KEEP-таблицы, варианты A/B | MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md | 0 (документ) | CLOSED (GO получен) |
| Этап 1: test-isolation fix | M8.1-тест не восстанавливал синглтон → M9 падал при совместном прогоне; try/finally `we._temporal_engine=None` | `runtime/tests/test_m8_1_present_anchor.py` (незакоммичен в рабочем дереве); M8_1_TEST_ISOLATION_FIX_REPORT.md | 207/207 temporal (подтверждено этим аудитом: 237/237 расширенный чанк) | TESTED; ждёт коммита |
| **M4.1 bootstrap** | Репо arkaim-media + Media Contract v1.0 (4 схемы, 5-полей execution-конверт, 7 кодов ошибок, ownership-таблица) + пример из живого кода | arkaim-media root-commit `8e465cc` (13 файлов) | 15/15 | **ACCEPTED & CLOSED** (MEDIA_CONTRACT утверждён `f0327cd`) |
| M4.2.1 inventory | Forensic-опись 7 провайдеров; K1–K8; Q1/Q2/Q3 | MD4_M42_1_PROVIDER_INVENTORY.md | 0 (документ) | CLOSED (GO получен; Q1=SD не переносить, Q2=quality не переносить, Q3=пакет media/) |
| **M4.2.2 ComfyUI migration** | comfyui.py → media/image/ (152 стр., boundary-правки: WF_DIR→repo-local, config→media.config, quality удалён); workflows/default.json байт-в-байт (SHA `40F788FC…` — проверено этим аудитом); media/config.py | arkaim-media commit `d4bcef2` (5 файлов) | **42/42 PASS (этот аудит; 1 падение = sandbox-артефакт, при полной ФС — зелёный)** | **ACCEPTED & CLOSED** |
| **M4.2.3 video** | image_sequence.py + mock.py → media/video/ (ffmpeg-логика как есть, тест-зеркало) | arkaim-media commit `0256140` | **42/42 PASS** | **ACCEPTED & CLOSED** |
| **M4.2.4 chain/mock/svg** | ImageProviderChain + MockImage + SVGTemplate → media/image/ (chain/factory) | arkaim-media commit `4ccfd8e` | **PASS** | **ACCEPTED & CLOSED** |
| **M4.3 MediaClient-bridge** | Замена цепи в adc_deps: legacy providers → MediaClient по контракту v1.0 | arkaim commit `81612b7`; media `5922dcc` | **15/15 PASS** | **ACCEPTED & CLOSED** |
| **M4.4 живой прогон** | Live byte-gate: 5 маршрутов A–E через MediaClient, 207/207 тестов | arkaim `b5d399d`; media `0d10396` | **207/207 PASS** | **ACCEPTED & CLOSED** |
| **M4.5 workflows/env** | workflows/env переезд + частичная де-публикация | частично в MD-5 | — | **ЧАСТИЧНО CLOSED (в MD-5)** |

---

## 7. Accepted ADR / Decisions

Три ADR физически находятся в `docs/ADR/` (пустой корневой `ADR/` — см. §14-1).

### 7.1 ADR_TEMPORAL_WORLD_MODEL (docs/ADR/, 2026-09-09)
**Статус-пометка в файле: PROPOSED — ожидает ACCEPTED** — НО по факту последующих реализаций (B1+C1 выполнены, F3 построен на его инвариантах, TEMPORAL_API_ALIGNMENT_REPORT называет его «ACCEPTED») решения признаны каноническими. Это несоответствие статуса — см. §14-4.

| Решение | Суть | Что запрещает | Реализовано |
|---|---|---|---|
| **A. TODAY** | `temporal_today` — методологический TemporalNode (HYPOTHESIS, confidence 1.0), В графе, БЕЗ relations; единственная фабрика `present_anchor()` | Создавать Today-узлы иначе; today в chains; AUTHOR_CANON для Present | ✅ engine (M8.1) + API B1 (nodes включает today) |
| **B. Relation** | PRECEDES — единственный тип оси; ребро только между соседями; дубли запрещены; DEVELOPS_FROM/TRANSFORMS_INTO — только человек через M10.2 | Новые типы ради оси; бидирекционные рёбра; автосоздание контекстных связей | ✅ (11 PRECEDES — live-факты) |
| **C. Provenance** | ProvenanceTag на каждом узле/ребре; категории: узлы AUTHOR_CANON+EXTERNAL_SOURCE/HYPOTHESIS; рёбра DERIVED/RECONSTRUCTION **НИКОГДА AUTHOR_CANON**; FUTURE_EXTRAPOLATION для M8; UI обязан показывать бейджи | AUTHOR_CANON на рёбрах оси; UI-самодеятельность; отдельный реестр provenance | ✅ кроме C2 (рёбра до сих пор несут фабричный AUTHOR_CANON — finding, не исправлен) |
| **D. Anchor** | `temporal_arkaim_era` единственный якорь; ArkaimAnchor-dataclass — только источник enrichment; alias-правило документное | Второй anchor-узел; третья сущность | ✅ (orphan удаляется engine-путём) |
| Инвариант §5 | Фронтенд не достраивает temporal graph | Синтетические связи, «скрытые линии», вычисление пропущенных эпох | ✅ (F3-тесты + live) |

Unresolved (не блокируют): U1 provenance для будущего computed-path; U2 теги на рёбрах (C2); U3 bounds «2025 CE» у today.

### 7.2 ADR_ARKAIM_MEDIA_BOUNDARY (docs/ADR/, 2026-09-09)
По MEDIA_DIRECTION_FOUNDATION и M4.1-отчёту — принят владельцем (GO на MD-линию). См. §3 выше (5 Decisions + инварианты + findings MB-1…MB-5). Реализовано: граница зафиксирована документально (MD-1), контракт MediaPlan (MD-3), bootstrap Media-репо (M4.1–M4.2.2 частично). Не реализовано: физический вынос всего стека (B1 pipeline остаётся в Аркаиме до MD-5), де-публикация /comfyui/* (D-5), чистка GenerationParams (MB-3).

### 7.3 ADR_MEDIA_PLAN_V0 (docs/ADR/, 2026-09-11)
**Статус: ACCEPTED** (10 owner-decisions). Ключевое: MediaPlan — доменный контракт без execution-семантики (BANNED 20 полей вкл. quality); negative_constraints — смысловое поле; provenance+lineage обязательны; ExecutionDispatch — временный мост (REMOVE IN MD-5); PA-F1 закрыт на уровне плана; frontend не меняется; версионирование 0.1.0 + JSON-Schema; порядок MD-3.1→3.2→3.3 со STOP на каждом; STRICTLY FORBIDDEN-список (MD-4 в scope MD-3 был запрещён — теперь MD-4 идёт своим чередом по отдельным GO). Реализовано: полностью (MD-3 CLOSED).

### 7.4 ADR M8.1 (документ-решение, не в docs/ADR/)
`docs/M8_1_ARCHITECTURE_DECISION.md` — PRESENT-семантика (HYPOTHESIS-исправление, computed path вместо relation). Реализовано в engine (E2 ADR_TEMPORAL). Канонизировано ADR_TEMPORAL Decision A/D.

### 7.5 Замороженные Architecture Decisions владельца (упомянуты ADR_MEDIA_BOUNDARY Decision 3)
Asset≠File, Capability≠Workflow, Provider≠Model, Provider≠Backend, Workflow≠Node Graph, ComfyUI≠Agent, LLM без прямого доступа к ComfyUI, Agent не управляет ComfyUI напрямую, PromptBuilder не выбирает capability, media-execution-backend не входит в domain logic, core media-agnostic — «зафиксированы здесь впервые как канон».

### 7.6 Owner-решения MD-4 (M4.1-отчёт §2)
Вариант A (минимальный bootstrap); Quality мёртв; Film Studio целиком в Arkaim; репо arkaim-media рядом; media_id разрешён наружу; shot_assembler не чинить (D-2); ExecutionDispatch ≠ постоянный API (REMOVE IN MD-5). Решения M4.2.1: Q1 SD-stub не переносить; Q2 quality не переносить; Q3 пакет `media/`.

---

## 8. Current Git State

### 8.1 arkaim

| Параметр | Факт |
|---|---|
| Branch | `master` |
| HEAD | `4be2a40` «feat(md-6): legacy cleanup + contract hardening — restore untracked routes/providers/media_plan» |
| Remote | origin → https://github.com/Ovladimirovich/arkaim.git |
| Теги/стэши | нет / пусто |
| Working tree | **CLEAN** (только CRLF noise в `core/DEVELOPER_GUIDE.md`, `core/PROJECT_BIBLE/README.md` — pre-existing) |
| Дополнительные ветки | `fresh-start` (`48c19c9`) — полный F1-F3 frontend закоммичен; `push-test-20260916` (`2a6c1b3`) — частичный frontend; по решению D3: не merge, оставить как reference/history |

**Последние тематические коммиты (новее → старее):**
- `4be2a40` feat(md-6): legacy cleanup + contract hardening
- `282c3aa` fix: restore frontend/backend files and initialize Book OS provider
- `4f9469d` fix(metrics+orchestrator) + feat(Book OS provider init)
- `3dd15ef` feat(runtime): initialize Book OS provider at startup
- `1e12df7` fix(orchestrator): rename provider_latency local var
- `57d85f0` Merge branch g0-clean
- `acbc7a3` docs(phases): отчёты всех завершённых фаз M0..M10, F1..F3, temporal-alignment
- `ae9c8f8` chore(scripts): comfyui-генератор сцен; HF/Pollinations-скрипты удалены
- `1f7c5db` feat(temporal): API-роуты /book/temporal/* + тесты
- `7a19386` feat(frontend): F-фазы + arkaim-web-v2
- `963322a` chore(providers): удаление HuggingFace/Pollinations провайдеров
- `ff40ef4` feat(temporal): M-фазы временной модели мира
- `6b60d4e` docs(media): MD-2/MD-3 отчёты, ADR MediaPlan v0
- `5023de2` feat(media): MD-2 + MD-3 contract v0
- `323c666` feat: version genome data for portability
- (ранее: серия Этапов 1–16 World Explorer, комьюнити, GigaChat и т.д.)

**Незавершённый WIP:** arkaim-web-v2 frontend (19 страниц + 27 тестов) — код на диске, не в git master (untracked). Полный F1-F4 ACCEPTED; F4-код untracked (не закоммичен). По решению D3 — не merge.

### 8.2 arkaim-media

Branch `master`; HEAD `f0327cd` «docs(medium): accept MEDIA_CONTRACT v1.0 — фактически реализован и используется» (родитель `c942043`, далее `0d10396`→`ca2c3a5`→`4f60229`→`4ccfd8e`→`6f39b76`→`0256140`→`d4bcef2`→`8e465cc`). Полный MD-4 подэтапы M4.1–M4.4 закрыты, MEDIA_CONTRACT v1.0 ACCEPTED. Рабочий чистый (только __pycache__, игнорируется). Remote нет (локальный репозиторий).

### 8.3 Расхождения документации и кода

См. §14.

---

## 9. Current Contracts

### 9.1 Контракт Arkaim ↔ Media (внешний, v1.0 DRAFT)

| Аспект | Факт |
|---|---|
| Владелец | Совместно: документ в arkaim-media/docs/MEDIA_CONTRACT.md; MediaPlan-часть — байт-в-байт аркаимская `SCHEMAS/MEDIA_PLAN.schema.json` (SHA256 `B52B7E7A…50F635` — сверено) |
| Транспорт | HTTP POST `/v1/generate` (единственный endpoint; синхронный) |
| Данные вниз | `plan` (MediaPlan v0.1.0) + `execution` (ровно 5 полей: media_kind, size, preferred_backend, duration_sec, fps) |
| Данные вверх | `media_id`, kind, bytes_b64, content_format, backend, workflow_used? |
| **НЕ передаётся (физически запрещено схемами additionalProperties:false)** | quality, model, checkpoint, steps, cfg, sampler, seed, workflow, node_graph, provider (→ preferred_backend), comfyui, loras, denoise, negative как execution-поле |
| Ошибки | 400 INVALID_REQUEST / 422 UNSUPPORTED_MEDIA_KIND·UNSUPPORTED_SIZE·BACKEND_NOT_AVAILABLE / 429 OVERLOADED / 500 GENERATION_FAILED / 504 GENERATION_TIMEOUT; тело `{error:{code,message,retryable}}` |
| Временный элемент | execution-конверт = сериализация живого ExecutionDispatch (dispatch.py:42–64) — «не новый дизайн»; умирает в MD-5 |
| Статус | **ACCEPTED & CLOSED** (arkaim-media `f0327cd` — «accept MEDIA_CONTRACT v1.0»). Де-факто использовался с M4.3 (MediaClient bridge). |

### 9.2 Внутренние контракты Аркаима (замороженные)

| Контракт | Где | Владелец |
|---|---|---|
| MediaPlan v0 (pydantic extra=forbid + BANNED) | core/CORE/media_plan/schemas.py | Arkaim (MD-3 CLOSED) |
| SceneContext (extras: temporal/source_refs/integrity) | visual/scene_context.py + visual_context.py | Arkaim (MD-2 CLOSED) |
| 5 маршрутов A–E (ответы byte-identical) | routes/visual.py, assets.py, film_studio.py | Arkaim; подмена цепи — только за DI |
| Temporal API (14 путей: 7 M4/M8 + 7 M10.2) | routes/temporal.py, temporal_updates.py | Arkaim (B1/C1 done; C2 deferred) |
| AssetStorage/файлы ассетов | visual_assets/storage.py + data/ | **Arkaim — единственный владелец** (контракт §6) |
| Frontend↔Backend | OpenAPI-слепок 289 путей (web-v2/contracts/) + RBAC-матрица 298; F1-F4 ACCEPTED (19 страниц), backend 0 изменений | backend — источник истины |
| LLM-цепь GigaChat→OpenRouter | runtime/core/provider_registry.py + core/CORE/providers/gigachat.py | Arkaim (LLM ≠ media) |

### 9.3 Границы ответственности и временные контракты

- **shot_assembler (Arkaim)** читает ассеты по сырым путям с диска (не через storage-API) — работает, пока оба проекта на одной машине; **задокументированный обход (D-2), НЕ чинится до MD-5** (контракт §6, owner §16-6).
- **queue/async/batch/regenerate** — 4 живых пути БЕЗ плана (chapter/scene_id/overrides; style/quality) — миграция была запрещена в MD-3, остаётся отдельным решением после MD-4 (MD4_PRE §9).
- **`/comfyui/*` и `/providers/*` роуты Аркаима** читают приватный атрибут `_base_url` и `providers[0]` — будущий мост MediaClient обязан их поддерживать (M4.2.1 R2); роуты не трогать.
- **Genome-history churn:** каждый запуск бэкенда/тестов дописывает снапшот в `core/CORE/genome/history/index.json` + плодит файлы GENOME/history — runtime-артефакт, «не source», но пачкает git-статус (наблюдение F3 §12-4).

---

## 10. Current Visual Production Project State (arkaim-media)

| Вопрос | Факт |
|---|---|
| Зачем создан | Исполнитель генерации: Аркаим производит смысл (Scene Context → Media Plan), Media исполняет (workflow → provider → backend → bytes). Основа: ADR_ARKAIM_MEDIA_BOUNDARY; цель — вынести знание ComfyUI из ядра Аркаима (MB-1) |
| Что существует | Контракт v1.0 DRAFT (4 схемы + 15 контрактных тестов); пакет `media/` (config.py + image/{__init__,comfyui}.py); workflows/default.json; 27 ComfyUI-тестов; README/pyproject/gitignore |
| Провайдеры реально используемые | **Перенесён: ComfyUIProvider** (media/image/comfyui.py). НЕ перенесены: MockImage, SVGTemplate (→M4.2.4), StableDiffusion (не переносится, Q1), ImageSequenceVideo + MockVideo (→M4.2.3), цепи (→M4.2.4). **Аркаим-цепь в adc_deps по-прежнему работает на СТАРОМ стеке** (ComfyUI из core/CORE/providers) — двойная копия провайдера сознательна до MD-5 (мандат 17: legacy не удалять) |
| Где workflows | `arkaim-media/workflows/default.json` (SHA256 = аркаимскому `core/GENOME/workflows/default.json`, байт-в-байт; проверено этим аудитом). Аркаим-копия остаётся до MD-5 |
| Что перенесено | Только 5 файлов M4.2.2 (см. §6.5). Аркаим-side не менялся |
| Что в исходном проекте | Весь остальной исполнительный слой: pipeline, storage, queue, film_studio (включая ffmpeg-сборку), providers/{mock,svg,SD,video}, media_plan/dispatch |
| Контракт с основным проектом | MEDIA_CONTRACT.md v1.0 (§9.1): план+конверт → байты+media_id; Arkaim владеет ассетами; Media stateless |
| Сознательно НЕ переносится | quality-механика (Q2); StableDiffusion (Q1); GigaChat/LLM (K7); pollinations.pyc/registry.py (K6); pipeline/storage/queue (вариант B отвергнут); Film Studio; frontend; audio; ComfyUI Agent v1 (не поглощается) |
| Дефекты, перенесённые как есть | seed = hash(prompt) (недетерминирован между рестартами — мандат «не чинить»); перечитывание COMFYUI_URL при каждом вызове (сохранено) |

---

## 11. Deferred / Rejected Work

### 11.1 Отвергнутые архитектурные варианты (по ADR/аудитам)

| Вариант | Почему отвергнут | Источник |
|---|---|---|
| Провайдеры остаются в core Аркаима | Уже показало цену: 3 слоя визуала, provider-специфика в доменных схемах | ADR_MEDIA_BOUNDARY Decision 1 Rejected |
| Arkaim→ComfyUI HTTP с workflow-параметрами | Утечка knowledge об исполнении в Аркаим | там же |
| Present как метаданные вне графа | today невидим для graph-алгоритмов; точка старта «из ниоткуда» | ADR_TEMPORAL Decision A Rejected |
| Present как исторический узел с relation к arkaim | Ложная историчность; нарушает запрет | там же |
| DEVELOPS_FROM как канон оси / новый тип CONNECTS_TO / бидирекционные рёбра | Интерпретация вместо порядка; новые сущности; дубли | ADR_TEMPORAL Decision B Rejected |
| Provenance в отдельном реестре / только SourceLevel / UI-вычисление | Рассинхрон; потеря семантики; нарушение инварианта | ADR_TEMPORAL Decision C Rejected |
| Третий anchor-узел / оставить оба / удалить ArkaimAnchor-dataclass | Новая миграция; двойное знание; потеря curated-provenance | ADR_TEMPORAL Decision D Rejected |
| MD-4 вариант B (полный перенос pipeline+storage+queue+ffmpeg) | Нарушение 3 инвариантов MD-3 сразу; byte-identical невозможен | MD4_PRE §11 |
| Media хранит файлы ассетов (альтернатива v1) | Ломает 6 работающих роутов чтения + frontend | MD4_PRE §8 |
| Перенос quality в Media | Оживит мёртвый словарь; owner «quality мёртв»; standard==DEFAULT_WF → байты идентичны и без него | M4.2.1 K5/Q2 |

### 11.2 Отложенные задачи (дорога)

MD-5 (adapter на контракте; де-публикация /comfyui/*; удаление ExecutionDispatch/legacy-проекций/GENOME-workflows-копии; D-6 реэкспорт; B1 plan-only pipeline); C2 ✅ (provenance-теги на PRECEDES-рёбрах, AUTHOR_CANON→DERIVED); D-10 ✅ (SharedSettings: PROVIDER_CHAIN, PROVIDER_FAILURE_THRESHOLD, PROVIDER_COOLDOWN_SECONDS); F4+ фронт (community/explorer/studio экраны по FRONTEND_ARCHITECTURE §4); audio-домен (extension point, схема не определяется); quality-решение MD-4/5; negative-to-provider (MP-F2, MD-4/5); video-план в Route C (F-33-1, сигнатура pipeline); F-12 film-БД (пересоздание/миграция — решение владельца); persistence M10.2-истории; M25 Experience; консолидация словарей стилей (MP-F8); async/queue/batch/regenerate миграция; переименование measurement-класса SceneContext (visual_models.py:7 — перегрузка имени, MD-3+).

### 11.3 Запрещённые направления (действующие)

Из ADR_MEDIA_PLAN_V0 Decision 7 (STRICTLY FORBIDDEN для MD-3 — исторические, но дух сохранён): параллельный SceneContext; параллельная prompt-архитектура; оживление quality; изменение provider semantics вне adapter/dispatch. Из ADR_MEDIA_BOUNDARY инвариантов (§3). Из MD4_PRE §14 (scope MD-4): quality-оживление; negative-to-provider в Аркаиме; video-план до generate_video; правки MediaPlan/SceneContext/WorldModel/temporal; удаление legacy; переносы queue/batch/regenerate/async; frontend; audio; изменение 5 маршрутов; film_studio-домен; словари стилей; ComfyUI Agent v1.

---

## 12. Technical Debt

| ID | Debt | Где | Почему существует | Когда решается | Трогать сейчас? |
|----|------|-----|-------------------|-----------------|-----------------|
| D-1 | ExecutionDispatch-мост | core/CORE/media_plan/dispatch.py | Провайдеры живут на старом конверте (prompt,size,provider) | MD-5 (REMOVE) | Нет |
| D-2 | shot_assembler сырые пути | core/CORE/film_studio/shot_assembler.py:37–46 | Читает файлы ассетов мимо storage-API | MD-5 (file-API/общий том) | Нет (owner §16-6) |
| D-3 | Video-план Route C не доходит до generate_video (F-33-1) | routes/assets.py (video-ветка) + pipeline.generate_video (сигнатура без plan) | Сигнатуру менять запрещено было в MD-3 | MD-5 / мини-этап | Нет |
| D-4 | Queue/async/batch/regenerate без плана | visual_assets/queue.py:44–62; assets.py:411 | Миграция запрещена в MD-3 | После MD-4, отдельное решение | Нет |
| D-5 | /comfyui/* публичные роуты | routes/visual.py:339–368 | Backend-управление в Arkaim-API | MD-5 (де-публикация) | Нет |
| D-6 | visualization/__init__:18 реэкспорт провайдеров | core/CORE/visualization/__init__.py | Домен-слой знает провайдерные типы (B4) | MD-5-cleanup | Нет |
| D-7 | GenerationParams execution-поля в домен-схеме | visual_assets/schemas.py:44–51 | Legacy VisualAsset-контракт (29 ключей ответа) | MD-5+ | Нет |
| D-8 | Три словаря стилей | visual_assets/prompt_builder.py (8 пресетов вкл. F-4 CJK «ancient壁画»), visualization, visual | Исторические слои | Отдельное решение | Нет |
| D-9 | F-12: film_studio.db без quality-колонки | data/film_studio.db (создан 19.07; код 07.08+) | CREATE TABLE IF NOT EXISTS не мигрирует | Решение владельца (пересоздать/ALTER) | Нет |
| D-10 | SharedSettings: ✅ ИСПРАВЛЕНО 2026-09-16 (PROVIDER_CHAIN=gigachat,openrouter — без huggingface; PROVIDER_FAILURE_THRESHOLD=3; PROVIDER_COOLDOWN_SECONDS=60) |
| D-11 | test_assets_new_params ×4 | runtime/tests/test_assets_new_params.py | `from runtime.core.routes...` — модуль недоступен из pytest-cwd | Тест-инфра, отдельно | Нет |
| D-12 | Мёртвые импорты providers.registry | narrative_engine/story/api_routes.py:243, research/{entity_extractor,source_searcher}.py, community/vk.py | providers/registry.py не существует; try/except-fallback | MD-5+/cleanup | Нет |
| D-13 | pollinations.pyc stale + stable_diffusion.py не в DI | core/CORE/providers/image/__pycache__/pollinations…pyc; stable_diffusion.py | Удалённые провайдеры (963322a) оставили pyc; SD — заглушка | MD-5-cleanup | Нет |
| D-14 | Висячая `__all__`-строка get_prompt_composer | runtime/core/adc_deps.py:~366 | Функция не существует (F-33-4) | MD-5+ | Нет |
| D-15 | Легаси-промпт-проекции A/B/C/E (byte-frozen) | visualization/prompt_builder.py + visual_assets/prompt_builder.py | PA-F1: контракт сохранён до MD-5 | MD-5 | Нет |
| D-16 | C2-finding: фабрика рёбер ставит AUTHOR_CANON | core/CORE/narrative_engine/temporal/relation.py:151–166 | Исправление = семантическое изменение данных; запрещено scope | Этап C2 (owner-решение) | Нет |
| D-17 | Genome-history churn при каждом запуске | core/CORE/genome/history/ (+ index.json) | Runtime-поведение снапшотов | Отдельное решение | Нет |

---

## 13. Test State (фактические прогоны этого аудита, 2026-09-13)

Все backend-прогоны: `runtime/.venv`, `COMFYUI_URL=http://127.0.0.1:18188` (офлайн-заглушка, кроме отмеченного), pytest `-q`.

| Suite | Команда/файлы | Результат |
|---|---|---|
| MD-3 (контракт+5 маршрутов+deprecations) | 7 файлов test_md3_* | **134 passed, 0 failed** (6.49s) |
| Temporal chunk (расширенный) | temporal_model, temporal_reconstruction, m8_1, m9, m5, m8, temporal_routes | **237 passed, 0 failed** (4.43s) |
| MD2/M7/M10/M10.2 | test_md2_routes, test_m7_epoch_visual, test_m10_temporal_updates, test_m10_2_pending_updates_api | **74 passed, 0 failed** |
| Visual-family core | test_visual_conflict, test_visual_meaning, test_visual_archetype, test_genome, test_genome_narrative | **45 passed, 4 skipped** (skips — pre-existing, по m7/genome-отчётам) |
| Visual+assets+film+md2 chunk | test_visual_comfyui, test_visual_assets_provider_chain, test_visualization, test_assets_new_params, test_film_endpoints, test_md2_scene_context, test_md2_routes | **114 passed, 4 failed** — все 4 = pre-existing `ModuleNotFoundError: No module named 'runtime.core'` (D-11), падали и во всех предыдущих отчётах |
| **arkaim-media (полный suite)** | `pytest tests` (аркаим-venv) | **42 passed** при полной ФС (62s). При sandbox-режиме DSH: 41/1 — `test_set_workflow` падает на PermissionError записи `workflows/custom_test.json` — доказано, что это ограничение песочницы, не дефект миграции (эскалация → PASS) |
| arkaim-web-v2 (unit) | `node scripts/run-tests.mjs` (12 файлов) | **85 passed, 0 failed** (включая temporal 11, provenance-badge 7) |
| ComfyUI-сервер | GET :8188/system_stats | **HTTP 200** (жив) |

**Pre-existing failures (не запускавшийся в этом аудите полный suite, но зафиксированные ранее и подтверждённые документами):** test_metrics (FastAPI 0.141 `_IncludedRouter` без `.path`); test_integrations/test_crowdfunding (sqlite readonly в sandbox-среде); test_auth ×3 (Telegram-хэш); test_memory ×8 (SQLite readonly); test_book_ui ×4; auth/test_migrations (rmtree WinError 5 — sandbox); сетевые тесты (stream/email/telegram/providers/pdf) блокируют полный pytest-процесс — полные прогоны исторически выполняются чанками. Причины — среда (DSH-sandbox) или pre-existing конфиг-долг D-10; ни одно не связано с MD-линией.

**Не запускавшиеся (вне мандата аудита):** E2E Playwright (среда запрещает spawn — документировано в F1/F2), полный backend-suite одним процессом (виснет на сетевых), live-смоук F3 (сервер не поднимался в этой сессии — предыдущие 25/25 и 14/14 зафиксированы отчётами temporal-alignment/F3).

---

## 14. Documentation vs Code Gaps (несоответствия)

| # | Несоответствие | Документ говорит | Код/факт делает | Что истина |
|---|---|---|---|---|
| 1 | **AGENTS.md → ADR/** | «ADR/ — Architecture Decision Records» (структура проекта) | Корневой `ADR/` **пуст**; ADR-файлы в `docs/ADR/` | Факт: docs/ADR/. AGENTS.md устарел по пути |
| 2 | **AGENTS.md слои Pulse** | «6 слоёв» в архитектурной диаграмме; «8 слоёв Pulse» далее; «WorldEngineLayerV2» | Проверено этим аудитом (`grep '^class \w+Layer' pulse/layers.py`): **10 конкретных слоёв** (Knowledge, VisualStyle, NarrativeArc, Scene, Meaning, Identity, Mission, Expansion, Screenplay, WorldEngine) + BaseLayer; класс называется `WorldEngineLayer`, не V2 | Факт: 10 слоёв; CHANGELOG 2.0.0 («с 4 до 10») точен; AGENTS.md и PROJECT_STATE (6/8) устарели |
| 3 | **AGENTS.md порты/структура** | «Ant Design 6», «/_ui/* Jinja2+HTMX», docker-compose как основной старт | Существует; но не упоминает arkaim-web-v2, arkaim-media, MD-линейку, порт 3001 v2-фронтенда | AGENTS.md описывает состояние ~05.09 (последнее редактирование), не знает текущей фазы |
| 4 | **ADR_TEMPORAL статус «PROPOSED»** | Заголовок: «ожидает ACCEPTED владельца» | B1/C1 реализованы (TEMPORAL_API_ALIGNMENT_REPORT называет его «ACCEPTED»), F3 построен на его инвариантах | Факт: решения канонические (реализованы); статус в шапке ADR не обновлён |
| 5 | **docs/PROJECT_STATE.md, PROJECT_STATUS.md, PROJECT_SUMMARY.md (08.08)** | «219+ роутов», «34 страницы», «AntD 6», описывают legacy-стек как текущий | Актуальнее: web-v2-контракты (289 OpenAPI-путей, 298 RBAC), MD-линия, media-граница | Документы августа устарели как «текущее состояние»; сохраняют ценность как исторический срез |
| 6 | **docs/CLAUDE.md** | «111+ unit-тестов backend», «World Engine НОВЫЙ», требует start_all.bat | Сейчас 66 тест-файлов (сотни тестов); start*.bat в .gitignore (перемещены в scripts/) | CLAUDE.md устарел (20.07); дублированные секции внутри него |
| 7 | **README метрики** | «Слоёв Pulse 10», «API 219», «тестов 349+» | Реальные цифры дрейфуют (OpenAPI 289 путей по F1-снимку) | README — маркетинговый срез 08.08; не оперативный статус |
| 8 | **F3 статус** | F3_REPORT: «IMPLEMENTED & TESTED & VERIFIED. Жду решения владельца» + FOLLOW-UP закрыл PA-1/PA-2 | F3 ACCEPTED owner-GO D1 (2026-09-18): 85/85 тестов, 14/14 live-smoke, forensic post-audit выполнен, backend не тронут | Факт: F3 — ACCEPTED & CLOSED (D1). Документ обновлён. |
| 8.5 | **F4 STATUS** | Раньше: F4 WIP на диске, untracked; нет SPEC, PRE-AUDIT, GO | СЕЙЧАС: F4 ACCEPTED & CLOSED 2026-09-18 (owner-GO ПРИНЯТО); F4_IMPLEMENTATION_REPORT создан; 80 тестов green; 5 страниц в next build; backend 0 изменений | Факт: F4 — ACCEPTED & CLOSED. Все несоответствия закрыты. |
| 9 | **MD-фазы vs M-фазы нумерация** | MD4-документы говорят «M4.1, M4.2.2…» | MEDIA_DIRECTION_FOUNDATION использует «MD-4» для всего этапа | «M4.x» = подэтапы MD-4; конфликтов по содержанию нет, только по именованию |
| 10 | **ADR_MEDIA_BOUNDARY статус** | Шапка: «PROPOSED — ожидает ACCEPTED» | M4.1-отчёт §2 называет owner-решения по нему принятыми; MD-2/3/4 выполнялись в его рамках | Факт: работает как принятый; статус-строка не обновлена |
| 11 | **GET /assets/{id}/file и чтения** | MD4_PRE: «роуты отдают их из data/» | Подтверждено: assets.py 317–410 существует | Соответствует |
| 12 | **Пара «arkaim-web против arkaim-web-v2»** | FRONTEND_ARCHITECTURE §1: «Локация кода arkaim-web/ — полная замена содержимого» | Реально построен ОТДЕЛЬНЫЙ каталог arkaim-web-v2/ (порт 3001), legacy не тронут | Факт: два фронтенда сосуществуют; вопрос финальной консолидации открыт (FRONTEND_ARCHITECTURE §12 — «решение владельца») |
| 13 | **WORLD_ENGINE_* / World_Explorer_* в корне** | Документы существуют в корне (июль) | .gitignore: «Duplicate docs in root» — игнорируются | Мёртвые копии; canonical — docs/ |
| 14 | **TEST_REPORT.md (20.07)** | «Все 56 тестов пройдены» | Ныне сотни тестов; отдельные цифры неактуальны | Исторический срез |
| 15 | **Media-Contract пример таймаутов** | Контракт: «image ≤300 с (как ComfyUIProvider._poll)» | comfyui.py _poll timeout=300 — соответствует | Соответствует |
| 16 | **`comfy_generate` MCP-описание DSH (среда)** | Глобальный AGENTS.md DSH: ComfyUI-инструменты «Media-agnostic генерация через Agent» | Не часть репо; упомянуто, чтобы не путать: MCP-инструменты ≠ Media-проект | Инструментальная среда, вне границ проекта |

---

## 15. Current Development Position

| Вопрос | Ответ | Источник |
|---|---|---|
| Последний завершённый этап | В MD-линии: **M4.2.2** (ComfyUI→arkaim-media, commit `d4bcef2`, 42/42). До него: M4.1 (контракт, `8e465cc`), M4.2.1 (инвентаризация), Этап 1 (test-fix, в рабочем дереве arkaim). Параллельно закрытые большие этапы: MD-3 (CLOSED 2026-09-12), F3 (followup closed), M10.2, temporal-alignment | §6.4–6.5 |
| Какой этап сейчас разрешён | Формально — **никакой не «разрешён»**: каждый milestone требует отдельного owner-GO. Логика дорожки: **M4.2.3** (video-провайдеры: image_sequence.py + mock.py в `media/video/`) — следующий по плану M4.2, но **STOP без GO** | MD4_M42_2 §STOP; MD4_M42_1 §9 |
| Ближайшая задача (по плану, не автоматическая) | 1) owner-GO на контракт v1.0 (если ещё не дан — M4.1 «ждёт owner-GO на этот договор»); 2) owner-GO на M4.2.3; далее M4.2.4 (mock/svg/chain), M4.3 (MediaClient-bridge в adc_deps, env MEDIA_BACKEND_URL), M4.4 (живой прогон 5 маршрутов, byte-гейт+207/207), M4.5 (workflows/env, де-публикация → MD-5) | MD4_PRE §15; MD4_M42_2 §9 |
| Что делать НЕЛЬЗЯ (до соответствующих GO/этапов) | Всё из §11.3; плюс: не чинить seed-hash; не оживлять quality; не переносить queue/batch/regenerate; не менять 5 маршрутов/контрактов MediaPlan/SceneContext/WorldModel/temporal; не удалять legacy-стек Аркаима (24 comfyui-теста должны жить); не трогать film_studio; не смешивать ComfyUI Agent v1 и Media-проект; frontend/audio вне этапа; F4 implementation без GO; не коммитить тест-фикс без решения (политика сессий — см. §8.1) | MD4_M42_2 §7 (17 правил GO); MD3_CLOSURE §3 |
| Решения, не требующие повторного обсуждения | ADR TEMPORAL (A–D + инвариант фронтенда); ADR MEDIA BOUNDARY (5 decisions + инварианты); ADR MEDIA PLAN V0 (10 owner-decisions); M8.1; MD-2/MD-3-контракты; MD-4 owner-решения §16 (вариант A, quality мёртв, film-studio в Arkaim, repo arkaim-media, media_id наружу, shot_assembler не чинить); Q1/Q2/Q3 M4.2.1; frozen AD-словарь §7.5 | §7 |
| Где требуется отдельный GO владельца | Каждый milestone MD-6+; утверждение контракта v1.0 (✅ уже ACCEPTED); коммит незакоммиченной волны (тест-фикс + документы); F-12 (film-БД); любые новые поля контракта (ADR); F4+ фронт | соответствующие отчёты |
---

## 16. Next Allowed Step (по регламенту проекта)

**Регламент:** каждый milestone = pre-audit → реализация → STOP → owner-GO. Ничего не начинается автоматически.

**Текущая позиция:** все MD-этапы (1–6) и F-линейка (F1–F4) закрыты. Все M4.1–M4.4 подэтапы arkaim-media закрыты. MEDIA_CONTRACT v1.0 ACCEPTED.

**Кандидаты на следующий этап (требуют отдельного owner-GO, ни один не автоматический):**

- **F5** — frontend: realtime (WS-интеграция), /xray, /admin (users/invites/keys), /system, /profile enhancements (по FRONTEND_ARCHITECTURE §4)
- **MD-7 / M4.5** — workflows/env переезд + полная де-публикация legacy `/comfyui/*` + чистка ExecutionDispatch-остатков
- **F-12** — film-studio БД миграция (пересоздание/ALTER, решение владельца)
- **C2** — provenance-теги на PRECEDES-рёбрах (AUTHOR_CANON→DERIVED)
- **Фиксация в git** — коммит untracked F4-кода + тест-фикса M8.1 (отдельный GO)
- **Архитектурные решения** — утверждение остающихся DRAFT-контрактов; новые ADR по желанию владельца

**Данный R1-аудит ничего из этого не начал.**

---

## 17. Explicitly Forbidden Work (на текущей позиции)

1. **Никакого кода** до отдельного owner-GO (мандат этого аудита).
2. Не переносить ничего из Аркаима в Media до GO на соответствующий подэтап; не расширять состав переноса (SD-stub, quality, GigaChat, pollinations-остатки — не переносятся никогда без нового решения).
3. Не менять: 5 маршрутов A–E; MediaPlan/SceneContext/WorldModel/temporal/M10.2-контракты; SCHEMAS/MEDIA_PLAN.schema.json (байт-идентичность с media-репо — инвариант); frontend; film_studio; провайдерные сигнатуры (включая `_base_url`-механику для роутов).
4. Не оживлять: quality (MP-F1); negative-to-provider в Аркаиме; dead-поля шота E; computed Present→Arkaim relation.
5. Не удалять legacy (двойной провайдер живёт до MD-5; deprecation-метки ≠ удаление).
6. Не чинить попутно: seed-hash; F-12; test_assets_new_params; C2-фабрику (✅ уже исправлена).
7. Не смешивать ComfyUI Agent v1 (MCP) с Media-проектом; не поглощать Agent.
8. Не начинать: audio; queue/batch/regenerate-миграцию; новые relation-типы; TemporalEngine-сервис; правки arkaim-данных. F4 — ПРИНЯТО (implementation закрыт). F4-код untracked — не коммитить без separate GO.
9. Не коммитить в arkaim/arkaim-media без решения владельца (политика сессий: незакоммиченная волна ждёт решения).

---

## 18. Финальная карта

```
ПРОЕКТЫ
├── arkaim (master 4be2a40) — домен книги; F4 ACCEPTED (код untracked); fresh-start (48c19c9) — reference
│   ├── runtime/ — FastAPI :8642, DI (adc_deps), 9 роутеров, auth, 66 тест-файлов
│   ├── core/CORE/ — Pulse · WorldEngine · temporal (12 эпох+today) · KG · RAG
│   │     · visual (SceneContext MD-2) · media_plan (MediaPlan v0 MD-3)
│   │     · visual_assets (pipeline+storage+queue) · film_studio · providers (legacy)
│   │     · GENOME (данные+workflows-копия) · KNOWLEDGE · CHROMA_DB
│   ├── arkaim-web/ (legacy, заморожен)
│   ├── arkaim-web-v2/ (F1–F4 ACCEPTED; 14 стр. в fresh-start + 5 F4 страниц untracked на master)
│   ├── arkaim-mobile/ (RN+Expo, заготовка)
│   └── docs/ (100+: ADR×3, MD-серия, M-серия, F-серия)
├── arkaim-media (master d4bcef2) — исполнитель генерации
│   ├── docs/MEDIA_CONTRACT.md (v1.0 DRAFT) + schemas/×4 + examples/×3
│   ├── media/ (config + image/comfyui — M4.2.2)
│   └── workflows/default.json (= аркаимский, SHA сверен)
└── ComfyUI-сервер :8188 (жив) + ComfyUI Agent v1 (MCP, вне проектов)

КОНТРАКТЫ
├── Arkaim→Media: POST /v1/generate {plan + execution×5} → {bytes_b64, media_id…}
│     · forbidden: quality/model/seed/workflow/provider/… (additionalProperties:false)
│     · MediaPlan-схема байт-идентична между репо (SHA B52B7E7A…)
├── Внутри Arkaim: MediaPlan v0 (BANNED) · SceneContext · 5 маршрутов (byte-frozen)
│     · temporal API ×14 (B1/C1 done, C2 deferred) · OpenAPI-289/RBAC-298 (web-v2)
└── Временные: ExecutionDispatch (→MD-5) · legacy-промпт-проекции · D-2 сырые пути

ТЕКУЩИЙ MILESTONE
MD-6 CLOSED (4be2a40) · F4 ACCEPTED & CLOSED (owner-GO ПРИНЯТО 2026-09-18) · F-12 FUNCTIONALLY ACCEPTED / CLOSED (c022e77, 2026-09-23) · MEDIA_CONTRACT v1.0 ACCEPTED (f0327cd)

NEXT ALLOWED STEP (требует owner-GO)
1) F5 — frontend: realtime/admin/xray (по FRONTEND_ARCHITECTURE §4)
2) MD-7 / M4.5 — workflows/env переезд + полная де-публикация /comfyui/*
3) Фиксация F4-кода в git (untracked → committed, отдельный GO)
4) C2 — provenance-теги на рёбрах (AUTHOR_CANON→DERIVED)
6) Архитектурные решения — новые ADR по желанию владельца

НЕ ТРОГАТЬ СЕЙЧАС
• 5 маршрутов A–E и их ответы (byte-frozen)
• MediaPlan/SceneContext/SCHEMAS (байт-идентичность — инвариант)
• WorldModel/temporal-данные (read-only; C2-фабрика — не менять)
• legacy-стек Аркаима (providers, dispatch, GENOME/workflows, deprecation-метки)
• queue/async/batch/regenerate; film_studio (F-12-БД закрыта)
• quality/negative/dead-поля — не оживлять
• seed-hash и др. перенесённые дефекты — не чинить
• /comfyui/*, /providers/* роуты — не трогать (мост обязан сохранить _base_url)
• ComfyUI Agent v1 — не поглощать
• frontend v2 F4 implementation — ПРИНЯТО 2026-09-18 (код на диске untracked, коммитит по отдельному GO)
• frontend legacy (заморожен до F6)
• незакоммиченная волна в arkaim — не коммитить без решения
```

---

## 19. Evidence / Source Files

**Git-факты:** `git branch/rev-parse/log/status/diff` обеих реп (выводы в §8); arkaim-media log `8e465cc`→`d4bcef2`.

**Ключевые документы (все в `docs/` если не указано иное):** MEDIA_DIRECTION_FOUNDATION.md · MD2_IMPLEMENTATION_REPORT.md + MD2_POST_IMPLEMENTATION_FORENSIC_AUDIT.md · MD3_1/3_2_ROUTE_{A,B,C,D,E}_{BASELINE,REPORT} · MD3_3_DEPRECATION_REGISTRY.md · MD3_STAGE_CLOSURE.md · MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md · MD4_M41_IMPLEMENTATION_REPORT.md · MD4_M42_1_PROVIDER_INVENTORY.md · MD4_M42_2_COMFYUI_MIGRATION_REPORT.md · M8_1_ARCHITECTURE_DECISION.md + M8_1_TEST_ISOLATION_FIX_REPORT.md · M9_SPEC.md · M10_2_POST_IMPLEMENTATION_AUDIT.md · TEMPORAL_API_ALIGNMENT_{PLAN,REPORT,FORENSIC_AUDIT}.md · F1/F2/F3_*REPORTS · FRONTEND_ARCHITECTURE.md · NEXT_PHASE_ARCHITECTURAL_AUDIT.md · ADR/ADR_TEMPORAL_WORLD_MODEL.md · ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md · ADR/ADR_MEDIA_PLAN_V0.md · PROJECT_STATE.md (устар.) · README/CHANGELOG/AGENTS.md (корень).

**Код (проверено построчно в этом аудите):** `core/CORE/media_plan/dispatch.py` (полностью) · `core/CORE/providers/image/comfyui.py` (полностью, 169 стр.) · `core/CORE/providers/image/__init__.py` (полностью) · `core/CORE/visualization/__init__.py` · `core/config.py` (полностью) · `runtime/core/adc_deps.py` (L1–373, фабрики+реестр) · `runtime/core/routes/visual.py` (L20–79, Route A) · `runtime/core/book_routes.py` (полностью) · `runtime/core/provider_registry.py` (L1–80) · `runtime/core/routes/{assets,film_studio,temporal,temporal_updates}.py` (декораторы роутов) · `arkaim-media/media/config.py` + `media/image/comfyui.py` (шапка) · `arkaim-media/docs/MEDIA_CONTRACT.md` (полностью, 165 стр.) · narrative_engine-импорты providers.registry (4 файла).

**Хеш-доказательства:** workflows/default.json SHA256 `40F788FC3F08B8C6…28063D2` (равен в обоих репо); MEDIA_PLAN.schema.json SHA256 `B52B7E7AD0C340E8…86A50F635` (равен в обоих репо).

**Тест-прогоны (этот аудит):** перечислены в §13 с командами и цифрами.

**Live-проверки:** ComfyUI :8188 /system_stats → 200.

---

*Документ создан по мандату владельца «полное восстановление контекста». Никакой код не менялся; никакие решения не принимались. Служит точкой входа для будущих инженеров/ИИ.*

**STOP. Аудит завершён. Жду GO владельца.**