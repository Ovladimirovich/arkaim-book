# GAP-АНАЛИЗ: BOOK OS Roadmap vs текущее состояние

> На основе 09_BOOK_OS_SPRINT_PLAN.md (13 рабочих дней последовательно)

| Спринт | Статус | Что сделано | Что нужно доделать |
|--------|--------|-------------|-------------------|
| **1 — Data Models** | ✅ 90% | `schemas/entity.py`, `fact.py`, `relationship.py`, `chunk.py`, `document.py`, `provenance.py` | JSON Schema (`*.schema.json`) в `SCHEMAS/` |
| **2 — Source Store** | ❌ 0% | `source_store.py` существует | Не реализован как неизменяемое хранилище с версионированием и хэшами |
| **3 — Knowledge Graph** | ✅ 80% | `entity_store.py`, `relationship_store.py`, `fact_store.py`, `graph_engine.py`, `knowledge_graph/populate.py` | `NameResolver` не интегрирован; нет метода `resolve_alias` |
| **4 — Provenance Layer** | ❌ 5% | Поле `provenance` в `Fact` модели | `ProvenanceTracker`, `ProvenanceValidator` не написаны; нет проверки цепочки происхождения |
| **5 — BookOSProvider** | ⚠️ 30% | `book_os/provider.py` — конкретная реализация | Нет `BookOSProvider(ABC)` как единого контракта; нет TraceId; нет изоляции от LLM |
| **6 — Ingestion Pipeline** | ❌ 0% | `book_os/pipeline/` существует (orchestrator, extractors, conflict_resolver) | Не интегрирован с Source Store и Provenance |
| **7 — Index Engine** | ⚠️ 40% | `book_os/index_engine.py` — обёртка ChromaDB | Нет фильтрации по provenance и entity_ids; metadata не обновлена |
| **8 — Migration** | ❌ 0% | `genome/extractor.py` читает KNOWLEDGE/*.json | Нет скрипта переноса KNOWLEDGE → OS хранилища |

### Ключевое нарушение архитектурных принципов

**Принцип 13 (из 15_ARCHITECTURE_PRINCIPLES.md):** *«Агенты, оркестрация, маршрутизация появляются только после BOOK INTELLIGENCE»*
- KeeperAgent напрямую вызывает LLM — это нарушает архитектуру BOOK OS
- LLM должен быть **внешним клиентом** OS, а OS ничего не должна знать об LLM

**Принцип 4:** *«LLM — инструмент, не архитектура»*
- retriever.py жёстко привязан к ChromaDB и llm_client
- При смене провайдера/модели нужно переписывать retriever

### Предложения по дальнейшей разработке (приоритет)

1. **Спринт 2 — Source Store**: неизменяемое хранилище документов с версионированием
2. **Спринт 4 — Provenance Layer**: трассировка происхождения каждого факта
3. **Спринт 5 — BookOSProvider**: единый ABC-контракт + изоляция от LLM
4. **Спринт 7 — Index Engine Upgrade**: фильтрация по provenance + entity_ids
5. **Спринт 6 — Ingestion Pipeline**: полный цикл приёма документов
6. **Спринт 8 — Migration**: перенос KNOWLEDGE/*.json → OS
7. **Отделение агентов от OS**: KeeperAgent → внешний клиент
