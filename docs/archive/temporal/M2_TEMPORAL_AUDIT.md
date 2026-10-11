# M2 — TEMPORAL MODEL AUDIT

**Цель:** Аудит существующей временной модели перед созданием TemporalChain.  
**Принцип:** EXTEND существующее, НЕ создавать дубликат.

---

## 1. СУЩЕСТВУЮЩАЯ TEMPORAL МОДЕЛЬ

### 1.1 Epoch (world_model.py)

```python
class Epoch(BaseModel):
    id: str
    name: str
    name_ru: str
    description: str = ""
    order: int = 0                    # ← линейный порядок
    duration_years: Optional[int] = None
    start_event: Optional[str] = None # ← строка, не temporal
    end_event: Optional[str] = None
    technologies_available: list[str]
    civilizations_active: list[str]
    source_level: SourceLevel
    provenance: list[ProvenanceTag]
```

**Статус:** ✅ Работает. 6 эпох в world_model_data.py.  
**ГАП:** `order` — единственный temporal field. Нет дат, нет precision, нет relations между эпохами.

### 1.2 CanonicalEvent (world_model.py)

```python
class CanonicalEvent(BaseModel):
    id: str
    title: str
    title_ru: str
    description: str = ""
    epoch: str                        # ← foreign key к Epoch
    location_id: Optional[str] = None
    characters_involved: list[str]
    chapter: Optional[int] = None
    order_in_epoch: int = 0           # ← линейный порядок внутри эпохи
    source_level: SourceLevel
    provenance: list[ProvenanceTag]
```

**Статус:** ✅ Работает.  
**ГАП:** Нет temporal precision, нет дат, только относительный порядок.

### 1.3 TimelinePlanner (planners/timeline.py)

```python
class ChronologicalEvent(BaseModel):
    id: str
    title: str
    epoch: str
    order: int = 0
    description: str = ""

class TimelinePlan(BaseModel):
    events_chronological: list[ChronologicalEvent]
    temporal_conflicts: list[str]
    character_lifetimes: dict
    safe_period: str
```

**Методы:** `plan()`, `_check_temporal_conflicts()`, `_determine_safe_period()`  
**Статус:** ✅ Работает для story constraints.  
**ГАП:** Проверяет только дубликаты, не temporal paradoxes. Не связан с TemporalChain.

### 1.4 WorldRelation (relation_models.py)

```python
class WorldRelation(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType        # CAUSAL, HISTORICAL, GEOGRAPHIC, ...
    description: str = ""
    strength: float = 1.0
    evidence: list[str]
    epoch: str = ""                    # ← временной контекст
    bidirectional: bool = False
```

**Статус:** ✅ Работает. 287 связей, 8 типов.  
**ГАП:** `epoch` — строка, не temporal node. Нет temporal relations (BEFORE, AFTER, OVERLAPS).

### 1.5 WorldState / WorldStateBuilder (world_state.py)

```python
class WorldState(BaseModel):
    epoch_id: str
    epoch_name_ru: str
    active_characters: list[CharacterState]
    available_locations: list[LocationState]
    technologies: list[Technology]
    events_happened: list[CanonicalEvent]
    events_pending: list[CanonicalEvent]
    active_rules: list[CausalRule]
    civilization_state: dict
```

**Статус:** ✅ Работает.  
**ГАП:** Snapshot по epoch_id, не chain.

### 1.6 CauseEffectNode (cause_effect.py)

```python
class CauseEffectNode(BaseModel):
    id: str
    type: str  # cause, effect, reaction, world_change, constraint
    description: str
    source_level: str = "SYSTEM_INTERPRETATION"
    confidence: float = 0.8
    depends_on: list[str]
    characters_involved: list[str]
    epoch: str = ""
    order: int = 0                   # ← temporal order
```

**Статус:** ✅ Работает.  
**ГАП:** `order` — относительный, не absolute temporal.

### 1.7 Epochs в world_model_data.py

6 стандартных эпох:
```
pre_arkaim (order=0)  — До Аркаима
satya_yuga (order=1)  — Золотой век
treta_yuga (order=2)  — Серебряный век
dvapara_yuga (order=3) — Бронзовый век
kali_yuga (order=4)   — Тёмный век
arkaim_era (order=5)  — Эпоха Аркаима
```

**Статус:** ✅ Заполнены.  
**ГАП:** Нет дат, нет precision, нет переходов между эпохами.

---

## 2. РЕШЕНИЕ: EXTEND, НЕ DUPLICATE

### 2.1 Что остаётся как есть

| Компонент | Решение | Причина |
|-----------|---------|---------|
| `Epoch` (world_model.py) | **KEEP** | Already has temporal data (order, duration, events). New TemporalNode wraps it. |
| `TimelinePlanner` | **KEEP** | Different responsibility: story constraints, not temporal graph. |
| `CanonicalEvent` | **KEEP** | Has epoch + order + provenance. Sufficient for event-level temporal. |
| `WorldRelation.epoch` | **KEEP** | String reference. TemporalRelation adds typed temporal edges. |

### 2.2 Что добавляем (M2)

| Новый компонент | Назначение |
|----------------|-----------|
| `TemporalPrecision` | Точность датировки (EXACT, YEAR, CENTURY, UNKNOWN, ...) |
| `TemporalNode` | Временной узел: epoch + precision + bounds + provenance |
| `TemporalRelationType` | Типизированные временные связи (BEFORE, DEVELOPS_FROM, ...) |
| `TemporalRelation` | Связь между TemporalNode |
| `TemporalChain` | Направленный граф эпох (BACKWARD / FORWARD) |
| `TemporalGap` | Явное представление неизвестного пробела |
| `ReconstructionPath` | Путь реконструкции: nodes + relations + gaps |
| `PresentAnchor` | Связь современного объекта с историческими слоями |
| `ArkaimAnchor` | Special temporal anchor для Аркаима |

### 2.3 Отличие TemporalNode от Epoch

```
Epoch (existing):
  order: int           ← linear position
  duration_years: int  ← approximate
  start_event: str     ← narrative event, not date

TemporalNode (new):
  epoch_id: str        ← reference to Epoch
  start: Optional[str] ← "2000 BCE" or None
  end: Optional[str]   ← "1500 BCE" or None
  precision: TemporalPrecision  ← EXACT, YEAR, CENTURY, UNKNOWN
  bounds: Optional[dict]       ← {start_date, end_date, uncertainty}
  provenance: list[ProvenanceTag]
```

**TemporalNode обёртывает Epoch, не заменяет его.**

---

## 3. TIMELINEPLANNER vs TEMPORALCHAIN

| Aspect | TimelinePlanner | TemporalChain |
|--------|----------------|---------------|
| Цель | Story constraints | Historical reconstruction |
| Уровень | Events within epoch | Epochs and transitions |
| Direction | None (sorted list) | BACKWARD / FORWARD |
| Gaps | Not modeled | Explicit TemporalGap |
| Provenance | Per event | Per node + relation |
| API | `/book/story/*` | `/book/temporal/*` |

**Обе системы работают параллельно, не конфликтуют.**

---

## 4. ПРОСТРАНСТВО ИМЁН

```
narrative_engine/
├── temporal/                    ← NEW package
│   ├── __init__.py
│   ├── precision.py             ← TemporalPrecision enum
│   ├── node.py                  ← TemporalNode
│   ├── relation.py              ← TemporalRelationType + TemporalRelation
│   ├── chain.py                 ← TemporalChain
│   ├── gap.py                   ← TemporalGap
│   ├── reconstruction_path.py   ← ReconstructionPath
│   ├── present_anchor.py        ← PresentAnchor
│   └── arkaim_anchor.py         ← ArkaimAnchor
```

---

## 5. АРКАИМ В TEMPORAL MODEL

Существующие данные об Аркаиме:
- `arkaim_era` epoch (order=5)
- `arkaim` location (sacred_site)
- Связи с Hyperborea, Atlantis в relation_extractor

M2 добавляет:
- `ArkaimAnchor` — special temporal node с ID `arkaim_temporal_anchor`
- Связи: `pre_arkaim → DEVELOPS_FROM → arkaim_era`
- `TemporalGap` между `kali_yuga` и `arkaim_era` (evidence_status=PARTIALLY_DOCUMENTED)

---

## 6. PERSISTENCE

Temporal objects сохраняются в:
- `WORLD_MODEL.json` (для архивных данных эпох)
- `runtime/arkaim.db` (для runtime state)
- `runtime/runtime_data/temporal/` (для временных цепочек)

Используем существующий `DatabaseManager` + SQLite.

---

## 7. НЕ ДЕЛАЕМ В M2

- ~~TemporalReconstructionEngine~~ (M3)
- ~~FutureExtrapolator~~ (M8)
- ~~Новый WorldEngine~~
- ~~Frontend~~
- ~~Изменение SOURCE_OF_TRUTH~~
- ~~Изменение GENOME v1.0.0~~
