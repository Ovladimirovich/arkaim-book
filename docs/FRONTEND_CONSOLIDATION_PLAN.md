<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL — НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Документ описывает период до консолидации. Единственный текущий frontend — `arkaim-web`; бывший v2 удалён. Сравнения, решения D1–D9, шаги переноса и удаления отменены. Актуальный статус: `docs/CURRENT_DEVELOPMENT_STATE.md` и `docs/DOCUMENTATION_INDEX.md`.

# FRONTEND_CONSOLIDATION_PLAN.md — план сведения двух frontend-направлений Arkaim к одному

**Тип документа:** read-only аудит + план консолидации (реализация НЕ начата).
**Дата аудита:** 2026-09-30.
**HEAD репозитория (на момент аудита):** `8aef0f98f217e742de86856a8076b6ec74c6c59e` (branch `master`).
**Метод:** чтение реальных файлов, конфигов, launch-скриптов, Docker/Make, git-индекса. Наличие документа НЕ считалось доказательством работы; каждый существенный факт снабжён источником (файл/git-команда).
**Ограничения:** ничего не изменялось, не удалялось, не переносилось. Код не трогался.

---

## Простыми словами (для владельца)

1. **Что было целью?** — Не угадывать, какой из двух фронтендов «главный», а по фактам определить, как оставить один и убрать лишнее.

2. **Что реально сделано?** — Проверены оба каталога, их страницы, конфиги, запуск, Docker, Make, git-статус и связанные документы. Собран точный фактический срез.

3. **Что получилось?** — **PARTIAL (аудит завершён, решение за вами).** Аудит дал однозначную картину, но её нужно утвердить: по коду и запуску единый рабочий фронтенд — `arkaim-web` (порт 3000), как и записано в вашем же плане трансформации. При этом обнаружено серьезное расхождение: **в git закоммичен `arkaim-web-v2`, а рабочий `arkaim-web` — нет (он лежит на диске как «untracked»).**

4. **Есть ли проблемы?** — Да, одна существенная: версионирование фронтендов «перевёрнуто». Рабочий фронтенд (`arkaim-web`) не находится под git, а справочный (`arkaim-web-v2`) — находится. Пока это не исправлено, любой сбой диска может стоить рабочего фронтенда. Серьёзность: **высокая** (риск потери данных, не ошибка логики).

5. **Что предлагается дальше?** — Утвердить целевым `arkaim-web` (порт 3000), поставить его под git, перенести оставшиеся уникальные функции `v2`, затем по отдельному решению вывести `v2` в архив. Ничего не делаю до вашего OWNER-GO.

---

## 1. FACTUAL STATE

### 1.1. `arkaim-web` (далее «v1» / :3000)

| Параметр | Факт | Источник |
|---|---|---|
| Стек | Next.js `16.2.10`, React `19.2.4`, AntD `6.5.0`, TanStack Query 5, react-hook-form, zod | `arkaim-web/package.json` |
| Скрипты | `dev`(turbo), `build`, `start`, `lint`; порт по умолчанию 3000 | `arkaim-web/package.json` |
| Dev-порт | **3000** | `Makefile` («frontend на :3000»), `start_all.bat`, `runtime/run-all.ps1`, `docker-compose.yml` |
| Маршрутизация | App Router, «плоские» каталоги `src/app/<route>/page.tsx`; корень → `redirect('/book')` | `arkaim-web/src/app/page.tsx`, листинг `src/app/` |
| Объём страниц | ~40 каталогов-маршрутов (см. §2) | листинг `arkaim-web/src/app/` |
| Архитектура | FSD-подобная (`app/ widgets/ entities*/ shared/`), плюс `shared/lib`, `shared/ui/light/*` | листинг `src/` |
| Реальный запуск | **Да** — только он поднимается любым из launcher-скриптов | `start_all.bat`, `runtime/run-all.ps1` |
| Docker | `Dockerfile.frontend` собирает именно `arkaim-web`, `docker compose` поднимает его на 3000 | `Dockerfile.frontend`, `docker-compose.yml` |
| PWA | Есть: `public/sw.js`, `public/offline.html`, `shared/ui/ServiceWorkerRegister.tsx` | листинг `arkaim-web/public`, `arkaim-web/src/shared/ui/` |
| API-слой | Типизированный: `shared/api/client.ts`, `envelope.ts`, `errors.ts`, `index.ts`, `contracts/*` + `generated/schema.d.ts`; **плюс** legacy-клиент `shared/lib/api.ts` с mock-fallback при 401/5xx в dev | листинг `src/shared/api/`, чтение `shared/lib/api.ts` |
| Auth/session | `Providers` → `AuthProvider`: cookie `arkaim_session` + `/auth/me` + dev-login, кэш в `localStorage['arkaim_user']`, метод `establish(user)` | `src/app/providers.tsx` |
| Роль/RBAC | Только guard `ProtectedRoute`; RBAC-матрицы нет | `src/shared/lib/guards.tsx`, отсутствует `shared/rbac/` |
| Realtime | WS-провайдер (`shared/lib/ws-hooks`), SSE-консьюмер (`shared/realtime/sse`) | `src/app/providers.tsx`, `src/app/ask/page.tsx`, `tests/unit/sse.test.ts` |
| Git-статус | **НЕ отслеживается** (untracked целиком) | `git ls-files arkaim-web` → 0; `git status` → `?? arkaim-web/`; `git ls-tree -r HEAD` → 0 файлов |

**Ключевой факт по v1 (git):** в истории (ветки/прошлые коммиты, напр. `fresh-start 48c19c9`, `7a19386`) каталог присутствовал, но **на текущем HEAD `master` он не закоммичен** — на диске он есть, в индексе git его нет.

### 1.2. `arkaim-web-v2` (далее «v2» / :3001)

| Параметр | Факт | Источник |
|---|---|---|
| Стек | Next.js `16.2.10`, React `19.2.4`, AntD `6.5.0`, TanStack Query 5, **openapi-fetch + openapi-typescript**, zod | `arkaim-web-v2/package.json` |
| Скрипты | `dev --port 3001`, `start -p 3001`, `typecheck`, `test`, `test:local`, `contracts:fetch/generate/verify`, `e2e` | `arkaim-web-v2/package.json` |
| Dev-порт | **3001** | `arkaim-web-v2/package.json`; `docs/CURRENT_DEVELOPMENT_STATE.md` §29 |
| Маршрутизация | App Router с группами `(auth)` и `(main)`; `not-found.tsx` | листинг `arkaim-web-v2/src/app/` |
| Объём страниц | ~22 каталога-маршрута (см. §2) | листинг `src/app/` |
| Архитектура | Чистая FSD: `app/ widgets/ entities/ shared/{api,rbac,realtime,reading,ui}` | листинг `src/` |
| Реальный запуск | **Нет** — ни один launcher/Docker/Make его не запускает; запускается только вручную (`npm run dev`) | `start_all.bat`, `Dockerfile.frontend`, `Makefile` (ссылаются только на `arkaim-web`) |
| Docker | Не собирается Dockerfile.frontend | `Dockerfile.frontend` |
| PWA | Нет (нет `sw.js`/`offline.html`/ServiceWorkerRegister) | листинг `src/`, `arkaim-web-v2/` |
| API-слой | OpenAPI-first: `generated/schema.d.ts`, `client.ts` (cookie+bearer, retry), `envelope.ts` (ENVELOPE_MAP), `errors.ts`, `contracts/*` | чтение `src/shared/api/client.ts`, листинг `src/shared/api/` |
| Auth/session | `entities/auth/AuthProvider.tsx` на TanStack Query `/auth/me`; **401 никогда не мокается**; dev-вход только при `NEXT_PUBLIC_DEV_AUTH=1`; `establish(user)` | чтение `src/entities/auth/AuthProvider.tsx`, `.env.local` |
| Роль/RBAC | **Полноценная матрица**: `shared/rbac/navigation.ts` (`navForRole`), `can.ts`, `RoleGate.tsx`, `rbac/generated/` | чтение `src/shared/rbac/navigation.ts`, листинг `src/shared/rbac/` |
| Realtime | WS-client + WsProvider + WsToast + SSE (`sse.ts`) + xray SSE (`xray-sse.ts`) | листинг `src/shared/realtime/` |
| Уникальные UI | `ProvenanceBadge`, `SourceBadge`, `StateView`, `ReadingTopbar`, `ChapterReader` | листинг `src/shared/ui/`, `src/entities/reader/`, `src/widgets/reading/` |
| Тесты | 33 unit + 4 e2e (F1–F6) | листинг `arkaim-web-v2/tests/` |
| Git-статус | **Отслеживается** (152 файла на HEAD), активно правится в рабочем дереве | `git ls-tree -r HEAD` → 152; `git status --short` → ` M arkaim-web-v2/...` |

### 1.3. Сводка расхождения (главный вывод раздела)

- **Операционно рабочий фронтенд — `arkaim-web` (:3000).** Именно он запускается скриптами, Docker и Make, содержит PWA и уже впитал ключевые функции v2 (типизированные контракты, `establish`, персистентность диалога, `EntityCard`, history, World→Temporal).
- **`arkaim-web-v2` (:3001) — справочный.** Он старше, полнее по API-контрактам/RBAC и закоммичен, но нигде не запускается как продукт.
- **Инверсия версионирования:** рабочий `arkaim-web` — вне git, справочный `arkaim-web-v2` — в git. Это противоречит и цели консолидации, и здравому смыслу: под контролем версий сейчас «не тот» фронтенд.
- **План владельца уже существует:** `docs/FRONTEND_TRANSFORMATION_PLAN.md` декларирует целевым `arkaim-web` (:3000), а `arkaim-web-v2` — временным референсом, и отмечает 7 этапов как **VERIFIED (27–29.09.2026)**. Код v1 это подтверждает (контракты, `establish`, ask-персистентность, EntityCard, history, deep-links World→Temporal).

---

## 2. FUNCTIONAL COMPARISON

Сравнение по фактическим маршрутам/файлам. Без рейтингов и оценок.

### 2.1. Маршруты (route → где есть)

| Маршрут/зона | `arkaim-web` (v1, :3000) | `arkaim-web-v2` (v2, :3001) | Примечание |
|---|---|---|---|
| ask (вопрос книге) | ✔ `app/ask` | ✔ `(main)/ask` | v1 — с SSE, EntityCard, «Ваши темы»-профилем, session в URL |
| reading / read | ✔ `app/reading` | ✔ `(main)/reading` (+ `entities/reader/ChapterReader`) | Оба |
| book (диалог) | ✔ `app/book` | — (чат помечен coming-soon) | v1 — есть |
| history | ✔ `app/history` | ✔ `(main)/history` | Оба, оба на реальной ReaderMemory |
| world-engine | ✔ `app/world-engine` | ✔ `(main)/world` | Разные имена маршрута |
| temporal | ✔ `app/temporal` | ✔ `(main)/temporal` (+ `(main)/temporal/queue`?) | Область v2 шире (queue в IA) |
| world-explorer | ✔ `app/world-explorer` | ✔ `(main)/world-explorer` | Оба |
| library/genome | ✔ `app/library` | ✔ `(main)/library` | Оба |
| graph | — | ✔ `(main)/graph` | **Только v2** (в v1 граф не отдельной страницей) |
| analytics | ✔ `app/analytics` | ✔ `(main)/analytics` | Оба |
| profile | ✔ `app/profile` | ✔ `(main)/profile` | Оба |
| admin | ✔ `app/admin` | ✔ `(main)/admin` (+ `admin/moderation`) | v2 шире (moderation) |
| xray | ✔ `app/xray` | ✔ `(main)/xray` | Оба (SSE) |
| community | ✔ `interpretations`, `artifacts`, `notifications` | ✔ `(main)/community` | Разная декомпозиция |
| proposals/presence/email | — (в IA нет отдельной зоны) | ✔ `(main)/proposals` | **Только v2** как отдельная зона (в v1 функции разнесены/частично) |
| studio/assets/film/upload/story | ✔ `assets`, `film-studio`, `upload`, `story` | ✔ `(main)/studio`, `(main)/upload` | Оба, v1 дробит иначе |
| map | ✔ `app/map` | — | **Только v1** |
| crowdfunding | ✔ `app/crowdfunding` | — | **Только v1** |
| screenplay | ✔ `app/screenplay` | — | **Только v1** |
| genres | ✔ `app/genres` | — | **Только v1** |
| visual / visual-view | ✔ `app/visual`, `app/visual-view` | — | **Только v1** |
| search | ✔ `app/search` | — (в IA coming-soon) | Только v1 как страница |
| recommendations | ✔ `app/recommendations` | — | **Только v1** |
| editor / api | ✔ `app/editor`, `app/api` | — | **Только v1** |
| help | ✔ `app/help` | ✔ `(main)/help` | Оба |
| status | — | ✔ `(main)/status` | **Только v2** |
| login/register | ✔ `login`, `register` | ✔ `(auth)/login`, `(auth)/register` | Оба |
| no-access | — | ✔ `(main)/no-access` | **Только v2** |
| about | ✔ `app/about` | — | **Только v1** |

### 2.2. Слои и инфраструктура

| Возможность | v1 | v2 | Комментарий |
|---|---|---|---|
| Типизированные контракты (`contracts/*`) | ✔ | ✔ | Оба; v2 — с OpenAPI-генерацией |
| `client.ts` (cookie+bearer, retry, ApiError) | ✔ | ✔ | Оба |
| `envelope.ts` (unwrap `{ok,data}`) | ✔ | ✔ | Оба |
| `errors.ts` | ✔ | ✔ | Оба |
| OpenAPI-схема (`generated/schema.d.ts`) | ✔ | ✔ | Оба |
| OpenAPI-скрипты (`contracts:*`) | — | ✔ | **Только v2** |
| RBAC-матрица (`can`, `navForRole`, `RoleGate`) | — | ✔ | **Только v2** |
| Route guard (`ProtectedRoute`) | ✔ | (через layout+role) | v1 — guard-компонент |
| AuthProvider (`establish`, без моков на 401) | ✔ (v1 мокает при отсутствии cookie → dev-user) | ✔ (строго без моков) | Ключевое различие в поведении |
| Mock-fallback в API-клиенте | ✔ (`shared/lib/api.ts`, только dev) | ✘ (запрещено красной линией) | Риск: в v1 dev-моки питают UI |
| Realtime WS + WsToast | ✔ (Ws-хуки) | ✔ (WsProvider+WsToast) | Оба |
| SSE (chat) + xray SSE | ✔ (ask, xray) | ✔ (`sse.ts`, `xray-sse.ts`) | Оба |
| PWA (sw/offline) | ✔ | — | **Только v1** |
| `GenerationSettingsPanel`+Context | ✔ | — | **Только v1** |
| `NotificationBell` | ✔ | — | **Только v1** |
| `ProvenanceBadge` | — | ✔ | **Только v2** |
| `StateView` (loading/empty/error) | — (частично inline) | ✔ | **Только v2** |
| Reading-entities (`ChapterReader`, `useReadingSettings`) | — | ✔ | **Только v2** |
| Theme (light/dark) | ✔ | (AntD default) | v1 — переключатель темы |

---

## 3. TARGET

**Предлагаемый единый target: `arkaim-web` (порт 3000).**

Обоснование — по фактам, а не по названию:
1. **Операционный статус.** Только `arkaim-web` реально поднимается всеми launcher-скриптами (`start_all.bat`, `runtime/run-all.ps1`), `Makefile` и Docker (`Dockerfile.frontend`, `docker-compose.yml`). Это «фактическая точка входа».
2. **Совпадение с решением владельца.** `docs/FRONTEND_TRANSFORMATION_PLAN.md` прямо фиксирует: единственный рабочий фронтенд — `arkaim-web` на :3000; `arkaim-web-v2` — временный референс.
3. **v1 уже впитал ядро v2.** Типизированные контракты + `client/envelope/errors`, `establish(user)`, персистентность `session_id` (`localStorage['arkaim_session_id']` + URL + ReaderMemory), `EntityCard` в ответе, `/history` на реальных данных, deep-link World→Temporal — всё читается в коде v1.
4. **v1 владеет тем, чего нет в v2** и что «нельзя потерять»: PWA (`sw.js`/`offline.html`/ServiceWorkerRegister), `GenerationSettingsPanel`, `NotificationBell`, map, crowdfunding, screenplay, genres, visual/visual-view, recommendations, editor, api.

**Почему не `arkaim-web-v2`:** он не запускается как продукт, нет PWA и ряда авторских экранов/компонентов v1, и его консолидация «в обратную сторону» означала бы перенос всего UX v1 в v2 — более дорогой путь, противоречащий уже утверждённому плану владельца.

**Оговорка (важно):** выбор target не означает, что v1 сейчас «правильнее по коду» — по строгости контрактов и RBAC **v2 полнее**. Но роль (продукт vs референс) и фактический запуск делают единым направлением именно v1, с переносом недостающих частей из v2.

> **Одновременно два frontend нельзя считать двумя истинами.** После утверждения плана проект должен перейти к одному направлению разработки. До переноса — v2 читать только как источник деталей, не развивать его как продукт.

---

## 4. MIGRATION / CLEANUP PLAN

Пошагово. Ни один шаг не выполняется без OWNER-GO. На каждом шаге фронтенд обязан оставаться собираемым и рабочим.

### Шаг 0 — Зафиксировать целевое решение и поставить v1 под git (приоритет №1: безопасность)
- **Что:** закоммитить `arkaim-web/` в git (сейчас untracked), исключив `node_modules`, `.next`, `*.tsbuildinfo`, `.env*`.
- **Зачем:** рабочий фронтенд сейчас вне версионирования — риск потери.
- **Проверить:** `git status` показывает `arkaim-web/` как tracked; сборка/линт не затронуты.
- **Stop 0:** подтверждение, что v1 под git и не потерян.

### Шаг 1 — Инвентаризация «что уже есть в v1 из v2» (read-only)
- **Что:** пройти по §2 и пометить для каждого пункта v2: «есть в v1 / нет в v1».
- **Проверить:** список gaps (ожидаемо: RBAC-матрица, `ProvenanceBadge`, `StateView`, reading-entities, `xray-sse`, `contracts:*`-скрипты, отдельные страницы `/graph`, `/status`, `/no-access`, `/proposals`, `/admin/moderation`, `/studio`).
- **Результат:** точная таблица переноса.

### Шаг 2 — Перенести уникальные «нельзя потерять» части v2 в v1
- **Что сохранить из v2 (перенос в v1):**
  - RBAC-слой: `shared/rbac/can.ts`, `navigation.ts`, `RoleGate.tsx`, `rbac/generated/` → в `arkaim-web/src/shared/`.
  - `shared/ui/StateView.tsx`, `shared/ui/ProvenanceBadge.tsx` (SourceBadge в v1 уже есть — сверить и объединить).
  - Reading: `entities/reader/*`, `widgets/reading/*` — сверить с существующей `app/reading`.
  - Realtime: `xray-sse.ts` (если xray-SSE в v1 отличается), сверить `ws-client`/`WsToast`.
  - Скрипты контрактов `scripts/contracts.mjs`, `fetch-contract.mjs` и `contracts:verify` — при необходимости.
  - Страницы, которых нет в v1 и которые не дублируют авторский UX: `graph`, `status`, `no-access`, `proposals`, `admin/moderation`, `studio` — **либо** перенести, **либо** явно признать необязательными (решение владельца).
- **Что переносить НЕЛЬЗЯ механически:** модели сессии (у v1 `localStorage['arkaim_user']`; не тащить чужой контракт), envelope-специфику — сверять.
- **Проверить:** `npm run lint`, `npx tsc --noEmit`, `npx vitest run` в `arkaim-web`.
- **Stop 1:** сборка и тесты v1 зелёные.

### Шаг 3 — Убрать «двойную правду» в API-слое v1
- **Что:** в `arkaim-web/src/shared/lib/api.ts` dev-моки при 401/5xx не должны маскировать реальные ошибки критического маршрута (правило из `FRONTEND_TRANSFORMATION_PLAN` §Этап 5: история читателя — не заглушка). Свести legacy `api.get/post` и типизированный клиент к одному источнику.
- **Проверить:** критический маршрут (ask → entity → world → temporal → history) не показывает фиктивных данных; ошибки показываются явно.
- **Stop 2:** ручная браузерная проверка критического маршрута.

### Шаг 4 — Выровнять авторизацию
- **Что:** v1 `providers.tsx` при отсутствии cookie уходит в dev-user. Привести поведение к согласованному с v2: dev-вход только по явному флагу, 401 → экран входа (без авто-мока), сохранив `establish` и `localStorage`.
- **Проверить:** F5 на защищённом маршруте сохраняет сессию; без cookie — понятный экран входа.
- **Stop 3:** проверка сессии.

### Шаг 5 — Сквозная проверка и приёмка v1
- **Что:** пройти сценарий Ask → Answer → Entity → World → Temporal → History; проверить PWA (оффлайн-страница), светлую/тёмную тему, RBAC-видимость по ролям.
- **Проверить:** unit/e2e v1 + ручной прогон; порт 3000.
- **Stop 4 (финальный):** полный маршрут PASS.

### Шаг 6 — Судьба v2 (архив)
- **Что:** после приёмки v1 переместить `arkaim-web-v2` в `docs/archive/arkaim-web-v2-reference/` (согласно `FRONTEND_TRANSFORMATION_PLAN` §6), затем — только после отдельного решения — удалить.
- **Что удалять пока нельзя:** сам `arkaim-web-v2` до приёмки v1 и явного OWNER-GO; любые части v2, не подтверждённые как перенесённые.

### Порядок-резюме
Сохранить v1 → перенести уникальные части v2 → заменить/убрать двойную правду в API-слое → проверить → затем архивировать/удалить v2.

---

## 5. RISKS

| # | Риск | Что именно | Серьёзность | Митигация |
|---|---|---|---|---|
| R1 | **Потеря v1 при сбое** | `arkaim-web` вне git (untracked), а закоммичен только v2 | Высокая | Шаг 0: закоммитить `arkaim-web` до любых действий |
| R2 | Потеря авторского UX | PWA, GenerationSettingsPanel, NotificationBell, map, crowdfunding, screenplay, genres, visual-view есть только в v1 | Высокая | Ничего не удалять из v1; переносы — только «в v1» |
| R3 | Потеря строгих контрактов | RBAC-матрица, `ProvenanceBadge`, `StateView`, reading-entities, `contracts:*` есть только в v2 | Средняя | Шаг 2: явная таблица переноса, подтверждение по файлам |
| R4 | Двойная «правда» данных | v1 dev-моки при 401/5xx могут скрывать реальные ошибки на критическом маршруте | Средняя | Шаг 3: убрать мок-фолбэк на критических путях |
| R5 | Рассинхрон сессии | Разные модели: v1 `localStorage['arkaim_user']` + авто-мок; v2 — строгий `/auth/me` без моков | Средняя | Шаг 4: единый контракт сессии |
| R6 | Скрытые зависимости v2 | `arkaim-web-v2/runtime/arkaim.db`, `contracts/`, `scripts/` | Низкая | Шаг 6: архивировать целиком, не выборочно |
| R7 | Ложная уверенность по документам | План владельца помечен «VERIFIED», но v1 вне git; свежесть кода могла измениться | Средняя | Сверять факты по коду на момент реализации (Шаг 1) |
| R8 | Порты/запуск | v2 на 3001 нигде не запускается; при удалении ничего в запуске не ломается | Низкая | Проверить `start_all.bat`/`run-all.ps1` (уже указывают только на v1) |
| R9 | Тесты | 33 unit + 4 e2e v2 исчезнут вместе с v2, если их не перенести | Средняя | Решить, какие тесты критичны, перенести в Шаг 2 |

---

## 6. ACCEPTANCE CHECKS

Как доказать, что после консолидации оставшийся фронтенд (v1) покрывает текущие сценарии:

1. **Сборка/линт/типы:** `cd arkaim-web && npm run lint && npx tsc --noEmit && npm run build` — без ошибок.
2. **Тесты:** `cd arkaim-web && npx vitest run` — зелёные; перенесённые e2e (Playwright) — зелёные.
3. **Сквозной маршрут (ручной, браузер, :3000):** Ask (вопрос, стриминг, Markdown, EntityCard) → World (`?entity_id=`) → Temporal (`?entity=`) → History (реальные сессии, F5 сохраняет).
4. **Персистентность:** F5 на `/ask?session_id=...` восстанавливает диалог; сессия авторизации не сбрасывается.
5. **RBAC:** навигация/действия скрываются по ролям reader/editor/admin; доступ к запрещённому маршруту → `no-access`-эквивалент.
6. **Нет mock-подмены на критическом пути:** при недоступном backend история/ответы показывают ошибку, а не фиктивный диалог.
7. **PWA:** `sw.js` регистрируется, оффлайн-страница открывается; отсутствие устаревшего API-кэша после перезагрузки.
8. **Запуск:** `start_all.bat` поднимает :8642 и :3000; порт 3001 свободен.
9. **Покрытие функций:** таблица §2.1/§2.2 не имеет «дыр» — каждая функция либо есть в v1, либо явно признана необязательной владельцем.

Критерий PASS: все пункты 1–9 выполнены, каждая функция из §2 либо присутствует в v1, либо решением владельца исключена.

---

## 7. DELETION BOUNDARY

**Точный список того, что потенциально можно будет удалить из второго направления (`arkaim-web-v2`), и что сначала должно быть подтверждено.**

### 7.1. Что потенциально удаляется (только после приёмки v1 и OWNER-GO)
- Весь каталог `arkaim-web-v2/` целиком, включая:
  - `src/app/` (`(auth)/*`, `(main)/*`, `layout.tsx`, `not-found.tsx`, `providers.tsx`, `globals.css`);
  - `src/widgets/`, `src/entities/`, `src/shared/` (после переноса уникального);
  - `tests/` (unit + e2e) — **если** критичные тесты не перенесены в v1;
  - `scripts/` (контракты), `contracts/` (json-дампы);
  - `package.json`, `package-lock.json`, `next.config.ts`, `tsconfig.json`, `vitest.config.mjs`, `playwright.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`;
  - `runtime/arkaim.db` (артефакт), логи `dev_*.txt`, `dev_server*.log`, `frontend.log`.

### 7.2. Что должно быть подтверждено ДО удаления
1. `arkaim-web` **закоммичен** в git (Шаг 0) и проходит сборку/тесты.
2. Перенесены (или явно признаны необязательными) все уникальные функции v2 из §2: RBAC (`shared/rbac/*`), `StateView`, `ProvenanceBadge`, reading-entities, `xray-sse`, `contracts:*`-скрипты, страницы `graph/status/no-access/proposals/admin-moderation/studio`.
3. Перенесены критичные тесты v2 (иначе удаление тестов = потеря защиты).
4. Проверено, что ни launcher/Docker/Make не ссылаются на `arkaim-web-v2` (сейчас — не ссылаются).
5. Проверено, что API-слой v1 не зависит от `envelope`/контрактов, специфичных только для v2.
6. Получен явный OWNER-GO на архивацию/удаление (`FRONTEND_TRANSFORMATION_PLAN` §6).

### 7.3. Что удалять нельзя
- `arkaim-web` (целевой продукт) — не удалять.
- `arkaim-web-v2` — не удалять **до** выполнения 7.2.
- Любые компоненты v1 (PWA, GenerationSettingsPanel, NotificationBell и пр.) — не удалять.

---

## 8. OWNER DECISIONS

Решения, которые должен принять OWNER до начала реализации:

| # | Решение | Варианты | Что зависит |
|---|---|---|---|
| D1 | **Целевой фронтенд** | (a) `arkaim-web` :3000 (рекомендуется по фактам) / (b) `arkaim-web-v2` :3001 | Весь план |
| D2 | **Закоммитить `arkaim-web` под git** | да/нет | Безопасность (R1) — приоритет |
| D3 | **Судьба v2** | архив / удалить / оставить как есть | Размер §7 |
| D4 | **Уникальные функции v2** | перенести все / часть / признать необязательными | Объём Шага 2 |
| D5 | **Страницы, которых нет в v1** (`graph`, `status`, `proposals`, `admin/moderation`, `studio`, `no-access`) | нужны/не нужны | Объём переноса |
| D6 | **Тесты v2** | перенести критичные / не переносить | Защита от регрессий |
| D7 | **Поведение авторизации в v1** (dev-user автоматом) | оставить / привести к строгому (без моков) | Шаг 4 |
| D8 | **Мок-фолбэк в v1 `shared/lib/api.ts`** | оставить в dev / убрать на критических путях | Шаг 3 |
| D9 | **Формат остановки** | Stop 0–4 по каждому шагу | Контроль |

**Дополнительно (обязательное условие):** `arkaim-web` и `arkaim-web-v2` нельзя одновременно считать двумя «истинами». После утверждения этого плана проект переходит к одному направлению разработки — `arkaim-web`. До завершения переноса `arkaim-web-v2` рассматривается исключительно как справочник деталей, не как развиваемый продукт.

---

## Итоговая сводка

- **Статус аудита:** AUDITED / PARTIAL — фактический срез собран, реализация не начиналась.
- **Краткий вывод:** операционно рабочий фронтенд — `arkaim-web` (:3000), он же целевой по плану владельца; `arkaim-web-v2` (:3001) — справочный и закоммичен, тогда как рабочий v1 — вне git. Направления нужно свести к одному, устранив инверсию версионирования.
- **Главный предложенный target:** `arkaim-web` (порт 3000).
- **Основные риски:** R1 (v1 вне git — риск потери), R2 (уникальный UX/PWA только в v1), R3 (RBAC/контракты/тесты только в v2).
- **Ближайшая конкретная задача:** OWNER-решение D1–D2, затем Шаг 0 — постановка `arkaim-web` под git. Только после этого — Шаг 1 (инвентаризация gaps).
- **Дальнейшее направление:** перенос уникальных частей v2 → выравнивание API/сессии → приёмка v1 по §6 → архивация v2 по §7.

---

*Аудит выполнен без изменений кода. Ожидается OWNER-GO. До получения OWNER-GO реализация не начинается и `arkaim-web-v2` не изменяется/не архивируется.*