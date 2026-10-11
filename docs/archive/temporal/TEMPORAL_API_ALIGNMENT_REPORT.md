# TEMPORAL API ALIGNMENT REPORT — B1 + C1

**Дата:** 2026-09-09
**Статус:** IMPLEMENTED / TESTED — ожидает независимого forensic audit (по STOP GATE владельца)
**Основа:** ADR_TEMPORAL_WORLD_MODEL (ACCEPTED) · План: `docs/TEMPORAL_API_ALIGNMENT_PLAN.md`
**Scope:** ТОЛЬКО B1 (`/book/temporal/nodes` + temporal_today) + C1 (`/book/temporal/chain` canonical provenance якоря). **C2 НЕ реализован** (deferred по ADR).

---

## Простыми словами

1. **Цель** — публичное API «времени мира» теперь отвечает тем же содержанием, что и канонический движок M8.1: в списке узлов появилась точка «Современность» (методологическая, без связей), а у якоря Аркаима — честные метки происхождения (авторский канон + археология, уверенность 0.85).

2. **Что сделано** — две правки в одном файле маршрутов (~35 строк) + 19 новых тестов. Никаких новых сущностей, миграций, типов связей; фронтенд/legacy/M10.2 не тронуты. Проверено на живом сервере: 25/25 живых проверок PASS.

3. **Результат** — PASS. Критический инвариант подтверждён живыми запросами и тестами: связь «Современность→Аркаим» НЕ создана нигде; ось эпох неизменна (12 узлов, 11 PRECEDES); C2 (метки на рёбрах) осознанно не делался.

4. **Проблемы** — две, обе вне этапа: (а) в песочнице DSH часть неродственных тестов падает по причинам среды (sqlite readonly для community/telegram-баз, EPERM на временных папках миграций, один legacy-тест несовместим с FastAPI 0.141 — написан 2026-07-10, до всех наших работ) — все они падали бы и без этого этапа, что доказано их содержимым; (б) обнаружен задокументированный finding: фабрика рёбер `precedes()` ещё до этого этапа ставила рёбрам метку AUTHOR_CANON, что расходится с ADR Decision C — но правка фабрики = семантическое изменение данных, запрещённое scope; зафиксировано как finding для этапа C2.

5. **Дальше** — жду вашего решения о независимом forensic audit этого этапа. F3 не начинался. Код-стоп соблюдён.

---

## 1. Changed files (полный след этапа, mtime-доказательство)

| Файл | Тип | Что |
|------|-----|-----|
| `runtime/core/routes/temporal.py` | EDIT (untracked-new файл проекта) | B1: `list_nodes` + сегодня; C1: `_enrich_canonical_anchor` + вызов в `get_temporal_chain` |
| `runtime/tests/test_temporal_api_alignment.py` | NEW | 19 тестов (B1×5, C1×7, invariants×7) |
| `docs/TEMPORAL_API_ALIGNMENT_PLAN.md` | NEW | план (зафиксирован до реализации) |
| `docs/TEMPORAL_API_ALIGNMENT_REPORT.md` | NEW | этот отчёт |
| `arkaim-web-v2/scripts/temporal-alignment-live.mjs` | NEW | live-валидация (инструмент проверки) |

**mtime-граница (источник, .py/.ts/.tsx, после 09:00 2026-09-09):** ровно `runtime/core/routes/temporal.py` [09:37] + `runtime/tests/test_temporal_api_alignment.py` [09:43]. Больше НИ ОДНОГО исходника в core/, runtime/, arkaim-web/, arkaim-web-v2/ не тронуто. Tracked-дифф проекта — pre-existing база (identity-sanitizer, visual M7.2, AB-testing, M10-серия), без изменений со стороны этого этапа.

## 2. Exact behavior before/after

### B1 — GET /book/temporal/nodes

| | Before | After |
|---|--------|-------|
| total | 12 | **13** |
| temporal_today | отсутствует | **присутствует, последним** (canonical order движка: эпохи → today) |
| today provenance | — | `[{category: HYPOTHESIS, source_level: SYSTEM_INTERPRETATION, confidence: 1.0, notes: "methodological anchor for temporal reconstruction — not book canon"}]` |
| today прочее | — | label=«Современность», precision=EXACT, bounds 2025 CE, era_id="", is_anchor=false |
| остальные 12 узлов | неизменны | **неизменны** (проверено: provenance/confidence прежние) |

### C1 — GET /book/temporal/chain (оба направления)

| | Before | After |
|---|--------|-------|
| arkaim_era provenance | `[]` | **[{AUTHOR_CANON, CANON, 1.0, source_title:"КНИГА.md"}, {EXTERNAL_SOURCE, HISTORICAL, 0.7, source_title:"ARCHAEOLOGY.json"}]** |
| arkaim_era confidence | 0.8 | **0.85** (как reconstruction_engine.py:595) |
| прочие 11 узлов | provenance=[] , conf 0.8 | **неизменны** (тест test_other_nodes_not_changed) |
| relations | 11 × PRECEDES с пред-существующим тегом фабрики | **не тронуты** (test_c2_not_implemented_edges_untouched) |
| stats | nodes=12, relations=11 | **12/11** (не изменились) |
| today в chain | нет | **нет** (узел без relations — в цепочку не входит) |
| Present→Arkaim relation | нет | **НЕ создана** (инвариант, проверен в обоих направлениях) |

### Реализация (строки)

- **B1:** `routes/temporal.py::list_nodes` — цикл эпох, затем `nodes.append(TemporalNode.present_anchor().to_dict())` (та же фабрика, что в `reconstruction_engine.py:606-608`).
- **C1:** `routes/temporal.py::_enrich_canonical_anchor(chain_data)` — источник provenance ТОЛЬКО `ArkaimAnchor.from_existing_data()` (arkaim_anchor.py:70-97); дедуп по категории (как reconstruction_engine.py:591-594); confidence=0.85 (как 595). Никаких новых значений.

## 3. Tests

| Группа | Результат |
|--------|-----------|
| NEW `test_temporal_api_alignment.py` | **19 passed** (B1×5: today-присутствие/порядок/one-only/HYPOTHESIS-семантика/нет-дубля-anchor; C1×7: provenance обеих направлений/confidence/источники-КНИГА.md+ARCHAEOLOGY.json/остальные-не-тронуты/is_anchor; INV×7: today-не-в-chain/нет-Present→Arkaim/12-11-PRECEDES-форма/C2-рёбра-нетронуты — параметризованы FOR/BACK) |
| `test_temporal_routes.py` (M5-маршруты) | **41 passed** (без regressions) |
| `test_temporal_model.py` + `test_temporal_reconstruction.py` + `test_temporal_integration.py` + `test_m5_temporal_integration.py` | **144 passed** (в сумме с routes: 185) |
| `test_m8_1_present_anchor.py` (прямой эталон canonical M8.1) | **32 passed** |
| `test_m8_future_extrapolation.py` | (в M8/M9/M10-группе) — **99 passed** суммарно с M9/M10/M10.2 |
| `test_m10_temporal_updates.py` + `test_m10_2_pending_updates_api.py` | **48 passed** (повторно подтверждено) |
| `test_narrative_*` + `test_knowledge_kernel.py` | **81 passed** |
| `test_m7_epoch_visual.py` + `test_genome*.py` | **18 passed, 4 skipped** (skip — pre-existing) |

**Итого stage-релевантная регрессия: ~400+ passed, 0 regressions.**

### Pre-existing/environmental падения (вне этого этапа, доказано содержимым):

| Тест-файл | Причина | Класс |
|-----------|---------|-------|
| `tests/auth/test_migrations.py` (6 ERRORS) | `PermissionError: WinError 5` на rmtree временной папки песочницы DSH | среда (sandbox) |
| `tests/test_metrics.py` (1 FAILED + 2 ERRORS) | тест (2026-07-10) итерирует `app.routes` с `r.path`; FastAPI 0.141 отдаёт 5 `_IncludedRouter` без `.path` — несовместимость доэтапная; endpoint /metrics жив (проверено live: 200) | pre-existing legacy |
| `tests/test_integrations.py` (4 FAILED) + `tests/test_crowdfunding.py` (10 FAILED) | `sqlite3.OperationalError: attempt to write a readonly database` (community/telegram-базы) — файловая блокировка песочницы | среда (sandbox) |

Ни один из них не импортирует/не касается temporal; ключевой контроль: полный temporal-домен + M8.1 + M10/M10.2 зелёные; ручная live-проверка `/metrics` = 200.

**Ограничение среды (зафиксировано):** ruff в runtime-venv не установлен (pre-existing) — lint подмён компиляцией `py_compile` (exit 0 оба файла).

## 4. Live evidence (живой uvicorn :8642, 2026-09-09)

Скрипт `arkaim-web-v2/scripts/temporal-alignment-live.mjs` — **25/25 PASS**:
- `/nodes` 200; total=13; today присутствует, ровно один, последний; category=HYPOTHESIS; is_anchor=false; era_id="";
- `/chain` FORWARD и BACKWARD: arkaim_era provenance=AUTHOR_CANON+EXTERNAL_SOURCE, confidence=0.85; today НЕ в chain; **relations не содержат temporal_today ни source, ни target (Present→Arkaim отсутствует)**; 12 узлов / 11 PRECEDES; рёбра нетронуты (пред-существующий фабричный тег); остальные узлы неизменны;
- OpenAPI: ровно 14 temporal-путей (7 M4/M8 + 7 M10.2), новых путей 0, исчезнувших 0 — структура API неизменна.

## 5. Regression results (сводка)

Temporal-домен полностью зелёный (см. §3). Unrelated-группы: 98 passed/14 environmental-failed (sqlite-readonly sandbox; детально в §3). Полный прогон одного куска (78 файлов) в этой песочнице не завершается — тяжёлые integration-тесты ждут сеть/провайдеров; заменён покомпонентным покрытием всех релевантных групп (все временные/якорные/M8/M9/M10/M10.2/narrative/gateway/auth/metrics-изолированные). Backend-граница этапа при этом доказана независимо (mtime + git).

## 6. Git diff boundary

- **Tracked-изменений НЕТ** (мой этап не меняет ни одного tracked-файла; `runtime/core/routes/temporal.py` — untracked-файл проекта с самого начала, как и весь temporal-стек — это M-серия, известная базе аудитов).
- **Файлы этапа:** 2 код-файла (1 отредактирован, 1 создан) + 2 документа + 1 live-скрипт.
- **НЕ изменено:** F3-frontend (не существует), legacy frontend (`arkaim-web/` — 0 правок), M10.2 (`temporal_updates.py` не открывался), core/CORE (включая world_model.py, reconstruction_engine.py, source_levels.py), relation types (не добавлены), Present→Arkaim relation (не создан), HistoricalLayerStack/EpochTransitionModel (не тронуты), TemporalEngine (не создан), temporal data (не менялись), unrelated endpoints (не тронуты), contracts (0 упоминаний temporal — конфликтов нет).

## 7. Confirmation: C2 NOT implemented

- В `chain.relations` **не добавлено ни одного provenance-тега** этапом: рёбра несут ровно пред-существующий фабричный тег (AUTHOR_CANON, notes="temporal precedence — from epoch ordering", relation.py:151-166) — зафиксировано тестом `test_c2_not_implemented_edges_untouched` и live-проверкой `C2-deferred`.
- **Finding для этапа C2 (зафиксирован, НЕ исправлен):** фабрика `TemporalRelation.precedes()` в core/ставит рёбрам оси тег AUTHOR_CANON, что расходится с ADR Decision C-п.2 («рёбрам оси — DERIVED/RECONSTRUCTION, НИКОГДА AUTHOR_CANON»). Исправление = изменение фабрики/данных — вне scope этого этапа (владелец запретил: «не менять значения существующих temporal данных»). Требует решения в рамках C2.

## 8. Критические инварианты (итог)

| Инвариант | Статус |
|-----------|--------|
| public API temporal semantics == canonical M8.1 engine semantics (для /nodes и /chain) | ✅ today теми же фабрикой/порядком; якорь тем же provenance/confidence, что движок |
| frontend does not synthesize missing temporal relations | ✅ (frontend не тронут вовсе; API отдаёт только реальные связи) |
| Present→Arkaim НЕ создан | ✅ тесты (обе направления) + live |
| 12 узлов / 11 PRECEDES / today-вне-цепочки | ✅ тесты + live |
| C2 deferred | ✅ рёбра нетронуты; finding задокументирован |

## 9. STOP GATE

Production-код: СТОП (после B1+C1 ничего не менялось). F3: СТОП (не начат). Никаких дополнительных fixes, B3/B4, новых архитектурных решений. Жду отдельного approval владельца на independent forensic audit.
