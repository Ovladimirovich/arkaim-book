# TEMPORAL LEGACY REFINEMENT — IMPLEMENTATION REPORT

**Milestone:** TEMPORAL_LEGACY_REFINEMENT
**Дата:** 2026-09-15
**Статус:** IMPLEMENTED + TESTED
**Источник:** `docs/TEMPORAL_LEGACY_FORENSIC_AUDIT.md`, `docs/TEMPORAL_LEGACY_REFINEMENT_DESIGN_CHECK.md`

---

## Простыми словами

1. **Что было целью?** — Расширить temporal/event механизм, чтобы он мог выражать линию «Носитель → Учение → передача → наследие → зеркальные эпохи».

2. **Что реально сделано?** — Добавлены 3 новых типа связей (CARRIES, TRANSMITS_TO, ECHOES), заменены 17 заглушек событий на 8 реальных, добавлены связи между персонажами (mentor/student), добавлены зеркальные эпохи.

3. **Что получилось?** — 415 тестов пройдены, 0 новых failures. Все существующие invariant-ы сохранены.

4. **Есть ли проблемы?** — 18 pre-existing permission errors в store tests (temp dir access) — не связаны с изменениями.

5. **Что дальше?** — Milestone complete. Жду решения владельца.

---

## A. WHAT WAS CHANGED

### Files Modified (7 total)

| # | File | Change Type | Lines Changed |
|---|------|-------------|--------------|
| 1 | `core/CORE/narrative_engine/temporal/relation.py` | Enum extension + factories | +60 |
| 2 | `core/CORE/narrative_engine/world_model.py` | New models + methods | +45 |
| 3 | `core/CORE/narrative_engine/data/WORLD_MODEL.json` | Events + parallels + character relations | +150, -136 |
| 4 | `runtime/tests/test_temporal_model.py` | New tests for 3 relation types | +130 |
| 5 | `runtime/tests/test_narrative_world_model.py` | New tests for parallels + character rels | +135 |
| 6 | (no new files created) | — | — |

### No New Files Created

---

## B. THREE NEW RELATION TYPES

### Added to `TemporalRelationType`:

| Type | Value | Domain | Semantics | Provenance Default |
|------|-------|--------|-----------|-------------------|
| `CARRIES` | `"CARRIES"` | character → knowledge | Носитель несёт/хранит знание | AUTHOR_CANON |
| `CARRIED_BY` | `"CARRIED_BY"` | knowledge → character | Обратный к CARRIES | (auto) |
| `TRANSMITS_TO` | `"TRANSMITS_TO"` | character → character | Учитель передаёт ученику | AUTHOR_CANON |
| `RECEIVES_FROM` | `"RECEIVES_FROM"` | character → character | Обратный к TRANSMITS_TO | (auto) |
| `ECHOES` | `"ECHOES"` | epoch ↔ epoch | Зеркальность/аналогия, НЕ причинность | HYPOTHESIS |

### NOT Added:
- `INHERITS_FROM` — исключён, `DEVELOPS_FROM` + description достаточен

### New Properties on `TemporalRelation`:
- `is_contextual` — True для CARRIES/CARRIED_BY/TRANSMITS_TO/RECEIVES_FROM/ECHOES/DEVELOPS_FROM/TRANSFORMS_INTO/CONTEMPORARY_WITH/COEXISTS_WITH. False для PRECEDES/FOLLOWS/BEFORE/AFTER/OVERLAPS/CONTAINS/CONTAINED_BY/UNKNOWN.

### REVERSE_RELATIONS Updated:
- CARRIES ↔ CARRIED_BY
- TRANSMITS_TO ↔ RECEIVES_FROM
- ECHOES ↔ ECHOES (self-reverse)

---

## C. REAL EVENTS (8 replacing 17 stubs)

| Event ID | Title | Epoch | Characters | Chapter | Provenance |
|----------|-------|-------|-----------|---------|-----------|
| `event_cosmic_impulse` | Космический импульс и пробуждение носителя | pre_arkaim | Архат | 1 | AUTHOR_CANON |
| `event_teacher_gathering` | Сбор учеников по зову Учителя | satya_yuga | Велик, Учитель, Наставники, Световит | 2 | AUTHOR_CANON |
| `event_oceania_decline` | Упадок цивилизации Океании | satya_yuga | Велик | 3 | AUTHOR_CANON |
| `event_journey_to_hyperborea` | Путешествие Велика в Гиперборею | satya_yuga | Велик | 3 | AUTHOR_CANON |
| `event_transmission_of_teaching` | Передача Учения от Учителя к ученикам | satya_yuga | Учитель, Велик, Наставники | 5 | AUTHOR_CANON |
| `event_arkaim_construction` | Строительство и расцвет Аркаима | arkaim_era | Радомир, Наставники | 11 | AUTHOR_CANON |
| `event_kali_yuga_onset` | Наступление Кали Юги | эпоха_кали_юги | — | 13 | AUTHOR_CANON |
| `event_awakening` | Пробуждение | переход_к_новой_эре_(кали_юга) | — | 16 | AUTHOR_CANON |

---

## D. CHARACTER CROSS-REFERENCES

### `CharacterPresence.relations` field added:

```python
relations: list[dict] = Field(default_factory=list)
# [{"type": "mentor_of", "target": "name", "provenance": "AUTHOR_CANON"}]
```

### Populated in WORLD_MODEL.json:

| Character | Relation | Target | Source |
|-----------|----------|--------|--------|
| Учитель | mentor_of | Велик | Части 2-5 книги |
| Световит | mentor_of | Велик | Части 5-13 книги |
| Велик | mentor_of | Мирослав | Части 5-6 книги |
| Учитель | mentor_of | Наставники | Части 2-5 книги |
| Радомир | peer_of | Велик | Части 10-11 книги |

### CharacterRelation model added:

```python
class CharacterRelation(BaseModel):
    character: str
    relation: str   # mentor_of, student_of, peer_of, predecessor_of
    target: str
    provenance: list[ProvenanceTag]
```

### Query methods added:
- `get_character_relations(character_name?)` — all or filtered
- `get_character_mentors(character_name)` — who mentors this character
- `get_character_students(character_name)` — who this character mentors

---

## E. EPOCH PARALLELS

### `EpochParallel` model added:

```python
class EpochParallel(BaseModel):
    source: str       # epoch ID
    target: str       # epoch ID
    description: str
    provenance: list[ProvenanceTag]
```

### Data in WORLD_MODEL.json:

| Source | Target | Description | Provenance |
|--------|--------|-------------|-----------|
| satya_yuga | переход_к_новой_эре_(кали_юга) | Расцвет знания ↔ пробуждение интереса к утраченному знанию | HYPOTHESIS |
| эпоха_кали_юги | kali_yuga | Книжная Кали Юга ↔ ведическая Кали Юга | AUTHOR_CANON |

### Query method:
- `get_epoch_parallels()` — returns list[EpochParallel]

---

## F. TRACES (Before → After)

### Trace A: Носитель → ученик → наследие

**Before:** CharacterPresence exists but flat, no relations. CARRIES type doesn't exist. Chain breaks at character level.

**After:**
```
Учитель —[mentor_of]→ Велик          (CharacterPresence.relations)
Велик  —[mentor_of]→ Мирослав         (CharacterPresence.relations)
Учитель —[TRANSMITS_TO]→ Велик        (available as TemporalRelation factory)
Велик —[CARRIES]→ "Единое Учение"     (available as TemporalRelation factory, description)
```

**Provenance:** AUTHOR_CANON for all — directly described in book parts 2-6.

**Gap remaining:** Knowledge is referenced via `description` field on CARRIES relation, not as a standalone entity. Sufficient for current needs (per design check decision).

### Trace B: Гиперборейская линия → последующее развитие

**Before:** Only PRECEDES between epochs. No quality transitions.

**After:**
```
satya_yuga —[PRECEDES]→ переходная_эпоха —[PRECEDES]→ ... → arkaim_era
```

**Provenance:** AUTHOR_CANON on PRECEDES.

**Quality transitions (DEVELOPS_FROM)** still require manual creation via M10.2 workflow — by design (ADR Decision B).

**Gap remaining:** DEVELOPS_FROM between satya_yuga and arkaim_era not yet created — must go through M10.2 human confirmation.

### Trace C: Атлантида → состояние эпохи → ECHOES → современность

**Before:** ECHOES type doesn't exist. No way to express structural parallel.

**After:**
```
temporal_атлантическая_линия —[ECHOES]→ temporal_today
    description: "технологии без духовности"
    provenance: HYPOTHESIS
```

**Provenance:** HYPOTHESIS — structural parallel, not historical causation.

**ECHOES does NOT participate in chain building** — contextual relation only.

**Gap remaining:** ECHOES relation data exists in `epoch_parallels` (satya_yuga ↔ пробуждение). The specific Океания→TODAY parallel is expressible via the factory but not yet committed to data — can be added through M10.2 workflow.

### Trace D: Arkaim → исторические проявления → TODAY

**Before:** Computed path works (BACKWARD from today finds arkaim_era through reverse PRECEDES). Archaeology data in ArkaimAnchor provenance.

**After:** No change needed — this trace already works through existing mechanism:
```
temporal_today ←[BFS reverse]← ... ← temporal_arkaim_era
    arkaim_era provenance: [AUTHOR_CANON, EXTERNAL_SOURCE]
    confidence: 0.85
```

**Gap remaining:** Синташта/Гардарика as separate temporal nodes not yet created — future enhancement.

### Trace E: Внешний культурный носитель (HYPOTHESIS)

**Before:** No CARRIES type. Can't express "knowledge manifests in cultural form".

**After:**
```
Великий Учитель Истины —[CARRIES]→ "Единое Учение"
    provenance: AUTHOR_CANON

"Ведическая традиция" —[ECHOES]→ "Единое Учение"
    provenance: HYPOTHESIS  ← НЕ исторический факт
```

**Provenance:** HYPOTHESIS on ECHOES — explicitly not a historical claim.

**Gap remaining:** Requires manual creation of ECHOES relation through M10.2.

---

## G. TEMPORAL_TODAY

**No changes to temporal_today.** Status:
- Exists as TemporalNode with HYPOTHESIS provenance
- is_anchor=False, era_id=""
- NO relations to any epoch (ADR Decision A)
- "Факт существования современности" = HYPOTHESIS provenance (methodological observation point)
- "Гипотеза о будущем" = FUTURE_EXTRAPOLATION (separate mechanism, unchanged)

These remain correctly separated.

---

## H. FUTURE EXTRAPOLATION

**No changes.** Status:
- FutureExtrapolator uses FUTURE_EXTRAPOLATION provenance
- Deterministic (no LLM), BFS from anchor
- Templates from hardcoded scenarios
- CompatibilityChecker filters
- Cannot accidentally become historical fact (provenance invariant preserved)

---

## I. TEST RESULTS

### New Tests Added: 34

| File | Tests | Classes |
|------|-------|---------|
| `test_temporal_model.py` | 23 | TestCARRIESRelationType (8), TestTRANSMITS_TO_TeRelationType (6), TestECHOESRelationType (7), TestNewReverseCompleteness (2) |
| `test_narrative_world_model.py` | 11 | TestCharacterRelations (6), TestEpochParallels (5) |

### Updated Tests: 2

| File | Test | Change |
|------|------|--------|
| `test_temporal_model.py::test_all_relation_types_exist` | Added 5 new types to expected set |
| `test_narrative_world_model.py::test_load_empty` | Updated summary format check |

### Full Temporal Suite Results:

```
415 passed, 0 failed, 1 warning in 3.04s
```

Files tested:
- test_temporal_model.py (86 tests)
- test_temporal_reconstruction.py (55 tests)
- test_narrative_world_model.py (26 tests)
- test_provenance.py (55 tests)
- test_temporal_routes.py (17 tests)
- test_temporal_integration.py (31 tests)
- test_m5_temporal_integration.py (19 tests)
- test_m8_future_extrapolation.py (13 tests)
- test_m8_1_present_anchor.py (32 tests)
- test_m9_expansion_temporal.py (38 tests)
- test_m10_temporal_updates.py (24 tests)
- test_temporal_api_alignment.py (14+ tests)

### Broader Suite Results:

```
238 passed, 18 errors (pre-existing permission errors in store tests)
```

The 18 errors are all `PermissionError: [WinError 5]` in temp directory access — pre-existing, unrelated to this milestone.

---

## J. SCOPE CREEP CHECK

| Check | Status |
|-------|--------|
| KnowledgeArtifact Model created? | ❌ NO (excluded by design check) |
| INHERITS_FROM added? | ❌ NO (excluded — DEVELOPS_FROM sufficient) |
| New temporal subsystem? | ❌ NO |
| New carrier subsystem? | ❌ NO |
| New provenance categories? | ❌ NO |
| ADR Decisions A/B/C/D violated? | ❌ NO |
| Studio/Media/ComfyUI touched? | ❌ NO |
| Frontend changed? | ❌ NO |
| Public API changed? | ❌ NO (additive only) |
| Entities renamed? | ❌ NO |
| Speculative historical links? | ❌ NO |
| Future Extrapolation mixed with canon? | ❌ NO |

---

## K. REMAINING GAPS

1. **DEVELOPS_FROM relations** between epochs — must go through M10.2 workflow (human confirmation)
2. **More ECHOES parallels** — Океания↔TODAY etc. — can be added through M10.2
3. **More character relations** — only key pairs populated; full graph requires manual review
4. **Knowledge as standalone entity** — deferred per design check (CARRIES + description sufficient)
5. **Синташта/Гардарика as temporal nodes** — future enhancement
6. **Auto-detection of mirrors** — manual via epoch_parallels (by design)

---

## L. FILES CHANGED (Summary)

| File | Lines Before | Lines After | Delta |
|------|-------------|------------|-------|
| `core/CORE/narrative_engine/temporal/relation.py` | 217 | 277 | +60 |
| `core/CORE/narrative_engine/world_model.py` | 458 | 503 | +45 |
| `core/CORE/narrative_engine/data/WORLD_MODEL.json` | 861 | 875 | +14 |
| `runtime/tests/test_temporal_model.py` | 596 | 726 | +130 |
| `runtime/tests/test_narrative_world_model.py` | 177 | 312 | +135 |

**Total: ~384 lines added, ~136 lines removed (event stubs replaced). Net: +248 lines.**
**New files: 0.**

---

**STOP — TEMPORAL_LEGACY_REFINEMENT IMPLEMENTATION COMPLETE. Жду проверки.**
