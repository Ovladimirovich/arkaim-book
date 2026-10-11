# PROVENANCE COMPLETION — Forensic Map

## Provenance Creation Points (33 total)

### Format A: Legacy dict ({"type": "...", ...}) — 26 points
These use `provenance=[{"type": "..."}]` — NOT ProvenanceTag.

| File | Line | Layer | Type Tag |
|------|------|-------|----------|
| layers.py | 131 | KnowledgeLayer | themes_summary |
| layers.py | 143 | KnowledgeLayer | characters_summary |
| layers.py | 155 | KnowledgeLayer | values_summary |
| layers.py | 173 | KnowledgeLayer | world_summary |
| layers.py | 219 | KnowledgeLayer | character |
| layers.py | 251 | KnowledgeLayer | theme |
| layers.py | 283 | KnowledgeLayer | symbol |
| layers.py | 312 | KnowledgeLayer | conflict |
| layers.py | 341 | KnowledgeLayer | world_entity |
| layers.py | 364 | KnowledgeLayer | catalog_text |
| layers.py | 403 | KnowledgeLayer | catalog_text |
| layers.py | 432 | KnowledgeLayer | rag_search |
| layers.py | 494 | VisualStyleLayer | style_preset |
| layers.py | 535 | NarrativeArcLayer | narrative_arc |
| layers.py | 551 | NarrativeArcLayer | narrative_arc |
| layers.py | 566 | NarrativeArcLayer | narrative_arc |
| layers.py | 619 | SceneLayer | scene |
| layers.py | 642 | MeaningLayer | author_intent |
| layers.py | 654 | MeaningLayer | author_intent |
| layers.py | 665 | MeaningLayer | author_intent |
| layers.py | 677 | MeaningLayer | author_intent |
| layers.py | 742 | IdentityLayer | identity |
| layers.py | 758 | IdentityLayer | identity |
| layers.py | 813 | MissionLayer | mission |
| layers.py | 825 | MissionLayer | mission |
| layers_world_engine.py | 75 | WorldEngineLayer | world_engine |
| layers.py | 1295 | ScreenplayLayer | screenplay |
| layers.py | 1357 | WorldEngineLayerV2 | world_model |

### Format B: ProvenanceTag (typed) — 4 points
These already use `ProvenanceTag(...)`.

| File | Line | Layer | Category |
|------|------|-------|----------|
| layers.py | 1007 | ExpansionLayer (BACKWARD) | RECONSTRUCTION |
| layers.py | 1040 | ExpansionLayer (FORWARD) | FUTURE_EXTRAPOLATION |
| layers.py | ~1060 | ExpansionLayer (CONTEXT) | AUTHOR_CANON |
| layers.py | ~1080 | ExpansionLayer (POSITION) | AUTHOR_CANON |

### Format C: Empty provenance — 2 points
| File | Line | Layer | Issue |
|------|------|-------|-------|
| layers.py | 1133 | ExpansionLayer (standard) | provenance=[] |
| layers.py | 1150 | ExpansionLayer (standard) | provenance=[] |

## Provenance Loss Points

### Loss 1: ExpansionLayer._standard_respond() (line 1133, 1150)
When ExpansionLayer answers from _DEEP/_EXPANDED data WITHOUT temporal intent,
provenance is EMPTY. This means 168 expanded topics answer without provenance.

### Loss 2: KnowledgeLayer → PulseResponse (all 13 points)
All KnowledgeLayer answers use legacy dict format. ProvenanceTag is not used.
The `type` field (character, theme, symbol, etc.) doesn't map to ProvenanceCategory.

### Loss 3: Voice.py → Utterance (line 217)
Voice propagates provenance from PulseResponse but doesn't transform format.
If PulseResponse uses legacy dict, Utterance carries legacy dict.

### Loss 4: KeeperAgent → API response (line 96)
KeeperAgent propagates provenance from Utterance but doesn't transform format.

### Loss 5: RAG results (layers.py line 432)
RAG search results get `{"type": "rag_search", "source": ...}` — no ProvenanceCategory.
The `source` field is "catalog" or "genome" — not a provenance category.

## Migration Plan

### Phase 1: KnowledgeLayer (13 points)
Change: `{"type": "character", "name": ...}` → `ProvenanceTag(category=AUTHOR_CANON, ...)`
All KnowledgeLayer data comes from GENOME = AUTHOR_CANON by definition.

### Phase 2: MeaningLayer (4 points)
Change: `{"type": "author_intent", "field": ...}` → `ProvenanceTag(category=AUTHOR_CANON, ...)`
Author intent = direct from book = AUTHOR_CANON.

### Phase 3: IdentityLayer + MissionLayer (4 points)
Change: `{"type": "identity/mission", ...}` → `ProvenanceTag(category=AUTHOR_CANON, ...)`

### Phase 4: Other layers (VisualStyle, NarrativeArc, Scene, Screenplay, WorldEngine)
Change: `{"type": "...", ...}` → `ProvenanceTag(category=DERIVED, ...)`

### Phase 5: ExpansionLayer standard (2 empty points)
Change: `provenance=[]` → `ProvenanceTag(category=DERIVED, ...)`

### Phase 6: RAG results
Change: `{"type": "rag_search", "source": ...}` → `ProvenanceTag(category=DERIVED, ...)`

### Phase 7: PulseResponse contract
Change: `provenance: list[dict]` → `provenance: list[ProvenanceTag]`
Add backward-compatible to_dict() serialization.

### Phase 8: KeeperAgent serialization
Ensure ProvenanceTag is serialized to dict for JSON API response.
