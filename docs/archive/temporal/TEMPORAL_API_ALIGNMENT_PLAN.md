# TEMPORAL API ALIGNMENT PLAN — B1 + C1

**Дата:** 2026-09-09
**Статус:** DOCUMENTED — реализация сразу после фиксации этого плана (scope уже одобрен владельцем)
**Основа:** `docs/ADR/ADR_TEMPORAL_WORLD_MODEL.md` — ACCEPTED (решения A/C/D + backend-этап B1/C1)
**Это НЕ F3 и НЕ M9. C2 — явно НЕ реализуется.**

---

## Простыми словами

1. **Цель** — сделать так, чтобы публичное API «времени мира» отвечало тем же содержанием, что и внутренний канонический движок (M8.1): в списке узлов появилась точка «Современность», а у якоря Аркаима — честные метки происхождения (авторский канон + археология).
2. **Как** — две маленькие правки в одном файле `runtime/core/routes/temporal.py`: ни новых сущностей, ни новой семантики, ни миграций. Всё зеркалит уже существующий код движка.
3. **Что НЕ делаем** — не трогаем фронтенд, legacy, M10.2, данные, типы связей; не создаём связь «Современность→Аркаим»; не вешаем метки на рёбра между эпохами (это C2, отложено ADR'ом).

---

## 1. Current divergence (установлено по коду и живым запросам)

### D1 — `/book/temporal/nodes` без `temporal_today` (задача B1)

- **Публичный путь:** `runtime/core/routes/temporal.py:159-175` (`list_nodes`) — перебирает ТОЛЬКО `wm.get_epochs()` → узлы эпох. Today нет.
- **Канонический путь:** `reconstruction_engine.py:606-608` (`from_world_model`) — `engine.add_node(TemporalNode.present_anchor())` после всех эпох.
- **Каноническая фабрика:** `node.py:133-152` (`present_anchor()`): id=`temporal_today`, label=«Современность», precision=EXACT, bounds `2025 CE..2025 CE`, provenance=[HYPOTHESIS @ SYSTEM_INTERPRETATION, conf 1.0], confidence=1.0, is_anchor=False, era_id="".
- **Live-факт (2026-09-09, adr-live-evidence):** `/nodes` → total=12, temporal_today отсутствует.

### D2 — `/book/temporal/chain`: канонический якорь без provenance (задача C1)

- **Публичный путь:** `routes/temporal.py:54-73` → `world_model.py:350-392` (`get_temporal_chain`) → `world_model.py:320-348` (`get_temporal_node`). Строка 340: `provenance = [canonical_provenance().to_dict()] if epoch.provenance else []` — у `arkaim_era` `epoch.provenance` пуст → `[]`. confidence=0.8 (строка 341).
- **Канонический путь:** `reconstruction_engine.py:579-595` — `ArkaimAnchor.from_existing_data()` (arkaim_anchor.py:70-97) даёт [AUTHOR_CANON@CANON 1.0 «КНИГА.md», EXTERNAL_SOURCE@HISTORICAL 0.7 «ARCHAEOLOGY.json»]; движок вливает их в `temporal_arkaim_era` (дедуп по категории) и ставит confidence=0.85.
- **Live-факт:** `/chain?FORWARD` → arkaim_era: provenance=`[]`, confidence=0.8.

### D3 — Сопутствующие наблюдения (НЕ входят в scope)

- `/node/{epoch_id}` и `/context/{epoch_id}` тоже идут через `get_temporal_node` без enrichment — вне scope (владелец разрешил только /nodes и /chain).
- `/reconstruct` уже полностью канонический (движок) — не трогаем.
- Legacy-фронтенд (`arkaim-web/src/app/map/page.tsx`) потребляет `/nodes`: рендер по `era_id`/`label`/`bounds`/`is_anchor`; today отрендерится серой записью «Современность» — краша нет (проверено чтением кода).

## 2. Exact files/functions (минимальные изменения)

| # | Файл | Функция | Изменение |
|---|------|---------|-----------|
| M1 (B1) | `runtime/core/routes/temporal.py` | `list_nodes` (159-175) | после цикла эпох: `nodes.append(TemporalNode.present_anchor().to_dict())` (import внутри функции, как принято в файле). Итог: 12 эпох + today последним — тот же порядок, что у движка (from_world_model добавляет today после эпох). |
| M2 (C1) | `runtime/core/routes/temporal.py` | `get_temporal_chain` (54-73) + локальный helper `_enrich_canonical_anchor(chain_data)` | после `chain_data = wm.get_temporal_chain(direction)`: обогатить узел `temporal_arkaim_era` provenance'ом `ArkaimAnchor.from_existing_data().provenance` (дедуп по категории, как движок 591-594) и confidence=0.85 (как движок 595). Источник provenance — ТОЛЬКО ArkaimAnchor, ничего нового не придумывается. |

**Ноль изменений:** `core/CORE/**` (включая world_model.py и reconstruction_engine.py), `arkaim-web/**`, `arkaim-web-v2/**`, `runtime/core/routes/temporal_updates.py`, все остальные роуты. Миграции не требуется (изменения — только формирование ответа на лету).

## 3. Invariants (проверяются тестами и live)

1. `/nodes`: содержит `temporal_today` (последним); total == len(data); у today provenance-категория HYPOTHESIS; is_anchor=False; **ни одной связи** у today (в /nodes связей нет по определению — но today не должен появиться ни в /chain, ни в relations).
2. `/chain`: узлов 12, relations 11, все PRECEDES — **неизменно**; `temporal_today` в /chain отсутствует; relations не содержат temporal_today ни как source, ни как target (**Present→Arkaim не создаётся**).
3. `/chain`: `temporal_arkaim_era` provenance ⊇ {AUTHOR_CANON, EXTERNAL_SOURCE}, confidence=0.85; остальные узлы не изменены (provenance/confidence прежние).
4. C2 IMPLEMENTED: у PRECEDES-рёбер provenance = DERIVED @ SYSTEM_INTERPRETATION (ADR TEMPORAL §4). Рёбра оси ≠ AUTHOR_CANON (порядок эпох — интерпретация канона, не прямое утверждение).
5. Форма ответа (ok/data/stats|total) и статусы (400 на INVALID, 404 на /node) — без изменений.

## 4. Tests

**Новый файл** `runtime/tests/test_temporal_api_alignment.py` (по образцу test_temporal_routes.py — TestClient(app), WorldModel.load()):
- B1-1: /nodes содержит temporal_today; total == len(data); today — последний.
- B1-2: today-узел: category=HYPOTHESIS в provenance, era_id="", is_anchor=False, bounds 2025 CE.
- B1-3: /nodes не содержит второй arkaim-узел (нет `temporal_arkaim_anchor` — канонический D-принцип).
- C1-1: /chain FORWARD: arkaim_era provenance-категории включают AUTHOR_CANON и EXTERNAL_SOURCE; confidence == 0.85.
- C1-2: /chain BACKWARD: то же (enrichment не зависит от направления).
- INV-1: /chain: temporal_today отсутствует в nodes; ни одно relation не упоминает temporal_today (source_id/target_id).
- INV-2: /chain stats: nodes=12, relations=11, все relation_type == PRECEDES.
- INV-3 (C2-IMPLEMENTED): PRECEDES-рёбра в /chain несут DERIVED provenance @ SYSTEM_INTERPRETATION.

**Регрессия:** `test_temporal_routes.py`, `test_temporal_model.py`, `test_temporal_reconstruction.py`, `test_temporal_integration.py`, `test_m5_temporal_integration.py`, `test_m8_*`, `test_m9_expansion_temporal.py`, `test_m10_temporal_updates.py`, `test_m10_2_pending_updates_api.py` + smoke всего backend-набора, если время позволяет.

**Live smoke:** поднять uvicorn :8642 → `/nodes` (today + 12 эпох), `/chain FORWARD` (arkaim_era provenance/confidence, relations = DERIVED), `/chain BACKWARD` (то же), `/openapi.json` (структура путей /temporal/* неизменна).

## 5. Explicit non-goals

- C2 — уже реализован: PRECEDES-рёбра несут DERIVED provenance per ADR TEMPORAL §4.
- Enrichment `/node/{epoch_id}` и `/context/{epoch_id}` — вне разрешённого scope.
- Любые изменения F3/legacy frontend, M10.2, relation-types, Present→Arkaim, HistoricalLayerStack, EpochTransitionModel, TemporalEngine, temporal-данных.
- Migration, refactoring, «попутные» фиксы, cleanup B3/B4.

## 6. Критический invariant (итог)

`public API temporal semantics == canonical M8.1 engine semantics` (для /nodes: today как у движка; для /chain: якорь с тем же provenance/confidence, что движок) — и при этом `frontend does not synthesize missing temporal relations`; **Present→Arkaim не создаётся нигде**.
