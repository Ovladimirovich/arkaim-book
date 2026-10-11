# Состояние проекта «Наследие Аркаима»

Этот документ отражает объективное состояние проекта на основе анализа кодовой базы, структуры и функциональности. Он предназначен для ИИ-инженеров и разработчиков.

## 1. Общая архитектура и реализация

Проект реализован как трехуровневая система:

**Читатель → Web UI (Next.js :3000) → Gateway/API Proxy → Backend (FastAPI :8642) → BookPulse**

### Реализованные компоненты:

#### 1.1. Frontend (arkaim-web)
- **Next.js 16** с App Router
- **React 19** + **Ant Design 6** для UI компонентов
- **TypeScript 5** в strict режиме
- **Tailwind CSS 4** для стилей
- **Zustand** + **TanStack React Query** для state management
- **34 страницы** включая:
  - Основные: ask, book, library, settings
  - Специализированные: film-studio, world-engine, world-explorer, visual, visual-view
  - Социальные: profile, notifications, history, recommendations
  - Административные: admin, xray, upload
- **Тесты:** Vitest (unit), Playwright (E2E)

#### 1.2. Mobile (arkaim-mobile)
- **React Native + Expo**
- **React Navigation** для навигации
- Экраны: admin, chat, history, login, notifications, profile, reading, search
- Shared API и типы данных

#### 1.3. Backend (runtime)
- **FastAPI 0.136+** с асинхронной обработкой
- **SQLite** (aiosqlite) для данных читателей и сессий
- **ChromaDB** для векторного поиска
- **JWT** аутентификация (HS256)
- **OAuth**: Telegram, Google
- **API Keys** для программного доступа
- **WebSocket** для real-time уведомлений
- **219+ API роутов** по префиксам:
  - `/book/*` — основные эндпоинты книги
  - `/auth/*` — аутентификация и авторизация
  - `/api/*` — управление API ключами
  - `/xray/*` — observability
  - `/_ui/*` — Web UI (Jinja2 + HTMX)

#### 1.4. Core — BookPulse (ядро знаний)
**Реализовано 6 слоев Pulse:**
- **KnowledgeLayer** — факты, темы, RAG, O(1) индексы
- **ExpansionLayer** — расширенные знания (168 тем)
- **MeaningLayer** — замысел автора
- **IdentityLayer** — самопредставление, границы (Immutable)
- **MissionLayer** — миссия книги (Immutable)
- **WorldEngineLayerV2** — вычислимая модель мира (547 сущностей, 287 связей)

**Подсистемы Core:**
- **BookVoice** — LLM как микрофон (GigaChat, OpenRouter)
- **World Engine** — narrative_engine с полным циклом:
  - world_model, world_state, world_delta
  - scenario_modeler, branch_manager, story_from_branch
  - consistency_engine, contradiction_detector, canon_validator
  - deep_explorer, hypothesis_generator
  - form_engine (FORM/боди-язык/одежда/цвета/свет/материалы/ритуалы/звуки/текстуры/погода)
  - unified_pipeline, pipeline_errors
- **Knowledge Graph** — graph_engine с BFS, shortest path, populate
- **Knowledge Expansion Pipeline** — 11 модулей обогащения знаний:
  - expansion_loader, llm_client, pipeline, scheduler
  - enrichers, extractors, linkers, modules, store, validators
- **Intelligence** — RAG, chunker, retriever, cleaner, enricher, nameresolver, character_profiler
- **Visualization Pipeline** — генерация изображений:
  - ComfyUI провайдер
  - prompt_composer, prompt_templates
  - visual_context_builder, visual_validator
  - atmosphere_engine, camera_engine, character_visual_engine
  - location_engine, symbol_engine
  - continuity_engine, continuity_state
- **Film Studio** — модуль для создания визуальных сцен:
  - shot_assembler, schemas, store
- **Community** — социальные функции:
  - telegram_notifications, vk, email
  - crowdfunding, crowdfunding_api
  - artifacts, comments, interpretations
- **Presence** — наблюдение и предложения автору:
  - observer, suggester, email_sender, telegram_presence
- **Core Memory** — память читателей:
  - reader_profile, store, analyzer, leads, logger
- **Agents** — агентная система:
  - base agent, keeper

## 2. Данные и знания

### 2.1. KNOWLEDGE/ — 50+ JSON файлов
- **Персонажи:** CHARACTERS.json, character_profiles.json, character_deep_profiles.json, deep_characters.json
- **Темы:** THEMES.json, THEMES_EXPANDED.json
- **Символы:** SYMBOLS.json, SYMBOLS_EXPANDED.json, SYMBOLS_DEEP.json
- **Архетипы:** ARCHETYPES_EXPANDED.json
- **Место и время:** GEOGRAPHY.json, MAP_DATA.json, EPOCH_PALETTES.json
- **Сюжет:** PLOT.json, SYNOPSIS_DOCUMENT.json, SYNOPSIS_PROFILE.json
- **Философия:** PHILOSOPHY.json, PHILOSOPHY_DEEP.json
- **Психология:** PSYCHOLOGY.json
- **Ритуалы:** RITUALS.json
- **Технологии:** TECHNOLOGY.json
- **Язык:** LANGUAGE.json
- **Космология:** COSMOLOGY.json, COSMOLOGY_DEEP.json
- **Археология:** ARCHAEOLOGY.json, ARCHAEOLOGY_DEEP.json
- **Энергия мест:** ENERGY_OF_PLACES.json
- **Значения:** VALUES.json
- **Цитаты:** ANCHOR_QUOTES.json
- **Перекрестные ссылки:** CROSS_REFERENCES.json, CROSS_REFERENCES_DEEP.json
- **Academic подтверждения:** ACADEMIC_CONFIRMATIONS.json
- **Book Genome:** BOOK_GENOME.json, BOOK_DOCUMENT.json, BOOK_PROFILE.json
- **Enriched данные:** enriched_catalog.json, enriched_chunks.json
- **Сценарии:** SCENE_PROMPTS.json, screenplay_extracts.json
- **Другие:** HIERARCHY_OF_LIGHT.json, ESOTERIC_CONNECTIONS.json, PATTERNS.json, MEANING_TREE.json, QUESTIONS_FOR_READER.json

### 2.2. GENOME/ — Геном книги
- **extractor.py** — извлечение генома из книги
- **schema.py** — схема генома
- **validator.py** — валидация генома
- **history/** — история версий генома

### 2.3. SCHEMAS/ — JSON Schema
- CHARACTER.schema.json
- ENTITY.schema.json
- QUOTE.schema.json
- THEME.schema.json

## 3. Технологический стек

### Backend (Python)
- **Язык:** Python 3.14+
- **Фреймворк:** FastAPI 0.110+
- **Сервер:** Uvicorn с расширенными возможностями
- **Базы данных:**
  - SQLite (aiosqlite) — для памяти читателей, сессий
  - ChromaDB — векторная БД для семантического поиска
- **Аутентификация:**
  - JWT (python-jose с cryptography)
  - OAuth: Telegram, Google
  - API Keys
- **LLM интеграция:**
  - sentence-transformers для эмбеддингов
  - GigaChat
  - OpenRouter
- **Обработка документов:**
  - pdfplumber, pdfminer.six — извлечение из PDF
  - python-multipart — загрузка файлов
- **HTTP клиент:** httpx
- **Тестирование:** pytest, pytest-asyncio
- **Линтинг:** ruff
- **Управление конфигурацией:** python-dotenv

### Frontend (TypeScript/React)
- **Язык:** TypeScript 5 (strict)
- **Фреймворк:** Next.js 16
- **UI:** React 19 + Ant Design 6
- **Стили:** Tailwind CSS 4
- **State:** Zustand + TanStack React Query
- **Тесты:** Vitest, Playwright
- **Линтинг:** ESLint
- **Форматирование:** Prettier

### Mobile (React Native)
- **Фреймворк:** React Native + Expo
- **Навигация:** React Navigation
- **State:** Context API + hooks

### Инфраструктура
- **Контейнеризация:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Мониторинг:** X-Ray Observability (aethon.xray встроен в репозиторий)
- **HTTPS:** Cloudflare Tunnel / Tailscale Funnel
- **Базы данных:** SQLite, ChromaDB

## 4. Функциональные возможности

### 4.1. Взаимодействие с книгой
- **Вопросы и ответы** через Voice-протокол:
  - Pulse ищет ответ в слоях
  - BookVoice формулирует ответ через LLM
  - Pulse.verify() проверяет соответствие
  - IdentityLayer.validate() финальная проверка
- **Адаптивные ответы** под профиль читателя
- **Поиск** — гибридный поиск (keyword + semantic)
- **Recommendations** — рекомендации на основе чтения

### 4.2. World Engine
- **547 сущностей** мира книги
- **287 связей** между сущностями
- **BFS/Shortest Path** графовые алгоритмы
- **Сценарии** — генерация возможных исходов
- **Ветвление** — branch_manager для альтернативных сюжетных линий
- **Валидация** — проверка на противоречия с каноном
- **Form Engine** — 11 аспектов визуального описания мира

### 4.3. Генерация контента
- **Визуализация:**
  - Генерация изображений через ComfyUI
  - Prompt composer и templates
  - Character visualizer, location engine, atmosphere engine
- **Film Studio:**
  - Создание сцен
  - Shot assembler
  - Сборка визуальных элементов
- **Расширенные знания:**
  - 168 тем расширенных знаний
  - Автоматическое обогащение через LLM
  - Модульная пайплайн система

### 4.4. Социальные функции
- **Community:**
  - Артефакты, комментарии, интерпретации
  - Crowdfunding API
- **Notifications:**
  - Telegram, VK, Email
- **Reader Memory:**
  - Профили читателей
  - Адаптация контента
  - Exploration store, feedback store

### 4.5. Администрирование
- **Admin Panel** — управление системой
- **User Management** — управление пользователями
- **API Key Management** — ключи доступа
- **Draft Approval** — утверждение черновиков
- **Invite System** — приглашения
- **Analytics** — аналитика использования
- **X-Ray Dashboard** — observability

### 4.6. Ввод и обработка данных
- **Загрузка документов** — PDF, текстовые файлы
- **Извлечение знаний** — автоматическое извлечение из книги
- **Ревью и коррекция** — интерфейс для автора
- **Pipeline обработки** — полный цикл от сырого текста до знаний

## 5. Скрипты автоматизации

### 5.1. Обработка книги
- **extract_visuals_from_book.py** — извлечение визуальных описаний
- **full_pipeline.py** — полный пайплайн индексации
- **clean_genome_values.py** — очистка генома
- **fix_vlad_archetype.py** — исправление архетипов

### 5.2. Генерация визуалов
- **generate_scenes.py** — базовая генерация сцен
- **generate_scenes_comfyui.py** — генерация сцен через ComfyUI
- **populate_visual_genome.py** — заполнение визуального генома
- **schemas_to_visuals.py** — конвертация схем в визуалы
- **image_to_visual_genome.py** — из изображений в геном
- **kg_to_visuals.py** — из графа знаний в визуалы
- **rag_to_visuals.py** — из RAG в визуалы
- **visualize_scene.py** — визуализация конкретной сцены

### 5.3. Обслуживание
- **health_check.py** — проверка здоровья сервисов
- **cron_refresh_visuals.py** — периодическое обновление визуалов
- **cron_reindex.py** — периодическая реиндексация
- **load_test.py** — нагрузочное тестирование

### 5.4. Запуск
- **start_all.bat** — запуск всех сервисов
- **start_core.bat** — запуск только backend
- **start_frontend.bat** — запуск только frontend
- **stop_all.bat** — остановка всех сервисов
- **stop-arkaim-services.ps1** — остановка через PowerShell
- **run-all.ps1** — запуск через PowerShell

## 6. API роуты (runtime/core/routes/)

### 6.1. Основные эндпоинты
- **book.py** — `/book/*` — ask, genome, layers, world
- **world_engine.py** — `/book/world/*` — World Engine API
- **visual.py** — `/book/visual/*` — визуализация
- **reader.py** — `/book/reader/*` — работа с читателями

### 6.2. Film Studio
- **film_studio.py** — `/film-studio/*` — создание фильмов/сцен

### 6.3. Assets
- **assets.py** — `/assets/*` — загрузка и управление файлами

## 7. Voice-протокол (архитектурный паттерн)

```
Вопрос читателя
    ↓
Pulse (pulse/pulse.py, layers.py)
    ├── KnowledgeLayer → факты из генома (без LLM)
    ├── ExpansionLayer → 168 тем (без LLM)
    ├── MeaningLayer → замысел автора (без LLM)
    ├── IdentityLayer → границы самопредставления (Immutable)
    └── MissionLayer → миссия книги (Immutable)
    ↓
BookVoice (pulse/voice.py)
    ├── Если уверенность Pulse ≥ порог → ответ без LLM
    └── Если уверенность низкая → LLM формулирует ответ
    ↓
Pulse.verify() — проверка ответа LLM на соответствие книге
    ↓
IdentityLayer.validate() — финальная проверка
```

## 8. Принципы разработки (соблюдаются)

1. **Книга — первичный источник истины** — все ответы из книги, не из LLM
2. **LLM — инструмент, не архитектура** — LLM только для формулирования
3. **Pulse знает книгу без LLM** — каждый слой может ответить сам
4. **Никаких автономных действий** — система предлагает, автор решает
5. **DI-контейнер** — все зависимости через adc_deps.py
6. **Обработка ошибок** — никогда `except: pass`
7. **Секреты только через .env** — никогда в коде
8. **API-first** — сначала API, потом UI
9. **Проверка перед созданием** — проверить Pulse/layers/ перед новым модулем

## 9. Тестирование

### Backend
- **pytest** с async поддержкой
- **349+ тестов** покрытия
- Модульное и интеграционное тестирование

### Frontend
- **Vitest** для unit-тестов
- **Playwright** для E2E
- **30+ тестов**

## 10. Документация

### Структура docs/
- **AI_ENGINEER_GUIDE.md** — руководство для ИИ-инженеров
- **ARCHITECTURE.md** — архитектурная документация
- **WORLD_ENGINE.md** — документация World Engine
- **WORLD_EXPLORER.md** — руководство по World Explorer
- **DEPLOY.md** — инструкции деплоя
- **KNOWLEDGE_BASE.md** — база знаний
- **KNOWLEDGE_EXPANSION.md** — расширение знаний
- **PROJECT_STATUS.md** — статус проекта
- **visualization_layer.md** — визуализация
- **comfyui_guide.md** — руководство по ComfyUI
- **plan_sprint2.md** — планы спринтов

## 11. CI/CD

- **GitHub Actions** — автоматизация
- **Branch protection:** main требует passing CI
- **Docker images:** автоматическая сборка для main
- **Registry:** GitHub Container Registry (ghcr.io)
- **Commit format:** conventional commits

## 12. Текущее состояние

### Реализовано и работает:
- Полнофункциональный backend на FastAPI
- Frontend на Next.js с 34 страницами
- Mobile приложение на React Native
- BookPulse с 6 слоями
- World Engine с 547 сущностями
- Knowledge Graph с графовыми алгоритмами
- Knowledge Expansion Pipeline с 168 темами
- Visualization Pipeline (ComfyUI)
- Film Studio модуль
- Community функции (Telegram, VK, Email)
- Reader Memory и адаптация
- Authentication (JWT, OAuth, API Keys)
- Full-text и семантический поиск
- Admin панель
- X-Ray observability
- Docker Compose для dev/prod
- CI/CD через GitHub Actions
- umprehensive тестовое покрытие

### Ключевые метрики:
- **Сущностей мира:** 547
- **Связей:** 287
- **Форм визуализации:** 55
- **Страниц интерфейса:** 34
- **Слоёв Pulse:** 6 (Mutable/Immutable)
- **API эндпоинтов:** 219+
- **Тестов:** 349+ (backend) + 30 (frontend)
- **Модулей обогащения:** 11
- **Тем расширенных знаний:** 168
- **JSON файлов знаний:** 50+

## 13. Возможности для ИИ-инженера

При работе с проектом ИИ-инженер может:
1. **Добавлять новые знания** в KNOWLEDGE/JSON файлы
2. **Создавать новые слой Pulse** для дополнительных типов знаний
3. **Расширять World Engine** новыми механиками
4. **Генерировать визуальный контент** через Visualization Pipeline
5. **Создавать новые сценарии** через World Engine
6. **Развивать сообщество** через Community модули
7. **Настраивать LLM провайдеров** для новых моделей
8. **Добавлять новые роуты API** с сохранением Voice-протокола
9. **Расширять мобильное приложение** новыми экранами
10. **Интегрировать новые источники** данных

## 14. Ключевые файлы для разработки

- **core/config.py** — центральная конфигурация
- **runtime/core/adc_deps.py** — DI-контейнер
- **runtime/core/main.py** — точка входа FastAPI
- **core/CORE/pulse/pulse.py** — BookPulse ядро
- **core/CORE/pulse/layers.py** — слои Pulse
- **core/CORE/pulse/voice.py** — BookVoice
- **core/CORE/narrative_engine/world_engine.py** — World Engine
- **core/CORE/knowledge_graph/graph_engine.py** — граф знаний
- **core/CORE/intelligence/retriever.py** — RAG
- **runtime/core/routes/book.py** — основные роуты
- **arkaim-web/src/shared/lib/api.ts** — HTTP клиент
- **docs/AI_ENGINEER_GUIDE.md** — руководство по разработке