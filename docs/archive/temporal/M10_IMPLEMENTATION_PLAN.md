# M10 IMPLEMENTATION PLAN (read-only audit completed)

Дата: 2026-09-06
Сверено с: `docs/M10_PRE_IMPLEMENTATION_AUDIT.md` (SPEC DRAFT), утверждение владельца.

## Сверка плана с утверждённым SPEC

| SPEC пункт | Реализация | Контракт-основа |
|------------|-------------|-----------------|
| BookChangeDetector (mtime→hash) | Новый модуль | Паттерн `Pulse.watch()` (pulse.py:116-135) |
| TemporalExtractor (словарь маркеров) | Новый модуль | Стиль `entity_extractor.KNOWN_ENTITIES` |
| TemporalFinding (provenance) | Новая Pydantic-модель | `ProvenanceTag`/`ProvenanceCategory` (source_levels.py) |
| Pending queue (suggest-only) | Новый модуль | in-memory, без API endpoint |
| Human confirmation gate | Новый модуль | `WorldModel.save()/reload()` |
| Canon/provenance validation | Внутри confirmation gate | Инварианты M1 (canon не понижается, DERIVED не повышается) |
| WorldEngine.refresh_temporal() | Новая функция рядом с enable_temporal | `from_world_model()` (M4, не изменяется) |
| 12 контрактных тестов | Новый тест-файл | pytest, как M8/M9 |

## Файлы для изменения (фиксация)

### Новый production-код (3 новых модуля, существующие НЕ переписываются)

| Файл | Тип | Содержимое |
|------|-----|------------|
| `core/CORE/narrative_engine/research/book_change_detector.py` | NEW | `BookChangeDetector` класс |
| `core/CORE/narrative_engine/research/temporal_extractor.py` | NEW | `TemporalExtractor` + `TemporalFinding` |
| `core/CORE/narrative_engine/research/temporal_update_manager.py` | NEW | `TemporalUpdateManager` (pending queue + confirmation gate + refresh) |

### Минимальное изменение существующего кода (1 файл)

| Файл | Тип | Изменение |
|------|-----|-----------|
| `core/CORE/narrative_engine/world_engine.py` | EDIT | +`refresh_temporal()` (~15 строк, рядом с `enable_temporal()`, не трогает M5.1) |

### Новый тестовый файл

| Файл | Тестов |
|------|--------|
| `runtime/tests/test_m10_temporal_updates.py` | 12+ |

### НЕ изменяются (проверено read-only audit)

- `temporal/reconstruction_engine.py` (M3/M8.1) — используется как есть
- `temporal/future_extrapolator.py` (M8) — не трогается
- `pulse/layers.py` (M9) — не трогается
- `world_model.py` — используется через публичный API (`get_epochs`, `save`, `reload`)
- `research/entity_extractor.py` — используется как стиль-референс, не изменяется
- `research/world_model_writer.py` — не используется (у него другая data model: ResearchFinding для external sources; M10 findings имеют иную семантику — прямое canon-обогащение)
- `canon_validator.py` — не используется (он для story validation; M10 использует собственную canon/provenance-валидацию в confirmation gate на базе инвариантов M1)
- Никаких routes/endpoints — M10.1 без API
- Никаких frontend/UI изменений

## Data flow (реализуемый)

```
КНИГА.md
  │
  ▼ [polling: caller invokes detector.watch()]
BookChangeDetector.watch()
  ├─ mtime unchanged → None (cheap)
  ├─ mtime changed → hash check
  │    ├─ hash unchanged → None (touch без правки)
  │    └─ hash changed → BookChangeSnapshot
  ▼
TemporalExtractor.extract(text)
  ├─ regex-словарь temporal маркеров
  ├─ absolute: "~4000 лет до н.э." → TemporalFinding(AUTHOR_CANON)
  ├─ relative: "многие века" → TemporalFinding(DERIVED, normalized=CENTURY)
  └─ extraction error → logged, [] findings (graceful)
  ▼
TemporalUpdateManager.submit_findings()
  ├─ dedupe (idempotency: re-extract → 0 новых pending)
  ├─ validate provenance rules (AUTHOR_CANON vs DERIVED)
  └─ → pending queue (in-memory, НЕ применено)
  ▼
[WorldModel НЕ изменён — suggest-only boundary]
  ▼
TemporalUpdateManager.confirm(finding_id)   ← human confirmation
  ├─ canon validation: AUTHOR_CANON не понижается
  ├─ DERIVED не повышается до AUTHOR_CANON
  ├─ conflict → reject (rejected_findings)
  ├─ OK → WorldModel.save() + reload()
  ▼
WorldEngine.refresh_temporal()
  └─ rebuild engine from refreshed WorldModel (from_world_model)
```

## Provenance contract (реализуемый)

| Ситуация | Правило | Категория finding'а |
|----------|---------|---------------------|
| Прямая дата в тексте («~4000 лет до н.э.», «в пятую эпоху») | literal match | AUTHOR_CANON |
| Относительное выражение («многие века», «спустя тысячелетия») | interpretation/normalization | DERIVED |
| Подтверждение AUTHOR_CANON на existing epoch | canon merge, исходные tags сохраняются | AUTHOR_CANON |
| Подтверждение DERIVED на epoch | добавляется как DERIVED tag | DERIVED |
| Попытка подтвердить finding, понижающий canon | **REJECT** | — |
| Попытка подтвердить DERIVED как canon | **REJECT** (validation fails) | — |

## Invariant checks (реализуемые в тестах)

1. Без подтверждения WorldModel идентичен (byte-compare после submit)
2. confirm() → save/reload вызван, данные в WorldModel
3. refresh_temporal() → новый engine instance
4. refresh_temporal() при неизменном WorldModel → тот же instance (idempotent)
5. AUTHOR_CANON epoch не понижен после confirm DERIVED finding
6. DERIVED не повышен до AUTHOR_CANON
7. Повторный extract без изменения книги → 0 новых pending
8. Extraction error → graceful: [] findings, no crash, logged
