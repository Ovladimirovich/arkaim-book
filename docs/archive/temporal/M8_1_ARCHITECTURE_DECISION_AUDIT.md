# M8.1 — ARCHITECTURE DECISION AUDIT
## PRESENT → ARKAIM → FUTURE: Архитектурный анализ без реализации

---

## VERIFIED FACTS

### Факт 1: `TemporalNode.present_anchor()` существует, но не вызывается
```python
# node.py:134-148
@staticmethod
def present_anchor() -> "TemporalNode":
    return TemporalNode(
        id="temporal_today",
        label="Современность",
        precision=TemporalPrecision.EXACT,
        bounds=TemporalBounds(start="2025 CE", end="2025 CE"),
        provenance=[ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
            notes="present reference point",
        )],
        confidence=1.0,
    )
```
**Проблема:** provenance установлен как `AUTHOR_CANON`, но современность — это не канон книги, это факт existence reader. Это ошибочная provenance.

### Факт 2: `temporal_today` НЕ в графе
```python
engine._graph.get_node("temporal_today")  # → None
```
Метод определён, но `TemporalReconstructionEngine.from_world_model()` его не вызывает.

### Факт 3: Два anchor-узла для Аркаима
```
temporal_arkaim_anchor  (из ArkaimAnchor, provenance=[AUTHOR_CANON, EXTERNAL_SOURCE], ORPHAN)
temporal_arkaim_era     (из WorldModel,      provenance=[],                   CONNECTED)
```

### Факт 4: `ProvenanceCategory.FUTURE_EXTRAPOLATION` существует, но M8 не использует
```python
# source_levels.py:61
FUTURE_EXTRAPOLATION = "FUTURE_EXTRAPOLATION"
# source_levels.py:110
ProvenanceCategory.FUTURE_EXTRAPOLATION: SourceLevel.USER_HYPOTHESIS
# source_levels.py:145-149
SOURCE_CATEGORY_LABELS[FUTURE_EXTRAPOLATION] = {
    "label": "Будущее extrapolation",
    "color": "magenta",
    "description": "Проекция от канона в будущее",
}
```

### Факт 5: Нет evidence для связи Present → Arkaim в KNOWLEDGE/
```bash
# grep "открыт|раскопк|археолог|198" core/KNOWLEDGE/ARCHAEOLOGY.json
# Результат: 0 matches (только численные значения 2000-2500 человек)
```
**ARCHAEOLOGY.json НЕ содержит информации об открытии Аркаима в современности.**

### Факт 6: Существующие relation types НЕ покрывают Present→Arkaim
```python
# Все типы TemporalRelationType:
BEFORE / AFTER           #纯 temporal order
OVERLAPS / CONTAINS      # spatial/temporal containment
CONTEMPORARY_WITH        # simultaneity
PRECEDES / FOLLOWS       # strict order
DEVELOPS_FROM / TRANSFORMS_INTO  # qualitative development
COEXISTS_WITH / UNKNOWN
```
**Ни один тип не означает «современность обнаруживает древнюю эпоху через археологию».**

### Факт 7: `WorldModel.get_temporal_node()` всегда ставит `is_anchor=True` только для `arkaim_era`
```python
# world_model.py:347
"is_anchor": epoch_id == "arkaim_era",
```
`ArkaimAnchor.node` создаёт ДРУГОЙ узел с `is_anchor=True`, который НЕ учитывается при создании chain.

---

## DECISION 1 — TODAY

### Варианты

| Вариант | Описание | Плюсы | Минусы |
|---------|----------|-------|--------|
| **A. Полноценный TemporalNode** | `temporal_today` как узел графа с EXACT precision | Естественная часть графа, работает с BFS/PATH finders | Требует добавления в graph, risk: provenance AUTHOR_CANON — некорректно для «настоящего» |
| **B. PresentAnchor как metadata** | PresentAnchor остаётся метаданными, не узел графа | Нет изменений в графе, соответствует текущей архитектуре | Не даёт temporal navigation, M8 не может начать от "present" |
| **C. Комбинация** | PresentAnchor (metadata) + TemporalNode (graph) | Лучшее из двух миров | Больше сложности, нужен механизм синхронизации |

### Анализ

**A (TemporalNode)** — технически возможен, но:
- `present_anchor()` ставит `AUTHOR_CANON` для «современности» — это ошибочно. Современность reader'а не является каноном книги.
- Нужен новый provenance type или коррекция default provenance для present node.
- `TemporalPrecision.EXACT` для "2025 CE" — корректно (точное время известно).

**B (PresentAnchor metadata)** —现状:
- PresentAnchor уже существует, но `temporal_nodes=[]` (пусто).
- Не даёт ability для reconstruction path.
- Соответствует M0 vision section 17.2: "PresentAnchor — связь современного объекта с историческими слоями".

**C (Комбинация)** — идеал, но:
- Нужен механизм: PresentAnchor.temporal_nodes ссылается на TemporalNode.id в графе.
- PresentAnchor.for_entity() уже принимает `provenance_tags` — можно передать correct provenance.

### Рекомендация (анализ, не реализация)

**Вариант C (комбинация) — архитектурно наиболее корректный.**

Обоснование:
1. `PresentAnchor` — metadata layer (связь entity ↔ temporal nodes)
2. `TemporalNode.present_anchor()` — graph node (точка отсчёта для BFS)
3. PresentAnchor.temporal_nodes должен ссылаться на TemporalNode.id
4. Provenance для present node должен быть НЕ AUTHOR_CANON — скорее HYPOTHESIS или NEW category

**НО:** требуется решение по provenance present node (см. Decision 5).

---

## DECISION 2 — PRESENT → ARKAIM

### Цель: A (temporal navigation / reconstruction path)
НЕ утверждение исторической причинности.

### Что позволяет существующая архитектура

**1. TemporalGraph.bfs_path() и all_paths()**
```python
# graph.py:92-157
def bfs_path(self, source_id, target_id, max_depth=10) -> Optional[list[str]]
def all_paths(self, source_id, target_id, max_depth=10) -> list[list[str]]
```
Эти методы работают с ЛЮБЫМИ двумя узлами в графе. Если добавить `temporal_today` и relation → path будет найден автоматически.

**2. TemporalReconstructionEngine._trace_backward()**
```python
# reconstruction_engine.py:493-525
# Идёт от anchor назад по incoming relations (PRECEDES, BEFORE, FOLLOWS)
```
Если relation идёт от today → arkaim, то `_trace_backward("temporal_today")` найдёт arkaim_era.

**3. Evidence для связи Present → Arkaim**

| Источник | Что содержит | Достаточно? |
|----------|-------------|-------------|
| ARCHAEOLOGY.json | Аркаим — реальное городище, ~4000-3700 до н.э. | ✅ Да |
| ARCHAEOLOGY.json | "Аркаим опровергает представление о примитивных племенах" | ✅ Да |
| ARCHAEOLOGY.json | "Археологическое открытие — подтверждение древней цивилизации" | ⚠️ ЧАСТИЧНО (нет даты открытия) |
| KNOWLEDGE/*.json | Гугл-поиск: 0 matches на "открыт Аркаим 198" | ❌ НЕТ |
| WorldModel epochs | arkaim_era: order=5, source_level=SYSTEM_INTERPRETATION | ⚠️ ЧАСТИЧНО |

**Не хватает:**
- Дата/год археологического открытия Аркаима (факт: 1980-е, Ю.Б. Орехов)
- Ссылка на конкретный archaeological source в KNOWLEDGE
- PresentAnchor.temporal_nodes заполнен? Нет ([].)

### Вывод

**Существующие данные ПОЗВОЛЯЮТ построить reconstruction path**, но:
- Нужно добавить evidence (дата открытия) в KNOWLEDGE или использовать существующий ARCHAEOLOGY.json как источник
- PresentAnchor должен быть наполнен temporal_nodes
- Relation должна быть создана с корректным provenance

**Риск:** если relation будет создана без evidence, система может начать воспринимать её как established fact.

---

## DECISION 3 — RELATION TYPE

### Анализ кандидатов

| Тип | Смысл | Утверждение | Подходит? | Provenance risk |
|-----|-------|-------------|-----------|-----------------|
| **PRECEDES** | A предшествует B (строгий порядок) | "Современность ПЕРЕД Аркаимом" — ЛОЖЬ (temporally incorrect) | ❌ НЕТ | Превращает anachronism в fact |
| **FOLLOWS** | A следует за B | "Современность ПОСЛЕ Аркаима" — ВЕРНО temporal, но слишком weak | ⚠️ ЧАСТИЧНО | Низкий, но не несёт semantic meaning |
| **DEVELOPS_FROM** | A развивается из B | "Современность развилась из Аркаима" — ИСТОРИЧЕСКОЕ УТВЕРЖДЕНИЕ | ❌ НЕТ | Превращает гипотезу в fact |
| **CONTAINS** | A содержит B | "Современность содержит Аркаим" — метафорически, не буквально | ⚠️ ЧАСТИЧНО | Риск метафорической интерпретации как факт |
| **CONTEMPORARY_WITH** | Одновременно | "Современность и Аркаим существуют одновременно" — ЛОЖЬ | ❌ НЕТ | Anachronism |
| **UNKNOWN** | Связь не определена | Честно, но бесполезно | ⚠️ Для gap, не для path | Низкий, но не даёт navigation |

### Вывод

**НИ ОДИН существующий relation type НЕ подходит для Present → Arkaim.**

Причина: все существующие типы описывают ЧИСТО ВРЕМЕННЫЕ отношения (порядок, одновременность, развитие). Связь Present → Arkaim — это НЕ временное отношение. Это **epistemological relation**: «современность ДОСТУПА к аркаимской эпохе через археологию».

### Необходимое решение

Либо:
1. **Создать новый TemporalRelationType** (например, `ARCHAEOLOGICAL_CONNECTION` или `DISCOVERED_FROM`) — НОВАЯ абстракция, требует изменения relation.py
2. **Использовать существующий `UNKNOWN`** с описанием в `relation.description` — честный, но не даёт navigation semantics
3. **Использовать `FOLLOWS`** (temporally correct: modern era follows arkaim era) + metadata в description — workable compromise

**Рекомендация (анализ):** Вариант 3 (`FOLLOWS` с detailed description) — наименее инвазивный. `FOLLOWS` temporally correct, а semantic meaning передаётся через `description` и `provenance`.

---

## DECISION 4 — ДВА ARKAIM ANCHOR

### Анализ

| Атрибут | `temporal_arkaim_anchor` | `temporal_arkaim_era` |
|---------|-------------------------|----------------------|
| Источник | `ArkaimAnchor.from_existing_data()` | `WorldModel.get_temporal_node("arkaim_era")` |
| ID | `temporal_arkaim_anchor` | `temporal_arkaim_era` |
| Label | "Аркаим — temporal anchor" | "Аркаимская эпоха" |
| Provenance | [AUTHOR_CANON, EXTERNAL_SOURCE] | [] (пусто) |
| Confidence | 0.7 | 0.8 |
| Relations | 0 (орфан) | 2 (in+out PRECEDES) |
| is_anchor | True | True |
| Используется M8 | ❌ Нет | ✅ Да |
| Цель | Metadata anchor (источник provenance) | Data anchor (участник chain) |

### Зачем существует каждый

**`temporal_arkaim_anchor`:**
- Создан `ArkaimAnchor.from_existing_data()` в `reconstruction_engine.py:589`
- Содержит rich provenance: AUTHOR_CANON (from book) + EXTERNAL_SOURCE (from ARCHAEOLOGY.json)
- Это metadata-представление: «Аркаим как temporal anchor»
- Но он НЕ имеет relations — орфан в графе

**`temporal_arkaim_era`:**
- Создан `WorldModel.get_temporal_node("arkaim_era")`
- Пустой provenance (epoch.provenance = [])
- Имеет relations (в chain)
- Это data-представление: «Аркаим как epoch в temporal chain»
- Используется M8

### Проблема

Два узла с is_anchor=True, но разными свойствами. M8 использует второй (без provenance), первый орфан.

### Рекомендация (анализ)

**Canonical temporal node = `temporal_arkaim_era`** (уже в chain, используется M8).

**`temporal_arkaim_anchor` должен стать metadata-ссылкой**, а не отдельным узлом:
- ArkaimAnchor.provenance должен применяться к `temporal_arkaim_era` при загрузке
- `temporal_arkaim_anchor` УДАЛЯТЬ из графа (или не добавлять)
- M8 должен ссылаться на `temporal_arkaim_era` (не менять)

**Или альтернативно:**
- Оставить оба, но `temporal_arkaim_anchor` — metadata reference, не graph node
- Добавить relation между ними: `temporal_arkaim_anchor --IDENTICAL_TO--> temporal_arkaim_era`
- Но это новая абстракция — risk

**Наименее инвазивный вариант:** enrich `temporal_arkaim_era` provenance из ArkaimAnchor при загрузке, убрать дублирующий узел из графа.

---

## DECISION 5 — PROVENANCE

### 5.1 PRESENT anchor

| Attribute | Current (present_anchor()) | Recommended |
|-----------|---------------------------|-------------|
| category | AUTHOR_CANON | **HYPOTHESIS** или новый `PRESENT_REFERENCE` |
| source_level | CANON | **SYSTEM_INTERPRETATION** или **CANON** (если present = reader's reality) |
| confidence | 1.0 | 1.0 (correct — present IS exact) |
| notes | "present reference point" | "reader's current temporal reference — not book canon" |

**Ключевой принцип:** `temporal_today` — это точка отсчёта reader'а, НЕ утверждение о мире книги. Его provenance НЕ может быть AUTHOR_CANON.

**Рекомендация:** Создать новый category `PRESENT_REFERENCE` ИЛИ использовать `HYPOTHESIS` с source_level=CANON (парадоксально, но present IS a canonical reference point for the reader).

**ИЛИ:** Использовать существующий `EXTERNAL_SOURCE` (present = real world data).

### 5.2 PRESENT → ARKAIM reconstruction

| Attribute | Recommended |
|-----------|-------------|
| category | **RECONSTRUCTION** |
| source_level | **HISTORICAL** |
| confidence | 0.6-0.7 (archaeological evidence is strong but not exact) |
| notes | "Archaeological discovery connects modern era to Arkaim epoch" |
| evidence | ARCHAEOLOGY.json (Arkaim site facts) |

**Принцип:** RECONSTRUCTION ≠ HISTORICAL_FACT. Relation exists as reconstruction, not established fact.

### 5.3 ARKAIM canonical node

| Attribute | Current | Recommended |
|-----------|---------|-------------|
| category | [] (empty) | **RECONSTRUCTION** (from ARCHAEOLOGY.json) + **AUTHOR_CANON** (from book) |
| source_level | SYSTEM_INTERPRETATION | HISTORICAL + CANON |
| confidence | 0.8 | 0.85 (combined) |

**Принцип:** arkaim_era epoch has EMPTY provenance. This is a bug. It should inherit provenance from both book canon AND archaeological evidence.

### 5.4 ARKAIM → FUTURE extrapolation

| Attribute | Recommended |
|-----------|-------------|
| category | **FUTURE_EXTRAPOLATION** |
| source_level | **USER_HYPOTHESIS** |
| confidence | varies by scenario (0.3-0.7) |
| notes | "Projection from Arkaim canon into future — not historical fact" |

**Принцип:** `ProvenanceCategory.FUTURE_EXTRAPOLATION` УЖЕ ОПРЕДЕЛЁН. M8 должен его использовать.

### 5.5 Future scenario

Каждый сценарий от M8:
| Attribute | Recommended |
|-----------|-------------|
| category | **FUTURE_EXTRAPOLATION** |
| source_level | **USER_HYPOTHESIS** |
| compatibility_score | из CompatibilityChecker (0.0-1.0) |
| risk_level | из CompatibilityChecker (low/medium/high/rejected) |

**Принцип:** Сценарий ≠ факт. Даже high-compatibility scenario remains FUTURE_EXTRAPOLATION.

---

## DECISION 6 — FULL PIPELINE

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PRESENT                                  │
│  temporal_today (TemporalNode)                               │
│  provenance: HYPOTHESIS / PRESENT_REFERENCE                  │
│  precision: EXACT                                             │
│  confidence: 1.0                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ relation: FOLLOWS (or new type)
                   │ provenance: RECONSTRUCTION
                   │ evidence: ARCHAEOLOGY.json
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    ARKAIM ERA                                 │
│  temporal_arkaim_era (canonical node)                        │
│  provenance: AUTHOR_CANON + RECONSTRUCTION (combined)        │
│  precision: RELATIVE                                          │
│  confidence: 0.85                                             │
│  is_anchor: True                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   │ BACKWARD (M5/M6): trace_backward()
                   │ → pre_arkaim → ... → earlier epochs
                   │
                   │ FORWARD (M8): trace_forward()
                   │ → future epochs → future scenarios
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      FUTURE                                  │
│  FutureExtrapolator scenarios                                │
│  provenance: FUTURE_EXTRAPOLATION                            │
│  each scenario: { compatibility_score, risk_level }          │
│  NOT histotical fact                                         │
└─────────────────────────────────────────────────────────────┘
```

### Provenance Invariants (уже существуют)

```python
# source_levels.py — verified
HYPOTHESIS with confidence=1.0 → stays HYPOTHESIS
EXTERNAL_SOURCE with confidence=1.0 → stays EXTERNAL_SOURCE
RECONSTRUCTION ≠ HISTORICAL_FACT
FUTURE_EXTRAPOLATION ≠ HISTORICAL_FACT
```

### What needs to be preserved

1. **AUTHOR_CANON ≠ HISTORICAL_FACT** — book canon is about the narrative, not archaeology
2. **EXTERNAL_SOURCE ≠ AUTHOR_CANON** — archaeological data doesn't become book canon
3. **RECONSTRUCTION ≠ HISTORICAL_FACT** — reconstruction is system interpretation
4. **HYPOTHESIS ≠ HISTORICAL_FACT** — hypothesis stays hypothesis even at confidence=1.0
5. **FUTURE_EXTRAPOLATION ≠ HISTORICAL_FACT** — future scenarios are projections, not facts

---

## TARGET ARCHITECTURE

### Graph Structure (Target)

```
temporal_today ──[FOLLOWS, RECONSTRUCTION]──► temporal_arkaim_era
                                                    │
                                                    ├─[PRECEDES]──► temporal_будущее_время
                                                    │
                                                   (M8 forward chain)
                                                    │
                                                    ├─[PRECEDES]──► temporal_..._earlier (BACKWARD from today)
```

### Component Responsibilities

| Компонент | Ответственность | Изменений |
|-----------|----------------|-----------|
| `TemporalNode.present_anchor()` | Create present node | Fix provenance (NOT AUTHOR_CANON) |
| `TemporalReconstructionEngine.from_world_model()` | Load graph | Add present node + relation |
| `ArkaimAnchor` | Metadata anchor | Enrich arkaim_era provenance, remove orphan |
| `FutureExtrapolator` | Forward chain | Use FUTURE_EXTRAPOLATION provenance |
| `PresentAnchor` | Entity↔node mapping | Fill temporal_nodes[] |

### Data Flow

```
1. WorldModel.load()
   ↓
2. TemporalReconstructionEngine.from_world_model(wm)
   ├─ Load epochs → TemporalNodes
   ├─ Load relations (PRECEDES between epochs)
   ├─ Add temporal_today (fixed provenance)
   ├─ Add relation temporal_today → temporal_arkaim_era
   └─ Enrich temporal_arkaim_era with ArkaimAnchor provenance
   ↓
3. M6 BACKWARD: _trace_backward("temporal_today")
   → [temporal_today, ..., temporal_arkaim_era, ..., temporal_pre_arkaim]
   ↓
4. M8 FORWARD: _trace_forward("temporal_arkaim_era")
   → [temporal_arkaim_era, temporal_future, ...]
   → FutureExtrapolator generates scenarios
   → Each scenario tagged FUTURE_EXTRAPOLATION
```

---

## UNSOLVED QUESTIONS

### Q1: Provenance для temporal_today

Какой category использовать?
- [ ] `HYPOTHESIS` — safe, but implies uncertainty
- [ ] `PRESENT_REFERENCE` — new category, cleanest
- [ ] `EXTERNAL_SOURCE` — present is real-world data
- [ ] `AUTHOR_CANON` — WRONG (present ≠ book canon)

### Q2: Relation type для Present → Arkaim

- [ ] `FOLLOWS` (existing) + description metadata — least invasive
- [ ] New `ARCHAEOLOGICAL_CONNECTION` type — semantically correct, more code
- [ ] `UNKNOWN` + detailed description — honest but limited

### Q3: Dual anchor resolution

- [ ] Enrich arkaim_era with ArkaimAnchor provenance, remove arkaim_anchor from graph
- [ ] Keep both, add IDENTICAL_TO relation
- [ ] Make arkaim_anchor the canonical, migrate arkaim_era to metadata

### Q4: Evidence for Present → Arkaim

- [ ] Add archaeological discovery date to KNOWLEDGE/ARCHAEOLOGY.json
- [ ] Use existing ARCHAEOLOGY.json facts as evidence (weaker but available)
- [ ] Mark relation as HYPOTHESIS until evidence is added

### Q5: M8 integration with full chain

- [ ] M8 should accept `anchor_id="temporal_today"` and trace through arkaim_era
- [ ] M8 should tag results with FUTURE_EXTRAPOLATION provenance
- [ ] M8 should report chain context (present → arkaim → future)

---

## M8.1 IMPLEMENTATION SCOPE

### After decision on questions above, M8.1 needs:

#### Must have (M8.1.1)
1. Fix `TemporalNode.present_anchor()` provenance (remove AUTHOR_CANON)
2. Add `temporal_today` to graph in `TemporalReconstructionEngine.from_world_model()`
3. Add relation `temporal_today → temporal_arkaim_era` with correct provenance
4. Enrich `temporal_arkaim_era` with ArkaimAnchor provenance (merge both)
5. Remove orphan `temporal_arkaim_anchor` from graph

#### Should have (M8.1.2)
6. M8 accepts `anchor_id="temporal_today"` (not just "arkaim_era")
7. M8 tags scenario results with `FUTURE_EXTRAPOLATION` provenance
8. M8 returns chain context (present→arkaim→future)

#### Nice to have (M8.1.3)
9. Fill `PresentAnchor.temporal_nodes` with actual node IDs
10. Add archaeological discovery date to ARCHAEOLOGY.json evidence

### Estimated scope
- **Code changes:** ~80 lines (present_anchor fix + from_world_model enrichment)
- **New tests:** ~8 tests
- **Breaking changes:** None (additive)

---

## FINAL STATUS

### M8.1 — ARCHITECTURE READY FOR DECISION

**Обоснование:**

1. Все ключевые компоненты идентифицированы и проанализированы
2. Существующие provenance инварианты проверены на соответствие
3. Gap между Present и Arkaim точно определён
4. Двойной anchor проанализирован
5. FUTURE_EXTRAPOLATION category найдена и готова к использованию
6. 5 unresolved questions сформулированы явно
7. Implementation scope определён без выбора конкретных решений

**Блокировок нет.** Требуется архитектурное решение по 5 вопросам выше, после чего M8.1 может быть реализован.
