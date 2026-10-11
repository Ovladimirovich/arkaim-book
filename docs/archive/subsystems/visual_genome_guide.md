# Полное руководство по наполнению Visual Genome

> Объединённый документ: базовые способы + автоматические + продвинутые (2026-07-10).

 — часть проекта «Наследие Аркаима». Хранится в `modules` файла `GENOME_v1.0.0.json`. Включает:

- `scenes` — сюжетные сцены (связь персонажей, локаций, эмоций)
- `character_visuals` — визуальные описания персонажей (одежда, цвета, черты)
- `location_visuals` — визуальные описания локаций (архитектура, атмосфера, освещение)
- `style_presets` — стилевые пресеты для генерации изображений

---

## 1. Базовая структура Visual Genome

```
modules/
├── scenes/             # Сюжетные сцены
│   ├── chapter
│   ├── scene_id
│   ├── title
│   ├── characters[]    # ID персонажей
│   ├── location        # ID локации
│   ├── emotion
│   └── meaning_tags[]
├── character_visuals/  # Визуал персонажей
│   ├── character_id
│   ├── age_range
│   ├── build
│   ├── hair
│   ├── eyes
│   ├── clothing
│   ├── accessories[]
│   ├── color_palette[]
│   └── style_constants[]
├── location_visuals/   # Визуал локаций
│   ├── location_id
│   ├── type
│   ├── architecture
│   ├── atmosphere
│   ├── lighting
│   └── palette[]
└── style_presets/      # Стилевые пресеты
    └── {preset_id}
        ├── prompt_suffix
        └── negative_prompt
```

---

## 2. Базовые способы наполнения

### 2.1 Ручное редактирование JSON

Открыть `GENOME/GENOME_v1.0.0.json` и добавить напрямую:

```json
{
  "modules": {
    "scenes": [{
      "chapter": 1, "scene_id": "s1", "title": "Встреча у костра",
      "characters": ["hero", "wise_old"], "location": "arkaim_altar",
      "emotion": "warm_intimate", "meaning_tags": ["знание", "передача"]
    }],
    "character_visuals": [{
      "character_id": "hero", "age_range": "30-35", "build": "athletic",
      "hair": "short brown", "eyes": "green",
      "clothing": "leather armor, cloak", "accessories": ["amulet"],
      "color_palette": ["#8B4513", "#2F4F4F"],
      "style_constants": ["cinematic lighting"]
    }],
    "location_visuals": [{
      "location_id": "arkaim_altar", "type": "ancient_temple",
      "architecture": "stone circles, bronze symbols",
      "atmosphere": "mystical, dawn", "lighting": "golden hour",
      "palette": ["#DAA520", "#8B4513"]
    }],
    "style_presets": {
      "cinematic_fantasy": {
        "preset_id": "cinematic_fantasy",
        "prompt_suffix": "cinematic lighting, epic composition",
        "negative_prompt": "blurry"
      }
    }
  }
}
```

### 2.2 CLI-инструмент `populate_visual_genome.py`

```bash
python scripts/populate_visual_genome.py --scenes scenes.json
python scripts/populate_visual_genome.py --character-visuals character_visuals.json
python scripts/populate_visual_genome.py --location-visuals location_visuals.json
python scripts/populate_visual_genome.py --style-presets style_presets.json
```

Примеры JSON-файлов: `scripts/examples/`.

### 2.3 Скрипт `visualize_scene.py`

```bash
python scripts/visualize_scene.py --chapter 1 --scene s1 --output output/scene.svg
```

Генерирует изображение из уже наполненных данных.

---

## 3. Продвинутые способы (с участием пользователя)

### 3.1 Web UI-форма (`/_ui/visual-genome`)

**Кто:** автор (нетехнический)

В браузере открыть `/_ui/visual-genome`. Три секции:

- **Сцены:** выбор главы → название → персонажи (автокомплит) → локация → эмоция → color picker (5 цветов) → сохранить
- **Персонажи:** выбор персонажа → возраст, одежда, цвета → сохранить
- **Локации:** ID, тип, архитектура, атмосфера, освещение, цвета → сохранить
- **🎤 Голос:** текстовое описание → LLM → структура Visual Genome
- **🖼️ Изображение:** загрузить концепт-арт → распознать

**API:** `POST /book/visual-genome/scene`, `POST /book/visual-genome/character`, `POST /book/visual-genome/location`, `POST /book/visual-genome/from-speech`, `POST /book/visual-genome/from-image`

### 3.2 Голосовой ввод (Voice)

**Кто:** автор (любой)

```python
from pulse.voice import BookVoice
voice = BookVoice(pulse)
await voice.extract_visual_from_speech("Велик в кожаном доспехе у костра на закате")
# → {"scenes": [...], "character_visuals": [...], "location_visuals": [...]}
```

Через Web UI: кнопка 🎤 → описание → LLM → структура → сохранить.

### 3.3 VLM pipeline — Изображение → Visual Genome

**Кто:** автор (любой)

```bash
python scripts/image_to_visual_genome.py concept_art.png --entity-type character --entity-id velik
```

Анализ через GigaChat Vision / OpenRouter vision:
- Распознаёт одежду, цвета, архитектуру, атмосферу
- Извлекает доминантные цвета (PIL)
- Сохраняет в `GENOME/CURRENT/`

### 3.4 Telegram-краудсорсинг

**Кто:** читатели (не автор)

Бот спрашивает: *«Как вы представляете Велика? Опишите внешность»* → собирает ответы → частотный анализ → агрегированный character_visual.

```python
bot = TelegramBotStub()
await bot.poll_visuals("Велик", hours=24)
result = await bot.aggregate_poll_results("Велик")
```

---

## 4. Автоматические методы (без участия пользователя)

### 4.1 LLM-пайплайн — из текста книги

```bash
python scripts/extract_visuals_from_book.py --chapters 1-10
```

Читает `KNOWLEDGE/BOOK_DOCUMENT.json` → разбивает на сцены → GigaChat → структура → `GENOME/CURRENT/`.

### 4.2 MeaningLayer → Scene (Pulse)

Система сама маппит themes/values из genome в:

- `emotion` (14 типов: утрата → melancholic_dark, надежда → bright_warm...)
- `color_palette` (13 палитр с 4 цветами каждая)
- `visual_style_hint` (14 стилей)
- `style_presets` (авто-создание)

Запуск: `python scripts/cron_refresh_visuals.py` или через хук в Pulse.

### 4.3 Из Knowledge Graph

```bash
python scripts/kg_to_visuals.py
```

Обходит GraphEngine: для person → character_visual, для location → location_visual, для conflict_with → Scene с полярными палитрами.

### 4.4 Из RAG-чанков (ChromaDB)

```bash
python scripts/rag_to_visuals.py
```

Сканирует 1037 чанков через regex (одежда, стены, цвет, свет) → группирует по персонажам/локациям → visual.

### 4.5 Из JSON-схем (SCHEMAS)

```bash
python scripts/schemas_to_visuals.py
```

Читает `SCHEMAS/CHARACTER.schema.json`, `ENTITY.schema.json`, `THEME.schema.json` → маппинг в Visual Genome.

### 4.6 Архетипы — наследование

8 архетипов с шаблонами:

| Архетип | Визуальный шаблон |
|---------|------------------|
| Искатель | Лёгкая одежда, земляные тона, открытое лицо |
| Мудрец | Белые/серые одежды, посох, мягкий свет |
| Хранитель | Тёмные тона, закрытая одежда, металл |
| Проводник | Голубые/золотые тона, мерцающие акценты |
| Архат | Минимализм, белый/золотой, нимб/сияние |
| Наставник | Практичные одежды, тёплый свет |
| Лидер | Парадные одежды, эпическое освещение |
| Учёный | Туника, очки, детали |

При добавлении персонажа с archetype → visual создаётся автоматически.

### 4.7 Эволюционный обвес (EvolutionTracker)

Хук в `BookPulse.evolve()`: при каждом обновлении генома проверяет `GenomeDiff.new_characters` → `fill_missing_archetype_visuals()`.

### 4.8 Конфликтные палитры

```python
from visualization.conflict_palettes import generate_all_conflict_scenes
scenes = generate_all_conflict_scenes(genome)
# Полярные цвета для Гиперборея vs Атлантида, Кали-юга vs Сати-юга и т.д.
```

### 4.9 X-Ray data-driven

`XRayVisualTriggers` анализирует вопросы читателей:

- *«Как выглядит Аркаим?»* → отсутствует location_visual → счётчик +1
- При достижении порога (5) → задача через `PresenceSuggester.suggest(action="add_visual")`

---

## 5. Обслуживание и автоматизация

### 5.1 Cron-рефреш

```bash
python scripts/cron_refresh_visuals.py --dry-run --notify
```

Раз в неделю:
1. Сравнить хэш генома с сохранённым
2. Запустить: archetype_visuals → conflict_palettes → meaning_to_visual
3. Проверить отсутствующие visual → создать задачи
4. Отправить дайджест в Telegram

### 5.2 Presence + email

`PresenceSuggester.suggest_missing_visual()` создаёт предложение с action `"add_visual"` и примером JSON. Автор получает email / видит в админке.

---

## 6. Сводная таблица всех методов

| # | Метод | Участие пользователя | Источник | Сложность |
|---|-------|---------------------|----------|-----------|
| 1 | Ручной JSON | Редактирование файла | Автор | Низкая |
| 2 | CLI populate | Запуск скрипта | JSON-файлы | Низкая |
| 3 | visualize_scene | Запуск скрипта | Genome | Низкая |
| 4 | Web UI | Заполнение формы | Автор | Средняя |
| 5 | Voice-ввод | Голос | LLM | Средняя |
| 6 | VLM pipeline | Загрузка изображения | VLM | Высокая |
| 7 | Telegram-краудсорсинг | Опрос читателей | Читатели | Средняя |
| 8 | LLM-пайплайн | Запуск скрипта | GigaChat | Средняя |
| 9 | MeaningLayer | Не требуется | Pulse | Высокая |
| 10 | Knowledge Graph | Не требуется | KG | Средняя |
| 11 | RAG-чанки | Не требуется | ChromaDB | Средняя |
| 12 | SCHEMAS | Не требуется | JSON-схемы | Низкая |
| 13 | Архетипы | Не требуется | CHARACTER | Низкая |
| 14 | EvolutionTracker | Не требуется | Genome | Низкая |
| 15 | Conflict-палитры | Не требуется | KG | Низкая |
| 16 | X-Ray triggers | Не требуется | X-Ray | Средняя |
| 17 | Presence + email | Утверждение | Автор | Низкая |
| 18 | Cron-рефреш | Не требуется | Genome diff | Средняя |

---

## 7. Проверка

```bash
cd runtime && python -m pytest tests/test_visualization.py -v
```

Или через API:

```bash
curl -X POST "http://localhost:8642/book/visualize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chapter": 1, "scene_id": "s1"}'
```

---

## 8. Приоритет для внедрения

**Быстрые победы:** Архетипы → SCHEMAS → Conflict-палитры → эво-хук → Presence

**Интеграции:** MeaningLayer → KG → RAG → X-Ray

**Интерактив:** Web UI → Voice → VLM → Telegram

**Автоматизация:** LLM-пайплайн → Cron-рефреш

---

*Создан 10.07.2026. Объединяет `visual_genome_howto.md` + `visual_genome_advanced_methods.md` + новые модули.*
Visual Genome