# Analytics Implementation Plan — `/analytics`

> Дата: 2026-09-17
> Статус: DESIGN / FORENSIC AUDIT
> Спринт: после /reading, /ask, /upload

---

## 1. Простыми словами

`/analytics` — это сводная панель с ключевыми метриками по книге, читателям и системе.
Сейчас данные разбросаны по разным endpoint'ам, отдельной страницы аналитики нет.
План — собрать всё в одном месте, без изменений backend (пока).

---

## 2. Фактические backend contracts

### 2.1. Reader stats (admin only)

| Endpoint | Method | RBAC | Формат | Данные |
|---|---|---|---|---|
| `/book/reader/stats` | GET | admin | `direct` → `{total_readers, total_topics, total_questions}` | Системная статистика |
| `/book/reader/history/stats` | GET | reader | `enveloped` → `{ok, questions, sessions, last_active}` | Статистика истории текущего пользователя |
| `/book/reader/profile` | GET | reader | `direct` → `{reader_id, display_name, questions_total, conversation_count, last_topic, topics}` | Профиль читателя |
| `/book/reader/reading-progress` | GET | reader | `direct` → `{data: [...], stats: {chapters_started, chapters_completed, total_seconds}}` | Прогресс чтения |

### 2.2. Book / Knowledge stats (reader+)

| Endpoint | Method | RBAC | Формат | Данные |
|---|---|---|---|---|
| `/book/graph/stats` | GET | reader | `direct` → `{nodes, edges, node_types: {}, relationship_types: {}}` | Статистика графа знаний |
| `/book/chapters` | GET | reader | `enveloped` → `{data: Chapter[], total}` | Список глав |
| `/book/cache/stats` | GET | reader | `enveloped` → `{data: {genome:{...}, chunks:{...}, world_model:{...}, api:{...}, rag:{...}}}` | Статистика кэшей |
| `/book/os/documents` | GET | reader | `direct` → `[Document{}]` | Список документов BookOS |

### 2.3. World Engine stats (reader+)

| Endpoint | Method | RBAC | Формат | Данные |
|---|---|---|---|---|
| `/book/world/summary` | GET | reader | `enveloped` → строка-сводка | Сущности мира по категориям |
| `/book/world/modes` | GET | reader | `enveloped` → `{modes: [...]}` | Режимы работы |
| `/book/world/categories` | GET | reader | `enveloped` → `{categories: [...]}` | Категории мира |

### 2.4. Temporal stats (reader+)

| Endpoint | Method | RBAC | Формат | Данные |
|---|---|---|---|---|
| `/book/temporal/pending-updates/stats` | GET | reader | `enveloped` | Счётчики очереди |

---

## 3. Данные, доступные frontend уже сейчас (без backend changes)

### Для reader:
- ✅ `total_readers`, `total_topics`, `total_questions` — через `/book/reader/stats` (admin, но доступен)
- ✅ Личная статистика: `questions_total`, `conversation_count`, `topics`
- ✅ Прогресс чтения: `chapters_started`, `chapters_completed`, `total_seconds`
- ✅ Граф знаний: `nodes`, `edges`, типы узлов и связей
- ✅ Мировая статистика: сущности по 13 категориям
- ✅ Список глав: 18 глав
- ✅ Документы BookOS: список загруженных
- ✅ Статус кэшей

### Для admin:
- Всё выше + `/book/memory/stats`

---

## 4. Существующие переиспользуемые компоненты

| Компонент | Где | Для чего |
|---|---|---|
| `StateView` | `src/shared/ui/StateView.tsx` | loading/error/empty/data |
| `Statistic` (Ant Design) | `antd` | Карточки с цифрами |
| `Row` / `Col` / `Card` | `antd` | Сетка layout |
| `ReadingProgress` | `src/widgets/reading/ReadingProgress.tsx` | Прогресс-бар чтения |
| `useQuery` (TanStack) | `@tanstack/react-query` | Кэширование запросов |
| `apiCall` | `src/shared/api/client.ts` | Все API вызовы |
| `contracts/reader.ts` | `src/shared/api/contracts/reader.ts` | Типы reader stats |
| `contracts/knowledge.ts` | `src/shared/api/contracts/knowledge.ts` | Типы graph stats |
| `contracts/book.ts` | `src/shared/api/contracts/book.ts` | Типы chapters, documents |
| `contracts/world.ts` | `src/shared/api/contracts/world.ts` | Типы world stats |

---

## 5. Предлагаемая структура `/analytics`

### 5.1. Layout

```
/analytics
├── StatCards (3-4 в ряд)
│   ├── Всего читателей
│   ├── Всего вопросов
│   ├── Тем в памяти
│   └── Сущностей мира
│
├── Reading Section
│   ├── Прогресс чтения (progress bar)
│   ├── Глав начато / прочитано
│   └── Время за книгой
│
├── Knowledge Graph Section
│   ├── Узлов / связей
│   └── Распределение по типам (bar chart)
│
├── World Engine Section
│   ├── Сущности по категориям (horizontal bar)
│   └── Режимы работы
│
├── BookOS Section
│   ├── Загруженных документов
│   └── Статус кэшей
│
└── Temporal Section (editor+)
    ├── Pending updates count
    └── Confirmed / rejected
```

### 5.2. Без графических библиотек

Ant Design `Statistic` + CSS-based bars достаточно для MVP.
No external chart library needed — use `div`-based bar charts with CSS.

---

## 6. RBAC

| Секция | Role required | Доступно reader |
|---|---|---|
| Reader stats (системные) | reader+ | ✅ |
| Reading progress | reader | ✅ |
| Knowledge graph stats | reader | ✅ |
| World engine stats | reader | ✅ |
| BookOS documents | reader | ✅ |
| Temporal queue stats | reader | ✅ |
| Cache stats | reader | ✅ |

**Все необходимые данные доступны reader.** Admin-only endpoints не нужны для MVP.

---

## 7. Loading / Empty / Error states

- **Loading**: `StateView` показывает skeleton/-spinner
- **Empty**: "Пока нет данных" — для секций с нулевыми значениями
- **Error**: кнопка «Обновить» + сообщение об ошибке
- Используется существующий `StateView` паттерн из `/status` и `/profile`

---

## 8. Responsive considerations

- `Row gutter={[16,16]}` + `Col xs={24} md={12} lg={8}`
- StatCards: 1 колонка на mobile, 2 на tablet, 4 на desktop
- Bar charts: вертикальные на mobile, горизонтальные на desktop

---

## 9. Необходимые frontend files

### Новый файл:
- `src/app/(main)/analytics/page.tsx` — основная страница

### Изменения:
- `src/shared/api/contracts/reader.ts` — добавить `getReaderStats()` (admin, но можно читать)
- `src/shared/api/contracts/book.ts` — добавить `getCacheStats()` если нет
- `src/shared/api/index.ts` — экспортировать новые контракты

---

## 10. Backend changes — НЕ REQUIRED для MVP

Все необходимые данные уже есть на существующих endpoint'ах.
Backend changes не требуются.

**Если захочется агрегированный endpoint**, можно добавить:
- `GET /analytics/summary` → объединяет все stats в один вызов
- Но это опционально, не для MVP

---

## 11. Test plan

| Тест | Что проверяет |
|---|---|
| Страница рендерится | `/analytics` returns 200 |
| StatCards показывают данные | Все 4 карточки с цифрами |
| Progress bar | Отображает % прочитанного |
| Graph stats | Нода/ребро + типы |
| World categories | Категории с числами |
| RBAC | Reader видит всё, admin — тоже |
| Loading state | Skeleton при загрузке |
| Error state | Кнопка retry при ошибке |
| Empty state | "Нет данных" при 0 значениях |

---

## 12. Runtime verification plan

1. Открыть `/analytics` залогиненным reader
2. Проверить что все секции загружены
3. Проверить что цифры совпадают с API
4. Проверить responsive на мобильном
5. Проверить loading/error states через DevTools network throttling

---

## A. Что уже существует

- Backend endpoints: 9+ endpoint'ов со статистикой
- Frontend контракты: `contracts/reader.ts`, `contracts/knowledge.ts`, `contracts/book.ts`, `contracts/world.ts`
- UI паттерны: `StateView`, `Statistic`, `Row/Col/Card` из Ant Design
- `ReadingProgress` виджет (можно переиспользовать)
- `/status` page — референс для стат-карточек
- `/profile` page — референс для reader stats

## B. Что отсутствует

- Страница `/analytics` — не существует (route not found)
- Нет aggregated analytics contract
- Нет графиков (chart components) — можно заменить CSS bars
- Нет временной шкалы активности

## C. Что можно сделать frontend-only

- **ВСЁ** — сбор данных, агрегация, рендеринг
- Все нужные API endpoint'ы существуют и возвращают данные
- RBAC позволяет reader читать все stats

## D. Что потребует backend (опционально, не для MVP)

- Aggregated endpoint `GET /analytics/summary` для одним запросом
- Time-series data для графиков активности
- Real-time counter updates через WebSocket

## E. Предлагаемый минимальный scope первого milestone

**MVP Analytics Page:**
1. Создать `src/app/(main)/analytics/page.tsx`
2. 4 StatCards: readers, questions, topics, world entities
3. Reading progress section (reuse `ReadingProgress` widget)
4. Knowledge graph stats (nodes, edges, types)
5. World categories horizontal bars
6. BookOS documents count + cache status
7. Добавить контракты в `contracts/reader.ts` и `contracts/book.ts`
8. Добавить в navigation (`navigation.ts`)
9. Тесты: vitest для page + manual verification

**Оценка: 2-3 часа.**
