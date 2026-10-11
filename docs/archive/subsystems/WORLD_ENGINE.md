# World Engine — Полная документация

## Дата создания: 20 июля 2026
## Версия: 1.0.0
## Статус: Завершён ✅

---

## 1. Обзор

**World Engine** — вычислимая модель мира книги «Наследие Аркаима». Система способна:
- понимать канон книги
- раскрывать форму мира
- проверять допустимость новых идей
- строить новые истории
- создавать визуализации
- поддерживать исследовательский диалог

---

## 2. Архитектура

```
BookPulse
├── KnowledgeLayer       ✅
├── MeaningLayer         ✅
├── IdentityLayer        ✅
├── MissionLayer         ✅
├── VisualStyleLayer     ✅
├── SceneLayer           ✅
├── NarrativeArcLayer    ✅
├── ExpansionLayer       ✅
├── ScreenplayLayer      ✅
├── WorldEngineLayer     ✅ (старый)
└── WorldEngineLayerV2   ✅ (НОВЫЙ)
    ├── WorldModelExt (547 сущностей, 13 категорий)
    ├── RelationGraph (287 связей, 8 типов)
    ├── FormEngine (55 форм, 11 категорий)
    ├── ConsistencyEngine (5 правил)
    └── ExperienceEngine (10 режимов)
```

---

## 3. Статистика

| Метрика | Значение |
|---------|----------|
| Сущностей мира | 547 |
| Категорий | 13 |
| Связей | 287 |
| Типов связей | 8 |
| Форм | 55 |
| Категорий форм | 11 |
| Правил | 5 |
| Режимов | 10 |
| API эндпоинтов | 10 |
| Тестов | 57 |

---

## 4. Категории мира

| Категория | Количество | Описание |
|-----------|------------|----------|
| philosophy | 268 | Философские концепции |
| language | 134 | Язык и терминология |
| geography | 38 | География мира |
| mythology | 37 | Мифология и символы |
| technologies | 22 | Технологии |
| social_structure | 12 | Социальная структура |
| religion | 10 | Религия |
| rituals | 10 | Ритуалы |
| architecture | 5 | Архитектура |
| civilizations | 4 | Цивилизации |
| daily_life | 3 | Быт |
| climate | 2 | Климат |
| transport | 2 | Транспорт |

---

## 5. Типы связей

| Тип | Количество | Описание |
|-----|------------|----------|
| geographic | 262 | Географические связи |
| historical | 25 | Исторические связи |

---

## 6. Режимы работы

| Режим | Описание |
|-------|----------|
| dialog | Диалог с книгой |
| story | История |
| movie | Фильм |
| quest | Квест |
| game | Игра |
| research | Исследование |
| lesson | Урок |
| timeline | Хронология |
| documentary | Документальный фильм |
| illustration | Иллюстрация |

---

## 7. API Эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/book/world/summary` | Сводка мира |
| POST | `/book/world/search` | Поиск по миру |
| GET | `/book/world/entity/{id}` | Получить сущность |
| GET | `/book/world/entity/{id}/context` | Контекст сущности |
| GET | `/book/world/entity/{id}/visual-prompt` | Визуальный промпт |
| POST | `/book/world/validate` | Проверка консистентности |
| GET | `/book/world/rules` | Правила мира |
| GET | `/book/world/modes` | Режимы работы |
| GET | `/book/world/categories` | Категории мира |
| GET | `/book/world/form-library` | Библиотека форм |

---

## 8. Использование

### Python API

```python
from narrative_engine.world_engine import get_world_engine

# Получить движок
engine = get_world_engine()

# Поиск
results = engine.search("Аркаим")

# Получить сущность
entity = engine.get_entity("region_arkaim")

# Визуальный промпт
prompt = engine.form_engine.generate_visual_prompt("region_arkaim")

# Проверка консистентности
report = engine.consistency.validate_entity(entity)
```

### CLI

```bash
# Поиск
python world_cli.py search "Аркаим"

# Сущность
python world_cli.py entity region_arkaim

# Визуальный промпт
python world_cli.py visual region_arkaim --style cinematic

# Правила
python world_cli.py rules

# Режимы
python world_cli.py modes

# Статистика
python world_cli.py stats
```

### API

```bash
# Сводка
curl http://localhost:8642/book/world/summary

# Поиск
curl -X POST http://localhost:8642/book/world/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Аркаим", "limit": 5}'

# Сущность
curl http://localhost:8642/book/world/entity/region_arkaim

# Визуальный промпт
curl http://localhost:8642/book/world/entity/region_arkaim/visual-prompt?style=cinematic
```

---

## 9. Файловая структура

```
core/CORE/
├── narrative_engine/
│   ├── world_engine.py           # WorldEngine — координатор
│   ├── world_model_ext.py        # Расширенная модель мира
│   ├── world_models.py           # 21 Pydantic-модель
│   ├── relation_models.py        # Модели связей
│   ├── relation_extractor.py     # Извлечение связей
│   ├── form_engine.py            # Движок форм
│   ├── consistency_engine.py     # Проверка консистентности
│   └── experience_engine.py      # 10 режимов работы
├── WORLD_MODEL/
│   ├── ARCHITECTURE.json
│   ├── CIVILIZATIONS.json
│   ├── CLIMATE.json
│   ├── DAILY_LIFE.json
│   ├── GEOGRAPHY.json
│   ├── LANGUAGE.json
│   ├── MYTHOLOGY.json
│   ├── PHILOSOPHY.json
│   ├── RELIGION.json
│   ├── RITUALS.json
│   ├── SOCIAL_STRUCTURE.json
│   ├── TECHNOLOGIES.json
│   └── TRANSPORT.json
├── FORM/
│   ├── architecture.json
│   ├── body_language.json
│   ├── clothes.json
│   ├── colors.json
│   ├── faces.json
│   ├── lighting.json
│   ├── materials.json
│   ├── rituals.json
│   ├── sounds.json
│   ├── textures.json
│   └── weather.json
└── pulse/
    └── layers_world_engine.py    # WorldEngineLayerV2

runtime/
├── world_cli.py                  # CLI интерфейс
├── world_batch.py                # Пакетная обработка
├── world_advanced.py             # Расширенные функции
├── world_performance.py          # Оптимизация
├── world_test_pipeline.py        # Тестирование
├── demo_world_engine.py          # Демонстрация
├── world_engine_demo.html        # Frontend demo
├── world_visualization.html      # Визуализация
├── API_DOCUMENTATION.md          # Документация API
├── integrate_real_data.py        # Интеграция данных
├── export_knowledge_base.py      # Экспорт базы знаний
├── backup_world_engine.py        # Бэкап
└── tests/
    ├── test_world_engine.py
    └── test_world_engine_integration.py

tests/test_visual/               # 25 тестов
```

---

## 10. Тесты

```
tests/test_visual/                     25 passed ✅
tests/test_world_engine.py              6 passed ✅
tests/test_world_engine_integration.py 25 passed ✅
runtime/test_llm.py                     1 passed ✅

Итого: 57 тестов пройдены ✅
```

---

## 11. Дорожная карта

### Краткосрочные планы (Q4 2026)
- [ ] Расширение данных
- [ ] Frontend интеграция
- [ ] LLM интеграция

### Среднесрочные планы (Q1-Q2 2027)
- [ ] Игровой режим
- [ ] Визуализация мира
- [ ] Мультиязычность

### Долгосрочные планы (2027+)
- [ ] Продвинутая аналитика
- [ ] Коллаборативные функции
- [ ] Мобильное приложение

---

## 12. Заключение

Проект **World Engine** успешно завершён. Создана вычислимая модель мира книги «Наследие Аркаима» с полной интеграцией в существующую инфраструктуру.

**Статус: ЗАВЕРШЁН ✅**
