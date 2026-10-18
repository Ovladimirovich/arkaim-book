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

# F5 SPEC — Pre-implementation Audit v3

**Дата:** 2026-09-18 · **Версия:** v3 (после arithmetic verification)
**Статус:** PRE-IMPLEMENTATION AUDIT (не реализация)
**Мандат:** только чтение, только спецификация. Никакого кода.

---

## 1. Простыми словами

F5 — это завершение frontend-продукта. Backend полностью готов (все 52 контракта существуют). На диске лежат 5 готовых страниц (`/admin`, `/analytics`, `/profile`, `/status`, `/upload`), которые ждут коммита. Не хватает 2 новых страниц (`/xray`, `/history`) и интеграции WebSocket-тостов.

**Никаких изменений backend не требуется.**

---

## 2. Арифметика — разрешённое противоречие

### 2.1 Разные множества

| Множество | Количество | Описание |
|-----------|-----------|---------|
| Envelope keys | 90 | Записей в `ENVELOPE_MAP` |
| OpenAPI paths | 290 | Всего путей в API |
| **F5 endpoints** | **52** | Подмножество OpenAPI для F5-диапазона |
| ALREADY COVERED | 15 | F5 endpoints уже в envelope |
| REQUIRED ADDITIONS | 6 | F5 endpoints требуют additions |
| OPTIONAL ADDITIONS | 10 | F5 endpoints опциональны |
| EXCLUDED | 21 | F5 endpoints исключены из F5 scope |

### 2.2 Проверка суммы

```
ALREADY COVERED (15) + REQUIRED (6) + OPTIONAL (10) + EXCLUDED (21) = 52 ✓
```

### 2.3 Почему в v1 было 50, а сейчас 52?

В v1 я посчитал auth-admin как 12 endpoints, но фактически их **13** (добавлен `DELETE /auth/admin/sessions/{session_id}`). Разница в 1 endpoint.

**Итоговый точный total: 52 F5 endpoints.**

---

## 3. Полная классификация всех 52 F5 endpoints

### 3.1 Auth/Admin — 13 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 1 | GET | `/auth/admin/api-keys` | ✅ | COVERED | admin page uses this |
| 2 | DELETE | `/auth/admin/api-keys/{key_id}` | ✅ | COVERED | admin page uses this |
| 3 | POST | `/auth/admin/invites` | ❌ | OPTIONAL | optional admin invites tab |
| 4 | GET | `/auth/admin/invites` | ❌ | OPTIONAL | optional admin invites tab |
| 5 | DELETE | `/auth/admin/invites/{invite_id}` | ❌ | OPTIONAL | optional admin invites tab |
| 6 | GET | `/auth/admin/sessions` | ❌ | OPTIONAL | optional admin sessions tab |
| 7 | DELETE | `/auth/admin/sessions/{session_id}` | ❌ | EXCLUDED | no UI scenario in F5 |
| 8 | GET | `/auth/admin/stats` | ✅ | COVERED | admin page uses this |
| 9 | GET | `/auth/admin/users` | ✅ | COVERED | admin page uses this |
| 10 | GET | `/auth/admin/users/{user_id}` | ✅ | COVERED | admin page uses this |
| 11 | DELETE | `/auth/admin/users/{user_id}` | ✅ | COVERED | admin page uses this |
| 12 | POST | `/auth/admin/users/{user_id}/role` | ✅ | COVERED | admin page uses this |
| 13 | POST | `/auth/admin/users/{user_id}/toggle` | ✅ | COVERED | admin page uses this |

**Итого auth-admin:** 13 total | 8 COVERED | 4 OPTIONAL | 1 EXCLUDED

### 3.2 Health — 2 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 14 | GET | `/book/health` | ❌ | EXCLUDED | duplicate of /health, no consumer |
| 15 | GET | `/health` | ✅ | COVERED | status page uses this |

**Итого health:** 2 total | 1 COVERED | 0 OPTIONAL | 1 EXCLUDED

### 3.3 Reader — 10 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 16 | GET | `/book/reader/context` | ❌ | EXCLUDED | no UI scenario in F5 |
| 17 | GET | `/book/reader/history` | ✅ | COVERED | profile page uses this |
| 18 | GET | `/book/reader/history/full` | ❌ | REQUIRED | history page needs full content |
| 19 | GET | `/book/reader/history/sessions` | ❌ | REQUIRED | history page needs sessions list |
| 20 | GET | `/book/reader/history/stats` | ✅ | COVERED | analytics page uses this |
| 21 | GET | `/book/reader/profile` | ✅ | COVERED | profile page uses this |
| 22 | POST | `/book/reader/reading-event` | ✅ | COVERED | reading page uses this |
| 23 | GET | `/book/reader/reading-position` | ✅ | COVERED | reading page uses this |
| 24 | GET | `/book/reader/reading-progress` | ✅ | COVERED | profile/analytics use this |
| 25 | GET | `/book/reader/stats` | ❌ | OPTIONAL | optional extended analytics |

**Итого reader:** 10 total | 6 COVERED | 2 REQUIRED | 1 OPTIONAL | 1 EXCLUDED

### 3.4 X-Ray — 27 endpoints

| # | Method | Path | Envelope | Classification | Reason |
|---|--------|------|----------|---------------|--------|
| 26 | GET | `/xray/audit` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 27 | GET | `/xray/audit/{trace_id}` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 28 | GET | `/xray/diagnostics` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 29 | GET | `/xray/events` | ❌ | REQUIRED | xray page needs events list |
| 30 | GET | `/xray/events/stream` | ❌ | REQUIRED | xray page needs SSE live feed |
| 31 | GET | `/xray/manual/{scenario}` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 32 | GET | `/xray/mode` | ❌ | OPTIONAL | optional xray mode display |
| 33 | GET | `/xray/replay/{trace_id}` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 34 | POST | `/xray/retention/run` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 35 | GET | `/xray/retention/storage-stats` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 36 | GET | `/xray/retention/trace-list` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 37 | POST | `/xray/sanitize/orphan-cleanup` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 38 | GET | `/xray/sanitize/quarantine-list` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 39 | POST | `/xray/sanitize/repair-duplicates` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 40 | GET | `/xray/sanitize/scan-duplicates` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 41 | GET | `/xray/stats` | ❌ | REQUIRED | xray page needs stats |
| 42 | GET | `/xray/store/status` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 43 | GET | `/xray/traces` | ❌ | OPTIONAL | optional xray traces list |
| 44 | GET | `/xray/traces/{trace_id}` | ❌ | OPTIONAL | optional xray trace details |
| 45 | POST | `/xray/traces/{trace_id}/freeze` | ❌ | EXCLUDED | admin operation, no F5 UI |
| 46 | POST | `/xray/traces/{trace_id}/tag` | ❌ | EXCLUDED | admin operation, no F5 UI |
| 47 | POST | `/xray/traces/{trace_id}/terminate` | ❌ | EXCLUDED | admin operation, no F5 UI |
| 48 | POST | `/xray/traces/{trace_id}/unfreeze` | ❌ | EXCLUDED | admin operation, no F5 UI |
| 49 | GET | `/xray/traces/active` | ❌ | OPTIONAL | optional xray active traces |
| 50 | GET | `/xray/traces/completed` | ❌ | OPTIONAL | optional xray completed traces |
| 51 | GET | `/xray/traces/search` | ❌ | EXCLUDED | admin tool, no F5 UI |
| 52 | GET | `/xray/version` | ❌ | REQUIRED | xray page needs version info |

**Итого xray:** 27 total | 0 COVERED | 4 REQUIRED | 5 OPTIONAL | 18 EXCLUDED

### 3.5 Итоговая сводка по категориям

| Категория | Total | COVERED | REQUIRED | OPTIONAL | EXCLUDED |
|-----------|-------|---------|----------|----------|----------|
| auth-admin | 13 | 8 | 0 | 4 | 1 |
| health | 2 | 1 | 0 | 0 | 1 |
| reader | 10 | 6 | 2 | 1 | 1 |
| xray | 27 | 0 | 4 | 5 | 18 |
| **ИТОГО** | **52** | **15** | **6** | **10** | **21** |

**Арифметическая проверка:** 15 + 6 + 10 + 21 = **52** ✓

---

## 4. Обязательные envelope additions (6 шт.)

Каждый endpoint проверен на наличие в OpenAPI и наличие frontend consumer.

| # | Endpoint | Method | Type | Frontend consumer | F5 файл | Response shape |
|---|----------|--------|------|-------------------|---------|---------------|
| 1 | `/xray/events/stream` | GET | SSE direct | `/xray` page (SSE-лента) | `contracts/xray.ts` | SSE stream: `event: <name>\ndata: <json>` |
| 2 | `/xray/stats` | GET | direct | `/xray` page (статистика) | `contracts/xray.ts` | `{active_traces, completed_traces}` |
| 3 | `/xray/events` | GET | direct | `/xray` page (последние события) | `contracts/xray.ts` | массив событий |
| 4 | `/xray/version` | GET | direct | `/xray` page (версия) | `contracts/xray.ts` | `{version, build}` |
| 5 | `/book/reader/history/sessions` | GET | enveloped | `/history` page (список сессий) | `contracts/reader.ts` | `{ok, data: Session[], total}` |
| 6 | `/book/reader/history/full` | GET | enveloped | `/history` page (полная история) | `contracts/reader.ts` | `{ok, data: FullItem[], total}` |

**Проверка OpenAPI:** все 6 endpoints существуют ✓

---

## 5. Проверка пяти existing pages

### 5.1 `/admin` (426 строк)

| Вопрос | Ответ |
|--------|-------|
| Когда создан | 2026-09-17 17:46 |
| Первоначальный milestone | F5 (Product completion — admin) |
| Почему относится к F5 | Страница готова, использует только существующие контракты, требует коммита |
| Tests | ✅ `admin.test.ts` (266 строк, 17.09) |
| Backend contracts | `GET /auth/admin/*`, `POST /auth/admin/*`, `DELETE /auth/admin/*` — 8 путей, все в envelope |
| Изменений F5 | **0** — страница готова, нужен только коммит |
| Достаточно ли зафиксировать? | ✅ Да |

### 5.2 `/analytics` (300 строк)

| Вопрос | Ответ |
|--------|-------|
| Когда создан | 2026-09-17 16:21 |
| Первоначальный milestone | F5 (Product completion — analytics) |
| Почему относится к F5 | Страница готова, использует существующие контракты |
| Tests | ✅ `analytics.test.ts` (149 строк, 17.09) |
| Backend contracts | `/book/reader/history/stats`, `/book/graph/stats`, `/book/cache/stats`, `/book/os/documents`, `/book/reader/reading-progress` — все в envelope |
| Изменений F5 | **0** — страница готова, нужен только коммит |
| Достаточно ли зафиксировать? | ✅ Да |

### 5.3 `/profile` (177 строк)

| Вопрос | Ответ |
|--------|-------|
| Когда создан | 2026-09-16 20:39 |
| Первоначальный milestone | F2 (Reader Profile) |
| Почему относится к F5 | Не коммичен, является частью product completion |
| Tests | ❌ Нет отдельного test-файла (тесты через `contracts.test.ts`) |
| Backend contracts | `/book/reader/profile`, `/book/reader/history`, `/book/reader/reading-progress` — все в envelope |
| Изменений F5 | **0** — страница готова, нужен только коммит |
| Достаточно ли зафиксировать? | ✅ Да |

### 5.4 `/status` (70 строк)

| Вопрос | Ответ |
|--------|-------|
| Когда создан | 2026-09-16 20:39 |
| Первоначальный milestone | F1 (Foundation dashboard) |
| Почему относится к F5 | Не коммичен, требует коммита |
| Tests | ❌ Нет отдельного test-файла |
| Backend contracts | `GET /health` — в envelope |
| Изменений F5 | **0** — страница готова, нужен только коммит |
| Достаточно ли зафиксировать? | ✅ Да |

### 5.5 `/upload` (236 строк)

| Вопрос | Ответ |
|--------|-------|
| Когда создан | 2026-09-17 13:55 |
| Первоначальный milestone | F5 (BookOS integration) |
| Почему относится к F5 | Страница готова, использует существующие контракты |
| Tests | ✅ `upload.test.ts` (149 строк, 17.09) |
| Backend contracts | `GET /book/os/documents`, `POST /book/os/pipeline/ingest` — все в envelope |
| Изменений F5 | **0** — страница готова, нужен только коммит |
| Достаточно ли зафиксировать? | ✅ Да |

---

## 6. Новые страницы: минимальный scope

### 6.1 `/xray` — SSE Observability

**Data sources (обязательные):**
- `GET /xray/version` — версия (1 запрос, статично)
- `GET /xray/stats` — active/completed traces count (статично)
- `GET /xray/events/stream` — SSE live лента (открытое соединение)

**Опционально (может быть добавлено позже):**
- `GET /xray/events` — список последних событий
- `GET /xray/mode` — текущий режим
- `GET /xray/traces`, `/traces/active`, `/traces/completed` — списки трейсов

**SSE lifecycle:**
```
mount   → consumeSseResponse(fetch('/xray/events/stream'), { onEvent, onError })
        → render event в список (bounded buffer: последние 100 событий)
        → auto-reconnect при disconnect (reuse ws-client backoff pattern)
unmount → AbortController.abort() + cleanup buffer
```

**React hook (новый):**
```ts
// shared/realtime/xray-sse.ts
export function useXraySse(onEvent: (e: XrayEvent) => void) {
  // consumeSseResponse → wrapper над fetch + SSE parser
  // signal через useEffect cleanup
  // bounded buffer: последние N событий
}
```

**XRayEvent тип (из OpenAPI description):**
```ts
export type XrayEvent =
  | { event: 'trace_completed'; data: { trace_id: string; name: string; duration_ms: number } }
  | { event: 'trace_frozen'; data: { trace_id: string } }
  | { event: 'trace_terminated'; data: { trace_id: string } }
  | { event: 'orphan_change'; data: { count: number } }
  | { event: 'stats_changed'; data: { active: number; completed: number } }
  | { event: 'heartbeat' };
```

**Файлы:**
- NEW: `src/app/(main)/xray/page.tsx` (~150 строк)
- NEW: `src/shared/api/contracts/xray.ts` (~50 строк)
- NEW: `src/shared/realtime/xray-sse.ts` (~60 строк)
- NEW: `tests/unit/xray.test.ts` (~80 строк)

### 6.2 `/history` — Reader Sessions

**Data sources (обязательные):**
- `GET /book/reader/history/sessions` — список сессий (enveloped, **без query params**)
- `GET /book/reader/history/full?limit=N&session_id=X` — полный контент (enveloped, **limit + session_id**)

**Backend constraints (факт из OpenAPI):**

| Параметр | `history/sessions` | `history/full` |
|----------|-------------------|----------------|
| `limit` | ❌ нет | ✅ есть (default 100) |
| `offset` | ❌ нет | ❌ нет |
| `session_id` | ❌ нет | ✅ есть (optional) |
| `date_range` | ❌ нет | ❌ нет |
| `search` | ❌ нет | ❌ нет |

**Реализация фильтров на frontend:**

| Фильтр | Реализация | Обоснование |
|--------|-----------|-------------|
| limit | ✅ backend support | `history/full?limit=N` |
| session_id | ✅ backend support | `history/full?session_id=X` |
| offset | ❌ client-side pagination | backend не поддерживает, используем limit-based pagination |
| date range | ❌ client-side filter | backend не поддерживает, фильтруем уже полученные данные |
| search by content | ❌ client-side filter | backend не поддерживает, фильтруем уже полученные данные |

**UI layout:**
- Filter bar: session dropdown (из `history/sessions`), limit selector
- Session list: expandable карточки с question content
- Client-side search и date filter над уже загруженными данными

**Файлы:**
- NEW: `src/app/(main)/history/page.tsx` (~200 строк)
- CHANGE: `src/shared/api/contracts/reader.ts` — добавить `getHistorySessions()`, `getHistoryFull()`
- NEW: `tests/unit/history.test.ts` (~80 строк)

---

## 7. WS Toast — интеграция

### 7.1 Существующее состояние

`WsProvider.tsx` (44 строки):
- Подключает WS при mount root layout
- Экспортирует `useWsStatus()` — только boolean connected
- Экспортирует `useWsEvent(event, handler)` — generic подписка
- WS события: `pulse_beat`, `new_suggestion`, `service_status`, `new_question`, `your_question_answered`, `chat_response`, `crowdfunding_milestone`

### 7.2 Toast policy

**Toast-triggering events (F5 scope):**
| Событие | Toast message |
|---------|--------------|
| `new_question` | «Новый вопрос к книге» |
| `your_question_answered` | «Ответ на ваш вопрос готов» |
| `new_suggestion` | «Новое предложение в сообществе» |
| `crowdfunding_milestone` | «Новый milestone краудфандинга» |
| `service_status` | «Статус сервиса изменён» |

**НЕ toast (только log/debug):**
- `pulse_beat` — heartbeat, слишком часто
- `chat_response` — поток в реальном времени, не тост

### 7.3 Интеграция

**Единая точка:** создать `WsToast.tsx` в `shared/realtime/`, подключать в root layout (рядом с WsProvider).

```tsx
// shared/realtime/WsToast.tsx
export function WsToast() {
  const { message } = App.useApp();
  
  useWsEvent('new_question', () => message.info('Новый вопрос к книге'));
  useWsEvent('your_question_answered', () => message.success('Ответ на ваш вопрос готов'));
  useWsEvent('new_suggestion', () => message.info('Новое предложение в сообществе'));
  useWsEvent('crowdfunding_milestone', () => message.success('Новый milestone'));
  useWsEvent('service_status', () => message.warning('Статус сервиса обновлён'));
  
  return null;
}
```

**Подключение в `providers.tsx`:**
```tsx
<WsProvider>
  <WsToast /> {/* toast логика */}
  {children}
</WsProvider>
```

### 7.4 Reconnect behavior

- `WsClient` уже имеет auto-reconnect (exponential backoff, max 10 attempts)
- `useWsEvent` хук перезапускает подписку при каждом ререндере с новыми handler
- **Проблема:** при reconnect все `useWsEvent` handlers перезaregistrent — но это корректно (эффект React run again)
- **Решение:** добавить `key` на `WsToast` или использовать стабильный reference для handlers

### 7.5 Cleanup

При unmount `WsToast`:
- `useWsEvent` effect cleanup вызывает `off()` — подписка удалена
- При remount (навигация на другую страницу и назад) — подписки восстанавливаются
- **Нет утечек:** каждый `useEffect` имеет cleanup

---

## 8. F5 — полный список файлов

### 8.1 Новые файлы

| Файл | Описание | Строк (оценка) |
|------|----------|---------------|
| `src/app/(main)/xray/page.tsx` | SSE-лента трасировок | ~150 |
| `src/app/(main)/history/page.tsx` | История сессий читателя | ~200 |
| `src/shared/api/contracts/xray.ts` | XRay контракты | ~50 |
| `src/shared/realtime/xray-sse.ts` | SSE hook для xray | ~60 |
| `src/shared/realtime/WsToast.tsx` | WS toast интеграция | ~40 |
| `tests/unit/xray.test.ts` | XRay контракт тесты | ~80 |
| `tests/unit/history.test.ts` | History контракт тесты | ~80 |

### 8.2 Изменяемые файлы

| Файл | Изменение | Причина |
|------|-----------|---------|
| `src/shared/api/envelope.ts` | +6 записей | xray + history endpoints |
| `src/shared/api/contracts/reader.ts` | +2 функций | getHistorySessions, getHistoryFull |
| `src/shared/rbac/navigation.ts` | +2 items | xray (admin+), history (reader+) |
| `src/app/providers.tsx` | +WsToast | toast интеграция |

### 8.3 Коммит готовых страниц (5 шт.)

| Файл | Статус | Строки |
|------|--------|--------|
| `src/app/(main)/admin/page.tsx` | ✅ готов | 426 |
| `src/app/(main)/analytics/page.tsx` | ✅ готов | 300 |
| `src/app/(main)/profile/page.tsx` | ✅ готов | 177 |
| `src/app/(main)/status/page.tsx` | ✅ готов | 70 |
| `src/app/(main)/upload/page.tsx` | ✅ готов | 236 |

**Все 5 страниц используют только существующие backend-контракты. Zero изменений backend.**

---

## 9. Test plan

### 9.1 Новые тесты

| Файл | Что тестирует | Ожидаемый результат |
|------|--------------|---------------------|
| `xray.test.ts` | envelope map (4 записи), xray contract types | 4+ tests PASS |
| `history.test.ts` | envelope map (2 записи), getHistorySessions, getHistoryFull | 4+ tests PASS |
| `ws-toast.test.ts` | toast events: new_question, your_question_answered, new_suggestion | 3+ tests PASS |

### 9.2 Изменяемые тесты

| Файл | Изменение |
|------|-----------|
| `contracts.test.ts` | Добавить проверку 6 новых envelope записей |
| `rbac.test.ts` | Добавить проверку навигационных пунктов xray/history |

### 9.3 Ожидаемый итог

```
arkaim-web-v2 tests: 132 (текущие) + 15 (новые) = 147/147 PASS
next build: 24 страницы (17 untracked + 5 F4 committed) → все статично генерируются
```

---

## 10. Verification Checklist (post-F5)

- [ ] `/xray` страница существует, показывает SSE-ленту + статистику
- [ ] `/history` страница существует, показывает сессии с фильтрами
- [ ] WS-тосты появляются при `new_question`, `your_question_answered`, `new_suggestion`
- [ ] 5 готовых страниц закоммичены
- [ ] envelope.ts содержит 6 новых записей (xray×4 + history×2)
- [ ] 147/147 тестов green
- [ ] `next build` проходит (24 страницы)
- [ ] Backend не изменён (0 файлов в runtime/)
- [ ] Рабочее дерево: только F5-файлы + docs/

---

## 11. Разделение F5 и Technical Debt

| Элемент | F5? | Обоснование |
|---------|-----|-------------|
| M8.1 test-fix | ❌ НЕ F5 | Отдельный technical-debt item |
| Legacy `arkaim-web/` удаление | ❌ НЕ F5 | F6 scope |
| F6 (help, a11y, mobile, E2E) | ❌ НЕ F5 | Следующая фаза |
| Backend changes | ❌ НЕ F5 | Регламент F-линейки: 0 изменений |
| `reader/stats` envelope | ⚠️ Опционально | Может быть добавлен при реализации |
| `admin/sessions` + `admin/invites` | ⚠️ Опционально | Могут быть доп. табами в `/admin` |

---

## 12. Итоговая сводка

| Метрика | Значение |
|---------|---------|
| **TOTAL F5 endpoints** | **52** |
| ALREADY COVERED (в envelope) | 15 |
| REQUIRED ADDITIONS | 6 |
| OPTIONAL ADDITIONS | 10 |
| EXCLUDED | 21 |
| **Проверка:** 15 + 6 + 10 + 21 | **= 52** ✓ |
| Новых страниц | 2 (`/xray`, `/history`) |
| Коммит готовых страниц | 5 (`/admin`, `/analytics`, `/profile`, `/status`, `/upload`) |
| Новый код (строки, оценка) | ~580 |
| Новые тесты (строки, оценка) | ~160 |
| **Backend changes** | **0** |
| **M8.1 included** | **Нет** |
| **F6 included** | **Нет** |
| **Legacy removal included** | **Нет** |

---

## STOP

Это complete pre-implementation audit v3. **Никакого кода не написано.**
Следующий step — owner-GO на **F5 implementation**.
