# FORENSIC AUDIT — MILESTONE C: Knowledge Cards + Cross-Source

**Дата:** 2026-09-15
**Статус:** READ-ONLY аудит перед реализацией

---

## Простыми словами

Провёл аудит текущего состояния системы перед созданием карточек знаний.
Вывод: **инфраструктура уже готова на 80% — нужно лишь собрать существующие механизмы в единое entity-centric представление.**

---

## 1. Существующая инфраструктура

### Entity System (WorldEngine)

| Компонент | Путь | Статус |
|-----------|------|--------|
| WorldModelExt | `core/CORE/narrative_engine/world_model_ext.py` | 13 категорий, ~406 сущностей |
| RelationGraph | `core/CORE/narrative_engine/relation_models.py` | 287 связей |
| Entity index | `WorldEngine._entity_index` | O(1) lookup по entity_id |
| get_entity() | `world_engine.py:292` | Возвращает dict по ID |
| get_entity_context() | `world_engine.py:296` | Сущность + связи |

**Важно:** `get_entity_context()` уже существует и возвращает структуру:
```python
{"entity": {...}, "relations": {...}, "form_context": {...}}
```

### Provenance System

| Компонент | Путь | Статус |
|-----------|------|--------|
| ProvenanceCategory | `narrative_engine/source_levels.py` | 8 уровней |
| SourceLevel | `narrative_engine/source_levels.py` | 7 весов |
| ProvenanceTag | `narrative_engine/source_levels.py` | Двумерный provenance |
| UncertaintyFlag | `pulse/layers.py:17` | Структурированная неопределённость |
| PulseResponse | `pulse/layers.py:49` | text + source + confidence + provenance + uncertainty |

**Полный набор provenance категорий:**
- `AUTHOR_CANON` (confidence=1.0) — текст книги
- `EXTERNAL_SOURCE` (0.8) — археология, академические данные
- `RECONSTRUCTION` (0.7) — внешний источник + интерпретация
- `HYPOTHESIS` (0.5) — авторская гипотеза
- `DERIVED` (0.7) — логический вывод системы
- `ARTISTIC_MODEL` (0.6) — художественная модель
- `FUTURE_EXTRAPOLATION` (0.4) — будущее Extrapolation
- `UNKNOWN` (0.3) — неопределённо

**Ключевой инвариант:** HYPOTHESIS с confidence=1.0 остаётся HYPOTHESIS.

### Data Sources (готовые к агрегации)

| Источник | Путь | Сущности | Provenance |
|----------|------|----------|------------|
| BOOK (КНИГА.md) | `SOURCE_OF_TRUTH/BOOK/КНИГА.md` | 115K chars, 2566 lines | AUTHOR_CANON |
| Archaeology | `KNOWLEDGE/ARCHAEOLOGY.json` | ~6 sites | EXTERNAL_SOURCE, HYPOTHESIS, RECONSTRUCTION |
| Cross-References | `KNOWLEDGE/CROSS_REFERENCES.json` | ~10 themes | EXTERNAL_SOURCE, DERIVED |
| Academic Confirmations | `KNOWLEDGE/ACADEMIC_CONFIRMATIONS.json` | ~6 categories | EXTERNAL_SOURCE |
| World Model | `WORLD_MODEL/*.json` | 13 категорий, ~406 сущностей | CANON |
| Relation Graph | extracted from WORLD_MODEL | 287 связей | varies |

### Retrieval System (Book Intelligence Pipeline)

| Компонент | Путь | Статус |
|-----------|------|--------|
| SemanticChunker | `intelligence/chunker.py` | 5 стратегий, 824+ chunks |
| BookRetriever | `intelligence/retriever.py` | ChromaDB + fallback |
| IndexEngine | `book_os/index_engine.py` | С фильтрами и retry |
| ChromaDB | `CHROMA_DB/` | 8 HNSW индексов, 2 коллекции |

**Retrieval результат (после D):**
```python
{
    "text": "...",
    "score": 0.85,
    "chunk_id": "chunk_p_0001_xxx",
    "chapter_title": "Часть 0",
    "source": "book",
    "provenance_category": "AUTHOR_CANON",
}
```

### Existing Cross-Reference / Aggregation Mechanisms

| Механизм | Что делает | Можно переиспользовать? |
|----------|-----------|------------------------|
| `WorldEngine.get_entity_context()` | Сущность + связи + визуальная форма | ✅ Частично |
| `ARCHAEOLOGY.json` sites | Археологические данные с provenance | ✅ Прямое использование |
| `CROSS_REFERENCES.json` | Культурные параллели | ✅ Прямое использование |
| `ACADEMIC_CONFIRMATIONS.json` | Академические подтверждения | ✅ Прямое использование |
| `WorldModelExt.search(query)` | Поиск по всем категориям | ✅ Для discovery |
| `RelationGraph.get_entity_context()` | Графовые связи сущности | ✅ Для relations |

**Вывод:** Нет единого entity-centric view, но все источники данных существуют и структурированы правильно.

---

## 2. Gap Analysis

### Что нужно создать

1. **KnowledgeCard model** — Pydantic schema для entity-centric карточки
2. **KnowledgeCardBuilder** — агрегатор из 5 источников
3. **API route** — `GET /knowledge/cards/{entity_id}`
4. **Tests** — агрегация, provenance, contradictions, book integration

### Что НЕ нужно создавать

- ❌ New relation types (ECHOES, CARRIES и т.д. уже есть)
- ❌ New provenance categories (8 уровней уже есть)
- ❌ New uncertainty mechanism (UncertaintyFlag уже есть)
- ❌ New graph engine (RelationGraph уже работает)
- ❌ New temporal engine (TemporalLegacy уже работает)
- ❌ New embedding model (already configured)

---

## 3. Reuse Map

| Требование | Существующий механизм | Action |
|------------|----------------------|--------|
| Entity lookup | `WorldEngine.get_entity(entity_id)` | Вызывать напрямую |
| Entity relations | `RelationGraph.get_entity_context(entity_id)` | Вызывать напрямую |
| Book claims | `BookRetriever.search(entity_name)` | Использовать с chunk_id tracking |
| Archaeology data | `KNOWLEDGE/ARCHAEOLOGY.json` | Парсить sites по name |
| Cross-references | `KNOWLEDGE/CROSS_REFERENCES.json` | Фильтровать по theme |
| Academic data | `KNOWLEDGE/ACADEMIC_CONFIRMATIONS.json` | Фильтровать по category |
| Provenance tags | `ProvenanceTag`, `_canon_tag()` | Переиспользовать |
| Uncertainty | `UncertaintyFlag` | Переиспользовать |
| Entity aliases | `CharacterPresence.relations` | Использовать где есть |

---

## 4. Architecture Decision

**Проблема:** Мир Entity в WorldEngine — это 406 сущностей из WORLD_MODEL/*.json. Но книга и археология имеют свои сущности (Аркаим, Гиперборея, Синташта, и т.д.), которые могут пересекаться или дополнять WorldModel.

**Решение:** KnowledgeCard — read-only view поверх существующих данных. Не создаёт новых сущностей, не модифицирует WorldModel. Агрегирует из:

1. **EntityIndex** (WorldEngine) — каноническая сущность из модели мира
2. **BookRetriever** — книжные утверждения через RAG
3. **ARCHAEOLOGY.json** — археологические данные
4. **CROSS_REFERENCES.json** — культурные параллели
5. **ACADEMIC_CONFIRMATIONS.json** — академические подтверждения

**API pattern:** Использовать существующий `GET /world/entity/{entity_id}` как основу, добавить новый `GET /knowledge/cards/{entity_id}` как entity-centric enriched view.

---

## 5. Entity Name Resolution Strategy

**Не делать:** автономный entity-resolution engine (слишком сложно, неоднозначно).

**Делать:**
1. Сначала ищем в WorldEngine по ID
2. Если не найдено — ищем по имени в WorldEngine.search()
3. Если не найдено — ищем в ARCHAEOLOGY.json по name
4. Если найдено несколько — UNKNOWN/POSSIBLE_MATCH

**Никогда не объединять автоматически.**

---

## 6. Test Coverage Plan

| Тест | Проверка |
|------|---------|
| Card aggregation | Сбор из 5 источников |
| Provenance separation | AUTHOR_CANON ≠ HYPOTHESIS |
| Book chunk tracking | chunk_id → source location |
| Contradictions | conflict между источником и книгой |
| Missing entity | 404 для несуществующего entity |
| Empty card | entity без данных = пустая карточка |
| Alias resolution | правильное сопоставление по имени |
| Regression | все существующие тесты проходят |

---

## 7. Files to Create/Modify

| Файл | Тип | Изменение |
|------|-----|-----------|
| `core/CORE/knowledge_card/__init__.py` | NEW | Package init |
| `core/CORE/knowledge_card/models.py` | NEW | Pydantic schema |
| `core/CORE/knowledge_card/builder.py` | NEW | Aggregation logic |
| `runtime/core/routes/knowledge_cards.py` | NEW | API route |
| `runtime/tests/test_knowledge_cards.py` | NEW | Tests |
| `docs/TRUTH_CORE_FORENSIC_AUDIT.md` | EXISTING | Already done |

**Не менять:**
- ❌ provenance system
- ❌ WorldModel / WORLD_MODEL.json
- ❌ ARCHAEOLOGY.json / CROSS_REFERENCES.json
- ❌ BookRetriever / retrieval logic
- ❌ Temporal engine
- ❌ Graph engine

---

**STOP. Audit complete. Proceeding to implementation.**
