# Обзор проекта «Наследие Аркаима» для ИИ-инженеров

Этот документ предоставляет всесторонний обзор проекта «Наследие Аркаима», предназначенный для ИИ-инженеров, чтобы быстро понять его архитектуру, стек технологий, основные принципы и текущее состояние.

## 1. Общее описание

«Наследие Аркаима» — это цифровое сознание одноименной книги, реализованное как интерактивная система. Главной особенностью проекта является "живое ядро" (BookPulse), которое обладает полным знанием книги без прямой зависимости от больших языковых моделей (LLM). LLM используются в качестве "микрофона" для формулирования ответов, которые затем проходят строгую внутреннюю проверку на соответствие первоисточнику и "личности" книги.

### Ключевые принципы:
- **Книга — первичный источник истины:** Все решения и ответы базируются на содержании книги, а не на возможностях LLM.
- **LLM — инструмент, а не архитектура:** LLM служат для формулирования, но не определяют личность или знание книги.
- **BookPulse знает книгу без LLM:** Каждый слой Pulse способен ответить на вопросы самостоятельно.
- **Никаких автономных действий:** Система предлагает варианты, но окончательное решение всегда за автором.
- **Voice-протокол:** Строгий протокол взаимодействия: Pulse ищет ответ → BookVoice формулирует → Pulse проверяет → IdentityLayer.validate() финальная проверка.

## 2. Архитектура

Проект имеет трехуровневую архитектуру:

**Читатель → Web UI (Next.js :3000) → Gateway/API Proxy → Backend (FastAPI :8642) → BookPulse**

### Компоненты:
- **Web UI (arkaim-web):** Фронтенд на Next.js 16, React 19, Ant Design 6.
- **Mobile (arkaim-mobile):** Мобильное приложение на React Native + Expo.
- **Backend (runtime):** Серверная часть на FastAPI (Python 3.14+) с SQLite и ChromaDB.
- **BookPulse (core):** "Живое ядро" книги, состоящее из нескольких слоев:
    - **KnowledgeLayer (Mutable):** Факты, темы, O(1) индексы + RAG.
    - **ExpansionLayer (Mutable):** Расширенные знания (168 тем).
    - **MeaningLayer (Mutable):** Замысел автора.
    - **IdentityLayer (Immutable):** Самопредставление, границы.
    - **MissionLayer (Immutable):** Миссия книги.
    - **WorldEngineLayerV2 (Mutable):** Вычислимая модель мира книги (547 сущностей, 287 связей).
- **BookVoice:** Модуль, использующий LLM (GigaChat, OpenRouter) для формулирования ответов на основе знаний Pulse.
- **ReaderMemory:** Система памяти читателей для адаптации ответов.
- **World Engine:** Вычислимая модель мира книги, управляющая сущностями и связями.
- **Knowledge Graph:** Графовый движок для поиска и контекстуализации знаний.
- **Knowledge Expansion Pipeline:** Пайплайн для автоматического обогащения знаний.
- **Visualization Pipeline:** Генерация изображений (ComfyUI, SVG, Mock).

### 2.1. Расширенные возможности и генерация контента

Проект «Наследие Аркаима» активно использует AI для динамического развития мира книги и генерации мультимедийного контента:

- **Развитие сюжета и сценариев:** World Engine и Narrative Engine позволяют генерировать новые сюжетные линии, сценарии и "отдельные развития" мира книги, исследуя возможные исходы и вариации на основе существующего генома.
- **Генерация изображений:** Интегрированный Visualization Pipeline (через ComfyUI) способен создавать визуальный контент (изображения) на основе текстовых описаний из книги или динамически генерируемых сценариев.
- **Персонализированный контент:** Система может адаптировать и генерировать контент, включая визуальные элементы, под индивидуальные запросы и профиль читателя.

## 3. Стек технологий

### Бэкенд (Python)
- **Язык:** Python 3.14+
- **Фреймворк:** FastAPI 0.136+
- **Базы данных:** SQLite (для памяти читателей), ChromaDB (векторная БД)
- **Аутентификация:** JWT (HS256), OAuth (Telegram/Google), API Keys
- **LLM-провайдеры:** GigaChat, OpenRouter
- **Генерация изображений:** ComfyUI
- **WebSocket:** Для real-time уведомлений

### Фронтенд (TypeScript)
- **Язык:** TypeScript 5 (strict)
- **Фреймворк:** Next.js 16
- **UI-библиотека:** React 19 + Ant Design 6
- **Стейт-менеджмент:** Zustand + TanStack React Query
- **Стили:** Tailwind CSS 4
- **Тестирование:** Vitest (unit-тесты), Playwright (E2E-тесты)

### Мобильное приложение
- **Фреймворк:** React Native + Expo
- **Навигация:** React Navigation

### Инфраструктура
- **Контейнеризация:** Docker, Docker Compose
- **CI/CD:** GitHub Actions
- **HTTPS:** Cloudflare Tunnel / Tailscale Funnel
- **Мониторинг:** X-Ray Observability

## 4. Структура проекта (ключевые директории)

```
arkaim/
├── arkaim-web/              # Frontend (Next.js, React)
├── arkaim-mobile/           # Mobile (React Native, Expo)
├── runtime/                 # Backend (FastAPI)
│   ├── core/                # Основной код: роуты, провайдеры, сервисы, auth
│   ├── auth/                # OAuth, JWT, RBAC
│   ├── memory/              # Память читателей
│   └── tests/               # Backend тесты
├── core/                    # Ядро знаний (Book Intelligence)
│   ├── CORE/                # Pulse, Voice, World Engine, Knowledge Graph
│   │   ├── pulse/           # Слои Pulse, BookVoice
│   │   ├── narrative_engine/  # World Engine, сюжетный движок
│   │   └── knowledge_graph/   # Граф знаний
│   ├── KNOWLEDGE/          # 40+ JSON-файлов знаний
│   ├── GENOME/             # Геном книги
│   └── CHROMA_DB/          # Векторная БД
├── docs/                    # Документация
├── SCHEMAS/                 # JSON Schema
├── ADR/                     # Architecture Decision Records
├── scripts/                 # Утилиты и скрипты
└── Makefile                 # Универсальные dev-команды
```

## 5. Как запустить Dev-среду

### Быстрый старт (Docker)
```bash
docker compose up --build
```
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://localhost:8642](http://localhost:8642)
- Swagger UI: [http://localhost:8642/docs](http://localhost:8642/docs)

### Локальная разработка
```bash
# Бэкенд
cd runtime
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn core.main:app --port 8642 --reload

# Фронтенд
cd arkaim-web
npm install
npm run dev
```

### Универсальные команды (Makefile)
```bash
make dev          # Запустить backend + frontend
make test         # Запустить все тесты
make lint         # Линтер для backend + frontend
make format       # Форматирование кода
```

## 6. Рекомендации для ИИ-инженеров

- **Всегда следуйте Voice-протоколу:** Никогда не обходите его напрямую. Все ответы на вопросы книги должны идти через Pulse → Voice → Validate.
- **Используйте DI-контейнер:** Для управления зависимостями в FastAPI (`runtime/core/adc_deps.py`).
- **Добавление новой функции:** Последовательность действий описана в `docs/AI_ENGINEER_GUIDE.md` (раздел "Как добавить новую функцию").
- **Избегайте прямых system prompt для LLM:** Личность и знания книги должны исходить из Pulse, а не из инструкций LLM.
- **Обработка ошибок:** Всегда обрабатывайте ошибки, избегайте `except: pass`.