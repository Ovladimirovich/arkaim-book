# F1 SPEC — Foundation нового frontend
## Спецификация этапа F1 (для утверждения владельцем)

Дата: 2026-09-08
Статус: SPEC. Реализация НЕ начата — ожидается отдельный ACCEPTED владельца.
Основа: FRONTEND_FORENSIC_AUDIT (ACCEPTED), FRONTEND_ARCHITECTURE (ACCEPTED), F1_PRE_IMPLEMENTATION_AUDIT (PASS).
Source of truth: текущий backend/API/доменные контракты. Legacy — только исторический reference.

---

## Простыми словами

**1. Что было целью?**
Точно описать, что входит в первый строительный блок нового frontend (фундамент: каркас, вход, права, API-слой, обработка ошибок, тесты) — и что в него НЕ входит.

**2. Что реально сделано?**
Зафиксированы: границы (scope/non-goals), архитектурные красные линии, точные контракты API/входа/ролей/realtime, модель ошибок и состояний, тестовая и CI-стратегия, критерии готовности. Ни одна domain-страница не описана как реализуемая в F1 — фундамент категорически без доменного контента.

**3. Что получилось?** — **PASS**: SPEC полон, внутренние противоречия отсутствуют.

**4. Есть ли проблемы?** Нет. Одно предупреждение: F1 не даёт видимой пользователю «ценности» кроме экранов входа — это нормальный фундаментный этап; все доменные экраны идут в F2+.

**5. Что предлагается дальше?**
Утвердить SPEC → implementation plan → реализация.

---

## 1. Scope

F1 реализует **только**:

| # | Компонент | Содержание |
|---|---|---|
| 1 | Application shell | новый app-root (`/` → redirect по роли), Topbar+Sidebar по новому IA (пункты-заглушки F2+, отключённые), тема (light/dark), лейауты |
| 2 | Routing/navigation | route-groups: `(auth)` публичные, `(main)` под AuthGuard; foundation-маршруты: `/login`, `/register`, `/` (дашборд-заглушка), `/no-access` (403), `not-found` |
| 3 | API client layer | `shared/api`: fetch-обёртка (credentials, Bearer-override, retry 1, ApiError), envelope-unwrap per-endpoint |
| 4 | Typed contracts | `npm run contracts`: слепок `openapi.json` (committed) → `openapi-typescript` → `schema.d.ts`; + `contracts/*.ts` — per-domain typed-функции (F1: auth + health); envelope-флаги; ручные типы для 6 auth-ответов без response_model |
| 5 | Authentication | страницы /login (Telegram-виджет, email, dev по флагу) и /register; AuthProvider: `/auth/me` → user+role; logout; 401 → redirect /login; **никаких моков при 401** |
| 6 | RBAC-модель | `shared/rbac`: матрица (307 маршрутов → {path, roles[]}), `can(user, action)`; RoleGate-компонент; ролевая навигация sidebar; пометки дефектов D1–D6 |
| 7 | API errors | единый ApiError {status, code, message}; разбор обоих форматов backend (enveloped/direct+detail); глобальные toast; 401/403-обработка |
| 8 | States foundation | `StateView` (loading-skeleton / empty / error+retry) + покрытие всех F1-экранов |
| 9 | Realtime infra | ws-client (перенос ws.ts, reconnect+backoff) + WsProvider с шиной событий; SSE-примитив (parse typed events); **без доменных подписок** |
| 10 | CI contract-test | шаг «contracts»: регенерация schema.d.ts от committed слепка → git diff --exit-code; новые unit-тесты в vitest-шаге |
| 11 | Tests | vitest: contracts (генерация воспроизводима), rbac-матрица (все 307 маршрутов типизированы), auth-flow (моктранспорт, не мок-данные!), ApiError-разбор, StateView, ws-client (fake-timers); playwright smoke: /login → dev-вход → / виден по роли |

## 2. Non-goals (ЖЁСТКО)

Не реализуется в F1: domain pages; temporal queue; discovery UI; assets/workflows UI; job tracker; evolution/presence/email UI; перенос legacy pages; исправление backend-дефектов (D1–D6 остаются пометками); изменения M10/M10.2; новые backend endpoints; persistence; business logic в frontend; удаление legacy frontend.

Legacy-код не переносится, кроме: ws.ts (→ realtime), light-обёрток AntD (→ shared/ui, только те, что нужны shell), RoleGuard-паттерна (переписан на новую rbac). Никаких страниц/виджетов из legacy.

## 3. Архитектурные границы (напоминание + enforcement)

| Линия | Как enforcement в F1 |
|---|---|
| Backend — source of truth | все пути/типы из `schema.d.ts` или typed-контрактов; линт-правило: запрет fetch/строковых путей вне `shared/api` |
| Никаких моков при 401 | dev-моки = только явные `NEXT_PUBLIC_MOCK=strict-list`; 401 всегда redirect |
| Никакой business logic | F1 не содержит доменных экранов — автоматически соблюдено |
| Не трогаем legacy | новый код в новом дереве; legacy-файлы не изменяются |
| Не трогаем backend | git-diff пуст для `runtime/`, `core/` (кроме committed evidence-дампов, уже существующих) |

## 4. Структура кода F1 (новое дерево)

```
arkaim-web/src/                     # legacy живёт нетронуто до F6
├── app/                            # ЗАМЕЩАЕТСЯ постепенно? НЕТ:
│   (см. ниже — F1 использует ОТДЕЛЬНЫЙ root)
```

**Решение по colocation (из аудита §7):** новый код в `arkaim-web/src2/` — отдельное дерево, собираемое Next-ом параллельно (механика: `app/` в src2 монтируется экспериментальным способом ИЛИ проект-клон в `arkaim-web-v2/`).

**Уточнение для implementation plan:** владельцу предлагается вариант **A (recommended): `arkaim-web-v2/`** — чистый соседний проект (собственный package.json на тех же locked-версиях, tsconfig/vitest/playwright переносятся, rewrites переносятся; порт 3001 в dev), потому что: (а) zero-риск для работающего legacy :3000; (б) чистая граница «новый frontend»; (в) CI-фронтенд-джоба переключается на v2 поэтапно (F1: оба проекта собираются; F6: legacy-джоба удаляется). Вариант B (src2 в том же проекте) сложнее из-за App Router-конфликтов и отклонён.

## 5. API Contract (F1-объём)

F1 использует только:

| Endpoint | Метод | Тип ответа | Envelope |
|---|---|---|---|
| `/auth/me` | GET | `{user: {id, role, username?, display_name?, provider}}` (ручной тип: response_model отсутствует) | direct |
| `/auth/register` | POST | `{ok, user{role:"reader",...}}` + Set-Cookie | direct |
| `/auth/telegram/login` | POST | `{ok, user{...}}` + Set-Cookie | direct |
| `/auth/telegram/callback` | POST | `{ok, user{...}}` + Set-Cookie | direct |
| `/auth/dev/generate-token` | POST | `{token, login_url}` — **только при NEXT_PUBLIC_DEV_AUTH=1** | direct |
| `/auth/logout` | POST | delete-cookie | direct |
| `/health` | GET | `{status: ok...}` (system-check экрана) | direct |
| `/openapi.json` | GET | (источник контрактов; слепок committed) | — |

Ошибки: `{"detail": "..."}` (HTTPException) ИЛИ `{"ok": false, "error": {code, message}}` (глобальный handler) — оба парсятся в ApiError.

**RBAC-матрица** (порождается contracts-скриптом из forensic-обхода; committed): 307 записей {path, methods, roles}; ручные пометки: D1 (не вызывать `/book/book/*`), D2 (research-apply — заглушка), D3 (os/clear — admin), D4 (presence stats — admin), D6 (рендер строго по матрице).

## 6. Typed contracts механика

```
arkaim-web-v2/
├── contracts/openapi.json          # слепок (committed, обновляется npm run contracts:fetch при живом backend)
├── scripts/contracts.mjs           # 1) fetch openapi.json (при доступности) 2) openapi-typescript → src/shared/api/generated/schema.d.ts 3) rbac-matrix.json → src/shared/rbac/generated/matrix.ts 4) verification: сверка с committed
└── src/shared/api/
    ├── generated/schema.d.ts       # НЕ правится руками
    ├── client.ts                   # fetch-обёртка: credentials same-origin; Authorization-override для API-key режима; 1 retry на 5xx; ApiError
    ├── envelope.ts                 # unwrap: enveloped|direct — per-endpoint карта
    └── contracts/auth.ts           # typed-функции: getMe(), register(), telegramLogin(), devToken(), logout() — единственная точка вызова auth
```

Новые deps: `openapi-typescript` (^7), `openapi-fetch` (^1) — только devDep/dep соответственно, без конфликтов с locked-стеком (аудит §1).

## 7. Error model

```
ApiError { status: number; code: string; message: string; details?: unknown }
```
- Парсинг: если тело `{error:{code,message}}` → code/message; если `{detail}` → code=HTTP_{status}, message=detail; если иной → code=UNKNOWN.
- 401 → событие `session-expired` (AuthProvider redirect /login). 403 → `/no-access` для страниц; toast для действий.
- Сеть недоступна → ApiError(code=NETWORK) + StateView error с retry.

## 8. Auth/RBAC runtime

- `useAuth()`: {user, loading, login, logout} — на `/auth/me`; роль из ответа; loading → fullscreen-skeleton.
- `can(user, endpointAction)`: по матрице; sidebar/пункты фильтруются; RoleGate для страниц.
- Dev-вход: кнопка на /login видна только при `NEXT_PUBLIC_DEV_AUTH=1`; вызывает dev/generate-token → telegram/login; НИКОГДА не выполняется автоматически (в отличие от legacy).
- Роли: reader (по умолчанию с регистрации), editor, admin — развилки UI только через `can()`.

## 9. Realtime (инфраструктура)

- WsProvider: connect `/ws` (cookie-token), reconnect exponential backoff+jitter (перенос из ws.ts), шина `subscribe(event, cb)`; F1 использует её только для индикатора соединения в Topbar (online/offline badge).
- SSE-примитив `createSseClient(url, onEvent)`: типизированный парсер `event:`/`data:` строк; в F1 покрыт тестами, доменных потребителей нет.

## 10. Testing

| Слой | Инструмент | Что проверяется |
|---|---|---|
| Contracts | vitest | schema.d.ts генерируется; matrix.ts содержит все 307 путей; envelope-карта согласована со schema |
| Auth | vitest (mock transport: перехват fetch, НЕ мок-данные) | login/register/me/logout флоу; 401→redirect; dev-вход скрыт без флага |
| RBAC | vitest | can() для всех ролей × ключевые endpoints; D1–D6 пометки |
| Errors | vitest | оба формата ошибок → ApiError |
| UI states | vitest+testing-library | StateView ветки; RoleGate |
| WS | vitest (fake ws) | connect/reconnect/backoff; badge online/offline |
| Smoke e2e | playwright | dev-вход → / загружается; 403-редирект |

**Правило:** юнит-тесты мокают ТРАНСПОРТ (fetch/ws), но ответы соответствуют реальным контрактам (из слепка). Никаких MOCK_DATA-страниц.

## 11. CI

Frontend-job (v2) добавляет: `npm run contracts:verify` (регенерация от committed слепка + git diff --exit-code) ПЕРЕД vitest. Backend-job не изменяется. Legacy-job продолжает собираться (legacy не трогаем). F6 (не F1) уберёт legacy-job.

## 12. DoD F1

1. `arkaim-web-v2/` собирается (`npm run build`) чисто; lint/tsc/vitest зелёные.
2. `/login` и `/register` работают на реальном backend (не на моках): Telegram-флоу (если бот задан), email-регистрация, dev-вход (при флаге).
3. После входа `/` рендерит shell: Topbar (пользователь, роль, online-badge, logout), Sidebar (пункты F2+ видимы по роли, ведут на «coming soon»-заглушки F1), контент-заглушка.
4. `/auth/me` — единственный источник роли; навигация фильтруется `can()`.
5. 401 → /login; 403 → /no-access; обе ошибки отображаются единым ApiError-форматом.
6. `npm run contracts` воспроизводим: слепок ↔ schema.d.ts ↔ matrix.ts без ручных правок; CI-шаг contracts зелёный.
7. WS-клиент подключается к `/ws`, badge отражает соединение, reconnect работает (тест).
8. Ни один legacy-файл не изменён (git-diff); ни один backend-файл не изменён (git-diff).
9. Красные линии §2 соблюдены (ревью по чеклисту).
10. Регрессия backend 432/432 не тронута (прогон не обязателен — backend не менялся; git-доказательство достаточно).

---

## Приложение: открытые вопросы для владельца (решаются при утверждении)

| Вопрос | Рекомендация |
|---|---|
| Вариант колокации: отдельный `arkaim-web-v2/` (A) vs подпапка src2 (B) | **A** — изолированность, ноль риска для legacy, чистая F6-замена |
| Dev-вход: оставить доступным по флагу? | да, `NEXT_PUBLIC_DEV_AUTH=1` только в dev-сборке |
| Порт dev-сервера v2 | 3001 (параллельно с legacy :3000) |
