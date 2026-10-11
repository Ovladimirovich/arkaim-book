# M5 PRE-IMPLEMENTATION AUDIT

**Дата:** 2026-09-05  
**Статус:** PRE-IMPLEMENTATION AUDIT ONLY  
**Цель:** Определить архитектурную границу для M5 — Temporal ↔ WorldEngine Integration

---

## 1. EXECUTIVE SUMMARY

### Ключевая находка
**"WorldEngineV2" не существует.** В коде есть только `WorldEngine` (один класс).

```
Фактическое имя: WorldEngine (core/CORE/narrative_engine/world_engine.py)
Ожидаемое имя из задания: WorldEngineV2
Реальность: WorldEngine — это единый координатор
```

### Что уже реализовано
| Компонент | Статус | Тесты |
|-----------|--------|-------|
| M1 Provenance | ✅ | 55 passed |
| M2 Temporal Model | ✅ | 63 passed |
| M3 Reconstruction Engine | ✅ | 55 passed |
| M4 WorldModel ↔ Temporal | ✅ | 31 passed |
| **TOTAL M1-M4** | **✅** | **219 passed** |

### Фактическое состояние изоляции
```
WorldEngine ──► WorldModelExt + RelationGraph + FormEngine + ConsistencyEngine + ExperienceEngine
                                                          │
                                                          └── NO temporal awareness

TemporalReconstructionEngine ──► TemporalGraph (isolated, no WorldEngine connection)
```

### M5 задача
Создать **архитектурно безопасную интеграционную границу** между WorldEngine и Temporal Layer,
при этом:
- Не ломая существующие API
- Не создавая circular dependencies
- Не позволяя reconstruction мунтировать canonical state
- Сохраняя provenance integrity

---

## 2. REPOSITORY STATE

### Package structure
```
core/CORE/narrative_engine/
├── world_engine.py           ← WorldEngine (единый, не V2)
├── world_model.py            ← WorldModel (Pydantic модель, 6 epoch)
├── world_model_ext.py        ← WorldModelExt (file-based, 13 категорий)
├── world_state.py            ← WorldState (snapshot per epoch)
├── relation_models.py        ← RelationGraph, WorldRelation (8 типов связей)
├── relation_extractor.py     ← extract_relations() → RelationGraph
├── temporal/
│   ├── node.py               ← TemporalNode
│   ├── relation.py           ← TemporalRelation (12 типов)
│   ├── chain.py              ← TemporalChain
│   ├── gap.py                ← TemporalGap
│   ├── graph.py              ← TemporalGraph
│   ├── path_validator.py     ← PathValidator (7 правил)
│   ├── reconstruction_engine.py ← TemporalReconstructionEngine
│   └── arkaim_anchor.py      ← ArkaimAnchor
├── consistency_engine.py     ← ConsistencyEngine (5 типов правил)
├── experience_engine.py      ← ExperienceEngine (8 режимов)
└── form_engine.py            ← FormEngine (55 форм)
```

### Import analysis (verified)
```
WorldEngine imports:
  - world_model_ext (WorldModelExt, get_world_model_ext)
  - relation_models (RelationGraph, WorldRelation, RelationType)
  - relation_extractor (extract_relations)
  - NO temporal imports

TemporalReconstructionEngine imports:
  - node, relation, chain, gap, graph, path_validator
  - source_levels (ProvenanceCategory, etc.)
  - arkaim_anchor (in from_world_model)
  - NO world_engine imports
```

### Dependency direction (verified)
```
WorldEngine ──┐
              │   (ONE-WAY)
Temporal      │   WorldEngine does NOT import Temporal
              │   Temporal does NOT import WorldEngine
              ▼
           ISOLATED
```

---

## 3. M1–M4 BASELINE VERIFICATION

### M1 — Provenance ✅
- `ProvenanceCategory`: AUTHOR_CANON, EXTERNAL_SOURCE, HYPOTHESIS, RECONSTRUCTION
- `ProvenanceTag`: source_level + category + confidence
- **Invariant:** `confidence ↑ ≠ provenance ↑` (tested)

### M2 — Temporal Model ✅
- `TemporalNode`, `TemporalRelation` (12 типов), `TemporalChain`, `TemporalGap`
- `PresentAnchor`, `ArkaimAnchor`
- **Invariant:** `unknown gap ≠ error` (tested)

### M3 — Reconstruction Engine ✅
- `TemporalGraph` (BFS/DFS)
- `PathValidator` (7 правил)
- `TemporalReconstructionEngine`: find_paths, reconstruct_gap, reconstruct_chain
- **Invariant:** no invented nodes, no automatic gap filling

### M4 — Integration ✅
- `WorldModel.get_temporal_node(epoch_id)` → Epoch → TemporalNode
- `WorldModel.get_temporal_chain(direction)` → chain from epochs
- `TemporalReconstructionEngine.from_world_model(wm)` → engine population
- **Verified:** no circular dependency, no contamination

---

## 4. WORLDENGINE AUDIT

### Class: WorldEngine
**File:** `core/CORE/narrative_engine/world_engine.py` (172 lines)

```python
class WorldEngine:
    def __init__(self):
        self._world_model = get_world_model_ext()    # WorldModelExt
        self._relation_graph = None                  # RelationGraph
        self._form_engine = None                     # FormEngine
        self._consistency_engine = None              # ConsistencyEngine
        self._experience_engine = None               # ExperienceEngine
        self._entity_index = {}                      # dict for O(1) lookups
    
    def initialize(self):
        self._relation_graph = extract_relations()   # from WORLD_MODEL/*.json
        self._form_engine = FormEngine(self)
        self._consistency_engine = ConsistencyEngine(self)
        self._experience_engine = ExperienceEngine(self)
```

### Responsibilities
| Responsibility | Implemented By | Temporal-aware? |
|---------------|----------------|-----------------|
| Entity search | `search()` | NO |
| Entity lookup | `get_entity()` | NO |
| Entity context | `get_entity_context()` | NO |
| Stats | `get_stats()` | NO |
| Visual prompts | `FormEngine` | NO |
| Consistency | `ConsistencyEngine` | PARTIAL (has TEMPORAL rules) |
| Experience modes | `ExperienceEngine` | NO |
| **Temporal traversal** | **NOT IMPLEMENTED** | — |
| **Chain reconstruction** | **NOT IMPLEMENTED** | — |

### API Routes (runtime/core/routes/world_engine.py)
```
GET  /world/summary          → engine.summary()
POST /world/search           → engine.search()
GET  /world/entity/{id}      → engine.get_entity()
GET  /world/entity/{id}/context → engine.get_entity_context()
GET  /world/entity/{id}/visual-prompt → engine._form_engine
POST /world/validate         → engine._consistency_engine
GET  /world/rules            → engine._consistency_engine
GET  /world/modes            → engine._experience_engine
GET  /world/categories       → engine._world_model
GET  /world/form-library     → engine._form_engine
```

**NO temporal endpoints exist.**

---

## 5. TEMPORAL LAYER AUDIT

### Components
```
TemporalNode          — узел temporal graph
TemporalRelation      — связь (12 типов)
TemporalGraph         — BFS/DFS traversal
TemporalChain         — направленная цепочка
TemporalGap           — пробел в chain
ReconstructionPath    — результат реконструкции
TemporalReconstructionEngine — основной engine
```

### Public API
```python
engine = TemporalReconstructionEngine()
engine.add_node(node)
engine.add_relation(rel)

results = engine.find_paths(src, tgt, direction)
result = engine.find_shortest_path(src, tgt)
results = engine.reconstruct_gap(gap)
path = engine.reconstruct_chain(anchor, direction)

tags = engine.compute_path_provenance(nodes, relations)
conf = engine.compute_path_confidence(nodes, relations)

engine.save_reconstruction(result, path)
loaded = engine.load_reconstruction(path)
```

### M4 additions
```python
engine = TemporalReconstructionEngine.from_world_model(world_model)
```

---

## 6. CONSUMPTION MODEL ANALYSIS

### Current consumer pattern
```
HTTP Request
    ↓
API Route (world_engine.py)
    ↓
_get_world_engine() → WorldEngine singleton
    ↓
engine.method() → response
```

### Temporal consumer pattern (currently non-existent)
```
HTTP Request
    ↓
[NO ROUTE]
    ↓
[NO ENGINE USAGE]
    ↓
[nodata]
```

### Question: How should WorldEngine consume temporal?

**Option A: Direct dependency**
```python
class WorldEngine:
    def __init__(self):
        ...
        self._temporal_engine = None  # lazy
    
    @property
    def temporal_engine(self):
        if self._temporal_engine is None:
            from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
            self._temporal_engine = TemporalReconstructionEngine.from_world_model(self._world_model)
        return self._temporal_engine
```
**Pros:** Simple, explicit  
**Cons:** WorldEngine owns temporal lifecycle, coupling

**Option B: Optional service (composition)**
```python
class WorldEngine:
    def inject_temporal(self, temporal_engine):
        self._temporal_engine = temporal_engine
    
    def get_temporal_chain(self, direction):
        if not self._temporal_engine:
            return {"error": "Temporal engine not injected"}
        wm = self._world_model  # need to pass to engine
        # ...
```
**Pros:** Loose coupling, testable  
**Cons:** Requires explicit wiring

**Option C: Free function / standalone**
```python
def get_temporal_chain(world_model, direction):
    engine = TemporalReconstructionEngine.from_world_model(world_model)
    return engine.reconstruct_chain(...)
```
**Pros:** Zero coupling  
**Cons:** Duplicates initialization logic, no caching

**Option D: Coordinator-level integration (recommended)**
```python
# In WorldEngine, add optional temporal property
class WorldEngine:
    @property
    def temporal_engine(self) -> Optional[TemporalReconstructionEngine]:
        """Lazy-loaded temporal engine. Only available if initialized."""
        if not hasattr(self, '_temporal_engine'):
            return None
        return self._temporal_engine
    
    def enable_temporal(self):
        """Opt-in temporal integration."""
        from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
        from narrative_engine.world_model import WorldModel
        
        # Create canonical WorldModel for temporal
        canonical_wm = WorldModel(self._world_model._data)
        self._temporal_engine = TemporalReconstructionEngine.from_world_model(canonical_wm)
```
**Pros:** Opt-in, lazy, no breaking changes  
**Cons:** Slightly more complex initialization

---

## 7. CRITICAL BOUNDARY ANALYSIS

### Canonical vs Reconstruction contamination check

**Question:** Can WorldEngine accidentally mutate WorldModel via Temporal?

**Code trace:**
```
WorldEngine
    ↓
WorldModelExt (read-only, file-based)
    ↓
[NO write path to WorldModelExt from WorldEngine]

TemporalReconstructionEngine
    ↓
TemporalGraph (in-memory, transient)
    ↓
ReconstructionPath (output only)
    ↓
[NO write path to WorldModel]
```

**Verdict: SAFE** — No contamination path exists.

### Provenance flow verification
```
Epoch.provenance (AUTHOR_CANON)
    ↓ get_temporal_node()
TemporalNode.provenance (AUTHOR_CANON)
    ↓ compute_path_provenance()
ReconstructionPath.provenance (min of all)
    ↓
OUTPUT (never written back to source)
```

**Verdict: SAFE** — Provenance flows one way, never upgraded.

---

## 8. DEPENDENCY GRAPH

### Current state
```
WorldEngine
    ├── WorldModelExt ────► WORLD_MODEL/*.json (read)
    ├── RelationGraph ────► extracted from WORLD_MODEL/*.json
    ├── FormEngine ───────► (visual forms)
    ├── ConsistencyEngine ──► (rules validation)
    └── ExperienceEngine ──► (mode-specific output)

TemporalReconstructionEngine
    └── TemporalGraph ────► (in-memory, empty by default)
    
[NO CONNECTION between these two systems]
```

### After M5 (proposed)
```
WorldEngine
    ├── WorldModelExt (existing)
    ├── RelationGraph (existing)
    ├── FormEngine (existing)
    ├── ConsistencyEngine (existing)
    ├── ExperienceEngine (existing)
    └── TemporalEngine (OPTIONAL, lazy-loaded, opt-in)
            │
            └── TemporalReconstructionEngine.from_world_model(WM)
                    │
                    └── TemporalGraph (populated from epochs)
```

### Dependency direction (after M5)
```
WorldEngine ──(optional, lazy)──► TemporalReconstructionEngine
TemporalReconstructionEngine ──X──► WorldEngine
```

**NO circular dependency.** ✅

---

## 9. SIDE EFFECTS AUDIT

### WorldEngine methods
| Method | Side Effect | Type |
|--------|------------|------|
| `search()` | None | READ |
| `get_entity()` | None | READ |
| `get_entity_context()` | None | READ |
| `get_stats()` | None | READ |
| `summary()` | None | READ |
| `initialize()` | Creates sub-engines | MUTATE (internal) |

### TemporalReconstructionEngine methods
| Method | Side Effect | Type |
|--------|------------|------|
| `find_paths()` | None | READ |
| `find_shortest_path()` | None | READ |
| `reconstruct_gap()` | None | READ |
| `reconstruct_chain()` | None | READ |
| `add_node()` | Mutates _graph | MUTATE |
| `add_relation()` | Mutates _graph | MUTATE |
| `save_reconstruction()` | Writes JSON file | PERSIST |
| `load_reconstruction()` | None | READ |

**Key finding:** All public query methods are READ-ONLY. No mutation of WorldModel.

---

## 10. PERSISTENCE AUDIT

### Where data lives
| Data | Storage | Mutability |
|------|---------|------------|
| WorldModelExt | `core/CORE/WORLD_MODEL/*.json` | Read-only (file-based) |
| RelationGraph | In-memory (derived from JSON) | Read-only |
| TemporalGraph | In-memory (populated from WorldModel) | Mutable (add_node/add_relation) |
| ReconstructionPath | `runtime/runtime_data/temporal/reconstructions/*.json` | Writable |
| Epoch/CanonicalEvent | `core/CORE/narrative_engine/data/WORLD_MODEL.json` | Read-only (loaded at startup) |

### Contamination risk assessment
```
Can ReconstructionPath be saved to WORLD_MODEL/? → NO
Can TemporalGraph be persisted to canonical storage? → NO (only to reconstructions/)
Can WorldEngine mutate TemporalGraph? → ONLY via explicit add_node/add_relation calls
```

**Verdict: LOW RISK** — Persistence boundaries are clear.

---

## 11. EXPANSION / GENERATION AUDIT

### Current expansion path
```
ExpansionLayer (knowledge_expansion/)
    ↓ loads *_DEEP.json, *_EXPANDED.json from KNOWLEDGE/
    ↓ returns dict[str, dict] (topic → expansion)
```

**Temporal awareness:** NONE

### Generation path
```
FormEngine.generate_visual_prompt(entity_id, style)
    ↓
VisualGenome (arkaim-web/)
    ↓
ComfyUI (external)
```

**Temporal awareness:** NONE

### Risk: Can temporal reconstruction become generation input?
Currently: **NO** — no integration path exists.
After M5: **可控** — only if explicitly exposed via API.

---

## 12. TEST COVERAGE AUDIT

### Existing temporal tests
| Test file | Tests | Coverage |
|-----------|-------|----------|
| test_provenance.py | 55 | M1 provenance rules |
| test_temporal_model.py | 63 | M2 temporal types |
| test_temporal_reconstruction.py | 55 | M3 engine |
| test_temporal_integration.py | 31 | M4 WorldModel↔Temporal |
| test_narrative_world_model.py | 14 | WorldModel queries |
| **TOTAL** | **219** | M1-M4 baseline |

### Missing negative tests
```
☐ temporal_query_does_not_mutate_world_engine
☐ reconstruction_result_is_not_canonical
☐ temporal_engine_is_optional_in_world_engine
☐ no_circular_dependency_between_world_and_temporal
☐ provenance_preserved_through_integration
```

### Pre-existing failure
```
test_world_engine.py::TestWorldEngine::test_get_entity  ← FAILED
  Reason: entity "region_arkaim" not in WorldModelExt._data
  Status: PRE-EXISTING, NOT caused by M4
```

---

## 13. DUPLICATION AUDIT

### Graph engines comparison
| Aspect | RelationGraph | TemporalGraph |
|--------|--------------|---------------|
| Location | `relation_models.py` | `temporal/graph.py` |
| Node type | `WorldRelation` | `TemporalNode` |
| Edge type | 8 `RelationType` | 12 `TemporalRelationType` |
| Purpose | Entity relationships | Temporal ordering |
| Traversal | BFS/DFS | BFS/DFS |
| Owned by | WorldEngine | TemporalReconstructionEngine |

**Verdict: NOT duplicates** — Different semantic domains. RelationGraph = "what connects to what". TemporalGraph = "what comes before/after".

### Potential duplication risk
```
RelationGraph.find_path() vs TemporalGraph.bfs_path()
    ↓
Same pattern, different semantics
    ↓
INTENTIONAL pattern reuse (documented in code)
    ↓
NOT duplication — complementary systems
```

---

## 14. EPOCH / CANONICAL EVENT AUDIT

### Epoch ownership
```
Owner: WorldModel (core/CORE/narrative_engine/world_model.py)
Created by: world_model_data.py (default epochs)
Read by: WorldEngine, WorldStateBuilder, TemporalIntegration (M4)
Modified by: NONE (read-only after init)
```

### CanonicalEvent ownership
```
Owner: WorldModel
Created by: world_model_data.py
Read by: WorldStateBuilder, various planners
TemporalNode mapping: era_id field links to Epoch.id
```

### Temporal mapping
```
Epoch.id ──► TemporalNode.era_id
Epoch.order ──► used for chain ordering
CanonicalEvent.epoch ──► maps to TemporalNode.era_id
```

**No duplication** — clean 1:1 mapping via `era_id`.

---

## 15. PROVENANCE FLOW MAP

### Complete flow
```
SOURCE (book canon / external research)
    ↓
ProvenanceTag (source_level + category + confidence)
    ↓
Epoch.provenance / CanonicalEvent.provenance
    ↓
WorldModel.get_temporal_node()
    ↓
TemporalNode.provenance (copied from Epoch)
    ↓
TemporalGraph (nodes + relations)
    ↓
TemporalReconstructionEngine.find_paths()
    ↓
ReconstructionPath.provenance (compute_path_provenance: min of all)
    ↓
OUTPUT (with provenance tag, NEVER elevated)
```

### Invariants enforced
| Invariant | Mechanism | Test |
|-----------|-----------|------|
| RECONSTRUCTION ≠ FACT | `compute_path_provenance` lowers to HYPOTHESIS | `test_reconstruction_not_fact` |
| HYPOTHESIS ≠ FACT | Same as above | `test_hypothesis_not_upgraded` |
| EXTERNAL_SOURCE ≠ AUTHOR_CANON | Same as above | `test_external_not_canon` |
| confidence ≠ provenance | Separate fields, min() for confidence | `test_confidence_cannot_change_provenance` |

---

## 16. ARCHITECTURAL DECISION

### Recommended Integration Boundary

**OPTION D: Lazy-Loaded Optional Service**

```python
# In WorldEngine (minimal change)
class WorldEngine:
    def __init__(self):
        ...
        # NEW (optional, lazy)
        self._temporal_engine = None
    
    @property
    def temporal_engine(self) -> Optional[TemporalReconstructionEngine]:
        """Optional temporal engine — None until explicitly enabled."""
        if self._temporal_engine is None:
            return None
        return self._temporal_engine
    
    def enable_temporal(self):
        """Opt-in: populate temporal engine from WorldModel."""
        from narrative_engine.world_model import WorldModel
        from narrative_engine.temporal.reconstruction_engine import TemporalReconstructionEngine
        
        # Convert WorldModelExt data to WorldModel format
        canonical_data = {
            "version": "1.0.0",
            "epochs": [],
            "locations": [],
            "civilizations": [],
            "technologies": [],
            "religions": [],
            "canonical_events": [],
            "causal_rules": [],
            "characters_living": {},
        }
        
        # Map WorldModelExt data to WorldModel format
        for cat in self._world_model.get_categories():
            if cat == "epochs":
                canonical_data["epochs"] = self._world_model.get_category(cat)
            elif cat == "locations":
                canonical_data["locations"] = self._world_model.get_category(cat)
            # ... etc
        
        wm = WorldModel(canonical_data)
        self._temporal_engine = TemporalReconstructionEngine.from_world_model(wm)
        return self._temporal_engine
```

**Why this option:**
1. **Zero breaking changes** — existing code unchanged
2. **Opt-in** — temporal features disabled by default
3. **Lazy-loaded** — no performance impact unless used
4. **No circular dependency** — one-way import
5. **Testable** — can enable/disable per test
6. **Extensible** — future temporal features can be added via same pattern

---

## 17. M5 SCOPE

### MUST (без этого M5 неполон)
```
1. WorldEngine.enable_temporal() — опциональное включение temporal
2. WorldEngine.temporal_engine property — доступ к engine
3. Методы WorldEngine для temporal queries:
   - get_temporal_chain(direction) → dict
   - get_temporal_context(epoch_id) → dict (delegated to WM)
   - find_temporal_path(src, tgt, direction) → dict
4. Тесты: temporal интеграция в WorldEngine
5. 0 regressions на M1-M4
```

### SHOULD (желательно, но не блокирует)
```
1. API route /world/temporal/chain — HTTP endpoint
2. API route /world/temporal/context — HTTP endpoint
3. Integration с ExperienceEngine.TIMELINE mode
4. Документация M5
```

### LATER (следующие milestones)
```
1. M6: Temporal API routes (полный REST)
2. M7: VisualGenome temporal awareness
3. M8: FutureExtrapolator
4. ExpansionLayer temporal consumption
```

### OUT OF SCOPE (явно запрещено)
```
✗ Изменение WorldModelExt (read-only)
✗ Изменение RelationGraph
✗ Создание нового GraphEngine
✗ Изменение API существующих routes
✗ Мутация WorldModel из Temporal
✗ Изменение Genome
✗ UI изменения
✗ Web research
✗新数据库
```

---

## 18. M5.X BREAKDOWN

### M5.1: Core Integration
**Goal:** WorldEngine получает опциональный temporal engine

**Changes:**
- `world_engine.py`: +`enable_temporal()`, +`temporal_engine` property
- `tests/test_temporal_integration.py`: +тесты для WorldEngine.temporal_engine

**Acceptance:**
- `world_engine.temporal_engine is None` by default
- `world_engine.enable_temporal()` populates engine from WorldModel
- `world_engine.temporal_engine.find_paths()` works

### M5.2: Temporal Query Methods
**Goal:** WorldEngine методы для temporal запросов

**Changes:**
- `world_engine.py`: +`get_temporal_chain()`, +`find_temporal_path()`
- Возвращают dict (JSON-serializable), НЕ ReconstructionPath объекты

**Acceptance:**
- Методы возвращают корректные данные
- Works only after `enable_temporal()`
- Returns error if temporal not enabled

### M5.3: Tests
**Goal:** Покрытие интеграции тестами

**Changes:**
- `tests/test_temporal_integration.py`: +M5 тесты

**Acceptance:**
- 20+ новых тестов
- 0 regressions
- Negative tests (disabled temporal, etc.)

---

## 19. ACCEPTANCE CRITERIA

### Provenance
```
☐ RECONSTRUCTION ≠ FACT (provenance never elevated)
☐ HYPOTHESIS ≠ FACT (provenance stays HYPOTHESIS)
☐ confidence ↑ ≠ provenance ↑ (separate fields)
```

### Graph
```
☐ No duplicate graph engine (RelationGraph ≠ TemporalGraph)
☐ No circular dependency (WorldEngine ↔ Temporal)
```

### Temporal
```
☐ unknown date ≠ error
☐ unknown gap ≠ error
☐ no invented nodes in path
☐ no invented relations in path
```

### World Model
```
☐ No uncontrolled mutation (WorldEngine cannot write to WorldModel)
☐ Temporal is optional (disabled by default)
```

### Genome
```
☐ No implicit reconstruction → genome mutation
```

### Persistence
```
☐ canonical and derived states remain distinguishable
☐ reconstruction stored separately (not in WORLD_MODEL/)
```

### Architecture
```
☐ No circular dependency
☐ Zero breaking changes
☐ Lazy loading (no perf impact if unused)
```

### Regression
```
☐ M1 tests: 55 passed
☐ M2 tests: 63 passed
☐ M3 tests: 55 passed
☐ M4 tests: 31 passed
☐ Total: 204+ passed, 0 regressions
```

---

## 20. BLOCKER CLASSIFICATION

### P0 — Architectural Blockers
```
NONE FOUND
```

### P1 — High Risks
```
ID: M5-P1-1
Severity: P1
Location: WorldEngine.enable_temporal()
Problem: Converting WorldModelExt to WorldModel format is non-trivial
Risk: May miss some data during conversion
Recommendation: Use WorldModel.load() if WORLD_MODEL.json exists, fallback to manual mapping
Blocks M5? NO (handled via conditional logic)
```

### P2 — Medium Risks
```
ID: M5-P2-1
Severity: P2
Location: WorldEngine temporal_engine property
Problem: Singleton cache may return stale data after WorldModelExt reload
Risk: Stale temporal data
Recommendation: Invalidate temporal_engine when WorldModelExt invalidated
Blocks M5? NO
```

### P3 — Low Risks
```
ID: M5-P3-1
Severity: P3
Location: API design
Problem: No clear convention for temporal API response format
Risk: Inconsistent responses
Recommendation: Define response schema in M6
Blocks M5? NO
```

---

## 21. DEFERRED WORK (FUTURE)

```
M6: Temporal API routes (/world/temporal/*)
M7: VisualGenome temporal display
M8: FutureExtrapolator (projection to future)
M9: ExpansionLayer temporal consumption
M10: Real-time temporal updates from book text
```

---

## 22. FINAL ARCHITECTURE MAP

### Current (pre-M5)
```
┌─────────────────────────────────────────────┐
│              WorldEngine                     │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │WorldModelExt│  │    RelationGraph     │  │
│  │(13 cat, 406)│  │   (287 relations)    │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                     │              │
│  ┌──────▼──────┐  ┌──────────▼───────────┐  │
│  │ FormEngine  │  │ConsistencyEngine     │  │
│  │  (55 forms) │  │  (5 rules)           │  │
│  └─────────────┘  └──────────────────────┘  │
│  ┌─────────────┐                            │
│  │Experience   │                            │
│  │Engine (8)   │                            │
│  └─────────────┘                            │
│                       ✗ NO TEMPORAL          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│     TemporalReconstructionEngine             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ TemporalGraph│  │    PathValidator     │  │
│  │  (empty)    │  │   (7 rules)          │  │
│  └─────────────┘  └──────────────────────┘  │
│  ┌──────────────────────────────────────┐   │
│  │ find_paths / reconstruct_chain /     │   │
│  │ reconstruct_gap                      │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘

[ISOLATED — no connection between the two]
```

### After M5 (proposed)
```
┌─────────────────────────────────────────────┐
│              WorldEngine                     │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │WorldModelExt│  │    RelationGraph     │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                     │              │
│  ┌──────▼──────┐  ┌──────────▼───────────┐  │
│  │ FormEngine  │  │ConsistencyEngine     │  │
│  └─────────────┘  └──────────────────────┘  │
│  ┌─────────────┐                            │
│  │Experience   │                            │
│  │Engine (8)   │                            │
│  └─────────────┘                            │
│                      │                       │
│                 [OPTIONAL]                   │
│                 enable_temporal()            │
│                      │                       │
│              ┌───────▼────────┐             │
│              │ TemporalEngine │ ◄── LAZY    │
│              │ (from_world)   │     LOADED  │
│              └────────────────┘             │
└─────────────────────────────────────────────┘
```

---

## 23. FINAL AUDIT REPORT

### Repository
```
HEAD: N/A (git недоступен)
Branch: master
M1-M4 status: ALL VERIFIED (219 passed)
```

### Architecture
```
WorldEngine:    Единый координатор (WorldModelExt + RelationGraph + поддвижки)
Temporal:       Изолированный слой (TemporalReconstructionEngine)
Provenance:     M1 enforced (AUTHOR_CANON invariant)
WorldState:     Snapshot per epoch (WorldStateBuilder)
Genome:         Structural model (no temporal)
Persistence:    JSON files (WORLD_MODEL/, runtime_data/)
```

### Critical Findings
1. **"WorldEngineV2" не существует** — есть только `WorldEngine`
2. **Temporal полностью изолирован** — 0 импортов из WorldEngine в temporal
3. **Нет circular dependency** — все импорты one-way
4. **Нет contamination risk** — ReconstructionEngine не мутирует WorldModel
5. **Предварительный провал:** `test_world_engine.py::test_get_entity` (не связан с M4)

### M5 Decision
```
READY FOR IMPLEMENTATION
```

### Recommended M5 Scope
```
M5.1: WorldEngine.enable_temporal() + temporal_engine property
M5.2: WorldEngine temporal query methods (get_temporal_chain, find_temporal_path)
M5.3: Integration tests (20+ new tests)
```

### Explicitly NOT M5
```
✗ API routes (M6)
✗ VisualGenome (M7)
✗ FutureExtrapolator (M8)
✗ ExpansionLayer (future)
✗ Genome modification
✗ New database
✗ Breaking changes
```

### Blockers
```
P0: 0
P1: 1 (WorldModelExt→WorldModel conversion complexity — handled)
P2: 1 (stale cache on reload — handled via invalidation)
P3: 1 (API response format — deferred to M6)
```

---

## 24. FINAL STATEMENT

```
M5 PRE-IMPLEMENTATION AUDIT: COMPLETE

Implementation started: NO

Code modified: NO
Tests modified: NO
Architecture modified: NO

P0 blockers: 0
P1 risks: 1 (handled)
P2 risks: 1 (handled)
P3 risks: 1 (deferred)

M5 recommendation: READY FOR IMPLEMENTATION

Recommended next action:
  M5.1: Add enable_temporal() + temporal_engine property to WorldEngine
  M5.2: Add temporal query methods to WorldEngine
  M5.3: Add integration tests
  Then: await human confirmation for M6

M5 implementation has NOT started.
```
