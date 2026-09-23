# Knowledge Base — База знаний книги

> Дата: 16.07.2026

## Обзор

База знаний проекта «Наследие Аркаима» — это структурированное представление содержания книги, включающее:

- **Оригинальные знания** — извлечённые из текста книги
- **Расширенные знания** — обогащённые через LLM и кросс-референсы
- **Академические подтверждения** — параллели с мировыми традициями

---

## Структура файлов

### Оригинальные знания (`core/KNOWLEDGE/`)

| Файл | Размер | Назначение |
|------|--------|-----------|
| `BOOK_DOCUMENT.json` | 774 KB | Полный текст книги |
| `SYNOPSIS_DOCUMENT.json` | 858 KB | Структурированный синопсис |
| `enriched_chunks.json` | 1.41 MB | Обогащённые чанки (2123) |
| `enriched_catalog.json` | 538 KB | Каталог с метаданными |
| `character_profiles.json` | 71 KB | Профили персонажей |
| `PHILOSOPHY.json` | 44 KB | 106 философских концепций |
| `AUTHOR_INTENT.json` | 19 KB | 1 главное + 76 вторичных посланий |
| `VALUES.json` | 18 KB | 57 ценностей |
| `CHARACTERS.json` | 9 KB | Список персонажей |
| `PLOT.json` | 5 KB | Конфликты и сюжет |
| `SYMBOLS.json` | 2 KB | Символы |

### Расширенные знания (`core/KNOWLEDGE/`)

| Файл | Тем | Формат |
|------|-----|--------|
| `THEMES_DEEP.json` | 15 | `{name, layers: {literal, metaphorical, cosmic}, cross_references}` |
| `THEMES_EXPANDED.json` | 14 | `{topic, layers, cross_references}` |
| `SYMBOLS_EXPANDED.json` | 14 | `{name, layers, echoes_in}` |
| `CROSS_REFERENCES.json` | 7 | `{theme, book_context, parallels, significance}` |
| `ARCHAEOLOGY.json` | 10 | `{name, location, dating, facts}` |
| `ESOTERIC_CONNECTIONS.json` | 10 | `{name, core_teaching, parallels}` |
| `SCENE_PROMPTS.json` | 12 | `{id, title, prompt, emotion, palette}` |
| `ARCHETYPES_EXPANDED.json` | 15 | `{name, visual, psychology, book_characters}` |
| `EPOCH_PALETTES.json` | 6 | `{name, palette, transitions}` |
| `MAP_DATA.json` | 10 | `{regions, routes, energy_lines}` |
| `MEANING_TREE.json` | 5 | `{name, branches: [...]}` |
| `ANCHOR_QUOTES.json` | 16 | `{text, theme, source, meaning}` |
| `QUESTIONS_FOR_READER.json` | 15 | `{category, questions: [...]}` |
| `COSMOLOGY.json` | 24 | `{name, layers, cycles, cosmic_laws}` |
| `GEOGRAPHY.json` | 22 | `{name, layers, connections}` |
| `PSYCHOLOGY.json` | 26 | `{name, layers, stages}` |
| `LANGUAGE.json` | 135 | `{name, layers, patterns}` |
| `RITUALS.json` | 11 | `{name, layers, traditions}` |
| `TECHNOLOGY.json` | 23 | `{name, layers, parallels}` |

### Академические подтверждения

| Файл | Категорий |
|------|-----------|
| `ACADEMIC_CONFIRMATIONS.json` | 6 |

---

## Формат тем (THEMES_DEEP.json)

```json
{
  "description": "Описание файла",
  "themes": [
    {
      "name": "Название темы",
      "layers": {
        "literal": "Буквальное описание",
        "metaphorical": "Метафорический смысл",
        "cosmic": "Космический смысл"
      },
      "cross_references": ["Связанная тема 1", "Связанная тема 2"],
      "hidden_meaning": "Скрытый смысл",
      "book_quotes": ["Цитата 1", "Цитата 2"],
      "related_symbols": ["символ1", "символ2"]
    }
  ]
}
```

---

## Формат академических подтверждений

```json
{
  "description": "Описание файла",
  "confirmations": [
    {
      "category": "Название категории",
      "book_theme": "Связанная тема в книге",
      "academic_sources": [
        {
          "culture": "Название культуры",
          "text": "Описание параллели"
        }
      ],
      "scientific_explanations": [
        {
          "source": "Научная дисциплина",
          "explanation": "Объяснение явления"
        }
      ]
    }
  ]
}
```

---

## ExpansionLayer — загрузка данных

### Приоритет загрузки

1. `*_DEEP.json` (кроме THEMES_DEEP.json)
2. `THEMES_DEEP.json` (перезаписывает предыдущие данные для тех же тем)
3. `*_EXPANDED.json`
4. `ACADEMIC_CONFIRMATIONS.json`

### Правило перезаписи

Если тема встречается в нескольких файлах, последний загруженный файл перезаписывает предыдущие данные для этой темы.

---

## Статистика

| Метрика | Значение |
|---------|----------|
| Всего тем в ExpansionLayer | 168 |
| Категорий академических подтверждений | 6 |
| Культур в подтверждениях | 30+ |
| Файлов знаний | 40+ |
| Общий размер | ~5 MB |

---

## Управление

### Добавление темы

1. Создать/обновить JSON-файл в `core/KNOWLEDGE/`
2. Формат: `{ "themes": [{ "name": "...", "layers": {...}, ... }] }`
3. ExpansionLayer автоматически подхватит при перезагрузке

### Добавление модуля обогащения

1. Создать файл в `core/CORE/knowledge_expansion/modules/`
2. Зарегистрировать в `pipeline.py`
3. Запустить: `python -m knowledge_expansion.run --module name`

### Просмотр статуса

```bash
python -m knowledge_expansion.run --status
```
