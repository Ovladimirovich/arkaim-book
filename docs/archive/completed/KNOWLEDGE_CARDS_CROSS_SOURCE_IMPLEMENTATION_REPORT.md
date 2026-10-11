# MILESTONE C — KNOWLEDGE CARDS + CROSS-SOURCE — Report

**Milestone:** C — Knowledge Cards + Cross-Source
**Дата:** 2026-09-15
**Статус:** IMPLEMENTED + TESTED
**Результат:** 34 новых теста, 316 total, 0 failures (core)

---

## Простыми словами

1. **Что было целью?** — Создать entity-centric представление знания, где одна сущность показывает утверждения из книги, археологии, гипотез и внешних источников — с сохранением provenance каждого утверждения.

2. **Что реально сделано?** — Создан модуль `knowledge_card` с тремя файлами: модели (Pydantic), билдер (агрегация из 5 источников), API-роут. Проведён forensic audit существующей инфраструктуры (WorldEngine, ARCHAEOLOGY.json, CROSS_REFERENCES.json, ACADEMIC_CONFIRMATIONS.json, BookRetriever). Ничего не сломано, все 316 тестов проходят.

3. **Что получилось?** — PASS. Карточка собирает данные из книги (RAG), археологии, кросс-референсов и академических подтверждений. Каждое утверждение имеет provenance. Противоречия показываются, но не разрешаются автоматически.

4. **Есть ли проблемы?** — Две параллельные ChromaDB коллекции (`arkaim_book` vs `book_os_index`) — отложено до отдельного milestone. Embedding model mismatch — отложено.

---

## 0. Forensic Audit Summary

### Что уже существовало и было переиспользовано

| Компонент | Статус | Переиспользование |
|-----------|--------|-------------------|
| WorldEngine.get_entity() | ✅ EXISTS | Entity lookup по ID |
| WorldEngine.search() | ✅ EXISTS | Search by name |
| RelationGraph.get_entity_context() | ✅ EXISTS | Relations for card |
| BookRetriever.search() | ✅ EXISTS | Book claims via RAG |
| ARCHAEOLOGY.json | ✅ EXISTS | ~6 sites with provenance |
| CROSS_REFERENCES.json | ✅ EXISTS | Cultural parallels |
| ACADEMIC_CONFIRMATIONS.json | ✅ EXISTS | Academic sources |
| ProvenanceCategory (8) | ✅ EXISTS | AUTHOR_CANON, EXTERNAL_SOURCE, HYPOTHESIS, RECONSTRUCTION, DERIVED |
| SourceLevel (7) | ✅ EXISTS | CANON, HISTORICAL, AUTHOR_INTERPRETATION, SYSTEM_INTERPRETATION, USER_HYPOTHESIS |
| UncertaintyFlag | ✅ EXISTS | Structured uncertainty tracking |
| PulseResponse | ✅ EXISTS | text + source + confidence + provenance + uncertainty |

### Что НЕ создавалось (согласно требованиям)

- ❌ Новых relation types
- ❌ Новой системы provenance
- ❌ Новой модели сущностей
- ❌ Truth entity
- ❌ KnowledgeArtifact
- ❌ Nation-first taxonomy

---

## 1. Модель Knowledge Card

```python
KnowledgeCard {
    metadata: CardMetadata          # entity_id, entity_name, created_at
    primary_entity: dict | None     # From WorldEngine
    sources: list[SourceAggregation] # 4 источника
    relations: list[dict]           # From RelationGraph
    contradictions: list[ContradictionNote]
    uncertainty: dict | None        # From UncertaintyFlag
    search_suggestions: list[str]
    related_entities: list[dict]
}

SourceAggregation {
    source_name: str               # "book", "archaeology", "cross_references", "academic"
    provenance_category: ProvenanceCategory
    claim_count: int
    claims: list[CardClaim]
    summary: str
    confidence: float
}

CardClaim {
    text: str
    provenance: ProvenanceTag      # Два измерения: category + level
    source_ref: str                # "book:chunk_p_0001_xxx"
    chunk_id: str | None           # Для book claims
    chapter_title: str | None
}

ContradictionNote {
    description: str
    involved_claims: list[str]
    source_1_claim: str
    source_2_claim: str
    resolution: str = "DIFFERENT_PERSPECTIVES"  # НЕ "RESOLVED"
}
```

---

## 2. Cross-Source Aggregation

### Источники данных (в порядке приоритета)

| # | Источник | Provenance | Claim Level |
|---|----------|------------|-------------|
| 1 | **Book (КНИГА.md)** | AUTHOR_CANON | Confidence = retrieval score |
| 2 | **Archaeology** | EXTERNAL_SOURCE / HYPOTHESIS / RECONSTRUCTION | Fact: 0.8, Hypothesis: 0.5 |
| 3 | **Cross-References** | DERIVED | 0.6 |
| 4 | **Academic Confirmations** | EXTERNAL_SOURCE | 0.7 |

### Entity Resolution (3 уровня)

1. **WorldEngine by ID** → O(1) lookup
2. **WorldEngine by search** → name match across all categories
3. **ARCHAEOLOGY.json by name** → fallback для archaeological entities

**Никогда не объединяет автоматически.** Если неоднозначно → UNKNOWN.

---

## 3. Provenance Invariants

```
AUTHOR_CANON ≠ EXTERNAL_SOURCE ≠ HYPOTHESIS ≠ DERIVED
```

Каждый claim имеет свой provenance, который:
- Не меняется при агрегации
- HYPOTHESIS с confidence=1.0 остаётся HYPOTHESIS
- AUTHOR_CANON не становится EXTERNAL_SOURCE

---

## 4. Contradiction Handling

Система обнаруживает потенциальные противоречия через эвристику:
- Сравнение ключевых слов в AUTHOR_CANON vs EXTERNAL_SOURCE claims
- Если найдено → создаётся `ContradictionNote`
- **Никогда не разрешается автоматически**
- Статус: `DIFFERENT_PERSPECTIVES` или `UNRESOLVED`

---

## 5. API Contract

```
GET /knowledge/cards/{entity_id}
  → KnowledgeCard (JSON)

GET /knowledge/cards/search?q={query}&limit={n}
  → {entities: [...], total: int}
```

### Response Structure

```json
{
  "metadata": {
    "entity_id": "arkaim_region",
    "entity_name": "Аркаим",
    "coverage_note": "Данные из книги, археологии и академических источников"
  },
  "primary_entity": { ... },
  "sources": [
    {
      "source_name": "book",
      "provenance_category": "AUTHOR_CANON",
      "claim_count": 3,
      "claims": [
        {
          "text": "Аркаим построен потомками гипербореев",
          "provenance": { "category": "AUTHOR_CANON", "confidence": 1.0 },
          "source_ref": "book:chunk_p_0042_abc",
          "chunk_id": "chunk_p_0042_abc"
        }
      ]
    },
    {
      "source_name": "archaeology",
      "provenance_category": "EXTERNAL_SOURCE",
      "claim_count": 5,
      "claims": [...]
    }
  ],
  "contradictions": [
    {
      "description": "Книга связывает с гипербореями, археология молчит",
      "source_1_claim": "AUTHOR_CANON: связь с гипербореями",
      "source_2_claim": "EXTERNAL_SOURCE: нет данных",
      "resolution": "DIFFERENT_PERSPECTIVES"
    }
  ],
  "uncertainty": {
    "has_unknowns": true,
    "unknown_aspects": ["гипотезы требуют проверки"],
    "confidence_breakdown": [...]
  },
  "relations": [...],
  "search_suggestions": [...]
}
```

---

## 6. Changes Made

| Файл | Тип | Описание |
|------|-----|----------|
| `core/CORE/knowledge_card/__init__.py` | NEW | Package init + exports |
| `core/CORE/knowledge_card/models.py` | NEW | Pydantic models (5 классов) |
| `core/CORE/knowledge_card/builder.py` | NEW | Aggregation logic (613 строк) |
| `runtime/core/routes/knowledge_cards.py` | NEW | API routes |
| `runtime/core/main.py` | EDITED | Регистрация роута |
| `runtime/tests/test_knowledge_cards.py` | NEW | 34 теста |
| `docs/KNOWLEDGE_CARDS_FORENSIC_AUDIT.md` | NEW | Forensic audit |

**Не менялось:**
- ❌ provenance system
- ❌ WorldModel / WORLD_MODEL.json
- ❌ ARCHAEOLOGY.json / CROSS_REFERENCES.json / ACADEMIC_CONFIRMATIONS.json
- ❌ BookRetriever / retrieval logic
- ❌ Temporal engine / Graph engine

---

## 7. Tests

### Новый файл: tests/test_knowledge_cards.py — 34 теста

| Test Class | Тестов | Что проверяет |
|-----------|--------|---------------|
| TestModels | 7 | Pydantic валидация, provenance инварианты |
| TestEntityResolution | 4 | Lookup across systems |
| TestAggregation | 4 | Сбор из 4 источников |
| TestProvenance | 6 | Provenance per-claim, chunk_id |
| TestContradictions | 3 | Detection, no auto-resolution |
| TestUncertainty | 2 | Flag structure |
| TestBookIntegration | 2 | Real RAG integration |
| TestRegression | 3 | Existing functionality intact |
| TestAPIContract | 2 | JSON serialization |

### Regression

```
test_knowledge_cards.py:           34 passed
test_book_intelligence.py:         28 passed
test_provenance_completion.py:     20 passed
test_provenance.py:                55 passed
test_data_discipline.py:           25 passed
test_temporal_model.py:            86 passed
test_narrative_world_model.py:     26 passed
test_m8_1_present_anchor.py:       29 passed
test_m8_future_extrapolation.py:   13 passed
────────────────────────────────────────────
ИТОГО:                            316 passed, 0 failed
```

---

## 8. Known Limitations

| Limitation | Причина | Решение |
|------------|---------|---------|
| Entity resolution только по name | Упрощение для MVP | Expand при необходимости |
| Две параллельные ChromaDB коллекции | Отдельный milestone | Консолидация |
| Contradiction detection эвристический | Нет ML для semantic conflict | Улучшить при необходимости |
| No cross-entity alias resolution | Out of scope | Не делать autonomous resolver |

---

## 9. What Was Intentionally NOT Implemented

- ❌ Автоматическое разрешение противоречий
- ❌ Автоматическое объединение сущностей по похожему имени
- ❌ Nation-first taxonomy (Sumerians → X, etc.)
- ❌ New graph engine или temporal engine
- ❌ Truth entity или KnowledgeArtifact
- ❌ Frontend redesign
- ❌ Studio → Production миграция

---

**STOP. Milestone C завершён. Следующий: B (по запросу владельца).**
