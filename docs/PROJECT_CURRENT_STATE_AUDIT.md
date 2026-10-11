# PROJECT CURRENT STATE AUDIT — контрольный baseline

**Статус документа:** HISTORICAL BASELINE / SUPERSEDED STATUS MAP  
**Дата исходного восстановления:** 2026-09-30  
**Дата контрольной сверки:** 2026-10-01  
**Назначение:** сохранить evidence предыдущего baseline. Текущие статусы определяет `docs/CURRENT_DEVELOPMENT_STATE.md`; при расхождении приоритет имеют фактический код, конфигурация, тесты и live-проверки.

> [!WARNING]
> Раздел «139 passed» относится к историческому набору тестов и не должен автоматически переноситься как текущий результат. При контрольной сверке 2026-10-01 использовались реально существующие целевые тесты.

## 1. Правила чтения baseline

Документ не является доказательством самостоятельно. Доказательствами являются текущий код, конфигурация, тесты, зафиксированные результаты их запуска и явно принятые ADR. При расхождении с `docs/CURRENT_DEVELOPMENT_STATE.md`, `docs/DOCUMENTATION_INDEX.md` или этим документом приоритет имеют код, тесты и принятые архитектурные решения.

`docs/archive/` и явно помеченные HISTORICAL документы сохраняют историю и не создают текущих задач или статусов.

## 2. Границы проекта

- Единственный web frontend проекта — `arkaim-web/`; активный dev-порт: `3000`.
- `arkaim-web-v2/` отсутствует в текущем дереве и удалён как рабочее направление, runtime и архитектура. Сравнение `arkaim-web` с v2 не ведётся.
- Потенциально восстанавливаемые функции бывшего v2 перечислены только в `docs/FRONTEND_RESTORE_BACKLOG.md` и имеют статус **BACKLOG ONLY**.
- Backend — `runtime/` (FastAPI), активный порт `8642`; доменные и вычислительные модули находятся в `core/CORE/`.
- `arkaim-mobile/` существует как отдельный мобильный клиент и не создаёт второго web frontend.
- В актуальной документации `:3001` является только историческим/запрещённым состоянием, если явно не упомянут как запрет.

## 3. Текущий frontend/backend state

### Frontend

- `arkaim-web` содержит Next.js App Router, страницы Book, Ask, Reading, World Engine, Temporal, History и служебные разделы.
- `SourceBadge` присутствует в `arkaim-web/src/shared/ui/SourceBadge.tsx` и имеет unit-тест `arkaim-web/tests/unit/source-badge.test.tsx`.
- Polish Pass для единственного `arkaim-web` зафиксирован в `docs/FRONTEND_POLISH_PASS_REPORT.md`; это подтверждает состояние Polish Pass, но не означает новый общий frontend-аудит.
- B10 имеет отдельный browser console smoke test `arkaim-web/tests/e2e/b10-console-smoke.spec.ts`; ранее выполненный smoke прошёл на `/ask`, `/history`, `/world-engine` (`1 test passed`). B4-C имеет отдельное ранее выполненное browser evidence, не зависящее от B10.
- Auth/session, typed API contracts, SSE/WS, PWA и persistence представлены в текущем frontend-коде; этот baseline не заявляет новый полный live-аудит каждого frontend runtime flow.

### Backend

- FastAPI application и routes находятся в `runtime/`, DI registry — в `runtime/core/adc_deps.py`.
- Backend auth/RBAC, stream/SSE, `/book/ask`, World, Temporal, provenance и session handling проверялись только в пределах выполненных контрольных прогонов; отсутствующую live-проверку нельзя заменять утверждением в этом документе.
- Актуальные DTO/contracts и route behavior считаются доказательством только в связке с текущим FastAPI-кодом и тестами, а не по старым API dumps.

## 4. B3 / B4 / Knowledge Cards baseline

| Этап | Текущий статус | Фактическое evidence / ограничение |
|---|---|---|
| B3-CW | IMPLEMENTED / VERIFIED | Первый утверждённый набор crosswalk mappings; `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`. Новые mappings без отдельного решения не считаются реализованными. |
| B3-A | IMPLEMENTED / VERIFIED | ID reconciliation подтверждена `docs/B3A_ID_RECONCILIATION_REPORT.md` и текущими reconciliation/crosswalk tests. |
| B3-B | IMPLEMENTED / TESTED | Реализация Temporal-связей в `core/CORE/narrative_engine/world_model.py`; тесты `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`. Старый `docs/B3B_PLAN.md` — HISTORICAL. |
| B4-A | IMPLEMENTED / TESTED | Provenance inventory в `core/CORE/narrative_engine/world_provenance.py`; backend subset прошёл. |
| B4-B | IMPLEMENTED / TESTED | Read-only World provenance API/contracts; подтверждено backend subset и связанными tests. |
| B4-C | IMPLEMENTED / TESTED / VERIFIED | Реальный код есть в `arkaim-web/src/shared/ui/WorldProvenanceCard.tsx`, `arkaim-web/src/app/world-engine/page.tsx`, `arkaim-web/src/shared/api/contracts/world.ts`; UI/contract tests подтверждают реализацию. Browser evidence получено ранее: `region_arkaim` — PASS, `region_hyperborea` — provenance подтверждён после read-only диагностики, `region_gardarika` — PASS для missing related data, console без новых ошибок. Код B4-C после этой проверки не изменялся; повторный smoke не требуется. |
| Knowledge Cards backend | IMPLEMENTED / TESTED / LIVE CONFIRMED | `core/CORE/knowledge_card/builder.py`; `runtime/core/routes/knowledge_cards.py`; router подключен в `runtime/core/main.py`; HTTP 200 для search/card |
| Knowledge Cards frontend | TODO | Отдельного Knowledge Cards route/component в активном `arkaim-web` не обнаружено |
| B10 | VERIFIED | `arkaim-web/tests/e2e/b10-console-smoke.spec.ts`; ранее выполненный e2e smoke прошёл на `/ask`, `/history`, `/world-engine` (`1 test passed`). Evidence получено ранее; повторный live-run не требуется. |

`SourceBadge` относится к B3/frontend evidence и не является частью B4-C.

## 5. Актуальный backend baseline 2026-10-01

Фактические целевые наборы:

```text
runtime/tests/test_knowledge_cards.py
runtime/tests/test_data_discipline.py
runtime/tests/test_book_intelligence.py
runtime/tests/test_related_entities.py
runtime/tests/test_auth.py
```

Результат контрольного запуска:

```text
92 passed
0 failed
```

Core World/B3-B/provenance:

```text
core/CORE/narrative_engine/tests/test_b3b_crosswalk.py
core/CORE/narrative_engine/tests/test_world_provenance.py
```

Результат:

```text
8 passed
0 failed
```

Frontend целевые tests:

```text
tests/unit/world.test.ts
tests/unit/world-provenance-card.test.tsx
tests/unit/source-badge.test.tsx
```

Результат целевых файлов:

```text
17 passed
0 failed
```

Результат полного frontend unit suite:

```text
14 files
70 passed
0 failed
```

React вывел warnings `act(...)` в `pages.test.tsx`, но все тесты завершились успешно; warning не трактуется как verification.

Live Knowledge Cards:

```text
GET /knowledge/cards/search?q=Аркаим -> 200
GET /knowledge/cards/{entity_id} -> 200
book claims -> присутствуют
archaeology claims -> присутствуют
coverage note -> сущность распознана через entity_id аркаим
```

### Telegram OAuth

В исходном baseline были исправлены только устаревшие fixtures/ожидания в `runtime/tests/test_auth.py`: тесты data-check-string и HMAC OAuth должны использовать валидный Telegram freshness flow. Production auth logic не изменялась. После исправления auth subset прошёл; новых backend failures не обнаружено.

## 6. Restore backlog и ограничения

- `docs/FRONTEND_RESTORE_BACKLOG.md` — единственное допустимое место для потенциального восстановления функций бывшего v2. Backlog не равен реализации.
- B3/B4 планы, не подтверждённые текущим кодом или тестами, не являются разрешением на новую работу.
- B4-C имеет `VERIFIED` на основании ранее полученного browser evidence (`region_arkaim`, `region_hyperborea`, `region_gardarika`); повторный smoke не нужен, так как код B4-C после проверки не менялся.
- B10 имеет `VERIFIED` на основании ранее выполненного e2e smoke (`/ask`, `/history`, `/world-engine`, `1 passed`).
- Знание о Knowledge Cards должно браться из фактического кода/API, а не из старых формулировок «not implemented».
- Текущий git baseline фиксируется как commit `4bbfff0270f4f83e32bbd880fbcdf0e0e6c8d8af`. Рабочее дерево содержит изменения, поэтому baseline не означает чистый checkout и не использует незакоммиченные изменения как отдельный commit.
- Старые порты, routes, компоненты и документы не считаются актуальными только по текстовому упоминанию.

## 7. Итог

Текущий baseline: `arkaim-web` — единственный frontend; актуальные целевые тесты 2026-10-01 прошли; Knowledge Cards backend имеют IMPLEMENTED/TESTED/LIVE-confirmed evidence (live HTTP evidence зафиксировано в отчёте); B3-CW, B3-A, B3-B, B4-A и B4-B имеют зафиксированное evidence; B4-C — IMPLEMENTED/TESTED/VERIFIED на основании ранее полученного browser evidence (`region_arkaim`, `region_hyperborea`, `region_gardarika`); B10 — VERIFIED на основании ранее выполненного e2e smoke (`/ask`, `/history`, `/world-engine`, `1 passed`). Повторные проверки для уже имеющихся доказательств не запускались.
