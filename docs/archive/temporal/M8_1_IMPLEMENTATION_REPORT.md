# M8.1 — IMPLEMENTATION REPORT

## Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `core/CORE/narrative_engine/temporal/node.py` | present_anchor() provenance: AUTHOR_CANON → HYPOTHESIS |
| `core/CORE/narrative_engine/temporal/reconstruction_engine.py` | from_world_model(): add temporal_today, enrich arkaim_era provenance, remove orphan |
| `core/CORE/narrative_engine/temporal/future_extrapolator.py` | Tag forward chain + scenarios with FUTURE_EXTRAPOLATION provenance |
| `core/CORE/narrative_engine/world_engine.py` | get_full_temporal_pipeline() — orchestration layer |
| `runtime/tests/test_m8_1_present_anchor.py` | NEW — 32 M8.1 tests |
| `runtime/tests/test_temporal_model.py` | Fix test_present_anchor for new provenance |
| `runtime/tests/test_temporal_integration.py` | Fix test_arkaim_anchor_in_engine for orphan removal |

---

## Target Diff: Architectural Changes

### 1. `node.py` — present_anchor() provenance fix
```diff
  provenance=[ProvenanceTag(
      source_level=SourceLevel.CANON,          # → SYSTEM_INTERPRETATION
-     category=ProvenanceCategory.AUTHOR_CANON, # → HYPOTHESIS
+     category=ProvenanceCategory.HYPOTHESIS,
      confidence=1.0,
-     notes="present reference point",
+     notes="methodological anchor for temporal reconstruction — not book canon",
  )],
```

### 2. `reconstruction_engine.py` — from_world_model() M8.1 additions
```diff
  engine = cls()

+ # M8.1: Collect ArkaimAnchor provenance for enrichment
+ arkaim_anchor = ArkaimAnchor.from_existing_data()
+ arkaim_provenance = arkaim_anchor.provenance

  for epoch in world_model.get_epochs():
      node_data = world_model.get_temporal_node(epoch.id)
      if node_data:
          node = TemporalNode.from_dict(node_data)
+         # M8.1: enrich arkaim_era provenance
+         if epoch.id == "arkaim_era" and arkaim_provenance:
+             existing_cats = {p.category for p in node.provenance}
+             for tag in arkaim_provenance:
+                 if tag.category not in existing_cats:
+                     node.provenance.append(tag)
+             node.confidence = 0.85
          engine.add_node(node)

  # ... existing epoch relations ...

+ # M8.1: Add temporal_today as methodological anchor (NO relations)
+ today_node = TemporalNode.present_anchor()
+ engine.add_node(today_node)

+ # M8.1: Remove orphan temporal_arkaim_anchor
+ if engine._graph.get_node("temporal_arkaim_anchor"):
+     engine.remove_node("temporal_arkaim_anchor")
```

### 3. `future_extrapolator.py` — FUTURE_EXTRAPOLATION provenance tagging
```diff
  # 5. Build result
+ # M8.1: Tag scenarios with FUTURE_EXTRAPOLATION provenance
+ future_provenance = [ProvenanceTag(
+     source_level=SourceLevel.USER_HYPOTHESIS,
+     category=ProvenanceCategory.FUTURE_EXTRAPOLATION,
+     confidence=0.5,
+     notes="future projection from arkaim canon — not historical fact",
+ )]

  return {
      ...
      "scenarios": scenarios_filtered,
+     "provenance": future_provenance,
+     "provenance_note": "FUTURE_EXTRAPOLATION — projection from canon, not historical fact",
  }
```

### 4. `world_engine.py` — get_full_temporal_pipeline()
```python
def get_full_temporal_pipeline(self, prompt="", max_futures=5) -> Optional[dict]:
    """PRESENT → computed reconstruction → ARKAIM → M8 extrapolation → FUTURE"""
    # 1. BACKWARD reconstruction from arkaim_era
    # 2. Verify temporal_today exists
    # 3. FORWARD extrapolation via FutureExtrapolator
    # 4. Return composed result with provenance_invariants
```

---

## Результаты тестов

### M8.1 (32 теста) — все PASS ✅
```
TestPresentAnchorProvenance        4/4  PASS
TestPresentToArkaimComputedPath    5/5  PASS
TestNoPresentToArkaimRelation      2/2  PASS
TestCanonicalArkaimAnchor          4/4  PASS
TestArkaimEnrichedProvenance       5/5  PASS
TestM8FutureExtrapolationProvenance 4/4 PASS
TestM81Regression                  6/6  PASS
TestPreExistingFailure             1/1  PASS
```

### Полный temporal suite (186 тестов) — все PASS ✅
```
test_m8_1_present_anchor.py        32/32  PASS
test_m5_temporal_integration.py    19/19  PASS
test_m8_future_extrapolation.py    13/13  PASS
test_m7_epoch_visual.py            11/11  PASS
test_temporal_model.py             44/44  PASS
test_temporal_integration.py       22/22  PASS
test_temporal_routes.py            17/17  PASS
test_narrative_constraints.py      11/11  PASS
test_narrative_pipeline.py         17/17  PASS
```

### Предыдущие failures — исправлены
| Тест | Было | Стало | Причина |
|------|------|-------|---------|
| `test_present_anchor` | FAIL (was AUTHOR_CANON) | PASS (now HYPOTHESIS) | M8.1 fix |
| `test_arkaim_anchor_in_engine` | FAIL (orphan existed) | PASS (orphan removed) | M8.1 fix |

### Pre-existing failures (НЕ связаны с M8.1)
- `test_get_entity` (region_arkaim) — требует авторизации
- `test_telegram_handle_message` — интеграционный
- `test_draft_not_found` — интеграционный
- `test_load_book` — внешние зависимости
- `test_migrations` — Windows permission error

---

## Проверка архитектуры

### ✅ PRESENT
- `temporal_today` существует в графе
- Provenance = HYPOTHESIS (не AUTHOR_CANON)
- Нет relations (methodological anchor, not historical fact)

### ✅ PRESENT → ARKAIM
- Нет graph relation между today и arkaim
- Computed path через `_trace_backward("temporal_arkaim_era")`
- Все 11 relations в графе — только PRECEDES между эпохами

### ✅ Два Arkaim
- `temporal_arkaim_era` — canonical (в chain, с relations)
- `temporal_arkaim_anchor` — удалён из графа (орфан)
- `temporal_arkaim_era` enriched: AUTHOR_CANON + EXTERNAL_SOURCE, confidence=0.85

### ✅ FUTURE provenance
- M8 результат содержит `provenance: [FUTURE_EXTRAPOLATION]`
- forward chain nodes после arkaim_era tagged FUTURE_EXTRAPOLATION
- Сценарии сохраняют compatibility_score

### ✅ WorldEngine orchestration
- `get_full_temporal_pipeline()` комбинует BACKWARD + M8
- Возвращает provenance_invariants
- НЕ создаёт новых graph relations

### ✅ M8 остаётся standalone
- `anchor_id="arkaim_era"` работает как прежде
- Алгоритм `_build_forward_chain()` не изменён
- Только provenance tagging добавлен

---

## Финальный статус

### M8.1 — IMPLEMENTED ✅

**Обоснование:**
1. Все 6 архитектурных вопросов решены в соответствии с M8.1 ARCHITECTURE DECISION
2. 32 новых теста + 2 исправленных = 186 temporal тестов проходят
3. Превышение M8 standalone — provenance tagging только
4. Предустановленные relation count = 11 (не изменился)
5. Никаких новых relation types, TemporalEngine, сервисов
6. Инварианты provenance сохранены: RECONSTRUCTION ≠ HISTORICAL_FACT, FUTURE_EXTRAPOLATION ≠ HISTORICAL_FACT
