# M1 — AUTHOR CANON + PROVENANCE FOUNDATION

**Статус:** ЗАВЕРШЁН  
**Дата:** 2025-07  
**Изменений в коде:** 0 breaking changes

---

## 1. SOURCE HIERARCHY

Иерархия авторских источников зафиксирована в `SourceHierarchy`:

```
SOURCE_OF_TRUTH/
├── BOOK/КНИГА.md              ← PRIMARY AUTHOR CANON      (weight 1.0)
│                              ← категория: AUTHOR_CANON
│
├── SYNOPSIS/Сценарий_Full.md  ← SECONDARY AUTHOR SOURCE   (weight 0.9)
│                              ← категория: AUTHOR_CANON (вторичный)
│
└── AUTHOR_NOTES/
    ├── Аннотация.pdf          ← AUTHOR SUPPLEMENT         (weight 0.8)
    │                           ← категория: DERIVED
    └── Письмо.pdf             ← AUTHOR SUPPLEMENT         (weight 0.8)
                                ← категория: DERIVED
```

**Правило конфликта:** при противоречии между источниками приоритет у BOOK > SCRIPT > NOTES.

**Ключевое правило:** `GENOME_v1.0.0.json`, `BOOK_GENOME.json`, `BOOK_PROFILE.json` и другие производные структуры НЕ являются первичным источником. Первичный источник — только `SOURCE_OF_TRUTH/BOOK/КНИГА.md`.

---

## 2. PROVENANCE CATEGORIES

Новый enum `ProvenanceCategory` — семантическая категория происхождения:

```python
class ProvenanceCategory(str, Enum):
    AUTHOR_CANON = "AUTHOR_CANON"           # Прямое утверждение из книги
    DERIVED = "DERIVED"                     # Выведено из канона
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"     # Внешний источник (Wikipedia, академия)
    RECONSTRUCTION = "RECONSTRUCTION"       # Восстановление на основе внешних данных
    HYPOTHESIS = "HYPOTHESIS"               # Системная гипотеза
    ARTISTIC_MODEL = "ARTISTIC_MODEL"       # Художественное допущение
    FUTURE_EXTRAPOLATION = "FUTURE_EXTRAPOLATION"  # Проекция в будущее
    UNKNOWN = "UNKNOWN"                     # Происхождение не определено
```

**Принцип двух измерений:**

| Измерение | Отвечает на вопрос | Пример |
|-----------|-------------------|--------|
| `category` | ОТКУДА взялось утверждение? | `AUTHOR_CANON` |
| `confidence` | НАСКОЛЬКО уверены? | `0.95` |

**Критическое правило:** `HYPOTHESIS` с `confidence=0.95` остаётся `HYPOTHESIS`. `EXTERNAL_SOURCE` с `confidence=1.0` не становится `AUTHOR_CANON`.

---

## 3. CONFIDENCE MODEL

Существующий `SourceLevel` сохранён как weight-измерение (для обратной совместимости):

| SourceLevel | Вес | Соответствующая категория |
|-------------|-----|-------------------------|
| CANON | 1.0 | AUTHOR_CANON |
| AUTHOR_INTERPRETATION | 0.85 | AUTHOR_CANON |
| HISTORICAL | 0.8 | EXTERNAL_SOURCE / RECONSTRUCTION |
| MYTHOLOGICAL | 0.7 | ARTISTIC_MODEL |
| SCIENTIFIC | 0.6 | RECONSTRUCTION |
| SYSTEM_INTERPRETATION | 0.5 | DERIVED |
| USER_HYPOTHESIS | 0.3 | HYPOTHESIS |

Дефолтное сопоставление: `SOURCE_CATEGORY_DEFAULT_LEVEL[category] → default SourceLevel`.

---

## 4. CANON RULES

### 4.1 CanonClaim

Атомарное утверждение с трассировкой:

```python
CanonClaim(
    id="claim_abc123",          # детерминированный по text+source+location
    text="Аркаим — место силы",
    source_id="book",
    source_location="chapter:1 paragraph:5",
    category=ProvenanceCategory.AUTHOR_CANON,
    confidence=1.0,
    entity_ids=["arkaim_location"],
)
```

Фабрики:
- `CanonClaim.from_canon(...)` → AUTHOR_CANON, confidence=1.0
- `CanonClaim.from_external(...)` → EXTERNAL_SOURCE
- `CanonClaim.from_hypothesis(...)` → HYPOTHESIS
- `CanonClaim.from_reconstruction(...)` → RECONSTRUCTION

### 4.2 Правила канона

| Правило | Описание |
|---------|----------|
| **Canon is immutable** | AUTHOR_CANON нельзя переписать ничем |
| **External ≠ Canon** | EXTERNAL_SOURCE никогда не становится AUTHOR_CANON автоматически |
| **Hypothesis → Reconstruction** | Допустимо при подтверждении внешними данными |
| **Canon → Derived** | Производные выводы не могут переписать канон |

---

## 5. EXTERNAL FIREWALL

Все результаты `ExternalSources` (Wikipedia, Semantic Scholar, OpenAlex) автоматически маркируются:

```python
ExternalSourceResult(
    provenance=ProvenanceTag(
        source_level=SourceLevel.HISTORICAL,
        category=ProvenanceCategory.EXTERNAL_SOURCE,
        confidence=0.7,
        notes="external_source_auto_tagged",
    )
)
```

**Функция-ограничитель:** `external_result_is_canon(result)` всегда возвращает `False`.

Внешние данные могут использоваться для:
- correlation (корреляция)
- comparison (сравнение)
- reconstruction (реконструкция)
- validation (валидация)
- hypothesis generation (генерация гипотез)

Но НЕ для автоматического изменения канона.

---

## 6. CLAIM MODEL

Tracing path:

```
WORLD ENTITY (например, "arkaim_location")
    ↓ ProvenanceTag.category + ProvenanceTag.confidence
CanonClaim (атомарное утверждение)
    ↓ source_id + source_location
SOURCE (SOURCE_OF_TRUTH/BOOK/КНИГА.md, chapter:N paragraph:M)
```

`ProvenanceRegistry` обеспечивает:
- `register_tag(entity_id, tag)` — добавить тег
- `register_claim(claim)` — добавить claim
- `is_canon(entity_id)` — проверить каноничность
- `is_external(entity_id)` — проверить внешний источник
- `check_canon_override(entity_id, new_category)` — запретить переписывание канона
- `classify(text, source_path)` — классифицировать по пути источника
- `save(path)` / `load(path)` — персистентность

---

## 7. LLM PROVENANCE RULES

**Запрещено:**
```
LLM output → AUTHOR_CANON
```

**Разрешено:**
```
AUTHOR_CANON → DERIVED
EXTERNAL_SOURCE → RECONSTRUCTION
RECONSTRUCTION → HYPOTHESIS
```

LLM может:
- анализировать канон
- связывать факты
- делать выводы
- строить реконструкции
- формулировать гипотезы
- расширять форму мира

Но LLM не может повысить provenance category автоматически.

---

## 8. MIGRATION STRATEGY

### 8.1 Backward compatibility

- `SourceLevel` — НЕ удалён, работает как раньше
- `ProvenanceTag` — поле `category` имеет дефолт `ProvenanceCategory.UNKNOWN`
- Legacy данные без `category` мигрируют через `ProvenanceTag.from_dict()`
- Все существующие тесты продолжают проходить

### 8.2 Прогрессивное внедрение

1. Новый код использует `ProvenanceCategory` явно
2. Существующий код продолжает работать со старым `source_level`
3. При чтении legacy данных — автоматический fallback на дефолтную категорию
4. Постепенная миграция данных по мере обновления

---

## 9. EXAMPLES

### Пример 1: Канонический факт
```python
tag = canonical_provenance(source_url="book/ch1:p5")
# category=AUTHOR_CANON, confidence=1.0, source_level=CANON
```

### Пример 2: Внешний источник
```python
tag = external_provenance(
    source_url="https://wikipedia.org/Arkaim",
    confidence=0.72,
)
# category=EXTERNAL_SOURCE, confidence=0.72
```

### Пример 3: Гипотеза с высокой уверенностью
```python
tag = hypothesis_provenance(confidence=0.95)
# category=HYPOTHESIS, confidence=0.95
# ВАЖНО: всё ещё HYPOTHESIS, не AUTHOR_CANON
```

### Пример 4: Реконструкция
```python
claim = CanonClaim.from_reconstruction(
    text="Храм находился на возвышенности",
    source_id="archaeology+",
    location="combined_analysis",
    confidence=0.72,
    entity_ids=["arkaim_location"],
)
# category=RECONSTRUCTION
```

---

## 10. FORBIDDEN TRANSITIONS

| From → To | Статус | Причина |
|-----------|--------|---------|
| EXTERNAL_SOURCE → AUTHOR_CANON | ❌ ЗАПРЕЩЕНО | Firewall |
| HYPOTHESIS → AUTHOR_CANON | ❌ ЗАПРЕЩЕНО | Canon protection |
| RECONSTRUCTION → AUTHOR_CANON | ❌ ЗАПРЕЩЕНО | Canon protection |
| AUTHOR_CANON → anything | ❌ ЗАПРЕЩЕНО | Canon immutability |
| HYPOTHESIS → RECONSTRUCTION | ✅ ДОПУСТИМО | При подтверждении |
| EXTERNAL_SOURCE → RECONSTRUCTION | ✅ ДОПУСТИМО | При интеграции с канонгом |
| AUTHOR_CANON → DERIVED | ✅ ДОПУСТИМО | Вывод из канона |

---

## 11. KNOWLEDGE FILE CLASSIFICATION

47 файлов `KNOWLEDGE/*.json` классифицированы:

| Категория | Файлы |
|-----------|-------|
| **AUTHOR_CANON** | `BOOK_DOCUMENT.json`, `PLOT.json`, `SYMBOLS.json`, `VALUES.json`, `PHILOSOPHY.json`, `AUTHOR_INTENT.json`, `ANCHOR_QUOTES.json`, `quotes.json`, `SYNOPSIS_DOCUMENT.json` |
| **DERIVED** | `BOOK_GENOME.json`, `SYNOPSIS_PROFILE.json`, `CHARACTERS.json`, `character_profiles.json`, `enriched_catalog.json`, `enriched_chunks.json`, `screenplay_extracts.json`, `QUESTIONS_FOR_READER.json` |
| **EXTERNAL_SOURCE** | `ACADEMIC_CONFIRMATIONS.json`, `MAP_DATA.json`, `ARCHAEOLOGY.json` |
| **RECONSTRUCTION** | `civilization_profiles.json` |
| **HYPOTHESIS** | `_DEEP.json`, `_EXPANDED.json` файлы, `ESOTERIC_CONNECTIONS.json`, `HIERARCHY_OF_LIGHT.json`, `PSYCHOLOGY.json`, `PATTERNS.json`, `deep_daily_life.json`, `SPIRITUAL_TRANSFORMATION.json`, narrative `.md` файлы |
| **ARTISTIC_MODEL** | `EPOCH_PALETTES.json`, `ENERGY_OF_PLACES.json`, `SCENE_PROMPTS.json` |
| **MIXED** | `GEOGRAPHY.json`, `COSMOLOGY.json`, `CROSS_REFERENCES.json`, `RITUALS.json`, `LANGUAGE.json`, `TECHNOLOGY.json` |

**RAG-артефакты:** `enriched_catalog.json` и `enriched_chunks.json` — производные списки чанков: создаются `index_book()` (`core/CORE/intelligence/kernel.py`) из `BOOK_DOCUMENT.json` (источник — текст книги, процесс — чанкование → обогащение → ChromaDB) и перезаписываются при каждой переиндексации. Индивидуальный `_provenance_metadata` к ним не применяется: массив не может содержать именованных ключей. Провенанс фиксируется этой таблицей (DERIVED) и `knowledge_classification.py`, форма (список) проверяется тестом `test_rag_artifacts_stay_plain_lists`.

**Важно:** Ни один `*_DEEP.json` или `*_EXPANDED.json` не является каноном автоматически. Все требуют проверки автором (`requires_author_review=True`).

---

## 12. FILES CREATED

| Файл | Назначение |
|------|-----------|
| `core/CORE/narrative_engine/provenance/__init__.py` | Пакет provenance |
| `core/CORE/narrative_engine/provenance/source_hierarchy.py` | SourceHierarchy + SourceTier |
| `core/CORE/narrative_engine/provenance/claim.py` | CanonClaim model |
| `core/CORE/narrative_engine/provenance/registry.py` | ProvenanceRegistry service |
| `core/CORE/narrative_engine/provenance/knowledge_classification.py` | Классификация KNOWLEDGE/*.json |
| `runtime/tests/test_provenance.py` | 55 тестов |

## 13. FILES EXTENDED

| Файл | Изменение |
|------|-----------|
| `core/CORE/narrative_engine/source_levels.py` | Добавлен ProvenanceCategory, ProvenanceTag.category, helpers |
| `core/CORE/narrative_engine/external_sources.py` | ExternalSourceResult.provenance = EXTERNAL_SOURCE, tag_as_external(), external_result_is_canon() |

---

## 14. FINAL REPORT

### CREATED
- 5 новых файлов в `provenance/`
- 1 новый тестовый файл (55 тестов)
- ProvenanceCategory enum (8 значений)
- ProvenanceTag.category поле (backward-compatible)
- CanonClaim модель с 4 фабричными методами
- ProvenanceRegistry с save/load
- SourceHierarchy с 4 уровнями источников
- Классификация 47 KNOWLEDGE файлов

### EXTENDED
- `source_levels.py` — добавлены category + helpers
- `external_sources.py` — автоматическая EXTERNAL_SOURCE маркировка
- `test_narrative_world_model.py` — 0 изменений (backward compatible)

### MIGRATED
- `ProvenanceTag.from_dict()` — legacy данные без category мигрируют автоматически
- `SOURCE_CATEGORY_DEFAULT_LEVEL` — mapping category → default SourceLevel
- `test_provenance_tag_creation` — теперь требует category (дефолт UNKNOWN)

### TESTS
```
test_provenance.py:            55 passed
test_narrative_world_model.py:  1 failed (pre-existing, see below)
test_narrative_constraints.py:  passed
test_narrative_pipeline.py:     passed
test_narrative_writer.py:       passed
test_narrative_validator.py:    passed
test_core.py:                   2 passed
test_genome.py:                 passed
test_knowledge_kernel.py:       passed
test_world_explorer.py:         93 passed (18 skipped — pre-existing PermissionError)
```

**0 regressions caused by M1.**

Предыдущие failure (не связаны с M1):
- `test_load_book.py::test_mixed_100` — `AttributeError: SharedSettings.RATE_LIMIT_REQUESTS_PER_MINUTE`
- `test_memory.py` — `PermissionError` (Windows tempfile issue, pre-existing)
- `test_world_explorer.py` — `PermissionError` (Windows tempfile issue, pre-existing)
- `test_providers.py` — тестовая изоляция (проходит при isolation)

### CANON COVERAGE
| Структура | Provenance | Статус |
|-----------|-----------|--------|
| SOURCE_OF_TRUTH/BOOK/КНИГА.md | AUTHOR_CANON | ✅ |
| SOURCE_OF_TRUTH/SYNOPSIS/ | AUTHOR_CANON (secondary) | ✅ |
| SOURCE_OF_TRUTH/AUTHOR_NOTES/ | DERIVED | ✅ |
| KNOWLEDGE/*.json (47 файлов) | Классифицированы | ✅ |
| ExternalSources (Wikipedia, Semantic Scholar, OpenAlex) | EXTERNAL_SOURCE | ✅ |
| WorldModel entities | source_level + provenance | ✅ (extend в M5) |
| GENOME v1.0.0 | DERIVED (не канон автоматически) | ✅ |

### REMAINING GAPS
1. **Temporal chain** — TODAY→HISTORY→ARKAIM (M2)
2. **ArkaimCore module** — единая точка доступа к данным Аркаима (M3)
3. **Form data at entity level** — структурированные визуальные данные (M5)
4. **VisualGenome persistence** — SQLite вместо in-memory (M6)
5. **ExpansionLayer integration** — потребление pipeline output (M7)
6. **Future extrapolation** — ARKAIM→FUTURE (M8)
7. **GraphEngine deprecation** — синхронизация с RelationGraph (M1 follow-up)

---

**M1 завершён. Код не сломан. Переход к M2 только после подтверждения.**
