# FRONTEND FORENSIC AUDIT
## Backend как единственный источник истины → новый frontend

Дата: 2026-09-08
Статус: READ-ONLY АУДИТ. Ничего не реализовано, ни один файл кода не изменён.
Основание: решение владельца после закрытия M10.2 — «нужен НОВЫЙ frontend, клиент текущего backend/API/Core; старый frontend не является валидным продолжением».
Метод: дампы фактического OpenAPI-контракта (289 путей / 307 роутов), RBAC-матрица через обход include-дерева FastAPI, статический разбор legacy-кода (33 страницы), машинная сверка всех 91 API-вызовов legacy с реальными путями бэкенда.
Инструменты аудита (оставлены как evidence): `runtime/forensic_backend.py`, `runtime/forensic_rbac.py`, `runtime/forensic_fe.py`, `runtime/forensic_fe_check.py`, `runtime/forensic_manual.py` + дампы `forensic_*.txt`.

---

## Простыми словами

**1. Что было целью?**
Подробно разобраться, что реально умеет сегодняшний backend, что из себя представляет старый frontend, чем он противоречит backend, и что выбросить — до проектирования нового frontend.

**2. Что реально сделано?**
Снял полный «слепок» API бэкенда: 289 путей, роли для каждого, форматы ошибок, WebSocket/SSE-каналы, модель задач (job lifecycle) генерации ассетов. Разобрал старый frontend постранично: 33 страницы, 91 API-вызов — каждый сверен с реальным контрактом. Нашёл: 80 вызовов валидны, 11 — мёртвые пути (не существуют в backend), 4 — дубликаты роутов в backend. Плюс найдены 2 серверных дубликата пути и 3 ложных «мока» в dev-режиме.

**3. Что получилось?** — **PASS**: полный фактический контракт frontend↔backend зафиксирован (§3), карта legacy — в §4, устаревшие предположения — в §5, судьба каждой части legacy (A/B/C/D) — в §7.

**4. Есть ли проблемы?**
Да, три честных замечания (не блокируют проектирование, но фиксируются):
- **P1 — backend сам имеет 2 пары дублирующихся путей** (`/book/crowdfunding/*` ×2, `/book/os/clear` admin против reader-модификаций и др.) и **3 маршрута-заглушки** (research-engine `apply`, presence stats у crowdfunding) — новый frontend должен опираться только на подтверждённые контракты, не на заглушки;
- **P2 — 4 «публичных» группы маршрутов** (`/xray/*`, `/research-engine/*`, `/story-engine/*`, `/world-explorer/*`) фактически не защищены RBAC на уровне роутера (проверка внутри тела или вообще отсутствует) — frontend обязан сам не выводить их читателю, но защищённость — вопрос backend, не этого этапа;
- **P3 — legacy mock-механика** возвращает поддельные данные в dev-режиме при 401 — из-за неё «работающая» страница notifications реально не соединяется с backend (11 мёртвых путей). В новом frontend моки допустимы только как явно изолированный dev-слой.

**5. Что предлагается дальше?**
Утвердить архитектуру нового frontend (`docs/FRONTEND_ARCHITECTURE.md`) и план поэтапной реализации; legacy — держать в работе до готовности поэтапной замены (не чинить), после — удалить.

---

## 1. Методика и границы

| Вопрос аудита | Как проверено |
|---|---|
| Реальные frontend-facing endpoints | Живой импорт `core.main:app` → OpenAPI: 289 путей, 307 APIRoute (обход `_IncludedRouter` FastAPI 0.136) |
| RBAC каждого маршрута | Обход include-дерева, извлечение ролей из замыканий `require_role` (router-level + endpoint-level) |
| Публичные, но на деле защищённые | Полнотекстовый поиск `get_current_user`/`verify_request` внутри тел endpoint'ов |
| Legacy-вызовы | Статический парсинг `api.(get\|post\|put\|delete)` всех 33 страниц + машинная сверка с OpenAPI |
| Streaming/realtime | Чтение `main.py`, `websocket.py`, `useStreamingChat.ts`, `ws.ts` |
| Job lifecycle | Чтение `visual_assets/queue.py`, `schemas.py`, `routes/assets.py`, `film_studio.py` |

Ничего не изменялось: только чтение и генерация дампов в `runtime/forensic_*.txt` + 5 одноразовых скриптов аудита.

## 2. Фактический контракт: транспорт и форматы

### 2.1 Транспорт

| Канал | Контракт |
|---|---|
| HTTP REST | FastAPI :8642; фронт проксирует через Next rewrites (`/auth/*`, `/xray/*`, `/book/*`, `/v1/*`, `/api/*`→backend, `/analytics`) |
| WebSocket | `GET /ws?token=<JWT>` (cookie `arkaim_session`) — события: `pulse_beat`, `new_suggestion`, `service_status`, `new_question`, `your_question_answered` (user-targeted), `chat_response` (user-targeted), `crowdfunding_milestone`; формат `{event, data}` |
| SSE chat | `POST /v1/stream` (auth: Bearer/cookie) — `text/event-stream`, `data: {"text": ...}` |
| SSE xray | `GET /xray/events/stream` — типизированные события: `trace_completed`, `trace_started`, `trace_ended`, `trace_frozen`, `orphan_change`, `stats_changed`, `heartbeat` (каждую 1 сек) |

### 2.2 Формат ответов

**Два сосуществующих стиля** (факт, не идеал):
1. **Enveloped (M10.2, assets, reader и др.):** `{"ok": true, "data": <payload>, "trace_id"?}`; ошибки — глобальный handler: `{"ok": false, "error": {"code": "HTTP_409", "message": ...}}`.
2. **Direct-return (многие старые роуты):** сырой payload без конверта (`world/summary`, `graph/*`, `temporal/chain`, `auth/me` → `{user: {...}}` и т.п.).

Новый API-слой обязан уметь оба: конверт определяется per-endpoint в typed contract-модуле (§FRONTEND_ARCHITECTURE).

### 2.3 Аутентификация

| Механизм | Детали |
|---|---|
| JWT | Bearer `Authorization` или cookie `arkaim_session` (httponly, 12ч, samesite=Lax) |
| Провайдеры входа | `/auth/login` (Telegram widget), `/auth/google`+callback, регистрация `/auth/register`, инвайты `/auth/invite/{token}` |
| Сервисный ключ | `HERMES_API_KEY` (в `/v1/*` через `verify_request`) — роль admin (service), если не привязан к пользователю |
| API-ключи пользователя | SHA256-hash ключи, дают роль владельца ключа |
| `/auth/me` | `{user: {id, role, provider, username, display_name}}` — источник роли для UI-развилок |

### 2.4 RBAC-матрица (полная, из замыканий роутеров)

| Роль (require_role) | Число маршрутов | Примеры |
|---|---|---|
| admin | 43 | `/auth/admin/*`, presence approve/reject, email send, evolution evolve/rollback, community-модерация, crowdfunding config, `os/clear`, reader/stats |
| admin+editor | 3 | temporal pending-updates scan/confirm/reject (M10.2) |
| admin+editor+reader | 4 | temporal pending-updates list/stats/history/detail (M10.2) |
| admin+reader | 2 | assets delete-all, assets/{id} DELETE |
| editor | 40 | film-studio CRUD, generate, os/ingest, visual-genome, email drafts, drafts approve, presence suggestions list |
| editor+reader | 8 | assets generate*, regenerate, world/validate |
| reader | 69 | ask, genome, chapters, text, world view, temporal view, reader history, os search, presence observe/trending, visualize |
| public (без роутер-гейта) | 138 | auth-флоу, community read, graph, health, xray, research/story/world-explorer, v1/chat/stream, comfyui config |

**Роль читателя по умолчанию при регистрации:** reader (`auth/routes.py:56`).

**Публичные, но фактически с auth-проверкой в теле:** `/v1/chat`, `/v1/stream` (verify_request), `/book/reader/*` (get_current_user в теле).
**Публичные и реально открытые:** `/xray/*` (24 маршрута), `/book/research-engine/*` (7), `/book/story-engine/*` (6), `/book/world-explorer/*` (21), `/book/graph/*` (6), `/book/os/*` (16), `/book/comfyui/config POST`. — **Фронтенд не должен показывать их не-администратору как «функции», но и не должен скрывать возможности читателя, где роль не требуется.**

### 2.5 Модель задач (Job lifecycle)

| Подсистема | Контракт |
|---|---|
| **Asset generation queue** | `POST /book/assets/generate-async` → `{task_id, status: "queued"}`; опрос `GET /book/assets/queue/task/{task_id}` → `{task_id, status: queued\|generating\|completed\|failed, asset_id?, error?}`; статистика очереди `GET queue/status` → `{queue_size, workers_running, results_count, running}`. Статусы живут в `VisualAsset.status` (pending/generating/completed/failed), результат содержит полный asset |
| **Film assemble** | `POST /film/{id}/assemble` → `{status: "assembling"}`; опрос `GET /film/{id}/assemble/status` → `{status: preparing\|assembling\|completed\|failed, progress?}`; скачать `GET /film/{id}/output` |
| **Research jobs** | `POST /research-engine/extract|search|enrich` → job `{id, status}`, list `GET /jobs`, `apply/{job_id}` — **заглушка (просто возвращает ok)** — НЕ считать реальным контрактом применения |
| **Book OS ingest** | синхронные POST (documents/ingest, pipeline/ingest, index, build-bm25) — без job-модели, ответ сразу |
| **World explorer** | `POST explore` → exploration `{exploration_id, ...}` синхронно; история `GET history` |
| **Temporal proposals (M10.2)** | `POST scan` → `{book_changed, new_findings, total_pending}`; `GET list/stats/history/{id}`; `POST confirm/reject` — **единственная очередь проекта с подтверждением на сервере, всё in-memory** |

### 2.6 Discovery и manifests

| Что | Где | Контракт |
|---|---|---|
| Источники исследования | `GET /book/world-explorer/sources/search` | public |
| Провайдеры LLM | `GET /book/providers/list`, `GET /book/providers/status` | public (список gigachat/openrouter) |
| ComfyUI | `GET /book/comfyui/status`, `GET/POST /book/comfyui/config` | public |
| Capabilities-подобные | отсутствуют как отдельная сущность | «Capability» в терминах владельца = группы endpoint'ов (assets, film, temporal, world, explorer, community, presence, email, evolution); отдельных capability-manifest endpoints в backend НЕТ |

> **Важно для проектирования:** backend НЕ имеет `/discovery`-endpoint'а или manifest-механики. «Discovery» для нового frontend = навигация по статической карте известных endpoint-групп, построенной в build-time на основе OpenAPI. Не выдумывать несуществующих endpoints.

### 2.7 Найденные дефекты контракта (backend, не для исправления сейчас)

| # | Дефект | Влияние на frontend |
|---|---|---|
| D1 | Дубли путей: `/book/crowdfunding/*` и `/book/book/crowdfunding/*` (оба смонтированы); `crowdfunding/config` GET×2 и POST×2; `check-now` ×2; `milestones/check` ×2 | не вызывать `/book/book/*` (артефакт монтирования) |
| D2 | `/book/research-engine/apply/{job_id}` — заглушка («applied», ничего не применяет) | UI не должен обещать «применение находок» |
| D3 | Противоречие RBAC: `/book/os/clear` — POST admin; `/book/os/chunks` DELETE + `os/documents/ingest` POST — editor; при этом весь `os/*` остальной — reader/public | в UI действия очистки — только editor/admin |
| D4 | `/book/presence/suggestions/stats` admin-only, а list — editor: асимметрия (список editor видит, статистику — нет) | показывать stats только admin |
| D5 | Присутствие `GET /` (public redirect на `/_ui/book`) и одновременно root-роут фронтенда | фронт занимает `/` своим роутингом |
| D6 | `/book/assets/generate` (editor+reader) и `delete` (admin+reader) — reader-доступ к генерации/удалению выглядит шире необходимого | UI должен рендерить строго по фактической RBAC-матрице, не по «здравому смыслу» |

## 3. КАРТА LEGACY FRONTEND

### 3.1 Стек

Next.js 16 (App Router, turbo) + React 19 + AntD 6 (+ кастомный light-слой) + Tailwind 4 + TanStack Query 5 + react-hook-form + zod. Тесты: vitest + playwright (в devDeps). SSR/RSC не используются (все страницы `'use client'`).

### 3.2 Страницы (33) и их API-вызовы

| Страница | Строк | Query/Mut | API-вызовы (реальные backend-пути) |
|---|---|---|---|
| /about | 218 | Q | evolution/status, genome, layers |
| /admin | 42 | панель-роутер | (panels: users/sessions/invites/api-keys/stats/moderation/dashboard) |
| /analytics | 255 | Q | /analytics, auth/admin/stats, graph/stats |
| /api | 418 | Q+M | auth/api-key, api-keys |
| /artifacts | 237 | Q+M | community/artifacts CRUD |
| /ask | 282 | Q | book/ask, reader/profile (+mock) |
| /assets | 294 | Q+M | book/assets list, batch, queue/status |
| /book | 383 | Q | book/ask, reader/history (+mock) |
| /crowdfunding | 312 | Q+M | crowdfunding ×4 |
| /editor | 492 | Q+M | genome, visual-genome ×4 |
| /film-studio | 813 | Q+M | film create/list/shots/project |
| /genres | 342 | Q | genome |
| /help | 236 | — | — |
| /history | 140 | Q | reader/history ×4 |
| /interpretations | 197 | Q+M | community/interpretations |
| /library | 264 | Q | evolution/status, genome, layers |
| /login | 153 | — | /api/auth/login (собственный route handler) |
| /map | 354 | Q | community/map-data, temporal/nodes |
| /notifications | 263 | Q+M | **9 мёртвых путей** (см. 3.3) |
| /profile | 445 | Q+M | auth/update-profile, api-keys, community mine, email/subscribe, reader ×2 |
| /reading | 175 | Q | chapters ×2 |
| /recommendations | 285 | Q | genome, presence/trending, reader/profile |
| /register | 147 | — | auth/register |
| /screenplay | 193 | Q | screenplay ×2 |
| /search | 499 | Q | community/search, graph/entity, os/search, os/facts, os/entities |
| /settings | 494 | Q+M | admin/sessions, api-keys, comfyui, update-profile |
| /story | 395 | Q+M | story-engine/constraints, **world-engine/model (мёртвый)** |
| /upload | 255 | Q | os/documents/ingest (через UI) |
| /visual | 438 | Q+M | assets/generate ×3, genome, visual-genome ×4 |
| /visual-view | 584 | Q | genome |
| /world-engine | 306 | Q | world/entity, modes, rules, summary |
| /world-explorer | 290 | Q+M | world-explorer ×11 |
| /xray | 140 | Q | xray/stats, traces |

Итого **91 call-site**, 80 валидных, 11 невалидных.

### 3.3 Мёртвые/несуществующие пути (машинная сверка)

| Вызов legacy | Реальность backend |
|---|---|
| `/book/trending` | не существует; факт: `/book/presence/trending` |
| `/book/world-engine/model` | не существует; мир = `/book/world/*` (summary/entity/modes/rules) |
| `/book/graph/entity/{id}` | не существует; есть `/book/graph/entity/{id}/neighbors` и `/graph/context/{id}` |
| `/notifications/email/*` ×5 | не существуют; реально: `/book/email/*` |
| `/notifications/suggestions*` ×2 | не существуют; реально: `/book/presence/suggestions*` |
| (страница целиком) /notifications | живёт только на моках dev; в prod — 404 на все вызовы |

### 3.4 Компоненты

- **widgets/admin-panel** (7 панелей, ~770 строк): users, sessions, invites, api-keys, stats, moderation, dashboard — все на реальных контрактах, качество высокое
- **widgets/app-shell**: Sidebar (135), Topbar (232), index
- **shared/lib**: api.ts (372, вкл. 100+ моков), ws.ts (86, reconnect+jitter — хороший), useStreamingChat (101, SSE-парсер /v1/stream), useGenerateImage, useSearchPanel, guards (RoleGuard), markdown, theme
- **shared/ui**: light-обёртки AntD (23 компонента, ~1500 строк) + ChatBubble, Comments, CommunitySearch, ErrorBoundary, GenerationQueueStatus, GenerationSettingsPanel, NotificationBell, SourceBadge, ComfyUIStatus
- **shared/types/index.ts** (414): ручные TS-типы, частично устаревшие (не соответствуют новым pydantic-схемам M10.2)

### 3.5 Mock-механика (главная ловушка legacy)

`api.ts`: при `NODE_ENV=development` **любой 401 отдаёт мок**. Следствие: страницы «работают» в dev без backend. В prod те же страницы падают. Моки скрывают: разрывы контракта (11 мёртвых путей), отсутствие авторизации, пустые состояния. **Это архитектурно неверный паттерн** — новый frontend запрещает mock при 401 (мок только как явно включаемый флаг с жесткими списками путей).

## 4. УСТАРЕВШИЕ ПРЕДПОЛОЖЕНИЯ LEGACY

| # | Предположение legacy | Реальность backend |
|---|---|---|
| U1 | «Страница notifications = Presence+Email» через `/notifications/*` | пути `/book/presence/*`, `/book/email/*`; кроме того presence **персистит в JSON** и имеет admin-гейт approve |
| U2 | `world-engine/model` — единственный источник модели мира | нет такого пути; мир = `/book/world/*` (summary/entity/context/visual-prompt/rules/modes/form-library/categories/search/validate) |
| U3 | `graph/entity/{id}` — получение сущности | есть только neighbors/context |
| U4 | `book/trending` | `book/presence/trending` |
| U5 | RBAC = admin/edit/reader на редких страницах через RoleGuard | фактичческая матрица сложнее (307 роутов, 8 групп); часть admin-действий в community open (like), часть editor+reader (генерация) — UI обязан следовать фактической матрице |
| U6 | Моки «честны» | моки маскируют 401 и мёртвые пути |
| U7 | Сессия только cookie | cookie + Bearer + API-key + service key (4 механизма) |
| U8 | «upload = documents ingest» | os-инжест editor-гейтован, но страница upload не рендерит гейт (reader видит форму) |
| U9 | temporal = только `temporal/nodes` (map) | после M10/M10.2: полный набор `/book/temporal/*` (chain, chains, nodes, node, context, future-extrapolation, reconstruct, pending-updates ×7) — legacy о них не знает |
| U10 | job = только assets queue | есть film assemble job, research jobs (заглушка apply), world-explorer history — каждая со своим lifecycle |

## 5. ПРИГОДНЫЕ ЧАСТИ LEGACY (судьба по A/B/C/D)

| Часть | Класс | Обоснование |
|---|---|---|
| `ws.ts` (WS-клиент: reconnect+backoff+jitter, cookie-token) | **A — переиспользовать** | контракт `/ws` совпадает; чистая реализация |
| `useStreamingChat` SSE-парсер `/v1/stream` | **A** | точный контракт `data: {text}` |
| `api.ts` fetch-обёртка (без моков) | **A (только скелет)** | retry/redirect-логика; мок-часть выбросить |
| light-обёртки AntD (23 шт) | **A** | чистые UI-примитивы, без business logic |
| RoleGuard, ErrorBoundary, SourceBadge, ChatBubble, GenerationQueueStatus | **A** | контракто-совместимы |
| admin-panel (7 панелей) | **A** | на реальных контрактах, аккуратно |
| app-shell (Sidebar/Topbar) | **B — визуальный reference** | навигация меняется (новый page map), визуал сохраняем |
| страницы ask/book/story/film-studio/world-explorer | **B** | UX-паттерны полезны, но переписываются на typed contracts |
| `shared/types/index.ts` | **C — выбросить** | ручные типы разъехались с pydantic; новый слой = генерация из OpenAPI |
| мок-механика api.ts | **C** | архитектурно неверна (U6) |
| /notifications страница | **C** | 9 мёртвых путей |
| `/story` world-engine/model | **C** | мёртвый путь |
| Sidebar-структура 34-страничной навигации | **C** | не отражает контрактные группы backend |
| map page (TemporalNode из `/book/temporal/nodes`) | **D — отдельное решение** | зависят от решения по карте (визуализация графа — вне Phase 1) |
| playwright/vitest-обвязка | **D** | сохранить подход, конфиг переписать под новый app-root |
| **D-критичное:** `AGENTS.md`/`CLAUDE.md` в arkaim-web | **D** | предписывают Next-специфику, устареть не должны, но при новом frontend пересмотреть |

**Принцип деления:** чистая новая архитектура важнее максимального переиспользования. Класс A — только то, что не тянет за собой ни одного устаревшего предположения.

## 6. GAPS (что legacy не покрывает из реального backend)

| Возможность backend | Legacy статус |
|---|---|
| temporal pending-updates (M10.2, 7 endpoints) | **нет вообще** |
| temporal chain/nodes/context/future-extrapolation | только nodes на /map |
| world model: categories, form-library, visual-prompt, validate, search | частично (entity/modes/rules/summary) |
| assets job lifecycle (queue/task/status) | частично (queue/status есть, task/{id} опроса нет) |
| film assemble lifecycle (status/output) | частично (list/create, без assemble-цикла) |
| presence queue + admin approve/reject | **нет** (мёртвый путь /notifications/suggestions) |
| email queue (drafts/approve/send) | **нет** (мёртвый путь) |
| evolution (diff/evolve/rollback/versions) | **нет** |
| drafts approve | **нет** |
| xray observability (traces/SSE) | минимально (stats+traces) |
| community timeline/search/map-data | частично |
| reader history sessions/stats/full | есть |
| invite-флоу | нет UI |
| comfyui config | есть (settings) |
| providers list/status | нет UI |

## 7. ВЫВОДЫ ДЛЯ АРХИТЕКТУРЫ (мостик к FRONTEND_ARCHITECTURE.md)

1. **Контракт богаче, чем legacy:** backend поддерживает 15+ доменных групп, legacy покрывает ~60% и содержит 11 мёртвых путей → новый frontend строится от контракта, не от страниц.
2. **Две конвенции ответов** → typed contract-слой с per-endpoint envelope-флагом (см. выше 2.2).
3. **RBAC-матрица — истина для UI-развилок:** навигация и действия рендерятся из матрицы §2.4 (адаптивно к роли из `/auth/me`).
4. **Realtime уже существует** (WS 7 событий + 2 SSE) → фронт обязан потреблять, не изобретать polling, кроме job-статусов (polling по контракту queue/task).
5. **Job-модели разные** (assets queue, film assemble, research-jobs) → единый фронтовый паттерн «Operation tracker» поверх трёх разных контрактов, без дублирования их логики.
6. **Моки — изолированный dev-слой**, никогда не по 401.
7. **Backend-дефекты D1–D6** фиксируются в архитектуре как «известные исключения» (не вызывать /book/book/*, не обещать research apply, os/clear — admin-only UI и т.д.).

---

*Аудит завершён. Реализация не производилась. Следующий документ: `docs/FRONTEND_ARCHITECTURE.md`.*
