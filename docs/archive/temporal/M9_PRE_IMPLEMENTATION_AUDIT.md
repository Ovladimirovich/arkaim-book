# M9 — PRE-IMPLEMENTATION AUDIT

## 1. Что требует спецификация

### Найдено упоминаний M9

| Документ | Строка | Формулировка |
|----------|--------|-------------|
| `docs/M4_PRE_IMPLEMENTATION_AUDIT.md:587` | Deferred | `ExpansionLayer temporal consumption` |
| `docs/M4_PRE_IMPLEMENTATION_AUDIT.md:749` | NOT M4 | `ExpansionLayer temporal consumption` |
| `docs/M5_PRE_IMPLEMENTATION_AUDIT.md:677` | Later | `ExpansionLayer temporal consumption` |
| `docs/M5_PRE_IMPLEMENTATION_AUDIT.md:840` | Future | `M9: ExpansionLayer temporal consumption` |
| `docs/M7_2_PRE_IMPLEMENTATION_AUDIT.md:238` | Not started | `M9 — ExpansionLayer temporal | ❌ НЕ НАЧИНАЛ` |
| `docs/M8_FUTURE_EXTRAPOLATOR_IMPLEMENTATION.md:13` | Далее | `M9 (ExpansionLayer temporal consumption)` |

### Вывод по спецификации
**Детальной спецификации M9 НЕ СУЩЕСТВУЕТ.** M9 упомянут как one-liner в 6 документах без расшифровки:
- Цели
- Входов/выходов
- Acceptance criteria
- Тестов

**Существующая формулировка:** `ExpansionLayer temporal consumption`
**Интерпретация:** ExpansionLayer должен.consume (потреблять) temporal данные из построенной цепочки PRESENT→ARKAIM→FUTURE.

---

## 2. Что уже существует

### 2.1 ExpansionLayer (pulse/layers.py:823)
```python
class ExpansionLayer(BaseLayer):
    name = "expansion"
    # Методы: respond_to(), get_context(), summary
    # Тема: 168 topics из DEEP/EXPANDED JSON
```

**Текущее состояние:**
- `respond_to(query)` — keyword search по темам, возврат literal/metaphorical/cosmic layers
- `get_context(query)` — текстовый контекст для LLM
- **НЕТ temporal-aware методов**
- **НЕТ связи с TemporalReconstructionEngine**

### 2.2 ExpansionLayer temporal topics (17 из 168)
Темы, содержащие temporal keywords (yuga, epoch, время, эпоха):
- Кали Юга
- Сатья Юга
- Трета Юга
- Двупара Юга
- Аркаимская эпоха (в THEMES_DEEP.json)
- etc.

**Проблема:** Эти темы содержат текстовое описание, но НЕ связаны с temporal graph.
Query `respond_to('что было до Аркаима')` возвращает ARCHAEOLOGY topic (~4000 лет до н.э.),
но НЕ использует temporal chain для построения ответа.

### 2.3 WorldModel temporal methods
```python
# world_model.py:408
def get_temporal_context(self, epoch_id: str) -> dict
def get_temporal_summary(self) -> dict
```

### 2.4 TemporalReconstructionEngine (M5+M8.1)
```python
# reconstruction_engine.py
def _trace_backward(anchor_id, max_depth) -> list[str]
def _trace_forward(anchor_id, max_depth) -> list[str]
def reconstruct_chain(anchor_id, direction) -> Optional[ReconstructionPath]
```

### 2.5 WorldEngine pipeline (M8.1)
```python
# world_engine.py
def get_full_temporal_pipeline(prompt, max_futures) -> dict
# Возвращает: present_anchor, backward_reconstruction, arkaim_anchor, forward_extrapolation
```

### 2.6 Существующие тесты
- 0 тестов для ExpansionLayer temporal
- 5 тестов для pulse (email templates, не связанные с temporal)
- 186 temporal тестов (все PASS)

---

## 3. Что отсутствует

### Gap 1: ExpansionLayer не знает о temporal chain
ExpansionLayer не имеет доступа к:
- TemporalReconstructionEngine
- TemporalGraph
- FutureExtrapolator results
- PRESENT→ARKAIM→FUTURE pipeline

### Gap 2: Нет метода для temporal-aware queries
Текущий `respond_to()` работает только с текстовым search по темам.
Нет метода типа `respond_to_temporal(query, direction='BACKWARD')`.

### Gap 3: Нет enrichment temporal topics с chain data
THEMES_DEEP.json содержит темы типа "Кали Юга" с текстом, но без:
- Ссылки на temporal node ID
- Ссылки на chain position
- Provenance из temporal graph

### Gap 4: Нет тестов
0 тестов для M9 функциональности.

### Gap 5: Нет API endpoint
Нет `/book/temporal/expansion` или подобного для доступа к temporal expansion.

---

## 4. Dependency check M1–M8.1

| Мост | Статус | Зависимость M9 |
|------|--------|----------------|
| M1 (Provenance) | ✅ 30/30 PASS | Base provenance categories needed |
| M2 (Temporal Model) | ✅ | TemporalNode, TemporalRelation types |
| M3 (Reconstruction) | ✅ | `_trace_backward/forward()` |
| M4 (Integration) | ✅ | `WorldModel.get_temporal_context()` |
| M5 (WorldEngine temporal) | ✅ 19/19 PASS | `enable_temporal()`, `get_temporal_chain()` |
| M6 (API routes) | ✅ 17/17 PASS | `/book/temporal/*` endpoints |
| M7.1 (Frontend timeline) | ✅ | TimelineView component |
| M7.2 (Epoch visual) | ✅ 11/11 PASS | `build_epoch_prompt()` |
| M8 (FutureExtrapolator) | ✅ 13/13 PASS | `FutureExtrapolator.extrapolate()` |
| M8.1 (Present anchor) | ✅ 32/32 PASS | `get_full_temporal_pipeline()` |

**Все dependencies M1–M8.1 ПОКРЫТЫ.** M9 может использовать все существующие компоненты.

---

## 5. Architectural risks / ambiguities

### Риск 1: Что именно означает "consumption"?

**Амбигуйность:** Не ясно, что именно M9 должен сделать с temporal данными.

**Варианты интерпретации:**
1. **A) Enrich topics** — добавить temporal metadata в DEEP JSON файлы
2. **B) Layer integration** — ExpansionLayer научить использовать temporal chain при ответе
3. **C) API endpoint** — создать `/book/temporal/expansion` для внешнего доступа
4. **D) Все вышеперечисленное**

**Рекомендация:** Начать с минимального варианта (B) — научить `respond_to()` и `get_context()` использовать temporal данные.

### Риск 2: Provenance implications

**Критический вопрос:** Как маркировать temporal data в ExpansionLayer?

Если ExpansionLayer отвечает на "что было до Аркаима?" используя `_trace_backward()`,
ответ должен иметь provenance:
- `RECONSTRUCTION` — если использует temporal chain
- `AUTHOR_CANON` — если использует THEMES_DEEP.json текст
- Смешанная — если оба источника

**Риск:** Смешивание provenance без чёткого разделения нарушит инвариант `RECONSTRUCTION ≠ HISTORICAL_FACT`.

### Риск 3: Cycle dependency

ExpansionLayer сейчас не зависит от temporal компонентов.
Если M9 добавит зависимость `ExpansionLayer → TemporalReconstructionEngine`,
возникнет cycle:
```
Pulse → ExpansionLayer → TemporalReconstructionEngine → WorldModel → Pulse
```

**Решение:** Injection через parameter, не import-time dependency.

### Риск 4: Ambiguous scope

M9 может быть:
- **Minimal:** Только `respond_to()` temporal-aware
- **Full:** + API endpoint + enrichment + tests

Без детальной спецификации риск over-scope велик.

---

## 6. Exact implementation scope (варианты)

### Вариант A: Minimal (рекомендуется для начала)

**Изменения:**
1. `ExpansionLayer.__init__()` — принять optional `temporal_engine` parameter
2. `ExpansionLayer.respond_to()` — check temporal keywords, use `_trace_backward/forward` if relevant
3. `ExpansionLayer.get_context()` — include temporal chain context

**Не меняется:**
- DEEP JSON файлы
- API endpoints
- Provenance model (расширять не надо)

**Tests:** ~5-8 tests

### Вариант B: Full

Всё из A +
4. Добавить `/book/temporal/expansion` endpoint
5. Enrich THEMES_DEEP.json с temporal metadata
6. Добавить temporal-specific methods (`get_chain_for_topic()`, etc.)

**Tests:** ~15-20 tests

---

## 7. Tests required

### Минимальный set (Вариант A)

1. `test_expand_temporal_query_backward` — query about "before Arkaim" uses `_trace_backward`
2. `test_expand_temporal_query_forward` — query about "future of Arkaim" uses FutureExtrapolator
3. `test_expand_non_temporal_query_unchanged` — regular query still works
4. `test_expand_provenance_marked_reconstruction` — temporal answers have RECONSTRUCTION provenance
5. `test_expand_no_graph_relation_created` — no new relations in graph
6. `test_expand_temporal_engine_optional` — works without temporal engine (backward compatible)
7. `test_expand_get_context_includes_chain` — get_context includes temporal info

---

## 8. DoD (Definition of Done)

### Minimal DoD (Вариант A)

- [ ] `ExpansionLayer` accepts optional `temporal_engine` parameter
- [ ] `respond_to("что было до Аркаима")` returns answer based on `_trace_backward()`
- [ ] `respond_to("будущее Аркаима")` returns answer based on `FutureExtrapolator`
- [ ] Non-temporal queries unaffected
- [ ] Temporal answers tagged with correct provenance (RECONSTRUCTION / FUTURE_EXTRAPOLATION)
- [ ] No new graph relations created
- [ ] Backward compatible (works without temporal_engine)
- [ ] 7+ tests covering above
- [ ] All existing tests still pass

---

## 9. Verdict

### M9 — BLOCKED

**Причина:** Отсутствует детальная спецификация M9.

M9 упомянут как `ExpansionLayer temporal consumption` в 6 документах, но:
- Нет определённого scope (minimal vs full)
- Нет acceptance criteria
- Нет понимания, какие именно temporal queries должен обрабатывать ExpansionLayer
- Нет решения по provenance для temporal-enriched answers

**Рекомендация:** Создать `M9_PRE_IMPLEMENTATION_AUDIT.md` с детализацией scope до начала реализации.

**Альтернатива:** Начать с **Варианта A (Minimal)** с явным ограничением:
- Только `respond_to()` temporal-aware
- Без новых API endpoints
- Без изменения DEEP JSON
- 7 тестов
- Простой provenance model
