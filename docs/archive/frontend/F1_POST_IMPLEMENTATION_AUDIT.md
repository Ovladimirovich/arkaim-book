# F1 — POST-IMPLEMENTATION AUDIT (независимая проверка)

**Дата:** 2026-09-09
**Аудируемый объект:** `arkaim-web-v2/` (51 файл) + `.github/workflows/ci.yml` + F1-доки
**Метод:** независимая проверка фактического состояния (git-состояние, реальные запуски, live-flow, diff-обзор, целенаправленные эксперименты над WS/SSE/RBAC/error-моделями)
**Ограничение аудита:** nothing fixed, nothing refactored — только проверка и доказательства

---

## ВЕРДИКТ

# F1 — AUDIT PASSED

С двумяMedium-находками, требующими решения владельца в F2 (не блокируют закрытие F1, подробности ниже). Код по итогам аудита НЕ менялся.

---

## Простыми словами

1. **Что проверял?** — Что фундамент нового frontend'а реально построен строго по утверждённой спецификации: без подделок API, без прав самовыдачи, без изменений backend'а, с настоящими контрактами.

2. **Как проверял?** — Не по отчёту, а по коду и живым запускам: сверил все изменения git, прогнал все проверки заново, поднял backend и прожил весь путь пользователя (регистрация → cookie → «кто я» → выход), устроил стресс-тесты websocket-у teardown'у и кривым SSE-кадрам.

3. **Что получилось?** — Всё основное честно. Найдены 2 реальных недочёта среднего уровня (обе — в редких сценариях, обе уже задокументированы ниже с точными строками) и 2 косметических. Ни одна не подрывает архитектуру и не требует правок backend'а.

4. **Есть ли проблемы?** — (а) websocket после «отключиться» может тихо переподключиться обратно (эксперимент это показал); (б) страница входа при переходе по одноразовой ссылке из Telegram в dev-режиме может «прожать» вход дважды, и вторая попытка упадёт «токен недействителен» (токен одноразовый). Обе — кандидаты в F2-fix, не в F1.

5. **Что дальше?** — Владелец принимает решение: закрыть F1 с этими заметками (рекомендую) и включить обе находки в backlog F2.

---

## §1 GIT / SCOPE — PASS

**Доказательства:**

- `git status`: 115 строк. **43 tracked-изменения (39 M + 4 D)** — из них 42 файла pre-existing (сессии M0–M10.2: runtime-тесты, core, arkaim-web map/panel, docs), **1 файл F1: `.github/workflows/ci.yml`**.
- Проверка F1-контента в backend-диффах: `git diff -- runtime core | grep 'arkaim-web-v2|:3001|frontend-v2|\bF1\b'` → **0 совпадений**. Backend-диффы не содержат F1-контента.
- Untracked: `arkaim-web-v2/` (51 файл — полный список ниже), 44 docs (5 F1 + 39 прошлых milestone'ов), evidence-файлы runtime/forensic_*.txt (прошлый этап), core-модули прошлых этапов.
- `ci.yml` diff: +44 строки (новый job), −1 строка (needs-список расширен). Ничего больше.
- Скрытый scope creep: не найден — все 51 файл в границах SPEC (app shell / auth / rbac / realtime / state-primitives / tests / scripts / configs / contracts-слепки).

**Полный список 51 файла arkaim-web-v2:** .gitignore, contracts/{openapi.json, rbac-matrix.json}, eslint.config.mjs, next.config.ts, package.json, package-lock.json, playwright.config.ts, postcss.config.mjs, tsconfig.json, vitest.config.mjs, scripts/{contracts.mjs, dump_rbac_matrix.py, fetch-contract.mjs, live-smoke.mjs, run-tests.mjs, runner-globals.mjs, ts-alias-loader.mjs, vitest-shim.mjs, audit-sse.mjs*}, src/app/{layout,providers,globals.css,not-found} + (auth)/{layout,login,register} + (main)/{layout,page,no-access}, src/entities/auth/AuthProvider, src/shared/api/{client,envelope,errors,index,contracts/auth,generated/schema.d.ts}, src/shared/rbac/{can,RoleGate,navigation,generated/matrix.ts}, src/shared/realtime/{ws-client,WsProvider,sse}, src/shared/ui/StateView, src/widgets/app-shell/AppShell, tests/unit/{setup,errors,rbac,auth,ws-client,sse,contracts}, tests/e2e/foundation.spec.ts.

\* audit-sse.mjs добавлен самим аудитом (проверочный скрипт §6) — единственное изменение файлового списка от аудита.

## §2 FRONTEND CONTRACT BOUNDARY — PASS

- **Все сетевые вызовы** (grep-факт): `fetch()` — 1 место (client.ts:48, разрешённый слой), `new WebSocket` — 1 место (ws-client.ts:51, разрешённый слой), `apiCall` — 7 вызовов: /auth/me, /auth/register, /auth/telegram/login, /auth/telegram/callback, /auth/dev/generate-token, /auth/logout (POST), /health (GET).
- **7/7 endpoint'ов присутствуют в OpenAPI-слепке** (запуск-доказательство: all true; `/auth/logout` имеет get+post — frontend использует POST).
- **Mock/fake:** grep `MOCK_DATA|mockData|mock|fake|stub` по src → 0 совпадений. Mock-механика legacy (mock-on-401) отсутствует полностью.
- ENVELOPE_MAP — 8 записей, все пути существуют в OpenAPI (тест-проверено + независимо).
- Hardcoded-эндпоинтов вне OpenAPI — нет.

## §3 OPENAPI SOURCE OF TRUTH — PASS (с известными 5 unmatched)

Реальные запуски:
- `contracts:verify` (регенерация + дифф) → **exit 0, оба OK**.
- Числа: **289 OpenAPI paths**; **rbac-matrix total_routes=298; уникальных path+method пар=298; дублей=0**.
- Все вызываемые frontend'ом endpoint'ы (7) + все nav-метки (24) присутствуют в OpenAPI → **bad=0**.
- 5 unmatched-путей матрицы (`/cache/stats`, `/drafts`, `/drafts/{draft_id}/approve`, `/generate`, `/genome`) — суффиксные коллизии (например `/drafts` есть и в `/book/drafts`, и в `/book/email/drafts`). **Проверено направление отказа:** для всех 5 `can('admin', …) = false` — матрица отказывает консервативно, прав не добавляет. Функциональная потеря: по этим путям UI не сможет дать разрешение до уточнения в F2+ (это deny, не allow — безопасно).

## §4 RBAC — PASS

Реальное исполнение navForRole/can:
- reader → группы [book, community, personal]; editor → [book, studio, proposals, community, personal]; admin → все 6.
- `can('/auth/admin/users')`: reader=false, editor=false, admin=true — точно по матрице.
- Frontend не выдаёт права: `can()` только читает generated-матрицу (иерархия reader<editor<admin из backend ROLE_HIERARCHY); в `navigation.ts` роли зашиты из forensic-матрицы и совпадают с backend-группами (проверено тестом matrix==snapshot).
- **URL-обход невозможен by construction:** доменных страниц физически нет (4 page.tsx: /, /login, /register, /no-access); прямой URL к доменным разделам → 404. Единственный защищённый контент `/` — за AuthGuard (без сессии → /login).
- **298 vs 307: доказано числом.** forensic_rbac2.txt: 307 строк маршрутов = **298 уникальных + 9 дублей** (crowdfunding-роутер монтируется дважды — известный D1-паттерн; `/` и `/health` входят в два include-дерева). Число контракта — именно 298.

## §5 AUTH / SESSION — PASS (backend-нюанс задокументирован)

Live-flow (backend поднят, реальный запуск live-smoke):
- `GET /health` → 200 `{status:ok, mode:live, …}` ✓
- `GET /auth/me` без сессии → **401 `{ok:false, error:{code:"HTTP_401"}}`** — envelope (см. §11-KF1) ✓
- `POST /auth/register` → 200 `{ok:true, user:{id, role:"reader", …}}` + `Set-Cookie: arkaim_session=<JWT>` ✓
- `GET /auth/me` с cookie → 200 `{user:{id, role, username, display_name, provider:"email"}}` ✓
- `POST /auth/logout` → 200 `{ok:true}` ✓

**Backend-нюанс (не F1-дефект):** после logout сохранённый старый cookie продолжает работать до истечения JWT (12h) — backend stateless-JWT, logout только `delete_cookie` (routes.py:193-197). Frontend-сторона корректна: вызов POST /auth/logout + сброс react-query-кэша + redirect. Поведение — контрактная особенность backend'а, за красной линией F1; рекомендую в будущем отдельным backend-решением (revocation-list или short-lived JWT).

- 401-handling: getMe() → null → AuthGuard → /login. Никаких моков.
- Credentials: **0 токенов в localStorage/sessionStorage** (только `theme` — UI-настройка). WS читает cookie только для query-param (контракт `/ws?token=`).
- Комментарий AuthProvider.tsx:7 «снимает cookie» — **косметическая неточность** (cookie удаляется браузером через Set-Cookie, JWT остаётся валиден) — Low, не блокирует.

## §6 SSE / WS — PASS c 1 Medium-finding

**WS-leak (Medium):** `ws-client.ts:66-70` — `disconnect()` (стр. 76-83) сбрасывает таймеры и закрывает сокет, но `ws.close()` инициирует асинхронное close-событие; когда оно приходит, `onclose` безусловно вызывает `scheduleReconnect()` → новый WebSocket создаётся **после** disconnect. **Экспериментальное доказательство:** симуляция close-события через 5мс после disconnect → instances=2 (LEAK: reconnect-after-disconnect). Экспоненциальный backoff ограничивает последствия (maxAttempts=10), но lifecycle-контракт нарушен: после unmount WsProvider соединение может тихо воскресить. Файл/строка: `src/shared/realtime/ws-client.ts:66-70` (onclose → scheduleReconnect без проверки состояния disconnect). Рекомендация для F2: флаг `intentionalClose` в disconnect() и проверка в onclose.

**SSE-парсер — все malformed-кейсы корректны (запуск-доказательства):**
- битый JSON в data: → data как строка, не падает ✓
- `event:` без `data:` → кадр тихо пропускается ✓
- heartbeat-комментарий `: keep-alive` → игнорируется ✓
- нестандартные строки → игнорируются ✓
- пустой поток → onDone, не падает ✓

**Background polling:** отсутствует — grep setInterval/polling → только WS-reconnect-таймер и fetch-timeout (легитимные).

**Mock-события realtime:** отсутствуют (нет синтетических event'ов).

**Listeners-утечки:** `on()` возвращает off-функцию; WsProvider корректно отписывается (offConn/offDisc) — по handlers-механике утечки нет. Единственная утечка — WS-соединения (выше).

## §7 STATEVIEW / ERROR MODEL — PASS

Обе backend-модели нормализуются (запуск-доказательства):
- `{ok:false, error:{code,message,details}}` → ApiError с сохранением code+message+**details** (проверено: details={"field":"x"} сохранены) ✓
- `{detail:"..."}` → ApiError HTTP_<status> с message ✓
- `{detail:[pydantic]}` → message=первый msg, **весь массив в details** ✓
- 401→isAuthError, 403→isForbidden ✓
- StateView: loading (Skeleton), empty (AntEmpty), error+retry (Alert+Button), no-access (Result 403-страница) — все 4 примитива существуют и используются (foundation-дашборд).

**trace_id:** проверено — backend `ErrorResponse` (dto/responses.py:23-25) **не содержит trace_id** (только SuccessResponse его имеет). Потеря невозможна by contract; псевдо-находка из отчёта реализации снята.

## §8 BUILD / CI — PASS (полный re-run)

| Проверка | Результат |
|----------|-----------|
| ESLint | exit 0, 0 errors / 0 warnings |
| tsc --noEmit (strict) | exit 0 |
| Тесты (33) | **33 passed, 0 failed** |
| contracts:verify | exit 0, schema.d.ts OK, matrix.ts OK |
| Production build | 5 маршрутов: `/`, `/_not-found`, `/login`, `/no-access`, `/register` — все static |

CI-diff (git-доказательство): единственные изменения — новый job `frontend-v2-test` (+44 строки) и расширенный `needs:` docker-build (−1/+1). **Legacy-job: 0 изменений. Backend-job: 0 изменений.** Новый job изолирован (все шаги в `arkaim-web-v2/`, свой npm-cache, node 24).

Замечание: `vitest.config.mjs` (не .ts как в плане) — sandbox-обход, витвест подхватывает штатно; CI-гейт идентичен. Cosmetic.

## §9 RED-LINE CHECK — PASS

| Красная линия | Доказательство |
|---------------|----------------|
| Backend не изменён | git-диффы runtime/core не содержат F1-контента (0 совпадений); все 39M+4D — pre-existing |
| Legacy-frontend не изменён F1 | 4 диффа arkaim-web — pre-existing (map-страница, GenerationSettings — прошлые сессии); F1-контента 0 |
| M10/temporal не тронуты | core/CORE/narrative_engine диффы — pre-existing (M-серии); F1-маркеров нет |
| Новых backend-эндпоинтов нет | API-слой frontend вызывает только существующие 7 |
| Deps в пределах SPEC | package.json: только заявленный стек (next/react/antd/react-query/zod/openapi-tools/testing); 0 внезапных |
| Persistence нет | localStorage — только `theme` |
| Нового state-фреймворка нет | react-query + React context (оба из SPEC); grep zustand/redux/mobx → 0 |
| UI в пределах F1 | 4 страницы, доменных экранов 0 |

## §10 ACTUAL DIFF REVIEW — 2 findings

Просмотрен каждый src-файл. Отклонения от SPEC/плана, НЕ отражённые в отчёте реализации:

1. **[Medium] login/page.tsx:47-49 — side-effect в render.** `if (urlToken && !busy) { void handleTelegramToken(urlToken); }` — сетевой вызов в теле рендера. Последствия: (а) setState-во время рендера — React-антипаттерн; (б) в dev (Next App Router = StrictMode) двойной mount → **двойной POST /auth/telegram/login**; токен одноразовый (backend login_tokens.py:37 `_tokens.pop`) → второй вызов получает «Токен недействителен». В production-сборке билд-артефакт от этого не страдает (single mount), но паттерн ненадёжен. Правка — кандидат F2 (перенести в useEffect с ref-guard). Не блокирует F1: dev-феномен, worst-case — лишний error-toast.
2. **[Low] vitest.config.mjs вместо .ts** — план-девиация, sandbox-обход, функционально эквивалентна.
3. **[Low] openapi-fetch@0.14.1 установлен, но не импортируется** (0 использований в src) — F1-client самодостаточен; dep — задел на F2 или кандидат на удаление.
4. **[Cosmetic] AuthProvider.tsx:7 комментарий** «снимает cookie» — неточен (см. §5).
5. **[Cosmetic] /book/cache/stats и 4 sibling-пути** — RBAC-записи потеряны в суффикс-коллизиях, can()=false (deny) — задокументировано в §3, требует уточнения в F2 (выбрать правильный префикс вручную в слепке или улучшить матчинг).

## §11 KNOWN FINDINGS — все три подтверждены

**KF1: `/auth/me` 401 в envelope-формате.**
- A: **Факт.** main.py:380-391 — глобальный `http_exception_handler` перехватывает ВСЕ HTTPException → `{"ok":false,"error":{code,message}}`. Live-smoke: 401 пришёл именно в этом формате.
- B: Не нарушает инварианты: frontend-парсер (errors.ts:37-56) нормализует оба формата; тесты покрывают оба.
- C: Не маскирует backend-дефект: это **контрактная конвенция** backend'а (единый error-конверт), зафиксирована в F1_SPEC §5 как manual-typing.
- D: Remediation не требуется для закрытия F1.

**KF2: openapi-fetch ^1.1.1 → ^0.14.1.**
- A: **Факт.** Версии 1.x не существует (npm registry); установлен 0.14.1.
- B: Не нарушает: F1-client (`client.ts`) не использует openapi-fetch вовсе (самодостаточен); генерация типов — через openapi-typescript (штатно работает).
- C: Не маскирует: SPEC-ошибка версии исправлена явно, задокументирована.
- D: Не требуется. Замечание: dep не используется (см. §10-3) — решение об удалении/использовании в F2.

**KF3: FastAPI `_IncludedRouter` стирает родительские префиксы.**
- A: **Факт.** `effective_candidates()` отдаёт маршруты с локальными путями (без `/book`, `/auth`); forensic-иexperimental-доказательства в §4 (307→298) и dump_rbac_matrix.py docstring.
- B: Не нарушает: слепок выравнивается по OpenAPI-эталону (суффикс-матчинг), 293/298; unmatched-5 сохранены и fail-safe.
- C: Не маскирует: дефект — в структуре FastAPI 0.136 include-дерева (framework behavior), не в бизнес-коде backend'а; обобщение делает данные БОЛЕЕ консервативными (deny), не менее.
- D: Не требуется для F1. Рекомендация в F2+: для 5 коллизионных путей — ручное разрешение в слепке или переход на `app.openapi()` как единственный источник (но это не блокирует F1).

**Sandbox spawn EPERM:** подтверждено как **средовое ограничение**: (а) воспроизводится на legacy-проекте (vitest CLI + next build падают там же); (б) bare `spawnSync(stdio:'pipe')` → EPERM, `stdio:'ignore'` → OK; (в) production-дефектом не является: CI (GitHub Actions) запускает штатные `vitest run`/`next build` без worker-ограничений; обходы в v2 (`workerThreads`, `test:local`-раннер) — dev-эргономика, не prod-код-изменения. Не требует remediation.

---

## СВОДНАЯ ТАБЛИЦА

| § | Область | Вердикт | Findings |
|---|---------|---------|----------|
| 1 | Git/Scope | PASS | — |
| 2 | Contract boundary | PASS | — |
| 3 | OpenAPI SOT | PASS | 5 known unmatched (deny-safe) |
| 4 | RBAC | PASS | — (298 подтверждено) |
| 5 | Auth/Session | PASS | backend stateless-JWT нюанс (не F1) |
| 6 | SSE/WS | PASS | 1 Medium: reconnect-after-disconnect (ws-client.ts:66-70) |
| 7 | StateView/Errors | PASS | — |
| 8 | Build/CI | PASS | — (все 5 зелёные) |
| 9 | Red lines | PASS | — |
| 10 | Diff review | 2 findings | 1 Medium (login render-side-effect), 1 Low (unused dep), 3 cosmetic |
| 11 | Known findings | Все подтверждены | remediation не требуется |
| 12 | **ВЕРДИКТ** | **F1 — AUDIT PASSED** | 2 Medium в backlog F2 |

## Рекомендации (НЕ выполнены — по регламенту аудита)

Для F2-backlog (решение владельца, не автоматическое):
1. `ws-client.ts` — флаг intentionalClose в disconnect() (Medium).
2. `login/page.tsx` — urlToken-обработка в useEffect + ref-guard (Medium).
3. `openapi-fetch` — удалить или начать использовать (Low).
4. 5 RBAC-коллизионных путей — ручное разрешение в слепке (Low).
5. Комментарий AuthProvider про cookie (Cosmetic).

**Код по итогам аудита не изменён. F1 не продолжается. Следующий milestone не начат.**
