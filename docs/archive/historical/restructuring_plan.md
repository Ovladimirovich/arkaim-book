# План реструктуризации проекта «Наследие Аркаима»

> Текущее состояние: разбросан — дубли config, genome, memory, scripts, schemas.
> Цель: чистая иерархия без дублей.

---

## Текущие проблемы

| Проблема | Где |
|----------|-----|
| Два genome | `ADC/CORE/genome/` и `runtime/core/genome/` |
| Два memory | `ADC/CORE/memory/`, `ADC/CORE/core_memory/`, `runtime/memory/` |
| Два config | `ADC/CORE/config.py` и `runtime/shared_config.py` |
| Два SCHEMAS | `SCHEMAS/` и `ADC/SCHEMAS/` |
| Два scripts | `scripts/` и `ADC/scripts/` |
| Два TESTS | `runtime/tests/` и `ADC/TESTS/` |
| Два runtime | `runtime/` и `ADC/runtime/` |
| Два telegram | `ADC/CORE/community/telegram.py` и `runtime/integrations/` |
| Файлы в корне CORE | 15 `.py` файлов на уровне `CORE/` вместо пакетов |
| Папка `ai/` | Аналитика AI, не по месту |

---

## Целевая структура

```
arkaim/
├── core/                  # Ядро — всё, что не зависит от FastAPI
│   ├── pulse/             # Pulse — живое ядро
│   │   ├── pulse.py, layers.py, evolution.py, voice.py
│   │   └── __init__.py
│   ├── genome/            # Геном — схемы, экстрактор, валидатор
│   │   ├── schema.py, extractor.py, validator.py
│   │   └── __init__.py
│   ├── visualization/     # Визуализация
│   │   ├── prompt_builder, scene_engine, archetype_visuals,
│   │   │   conflict_palettes, meaning_to_visual, xray_triggers
│   │   └── providers/     # ImageProvider, ComfyUI, SD, Mock
│   │       ├── comfyui.py, stable_diffusion.py, mock.py
│   │       └── __init__.py
│   ├── knowledge_graph/   # Граф знаний
│   │   └── graph_engine.py, api_routes.py, populate.py
│   ├── intelligence/      # RAG, ретривер, ядро знаний
│   ├── agents/            # Keeper, Herald, Diplomat
│   ├── presence/          # Observer, Suggester
│   ├── community/         # Telegram, VK
│   ├── memory/            # Память (единственная)
│   └── config.py          # Единый конфиг
│
├── server/                # FastAPI — всё, что зависит от веб-фреймворка
│   ├── main.py            # Точка входа
│   ├── core/              # Маршруты, зависимости, менеджеры
│   │   ├── book_routes.py, ui_routes.py, adc_deps.py
│   │   ├── auth.py, pulse_manager.py
│   │   └── ...
│   ├── templates/         # Jinja2 шаблоны
│   ├── static/            # CSS, JS
│   └── memory/            # Только runtime-память (SQLite store)
│
├── scripts/               # CLI-инструменты — единая папка
│   ├── populate_visual_genome.py
│   ├── extract_visuals_from_book.py
│   ├── rag_to_visuals.py, kg_to_visuals.py
│   ├── schemas_to_visuals.py
│   ├── cron_refresh_visuals.py
│   ├── visualize_scene.py
│   └── examples/
│
├── data/                  # Данные — неизменяемые + сгенерированные
│   ├── GENOME/            # Геном JSON + workflows
│   ├── KNOWLEDGE/         # Исходные данные книги
│   ├── CHROMA_DB/         # Векторная БД
│   ├── SCHEMAS/           # JSON-схемы (один экземпляр)
│   └── OS_DATA/           # Runtime-данные (чат, опросы)
│
├── docs/                  # Документация
│   ├── visual_genome_guide.md
│   ├── comfyui_guide.md
│   └── ...
│
├── config/                # Конфигурация
│   └── project.yaml
│
├── tests/                 # Все тесты в одном месте
│   ├── test_pulse.py
│   ├── test_genome.py
│   ├── test_visual_*.py
│   ├── test_genome_narrative.py
│   └── ...
│
├── start.bat              # Запуск
├── stop.bat               # Остановка
├── README.md
└── ARCHITECTURE.md
```

---

## Пошаговый план миграции

### Шаг 1: Удалить явные дубли

```
Удалить:
├── ARKAIM_DIGITAL_CONSCIOUSNESS/SCHEMAS/        ← дубль корневых SCHEMAS/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CONFIG/          ← project.yaml, перенести
├── ARKAIM_DIGITAL_CONSCIOUSNESS/scripts/         ← дубль корневых scripts/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/TESTS/           ← дубль runtime/tests/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/runtime/         ← дубль корневого runtime/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/UI/              ← дубль runtime/templates/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/core_memory/ ← дубль CORE/memory/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/memory/     ← хлам (analyzer = 1 строка)
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/generator.py ← мёртвый код
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/email_sender.py ← мёртвый код
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/hermes_client.py ← мёртвый код
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/chatpdf_client.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/chatpdf_setup.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/check_genome_quality.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/refine_genome.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/service_auto_recovery.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/status_report.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/synopsis_reader.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/ui_serve.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/telegram_bot.py.old
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/book_genome.py   ← верхний уровень
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/book_intelligence.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/book_reader.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/book_understanding.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/book_world.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/run*.py
├── ARKAIM_DIGITAL_CONSCIOUSNESS/start.bat
├── runtime/core/genome/                              ← дубль
├── runtime/integrations/                             ← дубли telegram
├── ai/                                               ← перенести в docs/
├── test_*.py *.ps1 в корне
├── qc в корне
└── test_clean_visuals.json
```

### Шаг 2: Перенести core/genome в единый genome

```
Переместить:
ADC/CORE/genome/ → core/genome/
  ├── schema.py
  ├── extractor.py
  ├── validator.py
  └── __init__.py

Удалить:
runtime/core/genome/  ← полный дубль
```

### Шаг 3: Слить config

```
Взять runtime/shared_config.py как базовый
Добавить поля из ADC/CORE/config.py (GENOME_DIR, KNOWLEDGE_DIR etc.)
Удалить ADC/CORE/config.py
Переименовать runtime/shared_config.py → core/config.py
Обновить все import: from config import config
```

### Шаг 4: Слить memory

```
ADC/CORE/memory/analyzer.py     → удалить (1 строка)
ADC/CORE/memory/logger.py       → удалить (1 строка)
ADC/CORE/memory/__init__.py     → удалить
ADC/CORE/core_memory/analyzer.py → перенести в core/memory/analyzer.py
ADC/CORE/core_memory/logger.py   → перенести в core/memory/logger.py
ADC/CORE/core_memory/__init__.py → обновить
runtime/memory/store.py          → оставить в server/memory/
runtime/memory/leads.py          → оставить в server/memory/
```

### Шаг 5: Перенести верхнеуровневые файлы CORE/ в пакеты

```
book_genome.py      → перенести логику в genome/extractor.py
book_intelligence.py → перенести в intelligence/kernel.py
book_reader.py       → перенести в intelligence/reader.py
book_understanding.py → перенести в pulse/layers.py (MeaningLayer уже там)
book_world.py        → перенести в knowledge_graph/world.py
```

### Шаг 6: Переименовать ARKAIM_DIGITAL_CONSCIOUSNESS → core

```
ARKAIM_DIGITAL_CONSCIOUSNESS/  →  core/
Обновить пути в:
  - start.bat, stop.bat
  - scripts/*.py
  - runtime/core/adc_deps.py
  - runtime/core/main.py (импорт Orchestrator)
```

### Шаг 7: Перенести ImageProviders в visualization/providers/

```
ADC/CORE/providers/image/  →  core/visualization/providers/
```

Уже логически там — просто исправить import paths.

### Шаг 8: Собрать tests в одном месте

```
runtime/tests/  →  tests/
Обновить конфиги pytest
```

---

## Итоговая структура (без мусора)

```
arkaim/
├── core/
│   ├── __init__.py
│   ├── config.py              ← единый
│   ├── pulse/
│   ├── genome/
│   ├── visualization/
│   │   └── providers/
│   ├── knowledge_graph/
│   ├── intelligence/
│   ├── agents/
│   ├── presence/
│   ├── community/
│   ├── memory/
│   └── llm_client.py
│
├── server/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   ├── templates/
│   ├── static/
│   ├── memory/
│   └── .venv/
│
├── scripts/
├── data/
│   ├── GENOME/
│   ├── KNOWLEDGE/
│   ├── CHROMA_DB/
│   ├── SCHEMAS/
│   └── OS_DATA/
│
├── docs/
├── tests/
├── config/
│   └── project.yaml
│
├── start.bat
├── stop.bat
├── ARCHITECTURE.md
└── README.md
```

---

## Риски

| Риск | Митигация |
|------|-----------|
| Сломаются import-ы при переименовании ADC → core | Все импорты типа `from config import config` → заменить на `from core.config import config`. Скрипт `sed` по всем `.py` |
| `adc_deps.py` использует `_lazy_import` с абсолютными именами `providers.image` | Обновить пути в `_lazy_import` вызовах |
| `Orchestrator` импортирует `from memory.store` | Обновить на `from server.memory.store` |
| Pulse через sys.path лезет в CORE | Убрать sys.path, импортировать через `from core.pulse import BookPulse` |

### Порядок выполнения (чтобы не сломать)

1. Сначала убить дубли-файлы (не папки)
2. Потом merge config (самый критичный)
3. Потом merge genome
4. Потом rename ADC → core
5. В конце — удалить старые папки

После каждого шага: `python -m pytest tests/ -x` — чтобы не накапливать ошибки.
