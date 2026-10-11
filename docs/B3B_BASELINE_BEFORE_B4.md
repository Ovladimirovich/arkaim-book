<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL — НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Документ фиксирует предыдущий срез/аудит. Его статусы, маршруты и ссылки на бывший v2 отменены текущим состоянием. Используйте docs/CURRENT_DEVELOPMENT_STATE.md и docs/DOCUMENTATION_INDEX.md.

﻿# B3b Baseline Before B4

Status: DOCUMENTED / BASELINE FROZEN
Date: 2026-09-29
Git HEAD: 8aef0f9

## Purpose

This document freezes the observable project state after B3b and before B4. It is a control point, not a git commit or tag.

## Plain-language report

- Goal: preserve the B3b result before starting B4.
- Done: B3-CW approved; B3b implemented and tested.
- Result: PASS.
- Problem: the working tree contains many pre-existing changes and untracked artifacts. They are not assumed to be part of B3b.
- Next step: prepare a separate B4 plan and obtain a new OWNER-GO. B4 is not running now.

## Statuses

| Item | Status |
|---|---|
| B3-CW | APPROVED |
| B3b | IMPLEMENTED + TESTED |
| B3b tests | 3 passed |
| B3b lint | PASS |
| B4 | LOCKED / NOT STARTED |

## Approved crosswalk

File: `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`

| World Engine ID | Canonical ID | Status |
|---|---|---|
| `region_arkaim` | `аркаим` | APPROVED |
| `region_hyperborea` | `гиперборея` | APPROVED |

The artifact still contains its original `runtime_connected: false` label. After B3b, the runtime reads this approved artifact only to populate the two confirmed `entity_ids` values. The crosswalk is not expanded.

## B3b runtime result

- `temporal_arkaim_era.entity_ids` = `["region_arkaim"]`
- `temporal_satya_yuga.entity_ids` = `["region_hyperborea"]`
- The other 10 temporal nodes have empty `entity_ids`.

Evidence comes only from canonical events:

- `event_arkaim_construction`: epoch `arkaim_era`, location `аркаим`.
- `event_journey_to_hyperborea`: epoch `satya_yuga`, location `гиперборея`.
- `event_transmission_of_teaching`: epoch `satya_yuga`, location `гиперборея`.

## B3b files

- `core/CORE/narrative_engine/world_model.py`
- `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`
- `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`
- `docs/B3B_PLAN.md`
- `docs/B3_CW_CANDIDATES.md`
- `docs/B3A_ID_RECONCILIATION_REPORT.md`

## Data and UI boundary

The following were not changed by B3b:

- `core/CORE/narrative_engine/data/WORLD_MODEL.json`
- `core/CORE/WORLD_MODEL/*.json`
- `core/KNOWLEDGE/MAP_DATA.json`
- `arkaim-web/`
- `arkaim-web-v2/`

B4 was not started.

## Verification

- `python -m pytest core/CORE/narrative_engine/tests/test_b3b_crosswalk.py -q` -> `3 passed in 0.71s`.
- `python -m ruff check core/CORE/narrative_engine/world_model.py core/CORE/narrative_engine/tests/test_b3b_crosswalk.py` -> `All checks passed`.
- Live WorldModel check confirmed the two links above and no others.

## Working tree warning

At baseline time, `git status` contains many modified and untracked files from earlier work, including frontend, runtime, documentation, logs, generated files, and other artifacts. The baseline records this fact and does not clean or commit the working tree.

## B4 boundary

Before B4, do not:

- expand the approved crosswalk;
- change `WORLD_MODEL.json` without a separate decision;
- change UI without a concrete need;
- treat unrelated working-tree changes as B4 work;
- start B4 without a separate plan and OWNER-GO.

Required order:

`BASELINE → B4 PLAN → OWNER-GO → B4 → VERIFICATION → OWNER REVIEW`