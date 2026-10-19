# AI Engineer Guide — «Наследие Аркаима»

Руководство для ИИ-инженеров, работающих с проектом из IDE. Содержит ключевые сведения об архитектуре, Voice-протоколе и паттернах разработки.

---

## 1. Где запустить

| Сервис | URL | Команда |
|--------|-----|---------|
| Frontend (Next.js) | http://localhost:3000 | `cd arkaim-web && npm run dev` |
| Backend (FastAPI) | http://localhost:8642 | `cd runtime && uvicorn core.main:app --port 8642 --reload` |
| Swagger UI | http://localhost:8642/docs | Авто-генерируется FastAPI |
| Docker (все сразу) | | `docker compose up --build` |

---

## 2. Voice-протокол (ключевой архитектурный паттерн)

```
Вопрос читателя
    ↓
Pulse (core/CORE/pulse/pulse.py)
    ├── KnowledgeLayer → факты из генома (без LLM)
    ├── ExpansionLayer → 168 тем (без LLM)
    ├── MeaningLayer → замысел автора (без LLM)
    ├── IdentityLayer → границы самопредставления (Immutable)
    └── MissionLayer → миссия книги (Immutable)
    ↓
BookVoice (core/CORE/pulse/voice.py)
    ├── Если уверенность Pulse ≥ порог → ответ без LLM
    └── Если уверенность низкая → LLM формулирует ответ
    ↓
Pulse.verify() — проверка ответа LLM на соответствие книге
    ↓
IdentityLayer.validate() — финальная проверка (никогда не выходит за границы)
```

**Никогда не обходите Voice-протокол напрямую.** Все ответы на вопросы книги должны идти через Pulse → Voice → Validate.

---

## 3. Ключевые файлы для ИИ-инженера

### Core (ядро знаний)
| Файл | Назначение |
|------|-----------|
| `core/config.py` | Центральная конфигурация (все env-переменные) |
| `core/CORE/pulse/pulse.py` | BookPulse — поиск ответа, confidence scoring |
| `core/CORE/pulse/layers.py` | Слои Pulse (Knowledge, Meaning, Identity, Mission) |
| `core/CORE/pulse/voice.py` | BookVoice — LLM как микрофон |
| `core/CORE/pulse/evolution.py` | Версионирование генома |
| `core/CORE/knowledge_graph/` | Граф знаний (BFS, shortest path, RAG) |
| `core/CORE/intelligence/` | RAG, chunker, retriever |
| `core/CORE/narrative_engine/` | World Engine, сюжетный движок |
| `core/CORE/visualization/` | Генерация визуала (ComfyUI, SVG) |
| `core/CORE/knowledge_expansion/` | Пайплайн обогащения знаний |
| `core/KNOWLEDGE/` | 40+ JSON-файлов знаний (факты, темы, символы) |
| `core/GENOME/` | Геном книги (immutable) |
| `core/CHROMA_DB/` | Векторная БД (игнорируется в git) |

### Runtime (инфраструктура)
| Файл | Назначение |
|------|-----------|
| `runtime/core/main.py` | Точка входа FastAPI; инициализация Pulse (sys.path + lifespan) |
| `runtime/core/adc_deps.py` | FastAPI зависимости + DI-контейнер (ServiceRegistry) |
| `runtime/core/routes/` | API-роуты (`/book/*`, `/auth/*`, `/api/*`, `/xray/*`) |
| `runtime/core/orchestrator.py` | Оркестратор запросов |
| `runtime/core/memory/` | Память читателей (SQLite) |
| `runtime/core/providers/` | LLM-провайдеры (GigaChat, OpenRouter) |
| `runtime/tests/` | Backend-тесты (pytest) |

### Frontend
| Файл | Назначение |
|------|-----------|
| `arkaim-web/src/app/` | Страницы (34 шт.) |
| `arkaim-web/src/shared/lib/api.ts` | HTTP-клиент к backend |
| `arkaim-web/src/shared/lib/ws.ts` | WebSocket клиент |
| `arkaim-web/src/shared/types/index.ts` | Общие типы |
| `arkaim-web/src/widgets/` | Виджеты (Sidebar, AdminPanel) |

---

## 4. Как добавить новую функцию

1. Проверить, не реализует ли слой Pulse нужное (в `core/CORE/pulse/layers.py`)
2. Создать Pydantic-схему в `SCHEMAS/`
3. Создать модуль в `core/CORE/` или `runtime/core/`
4. Добавить Dependency в `runtime/core/adc_deps.py`
5. Добавить роут в `runtime/core/routes/`
6. Добавить тесты в `runtime/tests/`
7. Обновить документацию

---

## 5. Архитектурные ограничения (НЕ нарушать)

- ❌ **Книга — первичный источник истины.** Никакие решения не основаны на возможностях LLM.
- ❌ **LLM — инструмент, не архитектура.** Никогда не давайте LLM system prompt, который заставляет «быть книгой».
- ❌ **Pulse знает книгу без LLM.** Каждый слой может ответить на вопрос сам.
- ❌ **Никаких автономных действий.** Система предлагает — автор решает.
- ❌ **Никогда не читайте книгу через код** прежде, чем создать обработчик.
- ❌ **Никогда не подключайте UI** прежде, чем создать API.
- ❌ **Секреты только через `.env`** — никогда не добавляйте в код.
- ❌ **`except: pass`** — всегда обрабатывайте ошибки.

---

## 6. Тестирование

```bash
# Backend
cd runtime
python -m pytest tests/ -v              # все тесты
python -m pytest tests/ -k "world" -v   # World Engine тесты
python -m pytest tests/ -k "auth" -v    # Auth тесты

# Frontend
cd arkaim-web
npx vitest run                          # unit-тесты
npx playwright test                     # E2E-тесты
```

## 7. Линтеры

```bash
# Backend
cd runtime
ruff check .
ruff format --check .

# Frontend
cd arkaim-web
npm run lint
npx tsc --noEmit
```

---

## 8. CI/CD

- **Branch protection:** `main` требует passing CI
- **Commit format:** conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`)
- **Docker:** автоматически собираются для `main` → GitHub Container Registry (`ghcr.io/Ovladimirovich/arkaim-*`)
- **Secrets needed:** `GITHUB_TOKEN` (авто), опционально API-ключи LLM-провайдеров

---

## 9. Универсальные команды (Makefile)

```bash
make dev          # Запустить backend + frontend
make test         # Запустить все тесты
make lint         # Линтеры для backend + frontend
make format       # Форматирование
make clean        # Очистка кэша
make docker-up    # Docker compose up
```

---

## 10. Полезные команды для отладки

```bash
# Проверить health бэкенда
curl http://localhost:8642/health

# Запрос к книге (Voice-протокол)
curl -X POST http://localhost:8642/book/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Что такое Аркаим?"}'

# World Engine API
curl http://localhost:8642/book/world/entities

# Graph Engine (BFS)
curl http://localhost:8642/kg/search?query=аркаим

# Swagger UI
# http://localhost:8642/docs — интерактивная документация
```
