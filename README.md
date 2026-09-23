# 🏛️ Наследие Аркаима — Цифровое сознание книги

> **Цифровое представительство книги «Наследие Аркаима» (ОВладимирович).**
> Живое ядро (Pulse) знает книгу без LLM, использует AI только как голос.

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![CI/CD](https://github.com/Ovladimirovich/arkaim/actions/workflows/ci.yml/badge.svg)](https://github.com/Ovladimirovich/arkaim/actions/workflows/ci.yml)

---

## 📋 Содержание

- [О проекте](#о-проекте)
- [Архитектура](#архитектура)
- [Стек технологий](#стек-технологий)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [API](#api)
- [Тестирование](#тестирование)
- [Развёртывание](#развёртывание)
- [Вклад в проект](#вклад-в-проект)
- [Лицензия](#лицензия)

---

## О проекте

**«Наследие Аркаима»** — это цифровое сознание одноимённой книги. Система построена вокруг **Аватара Книги** — живого ядра (Pulse), которое:

- ✅ **Знает книгу без LLM** — отвечает на фактические вопросы напрямую
- ✅ **Использует LLM только как микрофон** — формулирует то, что уже знает
- ✅ **Помнит каждого читателя** — адаптирует ответы под уровень и интересы
- ✅ **Наблюдает и предлагает** — видит, что обсуждают читатели, и предлагает автору
- ✅ **Растёт без потери себя** — версионирование генома, иммутабельные слои

### Ключевые метрики

| Метрика | Значение |
|---------|----------|
| Сущностей мира | **547** |
| Связей между сущностями | **287** |
| Форм визуализации | **55** |
| Страниц интерфейса | **34** |
| Слоёв Pulse | **10** (+ ExpansionLayer) |
| API эндпоинтов | **219** |
| Тестов | **349+** (backend) + **30** (frontend) |
| Модулей обогащения знаний | **11** |
| Тем расширенных знаний | **168** |

---

## Архитектура

```
Читатель → Web UI (Next.js :3000) → API Proxy → Backend (FastAPI :8642)
                                                          │
                                                 ┌───────┴────────┐
                                                 │    BookPulse    │
                                                 │  (живое ядро)   │
                                                 │ ┌─────────────┐ │
                                                 │ │KnowledgeLayer│ │
                                                 │ │ MeaningLayer │ │
                                                 │ │IdentityLayer │ │
                                                 │ │ MissionLayer │ │
                                                 │ └─────────────┘ │
                                                 │    BookVoice     │
                                                 │  (LLM-микрофон)  │
                                                 │   ReaderMemory   │
                                                 │   World Engine   │
                                                 └─────────────────┘
```

### Слои Pulse

| Слой | Тип | Назначение |
|------|-----|-----------|
| KnowledgeLayer | Mutable | Факты, темы, O(1) индексы + RAG |
| ExpansionLayer | Mutable | Расширенные знания (168 тем) |
| MeaningLayer | Mutable | Замысел автора |
| IdentityLayer | Immutable | Самопредставление, границы |
| MissionLayer | Immutable | Миссия книги |
| WorldEngineLayerV2 | Mutable | Вычислимая модель мира |

### Подсистемы

- **World Engine** — вычислимая модель мира книги (547 сущностей, 287 связей)
- **Knowledge Expansion Pipeline** — авто-обогащение знаний через LLM
- **Knowledge Graph** — графовый движок с BFS, shortest path, контекстом для RAG
- **ReaderProfile + Adaptive Responses** — адаптация под читателя
- **Presence** — наблюдение + предложения автору
- **Visualization Pipeline** — генерация изображений (ComfyUI)

---

## Стек технологий

### Бэкенд

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.14+ |
| Фреймворк | FastAPI 0.136+ |
| База данных | SQLite + ChromaDB (векторная) |
| Аутентификация | JWT (HS256), OAuth Telegram/Google, API Keys |
| LLM | GigaChat, OpenRouter |
| Генерация изображений | ComfyUI, SVG, Mock |
| WebSocket | Real-time уведомления |

### Фронтенд

| Компонент | Технология |
|-----------|-----------|
| Язык | TypeScript 5 |
| Фреймворк | Next.js 16 |
| UI | React 19 + Ant Design 6 |
| Стейт-менеджмент | Zustand + TanStack React Query |
| Тесты | Vitest + Playwright |
| Стили | Tailwind CSS 4 |

### Мобильное приложение

| Компонент | Технология |
|-----------|-----------|
| Фреймворк | React Native + Expo |
| Навигация | React Navigation |

### Инфраструктура

| Компонент | Технология |
|-----------|-----------|
| Контейнеризация | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| HTTPS | Cloudflare Tunnel / Tailscale Funnel |
| Мониторинг | X-Ray Observability |

---

## Быстрый старт

### Локальный запуск

```bash
# Клонировать репозиторий
git clone https://github.com/Ovladimirovich/arkaim.git
cd arkaim

# Запустить всё сразу (backend + frontend + браузер)
start_all.bat

# Или по отдельности:

# Бэкенд (порт 8642)
cd runtime
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn core.main:app --port 8642

# Фронтенд (порт 3000)
cd arkaim-web
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
```

Откройте [http://localhost:3000](http://localhost:3000) в браузере.

---

## Структура проекта

```
arkaim/
├── arkaim-web/              # Фронтенд (Next.js + React + Ant Design)
│   ├── src/
│   │   ├── app/            # Страницы (34 шт.)
│   │   ├── shared/         # UI-компоненты, хуки, типы
│   │   ├── entities/       # Бизнес-сущности
│   │   ├── features/       # Фичи
│   │   └── widgets/        # Виджеты (Sidebar, AdminPanel и др.)
│   └── tests/              # Frontend тесты
│
├── arkaim-mobile/           # Мобильное приложение (React Native + Expo)
│   └── src/
│       ├── screens/        # Экраны
│       └── navigation/     # Навигация
│
├── runtime/                 # Бэкенд (FastAPI)
│   ├── core/               # Основной код (роуты, провайдеры, сервисы)
│   ├── auth/               # Аутентификация (OAuth, JWT, RBAC)
│   ├── bot/                # Telegram / VK боты
│   ├── memory/             # Память читателей (SQLite)
│   ├── tests/              # Backend тесты
│   └── prompts/            # Системные промпты
│
├── core/                    # Ядро знаний (Book Intelligence)
│   ├── CORE/
│   │   ├── pulse/          # BookPulse (слои, голос, эволюция)
│   │   ├── narrative_engine/  # World Engine, сюжетный движок
│   │   ├── knowledge_graph/  # Граф знаний
│   │   ├── intelligence/   # Интеллект (RAG, chunker, retriever)
│   │   ├── visualization/  # Визуализация (промпты, сцены)
│   │   └── knowledge_expansion/  # Пайплайн расширения знаний
│   ├── KNOWLEDGE/          # База знаний (40+ JSON-файлов)
│   ├── GENOME/             # Геном книги
│   └── CHROMA_DB/          # Векторная БД
│
├── docs/                    # Документация
│   ├── PROJECT_STATUS.md   # Статус проекта
│   ├── WORLD_EXPLORER.md   # World Explorer
│   └── images/             # Изображения
│
├── scripts/                 # Скрипты (очистка, генерация)
├── SCHEMAS/                 # JSON Schema
├── ADR/                     # Architecture Decision Records
│
├── docker-compose.yml       # Docker Compose
├── Dockerfile.backend       # Dockerfile для бэкенда
├── Dockerfile.frontend      # Dockerfile для фронтенда
├── .github/workflows/ci.yml # CI/CD Pipeline
│
├── README.md                # Этот файл
├── CHANGELOG.md             # История изменений
├── CONTRIBUTING.md          # Гайд для контрибьюторов
├── LICENSE                  # MIT License
├── docs/ARCHITECTURE.md     # Подробная архитектура
├── docs/DEPLOY.md           # Инструкция по деплою
```

---

## API

Бэкенд предоставляет **219 роутов** на следующих префиксах:

| Префикс | Описание |
|---------|----------|
| `/book/*` | Основные эндпоинты книги (ask, genome, layers, world) |
| `/auth/*` | Аутентификация (login, register, admin) |
| `/api/*` | API ключи |
| `/xray/*` | X-Ray observability |
| `/_ui/*` | Web UI (Jinja2 + HTMX) |

Swagger-документация доступна по адресу: [http://localhost:8642/docs](http://localhost:8642/docs)

---

## Тестирование

### Бэкенд

```bash
cd runtime
pytest tests/ -q                          # Все тесты
pytest tests/test_world_engine.py -v      # World Engine тесты
pytest tests/ -k "auth" -v                # Auth тесты
```

### Фронтенд

```bash
cd arkaim-web
npx vitest run              # Unit-тесты
npx playwright test         # E2E-тесты
```

---

## Развёртывание

Подробная инструкция — в [docs/DEPLOY.md](docs/DEPLOY.md).

### Варианты:
1. **Cloudflare Tunnel** (бесплатно, рекомендую) — HTTPS за 5 минут
2. **Docker Compose** — для продакшена
3. **Render.com** — автоматический деплой из GitHub

---

## 🤖 AI Engineer Guide

Для ИИ-инженеров, работающих с проектом из IDE.

**Самое главное:**
1. **Voice-протокол** — Pulse ищет ответ → BookVoice формулирует → Pulse проверяет → IdentityLayer.validate()
2. **Книга — первичный источник истины** — никогда не опирайтесь на возможности LLM
3. **DI-контейнер** — через `runtime/core/adc_deps.py` (ServiceRegistry)

| Быстрый старт | |
|---|---|
| Frontend | http://localhost:3000 | `cd arkaim-web && npm run dev` |
| Backend | http://localhost:8642 | `cd runtime && uvicorn core.main:app --port 8642` |
| Swagger UI | http://localhost:8642/docs | Interactive API docs |
| Все сразу | — | `docker compose up --build` |

**Команды:** `make dev`, `make test`, `make lint`

Подробнее — в [AI Engineer Guide](docs/AI_ENGINEER_GUIDE.md) и [AGENTS.md](AGENTS.md).

---

## 📚 Вклад в проект

См. [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🪪 Лицензия

Проект распространяется под лицензией **MIT**. См. [LICENSE](LICENSE).

