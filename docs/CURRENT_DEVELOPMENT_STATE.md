# Текущее состояние проекта ARKAIM

**Нормативность:** этот документ — текущая source-of-truth карта состава и статусов. Фактическими доказательствами считаются код, конфигурация, тесты и live-проверки. Дата контрольной актуализации: 2026-10-01.

## 1. Обязательные границы

- Единственный frontend проекта — `arkaim-web/`, порт разработки `3000`.
- `arkaim-web-v2/` удалён и не является средой запуска, архитектурой или рабочим направлением.
- Сравнивать `arkaim-web` с v2 запрещено. Бывшие функции v2 фиксируются только как потенциальные задачи в `docs/FRONTEND_RESTORE_BACKLOG.md`.
- Backend — `runtime/` (FastAPI), порт `8642`. Доменные/вычислительные модули находятся в `core/`.
- Mobile-клиент `arkaim-mobile/` существует отдельно и не меняет правило единственного web frontend.
- При расхождении документа с кодом, тестами, конфигурацией или этим индексом источником истины считаются код и явно принятые ADR.

## 2. Фактический состав

| Контур | Каталог | Текущее назначение |
|---|---|---|
| Web | `arkaim-web/` | Единственный Next.js frontend; App Router; страницы Book/Ask/Reading/World Engine/Temporal/History и служебные разделы |
| Backend | `runtime/` | FastAPI, DI, auth/session, routes, services, memory и backend tests |
| Domain/core | `core/CORE/` | Pulse, World Engine, Temporal, Knowledge/RAG, Knowledge Cards, media contracts и связанные модули |
| Mobile | `arkaim-mobile/` | Отдельный React Native/Expo клиент |
| ADR | `docs/ADR/` | Принятые архитектурные решения |
| Архив | `docs/archive/` | Исторические отчёты, спеки и аудиты; не текущие инструкции |

Порты и команды запуска описаны в `README.md`. Единственная актуальная frontend-команда запуска работает из `arkaim-web/`; `:3001` в активной документации не используется.

## 3. Frontend: консолидация завершена

### 3.1. Выполнено

- Polish Pass для `arkaim-web` выполнен и зафиксирован в `docs/FRONTEND_POLISH_PASS_REPORT.md`.
- `SourceBadge` существует в `arkaim-web/src/shared/ui/SourceBadge.tsx` и покрыт unit-тестом `arkaim-web/tests/unit/source-badge.test.tsx`.
- В `arkaim-web` присутствуют реальные страницы Ask, Book, Reading, Temporal, History, World Engine и связанные переходы.
- Auth/session, SSE/WS, typed API contracts, PWA и persistence представлены в текущем frontend-коде; их полный live-аудит не заявляется этим документом.

### 3.2. Статусы консолидации

| Работа | Статус | Каноническая запись |
|---|---|---|
| Перенос функциональности из бывшего v2 | **IMPLEMENTED / VERIFIED** | `docs/FRONTEND_POLISH_PASS_REPORT.md` |
| Polish Pass | **IMPLEMENTED / VERIFIED** | `docs/FRONTEND_POLISH_PASS_REPORT.md` |
| SourceBadge | **IMPLEMENTED / TESTED** | `arkaim-web/src/shared/ui/SourceBadge.tsx`, `arkaim-web/tests/unit/source-badge.test.tsx` |
| Возможное восстановление дополнительных функций v2 | **BACKLOG ONLY** | `docs/FRONTEND_RESTORE_BACKLOG.md` |

`docs/FRONTEND_CONSOLIDATION_PLAN.md` и `docs/FRONTEND_TRANSFORMATION_PLAN.md` сохранены как **HISTORICAL** записи периода миграции. Их этапы, сравнения и инструкции «перенести/удалить v2» больше не являются текущими задачами.

## 4. World / Temporal / provenance

### 4.1. B3

- B3-CW: первый утверждённый набор crosswalk mappings принят.
- B3-A: ID reconciliation выполнен; результат фиксирует `docs/B3A_ID_RECONCILIATION_REPORT.md`.
- B3-B: реализация подтверждённых Temporal-связей завершена в `core/CORE/narrative_engine/world_model.py` и тестах `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`.
- Старый `docs/B3B_PLAN.md` сохраняется как HISTORICAL, потому что описывает состояние до реализации.

Фактический crosswalk: `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`. Он не должен молча расширяться: новые mappings требуют явного решения владельца.

### 4.2. Knowledge Cards / cross-source API

| Этап | Статус | Фактическое доказательство |
|---|---|---|
| Entity-centric Knowledge Card builder | **IMPLEMENTED / TESTED** | `core/CORE/knowledge_card/builder.py`; `runtime/tests/test_knowledge_cards.py` — 37 passed |
| Read-only API | **IMPLEMENTED / TESTED / LIVE CONFIRMED** | `runtime/core/routes/knowledge_cards.py`; router подключен в `runtime/core/main.py`; live responses 200 и JSON-контракт подтверждены |
| Cross-source provenance | **IMPLEMENTED / TESTED** | Раздельные claims и provenance для book, World Model, archaeology, cross-references и academic sources; отсутствие источника не заполняется вымышленным значением |
| Frontend Knowledge Cards | **TODO** | Отдельного frontend-компонента или route Knowledge Cards в активном `arkaim-web` не обнаружено |
| Автоматическое разрешение конфликтов / LLM-интерпретация | **NOT IMPLEMENTED** | Реализованы только детектирование и показ различных источников/перспектив |

Контрольный результат 2026-10-01: backend 37/37, frontend unit 17/17, core World/B3-B/provenance 8/8. Live-check подтвердил search `200` и card `200` для `region_arkaim` / `аркаим`; в ответе присутствуют раздельные book и archaeology claims.

### 4.3. B4

| Этап | Статус | Фактическое место |
|---|---|---|
| B4-A — инвентаризация provenance | **IMPLEMENTED / TESTED** | `core/CORE/narrative_engine/world_provenance.py` |
| B4-B — read-only API | **IMPLEMENTED / TESTED** | World routes/contracts и `core/CORE/narrative_engine/tests/test_world_provenance.py` |
| B4-C — frontend provenance в карточке World entity | **IMPLEMENTED / TESTED / VERIFIED** | `arkaim-web/src/shared/ui/WorldProvenanceCard.tsx`, `arkaim-web/src/app/world-engine/page.tsx`, `arkaim-web/src/shared/api/contracts/world.ts`; целевые unit/API contract tests проходят. Browser evidence получено ранее: `region_arkaim` — PASS, `region_hyperborea` — provenance подтверждён после read-only диагностики, `region_gardarika` — PASS для missing related data, console без новых ошибок. Код B4-C после этой проверки не изменялся. |

`docs/B4_PLAN.md` и `docs/B4C_PLAN.md` сохранены как HISTORICAL планы. B4-C реализован в единственном `arkaim-web`: добавлены typed contract, `WorldProvenanceCard`, подключение к карточке World entity и unit/API contract tests. Browser evidence было получено ранее (см. выше) и после него код B4-C не изменялся, поэтому статус — VERIFIED без повторного запуска проверок. `SourceBadge` относится к B3 и не является частью B4-C.

Provenance остаётся read-only и не должен:
- выдумывать источник, URL, автора, главу или confidence;
- автоматически переноситься с сущности на relations/Temporal;
- менять World/Temporal data или crosswalk;
- подменять отсутствие источника нулевым процентом или fabricated badge.

## 5. API и auth/session

- Backend API контракт определяется работающим FastAPI-приложением и его схемами/DTO, а не старым v2 OpenAPI dump.
- Web обращается к backend через конфигурируемый proxy/base URL и типизированные contracts из `arkaim-web/src/shared/api/contracts/`.
- Browser session использует cookie `arkaim_session`, загрузку `/auth/me` и метод установления пользователя в текущем `AuthProvider`; dev-login не является production auth.
- Backend поддерживает JWT/API-key механики там, где это реализовано в `runtime/auth/` и dependency guards. Документ не должен приписывать frontend localStorage роль серверной сессии.
- RBAC описывается только по фактическим guards/permissions backend и текущим frontend guards/components. Старые v2 navigation/RBAC dumps являются историей, если явно не совпадают с кодом.

Актуальные OpenAPI-маршруты доступны в `http://localhost:8642/docs` при запущенном backend. Списки конкретных routes в старых спеках используются только как historical evidence до сверки с текущим `/openapi.json`.

## 6. Что выполнено и что осталось

### Выполнено и не требует повторного аудита

- B3-CW first batch.
- B3-A reconciliation.
- B3-B implementation.
- B4-A/B4-B implementation.
- B4-C implemented/tested/verified в `arkaim-web`; browser evidence получено ранее, код после проверки не менялся.
- B10 browser smoke выполнен ранее: `/ask`, `/history`, `/world-engine`, `1 test passed`.
- Knowledge Cards backend: builder, cross-source aggregation и read-only API — implemented/tested/live-confirmed (live HTTP evidence зафиксировано в отчёте).
- Polish Pass.
- Frontend consolidation: v2 удалён, `arkaim-web` — единственный frontend.
- SourceBadge и его тестовое покрытие.

### Не выполнено и не должно выдаваться за выполненное

- Новые World/Temporal mappings без утверждённого crosswalk.
- Provenance для relations, если backend реально не отдаёт такой provenance.
- Автоматическое разрешение конфликтов, LLM-интерпретация источников и frontend Knowledge Cards.
- Новый frontend-проект, отдельный v2 runtime или возврат `:3001`.
- Мобильная функциональность, не представленная в коде.

## 7. Единая карта статусов

| Статус | Пункты | Фактическое доказательство |
|---|---|---|
| COMPLETED / ACTIVE | `arkaim-web`, backend `runtime`, domain `core/CORE`, mobile project | Физическое существование, конфигурация запуска и подключенные приложения |
| IMPLEMENTED | `arkaim-web`, Knowledge Cards API, B4-C World provenance UI | Реальные файлы, routes, components и регистрация в приложениях |
| TESTED | SourceBadge 12/12; World/contract 2/2; WorldProvenanceCard 3/3; полный frontend unit suite 70/70; Knowledge Cards 37/37; core B3-B/provenance 8/8; auth/stream/discipline/related subset | Фактические прогоны 2026-10-01 |
| LIVE CONFIRMED | Backend Knowledge Cards search/card | HTTP `200`, JSON, наличие book/archaeology claims и корректный entity ID |
| PARTIAL | Документация | Устранены основные противоречия; часть исторических статусов требует маркировки |
| VERIFIED | B4-C browser smoke (`region_arkaim`, `region_hyperborea`, `region_gardarika`), B10 e2e smoke (`/ask`, `/history`, `/world-engine`, 1 passed) | Ранее полученное browser/e2e evidence; код после проверок не менялся |
| TODO | Knowledge Cards UI | В `arkaim-web/src/app` отдельного Knowledge Cards route нет |
| BLOCKED / OWNER DECISION | Расширение crosswalk, новые production-функции, изменения данных | Требуют отдельного OWNER-GO |

Следующие задачи берутся только из владельцем принятого roadmap/backlog. Старые планы не создают автоматического разрешения на работу.

## 8. Правила чтения документации

1. Для статуса и состава сначала открыть этот файл и `docs/DOCUMENTATION_INDEX.md`.
2. Для архитектурного решения проверить его ADR и фактический код.
3. Для маршрута проверить текущий `arkaim-web/src/app/` или FastAPI route registration.
4. Для команды проверить `package.json`, `pyproject.toml`, `Makefile`, Dockerfile или Compose.
5. Документ в `docs/archive/` читать только как history.
6. Старый `TODO/WIP/PLAN` не считать актуальным автоматически.
7. Упоминания `arkaim-web-v2` допустимы только с явной пометкой **HISTORICAL**, `:3001` как исторический порт либо как запрещённое состояние.

## 9. Итог

**Активная документация описывает одну текущую web-архитектуру: `arkaim-web` + `runtime` + `core/CORE`. Бывший v2 не существует как рабочая система; его функции представлены только backlog-задачами.**