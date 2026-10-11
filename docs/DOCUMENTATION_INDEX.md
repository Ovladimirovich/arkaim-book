# Индекс документации ARKAIM

**Актуальность:** 2026-10-01. Индекс определяет нормативность документов и сверяет их с фактическим кодом, тестами и конфигурацией.

## Приоритет источников

1. Фактический код, конфигурация и тесты.
2. Принятые ADR в `docs/ADR/`.
3. `docs/CURRENT_DEVELOPMENT_STATE.md` и этот индекс.
4. Тематические current contracts/specs.
5. Roadmap/backlog.
6. Исторические и архивные записи.

## Нормативные документы

| Документ | Назначение | Статус | Source of truth |
|---|---|---|---|
| `../AGENTS.md` | Правила работы и карта проекта | CURRENT | Да |
| `../README.md` | Назначение, установка и запуск | CURRENT | Да для setup/run |
| `CURRENT_DEVELOPMENT_STATE.md` | Единая карта состава и статусов | CURRENT | Да |
| `AI_ENGINEER_GUIDE.md` | Рабочие инструкции инженеру | CURRENT, subject to index | Ограниченно workflow |
| `../arkaim-web/README.md` | Frontend-specific setup | CURRENT | Только для `arkaim-web` |
| `../runtime/API_DOCUMENTATION.md` | Backend API description | SUBDOMAIN CONTRACT | После сверки с FastAPI/OpenAPI |
| `../runtime/contracts/` | Integration/execution contracts | SUBDOMAIN CONTRACT | Ограниченно контуром |
| `ADR/*` | Архитектурные решения | CURRENT | По соответствующему решению |

## Текущие результаты

| Документ | Назначение | Статус | Source of truth |
|---|---|---|---|
| `FRONTEND_POLISH_PASS_REPORT.md` | Polish Pass единственного `arkaim-web` | VERIFIED REPORT | Да для Polish Pass |
| `B3A_ID_RECONCILIATION_REPORT.md` | B3-A ID reconciliation | VERIFIED REPORT | Да для B3-A evidence |
| `PROJECT_CURRENT_STATE_AUDIT.md` | Контрольный baseline и evidence | CURRENT AUDIT | Только для зафиксированных проверок; не заменяет `CURRENT_DEVELOPMENT_STATE.md` |
| `A1_ROUTE_STATE_MAP_REPORT.md` | Frontend route/state map | CURRENT REPORT | Нет; сверять с `src/app` |
| `A1R_ROUTE_STATE_CONTRACT.md` | Route state contract | CURRENT CONTRACT | Нет; сверять с текущим frontend-кодом |
| `KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md` | Live-верификация read-only контура Knowledge Core (HEAD `1e3f812`) | LIVE VERIFICATION REPORT | Да для фактов прогона 2026-10-02; найденные расхождения перечислены в отчёте и не исправлялись |

## Фактически реализованные подсистемы

| Подсистема | Текущий фактический статус | Основные доказательства |
|---|---|---|
| Knowledge Cards builder | IMPLEMENTED / TESTED | `core/CORE/knowledge_card/builder.py`; `runtime/tests/test_knowledge_cards.py` — 40 тест-функций (прогон 2026-10-01 — 37 passed, повторный не запускался) |
| Knowledge Cards API | IMPLEMENTED / TESTED / LIVE CONFIRMED | `runtime/core/routes/knowledge_cards.py`; router в `runtime/core/main.py`; live 2026-10-02: search/card/trace HTTP 200, фильтры/pagination/totals — `KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md` |
| B4-C World provenance UI | IMPLEMENTED / TESTED / VERIFIED | `WorldProvenanceCard.tsx`; `world-engine/page.tsx`; целевые tests 17/17; полный frontend unit suite 70/70; browser evidence получено ранее (`region_arkaim`, `region_hyperborea`, `region_gardarika`), код после проверки не менялся |
| B10 browser e2e smoke | VERIFIED | `arkaim-web/tests/e2e/b10-console-smoke.spec.ts`; ранее выполненный smoke прошёл на `/ask`, `/history`, `/world-engine` (`1 passed`); повторный live-run не требуется |
| B3-B Temporal crosswalk | IMPLEMENTED / TESTED | `world_model.py`; `test_b3b_crosswalk.py` |
| World provenance | IMPLEMENTED / TESTED | `world_provenance.py`; `test_world_provenance.py` |

## Планы и backlog

| Документ | Назначение | Статус | Source of truth |
|---|---|---|---|
| `FRONTEND_RESTORE_BACKLOG.md` | Единственное место потенциально восстанавливаемых функций бывшего v2 | BACKLOG ONLY | Да только для backlog |
| `POST_FRONTEND_PRODUCT_ROADMAP.md` | Будущие этапы | PLAN | Нет |
| `B_WORLD_ENGINE_PLAN.md` | Исторический/справочный план World Engine | HISTORICAL / REFERENCE | Нет; текущие статусы — в `CURRENT_DEVELOPMENT_STATE.md` |
| `B3_CW_CANDIDATES.md` | Первый approved batch и кандидаты | REFERENCE / CANDIDATES | Нет; силу имеет только approved crosswalk |

## Исторические документы вне archive

| Документ | Причина |
|---|---|
| `FRONTEND_CONSOLIDATION_PLAN.md` | Аудит до решения владельца; сравнение двух frontend отменено |
| `FRONTEND_TRANSFORMATION_PLAN.md` | Этапы консолидации завершены; копирование из v2 больше не инструкция |
| `FRONTEND_ARCHITECTURE.md` | Архитектура периода двух направлений |
| `B3B_PLAN.md` | План до реализации B3-B |
| `B3B_BASELINE_BEFORE_B4.md` | Baseline до реализации B4 |
| `B4_PLAN.md` | План до реализации B4-A/B4-B |
| `B4C_PLAN.md` | Исторический план B4-C; текущий факт — IMPLEMENTED/TESTED/VERIFIED (browser evidence получено ранее); `SourceBadge` относится к B3, не B4-C |
| `F5_SPEC.md` | Спецификация закрытого этапа |
| `POST_F4_REBASELINE.md` | Срез после F4 |
| `MVP_CONTRACT_v2.md` | Старый этапный контракт, не вводящий вторую frontend-систему |
| `PRODUCT_MAP.md` | Старый срез; сверять с текущим state/code |
| `G0_IMPLEMENTATION_PLAN.md` | Старый implementation plan |

Их `PLAN/WIP/WAIT/LOCKED/DONE/VERIFIED` статусы отменены, если противоречат `CURRENT_DEVELOPMENT_STATE.md`, коду и тестам.

## Архив

Всё содержимое `archive/` имеет статус **HISTORICAL**, включая `completed/`, `frontend/`, `temporal/`, `md-line/` и прочие архивные каталоги. Файлы сохраняются для истории и не являются рабочими инструкциями.

## Канонические пути

| Область | Путь |
|---|---|
| Единственный web frontend | `arkaim-web/src/` |
| Frontend routes | `arkaim-web/src/app/` |
| Frontend API contracts | `arkaim-web/src/shared/api/contracts/` |
| FastAPI entry | `runtime/core/main.py` |
| Routes | `runtime/core/routes/` |
| Knowledge Cards API | `runtime/core/routes/knowledge_cards.py` |
| Knowledge Cards builder | `core/CORE/knowledge_card/builder.py` |
| DI registry | `runtime/core/adc_deps.py` |
| World Engine | `core/CORE/narrative_engine/world_engine.py` |
| WorldModel/Temporal | `core/CORE/narrative_engine/world_model.py` |
| World provenance | `core/CORE/narrative_engine/world_provenance.py` |
| Crosswalk | `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` |
| SourceBadge | `arkaim-web/src/shared/ui/SourceBadge.tsx` |
| World provenance UI | `arkaim-web/src/shared/ui/WorldProvenanceCard.tsx` |

## Решения по очистке

- Активные спеки периода двух frontend историзированы.
- Knowledge Cards backend перенесены из «not implemented» в фактический IMPLEMENTED/TESTED/LIVE-confirmed статус на основании кода, тестов и уже зафиксированного live HTTP evidence.
- B4-C повышен до VERIFIED на основании ранее полученного browser evidence; повторный smoke не запускается, так как код B4-C не менялся.
- B10 отражён как VERIFIED на основании ранее выполненного e2e smoke; новые проверки не запускаются.
- Требования повторять B3/B4 audits отменены.
- Старые порты, routes и удалённые компоненты не исполняются до сверки с кодом.
- Документы удалены: **0**; причина — сохранение истории по OWNER-GO.
- Дубли текущей карты устранены логически: `CURRENT_DEVELOPMENT_STATE.md` — единственная текущая status map, этот индекс — её реестр.
- Бывшие v2-функции существуют только в `FRONTEND_RESTORE_BACKLOG.md`.

## Правила

- Упоминания бывшего v2 допустимы только как HISTORICAL, запрещённое состояние или backlog.
- `:3001` не является активным портом.
- Не создавать второй frontend и не возвращать v2 runtime.
- Старый TODO/WIP/PLAN не создаёт разрешений на работу.
- При смене статуса обновлять current state и индекс, не возвращая историю в active section.
- `VERIFIED` допускается только при наличии проверяемого live-результата или другого явного контрольного запуска. Уже зафиксированное ранее evidence сохраняет силу, если относящийся к нему код после проверки не изменялся; повторный запуск ради него не требуется.

**Активная документация не описывает `arkaim-web-v2` как существующий frontend и не содержит параллельной web-архитектуры.**