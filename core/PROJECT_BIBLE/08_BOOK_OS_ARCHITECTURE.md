# 08_BOOK_OS_ARCHITECTURE.md — BOOK OS

> **Фаза 2 (OS) выполнена.** OS владеет данными, Pulse/Аватар — внешний клиент.
> Документ сохранён для истории. Актуальная архитектура — в `ARCHITECTURE.md` корня проекта.

## 1. Назначение

BOOK OS — платформа между книгой и любым будущим AI. Единственная ответственность: хранить, индексировать и трассировать происхождение знаний о книге.

**Проблема:** LLM-модели меняются, знания о книге — нет. Каждая новая модель требует перепроверки фактов. Каждый новый интерфейс (Telegram, Web, API) дублирует логику поиска.

**Решение:** Операционная система знаний, которая:
- Принимает первичные документы (книга, сценарий, интервью) — **один раз**
- Строит граф сущностей и фактов — **автоматически**
- Трассирует происхождение каждого утверждения — **всегда**
- Предоставляет единый контракт для любого AI/интерфейса — **независимо**

BOOK OS ничего не знает об AI. AI — внешний клиент OS.

---

## 2. Основные подсистемы

### 2.1 Source Store
Неизменяемое хранилище первичных документов:
- КНИГА.md (единственный primary source)
- Сценарий, синопсис, интервью, авторские заметки (secondary sources)
- Каждый документ имеет ID, версию, временную метку импорта
- Документы не редактируются после импорта — только новая версия

### 2.2 Knowledge Graph
Граф сущностей и связей между ними:
- Entity — персонаж, локация, концепция, символ, артефакт
- Relationship — связь между Entity (тип, направление, источник)
- Fact — атомарное утверждение, привязанное к Document
- Provenance — метка происхождения для каждого Fact

### 2.3 Index Engine
Поиск по тексту, сущностям, связям:
- Векторный поиск (ChromaDB) — по тексту чанков
- Ключевой поиск — по имени Entity, Relationship
- Фильтрация по Provenance, Document, Entity

### 2.4 Provenance Layer
Трассировка происхождения каждого утверждения:

| Метка | Значение | Пример |
|-------|----------|--------|
| `source` | Прямая цитата из документа | «Велик прибыл из Океании» — строка 142 книги |
| `derived` | Вывод из source-фактов | «Гиперборея старше Аркаима» — логический вывод |
| `interpretation` | Авторская интерпретация системы | «Пещера — метафора пробуждения» |
| `external` | Факт из внешнего источника | Исторические сведения об Аркаиме |
| `hypothesis` | Предположение без подтверждения | «Учитель мог быть атлантом» |

Система никогда не выдаёт `interpretation` или `hypothesis` как `source`.

### 2.5 Ingestion Pipeline
Приём новых документов без поломки схемы:
- Валидация формата (JSON Schema)
- Чанкинг (существующий SemanticChunker)
- Извлечение Entity, Fact, Relationship
- Индексация в Knowledge Graph + ChromaDB
- Проверка конфликтов с существующими фактами

---

## 3. Модель данных

### Core Entities

```
┌──────────────┐     ┌──────────────────┐
│  Document    │────→│     Chunk        │
│  ─────────── │     │  ───────────────  │
│  id: UUID    │     │  id: UUID        │
│  title: str  │     │  text: str       │
│  type: enum  │     │  position: int   │
│  version: str│     │  doc_id: UUID    │
│  imported_at │     │  metadata: dict  │
│  hash: str   │     └────────┬─────────┘
└──────────────┘              │
                              │ references
                              ▼
┌──────────────┐     ┌──────────────────┐
│   Entity     │     │      Fact        │
│  ─────────── │     │  ───────────────  │
│  id: UUID    │←────│  id: UUID        │
│  name: str   │     │  statement: str  │
│  type: enum  │     │  entity_id: UUID │
│  aliases: [] │     │  doc_id: UUID    │
│  canonical:  │     │  provenance: enum│
│    str       │     │  confidence: flt │
└──────┬───────┘     └──────────────────┘
       │
       │ has
       ▼
┌──────────────────┐
│  Relationship    │
│  ───────────────  │
│  id: UUID        │
│  source_id: UUID │
│  target_id: UUID │
│  type: enum      │
│  doc_id: UUID    │
│  weight: float   │
└──────────────────┘
```

### 3.1 Document
```yaml
Document:
  id:          UUID          # уникальный идентификатор
  title:       str           # название документа
  type:        enum          # primary_source | secondary_source | external
  version:     str           # семантическая версия
  imported_at: datetime      # дата импорта
  hash:        str           # SHA256 содержимого
  path:        str           # путь к файлу
```

### 3.2 Chunk
```yaml
Chunk:
  id:          UUID          # уникальный идентификатор
  doc_id:      UUID          # родительский документ
  text:        str           # текст фрагмента
  position:    int           # порядковый номер в документе
  metadata:    dict          # chapter_id, paragraph_id, themes, characters, symbols
```

Существующий enriched_chunk с полем `metadata` (themes, characters, symbols, conflicts, values).

### 3.3 Entity
```yaml
Entity:
  id:          UUID
  name:        str           # каноническое имя
  type:        enum          # person | location | civilization | concept |
                             # symbol | artifact | era | event | organization
  aliases:     [str]         # альтернативные имена
  description: str           # краткое описание
  first_seen:  UUID          # Document ID первого упоминания
```

### 3.4 Fact
```yaml
Fact:
  id:          UUID
  statement:   str           # атомарное утверждение
  entity_id:   UUID          # к какой Entity относится
  doc_id:      UUID          # из какого документа
  chunk_id:    UUID          # из какого чанка (если есть)
  provenance:  enum          # source | derived | interpretation | external | hypothesis
  confidence:  float         # 0.0–1.0 (назначается Ingestion Pipeline)
  created_at:  datetime
```

### 3.5 Relationship
```yaml
Relationship:
  id:          UUID
  source_id:   UUID          # Entity ID (от кого)
  target_id:   UUID          # Entity ID (к кому)
  type:        enum          # teacher_student | friend | belongs_to |
                             # located_in | symbolizes | opposes |
                             # predecessor_of | created_by
  doc_id:      UUID          # из какого документа
  weight:      float         # сила связи 0.0–1.0
```

### 3.6 Provenance
```yaml
Provenance:
  type:        enum          # source | derived | interpretation | external | hypothesis
  label:       str           # человекочитаемое описание
  doc_id:      UUID          # источник (для source)
  confidence:  float         # для derived/hypothesis
```

## 4. Публичный контракт (Provider Interface)

Внутренний Python-интерфейс. Не HTTP. Интерфейсы сменные — HTTP-слой надстраивается отдельно.

```python
class BookOSProvider(ABC):
    """Единый контракт для любого клиента OS."""

    @abstractmethod
    def get_document(self, doc_id: str) -> Document:
        """Вернуть документ по ID."""
        ...

    @abstractmethod
    def list_documents(self, doc_type: Optional[str] = None) -> List[Document]:
        """Список всех документов (с фильтром по типу)."""
        ...

    @abstractmethod
    def get_entity(self, name: str) -> Entity:
        """Вернуть entity по каноническому имени (с разрешением алиасов)."""
        ...

    @abstractmethod
    def search_entities(self, query: str, entity_type: Optional[str] = None) -> List[Entity]:
        """Поиск entity по имени/алиасу."""
        ...

    @abstractmethod
    def get_facts(self, entity_id: str, provenance: Optional[str] = None) -> List[Fact]:
        """Все факты о entity (с фильтром по provenance)."""
        ...

    @abstractmethod
    def get_relationships(self, entity_id: str,
                          rel_type: Optional[str] = None) -> List[Relationship]:
        """Все связи entity (с фильтром по типу)."""
        ...

    @abstractmethod
    def search_chunks(self, query: str,
                      filters: Optional[Dict] = None,
                      n_results: int = 5) -> List[Chunk]:
        """Векторный поиск по тексту чанков."""
        ...

    @abstractmethod
    def get_provenance(self, fact_id: str) -> Provenance:
        """Вернуть происхождение факта."""
        ...

    @abstractmethod
    def ingest_document(self, path: str) -> IngestionResult:
        """Импортировать документ: валидация → чанкинг → извлечение → индексация."""
        ...

    @abstractmethod
    def resolve_name(self, name: str) -> str:
        """Привести любое имя/алиас к канонической форме."""
        ...

    @abstractmethod
    def get_stats(self) -> Dict:
        """Статистика: количество документов, entity, fact, relationship, chunk."""
        ...
```

### Форматы входа/выхода

Все методы принимают/возвращают pydantic-модели, определённые в `CORE/schemas/`. Никаких сырых dict.

### Ошибки

Все ошибки — типизированные исключения:
- `DocumentNotFoundError`
- `EntityNotFoundError`
- `IngestionValidationError`
- `ProvenanceConflictError`
- `OSInternalError`

### Трассировка

Каждый вызов возвращает `TraceId` в заголовке ответа (для HTTP) или через contextvars (для прямых вызовов).

---

## 5. Отношение к существующему коду

### 5.1 Преемственность

| Существующий компонент | Статус | Роль в BOOK OS |
|------------------------|--------|----------------|
| KnowledgeKernel | Эволюционирует | Станет клиентом OS. Вместо прямых вызовов к KnowlegeKernel → вызовы через BookOSProvider. |
| KNOWLEDGE/*.json | Миграция | Данные переезжают в Source Store + Knowledge Graph. JSON-файлы остаются как export/cache. |
| ChromaDB (841 chunk) | Сохраняется | Остаётся как Index Engine. Добавляется provenance в metadata. |
| NameResolver | Сохраняется | Подсистема Entity Resolution внутри OS. |
| SemanticChunker | Сохраняется | Часть Ingestion Pipeline. |
| GenomeEnricher | Сохраняется | Часть Ingestion Pipeline (извлечение Entity, Fact, Relationship). |
| BookRetriever | Заменяется | Его логика переходит в OS Provider. Старый класс — deprecated. |
| TextCleaner | Сохраняется | Предварительный этап Ingestion Pipeline. |
| LLM | Выносится | LLM — внешний клиент OS. OS ничего не знает об LLM. |
| Generator | Выносится | Становится внешним сервисом, использующим OS Provider. |
| Keeper/Herald/Diplomat | Переписывается | Агенты становятся внешними приложениями, подключёнными к OS. |

### 5.2 Схема перехода

```
Фаза 1 (сейчас):    Kernel делает всё (поиск, enrich, ответ)
Фаза 2 (OS):        OS владеет данными, внешний код — только клиент
Фаза 3 (стабильно): OS frozen, все новые возможности — снаружи
```

### 5.3 Границы OS

BOOK OS НЕ делает:
- Не генерирует тексты
- Не отвечает на вопросы
- Не управляет диалогом
- Не обращается к LLM
- Не классифицирует запросы
- Не валидирует ответы

BOOK OS ТОЛЬКО:
- Хранит документы
- Строит граф знаний
- Индексирует текст
- Трассирует provenance
- Предоставляет данные по контракту

---

*~~Этот документ фиксирует архитектуру фазы 2. Переход начинается только после утверждения.~~*
*✅ Фаза 2 выполнена. BOOK OS реализована и работает как подсистема данных для Pulse/Аватара.*
