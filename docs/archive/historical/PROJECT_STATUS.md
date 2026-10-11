# Статус проекта «Наследие Аркаима»

> Дата: 16.07.2026
> Статус: Активная разработка

---

## Общая статистика

| Метрика | Значение |
|---------|----------|
| Страницы фронтенда | **29** |
| Роуты бэкенда | **195** |
| Сервисы DI (ServiceRegistry) | **16** |
| Провайдеры LLM | **2** (GigaChat, OpenRouter) |
| Провайдеры изображений | **3** (ComfyUI, SVG, Mock) |
| AI-агенты | **3** (Keeper, Herald, Diplomat) |
| Слои Pulse | **8** (+ ExpansionLayer) |
| Модули обогащения | **11** |
| Тесты бэкенд | **104+** |
| Тесты фронтенд | **30** |
| Файлы знаний | **40+** JSON |
| Тем в ExpansionLayer | **168** |

---

## Бэкенд (runtime/)

### Ядро — 20 модулей

| Модуль | Назначение | Статус |
|--------|-----------|--------|
| main.py | FastAPI app, lifespan, 195 роутов | ✅ |
| adc_deps.py | ServiceRegistry — 16 синглтонов через DI | ✅ |
| bootstrap.py | sys.path hack | ✅ Deprecated |
| orchestrator.py | Оркестрация запросов Voice | ✅ |
| database.py | DatabaseManager + connection pooling | ✅ |
| migration_engine.py | SQLite миграции (transactional, checksums) | ✅ |
| pulse_manager.py | Управление Pulse + ReaderAwarePulse | ✅ |
| auth.py | Auth middleware (Bearer → cookie → API key) | ✅ |
| websocket.py | ConnectionManager + 7 типов уведомлений | ✅ |
| provider_registry.py | Реестр LLM + circuit breaker | ✅ |
| config.py | Конфигурация | ✅ |
| middleware.py | Rate limiting, protected routes | ✅ |
| book_routes.py | Book intelligence роуты | ✅ |
| presence_manager.py | Presence (книга наблюдает) | ✅ |
| analytics.py | Агрегированная аналитика | ✅ |
| retry.py | Retry logic | ✅ |
| ui_routes.py | Web UI (Jinja2 + HTMX) | ✅ |
| logging.py | Структурированное логирование | ✅ |
| tools.py | Утилиты | ✅ |
| services/registry.py | ServiceRegistry | ✅ |

### Роуты — 5 роутеров

| Роутер | Эндпоинты |
|--------|-----------|
| UI Router | /_ui/* (book, about, profile, upload, admin) |
| Auth Router | /auth/* (login, register, admin/users, admin/invites) |
| Book Router | /book/* (ask, genome, layers, chapters, text, screenplay, visual-*) |
| Crowdfunding Router | /book/crowdfunding/* (status, campaign, history, config) |
| Community Router | /book/community/* (interpretations, artifacts, map-data, timeline, knowledge/*) |

### Провайдеры LLM

| Провайдер | Статус |
|-----------|--------|
| GigaChat (OAuth2) | ✅ Primary |
| OpenRouter (API key) | ✅ Fallback |

### Провайдеры изображений

| Провайдер | Статус | Описание |
|-----------|--------|----------|
| ComfyUI | ✅ Primary | Локальная генерация (требует GPU) |
| SVG Template | ✅ Fallback | Векторные шаблоны |
| Mock | ✅ Fallback | Заглушки |

### Аутентификация

| Модуль | Статус |
|--------|--------|
| routes.py (15+ эндпоинтов) | ✅ |
| users.py (aiosqlite + миграции) | ✅ |
| rbac.py (reader/editor/admin) | ✅ |
| tokens.py (JWT HS256) | ✅ |
| api_keys.py | ✅ |
| oauth/telegram.py | ✅ |
| oauth/google.py | ⚠️ Недоступен в РФ |

### Тесты

| Директория | Проходят |
|------------|----------|
| tests/ (root) | ✅ 30 файлов |
| tests/auth/ | ✅ 68 тестов |
| tests/new/ | ✅ 5 файлов |
| tests/test_providers.py | ✅ 29 тестов |
| tests/test_service_registry.py | ✅ 7 тестов |
| tests/test_crowdfunding.py | ✅ |

---

## Фронтенд (arkaim-web/)

### Стек

| Пакет | Версия |
|-------|--------|
| Next.js | 16.2.10 |
| React | 19.2.4 |
| Ant Design | ^6.5.0 |
| @tanstack/react-query | ^5.101.2 |
| Zustand | ^5.0.14 |
| TypeScript | ^5 |
| Vitest | ^4.1.10 |

### Страницы (29)

| Страница | Путь | Статус |
|----------|------|--------|
| Главная | / | ✅ |
| Задать вопрос | /ask | ✅ |
| Чат с книгой | /book | ✅ |
| Чтение | /reading | ✅ |
| Сценарий | /screenplay | ✅ |
| Библиотека | /library | ✅ |
| Жанры | /genres | ✅ |
| Визуал | /visual-view | ✅ |
| Редактор | /editor | ✅ |
| О книге | /about | ✅ |
| Поиск | /search | ✅ |
| Профиль | /profile | ✅ |
| Рекомендации | /recommendations | ✅ |
| История | /history | ✅ |
| Краудфандинг | /crowdfunding | ✅ |
| Аналитика | /analytics | ✅ |
| Уведомления | /notifications | ✅ Live-лента + WebSocket |
| API | /api | ✅ |
| Настройки | /settings | ✅ |
| Загрузка | /upload | ✅ |
| Визуалы | /visual | ✅ |
| Админ | /admin | ✅ CRUD + инвайты |
| X-Ray | /xray | ✅ |
| Вход | /login | ✅ |
| Регистрация | /register | ✅ |
| Помощь | /help | ✅ |
| **Карта** | /map | ✅ НОВАЯ — Leaflet + хронология |
| **Интерпретации** | /interpretations | ✅ НОВАЯ — читатели |
| **Артефакты** | /artifacts | ✅ НОВАЯ — находки |

---

## Ядро знаний (core/CORE/)

### Pulse — 8 слоёв

| Слой | Тип | Назначение |
|------|-----|-----------|
| KnowledgeLayer | Mutable | Факты, темы, O(1) индексы + RAG |
| **ExpansionLayer** | **Mutable** | **Расширенные знания (168 тем)** |
| MeaningLayer | Mutable | Замысел автора, 76 посланий |
| IdentityLayer | Immutable | Самопредставление, forbidden words |
| MissionLayer | Immutable | Миссия, предназначение |
| VisualStyleLayer | Mutable | Визуальные стили |
| SceneLayer | Mutable | Описания сцен |
| NarrativeArcLayer | Mutable | Дуги персонажей |

### AI-агенты

| Агент | Назначение |
|-------|-----------|
| KeeperAgent | Хранитель — отвечает на вопросы |
| HeraldAgent | Глашатай — генерирует контент |
| DiplomatAgent | Дипломат — личные сообщения |

### Knowledge Expansion Pipeline

| Компонент | Назначение |
|-----------|-----------|
| pipeline.py | Оркестратор пайплайна |
| extractors/ | Извлечение знаний |
| enrichers/ | LLM-обогащение |
| linkers/ | Связывание с графом |
| validators/ | Проверка формата |
| store/ | Хранение в JSON |
| modules/ | 11 модулей обогащения |
| scheduler.py | Авто-обогащение (24ч) |
| expansion_loader.py | Загрузчик для ExpansionLayer |
| llm_client.py | LLM-клиент (GigaChat) |

### Интеллект — 7 модулей

| Модуль | Назначение |
|--------|-----------|
| kernel.py | KnowledgeKernel (dense: 2123 чанка) |
| chunker.py | SemanticChunker (6 режимов) |
| enricher.py | GenomeEnricher |
| retriever.py | BookRetriever + rerank |
| cleaner.py | TextCleaner |
| nameresolver.py | NameResolver |
| character_profiler.py | Профили персонажей |

### ReaderProfile + Adaptive Responses

| Компонент | Назначение |
|-----------|-----------|
| reader_profile.py | Расширенный профиль (уровень, стиль, интересы) |
| adapt_response() | Адаптация ответов под профиль |

### Визуализация — 10 модулей

| Модуль | Назначение |
|--------|-----------|
| schema.py | Pydantic модели |
| prompt_builder.py | Промпты для генерации |
| scene_engine.py | Извлечение сцен |
| character_visualizer.py | Персонажи |
| world_visualizer.py | Мир |
| archetype_visuals.py | 15 архетипов |
| conflict_palettes.py | 4 палитры конфликтов |
| meaning_to_visual.py | 15 эмоций → стили |
| visual_genome.py | VisualGenomeStore |
| xray_visual_triggers.py | X-Ray триггеры |

### Knowledge Graph

| Компонент | Назначение |
|-----------|-----------|
| GraphEngine | BFS, path, subgraph, context |
| Populate | Наполнение из генома |
| API | /book/graph/* |

**Типы сущностей:** 13 | **Типы связей:** 18

### Сообщество

| Модуль | Назначение |
|--------|-----------|
| crowdfunding.py | Парсинг Planeta/Boomstarter |
| crowdfunding_api.py | REST API |
| interpretations.py | Интерпретации читателей |
| artifacts.py | Артефакты читателей |
| community_api.py | REST API (20+ эндпоинтов) |
| telegram.py | Telegram бот |
| telegram_notifications.py | Уведомления |
| vk.py | VK интеграция |

---

## База знаний — 40+ файлов

### Оригинальные знания

| Файл | Размер | Назначение |
|------|--------|-----------|
| enriched_chunks.json | 1.41 MB | Обогащённые чанки (2123) |
| SYNOPSIS_DOCUMENT.json | 858 KB | Синопсис |
| BOOK_DOCUMENT.json | 774 KB | Полный текст |
| enriched_catalog.json | 538 KB | Каталог |
| character_profiles.json | 71 KB | Профили |
| PHILOSOPHY.json | 44 KB | 106 концепций |
| AUTHOR_INTENT.json | 19 KB | 77 посланий |
| VALUES.json | 18 KB | 57 ценностей |

### Расширенные знания (Knowledge Expansion)

| Файл | Тем | Описание |
|------|-----|----------|
| THEMES_DEEP.json | 15 | Глубокий анализ тем (3 уровня) |
| THEMES_EXPANDED.json | 14 | Расширенные темы |
| SYMBOLS_EXPANDED.json | 14 | Символы с «эхами» в культурах |
| CROSS_REFERENCES.json | 7 | Параллели с мировыми легендами |
| ARCHAEOLOGY.json | 10 | Археологические памятники |
| ESOTERIC_CONNECTIONS.json | 10 | Изотерические традиции |
| SCENE_PROMPTS.json | 12 | Промпты для генерации сцен |
| ARCHETYPES_EXPANDED.json | 15 | Расширенные архетипы |
| EPOCH_PALETTES.json | 6 | Палитры эпох |
| MAP_DATA.json | 10 | Данные для карты |
| MEANING_TREE.json | 5 | Дерево смыслов |
| ANCHOR_QUOTES.json | 16 | Цитаты-якоря |
| QUESTIONS_FOR_READER.json | 15 | Вопросы для читателя |
| COSMOLOGY.json | 24 | Космология (юги) |
| GEOGRAPHY.json | 22 | География |
| PSYCHOLOGY.json | 26 | Психология персонажей |
| LANGUAGE.json | 135 | Язык и терминология |
| RITUALS.json | 11 | Ритуалы и практики |
| TECHNOLOGY.json | 23 | Технологии гипербореев |

### Академические подтверждения

| Файл | Категорий | Описание |
|------|-----------|----------|
| ACADEMIC_CONFIRMATIONS.json | 6 | Потоп, Атлантида, Белые бородатые, Космология, Иерархия, Энергетика |
| THEMES_DEEP.json | +1 | Океания = Атлантида |
| THEMES_DEEP.json | +1 | От Атлантиды к Аркаиму |

---

## Изображения

| Ассет | Количество | Описание |
|-------|-----------|----------|
| Сцены | 12 | scene_01.jpg — scene_12.jpg |
| API | ComfyUI (локально/Colab) | Локальная генерация, требyет GPU |

---

## ExpansionLayer — 168 тем

### Ключевые темы с академическими подтверждениями:

| Тема | Культуры |
|------|----------|
| Океания = Атлантида | Греция, Египет, Индия, Ирландия |
| Белые бородатые люди | Ацтеки, Майя, Инки, Шумер, Вавилон |
| Космология (юги) | Индия, Греция, Иран, Скандинавия, Китай, Египет |
| Иерархия Света | Индия, Тибет, Ислам, Христианство, Египет, Греция |
| Духовное преображение | Мифология, Алхимия, Индия, Египет, Дзен, Христианство |
| Энергетика мест | Кельты, Египет, Китай, Славянство, Индия, Греция |

---

## Что сделано (15-16.07.2026)

### Фаза 1 — Стабилизация ✅
- ServiceRegistry: 16 синглтонов
- bootstrap.py cleaned
- GraphEngine: 1 экземпляр через DI
- MigrationEngine работает
- Gateway тесты удалены
- 29 новых тестов providers

### Фаза 2 — Функциональность ✅
- WebSocket LiveFeedPanel (7 событий)
- RAG dense mode: 2123 чанка
- Краудфандинг страница + router

### Раскрытие книги (5 направлений) ✅
- 13+ JSON-файлов знаний
- ExpansionLayer: 168 тем
- LLM интеграция (GigaChat)
- Auto-enrichment по расписанию

### ReaderProfile + Adaptive Responses ✅
- Уровень читателя (novice → expert)
- Стиль обучения
- Интересы и вовлечённость
- Адаптация ответов

### Interactive Map + Timeline ✅
- Страница /map с Leaflet
- Хронология от 7000 до н.э.

### Community ✅
- Интерпретации читателей
- Артефакты читателей
- Связь Океания/Атлантида → Аркаим

---

## Следующие шаги

| Приоритет | Описание | Статус |
|-----------|----------|--------|
| Discussion Threads | Обсуждения тем книги | ❌ Не начато |
| Cross-Reference Engine | Автопоиск связей | ❌ Не начато |
| Redis Caching | Кеш ответов Pulse | ❌ Не начато |
| Telegram Bot 2.0 | Бот с расширенными знаниями | ❌ Не начато |
