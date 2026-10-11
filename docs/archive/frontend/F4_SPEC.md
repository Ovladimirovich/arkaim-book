# F4 SPEC — Спецификация «Предложения / Сообщество / Модерация»

**Дата:** 2026-09-18 (draft) → 2026-09-18 (final)
**Статус:** ✅ ACCEPTED & CLOSED 2026-09-18 (owner-GO ПРИНЯТО)
**Основание:** `docs/F4_PRE_IMPLEMENTATION_AUDIT.md`, `docs/F4_SCOPE_DECISION_PACK.md`
**Связь:** F4 IMPLEMENTED → ACCEPTED

---

## Простыми словами

**Что это?** F4 = 5 capabilities: community (fix), presence, email, drafts, moderation. Чистый scope по Architecture — без чужого WIP из F2/F3/F5.

**Зачем?** Зафиксировать итоговый scope F4 после owner-decisions и подготовить ground для реализации GO.

**Текущий статус:** Scope ACCEPTED (owner-GO decisions 1A/2A/3B/4B/5A). Реализация начнётся по отдельному GO.

---

## 1. Scope

### 1.1 Входы

| # | Вход | Источник |
|---|------|----------|
| E1 | Существующий WIP-код: 7 страниц в `arkaim-web-v2/src/app/(main)/` | audit §1.1 |
| E2 | Существующий WIP-тесты: 5 test-файлов, 60 tests | audit §1.2 |
| E3 | Backend API: 39 endpoints, все подтверждены (audit §2.3) | FRONTEND_FORENSIC_AUDIT.md |
| E4 | RBAC-матрица: 298 маршрутов, generated | rbac.generated/matrix.ts |
| E5 | ENVELOPE_MAP: 127 записей, все F4-endpoints покрыты | envelope.ts |
| E6 | FRONTEND_ARCHITECTURE §4.1: page map | docs/FRONTEND_ARCHITECTURE.md |

### 1.2 Пользовательские сценарии (Clean F4)

> **Диспозиция:** Все 7 WIP-страниц пересмотрены по owner-decisions (D-F4-1..5). Остались 5 capabilities по Architecture.

#### F4-A: Сообщество — community hub (fix WIP)

- **Роль:** reader+
- **Сценарий:** Просмотр хроники событий Аркаима + статистика интерпретаций/артефактов + поиск по сообществу
- **Контракты:** GET /book/community/timeline, /interpretations/stats, /artifacts/stats, /search
- **Страница:** `/community` — **fix существующего WIP** (BLOCKER: broken JSX + MEDIUM defects)
- **Status:** WIP код существует, но сломан. Требуется fix AI-1 + AI-4.

#### F4-B: Presence-очередь (new)

- **Роль:** reader+ (view), editor+ (approve/reject)
- **Сценарий:** List incoming presence-suggestions from community → approve/reject per item → stats
- **Контракты:** GET /book/presence/suggestions, GET /book/presence/suggestions/stats, GET /book/presence/suggestions/{id}, POST /book/presence/suggestions/{id}/approve, POST /book/presence/suggestions/{id}/reject, GET /book/presence/trending
- **Страница:** `/proposals/presence` — **новая страница**
- **Status:** Backend готов, frontend отсутствует.

#### F4-C: Email-рассылка (new)

- **Роль:** reader+ (drafts list), editor+ (send)
- **Сценарий:** Просмотр email-черновиков → отправить конкретный → статистика отправленных
- **Контракты:** GET /book/email/drafts, POST /book/email/draft/{id}/send, GET /book/email/stats, GET /book/email/draft/auto, GET /book/email/draft/topic/{topic}
- **Страница:** `/proposals/email` — **новая страница**
- **Status:** Backend готов, frontend отсутствует.

#### F4-D: Drafts-approve (new)

- **Роль:** reader+ (list), editor+ (approve)
- **Сценарий:** List content drafts → approve selected draft → draft moves to published state
- **Контракты:** GET /book/drafts, POST /book/drafts/{draft_id}/approve
- **Страница:** `/proposals/drafts` — **новая страница**
- **Status:** Backend готов, frontend отсутствует.

#### F4-E: Community moderation (new)

- **Роль:** admin
- **Сценарий:** List pending interpretations/artifacts → approve or reject → invalidate cache
- **Контракты:** GET /book/community/interpretations (pending filter), POST /book/community/interpretations/{id}/approve, POST /book/community/interpretations/{id}/reject, GET /book/community/artifacts (pending filter), POST /book/community/artifacts/{id}/approve, POST /book/community/artifacts/{id}/reject
- **Страница:** `/admin/moderation` — **новая страница** (не путать с `/admin` — F5)
- **Status:** Backend готов, frontend отсутствует.

---

### 1.3 Выходы (Clean F4)

| # | Выход | Критерий |
|---|-------|----------|
| O1 | 5 capabilities реализованы | community (fix) + 4 новых page |
| O2 | `npx tsc --noEmit` — 0 ошибок | в F4-related коде |
| O3 | community/page.tsx компилируется | BLOCKER AI-1 исправлен |
| O4 | RBAC enforcement корректен | Presence/editor+, Email/editor+, Drafts/editor+, Moderation/admin |
| O5 | 28 API-контрактов покрыты | envelope map + unit tests green |
| O6 | 4 новых page → next build successful | без regressions |

---

### 1.4 Зависимости

| Зависимость | Статус | Комментарий |
|------------|--------|-------------|
| F1 Foundation (antd, TanStack Query, StateView, RoleGate) | ✅ CLOSED | Базовые компоненты |
| F2 Book (reader API, community API types) | ✅ CLOSED | community зависит от F2 |
| F3 Temporal (M10.2) | ✅ CLOSED | `/proposals/temporal` УЖЕ В F3 — НЕ дублировать |
| Backend M10.2 (pending-updates) | ✅ CLOSED | Но `/proposals/temporal` НЕ В SCOPE F4 |
| openapi-fetch / typed contracts | ✅ F1 | shared/api/client.ts |
| ENVELOPE_MAP | ✅ F1 | envelope.ts |

### 1.3 Выходы

| # | Выход | Критерий |
|---|-------|----------|
| O1 | 7 страниц рендерятся без ошибок | next build успешен |
| O2 | 60 unit-тестов green | vitest run → 0 failed |
| O3 | Все 39 API-контрактов работают | envelope map + contract tests green |
| O4 | RBAC enforcement корректен | RoleGate на admin/upload, AuthGuard на остальное |
| O5 | F4-B1 (community JSX) исправлен | community/page.tsx компилируется |
| O6 | F4-H1 (graph TS) исправлен | graph/page.tsx нет TS-ошибок |
| O7 | F4-H2 (knowledge.test TS) исправлен | knowledge.test.ts нет TS-ошибок |

### 1.4 Зависимости

| Зависимость | Статус | Комментарий |
|------------|--------|-------------|
| F1 Foundation (antd, TanStack Query, StateView, SourceBadge) | ✅ CLOSED | Базовые компоненты |
| F2 Book (reader API, streaming, auth) | ✅ CLOSED | ask зависит от F2 |
| F3 Temporal (world/graph API) | ✅ CLOSED | graph использует knowledge API |
| Backend M10.2 (pending-updates) | ✅ CLOSED | Но `/proposals/temporal` НЕТ в F4 |
| openapi-fetch / typed contracts | ✅ F1 | shared/api/client.ts |
| ENVELOPE_MAP | ✅ F1 | envelope.ts |

---

## 2. Non-goals

F4 НЕ делает (post-decision, Clean F4):

| # | Non-goal | Обоснование |
|---|----------|-------------|
| NG1 | Создавать новые backend endpoints | R6 FRONTEND_ARCHITECTURE: frontend не добавляет endpoints |
| NG2 | Изменять Temporal mechanism | M10.2 закрыт, backend заморожен |
| NG3 | Реализовать new media-generation capabilities | MediaContract v1.0, M4.2.2 — отдельно |
| NG4 | Дублировать `/proposals/temporal` UI | Уже реализован в F3 как `/temporal/queue` |
| NG5 | Включать ask/graph/world-explorer | F2 scope — перемещены по D-F4-1 (1A) |
| NG6 | Включать upload | F3 scope — перемещён по D-F4-2 (2A) |
| NG7 | Включать `/admin` (users/keys) | F5 scope — по D-F4-3 (3B) |
| NG8 | Включать analytics | Отдельный milestone — по D-F4-4 (4B) |
| NG9 | Исправлять legacy arkaim-web | Legacy изолирован, заморожен до F6 |
| NG10 | Добавлять E2E-тесты (Playwright) | ВНЕ MANDATE F4 |
| NG11 | Реализовать F5/F6 | Отдельные фазы |
| NG12 | Коммитить F4-код в git master | Код остаётся untracked до GO |

---

## 3. API Contracts

### 3.1 F4-A: Community hub (`/community`)

| Endpoint | Method | Request | Response | Envelope | RBAC |
|----------|--------|---------|----------|----------|------|
| `/book/community/timeline` | GET | — | `{events: CommunityEvent[]}` | direct | auth |
| `/book/community/interpretations/stats` | GET | — | `{total, pending, approved, rejected}` | direct | auth |
| `/book/community/artifacts/stats` | GET | — | `{total, pending, approved, categories}` | direct | auth |
| `/book/community/search` | GET | `q=` | `{interpretations, artifacts, total}` | direct | auth |
| `/book/community/knowledge/status` | GET | — | `{module_count, last_refresh}` | direct | auth |
| `/book/community/knowledge/refresh` | POST | — | `{ok, refreshed_modules}` | direct | editor+ |

### 3.2 F4-B: Presence queue (`/proposals/presence`)

| Endpoint | Method | Request | Response | Envelope | RBAC |
|----------|--------|---------|----------|----------|------|
| `/book/presence/suggestions` | GET | — | `{data: PresenceSuggestion[], total}` | enveloped | auth |
| `/book/presence/suggestions/stats` | GET | — | `{total, pending, approved, rejected}` | enveloped | auth |
| `/book/presence/suggestions/{id}` | GET | — | `{data: PresenceSuggestion}` | enveloped | auth |
| `/book/presence/suggestions/{id}/approve` | POST | — | `{ok, suggestion_id}` | direct | editor+ |
| `/book/presence/suggestions/{id}/reject` | POST | — | `{ok, suggestion_id}` | direct | editor+ |
| `/book/presence/trending` | GET | — | `{data: TrendingItem[]}` | enveloped | auth |

### 3.3 F4-C: Email drafts (`/proposals/email`)

| Endpoint | Method | Request | Response | Envelope | RBAC |
|----------|--------|---------|----------|----------|------|
| `/book/email/drafts` | GET | — | `{data: EmailDraft[]}` | enveloped | auth |
| `/book/email/draft/{id}/send` | POST | — | `{ok, draft_id}` | direct | editor+ |
| `/book/email/stats` | GET | — | `{sent, pending, subscribers}` | enveloped | auth |
| `/book/email/draft/auto` | GET | — | `{data: EmailDraft}` | enveloped | auth |
| `/book/email/draft/topic/{topic}` | GET | — | `{data: EmailDraft}` | enveloped | auth |

### 3.4 F4-D: Drafts approve (`/proposals/drafts`)

| Endpoint | Method | Request | Response | Envelope | RBAC |
|----------|--------|---------|----------|----------|------|
| `/book/drafts` | GET | `status?` | `{data: Draft[]}` | enveloped | auth |
| `/book/drafts/{draft_id}/approve` | POST | — | `{ok, status: 'approved', draft_id}` | direct | editor+ |

### 3.5 F4-E: Community moderation (`/admin/moderation`)

| Endpoint | Method | Request | Response | Envelope | RBAC |
|----------|--------|---------|----------|----------|------|
| `/book/community/interpretations` | GET | `status=pending` | `{data: Interpretation[]}` | enveloped | admin |
| `/book/community/interpretations/{id}/approve` | POST | — | `{ok, interp_id}` | direct | admin |
| `/book/community/interpretations/{id}/reject` | POST | — | `{ok, interp_id}` | direct | admin |
| `/book/community/artifacts` | GET | `status=pending` | `{data: Artifact[]}` | enveloped | admin |
| `/book/community/artifacts/{id}/approve` | POST | — | `{ok, artifact_id}` | direct | admin |
| `/book/community/artifacts/{id}/reject` | POST | — | `{ok, artifact_id}` | direct | admin |

### 3.6 Источник истины для схем

- OpenAPI слепка: `arkaim-web-v2/contracts/openapi.json` (289 путей)
- Envelope map: `arkaim-web-v2/src/shared/api/envelope.ts` (127 записей)
- Type definitions: `arkaim-web-v2/src/shared/api/contracts/*.ts`
- Backend source: `runtime/core/routes/book.py`, `runtime/core/book_routes.py`

---

## 4. RBAC

### 4.1 Роли

| Роль | Описание | Источники |
|------|----------|-----------|
| `reader` | Основной читатель | backend auth |
| `editor` | Редактор (может загружать документы, управлять контентом) | backend auth |
| `admin` | Администратор (пользователи, ключи, модерация) | backend auth |

### 4.2 Page-level access (Clean F4)

| Страница | Минимальная роль | Enforcement |
|----------|-----------------|-------------|
| `/community` | reader | `AuthGuard` (layout) |
| `/proposals/presence` | reader (view), editor (write) | `AuthGuard` + RoleGate на approve/reject |
| `/proposals/email` | reader (view), editor (write) | `AuthGuard` + RoleGate на send |
| `/proposals/drafts` | reader (view), editor (write) | `AuthGuard` + RoleGate на approve |
| `/admin/moderation` | **admin** | `RoleGate roles={['admin']}` |

### 4.3 Action-level access (write operations)

| Action | Endpoint | Required role |
|--------|----------|--------------|
| Refresh community knowledge | POST /book/community/knowledge/refresh | editor+ |
| Approve presence suggestion | POST /book/presence/suggestions/{id}/approve | editor+ |
| Reject presence suggestion | POST /book/presence/suggestions/{id}/reject | editor+ |
| Send email draft | POST /book/email/draft/{id}/send | editor+ |
| Approve content draft | POST /book/drafts/{id}/approve | editor+ |
| Approve interpretation | POST /book/community/interpretations/{id}/approve | admin |
| Reject interpretation | POST /book/community/interpretations/{id}/reject | admin |
| Approve artifact | POST /book/community/artifacts/{id}/approve | admin |
| Reject artifact | POST /book/community/artifacts/{id}/reject | admin |

### 4.4 Backend enforcement

Все F4-эндпоинты защищены на уровне backend (FastAPI `require_role` декораторы). Frontend RoleGate — дополнительное ограничение видимости, но НЕ замена backend-проверки.

---

## 5. System Boundaries

### 5.1 Границы ответственности (Clean F4)

| Система | Владелец | F4 роль |
|---------|----------|---------|
| Community (`/book/community/*`) | Community layer | F4 читает+пишет: timeline, stats, moderation, knowledge refresh |
| Presence (`/book/presence/*`) | Presence layer | F4 читает suggestions + write approve/reject |
| Email (`/book/email/*`, `/book/drafts/*`) | Email/Drafts layer | F4 читает drafts + write send/approve |
| Auth (`/auth/*`) | Auth layer | F4 читает `/auth/me`, НЕ трогает `/auth/admin/*` (F5) |

### 5.2 Что F4 НЕ владеет

- **Temporal engine (M10.2):** `temporal/queue` реализован в F3; F4 НЕ дублирует
- **Admin users/keys:** `/auth/admin/*` — F5 scope
- **Analytics dashboard:** `/analytics` — отдельный milestone (D-F4-4 → 4B)
- **Upload/BookOS write:** POST /book/os/pipeline/ingest — F3 scope
- **Ask/Streaming chat:** `/ask` — F2 scope
- **Graph knowledge search:** `/graph` — F2 scope
- **World explorer:** `/world-explorer` — F2 scope
- **Media generation:** `/book/assets/*`, `/api/studio/*` — F3 scope
- **Legacy arkaim-web:** F6 scope

---

## 6. Defect Triage → Action Items (Clean F4)

**Контекст:** По D-F4-1 (1A) ask/graph/world-explorer → F2, по D-F4-2 (2A) upload → F3.
Остающиеся defects — только те, что относятся к Clean F4 (community fix + 4 новых page).

| ID | Проблема | Severity | Required Action | Acceptance Criterion | Phase |
|----|----------|----------|----------------|---------------------|-----------|
| **AI-1** | community/page.tsx broken JSX (незакрытые `</Timeline>`, `</Card>`, `</div>` строки 194-296) | **BLOCKER** | Исправить JSX-структуру; страница должна компилироваться | `npx tsc --noEmit` чист; Next build /community успешен | F4 |
| **AI-2** | community/page.tsx: hardcoded modules count = 14 | MEDIUM | Заменить на `getKnowledgeStatus()` вызов → отображать реальный `module_count` | community показывает реальное число модулей | F4 |
| **AI-3** | Отсутствуют unit-тесты для 4 новых page (presence, email, drafts, moderation) | MEDIUM | Добавить envelope-map тесты для каждого new page | 60 → ~90 тестов, все green | F4 |
| **AI-4** | Отсутствует `/admin/moderation` страница (есть только `/admin`) | HIGH | Создать новую page с approve/reject для interpretations + artifacts | Страница доступна по `/admin/moderation`, RBAC=admin | F4 |
| **AI-5** | Нет debounce на community search input | LOW | Добавить debounce 300ms на handleSearch | UX: запросы не дублируются при быстром наборе | F4 |
| **AI-6** | Нет тестов для `/proposals/presence` /email/ /drafts/ модерации | MEDIUM | Добавить unit-тесты для envelope map этих endpoints | +30 тестов | F4 |

**Исключены из Clean F4 (перемещены):**
- AI-7 (graph TS errors) → F2
- AI-8 (knowledge.test TS) → F2
- AI-9 (analytics re-export) → F3 / Separate
- AI-10 (world-explorer monolith) → F2

**Итого action items для Clean F4:** 6 (1 BLOCKER, 1 HIGH, 3 MEDIUM, 1 LOW).

---

## 7. Final Disposition (post-decision)

### 7.1 WIP → Phase mapping (принято owner-GO)

| WIP файл | Фактический scope | Решение | Куда перемещён |
|----------|------------------|---------|---------------|
| `ask/page.tsx` | Streaming chat S4 | D-F4-1 (1A) | **F2** |
| `graph/page.tsx` | Knowledge graph | D-F4-1 (1A) | **F2** |
| `world-explorer/page.tsx` | World exploration S5 | D-F4-1 (1A) | **F2** |
| `upload/page.tsx` | BookOS ingest | D-F4-2 (2A) | **F3** |
| `admin/page.tsx` | Admin users/keys/stats | D-F4-3 (3B) | **F5** |
| `analytics/page.tsx` | Analytics dashboard | D-F4-4 (4B) | **Separate milestone** |
| `community/page.tsx` | Community hub | **Остаётся в F4** | Fix + keep |

### 7.2 Clean F4 capabilities vs Architecture

| Capability | Architecture путь | Backend | Frontend | Status |
|-----------|------------------|---------|----------|--------|
| `/proposals/temporal` | F4 (главный экран) | ✅ 7 endpoints | ✅ `temporal/queue` (F3) | **CLOSED in F3** — НЕ дублировать |
| `/proposals/presence` | F4 | ✅ 6 endpoints | ❌ НЕТ | **Новая страница F4** |
| `/proposals/email` | F4 | ✅ 5 endpoints | ❌ НЕТ | **Новая страница F4** |
| `/proposals/drafts` | F4 | ✅ 2 endpoints | ❌ НЕТ | **Новая страница F4** |
| `/community` | F4 | ✅ 22 endpoints | ⚠️ WIP (BLOCKER) | **Fix существующего WIP** |
| `/admin/moderation` | F4 | ✅ 6 endpoints | ❌ НЕТ (есть wrong `/admin`) | **Новая страница F4** |

**Ключевая коррекция:** Architecture определяет `/proposals/temporal` как F4, но он УЖЕ реализован в F3 как `/temporal/queue`. Это архитектурный drift — не bug реализации.

---

## 8. Acceptance Criteria (Clean F4)

F4 считается ACCEPTED когда:

1. ✅ `npx tsc --noEmit` — 0 ошибок в F4-related коде (community + 4 new pages)
2. ✅ `npx vitest run` — все тесты green (target ~90, все green)
3. ✅ `next build` — успешен, 5 страниц F4 доступны без regressions
4. ✅ AI-1 (BLOCKER: community JSX) исправлен
5. ✅ 4 новых page созданы: presence, email, drafts, moderation
6. ✅ RBAC enforcement: presence/email/drafts — editor+ write; moderation — admin only
7. ✅ 28 API-контрактов F4 покрыты unit-тестами (envelope map + key paths)
8. ✅ Owner-GO получен

---

## 9. Implementation GO

**Статус:** ✅ GO ПОЛУЧЕН / ПРИНЯТО 2026-09-18

Инженеру даётся GO на реализацию только после:
1. Подтверждения этого GO владельцем
2. Прочтения §6 Action Items
3. Проверки backend-контрактов в §3.1–3.5

**Не начинать без GO.**
