# ГЛУБОКИЙ АУДИТ БЭКАНДА — «Наследие Аркаима»

> Дата: 10.07.2026
> Роль: Lead Backend Engineer / System Architect
> Стек: Python 3.14, FastAPI, aiosqlite, ChromaDB, Jinja2/HTMX
> Скоуп: Бэкенд, БД, бизнес-логика, API-контракты, безопасность
> **ВАЖНО: Без нового функционала и без фронтенда. Только стабилизация и рефакторинг.**

---

## ЭТАП 1: АУДИТ БАЗЫ ДАННЫХ И СУЩНОСТЕЙ (Data Layer)

### 1.1 Текущая архитектура данных

Проект использует **5 разрозненных SQLite-файлов** без единого менеджера:

| База данных | Путь | Таблицы | Назначение |
|---|---|---|---|
| `auth.db` | `runtime/memory/data/auth.db` | `users`, `sessions`, `api_keys` | Аутентификация |
| `readers.db` | `runtime/core/memory/data/readers.db` | `readers`, `topics`, `conversations`, `visual_memory` | Память читателей |
| `memory.db` | `runtime/memory/data/memory.db` | `conversations` | История чата |
| `leads.db` | `runtime/memory/data/leads.db` | `leads` | Лиды |
| `drafts.db` | `runtime/memory/data/drafts.db` | Черновики | Контент |
| `chroma.sqlite3` | `core/CHROMA_DB/chroma.sqlite3` | Внутренняя ChromaDB | Векторный индекс |

**Критическая проблема:** нет менеджера соединений. Каждый модуль (`UserStore`, `ReaderMemoryStore`, `MemoryStore`) создаёт собственное aiosqlite-соединение. При параллельных запросах это приводит к:
- Дублированию соединений (каждый `UserStore()` = новое соединение)
- Отсутствию контроля жизненного цикла (утечки при ошибках)
- Невозможности транзакций между базами

### 1.2 Нормализация и схемы

#### auth.db (миграция `001_initial_schema.sql`, 42 строки)

**Проблемы:**
1. **Нет `ON DELETE CASCADE`** — при удалении пользователя orphan-строки в `sessions` и `api_keys` остаются навсегда
2. **Нет индексов на `token_hash` и `key_hash`** — поиск по хэшу токена/ключа = полный скан таблицы
3. **`api_keys.name` не уникален** — можно создать дублирующие ключи с одинаковым именем
4. **Таймстампы как TEXT** — медленные диапазонные запросы по сравнению с INTEGER (epoch)
5. **`BOOLEAN` в SQLite** — работает, но неявно (1/0)

#### readers.db (миграция `001_initial_schema.sql`, 56 строк)

**Проблемы:**
1. **Нет `ON DELETE CASCADE`** — orphan-строки в `topics`, `conversations`, `visual_memory`
2. **`visual_memory` без PRIMARY KEY** — `INSERT OR REPLACE` всегда вставляет новую строку вместо обновления (дубликаты)
3. **Нет композитного уникального индекса на `topics(reader_id, name)`** — запросы по `topic_name` будут дублироваться
4. **Бесконтрольный рост `conversations`** — нет стратегии очистки/архивации
5. **Мёртвая колонка `conversations.confidence`** — есть в схеме, но нигде не используется

#### КРИТИЧЕСКИЙ БАГ: Несоответствие имён колонок

В `reader_memory.py` (строки 129, 169, 179, 183) запросы используют `topic_name`, но в схеме колонка называется `name`. Это вызывает `sqlite3.OperationalError: no such column: topic_name` при каждом обращении к топикам. **ReaderMemoryStore сломан в продакшене.**

### 1.3 Целостность связей (Foreign Keys)

| Связь | Текущее состояние | Проблема |
|---|---|---|
| `sessions.user_id` → `users.id` | FK есть, NO CASCADE | Orphan-сессии при удалении пользователя |
| `api_keys.user_id` → `users.id` | FK есть, NO CASCADE | Orphan-ключи при удалении пользователя |
| `topics.reader_id` → `readers.id` | FK есть, NO CASCADE | Orphan-топики |
| `conversations.reader_id` → `readers.id` | FK есть, NO CASCADE | Orphan-диалоги |
| `visual_memory.reader_id` → `readers.id` | FK есть, NO CASCADE | Orphan-визуальная память |

**Все 5 FK работают без каскадного удаления.** При удалении пользователя/читателя все связанные данные становятся мусором.

### 1.4 План исправления

| Приоритет | Действие | Сложность |
|---|---|---|
| P0 | Исправить `topic_name` → `name` в `reader_memory.py` | Низкая |
| P0 | Добавить PK в `visual_memory` или композитный уникальный индекс | Низкая |
| P1 | Добавить `ON DELETE CASCADE` во все FK | Низкая |
| P1 | Добавить индексы на `sessions.token_hash`, `api_keys.key_hash` | Низкая |
| P2 | Создать менеджер соединений (единый `DatabaseManager`) | Средняя |
| P2 | Добавить стратегию очистки `conversations` (TTL/архивация) | Средняя |
| P3 | Убрать мёртвую колонку `conversations.confidence` | Низкая |

---

## ЭТАП 2: АРХИТЕКТУРА БЭКАНДА И БИЗНЕС-ЛОГИКИ (Domain & Service Layer)

### 2.1 Оценка разделения ответственности (Separation of Concerns)

**Общая оценка: 4/10 — критически неудовлетворительно.**

| Модуль | Ответственность | Нарушения |
|---|---|---|
| `main.py` (799 строк) | Входная точка, МАРШРУТЫ, middleware, X-Ray, аналитика, SEO, SSE, health, rate limiting | **God Module**: 10+ обязанностей в одном файле |
| `orchestrator.py` (264 строки) | Бизнес-логика чата, роутинг, скиллы, провайдеры, идентичность, память, метрики | **God Module**: 8+ обязанностей |
| `book_routes.py` (446 строк) | Book Intelligence, Visual Genome, Reader Memory, Telegram, Voice | **God Router**: 5 доменов в одном файле |
| `config.py` (42 строки) | Дублирование `shared_config.py` | **Мёртвый код**: нулевая добавленная стоимость |

**Пример нарушения SoC в `orchestrator.py`:**
```python
async def chat(self, req, xray_headers=None):
    # 1. Роутинг намерений (router.py)
    # 2. Выполнение скиллов
    # 3. Сборка промпта (identity + system + context)
    # 4. Выбор провайдера + fallback
    # 5. Вызов LLM
    # 6. Санитайзинг ответа
    # 7. Пост-обработка скилла
    # 8. Сохранение в память
    # 9. Метрики
    # 10. Трейсинг
    # 11. Логирование
```

### 2.2 Рекомендуемый архитектурный паттерн

**Controller → Service → Repository** с чистым разделением:

```
Контроллеры (маршруты):
  - Принимают запрос
  - Валидируют через Pydantic DTO
  - Вызывают сервис
  - Возвращают DTO ответа
  - НЕ содержат бизнес-логики

Сервисы:
  - Бизнес-логика
  - Оркестрация вызовов
  - Валидация бизнес-правил
  - НЕ знают про HTTP/FastAPI

Репозитории:
  - Доступ к данным
  - SQL-запросы
  - Маппинг Row → Model
  - НЕ знают про бизнес-логику
```

### 2.3 Нарушения DRY и мёртвый код

#### Дублирование:

| Паттерн | Где дублируется | Проблема |
|---|---|---|
| Конфигурация | `shared_config.py` + `config.py` | Одни и те же поля в двух местах |
| Загрузка генома | `_load_genome()` + `_load_genome_full()` в `book_routes.py` | Почти идентичные функции |
| Сохранение генома | 4 блока `load→modify→save` в `book_routes.py` (строки 329-427) | Копипаст паттерна |
| Сборка промпта | `chat()` и `stream()` в `orchestrator.py` (строки 94-102 и 219-227) | Идентичная логика |
| Ключевые слова | `router.py` и `book_intelligence.py` | Два mechanism для определения намерения |
| SSE-эндпоинты | `/xray/events/stream` и `/xray/events` в `main.py` | Два способа стриминга |
| UserStore | `routes.py`, `rbac.py` | Каждый создаёт новый экземпляр |

#### Мёртвый код:

| Файл/блок | Причина |
|---|---|
| `router.py` (7 строк) | Intent вычисляется, но нигде не используется для маршрутизации |
| `config.py` (42 строки) | Полностью дублирует `shared_config.py` |
| `book_routes.py` `/visual-genome/from-image` | Стаб, возвращает захардкоженный JSON |
| `orchestrator.py` строка 153 | Выражение `(time.time() - provider_t0) * 1000` вычисляется, но результат отбрасывается |
| `google.py` `get_google_discovery()` | Загружает ключи Google, но они нигде не используются (verify_signature=False) |

### 2.4 Рекомендуемая структура папок

```
runtime/
├── core/
│   ├── main.py                  # Точка входа (только lifespan, middleware, подключение роутеров)
│   ├── config.py                # Единый конфиг (Pydantic BaseSettings)
│   ├── database.py              # DatabaseManager (единое соединение)
│   ├── middleware.py             # Rate limiting, auth middleware
│   ├── dependencies.py          # FastAPI Depends фабрики
│   │
│   ├── routes/                  # Контроллеры
│   │   ├── __init__.py
│   │   ├── chat.py              # /v1/chat, /v1/stream
│   │   ├── book.py              # /book/*
│   │   ├── auth.py              # /auth/*
│   │   ├── xray.py              # /xray/*
│   │   ├── admin.py             # Админ-эндпоинты
│   │   └── ui.py                # /_ui/*
│   │
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── chat_service.py      # Оркестрация чата
│   │   ├── book_service.py      # Book Intelligence
│   │   ├── auth_service.py      # Аутентификация/авторизация
│   │   ├── memory_service.py    # Память читателей
│   │   └── provider_service.py  # Управление провайдерами
│   │
│   ├── repositories/            # Доступ к данным
│   │   ├── __init__.py
│   │   ├── user_repo.py         # CRUD пользователей
│   │   ├── session_repo.py      # CRUD сессий
│   │   ├── api_key_repo.py      # CRUD API-ключей
│   │   ├── reader_repo.py       # CRUD читателей/топиков
│   │   └── conversation_repo.py # CRUD диалогов
│   │
│   ├── models/                  # Доменные модели
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── api_key.py
│   │   ├── reader.py
│   │   └── conversation.py
│   │
│   ├── dto/                     # Data Transfer Objects
│   │   ├── __init__.py
│   │   ├── requests.py          # Все входящие DTO
│   │   └── responses.py         # Все исходящие DTO
│   │
│   └── skills/                  # Скиллы (без изменений)
│       ├── base.py
│       ├── registry.py
│       └── book_intelligence.py
```

---

## ЭТАП 3: API-КОНТРАКТЫ (API Layer)

### 3.1 Анализ текущих эндпоинтов

**Всего эндпоинтов: ~70+**

| Группа | Кол-во | Статус |
|---|---|---|
| Book Intelligence | ~20 | Рабочие, но без единых DTO |
| Auth | ~12 | Рабочие, но с багами |
| X-Ray | ~15 | Рабочие, дублирование SSE |
| Chat/Stream | 2 | Нет валидации входных данных |
| UI (Jinja2) | ~8 | HTMX, не API |
| Health/Metrics | 4 | Базовые |

**Проблемы:**
1. **Нет валидации входных данных** — `/v1/chat` и `/v1/stream` принимают сырой `request.json()` без Pydantic модели
2. **Дублированные эндпоинты** — два SSE-эндпоинта для X-Ray
3. **Неконсистентная авторизация** — `/ask` проверяет `get_current_user` напрямую, другие используют `require_role("reader")`
4. **Стаб-эндпоинты** — `/visual-genome/from-image` возвращает фиктивный ответ
5. **OpenAPI-спецификация устарела** — `openapi.yaml` (221 строка) не покрывает все эндпоинты

### 3.2 Стандарты для DTO

#### Входящие DTO (requests.py)

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    messages: list[Message]
    session_id: str | None = None
    stream: bool = False

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=10000)

class BookAskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)

class BookGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    agent: Literal["herald", "keeper", "diplomat"] = "herald"

class TelegramMessageRequest(BaseModel):
    text: str
    chat_id: str
    user_id: str | None = None
```

#### Исходящие DTO (responses.py)

```python
class SuccessResponse(BaseModel):
    ok: bool = True
    data: Any
    trace_id: str | None = None

class ErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str          # "AUTH_EXPIRED", "BOOK_NOT_FOUND", "VALIDATION_ERROR"
    message: str       # Человеко-понятное сообщение
    details: dict | None = None

class PaginatedResponse(BaseModel):
    ok: bool = True
    data: list[Any]
    total: int
    page: int
    per_page: int
```

#### Стандарты именования

| Аспект | Стандарт |
|---|---|
| ID | UUID v4 строкой, не целые числа |
| Timestamps | ISO-8601 UTC: `"2026-07-10T12:00:00Z"` |
| Имена полей | snake_case |
| Булевы поля | Без префикса `is_` unless domain-specific |
| Пустые коллекции | `[]`, не `null` |
| Даты в ответах | Формат `"YYYY-MM-DDTHH:MM:SSZ"` |

#### Поля, которые НЕ ОТДАЁМ на фронтенд

| Поле | Причина |
|---|---|
| `key_hash` | Криптографический хэш |
| `token_hash` | Токен сессии |
| `password_hash` | Если появится |
| `session_secret` | Секрет |
| `HERMES_API_KEY` | Сервисный ключ |
| `db_path` | Путь к файлу БД |
| Внутренние `_` атрибуты | Инкапсуляция |

### 3.3 Унификация форматов ответов

#### Успешный ответ
```json
{
  "ok": true,
  "data": {
    "answer": "...",
    "sources": ["..."],
    "score": 0.85
  },
  "trace_id": "abc-123"
}
```

#### Ошибка
```json
{
  "ok": false,
  "error": {
    "code": "BOOK_NOT_FOUND",
    "message": "Книга не найдена или не загружена",
    "details": null
  }
}
```

#### HTTP-коды

| Код | Использование |
|---|---|
| 200 | Успех |
| 201 | Создано |
| 400 | Ошибка валидации (некорректный запрос) |
| 401 | Не аутентифицирован |
| 403 | Нет прав (роль ниже требуемой) |
| 404 | Ресурс не найден |
| 409 | Конфlict (дубликат, нарушение уникальности) |
| 422 | Ошибка бизнес-логики |
| 429 | Rate limit |
| 500 | Внутренняя ошибка сервера |

### 3.4 План документации

| Действие | Приоритет |
|---|---|
| Пересобрать `openapi.yaml` из кода (автогенерация через FastAPI) | P0 |
| Добавить все эндпоинты Book OS, Knowledge Graph, Evolution | P1 |
| Добавить auth-эндпоинты в спеку | P1 |
| Подключить Swagger UI в продакшене (только admin) | P2 |
| Настроить автогенерацию при каждом деплое | P2 |

---

## ЭТАП 4: ИНФРАСТРУКТУРА, БЕЗОПАСНОСТЬ И КОНФИГУРАЦИЯ

### 4.1 Переменные окружения и секреты

#### Найденные проблемы:

| Проблема | Где | Критичность |
|---|---|---|
| `SESSION_SECRET = "change-me-in-production"` | `shared_config.py:59` | **КРИТИЧЕСКАЯ** — если не изменён, все JWT подделываемы |
| Дублирование конфига | `shared_config.py` + `config.py` + `core/config.py` | Средняя — три источника правды |
| Secrets в `.env` без `.gitignore` | `core/.env` | Средняя — риск утечки |
| Нет валидации обязательных переменных | `shared_config.py` | Средняя — крэш при запуске вместо понятной ошибки |
| `int(os.getenv(...))` без try/except | `shared_config.py` | Низкая — крэш с неочевидным сообщением |

### 4.2 Аутентификация и безопасность

#### КРИТИЧЕСКИЕ ДЫРЫ В БЕЗОПАСНОСТИ:

**1. Подпись Google ID-токена ОТКЛЮЧЕНА (google.py:55)**
```python
payload = jwt.decode(id_token, key, algorithms=["RS256"],
                     audience=client_id,
                     options={"verify_signature": False})  # ← ОТКЛЮЧЕНО!
```
**Любой человек может подделать Google-идентификацию.** Создайте JWT с правильными `aud` и `iss` — и вы «google-пользователь». Discovery document загружается, ключи загружаются — но НЕ используются.

**2. Админ-бэкдор через HERMES_API_KEY (rbac.py:26-34)**
```python
if settings.HERMES_API_KEY and token == settings.HERMES_API_KEY:
    # ... проверка API-ключа ...
    return {"user_id": "service", "role": "admin", ...}  # ← ВСЕГДА admin
```
Любой запрос с `Authorization: Bearer <HERMES_API_KEY>` получает admin-права.

**3. Replay-атака на Telegram OAuth (routes.py + telegram.py)**
- `auth_date` не проверяется на свежесть
- Старый валидный ответ Telegram можно переиспользовать бесконечно
- Telegram рекомендует проверку `auth_date` в пределах 600 секунд

**4. XSS через шаблоны (routes.py:33-34)**
```python
_LOGIN_HTML = _LOGIN_HTML.replace("{{TELEGRAM_BOT_USERNAME}}", settings.TELEGRAM_BOT_USERNAME)
```
Если `TELEGRAM_BOT_USERNAME` или `PUBLIC_BASE_URL` содержат HTML/JS — XSS.

**5. Rate limit обходится User-Agent (main.py:272-277)**
```python
if request.headers.get("user-agent", "").startswith("testclient"):
    return await call_next(request)  # ← БЕЗ проверки rate limit
```
Любой клиент может послать `User-Agent: testclient` и обойти rate limiting.

**6. Нет server-side инвалидации сессий (routes.py)**
Logout удаляет только cookie. JWT остаётся валидным до истечения (12 часов). Нет механизма отзыва.

**7. Мидлварь читает тело запроса (main.py:304-309)**
`await request.json()` в rate-limit middleware может потребить тело потока, оставив endpoint без данных.

### 4.3 Логирование и обработка исключений

#### Текущее состояние:

| Проблема | Где |
|---|---|
| Голые `except Exception` без traceback | `main.py`, `orchestrator.py`, `book_routes.py` |
| Смешанные подходы к логированию | `logging.getLogger()` + `log_event()` + прямые `log.error()` |
| Нет глобального exception handler | Нет `@app.exception_handler` |
| f-string в логах (лишний вызов при отключённом уровне) | `book_routes.py:426` |
| Утечка внутренних ошибок клиенту | `google.py`, `routes.py` |

#### Рекомендуемый подход:

```python
# Глобальные обработчики
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": {"code": exc.detail, "message": str(exc)}}
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    log.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Внутренняя ошибка сервера"}}
    )
```

---

## ЭТАП 5: ПОШАГОВЫЙ ПЛАН РЕФАКТОРИНГА (Refactoring Roadmap)

### Этап 1: Критические баги и дыры в безопасности (1-2 недели)

| # | Задача | Сложность | Риск при откладывании |
|---|---|---|---|
| 1.1 | **Включить проверку подписи Google ID-токена** (`verify_signature=True` + JWKS) | Низкая | Полная подделка Google-идентичности |
| 1.2 | **Убрать admin-бэкдор HERMES_API_KEY** — проверять через RBAC, не хардкодить admin | Низкая | Привилегия сервисного ключа |
| 1.3 | **Добавить проверку `auth_date` в Telegram OAuth** (±600 сек) | Низкая | Replay-атака |
| 1.4 | **Исправить XSS в шаблонах** — HTML-escape переменных | Низкая | XSS-атака |
| 1.5 | **Исправить баг `topic_name` → `name`** в `reader_memory.py` | Низкая | ReaderMemoryStore полностью неработоспособен |
| 1.6 | **Исправить variable shadowing** в `routes.py:162` (`for k, v in k.items()`) | Низкая | `/api-keys` крэшится при вызове |
| 1.7 | **Убрать обход rate limit через User-Agent** | Низкая | DoS-атака |
| 1.8 | **Добавить `SESSION_SECRET` validation** — крэш при запуске если `change-me` | Низкая | Подделка JWT |
| 1.9 | **Исправить чтение тела в middleware** | Средняя | Потеря данных запроса |

### Этап 2: Рефакторинг БД и миграций (1-2 недели)

| # | Задача | Сложность |
|---|---|---|
| 2.1 | Добавить `ON DELETE CASCADE` во все FK | Низкая |
| 2.2 | Добавить индексы на `token_hash`, `key_hash` | Низкая |
| 2.3 | Добавить PK в `visual_memory` или уникальный композитный индекс | Низкая |
| 2.4 | Создать `DatabaseManager` — единое соединение на приложение | Средняя |
| 2.5 | Создать миграции 002_add_indexes.sql, 003_add_cascade.sql | Низкая |
| 2.6 | Добавить стратегию очистки `conversations` (TTL 30 дней) | Средняя |
| 2.7 | Убрать мёртвую колонку `conversations.confidence` | Низкая |
| 2.8 | Заменить `executescript` на транзакционные `execute` в `migration_engine.py` | Средняя |

### Этап 3: Вынос бизнес-логики из контроллеров (2-3 недели)

| # | Задача | Сложность |
|---|---|---|
| 3.1 | Создать `dto/requests.py` и `dto/responses.py` — Pydantic DTO для всех эндпоинтов | ✅ Готово |
| 3.2 | Создать `repositories/user_repo.py`, `session_repo.py`, `api_key_repo.py` | ✅ Готово |
| 3.3 | Создать `services/auth_service.py` — вынести логику из `routes.py` | ✅ Готово |
| 3.4 | Создать `services/chat_service.py` — вынести из `orchestrator.py` | ✅ Готово |
| 3.5 | Разбить `book_routes.py` на `routes/book.py`, `routes/visual.py`, `routes/reader.py` | ✅ Готово |
| 3.6 | Разбить `main.py`: вынести middleware в `middleware.py` | ✅ Готово |
| 3.7 | Убрать `config.py` → прокси-слой к `shared_config` | ✅ Готово |
| 3.8 | Убрать `router.py` (мёртвый код) | ✅ Готово |
| 3.9 | Заменить module-level синглтоны на FastAPI `Depends` + lifespan | Частично (см. ниже) |
| 3.10 | Заменить `adc_deps.py` sys.path hack на нормальные импорты | Частично (см. ниже) |

### Этап 4: Унификация DTO, Swagger/OpenAPI (1-2 недели)

| # | Задача | Сложность |
|---|---|---|
| 4.1 | Пересобрать OpenAPI из кода (FastAPI autogenerate) | Низкая |
| 4.2 | Добавить все эндпоинты Book OS, Knowledge Graph, Evolution | Средняя |
| 4.3 | Добавить auth-эндпоинты в спеку | Низкая |
| 4.4 | Добавить security schemes (Bearer, Cookie) | Низкая |
| 4.5 | Стандартизировать ошибки — единый ErrorResponse на все эндпоинты | Средняя |
| 4.6 | Убрать дублированные SSE-эндпоинты | Низкая |
| 4.7 | Убрать стаб-эндпоинты или пометить как deprecated | Низкая |
| 4.8 | Подключить Swagger UI для admin-пользователей | Низкая |

### Этап 5: Тесты (2-3 недели)

| # | Задача | Сложность |
|---|---|---|
| 5.1 | Auth-пакет — 71 тест (tokens, users, rbac, routes, oauth) | ✅ Готово |
| 5.2 | Repositories — 16 тестов (UserRepo, SessionRepo, ApiKeyRepo) | ✅ Готово |
| 5.3 | Services — покрыты через repositories + auth tests | ✅ Готово |
| 5.4 | Migration engine — 12 тестов (apply, skip, rollback, checksum) | ✅ Готово |
| 5.5 | DatabaseManager — 8 тестов (connection, WAL, FK, lifecycle) | ✅ Готово |
| 5.6 | DTOs — 18 тестов (request validation, response models) | ✅ Готово |
| 5.7 | **Итого: 54 новых + 71 существующих = 125 тестов** | ✅ Готово |

---

## ЭТАП 6: ВОПРОСЫ И «СЛЕПЫЕ ЗОНЫ»

### 6.1 Странные/устаревшие архитектурные решения

1. **Два «мира» (core/ и runtime/) с взаимными импортами** — нельзя запустить ADC отдельно от Runtime. Это не микросервис и не монолит — гибрид, который не даёт преимуществ ни одного из подходов.

2. **9 module-level синглтонов в `book_routes.py`** — `ConsciousnessLayers()`, `BookRetriever()`, `KeeperAgent()`, `HeraldAgent()` и т.д. создаются при старте. Если книга не загружена — они висят в памяти мёртвыми объектами.

3. **`BookPulse` создаётся на каждый запрос** в `book_intelligence.py` — `pulse.load()` читает JSON с диска при каждом обращении. Это катастрофа для производительности.

4. **Нет `__init__.py` в `runtime/`** — Python не видит `runtime/` как пакет, что заставляет использовать `sys.path` хаки.

5. **SQLite для production** — 5 файлов, без WAL mode (по умолчанию), без connection pooling, без FK enforcement (SQLite отключает FK по умолчанию!). Нужно `PRAGMA foreign_keys = ON`.

6. **`sys.path.insert` в `adc_deps.py`** — помечен как «deprecated», но используется как fallback. Нет плана миграции.

7. **Дублирование логирования** — три разных подхода в одном проекте: `logging.getLogger`, `log_event` из observability, и прямые `log.error/warning`.

8. **Нет health check для БД** — `/health` проверяет HTTP, но не проверяет доступность SQLite-файлов.

### 6.2 Чего критически не хватает

1. **Валидация входных данных на `/v1/chat` и `/v1/stream`** — принимается любой JSON без проверки
2. **Server-side session invalidation** — logout не работает真正的
3. **Транзакционные миграции** — `executescript` коммитит автоматически
4. **PRAGMA foreign_keys = ON** — FK в SQLite не работают по умолчанию!
5. **Единый DatabaseManager** — нет контроля соединений
6. **Обработка ошибок провайдеров** — при полном отказе всех провайдеров пользователь получает 500
7. **Request ID / Trace ID** — нет возможности отследить запрос через систему
8. **Structured logging** — текущие логи плохо парсятся

### 6.3 Уточняющие вопросы

**Вопрос 1: SQLite vs PostgreSQL**
Вы планируете переход на PostgreSQL в обозримом будущем? Если да — все миграции стоит писать сразу с учётом PostgreSQL (VARCHAR вместо TEXT, BOOLEAN, sequence для ID). Если нет — можно оптимизировать SQLite (WAL mode, PRAGMA foreign_keys, connection pooling).

**Вопрос 2: Ключевые слова для определения книжных вопросов**
Сейчас используется наивный список слов ("спроси", "книга", "персонаж"). Есть ли бизнес-правило: «вопрос считается книжным, если содержит хотя бы одно из N слов»? Или нужна более интеллектуальная классификация (NLP/LLM-based)?

**Вопрос 3: Многопользовательский режим**
Сейчас `ReaderMemoryStore` привязан к `reader_id`. Если пользователь логинится через Telegram и Google — это два разных `reader_id`? Как должна работать синхронизация профиля между провайдерами?

**Вопрос 4: Rate limiting — per-IP или per-user?**
Сейчас rate limit считается по IP. Для авторизованных пользователей стоит ли считать по user_id (справедливее)? Какой лимит для admin/сервисных ключей?

**Вопрос 5: Миграционная стратегия**
Текущие таблицы уже созданы через `CREATE TABLE IF NOT EXISTS`. При первом запуске新的 migration engine — как обработать существующие данные? Нужна ли миграция «000_baseline`» для фиксации текущего состояния?

---

## ОБЩАЯ ОЦЕНКА

| Критерий | До аудита | Целевое значение |
|---|---|---|
| Безопасность | 3/10 | 8/10 |
| Архитектура | 4/10 | 7/10 |
| Тестирование | 3.5/10 | 6/10 |
| API-контракты | 3/10 | 8/10 |
| БД | 4/10 | 7/10 |
| Документация | 8/10 | 9/10 |
| **Средняя** | **4.25/10** | **7.5/10** |

### Топ-5 критических находок

1. **Google ID-token подпись ОТКЛЮЧЕНА** — кто угодно может подделать Google-вход
2. **Админ-бэкдор через HERMES_API_KEY** — сервисный ключ = полные права
3. **`topic_name` vs `name`** — ReaderMemoryStore сломан в продакшене
4. **SQLite FK не работают** — нет `PRAGMA foreign_keys = ON`
5. **Нет server-side logout** — JWT живёт 12 часов после «выхода»

### Порядок действий

1. **Сегодня**: исправить 5 критических находок (Этап 1, задачи 1.1-1.9)
2. **Эта неделя**: миграции БД + DatabaseManager (Этап 2)
3. **Следующие 2 недели**: рефакторинг архитектуры (Этап 3)
4. **Через месяц**: DTO + Swagger (Этап 4)
5. **После**: тесты (Этап 5)

---

---

## ПРИНЯТЫЕ РЕШЕНИЯ (10.07.2026)

| Вопрос | Решение |
|---|---|
| SQLite vs PostgreSQL | **SQLite** — остаёмся, оптимизируем (WAL, PRAGMA foreign_keys, pooling) |
| Классификация намерения | **LLM-based** — заменить наивные ключевые слова на LLM-классификатор |
| Мульти-провайдер OAuth | **Один reader_id** — Telegram + Google привязываются к одному профилю |
| Rate limiting | **Гибридный** — per-IP для анонимных, per-user для авторизованных |
| Миграции | **000_baseline.sql** → снимок текущего состояния, затем инкрементальные миграции |
