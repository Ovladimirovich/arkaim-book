<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL - НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Статусы, маршруты, компоненты и упоминания бывшего v2 ниже отражают состояние на момент создания документа. Актуальность проверяйте по docs/CURRENT_DEVELOPMENT_STATE.md, docs/DOCUMENTATION_INDEX.md, текущему коду и ADR.

# POST-F4 REBASELINE REPORT — R1

**Дата:** 2026-09-18  
**Мандат:** Post-F4 Rebaseline & Documentation Cleanup  
**Режим:** read-only аудит + изменение только `docs/` и структуры `docs/archive/`  
**Application code:** НЕ ИЗМЕНЯЛСЯ

---

## 1. Current Verified State (после F4)

### 1.1 Arkaim (монорепо)

| Параметр | Значение |
|----------|----------|
| Branch | `master` |
| HEAD | `4be2a40` «feat(md-6): legacy cleanup + contract hardening» |
| Рабочий набор | Только `core/CORE/genome/history/index.json` (автозапись, pre-existing) |
| F4-код | Untracked на master (не закоммичен); по решению D3 — не merge |
| Тесты backend | 141/141 MD-3+MD-4 PASS; 237/237 temporal PASS; 74/74 md2/m7/m10.x PASS; 114/4 (4 pre-existing `ModuleNotFoundError`) |
| Тесты frontend-v2 | 85/85 PASS |

### 1.2 Arkaim-media

| Параметр | Значение |
|----------|----------|
| Branch | `master` |
| HEAD | `f0327cd` «docs(medium): accept MEDIA_CONTRACT v1.0» |
| Подэтапы | M4.1 ✅ · M4.2.1 ✅ · M4.2.2 ✅ · **M4.2.3 ✅** · **M4.2.4 ✅** · M4.3 ✅ · M4.4 ✅ · M4.5 частично |
| MEDIA_CONTRACT | **v1.0 ACCEPTED & CLOSED** (фактически использовался с M4.3) |
| Тесты | 42/42 PASS (полная ФС) |

### 1.3 F4 статус

| Параметр | Значение |
|----------|----------|
| Дата принятия | 2026-09-18 (owner-GO ПРИНЯТО) |
| Capabilities | 5: community (fix) + presence/email/drafts/moderation (4 new pages) |
| Тесты | 80/80 green (F4-suite) |
| Next build | 5/5 маршрутов green |
| Backend изменений | 0 |
| Misplaced WIP disposition | ask/graph/world-explorer→F2; upload→F3; admin→F5; analytics→separate |

### 1.4 Все MD-этапы

| Этап | Статус | HEAD arkaim | HEAD arkaim-media |
|------|--------|-------------|-------------------|
| MD-1 Foundation | ✅ CLOSED | — | — |
| MD-2 Scene Context | ✅ CLOSED | — | — |
| MD-3 MediaPlan v0 | ✅ CLOSED | — | — |
| MD-4 bootstrap | ✅ CLOSED (все M4.x) | — | `f0327cd` |
| MD-5 Integration | ✅ ACCEPTED | `d73d29a` | — |
| MD-6 Legacy cleanup | ✅ CLOSED | `4be2a40` | — |

### 1.5 Все F-этапы

| Этап | Статус | Тесты |
|------|--------|-------|
| F1 Foundation | ✅ ACCEPTED & CLOSED | 85/85 (суммарно) |
| F2 Диалог с книгой | ✅ ACCEPTED & CLOSED | (входит в 85/85) |
| F3 Время мира | ✅ ACCEPTED & CLOSED | 85/85 суммарно |
| F4 Предложения/Очереди | ✅ ACCEPTED & CLOSED | 80/80 F4-suite |

---

## 2. Documentation Baseline (актуальные источники истины)

| Документ | Роль |
|----------|------|
| `docs/CURRENT_DEVELOPMENT_STATE.md` | **Главный operational Source of Truth** — фактическое состояние после R1 |
| `docs/FRONTEND_ARCHITECTURE.md` | **Архитектурный контракт** — F1-F6 scope, красные линии, page map |
| `docs/ADR/*.md` (7 файлов) | **Принятые архитектурные решения** — ADR_TEMPORAL, ADR_MEDIA_BOUNDARY, ADR_MEDIA_PLAN_V0 + 4 базовых |
| `docs/DEPLOY.md` | Инструкции деплоя |
| `docs/AI_ENGINEER_GUIDE.md` | Гайд для ИИ-инженеров |
| `docs/KNOWLEDGE_BASE.md` | Справочник по знаниям |
| `README.md` (корень) | Общее описание проекта (метрики устарели — см. R1-8) |

---

## 3. Archived Documents (~95 файлов)

Перемещены в `docs/archive/` с подкатегориями:

| Директория | Кол-во | Что входит |
|------------|--------|-----------|
| `archive/md-line/` | 27 | MD2/MD3/MD4/MD5 отчёты, MEDIA_DIRECTION_FOUNDATION, FORENSIC_AUDIT_POST_MD5 |
| `archive/temporal/` | 34 | M0-M10.2 все pre/post-audit, SPEC, IMPLEMENTATION_REPORT, TEMPORAL_* серии |
| `archive/frontend/` | 18 | F1/F2/F3/F4 SPEC, PRE-AUDIT, IMPLEMENTATION_PLAN, REPORT, POST-AUDIT, FOLLOWUP |
| `archive/historical/` | 17 | Sprint-era (sprint_0, plan_sprint2, restructuring_plan), PROJECT_STATUS/STATE/SUMMARY, INTERFACE_*, NEXT_PHASE_*, internal/* |
| `archive/subsystems/` | 8 | ARCHITECTURE.md, WORLD_ENGINE.md, WORLD_EXPLORER.md, ComfyUI guides, visualization_layer, KNOWLEDGE_EXPANSION |
| `archive/completed/` | 17 | DATA_DISCIPLINE, PROVENANCE_COMPLETION, TRUTH_CORE, FORENSIC_*, READING_*, ANALYTICS_PLAN, G0_PLAN, DOCUMENTATION_AUDIT |

**Итого архивировано: ~121 файл** (включая перемещённые из корня docs/)

---

## 4. Removed Documents

**Удалено: 0 файлов.**

Все документы, которые могли бы быть удалены (дубликаты PROJECT_STATUS/STATE/SUMMARY; дубли M8_1_IMPLEMENTATION_SUMMARY; дубли ComfyUI guides), были **архивированы** с сохранением исторической ценности, согласно правилу R1 §9.

---

## 5. Superseded Documents

| Документ | Чем заменён | Причина |
|----------|------------|---------|
| `PROJECT_STATE.md` | `CURRENT_DEVELOPMENT_STATE.md` | Устарел (нет MD-линии, 29 стр вместо 34) |
| `PROJECT_STATUS.md` | `CURRENT_DEVELOPMENT_STATE.md` | Устарел (нет MD-линии, 29 стр) |
| `PROJECT_SUMMARY.md` | `CURRENT_DEVELOPMENT_STATE.md` | Полный дубликат PROJECT_STATUS |
| `MD3_STAGE_CLOSURE.md` | `CURRENT_DEVELOPMENT_STATE.md` §6.4 | Ссылался на «ждёт GO на MD-4», MD-4/5 уже done |
| `MD4_M42_2_COMFYUI_MIGRATION_REPORT.md` | `CURRENT_DEVELOPMENT_STATE.md` §6.5 | M4.2.3+ уже реализованы; header сам говорит «SUPERSEDED» |
| `NEXT_PHASE_ARCHITECTURAL_AUDIT.md` | `CURRENT_DEVELOPMENT_STATE.md` §16 | Рекомендовал M11; MD-линия пошла иначе |
| `internal/PLAN_NEXT.md` | `CURRENT_DEVELOPMENT_STATE.md` §16 | Уже помечен «АРХИВ»; M11 не актуален |
| `F4_SCOPE_DECISION_PACK.md` (header) | `F4_IMPLEMENTATION_REPORT.md` | Header говорил «GO pending», F4 уже implemented |
| `COMFYUI.md` + `comfyui_guide.md` | Сохранены в archive как пара | Дублирующие ComfyUI-гайды; локальный сервер > Colab |
| `M8_1_IMPLEMENTATION_SUMMARY.md` | `M8_1_IMPLEMENTATION_REPORT.md` | Дубликат |

---

## 6. Documentation Inconsistencies Fixed

| # | Несоответствие | Что исправлено |
|---|---------------|----------------|
| R1-1 | M4.2.3/M4.2.4 в §6.5: «НЕ НАЧАТ» | Факт: committed в arkaim-media (`0256140`, `4ccfd8e`). Исправлено на ACCEPTED & CLOSED |
| R1-2 | MEDIA_CONTRACT v1.0: «DRAFT — ждёт GO» | Факт: коммит `f0327cd` в arkaim-media — ACCEPTED. Исправлено |
| R1-3 | F4_SCOPE_DECISION_PACK header: «GO pending» | Исправлено на «GO RECEIVED 2026-09-18» |
| R1-4 | §2 Executive Summary: «MD-5 ACCEPTED, следующий — MD-6» | Исправлено: «MD-6 CLOSED» |
| R1-5 | §2: «Следующий этап — M4.2.3 или F-линейка» | Исправлено: M4.2.3+ все done; следующий кандидат — F5 / MD-7 / F-12 / C2 |
| R1-6 | §6.3: MD-4 «IN PROGRESS», MD-5 «DEFERRED» | Исправлено: оба CLOSED |
| R1-7 | §8.2: arkaim-media HEAD `d4bcef2` | Исправлено: `f0327cd` |
| R1-8 | §9.1: MEDIA_CONTRACT статус DRAFT | Исправлено: ACCEPTED |

**Статусы ADR** (PROPOSED → ACCEPTED) — уже были исправлены в самих ADR-файлах до R1 (видимо, после первого аудита). Проверено: `ADR_TEMPORAL_WORLD_MODEL.md` и `ADR_ARKAIM_MEDIA_BOUNDARY.md` обе имеют статус ✅ ACCEPTED.

---

## 7. Current Product Capabilities (verified inventory)

### Backend (FastAPI :8642)
- **Pulse layers:** 10 слоёв (Knowledge, VisualStyle, NarrativeArc, Scene, Meaning, Identity, Mission, Expansion, Screenplay, WorldEngine)
- **World Engine:** 547 сущностей, 287 связей, 55 форм, 10 режимов, 10 API-эндпоинтов
- **Temporal model:** 12 эпох + Present (today) + Future extrapolation; 7 API-роутов
- **M10.2 pending-updates:** 7 API-роутов очереди, RBAC editor/admin
- **MediaPlan v0:** единый смысловой контракт (22 поля, BANNED-инвариант)
- **5 маршрутов генерации A–E:** byte-frozen, работают через MediaPlan
- **Auth:** JWT + Telegram OAuth + email + dev-mode; RBAC reader/editor/admin
- **WebSocket + SSE:** real-time уведомления, streaming chat
- **~289 API-путей** (OpenAPI слепок)

### Frontend v2 (Next.js :3001)
- **19 страниц** (14 F1-F3 в fresh-start + 5 F4 untracked)
- **80 F4-тестов green**, 85 суммарно
- **Typed contracts** из OpenAPI (289 путей)
- **RBAC-матрица** (298 маршрутов)
- **Legacy arkaim-web** (:3000) — заморожен до F6

### Media Project (arkaim-media)
- **ComfyUI provider** (`media/image/comfyui.py`) — M4.2.2
- **Video providers** (`media/video/image_sequence.py`, `mock.py`) — M4.2.3
- **Provider chains** (ImageProviderChain, MockImage, SVGTemplate) — M4.2.4
- **MediaClient bridge** (adc_deps substitution) — M4.3
- **Live route gate** (5 маршрутов через Media) — M4.4
- **MEDIA_CONTRACT v1.0 ACCEPTED**
- **workflows/default.json** — байт-в-байт копия аркаимского (SHA verified)

---

## 8. Remaining Gaps

| ID | Gap | Severity | Когда решается |
|----|-----|----------|----------------|
| G-1 | F4-код untracked (не закоммичен в git master) | Низкая | Отдельный GO на коммит |
| G-2 | M8.1 test-isolation fix (незакоммичен в рабочем дереве) | Низкая | Отдельный GO на коммит |
| G-3 | D-1: ExecutionDispatch код физически удалён, но метки deprecation остались в других файлах | Низкая | MD-7 cleanup |
| G-4 | D-2: shot_assembler читает файлы сырыми путями | Средняя | MD-5 (частично) → MD-7 |
| G-5 | D-3: Video-план Route C не доходит до generate_video | Средняя | Мини-этап после MD-7 |
| G-6 | D-4: Queue/async/batch/regenerate без плана | Средняя | Отдельное решение |
| G-7 | D-5: `/comfyui/*` роуты депубликованы, но код роутов ещё в visual.py | Низкая | MD-7 cleanup |
| G-8 | D-7: GenerationParams execution-поля в домен-схеме | Низкая | MD-7+ |
| G-9 | D-8: Три словаря стилей | Низкая | Отдельное решение |
| G-10 | D-9: F-12 film_studio.db без quality-колонки | Средняя | Решение владельца |
| G-11 | D-12..D-15: мёртвые импорты, pyc-файлы, висячие `__all__` | Низкая | MD-7 cleanup |
| G-12 | D-16: C2-finding — фабрика рёбер ставит AUTHOR_CANON | Средняя | Отдельный этап C2 |
| G-13 | D-17: Genome-history churn при каждом запуске | Низкая | Отдельное решение |
| G-14 | Legacy arkaim-web заморожен до F6 | Информационно | F6 (owner-GO) |
| G-15 | README.md (корень): устаревшие метрики (29 стр→34, 195→219 роутов) | Низкая | Обновить при следующем GO |

---

## 9. Deferred / Historical Directions (НЕ текущая работа)

| Направление | Статус | Комментарий |
|------------|--------|-------------|
| **M4.2.3 video-провайдеры** | ✅ CLOSED | Коммит `0256140` в arkaim-media |
| **M4.2.4 chain/mock/svg** | ✅ CLOSED | Коммит `4ccfd8e` в arkaim-media |
| **M4.3 MediaClient bridge** | ✅ CLOSED | Коммит `81612b7` / `5922dcc` |
| **M4.4 live route gate** | ✅ CLOSED | Коммит `b5d399d` / `0d10396` |
| **MEDIA_CONTRACT v1.0** | ✅ ACCEPTED | Коммит `f0327cd` |
| **F5 frontend** | DEFERRED | По FRONTEND_ARCHITECTURE §4; требует owner-GO |
| **F6 polish/legacy cleanup** | DEFERRED | По FRONTEND_ARCHITECTURE §4; требует owner-GO |
| **Audio domain** | DEFERRED | Extension point; схема не определена |
| **Quality revival** | REJECTED | Owner-решение: quality мёртв (Q2) |
| **Queue/batch/regenerate migration** | DEFERRED | Запрещено в MD-3; отдельное решение |
| **F-12 film-БД** | DEFERRED | Решение владельца (пересоздать/ALTER) |
| **C2 provenance on edges** | DEFERRED | Требует семантического изменения данных |
| **Analytics dashboard** | SEPARATE MILESTONE | D-F4-4 (4B); не в F4 scope |
| **ComfyUI Agent v1** | OUT OF SCOPE | MCP-инструмент DSH; не часть Media-проекта |

---

## 10. Next-Step Candidates (фактические, без выбора за владельца)

| # | Кандидат | Обоснование | Требуется |
|---|----------|------------|-----------|
| 1 | **F5 — frontend realtime/admin** | По FRONTEND_ARCHITECTURE §4.1; логическое продолжение F-линейки после F4 | owner-GO |
| 2 | **MD-7 / M4.5 — workflows/env + полная де-публикация** | Завершение MD-4 линии; чистка legacy `/comfyui/*` кода | owner-GO |
| 3 | **Фиксация в git** — коммит F4-кода + M8.1 test-fix | Untracked-код на master; решение D3 — «не merge» относится к fresh-start, не к коммиту F4 | owner-GO |
| 4 | **F-12 — film-БД миграция** | Small debt; требует решения владельца (пересоздать vs ALTER) | owner-GO |
| 5 | **C2 — provenance-теги на рёбрах** | Исправление AUTHOR_CANON→DERIVED на PRECEDES-рёбрах | owner-GO |
| 6 | **Обновить README.md** | Метрики устарели (34 страницы, 219+ роутов) | owner-GO |

---

## 11. R1 Changes Summary

### Изменено (docs/)
- `docs/CURRENT_DEVELOPMENT_STATE.md` — актуализированы: M4.2.3/M4.2.4 статус, MEDIA_CONTRACT статус, текущая фаза (MD-6 CLOSED), arkaim-media HEAD, §6.3/§6.5/§8.2/§9.1/§16/§18
- `docs/archive/frontend/F4_SCOPE_DECISION_PACK.md` — исправлен header статус (GO pending → GO RECEIVED)
- `docs/DOCUMENTATION_INVENTORY.md` — **создан** (полный инвентарь ~160 документов)
- `docs/archive/README.md` — **создан** (навигация по архиву)

### Перемещено в `docs/archive/`
- `archive/md-line/` — 27 файлов
- `archive/temporal/` — 34 файла
- `archive/frontend/` — 18 файлов
- `archive/historical/` — 17 файлов
- `archive/subsystems/` — 8 файлов
- `archive/completed/` — 17 файлов
- **Итого перемещено: ~121 файл**

### Удалено
- 0 файлов (все исторические документы сохранены в архиве)

### Application code
- **НЕ ИЗМЕНЯЛСЯ** (backend, frontend, tests, configs — всё нетронуто)

---

## 12. Финальная структура `docs/`

```
docs/
├── CURRENT_DEVELOPMENT_STATE.md    ← главный Source of Truth
├── DOCUMENTATION_INVENTORY.md      ← инвентарь (создан R1)
├── POST_F4_REBASELINE.md          ← этот файл (создан R1)
├── FRONTEND_ARCHITECTURE.md        ← архитектурный контракт
├── DEPLOY.md                       ← инструкции деплоя
├── AI_ENGINEER_GUIDE.md           ← гайд для инженеров
├── KNOWLEDGE_BASE.md              ← справочник знаний
├── ADR/                           ← 7 ADR (канонические решения)
│   ├── ADR_0001_BOOK_IS_PRIMARY_SOURCE.md
│   ├── ADR_0002_BOOK_FIRST_LLM_SECOND.md
│   ├── ADR_0003_NO_AGENTS_BEFORE_INTELLIGENCE.md
│   ├── ADR_0004_SINGLE_BOOK_FIRST.md
│   ├── ADR_ARKAIM_MEDIA_BOUNDARY.md
│   ├── ADR_MEDIA_PLAN_V0.md
│   └── ADR_TEMPORAL_WORLD_MODEL.md
└── archive/                       ← ~121 исторический документ
    ├── README.md
    ├── md-line/    (27)
    ├── temporal/   (34)
    ├── frontend/   (18)
    ├── historical/ (17)
    ├── subsystems/ (8)
    └── completed/  (17)
```

---

## STOP

**R1 завершён.** Application code не изменялся. Все MD-этапы (1–6) и F-этапы (1–4) закрыты. MEDIA_CONTRACT v1.0 ACCEPTED.

Следующий шаг: владелец определяет следующий milestone по кандидатам в §11.
