# F1 — Отчёт о реализации (Новый Frontend: Фундамент)

**Дата:** 2026-09-09
**Статус:** PASS (все 10 контрольных проверок)
**Спецификация:** `docs/F1_SPEC.md` (11 пунктов объёма, все реализованы)
**План:** `docs/F1_IMPLEMENTATION_PLAN.md` (шаги 0–7, все выполнены)

---

## Простыми словами

1. **Что было целью?** — Построить фундамент нового frontend («arkaim-web-v2»): каркас приложения, вход по реальным механизмам backend'а, права по фактической матрице, единые правила ошибок/загрузки, живое WS-соединение — без единого доменного экрана.

2. **Что реально сделано?** — Создан отдельный проект `arkaim-web-v2/` (51 файл): приложение с входом/регистрацией, дашбордом статуса, навигацией по ролям; сгенерированы типизированные контракты из «слепков» backend'а (289 API-путей + 298 правил доступа); написаны 33 автотеста; настроена CI-проверка целостности контрактов.

3. **Что получилось?** — **PASS**. Все 10 контрольных проверок прошли.

4. **Есть ли проблемы?** — Нет блокирующих. Два технических обстоятельства среды разработки (не проекта): (а) сборка требует флаг `workerThreads` (иначе анти-вирусная политика Windows блокирует служебные процессы — то же самое происходит со старым frontend'ом на этой машине); (б) тестовый раннер vitest не запускается в этой сессии — написан локальный обходной раннер, в CI работает штатный vitest.

5. **Что предлагается дальше?** — Независимый post-implementation аудит (по регламенту), затем F2 (доменные экраны Читателя: чтение, вопрос-ответ, чат) по решению владельца.

---

## Сводка контрольных проверок (10/10 PASS)

| # | Проверка | Результат | Детали |
|---|----------|-----------|--------|
| 1 | Тест-набор | **PASS** | 33/33 (локальный раннер; в CI — `vitest run` тем же набором) |
| 2 | tsc strict | **PASS** | 0 ошибок (`tsc --noEmit`) |
| 3 | Lint | **PASS** | 0 ошибок, 0 предупреждений (`eslint`, включая красные линии) |
| 4 | Production build | **PASS** | 5 маршрутов: `/`, `/login`, `/register`, `/no-access`, `/_not-found` — все собраны |
| 5 | OpenAPI-контракты | **PASS** | слепок 289 путей ↔ `schema.d.ts` (515 КБ) ↔ `contracts:verify` OK; live-сверка `/openapi.json` = слепку |
| 6 | Auth/RBAC | **PASS** | live-smoke: register→cookie→me, 401-формат; RBAC: 298 маршрутов, can() по иерархии, D1/D2 помечены |
| 7 | SSE/WS | **PASS** | ws-client (reconnect/backoff/jitter/cookie-токен) + SSE-парсер W3C; тесты 3+3 |
| 8 | Backend не тронут | **PASS** | git: 0 новых диффов в `runtime/`, `core/`, `arkaim-web/` (43 ранее существующих диффа — от прошлых сессий, не тронуты) |
| 9 | git stat | **PASS** | untracked: `arkaim-web-v2/` (51 файл), 5 доков F1, `ci.yml` (+1 job); legacy-job CI не изменён |
| 10 | Отчёт | **PASS** | этот документ |

---

## Что сделано (по 11 пунктам F1_SPEC)

### Реализовано полностью (сделано)

| Пункт SPEC | Что | Артефакты |
|------------|-----|-----------|
| §1 Каркас приложения | Next.js 16.2.10 (App Router, Turbopack), порт 3001, отдельный проект | `package.json`, `next.config.ts` |
| §2 Навигация/маршруты | Новый IA от backend-возможностей; группы по ролям; F2+-пункты «скоро» | `src/shared/rbac/navigation.ts`, `src/widgets/app-shell/AppShell.tsx` |
| §3 Typed API-клиент | fetch-обёртка: cookie-сессия, retry, timeout, единый ApiError | `src/shared/api/client.ts`, `src/shared/api/errors.ts` |
| §4 OpenAPI→контракты | Слепок → openapi-typescript → `schema.d.ts`; верификация диффом в CI | `scripts/contracts.mjs`, `contracts/openapi.json` |
| §5 Аутентификация | /login (Telegram-токен из URL, регистрация, dev за флагом), /register; cookie-сессия; **никаких моков при 401** | `src/entities/auth/AuthProvider.tsx`, `src/app/(auth)/**` |
| §6 RBAC | Матрица из живого backend'а → `matrix.ts`; `can()`; RoleGate; навигация фильтруется по роли | `scripts/dump_rbac_matrix.py`, `src/shared/rbac/can.ts` |
| §7 Единая модель ошибок | Оба формата backend (`{ok:false,error}` и `{detail}`) → ApiError | `src/shared/api/errors.ts` (тесты обоих форматов) |
| §8 Состояния UI | StateView: loading/empty/error+retry — единые примитивы | `src/shared/ui/StateView.tsx` |
| §9 Realtime-инфраструктура | WS-клиент (порт legacy ws.ts: reconnect/backoff/jitter) + WsProvider + индикатор онлайн; SSE-парсер-примитив | `src/shared/realtime/*` |
| §10 CI contract-verification | Новый job `frontend-v2-test`: npm ci → contracts:verify → lint → tsc → vitest → build | `.github/workflows/ci.yml` |
| §11 Тесты фундамента | 33 unit-теста: контракты, RBAC, auth-моки (транспорт, не данные), ApiError, SSE, WS | `tests/unit/*` |

### Ключевые инженерные решения

1. **Слепки контрактов как source of truth.** `contracts/openapi.json` (289 путей, снят с живого backend'а) и `contracts/rbac-matrix.json` (298 маршрутов, извлечён обходом include-дерева FastAPI) коммитятся. CI-верификация — node-only: регенерация из слепков и дифф с committed-артефактами. Backend в CI не нужен.

2. **RBAC-дампер с выравниванием по OpenAPI.** Дефект FastAPI 0.136 (`_IncludedRouter` стирает родительские префиксы `/book`, `/auth` при include) обойдён: пути матрицы выравниваются по OpenAPI-эталону суффиксным матчингом (293/298 однозначно; 5 неоднозначных суффиксов сохранены как есть — `can()` для них консервативно вернёт false).

3. **Auth без response_model → ручные типы по фактическому JSON.** `AuthUser {id, role, username?, display_name?, provider?}` — подтверждено live-smoke'ом (включая `provider`).

4. **Единый ApiError на оба формата ошибок.** Live-smoke открыл: `/auth/me` 401 отдаёт **глобальный envelope** `{"ok":false,"error":{code,message}}`, а не FastAPI-`{detail}` — парсер покрывает оба (тесты на оба формата).

5. **Красные линии в eslint.** `fetch` запрещён вне `src/shared/api|realtime` и `src/app/api`; `WebSocket` — вне `src/shared/realtime`. Generated-артефакты исключены из линта.

6. **React Compiler-совместимость.** Next 16 линтит `setState`-в-effect: AuthProvider переписан на react-query (`/auth/me` как server-state), тема — ленивая инициализация. 0 нарушений.

### Отклонения/уточнения от SPEC (все в пользу надёжности)

- **`openapi-fetch@^1.1.1` не существует** (версии 0.x) — SPEC-версия была ошибочна; использован `^0.14.1`, `openapi-typescript ^7.13.0`. Тип-генерация не зависит от openapi-fetch (F1 использует собственный client).
- **RBAC-маршрутов 298, а не 307**: 307 — с дублями path+method (кросс-роутеры монтируются дважды); уникальных — 298. Матрица консервативна: неизвестный путь → `can()=false`.
- **D1/D2-дефекты** не в матрице (пути `/book/book/*` и заглушка apply не входят в OpenAPI 289) — помечены в `BACKEND_DEFECTS` из forensic-аудита.

### Обходные пути среды разработки (задокументированы в коде)

| Проблема среды | Решение | Влияние на CI |
|----------------|---------|---------------|
| Антивирус блокирует npm postinstall | `--ignore-scripts` + локальный кэш | нет (CI-политика иная) |
| Sandbox блокирует pipe-спавн (vitest CLI, next build workers, next dev) | `workerThreads: true` в next.config; локальный in-process раннер `scripts/run-tests.mjs` для сессии; **CI использует штатные** `vitest run` / `next build` | нет |
| tsc в build спавнит worker | `typescript.ignoreBuildErrors` (tsc — отдельный CI-гейт до build) | нет (CI гоняет tsc сам) |

---

## Результаты прогонов (2026-09-09)

```
1. lint:            0 errors, 0 warnings
2. tsc --noEmit:    0 errors (strict)
3. contracts:verify: schema.d.ts OK, matrix.ts OK
4. tests:           33 passed, 0 failed
5. build:           ✓ 5 routes (/, /login, /register, /no-access, /_not-found)
6. live-smoke:      /health 200; /auth/me 401→envelope; register 200+cookie;
                    /auth/me(session) 200 {user}; dev/generate-token 200 {token,login_url}
7. proxy-rewrites:  /auth/me через :3001 → backend 401 (проксирование подтверждено)
```

## Дерево arkaim-web-v2 (51 файл, ~2500 строк)

```
arkaim-web-v2/
├── contracts/               # СЛЕПКИ (коммитятся — source of truth)
│   ├── openapi.json         #   289 путей
│   └── rbac-matrix.json     #   298 маршрутов
├── scripts/                 # Пайплайн контрактов + обходы среды
│   ├── fetch-contract.mjs   #   GET /openapi.json → слепок
│   ├── dump_rbac_matrix.py  #   живой обход FastAPI → RBAC-слепок
│   ├── contracts.mjs        #   генерация schema.d.ts + matrix.ts, --verify
│   ├── live-smoke.mjs       #   live-проверка auth-контрактов
│   └── run-tests.mjs + ts-alias-loader + runner-globals + vitest-shim  # локальный раннер
├── src/
│   ├── app/                 # layout, providers, (auth)/login|register, (main)/|no-access, not-found
│   ├── entities/auth/       # AuthProvider (react-query /auth/me)
│   ├── shared/api/          # client, envelope, errors, contracts/auth, generated/schema.d.ts
│   ├── shared/rbac/         # can, RoleGate, navigation, generated/matrix.ts
│   ├── shared/realtime/     # ws-client, WsProvider, sse
│   ├── shared/ui/           # StateView
│   └── widgets/app-shell/   # AppShell (Topbar+Sidebar)
├── tests/unit/              # 6 файлов, 33 теста
├── tests/e2e/               # foundation.spec.ts (playwright, вручную)
├── package.json, tsconfig, next.config, eslint, vitest, playwright, postcss, .gitignore, .env.local
```

---

## Соответствие красным линиям (FRONTEND_ARCHITECTURE R1–R7)

- ✅ R1: backend — единственный источник истины (слепки + генерация, ручные типы только там, где backend не типизирован — auth)
- ✅ R2: никакого mock-on-401 (AuthProvider при 401 = «не залогинен» → /login)
- ✅ R3: dev-вход только по `NEXT_PUBLIC_DEV_AUTH=1`, никогда автоматически
- ✅ R4: RBAC строго по фактической матрице (298 маршрутов, иерархия reader<editor<admin)
- ✅ R5: сетевые вызовы только в shared/api + shared/realtime (eslint-гейт)
- ✅ R6: доменные экраны НЕ реализованы (все coming-soon, только foundation-дашборд)
- ✅ R7: legacy не тронут (0 диффов в arkaim-web/)

## Запланированное, но не делавшееся (вне объёма F1)

- Доменные экраны (F2+): все пункты навигации «скоро» — по плану
- Playwright e2e: написаны (`tests/e2e/foundation.spec.ts`), в CI не включены (нужен backend; SPEC §10: smoke не входит в CI-гейт)
- Google OAuth: скрыт (не настроен в backend — решение владельца подтверждено)

---

## Предложение по дальнейшим шагам

1. **Post-implementation аудит F1** (независимый, по регламенту владельца).
2. После ACCEPTED — F2 (экраны Читателя: чтение, вопрос-ответ, чат с книгой) отдельной SPEC'ой.
