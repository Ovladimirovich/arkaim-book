# M2 — TEMPORAL MODEL FOUNDATION

**Статус:** ЗАВЕРШЁН  
**Дата:** 2025-07  
**Изменений в коде:** 0 breaking changes

---

## 1. ГЛАВНЫЙ ПРИНЦИП

M2 создаёт **инфраструктуру для представления времени**, а не историю Аркаима.

```
TODAY → HISTORY → ARKAIM → PRE-ARKAIM    (BACKWARD)
ARKAIM → DEVELOPMENT → HISTORY → TODAY → FUTURE   (FORWARD)
```

Это **двунаправленный temporal graph**, не линейный список дат.

**Ключевые правила:**
- `unknown date` ≠ error
- `unknown gap` ≠ error
- `confidence=0.95` + `HYPOTHESIS` = всё ещё HYPOTHESIS
- `EXTERNAL_SOURCE` с `confidence=1.0` ≠ AUTHOR_CANON
- `RECONSTRUCTION` ≠ FACT даже при high confidence

---

## 2. ЧТО ССУЩЕСТВОВАЛО (AUDIT)

| Компонент | Статус | Решение M2 |
|-----------|--------|-----------|
| `Epoch` (world_model.py) | ✅ 6 эпох с order | **KEEP** — обёртка через TemporalNode.from_epoch() |
| `CanonicalEvent` (world_model.py) | ✅ epoch + order + provenance | **KEEP** — уже имеет temporal metadata |
| `TimelinePlanner` (planners/timeline.py) | ✅ story constraints | **KEEP** — другая ответственность |
| `WorldRelation.epoch` | ✅ строка | **KEEP** — TemporalRelation добавляет typed temporal edges |
| `CauseEffectNode.order` | ✅ относительный порядок | **KEEP** — не абсолютная temporal модель |

**Результат аудита:** `docs/M2_TEMPORAL_AUDIT.md`

---

## 3. TEMPORAL PRECISION

10 уровней точности (от наиболее к наименее):

```
EXACT → YEAR → YEAR_RANGE → DECADE → CENTURY → MILLENNIUM
     → ARCHAEOLOGICAL_PERIOD → RELATIVE → STRATIGRAPHIC → UNKNOWN
```

`UNKNOWN` — валидный результат, честная оценка недостатка данных.

```python
TemporalNode(
    id="arkaim_era",
    precision=TemporalPrecision.RELATIVE,  # относительная датировка
)
TemporalNode(
    id="today",
    precision=TemporalPrecision.EXACT,     # точно знаем
)
TemporalNode(
    id="gap_pre_arkaim",
    precision=TemporalPrecision.UNKNOWN,   # честно: не знаем
)
```

---

## 4. TEMPORAL NODE

```python
TemporalNode(
    id="temporal_arkaim_era",
    label="Эпоха Аркаима",
    precision=TemporalPrecision.RELATIVE,
    era_id="arkaim_era",              # ссылка на существующий Epoch
    entity_ids=["arkaim_location"],
    event_ids=[],
    provenance=[... ProvenanceTag ...],
    confidence=0.7,                   # уверенность ≠ provenance
    bounds=TemporalBounds(
        start="2000 BCE",
        end="1800 BCE",
        uncertainty="±200 лет",
    ),
    is_anchor=True,
)
```

**Свойства:**
- `is_known_temporal` — есть ли точность (не UNKNOWN)
- `has_bounds` — есть ли обе временные границы
- `is_canon` / `is_external` / `is_hypothesis` / `is_reconstruction` — по provenance
- `is_gap` — узел-пробел (precision=UNKNOWN, era_id="")

**Factory:**
- `TemporalNode.from_epoch()` — из существующего Epoch
- `TemporalNode.present_anchor()` — современный якорь
- `TemporalNode.gap_node()` — временной пробел

---

## 5. TEMPORAL RELATIONS

12 типизированных отношений:

```
BEFORE / AFTER / OVERLAPS / CONTAINS / CONTAINED_BY
CONTEMPORARY_WITH / PRECEDES / FOLLOWS
DEVELOPS_FROM / TRANSFORMS_INTO   ← линии развития
COEXISTS_WITH / UNKNOWN
```

**ВАЖНО:** `DEVELOPS_FROM` ≠ `PRECEDES`

```python
# Простой порядок (канон из epoch ordering)
TemporalRelation.precedes("satya_yuga", "treta_yuga")
# → AUTHOR_CANON, provenance из упорядочения эпох

# Качественное развитие (гипотеза)
TemporalRelation.develops_from("pre_arkaim", "arkaim_era")
# → HYPOTHESIS, требует археологического подтверждения
```

Обратные отношения автоматические:
```python
REVERSE_RELATIONS[DEVELOPS_FROM] == TRANSFORMS_INTO
REVERSE_RELATIONS[PRECEDES] == FOLLOWS
```

---

## 6. TEMPORAL CHAIN

Направленный граф с поддержкой обоих направлений:

```python
# BACKWARD: TODAY → HISTORY → ARKAIM
chain = TemporalChain.backward_from_today([today_node])

# FORWARD: ARKAIM → DEVELOPMENT → TODAY → FUTURE
chain = TemporalChain.forward_from_arkaim([arkaim_node])
```

**Методы:**
- `add_node()`, `add_relation()`, `add_gap()`
- `get_node()`, `get_relation()`, `get_outgoing_relations()`, `get_incoming_relations()`
- `has_gap_between(from_id, to_id)` — проверка пробела
- `is_continuous()` — непрерывна ли цепочка (без gaps)
- `stats()` — сводная статистика

**Non-continuous chain — валидна:**
```text
A → B → [UNKNOWN GAP] → D
```
Система НЕ заполняет пробелы автоматически.

---

## 7. TEMPORAL GAP

```python
TemporalGap(
    id="gap_pre_arkaim",
    from_node="kali_yuga",
    to_node="arkaim_era",
    reason="Археологические данные недостаточны для определения связи",
    evidence_status=EvidenceStatus.INSUFFICIENT_DATA,
    candidate_bridges=["bridge_x", "bridge_y"],
)
```

**EvidenceStatus (6 уровней):**
```
DOCUMENTED          — пробел документирован
PARTIALLY_DOCUMENTED — частичные данные
INSUFFICIENT_DATA   — валидное состояние (не ошибка!)
RECONSTRUCTABLE     — можно восстановить с новыми данными
HYPOTHETICAL        — гипотетический пробел
UNKNOWN             — статус не определён
```

**Фабрики:**
- `TemporalGap.unknown_gap()` — INSUFFICIENT_DATA (валидно)
- `TemporalGap.reconstructable_gap()` — с candidate bridges

---

## 8. RECONSTRUCTION PATH

Структура для сохранения пути реконструкции (M2 — только структура, без inference):

```python
ReconstructionPath(
    id="rp_today_to_arkaim",
    direction=ChainDirection.BACKWARD,
    nodes=[today, historical, archaeological, arkaim],
    relations=[precedes, develops_from, ...],
    gaps=[unknown_gap],
    provenance=[...],
    confidence=0.65,
)
```

**Свойства:**
- `is_complete` — полный путь (без UNKNOWN GAP)
- `unknown_gap_count` — количество неизвестных пробелов
- `start_node_id` / `end_node_id`

---

## 9. PRESENT ANCHOR

Связь современного объекта с историческими слоями:

```python
anchor = PresentAnchor.for_entity(
    entity_id="modern_urban_infrastructure",
    label="Современная городская инфраструктура",
)
anchor.temporal_nodes = ["temporal_today", "temporal_industrial", "temporal_settlement"]
```

**Принцип:** связь создаётся только при наличии evidence, не автоматически.

---

## 10. ARKAIM ANCHOR

Special temporal anchor для Аркаима (без новых утверждений):

```python
anchor = ArkaimAnchor.from_existing_data()
# → epoch_id="arkaim_era"
# → location_id="arkaim"
# → provenance: AUTHOR_CANON (из книги) + EXTERNAL_SOURCE (археология)
```

**Содержит:**
- Stable ID: `arkaim_anchor`
- Temporal bounds: RELATIVE precision (как известно)
- Provenance: существующие источники (КНИГА.md + ARCHAEOLOGY.json)
- Archaeological links: `["arkaim_site", "bronze_age_culture"]`
- Canon links: `["arkaim_era", "hyperborea", "ritual_center"]`

---

## 11. PROVENANCE INTEGRATION

Каждый temporal объект имеет provenance через M1:

```python
TemporalNode(
    provenance=[
        ProvenanceTag(
            source_level=SourceLevel.CANON,
            category=ProvenanceCategory.AUTHOR_CANON,
            confidence=1.0,
            source_title="КНИГА.md",
            notes="arkaim_era epoch from book canon",
        ),
        ProvenanceTag(
            source_level=SourceLevel.HISTORICAL,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            confidence=0.7,
            source_title="ARCHAEOLOGY.json",
            notes="archaeological evidence for Arkaim site",
        ),
    ],
)
```

**Защитные правила:**
- `TemporalRelation.develops_from()` → HYPOTHESIS provenance (требует подтверждения)
- `TemporalRelation.precedes()` → AUTHOR_CANON (из epoch ordering)
- `ArkaimAnchor.from_existing_data()` → только существующие источники

---

## 12. TIME ≠ CONFIDENCE ≠ PROVENANCE

Четыре независимых измерения:

| Измерение | Вопрос | Пример |
|-----------|--------|--------|
| `precision` | Насколько точно знаем время? | CENTURY vs UNKNOWN |
| `confidence` | Насколько уверены? | 0.95 vs 0.3 |
| `provenance.category` | Откуда взялось? | AUTHOR_CANON vs HYPOTHESIS |
| `evidence_status` | Какой статус доказательств? | INSUFFICIENT_DATA vs DOCUMENTED |

```python
# Все 4 комбинации допустимы:
TemporalNode(precision=EXACT, confidence=1.0, category=AUTHOR_CANON)   # точный канон
TemporalNode(precision=UNKNOWN, confidence=1.0, category=AUTHOR_CANON)  # канон, но время неизвестно
TemporalNode(precision=CENTURY, confidence=0.65, category=EXTERNAL_SOURCE)  # внешний, не канон
TemporalNode(precision=RELATIVE, confidence=0.95, category=HYPOTHESIS)   # гипотеза с высокой уверенностью
```

---

## 13. TIMELINEPLANNER vs TEMPORALCHAIN

| Аспект | TimelinePlanner | TemporalChain |
|--------|----------------|---------------|
| Цель | Story constraints | Historical reconstruction |
| Уровень | События внутри epoch | Epochs и переходы |
| Direction | Нет (sorted list) | BACKWARD / FORWARD |
| Gaps | Не моделирует | Явные TemporalGap |
| Provenance | Per event | Per node + relation |
| API | `/book/story/*` | `/book/temporal/*` |

**Работают параллельно, не конфликтуют.**

---

## 14. FILES CREATED

| Файл | Назначение |
|------|-----------|
| [core/CORE/narrative_engine/temporal/__init__.py](core/CORE/narrative_engine/temporal/__init__.py) | Пакет temporal |
| [core/CORE/narrative_engine/temporal/precision.py](core/CORE/narrative_engine/temporal/precision.py) | TemporalPrecision enum (10 значений) |
| [core/CORE/narrative_engine/temporal/node.py](core/CORE/narrative_engine/temporal/node.py) | TemporalNode + TemporalBounds |
| [core/CORE/narrative_engine/temporal/relation.py](core/CORE/narrative_engine/temporal/relation.py) | TemporalRelationType (12 типов) + TemporalRelation |
| [core/CORE/narrative_engine/temporal/chain.py](core/CORE/narrative_engine/temporal/chain.py) | TemporalChain (BACKWARD/FORWARD) |
| [core/CORE/narrative_engine/temporal/gap.py](core/CORE/narrative_engine/temporal/gap.py) | TemporalGap + EvidenceStatus |
| [core/CORE/narrative_engine/temporal/reconstruction_path.py](core/CORE/narrative_engine/temporal/reconstruction_path.py) | ReconstructionPath |
| [core/CORE/narrative_engine/temporal/present_anchor.py](core/CORE/narrative_engine/temporal/present_anchor.py) | PresentAnchor |
| [core/CORE/narrative_engine/temporal/arkaim_anchor.py](core/CORE/narrative_engine/temporal/arkaim_anchor.py) | ArkaimAnchor |

## 15. FILES EXTENDED

| Файл | Изменение |
|------|-----------|
| `temporal/node.py` | Добавлен `is_reconstruction` property |
| `temporal/chain.py` | Добавлен `gap_count` property, исправлен `is_continuous()` |

---

## 16. TESTS

```
test_temporal_model.py:         63 passed ✅
test_provenance.py:             55 passed ✅
test_narrative_world_model.py:  14 passed ✅
test_narrative_constraints:     passed ✅
test_narrative_pipeline:        passed ✅
test_narrative_writer:          passed ✅
test_narrative_validator:       passed ✅
test_core.py:                   2 passed ✅
test_genome.py:                 passed ✅
test_knowledge_kernel:          passed ✅
test_world_explorer:            93 passed ✅ (18 skipped — pre-existing PermissionError)
```

**Итого: 323 passed, 4 skipped, 0 regressions от M2.**

---

## 17. CANON COVERAGE (TEMPORAL)

| Структура | TemporalPrecision | Provenance | Статус |
|-----------|------------------|------------|--------|
| `epoch.satya_yuga` → `TemporalNode` | RELATIVE | AUTHOR_CANON | ✅ |
| `epoch.arkaim_era` → `TemporalNode` | RELATIVE | AUTHOR_CANON | ✅ |
| `arkaim` → `ArkaimAnchor` | RELATIVE | CANON + EXTERNAL | ✅ |
| `today` → `TemporalNode.present_anchor()` | EXACT | AUTHOR_CANON | ✅ |
| `kali_yuga → arkaim_era` → `TemporalGap` | UNKNOWN | HYPOTHESIS | ✅ |
| `pre_arkaim → arkaim_era` → `DEVELOPS_FROM` | RELATIVE | HYPOTHESIS | ✅ |

---

## 18. FINAL REPORT

### CREATED
- 9 файлов в `temporal/` пакет
- 1 тестовый файл (63 теста)
- `TemporalPrecision` enum (10 значений)
- `TemporalNode` с `TemporalBounds`
- `TemporalRelationType` (12 типов, включая DEVELOPS_FROM/TRANSFORMS_INTO)
- `TemporalChain` с BACKWARD/FORWARD направлениями
- `TemporalGap` с 6 уровнями evidence_status
- `ReconstructionPath` — структура для сохранения путей реконструкции
- `PresentAnchor` — связь современного с историческим
- `ArkaimAnchor` — special anchor для Аркаима (без новых утверждений)

### EXTENDED
- `temporal/node.py` — `is_reconstruction` property
- `temporal/chain.py` — `gap_count` property, исправлен `is_continuous()`

### REMAINING GAPS
1. **TemporalReconstructionEngine** — inference engine для заполнения gaps (M3)
2. **ArkaimCore module** — единая точка доступа к temporal данным Аркаима
3. **Integration с WorldEngineV2** — temporal awareness в world state
4. **API routes** — `/book/temporal/*` для temporal queries
5. **VisualGenome temporal awareness** — временная осведомлённость визуализации
6. **FutureExtrapolator** — проекция в будущее (M8)

---

**M2 завершён. Код не сломан. Переход к M3 (TemporalReconstructionEngine) только после подтверждения.**
