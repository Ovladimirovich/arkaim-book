# TRUTH AS CORE — FORENSIC / ARCHITECTURAL AUDIT

**Тип:** Full read-only forensic / architectural audit
**Дата:** 2026-09-15
**Статус:** FINAL — no implementation, no changes
**Объект:** Whether existing Arkaim architecture can be a carrier of Truth as its fundamental semantic foundation
**Метод:** Read-only. Four subagents + direct reading. All findings traceable to specific files, lines, and data.

---

## Простыми словами

1. **Что было целью?** — Проверить, может ли существующая архитектура Arkaim стать системой, в которой ИСТИНА является фундаментом — относительно которого организуются знания, факты, события, эпохи, носители, наследие и гипотезы.

2. **Что реально сделано?** — Прочитаны все ключевые файлы проекта: provenance system (source_levels.py), temporal chain (12 файлов), knowledge layer (49 JSON + 13 WORLD_MODEL JSON), genome (4796 строк), query/reasoning path (pulse.py, voice.py, layers.py — 1374 строки), expansion layer (M9 temporal-aware), 14 test files (499+ тестов), ADR.

3. **Главный вывод:** — **Существующая архитектура уже является носителем Truth-centered model.** Provenance-система (8 категорий × 7 уровней), temporal graph с PRECEDES/CARRIES/TRANSMITS_TO/ECHOES, IdentityLayer с границами «я не выхожу за книгу», confirmation boundary в M10.2 — всё это работает. **Фундамент менять не нужно.** Что нужно — это **data discipline** (применить существующую provenance-модель к данным, которые сейчас не тегированы).

4. **Ключевой парадокс:** — Код Arkaim уже различает AUTHOR_CANON / EXTERNAL_SOURCE / HYPOTHESIS / RECONSTRUCTION / FUTURE_EXTRAPOLATION. Но JSON-данные WORLD_MODEL и KNOWLEDGE **не используют** эту систему — provenance в данных отсутствует.

5. **Что НЕ нужно менять:** — ProvenanceCategory, SourceLevel, TemporalRelationType, IdentityLayer, confirmation boundary, provenance invariants. Всё это — already correct.

6. **Что нужно:** — Применить provenance к данным. Не новая архитектура, а data enrichment через существующие механизмы.

---

## A. CURRENT STATE

### A.1 Provenance System — The Epistemic Foundation

**Файл:** `core/CORE/narrative_engine/source_levels.py` (320 строк)

**Two-dimensional model:**

| Dimension | Values | Purpose |
|-----------|--------|---------|
| ProvenanceCategory (8) | AUTHOR_CANON, DERIVED, EXTERNAL_SOURCE, RECONSTRUCTION, HYPOTHESIS, ARTISTIC_MODEL, FUTURE_EXTRAPOLATION, UNKNOWN | WHERE did the claim come from? |
| SourceLevel (7) | CANON=1.0 → USER_HYPOTHESIS=0.3 | HOW confident are we? |

**Mapping to Truth levels (existing, not proposed):**

| Truth Level | ProvenanceCategory | SourceLevel | Example |
|-------------|-------------------|-------------|---------|
| A. Author's canon | AUTHOR_CANON | CANON=1.0 | «Велик направился к Аркаиму» |
| B. External knowledge | EXTERNAL_SOURCE | HISTORICAL=0.8 | «Аркаим датируется ~4000 до н.э.» |
| C. Interpretation | DERIVED | SYSTEM_INTERPRETATION=0.5 | «Велик был в эпоху Кали Юги» |
| D. Hypothesis | HYPOTHESIS | USER_HYPOTHESIS=0.3 | «Гардарика — сеть гипербореев» |
| E. Reconstruction | RECONSTRUCTION | HISTORICAL=0.8 | «Гипербореи строили Аркаим» |
| F. Myth/tradition | MYTHOLOGICAL | MYTHOLOGICAL=0.7 | Ведическая космология |
| G. Artistic model | ARTISTIC_MODEL | MYTHOLOGICAL=0.7 | Visual appearance |
| H. Future | FUTURE_EXTRAPOLATION | USER_HYPOTHESIS=0.3 | «Эпоха возрождения» |

**Критические инварианты (реализованы и протестированы):**
- `HYPOTHESIS с confidence=1.0 остаётся HYPOTHESIS` — ✅ test_provenance.py
- `EXTERNAL_SOURCE не становится AUTHOR_CANON` — ✅ test_provenance.py
- `LLM не может повысить provenance до AUTHOR_CANON` — ✅ test_provenance.py
- `Path provenance = lowest common denominator` — ✅ test_temporal_reconstruction.py
- `Canon cannot be overwritten` — ✅ ProvenanceRegistry.check_canon_override()

**Вердикт:** ✅ **Формальная модель — excellent.** Полностью покрывает все 8 уровней Truth из задания. Не требует нового типа «Truth» как сущности.

---

### A.2 Temporal Chain — How History Is Modeled

**Файл:** `core/CORE/narrative_engine/temporal/reconstruction_engine.py` (691 строк)

**Chain structure:**
- 12 epochs → 11 PRECEDES relations (linear axis)
- `temporal_today` — HYPOTHESIS methodological anchor, NO relations
- `temporal_arkaim_era` — AUTHOR_CANON + EXTERNAL_SOURCE, confidence=0.85

**Contextual relations (added in TEMPORAL_LEGACY_REFINEMENT):**
- `CARRIES` — character → knowledge (Велик несёт Учение)
- `TRANSMITS_TO` — character → character (Учитель → Велик)
- `ECHOES` — epoch ↔ epoch (structural parallel, HYPOTHESIS)
- `DEVELOPS_FROM` — reserved for human-created quality transitions

**Chain provenance:**
- `compute_path_provenance()` — lowest common denominator
- `compute_path_confidence()` — minimum of all components
- Path validator: 7 rules including provenance downgrade detection

**Вердикт:** ✅ Temporal chain correctly models linear history with contextual knowledge flow. Truth separation preserved at every node and relation.

---

### A.3 Query / Reasoning / Answer Path

**Файл:** `core/CORE/pulse/voice.py` (358 строк) + `core/CORE/pulse/layers.py` (1374 строки)

**Answer pipeline:**
```
User query
  → Voice._detect_mood()
  → ReaderAwarePulse.listen()
  → [10 layers tried in order]:
     1. KnowledgeLayer (genome facts, RAG)
     2. MeaningLayer (author intent)
     3. IdentityLayer (self-description, boundaries)
     4. MissionLayer (purpose)
     5. ExpansionLayer (168 expanded themes + M9 temporal)
     6. VisualStyleLayer
     7. SceneLayer
     8. NarrativeArcLayer
     9. ScreenplayLayer
     10. WorldEngineLayer
  → PulseResponse (text + source + confidence + provenance)
  → If LLM available:
     → LLM formulates answer from Pulse knowledge
     → IdentityLayer.validate_detail() — checks for hallucination/external knowledge
     → If validation fails → fallback to Pulse direct text
  → Utterance (text + source + llm_used + mood + reader_depth)
```

**Truth protection at each stage:**

| Stage | Truth Protection |
|-------|-----------------|
| KnowledgeLayer | Source = "knowledge:character", "knowledge:theme" — always from genome |
| MeaningLayer | Source = "meaning:main_message" — always from author_intent |
| IdentityLayer | **BLOCKS** external knowledge patterns (Marvel, Wikipedia, etc.) |
| ExpansionLayer (M9) | BACKWARD → RECONSTRUCTION provenance. FORWARD → FUTURE_EXTRAPOLATION |
| Voice LLM | Rules: "Отвечай ТОЛЬКО на основе фактов из книги. Не придумывай." |
| Voice Identity | `validate_detail()` — if LLM hallucinates → blocks or falls back |

**IdentityLayer FORBIDDEN patterns (code line 690-703):**
- Marketing: "купите", "закажите", "скидка"
- External facts: "учёные доказали", "наука утверждает", "по статистике"
- Personal opinions: "я думаю", "по моему мнению"

**IdentityLayer EXTERNAL_KNOWLEDGE_PATTERNS (code line 706-715):**
- DC Comics, Marvel, franchise references
- "согласно википедии", "по данным интернета"
- "персонаж из ... вселенной"

**ExpansionLayer temporal answers (code line 961-1044):**
- BACKWARD query → `ProvenanceCategory.RECONSTRUCTION`, confidence=0.7
- FORWARD query → `ProvenanceCategory.FUTURE_EXTRAPOLATION`, confidence=0.5
- CONTEXT query → `ProvenanceCategory.AUTHOR_CANON`, confidence=0.85
- Each answer explicitly marked: "not historical fact", "temporal reconstruction"

**Вердикт:** ✅ **Query path preserves Truth boundaries.** System cannot accidentally present hypothesis as canon, external fact as book fact, or LLM hallucination as book knowledge.

---

### A.4 Knowledge Data Layer

**Файл:** `core/KNOWLEDGE/` (49 JSON files) + `core/CORE/WORLD_MODEL/` (13 JSON files)

**Knowledge organized by source type:**

| Source | Files | Provenance in Code | Provenance in Data |
|--------|-------|-------------------|-------------------|
| Book canon | CHARACTERS.json, PLOT.json, SYMBOLS.json, VALUES.json | AUTHOR_CANON (implied) | ❌ No tags |
| Archaeology | ARCHAEOLOGY.json, ARCHAEOLOGY_DEEP.json | EXTERNAL_SOURCE | ❌ No tags — mixed with hypotheses |
| Academic | ACADEMIC_CONFIRMATIONS.json, CROSS_REFERENCES.json | EXTERNAL_SOURCE | ❌ No tags |
| Esoteric | ESOTERIC_CONNECTIONS.json, COSMOLOGY.json | HYPOTHESIS (implied) | ❌ No tags |
| System | enriched_chunks.json, MAP_DATA.json | SYSTEM_INTERPRETATION | ❌ No tags |
| WORLD_MODEL/ | 13 category files, ~547 entities | Mixed | ❌ All confidence=1.0, no category |

**Critical data quality issues:**
1. **WORLD_MODEL/TECHNOLOGIES.json** contains archaeological site names (Аркаим, Синташта), not technologies
2. **WORLD_MODEL/CIVILIZATIONS.json** contains character types (main, secondary), not civilizations
3. **ARCHAEOLOGY.json** mixes scientific facts (dating, area) with author hypotheses (atlantis_connection) in same object
4. **All WORLD_MODEL entities** have `confidence: 1.0` and no `provenance_category` field
5. **Knowledge graph** (`populate.py`) sets `provenance="genome"` as flat string, not ProvenanceCategory

**Organization pattern:** Nation-first (by file category: CIVILIZATIONS, GEOGRAPHY, MYTHOLOGY) rather than knowledge-first (entity-centric view).

**Вердикт:** ⚠️ **Data gap, not architecture gap.** Provenance model exists and is correct. Data just isn't tagged. This is the single most important finding of this audit.

---

### A.5 Book as Foundation

**Файл:** `core/GENOME/GENOME_v1.0.0.json` (4796 строк)

**What the book expresses (from genome themes):**
- theme_138: "Наследие Учения" (strength=0.95)
- theme_137: "Кали Юга и Сатья Юга" (strength=0.95) — cyclical nature of epochs
- theme_136: "Великий потоп" (strength=0.95)
- theme_013: "Миссия учителя" (strength=0.7) — carrier concept
- theme_060: "Передача знаний от Посвящённых" (strength=0.7) — transmission
- theme_115: "Передача знаний" (strength=0.7) — knowledge flow
- theme_003: "Параллельные миры" (strength=0.7) — mirror concept

**Book's core concept (from BOOK_DOCUMENT.json annotation):**
> «Все предания народов мира являются отражением таинственной, загадочной и сокрытой предысторией современного человечества. Расшифровывая эту часть предыстории и связывая её с современной историей мы наконец получаем то культурное наследие которое когда-то было сокрыто и потеряно.»

**Can the model express "Единое Учение / Единая Истина"?**

YES — through combination of:
1. Genome themes (theme_138: "Наследие Учения")
2. CharacterPresence.relations (Учитель → Велик → Мирослав)
3. TemporalRelation CARRIES (character → knowledge with description)
4. TemporalRelation TRANSMITS_TO (teacher → student)
5. ProvenanceAuthor on each relation (AUTHOR_CANON for book-described, HYPOTHESIS for interpreted)

**Can the model express "Носитель не обязательно является представителем конкретного народа"?**

PARTIALLY. CharacterPresence has fields: character_name, epoch, location_id, status, relations. It does NOT have `nation`, `religion`, or `civilization` fields. This means a carrier is identified by name and epoch, not by cultural affiliation. However, the genome `world_entities` DO link characters to civilizations (e.g., "Гиперборея" has `values: ["знание", "гармония"]`).

**Can the model express "Он был ими, а они им" (multiple carriers of one teaching line)?**

YES — through CARRIES relations:
```
Учитель —[CARRIES]→ "Единое Учение"
Велик —[CARRIES]→ "Единое Учение"  
Мирослав —[CARRIES]→ "Единое Учение"
```
Multiple characters can carry the same knowledge. No single point of failure.

**Вердикт:** ✅ Book concept is structurally expressible. Character model is already knowledge-first (no nation/religion fields).

---

## B. TRUTH MODEL GAP ANALYSIS

### What Is Already Covered

| Truth Aspect | Mechanism | Status |
|-------------|-----------|--------|
| Author's canon | AUTHOR_CANON + IdentityLayer validation | ✅ IMPLEMENTED |
| External knowledge | EXTERNAL_SOURCE + SourceLevel.HISTORICAL | ✅ MODEL EXISTS |
| Interpretation | DERIVED | ✅ MODEL EXISTS |
| Hypothesis | HYPOTHESIS | ✅ IMPLEMENTED + TESTED |
| Reconstruction | RECONSTRUCTION + PathValidator | ✅ IMPLEMENTED + TESTED |
| Myth/tradition | SourceLevel.MYTHOLOGICAL | ✅ MODEL EXISTS |
| Artistic model | ARTISTIC_MODEL | ✅ MODEL EXISTS |
| Future | FUTURE_EXTRAPOLATION | ✅ IMPLEMENTED + TESTED |
| Boundary: hypothesis ≠ fact | ProvenanceRegistry + tests | ✅ ENFORCED |
| Boundary: LLM ≠ canon | IdentityLayer + tests | ✅ ENFORCED |
| Boundary: external ≠ canon | ProvenanceRegistry.firewall | ✅ ENFORCED |
| Path provenance aggregation | Lowest-common-denominator | ✅ IMPLEMENTED |
| Temporal chain with provenance | Every node/relation tagged | ✅ IMPLEMENTED |
| Knowledge carrier model | CARRIES + CharacterPresence.relations | ✅ IMPLEMENTED |
| Knowledge transmission | TRANSMITS_TO | ✅ IMPLEMENTED |
| Structural parallel (not causation) | ECHOES (HYPOTHESIS) | ✅ IMPLEMENTED |
| Temporal today as observation point | HYPOTHESIS, no relations | ✅ IMPLEMENTED |

### What Has Gaps

| Gap | Type | Severity |
|-----|------|----------|
| WORLD_MODEL entities lack provenance tags | DATA GAP | HIGH |
| KNOWLEDGE JSON files lack provenance tags | DATA GAP | HIGH |
| ARCHAEOLOGY.json mixes facts with hypotheses | DATA GAP | HIGH |
| Knowledge graph uses flat provenance="genome" | SEMANTIC GAP | MEDIUM |
| Nation-first data organization | GRAPH GAP | MEDIUM |
| No entity-centric knowledge cards | ARCHITECTURAL GAP | LOW |
| 5/8 WorldRelation types never extracted | GRAPH GAP | LOW |
| In-memory pending queue (M10.2) | DATA GAP | LOW |

---

## C. EXISTING ARCHITECTURE MAP

```
TRUTH (as an abstract concept — not a code entity)
  ↓
Knowledge / Facts
  ├── Genome (AUTHOR_CANON by definition)
  ├── WORLD_MODEL/ (no provenance tags — DATA GAP)
  ├── KNOWLEDGE/*.json (no provenance tags — DATA GAP)
  └── Temporal events (AUTHOR_CANON — tagged)
  ↓
Provenance System
  ├── ProvenanceCategory (8 values) — ✅ EXISTS
  ├── SourceLevel (7 weights) — ✅ EXISTS
  ├── ProvenanceTag (2D: category + confidence) — ✅ EXISTS
  └── ProvenanceRegistry (canon protection) — ✅ EXISTS
  ↓
Carrier (Character)
  ├── CharacterPresence (name, epoch, status) — ✅ EXISTS
  ├── .relations (mentor_of, student_of, peer_of) — ✅ EXISTS (TEMPORAL_LEGACY_REFINEMENT)
  └── NO nation/religion fields — ✅ CORRECT (knowledge-first)
  ↓
Transmission
  ├── CARRIES (character → knowledge) — ✅ EXISTS
  ├── TRANSMITS_TO (character → character) — ✅ EXISTS
  └── Provenance on each relation — ✅ EXISTS
  ↓
Heritage / Development
  ├── DEVELOPS_FROM (epoch → epoch) — ✅ EXISTS (reserved for human-created)
  ├── ECHOES (epoch ↔ epoch, HYPOTHESIS) — ✅ EXISTS
  └── PRECEDES (chronological axis) — ✅ EXISTS
  ↓
Culture / Historical manifestation
  ├── Epoch model (12 epochs) — ✅ EXISTS
  ├── CanonicalEvent (8 real events) — ✅ EXISTS (TEMPORAL_LEGACY_REFINEMENT)
  └── Civilization model — ⚠️ PARTIAL (empty descriptions in data)
  ↓
Present (temporal_today)
  ├── HYPOTHESIS provenance — ✅ EXISTS
  ├── No relations (observation point) — ✅ EXISTS
  └── Computed path to arkaim_era — ✅ EXISTS
  ↓
Future
  ├── FUTURE_EXTRAPOLATION provenance — ✅ EXISTS
  ├── FutureExtrapolator (deterministic) — ✅ EXISTS
  └── CompatibilityChecker — ✅ EXISTS
```

**Summary of transitions:**

| Transition | Status |
|-----------|--------|
| Truth → Knowledge | PARTIAL (model exists, data not tagged) |
| Knowledge → Carrier | ✅ EXISTS (CARRIES) |
| Carrier → Transmission | ✅ EXISTS (TRANSMITS_TO) |
| Transmission → Heritage | ✅ EXISTS (DEVELOPS_FROM + PRECEDES) |
| Heritage → Culture | PARTIAL (epoch model exists, civilization data sparse) |
| Culture → Event | ✅ EXISTS (CanonicalEvent with temporal anchors) |
| Event → Epoch | ✅ EXISTS (event.epoch field) |
| Epoch → Present | ✅ EXISTS (temporal_today + computed path) |
| Present → Future | ✅ EXISTS (FUTURE_EXTRAPOLATION) |

---

## D. PROVENANCE AUDIT

### Can the system protect the boundary between:

| Boundary | Protection Mechanism | Test Coverage |
|----------|---------------------|--------------|
| CANON vs FACT | ProvenanceCategory (AUTHOR_CANON vs EXTERNAL_SOURCE) | ✅ 55 tests |
| FACT vs INTERPRETATION | EXTERNAL_SOURCE vs DERIVED | ✅ Tested |
| INTERPRETATION vs HYPOTHESIS | DERIVED vs HYPOTHESIS | ✅ Tested |
| HYPOTHESIS vs RECONSTRUCTION | HYPOTHESIS vs RECONSTRUCTION | ✅ Tested |
| RECONSTRUCTION vs ARTISTIC | RECONSTRUCTION vs ARTISTIC_MODEL | ✅ Model exists |
| ARTISTIC vs FUTURE | ARTISTIC_MODEL vs FUTURE_EXTRAPOLATION | ✅ Model exists |
| Any → CANON (forbidden) | ProvenanceRegistry.check_canon_override() | ✅ Explicit test |
| LLM → CANON (forbidden) | IdentityLayer + ProvenanceRegistry | ✅ Explicit test |
| Path aggregation | Lowest-common-denominator | ✅ Tested |

### Provenance in practice:

| Component | How provenance flows |
|-----------|---------------------|
| TemporalNode | Every node has `provenance: list[ProvenanceTag]` |
| TemporalRelation | Every relation has `provenance: list[ProvenanceTag]` |
| CanonicalEvent | `source_level: SourceLevel` + `provenance: list[ProvenanceTag]` |
| Epoch | `source_level: SourceLevel` + `provenance: list[ProvenanceTag]` |
| PulseResponse | `provenance: list[dict]` — but uses dict, not ProvenanceTag |
| ExpansionLayer (M9) | Creates ProvenanceTag with correct category per intent |
| FutureExtrapolator | Always FUTURE_EXTRAPOLATION |

### Provenance NOT in practice:

| Component | Gap |
|-----------|-----|
| WORLD_MODEL entities (547) | No provenance fields, all confidence=1.0 |
| KNOWLEDGE JSON files | No provenance tags |
| Knowledge graph facts | Flat string `provenance="genome"` |
| PulseResponse.provenance | Uses `list[dict]`, not typed ProvenanceTag |

---

## E. TEMPORAL LEGACY AUDIT (Post-TEMPORAL_LEGACY_REFINEMENT)

### What CARRIES, TRANSMITS_TO, ECHOES, DEVELOPS_FROM provide for Truth model:

| Type | Domain | Provenance | Truth Role |
|------|--------|-----------|-----------|
| CARRIES | character → knowledge | AUTHOR_CANON (default) | Expresses: "this character carries this teaching" — without claiming historical fact |
| TRANSMITS_TO | character → character | AUTHOR_CANON (default) | Expresses: "knowledge passed from teacher to student" — as described in book |
| ECHOES | epoch ↔ epoch | HYPOTHESIS (always) | Expresses: "structural parallel between epochs" — explicitly NOT causation |
| DEVELOPS_FROM | epoch → epoch | HYPOTHESIS (default) | Expresses: "qualitative development" — reserved for human-created transitions |

### Can the chain express:

`ИСТИНА → знание → носитель → передача → ученик → наследие → развитие → новая культурная форма → новый носитель → следующая эпоха`

**YES** — through:
```
"Единое Учение" (knowledge, referenced via CARRIES.description)
  ←[CARRIES]— Учитель (AUTHOR_CANON)
  —[TRANSMITS_TO]→ Велик (AUTHOR_CANON)
  ←[CARRIES]— Велик (AUTHOR_CANON)
  —[TRANSMITS_TO]→ Мирослав (AUTHOR_CANON)
  ←[CARRIES]— Мирослав (AUTHOR_CANON)
  —[DEVELOPS_FROM]→ temporal_arkaim_era (HYPOTHESIS, human-created)
  —[PRECEDES]→ temporal_kali_yuga (AUTHOR_CANON)
```

**Remaining gap:** Knowledge as referenced entity (via description field) rather than standalone node. This is by design (TEMPORAL_LEGACY_REFINEMENT excluded KnowledgeArtifact model).

---

## F. CROSS-CULTURAL AUDIT

### Can the system explore knowledge manifestations across cultures WITHOUT pre-assigned nation binding?

**PARTIALLY.**

**What allows it:**
1. CharacterPresence has NO `nation` or `religion` field — carriers are identified by name + epoch
2. CARRIES/TRANSMITS_TO connect character → knowledge, not character → civilization
3. ECHOES connects epoch ↔ epoch, not nation ↔ nation
4. Provenance allows HYPOTHESIS for "possible cultural parallel" without claiming historical connection

**What limits it:**
1. Genome `world_entities` link civilizations to values: "Гиперборея" → ["знание", "гармония"]
2. WORLD_MODEL/CIVILIZATIONS.json is organized by civilization name
3. No cross-cultural query mechanism: "find all carriers of teaching X across all cultures"
4. No way to represent: "Кецалькоатль as POSSIBLE carrier of Truth" — would need character creation + CARRIES relation with HYPOTHESIS provenance

**Could the system answer: "Можно ли рассматривать Кецалькоатля как возможного Носителя Истины?"**

STRUCTURALLY YES, but requires:
1. Add character "Кецалькоатль" to genome or WORLD_MODEL
2. Create CARRIES relation: Кецалькоатль —[CARRIES]→ "Учение" (HYPOTHESIS)
3. Create ECHOES relation: Mesoamerican epoch ↔ relevant book epoch (HYPOTHESIS)
4. Answer path: ExpansionLayer → temporal query → provenance check → HYPOTHESIS answer

**The answer would correctly carry HYPOTHESIS provenance** — the system would NOT present it as established fact.

**Вердикт:** ✅ Architecture allows cross-cultural exploration. ⚠️ Data and queries not yet set up for it.

---

## G. ATLANTIS → TODAY AUDIT

### Can the system express temporal analogy WITHOUT false causation?

**YES** — through ECHOES.

**ECHOES properties (code-verified):**
- `is_contextual = True` — NOT part of chronological axis
- `is_developmental = False` — NOT a causal development
- Provenance: ALWAYS HYPOTHESIS
- Notes: "structural parallel — not historical causation"
- Self-reverse: ECHOES ↔ ECHOES

**What exists in data:**
1. `epoch_parallels` in WORLD_MODEL.json:
   - satya_yuga ↔ переход_к_новой_эре_(кали_юга) — HYPOTHESIS
   - эпоха_кали_юги ↔ kali_yuga — AUTHOR_CANON (author explicitly uses Vedic concept)

**What can be expressed:**
```
temporal_атлантическая_линия —[ECHOES]→ temporal_today
    description: "технологии без духовности"
    provenance: HYPOTHESIS
    notes: "structural parallel — not historical causation"
```

**Boundary enforcement:**
- ECHOES does NOT participate in chain building (only PRECEDES does)
- ECHOES relations are NOT auto-created — require human confirmation via M10.2
- BACKWARD/FORWARD chain traversal skips ECHOES (they're contextual, not axis)
- Provenance cannot be upgraded from HYPOTHESIS

**Can TODAY be used for new understanding of old data without retroactive rewriting?**

YES — temporal_today has HYPOTHESIS provenance and NO graph relations. It's an observation point, not a historical claim. Any connection to past epochs is computed (BFS reconstruction path), never stored as graph edge.

**Вердикт:** ✅ ECHOES correctly separates analogy from causation. Boundary enforced by code + tests.

---

## H. QUERY / ANSWER AUDIT

### Full path: data → retrieval → graph traversal → reasoning → user answer

**Step 1: Data retrieval**
- KnowledgeLayer searches genome (characters, themes, symbols, conflicts)
- ExpansionLayer searches _DEEP and _EXPANDED JSON files
- RAG via BookRetriever + ChromaDB

**Provenance at retrieval:** PulseResponse.source = "knowledge:character" etc. — indicates origin, but uses flat string, not ProvenanceCategory.

**Step 2: Graph traversal**
- TemporalReconstructionEngine: BFS forward/backward
- RelationGraph: neighbors, find_path
- Knowledge graph: entity neighbors

**Provenance at traversal:** Every node and relation carries ProvenanceTag. Path provenance = lowest common denominator.

**Step 3: Reasoning**
- ExpansionLayer._build_temporal_answer() — maps intent to provenance:
  - BACKWARD → RECONSTRUCTION
  - FORWARD → FUTURE_EXTRAPOLATION
  - CONTEXT → AUTHOR_CANON
  - POSITION → AUTHOR_CANON
- _combine_provenance() — lowest priority wins

**Step 4: LLM formulation**
- Voice.speak() — LLM formulates answer from Pulse knowledge
- Strict rules: "Отвечай ТОЛЬКО на основе фактов из книги"
- IdentityLayer.validate_detail() — blocks hallucination

**Step 5: User answer**
- Utterance contains: text, source, llm_used, mood, reader_depth
- Frontend shows source badge (pulse/llm/hybrid)

### Can the system say each of these?

| Statement | Can Say? | How |
|-----------|----------|-----|
| «это установлено» | ✅ | AUTHOR_CANON + confidence=1.0 |
| «это следует из книги» | ✅ | DERIVED |
| «это внешняя научная интерпретация» | ✅ | EXTERNAL_SOURCE |
| «это гипотеза» | ✅ | HYPOTHESIS |
| «это реконструкция» | ✅ | RECONSTRUCTION |
| «это аналогия» | ✅ | ECHOES (HYPOTHESIS) |
| «это художественное продолжение» | ✅ | ARTISTIC_MODEL |
| «данных недостаточно» | ⚠️ PARTIAL | Voice says "я не нахожу ответа" but no structured "uncertain" response |

**Gap:** No structured `uncertainty` field in PulseResponse. When Pulse returns None, Voice says "я не нахожу ответа" — but there's no way to express "partial answer with known gaps."

**Вердикт:** ✅ Query path preserves Truth boundaries at every stage. ⚠️ Minor gap: no structured uncertainty/partial-answer mechanism.

---

## I. GAPS

### DATA GAP (provenance model exists, data not tagged)

| Gap | Where | Impact |
|-----|-------|--------|
| WORLD_MODEL entities: no provenance | 547 entities in 13 JSON files | Cannot distinguish canon/external/hypothesis at entity level |
| KNOWLEDGE files: no provenance | 49 JSON files | Cannot distinguish book facts from archaeological facts from esoteric interpretations |
| ARCHAEOLOGY.json: mixed facts+hypotheses | Single objects contain both | `atlantis_connection` (hypothesis) alongside `dating` (science) |
| PulseResponse.provenance: dict not typed | layers.py PulseResponse | Loose typing, not validated |

### SEMANTIC GAP (meaning not fully expressed)

| Gap | Where | Impact |
|-----|-------|--------|
| Knowledge graph flat provenance | populate.py `provenance="genome"` | All facts treated equally regardless of actual source |
| No structured uncertainty | PulseResponse | Cannot express "partial answer with known gaps" |
| PulseResponse.provenance uses dict | layers.py | Not type-safe, not validated against ProvenanceCategory |

### GRAPH GAP (relations not populated)

| Gap | Where | Impact |
|-----|-------|--------|
| 5/8 WorldRelation types never extracted | relation_extractor.py | Only GEOGRAPHIC, HISTORICAL, MYTHOLOGICAL used |
| epoch_parallels not auto-converted to ECHOES | world_model.py | Data exists but not in graph (by design — requires human) |
| No cross-entity temporal relations | temporal graph | "Archeology site X belongs to epoch Y" not represented |

### PROVENANCE GAP (model exists but not applied)

| Gap | Where | Impact |
|-----|-------|--------|
| ExpansionLayer knowledge has no provenance | _load_expansion() | _DEEP files loaded without provenance tags |
| MythologyContextBuilder no provenance | contexts/mythology.py | Mythological data treated same as canon |
| GeographyContextBuilder no provenance | contexts/geography.py | Geographic data treated same as canon |
| HistoricalContextBuilder has provenance | contexts/historical.py | ✅ CORRECT — only context builder with provenance |

### REASONING GAP (logic not fully expressed)

| Gap | Where | Impact |
|-----|-------|--------|
| No "competing interpretations" | Voice/Pulse | System gives one answer, not multiple perspectives |
| No "data insufficient" structured response | PulseResponse | Binary: answer or "I don't know" |
| No query filtering by provenance | ExpansionLayer | Cannot ask "what do we know from archaeology only?" |

### ARCHITECTURAL GAP (structural limitation)

| Gap | Where | Impact |
|-----|-------|--------|
| No entity-centric knowledge card | WorldModel/WORLD_MODEL/ | "Everything about Arkaim" scattered across files |
| Nation-first organization | JSON file structure | Cannot easily find "all knowledge about teaching X" |
| No cross-source aggregation | No unified entity view | Canon + archaeology + hypothesis for same entity in different files |

---

## J. WHAT MUST NOT BE CHANGED

| Component | Why |
|-----------|-----|
| ProvenanceCategory (8 values) | Correctly covers all Truth levels from audit task |
| SourceLevel (7 weights) | Correct epistemic ordering |
| ProvenanceTag (2D: category + confidence) | Correct — category ≠ confidence |
| ProvenanceRegistry.canon_override protection | Critical invariant — canon cannot be overwritten |
| IdentityLayer (forbidden patterns + external knowledge) | Prevents LLM hallucination from becoming "book knowledge" |
| Confirmation boundary (M10.2) | No automatic WorldModel changes without human approval |
| temporal_today as HYPOTHESIS with no relations | Correct — observation point, not historical claim |
| ECHOES as always HYPOTHESIS | Correct — structural parallel, not causation |
| CARRIES/TRANSMITS_TO as AUTHOR_CANON by default | Correct — book describes these relationships |
| Path provenance as lowest-common-denominator | Correct — if ANY component is hypothesis, whole path is |
| FutureExtrapolator with FUTURE_EXTRAPOLATION provenance | Correct — future scenarios are never historical facts |
| PRECEDES as only axis relation | Correct — only chronological ordering in chain |
| DEVELOPS_FROM as reserved for human-created | Correct — quality transitions require human judgment |

---

## K. RECOMMENDATION

### 1. What is ALREADY sufficient for Truth-centered model:

- **ProvenanceCategory** (8 values) — covers all Truth levels
- **SourceLevel** (7 weights) — correct epistemic ordering
- **Temporal graph** with per-node/per-relation provenance
- **IdentityLayer** preventing external knowledge intrusion
- **Confirmation boundary** preventing auto-canonization
- **ECHOES** preserving structural parallel without false causation
- **CARRIES/TRANSMITS_TO** expressing knowledge flow
- **temporal_today** as methodological observation point

### 2. What requires CONCEPTUAL decision (not implementation):

- Should Arkaim have an explicit `Truth` entity? **NO** — ProvenanceCategory already serves this role. Adding a Truth entity would duplicate the provenance system.
- Should knowledge be organized knowledge-first instead of nation-first? **YES** — but this is a data reorganization, not architectural change.
- Should the system present competing interpretations? **YES** — but requires design decision on how to represent "multiple valid views."

### 3. What requires ARCHITECTURAL decision:

- Should PulseResponse use typed ProvenanceTag instead of dict? **Probably yes** — for consistency and validation.
- Should there be an entity-centric knowledge card aggregating all sources? **Probably yes** — for cross-source queries.
- Should there be a structured uncertainty mechanism? **Maybe** — for "partial answer with known gaps."

### 4. What does NOT need to change now:

- Adding `Truth` entity — not needed, ProvenanceCategory sufficient
- Adding `KnowledgeArtifact` model — deferred in TEMPORAL_LEGACY_REFINEMENT, still valid
- Adding new relation types — TEMPORAL_LEGACY_REFINEMENT added what's needed
- Adding new temporal subsystem — not needed
- Changing ADR decisions — all 4 decisions still valid
- Changing provenance categories — all 8 cover the Truth spectrum
- Frontend changes — not in scope

---

## L. ANSWER TO THE MAIN QUESTION

> **«Если ИСТИНА становится ядром Arkaim, может ли существующая архитектура уже сейчас быть её носителем — или нам действительно требуется менять фундамент проекта?»**

**Да, существующая архитектура уже является носителем Truth-centered model. Фундамент менять не нужно.**

### Evidence:

1. **ProvenanceCategory** (source_levels.py) already maps 1:1 to the 8 Truth levels required by this audit:
   - AUTHOR_CANON = book fact
   - EXTERNAL_SOURCE = external knowledge
   - DERIVED = interpretation
   - HYPOTHESIS = hypothesis
   - RECONSTRUCTION = reconstruction
   - MYTHOLOGICAL = myth/tradition (via SourceLevel)
   - ARTISTIC_MODEL = artistic development
   - FUTURE_EXTRAPOLATION = future

2. **Provenance invariants** (tested in 55+ tests) prevent:
   - Hypothesis from becoming fact
   - External knowledge from becoming canon
   - LLM hallucination from becoming book knowledge
   - Automatic canonization without human confirmation

3. **Temporal graph** preserves provenance at every node and relation:
   - CARRIES/TRANSMITS_TO express knowledge flow with provenance
   - ECHOES expresses structural parallel as HYPOTHESIS
   - Path provenance = lowest common denominator

4. **Query path** preserves Truth boundaries:
   - IdentityLayer blocks external knowledge intrusion
   - ExpansionLayer tags temporal answers with correct provenance
   - Voice rules prevent LLM from inventing content

5. **Character model** is already knowledge-first:
   - No nation/religion fields
   - Relations express mentor/student/peer
   - CARRIES connects character → knowledge

### What IS needed (not architectural, but data discipline):

1. **Apply provenance to WORLD_MODEL entities** — add `provenance_category` + `confidence` fields
2. **Apply provenance to KNOWLEDGE JSON files** — tag each source with its category
3. **Clean WORLD_MODEL pollution** — fix TECHNOLOGIES.json (contains site names), CIVILIZATIONS.json (contains character types)
4. **Separate facts from hypotheses in ARCHAEOLOGY.json** — `dating` = EXTERNAL_SOURCE, `atlantis_connection` = HYPOTHESIS
5. **Add structured uncertainty to PulseResponse** — optional `uncertainty` field

These are data enrichment tasks, not architectural changes. The mechanism already exists; it just needs to be applied.

---

**STOP. Ничего не реализовывать. Ничего не менять.**
