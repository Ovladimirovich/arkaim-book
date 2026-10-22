# Текущее состояние проекта ARKAIM

**Нормативность:** этот документ — текущая source-of-truth карта состава и статусов. Фактическими доказательствами считаются код, конфигурация, тесты и live-проверки. Дата контрольной актуализации: 2026-10-21 (аудит `docs/AUDIT_AND_DEV_PLAN_2026-10-21.md`).

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
- Честная индикация ошибок на экранах: `reading`/`profile` — never-mocked пути (`/book/chapters*`, `/book/reader/profile`) в `shared/lib/api.ts` (ERROR-STATE-DISPLAY-1); `notifications`/`recommendations`/`search`/`library`/`interpretations`/`artifacts`/`map`/`genres` — `StateView state="error"` с кнопкой повтора вместо пустых таблиц, вечного спиннера, ложных «Ничего не найдено», «Данные не загружены» и «Пока нет …» (все 4 панели notifications; genome/profile/trending recommendations; все 6 панелей search — глобальный поиск, знания, сообщество, факты, сущности, граф; все 3 вкладки library — геном, слои, эволюция; списки interpretations/artifacts — при сбое stats-запроса показывается «—», а не выдуманные нули; сбой отправки форм interpretations/artifacts — видимая ошибка с повтором вместо молчания; все вкладки map — карта, локации, маршруты (пустая карта и пустые карточки вместо ошибки) и хронология (красный текст без кнопки повтора); все 3 вкладки genres — ложные «Данные не загружены»/«Ценности не определены» и нули в счётчиках вместо «—»). Покрыто `tests/unit/api.test.ts` (never-mocked) и `tests/unit/error-state-screens.test.tsx` (401, 503, недоступный сервер, восстановление после повтора, успешный рендер без баннера — 48/48: notifications 5, recommendations 6, about 6, admin 8, map 6, genres 5, library 5, search 7; 23 проверки map/genres/search/library восстановлены из удалённого и никогда не коммитившегося smoke-скрипта make-screens-error-state-smoke).

### 3.2. Статусы консолидации

| Работа | Статус | Каноническая запись |
|---|---|---|
| Перенос функциональности из бывшего v2 | **IMPLEMENTED / VERIFIED** | `docs/FRONTEND_POLISH_PASS_REPORT.md` |
| Polish Pass | **IMPLEMENTED / VERIFIED** | `docs/FRONTEND_POLISH_PASS_REPORT.md` |
| SourceBadge | **IMPLEMENTED / TESTED** | `arkaim-web/src/shared/ui/SourceBadge.tsx`, `arkaim-web/tests/unit/source-badge.test.tsx` |
| Честная индикация ошибок (`notifications`, `recommendations`, `search`, `library`, `interpretations`, `artifacts`, `map`, `genres`) | **IMPLEMENTED / TESTED** | `arkaim-web/src/app/notifications/page.tsx`, `arkaim-web/src/app/recommendations/page.tsx`, `arkaim-web/src/app/search/page.tsx`, `arkaim-web/src/app/library/page.tsx`, `arkaim-web/src/app/interpretations/page.tsx`, `arkaim-web/src/app/artifacts/page.tsx`, `arkaim-web/src/app/map/page.tsx`, `arkaim-web/src/app/genres/page.tsx`, `arkaim-web/tests/unit/error-state-screens.test.tsx` |
| Очистка диалога на странице «Задать вопрос» (кнопка «Очистить» с подтверждением) | **IMPLEMENTED / TESTED** | `arkaim-web/src/app/ask/page.tsx`, `arkaim-web/src/shared/api/contracts/reader.ts`, `runtime/core/routes/reader.py`, `runtime/memory/store.py`; тесты `arkaim-web/tests/unit/ask-clear-history.test.tsx`, `runtime/tests/test_reader_clear_history.py`, `runtime/tests/test_memory.py` |
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
| Entity-centric Knowledge Card builder | **IMPLEMENTED / TESTED** | `core/CORE/knowledge_card/builder.py`; `runtime/tests/test_knowledge_cards.py` — 43 тест-функции. **Re-baseline 2026-10-11, HEAD `1e3f812` (коммит 2026-10-02): targeted Knowledge Core regression (20 файлов) — после фикса GO-8: 333 collected, 333 passed, 0 failed.** Было до фикса: 330/329 passed/1 failed (BASELINE-1) |
| Read-only API | **IMPLEMENTED / TESTED / LIVE CONFIRMED** | `runtime/core/routes/knowledge_cards.py`; router подключен в `runtime/core/main.py`; live 2026-10-02 (HEAD `1e3f812`): search/card/trace `200`, auth `401`, фильтры, pagination (`next_offset`, неизменные `totals`), реальные `RESOLVED`/`UNAVAILABLE`/`UNKNOWN` — отчёт `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md` |
| Cross-source provenance | **IMPLEMENTED / TESTED** | Раздельные claims и provenance для book, World Model, archaeology, cross-references и academic sources; отсутствие источника не заполняется вымышленным значением |
| Frontend Knowledge Cards | **IMPLEMENTED (отдельный route)** | Страница `arkaim-web/src/app/knowledge/page.tsx` (поиск + трассировка), компонент `arkaim-web/src/shared/ui/KnowledgeTraceCard.tsx` из M9; трассировка перенесена из `world-engine` (+ `arkaim-web/tests/unit/knowledge-route.test.tsx`, `knowledge-trace-card.test.tsx`) |
| Автоматическое разрешение конфликтов / LLM-интерпретация | **NOT IMPLEMENTED** | Реализованы только детектирование и показ различных источников/перспектив |

Контрольный результат 2026-10-01: backend 37/37, frontend unit 17/17, core World/B3-B/provenance 8/8. Live-check подтвердил search `200` и card `200` для `region_arkaim` / `аркаим`; в ответе присутствуют раздельные book и archaeology claims.

**Re-baseline 2026-10-11 (HEAD `1e3f812`, коммит 2026-10-02) — фактический прогон Knowledge Core regression** (20 файлов: knowledge_cards, knowledge_kernel, M1, M2 contract/integration/lifecycle, M3, M4, M5, M6, M7, M8 trace/api/journey/present-anchor/future-extrapolation, provenance, provenance_completion, book_intelligence, visual_conflict): **до фикса 330 collected — 329 passed / 1 failed; после фикса GO-8 — 333 collected / 333 passed / 0 failed, 6 warnings, ~5s** (в файле knowledge_cards 40 → 43 тест-функции).

**BASELINE-1 (устранено, GO-8, 2026-10-11)** — `tests/test_knowledge_cards.py::TestAggregation::test_no_duplicate_claims`:
- классификация: **Knowledge Core, введено HEAD `1e3f812`** (не pre-existing, не unrelated);
- доказательство: эмуляция parent `6f4611b` (отключение нового `_genome_claims`) даёт 0 дубликатов; diff `1e3f812` в `core/CORE/knowledge_card/builder.py` — только аддитивный (+34);
- причина: `_book_claims` (`builder.py:295-324`) принимал genome-fallback результаты retriever и помечал их как AUTHOR_CANON `book:{chunk_id}`, тогда как `_genome_claims` (`builder.py:326+`, добавлен в `1e3f812`) проецирует тот же текст как DERIVED `genome:theme:{id}` → одинаковый текст в источниках `book` и `genome`;
- фикс (GO-8): в `_book_claims` пропускаются результаты `source == "genome"`; M2/M8 контракты, namespace policy и fail-closed не изменялись; +3 targeted tests (обычный book claim, только genome fallback, смешанные результаты);
- решение владельца: GO-8 (2026-10-11), вариант A (только этот регресс, другие проблемы не трогать).

**NEW-1 (обнаружено при GO-8, НЕ исправлено, вне объёма):** при незагруженном World Engine (`builder.py:80-90`, путь деградации) источники `world_model` и `archaeology` возвращают одинаковые тексты (7 пар у `region_arkaim`); в штатном пути дублей нет.

**GO-free семантики зафиксированы документацией (T3, 2026-10-11, без изменения поведения):** `search.total` = размер возвращённой страницы (`len(entities) ≤ limit`, глобального счётчика нет; добор из `ARCHAEOLOGY.json` не фильтрует по `q`), `uncertainty.has_unknowns` = card-level `bool(unknown_aspects)` по 4 источникам и **не зависит** от evidence-статусов/`trace.status` (у `region_arkaim` 7 `UNKNOWN` evidence при `has_unknowns=false`). Описание: SoT-план (M8, подраздел «Фактическая семантика…») + docstring endpoint-ов `runtime/core/routes/knowledge_cards.py`. Побочно замечено (не исправлялось): 4 из 14 `entity_id` из `search?q=аркаим&limit=50` дают 404 на карточке.

**Claim ↔ evidence join явный (T4, 2026-10-11, additive):** каждая evidence-строка trace несёт `claim_id`, вычисляемый тем же мостом `_card_claim_id(claim)`, что и claims-секция; при невозможности достоверно установить соответствие (нет text/chunk_id, схема вне `book:`/`ARCHAEOLOGY.json:`/`external:` — напр. `genome:`, `world_model:`) — `null`; статус резолвера (RESOLVED/UNAVAILABLE/UNKNOWN) на identity не влияет. DTO/M2-схемы/статусы/namespace policy/fail-closed не менялись. +5 targeted tests (4 unit + journey на реальном `region_arkaim`); baseline **338/338 passed / 0 failed**; `git diff --check` чисто.

**Frontend-контракт и lineage UI синхронизированы (T5, 2026-10-11, только frontend):** типы `arkaim-web/src/shared/api/contracts/knowledge.ts` приведены к `KnowledgeTraceResponse` (добавлены `lineage`, `totals`, `offset`, `limit`, `next_offset`, типизированная evidence-строка с `claim_id`; `getKnowledgeTrace` принимает `offset`/`limit` как query); `KnowledgeTraceCard` рендерит секцию Lineage (filled/empty/missing), блок totals+pagination и `claim_id` в evidence-строке, поддерживает состояния `loading`/`error`; `world-engine/page.tsx` различает загрузку/ошибку/нет данных. Проверки: **vitest 84/84 passed (16 файлов)**, `eslint` 0 errors, `next build` (production + type-check) exit 0. Backend не менялся. **H1 завершён (STOP): T1/T1b/T3/T4/T5 DONE, T2 — ждёт GO-9; дальше — только OWNER-GO (GO-1…GO-7).**

**Git-фиксация H1 выполнена (T2 / GO-9, 2026-10-11):** в commit внесены код и тесты H1 (GO-8 фикс, T3-docstring'и, T4 `claim_id`, T5 frontend), 19 knowledge-документов (A-list + `CURRENT_DEVELOPMENT_STATE.md`), runtime-ассет `runtime/xray_dashboard/` (монтируется `main.py:447`), `AGENTS.md` (ремонт кодировки подтверждён владельцем) и junk-паттерны корневого `.gitignore` (файлы на диске не удалялись). Не включены по решению владельца: `docs/archive/`, `SCHEMAS/`/`scripts/`/`notebooks/`/корневой `tests/`/`core/run_*.py`/runtime-утилиты/`core/.gitignore`/AI-конфиги, genome-снимки и modified `core/CORE/genome/history/index.json`. Проверки перед commit: backend 338/338, vitest 84/84, lint 0 errors, build exit 0, `git diff --check` чисто.

**H2-A выполнен (GO-1 + GO-2, 2026-10-11):** **GO-1 — правило `trace.status`:** `COMPLETE` ⇔ есть claims ∧ все evidence-строки `RESOLVED` ∧ нет `limitations`; иначе `PARTIAL` (обрыв пути: `UNAVAILABLE`/`UNKNOWN` evidence и пр.); отдельный `UNKNOWN` не вводится (зарезервирован в словаре `TraceabilityStatus`, пустая сущность остаётся `PARTIAL`); статус считается по полному набору evidence до секционных фильтров/пагинации — правка в docstring + `evidence_unresolved` в `runtime/core/routes/knowledge_cards.py`; +3 unit-теста в `test_m8_knowledge_trace_api.py`, journey-правило (`test_m8c_trace_journey.py`) обновлено под новую семантику; live `region_arkaim` → **`PARTIAL`** (17 `RESOLVED` + 7 `UNKNOWN`, limitations пусты — раньше был `COMPLETE`, live-проблема №1 закрыта). **GO-2 — единый формат 422:** глобальный `RequestValidationError`-handler в `runtime/core/main.py` отдаёт envelope `{"ok":false,"error":{"code":"HTTP_422","message":…,"details":[{"loc","msg","type"}]}}` на всех routes (рядом с `HTTPException`-handlerом — единая форма 401/404/422/500); статусы и состав ошибок валидации сохранены; фронт без правок (`errors.ts::parseErrorBody` уже парсит envelope); 6 новых тестов в новом `runtime/tests/test_error_envelope_422.py` (включая регрессии 401/404). Проверки: **baseline 20 файлов 338 → 341 passed / 0 failed** (+ отдельный файл 6 passed, `test_md3_route_a` 11 passed), **vitest 84/84**, acceptance TestClient на реальных данных OK. Решения зафиксированы: SoT §2.5 + OWNER-GO ITEMS (п.1-2 RESOLVED), roadmap (§1/§2/§4/§5/§9). **Commit не выполнялся — нет явного GO.**

Live-верификация 2026-10-02 (HEAD `1e3f812`, read-only): search/card/trace `200` на 7 реальных сущностях, auth `401` без токена, фильтры и pagination работают, claim → evidence → source → world/temporal подтверждены, evidence-статусы фактические (напр. `region_arkaim`: 17 `RESOLVED` / 1 `UNAVAILABLE` / 7 `UNKNOWN`). Conflicts / reasoning / corrections / lineage в live пусты — `runtime/runtime_data/knowledge/` существует и не содержит production-записей; искусственные данные не создавались. Полный отчёт с фактическими результатами, DOC DRIFT и PROBLEMS: `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`.

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

### 4.3. Инженерное состояние (актуализировано 2026-10-22)

- CI зелёный: `ruff check` + `ruff format --check` в `runtime/` — чисто; `tsc --noEmit` — чисто;
  `eslint` — 0 ошибок; backend `pytest tests` — **2636 passed, 27 skipped, 2 deselected, 0 failed**;
  frontend `vitest run` — **241/241 в 31 файле**; `core/CORE/narrative_engine/tests` — 26 passed.
- Живые медиа-прогоны помечены маркером `live` и исключены из обычного прогона
  (`runtime/pyproject.toml`: `addopts = -m 'not live'`).
- Stage 2 (gap-driven расширение знаний) — **за флагом** `STAGE2_ENABLED` (по умолчанию выключен);
  пишет предложения в runtime-пространство, а не в `core/KNOWLEDGE`.
- Единый реестр имён: `nameresolver` собирается из утверждённой владельцем таблицы
  `knowledge/screenplay_scene_aliases.py`; guard-тест `tests/test_name_registry_consistency.py`.
  «Велика» склеена с «Велик» (решение G7a).
- Provenance: разрушительный `scripts/enrich_knowledge_provenance.py` удалён, вместо него
  read-only `scripts/validate_knowledge_provenance.py`; guard-тест `tests/test_provenance_registry_consistency.py`.
  Канон определён данными на диске (решение G13): реестр приведён к `_provenance_metadata`,
  `is_canon` выводится из категории, проверка равенства включена в guard-тест.
  Канон: `BOOK_DOCUMENT.json`, `SYNOPSIS_DOCUMENT.json`, `AUTHOR_INTENT.json`.

### 4.4. Решения владельца от 2026-10-22

| Решение | Итог |
|---|---|
| G6 — 7 несопоставленных регионов | `PRESERVE_UNCHANGED`, зафиксировано в crosswalk-артефакте. Гейт закрыт |
| G7a — «Велика» vs «Велик» | Склеено в «Велик»; оба реестра совпадают |
| G9 — 3 сцены без claim-связи | Одобрены: сцен `scene_003`, `scene_021`, `scene_022` получили событие и эпоху. Связей claim→событие 18 (было 15); сцен с подтверждённой эпохой 14 (было 11); сцен с книжной связью без claim-связи не осталось |
| G13 — канон | Канон — как на диске: `core/KNOWLEDGE/*` не менялись, реестр приведён к ним |
| G14 — дубли id в модели мира | Помечены `also_in_categories` / `pseudonym` + `canonical_id`; ничего не удалено. Guard-тест `tests/test_world_model_identity.py` |
| G15 — запись в World Model из пилота | Остаётся dry-run: CLI не создаётся, модель мира меняется только ручной правкой |

Полный перечень и открытые пункты — `docs/OWNER_DECISION_SHEET.md`.

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
- Knowledge Cards backend: builder, cross-source aggregation и read-only API — implemented/tested/live-confirmed; полный live HTTP evidence зафиксировано в `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md` (2026-10-02).
- Polish Pass.
- Frontend consolidation: v2 удалён, `arkaim-web` — единственный frontend.
- SourceBadge и его тестовое покрытие.
- Честная индикация ошибок на `notifications`, `recommendations`, `search`, `library`, `interpretations`, `artifacts`, `map` и `genres` (сценарии 401/503/недоступный сервер/восстановление после повтора/успешный рендер без баннера — 48/48 unit-тестов в `tests/unit/error-state-screens.test.tsx` (notifications 5, recommendations 6, about 6, admin 8, map 6, genres 5, library 5, search 7); 23 проверки map/genres/search/library восстановлены как vitest-тесты из удалённого и никогда не коммитившегося smoke-скрипта make-screens-error-state-smoke; сценарий сбоя отправки форм interpretations/artifacts зафиксирован в исходниках панелей, отдельного unit-теста в этом файле нет); полный frontend unit suite **241/241 (31 файл)**, `npx tsc --noEmit` — exit 0, `npx eslint .` — 0 ошибок / 79 предупреждений (baseline) (проверено 2026-10-21).

### Не выполнено и не должно выдаваться за выполненное

- Новые World/Temporal mappings без утверждённого crosswalk.
- Provenance для relations, если backend реально не отдаёт такой provenance.
- Автоматическое разрешение конфликтов, LLM-интерпретация источников и mutation UI Knowledge Cards (сам route `/knowledge` реализован 2026-10-21 — см. 4.2).
- Новый frontend-проект, отдельный v2 runtime или возврат `:3001`.
- Мобильная функциональность, не представленная в коде.

## 7. Единая карта статусов

| Статус | Пункты | Фактическое доказательство |
|---|---|---|
| COMPLETED / ACTIVE | `arkaim-web`, backend `runtime`, domain `core/CORE`, mobile project | Физическое существование, конфигурация запуска и подключенные приложения |
| IMPLEMENTED | `arkaim-web`, Knowledge Cards API, B4-C World provenance UI | Реальные файлы, routes, components и регистрация в приложениях |
| TESTED | SourceBadge 12/12; World/contract 2/2; WorldProvenanceCard 3/3; полный frontend unit suite **241/241 passed (31 файл)** после T5 (knowledge-trace-card 11 + knowledge-contract 3); Knowledge Core regression (20 файлов) **341/341 passed, 0 failed** (re-baseline + фикс GO-8 + T4 claim↔evidence join + H2-A GO-1/GO-2, 2026-10-11, HEAD `1e3f812`; +5 тестов T4 + 3 теста GO-1); отдельный `tests/test_error_envelope_422.py` (GO-2) **6/6 passed**; core B3-B/provenance 8/8; auth/stream/discipline/related subset | Фактические прогоны 2026-10-11 (HEAD `1e3f812`) + прогоны 2026-10-01 |
| TESTED | Studio (Phase 1A/1B): `test_phase1a_studio.py`, `test_phase1b_studio.py`, `test_media_boundary.py`, `test_md3_media_plan.py` — **142 passed, 2 skipped**; `test_studio_art_direction.py`, `test_studio_image_job.py` — **23 passed** | `core/CORE/studio/`, `runtime/core/routes/studio.py`, `arkaim-web/src/app/studio/` — DI MediaClient зарегистрирован, прямые вызовы заменены на `registry.get("media_client")` |
| LIVE CONFIRMED | Backend Knowledge Cards search/card/trace | HTTP `200` (live 2026-10-02), JSON, наличие book/archaeology claims, корректный entity ID, фильтры/pagination/totals и реальные evidence-статусы; отчёт `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md` |
| PARTIAL | Документация | Устранены основные противоречия; часть исторических статусов требует маркировки |
| VERIFIED | B4-C browser smoke (`region_arkaim`, `region_hyperborea`, `region_gardarika`), B10 e2e smoke (`/ask`, `/history`, `/world-engine`, 1 passed) | Ранее полученное browser/e2e evidence; код после проверок не менялся |
| IMPLEMENTED | Отдельный Knowledge route | Страница `arkaim-web/src/app/knowledge/page.tsx` (поиск по карточкам знаний + трассировка), тест `arkaim-web/tests/unit/knowledge-route.test.tsx`; компонент `KnowledgeTraceCard` вынесен из `world-engine` (M9) |
| BLOCKED / OWNER DECISION | Новые production-функции; открытые вопросы по содержимому мира (G1, G5, G6, G8, G9, G10) | Расширение crosswalk (до `region_oceania`) и изменения данных одобрены владельцем 2026-10-20; остальные требуют отдельного OWNER-GO — перечень в `docs/OWNER_DECISION_SHEET.md` |

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