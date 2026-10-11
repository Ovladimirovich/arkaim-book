# ПЛАН: Фронтенд-аудит и дорожная карта — «Наследие Аркаима»

## Контекст

Проект «Наследие Аркаима» — цифровое сознание книги. Бэкенд: FastAPI + SQLite, ~100+ API эндпоинтов. Текущий фронтенд: Jinja2 + HTMX + vanilla JS (~2700 строк).

**Принятые решения:**
- **React + Next.js** (SSR для SEO)
- **Ant Design** (UI-библиотека)
- **Cloudflare Pages** (деплой)
- **React Native (Expo)** (мобильное приложение)
- **Только русский язык**
- **Все фичи равномерно**

---

## ЭТАП 1: Глубокий аудит и инвентаризация (Discovery)

### 1.1 Бизнес-домены

| Домен | Сущности | API |
|---|---|---|
| Book Intelligence | Genome, Pulse, Voice, Agents | `/book/*` |
| Reader Memory | Profiles, Topics, Conversations | `/book/reader/*` |
| Content Generation | Drafts, Articles | `/book/generate`, `/book/drafts/*` |
| Community Presence | Observations, Suggestions | `/book/presence/*` |
| Visual Genome | Scenes, Characters, Locations | `/book/visualize`, `/book/visual-genome/*` |
| Book OS | Documents, Entities, Facts | `/book/os/*` |
| Knowledge Graph | Entities, Paths, Subgraphs | `/book/graph/*` |
| Evolution | Versions, Diffs, Rollbacks | `/book/evolution/*` |
| Auth | Users, Sessions, API Keys, Invites | `/auth/*` |
| Observability | Traces, Events, Metrics | `/xray/*` |
| Crowdfunding | Campaigns, Milestones | `/book/crowdfunding/*` |
| Email | Subscribers, Drafts, Digests | `/book/email/*` |

### 1.2 Роли и User Flows

| Роль | Сценарии |
|---|---|
| **Аноним** | Лендинг → Регистрация (Telegram/Google) |
| **Reader** | Чат с книгой → Профиль → История → Email → Краудфандинг |
| **Editor** | Reader + Загрузка → Генерация → Visual Genome |
| **Admin** | Editor + Пользователи → Инвайты → Статистика → X-Ray |

### 1.3 Скрытые функции

1. **WebSocket** — 7 событий, user-specific доставка
2. **Visual Genome** — 5 вкладок, LLM-преобразование голоса
3. **Dark/Light theme** — CSS variables, localStorage
4. **Drag-and-drop загрузка** — pipeline-обработка
5. **Email-рассылки** — шаблоны, одобрение, отправка
6. **Краудфандинг** — прогресс-бары, майлстоуны
7. **X-Ray** — графы трейсов, SSE-стриминг

---

## ЭТАП 2: Архитектура и Технологический стек

### 2.1 Стек

| Компонент | Технология | Обоснование |
|---|---|---|
| **Фреймворк** | **Next.js 14+ (App Router)** | SSG для SEO, CSR для авторизованных |
| **UI-библиотека** | **Ant Design 5+** | Таблицы, формы, модалки, графы из коробки |
| **State Management** | **Zustand** | Легковесный (~1KB), простой API |
| **API-клиент** | **fetch + custom hooks** | Нативный, без лишних зависимостей |
| **Forms** | **React Hook Form + Zod** | Валидация, типизация |
| **WebSocket** | **Native + custom hook** | Уже реализовано на бэкенде |
| **Мобильное** | **React Native (Expo)** | Общий код с вебом |
| **Тестирование** | **Vitest + Playwright** | Unit + E2E |
| **Деплой** | **Cloudflare Pages** | SSG/ISR + Edge Functions |

### 2.1.1 Режим рендеринга: Гибрид SSG + CSR

| Тип страницы | Рендеринг | Примеры |
|---|---|---|
| **Публичные** | SSG (Static Site Generation) | About, Crowdfunding, Login |
| **Авторизованные** | CSR (Client-Side Rendering) | Chat, Profile, History, Admin |
| **SEO-важные** | ISR (Incremental Static Regeneration) | About (обновление раз в час) |

### 2.2 Архитектура: Feature-Sliced Design (FSD)

```
src/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout (nav, theme, providers)
│   ├── page.tsx            # Лендинг / redirect
│   ├── providers.tsx       # ThemeProvider, AuthProvider, WSProvider
│   └── globals.css         # Ant Design + Tailwind styles
│
├── pages/                  # Страницы (Next.js page.tsx)
│   ├── book/page.tsx       # Чат с книгой (SSR)
│   ├── about/page.tsx      # О книге (SSR)
│   ├── profile/page.tsx    # Профиль
│   ├── history/page.tsx    # История
│   ├── upload/page.tsx     # Загрузка
│   ├── visual/page.tsx     # Visual Genome
│   ├── admin/page.tsx      # Админ-панель
│   ├── crowdfunding/page.tsx # Краудфандинг
│   ├── login/page.tsx      # Авторизация
│   └── xray/page.tsx       # X-Ray дашборд
│
├── widgets/                # Сложные виджеты
│   ├── chat/               # Чат (MessageList, MessageInput, TypingIndicator)
│   ├── admin-panel/        # Админка (UsersTable, InvitesPanel, etc.)
│   ├── visual-editor/      # Visual Genome (SceneForm, CharacterForm, etc.)
│   └── upload-zone/        # Загрузка (DropZone, ProgressBar)
│
├── features/               # Пользовательские действия
│   ├── auth/               # Login, Logout, Session
│   ├── chat/               # Send message, Receive response
│   ├── user-management/    # CRUD пользователей
│   ├── invite-system/      # Инвайт-ссылки
│   ├── email-subscription/ # Подписка
│   ├── document-upload/    # Загрузка документов
│   ├── visual-scene/       # Создание сцен
│   ├── visual-character/   # Визуалы персонажей
│   ├── visual-location/    # Визуалы локаций
│   └── draft-approval/     # Утверждение черновиков
│
├── entities/               # Бизнес-сущности (API + types)
│   ├── user/
│   ├── book/
│   ├── message/
│   ├── draft/
│   ├── invite/
│   ├── session/
│   ├── api-key/
│   ├── suggestion/
│   ├── visual/
│   ├── campaign/
│   └── trace/
│
├── shared/                 # Переиспользуемые компоненты
│   ├── ui/                 # Ant Design wrappers + custom components
│   ├── lib/                # api.ts, ws.ts, formatters, hooks
│   ├── config/             # API URLs, feature flags
│   └── types/              # TypeScript типы
│
└── public/                 # Статика
```

### 2.3 Стратегия асинхронности

| Паттерн | Реализация |
|---|---|
| API-клиент | `api.ts` — fetch + JWT + error handling + retry |
| Кэширование | `@tanstack/react-query` — серверный стейт, кэш, рефеч |
| WebSocket | `useWebSocket` hook — reconnect, heartbeat, event routing |
| Optimistic updates | React Query mutation + rollback |
| Streaming | SSE через `/v1/stream` для чата |
| Loading states | Next.js Suspense + loading.tsx |

### 2.4 Структура папок

```
arkaim-web/
├── src/
│   ├── app/               # Next.js App Router (10 страниц)
│   ├── pages/             # Страницы
│   ├── widgets/           # 4 виджета
│   ├── features/          # 10 фич
│   ├── entities/          # 11 сущностей
│   ├── shared/            # UI-kit, утилиты
│   └── public/            # Статика
├── tests/
│   ├── unit/              # Vitest
│   └── e2e/               # Playwright
├── package.json
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts
└── antd.config.ts
```

---

## ЭТАП 3: Декомпозиция функций (Feature Breakdown)

### 3.1 Чат с книгой

| Компонент | Описание | Стор |
|---|---|---|
| `ChatWidget` | Виджет чата (layout + messages + input) | chat |
| `MessageList` | Virtual scroll, auto-scroll | messages |
| `MessageInput` | Валидация, отправка, индикатор | — |
| `MessageBubble` | Пузырь (user/book) + markdown | — |
| `TypingIndicator` | «Книга думает...» | — |
| `BookSidebar` | Жанр, темы, топики | book, reader |
| **API:** `POST /book/ask`, `GET /book/genome`, `GET /book/reader/profile` |
| **WebSocket:** `chat_response`, `new_question` |

### 3.2 Админ-панель

| Компонент | Описание | Стор |
|---|---|---|
| `AdminWidget` | 7 вкладок (Ant Design Tabs) | — |
| `UsersTable` | Ant Design Table + CRUD | users |
| `UserDrawer` | Drawer для деталей | users |
| `InvitesPanel` | Создание + список | invites |
| `SessionsTable` | Список + revoke | sessions |
| `ApiKeysTable` | Список + revoke | apiKeys |
| `SuggestionsList` | Одобрение/отклонение | suggestions |
| `StatsGrid` | Статистика | stats |
| **API:** 15+ эндпоинтов `/auth/admin/*` |

### 3.3 Профиль

| Компонент | Описание | Стор |
|---|---|---|
| `ProfileWidget` | Страница профиля | — |
| `TopicChart` | Ant Design Progress + Radar | profile |
| `EmailForm` | Ant Design Form | — |
| `ApiKeySection` | Ant Design Input + Button | apiKeys |
| **API:** `/book/reader/profile`, `/auth/api-key`, `/book/email/subscribe` |

### 3.4 Visual Genome

| Компонент | Описание | Стор |
|---|---|---|
| `VisualEditorWidget` | 5 вкладок | — |
| `SceneForm` | Ant Design Form + Select | — |
| `CharacterForm` | Ant Design Form | — |
| `LocationForm` | Ant Design Form | — |
| `VoiceInput` | Textarea + Button | — |
| `ImageInput` | Upload + Button | — |
| **API:** `/book/visualize`, `/book/visual-genome/*` |

### 3.5 Загрузка документов

| Компонент | Описание | Стор |
|---|---|---|
| `UploadWidget` | Ant Design Upload (drag-and-drop) | — |
| `FileTypeSelect` | Ant Design Select | — |
| `ProgressBar` | Ant Design Progress | — |
| `ResultCard` | Ant Design Result | — |
| **API:** `POST /book/os/pipeline/ingest` |

### 3.6 Краудфандинг

| Компонент | Описание | Стор |
|---|---|---|
| `CrowdfundingWidget` | Страница кампаний | — |
| `CampaignCard` | Ant Design Card + Progress | campaigns |
| `MilestoneList` | Ant Design Timeline | campaigns |
| **API:** `/book/crowdfunding/status` |

### 3.7 История

| Компонент | Описание | Стор |
|---|---|---|
| `HistoryWidget` | Страница истории | — |
| `HistoryStats` | Ant Design Statistic | history |
| `SessionFilter` | Ant Design Select | history |
| `QuestionList` | Ant Design List | history |
| `ConversationView` | Ant Design Timeline | history |
| **API:** `/book/reader/history/*` |

---

## ЭТАП 4: Пошаговый план разработки (Roadmap)

### Фаза 0: Настройка окружения (1 неделя)

| Задача | Описание | DoD |
|---|---|---|
| 0.1 | `npx create-next-app` + TypeScript | Проект запускается |
| 0.2 | Ant Design 5 + конфигурация темы | Ant Design работает |
| 0.3 | Tailwind CSS + dark theme | Dark mode переключается |
| 0.4 | React Router (Next.js App Router) | Маршруты настроены |
| 0.5 | `api.ts` — fetch + JWT + error handling | API-клиент готов |
| 0.6 | `ws.ts` — WebSocket клиент | WS подключается |
| 0.7 | Shared UI (Ant Design wrappers) | Кнопки, формы, таблицы доступны |
| 0.8 | Vitest + Playwright настройка | Тесты запускаются |
| 0.9 | Cloudflare Pages деплой | Автоматический деплой из Git |

### Фаза 1: Авторизация + Layout (2 недели)

| Задача | Описание | DoD |
|---|---|---|
| 1.1 | LoginPage — Telegram + Google OAuth | Вход работает |
| 1.2 | AuthProvider — JWT хранение, auto-refresh | Сессия управляется |
| 1.3 | AppShell — Ant Design Layout + Menu | Навигация работает |
| 1.4 | ProtectedRoute + RoleGuard | RBAC работает |
| 1.5 | ProfilePage — профиль читателя | Темы, статистика, email |
| 1.6 | ThemeToggle — dark/light (Ant Design config) | Тема переключается |

### Фаза 2: Core-фичи (3 недели)

| Задача | Описание | DoD |
|---|---|---|
| 2.1 | ChatWidget — чат с книгой | Чат работает |
| 2.2 | MessageList — virtual scroll | Производительность OK |
| 2.3 | Markdown rendering в ответах | Код блоки, списки |
| 2.4 | AboutPage — genome карточки (Ant Design Cards) | Данные отображаются |
| 2.5 | HistoryPage — история вопросов | Фильтр, поиск |
| 2.6 | WebSocket — real-time уведомления | Toast для событий |

### Фаза 3: Сложные фичи (4 недели)

| Задача | Описание | DoD |
|---|---|---|
| 3.1 | AdminWidget — все 7 вкладок (Ant Design Tabs) | CRUD работает |
| 3.2 | UsersTable — batch actions, export (Ant Design Table) | Массовые операции |
| 3.3 | InviteSystem — создание, копирование | Инвайты работают |
| 3.4 | VisualEditorWidget — 5 вкладок | Визуал-редактор |
| 3.5 | UploadWidget — Ant Design Upload + Progress | Загрузка работает |
| 3.6 | CrowdfundingWidget — кампании | Отображается |
| 3.7 | XRayPage — графы трейсов | Дашборд работает |

### Фаза 4: Мобильное приложение (4 недели)

| Задача | Описание | DoD |
|---|---|---|
| 4.1 | React Native (Expo) инициализация | Expo запускается |
| 4.2 | Общий код (entities, lib) | 60%+ переиспользования |
| 4.3 | ChatScreen — чат с книгой | Чат работает |
| 4.4 | ProfileScreen — профиль | Профиль работает |
| 4.5 | HistoryScreen — история | История работает |
| 4.6 | Push-уведомления | WebSocket → Push |
| 4.7 | Deep linking | Ссылки открывают экраны |

### Фаза 5: Оптимизация + Тестирование (2 недели)

| Задача | Описание | DoD |
|---|---|---|
| 5.1 | Performance (Lighthouse > 90) | Метрики OK |
| 5.2 | Accessibility (WCAG 2.1 AA) | ARIA, keyboard nav |
| 5.3 | E2E тесты (Playwright) — 15+ сценариев | Критический путь |
| 5.4 | Unit тесты (Vitest) — 80%+ coverage | Покрытие OK |
| 5.5 | Error boundary | Ошибки не ломают UI |
| 5.6 | Lazy loading + code splitting | Bundle < 200KB |

---

## ЭТАП 5: Риски и Вопросы

### 5.1 Слепые зоны

1. **OpenAPI устарел** — покрывает 8 из ~100+ эндпоинтов
2. **Нет документации WebSocket** — 7 событий не описаны
3. **Email-черновики** — API есть, UI нет
4. **X-Ray дашборд** — статические HTML, не интегрированы
5. **Нет client-side rate limiting** — нет throttle для API-вызовов

### 5.2 Риски

| Риск | Митигация |
|---|---|
| Next.js + Ant Design = тяжёлый bundle | Tree shaking, dynamic imports, lazy loading |
| React Native = отдельный код | Общий слой entities/lib, ~60% переиспользования |
| Миграция с Jinja2 = 3-4 месяца | Поэтапная, не все сразу |
| Cloudflare Pages = нет серверного кода | API на бэкенде, фронтенд — статика + SSR |

### 5.3 Вопросы

1. **Бэкенд на том же сервере?** Next.js SSR нуждается в Node.js сервере. Cloudflare Pages = только статика + Edge Functions. Нужно ли SSR или SSG?
2. **Ant Design bundle size** — ~1MB. Нужен ли code splitting для экономии?
3. **Мульти-tenant** — планируется ли поддержка нескольких книг на одной платформе?
