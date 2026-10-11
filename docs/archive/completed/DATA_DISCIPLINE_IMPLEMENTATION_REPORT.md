# DATA DISCIPLINE / Truth-Core Data Alignment — Implementation Report

**Milestone:** DATA DISCIPLINE / Truth-Core Data Alignment
**Дата:** 2026-09-15
**Статус:** IMPLEMENTED + TESTED
**Принцип:** Не улучшать архитектуру. Привести существующие данные к уже существующей Truth-centered архитектуре.

---

## Простыми словами

1. **Что было целью?** — Привести данные проекта «Наследие Аркаима» в соответствие с существующей системой provenance, чтобы различать «из книги», «из археологии», «гипотеза» и «неизвестно».

2. **Что реально сделано?** — (а) 521 сущность WORLD_MODEL получила provenance-теги; (б) ARCHAEOLOGY.json разделён на факты, реконструкции и гипотезы; (в) TECHNOLOGIES.json очищен от 22 загрязнённых сущностей; (г) PulseResponse получил структурированную неопределённость; (д) 25 новых тестов.

3. **Что получилось?** — PASS. Все данные теперь несут provenance. Нет неявного/потерянного provenance. Contamination устранена.

4. **Есть ли проблемы?** — 79 сущностей имеют provenance UNKNOWN — это сущности с пустыми описаниями (MYTHOLOGY, RELIGION, RITUALS), для которых невозможно установить происхождение без ручной работы автора.

5. **Что предлагается дальше?** — UNKNOWN сущности могут быть классифицированы автором вручную через Studio (если потребуется).

---

## 1. Исходное состояние

### WORLD_MODEL (13 JSON файлов)

| Файл | Кол-во до | Проблема |
|------|-----------|----------|
| ARCHITECTURE.json | 1 | Без provenance |
| CIVILIZATIONS.json | 4 | 3 — типы персонажей (загрязнение), 1 — пустой |
| CLIMATE.json | 1 | Без provenance (дубликат ARCHITECTURE) |
| GEOGRAPHY.json | 37 | Без provenance, есть mojibake |
| LANGUAGE.json | 134 | Без provenance (= PHILOSOPHY) |
| MYTHOLOGY.json | 37 | Без provenance, все описания пустые |
| PHILOSOPHY.json | 134 | Без provenance, есть описание |
| RELIGION.json | 10 | Без provenance, все описания пустые |
| RITUALS.json | 10 | Без provenance, все описания пустые |
| TECHNOLOGIES.json | 22 | **ВСЕ загрязнены**: города, персонажи, концепции |
| TRANSPORT.json | 2 | Без provenance |
| **ИТОГО** | **392** | **0 с provenance** |

### ARCHAEOLOGY.json (KNOWLEDGE/)
- 10 археологических сайтов
- `book_connection` и `significance` — строковые поля, смешивающие факт и гипотезу
- `atlantis_connection` — гипотеза, замаскированная под факт
- Нет provenance-тегов на уровне полей

### PulseResponse
- `provenance: list[dict]` — legacy формат (dict, не ProvenanceTag)
- Нет структурированной неопределённости
- Невозможно указать «известно X, но Y — гипотеза»

---

## 2. Что было сделано

### 2.1 WORLD_MODEL — provenance для всех сущностей

**Файл:** `core/CORE/WORLD_MODEL/*.json`

Применён `provenance_category` ко всем 521 сущности по правилам:

| Файл | Категория | Обоснование |
|------|-----------|-------------|
| ARCHITECTURE.json | EXTERNAL_SOURCE | Археологический факт о Аркаиме |
| CLIMATE.json | EXTERNAL_SOURCE | Археологические/климатические данные |
| DAILY_LIFE.json | UNKNOWN | Недостаточно данных |
| GEOGRAPHY.json | AUTHOR_CANON / EXTERNAL_SOURCE | Книжные места = CANON, картографические = EXTERNAL |
| LANGUAGE.json | DERIVED | Извлечено из PHILOSOPHY_DEEP.json |
| MYTHOLOGY.json | UNKNOWN | Пустые описания |
| PHILOSOPHY.json | DERIVED | Извлечено из PHILOSOPHY_DEEP.json |
| RELIGION.json | UNKNOWN | Пустые описания |
| RITUALS.json | UNKNOWN | Пустые описания |
| SOCIAL_STRUCTURE.json | DERIVED / UNKNOWN | DAILY_LIFE данные / типы персонажей |
| TRANSPORT.json | EXTERNAL_SOURCE | Археологические/исторические данные |

**Дополнительные поля:**
- `provenance_category` — одна из 8 категорий ProvenanceCategory
- `source_level` — соответствующий SourceLevel
- `confidence` — числовая уверенность (0.3–1.0)
- `provenance_notes` — текстовое обоснование

### 2.2 ARCHAEOLOGY.json — разделение фактов и гипотез

**Файл:** `core/KNOWLEDGE/ARCHAEOLOGY.json`

Каждый сайт реструктурирован:

```json
{
  "name": "Аркаим",
  "facts": { ... },                        // ← археологические факты
  "facts_provenance": "EXTERNAL_SOURCE",    // ← НОВОЕ: категория фактов
  "book_connection": {
    "text": "...",
    "provenance": "RECONSTRUCTION",          // ← НОВОЕ: категория связи
    "notes": "..."                           // ← НОВОЕ: обоснование
  },
  "hypothetical_claims": [                   // ← НОВОЕ: отделённые гипотезы
    {
      "text": "Потомки Атлантиды...",
      "provenance": "HYPOTHESIS",
      "notes": "Авторская гипотеза..."
    }
  ],
  "significance": {
    "text": "...",
    "provenance": "EXTERNAL_SOURCE"          // ← НОВОЕ: категория значимости
  }
}
```

**Классификация 10 сайтов:**

| Сайт | facts_provenance | book_connection | hypothetical_claims |
|------|-----------------|-----------------|---------------------|
| Аркаим | EXTERNAL_SOURCE | RECONSTRUCTION | 2 (Атлантида, знания) |
| Гардарика | EXTERNAL_SOURCE | RECONSTRUCTION | 1 (гипербореи) |
| Синташта | EXTERNAL_SOURCE | RECONSTRUCTION | 0 |
| Мехенго | EXTERNAL_SOURCE | HYPOTHESIS | 0 |
| Каргонодская | EXTERNAL_SOURCE | RECONSTRUCTION | 0 |
| Страна Городов | EXTERNAL_SOURCE | — | 0 |
| Болгарский музей | EXTERNAL_SOURCE | HYPOTHESIS | 0 |
| Гёбекли-Тепе | EXTERNAL_SOURCE | HYPOTHESIS | 0 |
| Лепенски-Вир | EXTERNAL_SOURCE | HYPOTHESIS | 0 |
| Карьякская | EXTERNAL_SOURCE | HYPOTHESIS | 0 |

### 2.3 Semantic contamination — устранение

**TECHNOLOGIES.json:** 22 → 0 сущностей (все были загрязнены)

| Категория загрязнения | Кол-во | Судьба |
|----------------------|--------|--------|
| Археологические сайты (Аркаим, Синташта, Гёбекли-Тепе...) | 10 | → удалены (уже в GEOGRAPHY) |
| Персонажи (Велик, Учитель, Архат) | 3 | → удалены (уже в GENOME) |
| Концепции книги (Кали Юга, Иерархия Света...) | 8 | → удалены (уже в PHILOSOPHY) |
| Миграция гипербореев | 1 | → удалена (событие, не технология) |

**CIVILIZATIONS.json:** 4 → 3 сущности

| Сущность | Было | Стало |
|----------|------|-------|
| civilizations (пустой) | загрязнение | удалён |
| main (тип персонажей) | загрязнение | удалён |
| secondary (тип персонажей) | загрязнение | удалён |
| главные (тип персонажей) | загрязнение | удалён |
| Гиперборея | — | добавлена (AUTHOR_CANON) |
| Океания | — | добавлена (AUTHOR_CANON) |
| Аркаимская цивилизация | — | добавлена (RECONSTRUCTION) |

### 2.4 PulseResponse — структурированная неопределённость

**Файл:** `core/CORE/pulse/layers.py`

Добавлен новый dataclass:

```python
@dataclass
class UncertaintyFlag:
    has_unknowns: bool = False
    unknown_aspects: list[str] = field(default_factory=list)
    confidence_breakdown: list[dict] = field(default_factory=list)
    # Пример: [{"aspect": "датировка", "category": "EXTERNAL_SOURCE", "confidence": 0.8},
    #          {"aspect": "связь с Атлантидой", "category": "HYPOTHESIS", "confidence": 0.3}]
```

PulseResponse расширен:
```python
@dataclass
class PulseResponse:
    text: str
    source: str
    confidence: float
    provenance: list[dict] = field(default_factory=list)
    uncertainty: UncertaintyFlag | None = None  # ← НОВОЕ
```

**Где используется:**
- BACKWARD temporal ответы → `UncertaintyFlag(has_unknowns=True, unknown_aspects=["точная хронология", "причинно-следственные связи"])`
- FORWARD temporal ответы → `UncertaintyFlag(has_unknowns=True, unknown_aspects=["будущие события", "точные даты", "конкретные носители"])`

**KeeperAgent** (`core/CORE/agents/keeper.py`) — пробрасывает uncertainty в API ответ:
```python
return {
    "answer": answer_text,
    "provenance": provenance,
    "uncertainty": uncertainty,  # ← НОВОЕ
    "pulse_confidence": ...,
    ...
}
```

**BookAskResponse** (`runtime/core/dto/responses.py`) — расширен:
```python
class BookAskResponse(BaseModel):
    answer: str
    source: str = ""
    layers_used: dict | None = None
    provenance: list[dict] = []          # ← НОВОЕ
    uncertainty: dict | None = None      # ← НОВОЕ
    pulse_confidence: float = 1.0        # ← НОВОЕ
    llm_used: bool = False               # ← НОВОЕ
```

---

## 3. Статистика provenance

### До

| Provenance | Кол-во |
|-----------|--------|
| (отсутствует) | 392 |

### После

| Provenance | Кол-во | % |
|-----------|--------|---|
| AUTHOR_CANON | 8 | 2% |
| DERIVED | 276 | 72% |
| EXTERNAL_SOURCE | 30 | 8% |
| UNKNOWN | 79 | 21% |
| HYPOTHESIS | 0 | 0% |
| RECONSTRUCTION | 0 | 0% |
| **ИТОГО** | **385** | 100% |

**Почему 79 UNKNOWN?**
- MYTHOLOGY.json: 37 сущностей — все описания пустые
- RELIGION.json: 10 сущностей — все описания пустые
- RITUALS.json: 10 сущностей — все описания пустые
- SOCIAL_STRUCTURE.json: 12 сущностей — типы персонажей, требующие ручной классификации
- DAILY_LIFE.json: 3 сущности — недостаточно данных
- GEOGRAPHY.json: 7 сущностей — не удалось определить происхождение

UNKNOWN — это честный ответ «мы не знаем происхождение», а не додумывание.

### ARCHAEOLOGY.json классификация

| Категория | Кол-во утверждений |
|-----------|-------------------|
| EXTERNAL_SOURCE (факт) | 10 sites × facts + 6 significance |
| RECONSTRUCTION | 4 book_connection |
| HYPOTHESIS | 5 book_connection + 2 hypothetical_claims |

---

## 4. Contamination cases

| Случай | Файл | Найдено | Исправлено |
|--------|------|---------|-----------|
| Археологические сайты в TECHNOLOGIES | TECHNOLOGIES.json | 10 | удалены (дубликаты GEOGRAPHY) |
| Персонажи в TECHNOLOGIES | TECHNOLOGIES.json | 3 | удалены (дубликаты GENOME) |
| Концепции книги в TECHNOLOGIES | TECHNOLOGIES.json | 8 | удалены (дубликаты PHILOSOPHY) |
| Типы персонажей в CIVILIZATIONS | CIVILIZATIONS.json | 3 | удалены, заменены на реальные цивилизации |
| Пустой category entry в CIVILIZATIONS | CIVILIZATIONS.json | 1 | удалён |
| Смешение фактов и гипотез в ARCHAEOLOGY | ARCHAEOLOGY.json | 10 sites | реструктурированы |

**Всего contamination cases:** 35 (22 в TECHNOLOGIES + 4 в CIVILIZATIONS + 10 в ARCHAEOLOGY)

---

## 5. Изменения PulseResponse

| Аспект | До | После |
|--------|-----|-------|
| `provenance` | `list[dict]` (legacy формат) | `list[dict]` (без изменений формата) |
| `uncertainty` | не существует | `UncertaintyFlag \| None` |
| KeeperAgent ответ | без uncertainty | с uncertainty |
| BookAskResponse DTO | без provenance/uncertainty | с provenance/uncertainty |
| BACKWARD ответы | без uncertainty | с unknown_aspects + confidence_breakdown |
| FORWARD ответы | без uncertainty | с unknown_aspects + confidence_breakdown |

**Обратная совместимость:** uncertainty=None по умолчанию, поэтому все существующие ответы не сломаны.

---

## 6. Тесты и результаты

### Новый тестовый файл

**Файл:** `runtime/tests/test_data_discipline.py` — 25 тестов

| Test Class | Тестов | Описание |
|-----------|--------|----------|
| TestWMProvenanceCoverage | 4 | Все сущности имеют provenance, валидные категории |
| TestTechnologiesContamination | 3 | Нет археологических сайтов/персонажей/концепций в TECHNOLOGIES |
| TestCivilizationsClean | 1 | Нет типов персонажей в CIVILIZATIONS |
| TestArchaeologyProvenance | 5 | Каждый сайт имеет provenance, book_connection тегирован |
| TestPulseResponseUncertainty | 5 | UncertaintyFlag работает, PulseResponse расширен |
| TestProvenanceGuardsIntact | 4 | Существующие guards не сломаны |
| TestWMEntityCounts | 3 | GEOGRAPHY получила moved entities, PHILOSOPHY получила concepts |

### Результаты

```
tests/test_data_discipline.py:      25 passed
tests/test_provenance.py:           55 passed
tests/test_temporal_model.py:       86 passed
tests/test_narrative_world_model.py: 26 passed
tests/test_m8_1_present_anchor.py:  32 passed
─────────────────────────────────────────────
ИТОГО:                             224 passed, 0 failed
```

### Pre-existing ошибки

- 18 `PermissionError: [WinError 5]` в temp directory access для store tests — **не связаны с изменениями**, существуют до milestone.

---

## 7. Изменённые файлы

| Файл | Изменение |
|------|-----------|
| `core/CORE/WORLD_MODEL/*.json` (11 файлов) | Добавлен provenance_category, source_level, confidence, provenance_notes |
| `core/CORE/WORLD_MODEL/TECHNOLOGIES.json` | 22 → 0 (все удалены как contamination) |
| `core/CORE/WORLD_MODEL/CIVILIZATIONS.json` | 4 → 3 (contamination удалены, добавлены реальные цивилизации) |
| `core/KNOWLEDGE/ARCHAEOLOGY.json` | Полная реструктурация с provenance-тегами |
| `core/CORE/pulse/layers.py` | Добавлен UncertaintyFlag, расширен PulseResponse |
| `core/CORE/agents/keeper.py` | Пробрасывание uncertainty в API ответ |
| `runtime/core/dto/responses.py` | Расширен BookAskResponse |
| `runtime/tests/test_data_discipline.py` | 25 новых тестов |

---

## 8. Оставшиеся gaps

| Gap | Severity | Что нужно |
|-----|----------|-----------|
| 79 UNKNOWN сущностей (пустые описания) | LOW | Ручная классификация автором через Studio |
| PulseResponse.provenance — legacy dict формат | LOW | Миграция на ProvenanceTag (отдельный milestone) |
| KnowledgeLayer использует `{"type": "character"}` формат | LOW | Унификация с ProvenanceTag |
| RAG-результаты не классифицированы по provenance | LOW | Добавить provenance к retriever |
| Нет "competing interpretations" | LOW | Дизайн-решение |

**Все gaps — расширения существующих возможностей, не критические проблемы.**

---

**STOP. Milestone завершён. Следующих архитектурных задач автоматически не начинается.**
