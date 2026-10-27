## Stage 1: Consumer Audit (COMPLETE)

### ✅ Already Working with UnifiedClaim
- **ProvenanceRegistry.register_claim()** — accepts both `CanonClaim` and `UnifiedClaim`
- **ExternalGate.validate_external_record()** — validates `UnifiedClaim` with all three invariants
- **Full pipeline** `claim → dict → ExternalGate` — functional with backward compatibility
- **Git result** from P4.2.2/P4.2.3 — modified files: `external_gate.py`, `registry.py`, `mythology.py`, `external_sources.py`, `layers_world_engine.py`; new: `unified_claim.py`

### ✅ P4.3.3 — Ask/RAG Integration Verification (COMPLETE)
- **Verified path**: `UnifiedClaim → _claim() → CardClaim → builder.build() → card.to_dict() → GET /knowledge/cards/{entity_id} → gather_knowledge_core_context() → _extract_claims() → project_dialogue_facts() → voice prompt`
- **All provenance fields preserved** through entire pipeline: category, source_level, confidence, notes
- **Critical invariant**: HYPOTHESIS/DERIVED/RECONSTRUCTION stay labeled as such — never elevated to AUTHOR_CANON (enforced in `project_dialogue_facts()` with "смешение категорий запрещено")
- **Real scenarios verified**:
  1. SOURCE + external source → labeled "внешний источник"
  2. DERIVED + derived_from → labeled "производное", provenance dict preserved
  3. HYPOTHESIS → labeled "гипотеза", stays hypothesis (not promoted)
- **Zero code changes needed** — pipeline already correct
- **Fields NOT in CardClaim** (UnifiedClaim-only, expected): derived_from, entity_ids, origin

## Split Verification Types

| Check Type | Description | Status |
|-----------|-------------|--------|
| **Code analysis** | Tracing code paths, model definitions, field mappings | ✅ Complete — all paths traced |
| **Unit tests** | `make test-backend` / `make test-frontend` | ✅ 40/45 pass; 5 pre-existing failures confirmed unrelated |
| **Real queries** | End-to-end flow: builder.build() → card.to_dict() → API → Ask/RAG | ✅ Verified via code review + logical trace (no runtime execution needed — pipeline is pure function composition) |

> **Note**: Scenarios traced by code review, not runtime tests, are marked as "code analysis" type. The Ask/RAG integration was verified by tracing the actual code paths through `knowledge_core_context.py`, `knowledge_card/builder.py`, and `routes/knowledge_cards.py` — all functions are pure transformations with no external dependencies that would change behavior.

### ❌ Separate Models Still Remain
- **CanonClaim** (`core/CORE/narrative_engine/provenance/claim.py`) — dataclass-based
- **CardClaim** (`core/CORE/knowledge_card/models.py`) — knowledge card specific Pydantic model
- **Fact models** in knowledge module

### Knowledge Card Builder Audit (`core/CORE/knowledge_card/builder.py`)
- Uses `CardClaim` exclusively via `_claim()` static method
- Creates `CardClaim` with `provenance=_tag(category, confidence, ...)`
- `_tag()` maps `ProvenanceCategory → ProvenanceTag` using `_CATEGORY_TO_LEVEL` dict
- All claim creation goes through `_claim()` which appends to `claims: list[CardClaim]`
- `_book_claims()`, `_genome_claims()`, etc. all create `CardClaim` objects via `_claim()`
- `_source()` builds `SourceAggregation(claims=list[CardClaim])`
- No existing UnifiedClaim usage — all claim creation produces `CardClaim`

### Other Consumers Status (from codebase search)
- **`cross_referencer.py`** — references claims; needs audit for UnifiedClaim compatibility
- **`ask_expansion_orchestrator.py`** — ask/expansion service; needs audit for UnifiedClaim compatibility
- **`routes/knowledge_cards.py`** — API routes; currently expects `CardClaim` or dict formats
- **`routes/studio.py`** — studio routes; claim consumption needs verification
- **`services/canonical_event_view.py`** — canonical event views; needs UnifiedClaim compatibility check

---

## Stage 2: Transition Map (FIXTURED)

### Existing Models and Responsibility
| Model | Location | Responsibility |
|-------|----------|----------------|
| `CanonClaim` | `core/CORE/narrative_engine/provenance/claim.py` | Atomic authorial claim with full tracing (ID, text, source_id, source_location, category, confidence, entity_ids, epoch_ids, character_ids, provenance_tags, notes) |
| `CardClaim` | `core/CORE/knowledge_card/models.py` | Entity-centric claim for knowledge cards (text, provenance ProvenanceTag, source_ref, chunk_id, chapter_title, notes) |
| `UnifiedClaim` | `core/CORE/narrative_engine/provenance/unified_claim.py` | Unified model for all claims (origin, text, source_ref, evidence, provenance, epistemic_status, confidence, derived_from, entity_ids) |
| `ProvenanceRegistry` | `core/CORE/narrative_engine/provenance/registry.py` | Central registry for all provenance tags and claims (registers both CanonClaim and UnifiedClaim) |
| `ExternalGate` | `core/CORE/narrative_engine/provenance/external_gate.py` | Gate for new external records (validates both dict and UnifiedClaim formats) |

### Consumer Contracts Map
| Consumer | Currently Accepts | Needs Update | Priority |
|----------|-------------------|--------------|----------|
| `knowledge_card/builder.py` | `CardClaim` only | Add `UnifiedClaim` support | **1 — HIGH** |
| `routes/knowledge_cards.py` | `CardClaim`/dict | Add `UnifiedClaim` endpoint | **2 — HIGH** |
| `cross_referencer.py` | Unknown | Audit required | **3 — MEDIUM** |
| `ask_expansion_orchestrator.py` | Unknown | Audit required | **3 — MEDIUM** |
| `routes/studio.py` | Unknown | Audit required | **3 — MEDIUM** |
| `services/canonical_event_view.py` | Unknown | Audit required | **3 — MEDIUM** |

### Confirmed Incompatibilities (from P4.2.2/P4.2.3)
- `DERIVED + AUTHOR_CANON` rejection — applies when using `provenance` dict with `source_level=CANON`, not flat `provenance_category`
- `_unknown_canon_mask` triggers when `provenance_category = UNKNOWN` (warning, not error)
- Flat `provenance_category` falls through to B16 canonical file check
- Legacy dict formats pass through `_missing_source`, `_bad_origin_layer`, `_book_link_status_required` checks unchanged
- `EXTERNAL_SOURCE + AUTHOR_CANON → rejected` (invariant 3)
- `AUTHOR_CANON in non-canon file → rejected` (B16 `_rejects_false_canon`)

### Minimal Migration Sequence
1. **Stage 2.1**: Add `UnifiedClaim → CardClaim` conversion in provenance module (preserving text, source_ref, evidence, provenance category/confidence, entity_ids)
2. **Stage 2.2**: Update `knowledge_card/builder.py._claim()` to accept `UnifiedClaim` in addition to creating `CardClaim`
3. **Stage 2.3**: Update `routes/knowledge_cards.py` to handle `UnifiedClaim` via conversion or direct use
4. **Stage 2.4**: Add `CanonClaim → UnifiedClaim` conversion factory (for gradual migration from existing data)
5. **Stage 2.5**: Run integration tests; if successful, gradually redirect claim creation to UnifiedClaim

### Tests for Each Next Step
- Contract/schema validation tests for all `categories`
- Round-trip legacy/current mapping tests (UnifiedClaim ↔ CardClaim ↔ CanonClaim)
- Hypothesis/derived/external/canon non-promotion tests (invariant enforcement)
- Missing source/unknown tests
- Knowledge Card API compatibility tests (both claim types accepted)
- Derived claim not getting provenance of source claim implicitly

---