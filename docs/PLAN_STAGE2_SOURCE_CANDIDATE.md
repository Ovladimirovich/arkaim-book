# PLAN_STAGE2_SOURCE_CANDIDATE
**Статус:** реализовано и протестировано (все целевые тесты зелёные)
**Связь с Stage 1:** работает поверх Knowledge Core → Dialogue Context из Stage 1.
**Предназначение:** формальное задание Stage 2 — Source → Candidate → Validation → Knowledge Core, интегрированное с /book/ask управляемым, не автономным путем.

---

## 1. Архитектурный контракт

### 1.1 Поток

`	ext
QUESTION / GAP
      ↓
SOURCE SEARCH
      ↓
CANDIDATE EXTRACTION
      ↓
ENTITY / RELATION RESOLUTION
      ↓
VALIDATION
      ↓
ACCEPT / REVIEW / REJECT
      ↓
KNOWLEDGE CORE
      ↓
WORLD MODEL
      ↓
DIALOGUE
`

### 1.2 Правило разграничения

> Отсутствие structureClaim в Knowledge Core **не** является доказательством отсутствия факта в книге.
>
> Gap означает только: **подтверждённого structureзированного знания сейчас недостаточно** для выдачи ответа без UX-фрагментации.


## 2. Компоненты

### 2.1 AskGapDetector
Место: 
untime/core/services/ask_gap_detector.py
На вход: question, existing_dialogue_context, existing_knowledge_core.
На выход: GapReport:
- question
- status: KNOWN | PARTIALLY_KNOWN | MISSING | CONFLICTING
- missing_knowledge_area
- relevant_entities: [str]
- relevant_claims: [dict]
- evidence_available: int
- source_search_required: bool
- confidence: float
- detected_from: [...]

**Реализация:**
- Использовать 
esolve_related_entities (runtime/core/services/related_entities.py) для поиска сущностей по вопросу.
- Использовать gather_knowledge_core_context (runtime/core/services/knowledge_core_context.py) для определения наличия structureзированного знания.
- Порог определения: если knowledge_core содержит подходящие факты для существенной части вопроса -> KNOWN; если есть слабые корни -> PARTIALLY_KNOWN; если сущности есть, но structureзированных фактов недостаточно -> MISSING; если есть противоречащие факты -> CONFLICTING.
- TemporalReconstructionEngine.detect_gaps() используют **только** для временной цепи. Не превращать в общий gap engine.

### 2.2 AskExpansionOrchestrator
Место: 
untime/core/services/ask_expansion_orchestrator.py
Последовательность:
`	ext
expand(question, context) -> ExpansionResult
`
Шаги:
1. **Source Search** - Использовать SourceSearcher.search_sources(entity, type=...).
2. **Candidate Extraction** - Использовать JSONExtractor для извлечения из JSON источников.
3. **Entity Resolution** - Использовать NameResolver.resolve() для entity_id.
4. **Relation Resolution** - Проверять subject -> predicate -> object из evidence.
5. **Validation** - Использовать SchemaValidator.validate().
6. **Editorial Gate** - ACCEPT / REVIEW / REJECT.
7. **Storage** - Использовать KnowledgeStore.save().

### 3. Интеграция с /book/ask

**Ограничения:**
- Не делать бэкграунд-запуск без OWNER-GO.
- Не превращать refresh_knowledge() в синхронный ask pipeline.

### 4. Проверки
- Stage 1 tests: make test-backend
- Stage 2 targeted tests для AskGapDetector, AskExpansionOrchestrator, EditorialGate, idempotency, end-to-end question->knowledge.
- make test-backend
