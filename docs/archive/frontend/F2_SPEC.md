# F2 SPEC — «Диалог с книгой» (первая domain vertical нового frontend)

**Статус:** ACCEPTED — IMPLEMENTED — CLOSED (F2 — ACCEPTED & CLOSED, решение владельца от 2026-09-09)
**Дата:** 2026-09-09
**Основа:** `docs/F2_PRE_IMPLEMENTATION_AUDIT.md` (вердикт: vertical A)
**Source of truth:** backend contracts (`arkaim-web-v2/contracts/openapi.json` 289 путей + `rbac-matrix.json` 298) — БЕЗ изменений
**Принцип:** никакой реализации до отдельного ACCEPTED; backend не меняется.

---

## 1. Scope (что строим)

Вертикаль читателя: **спросить книгу → прочитать ответ с провенансом → читать главы → увидеть свой профиль и историю**.

Три доменных экрана поверх F1-foundation:

1. **`/` «Спросить книгу»** (домашний экран; заменяет foundation-дашборд F1, тот переезжает на `/status`):
   - поле вопроса; отправка `POST /book/ask`;
   - ответ: текст, SourceBadge (`source` + `pulse_confidence` + `llm_used`), список провенанса;
   - «популярные темы» из `profile.topics` (reader/profile);
   - StateView-состояния: loading (задумчивый skeleton), error+retry, пустой ответ.
2. **`/reading` «Чтение»**:
   - список глав (`GET /book/chapters`): title, char_count;
   - чтение выбранной главы (`GET /book/text` пагинацией: offset/limit/has_more);
   - фиксация прогресса `POST /book/reader/reading-event` (глава/событие чтения);
   - StateView для глав/текста.
3. **`/profile` «Профиль читателя»**:
   - карточка профиля (`GET /book/reader/profile`): display_name, questions_total, conversation_count, last_topic, topics[];
   - история вопросов (`GET /book/reader/history?limit=…`).

Инфраструктурные задачи (в рамках F2):
- ENVELOPE_MAP-расширение: 8 записей по фактическим конвертам (см. §5);
- typed-контракты `contracts/book.ts`, `contracts/reader.ts` (ручная типизация по live-JSON);
- активация nav-пунктов `ask`, `read`, `profile` (снятие coming-soon);
- опционально: WS-toast на `your_question_answered`/`new_question` (useWsEvent уже в F1);
- F1-backlog-фиксы B1 (WS-race) и B2 (login-effect) — по решению владельца в F2 (см. F2_PRE_IMPLEMENTATION_AUDIT §Backlog).

## 2. Non-goals (жёсткие)

- ❌ `/v1/stream`/`/v1/chat` LLM-чат (нестабильный контракт в текущей конфигурации — нет ключей провайдеров; SSE-парсер F1 остаётся инфраструктурой);
- ❌ community, temporal, world-explorer, студия, assets, admin — вне F2;
- ❌ любые изменения backend (endpoints, контракты, RBAC, M10/M10.2);
- ❌ mock-механики (mock-on-401 и пр.);
- ❌ streaming-ответов ask (контракт синхронный — не выдумывать);
- ❌ миграция/рефакторинг legacy; перенос legacy-архитектуры;
- ❌ новые state-management фреймворки; persistence кроме backend-вызовов;
- ❌ расширенный UI-полиш (тёмная тема, анимации) — по F4+.

## 3. Domain screens

| Маршрут | Экран | Компоненты | F1-базис |
|---------|-------|------------|----------|
| `/` | Спросить книгу | AskForm, AnswerCard (SourceBadge, ProvenanceList), PopularTopics | (main)-layout, AppShell, StateView |
| `/reading` | Чтение | ChapterList, ChapterReader (пагинация), ReadingTracker | StateView |
| `/profile` | Профиль | ProfileCard, TopicList, QuestionHistory | StateView, RoleGate не нужен (reader-контракт) |
| `/status` | Foundation-дашборд F1 (health/contracts/ws) | — переезд без изменений | сам F1 |

## 4. API contracts (фактические, live-проверенные)

| Endpoint | Request | Response (конверт) | RBAC | Замечания |
|----------|---------|--------------------|------|-----------|
| `POST /book/ask` | `{question: string, context?: string, messages?: []}` | **enveloped**: `{ok, data: {answer, source, provenance[], pulse_confidence, llm_used, mood, suggestion}}` | reader | source-бейдж обязателен в UI |
| `GET /book/chapters` | — | **enveloped**: `{ok, data: [{id, title, char_count, index}]}` | reader | |
| `GET /book/text` | `?offset&limit` | **enveloped**: `{ok, data: string, offset, limit, total, has_more}` | reader | пагинация чанками ~200 символов... фактически backend режет по limit (live: limit=200 → 200 симв. текста, total=116333) |
| `GET /book/layers` | — | **direct**: `{knowledge_layer, identity_layer?, mission_layer?, ...}` (live: ключи knowledge_layer…) | reader | |
| `GET /book/genome` | — | **direct**: BookGenomeResponse `{themes[], characters[], ...}` | reader (backend), **can()-гейт НЕ строить** (матрица-коллизия) | |
| `GET /book/reader/profile` | — | **direct**: `{reader_id, display_name, questions_total, conversation_count, last_topic, topics: [{name, depth, questions}]}` | reader | |
| `GET /book/reader/history` | `?limit` | **enveloped**: `{ok, data: [...], total}` | reader | **Live-факт (шаг 0):** читает conversations-таблицу, которую `/book/ask` не заполняет (ask пишет в ReaderMemory). Для свежего пользователя всегда пуст. История в UI строится из `profile.topics` + `last_question`; endpoint остаётся контрактом (пуст = честная пустота) |
| `POST /book/reader/reading-event` | `{chapter_id, chapter_index, read_seconds, scroll_percent, completed}` (Body-поля) | **enveloped**: `{ok: true}` | reader | live-проверено; пишет в reader-memory → виден в reading-progress/reading-position |
| `GET /book/reader/reading-progress` | — | **enveloped**: `{ok, data: [{chapter_id, chapter_index, first_read_at, last_read_at, read_seconds, completed, scroll_percent}], stats: {chapters_started, chapters_completed, total_seconds}}` | reader | live-проверено — основа «Продолжить чтение» |
| `GET /book/reader/reading-position` | — | **enveloped**: `{ok, data: {chapter_id, chapter_index, scroll_percent, last_read_at}}` | reader | live-проверено — «Продолжить с места» |

Ручная типизация — по live-JSON (OpenAPI response-schema у большинства пустая `{}`) — тот же паттерн, что auth в F1.

## 5. ENVELOPE_MAP-расширение (данные, не архитектура)

```
'POST /book/ask':                'enveloped',
'GET /book/chapters':            'enveloped',
'GET /book/text':                'enveloped',
'GET /book/layers':              'direct',
'GET /book/genome':              'direct',
'GET /book/reader/profile':      'direct',
'GET /book/reader/history':      'enveloped',
'POST /book/reader/reading-event': <по live-пробе>,
```

## 6. Mutations

| Mutation | Endpoint | Оптимистичность | Rollback |
|----------|----------|------------------|----------|
| Задать вопрос | POST /book/ask | нет (синхронный ответ важнее) | react-query invalidate history/profile после успеха |
| Зафиксировать чтение | POST /book/reader/reading-event | нет; fire-and-forget с queue | повтор при ошибке не критичен |

## 7. RBAC

- Все 8 endpoints — reader-контракт (минимальная роль приложения); дополнительный route-guard не нужен: (main)-AuthGuard уже требует сессию.
- `/book/genome`: **без can()-гейта** (суффикс-коллизия матрицы — F2-B4); backend сам авторизует.
- Nav: пункты `ask`, `read`, `profile` — roles: ALL (reader+); включение снимает `comingSoon`.
- Роли editor/admin видят те же экраны (контракт идентичен) — доменной развилки в F2 нет.

## 8. Realtime

- WS `/ws` — уже подключён (онлайн-бейдж F1).
- Опционально (низкий приоритет): toast `your_question_answered`/`new_question` через `useWsEvent` — НЕ критический путь: ask-ответ уже синхронный, WS-событие дублирует.
- SSE — не используется (контракт /v1 вне scope).
- **Никакого polling'а.**

## 9. State model

- Server-state: react-query (ключи: `['book','ask',question]`-mutation; `['book','chapters']`, `['book','text',chapterId,offset]`, `['reader','profile']`, `['reader','history',limit]` — staleTime по стабильности: chapters/text — 5 мин, profile — 60с).
- Client-state: только локальный UI (текущий вопрос, выбранная глава, scroll-позиция) — React useState; **никаких глобальных сторов**.
- Чтение главы — инкрементальная пагинация (useInfiniteQuery или ручной offset-стек).

## 10. Error handling

- Единая ApiError-модель F1 (обе backend-формата уже покрыты).
- 401 → AuthGuard redirect (F1). 403 → /no-access (F1). 5xx → StateView error+retry; ask-ретрай не автоматический (дорогая операция — только кнопкой).
- Пустой ask-ответ (`data.answer` пуст) → StateEmpty с подсказкой переформулировать.
- timeout ask: повышенный (60с — RAG может думать; F1-client позволяет opts.timeoutMs).

## 11. Tests (unit)

1. contracts: 8 новых ENVELOPE_MAP-записей существуют в OpenAPI (расширение contracts.test.ts).
2. book-контракты: ask-request/response shape против live-JSON-фикстуры (mock-транспорт F1-паттерн).
3. reader-контракты: profile/history shape (фикстуры).
4. ask-flow: loading → answer с source-бейджем; error → retry (react-query + StateView, транспорт-моки).
5. reading: chapters → выбор главы → пагинация текста; reading-event fire (mock-transport).
6. nav: пункты ask/read/profile активны для reader (не coming-soon).
7. WS-race-фикс (если B1 делается в F2): после disconnect() не планируется reconnect (fake-timers, расширение ws-client.test.ts).
8. login-effect-фикс (если B2): urlToken-обработка — один вызов (счётчик fetch-мок).

## 12. E2E checks (playwright, локально; в CI не входят как и в F1)

1. register → `/` → задать вопрос → виден ответ с source-бейджем.
2. `/reading` → глава открывается → текст загружается → скролл-пагинация.
3. `/profile` → questions_total вырос после ask (после invalidate).
4. unauth → `/` → redirect /login.
5. `/status` → foundation-карточки живы (регресс F1).

## 13. DoD

1. Все три экрана работают на живом backend'е (register→ask→reading→profile).
2. Unit-тесты: все F1 + новые из §11 — зелёные.
3. tsc strict 0; eslint 0/0 (красные линии F1 сохранены: fetch/WebSocket-бан).
4. Production build: маршруты `/`, `/reading`, `/profile`, `/status`, `/login`, `/register`, `/no-access`, `/_not-found`.
5. contracts:verify — зелёный (слепки не менялись; новая типизация — в src-контрактах).
6. Backend: 0 изменений (git-дифф runtime/core — пустой от F2-работы).
7. ENVELOPE_MAP-расширение протестировано.
8. E2E-сценарии §12 пройдены вручную.
9. Отчёт `docs/F2_IMPLEMENTATION_REPORT.md` (формат «Простыми словами»).
10. Post-implementation audit — отдельным шагом владельца.

## 14. Backend invariants (границы F2)

- Backend, M10, M10.2, RBAC-контракты, realtime-контракты — **не меняются**; любое обнаруженное несоответствие → STOP + GAP-запись (не workaround).
- Слепки contracts/*.json — не переснимаются в F2 (изменений backend нет; если владелец обновит backend отдельно — переснятие согласуется отдельно).
- Legacy — только reference-паттерны (§6 аудита), без копирования кода.

## 15. F2-B1/B2 (закрепление решения владельца)

Оба Medium-фикса **разрешены к выполнению в рамках F2** (по строкам из F1-аудита: ws-client.ts:66-70 intentionalClose; login/page.tsx:47-49 → useEffect+ref-guard), Low-находки B3–B5 — по усмотрению исполнителя попутно. Отдельный cleanup-milestone не создаётся.
