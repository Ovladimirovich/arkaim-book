# Temporal Chain Architecture Audit
## PRESENT → ARKAIM → FUTURE — Фактическое состояние

---

## 1. VERIFIED EXISTING

### 1.1 Компоненты, которые СУЩЕСТВУЮТ

| Компонент | Файл | Статус | Примечание |
|-----------|------|--------|------------|
| `TemporalNode.present_anchor()` | `temporal/node.py:134` | ✅ МЕТОД ЕСТЬ | НЕ вызывается нигде |
| `PresentAnchor` (dataclass) | `temporal/present_anchor.py` | ✅ ЕСТЬ | Метаданные, не узел графа |
| `ArkaimAnchor` (dataclass) | `temporal/arkaim_anchor.py` | ✅ ЕСТЬ | Создаёт `temporal_arkaim_anchor` |
| `TemporalReconstructionEngine._trace_forward()` | `temporal/reconstruction_engine.py:527` | ✅ РАБОТАЕТ | BFS по PRECEDES |
| `TemporalReconstructionEngine._trace_backward()` | `temporal/reconstruction_engine.py:493` | ✅ РАБОТАЕТ | BFS по incoming |
| `WorldModel.get_temporal_chain('FORWARD')` | `world_model.py:350` | ✅ РАБОТАЕТ | 12 узлов, 11 relations |
| `WorldModel.get_temporal_chain('BACKWARD')` | `world_model.py:350` | ✅ РАБОТАЕТ | 12 узлов, 11 relations |
| `ProvenanceCategory.FUTURE_EXTRAPOLATION` | `source_levels.py:61` | ✅ ОПРЕДЕЛЁН | color=magenta |
| `CompatibilityChecker` | `compatibility_checker.py` | ✅ РАБОТАЕТ | 6 осей |
| `FutureExtrapolator` (M8) | `temporal/future_extrapolator.py` | ✅ РЕАЛИЗОВАН | M8 implementation |

### 1.2 Типы отношений, которые МОГУТ связать Present → Arkaim

```python
# Все типы TemporalRelationType (relation.py:17-57):
BEFORE          # A происходит до B
AFTER           # A происходит после B
OVERLAPS        # A и B пересекаются
CONTAINS        # A содержит B
CONTAINED_BY    # A содержится в B
CONTEMPORARY_WITH  # A и B одновременно
PRECEDES        # A предшествует B (строгий порядок)
FOLLOWS         # A следует за B
DEVELOPS_FROM   # A развивается из B ← ПОТЕНЦИАЛЬНЫЙ КАНИДАТ
TRANSFORMS_INTO # A трансформируется в B
COEXISTS_WITH   # A и B сосуществуют
UNKNOWN         # Связь не определена
```

**НИ ОДНОГО типа «ArchaeologicalConnection», «DiscoveredFrom», «LinksToPresent» и т.п. НЕТ.**

---

## 2. PRESENT → ARKAIM

### Факт 1: `temporal_today` НЕ в графе
```python
engine._graph.get_node("temporal_today")  # → None
```
Метод `TemporalNode.present_anchor()` определён (node.py:134), но **нигде не вызывается**.

### Факт 2: Нет relations от/к temporal_today
```python
engine._graph.get_outgoing("temporal_today")  # → []
engine._graph.get_incoming("temporal_today")  # → []
```

### Факт 3: BFS от temporal_today к arkaim_era = None
```python
engine._graph.bfs_path("temporal_today", "temporal_arkaim_era")  # → None
```

### Вывод
**Цепочка Present → Arkaim НЕ существует.**

Отсутствует:
- Узел `temporal_today` в графе
- Relation между "present" и "arkaim_era"
- Механизм, который бы автоматом связывал PresentAnchor с temporal graph

---

## 3. ARKAIM → FUTURE

### Как M8 получает anchor
```python
# M8 FutureExtrapolator
extrapolator.extrapolate(anchor_id="arkaim_era")
# → нормализует в "temporal_arkaim_era"
# → находит в графе: ✓
# → строит FORWARD chain: ✓
```

### Факт: temporal_arkaim_era В графе
```python
engine._graph.get_node("temporal_arkaim_era")  # → TemporalNode ✓
```

### Факт: Из temporal_arkaim_era есть outgoing PRECEDES
```
temporal_arkaim_era --[PRECEDES]--> temporal_будущее_время
```

### Вывод
**M8 работает корректно, но использует `arkaim_era` как standalone anchor**,
не связанный с "present" через temporal graph.

---

## 4. ДВОЙНОЙ ARKAIM ANCHOR

### Факт: Два узла с is_anchor=True
```
temporal_arkaim_anchor  (из ArkaimAnchor)  — PROVENANCE=[AUTHOR_CANON, EXTERNAL_SOURCE]
temporal_arkaim_era     (из WorldModel)     — PROVENANCE=[] (пусто!)
```

### Различия
| Поле | temporal_arkaim_anchor | temporal_arkaim_era |
|------|----------------------|---------------------|
| Источник | ArkaimAnchor.from_existing_data() | WorldModel.get_temporal_node() |
| Provenance | [AUTHOR_CANON, EXTERNAL_SOURCE] | [] (пусто) |
| Confidence | 0.7 (archaeological support) | 0.8 (default) |
| В графе | ✅ Есть | ✅ Есть |
| Relations | ❌ Нет (орфан) | ✅ Есть (in+out PRECEDES) |
| Используется M8 | ❌ Нет | ✅ Да |

### Проблема
- **Мировая модель (WorldModel)** даёт узел без provenance
- **ArkaimAnchor** даёт узел с provenance, но без relations
- M8 работает с узлом без provenance
- Нет единого канонического anchor-узла

---

## 5. FULL CHAIN

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

[temporal_pre_arkaim] --PRECEDES--> ... --> [temporal_arkaim_era] (anchor)
    → [temporal_будущее_время]  ← M8 работает здесь
```

**Цепочка Present → Arkaim отсутствует.**
**Цепочка Arkaim → Future существует (через M8).**

---

## 6. GAPS

| Gap | Severity | Описание | Статус |
|-----|----------|----------|--------|
| G1 | P0 | `temporal_today` не создан в графе | Метод есть, вызовов нет |
| G2 | P0 | Нет relation между "present" и "arkaim" | Отсутствует тип + данные |
| G3 | P1 | Двойной anchor: `arkaim_anchor` vs `arkaim_era` | Оба в графе, разные provenance |
| G4 | P1 | `arkaim_era` epoch имеет пустой provenance | `source_level=SYSTEM_INTERPRETATION` |
| G5 | P2 | M8 не маркирует результаты `FUTURE_EXTRAPOLATION` | Категория есть, но не используется |
| G6 | P3 | `HistoricalLayerStack`, `EpochTransitionModel` — НЕ CREATED | Упомянуты в M0 как "WHAT MUST BE ADDED" |

---

## 7. ARCHITECTURAL RISK

### M8 является изолированной веткой

```
        M8 FutureExtrapolator
              │
              └─► anchor_id="arkaim_era"  (принимается как dado)
                    │
                    └─► _trace_forward("temporal_arkaim_era")
                          → FORWARD chain: 12 узлов
```

**Проблема:** M8 использует `arkaim_era` как hardcoded anchor, не проверяя связь с "present".

### Что это значит
1. **Past → Present реконструкция невозможна** — нет пути от temporal_today к arkaim_era
2. **Future extrapolation работает, но изолирована** — M8 строит цепочку от arkaim_era, но не может ответить "как это связано с настоящим?"
3. **Нет единой temporal pipeline** — BACKWARD (M5/M6) и FORWARD (M8) работают независимо
4. **Двойной anchor создаёт путаницу** — какой узел является каноническим?

---

## 8. КЛЮЧЕВОЕ ОТКРЫТИЕ

### `FUTURE_EXTRAPOLATION` provenance category УЖЕ СУЩЕСТВУЕТ

```python
# source_levels.py:61
FUTURE_EXTRAPOLATION = "FUTURE_EXTRAPOLATION"
"""Проекция в будущее."""

# source_levels.py:110
ProvenanceCategory.FUTURE_EXTRAPOLATION: SourceLevel.USER_HYPOTHESIS

# source_levels.py:145-149
SOURCE_CATEGORY_LABELS[FUTURE_EXTRAPOLATION] = {
    "label": "Будущее extrapolation",
    "color": "magenta",
    "description": "Проекция от канона в будущее",
}
```

**Система была спроектирована с учётом future extrapolation!**
Но M8 не использует эту категорию — результаты не маркируются.

---

## 9. RECOMMENDATION

### AUDIT RESULT: PARTIAL CHAIN — EXISTING COMPONENTS BUT NO INTEGRATED PATH

**Обоснование:**

1. **Компоненты есть, но связи отсутствуют:**
   - `TemporalNode.present_anchor()` — factory method определён, но нигде не вызывается
   - `PresentAnchor` — класс определён, но это мета-данные, не узел графа
   - `ArkaimAnchor` — класс определён, создаёт орфанный узел с provenance
   - `ProvenanceCategory.FUTURE_EXTRAPOLATION` — определён, но M8 не использует

2. **Архитектурный разрыв:**
   - BACKWARD chain (M5/M6): работает, но начинается не с "present"
   - FORWARD chain (M8): работает, но начинается с "arkaim_era" без связи к "present"
   - Единая ось `PRESENT → ARKAIM → FUTURE` НЕ собрана

3. **Проблема двойного anchor:**
   - `temporal_arkaim_anchor` (с provenance, без relations)
   - `temporal_arkaim_era` (без provenance, с relations)
   - M8 использует второй, но он не имеет provenance-меток

4. **Риск M9:**
   - Если начать M9 (ExpansionLayer temporal consumption), он будет потреблять неполную структуру
   - ExpansionLayer может считать `Arkaim → Future` полноценной цепочкой
   - Это создаст ложное ощущение завершённости temporal модели

### Что нужно решить ДО M9 (без реализации):

**Вопрос 1: Что такое TODAY?**
- Реальный temporal node в графе?
- PresentAnchor как метаданные?
- Отдельная точка отсчёта?

**Вопрос 2: Как Present связан с Arkaim?**
- Какой тип relation использовать?
  - `DEVELOPS_FROM` (современность развилась из аркаимской эпохи)?
  - `CONTAINS` (современность содержит аркаимское наследие)?
  - Нужен ли новый тип relation?
- Какие данные обосновывают эту связь?
  - ARCHAEOLOGY.json?
  - WorldModel epoch data?
  - PresentAnchor metadata?

**Вопрос 3: Какой provenance у связи Present→Arkaim?**
- НЕ `AUTHOR_CANON` (это археологическая интерпретация, не канон книги)
- `RECONSTRUCTION`? (археологические данные + канон)
- `HYPOTHESIS`? (системная гипотеза)
- `FUTURE_EXTRAPOLATION`? (нет, это для будущего, не для прошлого)

**Вопрос 4: Что делать с двойным anchor?**
- Объединить `temporal_arkaim_anchor` и `temporal_arkaim_era`?
- Оставить metadata anchor отдельно?
- Сделать один источником истины?

---

## 10. WHAT SHOULD NOT BE DONE

❌ **НЕ** добавлять relation `temporal_today → temporal_arkaim_era` без решения вопросов 1-4
❌ **НЕ** использовать `AUTHOR_CANON` для связи Present→Arkaim
❌ **НЕ** начинать M9 до решения архитектурных вопросов
❌ **НЕ** исправлять двойной anchor без обсуждения
❌ **НЕ** создавать новый TemporalEngine / TemporalService

## 11. WHAT SHOULD BE DONE

✅ Архитектурное решение по вопросам 1-4
✅ После решения — единая temporal pipeline:
   ```
   PRESENT (anchor)
      ↓
   BACKWARD reconstruction (M5/M6)
      ↓
   ARKAIM (single canonical anchor)
      ↓
   FORWARD extrapolation (M8)
      ↓
   FUTURE (с FUTURE_EXTRAPOLATION provenance)
   ```

---

## Appendices

### A. Graph Stats (Current)
```
Nodes: 13
  - temporal_today: NOT IN GRAPH
  - temporal_arkaim_anchor: IN GRAPH (orphan, no relations)
  - temporal_arkaim_era: IN GRAPH (used by M8, no provenance)
  - 11 epoch nodes: IN GRAPH (connected via PRECEDES)
Relations: 11 (all PRECEDES between epochs)
  - No relation involves temporal_today
  - No relation connects arkaim_anchor to arkaim_era
```

### B. M8 Anchor Resolution
```python
# User passes: anchor_id="arkaim_era"
# M8 normalizes: "temporal_arkaim_era"
# M8 finds: engine._graph.get_node("temporal_arkaim_era") → TemporalNode ✓
# M8 traces forward: _trace_forward("temporal_arkaim_era") → [12 nodes]
# Result: SUCCESS, but no connection to "present"
# M8 does NOT use FUTURE_EXTRAPOLATION provenance ❌
```

### C. What Full Chain Would Require
```python
# Step 1: Add temporal_today to graph
engine.add_node(TemporalNode.present_anchor())

# Step 2: Add relation from today to arkaim
# (Type and provenance TBD after architectural decision)
engine.add_relation(TemporalRelation.some_new_type(
    source_id="temporal_today",
    target_id="temporal_arkaim_era",
    provenance=[...],  # TBD
))

# Step 3: M8 should verify present→arkaim connection
# Before extrapolating future from arkaim
```

### D. M0 vs Reality Comparison
```
M0 Vision:                    Reality:
  TODAY ──→ ARKAIM ──→ FUTURE
     │         │           │
     │         │           │
   present   anchor     M8 works
             (double)
```
