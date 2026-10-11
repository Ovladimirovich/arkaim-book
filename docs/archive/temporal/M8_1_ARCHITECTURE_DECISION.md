# M8.1 — ARCHITECTURE DECISION
## PRESENT → ARKAIM → FUTURE: Финальное архитектурное решение

---

## 1. PRESENT / TODAY

### 1.1 Что такое temporal_today семантически

`temporal_today` — это **методологическая точка отсчёта**, а не узел внутри нарратива книги.

Это «сейчас» читателя / системы. Из этой точки запускается BACKWARD reconstruction и FORWARD extrapolation.

**НЕ является:**
- Историческим фактом мира книги
- Часть канона (канон — это текст КНИГИ, present — это现实 читателя)
- Узел, который можно «исследовать» как историческую эпоху

**Является:**
- Reference frame для temporal analysis
- Методологический anchor: «мы начинаем реконструкцию от сегодня»
- Точка входа для navigation по temporal graph

### 1.2 Должен ли PRESENT быть TemporalNode в графе?

**ДА, но с оговоркой.**

Он должен существовать как `TemporalNode` (метод `present_anchor()` уже определён), но:
- Его роль — reference point, не narrative entity
- Он НЕ должен иметь relation к arkaim_era в графе (см. Decision 2)
- Его presence в графе позволяет `get_temporal_chain()` включать его как возможную точку старта

**Проблема текущей реализации:**
```python
# node.py:141-146 — CURRENT provenance ОШИБОЧЕН
provenance=[ProvenanceTag(
    source_level=SourceLevel.CANON,
    category=ProvenanceCategory.AUTHOR_CANON,  # ← НЕВЕРНО
    confidence=1.0,
    notes="present reference point",
)]
```

**AUTHOR_CANON для present day — semantically wrong.**
Present day reader's reality не является авторским канонтом книги. Это внешнийreferенс.

### 1.3 Какой provenance у PRESENT

| Поле | Текущее | Корректное | Обоснование |
|-------|---------|------------|-------------|
| category | AUTHOR_CANON | **HYPOTHESIS** | Present как methodological starting point — это гипотеза реконструкции, не канон |
| source_level | CANON | **SYSTEM_INTERPRETATION** | Система определяет точку отсчёта |
| confidence | 1.0 | 1.0 | Точность времени — точна (текущий год) |
| notes | "present reference point" | "methodological anchor for temporal reconstruction — not book canon" |

**Почему HYPOTHESIS, не EXTERNAL_SOURCE:**
- `EXTERNAL_SOURCE` = данные извне о МИРЕ книги (археология, история)
- Present = точка отсчёта внутри СИСТЕМЫ, не данные о мире
- `HYPOTHESIS` = системная гипотеза, методологическое допущение
- Present is a METHODOLOGICAL hypothesis: "we begin from today"

**Почему не новый PRESENT_REFERENCE category:**
- Нет необходимости расширять enum ради одной точки
- HYPOTHESIS semantically correct и уже существует
- Новый category добавил бы абстракцию без добавленной ценности

### 1.4 Не смешивается ли PRESENT с историческим фактом?

**Сейчас — ДА, смешивается.**
- `present_anchor()` ставит `AUTHOR_CANON`
- Это нарушает инвариант: `AUTHOR_CANON ≠ HISTORICAL_FACT` (present — не часть канона)

**После исправления provenance → НЕТ.**
- HYPOTHESIS clearly marks it as methodological, not historical
- Reader knows: "this is our starting point, not a fact about the world"

---

## 2. PRESENT → ARKAIM

### 2.1 КРИТИЧЕСКИЙ ВОПРОС: WorldRelation или reconstruction path?

**РЕШЕНИЕ: Это RECONSTRUCTION / NAVIGATION PATH, НЕ WorldRelation.**

Обоснование:

| Аспект | WorldRelation | Reconstruction Path |
|--------|---------------|---------------------|
| Что утверждает | Исторический/временной факт | Методологический подход |
| Хранится в графе | Да | Нет (computed on query) |
| Provenance | AUTHOR_CANON / RECONSTRUCTION | RECONSTRUCTION (entire path) |
| Evidence required | Археологические данные связи | Методологическое обоснование |
| Риск | Превращение гипотезы в fact | Низкий (явно marked as reconstruction) |

PRESENT → ARKAIM — это **не историческая причинность**. Это **эпистемологическая связь**: «мы узнаём об Аркаиме из современности через археологию».

Такая связь НЕ выражается никаким существующим `TemporalRelationType`.

### 2.2 Анализ каждого relation candidate

#### PRECEDES / FOLLOWS
- Семантика: строгий временной порядок
- Утверждение: "Present temporally precedes/follows Arkaim"
- Исторический факт: тривиален (все современные эпохи следуют за древними)
- Evidence: не требуется (trivially true)
- Provenance: AUTHOR_CANON (из epoch ordering)
- **Риск:** НЕРЕЛЕВАНТЕН. Не передаёт epistemological meaning.

#### DEVELOPS_FROM
- Семантика: качественное развитие
- Утверждение: "Present civilization developed from Arkaim civilization"
- Исторический факт: СИЛЬНОЕ утверждение о культурной преемственности
- Evidence: требуется доказательство непрерывности культуры
- **Риск: ВЫСОКИЙ.** Превращает гипотезу о преемственности в graph fact. Нарушает RECONSTRUCTION ≠ HISTORICAL_FACT.
- **Рекомендация: НЕ ИСПОЛЬЗОВАТЬ.**

#### CONTAINS
- Семантика: пространственно-временная включённость
- Утверждение: "Present contains Arkaim (as heritage)"
- Исторический факт: метафорический, не буквальный
- **Риск: СРЕДНИЙ.** Может быть интерпретирован как факт культурного наследия.
- **Рекомендация: НЕ ИСПОЛЬЗОВАТЬ.**

#### CONTEMPORARY_WITH
- Семантика: одновременность
- Утверждение: "Present and Arkaim existed simultaneously"
- Исторический факт: ЛОЖНЫЙ
- **Риск: КРИТИЧЕСКИЙ.** Anachronism в графе.
- **Рекомендация: КАТЕГОРИЧЕСКИ НЕ ИСПОЛЬЗОВАТЬ.**

#### UNKNOWN
- Семантика: связь не определена
- Утверждение: честное признание ignorance
- **Риск: НИЗКИЙ.** Но бесполезен для navigation.
- **Рекомендация: НЕ ИСПОЛЬЗОВАТЬ для target architecture.**

### 2.3 Вариант: Navigation-only path (без graph relation)

**Рекомендуемый подход.**

PRESENT → ARKAIM существует как **computed path**, не как stored relation:

```
Методологический pipeline:
1. System starts from temporal_today (reference point)
2. TemporalReconstructionEngine._trace_backward("temporal_arkaim_era")
   → returns chain: [today's perspective, ..., arkaim_era, ...]
3. The "link" is in the ENGINE'S methodology, not in the GRAPH
```

**Как это работает:**
- `temporal_arkaim_era` — anchor node в графе
- `temporal_today` — reference point (не в графе, или в графе без relations)
- `_trace_backward("temporal_arkaim_era")` строит цепочку ВНАЗАД от якоря
- Пользователь / система интерпретирует эту цепочку «от современности к Аркаиму»
- Но граф НЕ содержит relation между today и arkaim

**Преимущества:**
1. Не изобретается relation без evidence
2. RECONSTRUCTION ≠ HISTORICAL_FACT — путь явно marked как reconstruction
3. Существующая архитектура поддерживает: `chain.py:130-144` уже есть `TemporalChain.backward_from_today()`
4. `_trace_backward()` уже реализован в ReconstructionEngine

**Недостатки:**
1. `bfs_path("temporal_today", "temporal_arkaim_era")` вернёт None (нет relation в графе)
2. Navigation через граф невозможен без relation

**Компромисс:** `bfs_path` не нужен. Pipeline использует `_trace_backward(anchor_id)` напрямую.

### 2.4 Чего не хватает для real WorldRelation

Если в будущем потребуется real relation Present→Arkaim:

| Evidence | Статус |
|----------|--------|
| Дата археологического открытия Аркаима | ❌ НЕТ в KNOWLEDGE |
| Конкретный archaeological source | ❌ НЕТ |
| Связь «современность ↔ Аркаим» в ARCHAEOLOGY.json | ❌ НЕТ |
| PresentAnchor.temporal_nodes заполнен | ❌ НЕТ (пусто) |

**Вывод:** Evidence отсутствует. Relation создавать нельзя — это нарушит принцип «не выдумывать исторические связи».

---

## 3. ДВА ARKAIM ANCHOR

### 3.1 Анализ

| | `temporal_arkaim_anchor` | `temporal_arkaim_era` |
|---|---|---|
| Источник | `ArkaimAnchor.from_existing_data()` | `WorldModel.get_temporal_node("arkaim_era")` |
| Provenance | [AUTHOR_CANON, EXTERNAL_SOURCE] | [] (пусто) |
| Relations | 0 (orphan) | 2 (in+out PRECEDES) |
| is_anchor | True | True |
| Используется M8 | Нет | Да |
| Цель | Metadata anchor (rich provenance) | Data anchor (in chain) |

### 3.2 Canonical anchor

**`temporal_arkaim_era` — canonical temporal node.**

Обоснование:
- Он В графе, с relations, участвует в chain
- M8 уже использует его
- `temporal_arkaim_anchor` — орфан без relations

### 3.3 Проблема provenance

**`temporal_arkaim_era` имеет EMPTY provenance.**

Причина: `world_model.py:340`:
```python
"provenance": [canonical_provenance().to_dict()] if epoch.provenance else [],
```

`epoch.provenance = []` → condition is False → provenance = `[]`.

Но `canonical_provenance()` возвращает `AUTHOR_CANON, confidence=1.0` — этот fallback НЕ применяется когда provenance пуст.

**`temporal_arkaim_anchor` (из ArkaimAnchor) имеет CORRECT provenance:**
```python
[
    AUTHOR_CANON (from КНИГА.md),
    EXTERNAL_SOURCE (from ARCHAEOLOGY.json),
]
```

### 3.4 Решение (архитектурное, без кода)

**Canonical node = `temporal_arkaim_era`.**

Его provenance должен быть ENRICHED из ArkaimAnchor:
- SOURCE: AUTHOR_CANON (book canon)
- SOURCE: EXTERNAL_SOURCE (archaeology)
- COMBINED confidence: ~0.85 (between 1.0 and 0.7)

**`temporal_arkaim_anchor` (орфан) должен быть REMOVED из графа.**

Он создаётся в `reconstruction_engine.py:589-590`:
```python
anchor = ArkaimAnchor.from_existing_data()
engine.add_node(anchor.node)  # ← добавляет орфана
```

Архитектурно верно: ArkaimAnchor.provenance должен применяться к `temporal_arkaim_era`, а не создавать дублирующий узел.

**Без изменения кода:** текущее состояние — dual anchor с orphan. Это architectural debt, не критический баг.

---

## 4. FUTURE — Provenance Model

### 4.1 Где применяется FUTURE_EXTRAPOLATION

**Существующий category:**
```python
# source_levels.py:61
FUTURE_EXTRAPOLATION = "FUTURE_EXTRAPOLATION"
"""Проекция развития от канона в будущее."""
# source_levels.py:110
ProvenanceCategory.FUTURE_EXTRAPOLATION: SourceLevel.USER_HYPOTHESIS
# source_levels.py:145-149
SOURCE_CATEGORY_LABELS[FUTURE_EXTRAPOLATION] = {
    "label": "Будущее extrapolation",
    "color": "magenta",
    "description": "Проекция от канона в будущее",
}
```

### 4.2 Где должен применяться (target)

| Элемент | Provenance | Текущий статус |
|---------|-----------|----------------|
| Future epoch nodes (будущее_время etc.) | **FUTURE_EXTRAPOLATION** | ❌ Пусто |
| Each generated scenario | **FUTURE_EXTRAPOLATION** + compatibility_score | ❌ Пусто |
| Forward chain (M8 output) | **FUTURE_EXTRAPOLATION** | ❌ Пусто |
| Extrapolation path (arkaim→future) | **FUTURE_EXTRAPOLATION** | ❌ Пусто |

### 4.3 Почему FUTURE_EXTRAPOLATION, не HYPOTHESIS

- `HYPOTHESIS` — системная гипотеза о мире
- `FUTURE_EXTRAPOLATION` — специфическая проекция от канона в будущее
- Category специально создан для этого (source_levels.py:61-62)
- Использование HYPOTHESIS для future scenarios было бы менее точно

### 4.4 Полный provenance pipeline

```
PRESENT                          → HYPOTHESIS (methodological anchor)
  ↓ [reconstruction path, computed]
BACKWARD chain                   → RECONSTRUCTION (archaeological + canon)
  ↓
ARKAIM (temporal_arkaim_era)     → AUTHOR_CANON + EXTERNAL_SOURCE (enriched)
  ↓ [extrapolation, M8]
FORWARD chain nodes              → FUTURE_EXTRAPOLATION
  ↓
SCENARIOS                        → FUTURE_EXTRAPOLATION + compatibility data
```

**Инвариант сохраняется:**
```
FUTURE_EXTRAPOLATION ≠ HISTORICAL_FACT  ✓
RECONSTRUCTION ≠ HISTORICAL_FACT        ✓
HYPOTHESIS ≠ HISTORICAL_FACT            ✓
```

---

## 5. M8 INTEGRATION

### 5.1 Текущий контракт

```python
FutureExtrapolator(wm).extrapolate(anchor_id="arkaim_era")
→ { chain: TemporalChain, scenarios: list[dict] }
```

M8 работает как **standalone engine**: принимает anchor, строит forward chain, генерирует сценарии.

### 5.2 Целевой контракт

**M8 остаётся standalone (`ARKAIM → FUTURE`).**

Объединение в единую pipeline выполняется на уровне orchestration (WorldEngine), не внутри M8.

```python
# WorldEngine (orchestration layer)
def get_full_temporal_pipeline():
    backward = self.get_temporal_chain("BACKWARD")      # M6
    forward = self._future_extrapolator.extrapolate(     # M8
        anchor_id="arkaim_era"
    )
    return {
        "present_reference": "temporal_today",
        "backward_chain": backward,
        "arkaim_anchor": "temporal_arkaim_era",
        "forward_chain": forward.chain,
        "scenarios": forward.scenarios,
    }
```

**Почему не менять M8:**
1. M8 технически корректен
2. M8 уже покрыт 13 тестами
3. Изменение контракта M8 = риск regressions
4. Orchestration layer — правильный уровень для композиции

### 5.3 Что изменить в M8 (минимально, после решения)

1. **Provenance tagging:** tagged forward chain + scenarios with `FUTURE_EXTRAPOLATION`
2. **No structural changes:** anchor handling, BFS, scenario generation — оставить как есть

---

## 6. ФИНАЛЬНАЯ МОДЕЛЬ

### 6.1 Target Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENT                               │
│  Node: temporal_today (exists in code, not in graph)    │
│  Provenance: HYPOTHESIS                                 │
│  Role: methodological starting point                    │
│  Confidence: 1.0 (exact time)                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ MECHANISM: _trace_backward()
                       │ (engine methodology, NOT graph relation)
                       │
                       │ SEMANTICS: "starting reconstruction from present"
                       │
                       │ PROVENANCE: RECONSTRUCTION
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    ARKAIM                                │
│  Node: temporal_arkaim_era (CANONICAL)                  │
│  Provenance: AUTHOR_CANON + EXTERNAL_SOURCE             │
│  (currently EMPTY — needs enrichment from ArkaimAnchor) │
│  is_anchor: True                                        │
│  Relations: in+out PRECEDES (connected to chain)        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ MECHANISM: FutureExtrapolator
                       │ (M8 — standalone engine)
                       │
                       │ SEMANTICS: "project from anchor to future"
                       │
                       │ PROVENANCE: FUTURE_EXTRAPOLATION
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    FUTURE                                │
│  Nodes: future epochs (e.g., temporal_будущее_время)     │
│  Provenance: FUTURE_EXTRAPOLATION                       │
│  Scenarios: { description, compatibility_score, risk }  │
│  Each scenario: FUTURE_EXTRAPOLATION + score            │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Для каждой стрелки

| Связь | Тип | Механизм | Provenance | Status |
|-------|-----|----------|------------|--------|
| PRESENT → ARKAIM | Methodological reconstruction path | `_trace_backward(arkaim_era)` | RECONSTRUCTION | Reconstruction, not fact |
| ARKAIM → FUTURE | Forward extrapolation | `FutureExtrapolator` | FUTURE_EXTRAPOLATION | Projection, not fact |

### 6.3 Arrow 1: PRESENT → ARKAIM

- **Тип связи:** Methodological reconstruction path (NOT a graph relation)
- **Механизм:** `TemporalReconstructionEngine._trace_backward("temporal_arkaim_era")`
- **Provenance всей цепочки:** `RECONSTRUCTION`
- **Является ли историческим утверждением:** НЕТ
- **Является ли реконструкцией:** ДА
- **Текущее состояние:** BACKWARD chain работает, но не имеет явного "from present" контекста

### 6.4 Arrow 2: ARKAIM → FUTURE

- **Тип связи:** Forward extrapolation (M8)
- **Механизм:** `FutureExtrapolator._build_forward_chain()` + `_generate_scenarios()`
- **Provenance узлов:** `FUTURE_EXTRAPOLATION` (currently EMPTY — bug)
- **Provenance сценариев:** `FUTURE_EXTRAPOLATION` + compatibility data
- **Является ли историческим утверждением:** НЕТ
- **Является ли проекцией:** ДА
- **Текущее состояние:** Работает, но provenance не маркируется

---

## 7. UNSOLVED QUESTIONS

| # | Вопрос | Варианты | Рекомендация |
|---|--------|----------|--------------|
| Q1 | Provenance для temporal_today | HYPOTHESIS / EXTERNAL_SOURCE / PRESENT_REFERENCE | **HYPOTHESIS** — методологическое допущение |
| Q2 | Present→Arkaim relation | Graph edge / Computed path / New type | **Computed path** — без graph edge |
| Q3 | Dual anchor | Enrich + remove orphan / Keep both / New identity rel | **Enrich arkaim_era provenance, remove orphan from graph** |
| Q4 | Future provenance | FUTURE_EXTRAPOLATION / HYPOTHESIS / mixed | **FUTURE_EXTRAPOLATION** for all forward elements |
| Q5 | M8 integration | Standalone + orchestration / Unified / New pipeline class | **Standalone + WorldEngine orchestration** |
| Q6 | Evidence for Present→Arkaim | Add to ARCHAEOLOGY.json / Use existing / Mark as gap | **Mark as gap** until evidence added |

---

## 8. M8.1 IMPLEMENTATION SCOPE

После утверждения архитектуры, M8.1 требует:

### Must have
1. Исправить provenance в `TemporalNode.present_anchor()` → HYPOTHESIS
2. Enrich `temporal_arkaim_era` provenance из ArkaimAnchor (AUTHOR_CANON + EXTERNAL_SOURCE)
3. Убрать `temporal_arkaim_anchor` из графа (не добавлять орфана)
4. M8: tag forward chain and scenarios with `FUTURE_EXTRAPOLATION` provenance

### Should have
5. `WorldEngine.get_full_temporal_pipeline()` — orchestration layer (present→backward→arkaim→forward)
6. Fill `PresentAnchor.temporal_nodes` с actual node IDs

### Nice to have
7. Добавить archaeological discovery date в ARCHAEOLOGY.json evidence
8. M8 принимает `anchor_id="temporal_today"` и internally resolves to arkaim_era

### Estimated scope
- **Code changes:** ~60 lines
- **New tests:** ~6 tests
- **Breaking changes:** None (additive provenance enrichment)

---

## FINAL STATUS

### M8.1 — ARCHITECTURE DECISION READY

**Обоснование:**

1. Все 6 вопросов проанализированы с вариантами и рекомендациями
2. Ключевое решение принято: PRESENT→ARKAIM = computed path, НЕ graph relation
3. Provenance model определена для всех уровней pipeline
4. M8 остаётся standalone, orchestration — на уровне WorldEngine
5. Dual anchor решён архитектурно (enrich + remove orphan)
6. FUTURE_EXTRAPOLATION applied correctly
7. Implementation scope определён без Ambiguity

**Блокировок нет.** Решение готово к реализации после утверждения.
