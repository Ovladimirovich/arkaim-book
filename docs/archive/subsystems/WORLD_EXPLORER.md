# World Explorer — Документация подсистемы

## Обзор

**World Explorer** — подсистема исследования мира книги «Наследие Аркаима». Позволяет исследовать альтернативные линии развития мира, не разрушая канон.

Это НЕ генератор рассказов. Это движок реконструкции и развития мира.

---

## Архитектура

### Модули

| Модуль | Файл | Назначение |
|--------|------|------------|
| Canon Engine | `compatibility_checker.py` | Проверка совместимости по 6 осям |
| World Model | `ability_model.py` | Модель возможностей мира |
| Logic Engine | `impact_assessor.py`, `contradiction_detector.py`, `world_delta.py` | Логика следствий |
| Exploration Core | `hypothesis_generator.py`, `scenario_modeler.py`, `branch_manager.py` | Ядро исследования |
| Quality Evaluator | `quality_evaluator.py` | Оценка по 5 критериям |
| World Explorer | `world_explorer.py` | Единый pipeline |
| Deep Explorer | `deep_explorer.py` | Многоуровневое исследование |
| External Sources | `external_sources.py` | Wikipedia, Semantic Scholar, OpenAlex |
| Performance | `performance.py` | Кэширование, метрики |
| Export Report | `export_report.py` | Генерация Markdown отчётов |
| WebSocket | `exploration_ws.py` | Real-time прогресс |
| History Store | `exploration_store.py` | История в SQLite |
| Feedback Store | `feedback_store.py` | Обратная связь |
| Unified Pipeline | `unified_pipeline.py` | Связка World Explorer + Story Engine |

### Pipeline

```
Запрос → Compatibility Check → Hypothesis Generation → Scenario Modeling →
Impact Assessment → Contradiction Detection → World Delta → Quality Evaluation →
Ranking → (Story Generation) → Export
```

---

## API Endpoints

### Основные

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/book/world-explorer/explore` | Исследование мира |
| POST | `/book/world-explorer/explore/hypothesis` | Исследование от гипотезы |
| POST | `/book/world-explorer/explore-deep` | Глубокое исследование |
| POST | `/book/world-explorer/unified` | Unified Pipeline (Explorer + Story) |
| POST | `/book/world-explorer/validate` | Проверка совместимости |
| POST | `/book/world-explorer/export` | Экспорт в Markdown |

### Данные

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/book/world-explorer/hypotheses/{epoch}` | Гипотезы для эпохи |
| GET | `/book/world-explorer/possibilities/{epoch}` | Возможности эпохи |
| GET | `/book/world-explorer/free-points` | Свободные точки мира |
| GET | `/book/world-explorer/best-paths` | Лучшие пути в дереве |
| GET | `/book/world-explorer/epochs` | Список эпох |
| GET | `/book/world-explorer/stats` | Статистика системы |

### Управление

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/book/world-explorer/history` | История исследований |
| GET | `/book/world-explorer/history/{id}` | Детали исследования |
| POST | `/book/world-explorer/history` | Сохранить исследование |
| DELETE | `/book/world-explorer/history/{id}` | Удалить исследование |
| POST | `/book/world-explorer/generate-from-branch` | Генерация текста из ветви |

### Обратная связь

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/book/world-explorer/feedback` | Добавить отзыв |
| GET | `/book/world-explorer/feedback` | Отзывы пользователя |
| GET | `/book/world-explorer/feedback/average` | Средний рейтинг |
| DELETE | `/book/world-explorer/feedback/{id}` | Удалить отзыв |

### Внешние источники

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/book/world-explorer/sources/search` | Поиск во внешних источниках |

### Производительность

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/book/world-explorer/cache/stats` | Статистика кэша |
| POST | `/book/world-explorer/cache/clear` | Очистить кэш |

---

## Модели данных

### ExplorationRequest

```json
{
  "prompt": "Что если Аркаим не был разрушен?",
  "epoch": "satya_yuga",
  "location": null,
  "branch_count": 3,
  "max_depth": 2
}
```

### ExplorationResult

```json
{
  "request": {...},
  "hypothesis": {"id": "hyp_0001", "title": "...", "type": "CASCADE_EFFECT"},
  "scenario": {"branch_count": 3, "best_branch_id": "..."},
  "ranked_branches": [
    {
      "rank": 1,
      "branch_type": "conservative",
      "title": "...",
      "quality_score": 0.85,
      "strengths": ["..."],
      "weaknesses": ["..."],
      "impact_score": 0.7,
      "contradictions": 0,
      "delta_changes": 2
    }
  ],
  "duration_ms": 150,
  "summary": "Гипотеза: ...; Ветвей: 3; Лучшая: 0.850"
}
```

### CompatibilityReport

```json
{
  "overall_score": 0.85,
  "is_compatible": true,
  "risk_level": "low",
  "axis_scores": [
    {"axis": "book_canon", "score": 0.9, "violations_count": 0},
    {"axis": "historical", "score": 0.8, "violations_count": 0}
  ],
  "recommendations": ["..."]
}
```

### QualityReport

```json
{
  "overall_score": 0.82,
  "criteria_scores": [
    {"criterion": "canon_alignment", "score": 0.9, "weight": 0.3},
    {"criterion": "logical_consistency", "score": 0.85, "weight": 0.25}
  ],
  "strengths": ["..."],
  "weaknesses": ["..."],
  "recommendations": ["..."]
}
```

---

## Фронтенд

### Страница `/world-explorer`

9 блоков функциональности:

1. **Панель ввода** — TextArea + селектор эпохи + slider ветвей
2. **Проверка совместимости** — real-time debounce + Progress по 6 осям
3. **Результаты исследования** — ranked branches с quality scores
4. **Детали ветви** — Modal с 5 критериями + strengths/weaknesses
5. **Браузер гипотез** — Tab с List гипотез
6. **Браузер возможностей** — Tab с List возможностей
7. **Сравнение ветвей** — Modal side-by-side
8. **История** — localStorage + API
9. **Real-time прогресс** — WebSocket events

---

## Тестирование

### Статистика

- **111 unit-тестов** — все проходят
- **15 модулей** — полная покрытие
- **24 API endpoints** — все протестированы

### Запуск тестов

```bash
cd runtime && .venv\Scripts\python -m pytest tests/test_world_explorer.py -v
```

---

## Дорожная карта

| Этап | Описание | Тесты |
|------|----------|-------|
| 1 | Canon Engine + World Model | 21 |
| 2 | Logic Engine (54 паттерна) | 13 |
| 3 | Exploration Core | 15 |
| 4 | Quality Evaluator (5 критериев) | 7 |
| 5 | Integration (API + Pipeline) | 6 |
| 6 | Frontend (9 блоков UI) | — |
| 7 | WebSocket Real-time | 6 |
| 8 | История в SQLite | 6 |
| 9 | Генерация текста из ветви (LLM) | 4 |
| 10 | Внешние источники | 5 |
| 11 | Глубокое исследование | 6 |
| 12 | Обратная связь | 6 |
| 13 | Оптимизация производительности | 8 |
| 14 | Интеграция со Story Engine | 4 |
| 15 | Экспорт результатов | 4 |
| **Итого** | | **111 тестов** |
