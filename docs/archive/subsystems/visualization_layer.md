# Visualization Layer — документация

## Обзор

Visualization Layer добавлен в проект «Наследие Аркаима» в рамках **Sprint 0**. Это каркас для генерации визуальных образов сцен, персонажей и локаций книги на основе Genome + Pulse + Image Providers.

**Принцип:** никакого LLM для промптов. Всё строится из структурированных данных Genome и Pulse-слоёв.

---

## Архитектура

```
CORE/
└── visualization/
    ├── __init__.py              # Публичный API модуля
    ├── schema.py                # Pydantic-схемы
    ├── visual_genome.py         # CRUD + versioning визуального генома
    ├── scene_engine.py           # Извлечение сцены из Genome + Retriever
    ├── character_visualizer.py   # Визуальная спецификация персонажа
    ├── world_visualizer.py       # Визуальная спецификация локации
    └── prompt_builder.py         # Jinja2-шаблоны промптов

providers/
└── image/
    ├── __init__.py              # ImageProvider + ImageProviderChain
    ├── mock.py                  # Мок-провайдер (SVG placeholder)
    ├── svg_template.py          # SVG-рендеринг без нейросетей
    └── stable_diffusion.py      # Обёртка над SD API (заглушка)

runtime/
├── core/
│   ├── adc_deps.py             # Дependencies: scene_engine, prompt_builder, image_provider
│   └── book_routes.py          # POST /book/visualize endpoint
├── tests/
│   └── test_visualization.py   # Базовые тесты
└── core/memory/
    └── migrations/
        └── 001_initial_schema.sql  # Таблица visual_memory
```

---

## Ключевые компоненты

### 1. SceneEngine (`visualization/scene_engine.py`)

**Назначение:** thin wrapper над Genome + Retriever. Извлекает сцены и визуальные спецификации.

**Методы:**
- `get_scene(chapter, scene_id)` → dict | None
- `get_character_visual(character_id)` → dict | None
- `get_location_visual(location_id)` → dict | None

**Fallback:** если нет готовой визуальной спецификации — строит на основе character/world_entity.

### 2. PromptBuilder (`visualization/prompt_builder.py`)

**Назначение:** собирает промпт для ImageProvider из Scene + CharacterVisuals + Location + VisualStyle.

**Использует:** Jinja2-шаблон `SCENE_TEMPLATE`.

**Пример вывода:**
```
Scene: Встреча у костра
Characters:
  hero: 30 лет, leggins, boots
Environment: forest - pine forest
Atmosphere: intimate, warm
Style: cinematic_fantasy
```

### 3. ImageProvider (`providers/image/`)

Абстракция генерации изображений:

```python
class ImageProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes: ...
    @abstractmethod
    async def health(self) -> bool: ...
```

**Провайдеры:**
- `MockImageProvider` — SVG "Mock Visualization"
- `SVGTemplateProvider` — compositional SVG
- `StableDiffusionProvider` — заглушка под SD API

**Chain:** `ImageProviderChain([MockImageProvider(), SVGTemplateProvider()])` — перебирает провайдеры по здоровью.

### 4. VisualGenomeStore (`visualization/visual_genome.py`)

CRUD + versioning визуального генома. Пока in-memory, потом заменить на SQLite/CHROMA.

- `add_entry(entry)` — добавляет, увеличивает version
- `get_entry(book_id, entity_type, entity_id)` — получить запись
- `invalidate_by_source_hash(book_id, hash)` — инвалидация при изменении Genome

### 5. CharacterVisualizer / WorldVisualizer

Билдят визуальную спецификацию из:
1. Готовых `modules.character_visuals` / `modules.location_visuals`
2. Fallback: `modules.characters` / `world_entities`

### 6. Visual Memory

**Таблица:** `visual_memory` в `readers.db`

| Поле | Тип | Назначение |
|------|-----|-----------|
| reader_id | TEXT | Читатель |
| scene_id | TEXT | Сцена |
| character_id | TEXT | Персонаж (опционально) |
| image_hash | TEXT | Хэш сгенерированного изображения |
| visual_spec_hash | TEXT | Хэш визуальной спецификации |
| cached_until | TEXT | TTL кэша (24ч) |

**Методы:**
- `ReaderMemoryStore.save_visual_memory(...)`
- `ReaderMemoryStore.get_visual_memory(...)`

---

## API

### POST /book/visualize

Генерация сцены.

**Request:**
```json
{
  "chapter": 1,
  "scene_id": "s1",
  "reader_id": "optional_reader_id"
}
```

**Response:**
```json
{
  "prompt": "Scene: ...",
  "image_bytes": "base64_encoded_bytes",
  "content_type": "image/svg+xml"
}
```

**RBAC:** роль `reader`.

---

## Зависимости

### Python пакеты
- `jinja2` — шаблонизация промптов
- `httpx` — для StableDiffusionProvider
- `pydantic` — схемы

### Внутренние модули
- `pulse.layers` — VisualStyleLayer, SceneLayer
- `intelligence.retriever` — BookRetriever (fallback поиск)
- `memory.reader_memory` — Visual Memory

---

## Конфигурация

**Переменные окружения (потенциальные):**
- `VISUALIZATION_PROVIDER` — выбор провайдера (`mock`, `svg`, `sd`)
- `SD_API_URL` — адрес Stable Diffusion API
- `VISUAL_CACHE_TTL` — TTL кэша в секундах

---

## Тестирование

**Файл:** `runtime/tests/test_visualization.py`

**Покрытие:**
- MockImageProvider.generate()
- SceneEngine.get_scene() при пустом геноме
- CharacterVisualizer fallback
- WorldVisualizer fallback
- PromptBuilder дефолтный промпт

**Запуск:**
```bash
cd runtime && python -m pytest tests/test_visualization.py -v
```

---

## Sprint 1 — план

1. **Заполнить Visual Genome**
   - 10 сцен в `GENOME_v1.0.0.json` → `modules.scenes`
   - 3-5 персонажей → `modules.character_visuals`
   - 2-3 локации → `modules.location_visuals`
   - 2-3 style_presets → `modules.style_presets`

2. **Подключить Stable Diffusion**
   - Заглушка в `StableDiffusionProvider.generate()`
   - Реальный вызов `/sdapi/v1/txt2img`

3. **CLI**
   - `scripts/visualize_scene.py` — ручная генерация
   - `scripts/backfill_visuals.py` — массовая генерация

4. **UI**
   - Кнопка в `UI/index.html`
   - Отображение result в модалке

5. **E2E тесты**
   - Тест endpoint /book/visualize
   - Тест кэширования Visual Memory

---

## Известные ограничения

1. **Pylance warnings** — импорты из COREModules работают через `sys.path` hack в `adc_deps.py`. В IDE могут подсвечиваться красным.
2. **SceneEngine** — пока не умеет искать по RAG (Retriever зарезервирован).
3. **VisualGenomeStore** — in-memory, без персистентности.
4. **StableDiffusionProvider** — заглушка, возвращает SVG.

---

## Комментарии

Каркас спроектирован так, чтобы добавление новых провайдеров или слоёв не требовало изменения существующего кода. Достаточно реализовать `ImageProvider` и зарегистрировать в `ImageProviderChain`.