# MILESTONE D — BOOK INTELLIGENCE PIPELINE — Report

**Milestone:** D — Book Intelligence Pipeline
**Дата:** 2026-09-15
**Статус:** IMPLEMENTED + TESTED
**Результат:** 269 tests, 0 failures

---

## Простыми словами

1. **Что было целью?** — Построить реальный pipeline: книга → чанки → embeddings → vector store → retrieval → provenance → ответ. Без mock/stub.

2. **Что реально сделано?** — (а) Проведён forensic audit существующей инфраструктуры; (б) добавлен `chromadb` в зависимости; (в) provenance для retrieval результатов (AUTHOR_CANON для текста книги); (г) KnowledgeLayer RAG path исправлен: книжный текст = AUTHOR_CANON, не DERIVED; (д) retrieval результаты теперь содержат chunk_id, source, provenance_category, chapter_number; (ё) uncertainty при слабом retrieval; (ж) 28 новых тестов.

3. **Что получилось?** — PASS. Существующая инфраструктура (SemanticChunker, BookRetriever, ChromaDB, KnowledgeKernel) — рабочая. Не потребовалось строить с нуля — нужно было починить provenance и зависимости.

4. **Есть ли проблемы?** — Embedding model mismatch (config vs runtime) — отложено до решения о пересоздании индекса. Две параллельные ChromaDB коллекции — отложено до консолидации.

---

## 0. Forensic Audit Findings

### Что уже существует и работает

| Компонент | Статус | Путь |
|-----------|--------|------|
| Текст книги | ✅ EXISTS | `core/SOURCE_OF_TRUTH/BOOK/КНИГА.md` (115K chars, 2566 lines) |
| BOOK_DOCUMENT.json | ✅ EXISTS | `core/KNOWLEDGE/BOOK_DOCUMENT.json` (17 chapters, 824 paragraphs) |
| SemanticChunker | ✅ IMPLEMENTED | `core/CORE/intelligence/chunker.py` (5 стратегий) |
| BookRetriever | ✅ IMPLEMENTED | `core/CORE/intelligence/retriever.py` (ChromaDB + fallback) |
| IndexEngine | ✅ IMPLEMENTED | `core/CORE/book_os/index_engine.py` |
| KnowledgeKernel | ✅ IMPLEMENTED | `core/CORE/intelligence/kernel.py` (оркестратор) |
| ChromaDB | ✅ POPULATED | `core/CHROMA_DB/` (8 HNSW segments, 2 коллекции) |
| Enriched data | ✅ GENERATED | `enriched_chunks.json` (20K lines), `enriched_catalog.json` (10K lines) |

### Что было исправлено

| Проблема | Решение |
|----------|---------|
| `chromadb` не в requirements.txt | Добавлен `chromadb>=0.4.0` |
| RAG provenance = DERIVED вместо AUTHOR_CANON | Исправлено: текст книги = AUTHOR_CANON |
| Catalog text provenance = DERIVED | Исправлено: catalog = AUTHOR_CANON |
| Retrieval results без provenance_category | Добавлено `provenance_category`, `chunk_id`, `source`, `chapter_number` |
| Нет uncertainty при слабом retrieval | Добавлен UncertaintyFlag при score < 0.7 |
| Catalog fallback без provenance полей | Добавлены `chunk_id`, `source`, `provenance_category` в fallback |

### Что отложено

| Проблема | Причина отложения |
|----------|------------------|
| Embedding model mismatch (config=`multilingual-e5-small`, runtime=`all-MiniLM-L6-v2`) | Требует пересоздания всех индексов — отдельный milestone |
| Две параллельные коллекции (`arkaim_book` vs `book_os_index`) | Требует консолидации — отдельный milestone |

---

## 1. Source of Truth

**Canonical source:** `core/SOURCE_OF_TRUTH/BOOK/КНИГА.md`
- 115,828 characters
- 2,566 lines
- 17 chapters (Parts 0-16 + Prologue + Epilogue)
- 824 paragraphs

**Processed:** `core/KNOWLEDGE/BOOK_DOCUMENT.json`
- Chapters with `char_start`/`char_end` positions
- Paragraphs with `chapter_id`, `id`, `text`

---

## 2. Chunking Pipeline

**Module:** `core/CORE/intelligence/chunker.py`

5 стратегий:
1. `chunk_by_paragraph()` → 824 chunks (по абзацу)
2. `chunk_by_chapter()` → 17 chunks (по главе)
3. `chunk_hybrid()` → 841 chunks (абзацы + главы)
4. `chunk_by_subparagraph(max_size=500)` → длинные абзацы разбиваются
5. `chunk_by_sliding_window(size=400, overlap=100)` → перекрывающиеся окна

**Каждый chunk содержит:**
- `id` — стабильный MD5-based ID
- `text` — текст абзаца
- `chapter_id`, `chapter_title`, `chapter_number`
- `paragraph_id`
- `char_start`, `char_end` — позиции в исходном тексте
- `source` = `"book"`

---

## 3. Retrieval Path (после исправлений)

```
User query
  ↓
KnowledgeLayer.respond_to(query)
  ↓
[1] catalog_texts keyword match → PulseResponse(provenance=AUTHOR_CANON)
  ↓
[2] BookRetriever.search(query)
    ├─ ChromaDB.collection("arkaim_book").query(query_texts=...)
    │   → results with: text, score, chunk_id, chapter_title, source, provenance_category
    └─ fallback: enriched_catalog.json + genome keyword match
        → results with: text, score, chunk_id, source, provenance_category
  ↓
PulseResponse(
    provenance=[ProvenanceTag(AUTHOR_CANON)],
    uncertainty=UncertaintyFlag if score < 0.7
)
  ↓
KeeperAgent.get_provenance_dicts() → API JSON
```

---

## 4. Changes Made

| Файл | Изменение |
|------|-----------|
| `runtime/requirements.txt` | Добавлен `chromadb>=0.4.0` |
| `core/CORE/intelligence/retriever.py` | Добавлены `chunk_id`, `chapter_number`, `source`, `provenance_category` в ChromaDB и fallback результаты |
| `core/CORE/pulse/layers.py` | RAG provenance: DERIVED → AUTHOR_CANON; catalog provenance: DERIVED → AUTHOR_CANON; uncertainty при слабом retrieval |
| `runtime/tests/test_book_intelligence.py` | 28 новых тестов |

---

## 5. Tests

### Новый файл: tests/test_book_intelligence.py — 28 тестов

| Test Class | Тестов | Что проверяет |
|-----------|--------|---------------|
| TestBookSource | 5 | Книга существует, UTF-8, главы, BOOK_DOCUMENT.json |
| TestChunking | 7 | Чанкинг, стабильность ID, метаданные, нет потерь текста |
| TestVectorStore | 5 | ChromaDB директория, SQLite, HNSW, enriched data |
| TestRetrieval | 5 | provenance_category, chunk_id, score, source, AUTHOR_CANON |
| TestEndToEndProvenanceFlow | 3 | Provenance от retrieval до API dict, uncertainty |
| TestEmbeddingConfig | 3 | Модель настроена, мультиязычная, CHROMA_DIR |

### Regression

```
test_book_intelligence.py:        28 passed
test_provenance_completion.py:    20 passed
test_provenance.py:               55 passed
test_data_discipline.py:          25 passed
test_temporal_model.py:           86 passed
test_narrative_world_model.py:    26 passed
test_m8_1_present_anchor.py:      29 passed
────────────────────────────────────────────
ИТОГО:                           269 passed, 0 failed
```

---

## 6. Pre-existing ошибки

- 18 `PermissionError: [WinError 5]` в store tests — не связаны с изменениями.

---

**STOP. Milestone завершён. Следующий: C. Knowledge Cards + Cross-Source.**
