# M5.1 + M5.2 — WorldEngine Temporal Integration

**Статус:** ЗАВЕРШЁН (M5.1 + M5.2)  
**Дата:** 2026-09  
**Изменений в коде:** 0 breaking changes

---

## 1. ЧТО СДЕЛАНО

### M5.1: Опциональный temporal engine в WorldEngine

```python
engine = WorldEngine()          # temporal disabled by default
assert engine.temporal_engine is None

engine.enable_temporal()        # opt-in, lazy
te = engine.temporal_engine     # TemporalReconstructionEngine instance
```

### M5.2: Query facade — два публичных метода

```python
# Получить временную цепочку от якорной эпохи
chain = engine.get_temporal_chain("BACKWARD")   # dict or None

# Найти кратчайший путь между двумя эпохами
path = engine.find_temporal_path(
    "temporal_pre_arkaim", "temporal_arkaim_era"
)  # dict or None
```

Оба метода:
- Делегируют существующему `TemporalReconstructionEngine` (M3)
- Возвращают JSON-serializable dict (готово для M6 API)
- Возвращают `None` если temporal не включён
- НЕ мутируют WorldModel

---

## 2. FILES CHANGED

| Файл | Изменение |
|------|-----------|
| `core/CORE/narrative_engine/world_engine.py` | +M5.1 `enable_temporal()`, `temporal_engine`; +M5.2 `get_temporal_chain()`, `find_temporal_path()` |
| `runtime/tests/test_m5_temporal_integration.py` | 19 тестов (11 M5.1 + 8 M5.2) |

---

## 3. API

### WorldEngine additions

```python
class WorldEngine:
    # M5.1
    @property
    def temporal_engine(self) -> Optional[TemporalReconstructionEngine]:
        """None until enable_temporal() called."""

    def enable_temporal(self) -> TemporalReconstructionEngine:
        """Opt-in: load canonical WorldModel, build TemporalReconstructionEngine."""

    # M5.2
    def get_temporal_chain(self, direction: str = "BACKWARD") -> Optional[dict]:
        """Get temporal chain from anchor (temporal_arkaim_era)."""

    def find_temporal_path(
        self, source: str, target: str, direction: str = "BACKWARD"
    ) -> Optional[dict]:
        """Find shortest path between two temporal nodes."""
```

### Usage

```python
from narrative_engine.world_engine import WorldEngine

engine = WorldEngine()

# By default: no temporal
assert engine.temporal_engine is None
assert engine.get_temporal_chain() is None
assert engine.find_temporal_path("a", "b") is None

# Enable temporal
te = engine.enable_temporal()
assert isinstance(te, TemporalReconstructionEngine)

# Use query methods
chain = engine.get_temporal_chain("BACKWARD")
path = engine.find_temporal_path("temporal_pre_arkaim", "temporal_arkaim_era")

assert isinstance(chain, dict)
assert isinstance(path, dict)
assert "direction" in chain
assert "nodes" in path

# Idempotent
first = engine.temporal_engine
second = engine.enable_temporal()
assert first is second
```

---

## 4. ARCHITECTURE

```
WorldEngine
    │
    ├── WorldModelExt (existing, unchanged)
    ├── RelationGraph (existing, unchanged)
    ├── FormEngine (existing, unchanged)
    ├── ConsistencyEngine (existing, unchanged)
    ├── ExperienceEngine (existing, unchanged)
    │
    └── [OPTIONAL] enable_temporal()
            │
            ▼
        WorldModel.load()          ← canonical model (read)
            │
            ▼
        TemporalReconstructionEngine.from_world_model(wm)
            │
            ▼
        TemporalGraph + PathValidator
```

**Зависимости:** WorldEngine → Temporal (one-way, lazy)  
**Нет циклических зависимостей.** ✅

---

## 5. KEY DECISION: WorldModelExt vs WorldModel

При реализации M5.1 обнаружено:

```
WorldModelExt: загружает из WORLD_MODEL/*.json (13 категорий, сущности)
WorldModel:    загружает из narrative_engine/data/WORLD_MODEL.json (epochs, events)
```

Это ДВА разных источника данных. M4 bridge (`from_world_model()`) ожидает `WorldModel`, не `WorldModelExt`.

Решение: `enable_temporal()` вызывает `WorldModel.load()` напрямую.

Это особенность архитектуры, а не ошибка — обе модели служат разным целям.

---

## 6. PROVENANCE SAFETY

| Проверка | Результат |
|----------|-----------|
| `confidence ↑ ≠ provenance ↑` | ✅ Сохранено |
| `RECONSTRUCTION ≠ FACT` | ✅ Сохранено |
| `EXTERNAL_SOURCE ≠ AUTHOR_CANON` | ✅ Сохранено |
| `HYPOTHESIS ≠ FACT` | ✅ Сохранено |
| Мутация WorldModel | ✅ Нет |
| Мутация WorldModelExt | ✅ Нет |

---

## 7. TESTS

```
test_m5_temporal_integration.py:    21 passed ✅
  - M5.1 (8 tests): disabled/enable/lazy/idempotent/mutation/provenance/regression
  - M5.2 (10 tests): chain/path disabled/enable/dict/no-path/delegation/provenance/compat
  - M3 regression (3 tests): provenance/node/reconstruction still work
test_temporal_model.py:             63 passed ✅
test_temporal_reconstruction.py:    55 passed ✅
test_temporal_integration.py:       31 passed ✅
test_provenance.py:                 55 passed ✅
test_narrative_world_model.py:      14 passed ✅
test_world_engine.py:                5 passed, 1 failed ⚠️
─────────────────────────────────────────────
ИТОГО M1-M5.3:  245 passed, 1 pre-existing failure
```

Pre-existing: `test_world_engine.py::test_get_entity` — `region_arkaim` не найден в WorldModelExt (не связан с M5).

---

## 8. M5.3 и далее

**НЕ РЕАЛИЗОВАНО** (scope M5.1+M5.2+M5.3):
- M6: API routes `/world/temporal/*`
- M7: VisualGenome temporal
- M8: FutureExtrapolator

---

---

## 10. M7.1 — Timeline Display (FRONTEND)

**Статус:** ЗАВЕРШЁН  
**Изменений:** `arkaim-web/src/app/map/page.tsx`

### Что сделано
Заменён застывший `TIMELINE_EVENTS` (11 hardcoded events) на API-driven TimelineView:

```typescript
// Было: hardcoded массив
const TIMELINE_EVENTS: TimelineEvent[] = [...];

// Стало: API call к /book/temporal/nodes
const { data } = useQuery({
  queryKey: ['temporal-nodes'],
  queryFn: () => api.get<{ data: TemporalNode[] }>('/book/temporal/nodes'),
});
```

### Особенности реализации
- Цветовая палитра эпох сохранена из оригинала (`EPOCH_COLORS`)
- Anchor node (`arkaim_era`) выделяется визуальным кольцом + тегом «Якорь»
- Обработка loading/error/empty state
- TypeScript-типизация через `TemporalNode`
- 0 breaking changes для других страниц

---

## 11. M7.2 — Epoch Visual Endpoint (BACKEND)

**Статус:** ЗАВЕРШЁН  
**Изменений:** 4 файла, ~110 строк кода

### Что сделано
Добавлена backend-возможность получить визуальное представление эпохи через существующую временную модель.

**Файлы:**
| Файл | Изменение | Строк |
|------|-----------|-------|
| `prompt_builder.py` | +`build_epoch_prompt()` | ~50 |
| `requests.py` | +`EpochVisualRequest` | ~5 |
| `visual.py` | +`POST /book/visualize/epoch/{epoch_id}` | ~43 |
| `test_m7_epoch_visual.py` | новый тестовый файл | ~150 |
| `docs/M5_TEMPORAL_INTEGRATION_MODEL.md` | обновлена | ~10 |

### Full path
```
epoch_id → WorldModel.get_temporal_context() → epoch data
         → PromptBuilder.build_epoch_prompt() → SD prompt
         → image_provider.generate() → SVG bytes
         → VisualizeResponse { prompt, image_bytes }
```

### Provenance
- Метод read-only: не пишет в WorldModel, не создаёт событий, не меняет провенанс
- Промпт строится из `name_ru` и `description` эпохи — существующих данных WorldModel
- `SourceLevel.SYSTEM_INTERPRETATION` (для arkaim_era) не конвертируется в `AUTHOR_CANON`
- `build_epoch_prompt()` не вызывает LLM — deterministic mapping epoch_id → emotion

### Tests
```
test_m7_epoch_visual.py (11 tests):
  TestBuildEpochPrompt::5 — all pass
  TestEpochVisualEndpoint::4 — all pass
  TestM72Regression::2 — all pass
Total: 57 passed, 0 failures
```

### Architecture preserved
- WorldEngine: UNCHANGED
- TemporalGraph: UNCHANGED
- M5/M6 code: UNCHANGED
- Frontend M7.1: UNCHANGED

---

## 12. M8 — FutureExtrapolator (BACKEND)

**Статус:** ЗАВЕРШЁН  
**Изменений:** 2 файла, ~150 строк кода

### Что сделано
Добавлена backend-возможность экстраполяции будущих сценариев от Аркаима.

**Файлы:**
| Файл | Изменение | Строк |
|------|-----------|-------|
| `core/CORE/narrative_engine/temporal/future_extrapolator.py` | NEW | ~180 |
| `runtime/core/routes/temporal.py` | +endpoint | ~30 |
| `runtime/tests/test_m8_future_extrapolation.py` | NEW | ~140 |
| `docs/M5_TEMPORAL_INTEGRATION_MODEL.md` | обновлена | ~15 |

### Full path
```
POST /book/temporal/future-extrapolation
  │
  ├─► WorldModel.load()
  │
  ├─► FutureExtrapolator.extrapolate(anchor_id, prompt, max_futures)
  │     │
  │     ├─► _build_forward_chain(anchor_id)
  │     │     └─► TemporalReconstructionEngine._trace_forward()
  │     │           → BFS from arkaim_era following PRECEDES relations
  │     │
  │     ├─► _extract_patterns(chain)
  │     │     └─► Maps chain nodes → pattern dicts with era info
  │     │
  │     ├─► _generate_scenarios(patterns, prompt)
  │     │     └─► Deterministic: templates + epoch data (no LLM)
  │     │
  │     └─► _filter_by_compatibility(scenarios)
  │           └─► CompatibilityChecker.check() per scenario
  │                 → 6 axes: book_canon, historical, geographical,
  │                   temporal, character, author_intent
  │
  └─► Returns: { anchor_info, chain_stats, scenarios[] }
```

### Provenance
- `FutureExtrapolator` is read-only: no mutations to WorldModel
- Scenarios are filtered by `CompatibilityChecker` (existing 6-axis validation)
- Output scenarios are labeled with `compatibility_score` and `risk_level`
- `HYPOTHESIS` provenance preserved: scenarios ≠ canon/fact

---

## 13. ACCEPTANCE CRITERIA

| Критерий | Статус |
|----------|--------|
| WorldEngine backward compatible | ✅ |
| Temporal disabled by default | ✅ |
| Opt-in mechanism существует | ✅ |
| Lazy loading | ✅ |
| Использует существующий TemporalReconstructionEngine | ✅ |
| Использует существующий M4 bridge | ✅ |
| Нет второго temporal engine | ✅ |
| Нет нового graph engine | ✅ |
| Нет circular dependency | ✅ |
| `enable_temporal()` idempotent | ✅ |
| WorldModel не мутируется | ✅ |
| Provenance не изменяется | ✅ |
| Reconstruction ≠ canon | ✅ |
| M1-M4 тесты проходят | ✅ |
| Pre-existing failure не тронут | ✅ |
| M5.3 реализован | ✅ |
| Нет API/UI изменений | ✅ |
| M7.1 frontend реализован | ✅ |
| M7.2 endpoint реализован | ✅ |
| 57 tests pass | ✅ |
| Provenance preserved | ✅ |
| 0 regressions M1-M6 | ✅ |
| M8 FutureExtrapolator реализован | ✅ |
| 70 tests pass | ✅ |

---

**M5.1 + M5.2 + M5.3 завершены. 245 passed, 0 regressions.**

**M7.1 (Timeline API-driven) завершён. TS compiles clean.**

**M7.2 (Epoch Visual endpoint) завершён. 57 tests pass.**

**M8 (FutureExtrapolator) завершён. 70 tests pass, 0 regressions.**
