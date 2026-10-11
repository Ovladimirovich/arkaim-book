# F2 IMPLEMENTATION PLAN — «Диалог с книгой»

**Статус:** EXECUTED — F2 закрыт (F2 — ACCEPTED & CLOSED, решение владельца от 2026-09-09; план выполнен полностью, post-audit: PASS WITH FINDINGS)
**Дата:** 2026-09-09
**Вход:** F2_SPEC (§1–15); F1-foundation (готов, PASS); F2-backlog B1–B5 (включены как задачи плана).
**Порядок:** шаги 0→1→2→3→4→5→6→7; проверки после каждого шага; финальная батарея — по DoD F2_SPEC §13.

---

## Шаг 0 — Live-проба недоопределённых контрактов (read-only)

Прочитать live-JSON у двух недоопределённых точек (fresh-пользователь не даёт данных — нужен пользователь с историей):
- `GET /book/reader/history` после ≥1 ask (формат элемента data);
- `POST /book/reader/reading-event` (request/response-shape по Body-схеме OpenAPI + live);
- повторно `GET /book/layers` — зафиксировать полный набор ключей (knowledge_layer + прочие слои).

**Выход:** дополнение F2_SPEC §4 живыми шейпами (запись в SPEC до кода).
**Проверка:** SPEC-факты не противоречат live-ответам.

## Шаг 1 — Контракты (данные, не архитектура)

Файлы:
- `src/shared/api/envelope.ts` — +8 записей ENVELOPE_MAP (F2_SPEC §5);
- `src/shared/api/contracts/book.ts` — ask, chapters, text, layers, genome (типы по live-JSON + OpenAPI-имена);
- `src/shared/api/contracts/reader.ts` — profile, history, reading-event;
- `src/shared/api/index.ts` — реэкспорт.

Паттерн: как `contracts/auth.ts` F1 (apiCall + ручные типы; никакой новой архитектуры).

**Выход:** контракт-слой домена.
**Проверка:** unit-тест contracts (map-записи существуют в OpenAPI; шейпы против фикстур live-JSON).

## Шаг 2 — F1-backlog-фиксы B1+B2 (утверждённые Medium)

- **B1:** `ws-client.ts` — поле `intentionalClose` в disconnect(); `onclose` → reconnect только если не intentionalClose. Обновить ws-client.test.ts (fake-timers: после disconnect — 0 reconnect'ов).
- **B2:** `login/page.tsx` — urlToken-обработка в `useEffect` + ref-guard (однократный вызов); тест-счётчик вызовов (mock-transport).
- Попутно (по усмотрению): B5 комментарий AuthProvider; B3 (openapi-fetch) — решение: удалить dep (чистый package.json) или оставить для F4; решение отразить в отчёте.

**Выход:** B1/B2 закрыты тестами.
**Проверка:** полный unit-прогон; lint; tsc.

## Шаг 3 — Навигация + routing

- `navigation.ts`: пункты `ask` (label «Спросить книгу», href `/`), `read` (→ `/reading`), `profile` (→ `/profile`) — `comingSoon: false`; пункт foundation-дашборда → «Статус системы» `/status`.
- Маршруты: `src/app/(main)/reading/page.tsx`, `src/app/(main)/profile/page.tsx`, `src/app/(main)/status/page.tsx` (перенос текущего `(main)/page.tsx`-контента).
- `/` → новый AskScreen.

**Выход:** живая навигация на 4 активных пункта.
**Проверка:** unit: nav-тесты обновлены (reader видит активные ask/read/profile, статус — все); manual: клики по sidebar.

## Шаг 4 — Экран «Спросить книгу» (`/`)

- `entities/book/` или `features/ask/`: AskForm (AntD Input.TextArea + кнопка), AnswerCard (Typography.Paragraph + SourceBadge + ProvenanceList), PopularTopics (из profile.topics — ссылка-кнопки, подставляющие вопрос).
- react-query: `useMutation` ask; после успеха — invalidate `['reader','profile']` и `['reader','history']`.
- StateView: loading-скелет, error+retry (кнопкой — ask дорогой), empty («переформулируйте»).
- timeout: 60с (client opts).
- SourceBadge-компонент v2 (`shared/ui/SourceBadge.tsx`): бейдж source (`knowledge:rag:catalog` → «База знаний», pulse → «Pulse», llm_used=true → «+LLM»), pulse_confidence %-метрика. Legacy-паттерн — reference, код новый.

**Выход:** главный экран продукта.
**Проверка:** unit §11-4 (ask-flow, транспорт-моки); manual live.

## Шаг 5 — Экран «Чтение» (`/reading`)

- ChapterList (chapters → List/Card: title + char_count);
- ChapterReader: выбранный глава → текст инкрементально (`offset`-стек + «ещё»/автоскролл), ReadingTracker → debounce reading-event POST (fire-and-forget);
- StateView на списках/тексте; «назад к главам».

**Выход:** чтение глав с трекингом.
**Проверка:** unit §11-5; manual: открытие главы, пагинация, скролл.

## Шаг 6 — Экран «Профиль» (`/profile`)

- ProfileCard (display_name, вопросы, сессии, last_topic), TopicList (topics[]), QuestionHistory (history limit=20, обновляется после ask).
- StateView; пустая история → StateEmpty («задайте первый вопрос»).

**Выход:** третий экран вертикали.
**Проверка:** unit §11-3; manual.

## Шаг 7 — Тесты + E2E + батарея

- Unit: §11-1…8 (contracts, ask-flow, reading, nav, B1/B2-фиксы).
- E2E (локально): §12-1…5 (register → ask → reading → profile; unauth-redirect; /status-регресс).
- Батарея: lint (0/0), tsc (0), unit-прогон, production build (8 маршрутов: /, /reading, /profile, /status, /login, /register, /no-access, /_not-found), contracts:verify, live-smoke F1 (не регресс), git-check: 0 диффов runtime/core/arkaim-web.
- CI: изменений не требуется (frontend-v2-job уже гоняет lint+tsc+test+build+verify).

**Выход:** полный зелёный прогон.
**Проверка:** DoD-чеклист F2_SPEC §13.

## Шаг 8 — Отчёт

`docs/F2_IMPLEMENTATION_REPORT.md`:
- «Простыми словами» (цель/сделано/PASS-PARTIAL-BLOCKED/проблемы/дальше);
- таблица DoD (13 пунктов);
- B1–B5-статусы (закрыто/решение);
- git-stat: только arkaim-web-v2/ + F2-доки;
- STOP → post-implementation audit владельца.

---

## Объём-оценка

| Категория | Файлов | Примечание |
|-----------|--------|------------|
| Контракты (step 1) | 3 новых + 2 правки | book.ts, reader.ts, index.ts, envelope.ts, contracts.test.ts |
| Навигация/маршруты (step 3) | 4 новых + 2 правки | reading, profile, status, AskScreen; navigation.ts, layout-пункты |
| Экраны (steps 4-6) | ~8-10 новых | ask-фича (4-5), reading (3), profile (2) + SourceBadge |
| Backlog-фиксы (step 2) | 2 правки + 2 теста | ws-client, login + тесты |
| Тесты (step 7) | ~4 новых + 3 правки | ask/reading/profile/счётчики |
| **Итого** | **~20-24 файла, ~1200-1600 строк** | |

## STOP-точки плана

1. После шага 0 — если live-шейпы противоречат SPEC-гипотезам → обновить SPEC, доложить.
2. Любой шаг: потребность backend-правки → STOP + GAP-документ (без workaround).
3. После шага 8 — полная остановка: ждём post-implementation audit.

**План не исполняется до отдельного ACCEPTED F2_SPEC.**
