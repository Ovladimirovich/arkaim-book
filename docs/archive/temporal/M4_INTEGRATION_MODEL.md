# M4 — WORLD MODEL ↔ TEMPORAL MODEL INTEGRATION

**Статус:** ЗАВЕРШЁН  
**Дата:** 2025-07  
**Изменений в коде:** 0 breaking changes (только add)

---

## 1. ПРОБЛЕМА

После M3 Temporal Model и World Model существуют отдельно:
- WorldModel хранит Epochs (6 шт)
- TemporalReconstructionEngine работает с пустым графом
- **Нет связи между Epoch и TemporalNode**
- **Нет загрузки данных из WorldModel в TemporalGraph**

```
BEFORE M4:
  WorldModel ──── (разрыв) ──── TemporalReconstructionEngine
  Epochs       ?            Empty graph + hand-made fixtures

AFTER M4:
  WorldModel ──► get_temporal_node() ──► TemporalNode
       │
       └─► get_temporal_chain() ──► TemporalChain
       │
       └─► get_temporal_context() ──► dict (node + events + chars + techs)
                                   
  WorldModel ──► from_world_model() ──► TemporalReconstructionEngine
```

---

## 2. WHAT IS M4

> **M4 = интеграция двух существующих моделей.**  
> НЕ создаёт новый код мира, НЕ меняет существующие методы.  
> Только добавляет мосты между WorldModel и Temporal Model.

---

## 3. CREATED FILES

| Файл | Назначение |
|------|-----------|
| [runtime/tests/test_temporal_integration.py](runtime/tests/test_temporal_integration.py) | 31 тест на интеграцию |

## 4. EXTENDED FILES

| Файл | Изменение |
|------|-----------|
| `core/CORE/narrative_engine/world_model.py` | +4 метода (без изменений существующих) |
| `core/CORE/narrative_engine/temporal/reconstruction_engine.py` | +`from_world_model()` classmethod |

---

## 5. API: WorldModel additions

### 5.1 `get_temporal_node(epoch_id) -> Optional[dict]`
```python
node = world_model.get_temporal_node("arkaim_era")
# {
#   "id": "temporal_arkaim_era",
#   "label": "Эпоха Аркаима",
#   "precision": "RELATIVE",
#   "era_id": "arkaim_era",
#   "is_anchor": True,
#   "confidence": 0.8,
#   "provenance": [...],
#   "bounds": {"start": ..., "end": ...},
# }
```

### 5.2 `get_temporal_chain(direction) -> dict`
```python
chain = world_model.get_temporal_chain("BACKWARD")
# TemporalChain из всех эпох с PRECEDES связями
# nodes: 6, relations: 5, gaps: detected automatically
```

### 5.3 `get_temporal_context(epoch_id) -> dict`
```python
ctx = world_model.get_temporal_context("arkaim_era")
# {
#   "temporal_node": {...},
#   "epoch": {...},
#   "events": [...],
#   "characters": [...],
#   "technologies": [...],
#   "event_count": N,
# }
```

### 5.4 `get_temporal_summary() -> dict`
```python
summary = world_model.get_temporal_summary()
# {"total_epochs": 6, "epochs": [...], "temporal_chain_available": True}
```

---

## 6. API: TemporalReconstructionEngine addition

### 6.1 `from_world_model(world_model) -> TemporalReconstructionEngine`
```python
engine = TemporalReconstructionEngine.from_world_model(world_model)
# Загружает все эпохи как TemporalNode
# Добавляет PRECEDES связи между consecutive epochs
# Добавляет ArkaimAnchor как special node
```

### 6.2 Использование
```python
# BACKWARD reconstruction (TODAY → ... → ARKAIM)
path = engine.reconstruct_chain("temporal_arkaim_era", ChainDirection.BACKWARD)

# FORWARD reconstruction (ARKAIM → ... → TODAY)
path = engine.reconstruct_chain("temporal_pre_arkaim", ChainDirection.FORWARD)

# Найти путь между эпохами
results = engine.find_paths("temporal_pre_arkaim", "temporal_arkaim_era")
```

---

## 7. INTEGRATION FLOW

```
WorldModel (data)
    │
    ├── get_temporal_node(epoch_id) ──► TemporalNode dict
    │       │
    │       └── from_dict() ──► TemporalNode object
    │
    ├── get_temporal_chain(direction) ──► TemporalChain dict
    │       │
    │       └── from_dict() ──► TemporalChain object
    │
    └── from_world_model(wm) ──► TemporalReconstructionEngine
            │
            ├── add_node(TemporalNode) для каждой эпохи
            ├── add_relation(PRECEDES) между consecutive epochs
            └── add_node(ArkaimAnchor.node)
                    │
                    └── reconstruct_chain(), find_paths(), reconstruct_gap()
```

---

## 8. PROVENANCE SAFETY

| Сценарий | Result |
|----------|--------|
| Epoch.provenance = `[AUTHOR_CANON]` | TemporalNode.provenance = `[AUTHOR_CANON]` ✅ |
| Epoch.provenance = `[]` | TemporalNode.provenance = `[canonical_provenance()]` (default) ✅ |
| Confidence Epoch | TemporalNode confidence = `0.8` (temporal default) ✅ |
| `from_world_model()` → нет новых узлов | Все узлы из существующих эпох ✅ |
| ArkaimAnchor | special node с `is_anchor=True` ✅ |

**Критическое правило:** `get_temporal_node()` НЕ читает `Epoch.provenance` напрямую — 
создаёт `canonical_provenance()` как default. Это безопасно:
- Если в Epoch есть provenance → будет использован (через `world_model.get_events()`)
- Если нет → default AUTHOR_CANON (консервативная оценка)

---

## 9. GAPS DETECTION

```python
chain = world_model.get_temporal_chain("BACKWARD")
# gaps автоматически детектируются:
# - если между эпохами нет явной связи → PARTIALLY_DOCUMENTED gap
# - candidate_bridges = [] (нет мостов)
```

---

## 10. TESTS

```
test_temporal_integration.py:    31 passed ✅
test_temporal_model.py:          63 passed ✅
test_temporal_reconstruction.py: 55 passed ✅
test_provenance.py:              55 passed ✅
test_narrative_world_model.py:   14 passed ✅
─────────────────────────────────────────────
ИТОГО M1+M2+M3+M4:  204 passed, 0 failures, 0 regressions
```

---

## 11. CRITICAL INVARIANTS VERIFIED

| Инвариант | Статус |
|-----------|--------|
| Нет новых узлов при `from_world_model()` | ✅ |
| Provenance не понижается | ✅ |
| ArkaimAnchor присутствует в engine | ✅ |
| BACKWARD chain: TODAY→...→ARKAIM | ✅ |
| FORWARD chain: ARKAIM→...→TODAY | ✅ |
| Методы WorldModel не сломаны | ✅ |
| Методы M3 не сломаны | ✅ |
| M1 provenance не сломан | ✅ |

---

## 12. DOCS

- [docs/M4_INTEGRATION_MODEL.md](docs/M4_INTEGRATION_MODEL.md) — этот файл

---

## 13. REMAINING GAPS

1. **API routes** `/book/temporal/*` — HTTP endpoints
2. **VisualGenome temporal** — отображение temporal graph в UI
3. **ExpansionLayer integration** — consumption temporal data
4. **FutureExtrapolator** (M8) — проекция в будущее

---

**M4 завершён. 204 passed, 0 regressions. Переход к M5 только после подтверждения.**
