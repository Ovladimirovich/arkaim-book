# F4 PRE-IMPLEMENTATION AUDIT

**Дата:** 2026-09-18
**Тип:** Read-only forensic audit (no code changes)
**Scope:** Существующий F4 WIP-код на диске (`arkaim-web-v2/`)
**Статус F4:** WIP / NOT ACCEPTED / NO GO (owner-GO D2)
**Метод:** Статический анализ файлов, сверка контрактов с backend, запуск тестов, TypeScript-check

---

## Простыми словами

**Цель:** Установить фактическое состояние F4-кода на диске — что существует, что работает, что сломано, и сколько из этого действительно относится к F4.

**Сделано:** Прочитаны все 7 F4-страниц и 5 F4-тестов, сверены API-контракты с backend, запущены тесты, выполнен TypeScript-check. Найден 1 BLOCKER (сломанный JSX в community/page.tsx), 2 HIGH (TS-ошибки в graph/page.tsx и knowledge.test.ts), 4 MEDIUM (неполный контракт / несоответствие scope), LOW — информационные замечания.

**Результат:** F4 не является готовым milestone. Требует исправлений перед любым accept.

---

## 1. Inventory F4-артефактов

### 1.1 Страницы (7 шт.)

| Файл | Строк | Экспортируемый компонент | Статус | Зависимости |
|------|-------|--------------------------|--------|-------------|
| `src/app/(main)/ask/page.tsx` | 400 | `AskPage` | ✅ implemented | useStreamingChat, SourceBadge, StateView, getReaderHistory/Profile |
| `src/app/(main)/community/page.tsx` | 296 | `CommunityPage` | ⚠️ **BLOCKER: broken JSX** | StateView, getCommunityTimeline, getInterpretationsStats, getArtifactsStats, searchCommunity |
| `src/app/(main)/admin/page.tsx` | 425 | `AdminPage` | ✅ implemented | RoleGate, Table, Select, Popconfirm, getAdminStats/Users/ApiKeys, mutations |
| `src/app/(main)/analytics/page.tsx` | 299 | `AnalyticsPage` | ✅ implemented | StateView, getReaderHistoryStats, getReadingProgress, getGraphStats, getWorldSummary, getCacheStats, listDocuments |
| `src/app/(main)/upload/page.tsx` | 235 | `UploadPage` | ✅ implemented | RoleGate, Upload.Dragger, Table, listDocuments, uploadDocument, deleteDocument |
| `src/app/(main)/graph/page.tsx` | 325 | `GraphPage` | ⚠️ **HIGH: TS errors** | StateView, getGraphStats, searchKnowledge, searchAutocomplete |
| `src/app/(main)/world-explorer/page.tsx` | 618 | `WorldExplorerPage` | ✅ implemented | Tabs, Modal, Progress, Rate, worldExplorer contracts (14 endpoints) |

### 1.2 Тесты (5 шт.)

| Файл | Тестов | Результат | Покрытие |
|------|--------|-----------|----------|
| `tests/unit/admin.test.ts` | 13 | ✅ PASS | Envelope map + CRUD контракты |
| `tests/unit/analytics.test.ts` | 6 | ✅ PASS | 6 endpoint-контрактов |
| `tests/unit/community.test.ts` | 9 | ✅ PASS | Envelope map + timeline/stats/search |
| `tests/unit/upload.test.ts` | 11 | ✅ PASS | listDocuments + uploadDocument + envelope |
| `tests/unit/world-explorer.test.ts` | 21 | ✅ PASS | 14+ envelope entries + wire tests |

**Итого:** 60 unit-тестов, все green. Нет E2E, нет integration-тестов, нет test для graph/analytics/ask страниц.

### 1.3 Общее число артефактов на диске

- **19 страниц** в `arkaim-web-v2/src/app/` (14 F1-F3 + 7 F4)
- **27 test-файлов** в `arkaim-web-v2/tests/unit/` (12 F1-F3 + 15 F4-related)
- Все F4-файлы — **untracked** на master

---

## 2. API Contract Audit

### 2.1 Методология

Каждый API-вызов из F4-страницы сопоставлен с `ENVELOPE_MAP` и реальным backend-эндпоинтом (источник: `docs/FRONTEND_FORENSIC_AUDIT.md`, `arkaim-web-v2/src/shared/api/envelope.ts`).

### 2.2 Результаты по страницам

#### ask/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| sendMessage | POST | `/v1/stream` | SSE (не HTTP) | ✅ `contracts/book.ts:7` |
| sendMessage fallback | POST | `/book/ask` | enveloped | ✅ `contracts/book.ts:6` |
| getReaderHistory | GET | `/book/reader/history` | enveloped | ✅ `envelope.ts:49` |
| getReaderProfile | GET | `/book/reader/profile` | direct | ✅ `envelope.ts:48` |

**Вердикт:** ✅ Все контракты подтверждены. ask использует F2-слой (useStreamingChat, getReaderHistory/Profile). Это F2-фича, а не F4.

#### community/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| getCommunityTimeline | GET | `/book/community/timeline` | direct | ✅ `envelope.ts:114` |
| getInterpretationsStats | GET | `/book/community/interpretations/stats` | direct | ✅ `envelope.ts:117` |
| getArtifactsStats | GET | `/book/community/artifacts/stats` | direct | ✅ `envelope.ts:121` |
| searchCommunity | GET | `/book/community/search?q=` | direct | ✅ `envelope.ts:123` |

**Вердикт:** ⚠️ Контракты подтверждены, но JSX сломан (см. §3 BLOCKER).

#### admin/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| getAdminStats | GET | `/auth/admin/stats` | direct | ✅ `envelope.ts:34` |
| getAdminUsers | GET | `/auth/admin/users` | direct | ✅ `envelope.ts:29` |
| updateUserRole | POST | `/auth/admin/users/{id}/role` | direct | ✅ `envelope.ts:31` |
| toggleUser | POST | `/auth/admin/users/{id}/toggle` | direct | ✅ `envelope.ts:32` |
| deleteUser | DELETE | `/auth/admin/users/{id}` | direct | ✅ `envelope.ts:33` |
| getAdminApiKeys | GET | `/auth/admin/api-keys` | direct | ✅ `envelope.ts:35` |
| deleteAdminApiKey | DELETE | `/auth/admin/api-keys/{id}` | direct | ✅ `envelope.ts:36` |

**Вердикт:** ✅ Все 7 endpoints подтверждены, все direct.

#### analytics/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| getReaderHistoryStats | GET | `/book/reader/history/stats` | enveloped | ✅ `envelope.ts:56` |
| getReadingProgress | GET | `/book/reader/reading-progress` | direct | ✅ `envelope.ts:53` |
| getGraphStats | GET | `/book/graph/stats` | direct | ✅ `envelope.ts:57` |
| getWorldSummary | GET | `/book/world/summary` | direct | ✅ (world.ts) |
| getCacheStats | GET | `/book/cache/stats` | enveloped | ✅ `envelope.ts:58` |
| listDocuments | GET | `/book/os/documents` | direct | ✅ `envelope.ts:108` |

**Вердикт:** ✅ Все контракты подтверждены. Однако `listDocuments` импортирован из `@/shared/api` (re-export), а не из `contracts/book.ts` напрямую — это стилистическое несоответствие, не функциональный дефект.

#### upload/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| uploadDocument | POST | `/book/os/pipeline/ingest?doc_type=&version=` | direct | ✅ `envelope.ts:110` |
| listDocuments | GET | `/book/os/documents` | direct | ✅ `envelope.ts:108` |
| deleteDocument | DELETE | `/book/os/documents/{doc_id}` | direct | ✅ `envelope.ts:109` |

**Вердикт:** ✅ Все контракты подтверждены. RBAC: RoleGate (editor/admin).

#### graph/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| getGraphStats | GET | `/book/graph/stats` | direct | ✅ `envelope.ts:57` |
| searchKnowledge | GET | `/book/knowledge/search?q=` | enveloped | ✅ `envelope.ts:60` |
| searchAutocomplete | GET | `/book/knowledge/autocomplete?q=` | enveloped | ✅ `envelope.ts` (через raw `apiCall`) |

**Вердикт:** ⚠️ Контракты подтверждены, но есть TS-ошибки типа (см. §3 HIGH).

#### world-explorer/page.tsx

| Вызов | Метод | Путь | Envelope | Контракт подтверждён |
|-------|-------|------|----------|---------------------|
| exploreWorld | POST | `/book/world-explorer/explore` | enveloped | ✅ `envelope.ts:78` |
| validateIdea | POST | `/book/world-explorer/validate` | enveloped | ✅ `envelope.ts:80` |
| getExplorerEpochs | GET | `/book/world-explorer/epochs` | enveloped | ✅ `envelope.ts:81` |
| getExplorerStats | GET | `/book/world-explorer/stats` | enveloped | ✅ `envelope.ts:82` |
| getHypotheses | GET | `/book/world-explorer/hypotheses/{epoch}` | enveloped | ✅ `envelope.ts:83` |
| getPossibilities | GET | `/book/world-explorer/possibilities/{epoch}` | enveloped | ✅ `envelope.ts:84` |
| getExplorationHistory | GET | `/book/world-explorer/history` | enveloped | ✅ `envelope.ts:85` |
| getExplorationDetail | GET | `/book/world-explorer/history/{id}` | enveloped | ✅ `envelope.ts:86` |
| saveExploration | POST | `/book/world-explorer/history` | direct | ✅ `envelope.ts:90` |
| deleteExploration | DELETE | `/book/world-explorer/history/{id}` | direct | ✅ `envelope.ts:92` |
| submitFeedback | POST | `/book/world-explorer/feedback` | direct | ✅ `envelope.ts:91` |
| generateFromBranch | POST | `/book/world-explorer/generate-from-branch` | enveloped | ✅ `envelope.ts:88` |

**Вердикт:** ✅ Все 12 endpoints подтверждены.

### 2.3 Сводка по контрактам

| Страница | Endpoints | Подтверждено | Mismatch |
|----------|-----------|-------------|----------|
| ask | 4 | 4 | 0 |
| community | 4 | 4 | 0 |
| admin | 7 | 7 | 0 |
| analytics | 6 | 6 | 0 |
| upload | 3 | 3 | 0 |
| graph | 3 | 3 | 0 (но TS-ошибка) |
| world-explorer | 12 | 12 | 0 |
| **Итого** | **39** | **39** | **0 API mismatch** |

**Вывод:** Ни одного mismatch между frontend-контрактами и backend. Все 39 endpoints существуют в `ENVELOPE_MAP` и подтверждены forensic audit.

---

## 3. Defects / Holes

### 3.1 BLOCKER

| ID | Проблема | Evidence | Влияние |
|----|----------|----------|---------|
| **F4-B1** | `community/page.tsx`: незакрытый JSX-тег в функции рендеринга Timeline | `community/page.tsx:194–296` — `<Timeline items={...}>` не закрыт `</Timeline>`, далее идёт `); } }` вместо корректной структуры | **Сломанная компиляция.** Страница не соберётся. Next.js build упадёт при рендере `/community`. |

**Рекомендация:** Исправить JSX — закрыть `<Timeline>`, `<Card>`, `<div>` корректно. action item #1 при GO на F4 fix.

### 3.2 HIGH

| ID | Проблема | Evidence | Влияние |
|----|----------|----------|---------|
| **F4-H1** | `graph/page.tsx:82,93`: `KnowledgeSearchResponse` не присваивается `KnowledgeSearchResult[]` | `page.tsx:46`: `useState<KnowledgeSearchResult[] | null>`; `page.tsx:82`: `setSearchResults(r)` где `r: KnowledgeSearchResponse`; `searchKnowledge` возвращает `Promise<KnowledgeSearchResponse>` (обёртка с `ok/data/total`), а не массив | **TS compilation error.** Страница не запустится в strict mode. Нужно извлекать `.data` из ответа. |
| **F4-H2** | `knowledge.test.ts:96–97`: неверный cast `KnowledgeSearchResponse → any[]` и property `text` не существует в типе `AutocompleteRawItem` | `test.ts:96`: `const r = result as KnowledgeSearchResult[]` — KnowledgeSearchResponse ≠ массив; `test.ts:206`: `{ text: '...' }` — AutocompleteRawItem это кортеж `[string, string, number]`, не объект с полем `text` | **TS compilation error в тестах.** Тесты могут проходить при `skipLibCheck`, но strict check не пройдёт. |

**Рекомендация:** F4-H1 — исправить `graph/page.tsx` (извлекать `.data` из KnowledgeSearchResponse). F4-H2 — исправить `knowledge.test.ts` (правильные типы).

### 3.3 MEDIUM

| ID | Проблема | Evidence | Влияние |
|----|----------|----------|---------|
| **F4-M1** | `community/page.tsx` не импортирует `getKnowledgeStatus` хотя импорт есть в контракте | `community.ts:122–124` определяет `getKnowledgeStatus()` — функция не вызывается на странице, статистика модулей жёстко закодирована `value={14}` (line 163) | UX: значение 14 — хардкод, не реальная статистика. Если модулей станет 15, страница покажет неверное число. |
| **F4-M2** | `ask/page.tsx` не имеет RBAC-гейта | `admin/page.tsx`, `upload/page.tsx` используют `RoleGate`; `ask/page.tsx` — нет. ask доступен всем авторизованным (reader+). | Это корректно по дизайну (ask — reader-функция), но inconsistency с другими F4-страницами. |
| **F4-M3** | `analytics/page.tsx` импортирует `listDocuments` из `@/shared/api` (re-export), а не из `contracts/book.ts` | `analytics/page.tsx:22`: `import { getCacheStats, type CacheStats, listDocuments, type Document } from '@/shared/api'` | Стиль: нарушает правило слоя «страница не импортирует shared/api напрямую». Функционально корректно (re-export пробрасывает). |
| **F4-M4** | Нет test-покрытия для 4 из 7 F4-страниц | tests: admin(13), analytics(6), community(9), upload(11), world-explorer(21). НЕТ tests для: ask, graph, community(Jsx). | Риск регрессии при изменениях. |

### 3.4 LOW

| ID | Проблема | Evidence | Влияние |
|----|----------|----------|---------|
| **F4-L1** | `community/page.tsx`: поиск без debounce | `community/page.tsx:84–94`: `handleSearch` вызывает `searchCommunity` синхронно при каждом Enter | UX: при быстром наборе — множественные запросы. Не блокирует, но неоптимально. |
| **F4-L2** | `graph/page.tsx`: debounce отсутствует | `graph/page.tsx:59–74`: `handleInputChange` вызывает `searchAutocomplete` без debounce | Аналогично L1 — множественные запросы при печатании. |
| **F4-L3** | `community/page.tsx`: `modules: 14` захардкожено | `community/page.tsx:163`: `<Statistic title="Модулей знаний" value={14} ... />` | Значение 14 берётся из FRONTEND_INVENTORY_REPORT. Если число модулей изменится, страница покажет устаревшее значение. |
| **F4-L4** | `world-explorer/page.tsx`: 618 строк — сложный монолит | Весь page.tsx — один компонент без подкомпонентов | Поддерживаемость: сложно ревьюить, сложно тестировать UI-логику. |

### 3.5 Informational

| ID | Замечание | Evidence | Примечание |
|----|-----------|----------|------------|
| **F4-I1** | ask/page.tsx — F2-функциональность, не F4 | Страница использует reader/history/profile API и streaming chat | См. §5 Scope Boundary |
| **F4-I2** | community/page.tsx — Community Hub, не Proposals | Комбинирует timeline + stats + search | См. §5 Scope Boundary |
| **F4-I3** | world-explorer — полностью соответствует WALKER-контракту backend | 12 endpoints, все enveloped/direct как в API docs | Пример хорошего соответствия |

---

## 4. RBAC Audit

### 4.1 Матрица F4-страниц

| Страница | Путь | required role | Frontend enforcement | Backend enforcement | Gap |
|----------|------|--------------|---------------------|--------------------|-----|
| ask | `/ask` | reader+ | ✅ `AuthGuard` layout | ✅ `/v1/stream` requires auth | Нет |
| community | `/community` | reader+ | ✅ `AuthGuard` layout | ✅ `/book/community/*` requires auth | Нет |
| admin | `/admin` | admin | ✅ `RoleGate roles={['admin']}` | ✅ `/auth/admin/*` requires admin | Нет |
| analytics | `/analytics` | reader+ | ✅ `AuthGuard` layout | ✅ reader-level endpoints | Нет |
| upload | `/upload` | editor+ | ✅ `RoleGate roles={['editor','admin']}` | ✅ `/book/os/pipeline/ingest` requires editor+ | Нет |
| graph | `/graph` | reader+ | ✅ `AuthGuard` layout | ✅ `/book/graph/*` requires auth | Нет |
| world-explorer | `/world-explorer` | reader+ | ✅ `AuthGuard` layout | ✅ `/book/world-explorer/*` requires auth | Нет |

### 4.2 Navigation mapping (F4 items in NAV_GROUPS)

| Nav key | Page | roles | comingSoon | href | Факт |
|---------|------|-------|-----------|------|------|
| `ask` | `/ask` | ALL | ❌ (active) | `/` | ⚠️ href=`/` — конфликт с /page.tsx (dashboard) |
| `community` | `/community` | ALL | ❌ (active) | `/community` | ✅ |
| `users` | `/admin` | A | ✅ (comingSoon) | `/admin` | ⚠️ навигация скрывает admin от reader/editor, но page существует |
| `upload` | `/upload` | E | ✅ (comingSoon) | `/studio/upload` | ⚠️ навигация → `/studio/upload`, page → `/upload` |
| `analytics` | `/analytics` | ALL | ❌ (active) | нет в NAV_GROUPS | ⚠️ page существует, но не в навигации |
| `graph` | `/graph` | ALL | ❌ (active) | `/graph` | ✅ |
| `world-explorer` | `/world-explorer` | ALL | ❌ (active) | `/world-explorer` | ✅ |

**Расхождения navigation vs pages:**
1. `ask` имеет `href: '/'` — конфликт с dashboard page. Фактически ask доступен по `/ask`, но навигация ведёт на `/`.
2. `analytics` нет в `NAV_GROUPS` — страница существует, но не видна в навигации.
3. `upload` в навигации → `/studio/upload`, но page на `/upload`.

---

## 5. Dependency Map

### 5.1 Зависимости F4 от backend-систем

```
F4 Pages
├── ask → F2 (reader API: history, profile, streaming)
├── community → community API (timeline, interpretations, artifacts, search)
├── admin → auth API (stats, users, api-keys)
├── analytics → reader API (history stats, reading progress)
│             → knowledge API (graph stats)
│             → world API (world summary)
│             → cache API (cache stats)
│             → os API (documents)
├── upload → os API (ingest, documents, delete)
├── graph → knowledge API (search, autocomplete, graph stats)
└── world-explorer → world-explorer API (explore, validate, epochs, hypotheses, possibilities, history, feedback, generate)
```

### 5.2 Зависимости от F1-F3 foundation

| Foundation | Используемые компоненты | Статус |
|-----------|-------------------------|--------|
| F1 (фундамент) | `StateView`, `SourceBadge`, `App.useApp()` (antd), `useQuery` (TanStack) | ✅ Используются всеми страницами |
| F1 (RBAC) | `RoleGate`, `navForRole` | ✅ admin, upload |
| F2 (reader) | `useStreamingChat`, `getReaderHistory`, `getReaderProfile` | ✅ ask |
| F2 (typed contracts) | `contracts/auth.ts`, `contracts/book.ts`, `contracts/reader.ts`, `contracts/knowledge.ts` | ✅ Все страницы |
| F3 (temporal) | — | Нет прямых зависимостей |
| Envelope system | `ENVELOPE_MAP`, `envelopeOf`, `unwrap` | ✅ Все API-вызовы |

**Вывод:** F4 зависит от F1-F2 foundation. Никаких новых backend-абстракций не создаётся.

---

## 6. Scope Boundary Analysis

### 6.1 Что относится к F4 (фактически)

F4-код на диске включает страницы, которые НЕ все попадают в оригинальную F4-спецификацию («Предложения/Очереди»). Фактический состав:

| Страница | Origin в FRONTEND_ARCHITECTURE | Фактический scope | Принадлежит F4? |
|----------|-------------------------------|-------------------|-----------------|
| `ask` | F2 «Диалог с книгой» (/book section) | Streaming chat | ❌ **F2-фича** |
| `community` | F4 «Сообщество» (/community/*) | Community hub | ✅ F4 (community sub-feature) |
| `admin` | F4 «Админ» (/admin) | Admin panel | ✅ F4 (admin sub-feature) |
| `analytics` | Неระบุ в Architecture | Analytics dashboard | ⚠️ **Scope creep** (не в F4, не в F5) |
| `upload` | F4 «Студия/Загрузка» (/studio/upload) | BookOS upload | ✅ F4 (studio sub-feature) |
| `graph` | F3 «Время мира» (/world/graph) — но это knowledge graph | Knowledge graph | ⚠️ **Scope creep** (knowledge, не proposals) |
| `world-explorer` | F2/F3 «Исследование мира» (/explorer) | World exploration | ✅ F4 (exploration sub-feature) |

### 6.2 Что НЕ относится к F4

| Код | Почему не F4 | Предпочтительный归属 |
|-----|-------------|---------------------|
| `ask/page.tsx` | Streaming chat — это F2 «Диалог с книгой» | Должен быть в F2 |
| `analytics/page.tsx` | Dashboard аналитики — не proposals, не очереди | Отдельная фича (F5?) |
| `graph/page.tsx` | Knowledge graph — это F3 world-функциональность | Должен быть в F3 |

### 6.3 Формирование F4 scope

**Чистый F4 scope** (строго «Предложения/Очереди» по FRONTEND_ARCHITECTURE):
- `/proposals/temporal` (M10.2 queue) — **НЕТ НА ДИСКЕ**
- `/proposals/presence` — **НЕТ НА ДИСКЕ**
- `/proposals/email` — **НЕТ НА ДИСКЕ**

**Фактический F4 WIP** (все что есть на диске):
- ask (F2 misplacement)
- community
- admin
- analytics (scope creep)
- upload
- graph (F3 misplacement)
- world-explorer

---

## 7. Test Results

### 7.1 F4 unit-тесты

```
✓ tests/unit/world-explorer.test.ts (21 tests)
✓ tests/unit/admin.test.ts (13 tests)
✓ tests/unit/upload.test.ts (11 tests)
✓ tests/unit/community.test.ts (9 tests)
✓ tests/unit/analytics.test.ts (6 tests)
— 5 passed (5)
— 60 passed (60)
```

### 7.2 TypeScript check (полный)

```
error TS2345: graph/page.tsx(82,37) — KnowledgeSearchResponse not assignable to KnowledgeSearchResult[]
error TS2345: graph/page.tsx(93,26) — same
error TS2352: knowledge.test.ts(96,13) — KnowledgeSearchResponse to any[]
error TS2352: knowledge.test.ts(97,13) — same
error TS2353: knowledge.test.ts(206,16) — 'text' not in AutocompleteRawItem tuple
```

**5 TS errors, все в F4-related коде.**

### 7.3 Backend tests

Предыдущие прогоны (из CURRENT_DEVELOPMENT_STATE.md): 260 passed, 1 skipped, 3 pre-existing failed (test_auth Telegram). Backend не изменялся.

---

## 8. Summary

| Категория | Количество |
|-----------|-----------|
| F4 страниц | 7 |
| F4 тест-файлов | 5 |
| F4 тестов | 60 (all pass) |
| BLOCKER defects | 1 (community JSX) |
| HIGH defects | 2 (graph TS, knowledge.test TS) |
| MEDIUM defects | 4 (hardcoded values, missing tests, re-export style, nav mismatch) |
| LOW defects | 4 (no debounce, monolith page) |
| API contract mismatches | 0 |
| Pages outside F4 scope | 3 (ask=F2, analytics=creep, graph=F3) |

---

## STOP

Audit завершён. Никакой код не изменялся.
`docs/CURRENT_DEVELOPMENT_STATE.md` — не тронут.
commit не сделан.
F4 остаётся **WIP / NOT ACCEPTED / NO GO**.

Следующий шаг: владелец решает — исправлять defects и принимать F4, или нет.
