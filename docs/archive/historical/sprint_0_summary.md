# Sprint 0 — Summary (исторический)

> **⚠️ Исторический документ.** Sprint 0 был первым этапом проекта.  
> Сейчас проект значительно расширен: добавлены 15 методов наполнения Visual Genome,  
> Web UI, Voice-ввод, VLM pipeline, авто-заполнение из архетипов/RAG/KG и cron-рефреш.  
> См. актуальное руководство: `docs/visual_genome_guide.md`.

**Дата:** 10.07.2026  
**Цель:** Добавить Visualization Layer в проект «Наследие Аркаима»  
**Статус:** ✅ Завершён (исторический)

---

## Что было сделано

### 1. Genome Schema расширен

Добавлены типы визуальных сущностей:
- `VisualStylePreset` — пресет стиля
- `SceneVisualSpec` — полная спецификация сцены
- `CharacterVisual` — визуальная spec персонажа
- `LocationVisual` — визуальная spec локации

**Файл:** `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/genome/schema.py`

### 2. Pulse Layers добавлены

- `VisualStyleLayer` — отвечает за стилевую составляющую
- `SceneLayer` — отвечает за сцены

**Файл:** `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/pulse/layers.py`

### 3. Visualization модуль создан

```
ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/
├── __init__.py              # Публичный API
├── schema.py                # Pydantic-схемы
├── visual_genome.py         # CRUD + versioning
├── scene_engine.py           # Извлечение сцены из Genome + Retriever
├── character_visualizer.py   # Визуальная spec персонажа
├── world_visualizer.py       # Визуальная spec локации
└── prompt_builder.py         # Jinja2-шаблоны промптов
```

### 4. Image Providers добавлены

```
ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/
├── __init__.py              # ImageProvider + ImageProviderChain
├── mock.py                  # Мок-провайдер (SVG placeholder)
├── svg_template.py          # Композиционный SVG
└── stable_diffusion.py      # Обёртка над SD API
```

### 5. Visual Memory добавлен

- Методы `save_visual_memory` и `get_visual_memory` добавлены в `ReaderMemoryStore`
- Миграция БД: создана таблица `visual_memory` в `runtime/core/memory/migrations/001_initial_schema.sql`
- Кэширование на 24 часа

**Файлы:**
- `runtime/core/memory/reader_memory.py`
- `runtime/core/memory/migrations/001_initial_schema.sql`

### 6. Интеграция в Runtime

- ADC зависимости добавлены в `runtime/core/adc_deps.py`:
  - `get_scene_engine()`
  - `get_prompt_builder()`
  - `get_image_provider()`
- API endpoint добавлен в `runtime/core/book_routes.py`:
  - `POST /book/visualize` (RBAC: reader)
- Тест добавлен: `runtime/tests/test_visualization.py`

---

## Изменённые файлы

| Файл | Что изменено |
|------|-------------|
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/pulse/pulse.py` | Добавлены VisualStyleLayer, SceneLayer в _init_layers |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/pulse/layers.py` | Добавлены VisualStyleLayer, SceneLayer |
| `runtime/core/book_routes.py` | Добавлен POST /book/visualize + модели запроса/ответа |
| `runtime/core/adc_deps.py` | Добавлены зависимости scene_engine, prompt_builder, image_provider |
| `runtime/core/memory/reader_memory.py` | Добавлены save_visual_memory, get_visual_memory |
| `runtime/core/memory/migrations/001_initial_schema.sql` | Добавлена таблица visual_memory |

---

## Созданные файлы

| Файл | Назначение |
|------|-----------|
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/__init__.py` | Публичный API модуля |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/schema.py` | Pydantic-схемы |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/visual_genome.py` | CRUD + versioning визуального генома |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/scene_engine.py` | Thin wrapper над Genome + Retriever |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/character_visualizer.py` | Визуализация персонажей |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/world_visualizer.py` | Визуализация локаций |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/prompt_builder.py` | Jinja2-шаблоны промптов |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/__init__.py` | ImageProvider + ImageProviderChain |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/mock.py` | Мок-провайдер |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/svg_template.py` | SVG-рендеринг |
| `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/stable_diffusion.py` | SD API заглушка |
| `runtime/tests/test_visualization.py` | Базовые тесты |
| `docs/visualization_layer.md` | Документация Visualization Layer |

---

## Проверка

```bash
cd runtime && python -m pytest tests/auth/ tests/test_visualization.py -q
# 69 passed, 3 skipped, 2 warnings
```

---

## Что дальше (Sprint 1)

1. **Заполнить Visual Genome** — 10 сцен + визуальные specs
2. **Подключить Stable Diffusion** — реальный вызов API
3. **CLI** — `scripts/visualize_scene.py`
4. **UI** — кнопка визуализации
5. **E2E тесты** — endpoint /book/visualize + кэширование

---

## Потенциальные риски

- Pylance warnings по импортам — не влияют на runtime, но ухудшают DX
- In-memory VisualGenomeStore — при перезагрузке теряется история
- StableDiffusionProvider — заглушка, требует локальный/удалённый SD сервер