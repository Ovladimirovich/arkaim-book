# M0 — ARCHITECTURE AUDIT
**Проект:** Наследие Аркаима — Цифровое сознание книги  
**Дата:** 2025-07  
**Статус:** АУДИТ ЗАВЕРШЁН · БЕЗ ИЗМЕНЕНИЙ КОДА  
**Цель M0:** Точная карта существующей архитектуры перед переходом к новой модели мира

---

## 1. CURRENT ARCHITECTURE

### 1.1 Общая топология

```
Читатель
  └─→ Next.js 16 (:3000) ──┐
                            │
                            ▼
                      FastAPI (:8642)
                            │
        ┌───────────────────┼───────────────────────┐
        │                   │                       │
   BookPulse           Orchestrator            ReaderMemory
   (live ядро)         (LLM-микрофон)         (SQLite readers.db)
        │                   │
   ┌────┴────┐        ProviderChain
   │ Слои    │         GigaChat → OpenRouter
   │ Pulse   │
   └────┬────┘
        │
   KnowledgeGraph (BFS, shortest path)
        │
   WorldEngine (406 сущностей, 287 связей)
        │
   ChromaDB (arkaim_book — RAG chunks)
```

### 1.2 Стек технологий

| Слой | Технология | Версия |
|------|-----------|--------|
| Frontend | Next.js + React | 16.2.10 / 19.2.4 |
| Frontend UI | Ant Design + Tailwind | 6.5.0 / 4.x |
| Backend | FastAPI + Uvicorn | 0.136+ / 0.48+ |
| Ядро знаний | Python | 3.14+ |
| БД читателей | SQLite (aiosqlite) | WAL режим |
| Векторный поиск | ChromaDB | arkaim_book collection |
| LLM адаптеры | GigaChat, OpenRouter | через ProviderRegistry |
| Визуализация | ComfyUI (DirectML) | 0.3.70, VRAM 1GB |
| Observability | aethon.xray (vendored) | in-repo |
| Линтер | ruff / eslint | line-length 160 |
| Тесты | pytest / vitest | 349+ BE / 30 FE |

### 1.3 Размеры кодовой базы

| Модуль | Файлов | Примечание |
|--------|--------|-----------|
| `runtime/` (весь, с .venv) | ~41 600 | .venv доминирует |
| `runtime/core/` (ядро runtime) | ~200 | FastAPI, DI, routes, auth, memory |
| `core/CORE/` (pulse, KG, narrative) | 612 | Python ядро знаний |
| `arkaim-web/src/` (фронтенд) | 182 | Next.js App Router, FSD |
| Тесты backend | 51 | pytest |
| Тесты frontend | 12 | vitest + Playwright |
| KNOWLEDGE/*.json | 47 | JSON-базы знаний |
| WORLD_MODEL/*.json | 9 | Категории мира |
| SOURCE_OF_TRUTH/ | 4 | Авторские источники |

---

## 2. EXISTING COMPONENTS

### 2.1 BookPulse — живое ядро

**Файл:** `core/CORE/pulse/pulse.py` (410 строк)

```
BookPulse
├── genome: dict              # загруженный GENOME_v{version}.json
├── genome_hash: str          # MD5 для детектирования изменений
├── layers: dict[str, BaseLayer]   # 10+ слоёв
├── state: PulseState         # genome_version, total_responses, beats_count
├── _evolution: EvolutionTracker
└── _retriever: BookRetriever # RAG-поиск
```

**Методы:** `load()`, `listen(query)`, `build_context()`, `get_beat()`

### 2.2 Слои Pulse (layers.py — 1120 строк)

| Слой | Тип | Класс | O(1) индекс | RAG |
|------|-----|-------|-------------|-----|
| KnowledgeLayer | Mutable | `KnowledgeLayer` | ✅ character_index, theme_index, symbol_index, conflict_index | ✅ set_retriever |
| ExpansionLayer | Mutable | `ExpansionLayer` | ✅ | ❌ |
| MeaningLayer | Mutable | `MeaningLayer` | ❌ | ❌ |
| IdentityLayer | Immutable | `IdentityLayer` | ❌ | ❌ |
| MissionLayer | Immutable | `MissionLayer` | ❌ | ❌ |
| WorldEngineLayer | Mutable | `WorldEngineLayer` | ❌ | ❌ |
| WorldEngineLayerV2 | Mutable | `WorldEngineLayerV2` | ❌ | ❌ (делегрует WorldEngine) |
| VisualStyleLayer | Mutable | `VisualStyleLayer` | ❌ | ❌ |
| SceneLayer | Mutable | `SceneLayer` | ❌ | ❌ |
| NarrativeArcLayer | Mutable | `NarrativeArcLayer` | ❌ | ❌ |
| ScreenplayLayer | Mutable | `ScreenplayLayer` | ❌ | ❌ |

**Ответы без LLM:** KnowledgeLayer отвечает на фактические вопросы (персонажи, темы, символы, конфликты, миры) через O(1) индексы + RAG. Confidence: 0.8–0.95.

### 2.3 BookVoice — LLM-микрофон

**Файл:** `core/CORE/pulse/voice.py` (358 строк)

```
BookVoice
├── _pulse: BookPulse
├── _reader_pulse: ReaderAwarePulse
├── _llm: LLMClient | None       # GigaChat / OpenRouter
└── _memory: ReaderMemoryStore
```

**Протокол:**
1. `_detect_mood(query)` → joy / curiosity / sadness / doubt / deep / neutral
2. `_reader_pulse.listen(query, reader_id)` → `(PulseResponse, reader_ctx)`
3. Если Pulse знает → LLM формулирует ответ (или возвращает raw)
4. `IdentityLayer.validate_detail(llm_text)` → если failed → вернуть pulse.text или "не могу ответить"
5. Запись в ReaderMemory

** Utterance **数据结构:** text, source, pulse_response, llm_used, llm_model, reader_topic, reader_depth, mood

### 2.4 ReaderAwarePulse

**Файл:** `core/CORE/pulse/reader_aware.py` (111 строк)

Обрабатывает "расскажи подробнее" → находит последнюю тему читателя → обогащает запрос → повышает confidence на +0.1.

### 2.5 EvolutionTracker

**Файл:** `core/CORE/pulse/evolution.py` (233 строки)

```
EvolutionTracker
├── IMMUTABLE_LAYERS = {"identity", "mission"}
├── MUTABLE_LAYERS = {"knowledge", "meaning"}
├── _history: list[GenomeSnapshot]
└── GENOME_BACKUP_DIR = core/GENOME/history/
```

**Методы:** `snapshot()`, `diff()`, `auto_fill_visuals()`, `get_version()`, `list_versions()`

**GenomeDiff:** new_characters, removed_characters, new_themes, new_symbols, new_world_entities, identity_changed, meaning_changed

### 2.6 World Engine (v2)

**Файл:** `core/CORE/narrative_engine/world_engine.py` (172 строки)

```
WorldEngine
├── _world_model: WorldModelExt      # 13 категорий из WORLD_MODEL/*.json
├── _relation_graph: RelationGraph    # 287 связей
├── _form_engine: FormEngine         # 55 визуальных форм
├── _consistency_engine: ConsistencyEngine  # 6 правил
├── _experience_engine: ExperienceEngine  # 10 режимов
└── _entity_index: dict[str, dict]   # O(1) по ID
```

**Инициализация:** `initialize()` — загружает все поддвижки, строит индекс.

### 2.7 WorldModelExt

**Файл:** `core/CORE/narrative_engine/world_model_ext.py` (112 строк)

Загружает `core/CORE/WORLD_MODEL/*.json`:
- ARCHITECTURE.json
- CIVILIZATIONS.json
- CLIMATE.json
- GEOGRAPHY.json
- LANGUAGE.json
- MYTHOLOGY.json
- PHILOSOPHY.json
- RELIGION.json
- RITUALS.json

### 2.8 RelationGraph

**Файл:** `core/CORE/narrative_engine/relation_models.py` (285 строк)

```
RelationType: CAUSAL, HISTORICAL, GEOGRAPHIC, PHILOSOPHICAL, MYTHOLOGICAL, ARCHAEOLOGICAL, SYMBOLIC, CULTURAL
RelationStrength: STRONG (0.8-1.0), MODERATE (0.5-0.7), WEAK (0.2-0.4), INFERRED (0.1)
WorldRelation: id, source_id, target_id, relation_type, description, strength, evidence, epoch, bidirectional
```

**RelationGraph:** BFS, shortest_path, get_connected, get_context, get_statistics

### 2.9 FormEngine

**Файл:** `core/CORE/narrative_engine/form_engine.py` (255 строк)

Использует `FORM.get_form_library()` — 55 визуальных форм, 11 категорий.
Генерирует `VisualForm` + `FormContext` с visual_prompt, palette, materials, mood.

### 2.10 ConsistencyEngine

**Файл:** `core/CORE/narrative_engine/consistency_engine.py` (236 строк)

```
RuleType: TEMPORAL, SPATIAL, CAUSAL, CULTURAL, METAPHYSICAL
RuleSeverity: HARD, SOFT, INFO
```

**DEFAULT_RULES:**
- `temporal_no_future` — персонажи не могут знать будущее
- `spatial_no_impossible` — нельзя быть в двух местах одновременно
- `causal_no_effect_before_cause` — следствие не может предшествовать причине
- `cultural_no_anachronism` — нельзя использовать технологии будущей эпохи
- `metaphysical_consistency` — правила метафизики должны соблюдаться

### 2.11 ExperienceEngine

**Файл:** `core/CORE/narrative_engine/experience_engine.py` (209 строк)

```
ExperienceMode: DIALOG, STORY, MOVIE, QUEST, GAME, RESEARCH, LESSON, TIMELINE, DOCUMENTARY, ILLUSTRATION
```

Каждый режим имеет: available_engines, output_types, constraints.

### 2.12 KnowledgeGraph

**Файл:** `core/CORE/knowledge_graph/graph_engine.py` (209 строк)

```
GraphEngine
├── _entity_store: EntityStore       # из book_os
├── _rel_store: RelationshipStore    # из book_os
├── _fact_store: FactStore           # из book_os
├── _adjacency: dict[str, list[dict]]
├── _node_types: dict[str, str]
└── _node_names: dict[str, str]
```

**Методы:** `build()`, `get_neighbors()`, `shortest_path()`, `get_subgraph()`, `get_context_for_rag()`

### 2.13 KnowledgeKernel

**Файл:** `core/CORE/intelligence/kernel.py` (339 строк)

```
KnowledgeKernel
├── chunker: SemanticChunker         # paragraph + chapter + sliding_window
├── enricher: GenomeEnricher         # обогащение метаданными из генома
├── retriever: BookRetriever         # ChromaDB RAG
├── cleaner: TextCleaner             # очистка текста
└── nameresolver: NameResolver       # алиасы персонажей
```

**Методы:** `index_book(mode="hybrid")`, `search(query, n=5)`, `get_enriched_catalog()`

### 2.14 BookRetriever

**Файл:** `core/CORE/intelligence/retriever.py` (329 строк)

ChromaDB collection `arkaim_book`. Кэш с TTL 60 сек. Enriched chunks с метаданными из генома.

### 2.15 NameResolver

**Файл:** `core/CORE/intelligence/nameresolver.py` (97 строк)

```
CANONICAL_MAP = {
    "Велик": {"Велик", "Велиусмус", "Великосвет", "Велом", ...},
    "Славный": {"Славный", "Мирослав", "Всеслав", ...},
    "Учитель": {"Учитель", ...},
    "Архат": {"Архат", "Высшее Существо", ...},
    ...
}
```

### 2.16 Knowledge Expansion Pipeline

**Файл:** `core/CORE/knowledge_expansion/pipeline.py` (205 строк)

```
KnowledgeExpansionPipeline
├── extractor: JSONExtractor
├── enricher: DeepAnalyzer (LLM)
├── linker: GraphLinker
├── validator: SchemaValidator
└── store: KnowledgeStore
```

**Модули (11 штук):** cosmology, geography, psychology, language, rituals, technology, +哲学的、 archaeology deep、 cosmology deep、 cross references deep、 philosophy deep、 symbols deep、 themes deep、 archetypes expanded、 symbols expanded、 themes expanded

**Модели данных:** RawKnowledge → EnrichedKnowledge → LinkedKnowledge → ValidatedKnowledge

### 2.17 ExpansionLoader

**Файл:** `core/CORE/knowledge_expansion/expansion_loader.py` (100 строк)

Загружает из `core/KNOWLEDGE/`:
- `*_DEEP.json` файлы (168 тем)
- `*_EXPANDED.json` файлы
- `ACADEMIC_CONFIRMATIONS.json`

### 2.18 ExternalSources

**Файл:** `core/CORE/narrative_engine/external_sources.py` (243 строки)

```
ExternalSourceResult: title, url, snippet, source_type, relevance_score, year, authors
```

**Источники:** Wikipedia API, Semantic Scholar API, OpenAlex API. Все бесплатные, без ключей.

### 2.19 SourceSearcher

**Файл:** `core/CORE/narrative_engine/research/source_searcher.py` (109 строк)

Rule-based поиск + LLM fallback. `SOURCE_DATABASES` по типам сущностей (location, character, concept, technology).

### 2.20 CanonValidator

**Файл:** `core/CORE/narrative_engine/canon_validator.py`

Проверяет генерируемый текст на соответствие канону книги.

### 2.21 ContradictionDetector

**Файл:** `core/CORE/narrative_engine/contradiction_detector.py` (276 строк)

Проверяет 5 типов противоречий в CauseEffectTree:
1. Temporal Paradox — следствие предшествует причине
2. Causal Loop — A → B → A
3. Missing Cause — следствие без причины
4. Timeline Violation — нарушение порядка эпох
5. Character Inconsistency — персонаж действует нехарактерно

### 2.22 CompatibilityChecker

**Файл:** `core/CORE/narrative_engine/compatibility_checker.py` (569 строк)

6 осей совместимости:
| Ось | Вес | Проверка |
|-----|-----|---------|
| book_canon | 0.30 | Прямые противоречия с текстом книги |
| historical | 0.15 | Историческая достоверность |
| geographical | 0.10 | Географическая согласованность |
| temporal | 0.15 | Временная последовательность |
| character | 0.15 | Соответствие характерам персонажей |
| author_intent | 0.15 | Соответствие замыслу автора |

### 2.23 TimelinePlanner

**Файл:** `core/CORE/narrative_engine/planners/timeline.py` (90 строк)

Проверяет временную согласованность событий. `ChronologicalEvent`, `TimelinePlan`.

### 2.24 CauseEffectPlanner

**Файл:** `core/CORE/narrative_engine/planners/cause_effect.py` (640 строк)

Гибридный подход: детерминированный каркас + LLM для связей + post-валидация.
`PATTERN_CHAINS` — 10+ паттернов (Путешествие героя, Учитель→Ученик→Посредник, и др.)

### 2.25 ContextAssembler

**Файл:** `core/CORE/narrative_engine/context_assembler.py` (282 строки)

Собирает `FullContext`:
- `world_state` — снимок мира
- `historical` — HistoricalContextBuilder
- `geography` — GeographyContextBuilder
- `mythology` — MythologyContextBuilder
- `book` — BookContext (RAG chunks)
- `screenplay` — ScreenplayContext

### 2.26 VisualGenome

**Файл:** `core/CORE/visualization/visual_genome.py` (40 строк)

In-memory CRUD + versioning. `VisualGenomeEntry`, `CharacterVisual`, `LocationVisual`.
`compute_source_hash()` для инвалидации при изменениях канона.

### 2.27 ArchetypeVisuals

**Файл:** `core/CORE/visualization/archetype_visuals.py`

Авто-заполнение визуалов при появлении новых персонажей (hook в EvolutionTracker).

### 2.28 SceneEngine

**Файл:** `core/CORE/visualization/scene_engine.py`

Генерация сценарных промптов для ComfyUI.

### 2.29 Presence / Observer / Suggester

**Файл:** `core/CORE/presence/observer.py`, `suggester.py`

Наблюдение за активностью читателей, предложения автору. Telegram email API.

### 2.30 ReaderMemoryStore

**Файл:** `runtime/core/memory/reader_memory.py` (525 строк)

SQLite-based. Таблицы: readers, topics, interactions.
`ReaderProfile`: level (novice/intermediate/advanced/expert), learning_style, engagement_score, topics, last_topic.

### 2.31 IdentityLayer (runtime)

**Файл:** `runtime/core/identity/policy.py` (39 строк)

```
IDENTITY_RULES:
- Always refer to yourself as 'Hermes' or 'Hermes Agent'
- Never say 'I am a model', 'I am an LLM', 'I am GigaChat'
- Never expose provider metadata
- If asked about provider: 'I use GigaChat as my cognitive provider'
```

**Sanitizer:** `runtime/core/identity/sanitizer.py` — фильтрует ответы по политикам.

### 2.32 Orchestrator

**Файл:** `runtime/core/orchestrator.py` (312 строк)

```
Orchestrator
├── memory: MemoryStore
├── leads: LeadStore
├── tools: ToolExecutor
├── skills: SkillRegistry
└── ProviderRegistry.chain_healthy()
```

Intent classification: chat, factual, creative, analysis, question.

### 2.33 PulseManager

**Файл:** `runtime/core/pulse_manager.py` (99 строк)

FastAPI-зависимости: `get_pulse()`, `get_voice()`, `get_reader_memory()`.
LLM подключается к Voice при старте.

### 2.34 DatabaseManager

**Файл:** `runtime/core/database.py` (100 строк)

Централизованное управление SQLite соединениями. MigrationEngine для схем.

### 2.35 API Routes

**Файл:** `runtime/core/routes/`

| Route | Prefix | Тег | Описание |
|-------|--------|-----|----------|
| book.py | `/book/*` | Book Intelligence | ask, genome, layers, world |
| world_engine.py | `/world/*` | World Engine | search, entities, visual prompts, validate |
| reader.py | `/reader/*` | Reader | profile, topics, interactions |
| visual.py | `/visual/*` | Visual | generate, assets |
| film_studio.py | `/film/*` | Film Studio | screenplay, scenes |
| assets.py | `/assets/*` | Assets | visual assets management |

### 2.36 Auth / RBAC

**Файл:** `runtime/auth/` — OAuth (Telegram, Google), JWT, RBAC (`require_role`).

---

## 3. EXISTING DATA MODEL

### 3.1 Геном (GENOME)

**Путь:** `core/GENOME/CURRENT/profile.json`, `core/GENOME/GENOME_v{version}.json`

```json
{
  "book_id": "nasledie-arkaima",
  "title": "Наследие Аркаима",
  "author": "ОВладимирович",
  "genome_version": "1.0.0",
  "metrics": {
    "total_themes": 138,
    "total_characters": 30,
    "total_symbols": 15,
    "total_values": 70,
    "total_conflicts": 32
  },
  "modules": {
    "characters": [...],
    "themes": [...],
    "symbols": [...],
    "values": [...],
    "conflicts": [...]
  },
  "world_entities": [...],
  "identity_layer": "...",
  "author_intent": { "main_message": "..." }
}
```

**Версионирование:** `GENOME_v1.0.0.json`, `GENOME_v1.1.0.json`, ... + backups в `core/GENOME/history/`

### 3.2 KNOWLEDGE/*.json (47 файлов)

| Категория | Файлы | Содержание |
|-----------|-------|-----------|
| Книга | BOOK_DOCUMENT.json, BOOK_PROFILE.json, SYNOPSIS_DOCUMENT.json, SYNOPSIS_PROFILE.json, BOOK_GENOME.json, PLOT.json | Структурированные данные из книги |
| Персонажи | CHARACTERS.json, character_profiles.json, character_deep_profiles.json, deep_characters.json | Профили 30+ персонажей |
| Цивилизации | civilization_profiles.json | Профили цивилизаций |
| Глубокие концепты | deep_concepts.json | Философские концепты |
| Темы | THEMES_DEEP.json, THEMES_EXPANDED.json | 168 тем с слоями |
| Символы | SYMBOLS.json, SYMBOLS_DEEP.json, SYMBOLS_EXPANDED.json | 15+ символов |
| Философия | PHILOSOPHY.json, PHILOSOPHY_DEEP.json | Философская система |
| Ценности | VALUES.json | 70 ценностей |
| Авторский замысел | AUTHOR_INTENT.json | Замысел автора |
| География | GEOGRAPHY.json, MAP_DATA.json | Локации, маршруты |
| Археология | ARCHAEOLOGY.json, ARCHAEOLOGY_DEEP.json | Археологические подтверждения |
| Космология | COSMOLOGY.json, COSMOLOGY_DEEP.json | Космологическая модель |
| Ритуалы | RITUALS.json | Ритуальные практики |
| Технологии | TECHNOLOGY.json | Технологический уровень |
| Язык | LANGUAGE.json | Языковая система |
| Психология | PSYCHOLOGY.json | Психологические профили |
| Энергия мест | ENERGY_OF_PLACES.json | Энергетические свойства |
| Архетипы | ARCHETYPES_EXPANDED.json | Расширенные архетипы |
| Связи | CROSS_REFERENCES.json, CROSS_REFERENCES_DEEP.json | Межтематические связи |
| Цитаты | ANCHOR_QUOTES.json, quotes.json | Ключевые цитаты |
| Сцены | SCENE_PROMPTS.json, screenplay_extracts.json | Сценарные данные |
| Подтверждения | ACADEMIC_CONFIRMATIONS.json | Научные подтверждения |
| Вопросы | QUESTIONS_FOR_READER.json | Вопросы для читателей |

### 3.3 WORLD_MODEL/*.json (9 категорий)

```
ARCHITECTURE.json   — архитектурные формы
CIVILIZATIONS.json  — цивилизации мира
CLIMATE.json        — климатические зоны
GEOGRAPHY.json      — географические объекты
LANGUAGE.json       — языки
MYTHOLOGY.json      — мифологические фигуры
PHILOSOPHY.json     — философские школы
RELIGION.json       — религиозные практики
RITUALS.json        — ритуалы
```

**Всего:** 406 сущностей, 287 связей.

### 3.4 WORLD/entities.json и WORLD/relations.json

Файлы в `core/WORLD/` — сырые данные графа сущностей и отношений.

### 3.5 enriched_chunks.json и enriched_catalog.json

Результаты индексации книги через KnowledgeKernel. ChromaDB-совместимые чанки с метаданными.

### 3.6 SQLite БД (runtime/arkaim.db)

Таблицы: readers, topics, interactions, drafts, trace_store.

---

## 4. EXISTING KNOWLEDGE MODEL

### 4.1 Иерархия источников

```
SOURCE_OF_TRUTH/
├── BOOK/КНИГА.md              ← ПЕРВИЧНЫЙ ИСТОЧНИК (канон)
├── SYNOPSIS/Сценарий_Full.md  ← Вторичный (синопсис)
├── AUTHOR_NOTES/Аннотация.pdf ← Дополнение
└── AUTHOR_NOTES/Письмо.pdf    ← Дополнение
```

### 4.2 Протокол извлечения

```
run_extractor.py → BOOK_PROFILE.json (паспорт книги)
run_index_book_v2.py → enriched_chunks.json + ChromaDB индекс
character_profiler.py → character_deep_profiles.json
```

### 4.3 Обогашение знаний

```
knowledge_expansion/pipeline.py
├── JSONExtractor → RawKnowledge
├── DeepAnalyzer (LLM) → EnrichedKnowledge (3 слоя: буквальный, метафорический, космический)
├── GraphLinker → LinkedKnowledge (связи с KG)
└── SchemaValidator → ValidatedKnowledge
```

**11 модулей:** cosmology, geography, psychology, language, rituals, technology, philosophy_deep, archaeology_deep, cosmology_deep, cross_references_deep, themes_deep.

**Результат:** 168 тем в ExpansionLayer.

---

## 5. EXISTING PROVENANCE

### 5.1 SourceLevel Enum

**Файл:** `core/CORE/narrative_engine/source_levels.py` (56 строк)

```python
class SourceLevel(str, Enum):
    CANON = "CANON"                          # 1.0 — прямо из текста книги
    AUTHOR_INTERPRETATION = "AUTHOR_INTERPRETATION"  # 0.85 — материалы автора
    HISTORICAL = "HISTORICAL"                # 0.8 — летописи, археология
    MYTHOLOGICAL = "MYTHOLOGICAL"            # 0.7 — эпосы, легенды
    SCIENTIFIC = "SCIENTIFIC"                # 0.6 — исследования
    SYSTEM_INTERPRETATION = "SYSTEM_INTERPRETATION"  # 0.5 — выводы анализа
    USER_HYPOTHESIS = "USER_HYPOTHESIS"      # 0.3 — идеи читателей
```

### 5.2 ProvenanceTag

```python
@dataclass
class ProvenanceTag:
    source_level: SourceLevel
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    added_at: datetime
    added_by: str = "system"
    notes: Optional[str] = None
```

### 5.3 Применяется в

- `world_model.py` — Epoch, Location, Civilization, Technology, Religion имеют `source_level` + `provenance`
- `compatibility_checker.py` — веса осей используют SOURCE_LEVEL_WEIGHTS
- `cause_effect.py` — CauseEffectNode имеет `source_level`
- `historical.py` — ContextFact имеет `source_level`

### 5.4 ГАП: нет явного разделения на AUTHOR_CANON / DERIVED / EXTERNAL_SOURCE / RECONSTRUCTION / HYPOTHESIS / ARTISTIC_MODEL / FUTURE_EXTRAPOLATION

Текущий SourceLevel — это **градация достоверности**, а не **тип происхождения**. Не хватает семантических категорий:
- AUTHOR_CANON — прямые утверждения из книги
- RECONSTRUCTION — восстановление на основе археологии
- HYPOTHESIS — системные гипотезы
- ARTISTIC_MODEL — художественные допущения
- FUTURE_EXTRAPOLATION — проекции в будущее

---

## 6. EXISTING WORLD MODEL

### 6.1 WorldEngine — центральный координатор

**Файл:** `core/CORE/narrative_engine/world_engine.py`

Интегрирует 5 поддвижков:
1. WorldModelExt (данные)
2. RelationGraph (связи)
3. FormEngine (визуальные формы)
4. ConsistencyEngine (правила)
5. ExperienceEngine (режимы)

### 6.2 WorldModelExt — загрузчик данных

Загружает 9 JSON-категорий из `WORLD_MODEL/`. 406 сущностей.

### 6.3 RelationGraph — граф связей

8 типов связей (CAUSAL, HISTORICAL, GEOGRAPHIC, PHILOSOPHICAL, MYTHOLOGICAL, ARCHAEOLOGICAL, SYMBOLIC, CULTURAL).
4 уровня силы (STRONG, MODERATE, WEAK, INFERRED).
287 связей. BFS, shortest_path, get_connected.

### 6.4 WorldModel (Pydantic модели)

**Файл:** `core/CORE/narrative_engine/world_model.py` (322 строки)

```python
Epoch(id, name, name_ru, description, order, duration_years, start_event, end_event,
      technologies_available, civilizations_active, source_level, provenance)

Location(id, name, name_ru, type, description, coordinates, region_id,
         epochs_present, related_entities, source_level, provenance)

Civilization(id, name, name_ru, description, epochs, values, technologies,
             religion_ids, related_locations, source_level, provenance)

Technology(id, name, name_ru, description, epoch_first, civilization_origin,
           source_level, provenance)

Religion(id, name, name_ru, description, epochs, practices, key_figures,
         source_level, provenance)
```

### 6.5 WorldModelExt — дополнение к WorldModel

Расширяет WorldModel загрузкой из WORLD_MODEL/*.json. 13 категорий (9 JSON + дополнительные).

### 6.6 WorldState — снимок мира

**Файл:** `core/CORE/narrative_engine/world_state.py` (143 строки)

```python
WorldState(epoch_id, epoch_name_ru, active_characters, available_locations,
           technologies, events_happened, events_pending, active_rules,
           civilization_state)
```

### 6.7 GАП: нет единой временной цепи TODAY→HISTORY→ARKAIM

WorldModel имеет эпохи, но нет модели *обратной реконструкции* от современности к Аркаиму.

---

## 7. EXISTING TIME MODEL

### 7.1 Epochs (из world_model_data.py)

```python
EPOCHS = [
    {"id": "pre_arkaim", "name": "Pre-Arkaim", "name_ru": "До Аркаима", "order": 0},
    {"id": "arkaim_era", "name": "Arkaim Era", "name_ru": "Эпоха Аркаима", "order": 5},
    # ... ещё 4 эпохи
]
```

**Всего:** 6 эпох с порядковыми номерами.

### 7.2 TimelinePlanner

Проверяет хронологическую согласованность событий. `ChronologicalEvent.epoch`, `.order`.

### 7.3 CauseEffectTree

Узлы имеют `epoch` и `order` для временной упорядоченности.

### 7.4 ConsistencyRule (TEMPORAL)

- `temporal_no_future` — запрет знания будущего
- `causal_no_effect_before_cause` — следствие не раньше причины

### 7.5 GАП: нет явной модели исторического развития

Нет цепочки:
```
TODAY → исторические слои → Аркаимская эпоха → доаркаимское время
```

Нет модели *причинно-следственных переходов* между эпохами.

---

## 8. EXISTING FORM MODEL

### 8.1 FormEngine

**Файл:** `core/CORE/narrative_engine/form_engine.py`

55 визуальных форм, 11 категорий.
`VisualForm`: id, name, name_ru, category, description, visual_prompt, materials, colors, features, mood, style.

### 8.2 FormLibrary

**Файл:** `core/FORM/` (импортируется как `from FORM import get_form_library`)

### 8.3 Visualization Pipeline

| Компонент | Файл | Назначение |
|-----------|------|-----------|
| visual_genome.py | Core | CRUD визуального генома, versioning |
| archetype_visuals.py | Core | Авто-заполнение визуалов новых персонажей |
| scene_engine.py | Core | Генерация сценарных промптов |
| character_visualizer.py | Core | Визуализация персонажей |
| world_visualizer.py | Core | Визуализация мира |
| meaning_to_visual.py | Core | Перевод смыслов в визуальные промпты |
| prompt_builder.py | Core | Сборка промптов для ComfyUI |
| conflict_palettes.py | Core | Палитры конфликтов |
| xray_visual_triggers.py | Core | Триггеры визуализации по ключевым словам |

### 8.4 ComfyUI Integration

**Файл:** `core/CORE/providers/image/comfyui.py`

Генерация изображений через ComfyUI workflow. Префикс `arkaim`.

### 8.5 GАП: нет модели «как выглядел мир» на уровне данных

FormEngine генерирует промпты, но нет структурированных данных о:
- архитектуре (материалы, формы, цвета)
- одежде (ткани, крой, аксессуары)
- свете (источники, качество, атмосфера)
- звуке (звуковой ландшафт)
- эмоциональной атмосфере мест

---

## 9. EXISTING DIALOGUE MODEL

### 9.1 Путь диалога

```
Читатель → Web UI
    ↓
FastAPI /book/ask → Orchestrator.chat()
    ↓
BookVoice.speak(query, reader_id)
    ↓
ReaderAwarePulse.listen(query, reader_id)
    ↓
BookPulse.listen(query)
    ↓
KnowledgeLayer.respond_to(query)  ← O(1) ответ без LLM
    ↓
BookVoice → LLM (если confidence < порога или нужна формулировка)
    ↓
IdentityLayer.validate(llm_text)  ← финальная проверка
    ↓
Utterance → Читатель
    ↓
ReaderMemory.record(reader_id, question, answer, topic)
```

### 9.2 ReaderMemory

**Файл:** `runtime/core/memory/reader_memory.py`

- `ReaderProfile`: level, learning_style, engagement_score, topics
- `TopicMemory`: depth, questions_count, last_asked, pulse_source
- Метод `adapt_response(response, profile)` → AdaptiveResponse

### 9.3 Deepen Logic

`ReaderAwarePulse._is_deepen_request()` → распознаёт «расскажи подробнее» → подменяет query на enriched_query → повышает confidence.

### 9.4 Mood Detection

BookVoice определяет настроение вопроса (joy/curiosity/sadness/doubt/deep/neutral) и добавляет эмоциональный префикс + метафору.

### 9.5 ГАП: нет многоязычности диалога

Диалог только на русском. Нет модели переключения языка.

---

## 10. EXISTING EXTERNAL KNOWLEDGE

### 10.1 ExternalSources

**Файл:** `core/CORE/narrative_engine/external_sources.py`

| Источник | API | Без ключа | Rate limit |
|----------|-----|-----------|------------|
| Wikipedia | ru.wikipedia.org | ✅ | ~100/мин |
| Semantic Scholar | api.semanticscholar.org | ✅ | 100/5мин |
| OpenAlex | api.openalex.org | ✅ | нет жёсткого |

### 10.2 SourceSearcher

Rule-based + LLM fallback. `SOURCE_DATABASES` по типам сущностей.

### 10.3 HistoricalContextBuilder

Загружает COSMOLOGY.json, PHILOSOPHY_DEEP.json, CROSS_REFERENCES.json, ACADEMIC_CONFIRMATIONS.json из KNOWLEDGE/.

### 10.4 ГАП: нет фильтрации external → canon

Внешние источники НЕ помечаются как EXTERNAL_SOURCE в provenance.
Нет механизма, который предотвращал бы автоматическое смешивание внешних данных с каноническими.

---

## 11. ARKAIM COVERAGE

### 11.1 Где Аркаим представлен

| Компонент | Где | Что |
|-----------|-----|-----|
| world_model_data.py | `core/CORE/narrative_engine/` | Эпоха `arkaim_era` (order=5), локация `arkaim` (sacred_site) |
| compatibility_checker.py | `core/CORE/narrative_engine/` | Ключевые слова: аркаим, аркаима, аркаиме → усиление проверки book_canon |
| constraint_engine.py | `core/CORE/narrative_engine/` | Маппинг: "до аркаима"→pre_arkaim, "эпоха аркаима"→arkaim_era |
| entity_extractor.py | `core/CORE/narrative_engine/research/` | "аркаим" → (location, "Аркаим") |
| xray_visual_triggers.py | `core/CORE/visualization/` | Триггер: "аркаим" → визуализация |
| relation_extractor.py | `core/CORE/narrative_engine/` | Общие темы: гиперборея, атлантида, **аркаим**, катастрофа |
| KNOWLEDGE/ | 47 JSON файлов | Темы, символы, цитаты связанные с Аркаимом |

### 11.2 Данные об Аркаиме

**Из world_model_data.py:**
- Epoch: `arkaim_era` — order=5, описание эпохи
- Location: `arkaim` — type=sacred_site
- Связи с Hyperborea, Atlantis, catastrophe

### 11.3 Чего НЕ хватает для Аркаима

| Аспект | Статус |
|--------|--------|
| Географические координаты | ❌ Нет |
| Временные рамки эпохи (датируемые) | ❌ Нет (только order) |
| Археологическая привязка (реальный Аркаим) | ⚠️ Частично (ARCHAEOLOGY.json) |
| Связь «Аркаим ⇄ современность» | ❌ Нет |
| Связь «Аркаим ⇄ Hyperborea ⇄ Atlantis» | ⚠️ Упоминание в relation_extractor |
| Визуальная модель Аркаима | ⚠️ FormEngine есть, но нет конкретных данных |
| Историческая реконструкция | ❌ Нет separate module |
| Будущее extrapolation от Аркаима | ❌ Нет |

### 11.4 Аркаим в KNOWLEDGE

В KNOWLEDGE/ есть файлы ARCHAEOLOGY.json, GEOGRAPHY.json, MAP_DATA.json — они содержат данные о реальном и книжном Аркаиме, но **нет явного разделения** между ними на уровне данных.

---

## 12. GAPS

### 12.1 Критические gaps

| Gap | Описание |Impact |
|-----|----------|-------|
| **No Today→History→Arkaim chain** | Нет модели исторической реконструкции от современности к Аркаиму | Критический |
| **No Arkaim→Development→Today→Future chain** | Нет модели прямого развития от Аркаима через историю к будущему | Критический |
| **Provenance categories too coarse** | SourceLevel — это веса, не типы происхождения | Высокий |
| **No external→canon firewall** | Внешние данные могут смешиваться с каноническими | Высокий |
| **No temporal transition model** | Нет модели переходов между эпохами (causality across epochs) | Высокий |
| **No form data at entity level** | FormEngine генерирует промпты, но нет структурированных данных о формах | Средний |
| **No multi-language support** | Диалог только на русском | Средний |
| **No Arkaim-specific reconstruction module** | Нет отдельного модуля для реконструкции Аркаима | Средний |

### 12.2 Архитектурные конфликты

| Конфликт | Описание |
|----------|----------|
| **WorldEngine vs KnowledgeGraph** | Два графа: RelationGraph (WORLD_MODEL/) и GraphEngine (book_os). Нет синхронизации. |
| **pulse.layers.py vs runtime layers** | layers.py в CORE/ содержит 11 слоёв, но runtime использует свой IdentityLayer (policy.py). Рассинхронизация. |
| **GENOME v1.0.0 hardcode** | Multiple files hardcode `GENOME_v1.0.0.json` instead of reading from config. |
| **KnowledgeExpansion pipeline not integrated** | Pipeline produces *_DEEP.json but ExpansionLayer doesn't automatically consume them at runtime. |
| **VisualGenome in-memory only** | VisualGenomeStore is in-memory, lost on restart. No persistence. |
| **SourceLevel vs SourceCategory** | Протокол provenance есть (source_level), но семантические категории (AUTHOR_CANON, RECONSTRUCTION, HYPOTHESIS) не реализованы. |

---

## 13. DUPLICATES

| Дубликат | Где | Где ещё | Статус |
|----------|-----|---------|--------|
| WorldModel | `narrative_engine/world_model.py` | `narrative_engine/world_model_ext.py` | EXTEND (ext loads JSON) |
| Genome extraction | `core/CORE/genome/extractor.py` | `runtime/core/routes/book.py:_load_genome_raw()` | Consolidate |
| Reader memory | `runtime/core/memory/reader_memory.py` | `core/CORE/pulse/reader_aware.py` (imports from runtime) | Cross-boundary dependency |
| EntityStore | `book_os/entity_store.py` | `WORLD/entities.json` | Dual source of truth |
| RelationStore | `book_os/relationship_store.py` | `WORLD/relations.json` + `RelationGraph` | Triple source of truth |
| FormEngine | `narrative_engine/form_engine.py` | `FORM/` directory | Separate but linked |
| Knowledge expansion | `knowledge_expansion/pipeline.py` | `KNOWLEDGE/*_DEEP.json` (produced) | Output not consumed by Pulse |
| LLM client | `core/CORE/llm_client.py` | `runtime/core/providers/gigachat.py` + `openrouter.py` | Multiple entry points |

---

## 14. ARCHITECTURAL CONFLICTS

### 14.1 CORE/ vs runtime/ boundary

CORE/ добавляется в sys.path вручную в `runtime/core/main.py`:
```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE_DIR = _PROJECT_ROOT / "core" / "CORE"
sys.path.insert(0, str(_CORE_DIR))
```

Это создаёт хрупкую зависимость. ANY change to directory structure breaks import.

### 14.2 Double provenance tracking

- `source_levels.py` определяет SourceLevel + ProvenanceTag
- `compatibility_checker.py` определяет AXIS_WEIGHTS с разными весами
- `cause_effect.py` определяет source_level на узлах дерева
- **Нет единого центра** для provenance — каждый компонент решает сам.

### 14.3 Canonical vs expanded knowledge mixing

KNOWLEDGE/ содержит:
- `BOOK_GENOME.json` — структурированный геном (канон)
- `THEMES_DEEP.json` — расширенные темы (LLM-обогащённые)
- `ACADEMIC_CONFIRMATIONS.json` — внешние подтверждения
- `narrative_rumors.md` — ??? (неизвестный формат)

**Нет явного разделения** между каноническими и неканоническими данными на уровне файловой системы.

---

## 15. WHAT MUST NOT BE REBUILT

### 15.1 Already solid — KEEP as-is

| Компонент | Почему |
|-----------|--------|
| **SourceLevel enum + ProvenanceTag** |已经有了正确的抽象，只需扩展语义类别 |
| **BookPulse + layer architecture** | Core design is sound; layers respond without LLM |
| **KnowledgeLayer O(1) indexes** | Performance-critical, well-designed |
| **BookVoice mood detection + metaphor** | Unique feature, works well |
| **ReaderMemoryStore + profile system** | SQLite-based, proper schema |
| **WorldEngine integration pattern** | Coordinator delegates to sub-engines correctly |
| **RelationGraph BFS + shortest_path** | Algorithmically correct |
| **ConsistencyEngine rule system** | Extensible, well-typed |
| **CompatibilityChecker 6-axis model** | Good foundation for canonicity checking |
| **NameResolver canonical map** | Handles alias confusion correctly |
| **EvolutionTracker diff + snapshot** | Proper versioning pattern |
| **ChromaDB RAG pipeline** | Working, needs enrichment not rebuild |
| **FormEngine + FormLibrary** | 55 forms, 11 categories — substantial work preserved |
| **ExperienceEngine 10 modes** | Mode configuration is complete |
| **aethon.xray observability** | Vendored, working, full tracing |
| **IdentityLayer policy** | Well-defined rules |

### 15.2 Partially working — EXTEND, don't replace

| Компонент | Что добавить |
|-----------|-------------|
| **WorldModel** | Добавить temporal chain + historical reconstruction |
| **RelationGraph** | Добавить epoch-based relations + bidirectional time links |
| **FormEngine** | Добавить form data at entity level (materials, colors, etc.) |
| **ExpansionLayer** | Integrate with KnowledgeExpansion pipeline output |
| **VisualGenome** | Add persistence (SQLite) |
| **ExternalSources** | Add provenance tagging (mark as EXTERNAL_SOURCE) |
| **KnowledgeGraph** | Add sync with WorldModel |

---

## 16. WHAT SHOULD BE EXTENDED

### 16.1 SourceLevel → ProvenanceCategory

Расширить `SourceLevel` до полноценной provenance-модели:

```python
class ProvenanceCategory(str, Enum):
    AUTHOR_CANON = "AUTHOR_CANON"              # Прямые утверждения из книги
    DERIVED = "DERIVED"                        # Выведено из канона
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"        # Внешний исторический/научный источник
    RECONSTRUCTION = "RECONSTRUCTION"          # Восстановление на основе данных
    HYPOTHESIS = "HYPOTHESIS"                  # Системная гипотеза
    ARTISTIC_MODEL = "ARTISTIC_MODEL"          # Художественное допущение
    FUTURE_EXTRAPOLATION = "FUTURE_EXTRAPOLATION"  # Проекция в будущее
```

Каждый `ProvenanceTag` должен иметь `category` + `source_level` (вес).

### 16.2 Temporal Chain Model

Добавить в WorldModel:

```python
class TemporalChain(BaseModel):
    """Цепочка: TODAY → HISTORY → ARKAIM"""
    direction: str  # "reconstruction" or "development"
    nodes: list[TemporalNode]

class TemporalNode(BaseModel):
    era: str
    epoch_id: str
    events: list[str]
    transitions: list[str]  # ID соседних нод
```

### 16.3 Arkaim Reconstruction Module

Новый модуль `narrative_engine/arkaim_reconstruction.py`:
- Загружает ARCHAEOLOGY.json, GEOGRAPHY.json, MAP_DATA.json
- Строит цепочку: современный Аркаим → исторические слои → эпоха Аркаима
- Связывает с WorldModel epochs

### 16.4 External Knowledge Firewall

В `external_sources.py` добавить:
```python
class ExternalKnowledgeFirewall:
    def tag_as_external(self, result: ExternalSourceResult) -> ProvenanceTag:
        return ProvenanceTag(
            source_level=SourceLevel.EXTERNAL_SOURCE,
            category=ProvenanceCategory.EXTERNAL_SOURCE,
            source_url=result.url,
            confidence=result.relevance_score,
        )
```

### 16.5 Form Data Enrichment

Расширить `WorldEntity` в world_model.py:
```python
class WorldEntity(BaseModel):
    # ... existing fields ...
    form_data: Optional[FormContext] = None  # enriched at query time
    temporal_bounds: Optional[dict] = None   # {epoch_start, epoch_end}
```

---

## 17. WHAT MUST BE ADDED

### 17.1 Новая подсистема: TemporalReconstructionEngine

**Назначение:** построить цепочку TODAY→HISTORY→ARKAIM и ARKAIM→DEVELOPMENT→TODAY→FUTURE.

**Компоненты:**
- `TemporalChainBuilder` — строит цепочки эпох
- `HistoricalLayerStack` — стопка исторических слоёв (современность → античность → бронзовый век → Аркаим)
- `EpochTransitionModel` — моделирует переходы между эпохами
- `FutureExtrapolator` — проекции от Аркаима в будущее

### 17.2 Новая подсистема: ArkaimCore

**Назначение:** единая точка доступа ко всем данным об Аркаиме.

**Компоненты:**
- `ArkaimDataModel` — структура данных Аркаима (география, эпоха, связи)
- `ArkaimReconstructionPipeline` — конвейер реконструкции
- `ArkaimFormProfile` — визуальный профиль Аркаима

### 17.3 Новая подсистема: ProvenanceController

**Назначение:** единый контроллер для маркировки всех фактов по категориям происхождения.

**Компоненты:**
- `ProvenanceRegistry` — реестр всех provenance тегов
- `CanonFilter` — фильтр, отделяющий AUTHOR_CANON от остального
- `ExternalTagger` —自动 маркирует внешние источники
- `HypothesisValidator` — валидирует гипотезы перед записью

### 17.4 API endpoints

| Endpoint | Метод | Назначение |
|----------|-------|-----------|
| `/book/temporal-chain` | GET | Получить цепочку эпох |
| `/book/arkaim/reconstruction` | GET | Реконструкция Аркаима |
| `/book/provenance/category` | GET | Категории provenance |
| `/book/arkaim/forms` | GET | Визуальные формы Аркаима |
| `/book/future-extrapolation` | POST | Экстраполяция в будущее |

---

## 18. MIGRATION RISKS

### 18.1 HIGH RISK

| Риск | Причина | Митигация |
|------|---------|-----------|
| Breaking CHANGE in Genome schema | NEW provenance categories require schema update | Version bump to v1.1.0, backward-compatible migration |
| Double source of truth (GraphEngine vs RelationGraph) | Both store entities/relations independently | Single source: RelationGraph; deprecate GraphEngine for World queries |
| CORE/ path dependency | sys.path insert in main.py is fragile | Package as proper Python package with pyproject.toml |

### 18.2 MEDIUM RISK

| Риск | Причина | Митигация |
|------|---------|-----------|
| ExpansionLayer not consuming pipeline output | Pipeline writes *_DEEP.json but Pulse doesn't read them | Hook ExpansionLoader into Pulse.load() |
| VisualGenome in-memory loss | Restart loses all visual data | Add SQLite persistence |
| External sources mixed with canon | No firewall between external and canon | Add provenance tagging in ExternalSources |

### 18.3 LOW RISK

| Риск | Причина | Митигация |
|------|---------|-----------|
| FormEngine dependency on FORM/ module | External module import | Vendor FORM/ into project |
| LLM client multiplicity | Multiple entry points for LLM | Standardize on single LLMClient interface |

---

## 19. RECOMMENDED TARGET ARCHITECTURE

```
                    ┌─────────────────────────────┐
                    │        AUTHOR SOURCES        │
                    │  SOURCE_OF_TRUTH/BOOK/       │
                    │  SOURCE_OF_TRUTH/SYNOPSIS/   │
                    │  SOURCE_OF_TRUTH/AUTHOR_NOTES│
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      AUTHOR CANON            │
                    │  BOOK_PROFILE.json           │
                    │  GENOME_v{version}.json      │
                    │  (immutable once published)  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       WORLD GENOME           │
                    │  WORLD_MODEL/*.json          │
                    │  KNOWLEDGE/*_DEEP.json       │
                    │  (extended, versioned)       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       WORLD MODEL            │
                    │  WorldEngine                 │
                    │  ├─ WorldModelExt (data)     │
                    │  ├─ RelationGraph (links)    │
                    │  ├─ TemporalChain (time)     │ ← NEW
                    │  ├─ ArkaimCore (focus)       │ ← NEW
                    │  └─ ConsistencyEngine (rules)│
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     PROVENANCE CONTROLLER    │
                    │  CanonFilter                 │
                    │  ExternalTagger              │ ← NEW
                    │  HypothesisValidator         │ ← NEW
                    │  ProvenanceRegistry          │ ← NEW
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     RECONSTRUCTION ENGINE    │
                    │  TemporalReconstruction      │ ← NEW
                    │  HistoricalLayerStack        │ ← NEW
                    │  FutureExtrapolator          │ ← NEW
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │        DIALOGUE PATH         │
                    │  BookVoice → Pulse → Reader  │
                    │  IdentityLayer validation    │
                    └─────────────────────────────┘
```

### 19.1 Provenance Model (NEW)

```
AUTHOR_CANON          ← book text, BOOK_PROFILE, GENOME
DERIVED               ← computed from canon (indexes, summaries)
EXTERNAL_SOURCE       ← Wikipedia, Semantic Scholar, OpenAlex
RECONSTRUCTION        ← historical reconstruction from archaeology
HYPOTHESIS            ← system-generated hypotheses
ARTISTIC_MODEL        ← visual/creative interpretations
FUTURE_EXTRAPOLATION  ← projected futures
```

### 19.2 Temporal Chain (NEW)

```
TODAY (current)
  ↓ archaeological_layers
HISTORY (recorded history)
  ↓ civilizational transitions
ARKAIM ERA (primary focus)
  ↓ pre-history
PRE-ARKAIM (origins)

AND reverse:
ARKAIM
  ↓ cultural diffusion
HISTORY
  ↓ modern manifestations
TODAY
  ↓ extrapolation
FUTURE
```

---

## 20. PROPOSED M1–M8 MIGRATION SEQUENCE

### M1: Provenance Controller Foundation
**Цель:** Единый контроллер provenance для всех фактов.
**Действия:**
1. Расширить `SourceLevel` → `ProvenanceCategory` enum
2. Добавить `ProvenanceTag.category` field
3. Создать `ProvenanceRegistry` singleton
4. Обновить `WorldModel` entities to accept category
5. Обновить `ExternalSources` to tag results
**Не затрагивает:** Existing tests, API contracts, genome format (backwards compatible)

### M2: Temporal Chain Model
**Цель:** Модель исторической реконструкции.
**Действия:**
1. Добавить `TemporalChain` и `TemporalNode` models
2. Реализовать `TemporalChainBuilder`
3. Добавить epoch transitions в `WorldModel`
4. API: `/book/temporal-chain`
**Не затрагивает:** Existing pulse layers, dialogue path

### M3: ArkaimCore Module
**Цель:** Единая точка доступа к данным об Аркаиме.
**Действия:**
1. Создать `ArkaimDataModel`
2. Интегрировать с `ARCHAEOLOGY.json`, `GEOGRAPHY.json`, `MAP_DATA.json`
3. Связать с WorldModel epochs
4. API: `/book/arkaim/reconstruction`
**Не затрагивает:** Existing world engine, knowledge graph

### M4: External Knowledge Firewall
**Цель:** Предотвратить смешивание внешних данных с каноническими.
**Действия:**
1. Реализовать `ExternalTagger` в `ProvenanceController`
2. Обновить `ExternalSources` to tag all results
3. Добавить filter в `KnowledgeLayer.respond_to()`
4. Обновить `compatibility_checker` to weight external lower
**Не затрагивает:** Core pulse, voice, memory

### M5: Form Data Enrichment
**Цель:** Структурированные данные о формах на уровне сущностей.
**Действия:**
1. Добавить `form_data` и `temporal_bounds` в `WorldEntity`
2. Обновить `FormEngine` to enrich at query time
3. Миграция существующих WORLD_MODEL/*.json
**Не затрагивает:** API contracts (additive change)

### M6: VisualGenome Persistence
**Цель:** Сохранение визуального генома между рестартами.
**Действия:**
1. Заменить in-memory `VisualGenomeStore` на SQLite
2. Добавить migration для схемы
3. Интегрировать с `DatabaseManager`
**Не затрагивает:** Existing visual pipeline

### M7: ExpansionLayer Integration
**Цель:** Потребление результатов KnowledgeExpansion Pipeline.
**Действия:**
1. Hook `ExpansionLoader` into `Pulse.load()`
2. Update `ExpansionLayer.respond_to()` to use loaded data
3. Verify 168 topics are available
**Не затрагивает:** Core pulse, genome format

### M8: Future Extrapolation
**Цель:** Проекция от Аркаима в будущее.
**Действия:**
1. Создать `FutureExtrapolator`
2. Использовать `TemporalChain` as base
3. Apply `CompatibilityChecker` to filter implausible futures
4. API: `/book/future-extrapolation`
**Не затрагивает:** Existing components (additive)

---

## ACCEPTANCE CRITERIA STATUS

| Критерий | Статус | Комментарий |
|----------|--------|-------------|
| Вся архитектура прослежена от API до persistence | ✅ | 36+ компонентов идентифицированы |
| Найдены реальные точки входа WORLD MODEL | ✅ | WorldEngine.initialize(), WorldModelExt |
| Найдены источники авторского канона | ✅ | SOURCE_OF_TRUTH/BOOK/КНИГА.md |
| Найдено текущее provenance | ✅ | SourceLevel + ProvenanceTag в 5+ местах |
| Найдено текущее temporal model | ✅ | 6 эпох в world_model_data.py + TimelinePlanner |
| Найдено текущее form/visual model | ✅ | FormEngine + 55 форм + VisualGenome |
| Найден весь dialogue path | ✅ | Voice → Pulse → ReaderMemory → LLM → Identity |
| Определено текущее состояние ARKAIM | ✅ | sacred_site в arkaim_era, частичные связи |
| Определены все критические gaps | ✅ | 8 gaps identified, 2 critical |
| Определено, что можно сохранить | ✅ | 17 компонентов — KEEP |
| Определены точки расширения | ✅ | 6 компонентов — EXTEND |

---

## FINAL VERDICT

### KEEP
- BookPulse + 11 слоёв (architecture is sound)
- KnowledgeLayer O(1) indexes + RAG
- BookVoice mood detection + metaphor system
- ReaderMemoryStore + adaptive profiles
- WorldEngine coordination pattern
- RelationGraph BFS/shortest path
- ConsistencyEngine rule system
- CompatibilityChecker 6-axis model
- NameResolver canonical map
- EvolutionTracker diff + snapshot
- ChromaDB RAG pipeline
- FormEngine + 55 forms library
- ExperienceEngine 10 modes
- aethon.xray observability
- IdentityLayer policy

### EXTEND
- SourceLevel → add ProvenanceCategory
- WorldModel → add temporal chain + arkaim focus
- RelationGraph → add epoch-based relations
- FormEngine → enrich entities with form data
- ExpansionLayer → integrate pipeline output
- VisualGenome → add SQLite persistence
- ExternalSources → add provenance tagging

### ADD
- TemporalReconstructionEngine (TODAY→HISTORY→ARKAIM)
- ArkaimCore module (unified Arkaim data access)
- ProvenanceController (centralized provenance management)
- ExternalKnowledgeFirewall (canon protection)
- FutureExtrapolator (ARKAIM→FUTURE)
- 6 new API endpoints

### REPLACE
- ~~GraphEngine~~ → deprecate in favor of RelationGraph + WorldModel
- ~~In-memory VisualGenome~~ → SQLite-backed VisualGenomeStore

### DO NOT TOUCH
- SOURCE_OF_TRUTH/ (author sources are immutable)
- GENOME v1.0.0 (read-only reference)
- ComfyUI integration (environment constraint)
- Auth/OAuth layer (working, out of scope)
- Frontend routes (existing pages functional)
- CI/CD pipeline (working)

---

**M0 завершён. Код не изменён.**
**Следующий шаг: M1 — Provenance Controller Foundation**
