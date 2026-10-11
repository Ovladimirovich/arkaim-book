# F2 — PRE-IMPLEMENTATION FORENSIC AUDIT (read-only)

**Дата:** 2026-09-09
**Контекст:** F1 = PASS / CLOSED (см. `F1_POST_IMPLEMENTATION_AUDIT.md`). Backend — единственный source of truth. Legacy архитектурно не используется.
**Метод:** живой импорт backend'а (openapi.json + rbac-matrix слепки, live-пробинг фактических JSON-ответов), grep-проверки исходников, БЕЗ каких-либо правок кода.

---

## Простыми словами

1. **Что делал** — разложил все 289 API-путей backend'а по доменам, прожил их живыми запросами (регистрация → чтение → вопрос книге → профиль), оценил 5 кандидатов на первый «настоящий» экран нового frontend'а.

2. **Что нашёл** — ядро читателя (спросить книгу / читать главы / профиль читателя) — самый сильный кандидат: контракты стабильны, работают даже без LLM-ключей (Pulse+RAG отвечает сам), зависимостей от других доменов нет. Попутно вскрылись 3 факта, которые SPEC обязан зафиксировать: конверты ответов у book-домена НЕоднородны (часть direct, часть enveloped), у `/v1/stream` (LLM-шлюз) в этой среде нет ключей провайдеров — он пуст, а `/book/genome` потерялся в RBAC-матрице из-за известной суффикс-коллизии (нужно правило: route-guard по нему не строить).

3. **Что предлагаю** — F2 = «Диалог с книгой» (3 экрана: спросить, читать, профиль): минимальный полный пользовательский цикл на стабильных контрактах, без единого изменения backend'а.

---

## §1 Domain inventory (по 289 путям)

### Домены и их реальные API (жирным — активные/стабильные)

| Домен | Путей | Ключевые endpoints | Контракт | RBAC | Realtime |
|-------|-------|--------------------|----------|------|----------|
| **reader-core (диалог/чтение)** | ~14 | `/book/ask`, `/book/chapters`, `/book/text`, `/book/layers`, `/book/genome`, `/book/reader/profile`, `/book/reader/history`, `/book/reader/reading-event` | `BookAskRequest{question,context?,messages?}` → `SuccessResponse{data{answer,source,provenance,pulse_confidence,llm_used,mood,suggestion}}`; chapters/text/history — **enveloped** `{ok,data}`; layers/genome/profile — **direct** | reader | WS `new_question`/`your_question_answered`/`chat_response` (но ask — синхронный JSON) |
| v1-LLM-gateway | 2 | `/v1/chat`, `/v1/stream` | SSE OpenAI-style; **в этой среде пуст/500: нет ключей gigachat/openrouter** | API-key/JWT/HERMES (матрица: пусто=public-gate внутри verify_request) | это и есть SSE |
| community | 28 | interpretations/artifacts/timeline + comments/likes | InterpretationRequest и др.; GET public, POST reader | GET public, POST reader | — |
| temporal (M10/M10.2) | 14 | `/book/temporal/chain`, `/book/temporal/pending-updates*` | direct-конверты | chain: reader+ (матрица: пусто→public-gate), pending-updates: admin/editor/reader по операциям | — |
| world-explorer | 21 | explore/cache/stats | ExplorationRequest | в основном public/reader | — |
| assets/film/story/research (студия) | ~40 | generate/list/queue | typed-requests | editor;reader (генерация), админ-очистка | очереди через WS `service_status` |
| os (книгохранилище) | 19 | documents/ingest/index/search | SearchRequest | ingest: editor;reader | — |
| presence/email/crowdfunding | ~25 | suggestions/trending/drafts/campaigns | typed | presence: editor; trending: reader; email: editor | WS `new_suggestion`, `crowdfunding_milestone` |
| auth/admin/api-keys/invite | ~20 | admin CRUD | typed | admin | — |
| xray (observability) | ~20 | stats/traces/events/stream | SSE typed events | админ-панель: admin (матрица: несколько путей public) | SSE `/xray/events/stream` |
| _ui (HTMX server-side) | 11 | Jinja2-страницы | HTML — НЕ для SPA | mixed | — |
| прочее (health/metrics/robots/sitemap) | ~8 | — | direct | public | — |

### Ключевые контрактные факты (live-проверено)

1. **`POST /book/ask`** — синхронный JSON: `{ok:true, data:{answer, source:"knowledge:rag:catalog", provenance[], pulse_confidence, llm_used, mood, suggestion}}`. **Работает без LLM-ключей** (Pulse+RAG отвечает сам) — живой ответ получен: содержательный, с провенансом.
2. **Конверты НЕоднородны внутри book-домена:**
   - enveloped: `/book/chapters`, `/book/text` (пагинация в конверте: `{ok,data,offset,limit,total,has_more}`), `/book/reader/history`
   - direct: `/book/layers`, `/book/genome`, `/book/reader/profile`
   → F1 ENVELOPE_MAP должен расширяться по-эндпоинтно (это и предполагалось дизайном).
3. **`/book/genome` — NOT-IN-RBAC-MATRIX** (одна из 5 известных суффикс-коллизий F1-матрицы: `/genome` матчится и на `/book/genome`, и на `/book/screenplay/genome`; выровнен `/book/screenplay/genome` с roles=reader). **GAP-примечание:** сам backend-роут `/book/genome` — reader (routes/book.py, проверено: getMe reader → 200). Для F2: доступ не через `can()`, а по фактической доступности (backend сам рассудит); route-guard по genome не строить.
4. **`/v1/stream`/`/v1/chat` — aethon LLM-оркестратор**: требуют настроенного провайдера (gigachat/openrouter). В этой среде: stream → 200 + пустой поток; chat → 500 INTERNAL. **Для F2 НЕ использовать** (нестабильный контракт в текущей конфигурации; вопрос книги — через `/book/ask`).
5. **SSE в book-домене нет**: единственные SSE — `/v1/stream` (LLM) и `/xray/events/stream` (observability). Читательский ask — синхронный.
6. **WS-события читателя**: `new_question` (broadcast), `your_question_answered` (user-targeted), `chat_response` (user-targeted) — вызываются бекендом из ask-flow (websocket.py:121-144). F2-использование: индикатор/уведомление, не критический путь.
7. **`/book/reader/reading-event`** — POST reader: mutation для tracking'а чтения (Body_record_reading_event... в схемах).
8. **`/book/reader/profile`** — direct `{reader_id, display_name, questions_total, conversation_count, last_topic, topics[]}` (live-проверено).
9. **`/book/reader/history`** — enveloped `{ok,data[],total}`, query `limit`.

---

## §2 F2 candidate verticals (оценка по критериям)

| Кандидат | Пользовательская ценность | Экраны | API | Cross-domain зависимости | Реализация без backend-правок | Realtime | Риск |
|----------|---------------------------|--------|-----|--------------------------|-------------------------------|----------|------|
| **A. Диалог с книгой (ask + чтение глав + профиль читателя)** | **Максимальная**: ядро продукта «цифровое сознание книги» — задать вопрос, получить ответ с провенансом, читать первоисточник | 3: Спросить (/), Чтение глав (/reading), Профиль (/profile) | ask, chapters, text, layers, genome, reader/profile, reader/history, reading-event | **Нет** (self-contained) | **Да** (все контракты live-проверены) | WS-пульс уже в Topbar; your_question_answered — опционально | Низкий: контракты стабильны, ask работает без LLM |
| B. Сообщество (интерпретации/артефакты) | Средняя: чтение интерпретаций | 2-3 | interpretations, artifacts (GET public) + POST reader | Низкие | Да | — | Средний: 28 путей, модерация, генерация артефактов — новый UX без F1-паттерна |
| C. Temporal-модель мира (M10/M10.2) | Средняя: «время мира» — уникальная фича | 2-3 | temporal/chain, pending-updates | Нет | Да | — | Средний: M10.2-очередь = editor-flow, не reader; mixed-конверты |
| D. World-Explorer | Средняя: исследование мира | 2-3 | 21 путь explore | Нет | Да | — | Средний: сложный state (15 этапов), heavy-контракты |
| E. Студия (assets/film) | Низкая для первой vertical (editor-only) | 3-4 | assets/generate + queue | Средние (провайдеры) | Да | WS queue-статусы | Высокий: генерация требует провайдеров (в этой среде ComfyUI-зависимости) |

### Почему A (Диалог с книгой)

1. **Максимальная польза**: «спроси книгу» — сердце продукта. Пользователь получает ценность с первого экрана.
2. **Стабильные контракты**: все 8 endpoints live-проверены (§1-факты), ask отвечает через Pulse+RAG даже без LLM.
3. **Минимум cross-domain зависимостей**: ноль — читает и спрашивает, ничего не ждёт.
4. **Полноценная E2E**: register → ask → чтение ответа → чтение главы → профиль с историей — полный цикл проверяем end-to-end.
5. **Без backend-правок**: GAP-чек §7 — не требуется ничего.
6. **Максимум переиспользования F1**: StateView (loading/error/retry для ask), ApiError (обе error-модели), auth-cookie, WS-онлайн-бейдж, react-query, навигация (пункты «Спросить книгу» и «Чтение» уже в NAV_GROUPS как coming-soon → активируются).
7. B/C/D/E — не отбрасываются: остаются кандидатами F3+; community — идеальный третий (публичное чтение), temporal — после стабилизации reader-core.

---

## §3 Рекомендуемый F2 scope — «Диалог с книгой»

**Vertical:** читатель входит → спрашивает книгу (синхронный ответ с source-бейджем и провенансом) → читает главы → видит свой профиль/историю.

**В scope:**
- Экран «Спросить книгу» (замена foundation-дашборда `/` на домашний экран диалога): input вопроса, популярные вопросы (top из profile.topics), синхронный ответ, бейдж источника (`source`, `pulse_confidence`, `llm_used`), провенанс-список.
- Экран «Чтение» (`/reading`): список глав (chapters), чтение выбранной главы (`/book/text` пагинацией), фиксация reading-event.
- Экран «Профиль» (`/profile`): профиль читателя (questions_total, conversation_count, topics), история вопросов.
- ENVELOPE_MAP-расширение: 8 новых записей (по фактическим конвертам §1-факт 2).
- Typed-контракты: `contracts/book.ts` (ask/chapters/text/layers/genome) + `contracts/reader.ts` (profile/history/reading-event) — ручная типизация по live-JSON (schema у части — пустая `{}`).
- Навигация: активация пунктов `ask` и `read` (сейчас coming-soon), пункт `profile`.
- WS: опциональный toast на `your_question_answered`/`new_question` (не критический путь).

**Не в scope (non-goals):** /v1/stream-чат (нестабильный LLM-контракт), community, temporal, world-explorer, студия, admin, mock-механики, SSE-стриминг ответов (ask — синхронный), изменения backend/RBAC/M10/M10.2.

---

## §4 Проверка F1 foundation против vertical A

| Требование | F1-компонент | Вердикт |
|------------|--------------|---------|
| Routing | (main)-layout + AuthGuard, 4 страницы | ✅ достаточно (новые маршруты добавляются в (main)) |
| Auth | AuthProvider + cookie + 401→login | ✅ (register/me/logout live-проверено) |
| API client | client.ts + ApiError + retry | ✅ достаточно |
| Generated types | schema.d.ts (289 путей) | ✅ есть, но ask/chapters/text имеют пустые response-schema → **ручная типизация по live-JSON (штатный F1-паттерн)** |
| RBAC | can() + NAV_GROUPS + RoleGate | ✅ достаточно; genome-гейт НЕ строить (§1-факт 3) |
| Errors | ApiError обе модели | ✅ |
| Loading/empty/error | StateView | ✅ |
| SSE/WS | ws-client + WsProvider + sse-парсер | ✅ достаточно (WS-онлайн-бейдж уже работает; toast-хук useWsEvent есть) |
| **GAP-кандидаты** | — | **Не выявлено F2-prerequisites вне F1**: единственное расширение — ENVELOPE_MAP-записи (это данные, не код-архитектура) и typed-contracts (новые файлы в существующем паттерне). F1-код менять не нужно. |

---

## §5 F1 findings impact

| Finding | Вердикт | Обоснование |
|---------|---------|-------------|
| **WS reconnect race** (ws-client.ts:66-70) | **DOES NOT BLOCK F2** | F2-использование WS — пассивное (онлайн-бейдж + опциональный toast): reconnect-after-disconnect не искажает данные, только может держать соединение живым после unmount. Worst-case в F2-сценариях — лишний reconnect. Фикс — backlog F2 (одна строка: intentionalClose-флаг), выполняется попутно с F2-задачей WS-toast, не отдельным milestone'ом. |
| **Login render-side-effect** (login/page.tsx:47-49) | **DOES NOT BLOCK F2** | Касается только Telegram-token-login-пути. F2-vertical его не расширяет (вход уже работает через register/dev); двойной POST в StrictMode — dev-феномен, prod-сборку не затрагивает. Фикс — backlog F2 (useEffect+ref-guard), не блокирует ask/reading/profile. |

Обе находки остаются в F2-backlog (см. §Backlog ниже).

---

## §6 Legacy boundary (что можно как isolated reference)

Легально переносить как **reference/инфраструктуру** (class A, без архитектуры):

| Legacy-артефакт | Использование в F2 |
|-----------------|--------------------|
| `arkaim-web/src/shared/lib/useStreamingChat.ts` | **НЕ переносить в F2**: ask — синхронный; streaming актуален только для /v1 (вне scope). Отложенный reference для F4+ |
| `arkaim-web/src/shared/lib/ws.ts` | Уже портирован в F1 (ws-client). Не трогаем |
| SourceBadge UI-паттерн (`ui/SourceBadge.tsx`) | **Reference-паттерн** для бейджа источника ответа (pulse/llm/hybrid) — пере-реализовать в v2-стиле, не копипастить |
| Страница /ask legacy | Только как эталон UX-композиции (минималистичный input + popular questions); **не переносить код/архитектуру** |
| Mock-слой (`api.ts` MOCK_DATA) | **Запрещён** (красная линия) |
| Страницы/widgets legacy | Не переносить |

---

## §7 Backend gap check — **GAP NOT FOUND (STOP не требуется)**

Vertical A использует только существующие контракты:

| Endpoint | Контракт | RBAC-правка нужна? | M10/M10.2 затронуты? |
|----------|----------|--------------------|----------------------|
| POST /book/ask | BookAskRequest→SuccessResponse | Нет (reader) | Нет |
| GET /book/chapters | enveloped list | Нет (reader) | Нет |
| GET /book/text | enveloped пагинация | Нет (reader) | Нет |
| GET /book/layers | direct | Нет (reader) | Нет |
| GET /book/genome | direct (BookGenomeResponse) | **Нет** — доступ без can()-гейта (см. §1-факт 3) | Нет |
| GET /book/reader/profile | direct (ReaderProfileResponse) | Нет (reader) | Нет |
| GET /book/reader/history | enveloped | Нет (reader) | Нет |
| POST /book/reader/reading-event | Body_record... | Нет (reader) | Нет |

**Ни одного нового endpoint'а, изменения контракта, RBAC или M10/M10.2 не требуется.** Все ответы (включая error-форматы) уже покрыты F1 ApiError-моделью.

---

## F2 BACKLOG (фиксация по решению владельца от 2026-09-09)

Из F1-аудита, **не исправляются сейчас**:

| # | Finding | Severity | Файл/строка | Когда |
|---|---------|----------|-------------|-------|
| F2-B1 | WS reconnect race после disconnect | Medium | ws-client.ts:66-70 | F2 (попутно с WS-toast) |
| F2-B2 | Login render-side-effect (двойной POST в StrictMode) | Medium | login/page.tsx:47-49 | F2 |
| F2-B3 | openapi-fetch установлен, но не используется | Low | package.json | F2 (удалить или начать использовать) |
| F2-B4 | 5 RBAC-суффикс-коллизий (вкл. /book/genome) — can()=false (deny-safe) | Low | dump_rbac_matrix.py / matrix.ts | F2+: ручное разрешение в слепке |
| F2-B5 | Комментарий AuthProvider «снимает cookie» — неточен | Cosmetic | AuthProvider.tsx:7 | F2 попутно |

---

## Вердикт аудита

**F2 vertical = «Диалог с книгой» (ask + чтение + профиль читателя)** — рекомендован как единственный scope F2.

Обоснование-выжимка: максимальная пользовательская ценность (ядро продукта), 100% стабильных live-проверенных контрактов, ноль cross-domain зависимостей, ноль backend-изменений (GAP NOT FOUND), полное покрытие F1-foundation, полноценная E2E-проверяемость.

**STOP: implementation не начата. Жду ACCEPTED на F2_SPEC.**
