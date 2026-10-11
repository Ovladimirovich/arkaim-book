# M3 — TEMPORAL RECONSTRUCTION ENGINE AUDIT

**Дата:** 2025-07  
**Статус:** M2 завершён, M3 начинается

---

## 1. СУЩЕСТВУЮЩАЯ TEMPORAL ИНФРАСТРУКТУРА (M2)

### 1.1 TemporalNode
```python
TemporalNode(
    id, label, precision, era_id, entity_ids, event_ids,
    provenance, confidence, bounds, notes, is_anchor
)
```
- 10 уровней TemporalPrecision
- factory: `from_epoch()`, `present_anchor()`, `gap_node()`
- to_dict/from_dict для serialization
- **Паттерн persistence:** JSON file (как ProvenanceRegistry)

### 1.2 TemporalRelation
```python
TemporalRelation(
    id, source_id, target_id, relation_type, strength,
    provenance, confidence, epoch, bidirectional
)
```
- 12 типов: BEFORE, AFTER, OVERLAPS, CONTAINS, CONTAINED_BY,
  CONTEMPORARY_WITH, PRECEDES, FOLLOWS, DEVELOPS_FROM, TRANSFORMS_INTO,
  COEXISTS_WITH, UNKNOWN
- reverse_relations mapping
- factories: `develops_from()`, `transforms_into()`, `precedes()`, `contemporary_with()`
- **HYPOTHESIS provenance по умолчанию** для DEVELOPS_FROM/TRANSFORMS_INTO

### 1.3 TemporalChain
```python
TemporalChain(
    id, label, direction, nodes, relations, gaps,
    provenance, confidence
)
```
- BACKWARD / FORWARD / BI_DIRECTIONAL
- add_node(), add_relation(), add_gap()
- get_node(), get_relation(), get_outgoing/incoming_relations()
- has_gap_between(), is_continuous()
- **is_continuous() исправлен в M2: True только если len(gaps)==0**

### 1.4 TemporalGap
```python
TemporalGap(
    id, from_node, to_node, reason, evidence_status,
    candidate_bridges, notes
)
```
- 6 статусов: DOCUMENTED, PARTIALLY_DOCUMENTED, INSUFFICIENT_DATA, RECONSTRUCTABLE, HYPOTHETICAL, UNKNOWN
- factories: `unknown_gap()`, `reconstructable_gap()`
- **INSUFFICIENT_DATA — валидное состояние, не ошибка**

### 1.5 ReconstructionPath
```python
ReconstructionPath(
    id, direction, nodes, relations, gaps,
    provenance, confidence, description
)
```
- add_node(), add_relation(), add_gap()
- is_complete, gap_count, unknown_gap_count
- to_dict/from_dict

### 1.6 PresentAnchor / ArkaimAnchor
- PresentAnchor.for_entity() — современный якорь
- ArkaimAnchor.from_existing_data() — без новых утверждений

---

## 2. СЩЕСТВУЮЩАЯ GRAPH TRAVERSAL (НЕ M2)

### 2.1 RelationGraph (relation_models.py)
```python
class RelationGraph:
    def find_path(self, source_id, target_id, max_depth=5) → RelationPath
    def get_neighbors(self, entity_id, max_depth=1) → dict
    def get_relations_from/to/of_type()
```
- BFS path finding (find_path)
- DFS neighbor traversal (get_neighbors)
- Indexed by source/target/type

**РЕШЕНИЕ:** M3 использует **собственный** BFS для TemporalChain. RelationGraph — другой граф (世界 связей, не временной). Но паттерн BFS из RelationGraph заимствуется.

### 2.2 WorldEngine (world_engine.py)
```python
class WorldEngine:
    - relation_graph: RelationGraph
    - world_model: WorldModelExt
    - form_engine: FormEngine
    - consistency: ConsistencyEngine
    - experience: ExperienceEngine
```
- Singleton pattern: `get_world_engine()`
- Lazy initialization
- search(), get_entity(), get_entity_context()

**РЕШЕНИЕ:** M3 не интегрируется в WorldEngine напрямую (пока). Отдельный модуль temporal/reconstruction_engine.py.

### 2.3 ConsistencyEngine (consistency_engine.py)
```python
DEFAULT_RULES = [
    ("temporal_no_future", HARD),
    ("spatial_single_location", HARD),
    ("causal_no_effect_without_cause", HARD),
    ("technology_epoch_restriction", HARD),
    ("symbol_meaning_consistency", SOFT),
]
```
- TEMPORAL правило: "Characters cannot know events before they happen"
- **Расширяемо:** можно добавить правило для temporal reconstruction

**РЕШЕНИЕ:** M3 добавляет свои правила консистентности в отдельный модуль. Не модифицирует ConsistencyEngine.

### 2.4 HypothesisGenerator (hypothesis_generator.py)
- Генерация гипотез о развитии мира
- НЕ temporal reconstruction
- Разная ответственность

---

## 3. ПЕРСИСТЕНС

### 3.1 Присутствующие механизмы
| Компонент | Механизм |
|-----------|----------|
| WorldModel | JSON file (WORLD_MODEL.json) |
| RelationGraph | JSON file + SQLite (runtime/arkaim.db) |
| ProvenanceRegistry | JSON file |
| StoryStore | SQLite (runtime/arkaim.db) |
| CoreMemory | SQLite (runtime/memory/data/memory.db) |

**РЕШЕНИЕ:** M3 использует **JSON file** (как ProvenanceRegistry). Не создаёт новую БД.

### 3.2 Путь для сохранения
```
runtime/runtime_data/temporal/reconstructions/
```
Создаётся при первом сохранении.

---

## 4. ГРАНИЦА ОТВЕТСТВЕННОСТИ

| Компонент | Ответственность |
|-----------|----------------|
| **TimelinePlanner** | Story constraints, ordering within epoch |
| **TemporalChain** | Структура temporal graph (узлы + связи + пробелы) |
| **TemporalReconstructionEngine** | Анализ структуры, поиск путей, реконструкция пробелов |
| **ConsistencyEngine** | Проверка правил мира (включая temporal правила) |

**TimelinePlanner ≠ ReconstructionEngine.**  
TimelinePlanner — narrative story flow.  
ReconstructionEngine — temporal graph analysis.

---

## 5. РЕШЕНИЯ M3

### 5.1 Не создавать
- ~~ArkaimCore~~ (M3 запрет)
- ~~FutureExtrapolator~~ (M8)
- ~~Новую БД~~ (уже есть arkaim.db + JSON)
- ~~GraphEngine~~ (не существует, не нужно)
- ~~Дубликат BFS~~ (заимствуем паттерн из RelationGraph)
- ~~Web research~~ (M3 запрет)

### 5.2 Создать
- `temporal/reconstruction_engine.py` — основной engine
- `temporal/path_validator.py` — валидация путей
- `runtime/tests/test_temporal_reconstruction.py` — 30+ тестов

### 5.3 Интеграция
- API route `/book/temporal/reconstruct` (если паттерн API существует)
- Проверить: есть ли `/book/temporal/*` роуты?

---

## 6. ПРОВЕРКА API ПАТТЕРНА

Проверяю, есть ли уже temporal API:

```bash
grep -r "temporal" runtime/core/routes/
```

**Результат:** temporal routes НЕ существуют. M3 не создаёт API (M3 запрет — "API только если паттерн уже есть").

---

## 7. ИТОГ АУДИТА

| Вопрос | Ответ |
|--------|-------|
| Существующий ReconstructionEngine? | ❌ Нет |
| Дублирующая temporal система? | ❌ Нет (M2 — единственный) |
| Конфликт M2 contracts? | ❌ Нет |
| Два provenance системы? | ❌ Нет (M1 — единственная) |
| Направленность определена? | ✅ BACKWARD/FORWARD |
| Persistence совместим? | ✅ JSON (как ProvenanceRegistry) |
| API конфликтует? | ❌ Нет (temporal API отсутствует) |

**Решение:** M3 реализуется как `temporal/reconstruction_engine.py`.  
BFS-паттерн заимствуется из `RelationGraph.find_path()`.  
Persistence — JSON файл в `runtime/runtime_data/temporal/`.
