# F3 IMPLEMENTATION REPORT — «Время мира»

**Дата:** 2026-09-10
**Статус:** IMPLEMENTED → TESTED → VERIFIED. Ждёт решения владельца.
**Основа:** `docs/F3_PRE_IMPLEMENTATION_AUDIT.md` (ACCEPTED) + задача владельца Phase 1 GO.

---

## Простыми словами

1. **Что было целью?** — построить читателю экран «Время мира» (цепочка эпох книги с указанием происхождения каждого факта и сценариями будущего) и редактору — рабочее место «Temporal-очередь» (предложения по времени мира: подтвердить/отклонить).

2. **Что реально сделано?** — два новых экрана, полностью работающие на живом backend: цепочка из 12 эпох с бейджами происхождения (канон автора / внешний источник / гипотеза), якорь «Эпоха Аркаима» с двойным происхождением, «Современность» отдельно (точка наблюдателя, не эпоха), сценарии будущего с обязательной пометкой «это проекция, не предсказание», панель деталей эпохи. Плюс editor-экран очереди: сканирование книги, список находок, подтверждение/отклонение, счётчики, история. Плюс два маленьких фикса качества с прошлого этапа (честный процент чтения при прокрутке; понятная подсказка «вопрос слишком короткий» вместо технической ошибки).

3. **Что получилось?** — **PASS**: все проверки зелёные (67 тестов, линт, strict-компиляция, сборка из 10 страниц, 14/14 живых проверок, контрактная верификация). Backend не тронут ни одной строкой.
   *Post-audit-уточнение (F3 FOLLOW-UP):* «67 тестов» относилось к прогону стандартного раннера на момент реализации — в его список НЕ были зарегистрированы два новых F3-файла (temporal, provenance-badge); при их отдельном прогоне 4 ассерта падали из-за механики раннера (не продукта). В ходе FOLLOW-UP оба файла зарегистрированы, ассерты исправлены: штатный прогон = **85/85** (67 прежних + 18 F3-тестов). Подробности: `docs/F3_POST_AUDIT_FOLLOWUP_REPORT.md`.

4. **Есть ли проблемы?** — одна, честно задокументированная: живую editor-проверку кнопок «Подтвердить/Отклонить» через HTTP не сделать (в проекте нет способа создать editor-сессию снаружи — только одноразовые токены от Telegram-бота). Эта часть прикрыта backend-тестами (426 строк pytest) и код страницы идентичен проверенным паттернам. Серьёзность — низкая: риск ограничен UI-обвязкой, серверная логика подтверждена своими тестами.

5. **Что предлагается дальше?** — принять F3 (или заказать независимый пост-аудит, как после F2). Следующий логичный шаг после принятия — по вашей дорожной карте; я ничего не начинаю сам.

---

## 1. Objective

F3 «Время мира» — вторая domain-vertical нового frontend (arkaim-web-v2): читатель исследует время мира книги, editor управляет temporal-очередью M10.2. Только frontend; backend = 0 правок.

## 2. Scope (по принятому audit §2)

| Пункт scope | Статус |
|-------------|--------|
| 1. Экран «Время мира» (цепочка, provenance-бейджи, якорь, Современность, сценарии, FUTURE_EXTRAPOLATION-бейдж) | ✅ |
| 2. Экран «Temporal-очередь» (scan/pending/confirm/reject/history/stats; строго M10.2-контракты) | ✅ |
| 3. Типизированные контракты + 9 envelope-записей | ✅ (14 записей — все temporal-пути) |
| 4. ProvenanceBadge — единый UI-компонент | ✅ |
| 5. Активация навигации (temporal, temporal-queue) | ✅ |
| 6. F2-A1 (scroll-%) + F2-A2 (min_length=3) | ✅ |
| 7. Тесты F3 | ✅ (3 файла: temporal, provenance-badge, rbac-обновление) |
| 8. Smoke/live verification | ✅ (f3-live-smoke.mjs 14/14) |

## 3. Implemented

**Экран `/temporal` (reader+):**
- Цепочка эпох — Timeline из `GET /chain` (12 узлов, 11 PRECEDES-связей; переключение направления FORWARD/BACKWARD);
- Якорь Аркаима — золотая метка + двойной provenance (AUTHOR_CANON 1.0 «КНИГА.md» + EXTERNAL_SOURCE 0.7 «ARCHAEOLOGY.json» — B1/C1-обогащение живо отображается);
- «Современность» — отдельная карточка «точка наблюдателя» (HYPOTHESIS-бейдж, bounds 2025 CE), ВНЕ цепочки — с прямым текстовым объяснением инварианта;
- Детали эпохи — `GET /context/{id}`: описание, счётчики (события/персонажи/технологии), списки;
- «Будущее мира» — `POST /future-extrapolation`: до 3 сценариев с совместимостью/риском; **каждый сценарий — бейдж FUTURE_EXTRAPOLATION**; provenance_note внизу;
- Финальный Alert «страница отображает только связи и происхождение, которые заданы бэкендом» — инвариант виден пользователю.

**Экран `/temporal/queue` (editor+, RoleGate на URL):**
- Scan (M10-цепочка: детектор→извлечение→pending; idempotent) с честным отчётом «книга не менялась»;
- Pending-список (FindingView: raw_text, категория-бейдж, строка, kind, контекст, confidence);
- Confirm — Popconfirm с объяснением серверного gate («Находка будет применена к модели мира»);
- Reject — причина до 500 символов (backend RejectRequest);
- Stats-счётчики + Tabs «Ожидают/История» (confirmed/rejected с reason);
- Подпись об in-memory природе очереди (O2-факт для editor).

**Инфраструктура:**
- `contracts/temporal.ts` — 11 typed-функций, 16 интерфейсов, doc-комментарии с live-фактами;
- `ENVELOPE_MAP` +14 temporal-записей; **расширение `envelopeOf` — template-матчинг path-параметров** (`{epoch_id}`, `{finding_id}`) — первые path-param контракты в проекте (exact-приоритет сохранён: /stats,/history,/scan не съедаются шаблонами);
- `ProvenanceBadge` + `ProvenanceBadgeList` (дедуп по категории, max-confidence) — точное зеркало backend-словаря `SOURCE_CATEGORY_LABELS` (source_levels.py:114-155): «Авторский канон»/green, «Внешний источник»/orange, «Реконструкция»/purple, «Гипотеза»/gold, «Будущее extrapolation»/magenta, «Производное»/blue, «Художественная модель»/cyan, «Неизвестно»/default;
- Навигация: `temporal` → href /temporal (ALL), `temporal-queue` → /temporal/queue (editor/admin);
- F2-A1: scroll-метрика = фактическая прокрутка контейнера главы (rect.top/scrollHeight), пересчёт при догрузке чанков, сброс при выходе; вместо старого «% загруженного текста»;
- F2-A2: гейт <3 симв. + подсказка «Вопрос должен быть не короче 3 символов» (под pydantic min_length=3, live-подтверждено: len=2 → 422).

## 4. Files changed

**15 файлов, все в arkaim-web-v2 (backend 0, legacy 0, docs 0):**

NEW (6):
- `arkaim-web-v2/src/app/(main)/temporal/page.tsx` — экран «Время мира»;
- `arkaim-web-v2/src/app/(main)/temporal/queue/page.tsx` — экран «Temporal-очередь»;
- `arkaim-web-v2/src/shared/api/contracts/temporal.ts` — typed-контракты;
- `arkaim-web-v2/src/shared/ui/ProvenanceBadge.tsx` — provenance-бейджи;
- `arkaim-web-v2/tests/unit/temporal.test.ts` — контракты+инварианты;
- `arkaim-web-v2/tests/unit/provenance-badge.test.ts` — бейджи;
- `arkaim-web-v2/scripts/f3-live-smoke.mjs` — live-проверка (14 проверок).

EDIT (7):
- `envelope.ts` (+14 записей + template-матчинг), `index.ts` (реэкспорт), `navigation.ts` (2 пункта), `page.tsx` (A2), `reading/page.tsx` (A1), `rbac.test.ts` (активные пункты), `temporal.test.ts` (правка unused-import).

REGENERATED (2, без содержательных правок — contracts.mjs-скрипт):
- `generated/schema.d.ts`, `generated/matrix.ts`.

Runtime-артефакты запуска backend (не source): `core/CORE/genome/history/*2026-09-10*` (штатный снапшот каждого запуска — плодится с 08.07.2026; untracked), `runtime/logs/core.log`, sqlite-wal/shm. Проверено git-статусом: untracked/ignored.

## 5. Tests

| Батарея | Результат |
|---------|-----------|
| Unit (run-tests.mjs, все 12 файлов) | *Post-audit-уточнение (F3 FOLLOW-UP):* на момент реализации в списке раннера было 10 файлов — F3-файлы (temporal, provenance-badge) НЕ были зарегистрированы; их отдельный прогон давал 8 PASS / 4 FAIL (механика раннера: отсутствие toMatch/.not в шиме, .tsx-импорт, toString-ассерт). В FOLLOW-UP файлы зарегистрированы, 4 ассерта исправлены без ослабления; штатный прогон = **85/85 PASS** (temporal 11, provenance-badge 7 — оба исполняются раннером; F1/F2-регрессия 67/67 без изменений) |
| Lint (eslint) | **0 errors, 0 warnings** |
| TypeScript strict (tsc --noEmit) | **0 ошибок** |
| Production build (next build) | **10 маршрутов** (8+2 temporal), без ошибок |
| Contract verification (contracts.mjs) | **OK** (schema.d.ts+matrix.ts регенерированы) |

Новые тесты покрывают: envelope-записи (14, все enveloped), path-param template-матчинг, exact-приоритет статических путей, отсутствие media-примесей в temporal-контрактах, инвариант «не синтезирует связи» (контракт-модуль не содержит generate/synthesize-функций; код контракта не оперирует temporal_today), M10.2-сигнатуры (7 функций очереди), wire-тело future-extrapolation (max_futures в POST-запросе), зеркало SOURCE_CATEGORY_LABELS (8 категорий, сверка FE↔BE 1:1), UNKNOWN-fallback, дедупликацию бейджей.

## 6. Regression

- Все F1/F2-тесты в прогоне 85/85 (auth, book, reader, contracts, errors, rbac, sse, ws, source-badge, login-b2 + temporal, provenance-badge после FOLLOW-UP-регистрации);
- rbac.test обновлён по новому факту: активные пункты = ask/read/profile/status/temporal/temporal-queue; reader видит temporal, НЕ видит temporal-queue; editor видит оба (тест F3 явно);
- contracts.test (openapi 289 путей, ENVELOPE_MAP только существующие пути, nav→openapi) — зелёный: новые nav-href указывают на существующие маршруты;
- backend-тесты не запускались (не тронуты — 0 правок);

## 7. Live/Smoke (f3-live-smoke.mjs — 14/14 PASS)

| # | Проверка | Факт |
|---|----------|------|
| 1 | register → cookie | 200 |
| 2 | /chain | enveloped, 12 эпох, 11 связей |
| 3 | Якорь Аркаима двойной provenance | AUTHOR_CANON + EXTERNAL_SOURCE (B1/C1) |
| 4 | /nodes | 13 узлов (12+today) |
| 5 | temporal_today | HYPOTHESIS, is_anchor=false |
| 6 | **ИНВАРИАНТ: today не в relations** | подтверждено живыми данными |
| 7 | /context/arkaim_era | {temporal_node, epoch, events, characters, technologies} |
| 8 | future-extrapolation | 3 сценария, provenance FUTURE_EXTRAPOLATION |
| 9 | Сценарные поля | compatibility_score, risk_level |
| 10-11 | pending/stats (reader-просмотр) | {ok, data, total} / {pending, confirmed, rejected} |
| 12 | reader → confirm | **403** (RBAC) |
| 13 | reader → scan | **403** (RBAC) |
| 14 | /chain без сессии | 200 (публичное GET-чтение — факт матрицы roles:[]) |

**Editor-flow HTTP-проверка (scan/confirm/reject живыми кнопками) не выполнима:** в системе нет внешнего способа создать editor-сессию (одноразовые токены выдаёт Telegram-бот). Компенсация: M10.2-backend подтверждён собственным pytest-суитом (426 строк: confirm/reject/scan/reader-403/history), UI использует ровно эти контракты; риск локализован UI-обвязкой. Зафиксировано как ограничение верификации (не дефект).

## 8. DoD checklist (audit §3)

| # | Критерий | Доказательство |
|---|----------|----------------|
| 1 | Экраны на живом backend | smoke 14/14 |
| 2 | Unit зелёные | 85/85 (после FOLLOW-UP: F3-файлы зарегистрированы в раннере, 4 ассерта исправлены; прежние 67 — без изменений) |
| 3 | lint+tsc strict | 0/0 |
| 4 | Production build | 10 маршрутов |
| 5 | contracts:verify | OK |
| 6 | Backend не тронут | forensic §10: py=0 |
| 7 | Фронт не синтезирует связи; today вне оси | тесты + smoke#5,6 + код (Timeline рендерит только nodes; today-карточка отдельна) |
| 8 | C2/TA/MB не тронуты | forensic §10 |
| 9 | F2-A1/A2 | код+тест; A2 live-факт 422@len<3 |
| 10 | RBAC | reader 403 confirm/scan (smoke), RoleGate на /queue URL, nav-тесты |

## 9. Provenance verification

- Лейблы/цвета — **зеркало SOURCE_CATEGORY_LABELS** (сверено построчно с source_levels.py:114-155): 8 категорий точно; тест `provenance-badge.test.ts` фиксирует соответствие;
- FUTURE_EXTRAPOLATION — обязательный бейдж каждого сценария (ADR Decision C): рендер в заголовке каждой карточки сценария + тест различимости от HYPOTHESIS;
- Фронт не создаёт свою provenance-систему: категории только из ProvenanceTag.category backend; UNKNOWN-fallback для незнакомых категорий (не выдумывает).

## 10. Temporal invariant verification

1. **Цепочка рендерится только из backend nodes/relations** — Timeline строится из `chain.data.nodes`; связи не пересчитываются; тест: контракт-модуль без generate/synthesize-функций.
2. **Present→Arkaim не рисуется**: temporal_today живёт только в отдельной карточке «точка наблюдателя»; в relations бэкенда его нет (smoke #6 живыми данными); код страницы не содержит логики today→эпохи.
3. **Today ≠ эпоха цепочки**: карточка с явной подписью «не эпоха исторической цепочки и не источник связей».
4. **Temporal read-only**: фронт вызвает только GET-чтение и два editor-POST (M10.2-мутации очереди); WorldModel меняет только серверный confirm-gate.
5. **C2/TA-1/TA-2 не реализованы**: 0 правок в temporal-коде (forensic).

## 11. Scope boundary verification

| Граница | Проверка | Результат |
|---------|----------|-----------|
| Backend files | mtime+git по *.py | **0** |
| Legacy arkaim-web/ | mtime+git | **0** |
| Media Direction Foundation (ADR, MEDIA doc, MD-код) | mtime | **0** |
| Temporal API/backend/data (WORLD_MODEL.json 16.07, routes, core temporal) | mtime+git | **0** |
| Master Roadmap | mtime | **0** |
| C2/TA/MB-deferred | не выполнялись | ✅ |
| Новые зависимости | package.json нетронут | ✅ |
| Все 15 файлов — только F3-scope | построчная сверка с audit §6 | ✅ (каждый файл соответствует пункту scope) |

Tracked-diff (43 файла) — pre-existing base до F3 (зафиксирован прошлыми аудитами); весь arkaim-web-v2 — untracked с рождения; мой F3 не добавил ни одного tracked-изменения.

## 12. Out-of-scope findings (зафиксировано, НЕ исправлено)

1. **Editor-HTTP-верификация невозможна без одноразового токена** — ограничение среды (см. §7). Кандидат на будущее: dev-путь editor-сессии для e2e — вне F3.
2. `/chain` публичен без сессии (roles:[] в матрице) — это фактический backend-контракт (все GET-чтения книги таковы); smoke-проверка скорректирована на факт. Отмечаю для владельца: если публичность temporal-чтения нежелательна — это backend-решение вне F3.
3. `context/arkaim_era` возвращает events=0, characters=0 (данные WorldModel по эпохе пусты) — экран корректно показывает нулевые счётчики; наполнение — домен данных, не фронт.
4. Дубль-глыба genome/history при каждом запуске backend (6 файлов за сегодня) — runtime-поведение, не source; вне F3.

## 13. Final verdict

**F3 «Время мира» — IMPLEMENTED & TESTED & VERIFIED.** Все 8 пунктов scope выполнены; 85/85 тестов (после FOLLOW-UP-регистрации F3-файлов; F1/F2-часть 67/67); 14/14 live-smoke; сборка чистая; backend/legacy/media/temporal-data — 0 изменений; инварианты ADR §5 соблюдены и протестированы. Единственное ограничение — editor-HTTP-smoke (компенсирован backend-pytest и контрактным совпадением).

**STOP.** Жду решения владельца: ACCEPTED / пост-аудит / правки. MD-2, C2, студия — не начинались.
