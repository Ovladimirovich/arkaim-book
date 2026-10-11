# Knowledge Expansion — Система расширения знаний

> Дата: 16.07.2026

## Обзор

**Knowledge Expansion** — инфраструктура для автоматического обогащения ядра знаний книги. Превращает статичные JSON-файлы в растущий организм знаний.

**Философия:** Не строить «очередной набор JSON-файлов». Строить инфраструктуру расширения знаний.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                  KNOWLEDGE EXPANSION PIPELINE            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Источник │───▶│ Extractor│───▶│ Enricher │          │
│  │ (JSON/   │    │ (парсинг)│    │ (LLM)    │          │
│  │  текст)  │    └──────────┘    └──────────┘          │
│  └──────────┘         │                │                │
│                       ▼                ▼                │
│                ┌──────────┐    ┌──────────┐            │
│                │ Validator│◀───│ Linker   │            │
│                │ (проверка│    │ (связи с │            │
│                │  формата)│    │  графом)  │            │
│                └──────────┘    └──────────┘            │
│                       │                │                │
│                       ▼                ▼                │
│                ┌──────────────────────────┐            │
│                │     Knowledge Store      │            │
│                │   (JSON + Graph Update)  │            │
│                └──────────────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Компоненты

### 1. Extractor (Извлечение)

Извлекает сырые знания из источников.

| Тип | Файл | Описание |
|-----|------|----------|
| JSON | `extractors/json_extractor.py` | Из существующих JSON-файлов |
| LLM | `extractors/llm_extractor.py` | Через LLM (для неструктурированных данных) |

### 2. Enricher (Обогащение)

Обогащает знания через LLM-анализ.

| Тип | Файл | Описание |
|-----|------|----------|
| DeepAnalyzer | `enrichers/deep_analyzer.py` | Углублённый анализ тем/символов |
| CrossReferencer | `enrichers/cross_referencer.py` | Поиск связей с другими культурами |
| PatternDetector | `enrichers/pattern_detector.py` | Обнаружение повторяющихся структур |

### 3. Linker (Связывание)

Связывает новые знания с существующим Knowledge Graph.

| Тип | Файл | Описание |
|-----|------|----------|
| GraphLinker | `linkers/graph_linker.py` | Связывание с KG через BFS |

### 4. Validator (Проверка)

Валидирует формат и качество знаний.

| Тип | Файл | Описание |
|-----|------|----------|
| SchemaValidator | `validators/schema_validator.py` | Проверка схемы JSON |

### 5. Store (Хранение)

Сохраняет знания и обновляет граф.

| Тип | Файл | Описание |
|-----|------|----------|
| KnowledgeStore | `store/knowledge_store.py` | JSON + Graph Update |

---

## Модули обогащения

### Регистрированные модули (11 шт.)

| Модуль | Источник | Выход | Описание |
|--------|----------|-------|----------|
| philosophy_deep | PHILOSOPHY.json | PHILOSOPHY_DEEP.json | Глубокий анализ философии |
| themes_deep | THEMES_DEEP.json | THEMES_EXPANDED.json | Расширенные темы |
| symbols_expanded | SYMBOLS_EXPANDED.json | SYMBOLS_DEEP.json | Глубокие толкования |
| cross_references | CROSS_REFERENCES.json | CROSS_REFERENCES_DEEP.json | Кросс-референсы |
| archaeology | ARCHAEOLOGY.json | ARCHAEOLOGY_DEEP.json | Археология |
| cosmology | THEMES_DEEP + ESOTERIC | COSMOLOGY.json | Космология |
| geography | MAP_DATA + ARCHAEOLOGY | GEOGRAPHY.json | География |
| psychology | THEMES_DEEP + SYMBOLS | PSYCHOLOGY.json | Психология |
| language | PHILOSOPHY + CROSS_REF | LANGUAGE.json | Язык |
| rituals | ESOTERIC_CONNECTIONS | RITUALS.json | Ритуалы |
| technology | ARCHAEOLOGY + THEMES | TECHNOLOGY.json | Технологии |

### Контракт модуля

```python
@dataclass
class EnrichmentModule:
    name: str                      # "philosophy_deep"
    description: str               # "Глубокий анализ философии"
    source_files: list[Path]       # Откуда берём данные
    output_file: Path              # Куда сохраняем
    enricher_class: type           # Класс обогащения
    dependencies: list[str]        # Какие модули нужны beforehand
```

### CLI

```bash
# Запустить все модули
python -m knowledge_expansion.run --all

# Запустить конкретный модуль
python -m knowledge_expansion.run --module cosmology

# Посмотреть статус
python -m knowledge_expansion.run --status
```

---

## ExpansionLayer (Pulse)

### Назначение

8-й слой Pulse, который ищет ответы в расширенных JSON-файлах.

### Порядок поиска

```
BookPulse.listen(query)
  → KnowledgeLayer.respond_to()     # базовые знания
  → ExpansionLayer.respond_to()     # расширенные знания
  → MeaningLayer.respond_to()       # смыслы
  → IdentityLayer.respond_to()      # кто я
  → MissionLayer.respond_to()       # миссия
```

### Загрузка данных

ExpansionLayer загружает:
1. `*_DEEP.json` файлы (кроме THEMES_DEEP.json)
2. `THEMES_DEEP.json` (перезаписывает предыдущие данные)
3. `*_EXPANDED.json` файлы
4. `ACADEMIC_CONFIRMATIONS.json`

### Файлы

| Файл | Назначение |
|------|-----------|
| `pulse/layers.py` | ExpansionLayer класс |
| `knowledge_expansion/expansion_loader.py` | Загрузчик данных |
| `knowledge_expansion/llm_client.py` | LLM-клиент (GigaChat) |

---

## Автоматическое обогащение

### Scheduler

`knowledge_expansion/scheduler.py` — планировщик обогащения:

- Проверяет изменения в исходных файлах
- Запускает обогащение для изменившихся модулей
- Уведомляет через WebSocket

### Интеграция с main.py

```python
# В lifespan:
_knowledge_task = asyncio.create_task(_knowledge_enrichment_loop())
```

### API endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /book/community/knowledge/refresh | Принудительное обогащение |
| GET | /book/community/knowledge/status | Статус пайплайна |

---

## LLM-клиент

### Поддержка

| Провайдер | Статус | Описание |
|-----------|--------|----------|
| GigaChat | ✅ | Через существующий провайдер с OAuth2 |
| OpenRouter | ❌ | Не настроен |

### Использование

```python
from knowledge_expansion.llm_client import create_llm_client

llm = create_llm_client(provider="gigachat")
response = await llm.generate("Промпт", max_tokens=2000)
```

---

## ExpansionLayer — 168 тем

### Ключевые темы

| Тема | Уровни | Связи |
|------|--------|-------|
| Гиперборея | literal, metaphorical, cosmic | Аркаим, Миграция |
| Аркаим | literal, metaphorical, cosmic | Океания, Гиперборея |
| Океания = Атлантида | literal, metaphorical, cosmic | Платон, Потоп |
| Иерархия Света | literal, metaphorical, cosmic | Архаты, Наставники |
| Кали Юга | literal, metaphorical, cosmic | Эпохи, Цикличность |
| Звукознание | literal, metaphorical, cosmic | Технологии, Практики |

### Академические подтверждения

| Категория | Культур |
|-----------|---------|
| Всемирный потоп | Месопотамия, Библия, Греция, Индия, Америка |
| Атлантида | Греция, Индия, Америка, Европа |
| Белые бородатые | Ацтеки, Майя, Инки, Шумер, Вавилон |
| Космология | Индия, Греция, Иран, Скандинавия, Китай, Египет |
| Иерархия Света | Индия, Тибет, Ислам, Христианство, Египет, Греция |
| Энергетика мест | Кельты, Египет, Китай, Славянство, Индия, Греция |

---

## Добавление нового модуля

### Шаг 1: Создать файл модуля

```python
# core/CORE/knowledge_expansion/modules/my_module.py
from pathlib import Path

MODULE_CONFIG = {
    "name": "my_module",
    "description": "Описание модуля",
    "source_files": [Path("core/KNOWLEDGE/SOURCE.json")],
    "output_file": Path("core/KNOWLEDGE/OUTPUT.json"),
}
```

### Шаг 2: Зарегистрировать в pipeline.py

```python
pipeline.register_module("my_module", {
    "description": "Описание",
    "source_files": [KNOWLEDGE_DIR / "SOURCE.json"],
    "output_file": KNOWLEDGE_DIR / "OUTPUT.json",
})
```

### Шаг 3: Запустить

```bash
python -m knowledge_expansion.run --module my_module
```

---

## Расширение ExpansionLayer

### Добавление темы

1. Создать/обновить JSON-файл в `core/KNOWLEDGE/`
2. Формат: объект с ключом "themes" (массив тем)
3. Каждая тема: name, layers (literal, metaphorical, cosmic), cross_references

### Пример

```json
{
  "themes": [
    {
      "name": "Новая тема",
      "layers": {
        "literal": "Буквальное описание",
        "metaphorical": "Метафорический смысл",
        "cosmic": "Космический смысл"
      },
      "cross_references": ["Связанная тема 1", "Связанная тема 2"]
    }
  ]
}
```
