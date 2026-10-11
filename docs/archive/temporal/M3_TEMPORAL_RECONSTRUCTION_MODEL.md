# M3 — TEMPORAL RECONSTRUCTION ENGINE

**Статус:** ЗАВЕРШЁН  
**Дата:** 2025-07  
**Изменений в коде:** 0 breaking changes

---

## 1. ГЛАВНЫЙ ПРИНЦИП

> **M3 должен уметь реконструировать путь, но не должен решать, что реконструированный путь является исторической истиной.**

```
existing evidence → existing temporal graph → candidate traversal → ReconstructionPath → provenance + confidence
```

НЕ:
```
gap → invented node → historical fact
```

---

## 2. AUDIT РЕЗУЛЬТАТ

| Существующее | Статус | Решение M3 |
|--------------|--------|-----------|
| `RelationGraph.find_path()` | ✅ BFS | **REUSE pattern** — свой BFS в TemporalGraph |
| `RelationGraph.get_neighbors()` | ✅ DFS | **REUSE pattern** — свой DFS в TemporalGraph |
| `ProvenanceRegistry.save/load()` | ✅ JSON | **FOLLOW pattern** — JSON persistence |
| `ConsistencyEngine` | ✅ правила мира | **EXTEND** — свои правила в path_validator |
| `HypothesisGenerator` | ✅ гипотезы мира | **KEEP separate** — другая ответственность |
| `TimelinePlanner` | ✅ story constraints | **KEEP separate** — narrative ordering |
| **Существующий ReconstructionEngine?** | ❌ Нет | **CREATE** — `TemporalReconstructionEngine` |

---

## 3. АРХИТЕКТУРА

```
Temporal Model (M2)
    ↓
TemporalGraph          ← обёртка над TemporalNode + TemporalRelation
    ↓
TemporalReconstructionEngine
    ↓
┌──────────────┬──────────────┐
│  BACKWARD    │   FORWARD    │
│  TODAY→...   │  ARKAIM→...  │
└──────────────┴──────────────┘
    ↓
Candidate Paths
    ↓
PathValidator      ← node/relation/direction/temporal consistency
    ↓
ReconstructionPath
    ↓
provenance + confidence
```

---

## 4. CREATED FILES

| Файл | Назначение |
|------|-----------|
| [core/CORE/narrative_engine/temporal/graph.py](core/CORE/narrative_engine/temporal/graph.py) | TemporalGraph — BFS/DFS traversal |
| [core/CORE/narrative_engine/temporal/path_validator.py](core/CORE/narrative_engine/temporal/path_validator.py) | PathValidator — валидация путей |
| [core/CORE/narrative_engine/temporal/reconstruction_engine.py](core/CORE/narrative_engine/temporal/reconstruction_engine.py) | TemporalReconstructionEngine — основной engine |

## 5. EXTENDED FILES

| Файл | Изменение |
|------|-----------|
| [core/CORE/narrative_engine/temporal/__init__.py](core/CORE/narrative_engine/temporal/__init__.py) | Экспорт M3 классов |

---

## 6. API ENGINE

### 6.1 Node / Relation Management
```python
engine = TemporalReconstructionEngine()
engine.add_node(node)           # Добавить узел
engine.add_relation(rel)        # Добавить связь
engine.remove_node(node_id)     # Удалить узел
engine.get_node(node_id)        # Получить узел
engine.get_all_nodes()          # Все узлы
engine.get_all_relations()      # Все связи
```

### 6.2 Path Finding
```python
# Найти ВСЕ пути между узлами
results = engine.find_paths("n1", "temporal_today", ChainDirection.BACKWARD)

# Найти кратчайший путь (BFS)
result = engine.find_shortest_path("n1", "temporal_today")

# Найти путь через gap
results = engine.reconstruct_gap(gap)
```

### 6.3 Chain Reconstruction
```python
# Построить chain от anchor в направлении
path = engine.reconstruct_chain("temporal_today", ChainDirection.BACKWARD)
path = engine.reconstruct_chain("arkaim_temporal", ChainDirection.FORWARD)
```

### 6.4 Gap Detection
```python
gaps = engine.detect_gaps(chain)  # Найти пробелы в chain
```

### 6.5 Provenance Helpers
```python
tags = TemporalReconstructionEngine.compute_path_provenance(nodes, relations)
confidence = TemporalReconstructionEngine.compute_path_confidence(nodes, relations)
```

**Правило compute_path_provenance:**
- ALL AUTHOR_CANON → AUTHOR_CANON
- ALL EXTERNAL_SOURCE → EXTERNAL_SOURCE  
- ANY HYPOTHESIS → HYPOTHESIS
- ANY RECONSTRUCTION → RECONSTRUCTION
- MIXED/UNKNOWN → HYPOTHESIS (с нотой)

### 6.6 Persistence
```python
engine.save_reconstruction(result, output_path)  # JSON
loaded = engine.load_reconstruction(path)         # JSON
```

---

## 7. TEMPORAL GRAPH

```python
class TemporalGraph:
    """BFS/DFS traversal для TemporalNode + TemporalRelation."""

    def bfs_path(self, source_id, target_id, max_depth=10) → Optional[list[str]]
    def all_paths(self, source_id, target_id, max_depth=10) → list[list[str]]
    def get_neighbors(self, node_id, max_depth=3) → dict[str, list[TemporalRelation]]
    def add_node(node), add_relation(rel), remove_node(node_id)
    def get_node(id), get_outgoing(id), get_incoming(id)
```

**BFS pattern заимствован из `RelationGraph.find_path()`**, но адаптирован для temporal relations (bidirectional traversal через incoming/outgoing).

---

## 8. PATH VALIDATOR

```python
class PathValidator:
    """Проверка кандидатных путей."""

    RULE_NODE_MISSING = "node_missing"         # hard
    RULE_RELATION_MISSING = "relation_missing" # hard
    RULE_DIRECTION_CONFLICT = "direction_conflict"  # soft
    RULE_TEMPORAL_CONFLICT = "temporal_conflict"    # hard
    RULE_PROVENANCE_DOWNGRADE = "provenance_downgrade"  # soft
    RULE_SELF_LOOP = "self_loop"               # soft
    RULE_CYCLE = "cycle"                       # hard
```

**Результат:** `PathValidationResult` с `is_valid`, `is_hard_valid`, `score`, `violations`, `warnings`.

---

## 9. DIRECTIONS

### 9.1 BACKWARD (TODAY → HISTORY → ARKAIM)
```python
chain = engine.reconstruct_chain("temporal_today", ChainDirection.BACKWARD)
# Внутренне: _trace_backward()
# Следует по incoming relations (PRECEDES → предшественники)
# и outgoing AFTER/FOLLOWS/TRANSFORMS_INTO (обратные направления)
```

### 9.2 FORWARD (ARKAIM → DEVELOPMENT → TODAY → FUTURE)
```python
chain = engine.reconstruct_chain("arkaim_temporal", ChainDirection.FORWARD)
# Внутренне: _trace_forward()
# Следует по outgoing relations (PRECEDES → наследники)
# и incoming BEFORE/DEVELOPS_FROM (обратные направления)
```

---

## 10. GAP HANDLING

```python
# Детекция пробелов в chain
gaps = engine.detect_gaps(chain)

# Реконструкция конкретного gap
results = engine.reconstruct_gap(gap)
```

**Правила:**
- `INSUFFICIENT_DATA` + нет `candidate_bridges` → возвращает unresolved result (НЕ заполняет)
- `INSUFFICIENT_DATA` + есть `candidate_bridges` → проверяет bridges, но НЕ создаёт новые
- `RECONSTRUCTABLE` → аналогично, проверяет bridges
- `DOCUMENTED` / `PARTIALLY_DOCUMENTED` → может быть обработан

**Критическое правило:** `reconstruct_gap()` НЕ создаёт новые узлы. Только использует существующие.

---

## 11. PROVENANCE SAFETY

| Входной provenance | Результат | Статус |
|-------------------|-----------|--------|
| AUTHOR_CANON + AUTHOR_CANON | AUTHOR_CANON | ✅ |
| EXTERNAL_SOURCE + EXTERNAL_SOURCE | EXTERNAL_SOURCE | ✅ |
| HYPOTHESIS + HYPOTHESIS | HYPOTHESIS | ✅ |
| AUTHOR_CANON + HYPOTHESIS | HYPOTHESIS | ⚠️ Mixed |
| ANY + confidence=0.99 | НЕ меняется | ✅ |

**Никогда:**
- confidence ↑ → provenance ↑
- HYPOTHESIS → AUTHOR_CANON
- EXTERNAL_SOURCE → AUTHOR_CANON
- RECONSTRUCTION → AUTHOR_CANON

---

## 12. ARKAIM INTEGRATION

```python
anchor = ArkaimAnchor.from_existing_data()
# node.id = "temporal_arkaim_anchor"

#参与 reconstruction
chain = engine.reconstruct_chain("arkaim_temporal", ChainDirection.FORWARD)
# Возвращает существующие узлы, НЕ создаёт новых
```

**Ограничение:** Engine не добавляет новые авторские утверждения об Аркаиме.

---

## 13. TESTS

```
test_temporal_reconstruction.py:    55 passed ✅
test_temporal_model.py:             63 passed ✅
test_provenance.py:                 55 passed ✅
test_narrative_world_model.py:      14 passed ✅
─────────────────────────────────────────────
ИТОГО M1+M2+M3:   188 passed, 0 failures
```

**Regression:** 133 passed (M1+M2 unchanged)

---

## 14. CRITICAL INVARIANTS VERIFIED

| Инвариант | Статус |
|-----------|--------|
| `unknown date` ≠ error | ✅ |
| `unknown gap` ≠ error | ✅ |
| `confidence ↑` ≠ `provenance ↑` | ✅ |
| `EXTERNAL_SOURCE` ≠ `AUTHOR_CANON` | ✅ |
| `RECONSTRUCTION` ≠ `FACT` | ✅ |
| `HYPOTHESIS` ≠ `FACT` | ✅ |
| candidate path ≠ proven fact | ✅ |
| missing bridge ≠ invented bridge | ✅ |
| no invented nodes in path | ✅ |
| no invented relations in path | ✅ |
| no automatic gap filling | ✅ |
| ArkaimAnchor — no new assertions | ✅ |
| PresentAnchor — valid traversal endpoint | ✅ |
| Direction consistency | ✅ |
| Temporal consistency (no contradictions) | ✅ |

---

## 15. DOCS

- [docs/M3_TEMPORAL_RECONSTRUCTION_AUDIT.md](docs/M3_TEMPORAL_RECONSTRUCTION_AUDIT.md) — аудит
- [docs/M2_TEMPORAL_MODEL.md](docs/M2_TEMPORAL_MODEL.md) — M2 (ссылка)

---

## 16. REMAINING GAPS

1. **API routes** `/book/temporal/*` — HTTP endpoints для reconstruction
2. **Integration с WorldEngineV2** — temporal awareness в world state
3. **VisualGenome temporal** — временная осведомлённость визуализации
4. **Integration с ExpansionLayer** — потребление temporal data
5. **FutureExtrapolator** — проекция в будущее (M8)

---

**M3 завершён. Код не сломан. Переход к M4 только после подтверждения.**
