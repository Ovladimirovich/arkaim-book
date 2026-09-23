# 09_BOOK_OS_SPRINT_PLAN.md — ПЛАН РАЗРАБОТКИ BOOK OS (ВЫПОЛНЕН)

> **Все 8 спринтов завершены.** BOOK OS реализована и интегрирована.
> Текущая разработка — Аватар (Pulse/Voice/Presence). См. `PLAN_DIGITAL_AVATAR.md`.

## Обзор

Реализация BOOK OS (08_BOOK_OS_ARCHITECTURE.md) в 8 спринтов. Каждый спринт — самодостаточный шаг: код + тесты + документация.

```
Спринт 1: Data Models      — фундамент типов ✅
Спринт 2: Source Store     — неизменяемое хранилище ✅
Спринт 3: Knowledge Graph  — граф сущностей + факты + связи ✅
Спринт 4: Provenance Layer — трассировка происхождения ✅
Спринт 5: BookOSProvider   — публичный контракт ✅
Спринт 6: Ingestion Pipeline — приём документов ✅
Спринт 7: Index Engine     — ChromaDB + provenance ✅
Спринт 8: Migration        — перенос существующих данных ✅
```

---

## Спринт 1: Data Models

**Цель:** pydantic-модели всех Core Entities + SCHEMAS/*.schema.json

**Новые файлы:**
```
SCHEMAS/
├── DOCUMENT.schema.json
├── ENTITY.schema.json
├── FACT.schema.json
├── RELATIONSHIP.schema.json
├── PROVENANCE.schema.json
└── CHUNK.schema.json

CORE/schemas/                 # (каталог)
├── __init__.py
├── document.py               # Document модель
├── entity.py                 # Entity модель
├── fact.py                   # Fact модель
├── relationship.py           # Relationship модель
├── provenance.py             # Provenance модель
└── chunk.py                  # Chunk модель
```

**Ключевые решения:**
- Все модели — `pydantic.BaseModel`
- Entity.type — `Literal` с полным списком типов
- Provenance — отдельная модель, не поле
- Relationship.type — `Literal` с полным списком типов
- Каждая модель имеет `to_dict()` и `from_dict()` для JSON-сериализации

**Тесты:** `TESTS/test_schemas.py` — валидация каждой модели, граничные случаи

**Зависимости:** нет

---

## Спринт 2: Source Store

**Цель:** неизменяемое хранилище первичных документов

**Новые файлы:**
```
CORE/book_os/
├── __init__.py
├── source_store.py           # SourceStore класс
└── exceptions.py             # DocumentNotFoundError, и т.д.
```

**SourceStore:**
```python
class SourceStore:
    def add(self, path: Path, doc_type: str) -> Document
    def get(self, doc_id: str) -> Document
    def get_by_title(self, title: str) -> Optional[Document]
    def list(self, doc_type: Optional[str] = None) -> List[Document]
    def delete(self, doc_id: str) -> None
```

**Хранение:**
- Файлы на диске: `OS_DATA/documents/{doc_id}.json`
- Метаданные отдельно от контента
- SHA256 хеш содержимого для проверки целостности
- Внутренняя директория `OS_DATA/` — скрыта от пользователя, не коммитится

**Тесты:** `TESTS/test_source_store.py` — add/get/delete/list, хеши, дубликаты

**Зависимости:** Спринт 1 (Document модель)

---

## Спринт 3: Knowledge Graph

**Цель:** граф сущностей, фактов и связей

**Новые файлы:**
```
CORE/os/
├── entity_store.py           # EntityStore
├── fact_store.py             # FactStore
└── relationship_store.py     # RelationshipStore
```

**EntityStore:**
```python
class EntityStore:
    def add(self, entity: Entity) -> Entity
    def get(self, name: str) -> Entity              # с разрешением алиасов
    def get_by_id(self, entity_id: str) -> Entity
    def search(self, query: str, type: Optional[str] = None) -> List[Entity]
    def resolve_alias(self, alias: str) -> str      # обёртка над NameResolver
    def list(self) -> List[Entity]
```

**FactStore:**
```python
class FactStore:
    def add(self, fact: Fact) -> Fact
    def get(self, fact_id: str) -> Fact
    def get_by_entity(self, entity_id: str, provenance: Optional[str] = None) -> List[Fact]
    def get_by_document(self, doc_id: str) -> List[Fact]
    def search(self, statement: str) -> List[Fact]
```

**RelationshipStore:**
```python
class RelationshipStore:
    def add(self, rel: Relationship) -> Relationship
    def get_by_entity(self, entity_id: str, rel_type: Optional[str] = None) -> List[Relationship]
    def get_between(self, source_id: str, target_id: str) -> Optional[Relationship]
    def get_by_document(self, doc_id: str) -> List[Relationship]
```

**Хранение:** JSON-файлы в `OS_DATA/graph/{entities,facts,relationships}.json`

**Интеграция:** EntityStore оборачивает существующий `NameResolver`

**Тесты:** `TESTS/test_knowledge_graph.py`

**Зависимости:** Спринт 1 (Entity, Fact, Relationship модели)

---

## Спринт 4: Provenance Layer

**Цель:** трассировка происхождения каждого факта

**Новые файлы:**
```
CORE/os/
├── provenance_tracker.py     # ProvenanceTracker
└── provenance_validator.py   # ProvenanceValidator
```

**ProvenanceTracker:**
```python
class ProvenanceTracker:
    def register(self, fact_id: str, provenance: Provenance) -> None
    def get(self, fact_id: str) -> Provenance
    def get_by_document(self, doc_id: str) -> List[Provenance]
    def get_by_entity(self, entity_id: str) -> List[Provenance]
    def verify(self, fact_id: str) -> bool           # проверка цепочки
    def get_chain(self, fact_id: str) -> List[Provenance]  # полная цепочка
```

**ProvenanceValidator:**
```python
class ProvenanceValidator:
    def can_be_direct(self, statement: str, document: Document) -> bool
    def can_be_derived(self, source_facts: List[Fact], derived: Fact) -> bool
    def check_conflicts(self, fact: Fact, existing: List[Fact]) -> List[Conflict]
```

**Хранение:** JSON-файл `OS_DATA/provenance/registry.json`

**Тесты:** `TESTS/test_provenance.py`

**Зависимости:** Спринт 1 (Provenance модель), Спринт 3 (FactStore)

---

## Спринт 5: BookOSProvider

**Цель:** реализация публичного контракта (ABC из архитектуры)

**Новые файлы:**
```
CORE/os/
├── provider.py               # BookOSProvider (реализация ABC)
└── context.py                # TraceId, контекст вызова
```

**BookOSProvider** реализует все 11 методов из контракта:
- `get_document` → SourceStore.get
- `list_documents` → SourceStore.list
- `get_entity` → EntityStore.get + NameResolver
- `search_entities` → EntityStore.search
- `get_facts` → FactStore.get_by_entity + фильтр
- `get_relationships` → RelationshipStore.get_by_entity
- `search_chunks` → IndexEngine.search (Спринт 7)
- `get_provenance` → ProvenanceTracker.get
- `ingest_document` → Ingestion Pipeline (Спринт 6)
- `resolve_name` → EntityStore.resolve_alias
- `get_stats` → агрегация всех сторах

**Трассировка:**
```python
@contextmanager
def trace(operation: str) -> Generator[TraceId, None, None]:
    trace_id = uuid4().hex[:16]
    yield trace_id
```

**Тесты:** `TESTS/test_provider.py` — 100% покрытие каждого метода (с mocks)

**Зависимости:** Спринты 1–4

---

## Спринт 6: Ingestion Pipeline

**Цель:** приём документа → валидация → чанкинг → извлечение → индексация

**Новые файлы:**
```
CORE/os/
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py       # IngestionOrchestrator
│   ├── validators.py         # DocumentValidator
│   ├── extractors.py         # EntityExtractor, FactExtractor, RelationshipExtractor
│   └── conflict_resolver.py  # ConflictResolver
```

**IngestionOrchestrator:**
```python
class IngestionOrchestrator:
    def ingest(self, path: Path, doc_type: str) -> IngestionResult:
        # 1. Валидация документа (JSON Schema)
        # 2. Чанкинг (существующий SemanticChunker)
        # 3. Извлечение Entity (существующий GenomeEnricher)
        # 4. Извлечение Fact (новый Extractor)
        # 5. Извлечение Relationship (новый Extractor)
        # 6. Проверка конфликтов
        # 7. Сохранение в Source Store + Knowledge Graph
        # 8. Индексация в ChromaDB
        # 9. Регистрация provenance
```

**Повторное использование:**
- `SemanticChunker` — без изменений
- `GenomeEnricher` — без изменений
- `TextCleaner` — вызывается перед чанкингом

**Новое:**
- `EntityExtractor` — извлекает Entity из enriched chunk
- `FactExtractor` — формирует Fact из chunk + metadata
- `RelationshipExtractor` — извлекает связи между Entity
- `ConflictResolver` — сверяет новые факты с существующими

**Тесты:** `TESTS/test_ingestion.py` — полный цикл ингеста

**Зависимости:** Спринты 1–4

---

## Спринт 7: Index Engine Upgrade

**Цель:** ChromaDB с фильтрацией по provenance + entity

**Новые/изменённые файлы:**
```
CORE/os/
└── index_engine.py           # IndexEngine (обёртка над ChromaDB)

CORE/intelligence/
└── retriever.py              # ДОБАВЛЯЕТСЯ: фильтр по provenance
```

**IndexEngine:**
```python
class IndexEngine:
    def search(self, query: str,
               entity_ids: Optional[List[str]] = None,
               provenance: Optional[str] = None,
               doc_ids: Optional[List[str]] = None,
               n_results: int = 5) -> List[Chunk]

    def index(self, chunks: List[Chunk]) -> None       # batch index
    def clear(self) -> None
    def get_stats(self) -> Dict
```

**Изменения в ChromaDB metadata:**
- Добавляется `provenance` в metadata каждого чанка
- Добавляется `entity_ids` — список Entity, упомянутых в чанке
- Добавляется `doc_id` — привязка к документу

**Тесты:** `TESTS/test_index_engine.py`

**Зависимости:** Спринты 1, 5

---

## Спринт 8: Migration

**Цель:** перенос существующих данных из KNOWLEDGE/*.json в OS

**Новый файл:**
```
scripts/migrate_to_os.py
```

**Миграция:**
```
1. KNOWLEDGE/BOOK_DOCUMENT.json       → SourceStore (Document)
2. KNOWLEDGE/enriched_chunks.json     → Chunk + ChromaDB
3. KNOWLEDGE/BOOK_PROFILE.json        → Entity + Fact
4. KNOWLEDGE/character_deep_profiles.json → Entity + Fact
5. KNOWLEDGE/civilization_profiles.json   → Entity + Fact
6. KNOWLEDGE/CHARACTERS.json          → Entity + Fact
7. KNOWLEDGE/SYMBOLS.json             → Entity
8. KNOWLEDGE/PHILOSOPHY.json          → Entity + Fact
9. KNOWLEDGE/VALUES.json              → Entity + Fact
10. KNOWLEDGE/PLOT.json               → Fact + Relationship
11. KNOWLEDGE/AUTHOR_INTENT.json      → Fact
12. GENOME/GENOME_v1.0.0.json         → Entity + Fact + Relationship
13. WORLD/entities.json               → Entity
14. WORLD/relations.json              → Relationship
15. WORLD/quotes.json                 → Fact (provenance=source)
```

**Проверка:**
- После миграции: `provider.get_stats()` показывает корректное количество
- Выборочная проверка 5 entity, 5 fact, 5 relationship
- Сравнение количества чанков в ChromaDB (было 841 → должно совпасть)

**Зависимости:** Спринты 1–7

---

## Сводная таблица

| Спринт | Файлы | Тесты | Зависит от |
|--------|-------|-------|------------|
| 1 Data Models | 6 models + 5 schemas | test_schemas.py | — |
| 2 Source Store | 2 файла | test_source_store.py | 1 |
| 3 Knowledge Graph | 3 файла | test_knowledge_graph.py | 1 |
| 4 Provenance Layer | 2 файла | test_provenance.py | 1, 3 |
| 5 BookOSProvider | 2 файла | test_provider.py | 1–4 |
| 6 Ingestion Pipeline | 5 файлов | test_ingestion.py | 1–4 |
| 7 Index Engine | 1 новый + правка retriever | test_index_engine.py | 1, 5 |
| 8 Migration | 1 скрипт | ручная проверка | 1–7 |

---

## Оценка

| Спринт | Примерное время |
|--------|----------------|
| 1 Data Models | 1 день |
| 2 Source Store | 1 день |
| 3 Knowledge Graph | 2 дня |
| 4 Provenance Layer | 1 день |
| 5 BookOSProvider | 2 дня |
| 6 Ingestion Pipeline | 3 дня |
| 7 Index Engine | 1 день |
| 8 Migration | 2 дня |

**Итого:** ~13 рабочих дней при последовательном выполнении. Спринты 2–4 можно делать параллельно (независимые хранилища).

---

*Утверждение плана → начало Спринта 1.*
