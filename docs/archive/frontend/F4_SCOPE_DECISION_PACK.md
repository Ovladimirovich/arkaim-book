# F4 SCOPE DECISION PACK

**Дата:** 2026-09-18
**Режим:** Read-only (ноль изменений в коде)
**Основание:** `docs/F4_PRE_IMPLEMENTATION_AUDIT.md` (2026-09-18), `docs/F4_SPEC.md` (2026-09-18)
**Статус:** ✅ DECISIONS ACCEPTED — GO RECEIVED 2026-09-18 · F4 IMPLEMENTED & ACCEPTED & CLOSED

---

## OWNER DECISIONS (ACCEPTED 2026-09-18)

| Решение | Вариант | Итог |
|---------|---------|------|
| **D-F4-1** | 1A | Ask / Graph / World-explorer → F2 (не раздувать F4 чужим WIP) |
| **D-F4-2** | 2A | Upload → F3 (часть /studio/upload функциональности) |
| **D-F4-3** | 3B | `/admin` → F5 целиком; F4 получает отдельный `/admin/moderation` |
| **D-F4-4** | 4B | Analytics → отдельный milestone (не затаскивать в F4) |
| **D-F4-5** | 5A | **Clean F4** = community fix + proposal capabilities (presence/email/drafts/moderation), при этом `/proposals/temporal` НЕ реализовывать повторно (уже в F3 как `/temporal/queue`) |

**Принцип:** F4 не должен становиться контейнером для случайно оказавшегося на диске frontend-кода.

---

## 1. Executive Summary

### 1.1 Суть проблемы

В проекте Arkaim v2 существует расхождение между **формальной архитектурой F4** (документировано в `FRONTEND_ARCHITECTURE.md`) и **фактическим WIP-кодом** на диске. Формальная F4 определяет 4 proposal-path'а (`/proposals/temporal`, `/proposals/presence`, `/proposals/email`, `/proposals/drafts`) + `/community` + `/admin/moderation`. Фактический WIP содержит 7 страниц, из которых только 2 (`community`, `world-explorer`) имеют явное соответствие в Architecture; остальные 5 — либо уже реализованы в других фазах, либо не имеют документального основания.

### 1.2 Что установлено

| Факт | Статус |
|------|--------|
| Backend имеет все необходимые API-эндпоинты | ✅ Подтверждено (OpenAPI 289 путей) |
| `/proposals/temporal` реализован в F3 как `/temporal/queue` | ✅ Подтверждено (F3-код существует) |
| `/proposals/presence` — backend существует, frontend отсутствует | ✅ Подтверждено (`/book/presence/suggestions`) |
| `/proposals/email` — backend существует, frontend отсутствует | ✅ Подтверждено (`/book/email/*`, `/book/drafts`) |
| `/proposals/drafts` — backend существует, frontend отсутствует | ✅ Подтверждено (`/book/drafts/{id}/approve`) |
| `/community` — frontend WIP существует (с BLOCKER) | ⚠️Broken JSX |
| `/admin` — frontend WIP существует (не `/admin/moderation`) | ⚠️ Scope mismatch |
| Формальные proposal-страницы НЕ существуют | ❌ Нет кода |
| 3 страницы WIP не относятся к F4 по Architecture | ❌ ask(F2), upload(F3), graph(F3) |

### 1.3 Ключевой вывод

**F4 в текущем виде — это «контейнер для всего, что случайно оказалось untracked на master во время одной сессии разработки».** Он не имеет чётких границ, смешивает код из F2, F3 и новых сценариев. Принятие F4 в текущем виде невозможно без явного решения владельца о том, что именно должно быть в F4.

---

## 2. Current F4 Ambiguity

### 2.1 Три источника истины — три разных ответа

| Источник | F4 scope | Источник |
|----------|----------|----------|
| `FRONTEND_ARCHITECTURE.md` §4.1, §11 | `/proposals/temporal`★★, `/proposals/presence`, `/proposals/email`, `/proposals/drafts`, `/community`, `/admin/moderation` | Архитектурный документ (проект) |
| `F4_PRE_IMPLEMENTATION_AUDIT.md` §1.1 | 7 страниц: ask, community, admin, analytics, upload, graph, world-explorer | Фактический WIP на диске |
| `F4_SPEC.md` §1.2 | Те же 7 страниц + описание сценариев | Draft-spec (продукт PRE-AUDIT) |

**Расхождение:** Architecture vs WIP vs SPEC — три разных набора. Ни один источник не является «автоматически истинным». Evidence необходимо проверять.

### 2.2 Почему возникла неоднозначность

WIP-код был написан в той же сессии, что и F3-followup (2026-09-16..09-18). Все 7 страниц были созданы как untracked файлы на master. В `CURRENT_DEVELOPMENT_STATE.md` (§6.3) они все собраны под одним заголовком «F4». Однако ни один из этих файлов не имеет формального owner-GO на реализацию как F4 milestone.

---

## 3. Evidence / Sources of Truth

### 3.1 Источники (все проверены read-only)

| # | Источник | Формат | Что подтверждает |
|---|----------|--------|-----------------|
| E1 | `docs/FRONTEND_ARCHITECTURE.md` | markdown | Формальный F4 scope (§4.1, §11) |
| E2 | `arkaim-web-v2/contracts/openapi.json` | JSON | 289 backend-путей, RBAC 298 маршрутов |
| E3 | `arkaim-web-v2/src/shared/api/envelope.ts` | TypeScript | Envelope map: 127 записей |
| E4 | `runtime/core/routes/*.py` (10 файлов) | Python | Фактические endpoint'ы backend |
| E5 | `arkaim-web-v2/src/shared/rbac/navigation.ts` | TypeScript | Фактическая навигация |
| E6 | `arkaim-web-v2/src/app/(main)/temporal/queue/page.tsx` | TSX | Фактическая реализация M10.2 UI (F3) |
| E7 | `arkaim-web-v2/tests/unit/temporal.test.ts` | TypeScript | Тесты M10.2 UI |
| E8 | `docs/F4_PRE_IMPLEMENTATION_AUDIT.md` | markdown | forensic audit F4 WIP |
| E9 | `docs/CURRENT_DEVELOPMENT_STATE.md` | markdown | D1-D3 decisions, статус F3/F4 |

### 3.2 Что НЕ является источником истины для F4 scope

- `F4_SPEC.md` — это draft, созданный на основании WIP, а не Architecture. Его scope — производный от WIP, не нормативный.
- `docs/CLAUDE.md` — устаревший (34 страницы legacy, F4 не упомянут).
- `docs/FRONTEND_INVENTORY_REPORT.md` — inventory, не scope.

---

## 4. WIP Page Reconciliation

### 4.1 Методология

Каждая из 7 F4 WIP-страниц сопоставлена с:
1. `FRONTEND_ARCHITECTURE.md` §4.1 (page map)
2. `FRONTEND_ARCHITECTURE.md` §11 (фазы)
3. Фактическим backend-контрактом (OpenAPI)
4. Фактическим placement в навигации (`navigation.ts`)

### 4.2 Таблица reconciliation

| Page | Current WIP | Documented phase (Architecture) | Actual domain (Architecture §4.1) | Proposed disposition | Evidence |
|------|-------------|-------------------------------|----------------------------------|--------------------|----------|
| `ask/page.tsx` | Streaming chat (reader+) | **F2** («Диалог с книгой») | /ask — S4 «Вопрос книге» | **F2** | Architecture §11: F2 = /ask (SSE); Navigation.ts: `ask` в группе `book`, roles ALL, comingSoon:false |
| `community/page.tsx` | Community hub (reader+) | **F4** («Сообщество») | /community — reader группа | **F4** | Architecture §11: F4 включает /community; §4.1: `/community/timeline`, `/community/interpretations`, `/community/artifacts`; Backend: `/book/community/*` существует (22 endpoint) |
| `admin/page.tsx` | Admin panel (admin) | **F5** («Realtime/Админ») | /admin — admin группа | **F5** | Architecture §11: F5 = /admin (users/invites/keys); §4.1: `/admin` дашборд + `/admin/moderation`; Backend: `/auth/admin/*` существует (8 endpoints) |
| `analytics/page.tsx` | Analytics dashboard (reader+) | **Не рабуролована** | Нет пути в Architecture | **SEPARATE MILESTONE** | Не существует ни в одной фазе Architecture; не в NAV_GROUPS; объединяет data из 6 разных доменов |
| `upload/page.tsx` | BookOS upload (editor+) | **F3** («Студия/Операции») | /studio/upload — S2 | **F3** | Architecture §11: F3 = /studio/upload; §4.1: `/studio/upload — os/ingest (editor-гейт)`; Backend: `/book/os/pipeline/ingest` существует |
| `graph/page.tsx` | Knowledge graph (reader+) | **F2** («Диалог с книгой») | /world/graph — reader | **F2** | Architecture §11: F2 = /world (+ graph); §4.1: `/world/graph` — граф знаний; Навигация: `graph` в группе `book`, roles ALL |
| `world-explorer/page.tsx` | World exploration (reader+) | **F2** («Диалог с книгой») | /explorer — S5 | **F2** | Architecture §11: F2 = /world (+ entity, temporal-view, **graph**); §4.1: `/explorer` — ★ world-explorer; S5 «Исследование мира»; Но! В navigation.ts `world-explorer` — comingSoon:false, group book |

### 4.3 Сводка disposition

| Disposition | Страницы | Количество |
|-------------|----------|-----------|
| **F4** | community | 1 |
| **F2** | ask, graph, world-explorer | 3 |
| **F3** | upload | 1 |
| **F5** | admin | 1 |
| **SEPARATE MILESTONE** | analytics | 1 |
| **ВСЕГО** | 7 | 7 |

### 4.4 Критические находки

1. **Только 1 из 7 WIP-страниц относится к F4 по Architecture.** Это community.
2. **3 страницы — F2 код, который уже был принят в F2/F3.** ask (S4) и graph/world-explorer (S5) — часть F2.
3. **1 страница — F3 код.** Upload — это F3 «Студия».
4. **1 страница — F5 код.** Admin — это F5 «Realtime/Админ».
5. **1 страница — new scope (analytics).** Не документирована ни в одной фазе.

---

## 5. Formal Architecture F4 Reconciliation

### 5.1 Что Architecture определяет как F4

```
F4 Предложения/Очереди:
  /proposals/temporal   — ★★ M10.2 очередь (главный экран)
  /proposals/presence   — presence-очередь
  /proposals/email      — email-черновики
  /proposals/drafts     — drafts-approve
  /community            — Сообщество
  /admin/moderation     — модерация community
```

### 5.2 Что есть на самом деле (backend + frontend)

| Formal F4 capability | Backend contract | Frontend F3/WIP | Status |
|---------------------|-----------------|-----------------|--------|
| `/proposals/temporal` (M10.2 UI) | `POST /book/temporal/pending-updates/scan`, `GET /book/temporal/pending-updates`, `POST /.../{id}/confirm`, `POST /.../{id}/reject` | `temporal/queue/page.tsx` (286 строк) | ✅ **Реализован в F3** |
| `/proposals/presence` | `GET /book/presence/suggestions`, `POST /.../{id}/approve`, `POST /.../{id}/reject`, `GET /.../stats`, `GET /.../trending` | НЕТ | ❌ Backend есть, frontend нет |
| `/proposals/email` | `GET /book/email/drafts`, `POST /book/email/draft/{id}/send`, `GET /book/email/stats` | НЕТ | ❌ Backend есть, frontend нет |
| `/proposals/drafts` | `GET /book/drafts`, `POST /book/drafts/{id}/approve` | НЕТ | ❌ Backend есть, frontend нет |
| `/community` | `GET /book/community/timeline`, `GET /book/community/interpretations/stats`, `GET /book/community/artifacts/stats`, `GET /book/community/search`, + 18 других | `community/page.tsx` (296 строк, BLOCKER) | ⚠️ Backend OK, frontend BROKEN |
| `/admin/moderation` | `POST /book/community/interpretations/{id}/approve`, `POST /book/community/artifacts/{id}/approve`, + reject endpoints | НЕТ (есть `admin/page.tsx` — users+keys, не moderation) | ❌ Backend есть, frontend нет (wrong page) |

### 5.3 Ключевая находка: `/proposals/temporal` УЖЕ РЕАЛИЗОВАН В F3

`temporal/queue/page.tsx` — это **полноценная реализация M10.2 очереди** (scan → список → confirm/reject → история). Она:
- Имеет 8 endpoint-контрактов, все enveloped
- Покрыта 11 тестами в `temporal.test.ts`
- Использует `confirmFinding`, `rejectFinding`, `scanBook` из `contracts/temporal.ts`
- RBAC: reader+ (список), editor+ (confirm/reject/scan) — согласно M10.2 specification
- Задокументирована в F3_IMPLEMENTATION_REPORT

**Вывод:** Формальный F4 «главный экран» (`/proposals/temporal`) — **УЖЕ ЗАКРЫТ В F3**. Он не является частью F4 scope.

### 5.4 Что значит «/admin/moderation» для F4

Architecture определяет `/admin/moderation` как **отдельную страницу** (не `/admin`). Фактический WIP — `admin/page.tsx` — это **полная админ-панель** (users, api-keys, stats), а не moderation. Это **разные страницы** с разными контрактами:
- `/admin` (F5) — `/auth/admin/*` (8 endpoints)
- `/admin/moderation` (F4) — `/book/community/*/{id}/approve`, `/book/community/*/{id}/reject`

**Текущий WIP admin/page.tsx — это F5-код, не F4.**

---

## 6. API/RBAC Feasibility

### 6.1 Что можно реализовать в F4 без изменений backend

| Capability | Backend | RBAC | Frontend effort |
|-----------|---------|------|----------------|
| `/proposals/presence` | ✅ 6 endpoints | reader+ (view), editor+ (approve/reject) | Средний: список + approve/reject UI |
| `/proposals/email` | ✅ 5 endpoints | reader+ (drafts), editor+ (send) | Средний: список черновиков + send |
| `/proposals/drafts` | ✅ 2 endpoints | reader+ (list), editor+ (approve) | Низкий: таблица + approve button |
| `/community` (fix) | ✅ 22 endpoints | reader+ | Низкий: fix JSX, добавить missing calls |
| `/admin/moderation` | ✅ 6 endpoints | admin | Низкий: таблица pending + approve/reject |

**Ни один из этих endpoint'ов не требует изменения backend.**

### 6.2 Что НЕ может быть реализовано в F4 без backend changes

Нет. Все endpoint'ы для формального F4 существуют в OpenAPI.

---

## 7. Dependency Boundaries

### 7.1 F4 зависит от

| Система | Статус | Зависимость |
|---------|--------|-------------|
| F1 Foundation | ✅ CLOSED | StateView, RoleGate, apiClient, envelope |
| F2 Book | ✅ CLOSED | reader API, community API базовые типы |
| F3 Temporal (M10.2) | ✅ CLOSED | `/book/temporal/pending-updates/*` (уже в F3) |
| Backend M10.2 | ✅ CLOSED | TemporalUpdateManager, in-memory queue |

### 7.2 F4 НЕ зависит от

| Система | Обоснование |
|---------|-------------|
| F3 Studio/Operations | `/studio/upload` — F3, но community/admin не трогают studio |
| F5 Realtime | WS/SSE — F5, но formal F4 (presence/email/drafts/moderation) — REST-only |
| F6 Polish | E2E, legacy cleanup — F6, не блокирует F4 |

---

## 8. Scope Contradictions (F4_SPEC vs Reality)

### 8.1 LIST OF SPEC GAPS

| # | Gap | Evidence | Required owner decision |
|---|-----|----------|------------------------|
| SGC-1 | F4_SPEC включает ask, но Architecture определяет ask как F2 | `F4_SPEC.md` §1.2 F4-A; `FRONTEND_ARCHITECTURE.md` §11 F2 = `/ask` | Переместить ask из F4 в F2 (или удалить из F4) |
| SGC-2 | F4_SPEC включает graph, но Architecture определяет graph как F2 | `F4_SPEC.md` §1.2 F4-F; `FRONTEND_ARCHITECTURE.md` §11 F2 = `/world/graph` | Переместить graph из F4 в F2 |
| SGC-3 | F4_SPEC включает world-explorer, но Architecture определяет explorer как F2 | `F4_SPEC.md` §1.2 F4-G; `FRONTEND_ARCHITECTURE.md` §11 F2 = `/explorer` (★) | Переместить world-explorer из F4 в F2 |
| SGC-4 | F4_SPEC включает upload, но Architecture определяет upload как F3 | `F4_SPEC.md` §1.2 F4-E; `FRONTEND_ARCHITECTURE.md` §11 F3 = `/studio/upload` | Переместить upload из F4 в F3 |
| SGC-5 | F4_SPEC включает admin, но Architecture определяет admin как F5 | `F4_SPEC.md` §1.2 F4-C; `FRONTEND_ARCHITECTURE.md` §11 F5 = `/admin` | Переместить admin из F4 в F5 |
| SGC-6 | F4_SPEC включает analytics, но Architecture НЕ определяет analytics | `F4_SPEC.md` §1.2 F4-D; `FRONTEND_ARCHITECTURE.md` §4.1 — нет `/analytics` | Решить: включить как новый scope или исключить |
| SGC-7 | F4_SPEC ссылается на `/proposals/temporal` как на F4, но он реализован в F3 | `F4_SPEC.md` §7.2; `temporal/queue/page.tsx` существует | Убрать proposals/temporal из F4 scope |
| SGC-8 | F4_SPEC определяет F4 как 7 страниц, но только 1 (community) относится к F4 по Architecture | `F4_SPEC.md` §1.2; `FRONTEND_ARCHITECTURE.md` §11 | Переписать F4_SPEC на основании reconciliation |

---

## 9. Decision Matrix

### 9.1 Item-by-item assessment

| Item | Evidence | Belongs to F4? | Why | Owner decision required? |
|------|----------|--------------:|----|-----------------------:|
| `/proposals/temporal` (M10.2) | Реализован в F3 как `/temporal/queue` (286 строк, 11 тестов) | ❌ NO | Уже CLOSED в F3 | Нет — факт |
| `/proposals/presence` | Backend: `/book/presence/suggestions` (6 endpoints); Frontend: НЕТ | ⚠️ YES (форма F4) | Architecture §4.1; M10.2 adjacent (presence-очередь) | Да — реализовывать? |
| `/proposals/email` | Backend: `/book/email/drafts`, `/book/email/draft/{id}/send` (5 endpoints); Frontend: НЕТ | ⚠️ YES (форма F4) | Architecture §4.1 | Да — реализовывать? |
| `/proposals/drafts` | Backend: `/book/drafts`, `/book/drafts/{id}/approve` (2 endpoints); Frontend: НЕТ | ⚠️ YES (форма F4) | Architecture §4.1 | Да — реализовывать? |
| `/community` (hub) | Backend: 22 endpoints; Frontend WIP: community/page.tsx (BLOCKER) | ✅ YES | Architecture §4.1: `/community/timeline`, `/community/interpretations`, `/community/artifacts` | Да — fix BLOCKER |
| `/admin/moderation` | Backend: 6 endpoints (approve/reject interpretations/artifacts); Frontend: НЕТ | ✅ YES (форма F4) | Architecture §4.1: `/admin/moderation` | Да — реализовывать? |
| `ask/page.tsx` | F2-S4 «Вопрос книге»; Navigation.ts: group `book`, roles ALL | ❌ NO | F2 phase, already in NAV_GROUPS as active | Нет — переместить в F2 |
| `graph/page.tsx` | F2: `/world/graph`; Navigation.ts: group `book`, roles ALL | ❌ NO | F2 phase | Нет — переместить в F2 |
| `world-explorer/page.tsx` | F2: `/explorer` (★); Navigation.ts: group `book`, roles ALL | ❌ NO | F2 phase | Нет — переместить в F2 |
| `upload/page.tsx` | F3: `/studio/upload`; Navigation.ts: group `studio`, roles E, comingSoon | ❌ NO | F3 phase | Нет — переместить в F3 |
| `admin/page.tsx` | F5: `/admin` (users/stats/keys); Navigation.ts: group `admin`, roles A | ❌ NO | F5 phase | Нет — переместить в F5 |
| `analytics/page.tsx` | Не рабуролована ни в одной фазе | ⚠️ NEW SCOPE | Не имеет основания в Architecture | Да — включить в F4 или выделить? |

---

## 10. Owner Decisions Required

### 10.1 Решения (в порядке приоритета)

#### D-F4-1: Что делать с Ask, Graph, World-explorer WIP-кодом?

| Вариант | Последствия | Зависимости | Файлы становятся частью |
|---------|------------|-------------|------------------------|
| A1: Переместить в F2 | F2 расширяется; эти страницы добавляются в F2 acceptance | F2 уже CLOSED — требуется re-accept F2 или new F2b GO | `ask/page.tsx`, `graph/page.tsx`, `world-explorer/page.tsx` → F2 |
| A2: Оставить в F4 как де-факто | F4 scope шире Architecture; acceptance F4 включает F2-фичи | Нет новых зависимостей; F2 остаётся CLOSED | Те же 3 файла остаются в F4 |
| A3: Удалить из WIP (так как уже в F2/F3) | Чистка untracked-файлов | Нет | Файлы удаляются из директории |

#### D-F4-2: Что делать с Upload WIP-кодом?

| Вариант | Последствия | Зависимости | Файлы становятся частью |
|---------|------------|-------------|------------------------|
| B1: Переместить в F3 | F3 расширяется; upload становится частью F3 acceptance | F3 уже CLOSED — требуется re-accept F3 или new F3b GO | `upload/page.tsx` → F3 |
| B2: Оставить в F4 | F4 включает F3-фичу | Нет новых зависимостей | Файл остаётся в F4 |
| B3: Удалить (F3 уже имеет upload-функциональность через other mechanisms) | Чистка | Нет | Файл удаляется |

#### D-F4-3: Что делать с Admin WIP-кодом?

| Вариант | Последствия | Зависимости | Файлы становятся частью |
|---------|------------|-------------|------------------------|
| C1: Переместить в F5 | F5 включает admin panel (users, api-keys) | F5 ещё не начата; admin/page.tsx станет первым артефактом F5 | `admin/page.tsx` → F5 |
| C2: Оставить в F4 + добавить `/admin/moderation` | F4 включает и users-panel (не по Architecture) + moderation (по Architecture) | Требуется создать `/admin/moderation` page | admin/page.tsx остаётся в F4, добавляется moderation page |
| C3: Разделить: admin/users → F5, admin/moderation → F4 | Чистое разделение по Architecture | 2 страницы вместо 1 | `admin/page.tsx` → F5; новый `admin/moderation/page.tsx` → F4 |

#### D-F4-4: Что делать с Analytics WIP-кодом?

| Вариант | Последствия | Зависимости | Файлы становятся частью |
|---------|------------|-------------|------------------------|
| D1: Включить в F4 как новый scope | F4 = proposals + analytics dashboard | Нет backend-изменений; analytics использует 6 existing endpoints | `analytics/page.tsx` → F4 |
| D2: Выделить отдельным milestone (F4.5 или F_new) | F4 остаётся clean (только proposals + community); analytics — отдельно | Требуется отдельный owner-GO на analytics | `analytics/page.tsx` → отдельный milestone |
| D3: Исключить из WIP | Чистка | Нет | Файл удаляется |

#### D-F4-5: Формальный F4 scope — подтвердить или изменить?

| Вариант | Последствия | Зависимости |
|---------|------------|-------------|
| E1: Классический F4 (Architecture) = proposals/presence + proposals/email + proposals/drafts + community + admin/moderation | F4 = 5 capabilities, 0 из которых реализованы (community — broken) | Требуется реализовать 4 новых page + fix 1 broken |
| E2: F4 = текущий WIP (7 страниц) после исправления defects | F4 = 7 страниц, но混入 F2/F3/F5 код | Исправить 1 BLOCKER + 2 HIGH + 4 MEDIUM + 3 LOW |
| E3: F4 split = proposals (новый) + community (fix) | Минимальный F4: только то, что есть в Architecture и не реализовано | 4 новых page + 1 fix |

---

## 11. Proposed F4 Scope — Технически обоснованный вариант для рассмотрения

### 11.1 Вариант A: Clean F4 (по Architecture)

**Включает:**
1. `/proposals/presence` — новый (6 endpoints, backend ready)
2. `/proposals/email` — новый (5 endpoints, backend ready)
3. `/proposals/drafts` — новый (2 endpoints, backend ready)
4. `/community` — fix существующего WIP (BLOCKER + MEDIUM)
5. `/admin/moderation` — новый (6 endpoints, backend ready)

**Исключает:**
- `ask/page.tsx` → должен быть в F2 (S4)
- `graph/page.tsx` → должен быть в F2 (/world/graph)
- `world-explorer/page.tsx` → должен быть в F2 (S5)
- `upload/page.tsx` → должен быть в F3 (/studio/upload)
- `admin/page.tsx` → должен быть в F5 (/admin)
- `analytics/page.tsx` → new scope, не в F4

**Что требуется:**
- Создать 4 новые страницы (presence, email, drafts, moderation)
- Исправить 1 BLOCKER + 4 MEDIUM в community/page.tsx
- Решить судьбу 6 misplacd WIP-файлов (переместить/удалить/оставить)

**Прогноз:** ~4 новых файла, 1 fix file. Backend: 0 изменений.

### 11.2 Вариант B: Pragmatic F4 (WIP-consolidation)

**Включает:**
1. `/community` — fix (BLOCKER + MEDIUM)
2. `/proposals/presence` — новый
3. `/proposals/email` — новый
4. `/proposals/drafts` — новый
5. `/admin/moderation` — новый
6. `ask/page.tsx` — оставить как F4 (scope creep accepted)
7. `graph/page.tsx` — оставить как F4 (scope creep accepted)
8. `world-explorer/page.tsx` — оставить как F4 (scope creep accepted)
9. `upload/page.tsx` — оставить как F4 (scope creep accepted)
10. `analytics/page.tsx` — включить как F4 (new scope)

**Что требуется:**
- Исправить 1 BLOCKER + 2 HIGH + 4 MEDIUM + 3 LOW
- Создать 4 новые страницы
- Решить судьбу admin/page.tsx (F5 mismatch)

**Прогноз:** ~4 новых файла + 9 fix/maintenance. Backend: 0 изменений.

### 11.3 Вариант C: Minimal F4 (только community)

**Включает:**
1. `/community` — fix BLOCKER + MEDIUM

**Исключает всё остальное.**

**Что требуется:**
- Исправить 1 BLOCKER + 1 MEDIUM в community/page.tsx
- Переместить или удалить 6 misplacd WIP-файлов

**Прогноз:** 1 fix file. Backend: 0 изменений.

---

## 12. Explicit Non-Scope

F4 НЕ включает (независимо от выбранного варианта):

| Элемент | Обоснование исключения |
|---------|----------------------|
| `/proposals/temporal` (M10.2 UI) | Уже реализован в F3 (`temporal/queue/page.tsx`) |
| `/studio/assets` | F3 scope |
| `/studio/film` | F3 scope |
| `/studio/story` | F3 scope |
| `/xray` | F5 scope |
| `/world` / `/world/entity/*` | F2 scope |
| `/temporal` (main) | F3 scope |
| `/library` | F2 scope |
| `/reading` | F2 scope |
| `/profile` | F2/F5 scope |
| `/login` / `/register` | F1 scope |
| `/help` | F6 scope |
| `/system` | F5 scope |
| Новые backend endpoints | R6 FRONTEND_ARCHITECTURE |
| Изменение backend-контрактов | Backend frozen после M10.2 |

---

## 13. Consequences of Unresolved Decisions

### 13.1 Что произойдёт, если решение НЕ принято

1. **F4 остаётся WIP forever.** Код на диске не закоммичен, не acceptance'ирован.
2. **Migration risk.** При следующем merge/g0-clean аналогичный WIP-код может быть потерян (как произошло с F1-F3 на push-20260916 vs master).
3. **Documentation drift.** CURRENT_DEVELOPMENT_STATE.md §6.3 говорит «F4 WIP», но не уточняет scope. Это вводит в заблуждение любого нового инженера.
4. **Test gap.** 60 F4-тестов покрывают только 5 из 7 WIP-страниц. 2 страницы (ask, graph) и community (из-за BLOCKER) не имеют тестов.
5. **TS errors.** 5 TypeScript ошибок в F4-коде блокируют `npx tsc --noEmit`. Next build не пройдёт для всех 7 страниц.

### 13.2 Что произойдёт, если принять F4 в текущем виде

1. **Scope contamination.** F4 будет включать F2/F3/F5 код, нарушая фазовую изоляцию.
2. **Acceptance ambiguity.** Неясно, что именно Accept'ируется — все 7 страниц или только те, что соответствуют Architecture?
3. **Future refactoring debt.** В F6 потребуется re-split страниц на фазы, что удвоит работу.

---

## 14. Preconditions for Implementation GO

Любой owner-GO на F4 реализацию требует:

1. ✅ Решение D-F4-1..D-F4-5 получено
2. ✅ F4 scope определён (какие страницы/капабилити входят)
3. ✅ Misplacd WIP-файлы перемещены или удалены (решение D-F4-1..D-F4-4)
4. ✅ BLOCKER (AI-1: community JSX) исправлен
5. ✅ HIGH defects (AI-2, AI-3: TS errors) исправлены
6. ✅ F4_SPEC.md актуализирован (убраны misplaced pages, добавлены missing capabilities)
7. ✅ F4_PRE_IMPLEMENTATION_AUDIT.md дополнен (reconciled disposition)

---

## 15. STOP Condition

**STOP после этого документа.**

F4 остаётся **WIP / NOT ACCEPTED / NO GO** до получения owner-GO на:
1. Выбранную схему F4 scope (Вариант A / B / C из §11)
2. Решение по misplaced WIP-файлам
3. Fix BLOCKER/HIGH defects (AI-1, AI-2, AI-3)

**Никакая реализация не начинается автоматически.**

---

*Decision Pack подготовлен read-only аудитом. Все факты — из существующих источников. Никакой новый код не создан, не изменён, не закоммичен.*
