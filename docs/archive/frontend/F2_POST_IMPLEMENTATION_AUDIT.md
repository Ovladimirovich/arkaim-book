# F2 — POST-IMPLEMENTATION FORENSIC AUDIT (read-only)

**Дата:** 2026-09-09
**Объект:** F2 «Диалог с книгой» — `arkaim-web-v2/` + SPEC/PLAN/REPORT
**Статус аудита:** завершён — вердикт **PASS WITH FINDINGS** · **F2 — ACCEPTED & CLOSED** (решение владельца от 2026-09-09; findings F2-A1/A2 → backlog F3; F2-A3 — backend-scope; F2-A4 — среда, не дефект)
**Метод:** независимая проверка фактического кода, живого runtime и git-состояния против `F2_SPEC.md`. Ничего не исправлено, не удалено, не начато (F3 не начинался, backend/M10/M10.2/legacy не тронуты — см. §1).
**Инструменты аудита:** `scripts/f2-audit-{contracts,rbac,auth,b1}.mjs` + независимые прогоны батарей + mtime/git-доказательства.

---

## ВЕРДИКТ

# F2 — PASS WITH FINDINGS

Реализация полностью соответствует SPEC; красные линии целы; все заявленные проверки воспроизводятся. Найдено 4 non-blocking findings (ниже), ни одно не блокирует F3.

---

## Простыми словами

1. **Что проверял** — не отчёт, а реальность: git-следы, живой backend, код каждого экрана, поведение websocket'а после отключения, права, историю входа и выходов.

2. **Как проверял** — поднял backend и прожил весь путь пользователя заново (вход → вопрос → ответ с источником → главы → чтение → профиль), сверил каждую букву контрактов, устроил websocket'у три стресс-сценария разрыва, пересчитал все тесты, пересобрал проект.

3. **Что получилось** — всё заявленное — правда: 66 тестов зелёные, 12/12 живых проверок, сборка из 8 страниц, backend и старый frontend не тронуты (доказано по датам файлов и содержимому диффов). Нашёл 4 мелочи, ни одна не мешает.

4. **Проблемы** (все — «заметки на полях», не поломки): (а) отметка «на сколько прочитано» при уходе с главы считается по загруженному объёму текста, а не по фактическому положению скролла — приближение; (б) кнопка «Спросить» пропускает вопросы из 1–2 символов — backend честно ответит ошибкой валидации (минимум 3), и фронт её красиво покажет, но можно было бы и сразу не пускать; (в) browser-E2E в этой среде физически невозможен (среда запрещает запуск браузера) — сценарии лежат в репо и сработают в CI, но в этом окружении это ограничение проверки, а не проверка; (г) сообщение об ошибке для короткого вопроса придёт «по-английски» от валидатора backend'а.

5. **Что дальше** — предлагаю принять F2 как закрытый этап; находки внести в backlog F3 (исправление — по одной строке каждая). Решение за вами.

---

## §1 Git boundary — PASS

Три независимых доказательства (не только grep):

1. **Tracked-счётчик:** 43 изменённых tracked-файла — ровно как в базе F1-аудита (42 pre-existing M-серии + ci.yml). F2 не добавил ни одного tracked-изменения.
2. **mtime-доказательство:** 0 файлов в runtime/core/arkaim-web (backend/legacy/M10) имеют время изменения позже начала F2-сессии (при том, что F2-файлы датированы сегодня 05:39+). Backend физически не открывался на запись.
3. **Содержимое runtime-диффов:** добавленные строки — это известная pre-existing M-серия (temporal-роутеры M10, identity-sanitizer, visual/epoch M7.2, provider AB-testing) — тема F2 в них отсутствует (grep по `arkaim-web-v2|:3001|frontend-v2|F2-` = 0).

F2-след: только `arkaim-web-v2/` (71 untracked-файл), `docs/F2_*.md` (4 документа + SPEC-правка live-фактами шага 0 — легальная документация), `scripts/f2-*.mjs` (аудит/проверка-скрипты).

## §2 F2 scope — PASS

Grep-сан по src/: `/v1/`-вызовы — 0; community/temporal/world-explorer — 0 вызовов (только coming-soon-метки навигации — разрешено SPEC); EventSource/ReadableStream/text-event-stream — 0 (нет fake streaming); setInterval — 0 (нет polling); fetch/WebSocket — только client.ts:48 и ws-client.ts:57 (красная линия F1 цела); mock/fake/stub — 0.

Каждый production-файл в SPEC-границах: контракты (envelope/book/reader), B1/B2-фиксы (ws-client, login), экраны (/, /reading, /profile), /status (F1-перенос), SourceBadge, navigation. Незаявленной бизнес-логики нет; legacy-архитектура не переносилась (SourceBadge — пере-реализация, не копипаст).

## §3 API contracts — PASS (10/10 live)

Независимый конверт-контроль (живые вызовы против ENVELOPE_MAP из кода):

| Endpoint | Живой факт | Map | Σ |
|----------|-----------|-----|---|
| POST /book/ask | enveloped | enveloped | ✅ |
| GET /book/chapters | enveloped | enveloped | ✅ |
| GET /book/text | direct (пагинация в конверте) | direct | ✅ |
| GET /book/layers | direct | direct | ✅ |
| GET /book/genome | direct | direct | ✅ |
| GET /book/reader/profile | direct | direct | ✅ |
| GET /book/reader/history | enveloped | enveloped | ✅ |
| POST /book/reader/reading-event | direct (ok-only) | direct | ✅ |
| GET /book/reader/reading-progress | direct (stats в конверте) | direct | ✅ |
| GET /book/reader/reading-position | enveloped | enveloped | ✅ |

**unwrap-семантика доказана исполнением** (не декларацией): text возвращает полный конверт (`total=116333` сохранён), progress — `stats` сохранены, reading-event — `{ok:true}`, history — разворачивается в data. Error-форматы: 401/403 — envelope, 422 — pydantic `{detail:[...]}`, 404 — стандартный; все три покрываются ApiError-парсером фронтенда (тесты F1 §errors).

**Genome — can()-gate ОТСУТСТВУЕТ (как требует SPEC §7):** `can()` используется только в F1-примитивах (can.ts/RoleGate), ни один F2-компонент его не вызывает; genome-доступ — прямой apiCall. Live: reader получает 200 (backend-гейт сам решает).

## §4 RBAC — PASS (18/18 live)

- **allowed:** все 5 F2-read-эндпоинтов для reader — 200 (live).
- **forbidden:** reader на editor/admin-эндпоинты (`/book/presence/suggestions`, `/auth/admin/users`, `/book/memory/stats`) — 403 (backend-гейт работает).
- **unauthenticated:** все 5 — 401 + envelope `{ok:false, error:{code:'HTTP_401'}}`.
- **Frontend не расширяет права:** navForRole(reader) = группы book/community/personal, активные пункты только ask/read/profile/status; studio/proposals/admin скрыты. Backend-гейты — единственный источник правды; фронт лишь прячет UI.

## §5 Authentication — PASS (9/9 live/source)

Live-lifecycle: register → 200 `{ok, user.role=reader}` + Set-Cookie `arkaim_session` (**HttpOnly + SameSite=Lax** — проверено) → /me с cookie → 200 `{user}` → /me без → 401 envelope → logout → 200 + delete-cookie-инструкция. Stateless-JWT-особенность (старый cookie валиден до 12ч) — задокументированное backend-свойство (не F2-дефект).

AuthProvider: logout() → apiLogout (POST /auth/logout) → setQueryData(['auth','me'],null) → redirect — код подтверждён.

**B2 (StrictMode):** не browser-tested (см. limitation §11). Доказано source-проверкой (useEffect + ref-guard, render-вызов отсутствует) + unit-семантикой (guard при double-invoke → ровно 1 вызов). Заявление REPORT об этом корректно — он не утверждал browser-тест.

## §6 B1 — WebSocket race — PASS (инвариант доказан экспериментально)

Независимые сценарии (не regression-тест, а живые эксперименты с настоящим WsClient + FakeWS, delayed-callback эмуляция):

| Сценарий | Результат |
|----------|-----------|
| **S1** connect → disconnect → delayed close (1с + backoff-окно 2.5с) | НОВОГО соединения нет; инстансов=1; клиент не подключён ✅ |
| **S2** connect → disconnect → close callback (поздний синхронный) | инстансов=1 (reconnect не случился) ✅ |
| **S3** connect → обрыв → reconnect (инстансов=2) → disconnect → stale close от старого + текущего | после disconnect воскрешений НЕТ (инстансов=2); клиент не подключён ✅ |
| **S4** (доп) disconnect→connect→живой обрыв | reconnect работает (3 инстанса) — фикс не сломал штатное поведение ✅ |

**Инвариант «после намеренного disconnect старое соединение не может инициировать reconnect» — ПОДТВЕРЖДЁН во всех сценариях.**

## §7 React Query / state — PASS

- Query-ключи консистентны между экранами: `['reader','profile']` (/, /profile), `['reader','progress']` + `['reader','position']` (/reading, /profile), `['book','chapters']`, `['book','text',chapterId]`, `['system','health']`.
- Invalidation: ask.onSuccess → invalidate profile (вопросы/темы растут); trackRead.onSuccess → invalidate progress+position («продолжить» обновляется).
- Mutations: ask — без optimistic (синхронный ответ важнее, по SPEC §6), onError → message.error; trackRead — fire-and-forget (SPEC §6 «повтор не критичен»), ошибки не роняют UI.
- staleTime: chapters/text — 5 мин (стабильные данные), profile/history/progress/position — 60с (живые счётчики), health — 30с — соответствует SPEC §9.
- History НЕ инвалидируется после ask — корректно (ask не пишет в conversations — шаг-0-факт).
- Loading/empty/error — везде StateView (/, /reading ×3, /profile ×2, /status).

## §8 Три доменных экрана — PASS

- **`/`** (ask): TextArea+Enter, кнопка disabled при пустом, ответ с SourceBadge (source+confidence+llm_used), провенанс-список, suggestion, «Ваши темы» (profile.topics, клик → подстановка), busy-состояние «Книга думает…». Все SPEC-сценарии присутствуют; mock не используется (только apiCall).
- **`/reading`**: оглавление с char_count и прогресс-барами начатых глав, «Продолжить: глава (на N%)» из reading-position, чтение с догрузкой CHUNK=4000 (индикатор «Загружено N из M»), «Глава прочитана» → completed-трекинг, уход с главы → частичный трекинг. SPEC-сценарии покрыты.
- **`/profile`**: счётчики (вопросы/диалоги/главы начато), «О вас» (display_name, reader_id, last_topic), «Темы (память книги о вас)», «История вопросов» (contracts-контракт; empty-состояние честно объясняет архитектуру), «Чтение»-статистика (started/completed/минуты).
- Все API-вызовы экранов — реальные контракты (§3-таблица); confidence/provenance/source отображаются; история пустых состояний — через StateView.

## §9 /status — PASS

Только F1-контент: health-запрос + WS-бейдж + статические статистики контрактов. Доменных F2-вызовов — 0 (grep ask/chapters/getText/reader = 0). Незаявленной логики нет.

## §10 Realtime — PASS

Fake streaming — нет (EventSource=0). Polling — нет (setInterval=0). WS-использование: только F1-инфраструктура (WsProvider — онлайн-бейдж; useWsEvent доступен, но F2-экраны его не используют — SPEC помечал WS-toast «опционально, не критический путь»). `/v1/stream` не вызывается нигде (0 упоминаний вызовов; ключи провайдеров отсутствуют — контракт бы вернул пустой поток).

## §11 Tests — PASS (с verification limitation)

Независимый пересчёт: **66 passed / 0 failed** (10 файлов). Состав подтверждён по describe-группам: B1-регрессия 3 (внутри WsClient:6), B2 6 (source 3 + StrictMode-семантика 3), доменные book 10 + reader 7 + source-badge 7, nav-F2 2 (внутри navigation:5), contracts — автопроверка новых ENVELOPE_MAP-ключей.

**VERIFICATION LIMITATION (зафиксирована, не скрыта):** browser-E2E (Playwright) в этой среде не запускается: spawn EPERM на worker'ах раннера и на chrome.exe — то же средовое ограничение, что документировано со времён F1 (воспроизводится и на legacy-проекте). **HTTP-E2E не эквивалент browser-E2E** — он проверяет маршруты/структуру, но не интерактив; интерактив здесь покрыт live-API (12/12) и unit-семантикой. Browser-спека (`tests/e2e/foundation.spec.ts`, 6 тестов) — в репо и работоспособна в средах без sandbox-ограничений (CI).

## §12 Build — PASS (независимый повторный прогон)

lint **exit 0** (0/0) · tsc strict **exit 0** (0) · unit **66/0** · contracts:verify **OK×2** · production build **exit 0** (8 маршрутов: /, /_not-found, /login, /no-access, /profile, /reading, /register, /status — все static).

## §13 Runtime — PASS (независимый live-smoke)

Критический путь — 12/12: register→cookie, ask→answer+source (Pulse, без LLM-ключей), profile после ask (total=1, topic), 17 глав, text-пагинация (total=116333), reading-event ok, position (40%), genome/layers 200-reader, 401-envelope, 422.

Негативные (доп. проверка): 422 → pydantic `{detail:[{msg:"String should have at least 3 characters"}]}`; 403 → envelope `HTTP_403`; 404 → 404. Все форматы обрабатываются ApiError-моделью.

## §14 Documentation consistency — PASS (одно заявление скорректировано)

SPEC ↔ PLAN ↔ REPORT ↔ код: сверены все ключевые заявления REPORT — **66 unit** (✓ §11), **12/12 live** (✓ §13), **8/8 HTTP-E2E** (✓ независимо воспроизведено с production-сервером), **33 новых теста** (✓ 66−33), **8 маршрутов** (✓ §12), **0 backend-изменений** (✓ §1).

Одно уточнение: REPORT «20 файлов, ~1200 строк» — фактически F2-извод 42 файла в src/+tests/ (включая тесты/скрипты); production-изменение — ~14 файлов. Неточность подсчёта, не искажает суть.

SPEC-правки шага 0 (history/reading-progress/reading-position/live-конверты) — легальны (документация живых фактов до кода, шаг 0 плана).

---

## FINDINGS (все non-blocking)

| # | Severity | Файл/строки | Доказательство | Влияние | BLOCKS F3 |
|---|----------|-------------|----------------|--------|-----------|
| F2-A1 | Low (informational) | `reading/page.tsx:113-126` (backToList) | scroll_percent = процент ЗАГРУЖЕННОГО текста, не фактический скролл пользователя | Метрика прогресса приближённая; backend-контракт допускает; «Продолжить (на N%)» может показывать объём загрузки | NO |
| F2-A2 | Low | `page.tsx` (/ask): кнопка disabled только при пустом вопросе | Live: вопрос 1–2 симв. → 422 pydantic (min_length 3) | Пользователь увидит честную ошибку валидации (обрабатывается ApiError); UX можно улучшить фрон-проверкой длины | NO |
| F2-A3 | Cosmetic | 422-сообщение backend pydantic — английское («String should have at least 3 characters») | §13-проба | Сообщение об ошибке не локализовано; это backend-текст за красной линией (менять backend нельзя) | NO |
| F2-A4 | Verification limitation (среда, не проект) | `tests/e2e/foundation.spec.ts` | Playwright spawn EPERM в sandbox (worker+chrome); HTTP-E2E ≠ browser-E2E | Browser-E2E не выполнен в этой среде; в CI выполним | NO |

Findings из F1 (WS-race, login-effect) — закрыты в F2 (B1/B2, доказано §6/§5). Backlog-остаток: openapi-fetch unused (Low) и 5 RBAC-коллизий (Low) — вне F2-scope, не тронуты (правильно).

---

## Сводная таблица

| § | Область | Вердикт |
|---|---------|---------|
| 1 | Git boundary | PASS (0 backend/legacy/M10-изменений, mtime+content-доказательства) |
| 2 | F2 scope | PASS (запрещённое отсутствует, красные линии целы) |
| 3 | API contracts | PASS (10/10 конвертов live + unwrap-семантика + genome без gate) |
| 4 | RBAC | PASS (18/18 live; фронт не расширяет права) |
| 5 | Auth | PASS (9/9; B2 source+unit, не browser) |
| 6 | B1 WS-race | PASS (инвариант доказан S1–S4 экспериментально) |
| 7 | React Query | PASS (ключи/invalidation/staleTime по SPEC) |
| 8 | Три экрана | PASS (все SPEC-сценарии, реальные API) |
| 9 | /status | PASS (чистый F1-перенос) |
| 10 | Realtime | PASS (нет fake/polling; /v1 не используется) |
| 11 | Tests | PASS 66/0 + зафиксированная browser-limitation |
| 12 | Build | PASS (lint 0/0, tsc 0, verify OK×2, build 8 маршрутов) |
| 13 | Runtime | PASS (12/12 критический путь + 403/404/422) |
| 14 | Docs consistency | PASS (заявления подтверждены; подсчёт файлов уточнён) |

## Вердикт

**F2 — PASS WITH FINDINGS**: полнота соответствия SPEC доказана; 4 non-blocking findings (2 Low, 1 Cosmetic, 1 среда-ограничение проверки); BLOCKS F3 — NO по всем.

Аудит read-only: production-код не изменён; backend/M10/M10.2/legacy не тронуты; F3 не начат. Останавливаюсь.
