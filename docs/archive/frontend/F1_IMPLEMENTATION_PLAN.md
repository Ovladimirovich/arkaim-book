# F1 IMPLEMENTATION PLAN
## План реализации Foundation (исполняется ПОСЛЕ ACCEPTED на F1_SPEC)

Дата: 2026-09-08
Статус: ПЛАН. Реализация не начата — ждёт ACCEPTED владельца на F1_SPEC.
Основа: F1_SPEC (scope/non-goals/DoD), F1_PRE_IMPLEMENTATION_AUDIT (PASS).
Общий контекст: git-workflow владельца — каждый шаг сопровождается проверяемыми артефактами.

---

## Простыми словами

**1. Что было целью?**
Разбить F1 на конкретные строительные шаги, которые можно выполнять и проверять по очереди, без риска для работающего старого frontend и backend.

**2. Что реально сделано?**
План из 8 шагов: подготовка нового проекта → контракты → API-клиент → права → вход → каркас приложения → realtime-инфраструктура → тесты/CI. Каждый шаг имеет свой «выход» (что должно работать после него) и проверку. Явно отмечено, что мы НЕ делаем (всё из non-goals SPEC).

**3. Что получилось?** — **PASS**: план покрывает весь DoD F1, шаги не пересекаются с красными линиями.

**4. Есть ли проблемы?** Нет. Риски сведены к двум контролируемым: (а) параллельная сборка двух frontend в CI — решается отдельной job-директорией; (б) воспроизводимость контрактов — решается committed-слепком.

**5. Что предлагается дальше?**
После ACCEPTED на SPEC — выполнить план (шаги 0–7), с отчётом по реализации и post-audit, как в M-этапах.

---

## Шаги (последовательные; шаг 3 параллелен 4)

### Шаг 0 — Каркас проекта `arkaim-web-v2/` (вариант A из SPEC)

**Действия:**
1. `arkaim-web-v2/package.json` — deps: те же locked-версии (next 16.2.10, react 19.2.4, antd 6.5.0, @tanstack/react-query 5.101.2, zod 4.4.3, react-hook-form) + `openapi-typescript` (dev), `openapi-fetch` (dep).
2. Конфиги: tsconfig (strict, `@/*`), next.config.ts (rewrites скопированы; порт 3001), eslint (+ правила: no-string-fetch-paths вне shared/api, no-mock-on-401), vitest, playwright.
3. `.env.local`: `NEXT_PUBLIC_DEV_AUTH=1`, `NEXT_PUBLIC_API_URL=http://localhost:8642`.
4. CI: frontend-job-v2 (npm ci → contracts:verify → lint → tsc → vitest → build); legacy-job не трогаем.

**Выход:** пустой Next-проект собирается на :3001, CI-джоба зелёная.
**Проверка:** `npm run build` в arkaim-web-v2; CI-статус.

### Шаг 1 — Слепок контрактов и генерация

1. `contracts/openapi.json` — снятие с живого backend (скрипт `scripts/fetch-contract.mjs`; backend уже поднимается в CI-env — проверено аудитом).
2. `scripts/contracts.mjs`: openapi-typescript → `src/shared/api/generated/schema.d.ts`; RBAC-обход (портируется forensic-метод `_IncludedRouter`-walk на node — ПОЧТИ ГОТОВО: forensic-скрипт уже отработал, переносится логика) → `src/shared/rbac/generated/matrix.ts`.
3. `npm run contracts` (fetch+generate+verify), `contracts:verify` (только verify от committed).

**Выход:** generated/schema.d.ts (51 схема, 289 путей) + rbac/matrix.ts (307 записей) — committed.
**Проверка:** повторный запуск → git diff пуст; unit-тест: matrix содержит `/book/temporal/pending-updates` c roles=[reader,editor,admin].

### Шаг 2 — API client + error model

1. `shared/api/client.ts`: fetch-обёртка (credentials, Authorization-override, retry-1 на 5xx, таймаут), выбрасывает ApiError.
2. `shared/api/envelope.ts`: парсинг обоих форматов (`{ok,data}` / direct+`{detail}`) — per-endpoint карта (F1: auth-группа = direct).
3. `shared/api/contracts/auth.ts`: getMe, register, telegramLogin, telegramCallback, devToken, logout — typed, из ручных типов SPEC §5 + schema.d.ts для остального.
4. ApiError-тесты (оба формата, network).

**Выход:** `import { getMe } from '@/shared/api/contracts/auth'` работает против живого backend.
**Проверка:** vitest: парсинг 401-detail и 409-enveloped → единый ApiError.

### Шаг 3 — Auth runtime (параллелен 4)

1. `entities/auth/`: AuthProvider (useAuth: user/role/loading/login/logout; `/auth/me`; 401-redirect), session-events.
2. Страницы `/login` (Telegram-виджет script, email-форма, dev-кнопка по флагу) и `/register` (username/display_name).
3. Никаких моков при 401; dev-вход строго по флагу.

**Выход:** вход работает (email-регистрация создаёт reader; dev-вход admin), logout чистит cookie.
**Проверка:** playwright smoke: register → `/` → role=reader в Topbar; logout → redirect.

### Шаг 4 — RBAC runtime

1. `shared/rbac/`: can(), RoleGate; матрица из generated; пометки D1–D6 (константы EXCLUDED_PATHS/NOTES).
2. Навигационная модель: NAV_GROUPS (IA из ARCHITECTURE §4.1) с `rolesFor` из матрицы; F2+-пункты помечены `disabled: coming-soon`.

**Выход:** `can(admin, '/xray')===true`, `can(reader, '/xray')===false` — по матрице, не по здравому смыслу.
**Проверка:** vitest: полный прогон ролей × навигационных пунктов; тест D-пометок.

### Шаг 5 — App shell

1. `widgets/app-shell`: Topbar (user, role-badge, ws-online-badge, logout), Sidebar (NAV_GROUPS, фильтр can(), collapse), лейауты `(auth)`/`(main)` + AuthGuard.
2. `/` — foundation-дашборд: приветствие по роли, статус-карточки (backend health `/health`, версия контрактов, ws-статус) — без доменных экранов.
3. `/no-access`, `not-found`, loading-fullscreen.

**Выход:** полный shell навигации с ролевой фильтрацией; все пункты F2+ — coming-soon.
**Проверка:** e2e: reader не видит «Студия»; admin видит; 403-роут → /no-access.

### Шаг 6 — Realtime infrastructure

1. `shared/realtime/ws-client.ts` (перенос ws.ts: reconnect/backoff/jitter/cookie-token) + WsProvider + событие online/offline → Topbar badge.
2. `shared/realtime/sse.ts`: createSseClient — типизированный парсер; тесты парсинга.

**Выход:** badge соединения живёт/реагирует на обрыв backend; WS-события логируются в dev-консоль (пока без доменных обработчиков).
**Проверка:** vitest fake-ws: connect→drop→reconnect; playwright: остановить backend → badge offline (ручная проверка, не в CI).

### Шаг 7 — Тесты, CI, финализация

1. Полный vitest-набор (по SPEC §10), playwright smoke.
2. CI: contracts:verify-шаг перед vitest; сборка обоих проектов зелёная.
3. Отчёт: F1_IMPLEMENTATION_REPORT.md (по формату владельца) → F1_POST_IMPLEMENTATION_AUDIT.md (с PROVEN-доказательствами по DoD §12 SPEC).

**Выход:** все DoD-пункты SPEC закрыты с доказательствами.

---

## Порядок зависимостей

```
0 (каркас) → 1 (контракты) → 2 (client) → {3 (auth) ∥ 4 (rbac)} → 5 (shell) → 6 (realtime) → 7 (тесты/CI/отчёты)
```

## Что НЕ делается (контроль красных линий)

- Ни одного вызова вне auth/health-контрактов.
- Ни одной domain-страницы (F2+).
- Ни одного изменения в `arkaim-web/` (legacy), `runtime/`, `core/` (проверка: git-diff по директориям в конце каждого шага).
- Никаких моков при 401; моки только транспорта в тестах.
- Backend-дефекты D1–D6: только пометки в matrix.ts, не исправления.

## Артефакты по завершении

| Артефакт | Тип |
|---|---|
| `arkaim-web-v2/` (проект F1: shell, auth, rbac, api, realtime, тесты) | NEW |
| `arkaim-web-v2/contracts/openapi.json` (слепок) + generated | NEW |
| CI job frontend-v2 | EDIT (.github/workflows/ci.yml — добавить job; legacy-job не трогать) |
| `docs/F1_IMPLEMENTATION_REPORT.md` | NEW |
| `docs/F1_POST_IMPLEMENTATION_AUDIT.md` | NEW (после отчёта, с доказательствами DoD) |

Оценка объёма: ~25–30 файлов нового кода, ~1800–2500 строк TS/TSX (без generated), 5 конфигов, CI-правка одного job-блока.
