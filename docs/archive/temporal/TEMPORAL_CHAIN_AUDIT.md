# Temporal Chain Architecture Audit

## 1. VERIFIED EXISTING

### 1.1 Temporal Node Factory Methods
```python
# core/CORE/narrative_engine/temporal/node.py
TemporalNode.present_anchor() → TemporalNode(
    id="temporal_today",
    label="Современность",
    precision=EXACT,
    provenance=[AUTHOR_CANON],
    confidence=1.0,
)
```
**Статус:** МЕТОД ЕСТЬ, но нигде не вызывается. Узел `temporal_today` НЕ создаётся автоматически при загрузке WorldModel.

### 1.2 PresentAnchor (dataclass)
```python
# core/CORE/narrative_engine/temporal/present_anchor.py
PresentAnchor.for_entity(entity_id, label, provenance_tags)
```
**Статус:** Класс есть, но это мета-данные (не узел графа). `temporal_nodes=[]` по умолчанию.

### 1.3 ArkaimAnchor (dataclass)
```python
# core/CORE/narrative_engine/temporal/arkaim_anchor.py
ArkaimAnchor.from_existing_data()
→ ArkaimAnchor(epoch_id="arkaim_era", location_id="arkaim", ...)
→ .node → TemporalNode(id="temporal_arkaim_anchor", ...)
```
**Статус:** Класс есть. Создаёт ДВА узла:
- `temporal_arkaim_anchor` (из ArkaimAnchor, is_anchor=True)
- `temporal_arkaim_era` (из WorldModel epochs, is_anchor=True)

**Проблема:** Два разных ID для одного и того же якоря.

### 1.4 TemporalReconstructionEngine._trace_forward()
```python
# core/CORE/narrative_engine/temporal/reconstruction_engine.py:527
def _trace_forward(self, anchor_id, max_depth) -> list[str]
```
**Статус:** Реализован. BFS от anchor_id через outgoing PRECEDES relations.

### 1.5 WorldModel.get_temporal_chain(direction)
```python
# core/CORE/narrative_engine/world_model.py:350
def get_temporal_chain(self, direction="BACKWARD") -> dict
```
**Статус:** Реализован. Строит цепочку из epoch-узлов. FORWARD chain: 12 узлов, 11 PRECEDES relations.

---

## 2. PRESENT → ARKAIM

### Факт 1: `temporal_today` НЕ в графе
```python
engine._graph.get_node("temporal_today")  # → None
```

### Факт 2: Нет relations от/к temporal_today
```python
engine._graph.get_outgoing("temporal_today")  # → []
engine._graph.get_incoming("temporal_today")  # → []
```

### Факт 3: BFS от temporal_today к arkaim_era возвращает None
```python
engine._graph.bfs_path("temporal_today", "temporal_arkaim_era")  # → None
```

### Вывод
**Цепочка Present → Arkaim НЕ существует в данных.**
Метод `TemporalNode.present_anchor()` определён, но не вызывается.
Класс `PresentAnchor` существует, но не добавляет узлы в граф.
Нет ни одного relation, связывающего "настоящее" с "Аркаимом".

---

## 3. ARKAIM → FUTURE

### Как M8 получает arkaim_era
```python
# M8 FutureExtrapolator
extrapolator = FutureExtrapolator(wm)
result = extrapolator.extrapolate(anchor_id="arkaim_era")
```

Внутри `_build_forward_chain`:
```python
if not anchor_id.startswith("temporal_"):
    anchor_id = f"temporal_{anchor_id}"
# → "temporal_arkaim_era"
```

### Факт: temporal_arkaim_era В графе
```python
engine._graph.get_node("temporal_arkaim_era")  # → TemporalNode ✓
```

### Факт: Из temporal_arkaim_era есть outgoing PRECEDES
```python
# Из проверки:
# temporal_arkaim_era --[PRECEDES]--> temporal_будущее_время
```

### Вывод
**M8 работает корректно, но использует отдельный anchor (`arkaim_era`),**
**не связанный с "present" через temporal graph.**

---

## 4. FULL CHAIN

### M0 Architecture Vision (docs/M0_ARCHITECTURE_AUDIT.md:1225-1242)
```
TODAY (current)
  ↓ archaeological_layers
HISTORY (recorded history)
  ↓ civilizational transitions
ARKAIM ERA (primary focus)
  ↓ pre-history
PRE-ARKAIM (origins)

AND reverse:
ARKAIM
  ↓ cultural diffusion
HISTORY
  ↓ modern manifestations
TODAY
  ↓ extrapolation
FUTURE
```

### Реальное состояние
```
[temporal_today] ← НЕ В ГРАФЕ ← absent

[temporal_pre_arkaim] --PRECEDES--> [temporal_..._..._] --PRECEDES--> ...
    → [temporal_arkaim_era] (anchor) → [temporal_...future...]
```

**Цепочка Present → Arkaim отсутствует.**
**Цепочка Arkaim → Future существует (через M8).**

### Можно ли получить единую цепочку?
**НЕТ.**因为没有:
1. `temporal_today` не в графе
2. Нет relations между "present" и "arkaim"
3. `PresentAnchor` не добавляет узлы в граф автоматически

---

## 5. GAPS

| Gap | Severity | Описание |
|-----|----------|----------|
| G1 | P1 | `temporal_today` не создан в графе |
| G2 | P1 | Нет relation `PRESENT → ARKAIM` в графе |
| G3 | P2 | `PresentAnchor` и `ArkaimAnchor` — метаданные, не узлы графа |
| G4 | P2 | Два anchor-узла для Аркаима: `temporal_arkaim_anchor` и `temporal_arkaim_era` |
| G5 | P3 | `HistoricalLayerStack`, `EpochTransitionModel`, `TemporalChainBuilder` — НЕ СОЗДАНЫ (упомянуты в M0 как "WHAT MUST BE ADDED") |

---

## 6. ARCHITECTURAL RISK

### M8 является изолированной веткой

```
M8 FutureExtrapolator
    │
    └─► anchor_id="arkaim_era"  (принимается как dado, не из графа)
          │
          └─► _trace_forward("temporal_arkaim_era")
                → FORWARD chain: arkaim_era → future_nodes
```

**Проблема:** M8 использует `arkaim_era` как hardcoded anchor, не проверяя связь с "present".

### Что это значит
1. **Past → Present реконструкция невозможна** — нет пути от temporal_today к arkaim_era
2. **Future extrapolation работает, но изолирована** — M8 строит цепочку от arkaim_era, но не может ответить "как это связано с настоящим?"
3. **Нет единой temporal pipeline** — BACKWARD (M5/M6) и FORWARD (M8) работают независимо

---

## 7. RECOMMENDATION

### AUDIT RESULT: PARTIAL CHAIN — EXISTING COMPONENTS BUT NO INTEGRATED PATH

**Обоснование:**

1. **Компоненты существуют:**
   - `TemporalNode.present_anchor()` — factory method определён
   - `PresentAnchor` — класс определён
   - `ArkaimAnchor` — класс определён
   - `TemporalReconstructionEngine._trace_forward()` — реализован
   - `TemporalChain` — поддерживает FORWARD направление

2. **Но связь отсутствует:**
   - `temporal_today` НЕ добавлен в граф
   - Нет relations между "present" и "arkaim"
   - M8 принимает anchor_id как dado, не интегрирован с PresentAnchor

3. **Что нужно для полной цепочки (без реализации):**
   - Добавить `temporal_today` в граф при загрузке WorldModel
   - Добавить relation `temporal_today → temporal_arkaim_era` (тип: ArchaeologicalConnection)
   - Или: интегрировать PresentAnchor в TemporalReconstructionEngine
   - M8 должен проверять существование связи Present→Arkaim перед экстраполяцией

4. **Provenance risk:**
   - Если добавить relation `today → arkaim`, нужно маркировать её как `RECONSTRUCTION` или `HYPOTHESIS`
   - Никогда не использовать `AUTHOR_CANON` для связи "настоящее ↔ аркаим" (это археологическая интерпретация, не канон книги)

---

## Appendices

### A. Graph Stats (Current)
```
Nodes: 13
  - temporal_today: NOT IN GRAPH
  - temporal_arkaim_anchor: IN GRAPH (from ArkaimAnchor)
  - temporal_arkaim_era: IN GRAPH (from WorldModel epoch)
  - 11 other epoch nodes: IN GRAPH
Relations: 11 (all PRECEDES between epochs)
  - No relation involves temporal_today
```

### B. M8 Anchor Resolution
```python
# user passes: anchor_id="arkaim_era"
# M8 normalizes: "temporal_arkaim_era"
# M8 finds: engine._graph.get_node("temporal_arkaim_era") → TemporalNode ✓
# M8 traces forward: _trace_forward("temporal_arkaim_era") → [12 nodes]
# Result: SUCCESS, but no connection to "present"
```

### C. What Would Make Full Chain
```python
# Step 1: Add temporal_today to graph
engine.add_node(TemporalNode.present_anchor())

# Step 2: Add relation from today to arkaim
engine.add_relation(TemporalRelation.precedes(
    source_id="temporal_today",
    target_id="temporal_arkaim_era",
    strength=0.7,  # archaeological confidence
))

# Step 3: M8 can now trace from present
# _trace_forward("temporal_today") → [today, arkaim, future_nodes]
```

### D. Provenance Rules for Full Chain
```python
# Relation "today → arkaim" must be:
provenance = [
    ProvenanceTag(
        source_level=SourceLevel.SCIENTIFIC,
        category=ProvenanceCategory.RECONSTRUCTION,  # NOT AUTHOR_CANON
        confidence=0.7,
        notes="archaeological reconstruction — not book canon",
    )
]
```
