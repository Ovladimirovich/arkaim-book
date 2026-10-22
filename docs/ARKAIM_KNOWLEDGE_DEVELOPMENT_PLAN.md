# ЕДИНЫЙ ОБЩИЙ ПЛАН РАЗВИТИЯ ARKAIM

**Статус:** стратегический архитектурный документ с зафиксированным состоянием реализации  
**Область:** Knowledge / World / Time / Reasoning / Traceability  
**Не входит:** изображения, видео, звук, Studio и отдельный media-проект  
**Frontend:** только существующий `arkaim-web/` как интерфейс к доменной логике  
**Дата актуализации:** 2026-10-01

## 0. Назначение и правила документа

Этот документ отвечает на пять вопросов:

1. Где Arkaim находится сейчас?
2. Какой фундамент уже построен?
3. Каким должен стать Knowledge Core?
4. В каком порядке его развивать?
5. Какой один следующий milestone начинается первым?

Документ **не вводит новую архитектуру**. Он связывает уже существующие World Engine, canonical WorldModel, temporal/event chains, provenance, Book Intelligence Pipeline, Book RAG, Knowledge Cards, ingestion stores и API/contracts в одну причинно-следственную последовательность.

При расхождении статусов приоритет имеют:

1. фактический код;
2. тесты и зафиксированные live-проверки;
3. принятые ADR;
4. `docs/CURRENT_DEVELOPMENT_STATE.md`;
5. backlog и исторические документы.

Исторические B3/B4/F/M-планы и restore backlog не создают разрешения на новую работу. `arkaim-web-v2` не возвращается и не используется как сравнительная база.

---

# CURRENT STAGE

## 1. CURRENT BASELINE: где Arkaim находится сейчас

Arkaim уже не является пустым прототипом. Он имеет работающий связный фундамент из нескольких контуров, но эти контуры ещё не объединены в единый устойчивый Knowledge Core.

### 1.1. Что уже является фундаментом

#### World и canonical identity

- Реализованы `WorldModel`, `WorldEngine`, canonical entity lookup и world context.
- Существует утверждённый первый batch crosswalk: `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`.
- Выполнена ID reconciliation; canonical ID не должен заново изобретаться под каждого потребителя.
- World relations и read-only provenance представлены в реальном API/UI-контуре.
- B3-B Temporal-связи реализованы в `core/CORE/narrative_engine/world_model.py` и подтверждены тестами.

**Решение:** World Engine, canonical WorldModel, entity identity и утверждённый crosswalk — основа, которую нельзя переделывать под Knowledge Cards или reasoning.

#### Temporal и время мира

- Реализован temporal graph с nodes, edges, chains, precision, gaps, anchors и reconstruction.
- `TemporalNode` уже умеет хранить entity/event links, bounds, precision, provenance и confidence.
- Есть «Время мира»: эпохи, порядок, `BACKWARD`/`FORWARD`, present anchor и future extrapolation.
- `TemporalRelation.precedes()` корректно помечается как `DERIVED`, а не `AUTHOR_CANON`.
- Реализованы refresh/reconstruction flow и M10-подобный suggest-only цикл: книга меняется → findings → pending → owner confirm/reject → только затем допустимое обновление WorldModel и temporal refresh.
- M10 API имеет RBAC и pending/confirmed/rejected history.

**Решение:** Temporal graph и неизменяемость канона до подтверждения — существующий foundation, а не новая подсистема Knowledge.

#### Provenance / epistemic model

- В `core/CORE/narrative_engine/source_levels.py` уже разделены два измерения:
  - `ProvenanceCategory` — **откуда/какого типа** утверждение;
  - `confidence` — **насколько уверены** в утверждении.
- Существуют категории `AUTHOR_CANON`, `DERIVED`, `EXTERNAL_SOURCE`, `RECONSTRUCTION`, `HYPOTHESIS`, `FUTURE_EXTRAPOLATION`, `UNKNOWN` и другие.
- Provenance сохраняется через Pulse → API serialization и не повышает hypothesis до canon.
- World provenance инвентаризирован и доступен read-only.

**Решение:** epistemic vocabulary и двумерность category/confidence — основа Knowledge Core; их нельзя заменять одним числом или одним `type`.

#### Book Intelligence и Book RAG

- Канонический текст книги, `BOOK_DOCUMENT.json`, semantic chunking, enrichment, catalog и Chroma retrieval существуют.
- Retrieval возвращает `chunk_id`, source, score и provenance category.
- Book Intelligence tests подтверждают стабильные chunk IDs, отсутствие пустых chunks, metadata и canon category.
- RAG/Pulse flow уже умеет отвечать с provenance и uncertainty.

**Решение:** Book RAG — потребитель Knowledge Core и источник evidence, но не место, где заново определяется семантика claims.

#### Knowledge Cards и cross-source aggregation

- `core/CORE/knowledge_card/models.py` уже задаёт entity-centric Knowledge Card.
- `CardClaim` имеет claim-level `ProvenanceTag`, `source_ref`, optional `chunk_id`, chapter metadata и notes.
- Builder уже агрегирует book, WorldModel, archaeology, cross-references и academic sources без epistemic blending.
- Разные источники и перспективы сохраняются раздельно; отсутствие источника не заменяется fabricated provenance.
- Read-only API реализован, подключён и имел live HTTP 200 evidence.
- Модель уже допускает `contradictions`, `uncertainty`, relations и related entities, хотя автоматическое наполнение этих секций пока не реализовано.

**Решение:** Knowledge Card — правильная внешняя проекция Knowledge Core, но текущий builder — тонкий read-only aggregator, а не каноническое хранилище knowledge semantics.

#### Ingestion и graph stores

- В `core/CORE/book_os/` существуют source/entity/fact/relationship stores, provenance registry, index engine и ingestion orchestrator.
- Pipeline выполняет validation → source registration → chunking → enrichment → extraction → conflict check → save → provenance registration → indexing.
- `FactStore` уже хранит атомарные statements с entity/document/chunk/provenance/confidence.
- `ProvenanceTracker` умеет строить ограниченную derived→source chain.
- Conflict pipeline и provenance validator реализованы, но их семантика уже, чем Knowledge Card epistemic model.

**Решение:** Book OS — важный ingestion foundation. Плану нужна тонкая compatibility boundary, а не параллельная вторая система фактов.

### 1.2. Что реально работает и доказано

Согласно `docs/CURRENT_DEVELOPMENT_STATE.md`, контрольным прогонам 2026-10-01 и live-верификации 2026-10-02 (`docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`, HEAD `1e3f812`):

| Контур | Уровень доказательства |
|---|---|
| Knowledge Cards backend | IMPLEMENTED / TESTED / LIVE CONFIRMED; live 2026-10-02: search/card/trace возвращали HTTP 200, фильтры/pagination/totals подтверждены |
| Knowledge Card builder | IMPLEMENTED / TESTED; 43 тест-функции в `test_knowledge_cards.py`. **Re-baseline 2026-10-11 (HEAD `1e3f812`, коммит 2026-10-02): targeted Knowledge Core regression (20 файлов) — 333 collected / 333 passed / 0 failed** (до фикса GO-8 было 330/329/1 — BASELINE-1, устранён 2026-10-11: genome-fallback исключён из `_book_claims`) |
| Book Intelligence/RAG | TESTED: source, chunking, metadata, retrieval, provenance и uncertainty |
| World/B3-B/provenance | TESTED: 8 целевых core-тестов |
| World provenance UI | IMPLEMENTED / TESTED / VERIFIED ранее, код после browser evidence не менялся |
| Frontend unit suite | 70/70 на контрольном прогоне |
| M10 temporal updates | TESTED: suggest-only, idempotency, confirm/reject, RBAC, canonical hash protection |
| Pending Updates API | TESTED: семь endpoint-ов, auth matrix, history, isolation |
| Current `arkaim-web` | Единственный frontend; отдельный Knowledge Cards route отсутствует (компонент `KnowledgeTraceCard` реализован в M9 внутри World Engine Context) |

Эти результаты не означают полного Knowledge reasoning: отсутствующие части не должны объявляться готовыми по косвенным признакам.

### 1.3. Что частично реализовано

1. **Knowledge Cards:** агрегируют claims, но строятся в основном представлением (`read()` из JSON/World/RAG), а не как полноценный write/read Knowledge Core с устойчивыми IDs, lineage и evidence graph.
2. **Claim semantics:** есть `CardClaim`, `Fact` и `ProvenanceTag`, но это разные модели с разными enum и полями; единая утверждённая семантика не зафиксирована.
3. **Source references:** `source_ref` и `chunk_id` есть, но для всех типов источников нет строгого resolver-контракта и проверки существования evidence.
4. **Confidence/uncertainty:** числа присутствуют, но aggregate confidence в карточке сейчас вычисляется по наличию источника и не имеет общей калибровочной семантики.
5. **Relations:** relations извлекаются и возвращаются, но claim provenance не переносится на relation автоматически; отдельного relation provenance contract нет.
6. **Conflicts:** `KnowledgeCard.contradictions` пуст; Book OS conflict resolver блокирует ingestion при heuristic conflicts; отдельного semantic conflict layer нет.
7. **Reasoning:** есть consistency/contradiction/LLM-слои в других контурах, но нет единого typed cross-source reasoning result с preserved input lineage.
8. **Temporal provenance correction:** есть pending-update и refresh flow, но нет общего lineage/correction model, связывающего старую интерпретацию, новое evidence, решение owner и все затронутые derived claims.
9. **Traceability:** component provenance проходит стек, однако полный путь `claim → evidence → source → supporting claims → world entity/event → status` не является единым проверяемым контрактом.

### 1.4. Что является TODO

- Единый Knowledge claim contract и compatibility mapping для существующих моделей.
- Evidence records/fragments, связывающие claims с конкретными фрагментами источников.
- Entity relation provenance semantics.
- Автоматическое сохранение semantic conflicts и competing interpretations.
- Derived knowledge с явным списком input claim IDs и inference provenance.
- Temporal correction lineage.
- Knowledge query/reasoning API как стабильный потребительский контракт.
- User-facing Knowledge Card/provenance/conflict/reasoning view после стабилизации ядра.
- Live verification browser-ветки и подтверждение conflicts/reasoning/corrections/lineage на production-записях (хранилище `runtime/runtime_data/knowledge/` пусто).

Live verification **backend-ветки** Knowledge Core выполнена 2026-10-02 (см. `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`): auth/search/card/trace, фильтры, pagination, `totals`/`next_offset`, claim → evidence → source → world/temporal и фактические `RESOLVED`/`UNAVAILABLE`/`UNKNOWN` подтверждены; расхождения факта с контрактными формулировками перечислены в отчёте и не исправлялись.

### 1.5. Технический долг, влияющий на Knowledge Core

1. **Два несовместимых provenance vocabularies:**
   - `ProvenanceCategory` в `narrative_engine.source_levels`;
   - строковые `source|derived|interpretation|external|hypothesis|genome` в `schemas.Fact/Provenance`.
2. **`CardClaim.source_ref` не является универсальным typed reference resolver-ом.**
3. **`FactStore.add()` перезаписывает по ID, а `ProvenanceTracker` хранит registry отдельно:** риск orphan/mismatch записей.
4. **`ProvenanceTracker.get_chain()` выбирает первую source-fact той же entity и не хранит точный список inputs derived claim-а.**
5. **`FactStore` и Knowledge Card builder имеют разные модели lifecycle/versioning.**
6. **Conflict detection разбросан:** ingestion heuristic, narrative contradiction detector и пустой `KnowledgeCard.contradictions` — это разные предметы, терминология частично пересекается.
7. **Relation provenance не является first-class**, хотя relation data уже возвращается в карточке.
8. **Book OS persistence — JSON files**, тогда как WorldModel и runtime имеют другие persistence paths; migration/cutover strategy не зафиксирована.
9. **Full traceability journey доказан только частично:** общий journey есть (`runtime/tests/test_m8c_trace_journey.py`) и его backend-ветка подтверждена live-прогоном 2026-10-02 (claim → evidence → source → world/temporal), но M5→M6→M7 lineage подтверждается пока только тестами — production-записей конфликтов/рассуждений/правок в live нет.

### 1.6. Что не следует перерабатывать заново

- World Engine и canonical identity flow.
- Утверждённый B3 crosswalk; его нельзя молча расширять.
- WorldModel/Temporal model и их guard-инварианты.
- `ProvenanceCategory` + confidence как два независимых измерения.
- Book source/chunk/enrichment/retrieval pipeline.
- Существующие F2/F3 contracts, если конкретный код/contract не противоречит этим границам; менять их в этом плане нельзя.
- Pending temporal update gate и RBAC.
- Текущие read-only Knowledge Cards API как compatibility surface.
- Единственный `arkaim-web`; frontend развивается только как consumer зрелого ядра.

---

# TARGET ARCHITECTURE

## 2. Как должно выглядеть рабочее ядро Arkaim

Ядро должно быть **traceable knowledge system поверх существующего World Engine**, а не отдельной базой «фактов о книге» и не набором агрегированных карточек.

### 2.1. A. Knowledge

#### Claim

Claim — минимальная адресуемая единица утверждения. Он должен иметь устойчивый ID и отвечать:

- что именно утверждается;
- к какой сущности относится;
- какова epistemics provenance category;
- каков confidence/uncertainty;
- какие evidence поддерживают claim;
- является ли claim source claim, derived knowledge, system interpretation или user hypothesis;
- какие conflicts/alternatives существуют.

#### Knowledge Card

Knowledge Card — **entity-centric read projection** над Knowledge Core. Она не становится вторым authority store. Карточка должна собирать claims и relations через canonical entity ID, сохраняя независимые источники и derived layers.

#### Source

Source — идентифицируемый origin: book, archaeology corpus, academic work, cross-reference collection, WorldModel artifact или иной зарегистрированный provider. Source должен иметь stable identity, тип, title/URL при наличии и integrity/version metadata. Отсутствующие данные остаются `null`/unknown.

#### Provenance

Knowledge provenance отвечает, **откуда взялось утверждение**, но не подменяет World provenance и не копируется на relation или event без отдельного основания.

#### Confidence / uncertainty

- `confidence` — локальная уверенность в конкретном claim/evidence assessment.
- `uncertainty` — явные неизвестные, gaps, competing interpretations и limitations.
- Они не равны `certainty`; высокая confidence при `HYPOTHESIS` не делает hypothesis canon.

#### Relations и evidence

- Relation — отдельный адресуемый knowledge object со своим provenance.
- Evidence — конкретный source fragment/spans/locations, поддерживающие один или несколько claims.
- Knowledge не должно утверждать наличие evidence только потому, что агрегатор знает имя файла.

### 2.2. B. World

- Entities берут identity из World Engine/canonical WorldModel.
- Knowledge layer ссылается на canonical entity IDs, не создавая конкурирующие identity.
- WorldModel остаётся canonical state representation.
- Knowledge builder получает World claims и World relations через существующий World Engine API/contracts.
- Knowledge не изменяет WorldModel и crosswalk; confirmed temporal updates идут только через существующий M10-style confirmation gate.

### 2.3. C. Time

- Events/epochs/chains остаются в Temporal subsystem.
- Claims связываются с `event_ids`, `era_id`, temporal node ID и precision/validity bounds, если такая связь подтверждена.
- «Время мира» отличается от времени публикации, ingestion и system execution.
- Изменение temporal interpretation порождает correction/lineage record, а не молчаливое перезаписывание старого claim.

### 2.4. D. Reasoning

Reasoning — детерминированный или LLM-assisted процесс, который:

1. получает конкретные claims/evidence;
2. сохраняет IDs всех inputs;
3. создаёт отдельный derived claim;
4. маркирует его `DERIVED` либо соответствующую interpretation/reconstruction category;
5. указывает rule/method/model и uncertainty;
6. не выдаёт derived output за source claim или established fact;
7. не удаляет альтернативы/conflicts.

Cross-source reasoning может сравнивать утверждения из разных источников, но не смешивает их provenance. Conflict detection может быть первым этапом reasoning или отдельным результатом.

### 2.5. E. Traceability

Целевой обязательный путь для существенного утверждения:

**что утверждается → claim → evidence/fragments → source → epistemic category → confidence/uncertainty → relations/inputs → canonical entity/event → temporal position → lineage/corrections → derivation/query path**.

Минимальный rule: если путь существенно утверждения обрывается, объект нельзя представить как verified knowledge; он должен иметь явный UNKNOWN или PARTIAL traceability status.

Операционное правило `trace.status` (GO-1, принято 2026-10-11): `COMPLETE` — есть хотя бы одна claim, все evidence-строки `RESOLVED` и нет `limitations`; иначе `PARTIAL` (обрыв пути: evidence `UNAVAILABLE`/`UNKNOWN`, отсутствие resolvable-ссылок, несвязанные M5/M6/M7-записи, неразрешённая сущность). `UNKNOWN` остаётся зарезервированным значением словаря `TraceabilityStatus` и сейчас не выдаётся. Правило статуса опирается на полный набор evidence-строк до секционных фильтров и пагинации. Подтверждено live: `region_arkaim` — 17 `RESOLVED` + 7 `UNKNOWN` evidence → `PARTIAL` (2026-10-11).

### 2.6. Целевая ответственность существующих контуров

| Контур | Ответственность |
|---|---|
| Book Intelligence / Book OS | Приём, chunking, extraction, source/evidence production |
| Knowledge Core | Claims, evidence links, provenance semantics, knowledge lifecycle |
| World Engine / WorldModel | Canonical entities, world state, relations lookup, confirmed world mutations |
| Temporal | Events, epochs, chains, world time, temporal validation/refresh |
| Reasoning | Conflicts, synthesis, derived knowledge, corrections proposals |
| Runtime API/contracts | Стабильная выдача Knowledge Core потребителям |
| Book RAG / Ask | Retrieval и ответ с evidence/provenance/uncertainty |
| `arkaim-web` | Просмотр и управление только через стабильные contracts |

---

# MILESTONES

## 3. Правильная причинно-следственная последовательность

```text
M0 Baseline / stabilization
  ↓
M1 Unified claim + provenance semantics
  ↓
M2 Evidence/source-fragment model
  ↓
M3 World ↔ Knowledge boundary
  ↓
M4 Temporal ↔ Knowledge boundary
  ↓
M5 Competing claims / conflicts
  ↓
M6 Cross-source reasoning
  ↓
M7 Temporal provenance correction lineage
  ↓
M8 Knowledge query/reasoning API
  ↓
M9 User-facing knowledge
  ↓
полноценное Knowledge reasoning operating state
```

Порядок нельзя менять без нового OWNER decision: evidence нельзя окончательно вводить до стабилизации claim; temporal correction — до конфликтов и lineage; API/UI — до устойчивой внутренней семантики.

---

## M0 — Baseline / stabilization

### Цель

Зафиксировать одну исполнимую карту уже существующей knowledge-логики и остановить смешение моделей до начала расширения ядра.

### Что уже существует

- Current development state и audit baseline.
- World Engine/canonical identity/crosswalk.
- ProvenanceCategory/confidence.
- Book Intelligence/RAG.
- Knowledge Card models/builder/API.
- Book OS stores/ingestion/provenance/conflict code.
- Temporal and pending-update gates.
- Current frontend/backend contracts and test evidence.

### Чего не хватает

- Формального mapping table между существующими provenance/claim моделями.
- Списка «contract owner» для Knowledge semantics.
- Зафиксированных unsupported/partial boundaries.
- Одного traceability test scenario, проходящего через существующие компоненты.

### Конкретные подсистемы/файлы

- `docs/CURRENT_DEVELOPMENT_STATE.md`
- `docs/PROJECT_CURRENT_STATE_AUDIT.md`
- `docs/FRONTEND_RESTORE_BACKLOG.md`
- `core/CORE/narrative_engine/source_levels.py`
- `core/CORE/schemas/fact.py`
- `core/CORE/schemas/provenance.py`
- `core/CORE/knowledge_card/models.py`
- `core/CORE/book_os/`
- `runtime/core/routes/knowledge_cards.py`
- `runtime/tests/test_knowledge_cards.py`
- `runtime/tests/test_book_intelligence.py`
- `runtime/tests/test_provenance_completion.py`
- `runtime/tests/test_m10_temporal_updates.py`

### Зависимость

Начальный, без предыдущего milestone.

### Минимальный scope

Только архитектурная спецификация mapping/compatibility и acceptance checklist. Никаких новых endpoint-ов, схем хранения или миграций.

### Что не входит

- Новый общий аудит.
- Изменение кода/API/WorldModel/Temporal/crosswalk.
- Решение окончательного physical storage без отдельного OWNER decision.

### Критерии приёмки

- Каждая существующая claim/fact/card representation отнесена к domain и canonical status.
- Для каждого поля определено: retain / adapt / deprecated later / owner decision required.
- Явно указано, какие существующие tests доказывают каждый baseline-компонент.
- `arkaim-web` и backend названы только потребителями, а не authority store.

### Необходимые тесты

M0 сам по себе не расширяет тесты. Он должен ссылаться на существующие `test_knowledge_cards.py`, `test_book_intelligence.py`, `test_provenance_completion.py`, `test_m10_temporal_updates.py`, `test_m10_2_pending_updates_api.py`, B3/B4 tests и зафиксированные прогоны.

---

## M1 — Unified claim and provenance semantics

### Цель

Утвердить минимальную семантику claim/provenance, совместимую с `CardClaim`, `Fact`, `ProvenanceTag` и Pulse, не создавая новый несвязанный store.

### Что уже существует

- `ProvenanceCategory` и `ProvenanceTag`.
- `CardClaim`.
- `Fact.statement`, entity/doc/chunk/provenance/confidence.
- Fact provenance tracker.
- Pulse serialization tests.

### Чего не хватает

- Одного canonical claim vocabulary и lifecycle.
- Стабильных правил для `unknown`, `source_ref`, confidence и claim status.
- Явного distinction между source claim, derived claim, interpretation, hypothesis и correction candidate.
- Точного определения, что является immutable, а что versioned.

### Конкретные подсистемы/файлы

- `core/CORE/narrative_engine/source_levels.py`
- `core/CORE/knowledge_card/models.py`
- `core/CORE/schemas/fact.py`
- `core/CORE/schemas/provenance.py`
- `core/CORE/book_os/fact_store.py`
- `core/CORE/book_os/provenance_tracker.py`
- `core/CORE/pulse/layers.py`
- `runtime/core/routes/knowledge_cards.py`
- `runtime/tests/test_knowledge_cards.py`
- `runtime/tests/test_provenance.py`
- `runtime/tests/test_provenance_completion.py`

### Зависимость

M0. Все дальнейшие milestones используют эту семантику.

### Минимальный scope

- Один target contract для claim identity, statement/topic, entity refs, category, confidence, source_ref, evidence refs, temporal refs, status и lineage refs.
- Explicit compatibility mapping legacy `Fact.provenance` и `Provenance.type` → `ProvenanceCategory`.
- Правила `UNKNOWN`: отсутствие источника не превращается в source и не заполняется нулевой уверенностью как доказательство отсутствия.
- Политика versioning: source claims могут быть superseded с lineage, но historical record не удаляется.

### Что не входит

- Новый vector DB или graph DB.
- Автоматическое извлечение всех evidence.
- Автоматическое разрешение конфликтов.
- LLM-generated claims в production path.

### Критерии приёмки

- Одна claim может быть round-trip представлена без потери category, confidence, entity, source reference и temporal references.
- `HYPOTHESIS confidence=1.0` остаётся `HYPOTHESIS`.
- Legacy representations имеют однозначный mapping или явный `UNKNOWN + migration-required`, а не молчаливое смешение.
- Existing Knowledge Card API не ломается: допускается compatibility layer, но не два конкурирующих authority semantics.
- Derived claim не может получить provenance первого исходного claim неявно.

### Необходимые тесты

- Contract/schema validation tests для всех categories.
- Round-trip legacy/current mapping tests.
- Hypothesis/derived/external/canon non-promotion tests.
- Missing source/unknown tests.
- Duplicate text из разных source refs должен оставаться различаемым, если semantic scope допускает разные evidence.
- Knowledge Card API compatibility tests.

---

## M2 — Evidence and source-fragment model

### Цель

Сделать источник и фрагмент источника проверяемым основанием claim, а не строковым `source_ref`.

### Что уже существует

- SourceStore и document IDs.
- Stable chunk IDs, chapter metadata, char/paragraph metadata.
- Retrieval result с text, chunk ID, score, source.
- `CardClaim.chunk_id` и `source_ref`.
- RAG provenance flow.

### Чего не хватает

- Универсального `Evidence`/`SourceFragment` contract.
- Exact locator/span semantics для book и внешних источников.
- Одного claim ко многим evidence и evidence ко многим claims.
- Проверки reachable source/reference и graceful unknown.
- Явного отделения raw source fragment от нормализованного claim.

### Конкретные подсистемы/файлы

- `core/CORE/book_os/source_store.py`
- `core/CORE/book_os/pipeline/orchestrator.py`
- `core/CORE/intelligence/chunker.py`
- `core/CORE/intelligence/retriever.py`
- `core/CORE/knowledge_card/models.py`
- `core/CORE/knowledge_card/builder.py`
- `core/CORE/schemas/chunk.py`
- `runtime/tests/test_book_intelligence.py`
- `runtime/tests/test_pdf_ingest.py`
- `runtime/tests/test_knowledge_cards.py`

### Зависимость

M1. Evidence нельзя определить стабильно без identity и provenance semantics claim-а.

### Минимальный scope

- Evidence identity: source ID + stable locator + optional span/hash/version.
- Claim-to-evidence explicit links.
- RAG chunk остаётся retrieval artifact, но получает разрешимую reference interpretation.
- Book evidence может указывать chunk/location; внешние sources — свой locator schema.
- Knowledge Card может вернуть evidence summary/links, не копируя весь raw corpus.

### Что не входит

- Новая ingestion platform.
- Семантический NER/LLM rewriting evidence.
- Автоматическое создание факта из каждого retrieval hit.
- Копирование raw source text в каждый claim.

### Критерии приёмки

- Каждый material claim указывает evidence ID либо имеет явный `evidence_status=UNKNOWN`.
- Book claim с `chunk_id` разрешается в существующий chunk/catalog chain.
- Перемещение/обновление исходного документа обнаруживается через version/hash policy.
- Разные claims могут ссылаться на один fragment; один claim — на несколько fragments.
- Retrieval hit не равен evidence claim автоматически; между ними есть явная extraction/assertion step.

### Необходимые тесты

- Stable locator tests для chapter/chunk/paragraph.
- Book chunk existence and metadata tests.
- Multi-evidence/multi-claim link tests.
- Broken/missing source reference tests.
- Deduplication must not collapse claims solely by normalized text when refs differ.
- PDF/plain/JSON ingestion reference tests.

---

## M3 — World ↔ Knowledge boundary

### Цель

Разрешить Knowledge использовать canonical World entities и relations, не превращая WorldModel в evidence store и не создавая новые entity IDs.

### Что уже существует

- WorldModel/WorldEngine.
- Canonical ID reconciliation и crosswalk.
- World claims и relations в KnowledgeCardBuilder.
- Related entities API/service.
- World provenance inventory/API/UI.
- Tests B3/B4.

### Чего не хватает

- Явного typed reference contract между Knowledge и World.
- Политики unresolved/alias/non-canonical entity.
- Раздельного contract для World relation provenance.
- Стабильного behavior при отсутствии World entity, но наличии knowledge source.

### Конкретные подсистемы/файлы

- `core/CORE/narrative_engine/world_model.py`
- `core/CORE/narrative_engine/world_engine.py`
- `core/CORE/narrative_engine/world_provenance.py`
- `core/CORE/knowledge_card/builder.py`
- `core/CORE/knowledge_card/models.py`
- `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`
- `runtime/core/services/related_entities.py`
- `runtime/core/routes/knowledge_cards.py`
- `runtime/core/routes/world.py` либо фактический зарегистрированный world route
- `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`
- `core/CORE/narrative_engine/tests/test_world_provenance.py`

### Зависимость

M1 и M2.

### Минимальный scope

- Knowledge subject всегда использует canonical World entity ID; query alias может быть отдельно.
- `unresolved`, `ambiguous`, `crosswalk_unapproved` — явные состояния.
- WorldModel fields остаются canonical world data; их source history — World provenance.
- Knowledge claim может ссылаться на World entity как context/subject, но World entity record не становится автоматически external source evidence.
- Relation получает собственный relation object/reference, когда доступен; его provenance не наследуется от claim.

### Что не входит

- Расширение crosswalk.
- Изменение WorldModel schema.
- Автоматическое создание/слияние сущностей по похожему тексту.
- Копирование World relation в произвольный source claim.

### Критерии приёмки

- Карточка по canonical ID и по approved alias разрешает одну и ту же World identity.
- Unapproved crosswalk не используется автоматически.
- Отсутствие World entity не ломает Knowledge claim; оно отражается как unresolved context.
- World provenance и Knowledge provenance видны раздельно.
- Relation без relation provenance не получает fabricated badge.

### Необходимые тесты

- Canonical ID/alias regression tests.
- B3-B crosswalk tests без изменения crosswalk.
- Missing/ambiguous entity tests.
- World provenance non-propagation tests.
- Relation provenance isolation tests.
- Existing related-entities and World API contract tests.

---

## M4 — Temporal ↔ Knowledge boundary

### Цель

Привязать claims к времени мира и событиям так, чтобы claim provenance, World time и source publication/ingestion time не смешивались.

### Что уже существует

- Temporal graph/nodes/relations/chains/precision/gaps.
- Entity/event IDs на TemporalNode.
- «Время мира», present anchor, reconstruction/extrapolation.
- M10/M10.2 pending updates, confirmation, RBAC, temporal refresh.
- Temporal API/contracts and frontend.

### Чего не хватает

- Typed temporal references на Knowledge claims.
- Семантики claim validity versus point-in-time/world position.
- Раздельного source date, ingestion time, assertion time и world time.
- Стабильного способа привязать claim к event/era без изменения Temporal model.

### Конкретные подсистемы/файлы

- `core/CORE/narrative_engine/temporal/node.py`
- `core/CORE/narrative_engine/temporal/relation.py`
- `core/CORE/narrative_engine/temporal/reconstruction_engine.py`
- `core/CORE/narrative_engine/world_model.py`
- `core/CORE/narrative_engine/research/temporal_extractor.py`
- `core/CORE/narrative_engine/research/temporal_update_manager.py`
- `core/CORE/knowledge_card/models.py`
- `runtime/core/routes/temporal_updates.py`
- `arkaim-web/src/shared/api/contracts/temporal.ts`
- `runtime/tests/test_temporal_model.py`
- `runtime/tests/test_m10_temporal_updates.py`
- `runtime/tests/test_m10_2_pending_updates_api.py`

### Зависимость

M1, M2, M3.

### Минимальный scope

- Knowledge claim может иметь temporal refs: event ID, era ID, temporal node ID, precision и optional bounds.
- `UNKNOWN` time остаётся unknown; отсутствие даты не заполняется текущим anchor-ом по умолчанию.
- Прямое утверждение книги и derived temporal order сохраняют разные categories.
- Любая mutation WorldModel/Temporal идёт только через существующий confirmed update flow.

### Что не входит

- Перестройка Temporal graph.
- Автоматическое принятие extracted dates.
- Новый temporal UI/API.
- Изменение anchor или crosswalk semantics.

### Критерии приёмки

- Claim at time of world может вернуть event/era/precision/bounds с сохранением source provenance.
- Exact, relative, reconstructed, extrapolated и unknown categories не смешиваются.
- Reader не может изменить WorldModel/Temporal.
- Pending extraction не меняет canonical state до confirm.
- Existing M10/M10.2 contracts и World/Temporal tests проходят.

### Необходимые тесты

- Claim temporal-reference round trip.
- Author canon vs derived precedence tests.
- Unknown time tests.
- Existing temporal graph/chain/path tests.
- M10 confirm/reject, idempotency, RBAC и canonical hash tests.
- Cross-contract test Knowledge Card ↔ Temporal API IDs.

---

## M5 — Competing claims and conflicts

### Цель

Сохранять противоречащие утверждения и разные интерпретации как данные, не теряя source lineage и не объявляя одно истинным без основания.

### Что уже существует

- `ContradictionNote` в KnowledgeCard models.
- Book OS `ConflictResolver` и heuristic validator.
- Narrative `ContradictionDetector` для cause-effect trees.
- Provenance precedence и high-severity ingestion gate.
- User hypothesis categories.

### Чего не хватает

- Semantic conflict classifier для claims одного subject/predicate.
- Разделения factual conflict, temporal conflict, source perspective и narrative consistency violation.
- Conflict record с exact claim IDs, evidence IDs, type, severity basis и resolution status.
- Стабильного rule: conflict не удаляет claims и не объединяет их текст.
- Owner resolution/rejection с lineage.

### Конкретные подсистемы/файлы

- `core/CORE/knowledge_card/models.py`
- `core/CORE/knowledge_card/builder.py`
- `core/CORE/book_os/pipeline/conflict_resolver.py`
- `core/CORE/book_os/provenance_validator.py`
- `core/CORE/narrative_engine/contradiction_detector.py`
- `core/CORE/narrative_engine/source_levels.py`
- `runtime/core/routes/knowledge_cards.py`
- `runtime/tests/test_knowledge_cards.py`
- `runtime/tests/test_provenance.py`
- narrative contradiction tests

### Зависимость

M1–M4. Без exact claim/evidence/entity/time refs conflict record нестабилен.

### Минимальный scope

- Conflict types, minimum: direct contradiction, temporal incompatibility, incompatible interpretation, source perspective/non-conflict.
- `UNRESOLVED`, `ACCEPTED_AS_PERSPECTIVES`, `RESOLVED_WITH_EVIDENCE`; resolution никогда не удаляет competing claims.
- Severity — policy label с explanation, не автоматический факт.
- LLM может предлагать match/conflict, но deterministic validators имеют приоритет для структурных нарушений.

### Что не входит

- Автоматическое исправление source text.
- Модель, автоматически выбирающая «истинный» источник.
- Изменение ingestion policy до завершения baseline tests.
- UI conflict manager.

### Критерии приёмки

- Два противоречивых book claims остаются двумя claims и формируют один conflict record с двумя claim IDs.
- Отсутствие данных не считается contradiction без явной negative claim.
- Разные временные интерпретации получают temporal conflict, а не source corruption.
- Hypothesis или system interpretation не может silently resolve external evidence.
- Narrative cause-effect contradiction и knowledge claim conflict явно различаются.

### Необходимые тесты

- Direct contradiction positive/negative cases.
- Same text/different sources cases.
- Temporal conflict cases.
- Multiple competing claims and resolution lineage.
- Hypothesis non-promotion.
- Regression tests для existing ConflictResolver.

---

## M6 — Cross-source reasoning

### Цель

Строить derived knowledge из нескольких claims/evidence с полным input lineage и uncertainty, не подменяя источники.

### Что уже существует

- Book, WorldModel, archaeology, cross-reference и academic aggregations.
- `DERIVED`, `RECONSTRUCTION`, `HYPOTHESIS` categories.
- Narrative hypothesis generation, consistency engine, knowledge expansion, Pulse/Ask/RAG.
- Knowledge Card cross-source view.

### Чего не хватает

- Typed inference input/output contract.
- Exact `supports_claim_ids` и source/evidence references на derived claim.
- Deterministic rule sets до LLM-assisted synthesis.
- Uncertainty aggregation semantics.
- Reproduction/version identifier для рассуждения.
- Guardrails против fabricated synthesis.

### Конкретные подсистемы/файлы

- `core/CORE/knowledge_card/models.py`
- `core/CORE/knowledge_card/builder.py`
- `core/CORE/narrative_engine/hypothesis_generator.py`
- `core/CORE/narrative_engine/consistency_engine.py`
- `core/CORE/narrative_engine/relation_extractor.py`
- `core/CORE/narrative_engine/unified_pipeline.py`
- `core/CORE/knowledge_expansion/`
- `core/CORE/pulse/layers.py`
- `runtime/core/routes/book.py`
- `runtime/tests/test_knowledge_kernel.py`
- `runtime/tests/test_book_intelligence.py`

### Зависимость

M1–M5. Reasoning не должно начинаться до стабильных inputs и conflict representation.

### Минимальный scope

- Derived claim создаётся только из явного claim/evidence input set.
- Сохраняются ordered input IDs, method/version, output category, confidence и uncertainty reasons.
- Cross-source aggregation и inference различаются: aggregation не меняет claim, reasoning создаёт новый derived claim.
- Answer/RAG must expose support and limitations without hiding source claims.

### Что не входит

- Автономный агент, меняющий canon.
- Обучение новой модели.
- Универсальный autonomous planner.
- Автоматическое принятие system interpretation за established fact.

### Критерии приёмки

- Каждый derived claim можно полностью реконструировать до input claims/evidence.
- Порядок и method version доступны.
- Unsupported generated text блокируется или маркируется hypothesis.
- Разные source claims остаются видимыми в resulting card/answer.
- Confidence не маскирует uncertainty и не используется как вероятность истины без policy.

### Необходимые тесты

- Two/three-source deterministic inference tests.
- Missing-input rejection tests.
- Input order/idempotency tests.
- LLM stub output lineage tests.
- Hypothesis/interpretation API serialization tests.
- Ask/RAG answer provenance preservation tests.

---

## M7 — Temporal provenance correction

### Цель

Исправлять знания при изменении temporal/historical interpretation с сохранением lineage, approval history и влияния на derived knowledge.

### Что уже существует

- M10 book change detector.
- Temporal extraction.
- Pending update manager.
- Pending Updates API with history, confirm/reject, RBAC.
- Confirmation gate, WorldModel save, temporal refresh.
- Existing provenance preservation.

### Чего не хватает

- Correction record, связывающей superseded claim/interpretation, triggering evidence, decision owner и affected downstream claims.
- Статусов superseded/current/corrected/rejected.
- Автоматического invalidation/recomputation policy для derived claims.
- Ссылки M10 finding на Knowledge claims/evidence.
- Версионированного lineage traversal.

### Конкретные подсистемы/файлы

- `core/CORE/narrative_engine/research/book_change_detector.py`
- `core/CORE/narrative_engine/research/temporal_extractor.py`
- `core/CORE/narrative_engine/research/temporal_update_manager.py`
- `runtime/core/routes/temporal_updates.py`
- `core/CORE/narrative_engine/world_model.py`
- `core/CORE/knowledge_card/models.py`
- `runtime/tests/test_m10_temporal_updates.py`
- `runtime/tests/test_m10_2_pending_updates_api.py`

### Зависимость

M1–M6. Correction нельзя спроектировать без claim lineage, conflict и reasoning inputs.

### Минимальный scope

- Correction proposal создаётся из finding + affected claim/temporal refs.
- До owner confirm ничего не меняется.
- Confirm создаёт новую interpretation/claim version и lineage edges; не переписывает историю.
- Reject сохраняет finding и причину без canonical mutation.
- Affected derived claims получают `stale/needs_recompute`, а не silently falsified status.

### Что не входит

- Автоматическое принятие correction.
- Физическое удаление старой версии.
- Изменение WorldModel/Temporal mechanics.
- Автоматический пересчёт всех downstream claims в первой версии.

### Критерии приёмки

- До confirm canonical hash и WorldModel state неизменны.
- После confirm доступна цепочка old → correction finding → decision → new version.
- Source claim, temporal interpretation и system correction различимы.
- Rejected correction не применяется, но трассируется.
- Superseded derived claims не выдаются как актуальные без статуса.

### Необходимые тесты

- Existing M10 suite must remain green.
- Correction lineage old/new tests.
- Pending/no-mutation tests.
- Confirm/reject history tests.
- Derived invalidation/stale tests.
- Idempotent repeat-confirm tests.
- Canonical data hash tests.

---

## M8 — Knowledge query / reasoning API

### Цель

Сделать устойчивое Knowledge Core доступным Book RAG, Ask и другим потребителям через минимальные read/query contracts и ограниченный reasoning contract.

### Что уже существует

- `/knowledge/cards/search` и `/knowledge/cards/{entity_id}`.
- `/book/ask` и Pulse/RAG response.
- World/Temporal APIs.
- Pending Updates API.
- Typed frontend contracts.
- Auth/RBAC conventions.

### Чего не хватает

- Query filters по entity, claim category, confidence/uncertainty, temporal scope, status.
- Trace endpoint/deep response с claim→evidence→source→lineage.
- Stable DTO names/semantics across Knowledge, World и Temporal.
- Reasoning result contract with inputs/method/uncertainties.
- Pagination/limits/error behavior for large evidence sets.

### Фактическая семантика `search.total` и `uncertainty.has_unknowns` (GO-free; документирование T3, 2026-10-11, HEAD `1e3f812`)

Ниже зафиксировано **то, как реализовано и наблюдается сейчас**. Runtime-поведение и API-контракты не менялись; изменение любого из этих значений — отдельный OWNER-GO.

#### `GET /knowledge/cards/search` → `total` (`runtime/core/routes/knowledge_cards.py:34-103`)

- `total = len(unique)` — это число элементов массива `entities` **в том же ответе** (`:103`). Endpoint объявлен без `response_model`.
- `offset` нет, отдельного счётчика выборки нет: всегда `total == len(entities)` и `total <= limit`.
- `limit`: 1..50, по умолчанию 10; сбор результатов обрывается на `len(unique) >= limit` (`:83`, `:100`).
- Следствие: `total` — **размер возвращённой страницы** (уникальность по `name.casefold()`), а не глобальное число совпадений в каталогах. Запрос с `limit=50`, для которого найдено 14 сущностей, вернёт `total=14`; тот же запрос с `limit=5` — `total=5`.
- Порядок источников: WorldEngine `engine.search(q)` (секция `world_model`), затем, если набрано меньше `limit`, добор из `ARCHAEOLOGY.json` (`sites`) — **без проверки соответствия `q`** (цикл `:87-100` не сопоставляет текст запроса). При нуле совпадений в WorldEngine ответ содержит первые археологические сущности, и `total` равен числу добранных (≤ `limit`), а не 0.
- Пустой `q` → HTTP 422 (`min_length=1`) в формате `detail` (см. PROBLEM №2 / OWNER-GO; формат не менялся).
- Фактические результаты (2026-10-11, TestClient против `core.main.app`):

| `q` | `limit` | `total` | `len(entities)` | происхождение entities |
|---|---|---|---|---|
| аркаим | 10 | 10 | 10 | world (architecture, civilizations, geography, language) + archaeology |
| аркаим | 3 | 3 | 3 | world |
| аркаим | 1 | 1 | 1 | world |
| аркаим | 50 | 14 | 14 | world + archaeology |
| мир | 50 | 28 | 28 | world + archaeology |
| мир | 5 | 5 | 5 | language |
| город | 5 | 5 | 5 | architecture, geography |
| богиня | 5 | 5 | 5 | только archaeology (world не дал совпадений) |
| zzznonexistentq | 5 / 8 | 5 / 8 | 5 / 8 | **только archaeology, добор без фильтра по `q`** |
| Аркаимская долина | 10 | 10 | 10 | только archaeology |
| `` (пусто) | 5 | — | — | HTTP 422 `{"detail": …}` |

- Наблюдение (не исправлялось в T3): round-trip `search → card` неполный — при `q=аркаим&limit=50` 4 из 14 `entity_id` (`archaeology:каргонодская_культура`, `archaeology:страна_городов_(археологический_термин)`, `archaeology:болгарский_государственный_историко-архитектурный_музей-заповедник`, `archaeology:карьякская_(карийская)_культура`) дают HTTP 404 на `/knowledge/cards/{entity_id}`.
- Потребителя поля `total` в `arkaim-web/src` нет (см. addendum к live-отчёту 2026-10-02).

#### `uncertainty.has_unknowns` (`core/CORE/knowledge_card/builder.py:621-639`, `:727-756`)

- Это **card-level агрегат**: `has_unknowns = bool(unknown_aspects)` (`:754`), где `unknown_aspects` — список строк из четырёх источников:
  1. `resolved is None` → «Сущность не найдена ни в одном структурном источнике»;
  2. пустые book claims → «Нет подтверждений из текста книги»;
  3. пустые archaeology claims → «Нет подтверждений из археологических источников»;
  4. строки из `unsolved` у разрешённой entity (в данных `WORLD_MODEL` на 2026-10-11 таких сущностей нет — ветка формально реализована, фактически не срабатывает).
- **Не зависит от evidence-статусов:** секция `uncertainty` в trace — passthrough карточки (`knowledge_cards.py:458`), равенство `trace.uncertainty == card.uncertainty` подтверждено для всех проверенных сущностей; 7 строк `UNKNOWN` evidence у `region_arkaim` сосуществуют с `has_unknowns=false`.
- **Не зависит от `trace.status` и `limitations`** (их логика — PROBLEM №1, отдельный OWNER-GO).
- Уровни доступа: `/knowledge/cards/{entity_id}` для несуществующей сущности возвращает **404** (`:495`), поэтому `has_unknowns=true` с аспектом «Сущность не найдена…» на карточке не отдаётся; `/knowledge/cards/trace/{entity_id}` для той же сущности возвращает **200 + `status=PARTIAL`** с этим `uncertainty` и `limitations`; у builder напрямую — `has_unknowns=true`.
- Фактические результаты (2026-10-11):

| Сценарий | book / arch claims | `has_unknowns` | `unknown_aspects` | card HTTP |
|---|---|---|---|---|
| `region_arkaim` | 4 / 13 | `false` | `[]` (при 7 `UNKNOWN` evidence в trace) | 200 |
| `arkaim_settlement` | 4 / 13 | `false` | `[]` | 200 |
| `geo_гардарика_(страна_городов)` | 0 / 9 | `true` | «Нет подтверждений из текста книги» | 200 |
| `lang_гардарикия_(страна_городов)` | 1 / 0 | `true` | «Нет подтверждений из археологических источников» | 200 |
| `archaeology:гёбекли-тепе`, `archaeology:синташта`, `archaeology:мехенго` | 0 / 7–8 | `true` | «Нет подтверждений из текста книги» | 200 |
| `__nonexistent_entity_xyz__` | 0 / 0 | `true` | все три аспекта (включая «Сущность не найдена…») | 404 на card, 200/PARTIAL на trace |

- Семантика зафиксирована для двух полей как есть; расширение `unknown_aspects` на evidence-пробелы или перевод `total` на глобальный счётчик — наблюдаемое изменение поведения поля API и потому требует отдельного OWNER-GO.

#### Claim ↔ evidence join в trace (реализовано T4, 2026-10-11; additive)

Каждая evidence-строка `GET /knowledge/cards/trace/{entity_id}` теперь несёт поле `claim_id` (`runtime/core/routes/knowledge_cards.py`, `_evidence_projection`):

- значение вычисляется **тем же мостом** `_card_claim_id(claim)`, что и поле `claim_id` в claims-секции, поэтому claim и её evidence-строка согласованы по identity;
- **fail-closed:** если соответствие нельзя достоверно установить — `null` (нет `text`; `book:` без `chunk_id`; схема вне allowlist `book:` / `ARCHAEOLOGY.json:` / `external:`, напр. `genome:theme:…` и `world_model:…`);
- **статус резолвера не участвует в identity:** RESOLVED и UNAVAILABLE несут `claim_id`, UNKNOWN без стабильного чанка остаётся `null` — статус ни не создаёт, ни не убирает идентификатор;
- строки без `source_ref` и `chunk_id` по-прежнему не проецируются (fabrication отсутствует);
- контракт: секции trace остаются `list[dict]` (`runtime/core/dto/knowledge.py:19-26`), DTO и M2-схемы не менялись; поле добавлено в JSON-строку как additive.

Проверено (2026-10-11): book claim с chunk (identity совпадает с claims-секцией), UNAVAILABLE book claim (`evidence_id=null` при `claim_id`), археологический external-locator (`external:archaeology:…`), genome/world refs и claim без text (все `null`), journey на реальном `region_arkaim` (evidence `claim_id` ⊆ claims-секции, book-строки покрыты, `world_model:` → `null`); baseline 20 файлов — **338 passed / 0 failed**.

### Конкретные подсистемы/файлы

- `runtime/core/routes/knowledge_cards.py`
- `runtime/core/routes/book.py`
- `runtime/core/routes/related_entities.py`
- `runtime/core/routes/temporal_updates.py`
- `runtime/core/dto/requests.py`
- `runtime/core/main.py`
- `arkaim-web/src/shared/api/contracts/`
- `runtime/tests/test_knowledge_cards.py`
- `runtime/tests/integration/test_book_api.py`
- `runtime/tests/test_provenance_completion.py`

### Зависимость

M1–M7. API не должен компенсировать неопределённую внутреннюю семантику.

### Минимальный scope

- Read-only query/trace DTOs поверх принятой модели.
- Filters и stable status vocabulary.
- Ask/RAG retrieval получает evidence/provenance/uncertainty/temporal context.
- API скрывает внутренние storage details, но не теряет IDs для traceability.
- Backward compatibility текущих Knowledge Card routes обязательна.

### Что не входит

- UI Knowledge Cards.
- Автоматическое mutation API.
- Новый gateway/service mesh.
- Полный rerank/search redesign.

### Критерии приёмки

- Один query может вернуть claims с exact source/evidence refs, category, confidence, uncertainty, entity и time.
- Derived claim возвращает input lineage.
- Temporal/current/superseded statuses различимы.
- API responses валидируются typed schemas и не превращают unknown source в fabricated data.
- Existing card routes и Ask remain compatible.

### Необходимые тесты

- DTO/contract tests.
- Query/filter/pagination tests.
- Trace completeness tests.
- Unknown/empty result tests.
- Ask/RAG integration with claim IDs.
- Auth and read-only tests.
- Backward compatibility Knowledge Card tests.

---

## M9 — User-facing knowledge

### Цель

После доказанной стабильности ядра дать пользователю минимальный способ увидеть Knowledge Card, provenance, evidence, conflicts, reasoning и temporal correction lineage.

### Что уже существует

- `SourceBadge`.
- `WorldProvenanceCard`.
- World Engine/Temporal/History/Ask pages.
- Typed API contracts and UI test infrastructure.

### Чего не хватает

- Knowledge Card route/view.
- Claim-level provenance/evidence display.
- Conflict/competing claims display.
- Derived reasoning lineage display.
- Correction history/status display.

### Конкретные подсистемы/файлы

- `arkaim-web/src/app/world-engine/page.tsx`
- `arkaim-web/src/app/temporal/page.tsx`
- `arkaim-web/src/shared/ui/WorldProvenanceCard.tsx`
- `arkaim-web/src/shared/ui/SourceBadge.tsx`
- `arkaim-web/src/shared/api/contracts/knowledge.ts` — целевой новый contract, если нужен
- `arkaim-web/src/app/knowledge/` — возможный целевой route
- `arkaim-web/tests/unit/`
- `arkaim-web/tests/e2e/`

### Зависимость

M8 и принятые API contracts.

### Минимальный scope

Только read/trace представления существующих данных: claim/source/evidence, confidence/uncertainty, conflicts, derived inputs, temporal position, correction status.

### Что не входит

- Новый media UI.
- Редактирование WorldModel.
- Автоматическое принятие claims/conflicts.
- Новый frontend runtime или возврат v2.
- Визуализация ради визуализации.

### Критерии приёмки

- Пользователь может ответить на traceability chain из раздела Target Architecture.
- Unknown и competing interpretations видны без fabricated certainty.
- UI не создаёт собственный authority/provenance semantics.
- Typed contracts проходят unit и browser smoke.
- Existing World/Temporal UI не регрессирует.

### Необходимые тесты

- Component unit tests для empty/loading/error/claim/evidence/conflict/derived/correction states.
- API contract tests.
- Browser e2e: entity → claim → source/evidence → lineage.
- Accessibility/console smoke.
- Regression tests World/Temporal/Ask.

---

# 4. Архитектурные границы

Ниже — обязательные правила, которые действуют на всех milestones.

## 4.1. World provenance ↔ Knowledge provenance

- **World provenance** описывает, как WorldModel/World Engine получил или классифицировал world data.
- **Knowledge provenance** описывает, как конкретный knowledge claim получил evidence/support.
- Knowledge может ссылаться на World entity/context, но не копирует World provenance на claim.
- World entity не становится external evidence только потому, что присутствует в WorldModel.

## 4.2. Claim provenance ↔ Relation provenance

- Provenance утверждения не наследуется relation-ом.
- Relation — отдельный object с отдельными supporting evidence и category.
- Наличие relation endpoint или World context не доказывает provenance самой связи.

## 4.3. Temporal provenance ↔ source provenance

- Source provenance отвечает, откуда claim/evidence.
- Temporal provenance отвечает, почему temporal interpretation/edge/order принадлежит соответствующему уровню и когда действует.
- PRECEDES остаётся `DERIVED`; это не делает source claim derived и не делает World ordering external fact.

## 4.4. Raw source ↔ derived knowledge

- Raw source/chunk — evidence material.
- Extracted claim — assertion о содержимом источника.
- Synthesis/inference — derived knowledge.
- Эти три уровня нельзя хранить как один неразличимый fact без type/lineage.

## 4.5. Confidence ↔ certainty

- Confidence — числовая оценка конкретного producer/claim.
- Certainty — статус/восприятие достоверности с учётом противоречий, gaps и scope.
- Высокий confidence не отменяет `HYPOTHESIS`, unknown evidence или конфликт.

## 4.6. System interpretation ↔ source claim

- System interpretation всегда остаётся derived/interpretation/reconstruction category.
- Система не может повышать interpretation до source claim.
- Автоматический LLM output без source/evidence — hypothesis либо rejected candidate, но не canon.

## 4.7. User hypothesis ↔ established fact

- User hypothesis хранится отдельно и никогда автоматически не становится established fact.
- Даже confidence=1.0 не меняет category.
- Принятие user hypothesis в canon/WorldModel возможно только через явный owner-approved workflow, если это вообще разрешено существующими contracts.

## 4.8. Identity boundary

- Knowledge и World используют canonical ID.
- Source-local IDs остаются source refs и не становятся canonical entity IDs автоматически.
- Новый crosswalk — отдельное OWNER decision.

## 4.9. Mutation boundary

- Knowledge creation/revision и WorldModel/Temporal mutation — разные операции.
- World/Temporal confirmed update идёт через существующий pending/confirmation flow.
- Knowledge correction не обходит этот gate.
- Reader никогда не изменяет canonical WorldModel/Temporal.

## 4.10. Storage/UI/API boundary

- Storage implementation может развиваться позднее, но не определяет domain semantics.
- API — projection/contract, не authority store.
- `arkaim-web` — consumer contracts, не место хранения или принятия решений.
- Knowledge Cards — projection над Knowledge, а не конкурирующий graph.

---

# 5. Что уже доказано и что ещё предстоит доказать

| Возможность | Статус сейчас | Следующий milestone доказательства |
|---|---|---|
| Claim-level provenance aggregation | IMPLEMENTED/TESTED | M1: единая claim semantics |
| Book RAG provenance | TESTED | M2/M8: evidence refs и query trace |
| Unknown aspects | PARTIAL | M1/M5: explicit unknown/conflict semantics |
| Cross-source perspectives | IMPLEMENTED/TESTED | M5: persisted competing claims |
| Automatic conflict resolution | NOT IMPLEMENTED | M5: preserve, не resolve |
| Cross-source reasoning | PARTIAL/fragmented | M6: typed lineage |
| Derived claim chain | PARTIAL (Book OS tracker) | M6: exact multi-input lineage |
| Temporal claim binding | PARTIAL | M4: typed refs and time distinctions |
| Temporal correction | PARTIAL/M10 flow | M7: knowledge lineage and stale derived |
| Full traceability journey | PROVEN частично: тест M8c + live read-only 2026-10-02 (claim → evidence → source → world/temporal); lineage M5–M7 live пуст | Записи M5/M6/M7 в production и live-подтверждение lineage |
| Knowledge UI | IMPLEMENTED/TESTED (M9, embedded в World Engine Context) | Отдельный Knowledge route и mutation/resolution UI — новый OWNER-GO |

---

# 6. Правильный порядок и причинность

## Почему нельзя начинать с UI

UI зафиксирует текущие несовместимые представления и заставит позже ломать пользовательские contracts до стабилизации claim/evidence semantics.

## Почему нельзя начинать с reasoning

Reasoning без stable input IDs, evidence и conflict model будет создавать derived text без воспроизводимого основания.

## Почему нельзя начинать с temporal correction

Correction зависит от claim identity, evidence, temporal refs и lineage. На раннем этапе она перепишет интерпретацию без возможности объяснить, что именно изменилось.

## Почему World Engine не надо переделывать

WorldModel и World Engine уже дают canonical identity, relations, temporal refresh и guard-инварианты. Knowledge должен использовать их как foundation, а не заменять.

## Почему Book RAG не надо делать заново

Book RAG умеет находить source evidence. Его нужно направить через stable claim/evidence IDs, а не заменять новым retrieval subsystem.

---

# 7. Технический долг

## 7.1. Блокирует основную Knowledge-логику

1. Несогласованные claim/provenance models (`CardClaim`, `Fact`, legacy `Provenance.type`).
2. Нет exact evidence link model.
3. Нет exact derived input list.
4. Нет relation provenance contract.
5. Нет единого conflict vocabulary/storage.
6. Нет temporal correction lineage to Knowledge.
7. Traceability acceptance test закрыт на уровне тестов и backend: общий journey есть (`runtime/tests/test_m8c_trace_journey.py`) и подтверждён live-прогоном 2026-10-02; оставшийся пробел — отсутствие production-записей M5/M6/M7 (`runtime/runtime_data/knowledge/` пусто), поэтому lineage живьём не воспроизводится.

Этот долг должен закрываться в M1–M7 и не может быть отложен до UI.

## 7.2. Не блокирует ядро, но требует cleanup

- Устаревшие warnings (`act(...)` в frontend pages tests).
- Неполный live verification отдельных frontend flows.
- Stale historical docs и restore backlog.
- Комментарии и документация про старые media boundaries.
- Некоторые legacy aliases/deprecated fields вне Knowledge path.
- Отдельные test fixture/documentation mismatches.

Этот долг следует вести параллельно только после стабилизации соответствующего contract; он не должен превращаться в новый roadmap Knowledge Core.

## 7.3. Риски

| Риск | Влияние | Контроль |
|---|---|---|
| Создать второй FactStore рядом с Book OS | Двойная истина | M0 mapping, один domain contract, migration decision |
| Автоматически повысить RAG/derived output до canon | Потеря канона | Category invariants и tests |
| Считать любой JSON path source_ref evidence | Fabricated traceability | M2 resolver и unknown status |
| Перенести provenance entity на relation/time | Ложная уверенность | M3/M4 isolation tests |
| Конфликт resolver блокирует ingestion и стирает перспективы | Потеря данных | M5 competing claims policy |
| Автоматическая temporal correction | Непроверяемое изменение World | M10 gate + M7 lineage |
| UI/API зафиксируют несовместимую семантику | Дорогая миграция | M8 before M9 |
| Расширение crosswalk «по ходу» | Identity drift | Существующий OWNER gate |
| Неполный test/live evidence | Ложный VERIFIED | Явные status labels и acceptance tests |

---

# 8. OWNER DECISIONS

### M2 STOP GATE — ACCEPTED POLICY

M2 не расширяется под будущие возможности. Приняты ровно три решения:

1. **Persistence / resolver integration:** `Evidence` сохраняется как отдельный Knowledge Core record рядом с существующей ingestion/source infrastructure, но не внутри `WorldModel` и не как authority store Knowledge Card. Integration boundary — repository/resolver service поверх существующего Book OS/source adapter; resolver возвращает `RESOLVED`, `UNAVAILABLE` или `UNKNOWN` и не подменяет отсутствие evidence fabricated объектом.
2. **Broken/missing references lifecycle:** записи Evidence и claim-to-evidence link не удаляются при исчезновении источника. Resolver переводит reference в `UNAVAILABLE`, сохраняя source ID, locator, optional version/hash и reason; claim получает `evidence_status=UNAVAILABLE`, не теряя claim/provenance. Восстановление возвращает link в `RESOLVED` только после проверки version/hash; несовпадение создаёт новую версию/reference, старый остаётся историческим. `UNKNOWN` — отсутствие/неподтверждение reference и не равен `UNAVAILABLE` после проверки.
3. **Locator schemas:** в M2 официально поддерживаются только существующие Book Intelligence/RAG locator'ы: `book:chunk:<chunk_id>` и book catalog locator с `chunk_id`/`id`, chapter/paragraph/char metadata. Для внешних источников минимальный typed namespace `external:<source_id>:<locator>`; locator provider-owned, versioned и opaque для Knowledge Core. DOI/URL/archive-page схемы не поддерживаются до отдельного OWNER decision и resolver contract. Неподдерживаемый формат → `UNKNOWN`.

Последовательность M2 завершена: **M2 integration → broken-reference lifecycle → external locator policy → M3 STOP GATE**.

**Статус M2 (все три шага реализованы и протестированы).** Добавлен узкий пакет `core/CORE/evidence/`:
- `EvidenceRepository` / `ClaimEvidenceLinkRepository` (`core/CORE/evidence/repository.py`) — persistence Evidence по стабильному `Evidence.id` и claim→evidence links по `link_id`, JSON-бэкенд рядом с существующим SourceStore, без второго FactStore и без записи в WorldModel;
- `EvidenceResolver` (`core/CORE/evidence/resolver.py`) — разрешение locator'ов в `Evidence` с явными статусами `RESOLVED` / `UNAVAILABLE` / `UNKNOWN`; поддержаны `book:chunk:<chunk_id>`, известный `chunk_id` из source и провайдерный namespace `external:<source_id>:<locator>` (opaque, versioned). Unsupported scheme → `UNKNOWN`, отсутствующий фрагмент → `UNAVAILABLE`, fabricated evidence не создаётся;
- `EvidenceLifecycle` (`core/CORE/evidence/lifecycle.py`) — lifecycle ссылки: `check()`/`restore()` с переходами `RESOLVED` / `UNAVAILABLE` / `UNKNOWN` / `SUPERSEDED`; разорванная ссылка НЕ удаляется, при изменении содержимого старая версия → `SUPERSEDED` и создаётся новая версия со связью `supersedes_link_id`; канонизация locator'а (`canonicalize_locator`) удерживает «голый» chunk id как `book:chunk:<id>`, чтобы пропавший фрагмент давал `UNAVAILABLE`, а не `UNKNOWN`.

Целевые тесты — `runtime/tests/test_m2_evidence_integration.py`, `runtime/tests/test_m2_evidence_lifecycle.py`, `runtime/tests/test_m2_external_locator_policy.py`. Контрольный прогон M2 + M1 + knowledge cards: **88 passed, 6 warnings**; полный M2+M1+provenance прогон ранее — **144 passed**. Это снимок на дату прогона: числа не пересчитывались после добавления тестов в `93272cf` и `1e3f812`. WorldModel, Temporal, crosswalk и frontend не изменялись.

**Статус M3 (минимальный boundary scope реализован и протестирован).** Добавлены:
- `core/CORE/schemas/world_reference.py` — typed `WorldEntityReference` и `WorldRelationReference`; `RESOLVED`, `UNRESOLVED`, `AMBIGUOUS`, `CROSSWALK_UNAPPROVED`; Knowledge provenance не может подменять relation provenance;
- `core/CORE/knowledge/world_resolver.py` — read-only resolver поверх существующего `WorldEngine` и fail-closed `_load_approved_crosswalk`; exact canonical ID и только owner-approved crosswalk могут стать `RESOLVED`;
- `runtime/tests/test_m3_world_knowledge_boundary.py` — проверки canonical ID, approved alias, ambiguity, unresolved, unapproved candidate и relation provenance isolation.

Контрольный прогон M3 + B3 crosswalk + World provenance + Knowledge Cards: **55 passed, 6 warnings**. WorldModel, Temporal, crosswalk и frontend не изменялись.

**Статус M4 (минимальный boundary scope реализован и протестирован).** Добавлены:
- `core/CORE/schemas/temporal_reference.py` — typed `TemporalReference`; `RESOLVED`/`UNRESOLVED`/`UNKNOWN`; раздельные `WORLD_TIME`, `SOURCE_PUBLICATION`, `INGESTION`, `ASSERTION`; только world-time reference может нести canonical temporal ID/bounds;
- `core/CORE/knowledge/temporal_resolver.py` — read-only resolver поверх существующего `TemporalReconstructionEngine.get_node()`, без создания узлов, заполнения gaps или выбора present anchor;
- `runtime/tests/test_m4_temporal_knowledge_boundary.py` — проверки resolved node, unresolved node, unknown time, precision, bounds, temporal provenance и time-basis boundary.

Контрольный прогон M4 + Temporal model + M10 + M10.2 API: **141 passed, 1 warning**. WorldModel, Temporal graph, M10 mutation flow, crosswalk и frontend не изменялись.

**Статус M5 (минимальный scope реализован и протестирован).** Добавлены:
- `core/CORE/schemas/conflict.py` — typed `ConflictRecord`, conflict types для direct contradiction, temporal incompatibility, incompatible interpretation, source perspectives и narrative consistency; статусы `UNRESOLVED`, `ACCEPTED_AS_PERSPECTIVES`, `RESOLVED_WITH_EVIDENCE`, `REJECTED`;
- `core/CORE/knowledge/conflict_repository.py` — JSON persistence conflict records, фильтрация по subject/status, explicit resolution metadata; competing claims и evidence IDs не удаляются;
- `runtime/tests/test_m5_competing_claims.py` — проверки unresolved conflicts, distinct claim IDs, explicit resolution requirements, perspective status, persistence и resolution без потери lineage.

Контрольный прогон M5 + Knowledge Cards + provenance + Temporal regression: **204 passed, 6 warnings**. Существующий Book OS `ConflictResolver` и narrative `ContradictionDetector` не изменялись.

**Статус M6 (минимальный scope реализован и протестирован).** Добавлены:
- `core/CORE/schemas/reasoning.py` — typed `ReasoningResult`/`ReasoningInput`, exact ordered input claim/evidence IDs, method/version, output category, confidence и uncertainty reasons; RESOLVED допускает только DERIVED/RECONSTRUCTION, HYPOTHESIS не повышается;
- `core/CORE/knowledge/reasoning.py` — deterministic source aggregation service; требует минимум два distinct claims, проверяет evidence через repository boundary, воспроизводимый method/version, не генерирует unsupported synthesis;
- `runtime/tests/test_m6_cross_source_reasoning.py` — проверки two-source lineage, evidence gating, uncertainty, order/idempotency, single-source rejection и hypothesis category.

Контрольный прогон M6 + Knowledge Cards + provenance + M10 + B3/World regression: **147 passed, 6 warnings**.

**Статус M7 (минимальный scope реализован и протестирован).** Добавлены:
- `core/CORE/schemas/correction.py` — typed `CorrectionRecord`; pending не может иметь replacement, confirm требует replacement/owner/timestamp, reject требует reason/owner/timestamp;
- `core/CORE/knowledge/correction_repository.py` — durable correction lineage, pending-first confirm/reject, `stale_reasoning_ids()` для affected derived claims;
- `runtime/tests/test_m7_temporal_correction_lineage.py` — проверки pending/reject/confirm, owner decision, old/new lineage, stale reasoning IDs, idempotent decision guard и round trip.

Контрольный прогон M7 + M10/M10.2 + Temporal + M6 + B3/World regression: **155 passed, 1 warning**. M10 `TemporalUpdateManager` остаётся единственным canonical mutation boundary; WorldModel/Temporal graph не изменялись.

**Статус M8 (минимальный read-only API scope реализован и протестирован).** Добавлены:
- `runtime/core/dto/knowledge.py` — typed `KnowledgeTraceResponse` и stable `COMPLETE`/`PARTIAL`/`UNKNOWN` traceability status; response содержит claims, evidence, world, temporal, conflicts, reasoning, corrections, uncertainty и limitations;
- `runtime/core/routes/knowledge_cards.py` — read-only `GET /knowledge/cards/trace/{entity_id}` поверх существующей Knowledge Card projection; legacy search/card routes сохранены, mutation endpoints не добавлены;
- M5 `ConflictRepository` подключён к trace projection через отдельный read-only adapter с `KNOWLEDGE_CONFLICT_DIR`; persisted conflict records фильтруются по canonical `subject_id` и добавляются без изменения competing claims или создания authority;
- M7 `CorrectionRepository` подключён через `KNOWLEDGE_CORRECTION_DIR`; pending/confirmed/rejected lineage читается без mutation API;
- trace query поддерживает `offset`, `limit`, `claim_category`, `evidence_status`, `conflict_status`, `correction_status`, `reasoning_status`, а response содержит `totals` и `next_offset`; claims/evidence/conflicts/corrections фильтруются и пагинируются;
- M6 `ReasoningResult` получил durable read-only boundary: `core/CORE/knowledge/reasoning_repository.py` (`ReasoningRepository`) хранит typed `ReasoningResult` по JSON рядом с существующими M5/M7 stores; records проходят валидацию M6 contract (min 2 distinct input claims, DERIVED/RECONSTRUCTION для RESOLVED, обязательные uncertainty reasons для RESOLVED), corrupt storage честно даёт пустой список вместо fabricated records;
- trace query подключает reasoning через `_reasoning_projection` с `KNOWLEDGE_REASONING_DIR`; фильтр по `subject_id` в `metadata.subjects`, фильтр `reasoning_status`, пагинация и `totals.reasoning` работают как в остальных секциях; M6 semantics, input order и method/version не изменялись;
- `runtime/tests/test_m8b_reasoning_trace.py` — round-trip lineage (claim/evidence IDs, method/version, category, confidence, uncertainty), фильтры subject/status, corrupt storage, projection и отсутствующее хранилище;
- `runtime/tests/test_m8_knowledge_trace_api.py` — DTO round-trip, отсутствие mutation fields, явная status vocabulary, фильтрация/pagination и проверки интеграции persisted M5/M7 records.

Контрольный прогон M8 + Knowledge Cards + Pending Updates API: **64 passed, 6 warnings**. M8 закрыт как минимальный read-only API scope.

**Статус M8e (evidence resolution подключён к trace projection).** Evidence section перестала быть заглушкой со статусом `UNKNOWN` для всех строк: claim-ссылки проходят через существующий M2 `EvidenceResolver` (`core/CORE/evidence/resolver.py`) без изменения M2-семантики. В `runtime/core/routes/knowledge_cards.py` добавлены `_default_evidence_catalog()` (существующий fragment catalog `core/KNOWLEDGE/enriched_catalog.json`), `_evidence_resolver()` (extension point `KNOWLEDGE_EVIDENCE_CATALOG`, кэш per path+mtime) и `_evidence_projection(payload)`: каждая claim с `source_ref`/`chunk_id` получает честный resolver outcome `RESOLVED` (с `evidence_id` из записи Evidence) / `UNAVAILABLE` (фрагмент отсутствует в каталоге, с reason) / `UNKNOWN` (world-refs, book claim без chunk_id, неподдерживаемые схемы); fabricated строк нет. Query-параметр `evidence_status` теперь фильтрует реальные resolver-статусы, а не константу. Найден и исправлен дефект интеграции: каталожные записи идентифицируются ключом `id`, тогда как `Evidence.from_chunk` читает `chunk_id`/`metadata.id` — без нормализации `record["chunk_id"]` реальные фрагменты давали бы ложный `UNAVAILABLE`.

Тесты M8e: `test_m8_knowledge_trace_api.py` — unit-тесты `_evidence_projection` (RESOLVED через tmp catalog с `evidence_id`/`chunk_id`/`source_title`, UNAVAILABLE с reason для отсутствующего chunk, UNKNOWN для book-claim без chunk_id и для `world_model:` ref, отсутствие fabricated строк при неверном каталоге); `test_m8c_trace_journey.py` — journey: фильтр `evidence_status` по фактическим статусам `region_arkaim` (каждый существующий статус переживает фильтр, totals не меняются, несуществующий статус даёт пустую секцию) и новый сценарий на книжной сущности `Аркаим` (5 book claims → `RESOLVED` через реальный каталог с `evidence_id`; подмена каталога на пустой через `KNOWLEDGE_EVIDENCE_CATALOG` → те же ссылки `UNAVAILABLE` без `evidence_id`, `RESOLVED` исчезает, totals стабильны).

Контрольные прогоны M8e: targeted (M8 + M8b + M8c + Knowledge Cards) — **14 повторных проходов/146 passed, 6 warnings** (до и после всех правок); `py_compile` по изменённым файлам — OK; полный backend regression `tests` (без providers) — **1788 passed, 26 skipped, 19 failed**: все 19 вне Knowledge Core контура (auth service key, book UI integration, crowdfunding, load book, m9 expansion, md3 routes, milestone B provenance metadata, provider reliability — env/401/LLM-зависимые), из них `test_authenticate_service_key_valid` подтверждён падающим и без правок Knowledge Core (`git stash` baseline), а ссылок на `knowledge_cards` в упавших тестах — 0. Ограничение: отдельные внешние тесты (`test_load_book`, `test_m9_expansion_temporal` и др.) при точечном запуске зависают на ожидании и были прерваны — в рамках Knowledge Core scope они не исследовались. WorldModel, Temporal, crosswalk, M5/M6/M7 semantics, M9 frontend и mutation/resolution flow не изменялись.

**Статус M8 (полный read-only integration journey добавлен).** Реализован `runtime/tests/test_m8c_trace_journey.py` — одна связанная цепочка через реальный `GET /knowledge/cards/trace/{entity_id}`: card claim (реальные `source_ref` Knowledge Card) → evidence → M5 conflict (`DIRECT_CONTRADICTION` + `TEMPORAL_INCOMPATIBILITY`) → M6 reasoning (`RESOLVED`/`HYPOTHESIS` с exact input lineage) → M7 correction (`PENDING`, `superseded_claim_ids` + `affected_reasoning_ids`), с проверкой auth (401 без reader), exact IDs/lineage на каждом звене, честности `COMPLETE/PARTIAL`, прохода pagination `limit=1` по всей цепочке, фильтров без fabrication и отсутствия утечки записей другого subject. Journey выявил и исправлены три дефекта read-проекции (без изменения семантики M5/M6/M7 и DTO): `next_offset` учитывал только conflicts/corrections/reasoning — claims/evidence-цепочка обрывалась при малом `limit`; `totals` считался часть до, часть после фильтров — теперь всегда полный нефильтрованный размер цепочки, фильтры сужают только содержимое страниц; limitation про evidence считался по отфильтрованному списку — теперь по нефильтрованному.

Контрольные прогоны journey: targeted (M8c + M8 + M8b + M5/M6/M7 + Knowledge Cards) — **75 passed**; полный Knowledge Core regression (M1–M8c + Knowledge Cards) — **143 passed, 6 warnings**; `compileall` по изменённым файлам — OK. M9 frontend не изменялся.

**Статус M8 (durable reasoning read boundary добавлен).** Reasoning section Knowledge Trace перестала быть пустой заглушкой: подключён `ReasoningRepository` поверх неизменённого M6 `ReasoningResult` contract. Контрольные прогоны: targeted `test_m8b + test_m8 + test_m6` — **17 passed**; полный Knowledge Core regression (M1–M8 + M8b + Knowledge Cards) — **130 passed, 6 warnings**; `compileall` по изменённым файлам — OK. WorldModel, Temporal, crosswalk, M5/M7 semantics, M9 frontend и mutation/resolution flow не изменялись.

**Фактическая интеграция M9 (выполненный scope):** добавлены typed `KnowledgeTrace`/`getKnowledgeTrace`, direct envelope mappings, read-only `KnowledgeTraceCard` и подключение к World Engine Context. Новый отдельный Knowledge route, mutation API и media UI не добавлялись. Проверки: KnowledgeTrace unit — **3 passed**; TypeScript — **0**; backend M8 regression — **3 passed**; полный frontend regression — **15 test files / 73 tests passed**. Первый полный прогон дал нестабильный timeout `GenresPage`; изолированный повтор прошёл **14/14**, повторный полный прогон прошёл.

**Live verification M9 — VERIFIED WITH SCOPE:** production build выполнен отдельно без backend и тестов: **BUILD_EXIT_CODE=0**. Backend и один `next start` запущены последовательно; browser smoke на `/world-engine?entity_id=region_arkaim` подтвердил загрузку World Context, World provenance, temporal context и Knowledge Trace через frontend proxy. Trace показал `COMPLETE`, 6 claims, 6 evidence items, 1 temporal relation, 0 conflicts, 0 corrections, empty World reference/uncertainty/limitations для этой выборки. Console logs не содержали ошибок. После smoke оба сервера остановлены, порты `3000/8642` освобождены. Проверка не подтверждает наличие заполненных World reference/uncertainty/reasoning/corrections — это корректный результат текущего backend projection, а не synthetic fallback.

## 8.1. Уже принятые решения

M1, M2, минимальные scope M3, M4, M5, M6, M7, M8 и минимальный read-only scope M9 зафиксированы выше. Изменение WorldModel, Temporal, crosswalk, relation contract, canonical persistence или mutation semantics по-прежнему требует отдельного OWNER decision.

## 8.2. Перед M1 — исторический контекст

1. Какой существующий contract считается canonical domain model: эволюция `CardClaim`/`ProvenanceTag` или controlled adaptation `Fact`/Book OS schema.
2. Является ли Knowledge Core отдельной долговременной persistence abstraction или phase-wise composition поверх существующих stores.
3. Какие поля versioned и обязательны для claim status/lineage.
4. Как legacy provenance strings маппятся и какой период поддерживаются.

## 8.3. Перед M5–M6

1. Какие conflict types должны входить в v1.
2. Может ли LLM только предлагать conflicts/reasoning, а acceptance выполняться deterministic policy/human gate.
3. Какие inference methods являются допустимыми для canon-adjacent output.

## 8.4. Перед M7

1. Как confirmed temporal update связывается с correction record для claims.
2. Что происходит с derived claims: `stale`, `recomputed`, `retained_with_warning`.
3. Где хранится correction history.

## 8.5. Перед M9

1. Нужен ли отдельный Knowledge route или достаточно trace views внутри World/Book/Temporal.
2. Какие роли могут видеть/предлагать resolution, но не менять canon.

---

# 9. WHERE WE ARE NOW

> **Текущая архитектурная стадия Arkaim = M1–M8 Knowledge Core foundations реализованы как typed/read-only contracts; минимальный read-only trace presentation M9 интегрирован в World Engine Context и проверен production browser smoke.**

Кратко: Arkaim умеет фиксировать claim semantics, связывать claims с evidence (включая фактическое разрешение book-ссылок в `RESOLVED`/`UNAVAILABLE`/`UNKNOWN` через M2 resolver внутри trace projection), разделять World/Knowledge/relation provenance, привязывать claims к temporal nodes, сохранять competing claims, воспроизводимые derived reasoning results и auditable temporal correction lineage. Read-only trace API и минимальный UI-потребитель реализованы, покрыты unit tests и прошли production browser smoke. Отдельный Knowledge route, mutation/resolution flows и browser e2e не реализованы.

---

# 10. NEXT MILESTONE

## M9 — User-facing knowledge

Минимальный read-only trace scope уже реализован в существующем `arkaim-web`: claim/source/evidence, confidence/uncertainty, conflicts, derived inputs, temporal position и correction status отображаются через typed contract без создания authority или mutation semantics.

OWNER-GO получен на вариант A: расширение существующего `KnowledgeTraceCard` внутри World Engine Context. Реализован strictly read-only claim drill-down: statement, provenance category, confidence, claim ID, source reference, evidence ID/locator/status, world reference, temporal position/references и честные unknown/empty states. Backend semantics, API contracts, WorldModel, Temporal, crosswalk, persistence, mutation/resolution, RBAC, media и отдельный Knowledge route не менялись.

Проверки M9: targeted KnowledgeTraceCard — **3 passed**; frontend regression — **14/15 files passed**, 72/73 tests passed, единственный `GenresPage` timeout при полном нагруженном прогоне прошёл изолированно (**1 passed**); production build — **PASS**; browser smoke World Engine → Context → Knowledge Trace → раскрытие claim → evidence → temporal — **PASS**, console без новых ошибок. Серверы после smoke остановлены, порты `3000/8642` свободны.

M9 закрыт как расширенный read-only Knowledge UI scope. Следующие mutation/resolution, отдельный Knowledge route, новые роли или изменение backend contracts не начинаются без отдельного OWNER-GO.

---

# 11. WHY NOW

1. M0 уже имеет достаточно фактического материала; новый аудит создаст повторение, а не новое знание.
2. M1 устраняет главный риск переделки: два разных claim/provenance словаря уже используются в Book OS и Knowledge Cards.
3. Evidence, World boundary, temporal references, conflicts и reasoning нельзя сделать устойчивыми поверх неоднозначного claim contract.
4. Это не требует изменения WorldModel, Temporal mechanics, crosswalk, API или frontend.
5. M1 даёт минимальный проверяемый scope и сохраняет существующие read-only Knowledge Card consumers.

---

# 12. STOP GATE — ACCEPTED

OWNER принял переход к M2 на основании трёх обязательных решений M1:

1. **Canonical Claim Contract:** `CanonClaim` из `core/CORE/narrative_engine/provenance/claim.py` является единственной канонической структурой claim для нового Knowledge Core.
2. **Versioning policy:** существующий claim ID и claim history не переиспользуются; изменение содержания, provenance, entity/time bindings или confidence создаёт новую версию с явной lineage-связью и сохранением предыдущей версии.
3. **Compatibility / persistence policy:** legacy `Fact.provenance`, `schemas.Provenance.type`, `source_ref`, `doc_id` и `chunk_id` сохраняются физически там, где уже являются частью записи; новые consumers читают их через compatibility layer и нормализуют в `ProvenanceCategory`; миграция существующих записей допускается только отдельной явной, тестируемой операцией и не является условием чтения старых данных.

Эти решения закрывают M1 STOP GATE. До отдельного нового OWNER-GO следующий рабочий milestone — **M2 — Evidence/source-fragment model**.

OWNER должен принять переход к M2 только когда M1 доказывает:

- [x] одна утверждённая семантика claim/provenance согласована;
- [x] legacy `Fact`/Book OS и Knowledge Card имеют явный mapping;
- [x] `ProvenanceCategory` и confidence остаются независимыми;
- [x] `HYPOTHESIS`, `DERIVED`, `EXTERNAL_SOURCE` и `AUTHOR_CANON` не смешиваются;
- [x] unknown/absence не превращается в fabricated evidence;
- [x] stable claim identity и versioning policy определены;
- [x] compatibility scope для текущего read-only API определён;
- [x] тесты M1 проходят без изменения WorldModel, Temporal, crosswalk и frontend;
- [x] OWNER письменно выбрал стратегию хранения/compatibility для следующих milestones.

До принятия STOP GATE код, API, WorldModel, Temporal, crosswalk и frontend не изменяются.

---

# 13. Финальное резюме

## CURRENT STAGE

World Engine, canonical WorldModel, Temporal/event chains, provenance categories, Book Intelligence/RAG, Book OS ingestion и read-only cross-source Knowledge Cards уже являются фундаментом и имеют фактическое кодовое и тестовое подтверждение.

## TARGET ARCHITECTURE

Arkaim должен развиваться как Knowledge Core, где claims, evidence, sources, provenance, uncertainty, canonical entities, world-time events, derived reasoning, conflicts и correction lineage связаны и трассируемы. Knowledge Cards, Ask/RAG и `arkaim-web` являются проекциями и потребителями этого ядра.

## MILESTONES

```text
M0 Baseline
→ M1 Claim + provenance semantics
→ M2 Evidence model
→ M3 World boundary
→ M4 Temporal boundary
→ M5 Competing claims/conflicts
→ M6 Cross-source reasoning
→ M7 Temporal correction lineage
→ M8 Query/reasoning API
→ M9 User-facing knowledge
```

## NEXT MILESTONE

**M9 — User-facing knowledge — CLOSED для OWNER-approved варианта A.** Расширенный strictly read-only claim/evidence/temporal drill-down реализован в `KnowledgeTraceCard` внутри World Engine Context и проверен unit/regression/build/browser smoke. Новый milestone автоматически не начинается; mutation/resolution UI, отдельный Knowledge route и расширение API требуют отдельного OWNER-GO.

## RISKS / TECH DEBT

Главные блокирующие риски — dual provenance vocabularies, approximate `source_ref`, incomplete derived lineage, isolated relation provenance и отсутствие temporal correction lineage. UI/media/historical documentation debt не должен менять этот порядок.

## OWNER DECISIONS

Перед развитием необходимо принять canonical claim contract, compatibility/migration policy, versioning, conflict/reasoning policy и correction lineage semantics. Начало реализации автоматически не разрешено этим документом.

## OWNER-GO ITEMS (по итогам live-verification 2026-10-02)

Два расхождения из live-отчёта (`docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`) НЕ исправляются автоматически: каждое меняет утверждённый контракт и требует отдельного OWNER-GO.

1. **PROBLEM №1 — `trace.status=COMPLETE` при наличии `UNKNOWN` evidence.** — **RESOLVED (GO-1, EXECUTED 2026-10-11).**
   - Факт: `region_arkaim` — 7 из 25 claims с `evidence.status=UNKNOWN` (и без `claim_id`), при этом `status=COMPLETE`, `limitations=[]`; логика — `runtime/core/routes/knowledge_cards.py:438-445` (PARTIAL только если нет `primary_entity`, нет evidence-строк либо есть несвязанные records).
   - Ожидание: §2.5 (E. Traceability) — «если путь существенно утверждения обрывается, объект нельзя представить как verified knowledge; иначе нужен PARTIAL или UNKNOWN traceability status».
   - Почему нужен GO: правка меняет семантику `KnowledgeTraceResponse.status` (read-only trace-контракт, M2/M8e-соглашение) и наблюдаемые состояния M9 UI.
   - **Принятое решение:** критерий перевода в `PARTIAL` — **любая evidence-строка со статусом ≠ `RESOLVED`** (`UNAVAILABLE` или `UNKNOWN`) либо любое `limitations`; `COMPLETE` — только когда есть claims, все evidence `RESOLVED` и `limitations` пусты; отдельный `UNKNOWN` **не вводится** (зарезервирован в словаре; пустая сущность остаётся `PARTIAL` с explicit limitations — M8c-контракт). Статус считается по полному набору evidence (до секционных фильтров). Правило зафиксировано в docstring `get_knowledge_trace`; live-подтверждение: `region_arkaim` → `PARTIAL`.
2. **PROBLEM №2 — два формата ошибок на одних endpoint-ах.** — **RESOLVED (GO-2, EXECUTED 2026-10-11).**
   - Факт: 401/404 → `{"ok":false,"error":{"code":...}}`; 422 (валидация `q`, `limit`) → `{"detail":[...]}` default FastAPI.
   - Почему нужен GO: переход на единый формат меняет API-контракт ответов об ошибках; route уже типизировано во frontend как `direct` (`arkaim-web/src/shared/api/envelope.ts:62-64`) и потребители ожидают стабильную форму.
   - **Принятое решение:** целевой формат — **envelope** `{"ok":false,"error":{"code":"HTTP_422","message":<первое msg>,"details":[{"loc","msg","type"},...]}}`; объём — **все routes** (глобальный `RequestValidationError`-handler в `runtime/core/main.py` рядом с `HTTPException`-handlerом — единая форма 401/404/422/500); способ обновления frontend contracts — **правок не потребовалось**: `errors.ts::parseErrorBody` уже разбирает envelope (`ApiErrorCode` — шаблонная строка `HTTP_${number}`), `details` ложится в `ApiError.details`. Статусы 422 и состав ошибок валидации сохранены; OpenAPI `schema.d.ts` (generated) при следующей регенерации подхватит новый response-формат.

Прочие findings из отчёта классифицированы как работы без нового OWNER-GO (при условии неизменности контракта) — факты проверки приведены в addendum отчёта `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`: семантика `search.total`, карточная семантика `uncertainty.has_unknowns`, mojibake в данных, документационный drift (закрыт 2026-10-02) и происхождение `core/CORE/genome/history/index.json` (выяснено: snapshot при `Pulse.load()`).

---

**Статус M8f (canonical region → Book → Evidence chain исправлен без изменения World data).** Установлен источник разрыва: World Engine уже имеет canonical ID `region_arkaim`, но его `name`/`description` повреждены mojibake, поэтому прежний Book RAG query по raw ID и display name возвращал пустой результат. Уже утверждённый B3 crosswalk содержит owner-reviewed связь `region_arkaim → аркаим` с evidence `name_ru=Аркаим`. `KnowledgeCardBuilder` теперь читает этот существующий read-only crosswalk и добавляет его canonical target ID только как дополнительный retrieval query; identity/crosswalk/WorldModel/API не изменяются и новые fuzzy mappings не выводятся. Фактический путь: `region_arkaim` → утверждённый canonical target `аркаим` → реальные book chunks → неизменённый M2 `EvidenceResolver` → `RESOLVED` с `evidence_id`; genome-derived retrieval row, отсутствующий в book fragment catalog, честно остаётся `UNAVAILABLE`.

Regression расширен unit-тестом Knowledge Card builder с mojibake fixture и M8c journey на `region_arkaim`: catalog-backed book chunks обязаны быть `RESOLVED` с evidence IDs, а пустой catalog переводит те же ссылки в `UNAVAILABLE` без fabricated IDs. Контроль: новые targeted сценарии — **2 passed**; Knowledge Core regression M1–M8/M8b/M8c + Knowledge Cards — **147 passed, 6 warnings**; `py_compile` — OK. WorldModel, canonical identity, crosswalk, M2/M8e semantics, M9 frontend и persistence не изменялись.

**Статус M8g (read-only cross-record lineage projection).** В `KnowledgeTraceResponse` добавлено additive-поле `lineage`; `_trace_lineage()` строит только exact-ID/ref joins поверх уже загруженных M5 conflict, M6 reasoning и M7 correction records. Поле не создаёт claim/evidence records и не меняет M5/M6/M7 contracts: conflict сохраняет исходные `claim_ids`/`evidence_ids`, reasoning — ordered input IDs, correction — `superseded_claim_ids`/`affected_reasoning_ids`; Trace показывает только найденные связи и stale IDs. При отсутствии совпадений links пусты, а при наличии несвязанных records статус становится `PARTIAL` с limitation.

Journey расширен positive-сценарием полного M5→M6→M7 link и negative-сценарием unmatched records без fabricated lineage. Контроль: M8/M8b/M8c targeted — **20 passed**; полный Knowledge Core regression M1–M8/M8b/M8c + Knowledge Cards — **148 passed, 6 warnings**; `py_compile` — OK. M5/M6/M7 semantics, WorldModel, Temporal, crosswalk, persistence, mutation/resolution и frontend не изменялись.

**Статус M8h (CanonClaim identity bridge для Knowledge Card → M5/M6/M7).** Исследование показало: `CanonClaim.make_id(text, source_id, location)` уже является принятым M1 identity contract, но Knowledge Card `CardClaim` его не проецирует. Добавлен минимальный read-only bridge `_card_claim_id()` в Trace projection: только claims с `book:` source reference, стабильным `chunk_id` и текстом получают deterministic CanonClaim ID (`source_id="book"`, `location="chunk:<chunk_id>"`). Claims без такого locator не получают guessed ID и остаются без claim identity. M5/M6/M7 records, persistence и semantics не изменяются.

Journey fixtures переведены на реальные CanonClaim IDs от card claims; положительный тест проверяет exact `claim_links`, evidence links, ordered reasoning inputs и correction stale IDs. Отдельно проверены deterministic bridge, duplicate-text/location behavior и fail-closed World/no-chunk cases; unmatched records по-прежнему не получают fabricated links. Контроль: targeted M8/M8b/M8c — **21 passed, 6 warnings**; полный Knowledge Core regression M1–M8/M8b/M8c + Knowledge Cards — **149 passed, 6 warnings**; `py_compile` — OK.

**Статус M8i (external Knowledge Card claim identity bridge).** Проверена действующая M2 policy: единственный официальный внешний locator — `external:<source_id>:<locator>`, provider-owned и opaque. Knowledge Card builder уже создаёт детерминированные archaeology/academic refs с artifact prefix (`ARCHAEOLOGY.json:` и `ACADEMIC_CONFIRMATIONS.json:`), но эти refs не были приведены к M2 external namespace. Bridge расширен exact allowlist: `ARCHAEOLOGY.json:` → `external:archaeology:<exact locator>` и `ACADEMIC_CONFIRMATIONS.json:` → `external:academic:<exact locator>`; затем применяется существующий `CanonClaim.make_id`. Произвольные `*.json` refs, World refs и неполные external locators не получают ID. Это read-only compatibility layer, не изменение M2 resolver или claim semantics.

Journey добавлены отдельные проверки: archaeology claim из реального `region_arkaim` получает deterministic ID; canonical `external:<source_id>:<locator>` сохраняет exact source/location; неизвестный artifact namespace fail-closed. Контроль: targeted M8/M8b/M8c — **23 passed, 6 warnings**; Knowledge Core regression M1–M8/M8b/M8c + Knowledge Cards — **151 passed, 6 warnings**; `py_compile` — OK.

**Статус M8j (versioned ExternalLocatorSource registry).** Добавлен `core/CORE/evidence/external_registry.py`: read-only registry строит `ExternalLocatorSource` из существующих `ARCHAEOLOGY.json` и `ACADEMIC_CONFIRMATIONS.json`, сохраняя для каждого fragment `source_version` на основе artifact SHA-256 и `content_hash`. M2 `EvidenceResolver` теперь получает этот registry через trace projection; canonical external locators разрешаются в Evidence без изменения Knowledge Card claim IDs, M2/M5/M6/M7 contracts или persistence semantics.

Registry cache учитывает mtime внешних artifacts, поэтому изменение source artifact приводит к новому read-only resolver snapshot. Journey проверяет versioned registry, archaeology evidence `RESOLVED` с evidence ID, а также сохранение исходного `ARCHAEOLOGY.json:` source_ref при canonical locator resolution. Контроль: targeted M8/M8b/M8c — **25 passed, 6 warnings**; Knowledge Core regression M1–M8/M8b/M8c + Knowledge Cards — **153 passed, 6 warnings**; `py_compile` registry/route/tests — OK.

**Live verification 2026-10-02 (HEAD `1e3f812`, read-only, код/тесты/API не изменялись).** Полный отчёт — `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`. Подтверждено live: auth `401` без токена; `search`/`card`/`trace` `200` на 7 реальных сущностях и `404` карточки для неизвестной entity; фильтры (claim_category/evidence_status/conflict/correction/reasoning) и pagination с `next_offset`, неизменные `totals`; claim → evidence → source (`evidence_id` у `RESOLVED`, честные `UNAVAILABLE`/`UNKNOWN` с reason), world reference и temporal `PROJECTED_FROM_WORLD_REF`; fail-closed `claim_id` (18/25 у `region_arkaim`, 8/12 у `archaeology:синташта`). Не подтверждается live: conflicts/reasoning/corrections/lineage = 0 — `runtime/runtime_data/knowledge/` не содержит production-записей (искусственные данные не создавались). Найденные фактические расхождения без исправления: `status=COMPLETE` при `UNKNOWN`-evidence у `region_arkaim` (§2.5 требует `PARTIAL`), два формата ошибок на одних endpoint-ах (envelope для 401/404 и `detail` FastAPI для 422), `search.total` равен размеру страницы, mojibake `region_arkaim.name` (M8f) сохраняется.

**Статус M10–M12 (2026-10-13) — функциональный путь связей сценарий↔книга доведён до рабочего результата.** Обнаружение кандидатов: новый `core/CORE/knowledge/screenplay_link_candidates.py` (M10 suggest-only gate) детерминированно сопоставляет 119 сцен `SYNOPSIS_DOCUMENT.json` и 824 чанков `enriched_chunks.json` (покрытие биграммами + дословные совпадения предложений); все 9 пар, одобренных M16.1, ранжируются как top-1 своих сцен, кандидаты никуда не пишутся. Подтверждение/сохранение: `knowledge.screenplay_links_provenance` стал единственным write-path реестра `screenplay_links.json` — `save_screenplay_links` сливается с записями на диске (owner-`notes` и `_provenance_metadata` никогда не теряются при регенерации), `approve_link` — подтверждение владельца (проверки форматов и существования id в реальных данных, pre-validate слияния, атомарная запись), `repair_provenance`/`--repair` self-heal-ит реестр, откатанный в 4-полевой формат (инцидент M16.3). CLI `scripts/generate_screenplay_links.py`: `--candidates [SCENE...]`, `--approve S C`, `--repair`, `--out`. `ScreenplayBookLinker` получил опциональное поле `provenance` (read-back после перезагрузки; 4-полевой read-only контракт M11 не изменён). `test_milestone_b.py` адаптирован к спискам-регистрам (M16.3: record-level метаданные у `screenplay_links.json`; M17: плоские записи `claim_temporal_links.json` освобождены на уровне списка). Тесты: `runtime/tests/test_m10_m12_screenplay_link_flow.py` — 18 сценариев на реальных данных (обнаружение, неоднозначности, подтверждение, перечитывание, self-heal, обратная совместимость; записи только в tmp). Проверки: targeted M10-M12+M16.3+M11 — 44 passed; M16.1/M16.2/M17/M19/M10/M12/M15 — 123 passed; полный backend-прогон — **2130 passed, 26 skipped**, единственный оставшийся failure `test_m9_expansion_temporal` — pre-existing (см. M8e-запись: m9 expansion уже входил в 19 out-of-scope failures до этого этапа), не зависит от связей сценария.

**END OF PLAN — M8 verified; M8e evidence resolution, M8f canonical region → Book → Evidence chain, M8g exact read-only M5/M6/M7 lineage, M8h CanonClaim card identity bridge, M8i external locator identity bridge, and M8j versioned ExternalLocatorSource registry integrated (153 Knowledge Core tests green по прогону M8j; **re-baseline 2026-10-11 на HEAD `1e3f812`: 333 collected / 333 passed / 0 failed после фикса GO-8; до фикса было 330/329/1 — BASELINE-1, см. `docs/CURRENT_DEVELOPMENT_STATE.md`**); M9 OWNER-approved expanded read-only Knowledge UI implemented and VERIFIED; full live verification of the read-only backend contour (search/card/trace) completed 2026-10-02, see `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`. STOP. Mutation/resolution UI, separate Knowledge route and API expansion require a new OWNER-GO.**

---

# 14. Таргет-карта пользователя — frontend-архитектура «цепочки истины» (добавлено 2026-10-22)

> **Статус главы: DRAFT — ожидает OWNER decision по Q1–Q4.**
> Основана на аудите всех user-facing страниц `arkaim-web` (навигация — `arkaim-web/src/components/layout/Sidebar.tsx`).
> Глава документирует границы frontend-архитектуры и НЕ входит в scope Knowledge Core (M0–M12); задачи T-UI-1…T-UI-5 — черновик, не начаты и не создают разрешения на работу (правила §0 и §12).

## 14.1. Каноническая цепочка («Chain of Truth»)

Каждая user-facing вкладка обязана принадлежать ровно одному звену цепи. Голос книги (диалог) — параллельный канал, который потребляет цепь, но никогда её не заменяет.

```
SOURCE → KNOWLEDGE → WORLD → STORY → MEDIA
```

| Звено | Что это | Вкладки |
|---|---|---|
| **SOURCE** | Текст книги и его структура — первичный источник истины | `/reading`, `/library` |
| **KNOWLEDGE** | Эпистемически размеченные карточки с трассировкой (контракт — §2.5 E. Traceability) | `/knowledge`, `/search`, `/genres` |
| **WORLD** | Вычисляемая модель мира: статические сущности/связи/правила + временной контекст | `/world-engine` (Model View), `/temporal`, `/map` |
| **STORY** | Эксплорация гипотез и генерация строго внутри модели (constraint-проверка до LLM) | `/story`, динамическая часть `/world-explorer` |
| **MEDIA** | Downstream-потребитель выхода Story/World: планирование сцен/шотов, сессии, ассеты. Генерация — в отдельном сервисе `arkaim-media` (задокументировано в UI) | `/film-studio`, `/studio`, `/assets`; источники описаний: `/visual`, `/visual-cards` |
| **ГОЛОС** (параллельно цепи) | Диалог: голос Pulse + Reader Memory + source badges; книга первична — голос лишь её проецирует | `/book`, `/ask` |

## 14.2. Статусы вкладок

| Статус | Значение |
|---|---|
| **CORE** | Вкладка соответствует своей роли в цепи; сохраняется и развивается |
| **OVERLAP** | Дублирует функциональность другой вкладки; требует объединения или переопределения |
| **LEGACY** | Инструмент просмотра логов/диагностики, экспонированный массовому читателю; деградировать или убрать |
| **WRONG BOUNDARY** | Нарушает цепь или эпистемические границы (смешение статики/динамики, отсутствие эпистемической разметки, missing provenance) |

## 14.3. Target User Map (18 роутов `arkaim-web`)

| Route | Имя | Роль в цепи | Статус | Решение |
|---|---|---|---|---|
| `/reading` | Чтение | SOURCE | CORE | Сохранить — фундамент цепи |
| `/library` | Библиотека | SOURCE (геном, слои сознания, эволюция) | CORE | Сохранить |
| `/book` | Книга | ГОЛОС (диалог с памятью, streaming, Pulse confidence, source badges, related entities) | CORE | Основной диалоговый вход |
| `/ask` | Спроси у книги | ГОЛОС (Pulse-вопрос + deep-dive на сущности/эпохи/мир) | OVERLAP | Объединить с `/book` (Q1) |
| `/history` | История | Диагностика: браузер сессий Reader Memory | LEGACY | Деградировать/убрать из главной навигации (Q2) |
| `/knowledge` | Знания | KNOWLEDGE | WRONG BOUNDARY | Нет эпистемических статусов (CANON/MODEL/HYPOTHESIS) → Epistemic UI (T-UI-1) |
| `/search` | Поиск | KNOWLEDGE (кросс-слойный) | CORE | Сохранить |
| `/genres` | Жанры | KNOWLEDGE (таксономия) | CORE | Сохранить |
| `/world-engine` | Мир | WORLD: статическая модель (entities/relations/modes/rules, cross-links на Temporal) | CORE | Сохранить как **Model View** (статика) |
| `/temporal` | Хронология | WORLD: временной слой (реальные данные, честная индикация недоступности) | CORE | Сохранить |
| `/map` | Карта | WORLD: регионы/маршруты/энергетические линии + хронология | CORE | Сохранить |
| `/story` | Движок | STORY: модель constraints → генерация эпизодов строго внутри модели | CORE | Сохранить |
| `/world-explorer` | World Explorer | STORY: динамика (гипотезы, ветки, feedback) | WRONG BOUNDARY | В user-facing инструменте мигрируют dev-панели (статистика/invalidation кэша, сырой JSON внешнего поиска) и статическое дублирование `/world-engine` → T-UI-2 |
| `/film-studio` | Film Studio | MEDIA | WRONG BOUNDARY (provenance gap) | Завязан на «сцены книги» без ссылки на выход Story/World Engine и без provenance-поля (Q3 → T-UI-4) |
| `/studio` | Studio | MEDIA (сессии генерации) | WRONG BOUNDARY (provenance gap) | То же (Q3 → T-UI-4) |
| `/visual` | Визуальный геном | MEDIA (источники описаний: collection/scene/character/location/voice) | CORE | Сохранить; boundary с `arkaim-media` уже задокументирован в UI (MediaBoundaryNotice) |
| `/visual-cards` | Визуальные карточки | MEDIA (источники; очередь художественной модели) | CORE | Сохранить; эпистемическая индикация уже присутствует («требует подтверждения» / «подтверждено», ARTISTIC_MODEL) — прототип для §14.4 |
| `/assets` | Ассеты | MEDIA (галерея результатов) | CORE | Сохранить; boundary с `arkaim-media` уже задокументирован в UI |

**Итого:** CORE — 12, OVERLAP — 1 (`/ask`), LEGACY — 1 (`/history`), WRONG BOUNDARY — 4 (`/knowledge`, `/world-explorer`, `/film-studio`, `/studio`).

## 14.4. Epistemic UI — обязательные правила отображения (draft)

1. У каждой единицы знания/сущности/артефакта в user-facing представлениях обязателен эпистемический статус:
   - **CANON** — извлечено из текста книги; обязателен источник (глава/фрагмент/traceability-карточка);
   - **MODEL** — выведено из World Engine; обязательна ссылка на правило/сущность;
   - **HYPOTHESIS / EXPLORATION** — сгенерировано внутри ограничений (Story/Explorer); обязательны confidence и provenance (ветка/эпизод);
   - **UNVERIFIED** — статус неизвестен → нейтральное отображение, смешивание с CANON запрещено.
2. HYPOTHESIS никогда не отображается без визуального маркера, отличающего его от CANON/MODEL.
3. Сгенерированные медиа (ассеты, шоты) наследуют статус источника: из модели сцены → MODEL; из ветки Story → HYPOTHESIS.
4. Эталонные элементы, существующие в UI и подлежащие распространению на все экраны: source badges в `/book`, «требует подтверждения» / «подтверждено» в `/visual-cards`, MediaBoundaryNotice в `/assets` и `/visual`, честная индикация недоступности данных в `/temporal` и `/map`.
5. Основной gap: `/knowledge` не отображает эпистемический статус — задача T-UI-1.

## 14.5. Задачи рефакторинга (черновик; статусы на 2026-10-22 — см. `docs/CURRENT_DEVELOPMENT_STATE.md` §11)

| ID | Задача |
|---|---|
| T-UI-1 | Epistemic UI в `/knowledge`: статусные бейджи + provenance-ссылки на трассировку (trace) |
| T-UI-2 | Разделение `/world-explorer`: user-facing динамическая часть (гипотезы, ветки, feedback, film-эксплорация) остаётся; dev-панели (статистика/invalidation кэша, сырой JSON внешнего поиска) → диагностический раздел (`/admin`/observability); статическое дублирование `/world-engine` заменить явными ссылками |
| T-UI-3 | Деградация `/history` (OWNER decision Q2): перенос в профиль читателя либо удаление из основной навигации |
| T-UI-4 | Media provenance (OWNER decision Q3): обязательное поле происхождения (ветка Story / сущность World / эпизод) у film-проектов и media-сессий; отображение «происхождение» в UI |
| T-UI-5 | Объединение `/ask` и `/book` (OWNER decision Q1) |

## 14.6. OPEN QUESTIONS — решения OWNER (STOP GATE для главы 14)

1. **Q1. Ask vs Book** — два входа в диалог: `/book` (полный разговор с памятью, streaming, подсказки) и `/ask` (одиночный Pulse-вопрос + deep-dive на сущности/эпохи/мир; принимает `session_id` из `/history`). Варианты: (а) сохранить `/book` как основной диалог, переопределить `/ask` как «deep-dive» (вопрос → сущность → временной/мировой контекст); (б) признать дублированием и убрать `/ask` из сайдбара. **Рекомендация инженера: (а).**
2. **Q2. History** — лог-браузер сессий Reader Memory. Варианты: (а) перенести в профиль читателя; (б) вынести в админ-раздел; (в) убрать из основной навигации (доступ по прямой ссылке). **Рекомендация инженера: (в) + доступ из профиля.**
3. **Q3. Media provenance** — обязательная зависимость: каждый media-проект/сессия привязывается к выходу Story/World (ветка/эпизод/сущность) с видимым provenance; запрет «свободной генерации без источника» в user-facing режиме.
4. **Q4. World Engine vs World Explorer** — утвердить разделение: `/world-engine` = статический Model View; `/world-explorer` = только динамическая эксплорация, без dev-панелей. (Технически относится к T-UI-2; вынесено как вопрос, поскольку меняется набор user-facing панелей.)

> STOP GATE главы 14 закрыт 2026-10-22: решения OWNER по Q1–Q4 получены — Q1 (раздельность `/ask` + `/book`) и Q2 (`/history`) — без изменений, T-UI-5/T-UI-3 заморожены; Q3 (media provenance) и Q4 (безопасность dev-панелей World Explorer) реализованы (факт и верификация — `docs/CURRENT_DEVELOPMENT_STATE.md` §11).
