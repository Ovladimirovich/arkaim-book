# AGENTS.md — Руководство для ИИ-инженеров

Этот файл содержит краткое руководство для ИИ-агентов (Kilo, Claude Code, GitHub Copilot) о работе с проектом **«Наследие Аркаима»**.

## Обзор проекта

**Что это:** Цифровое сознание книги «Наследие Аркаима» — система с «живым ядром» (Pulse), которое знает книгу без LLM, используя AI только как голос.

**Архитектура:**
```
Читатель → Web UI (Next.js:3000) → Gateway/API Proxy → Backend (FastAPI:8642)
                                                              │
                                    ┌─────────────────────────┴────────┐
                                    │  BookPulse (живое ядро)           │
                                    │  ├─ KnowledgeLayer (Mutable)      │ — факты, RAG
                                    │  ├─ ExpansionLayer  (Mutable)      │ — 168 тем
                                    │  ├─ MeaningLayer    (Mutable)      │ — замысел автора
                                    │  ├─ IdentityLayer    (Immutable)    │ — самопредставление
                                    │  ├─ MissionLayer     (Immutable)    │ — миссия
                                    │  └─ WorldEngineLayerV2 (Mutable)   │ — вычислимая модель
                                    │  BookVoice (LLM-микрофон)           │
                                    │  ReaderMemory + World Engine       │
                                    └─────────────────────────────────────┘
```

## Структура проекта

```
arkaim/
├── arkaim-web/              # Frontend — Next.js 16 + React 19 + Ant Design 6
├── arkaim-mobile/           # Mobile — React Native + Expo
├── runtime/                 # Backend — FastAPI 0.136 + SQLite
│   ├── core/                # Основной код: роуты, провайдеры, сервисы, auth
│   ├── auth/                # OAuth (Telegram, Google), JWT, RBAC
│   ├── bot/                 # Telegram + VK боты
│   ├── memory/              # Память читателей (SQLite)
│   ├── tests/               # Backend тесты
│   └── requirements.txt
├── core/                    # Ядро знаний (Book Intelligence)
│   ├── CORE/                # Pulse, Voice, World Engine, Knowledge Graph
│   │   ├── pulse/           # Слои Pulse, BookVoice
│   │   ├── narrative_engine/  # World Engine, сюжетный движок
│   │   ├── knowledge_graph/   # Граф знаний
│   │   ├── intelligence/     # RAG, chunker, retriever
│   │   ├── visualization/     # Визуализация
│   │   └── knowledge_expansion/ # Пайплайн обогащения знаний
│   ├── KNOWLEDGE/          # 40+ JSON-файлов знаний
│   ├── GENOME/             # Геном книги
│   └── CHROMA_DB/          # Векторная БД
├── docs/                    # Документация
├── SCHEMAS/                 # JSON Schema
├── ADR/                     # Architecture Decision Records
├── scripts/                 # Утилиты и скрипты
├── notebooks/               # Jupyter ноутбуки
├── Dockerfile.backend       # Docker для бэкенда
├── Dockerfile.frontend      # Docker для фронтенда
├── docker-compose.yml       # Локальная разработка
├── .github/workflows/ci.yml # CI/CD (GitHub Actions)
├── pyproject.toml           # Настройки ruff, pytest
├── Makefile                 # Универсальные dev-команды
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                  # MIT
```

## Как запустить dev-среду

### Быстрый старт (Docker)
```bash
docker compose up --build
```
- Frontend: http://localhost:3000
- Backend: http://localhost:8642
- Swagger UI: http://localhost:8642/docs

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
make clean        # Очистка кэша и артефактов
```

## Тестирование

### Backend (pytest)
```bash
cd runtime
python -m pytest tests/ -v
# Или через Makefile:
make test-backend
```

### Frontend (vitest)
```bash
cd arkaim-web
npx vitest run
# Или через Makefile:
make test-frontend
```

## Линтеры

### Backend (ruff)
```bash
cd runtime
ruff check .
ruff format .
# Или:
make lint-backend
make format-backend
```

### Frontend (eslint)
```bash
cd arkaim-web
npm run lint
# Или:
make lint-frontend
```

## Ключевые файлы и паттерны

### Центральная конфигурация
- `core/config.py` — основной конфиг проекта (все env-переменные)
- `runtime/core/adc_deps.py` — FastAPI зависимости и DI-контейнер (ServiceRegistry)

### Архитектурные принципы (НЕ нарушать)
1. **Книга — первичный источник истины.** Никакие решения не основаны на возможностях LLM.
2. **LLM — инструмент, не архитектура.** Личность книги — в Pulse, а не в system prompt.
3. **Pulse знает книгу без LLM.** Каждый слой может ответить на вопрос сам.
4. **Никаких автономных действий.** Система предлагает — автор решает.
5. **Voice-протокол:** Pulse ищет ответ → если уверенность высокая, отдаёт без LLM → если низкая, LLM формулирует, Pulse проверяет → IdentityLayer.validate() финальная проверка.

### Роуты API
- `/book/*` — основные эндпоинты книги (ask, genome, layers, world)
- `/auth/*` — аутентификация
- `/api/*` — управление API ключами
- `/xray/*` — observability
- `/_ui/*` — Web UI (Jinja2 + HTMX)

### Где добавлять новый функционал
1. Проверить, не реализует ли слой Pulse нужное
2. Создать Pydantic-схему в `SCHEMAS/`
3. Создать модуль в `core/CORE/` или `runtime/core/`
4. Добавить Dependency в `runtime/core/adc_deps.py`
5. Добавить роут в `runtime/core/routes/`
6. Добавить тесты
7. Обновить документацию

## Что НЕЛЬЗЯ делать
- ❌ Давать LLM system prompt, который заставляет «быть книгой»
- ❌ Создавать новый модуль, не проверив Pulse/layers/
- ❌ Делать автономных действий (публикации, рассылки)
- ❌ Читать книгу через код прежде, чем создать обработчик
- ❌ Подключать UI прежде, чем создать API
- ❌ Добавлять секреты в код — только через `.env`
- ❌ Использовать `except: pass` — обязательна обработка ошибок

## Правила кодстайла
- **Python:** 3.14+, type hints, async/await для I/O, Pydantic для валидации, snake_case, ruff (line-length: 160), один модуль = одна ответственность
- **TypeScript/React:** TS 5+ (strict), FSD архитектура, React Server Components, ESLint + Tailwind

## Инструменты разработки
- **Kilo CLI** — AI-агент для ассистентного программирования. Команды в `.kilo/command/`, агенты в `.kilo/agent/`
- **ruff** — линтер и форматтер Python
- **eslint** — линтер TypeScript
- **pytest** — тестирование Python
- **vitest** — тестирование frontend

## Полезные ссылки
- [Swagger UI (локально)](http://localhost:8642/docs)
- [Документация](docs/)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CHANGELOG.md](CHANGELOG.md)

---

## Правила работы с владельцем проекта

Владелец проекта **не является программистом**. Все отчёты должны быть понятны ему без перевода с технического языка.

### Формат итогового отчёта

**Каждый отчёт** должен начинаться с раздела «Простыми словами», содержащего:

1. **Что было целью?** — одно предложение.
2. **Что реально сделано?** — конкретно, без абстракций.
3. **Что получилось?** — PASS / PARTIAL / BLOCKED.
4. **Есть ли проблемы?** — человеческим языком, с оценкой серьёзности.
5. **Что предлагается дальше?** — как предложение, не автоматически.

После этого можно добавить техническую часть.

### Запрещено
- Писать только технический вывод без человеческого объяснения.
- Смешивать «сделано» и «предлагается».
- Автоматически переходить к следующему этапу без подтверждения.
- Скрывать неопределённость за терминологией.

### Различать статусы
| Статус | Что значит простыми словами |
|--------|---------------------------|
| DOCUMENTED | Задокументировано, объяснено |
| IMPLEMENTED | Код существует |
| TESTED | Проверено тестами |
| VERIFIED | Подтверждено архитектурное требование |
| ACCEPTED | Этап принят |

### Если обнаружена неожиданная архитектура
Объяснить: что найдено, почему это важно, как влияет на дальнейшую работу. Не скрывать за терминологией.

### Если не уверен
Написать прямо: «Я не могу безопасно утверждать, что это готово. Причина: …». Указать, какое решение требуется от владельца.
