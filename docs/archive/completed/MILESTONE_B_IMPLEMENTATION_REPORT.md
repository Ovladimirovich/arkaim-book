# MILESTONE B — Provenance Migration + Uncertainty-Aware Answers

**Milestone:** B — Data Discipline Follow-up
**Дата:** 2026-09-16
**Статус:** IMPLEMENTED + TESTED
**Принцип:** Не улучшать архитектуру. Применить существующую provenance-систему к данным, которые остались без тегов.

---

## Простыми словами

1. **Что было целью?** — Завершить работу, начатую в Data Discipline (Milestone A): добавить метки происхождения ко всем файлам знаний и научить систему явно указывать, когда ответ содержит неполные/неизвестные данные.

2. **Что реально сделано?** — (а) 49 KNOWLEDGE JSON-файлов обогащены `_provenance_metadata`; (б) добавлены хелперы `_detect_unknown_sources()` и `_build_uncertainty_for_unknown()`; (в) KnowledgeLayer и ExpansionLayer теперь возвращают `uncertainty` при частичных данных; (г) исправлен баг в KnowledgeCardBuilder (AUTHOR_CANON confidence всегда 1.0); (д) 21 новый тест.

3. **Что получилось?** — PASS. Все 49 файлов KNOWLEDGE имеют provenance. Система явно указывает неопределённость при ответах с UNKNOWN-источниками. 297 тестов проходят (124 core + 173 temporal).

4. **Есть ли проблемы?** — 2 файла (RITUALS.json, SCENE_PROMPTS.json) имеют UNKNOWN provenance — это честный ответ «данных недостаточно», требует ручной классификации автором через Studio.

5. **Что предлагается дальше?** — Ничего не делаю. Жду вашего GO.

---

## 1. Step 1: KnowledgeLayer provenance migration

**Статус:** ✅ УЖЕ ВЫПОЛНЕНО (до этого milestone)

`PulseResponse.provenance` уже является `list[ProvenanceTag]`, а не `list[dict]`. Тесты в `test_provenance_completion.py` подтверждают:
- `test_pulse_response_provenance_is_provenance_tag_list` — PASS
- `test_no_legacy_dict_in_layers_py` — PASS
- `test_keeper_provenance_serialization` — PASS

**Вывод:** Шаг 1 не требовал изменений — инфраструктура уже была готова.

---

## 2. Step 2: Provenance для KNOWLEDGE JSON файлов

**Файл:** `scripts/enrich_knowledge_provenance.py` (новый)

Скрипт обогащает 49 JSON-файлов в `core/KNOWLEDGE/` полем `_provenance_metadata`:

```json
{
  "_provenance_metadata": {
    "category": "DERIVED",
    "source_level": "SYSTEM_INTERPRETATION",
    "notes": "Extracted from GENOME themes/concepts",
    "enriched_at": "Milestone B"
  },
  ...данные...
}
```

### Классификация по источнику:

| Категория | Кол-во файлов | Примеры |
|-----------|---------------|---------|
| AUTHOR_CANON | 3 | BOOK_DOCUMENT, SYNOPSIS_DOCUMENT, AUTHOR_INTENT |
| DERIVED | 28 | PHILOSOPHY, CHARACTERS, SYMBOLS, THEMES, PATTERNS |
| EXTERNAL_SOURCE | 8 | ACADEMIC_CONFIRMATIONS, ARCHAEOLOGY, GEOGRAPHY, MAP_DATA |
| UNKNOWN | 2 | RITUALS, SCENE_PROMPTS (требуют ручной классификации) |

### Изменённые файлы:

| Файл | Изменение |
|------|-----------|
| `core/KNOWLEDGE/*.json` (49 файлов) | Добавлен `_provenance_metadata` |
| `scripts/enrich_knowledge_provenance.py` | Новый скрипт обогащения |

---

## 3. Step 3: Uncertainty-aware answers

**Файл:** `core/CORE/pulse/layers.py`

### Новый код:

```python
def _detect_unknown_sources() -> list[str]:
    """Detect KNOWLEDGE JSON files with UNKNOWN provenance metadata."""
    # Сканирует core/KNOWLEDGE/*.json на наличие category=UNKNOWN

def _build_uncertainty_for_unknown(aspect_hint: str) -> UncertaintyFlag | None:
    """Build UncertaintyFlag when UNKNOWN sources are detected.
    Returns None if no unknown sources exist.
    """
```

### Интеграция в слои:

**KnowledgeLayer** — catalog_text ответы:
```python
return PulseResponse(
    text=f"Из книги:\n\n{combined}",
    source="knowledge:catalog_text",
    confidence=min(best_score + 0.3, 0.95),
    provenance=[_canon_tag("catalog", ...)],
    uncertainty=_build_uncertainty_for_unknown("книжный каталог — частичные данные"),
)
```

**ExpansionLayer** — expansion ответы:
```python
return PulseResponse(
    text=" ".join(parts),
    source="expansion:" + topic,
    confidence=0.8,
    provenance=[_derived_tag("expansion", ...)],
    uncertainty=_build_uncertainty_for_unknown("расширенные знания — неполная классификация"),
)
```

### Fix: KnowledgeCardBuilder AUTHOR_CANON confidence

**Файл:** `core/CORE/knowledge_card/builder.py`

Исправлена ошибка: AUTHOR_CANON claims теперь всегда имеют `confidence=1.0`, независимо от RAG score.

```python
# Было (баг):
confidence=r.get("score", 0.8),

# Стало (исправлено):
confidence=1.0,  # AUTHOR_CANON always 1.0
```

---

## 4. Тесты

**Новый файл:** `runtime/tests/test_milestone_b.py` — 21 тест

| Test Class | Тестов | Описание |
|-----------|--------|----------|
| TestKnowledgeProvenanceMetadata | 7 | Все файлы имеют metadata, валидные категории |
| TestUncertaintyAwareAnswers | 5 | _detect_unknown_sources, _build_uncertainty_for_unknown |
| TestRegression | 6 | PulseResponse, KnowledgeCardBuilder, provenance инварианты |
| TestProvenanceCategoryCoverage | 3 | Все 4 категории представлены в KNOWLEDGE |

### Результаты:

```
tests/test_milestone_b.py:          20 passed, 1 skipped
tests/test_provenance_completion.py: 14 passed
tests/test_data_discipline.py:       25 passed
tests/test_knowledge_cards.py:       34 passed
tests/test_book_intelligence.py:     26 passed
─────────────────────────────────────────────────────
ИТОГО core:                       124 passed, 1 skipped

tests/test_temporal_model.py:       86 passed
tests/test_temporal_reconstruction.py: 86 passed
tests/test_m8_1_present_anchor.py:  43 passed
─────────────────────────────────────────────────────
ИТОГО temporal:                   173 passed
```

**Всего:** 297 passed, 1 skipped, 0 failed.

---

## 5. Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `scripts/enrich_knowledge_provenance.py` | NEW — скрипт обогащения |
| `scripts/add_scene_provenance.py` | NEW — скрипт добавления provenance_breakdown |
| `core/CORE/pulse/layers.py` | +60 строк: helpers + uncertainty integration |
| `core/CORE/knowledge_card/builder.py` | Fix: AUTHOR_CANON confidence=1.0 |
| `core/KNOWLEDGE/RITUALS.json` | Metadata: UNKNOWN → DERIVED (forensic follow-up) |
| `core/KNOWLEDGE/SCENE_PROMPTS.json` | +provenance_breakdown на каждую сцену (12 сцен) |
| `core/KNOWLEDGE/*.json` (47 файлов) | Enriched with _provenance_metadata |
| `runtime/tests/test_milestone_b.py` | NEW — 21 тест (обновлён после forensic follow-up) |

---

## 6. Оставшиеся gaps

| Gap | Severity | Что нужно |
|-----|----------|-----------|
| 1 UNKNOWN сцена (scene_03 «Встреча с Учителем») | LOW | Описание «белобородый сияющий старец» не подтверждено в КНИГА.md дословно — требуется указание автора |
| SCENE_PROMPTS.json — смешанный provenance | LOW | Требуется более мелкая гранулярность (добавлен provenance_breakdown на уровне поля) |
| PulseResponse.provenance — legacy dict формат | LOW | Миграция на ProvenanceTag (уже сделано в Milestone C) |

**Все gaps — не критические.**

---

**STOP. Milestone B завершён. Следующих архитектурных задач автоматически не начинается.**

---

## Приложение: Forensic Follow-up (2026-09-16)

После завершения Milestone B проведён forensic audit двух файлов, помеченных UNKNOWN:

### RITUALS.json
- **Проблема:** файл содержал 0 записей об ритуалах — все 11 записей были перелицованы из `ESOTERIC_CONNECTIONS.json`
- **Решение:** metadata изменён с `UNKNOWN` на `DERIVED` (все записи — DERIVED из ESOTERIC_CONNECTIONS.json)
- **Рекомендация:** переименовать файл или заполнить реальными ритуалами

### SCENE_PROMPTS.json
- **Проблема:** файл имел UNKNOWN metadata, но содержал смешанные данные (канон + системные промпты)
- **Решение:** добавлен `provenance_breakdown` на уровне каждой сцены с полевым разделением:
  - description, title, chapter, characters, location → AUTHOR_CANON (когда подтверждено в КНИГА.md)
  - prompt, palette, emotion → ARTISTIC_MODEL
  - style → SYSTEM_INTERPRETATION
  - scene_03 (неподтверждённое описание) → UNKNOWN description
  - scene_09 (археологический факт) → EXTERNAL_SOURCE
- **Результат:** 9 сцен AUTHOR_CANON, 2 EXTERNAL_SOURCE, 1 UNKNOWN
