# F3 PRE-IMPLEMENTATION AUDIT — «Время мира» (temporal vertical)

**Дата:** 2026-09-09
**Аудитор:** DSH-агент (read-only фаза; код не менялся)
**Основа:** `docs/FRONTEND_ARCHITECTURE.md` (master-план фронтенда; F-серия переопределена вертикальным подходом), решение владельца «F3 = Время мира» (дважды подтверждено: этап Temporal ADR и возврат к roadmap), `F2_PRE_IMPLEMENTATION_AUDIT.md` §7 («temporal — кандидат F3+ после стабилизации reader-core» — условие выполнено: F2 ACCEPTED), ADR_TEMPORAL_WORLD_MODEL (ACCEPTED), TEMPORAL API ALIGNMENT B1+C1 (PASS WITH FINDINGS, ACCEPTED).

---

## Простыми словами

1. **Что делал** — нашёл точное определение F3 в дорожной карте, сверил с фактическим состоянием после F2 и Temporal Alignment, прожил все temporal-контракты живыми запросами и изучил код экранов-паттернов F2.

2. **Что нашёл** — противоречие в понятии «F3»: старый план фронтенда называл F3 «Студией», но реальная траектория (вертикальный подход F2 + дважды подтверждённое решение владельца + принятый Temporal ADR/Alignment именно как подготовка F3 «Время мира») делает **F3 = temporal-вертикаль**. Студия остаётся будущей фазой. Всё для F3 готово: контракты стабильны и live-проверены (включая новые B1/C1), backend-границы заморожены, frontend-фундамент F1/F2 покрыт.

3. **Что предстоит** — два читательских экрана («Время мира» — цепочка эпох с provenance-бейджами и сценариями будущего; «Temporal-очередь» для editor — M10.2-confirm/reject-flow) + типизированные контракты + два маленьких backlog-фикса F2-A1/A2 (по отдельному решению владельца — в F3-backlog).

4. **Ноль backend-изменений** — все 14 temporal-путей уже существуют; B1+C1-обогащение сделано; C2/TA-1 не трогаем (вне F3).

---

## 1. F3 objective (по дорожной карте)

**F3 «Время мира»** — вторая domain-vertical нового frontend (arkaim-web-v2): читатель исследует время мира книги (цепочку эпох, якорь Аркаима, provenance каждого факта, сценарии будущего), а editor работает с очередью temporal-предложений M10.2 (scan → pending → confirm/reject → история).

**Происхождение определения:**
- `FRONTEND_ARCHITECTURE.md` §4.1: `/world/temporal` («временные цепочки») — экран нового IA; §11 F-фазы задавали Студию как F3, **однако** фактическая траектория проекта изменила состав фаз: F2 реализовала вертикаль «Диалог с книгой» (кандидат A из F2-PRE-AUDIT §2, а не «Книга/Мир» из старой таблицы фаз). Владелец дважды зафиксировал: «Следующий целевой этап: F3 "Время мира"» (задача Temporal ADR; задача возврата к roadmap). F2-PRE-AUDIT §7: «temporal — после стабилизации reader-core» — условие выполнено.
- **Вывод:** старая §11-таблица фаз описывала план до смены подхода на вертикали; действующее определение F3 = «Время мира». Студия/Предложения-остальное — последующие фазы. Это фиксация факта, не изменение Master Roadmap (документ не правится; порядок фаз уже фактически переопределён владельцем в диалогах F2/F3).

## 2. F3 scope (что входит)

**Reader-часть («Время мира»):**
1. Экран `/temporal` — «Время мира»: цепочка эпох (12 узлов, 11 PRECEDES, направление FORWARD/BACKWARD — traversal-switch), карточки эпох (label, bounds, is_anchor), **якорь Аркаима** (canonical, provenance AUTHOR_CANON+EXTERNAL_SOURCE после C1), **«Современность»** (temporal_today — отдельная опорная точка наблюдателя с HYPOTHESIS-бейджем, НЕ в цепочке), provenance-бейджи каждой эпохи (категория+confidence из SOURCE_CATEGORY_LABELS-семантики).
2. Сценарии будущего: панель «Будущее мира» — POST /book/temporal/future-extrapolation (reader-гейт, без LLM-ключей работает, детерминированно) — сценарии с compatibility/risk + **обязательный FUTURE_EXTRAPOLATION-бейдж** (ADR Decision C: «сценарии без бейджа к показу не допускаются»).
3. Богатый контекст эпохи: выбор эпохи → GET /book/temporal/context/{id} (temporal_node+epoch+events+characters+technologies) — панель «детали эпохи».

**Editor-часть («Temporal-очередь» M10.2):**
4. Экран `/temporal/queue`: POST scan (editor+) → список pending (FindingView: id/kind/raw_text/value/line_number/context/category/confidence) → детали → **confirm** (Popconfirm, editor+) / **reject** (reason ≤500) → счётчики stats → история confirmed/rejected. Только серверные статусы; никаких локальных confirmation-семантик (красная линия R2).

**Инфраструктура:**
5. Typed-контракты `contracts/temporal.ts`: chain/nodes/context/future-extrapolation/pending-updates(scan/list/stats/history/detail/confirm/reject) — по live-JSON (response-schema у части пустые).
6. ENVELOPE_MAP: +9 записей (chain, chains, nodes, context, node/{id}, future-extrapolation, pending-updates×5, reconstruct — по фактическим конвертам, live-проверить шагом 0).
7. Навигация: активация пунктов `temporal` («Время мира», reader) и `temporal-queue` («Temporal-очередь», editor).
8. **F3-backlog (по отдельному решению владельца в закрытии F2):** F2-A1 (scroll-метрика чтения — реальный % скролла вместо loaded-%) и F2-A2 (фронт-валидация длины вопроса ≥3 — под 422 pydantic min_length).

## 3. F3 DoD (критерии завершения)

| # | Критерий | Доказательство |
|---|----------|----------------|
| 1 | Оба экрана работают на живом backend (без моков) | live-smoke: register→chain→nodes(today!)→context→extrapolation→queue(reader-view)→editor-flow |
| 2 | Все unit-тесты зелёные | run-tests.mjs |
| 3 | lint 0/0, tsc strict 0 | npm-батареи |
| 4 | Production build | 8+2 маршрута |
| 5 | contracts:verify | OK (ENVELOPE_MAP + temporal-записи) |
| 6 | Backend не тронут | git/mtime-доказательство |
| 7 | ADR-инвариант §5: **фронт не синтезирует связи**; Present→Arkaim не рисуется; today — вне оси | тест + код-ревью |
| 8 | C2/TA-1/TA-2 не реализованы; MB-* не тронуты | git-аудит |
| 9 | F2-A1/A2 выполнены (если владелец подтверждает backlog в F3) | тесты A1/A2 |
| 10 | RBAC: reader — только свои гейты; editor-действия — за editor-гейтом; confirm/reject — 403 для reader | live-negative |

## 4. Existing implementation (что уже есть — ничего не изобретать)

| Компонент | Источник | Переиспользование |
|-----------|----------|-------------------|
| App Router (main)-layout + AuthGuard | F1 | ✅ новые маршруты в (main) |
| apiCall/ApiError/envelope.ts (query-string-strip) | F1/F2 | ✅ +9 записей в map |
| Контракт-паттерн book.ts/reader.ts (ручная типизация по live-JSON + doc-комментарии) | F2 | ✅ новый temporal.ts |
| StateView loading/empty/error | F1 | ✅ |
| SourceBadge (категория→бейдж) | F2 | **расширение** → ProvenanceBadge (категории AUTHOR_CANON/RECONSTRUCTION/HYPOTHESIS/FUTURE_EXTRAPOLATION/EXTERNAL_SOURCE/DERIVED; ADR Decision C: лейблы/цвета из backend-семантики SOURCE_CATEGORY_LABELS) |
| useMutation + invalidateQueries-паттерн (ask→profile) | F2 | ✅ scan→pending-list, confirm→list+stats+history |
| message.error-обработка ApiError | F2 | ✅ |
| can()/RoleGate/NAV_GROUPS (пункты temporal/temporal-queue уже есть как comingSoon) | F1/F2 | ✅ активация |
| Backend: 14 temporal-путей, B1+C1 (today+enriched anchor), M10.2-контракты | Alignment | ✅ только потребление |

## 5. Gap (что реально реализовать)

1. Экраны `/temporal` и `/temporal/queue` — НЕТ (пункты comingSoon).
2. `contracts/temporal.ts` — НЕТ (0 temporal-записей в ENVELOPE_MAP).
3. ProvenanceBadge — НЕТ (SourceBadge знает pulse/theme/прочее, не provenance-категории).
4. Активация навигации (2 пункта).
5. F2-A1: reading/page.tsx:113-126 — scroll_percent = loaded-% (нужен реальный % на основе scroll-позиции ридера).
6. F2-A2: page.tsx:77 — блокировка только пустого вопроса (нужно ≥3 симв. под backend min_length=3; честная подсказка вместо 422).
7. Тесты: temporal-контракты (envelope/типизация), ProvenanceBadge, экраны-семантика (today-вне-оси, FUTURE-бейдж-обязателен), queue-flow (confirm→invalidate), A1/A2-фиксы.
8. Live-smoke + HTTP-E2E сценарии (паттерн f2-live-smoke/f2-e2e-http).

## 6. Planned files (предположительно)

```
arkaim-web-v2/src/
├── shared/api/contracts/temporal.ts          # NEW: typed-контракты (10 вызовов)
├── shared/api/envelope.ts                    # EDIT: +9 temporal-записей
├── shared/api/index.ts                       # EDIT: реэкспорт
├── shared/ui/ProvenanceBadge.tsx             # NEW: бейдж provenance-категории
├── shared/rbac/navigation.ts                 # EDIT: активация temporal/temporal-queue
├── app/(main)/temporal/page.tsx              # NEW: Время мира
├── app/(main)/temporal/queue/page.tsx        # NEW: Temporal-очередь (editor)
├── app/(main)/reading/page.tsx               # EDIT: F2-A1 (scroll-%)
├── app/(main)/page.tsx                       # EDIT: F2-A2 (min_length=3)
└── tests/unit/temporal.test.ts               # NEW: контракты+семантика
    tests/unit/provenance-badge.test.ts       # NEW
    tests/unit/*: затронутые (navigation — активные пункты; A1/A2)
scripts/f3-live-smoke.mjs                     # NEW (паттерн f2-)
scripts/f3-e2e-http.mjs                       # NEW
```

Оценка: ~10-12 файлов (6 новых, ~6 правок), ~700-900 строк — сопоставимо с F2.

## 7. Explicit exclusions (ВНЕ F3)

- **C2 / TA-1 / TA-2** — deferred (фабрика precedes(), ArkaimAnchor.to_node()) — НЕ трогаем, даже увидев в данных.
- **MB-1..MB-5** (media findings) — вне F3 (MD-этапы).
- **MD-2..MD-5** — не начинаются.
- **/studio/**, **/proposals/presence|email|drafts**, **/community**, **/admin**, **/explorer**, **/world/graph**, **/library** — будущие фазы.
- **/v1/stream-чат** — вне (нестабильный LLM-контракт, наследие F2-решения).
- **Temporal data / WorldModel** — только чтение; никаких правок.
- **temporal_today bounds «2025 CE»** (U3-ADR) — backend-вопрос, не F3.
- **/node/{id} и /context/{id} enrichment-расхождение** (TA-3) — известный предел, F3-UI берёт узлы из /chain и /nodes (обогащённые), /context — для events/characters/technologies.
- Legacy frontend — не трогаем.
- B3/B4-backlog (openapi-fetch, RBAC-коллизии) — не трогаем.

## 8. Dependencies (все закрыты)

| Зависимость | Статус |
|-------------|--------|
| F1 foundation | ✅ ACCEPTED |
| F2 vertical + backlog-решение | ✅ ACCEPTED (A1/A2 → F3-backlog по слову владельца) |
| ADR_TEMPORAL_WORLD_MODEL | ✅ ACCEPTED (инварианты §5 обязательны к UI) |
| Temporal API Alignment B1+C1 | ✅ PASS WITH FINDINGS, ACCEPTED (today в /nodes; якорь обогащён в /chain) |
| M10.2 backend | ✅ ACCEPTED (контракты стабильны, in-memory-природа — индикатор «до перезапуска» по O2) |
| Backend | ✅ заморожен, 0 правок |

## 9. Regression surface (что может сломаться и защищаем)

| Поверхность | Защита |
|-------------|--------|
| ENVELOPE_MAP (18 записей) | только additive-записи; contracts-тест прогоняет все |
| navigation (активные пункты reader) | nav-тесты обновить: reader видит 5 активных (ask/read/profile/status/temporal) |
| /reading (A1-правка) | существующие reader-тесты + новый A1-тест (mock scroll) |
| / (A2-правка) | ask-тесты + A2-тест |
| Build 8 маршрутов | +2 → 10; build-батарея |
| 66 unit | прогон полностью, ожидаемо 66+N |
| Backend | 0 правок; regression-suite не требуется (но live-smoke подтвердит контракты) |

## Вердикт Phase 0

**F3 «Время мира» — GO.** Определение однозначно (владелец×2, ADR-подготовка, F2-трек); зависимости закрыты; контракты live-проверены (включая B1/C1-состояние); gap точно очерчен; exclusions зафиксированы. Backend-изменений: 0.

**Жду подтверждения владельца на Phase 1 (implementation).**
