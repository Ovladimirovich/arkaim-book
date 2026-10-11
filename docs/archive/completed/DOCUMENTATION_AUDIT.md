# АУДИТ ДОКУМЕНТАЦИИ — «Наследие Аркаима»

**Дата:** 2026-09-14  
**Метод:** inventory всех `.md` + сверка статусов с git-историей и кодом  
**Ограничения:** ничего не удалять, не архивировать физически, не менять код, не принимать решений

---

## 1. Полная таблица MD-линии (хронология)

| # | Этап | Дата | Коммит arkaim | Коммит media | Статус код | Статус docs | Тесты |
|---|------|------|---------------|--------------|-----------|-------------|-------|
| — | M0 Architecture Audit | 2026-09-04 | `7dbd751`-предыдущий | — | ✅ | ACCEPTED | 74/74 |
| — | M1 Canon Provenance | 2026-09-04 | `cb7d920` | — | ✅ | ACCEPTED | — |
| — | M2 Temporal Model | 2026-09-04..05 | `ff40ef4` | — | ✅ | CLOSED | 237/237 |
| — | M3 Temporal Reconstruction | 2026-09-04 | `ff40ef4` | — | ✅ | CLOSED | — |
| — | M4 Integration Model | 2026-09-05 | `1f7c5db` | — | ✅ | CLOSED | — |
| — | M5 Temporal Integration | 2026-09-05 | `1f7c5db` | — | ✅ | CLOSED | — |
| — | M7.2 Pre-audit | 2026-09-05 | `1f7c5db` | — | ✅ | CLOSED | — |
| — | M8 Future Extrapolator | 2026-09-05 | `1f7c5db` | — | ✅ | CLOSED | — |
| — | M8.1 Architecture Decision | 2026-09-06 | `1f7c5db` | — | ✅ | ACCEPTED | — |
| — | M9 Spec + Audit | 2026-09-08 | `1f7c5db` | — | ✅ | CLOSED | — |
| — | M10 Implementation | 2026-09-09 | `1f7c5db` | — | ✅ | CLOSED | — |
| — | M10.2 Implementation | 2026-09-09 | `1f7c5db` | — | ✅ | CLOSED | — |
| F1 | Frontend Phase 1 | 2026-09-09 | `7a19386` | — | ✅ | ACCEPTED | 85/85 |
| F2 | Frontend Phase 2 | 2026-09-09 | `7a19386` | — | ✅ | IMPLEMENTED / VERIFIED | — |
| F3 | Frontend Phase 3 | 2026-09-10 | `7a19386` | — | ⚠️ Ждёт GO владельца | IMPLEMENTED → TESTED → VERIFIED | — |
| MD-1 | Foundation (pre-MD) | 2026-09-11 | `5023de2` | — | ✅ | CLOSED | — |
| MD-2 | Scene Context Consolidation | 2026-09-11 | `5023de2` | — | ✅ | CLOSED | — |
| MD-3 | MediaPlan Contract v0 (all routes) | 2026-09-12 | `5023de2` | — | ✅ | CLOSED | 134/134 |
| MD-4 M4.1 | Media Project Bootstrap | 2026-09-13 | `8e465cc` (media) | `8e465cc` | ✅ | IMPLEMENTED | 42/42 media |
| MD-4 M4.2.2 | ComfyUI provider migration | 2026-09-13 | `d4bcef2` (media) | `d4bcef2` | ✅ | IMPLEMENTED + TESTED | — |
| MD-4 M4.2.3 | Video providers migration | 2026-09-13 | `0256140` (media) | `0256140` | ✅ | ACCEPTED (media) | — |
| MD-4 M4.2.4 | Provider chains migration | 2026-09-13 | `4f60229` (media) | `4f60229` | ✅ | ACCEPTED (media) | — |
| MD-4 M4.3 | MediaClient bridge + DI | 2026-09-13 | `81612b7` | `5922dcc` | ✅ | ACCEPTED | 15/15 |
| MD-4 M4.4 | Live route gate | 2026-09-13 | `b5d399d` | `0d10396` | ✅ | ACCEPTED | — |
| **MD-5** | **Integration by Contract** | **2026-09-14** | **`d73d29a`** | — | **✅ ACCEPTED** | **ACCEPTED** | **141/141** |

---

## 2. Инвентарь всех `.md` файлов (проект, без node_modules/.venv)

### 2.1. SOURCE OF TRUTH (источник истины)

| Файл | Статус | Комментарий |
|------|--------|-------------|
| `core/SOURCE_OF_TRUTH/BOOK/КНИГА.md` | ✅ Источник истины | Исходный текст книги |
| `core/SOURCE_OF_TRUTH/SYNOPSIS/Наследие_Аркаима_Сценарий_Full.md` | ✅ Источник истины | Сценарий |
| `docs/CURRENT_DEVELOPMENT_STATE.md` | ✅ **Текущий источник истины состояния** | Обновлено 2026-09-14 после MD-5 |
| `docs/MD5_MIGRATION_REPORT.md` | ✅ Актуальный отчёт | Последний milestone |
| `docs/MD3_STAGE_CLOSURE.md` | ⚠️ Частично устарел | Ссылается на «ждёт owner-GO на MD-4», но MD-4/5 уже завершены |

### 2.2. ADR (Architecture Decision Records)

| Файл | Статус | Комментарий |
|------|--------|-------------|
| `docs/ADR/ADR_MEDIA_PLAN_V0.md` | ✅ ACCEPTED | 10 owner decisions зафиксированы |
| `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` | ⚠️ PROPOSED — но **фактически реализован** | Граница проведена в коде (MD-4/5), ADR ждёт ACCEPTED |
| `docs/ADR/ADR_TEMPORAL_WORLD_MODEL.md` | ⚠️ PROPOSED — но **решения реализованы в коде** | M8.1 engine реализован, API-выравнивание отложено до owner-GO |
| `core/ADR/0001_BOOK_IS_PRIMARY_SOURCE.md` | ✅ Принят | Базовый принцип |
| `core/ADR/0002_BOOK_FIRST_LLM_SECOND.md` | ✅ Принят | Базовый принцип |
| `core/ADR/0003_NO_AGENTS_BEFORE_INTELLIGENCE.md` | ✅ Принят | Базовый принцип |
| `core/ADR/0004_SINGLE_BOOK_FIRST.md` | ✅ Принят | Базовый принцип |

### 2.3. PROJECT_BIBLE (ядро проекта)

| Файл | Статус | Комментарий |
|------|--------|-------------|
| `core/PROJECT_BIBLE/README.md` | ✅ Актуален | Индекс |
| `core/PROJECT_BIBLE/00_PROJECT_MANIFEST.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/01_CREATOR_INTENT.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/02_BOOK_DESCRIPTION.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/03_PROJECT_OBJECTIVES.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/04_SYSTEM_ARCHITECTURE.md` | ⚠️ Устарел | Дата 2026-07-09, не знает MD-линию |
| `core/PROJECT_BIBLE/05_DEVELOPMENT_ROADMAP.md` | ⚠️ Устарел | Ссылки на Sprint, не на MD |
| `core/PROJECT_BIBLE/06_AI_ENGINEER_PROTOCOL.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/07_NARRATIVE_PROTOCOL.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/08_BOOK_OS_ARCHITECTURE.md` | ⚠️ Частично устарел | 2026-07-09, нет MD-линии |
| `core/PROJECT_BIBLE/09_BOOK_OS_SPRINT_PLAN.md` | 🗄️ Кандидат в архив | Заголовок: «ВЫПОЛНЕН» |
| `core/PROJECT_BIBLE/15_ARCHITECTURE_PRINCIPLES.md` | ✅ Актуален | |
| `core/PROJECT_BIBLE/GAP_ANALYSIS.md` | ⚠️ Устарел | 2026-07-07, не знает MD-линию |
| `core/PROJECT_BIBLE/PLAN_DIGITAL_AVATAR.md` | 🗄️ Кандидат в архив | Отложенный план, не реализован |
| `core/PROJECT_BIBLE/ROADMAP_COMPLETE.md` | ⚠️ Устарел | 2026-07-08, Sprint-формат |

### 2.4. Отчёты MD (Milestone Documentation)

| Файл | Статус |
|------|--------|
| `docs/MD2_PRE_IMPLEMENTATION_AUDIT.md` | ✅ Архивный (этап закрыт) |
| `docs/MD2_IMPLEMENTATION_REPORT.md` | ✅ Архивный |
| `docs/MD2_POST_IMPLEMENTATION_FORENSIC_AUDIT.md` | ✅ Архивный |
| `docs/MD3_PRE_IMPLEMENTATION_AUDIT.md` | ✅ Архивный |
| `docs/MD3_1_IMPLEMENTATION_REPORT.md` | ✅ Архивный |
| `docs/MD3_2_ROUTE_{A,B,C,D,E}_BASELINE.md` | ✅ Архивный (6 файлов) |
| `docs/MD3_2_ROUTE_{A,B,C,D,E}_IMPLEMENTATION_REPORT.md` | ✅ Архивный (5 файлов) |
| `docs/MD3_3_{PRE,DEPRECATION_REGISTRY,IMPLEMENTATION}_*.md` | ✅ Архивный (3 файла) |
| `docs/MD3_STAGE_CLOSURE.md` | ⚠️ Устарел (ссылки на MD-4 как следующий) |
| `docs/MD4_PRE_IMPLEMENTATION_FORENSIC_AUDIT.md` | ✅ Архивный |
| `docs/MD4_M41_IMPLEMENTATION_REPORT.md` | ✅ Архивный |
| `docs/MD4_M42_1_PROVIDER_INVENTORY.md` | ✅ Архивный |
| `docs/MD4_M42_2_COMFYUI_MIGRATION_REPORT.md` | ⚠️ Устарел (M4.2.3+ уже сделаны, есть ссылка «ждёт GO на M4.2.3») |
| `docs/MD4_M43_BRIDGE_ARKAIM_SIDE.md` | ✅ Архивный |
| `docs/MD4_M44_LIVE_RUN_ARKAIM_SIDE.md` | ✅ Архивный |
| `docs/MD5_MIGRATION_REPORT.md` | ✅ **Актуальный** |

### 2.5. Temporal/M-отчёты

| Файл | Статус |
|------|--------|
| `docs/M0_ARCHITECTURE_AUDIT.md` | ✅ Архивный |
| `docs/M1_CANON_PROVENANCE.md` | ✅ Архивный |
| `docs/M2_TEMPORAL_{AUDIT,MODEL}.md` | ✅ Архивный (2 файла) |
| `docs/M3_TEMPORAL_{RECONSTRUCTION_,}AUDIT.md` | ✅ Архивный (2 файла) |
| `docs/M4_{INTEGRATION_MODEL,PRE_IMPLEMENTATION_AUDIT}.md` | ✅ Архивный (2 файла) |
| `docs/M5_{PRE_IMPLEMENTATION_AUDIT,TEMPORAL_INTEGRATION_MODEL}.md` | ✅ Архивный (2 файла) |
| `docs/M7_2_PRE_IMPLEMENTATION_AUDIT.md` | ✅ Архивный |
| `docs/M8_FUTURE_EXTRAPOLATOR_IMPLEMENTATION.md` | ✅ Архивный |
| `docs/M8_1_{ARCHITECTURE_DECISION,ARCHITECTURE_DECISION_AUDIT,IMPLEMENTATION_REPORT,IMPLEMENTATION_SUMMARY,POST_IMPLEMENTATION_AUDIT,TEST_ISOLATION_FIX_REPORT}.md` | ✅ Архивный (6 файлов) |
| `docs/M9_{PRE_IMPLEMENTATION_AUDIT,POST_IMPLEMENTATION_AUDIT,SPEC}.md` | ✅ Архивный (3 файла) |
| `docs/M10_{PRE_IMPLEMENTATION_AUDIT,IMPLEMENTATION_PLAN,IMPLEMENTATION_REPORT,POST_IMPLEMENTATION_AUDIT}.md` | ✅ Архивный (4 файла) |
| `docs/M10_2_{PRE_IMPLEMENTATION_AUDIT,IMPLEMENTATION_PLAN,IMPLEMENTATION_REPORT,POST_IMPLEMENTATION_AUDIT}.md` | ✅ Архивный (4 файла) |
| `docs/TEMPORAL_{CHAIN_AUDIT,CHAIN_ARCHITECTURE_AUDIT,API_ALIGNMENT_{PLAN,REPORT,FORENSIC_AUDIT}}.md` | ✅ Архивный (5 файлов) |
| `docs/NEXT_PHASE_ARCHITECTURAL_AUDIT.md` | ⚠️ Частично устарел | Рекомендует M11, но MD-линия ушла в другую сторону |

### 2.6. F-отчёты (Frontend)

| Файл | Статус |
|------|--------|
| `docs/F{1,2,3}_{PRE,IMPLEMENTATION_PLAN,SPEC,IMPLEMENTATION_REPORT,POST_IMPLEMENTATION_AUDIT}.md` | ✅ Архивный (каждый этап — 4-5 файлов) |
| `docs/F3_FORENSIC_POST_AUDIT_REPORT.md` | ✅ Архивный |
| `docs/F3_POST_AUDIT_FOLLOWUP_REPORT.md` | ✅ Архивный |
| `docs/FRONTEND_ARCHITECTURE.md` | ⚠️ Устарел | 2026-09-09, не знает arkaim-web-v2 |
| `docs/FRONTEND_FORENSIC_AUDIT.md` | ⚠️ Частично устарел | |

### 2.7. Корневая документация

| Файл | Статус | Проблема |
|------|--------|----------|
| `README.md` | ✅ Актуален | 2026-08-08, но метрики грубые |
| `docs/README.md` | ⚠️ Устарел | 2026-07-19, структура неполная |
| `docs/PROJECT_STATUS.md` | ⚠️ Устарел | 2026-08-08, «29 страниц» (сейчас 34), нет MD-линии |
| `docs/PROJECT_STATE.md` | ⚠️ Частично устарел | 2026-08-08, нет MD-линии, есть верные факты |
| `docs/PROJECT_SUMMARY.md` | ⚠️ Устарел | 2026-08-08, дублирует PROJECT_STATUS |
| `docs/ARCHITECTURE.md` | ⚠️ Устарел | 2026-07-16, есть ADC/-ref, нет MD-линии |
| `docs/CLAUDE.md` | ⚠️ Устарел | 2026-07-20, нет MD-линии, нет arkaim-media |
| `docs/AI_ENGINEER_GUIDE.md` | ⚠️ Частично устарел | 2026-08-08 |
| `docs/INTERFACE_CAPABILITIES.md` | ⚠️ Устарел | 2026-08-08, «29 страниц» |
| `docs/DEPLOY.md` | ✅ Актуален | |
| `docs/comfyui_guide.md` | ⚠️ Устарел | Ссылки на удалённые HF/Pollinations |
| `docs/ComfyUI.md` | ⚠️ Устарел | 2026-07-19, есть HF-ref |
| `docs/WORLD_ENGINE.md` | ⚠️ Устарел | 2026-07-20, нет MD-линии |
| `docs/WORLD_EXPLORER.md` | ⚠️ Устарел | 2026-07-19 |
| `docs/visual_genome_guide.md` | 🗄️ Кандидат в архив | Sprint-era |
| `docs/visualization_layer.md` | 🗄️ Кандидат в архив | Sprint-era, есть Sprint-ref |
| `docs/sprint_0_summary.md` | 🗄️ Кандидат в архив | Исторический, Sprint 0 |
| `docs/plan_sprint2.md` | 🗄️ Кандидат в архив | Sprint-era |
| `docs/plan_sprint2d_crowdfunding.md` | 🗄️ Кандидат в архив | Sprint-era |
| `docs/restructuring_plan.md` | 🗄️ Кандидат в архив | 2026-07-10, ADC-ref |
| `docs/project_overview.md` | ⚠️ Устарел | 2026-07-10, Sprint-era |
| `docs/MEDIA_DIRECTION_FOUNDATION.md` | ⚠️ Устарел | Ссылки на «Sprint» вместо MD-линии |
| `docs/PLAN_REMOVE_POLLINATIONS_HF.md` | 🗄️ Кандидат в архив | Исторический (удаление провайдеров сделано) |
| `docs/TEST_REPORT.md` | 🗄️ Кандидат в архив | 2026-07-20, устаревшие метрики |

### 2.8. Internal / Внутренние

| Файл | Статус |
|------|--------|
| `docs/internal/PLAN_NEXT.md` | ⚠️ Устарел | Рекомендует M11, но MD-линия прошла дальше |
| `docs/internal/SYSTEM_AUDIT.md` | ⚠️ Устарел | 2026-07-09 |
| `docs/internal/ANALYSIS_REPORT.md` | 🗄️ Кандидат в архив | 2026-07-23 |
| `docs/internal/nimble-nebula-notes.md` | 🗄️ Кандидат в архив | Notes |
| `docs/internal/SESSION_SUMMARY.md` | 🗄️ Кандидат в архив | |

### 2.9. Runtime

| Файл | Статус |
|------|--------|
| `runtime/contracts/EXECUTION_CONTRACT.md` | ✅ Актуален |
| `runtime/contracts/INTEGRATION_CONTRACT.md` | ✅ Актуален |
| `runtime/contracts/SKILL_CONTRACT.md` | ✅ Актуален |
| `runtime/docs/{COLLABORATOR_GUIDE,DEPLOYMENT,NETWORK_ACCESS_OPTIONS}.md` | ⚠️ Устарел | 2026-07-07 |
| `runtime/API_DOCUMENTATION.md` | 🗄️ Кандидат в архив | Дублируется Swagger |
| `runtime/prompts/system.md` | ✅ Актуален | |

### 2.10. Core

| Файл | Статус |
|------|--------|
| `core/DEVELOPER_GUIDE.md` | ⚠️ Устарел | ADC-ref |
| `core/PROJECT_STATUS.md` | ⚠️ Устарел | 2026-07-09, нет MD-линии |
| `core/KNOWLEDGE/*.md` | ✅ Актуален | Данные знаний |
| `core/LOGS/README.md` | ✅ Актуален | |

### 2.11. Arkaim-web / arkaim-mobile

| Файл | Статус |
|------|--------|
| `arkaim-web/README.md` | ⚠️ Устарел | 2026-07-10 |
| `arkaim-mobile/AGENTS.md`, `CLAUDE.md` | ⚠️ Минимальны | 2026-07-10 |

### 2.12. Arkaim-media

| Файл | Статус |
|------|--------|
| `docs/MEDIA_CONTRACT.md` | ⚠️ DRAFT — но **фактически реализован** | Контракт v1.0 используется в коде (MD-4/5) |
| `docs/MD4_M42_2_*.md` | ✅ Архивный |
| `docs/MD4_M42_3_*.md` | ✅ Архивный |
| `docs/MD4_M42_4_*.md` | ✅ Архивный |
| `docs/MD4_M43_*.md` | ✅ Архивный |
| `docs/MD4_M44_*.md` | ✅ Архивный |
| `README.md` | ⚠️ Устарел | 2026-09-13, нет MD-5 |

---

## 3. Ложные ощущения (документы, создающие неправильное представление)

| Документ | Ложное впечатление | Факт |
|----------|-------------------|------|
| `docs/MD3_STAGE_CLOSURE.md` | «ждёт owner-GO на MD-4» | MD-4 и MD-5 уже завершены |
| `docs/MD4_M42_2_COMFYUI_MIGRATION_REPORT.md` | «Ждёт GO на M4.2.3» | M4.2.3 и M4.2.4 уже сделаны |
| `docs/CURRENT_DEVELOPMENT_STATE.md` (строка 47) | «текущий этап = MD-4 / M4.2.2 — STOP» | UPGRADED в 99636e6, но строка 47 всё ещё говорит M4.2.2 |
| `docs/PROJECT_STATUS.md` | «29 страниц фронтенда» | 34 страницы (arkaim-web-v2 + legacy) |
| `docs/INTERFACE_CAPABILITIES.md` | «29 страниц» | 34 страницы |
| `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` | «PROPOSED — ожидает ACCEPTED» | Граница фактически проведена в коде (MD-4/5); ждёт только подписи владельца |
| `docs/ADR/ADR_TEMPORAL_WORLD_MODEL.md` | «PROPOSED — ожидает ACCEPTED» | Решения M8.1 реализованы в engine; ждёт ACCEPTED + small backend-этап |
| `docs/MEDIA_CONTRACT.md` (arkaim-media) | «DRAFT на утверждение» | Контракт v1.0 фактически используется (MediaClient, DI, routes) |
| `docs/NEXT_PHASE_ARCHITECTURAL_AUDIT.md` | «следующий этап — M11 UI очереди» | MD-линия пошла по другому вектору (MD-1..MD-5); M11 не актуален |
| `docs/internal/PLAN_NEXT.md` | «рекомендуется M11» | Не актуален после MD-5 |

---

## 4. ADR со статусом PROPOSED/DRAFT vs фактическое состояние

| ADR | Статус в файле | Факт | Действие |
|-----|----------------|------|-----------|
| `ADR_ARKAIM_MEDIA_BOUNDARY.md` | PROPOSED | Граница проведена: media-репо существует, ComfyUI перенесён, ExecutionDispatch удалён | **Требуется ACCEPTED владельца** — код уже соответствует |
| `ADR_TEMPORAL_WORLD_MODEL.md` | PROPOSED | M8.1 engine реализован; API-выравнивание (B1+C1) отложено | **Требуется ACCEPTED владельца** — решение принято кодом, ждёт formality |
| `MEDIA_CONTRACT.md` (media) | DRAFT | Контракт v1.0 используется в production-коде (MediaClient bridge) | **Требуется ACCEPTED владельца** — де-факто accepted |

---

## 5. Конфликты и рассинхронизации

### 5.1. Мета-документы корня репо ≠ факт
| Документ | Ожидают | Факт |
|----------|---------|------|
| `README.md` | 29 страниц, 195 роутов | 34 страницы, 219+ роутов, MD-5 |
| `docs/PROJECT_STATUS.md` | 29 страниц, MD-4 STOP | 34 страницы, MD-5 ACCEPTED |
| `docs/PROJECT_STATE.md` | Нет MD-линии | MD-1..MD-5 реализованы |
| `docs/CLAUDE.md` | Нет arkaim-media | arkaim-media существует, 6 коммитов |
| `docs/ARCHITECTURE.md` | Sprint-формат | MD-линия |
| `docs/restructuring_plan.md` | ADC/ пути | core/ пути |

### 5.2. Дубликаты
| Группа | Дублирующиеся файлы |
|--------|-------------------|
| Проектный статус | `PROJECT_STATUS.md`, `PROJECT_STATE.md`, `PROJECT_SUMMARY.md` — 3 документа об одном |
| World Engine | `WORLD_ENGINE.md`, `WORLD_ENGINE_DOCUMENTATION.md`, `WORLD_ENGINE_FINAL_REPORT.md`, `WORLD_ENGINE_ROADMAP.md` |
| ComfyUI | `ComfyUI.md`, `comfyui_guide.md` |
| Архитектура | `ARCHITECTURE.md`, `FRONTEND_ARCHITECTURE.md` |
| ADR | `core/ADR/` (4 старых) + `docs/ADR/` (3 новых) — раздельные каталоги |

### 5.3. Устаревшие пути
| Файл | Старый путь | Должен быть |
|------|------------|-------------|
| `core/DEVELOPER_GUIDE.md` | `ADC/CORE/...` | `core/CORE/...` |
| `core/PROJECT_BIBLE/PLAN_DIGITAL_AVATAR.md` | `ADC/...` | `core/...` |
| `docs/ARCHITECTURE.md` | `ADC/...` | `core/...` |
| `docs/restructuring_plan.md` | `ADC/...` | `core/...` |

---

## 6. Рекомендуемая структура документации

```
arkaim/
├── README.md                          ← обновить метрики (34 стр, 219 роутов, MD-5)
├── AGENTS.md                          ← обновить (добавить MD-линию, arkaim-media)
├── CLAUDE.md                          ← обновить (аналогично)
│
├── docs/
│   ├── README.md                      ← переписать: навигация по актуальной структуре
│   ├── CURRENT_DEVELOPMENT_STATE.md   ← ✅ ТЕКУЩИЙ SOURCE OF TRUTH (уже обновлён)
│   │
│   ├── ADR/                           ← ЕДИНЫЙ каталог ADR (переместить core/ADR/ сюда)
│   │   ├── ADR_0001_BOOK_IS_PRIMARY_SOURCE.md
│   │   ├── ADR_0002_BOOK_FIRST_LLM_SECOND.md
│   │   ├── ADR_0003_NO_AGENTS_BEFORE_INTELLIGENCE.md
│   │   ├── ADR_0004_SINGLE_BOOK_FIRST.md
│   │   ├── ADR_ARKAIM_MEDIA_BOUNDARY.md      ← статус → ACCEPTED (после GO)
│   │   ├── ADR_MEDIA_PLAN_V0.md              ← ✅ ACCEPTED
│   │   └── ADR_TEMPORAL_WORLD_MODEL.md       ← статус → ACCEPTED (после GO)
│   │
│   ├── milestones/                    ← все MD-отчёты (структурированно)
│   │   ├── MD3_STAGE_CLOSURE.md       ← обновить: «MD-3 CLOSED, далее MD-4»
│   │   ├── MD4_{M41,M42_2,M42_3,M42_4,M43,M44}_*.md
│   │   └── MD5_MIGRATION_REPORT.md    ← ✅ актуальный
│   │
│   ├── temporal/                      ← M0..M10.2 отчёты
│   │   ├── M0_ARCHITECTURE_AUDIT.md
│   │   ├── M1_CANON_PROVENANCE.md
│   │   ├── M2_TEMPORAL_*.md
│   │   ├── M3_TEMPORAL_*.md
│   │   ├── M4_INTEGRATION_MODEL.md
│   │   ├── M5_TEMPORAL_*.md
│   │   ├── M8_1_*.md
│   │   ├── M9_*.md
│   │   └── M10_*.md
│   │
│   ├── frontend/                      ← F1..F3 отчёты
│   │   ├── F1_*.md
│   │   ├── F2_*.md
│   │   └── F3_*.md
│   │
│   ├── guides/                        ← руководства (актуальные)
│   │   ├── AI_ENGINEER_GUIDE.md
│   │   ├── comfyui_guide.md
│   │   └── visual_genome_guide.md
│   │
│   ├── subsystems/                    ← документация подсистем
│   │   ├── WORLD_ENGINE.md            ← объединить WORLD_ENGINE_*.md
│   │   ├── WORLD_EXPLORER.md
│   │   └── MEDIA_DIRECTION.md         ← MEDIA_DIRECTION_FOUNDATION.md
│   │
│   └── historical/                    ← архив (Sprint-era, pre-MD)
│       ├── sprint_0_summary.md
│       ├── plan_sprint2.md
│       ├── plan_sprint2d_crowdfunding.md
│       ├── restructuring_plan.md
│       ├── PLAN_REMOVE_POLLINATIONS_HF.md
│       ├── PROJECT_STATUS.md          ← перенести (исторический snapshot 2026-08-08)
│       ├── PROJECT_STATE.md           ← перенести
│       ├── PROJECT_SUMMARY.md         ← перенести
│       ├── ARCHITECTURE.md            ← перенести
│       ├── FRONTEND_ARCHITECTURE.md   ← перенести
│       ├── FRONTEND_FORENSIC_AUDIT.md ← перенести
│       ├── NEXT_PHASE_ARCHITECTURAL_AUDIT.md ← перенести
│       ├── internal/                  ← перенести
│       └── compose/reports/          ← перенести
│
├── core/
│   ├── ADR/                           ← УДАЛИТЬ (перенесено в docs/ADR/)
│   ├── PROJECT_BIBLE/                 ← обновить устаревшие файлы
│   │   ├── 04_SYSTEM_ARCHITECTURE.md  ← обновить или перенести в historical
│   │   ├── 05_DEVELOPMENT_ROADMAP.md  ← обновить или перенести
│   │   ├── 08_BOOK_OS_ARCHITECTURE.md ← обновить или перенести
│   │   ├── 09_BOOK_OS_SPRINT_PLAN.md  ← перенести в historical («ВЫПОЛНЕН»)
│   │   └── GAP_ANALYSIS.md            ← перенести в historical
│   └── DEVELOPER_GUIDE.md             ← обновить пути (ADC→core)
│
├── runtime/
│   └── docs/                          ← обновить или перенести в historical
│
└── docs/HISTORY.md                    ← НОВЫЙ: краткая хронология всех этапов
```

---

## 7. Список файлов по категориям

### 7.1. Оставить в основном дереве (актуальные)

```
README.md
AGENTS.md
CLAUDE.md
docs/README.md
docs/CURRENT_DEVELOPMENT_STATE.md
docs/MD5_MIGRATION_REPORT.md
docs/ADR/ADR_MEDIA_PLAN_V0.md
docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md  (после ACCEPTED)
docs/ADR/ADR_TEMPORAL_WORLD_MODEL.md   (после ACCEPTED)
docs/guides/AI_ENGINEER_GUIDE.md
docs/guides/comfyui_guide.md
docs/guides/visual_genome_guide.md
docs/subsystems/WORLD_ENGINE.md
docs/subsystems/WORLD_EXPLORER.md
docs/subsystems/MEDIA_DIRECTION.md
docs/milestones/MD3_STAGE_CLOSURE.md   (после обновления ссылок)
docs/DEPLOY.md
core/PROJECT_BIBLE/{00,01,02,03,06,07,15}_*.md
core/PROJECT_BIBLE/README.md
core/SOURCE_OF_TRUTH/**/*
runtime/contracts/*.md
runtime/prompts/system.md
core/ADR/0001-0004/*.md                (перенести в docs/ADR/)
```

### 7.2. Перенести в historical/ (архивные, но ценные)

```
docs/historical/
├── PROJECT_STATUS.md           (snapshot на 2026-08-08)
├── PROJECT_STATE.md
├── PROJECT_SUMMARY.md
├── ARCHITECTURE.md
├── FRONTEND_ARCHITECTURE.md
├── FRONTEND_FORENSIC_AUDIT.md
├── NEXT_PHASE_ARCHITECTURAL_AUDIT.md
├── sprint_0_summary.md
├── plan_sprint2.md
├── plan_sprint2d_crowdfunding.md
├── restructuring_plan.md
├── PLAN_REMOVE_POLLINATIONS_HF.md
├── TEST_REPORT.md
├── internal/ANALYSIS_REPORT.md
├── internal/nimble-nebula-notes.md
├── internal/SESSION_SUMMARY.md
├── internal/PLAN_NEXT.md
├── compose/reports/BACKEND_AUDIT_2026-07-10.md
├── core/PROJECT_BIBLE/04_SYSTEM_ARCHITECTURE.md
├── core/PROJECT_BIBLE/05_DEVELOPMENT_ROADMAP.md
├── core/PROJECT_BIBLE/08_BOOK_OS_ARCHITECTURE.md
├── core/PROJECT_BIBLE/09_BOOK_OS_SPRINT_PLAN.md
├── core/PROJECT_BIBLE/GAP_ANALYSIS.md
├── core/PROJECT_BIBLE/PLAN_DIGITAL_AVATAR.md
├── core/DEVELOPER_GUIDE.md     (после обновления путей)
└── runtime/docs/*.md
```

### 7.3. Объединить / заменить

| Действие | Файлы |
|----------|-------|
| **Объединить** 4 World Engine файла → 1 | `WORLD_ENGINE.md`, `WORLD_ENGINE_DOCUMENTATION.md`, `WORLD_ENGINE_FINAL_REPORT.md`, `WORLD_ENGINE_ROADMAP.md` |
| **Объединить** 2 ComfyUI файла → 1 | `ComfyUI.md`, `comfyui_guide.md` |
| **Заменить** 3 статуса → 1 | `PROJECT_STATUS.md`, `PROJECT_STATE.md`, `PROJECT_SUMMARY.md` → оставить только `CURRENT_DEVELOPMENT_STATE.md` |
| **Переместить** `core/ADR/` → `docs/ADR/` | 4 файла `ADR_0001-0004.md` |
| **Обновить** `docs/README.md` | Переписать навигацию под новую структуру |
| **Обновить** `README.md` (корень) | Метрики: 34 стр, 219 роутов, MD-5 |
| **Обновить** `AGENTS.md`, `CLAUDE.md` | Добавить MD-линию, arkaim-media |

### 7.4. Требуют решения владельца

| Файл / Вопрос | Почему нужно решение |
|---------------|---------------------|
| `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` — принять ACCEPTED | Код уже соответствует, но ADR формально PROPOSED |
| `docs/ADR/ADR_TEMPORAL_WORLD_MODEL.md` — принять ACCEPTED | Engine реализован, API-выравнивание отложено |
| `arkaim-media/docs/MEDIA_CONTRACT.md` — принять ACCEPTED | Контракт де-факто используется |
| `docs/MD3_STAGE_CLOSURE.md` — обновить ссылку «следующий шаг» | Сейчас ссылается на MD-4, нужно на MD-6 |
| `docs/MD4_M42_2_COMFYUI_MIGRATION_REPORT.md` — пометить как superseded | M4.2.3+ уже реализованы |
| `docs/NEXT_PHASE_ARCHITECTURAL_AUDIT.md` — archивировать | Рекомендует M11, но MD-линия пошла иначе |
| `docs/internal/PLAN_NEXT.md` — archивировать | Не актуален после MD-5 |

---

## 8. Рекомендуемый CURRENT/SOURCE-OF-TRUTH набор

**Единственный источник истины о состоянии проекта:**
→ `docs/CURRENT_DEVELOPMENT_STATE.md` (обновлён в 99636e6)

**Единственный источник истины о архитектуре:**
→ `docs/ADR/` (все 7 ADR, после переноса core/ADR/)

**Единственный источник истины о milestone-этапах:**
→ `docs/milestones/` (MD3_STAGE_CLOSURE, MD4_*, MD5_MIGRATION_REPORT)

**Единственный источник истины о временной модели:**
→ `docs/temporal/` (M0..M10.2)

**Единственный источник истины о фронтенде:**
→ `docs/frontend/` (F1..F3) + `arkaim-web-v2/README.md`

**Исторический контекст (не для текущей работы):**
→ `docs/historical/` (Sprint-era, pre-MD, устаревшие статусы)

---

## 9. Итоговая таблица

| Категория | Кол-во файлов | Действие |
|-----------|---------------|----------|
| Актуальные (остаются) | ~35 | Обновить метрики, переместить ADR |
| Архивные (→ historical) | ~60 | Переместить, не удалять |
| Для объединения | ~8 | Консолидировать в 3-4 файла |
| Требуют GO владельца | 6 | ADR ACCEPTED + update links |
| Ложные впечатления | 10 | Исправлены в CURRENT_DEVELOPMENT_STATE.md |

**Всего `.md` файлов в проекте:** ~195 (без node_modules/.venv)  
**Из них проектных (не third-party):** ~120

---

**STOP / WAIT** — отчёт готов. Никаких изменений не вносил (кроме обновления CURRENT_DEVELOPMENT_STATE.md и MD5_MIGRATION_REPORT.md в ходе MD-5). Жду вашего решения по пунктам §7.4.
