# F1 PRE-IMPLEMENTATION AUDIT
## Foundation нового frontend — проверка готовности до изменения кода

Дата: 2026-09-08
Статус: READ-ONLY АУДИТ. Ничего не реализовано, ни один файл не изменён.
Основание: решение владельца — «F1 ACCEPTED FOR PRE-IMPLEMENTATION», обязательный аудит до SPEC.
Основа: `docs/FRONTEND_FORENSIC_AUDIT.md` (ACCEPTED), `docs/FRONTEND_ARCHITECTURE.md` (ACCEPTED).
Метод: прямое чтение конфигов/кода workspace; живой импорт backend-приложения; проверка CI-конфига.

---

## Простыми словами

**1. Что было целью?**
Перед стартом F1 убедиться: правильно ли мы понимаем техническую базу (сборка, зависимости, тесты), откуда брать контракт API, как работает вход/роли, и что из технической инфраструктуры legacy можно оставить, не перенося его архитектуру.

**2. Что реально сделано?**
Проверены: точные версии всех инструментов (Next 16.2.10, React 19.2.4, TypeScript 5.9.3, Node 24, AntD 6.5, TanStack Query 5.101); CI-конвейер (5 шагов, включая build); конфигурации тестов (vitest jsdom, playwright); существующие 5 auth-роутов legacy; контракт входа backend (Telegram/Google/email/dev + cookie `arkaim_session`); RBAC-матрица (307 маршрутов — уже в дампе forensic); WS/SSE-контракты; жизнеспособность backend в CI-подобном окружении (приложение поднимается, OpenAPI отдаётся — 289 путей).

**3. Что получилось?** — **PASS**: все предпосылки F1 подтверждены, изменений backend не требуется.

**4. Есть ли проблемы?**
Ни одного блокера. Три уточнения, учтённые в SPEC:
- Dev-вход (`/auth/dev/generate-token`) — публичный endpoint без защиты: он уже существует в backend, но новый frontend будет вызывать его **только при явно включённом dev-флаге** (в legacy legacy AuthProvider молча логинил dev-пользователя без cookie — это устраняем);
- `/auth/me` при отсутствии cookie отдаёт 401 с `detail` (не `error.code`) — error-модель F1 обязана покрывать оба формата (уже зафиксировано в forensic §2.2);
- Response-schemas большинства auth-endpoint'ов пустые в OpenAPI (`{}`) — прямого JSON-типа в generated-схеме не будет, эти 6-8 ответов описываем вручную в typed contracts (перечень в SPEC).

**5. Что предлагается дальше?**
Утвердить `docs/F1_SPEC.md` → затем implementation plan → реализация F1 (после вашего отдельного ACCEPTED на SPEC).

---

## 1. Техническая база (фактическая)

| Компонент | Версия/значение | Источник |
|---|---|---|
| Framework | **Next.js 16.2.10** (App Router, turbo dev) | package-lock (locked) |
| React | **19.2.4** | package-lock |
| TypeScript | **5.9.3** (strict, bundler resolution, `@/*` alias) | tsconfig + lock |
| Node.js (локально) | **24.16.0**, npm 11.5.2 | `node --version` |
| UI | AntD 6.5.0 + @ant-design/icons 6.3.2 | lock |
| Server state | @tanstack/react-query 5.101.2 | lock |
| Формы/валидация | react-hook-form 7.81 + @hookform/resolvers 5.4 + zod 4.4.3 | lock |
| Стили | Tailwind 4 (@tailwindcss/postcss) + postcss | postcss.config.mjs |
| Unit-тесты | vitest 4.1.10 + @vitejs/plugin-react 6.0.3 + jsdom 29 + testing-library 16 | vitest.config.ts |
| E2E | @playwright/test 1.61.1 (config: dev-server :3000) | playwright.config.ts |
| Линт | eslint 9 + eslint-config-next (web-vitals + TS) | eslint.config.mjs |
| Сборка | `next build` (Node 24 в CI) | package.json scripts |

**Вывод:** стек полностью соответствует архитектуре (FRONTEND_ARCHITECTURE §1). Никаких новых framework-решений не требуется.

## 2. Frontend workspace structure

```
arkaim-web/
├── src/app/                 # 33 legacy-страницы (НЕ переносим) + api/* route-handlers
│   └── api/auth/*, api/telegram/callback   # 5 серверных роутов (proxy legacy)
├── src/widgets/, src/shared/  # legacy-код (судьба по forensic §5)
├── tests/unit/              # 9 legacy unit-тестов
├── tests/e2e/               # playwright
├── .env.local               # только NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
├── next.config.ts           # rewrites: /auth, /xray, /book, /v1, /api→backend, /analytics
└── vitest.config.ts, playwright.config.ts, eslint.config.mjs, tsconfig.json
```

**Для F1 важно:** rewrites в next.config.ts корректны для всех контрактных путей (проверено forensic §2.1) — конфиг прокси переносится как есть. Route-handlers `src/app/api/auth/*` — **лишнее проксирующее звено** (frontend → Next handler → backend, вместо frontend → rewrite → backend): новый frontend ходит напрямую через rewrites, handlers не переносим (но не удаляем — legacy живёт до F6).

## 3. Точка получения OpenAPI + способ генерации

| Вопрос | Факт |
|---|---|
| Источник контракта | `GET http://localhost:8642/openapi.json` (FastAPI, живое приложение) |
| Доступность в CI-подобном env | ✅ проверено: `SESSION_SECRET` + `AUTH_DB_PATH=":memory:"` → app boots, 289 путей отдаются (прямой импорт `core.main:app`) |
| Схем в OpenAPI | 51 (pydantic) — покрывают domain-модели, но НЕ все response-типы (многие роуты отдают сырые dict без response_model) |
| Способ генерации typed API | **openapi-typescript** (`schema.d.ts` из openapi.json) + **обёртка per-endpoint с envelope-флагом** (для direct-return роутов без response_model — ручные типы в `contracts/`, см. SPEC §6) |
| Команда | `npm run contracts` — скрипт: (а) дергает openapi.json backend, (б) генерирует `src/shared/api/generated/schema.d.ts`, (в) diff-check против закоммиченной версии (CI-гейт) |

**Особенность, подтверждённая аудитом:** auth-ответы (`/auth/me`, register, telegram/login) не имеют response_model → в OpenAPI схемы пустые → эти ответы типизируются вручную в `shared/api/contracts/auth.ts` (источник истины — фактический JSON, зафиксирован в SPEC §5). Это не backend-изменение — это фронтовая typed-декларация фактического поведения.

## 4. Auth contract (фактический)

| Механизм | Контракт | Для F1 |
|---|---|---|
| Вход Telegram | `/auth/login` (HTML-виджет) → POST `/auth/telegram/callback` \| `/auth/telegram/login` → `{ok, user}` + cookie `arkaim_session` (httponly, Lax, 12ч) | F1: страница /login, вызов напрямую через rewrite |
| Email-регистрация | POST `/auth/register` `{username, display_name?}` → `{ok, user{role:"reader"}}` + cookie | F1: страница /register |
| Google | `/auth/google` → redirect → callback (клиент НЕ настроен: `GOOGLE_CLIENT_ID=""` — скрываем кнопку) | F1: скрыть |
| Выход | POST/GET `/auth/logout` → delete_cookie | F1: кнопка в Topbar |
| Сессия | GET `/auth/me` → `{user:{id, role, username, display_name, provider}}`; 401 без cookie (формат `detail`!) | F1: AuthProvider |
| Dev-вход | POST `/auth/dev/generate-token` `{telegram_user_id, username, display_name, role?}` → `{token}`; затем `/auth/telegram/login` `{token}` → cookie | F1: только при `NEXT_PUBLIC_DEV_AUTH=1`, НЕ автоматический |
| Приглашения | GET/POST `/auth/invite/{token}` | не F1 (входит в admin-флоу F5) |

**RBAC-матрица:** 307 маршрутов / 8 групп — зафиксирована в `runtime/forensic_rbac2.txt` (evidence), порождается в `shared/rbac/matrix.ts` тем же contracts-скриптом + ручные пометки дефектов D1–D6.

## 5. SSE/WS contracts (для realtime-foundation F1)

| Канал | Контракт | F1-обязательство |
|---|---|---|
| WS `/ws?token=` | `{event, data}`; события: pulse_beat, new_suggestion, service_status, new_question, your_question_answered (user), chat_response (user), crowdfunding_milestone; cookie-токен как query-param | F1: ws-client (reconnect+backoff, перенос ws.ts class A) + WsProvider — БЕЗ доменных обработчиков |
| SSE `/v1/stream` | POST, `text/event-stream`, `data: {text}` | F1: sse-хук-примитив (не чат-UI) |
| SSE `/xray/events/stream` | typed events: trace_*, orphan_change, stats_changed, heartbeat (1s) | F1: sse-client-примитив |

F1 доставляет только **инфраструктуру** (подключение/переподключение/роутинг событий в шину); доменные подписки (уведомления, трейсы) — F4/F5.

## 6. CI infrastructure

Текущий пайплайн `.github/workflows/ci.yml` (backend ruff+pytest ×2 python; frontend: `npm ci` → eslint → `tsc --noEmit` → `vitest run` → `next build`; docker после main).

**Для F1 добавляется** (в frontend-job, без изменения backend-job):
1. шаг «Generate & verify contracts»: поднять backend (python) ИЛИ использовать precommitted `openapi.json`-слепок → `npm run contracts` → `git diff --exit-code` (изменился — падение);
2. новые foundation-тесты в `vitest run` (已有的 шаг).

Backend-CI не трогаем. Backend-тесты не трогаем (red-line F1).

## 7. Что оставляем из технической инфраструктуры legacy

| Артефакт | Судьба | Причина |
|---|---|---|
| `next.config.ts` rewrites | **оставить** (перенести значения) | контрактная необходимость, не архитектура |
| `tsconfig.json` | **оставить** (strict + alias) | соответствует архитектуре |
| `vitest.config.ts` / `playwright.config.ts` | **оставить** | инфраструктура тестов |
| `eslint.config.mjs` | **оставить + расширить** (правила: запрет строковых API-путей вне contract-слоя; запрет моков при 401) | enforcement красных линий |
| `package.json` deps | **оставить** + добавить openapi-typescript (см. SPEC §6) | версии locked, конфликтов нет |
| `.env.local` | **оставить** + `NEXT_PUBLIC_DEV_AUTH`, `NEXT_PUBLIC_API_URL` | конфиг F1 |
| `src/app/api/*` route-handlers | **НЕ переносить** (но не удалять) | лишнее прокси-звено; прямые rewrites достаточны |
| legacy `src/**` (33 страницы, widgets, shared) | **не трогать** в F1 | работает до F6; новый код в новом дереве (SPEC §4) |
| `ws.ts`, light-обёртки AntD, RoleGuard и др. (class A forensic) | **перенести копированием в новое дерево** в F1-объёме (ws-client, StateView-набор) | без legacy-архитектуры, только изолированные модули |

## 8. Gaps / риски для F1

| # | Риск | Вердикт |
|---|---|---|
| G1 | Auth-ответы без response_model → не типизируются генерацией | не блокер: 6 ручных typed-контрактов (SPEC §5) |
| G2 | Dev-токен endpoint публичен | не блокер F1: gating через `NEXT_PUBLIC_DEV_AUTH` на фронте (backend не меняем) |
| G3 | Backend в CI недоступен для contracts-скрипта | решение: contracts-скрипт работает от precommitted слепка `openapi.json`; живая сверка — опциональный шаг при наличии services | 
| G4 | Два формата ошибок (enveloped / detail) | покрыто error-моделью SPEC §7 |
| G5 | Необходимость менять backend/M10 | **НЕ обнаружена** — F1 полностью фронтовая |

## 9. Вердикт

**F1 GO.** Все технические предпосылки подтверждены фактическим кодом/конфигами. Изменений backend не требуется. Красные линии F1 соблюдаемы. Переход к SPEC.
