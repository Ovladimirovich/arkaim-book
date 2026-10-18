<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL - НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Статусы, маршруты, компоненты и упоминания бывшего v2 ниже отражают состояние на момент создания документа. Актуальность проверяйте по docs/CURRENT_DEVELOPMENT_STATE.md, docs/DOCUMENTATION_INDEX.md, текущему коду и ADR.

﻿<!-- FRONTEND-CONSOLIDATION-BANNER -->
> [!IMPORTANT]
> **Архитектура фронтенда (решение владельца, зафиксировано).**
> - Единственный frontend проекта — `arkaim-web`: единственное направление дальнейшей разработки.
> - `arkaim-web-v2` — **удалён** из репозитория как рабочее направление.
> - Перечень потенциально восстанавливаемой из бывшего v2 функциональности: `docs/FRONTEND_RESTORE_BACKLOG.md`.
> - Дальнейшие сравнения `arkaim-web` против `arkaim-web-v2` не проводятся. Ниже могут встречаться исторические упоминания v2 (в датированных аудитах/спеках) — они относятся к удалённому направлению и НЕ означают сосуществования двух действующих фронтендов.

# FRONTEND ARCHITECTURE
## Новый frontend как клиент текущего backend (post-M10.2)

Дата: 2026-09-08
Статус: ПРОЕКТ АРХИТЕКТУРЫ (не реализован). Ожидает утверждения владельцем.
Основа: `docs/FRONTEND_FORENSIC_AUDIT.md` (фактический контракт backend), решение владельца «CURRENT BACKEND → CURRENT CONTRACTS → NEW FRONTEND».
Принцип-ограничение: M10/M10.2 и весь backend заморожены; frontend не добавляет backend-эндпоинты; frontend не дублирует business logic.

---

## Простыми словами

**1. Что было целью?**
Спроектировать новый frontend с нуля — не «починить старый», а построить клиент для сегодняшнего backend, где каждая кнопка и экран опирается на реально существующий и подтверждённый API-контракт.

**2. Что реально сделано?**
Определены: структура приложения (каркас + навигация), полный список экранов из возможностей backend (не из старых страниц), слой типизированных контрактов (генерация из OpenAPI бэкенда — вместо 414 строк ручных типов, которые разъехались с реальностью), стратегия real-time (WebSocket + SSE, которые уже есть в backend), стратегия прав (по фактической RBAC-матрице 307 маршрутов), единая модель ошибок/состояний, и план внедрения по 6 фазам с чёткими критериями готовности. Отдельно зафиксированы красные линии — чего frontend делать не имеет права.

**3. Что получилось?** — **PASS**: архитектура спроектирована полностью, пробелов, требующих решения backend-стороны, не обнаружено.

**4. Есть ли проблемы?**
Одно важное предупреждение: документ описывает замену старого frontend целиком. Пока новый не построен до фазы 5, старый остаётся в работе (не чиним, не развиваем). Это означает период сосуществования двух frontend — нужно ваше решение, когда и как его завершить (предложение в §12).

**5. Что предлагается дальше?**
Утвердить эту архитектуру → затем, как обычно: pre-implementation аудит фазы 1 → SPEC → реализация по фазам. Ничего не начато, ждём вашего решения.

---

## 1. Базовые решения

| Решение | Выбор | Обоснование |
|---|---|---|
| Стек | **Next.js 16 App Router + React 19 + TypeScript strict** | инфраструктура команды (AGENTS.md/CI), SSR-возможность для SEO-страниц, единый бандлер |
| UI-библиотека | **Ant Design 6 + light-обёртки (переиспользуем class A)** | 23 готовых обёртки без business logic — чистое переиспользование |
| State | **Zustand (только UI-state) + TanStack Query 5 (server state)** | server state = кэш контрактов, не дублируем; UI-state минимален (тема, свернутость, черновики ввода) |
| Типы контрактов | **Генерация из OpenAPI (`openapi-typescript` + `openapi-fetch` или ручные typed endpoints)** | backend — единственный источник истины; типы больше не «напоминают» API, а порождаются им; 51 pydantic-схема уже в схеме |
| Realtime | **WS `/ws` + SSE `/v1/stream` + SSE `/xray/events/stream`** (существующие контракты) | см. §7 |
| Тесты | **Vitest (unit) + Playwright (e2e) + contract-tests против живого OpenAPI** | contract-test гарантирует: типы не разошлись с backend |
| Локация кода | **`arkaim-web/` — полная замена содержимого** (новая структура §3) | legacy выбрасывается поэтапно, см. §12 |

**Ключевое отличие от legacy:** страница больше не «знает» API. Страница вызывает typed-функцию из `entities/<домен>/api`, сгенерированную/описанную из OpenAPI. Никаких строковых путей в компонентах. Никаких моков при 401.

## 2. Границы ответственности (красные линии)

Frontend НЕ имеет права:

| # | Запрет | Как обеспечивается |
|---|---|---|
| R1 | Изменять WorldModel напрямую | WorldModel-экраны только читают (`/book/world/*`, `/book/temporal/*` view); единственный путь изменения WorldModel — temporal confirm (M10.2) через серверный гейт |
| R2 | Реализовывать confirmation semantics | confirm/reject = POST к backend-эндпоинту; никакой локальной логики «считать подтверждённым»; UI отображает только серверные статусы из истории/списка |
| R3 | Реализовывать discovery/поиск знаний | поиск = вызов существующих search-endpoint'ов (`world/search`, `os/*-search`, `knowledge/search`, `community/search`); фронт не строит индексов |
| R4 | Реализовывать execution logic | генерация/сборка — только вызовы `assets/generate*`, `film/*`; статусы — только опрос контрактных status-эндпоинтов; фронт не «выполняет» и не интерпретирует pipeline |
| R5 | Создавать копию domain truth | фронт не хранит производные данные дольше сессии (нет IndexedDB-кэшей сущностей); единственный источник — запросы; кэш = TanStack Query (invalidate-able) |
| R6 | Добавлять backend endpoints для удобства UI | любое «не хватает эндпоинта» → стоп + вопрос владельцу, НЕ самовольный новый маршрут |
| R7 | Возвращать старую архитектуру (строковые пути, моки при 401, ручные типы) | enforced линтингом: запрет `api.get('/...')` в компонентах вне contract-слоя; запрет `MOCK_DATA` вне dev-flag strict-list |

Frontend ОБЯЗАН:

| # | Обязанность |
|---|---|
| O1 | Рендерить навигацию/действия по фактической RBAC-матрице (§2.4 forensic): reader/editor/admin |
| O2 | Показывать операции честно: in-memory сущности (pending-очереди) — с индикатором «до перезапуска» |
| O3 | Потреблять realtime-каналы вместо polling (кроме job-статусов — там контракт = опрос) |
| O4 | Единая модель ошибок: `{ok:false, error:{code,message}}` + direct-return фолбэк |
| O5 | Loading/Empty/Error состояния для каждого экрана (стандартные компоненты §5) |

## 3. Структура приложения

```
arkaim-web/src/
├── app/                        # Next.js App Router — только роутинг и лейауты
│   ├── (auth)/login, register  # публичные
│   ├── (main)/...              # защищённые (layout: AuthGuard)
│   └── api/health              # собственный health-роут (SSR-пинг)
├── widgets/                    # крупные композиции (панели, shell)
│   ├── app-shell/              # Sidebar + Topbar (новый page map §4)
│   ├── temporal-queue/         # очередь pending-предложений M10.2
│   ├── operations/             # job-tracker (assets/film)
│   └── moderation/             # approve/reject-панели
├── entities/                   # доменные слои (FSD): API + модель + hooks
│   ├── world/                  # /book/world/*, /book/graph/*
│   ├── temporal/               # /book/temporal/* (view + pending-updates)
│   ├── assets/                 # /book/assets/* + queue lifecycle
│   ├── film/                   # /book/film/*
│   ├── explorer/               # /book/world-explorer/*
│   ├── community/              # /book/community/*
│   ├── presence/               # /book/presence/* + /book/email/*
│   ├── reader/                 # /book/reader/*, /book/chapters, ask
│   ├── auth/                   # /auth/*, сессия, роль
│   ├── os/                     # /book/os/* (upload/ingest/search)
│   ├── evolution/              # /book/evolution/*
│   └── xray/                   # /xray/*
├── shared/
│   ├── api/                    # ★ typed contract layer (генерация из OpenAPI + envelope-флаги)
│   ├── api/contracts/*.ts      # per-endpoint: path, method, roles, envelope
│   ├── realtime/               # ws-client (class A reuse), sse hooks
│   ├── rbac/                   # can() — матрица прав из forensic §2.4, useAuth/role
│   ├── ui/                     # light-обёртки AntD (class A) + состояния
│   └── config/env.ts           # NEXT_PUBLIC_* (ports, ws-url)
└── contracts/                  # json-дампы контрактов для contract-tests
```

**Правило слоя:** `app → widgets → entities → shared`. Страница не импортирует `shared/api` напрямую (только через entities). Realtime-события инжектятся в Query-кэш (§7).

## 4. UX / Page Map (от возможностей backend)

### 4.1 Навигация (новый Information Architecture)

```
ЗАСТАВКА/ВХОД
├── /login, /register           — auth-флоу (Telegram/Google/email/invite)

КНИГА (reader)
├── /ask                        — задать вопрос (SSE-стрим, история)
├── /book                       — диалог с книгой (сессии, темы)
├── /read                       — чтение глав (chapters/text)
├── /world                      — ★ модель мира: категории→сущности→контекст
│   ├── /world/entity/[id]      — карточка: связи, формы, visual-prompt
│   ├── /world/temporal         — ★ временные цепочки (chain/nodes/context/epochs)
│   └── /world/graph            — граф знаний (neighbors/path/subgraph)
├── /library                    — геном/слои/эволюция статуса (genome, layers, evolution/status)

ПОЗНАНИЕ (reader+)
├── /explorer                   — ★ world-explorer: epochs → explore → гипотезы/возможности
│   ├── /explorer/history       — история исследований
│   └── /explorer/sources       — sources/search
├── /search                     — унифицированный поиск (knowledge/os/community/graph)

СТУДИЯ (editor)
├── /studio/assets              — ★ ассеты: список→генерация (sync/async)→job-трекер
│   └── /studio/assets/[id]     — карточка: file/thumbnail, regenerate
├── /studio/film                — ★ film-studio: проекты→сцены→кадры→assemble→output
├── /studio/upload              — os/ingest (editor-гейт)
├── /studio/story               — story-engine: constraints/generate/validate

ПРЕДЛОЖЕНИЯ (editor)
├── /proposals/temporal         — ★★ M10.2 очередь: scan → список → confirm/reject → история
├── /proposals/presence         — presence-очередь (editor list, admin approve/reject)
├── /proposals/email            — email-черновики (editor list, admin approve/send)
└── /proposals/drafts           — drafts-approve

СООБЩЕСТВО (reader)
├── /community/interpretations  — интерпретации (+like/comments)
├── /community/artifacts       — артефакты (+like/comments)
├── /community/timeline        — лента
└── /community/map             — карта (map-data)

ЛИЧНОЕ (reader)
├── /profile                   — профиль, статистика, API-ключи, подписка
├── /history                   — история вопросов/сессий

АДМИН (admin)
├── /admin                     — дашборд (stats, users, sessions, invites, api-keys)
├── /admin/moderation          — модерация community (approve/reject)
├── /admin/evolution           — ★ evolution diff/evolve/rollback/versions
├── /admin/reader-stats        — reader/stats
└── /xray                      — observability: traces, SSE-лента, diagnostics, sanitize

СИСТЕМНОЕ
├── /system                    — providers, comfyui, cache, memory, health
└── /help                      — справка (переработанная под новый IA)
```

★ — экраны, которых не было в legacy (gap §6 forensic). ★★ — главный новый экран (M10.2).

### 4.2 Ролевая видимость навигации (по матрице §2.4 forensic)

| Группа | reader | editor | admin |
|---|---|---|---|
| Книга, Познание, Сообщество, Личное | ✔ | ✔ | ✔ |
| Студия (assets/film/upload/story) | ✖ (скрыть) | ✔ | ✔ |
| Предложения temporal/presence/email/drafts | ✖ | ✔ (confirm/reject: temporal; presence: список; email: черновики) | ✔ (вкл. approve/send) |
| Админ, X-Ray, Evolution-управление | ✖ | ✖ | ✔ |

Правило: `can(ability)` из `shared/rbac` — единственная точка принятия решения; матрица зашита из forensic-дампа и покрыта contract-тестом.

### 4.3 Ключевые пользовательские сценарии (сквозные)

| Сценарий | Цепочка контрактов |
|---|---|
| **S1: Temporal-предложение** | `/proposals/temporal` → POST scan → список pending → detail → confirm (Popconfirm) → обновление: query-invalidate списка+истории → индикатор «WorldModel обновлена» (строку refresh делает backend) |
| **S2: Генерация ассета** | `/studio/assets` → POST generate-async → task_id → job-трекер (poll queue/task/{id}) → completed → карточка ассета (file/thumbnail) |
| **S3: Сборка фильма** | `/studio/film` → проект → сцены → кадры → POST assemble → poll assemble/status → completed → GET output |
| **S4: Вопрос книге** | `/ask` → POST /v1/stream (SSE) → стрим ответа → reader-история (reader/reading-event не требуется — история вопросов пишется backend'ом) |
| **S5: Исследование мира** | `/explorer` → epochs → POST explore → результат (гипотезы/возможности) → generate-from-branch → история |
| **S6: Модерация** | `/admin/moderation` → community pending → approve/reject (admin-гейт) → invalidate |
| **S7: Вход** | /login → Telegram/Google/email → cookie `arkaim_session` → GET /auth/me → роль → рендер навигации |

## 5. Component boundaries

| Уровень | Что живёт | Примеры |
|---|---|---|
| shared/ui | «глухие» примитивы | light-обёртки AntD, `StateView` (loading/empty/error), `RoleGate`, `ConfirmButton` (Popconfirm+mutation+invalidate) |
| entities/<домен> | typed-API + хуки + чистые отображалки | `usePendingUpdates()`, `useConfirmFinding()`, `TemporalFindingCard`, `AssetCard`, `JobBadge` |
| widgets | композиции поверх entities | `TemporalQueueWidget` (список+скан+подтверждения), `JobTrackerWidget` (poll+прогресс), `ModerationPanel` |
| app | только layout + composition | страницы без логики |

**Мутации — стандартная цепочка:** `mutation → onSuccess: invalidateQueries(domain) → WS/SSE-подстраховка`. Никаких локальных оптимистичных обновлений очередей подтверждения (риск рассинхрона с in-memory бэкендом).

## 6. State / Data flow

```
UI event
  → entities/<x>/api.<typed call>      (единственная дверь к сети)
    → openapi-fetch/typed fetch        (+ envelope unwrap per contract)
      → TanStack Query cache            (ключ = ['domain', 'resource', params])
        → invalidate / setQueryData (по WS-событию)
          → компонент перерисовывается
```

- **Server state:** только TanStack Query. staleTime: genome/world/layers — 5 мин; pending-очереди — 0 (всегда свежие); reader-history — 1 мин.
- **UI state (Zustand):** тема, collapsed-sidebar, черновики форм, язык. Ничего доменного.
- **Формы:** react-hook-form + zod-схемы, порождённые из тех же контрактов (request-модели).
- **Ошибка сети/сессии:** 401 → редирект /login (без моков!); 403 → «недостаточно прав» (не crash).

## 7. Realtime strategy

| Канал | Потребление |
|---|---|
| WS `/ws` | `shared/realtime/ws-client` (переиспольз. legacy ws.ts, class A): события `pulse_beat`, `new_suggestion`, `new_question`, `crowdfunding_milestone`, `service_status` → toast + invalidate соответствующих query (`proposals/presence`) |
| SSE `/v1/stream` | хук `useChatStream` (переиспольз. парсер legacy): инкрементальный ответ книги |
| SSE `/xray/events/stream` | admin-дашборд xray: живые трейсы (типизированные события) |

Job-статусы (assets queue, film assemble) — **только polling по контракту** (интервал 2s, до терминального статуса, с backoff); WS-канала для них backend не предоставляет — выдумывать нельзя (R4/R6).

## 8. API layer (ядро архитектуры)

```
shared/api/
├── generated/schema.d.ts        # openapi-typescript от живого /openapi.json backend
├── client.ts                    # openapi-fetch: auth (cookie+bearer), retry, ApiError
├── envelope.ts                  # unwrap {ok,data} vs direct-return (per-endpoint map)
└── index.ts                     # barrel: типизированные вызовы per-domain
```

- **Генерация:** `npm run contracts` → скрипт дергает `http://localhost:8642/openapi.json` → `schema.d.ts` + diff-check в CI (контракт изменился → тест падает до деплоя).
- **Envelope-карта** (из forensic §2.2): для каждого endpoint'а флаг `enveloped` — единое место правды; исправляет legacy-хаос.
- **Аутентификация:** cookie-first (`credentials: 'same-origin'`), Bearer — если задан NEXT_PUBLIC_TOKEN_STORAGE (для API-key тестера /api).
- **Ошибки:** `ApiError { status, code, message, details }`; 401 → событие session-expired; всё остальное — наверх в UI-стейт.

## 9. RBAC strategy

- `shared/rbac/matrix.ts` — компилируемая матрица: `{ endpoint, roles }` — порождается тем же `npm run contracts` из forensic-обхода (307 маршрутов) + ручные пометки дефектов D1–D6 (не вызывать `/book/book/*`, research-apply — заглушка, os/clear — admin).
- `can(user, endpoint)` — синхронная проверка; `RoleGate`/`can()` — единственные точки развилок в UI.
- Роль берём из `/auth/me` (single source), кэш в session-context; при 403 — экран «нет доступа», не crash.
- Роли editor/admin не видят друг друга отличий, кроме матрицы (не «admin = super-editor» вручную, а факт матрицы).

## 10. Error/state model (единая)

| Состояние | Стандарт |
|---|---|
| Loading | `StateView loading` (skeleton по типу контента) |
| Empty | `StateView empty` (+ кнопка действия, где уместно: «сканировать книгу» для пустой очереди) |
| Error | `StateView error` + `ApiError.message` + код (+ retry) |
| Partial (job failed) | `JobBadge failed` + `error` из контракта задачи |
| Session expired | глобальный toast + redirect /login |
| Offline (WS/SSE недоступны) | индикатор связи в Topbar; UI деградирует к polling-доступным данным |

## 11. Implementation phases

| Фаза | Содержимое | DoD |
|---|---|---|
| **F1 Foundation** | app-shell (новый IA), auth-флоу (`/login`,`/register`,`/auth/me`), rbac-matrix+can(), typed API-слой (`npm run contracts`), StateView, ErrorBoundary, CI contract-test | вход всеми 3 способами; навигация по роли; CI зелёный; генерация схемы из живого backend работает |
| **F2 Книга/Мир** | /ask (SSE), /book, /read, /world (+entity, temporal-view, graph), /library | сценарий S4+S5-read; все view-контракты без 404; RBAC-фильтрация |
| **F3 Студия/Операции** | /studio/assets (+job-tracker), /studio/film (+assemble), /studio/upload, /studio/story | S2, S3; job-статусы честны (queued→completed/failed); ни одной mock-мутации |
| **F4 Предложения/Очереди** | /proposals/temporal (**M10.2 UI — главный экран**), /proposals/presence, /proposals/email, /proposals/drafts, /community, /admin/moderation | S1+S6; confirm/reject только через сервер; история после рестарта честно пустая |
| **F5 Realtime/Админ** | WS-интеграция (toast+invalidate), /xray (SSE-лента), /admin (пользователи/инвайты/ключи), /system, /profile, /history | live-события приходят; admin-панели на реальных контрактах |
| **F6 Polish/Regression** | /help, доступность, мобильная адаптация, e2e-прогон Playwright, удаление legacy (см. §12), финальный аудит | 100% page-map покрыто; e2e зелёные; legacy удалено; тест 432 backend не тронут |

Порядок обоснован зависимостями: контракты/права → читательные экраны → операционные → очереди подтверждения (M10.2 — сердце) → realtime/админ → полировка. Фазы принимаются владельцем по отдельности (workflow M-этапов).

## 12. Судьба legacy (переходный план)

1. **Не чинить и не развивать** legacy с момента утверждения этой архитектуры (владелец уже решил: legacy — не источник истины).
2. До завершения F4 новый frontend живёт на **отдельном app-root** (`arkaim-web/src` заменяется только на F6; до этого новый код в `arkaim-web/src-v2/` либо legacy переносится в `legacy/` — решение за владельцем на F1-аудите).
3. Class A (ws.ts, useStreamingChat, light-обёртки, admin-панели, RoleGuard и др. из forensic §5) — **переносятся**, а не переписываются.
4. Class C (моки при 401, types/index.ts ручные, /notifications, /story world-engine/model, старый sidebar-IA) — **удаляются в F6** (git-история сохранит).
5. Class D (map-page визуализация, playwright-конфиг) — решения в F1/F2.

## 13. DoD всего этапа «Новый frontend» (сводное)

1. Все экраны page-map §4 работают на реальном backend без моков (моки только в dev-flag strict-list, не на 401).
2. Ноль строковых API-путей вне `shared/api` (линт-правило).
3. RBAC-матрица = источник навигации; contract-тест связывает матрицу с живым OpenAPI.
4. Realtime: WS+SSE потребляются; job-статусы — по контрактам опроса.
5. Backend не изменён (git-доказательство на каждой фазе; тесты backend не тронуты).
6. Красные линии R1–R7 соблюдены (проверено код-ревью по чеклисту).
7. Playwright e2e: S1–S7 сценариев зелёные.
8. Legacy удалён, сборка чистая, `npm run build` без ошибок.
9. Документация (README arkaim-web, docs/FRONTEND_*.md) отражает финальное состояние.

---

*Архитектура спроектирована. Реализация не начата. Ожидается решение владельца по фазам F1+ и переходному плану §12.*
