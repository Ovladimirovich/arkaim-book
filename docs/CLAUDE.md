## Проект
«Наследие Аркаима» — цифровое сознание книги. Бэкенд FastAPI + SQLite, фронтенд React + Next.js.

## Запуск
```bash
start_all.bat              # Всё сразу (Backend + Frontend + браузер)
stop_all.bat               # Остановка всего
cd arkaim-web && npm run dev       # Только фронтенд (порт 3000)
cd runtime && .venv\Scripts\python -m uvicorn core.main:app --port 8642  # Только бэкенд
cd arkaim-web && npx vitest run    # Тесты
```

## Порты
- Backend: 8642
- Frontend: 3000
- Frontend проксирует API на бэкенд через Next.js rewrites

## Текущее состояние
- **34 страницы** фронтенда, все работают (включая World Explorer и World Engine)
- **111+ unit-тестов** (backend) + 30 (frontend)
- **168 тем** в ExpansionLayer (расширенные знания)
- **11 модулей** обогащения знаний
- **8 слоёв** Pulse (+ ExpansionLayer)
- **219 роутов** API (включая 24 World Explorer)
- Авторизация: Telegram бот (/login) + email регистрация + dev-режим
- WebSocket реалтайм уведомления + Live-лента
- ReaderProfile + Adaptive Responses (адаптация под читателя)
- Knowledge Expansion Pipeline (авто-обогащение)
- Interactive Map + Timeline
- Краудфандинг интеграция
- **World Explorer** — подсистема исследования мира (15 этапов, 111 тестов)

## Архитектура
- Бэкенд: FastAPI + SQLite (runtime/, порт 8642)
- Фронтенд: React 19 + Next.js 16 + Ant Design 5 (arkaim-web/, порт 3000)
- Мобильное: React Native + Expo (arkaim-mobile/)
- Ядро: Pulse + Voice + Agents (core/)
- API прокси: Next.js rewrites (3000 → 8642)
- FSD: entities / features / widgets / shared

## Страницы (34 шт.)
| Страница | Путь | Описание |
|----------|------|----------|
| Задать вопрос | /ask | Минималистичный ввод вопроса, популярные вопросы, streaming |
| Чат с книгой | /book | Чат с sidebar (темы, профиль, статистика), streaming, сессии |
| Чтение | /reading | Режим чтения глав с оглавлением, размер шрифта, навигация |
| Сценарий | /screenplay | Чтение сценария с оглавлением сцен |
| Библиотека | /library | Геном (темы, персонажи, ценности, мир) + слои сознания + эволюция |
| Жанры | /genres | Темы по 6 жанрам (мифология, история, философия...) + ценности + мир |
| Визуал | /visual-view | Галерея сцен, персонажей, локаций |
| Редактор | /editor | Создание/редактирование сцен, персонажей, локаций |
| О книге | /about | Геном + Слои сознания + Эволюция |
| Поиск | /search | 4 вкладки: знания, факты, сущности, граф |
| Профиль | /profile | Быстрые действия, статистика, темы, API-ключи, подписка |
| Рекомендации | /recommendations | Персонализированные рекомендации, тренды, прогресс |
| История | /history | Вопросы, сессии, фильтры |
| Краудфандинг | /crowdfunding | Кампании, майлстоуны, admin-панель |
| Аналитика | /analytics | Запросы, граф знаний, системная статистика |
| Уведомления | /notifications | Live-лента + WebSocket + email-рассылка |
| API | /api | Ключи, тестер, примеры, документация |
| Настройки | /settings | Аккаунт, внешний вид, язык, безопасность |
| Загрузка | /upload | Drag-and-drop загрузка, история в localStorage |
| Визуалы | /visual | Формы создания сцен/персонажей/локаций + голосовой ввод |
| Админ | /admin | Дашборд, пользователи, инвайты, сессии, ключи, статистика |
| X-Ray | /xray | Статистика, трейсы, диагностика |
| Вход | /login | Telegram бот + email + dev-режим |
| Регистрация | /register | Email регистрация |
| Помощь | /help | Справка по функционалу |
| **Карта** | /map | Интерактивная карта + хронология мира книги |
| **Исследование** | /world-explorer | Исследование альтернативных линий развития мира |
| **Интерпретации** | /interpretations | Интерпретации читателей |
| **Артефакты** | /artifacts | Находки читателей |
| Краудфандинг | /crowdfunding | Кампании, майлстоуны, admin-панель |
| Аналитика | /analytics | Запросы, граф знаний, системная статистика |
| Уведомления | /notifications | Предложения, тренды, email-рассылка, подписчики |
| API | /api | Ключи, тестер, примеры, документация |
| Настройки | /settings | Аккаунт, внешний вид, язык, уведомления, безопасность, конфиденциальность |
| Загрузка | /upload | Drag-and-drop загрузка, история в localStorage |
| Визуалы | /visual | Формы создания сцен/персонажей/локаций + голосовой ввод |
| Админ | /admin | Дашборд, пользователи, инвайты, сессии, ключи, статистика |
| X-Ray | /xray | Статистика, трейсы, диагностика |
| Вход | /login | Telegram бот + email + dev-режим |
| Регистрация | /register | Email регистрация |



## World Engine (НОВЫЙ)

### Статистика
- **547 сущностей** мира в 13 категориях
- **287 связей** между сущностями (8 типов)
- **55 форм** для визуализации (11 категорий)
- **5 правил** консистентности мира
- **10 режимов** работы
- **10 API эндпоинтов** на `/book/world/`

### Категории мира
| Категория | Количество |
|-----------|------------|
| philosophy | 268 |
| language | 134 |
| geography | 38 |
| mythology | 37 |
| technologies | 22 |
| social_structure | 12 |
| religion | 10 |
| rituals | 10 |
| architecture | 5 |
| civilizations | 4 |
| daily_life | 3 |
| climate | 2 |
| transport | 2 |

### API Эндпоинты
```
/book/world/summary              # Сводка мира
/book/world/search               # Поиск по миру
/book/world/entity/{id}          # Получить сущность
/book/world/entity/{id}/context  # Контекст сущности
/book/world/entity/{id}/visual-prompt  # Визуальный промпт
/book/world/validate             # Проверка консистентности
/book/world/rules                # Правила мира
/book/world/modes                # Режимы работы
/book/world/categories           # Категории мира
/book/world/form-library         # Библиотека форм
```

### Команды
```bash
cd runtime && python world_cli.py stats           # Статистика мира
cd runtime && python world_cli.py search "Аркаим" # Поиск
cd runtime && python world_cli.py visual region_arkaim  # Визуальный промпт
cd runtime && python demo_world_engine.py         # Демонстрация
```

### Файлы
| Файл | Описание |
|------|----------|
| `core/CORE/narrative_engine/world_engine.py` | WorldEngine — координатор |
| `core/CORE/narrative_engine/world_model_ext.py` | Расширенная модель мира |
| `core/CORE/narrative_engine/form_engine.py` | Движок форм |
| `core/CORE/narrative_engine/consistency_engine.py` | Проверка консистентности |
| `core/CORE/narrative_engine/experience_engine.py` | 10 режимов работы |
| `runtime/world_cli.py` | CLI интерфейс |
| `runtime/world_batch.py` | Пакетная обработка |
| `runtime/demo_world_engine.py` | Демонстрация |



## World Engine (НОВЫЙ)

### Статистика
- **547 сущностей** мира в 13 категориях
- **287 связей** между сущностями (8 типов)
- **55 форм** для визуализации (11 категорий)
- **5 правил** консистентности мира
- **10 режимов** работы
- **10 API эンドпоинтов** на `/book/world/`

### Категории мира
| Категория | Количество |
|-----------|------------|
| philosophy | 268 |
| language | 134 |
| geography | 38 |
| mythology | 37 |
| technologies | 22 |
| social_structure | 12 |
| religion | 10 |
| rituals | 10 |
| architecture | 5 |
| civilizations | 4 |
| daily_life | 3 |
| climate | 2 |
| transport | 2 |

### API Эндпоинты
```
/book/world/summary              # Сводка мира
/book/world/search               # Поиск по миру
/book/world/entity/{id}          # Получить сущность
/book/world/entity/{id}/context  # Контекст сущности
/book/world/entity/{id}/visual-prompt  # Визуальный промпт
/book/world/validate             # Проверка консистентности
/book/world/rules                # Правила мира
/book/world/modes                # Режимы работы
/book/world/categories           # Категории мира
/book/world/form-library         # Библиотека форм
```

### Команды
```bash
cd runtime && python world_cli.py stats           # Статистика мира
cd runtime && python world_cli.py search "Аркаим" # Поиск
cd runtime && python world_cli.py visual region_arkaim  # Визуальный промпт
cd runtime && python demo_world_engine.py         # Демонстрация
```

### Файлы
| Файл | Описание |
|------|----------|
| `core/CORE/narrative_engine/world_engine.py` | WorldEngine — координатор |
| `core/CORE/narrative_engine/world_model_ext.py` | Расширенная модель мира |
| `core/CORE/narrative_engine/form_engine.py` | Движок форм |
| `core/CORE/narrative_engine/consistency_engine.py` | Проверка консистентности |
| `core/CORE/narrative_engine/experience_engine.py` | 10 режимов работы |
| `runtime/world_cli.py` | CLI интерфейс |
| `runtime/world_batch.py` | Пакетная обработка |
| `runtime/demo_world_engine.py` | Демонстрация |

## Авторизация
- **Telegram бот**: `/login` → токен → ссылка → JWT + cookie
- **Email**: `/register` → форма → JWT + cookie
- **Dev**: кнопка «Войти как разработчик» → dev-login API → JWT + cookie
- Cookie: `arkaim_session` (HttpOnly, SameSite=Lax)
- API routes: `/api/auth/login`, `/api/auth/logout`, `/api/auth/register`, `/api/auth/dev-login`

## Навигация
- Боковая панель с группировкой: Книга, Читатель, Сообщество, Инструменты, Админ
- Сворачиваемая панель (кнопка ☰)
- Ролевая фильтрация (admin/editor скрыты для reader)
- WebSocket badge на колокольчике

## API прокси (Next.js rewrites)
```
/auth/:path*   → http://localhost:8642/auth/:path*
/book/:path*   → http://localhost:8642/book/:path*
/api/:path*    → http://localhost:8642/api/:path*
/xray/:path*   → http://localhost:8642/xray/:path*
```

## Mock-режим
`src/shared/lib/api.ts` — при 401 возвращает mock-данные из `MOCK_DATA`.
Все страницы работают без реального бэкенда.

## Файлы API routes
```
src/app/api/auth/login/route.ts      # Логин по токену
src/app/api/auth/logout/route.ts     # Выход
src/app/api/auth/register/route.ts   # Регистрация
src/app/api/auth/dev-login/route.ts  # Dev-вход через бэкенд
src/app/api/telegram/callback/route.ts  # Telegram widget
```

## Известные проблемы
- Google OAuth недоступен в РФ
- Telegram бот нуждается в стабильном интернете для polling
- Некоторые API требуют реальную авторизацию

## Команды
```bash
start_all.bat              # Запуск всего
stop_all.bat               # Остановка всего
cd arkaim-web && npm run dev       # Фронтенд
cd arkaim-web && npx vitest run    # Тесты
cd arkaim-web && npm run build     # Production сборка
```

## Shared компоненты (`arkaim-web/src/shared/`)
| Компонент | Файл | Назначение |
|-----------|------|------------|
| SourceBadge | `ui/SourceBadge.tsx` | Бейдж источника (pulse/llm/hybrid/mock) |
| ChatBubble | `ui/ChatBubble.tsx` | Пузырь сообщения (user/assistant) |
| StreamingBubble | `ui/ChatBubble.tsx` | Пузырь streaming-ответа |
| useIsMobile | `lib/hooks.ts` | Хук определения мобильного |
| useStreamingChat | `lib/useStreamingChat.ts` | Хук SSE streaming чата |
| useSearchPanel | `lib/useSearchPanel.ts` | Generic хук поиска |
| Markdown | `lib/markdown.tsx` | Рендер markdown |

## Оптимизации производительности
- **Genome**: `@lru_cache` для чтения JSON (1 раз вместо каждого запроса)
- **Book text**: кэширование склеенного текста
- **KnowledgeLayer**: dict-индексы для O(1) поиска вместо O(N) перебора
- **Retriever**: кэш enriched_catalog.json в памяти
- **Frontend**: MOCK_DATA исключена из production (IS_DEV guard)
- **React Query**: staleTime увеличен до 5 минут для статических данных
