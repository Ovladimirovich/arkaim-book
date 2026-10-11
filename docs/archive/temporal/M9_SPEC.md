# M9 SPECIFICATION — Temporal-aware ExpansionLayer

> **СТАТУС: ACCEPTED & CLOSED (2026-09-06)**
> Спецификация утверждена владельцем, реализована, прошла
> post-implementation audit (28/28 PASS, 38/38 M9-тестов, 186/186 regression)
> и принята владельцем. См. `docs/M9_POST_IMPLEMENTATION_AUDIT.md`.

## 1. Goal

Make `ExpansionLayer.respond_to()` и `ExpansionLayer.get_context()` aware of temporal chain data, using the existing WorldEngine temporal facade, WITHOUT:
- Creating dependency cycles
- Duplicating temporal logic
- Changing existing expansion data (DEEP JSON)
- Adding new API endpoints
- Modifying M8 algorithm

**Цель:** ExpansionLayer начинает отвечать на temporal-запросы, используя построенную цепочку PRESENT→ARKAIM→FUTURE, с корректной маркировкой provenance.

---

## 2. Scope

### Minimal scope (M9)

| Что входит | Что НЕ входит |
|------------|---------------|
| Temporal intent detection в `respond_to()` | Новый temporal API endpoint |
| Temporal context enrichment в `get_context()` | Frontend/UI изменения |
| Provenance tagging для temporal answers | Enrichment всех 168 тем |
| Dependency via WorldEngine facade | Изменение TemporalReconstructionEngine |
| ~7-10 тестов | Изменение M8 алгоритма |
| | M10 |

### Temporal intent detection

ExpansionLayer определяет temporal intent по ключевым словам в query:

| Category | Keywords (RU) | Keywords (EN) | Direction |
|----------|--------------|---------------|-----------|
| **BACKWARD** | "до Аркаима", "предыстория", "до этого", "история", "как появилось", "исторический контекст" | "before arkaim", "history of", "preceding", "origin", "previous" | BACKWARD |
| **FORWARD** | "после Аркаима", "будущее", "что будет", "развитие", "продолжение" | "after arkaim", "future", "what comes next", "development", "continuation" | FORWARD |
| **ARKAIM CONTEXT** | "в эпоху Аркаима", "во время Аркаима", "аркаимская эпоха", "контекст Аркаима" | "in arkaim era", "during arkaim", "arkaim period" | BOTH (epoch-specific) |
| **POSITION** | "где во времени", "какая эпоха", "временная позиция" | "when", "what era", "temporal position" | BACKWARD |

**Правило:** Если query содержит temporal keyword → temporal path. Иначе → standard expansion path.

### Data ExpansionLayer получает от temporal subsystem

Через WorldEngine facade (без прямого импорта TemporalReconstructionEngine):

```python
# Внутри ExpansionLayer.respond_to():
we = get_world_engine()
te = we.temporal_engine  # None if not enabled

if te is not None and temporal_intent_detected(query):
    # Получаем данные из temporal subsystem
    chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
    # chain.nodes, chain.relations, chain.provenance
```

**Формат ответа:**
```python
{
    "text": str,                    # текстовый ответ
    "source": str,                  # "expansion:arkaim_era" или "temporal:backward_chain"
    "confidence": float,            # 0.0–1.0
    "provenance": list[dict],       # [{"category": "RECONSTRUCTION", ...}]
    "temporal_chain": dict|None,   # nodes + relations (опционально)
}
```

---

## 3. Supported Temporal Queries

### 3.1 BACKWARD queries (reconstruction from present to arkaim)

**Примеры:**
- "Что было до Аркаима?"
- "Какова предыстория Аркаима?"
- "Как появилась цивилизация Аркаима?"
- "Что предшествовало Аркаиму?"

**Механизм:**
```python
chain = temporal_engine.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
# chain.nodes = [temporal_future, ..., temporal_arkaim_era, ..., temporal_pre_arkaim]
# Но в BACKWARD direction: [temporal_arkaim_era, temporal_pre_arkaim, ...更早的...]
```

**Ответ:** ExpansionLayer комбинирует:
1. Текст из THEMES_DEEP.json (тем "Аркаим", "Гиперборея")
2. Temporal chain nodes (порядок эпох)
3. Маркирует provenance = RECONSTRUCTION

### 3.2 FORWARD queries (extrapolation from arkaim to future)

**Примеры:**
- "Что будет после Аркаима?"
- "Какое будущее у Аркаима?"
- "Что развивается из Аркаима?"

**Механизм:**
```python
chain = temporal_engine.reconstruct_chain("temporal_arkaim_era", ChainDirection.FORWARD)
# chain.nodes = [temporal_arkaim_era, temporal_future, ...]
```

**Ответ:** ExpansionLayer комбинирует:
1. Текст из THEMES_DEEP.json (тем "Кали Юга", "Будущее")
2. Temporal chain nodes
3. FutureExtrapolator scenarios (если запрос явно о будущем)
4. Маркирует provenance = FUTURE_EXTRAPOLATION (если есть scenarios) или RECONSTRUCTION

### 3.3 ARKAIM EPOCH context queries

**Примеры:**
- "Что происходило в эпоху Аркаима?"
- "Каков контекст Аркаима?"
- "Опиши аркаимскую эпоху"

**Механизм:**
```python
context = world_model.get_temporal_context("arkaim_era")
# {temporal_node, epoch, events, characters, technologies}
```

**Ответ:** ExpansionLayer использует стандартный respond_to() + temporal context enrichment.
Provenance = AUTHOR_CANON (из темы) + RECONSTRUCTION (из temporal context).

### 3.4 POSITION queries (temporal placement)

**Примеры:**
- "Где Аркаим во времени?"
- "Какая это эпоха?"
- "Когда был Аркаим?"

**Механизм:**
```python
node = temporal_engine.get_node("temporal_arkaim_era")
# node.bounds, node.precision, node.provenance
```

**Ответ:** Прямой ответ из temporal node данных.
Provenance = mix из provenance узла.

### 3.5 Non-temporal queries (regression)

**Примеры:**
- "Что такое Гиперборея?"
- "Расскажи про символы"
- "Что такое Кали Юга?"

**Механизм:** Standard expansionLayer.respond_to() — БЕЗ temporal path.
Provenance = как раньше (из DEEP JSON).

---

## 4. Data Flow

### 4.1 Query routing

```
User Query
    │
    ▼
ExpansionLayer.respond_to(query)
    │
    ├─→ temporal_intent_detected(query)?
    │       │
    │       YES → Check temporal_engine available?
    │       │             │
    │       │             YES → Query temporal subsystem
    │       │             │        │
    │       │             │        ▼
    │       │             │   Get chain/context
    │       │             │        │
    │       │             │        ▼
    │       │             │   Combine: expansion_text + temporal_data
    │       │             │        │
    │       │             │        ▼
    │       │             │   Return with temporal provenance
    │       │             │
    │       │             NO → Fallback to standard respond_to()
    │       │
    │       NO → Standard respond_to() (unchanged)
    │
    ▼
PulseResponse(text, source, confidence, provenance)
```

### 4.2 Temporal subsystem access

**НЕ напрямую:**
```python
# ❌ BAD — создаёт прямую зависимость от TemporalReconstructionEngine
from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
```

**Через WorldEngine facade:**
```python
# ✅ GOOD — использует существующий public API
from narrative_engine.world_engine import get_world_engine
we = get_world_engine()
te = we.temporal_engine  # None if not enabled
if te:
    chain = te.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)
```

### 4.3 Response composition

```python
# Псевдокод для temporal-aware respond_to():
def respond_to(self, query):
    # 1. Standard expansion response
    base_response = self._standard_respond(query)
    
    # 2. Check temporal intent
    if not self._is_temporal_query(query):
        return base_response  # unchanged
    
    # 3. Get temporal data via WorldEngine facade
    we = get_world_engine()
    te = we.temporal_engine
    if te is None:
        return base_response  # temporal not available
    
    # 4. Build temporal answer
    temporal_answer = self._build_temporal_answer(query, te)
    
    # 5. Combine
    combined = self._combine_answers(base_response, temporal_answer)
    return combined
```

---

## 5. Dependency Graph

### 5.1 Текущий граф (до M9)

```
pulse/layers.py
  └── ExpansionLayer
        └── expansion_loader.py
              └── KNOWLEDGE/*.json

narrative_engine/
  ├── world_engine.py
  │     └── TemporalReconstructionEngine (via enable_temporal)
  │           └── TemporalGraph, TemporalNode, TemporalRelation
  │
  └── temporal/
        ├── reconstruction_engine.py
        ├── future_extrapolator.py
        ├── chain.py
        └── node.py, relation.py, graph.py

Нет зависимостей между pulse/ и temporal/
```

### 5.2 Граф после M9 (target)

```
pulse/layers.py
  └── ExpansionLayer
        ├── expansion_loader.py          (existing)
        └── narrative_engine.world_engine  (NEW — one-way)
              └── TemporalReconstructionEngine  (existing, via facade)
                    └── temporal/...      (existing)
```

**Проверка cycle:**
- `pulse.layers` → `narrative_engine.world_engine` ✅ однонаправленно
- `narrative_engine.world_engine` → НЕ импортирует `pulse.layers` ✅
- **Cycle: NO** ✅

### 5.3 Почему нет cycle

```
pulse.layers:
  imports: config, dataclasses, typing
  does NOT import from narrative_engine

narrative_engine.world_engine:
  imports: narrative_engine.world_model_ext, relation_models, etc.
  does NOT import from pulse

ExpansionLayer добавляет:
  from narrative_engine.world_engine import get_world_engine  ← NEW
```

Этот импорт создаёт зависимость `ExpansionLayer → WorldEngine`, но WorldEngine не зависит от ExpansionLayer. **Cycle отсутствует.**

---

## 6. Provenance Contract

### 6.1 Rules

| Source | Provenance Category | Confidence | Notes |
|--------|-------------------|------------|-------|
| THEMES_DEEP.json text | AUTHOR_CANON | 0.8–1.0 | From book canon |
| Temporal chain (BACKWARD) | RECONSTRUCTION | 0.6–0.8 | Archaeological + canon |
| Temporal chain (FORWARD) | FUTURE_EXTRAPOLATION | 0.3–0.7 | Projection, not fact |
| FutureExtrapolator scenarios | FUTURE_EXTRAPOLATION | 0.3–0.7 | Compatible scenarios |
| temporal_today node | HYPOTHESIS | 1.0 | Methodological anchor |
| arkaim_era node | AUTHOR_CANON + EXTERNAL_SOURCE | 0.85 | Enriched from M8.1 |

### 6.2 Combining provenance

**Правило:** При комбинировании источников используется НАИНИЖАЯ категория (наиболее консервативная).

```python
# Пример: запрос "что было до Аркаима?"
# ExpansionLayer имеет тему "Аркаим" с AUTHOR_CANON
# Temporal chain даёт RECONSTRUCTION
# Итоговый provenance = RECONSTRUCTION (lower than AUTHOR_CANON)

categories = {AUTHOR_CANON, RECONSTRUCTION}
result = lowest_priority(categories)  # RECONSTRUCTION
```

**Priority order (lowest → highest):**
```
FUTURE_EXTRAPOLATION < HYPOTHESIS < RECONSTRUCTION < EXTERNAL_SOURCE < AUTHOR_CANON
```

### 6.3 Ответ с provenance

```python
PulseResponse(
    text="Аркаимская эпоха предшествовала Кали Юге...",
    source="expansion:arkaim + temporal:backward_chain",
    confidence=0.75,
    provenance=[
        ProvenanceTag(category=ProvenanceCategory.RECONSTRUCTION, confidence=0.75,
                      notes="Temporal reconstruction from chain + expansion layer"),
    ]
)
```

---

## 7. Non-goals (explicitly excluded)

### НЕ входит в M9

| Запрещено | Причина |
|-----------|---------|
| Новый temporal API endpoint | Out of scope, M6/M7 responsible |
| Frontend/UI изменения | M7.1 responsible |
| Enrichment всех 168 тем temporal metadata | Данные в JSON, не код |
| Изменение TemporalReconstructionEngine | M5/M8.1 responsible |
| Изменение M8 FutureExtrapolator algorithm | M8 stable |
| Создание нового TemporalEngine/Service | Уже есть TemporalReconstructionEngine |
| Создание нового relation type | No epistemological relation needed |
| M10 | Future milestone |
| Исправление pre-existing failures | Unrelated |

---

## 8. Test Contract

### 8.1 Required tests

| # | Test name | Что проверяет |
|---|-----------|---------------|
| 1 | `test_temporal_intent_backward` | Query "что было до Аркаима" → temporal path activated |
| 2 | `test_temporal_intent_forward` | Query "что будет после Аркаима" → temporal path activated |
| 3 | `test_temporal_intent_arkaim_context` | Query "контекст Аркаима" → epoch context enriched |
| 4 | `test_non_temporal_query_unchanged` | Regular query returns standard response |
| 5 | `test_temporal_provenance_reconstruction` | BACKWARD answer has RECONSTRUCTION provenance |
| 6 | `test_temporal_provenance_future` | FORWARD answer has FUTURE_EXTRAPOLATION provenance |
| 7 | `test_no_dependency_cycle` | No circular import between pulse.layers и temporal |
| 8 | `test_no_graph_relation_created` | No new edges in temporal graph after respond_to |
| 9 | `test_temporal_engine_optional` | Works without temporal_engine enabled (graceful fallback) |
| 10 | `test_expand_regression_existing` | All existing expansion tests still pass |

### 8.2 Negative tests

| # | Test name | Что проверяет |
|---|-----------|---------------|
| 11 | `test_no_false_temporal_for_non_temporal_query` | "Расскажи про символику" → no temporal path |
| 12 | `test_temporal_without_engine_returns_base` | Without temporal_engine → base expansion response |

---

## 9. DoD (Definition of Done)

### Code changes

- [ ] `ExpansionLayer.__init__()` accepts optional `temporal_engine` (backwards compatible)
- [ ] `ExpansionLayer._is_temporal_query(query)` detects temporal intent
- [ ] `ExpansionLayer._build_temporal_answer(query, te)` builds temporal-aware response
- [ ] `ExpansionLayer.respond_to()` routes to temporal path when appropriate
- [ ] `ExpansionLayer.get_context()` includes temporal context for temporal queries
- [ ] No imports of TemporalReconstructionEngine in pulse.layers
- [ ] Only WorldEngine facade used for temporal access

### Tests

- [ ] 12 new tests in `tests/test_expansion_temporal.py`
- [ ] All 186 existing temporal tests pass
- [ ] All existing expansion tests pass
- [ ] No regressions

### Provenance

- [ ] Temporal answers tagged with correct provenance category
- [ ] Combined provenance follows lowest-common-denominator rule
- [ ] FUTURE_EXTRAPOLATION used only for forward queries

### Architecture

- [ ] No dependency cycle between pulse.layers and temporal subsystem
- [ ] No new graph relations created
- [ ] No mutation of WorldModel
- [ ] Graceful fallback when temporal_engine is None

---

## 10. Architectural Risks

### Risk 1: Lazy import timing

**Problem:** `get_world_engine()` creates singleton on first call. If called during module import, may fail.

**Mitigation:** Import inside method body, not at module level:
```python
def respond_to(self, query):
    from narrative_engine.world_engine import get_world_engine  # lazy import
    we = get_world_engine()
    ...
```

### Risk 2: temporal_engine not enabled

**Problem:** `we.temporal_engine` is None by default (opt-in pattern).

**Mitigation:** Check before using:
```python
te = we.temporal_engine
if te is None:
    return self._standard_respond(query)  # fallback
```

### Risk 3: keyword matching false positives

**Problem:** Word "история" appears in non-temporal contexts ("история любви").

**Mitigation:** Use phrase matching, not single-word:
```python
TEMPORAL_PATTERNS = [
    r"до\s+аркаим", r"после\s+аркаим", r"будущее\s+аркаим",
    r"эпох.*аркаим", r"врем.*аркаим",
]
```

### Risk 4: Confidence inflation

**Problem:** Combining expansion (0.8) + temporal (0.7) → should not default to 0.8.

**Mitigation:** Use weighted average or minimum:
```python
confidence = min(expansion_confidence, temporal_confidence)
# или
confidence = expansion_confidence * temporal_confidence
```

---

## Implementation Sketch (for reference, NOT implementation)

```python
# В ExpansionLayer.__init__:
def __init__(self, genome: dict, retriever=None, temporal_engine=None):
    super().__init__(genome, retriever)
    self._knowledge = {}
    self._load_expansion()
    self._temporal_engine = temporal_engine  # optional, injected

# В ExpansionLayer.respond_to:
def respond_to(self, query):
    from narrative_engine.world_engine import get_world_engine
    
    # 1. Standard response
    base = self._standard_respond(query)
    
    # 2. Check temporal intent
    if not self._is_temporal_query(query):
        return base
    
    # 3. Get temporal data
    we = get_world_engine()
    te = self._temporal_engine or we.temporal_engine
    if te is None:
        return base  # no temporal, return base
    
    # 4. Build temporal answer
    temporal = self._build_temporal_answer(query, te)
    
    # 5. Combine
    return self._combine(base, temporal)
```

---

## FINAL STATUS

### M9 — SPEC READY ✅

**Обоснование:**
1. Scope определён (minimal: temporal-aware respond_to + get_context)
2. Dependency graph verified — no cycle
3. Provenance contract defined
4. 12 tests specified
5. 4 architectural risks identified with mitigations
6. Non-goals explicitly listed
7. DoD clear and testable

**Блокировок нет.** Спецификация готова к реализации после утверждения.
