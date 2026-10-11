# Проект «Наследие Аркаима» — обзор и проделанная работа

**Дата:** 10.07.2026  
**Текущий спринт:** Sprint 0 завершён  
**Цель проекта:** Создание цифрового сознания книги «Наследие Аркаима» с возможностями AI-коммуникации, управления знаниями и визуализации сцен.

---

## Архитектура проекта

```
c:\ПРОЕКТ Наследие Аркаима/
├── ARKAIM_DIGITAL_CONSCIOUSNESS/
│   ├── CORE/
│   │   ├── genome/                 # Genome: схемы, экстрактор, валидатор
│   │   ├── pulse/                  # Pulse: живое ядро, слои сознания
│   │   ├── visualization/          # Visualization: сцены, персонажи, визуальный геном
│   │   ├── intelligence/           # Retriever: RAG-поиск по книге
│   │   ├── memory/                 # Логирование событий, X-Ray
│   │   ├── agents/                 # Агенты: Keeper, Herald, Diplomat
│   │   ├── providers/              # LLM providers: GigaChat, Image providers
│   │   └── community/              # Telegram, notifications
│   ├── run_api.py                  # DEPRECATED standalone API
│   └── UI/                         # Веб-интерфейс
├── runtime/
│   ├── core/
│   │   ├── main.py                 # Hermes Core Runtime: FastAPI app
│   │   ├── book_routes.py          # Book Intelligence API endpoints
│   │   ├── adc_deps.py             # ADC зависимости: Pulse, Voice, SceneEngine, Providers
│   │   ├── memory/
│   │   │   ├── reader_memory.py    # Память читателей + Visual Memory
│   │   │   └── migrations/         # Миграции БД
│   │   └── tests/                  # Тесты runtime
│   ├── auth/                       # Auth, RBAC, OAuth Telegram
│   ├── gateway/                    # API Gateway
│   └── docs/                       # Документация
├── docs/                           # Проектная документация
└── scripts/                        # Скрипты запуска, загрузки, тестов
```

---

## Что было сделано

### Фундамент (до Sprint 0)

1. **Book Intelligence API** — `/book/ask`, `/book/genome`, `/book/layers`
2. **Pulse** — живое ядро книги: Genome → Layers → Context → LLM
3. **Pulse Layers** — KnowledgeLayer, MeaningLayer, IdentityLayer, MissionLayer
4. **Agents** — Keeper, Herald, Diplomat
5. **Reader Memory** — профили читателей, темы, история вопросов
6. **Auth & RBAC** — editor, reader, admin
7. **Telegram Bot** — интеграция с Telegram

### Sprint 0 — Visualization Layer

**Цель:** Добавить каркас для генерации визуальных образов сцен, персонажей и локаций.

#### Создано:

**Модули Visualization:**
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/__init__.py`
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/schema.py` — Pydantic-схемы
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/visual_genome.py` — CRUD + versioning
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/scene_engine.py` — извлечение сцен
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/character_visualizer.py` — визуал персонажей
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/world_visualizer.py` — визуал локаций
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/visualization/prompt_builder.py` — Jinja2-шаблоны

**Image Providers:**
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/__init__.py` — ImageProvider + ImageProviderChain
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/mock.py` — мок-провайдер
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/svg_template.py` — SVG-рендеринг
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/providers/image/stable_diffusion.py` — SD API wrapper

**Интеграция:**
- `runtime/core/adc_deps.py` — добавлены зависимости scene_engine, prompt_builder, image_provider
- `runtime/core/book_routes.py` — добавлен POST /book/visualize
- `runtime/core/memory/reader_memory.py` — добавлены save_visual_memory, get_visual_memory
- `runtime/core/memory/migrations/001_initial_schema.sql` — добавлена таблица visual_memory

**Тесты:**
- `runtime/tests/test_visualization.py` — базовые тесты

**Документация:**
- `docs/visualization_layer.md` — документация Visualization Layer
- `docs/sprint_0_summary.md` — итог Sprint 0

#### Проверка:

```bash
cd runtime && python -m pytest tests/auth/ tests/test_visualization.py -q
# 69 passed, 3 skipped, 2 warnings
```

---

## Текущее состояние

### Работает:
- ✅ Pulse: загрузка Genome, живой цикл, автологирование
- ✅ Book Intelligence API: ask, genome, layers
- ✅ Reader Memory: профили, темы, история
- ✅ Visualization Layer: каркас сценариев, промпты, провайдеры
- ✅ API endpoint /book/visualize
- ✅ Visual Memory: кэширование на 24ч

### Не подключено / заглушки:
- ⏳ Genome сценами — пока пустой
- ⏳ Stable Diffusion — заглушка SVG
- ⏳ RAG для сцен — Retriever зарезервирован
- ⏳ VisualGenomeStore — in-memory, без персистентности

---

## API Endpoints

### Public
- `GET /book/health` — статус API
- `GET /book/` — информация о сервисе
- `GET /book/genome` — общая информация о геноме (темы, персонажи, ценности)
- `GET /book/layers` — активные слои сознания

### Защищённые (требуют авторизацию)

**Reader:**
- `POST /book/ask` — задать вопрос книге
- `GET /book/drafts` — получить черновики
- `GET /book/reader/profile` — профиль читателя
- `GET /book/reader/context` — контекст читателя
- `POST /book/visualize` — визуализация сцены

**Editor:**
- `POST /book/generate` — генерация контента (черновики)
- `POST /book/drafts/{draft_id}/approve` — одобрить черновик
- `POST /book/telegram/message` — обработать Telegram сообщение

**Admin:**
- `GET /book/memory/stats` — статистика памяти
- `GET /book/xray` — X-Ray анализ
- `GET /book/reader/stats` — статистика читателей

---

## Стек технологий

### Backend
- **Python 3.10+**
- **FastAPI** — веб-фреймворк
- **GigaChat (СберAI)** — LLM провайдер
- **ChromaDB** — векторное хранилище для RAG
- **aiosqlite** — асинхронная SQLite

### Frontend
- HTML/CSS/JS (index.html)
- Fetch API для коммуникации с Core Runtime

### Infra
- **Docker / docker-compose** — не используется в текущей версии
- **GitHub Actions** — load testing
- **Pytest** — тестирование

---

## Конфигурация

### Переменные окружения

| Переменная | Назначение | Значение по умолчанию |
|------------|------------|----------------------|
| `GIGACHAT_CREDENTIALS` | Ключ GigaChat | — |
| `GENOME_VERSION` | Версия генома | `1.0.0` |
| `XRAY_MODE` | Режим X-Ray | `disabled` |
| `VISUALIZATION_PROVIDER` | Провайдер визуализации | `mock` |
| `SD_API_URL` | URL Stable Diffusion | `http://localhost:7860` |

**Файлы конфигурации:**
- `runtime/.env.template`
- `runtime/.env.example`
- `ARKAIM_DIGITAL_CONSCIOUSNESS/CORE/config.py`

---

## Тестирование

### Запуск всех тестов

```bash
cd runtime && python -m pytest tests/ -v
```

### Запуск визуализации

```bash
cd runtime && python -m pytest tests/test_visualization.py -v
```

### Load testing

```bash
cd runtime && python -m pytest tests/ -k load -v
# или через GitHub Actions
```

---

## Sprint 1 — план

### 1. Данные Visual Genome
- [ ] Заполнить `GENOME_v1.0.0.json`:
  - 10 сцен → `modules.scenes`
  - 3-5 персонажей → `modules.character_visuals`
  - 2-3 локации → `modules.location_visuals`
  - 3 style_presets → `modules.style_presets`

### 2. Stable Diffusion Provider
- [ ] Реальный вызов `/sdapi/v1/txt2img`
- [ ] Обработка ошибок, fallback на Mock/SVG
- [ ] Конфигурация через переменные окружения

### 3. CLI инструменты
- [ ] `scripts/visualize_scene.py` — ручная генерация
- [ ] `scripts/backfill_visuals.py` — массовая генерация

### 4. UI интеграция
- [ ] Кнопка «Визуализировать» на странице сцены
- [ ] Модальное окно с результатом
- [ ] Кэширование на клиенте

### 5. E2E тесты
- [ ] Тест POST /book/visualize
- [ ] Тест Visual Memory кэширования

---

## Потенциальные риски

1. **Pylance warnings** — импорты через `sys.path` hack. В IDE подсвечиваются красным, но работают в runtime.
2. **In-memory VisualGenomeStore** — теряется при перезагрузке. Нужна персистентность.
3. **Stable Diffusion** — требует локальный сервер или GPU. Нет облачного фоллбека.
4. **Visual Memory** — кэш 24ч, но нет очистки устаревших записей.

---

## Документация

- `docs/README.md` — индекс документации
- `docs/project_overview.md` — обзор проекта и архитектуры
- `docs/visual_genome_guide.md` — полное руководство по наполнению Visual Genome (18 методов)
- `docs/visualization_layer.md` — детали реализации Visualization Layer
- `docs/sprint_0_summary.md` — итог Sprint 0 (исторический)
- `ARCHITECTURE.md` — общая архитектура системы
- `ARKAIM_DIGITAL_CONSCIOUSNESS/DEVELOPER_GUIDE.md` — гайд для разработчиков

---

## Команда

Разработка: Cline (AI Assistant)  
Задача: Sprint 0 — Visualization Layer  
Дата: 10.07.2026