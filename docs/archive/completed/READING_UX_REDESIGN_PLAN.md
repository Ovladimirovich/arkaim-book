# Reading UX Redesign Plan

**Статус:** АУДИТ + ПЛАН (не реализация)
**Дата:** 2026-07
**Файл:** `docs/READING_UX_REDESIGN_PLAN.md`
**Scope:** Только UX/UI-план для `/reading` (arkaim-web-v2). Без реализации, без backend-изменений.

---

## 1. Executive Summary

**Цель аудита:** понять, каким должен быть действительно качественный Reading UX, опираясь на существующий проект, и подготовить план его реализации.

**Ключевой вывод:** текущий Reading в `arkaim-web-v2` — это CRUD-лист глав с пагинацией текста. Он не выполняет роль отправной точки пользовательского взаимодействия с Arkaim. Нет ощущения книги. Нет связи «книга → контекст → вопрос → возвращение к книге». Нет навигации по оглавлению при чтении. Нет контроля типографики. Интерфейс конкурирует с функционалом вместо того, чтобы помогать чтению.

**Рекомендация:** перестроить Reading как **read-first surface** — минималистичная панель чтения с боковым оглавлением, навигацией по главам, контекстными действиями и плавным переходом к диалогу с книгой. Сохранить существующие backend-контракты (`/book/chapters`, `/book/text`, `/book/reader/*`). Переписать фронтенд-компоненты, не меняя архитектуру.

---

## 2. Фактическое состояние текущего Reading

### 2.1 Код (arkaim-web-v2)

**Файл:** `arkaim-web-v2/src/app/(main)/reading/page.tsx` (288 строк)

Два состояния:
1. **Список глав** — `List` Ant Design с кнопками «читать/продолжить», прогресс-барами
2. **Режим чтения** — одна глава, текст чанками по 4000 символов, кнопка «Загрузить ещё», кнопка «Глава прочитана»

### 2.2 Что есть

| Элемент | Статус | Комментарий |
|---------|--------|-------------|
| Список глав (`/book/chapters`) | ✅ Работает | Отображает title, char_count, index |
| Чтение главы (`/book/text`) | ⚠️ Функционально | Пагинация чанками 4000 символов, «Загрузить ещё» вручную |
| Прогресс (`/book/reader/reading-progress`) | ✅ Работает | scroll_percent по главе |
| Позиция («продолжить») (`/book/reader/reading-position`) | ✅ Работает | Показывает последнюю главу |
| Трекинг события (`/book/reader/reading-event`) | ✅ Работает | Fire-and-forget |
| Навигация «← К оглавлению» | ✅ Есть | Возврат к списку глав |
| Индикатор загруженности текста | ✅ Есть | «Загружено X из Y символов» |
| Отметка «глава прочитана» | ✅ Есть | POST reading-event с completed=true |
| Состояния загрузки/ошибки/пустоты | ✅ Есть | StateView |
| Responsive | ❌ Нет | Фиксированный maxWidth: 760px, нет адаптивности |
| Настройки шрифта | ❌ Нет | Фиксированный fontSize: 17 |
| Оглавление при чтении | ❌ Нет | Нет side-panel с главами |
| Навигация «предыдущая/следующая глава» | ❌ Нет | Только кнопка «назад» |
| Связь с диалогом «Спросить книгу» | ❌ Нет | Пользователь должен выйти и перейти на / |
| Контекст главы (genome, граф) | ❌ Нет | Нет связи с /library, /graph |
| Тёмная тема | ❌ Нет | Фиксированные цвета |
| Progress bar в тексте | ❌ Нет | Прогресс только в списке глав |

### 2.3 Что работает реально

- Загрузка списка глав — стабильно
- Выбор главы и загрузка первого чанка — стабильно
- Кнопка «Главa прочитана» — работает, инвалидит query
- Карточка «Продолжить» — показывает последнюю позицию
- Scroll-based tracking — вычисляется корректно (scrollPercentRef)

### 2.4 Что является визуальным каркасом

- Весь дизайн — inline-styles, Ant Design default (без кастомизации)
- Нет единой визуальной системы
- Нет ощущения «книги»

---

## 3. UX-проблемы — с конкретными примерами

### 3.1 Нет ощущения книги

**Проблема:** Reading выглядит как админка. Карточки Ant Design, стандартные Typography.Title/Paragraph, inline styles.

**Пример из кода (строки 167-228):**
```tsx
<div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
  <Title level={3}>Чтение</Title>
  <Paragraph type="secondary">Читайте книгу по главам...</Paragraph>
  <Card size="small">...</Card>
  <List ... />
```

**Влияние:** Пользователь входит в Arkaim и видит стандартный CRUD-интерфейс. Нет ощущения погружения в книгу.

### 3.2 Нет навигации по книге при чтении

**Проблема:** Когда пользователь читает главу, он видит только кнопку «← К оглавлению». Нет быстрого перехода между главами, нет индикатора текущей позиции.

**Пример (строка 236):**
```tsx
<Button type="link" style={{ padding: 0, alignSelf: 'flex-start' }} onClick={backToList}>
  ← К оглавлению
</Button>
```

**Влияние:** Чтобы перейти к следующей главе, нужно: 1) нажать «К оглавлению», 2) найти нужную главу в списке, 3) нажать «читать». 3 клика вместо 1.

### 3.3 Нет управления типографикой

**Проблема:** Фиксированный `fontSize: 17` (строка 255). Нет выбора размера шрифта, межстрочного интервала, ширины колонки.

```tsx
<Paragraph key={i} style={{ whiteSpace: 'pre-wrap', fontSize: 17, lineHeight: 1.8 }}>
```

**Влияние:** Длительное чтение дискомфортно для пользователей с разным зрением и предпочтениями.

### 3.4 Нет связи с диалогом «Спросить книгу»

**Проблема:** Из режима чтения нет пути задать вопрос по книге. Пользователь должен: 1) выйти из чтения, 2) перейти на `/`, 3) ввести вопрос.

**Влияние:** Разрыв основного user journey: «читаю → возник вопрос → хочу спросить → теряю контекст → начинаю с нуля».

### 3.5 Нет связи с контекстом (genome, граф, слои)

**Проблема:** При чтении главы нет доступа к информации о персонажах, темах, значениях, связанных с содержанием главы.

**Влияние:** Пользователь читает о персонаже, но не может узнать о нём больше без перехода на другую страницу.

### 3.6 Пагинация текста не UX-friendly

**Проблема:** Кнопка «Загрузить ещё» (строка 273). Пользователь должен сам решить, когда догрузить текст. Нет автодогрузки при скролле.

```tsx
{moreHasNext && firstPage?.has_more && moreChunks.length >= 0 && firstPage.data.length > 0 && (
  <Button onClick={() => void loadMore()}>Загрузить ещё</Button>
)}
```

**Влияние:** Текст обрывается произвольно. Пользователь может не заметить, что есть продолжение.

### 3.7 Нет индикатора прогресса внутри главы

**Проблема:** Прогресс отображается только в списке глав (Progress bar), но не в режиме чтения.

**Влияние:** Пользователь не знает, сколько осталось читать.

### 3.8 Индикатор загруженности текста вреден

**Проблема (строки 264-268):**
```tsx
<Paragraph type="secondary">
  Загружено {firstPage.limit + moreChunks...} из {firstPage.total} символов ({percent}%)
</Paragraph>
```

**Влияние:** Технический индикатор, который не несёт пользы пользователю. 116k символов — это статистика, а не помощь.

### 3.9 Layout не responsive

**Проблема:** `maxWidth: 760` — фиксировано. Нет адаптации под narrow window, планшет, мобильный.

**Влияние:** На узких экранах контент выходит за пределы или требует горизонтального скролла.

### 3.10 AppShell мешает чтению

**Проблема:** Sidebar + Header занимают место. При чтении длинного текста боковая панель отвлекает.

**AppShell.tsx (строки 52-96):**
```tsx
<Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={220}>
  ...
</Sider>
<Layout>
  <Header>...</Header>
  <Content style={{ padding: 24, maxWidth: 1100, width: '100%', margin: '0 auto' }}>
    {children}
  </Content>
</Layout>
```

**Влияние:** Reading surface ограничен 1100px — это много для текста, мало для side-by-side layouts.

---

## 4. Пользовательский сценарий

### Сценарий: «Первое знакомство с Arkaim»

| Этап | Что видит пользователь | Что понимает | Что непонятно | Куда нажимает | Когнитивная нагрузка | Что мешает |
|------|------------------------|--------------|---------------|---------------|---------------------|------------|
| 1. Вход в Arkaim | Home page (`/`) — чат с книгой | «Это диалог с книгой» | «Где сама книга?» | «Чтение» в sidebar | Низкая | — |
| 2. Переход в Reading | Список глав (Ant Design List) | «Список глав» | «Почему это выглядит как админка?» | Кнопка «читать» у первой главы | Средняя | Нет ощущения книги |
| 3. Чтение главы | Текст в карточке, кнопка «Загрузить ещё» | «Читаю текст» | «Где оглавление? Как перейти к следующей главе?» | Скролл вниз, кнопка «Загрузить ещё» | Высокая | Нет навигации, нет автодогрузки |
| 4. Возник вопрос | Текст продолжается | «Хочу спросить о персонаже» | «Как спросить, не теряя контекст?» | Кнопка «← К оглавлению» → `/` → ввод вопроса | Высокая | Разрыв flow |
| 5. Возврат к чтению | Список глав | «Где я остановился?» | «Какая глава была последней?» | Кнопка «читать» / «продолжить» | Средняя | Нет индикатора прогресса в тексте |
| 6. Длительное чтение | Текст, фиксированный шрифт | «Нужно изменить размер» | «Где настройки?» | — | Высокая | Нет control panel |

### Ключевые инсайты:

1. **Reading — это не «ещё одна страница»**. Это точка входа. 80% пользователей начнут с чтения.
2. **Нет связности между чтением и диалогом**. Это главный разрыв UX.
3. **Нет ощущения книги**. CRUD-паттерн убивает нарратив.
4. **Навигация по книге отсутствует**. 3 клика вместо 1.
5. **Нет контроля над комфортным чтением**. Шрифт, ширина, межстрочный интервал — всё фиксировано.

---

## 5. Целевая концепция Reading

### 5.1 Основная идея

**Reading как read-first surface.** Главное — текст книги. Остальное — вторично, доступно по запросу.

### 5.2 Структура экрана

```
┌─────────────────────────────────────────────────────────────┐
│  [☰] Arkaim v2                    📖 Оглавление  🔍  ⚙️    │  ← Topbar (минималистичный)
├──────────────┬──────────────────────────────────────────────┤
│              │                                               │
│  ОГЛАВЛЕНИЕ  │  РЕЖИМ ЧТЕНИЯ                                 │
│              │                                               │
│  ─────────   │  ┌─────────────────────────────────────┐     │
│  ◀ Глава 1   │  │  Глава 1. Название главы            │     │
│  ▶ Глава 2   │  │                                     │     │
│    Глава 3   │  │  Текст книги...                     │     │
│    Глава 4   │  │  Текст книги...                     │     │
│    Глава 5   │  │  Текст книги...                     │     │
│              │  │  (автодогрузка при скролле)          │     │
│  ─────────   │  │                                     │     │
│ 进度条       │  │  [◀ Пред.]  3/12  [След. ▶]         │     │
│              │  └─────────────────────────────────────┘     │
│              │                                               │
│              │  💬 Спросить о главе     📖 В геном          │
├──────────────┴──────────────────────────────────────────────┤
│  [📊 Прогресс: 25% книги]  [⏱ 45 мин]                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Принципы

1. **Книга — первична.** Текст занимает максимум пространства.
2. **Оглавление — рядом.** Sidebar с главами, сворачиваемый.
3. **Контекст — по запросу.** Кнопки «Спросить», «Геном» — вторичны, не мешают.
4. **Навигация — мгновенна.** «Пред. / След.» глава, клик по оглавлению.
5. **Автодогрузка.** Текст подгружается при скролле, без кнопки «Загрузить ещё».
6. **Прогресс — виден.** Индикатор внутри главы и общий прогресс внизу.
7. **Настройки — доступны.** Размер шрифта, ширина колонки, тема — в панели настроек.

### 5.4 Роли Reading в общей архитектуре

| Роль | Описание |
|------|----------|
| **Главный вход** | Первая страница после входа (опционально: редирект с `/` на `/reading` для reader) |
| **Точка возврата** | Из любого раздела (`/world`, `/library`, `/graph`) — кнопка «Вернуться к чтению» |
| **Контекст для диалога** | Кнопка «Спросить о главе» → `/` с pre-filled question context |
| **Связь с геномом** | Выделение персонажа/темы в тексте → переход в `/library` с фильтром |

---

## 6. Information Architecture

### 6.1 Навигационная модель

```
/reading (Чтение)
├── Список глав (TOC view)
│   ├── «Продолжить» карточка (position)
│   ├── Список всех глав
│   │   ├── Название + индекс
│   │   ├── Прогресс (если начато)
│   │   └── Кнопка «Читать / Продолжить»
│   └── Общий прогресс (stat)
│
└── Режим чтения (Reader view)
    ├── Topbar:
    │   ├── ☰ Sidebar toggle
    │   ├── Текущая глава (nav)
    │   ├── 🔍 Поиск по книге (future)
    │   └── ⚙️ Настройки (font, width, theme)
    │
    ├── Reading surface:
    │   ├── Название главы
    │   ├── Текст (автодогрузка)
    │   └── Progress bar (внутри главы)
    │
    ├── Navigation bar:
    │   ├── ◀ Пред. глава
    │   ├── X / Y (номер главы)
    │   └── След. глава ▶
    │
    └── Context actions (secondary):
        ├── 💬 Спросить о главе
        ├── 📖 В геном (глава → фильтры)
        └── 📊 Мой прогресс
```

### 6.2 Состояния Reading

| Состояние | Описание | Компонент |
|-----------|----------|-----------|
| **TOC (список глав)** | Начальное состояние | `ChapterList` |
| **Reading (чтение)** | Активное чтение главы | `ChapterReader` |
| **Loading** | Загрузка текста | `StateView` (existing) |
| **Error** | Ошибка загрузки | `StateView` (existing) |
| **Empty** | Нет глав | `StateView` empty |
| **Progress** | Показать прогресс | Inline stat bar |

### 6.3 Переходы между состояниями

```
[TOC] --(клик по главе)--> [Reading]
  ↑                              │
  │         ←(«К оглавлению»)───┘
  │
  └──(автопереход)──▶ [Reading] (при наличии position)
```

**Smart start:** Если есть сохранённая позиция → автоматический переход в Reading на последнюю главу. Иначе → показ TOC.

---

## 7. Component Architecture

### 7.1 Новые компоненты

| Компонент | Путь | Назначение |
|-----------|------|------------|
| `ChapterList` | `entities/reader/ChapterList.tsx` | Список глав с прогрессом |
| `ChapterReader` | `entities/reader/ChapterReader.tsx` | Режим чтения (текст + навигация) |
| `ReadingTOC` | `widgets/reading/ReadingTOC.tsx` | Боковое оглавление |
| `ReadingTopbar` | `widgets/reading/ReadingTopbar.tsx` | Минималистичный topbar |
| `ReadingSettings` | `widgets/reading/ReadingSettings.tsx` | Панель настроек (шрифт, ширина, тема) |
| `ReadingProgress` | `widgets/reading/ReadingProgress.tsx` | Индикатор прогресса |
| `ReadingContextActions` | `widgets/reading/ReadingContextActions.tsx` | Вторичные действия (спросить, геном) |

### 7.2 Изменение существующих компонентов

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| `AppShell` | Добавить `ReadingTopbar` для `/reading` | Убрать sidebar на время чтения |
| `StateView` | Без изменений | Уже подходит |
| `api/contracts/reader.ts` | Без изменений | Контракты достаточны |
| `api/contracts/book.ts` | Без изменений | Контракты достаточны |

### 7.3 Reuse existing

- `StateView` — loading/empty/error
- `api` calls — уже typed
- `useQuery` / `useMutation` — TanStack Query pattern

---

## 8. Navigation Model

### 8.1 Текущая навигация (проблема)

```
Sidebar → /reading → TOC view → Chapter click → Reading view
Reading view → "← К оглавлению" → TOC view → повтор
```

**Проблема:** 3 клика для перехода между главами. Нет «следующая/предыдущая».

### 8.2 Целевая навигация

```
Sidebar → /reading → (auto-continue or TOC)
Reading view:
  - Sidebar TOC (toggleable) → клик по главе
  - Bottom nav: ◀ Пред. | X/Y | След. ▶
  - Topbar: 📖 Оглавление | ⚙️ Настройки
  - Context: 💬 Спросить | 📖 Геном
```

### 8.3 Deep links

| URL | Поведение |
|-----|-----------|
| `/reading` | Smart start (позиция или TOC) |
| `/reading?chapter=ch_03` | Открыть конкретную главу |
| `/reading?continue=1` | Принудительный continue |

### 8.4 Back-navigation from other pages

Добавить в AppShell: кнопка «Вернуться к чтению» на `/world`, `/library`, `/graph` (если пользователь был в Reading).

---

## 9. State / Data Flow

### 9.1 Текущий state management

```
ChapterList: useState(chapter)
ChapterReader: useState(moreChunks, moreOffset, moreHasNext)
Scroll tracking: useRef(scrollPercentRef)
Reading event: useMutation(trackRead)
```

### 9.2 Целевой state management

```
ChapterList:
  - useQuery(['book', 'chapters'])
  - useQuery(['reader', 'position'])
  - useQuery(['reader', 'progress'])
  - useState(selectedChapterId)

ChapterReader:
  - useQuery(['book', 'text', chapterId, offset])
  - useInfiniteQuery для автодогрузки (или ручной offset с scroll listener)
  - useMutation для reading-event
  - useState для настроек (fontSize, columnWidth, theme)
  
Global:
  - zustand store для settings (font, width, theme) — только UI-state
```

### 9.3 Инвалидация кэша

```typescript
// После reading-event
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['reader', 'progress'] });
  queryClient.invalidateQueries({ queryKey: ['reader', 'position'] });
}
```

---

## 10. Visual / Typography System

### 10.1 Typography

| Элемент | Шрифт | Размер | Line-height | Weight |
|---------|-------|--------|-------------|--------|
| Заголовок главы | Georgia, serif | 24px | 1.4 | 600 |
| Основной текст | Georgia, serif | 18px (baseline) | 1.8 | 400 |
| Навигация | System UI | 14px | 1.5 | 500 |
| Мета-данные | System UI | 12px | 1.4 | 400 |
| Secondary text | System UI | 13px | 1.5 | 400 |

**Шрифты:** Georgia (readable serif для текста), system-ui (для UI).

### 10.2 Hierarchy

```
1. Название главы (h2, serif, centered)
2. Текст (paragraph, serif, justified or left)
3. Навигация (button, system font)
4. Мета-данные (secondary, muted)
```

### 10.3 Spacing

| Элемент | Padding | Margin |
|---------|---------|--------|
| Reading surface | 32px horizontal | 24px vertical |
| Chapter title | 0 | 16px bottom |
| Paragraph | 0 | 1.5em bottom |
| Navigation bar | 16px horizontal | 24px top/bottom |

### 10.4 Proportions

- **Reading column:** 680px (optimal for line length), max 72ch
- **TOC sidebar:** 260px collapsed, 300px expanded
- **Content area:** flex-1, min-width 320px

### 10.5 Colors

```css
/* Light theme */
--bg-primary: #faf9f6;      /* warm paper */
--bg-secondary: #ffffff;
--text-primary: #1a1a1a;
--text-secondary: #6b7280;
--accent: #2563eb;
--border: #e5e7eb;

/* Dark theme */
--bg-primary: #0f0f0f;
--bg-secondary: #1a1a1a;
--text-primary: #e5e5e5;
--text-secondary: #9ca3af;
--accent: #60a5fa;
--border: #2d2d2d;
```

### 10.6 Chapter title treatment

```tsx
<h2 style={{
  fontFamily: 'Georgia, serif',
  fontSize: 24,
  fontWeight: 600,
  lineHeight: 1.4,
  textAlign: 'center',
  marginBottom: 24,
  color: 'var(--text-primary)',
}}>
  {chapter.index + 1}. {chapter.title}
</h2>
```

### 10.7 Paragraph treatment

```tsx
<p style={{
  fontFamily: 'Georgia, serif',
  fontSize: 18,
  lineHeight: 1.8,
  marginBottom: '1.5em',
  textIndent: '2em',
  color: 'var(--text-primary)',
  whiteSpace: 'pre-wrap',
}}>
  {text}
</p>
```

---

## 11. Responsive Behavior

### 11.1 Breakpoints

| Breakpoint | Max width | Layout |
|------------|-----------|--------|
| Mobile | < 640px | TOC overlay, single column |
| Tablet | 640-1024px | Collapsed TOC, wider text |
| Desktop | > 1024px | Expanded TOC, optimal text width |

### 11.2 Mobile behavior

- TOC → full-screen overlay (drawer)
- Navigation → bottom bar
- Settings → modal
- Font size → auto-adjusted (16px baseline)

### 11.3 Narrow window behavior

- TOC → collapse to icon
- Text width → 100% (но max 72ch)
- Navigation → compact

---

## 12. Accessibility Considerations

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | Tab через главы, Enter для выбора |
| Screen reader | Semantic HTML (`<article>`, `<nav>`, `<h1>`) |
| Focus states | Visible focus ring на всех interactive elements |
| Color contrast | WCAG AA (4.5:1 for text) |
| Font scaling | User agent font-size respected |
| Reduced motion | `prefers-reduced-motion` → disable scroll animation |

---

## 13. Backend Contract Audit

### 13.1 Существующие контракты (достаточны)

| Endpoint | Метод | Данные | Статус |
|----------|-------|--------|--------|
| `/book/chapters` | GET | Список глав | ✅ |
| `/book/text` | GET | Текст главы (чанк) | ✅ |
| `/book/reader/reading-event` | POST | Событие чтения | ✅ |
| `/book/reader/reading-progress` | GET | Прогресс по главам | ✅ |
| `/book/reader/reading-position` | GET | Последняя позиция | ✅ |
| `/book/genome` | GET | Геном (для контекста) | ✅ |
| `/book/ask` | POST | Вопрос книге | ✅ |

### 13.2 Что можно реализовать только frontend

- Автодогрузка текста (IntersectionObserver)
- Настройки шрифта/ширины (localStorage)
- Навигация «пред. / след.» (список глав из `/book/chapters`)
- Контекстные действия (переход на `/`, `/library`)
- Оглавление в sidebar (список глав)

### 13.3 Backend gaps

| Gap | Обоснование | Приоритет |
|-----|-------------|-----------|
| Нет поиска по тексту книги | Для полноты UX нужен поиск внутри главы | Medium (можно сделать frontend search по загруженному тексту) |
| Нет anchor-навигации по главам | `/book/chapters/{id}` возвращает полную главу — это хорошо, но нет fragment navigation | Low |
| Нет semantic chunking | Текст делится по символам, не по параграфам | Medium (backend optimization, не blocker) |

**Рекомендация:** Gaps не блокируют redesign. Поиском можно заняться позже (frontend search по загруженному тексту).

---

## 14. Backend Gaps (обоснование)

### 14.1 Существующие gaps

1. **`/book/text` делит по символам, не по параграфам**
   - Факт: текст режется по `offset+limit` символов
   - Влияние: текст может обрезаться посередине абзаца
   - Рекомендация: не blocker, frontend может «дорезать» до конца параграфа

2. **Нет поиска по тексту книги**
   - Факт: `/book/knowledge/search` ищет по ExpansionLayer, не по raw text
   - Влияние: нельзя найти упоминание персонажа в тексте
   - Рекомендация: frontend search по загруженному тексту (in-memory)

3. **Нет semantic chapter boundaries**
   - Факт: `char_count` есть, но нет `paragraph_count` или `word_count`
   - Влияние: сложно показать «осталось 3 абзаца»
   - Рекомендация: не blocker, можно оценить по символу (средний абзац ~500 символов)

### 14.2 Что НЕ менять в бэкенде

- Endpoints оставить как есть
- Контракты не расширять
- RBAC не менять

---

## 15. Поэтапный план реализации

### Phase 1: Foundation (1 спринт)

| Задача | Компонент | Описание |
|--------|-----------|----------|
| Create `entities/reader` | — | API hooks для reading (reuse existing) |
| Create `widgets/reading/ReadingTopbar` | Topbar | Минималистичный topbar (toggle TOC, settings) |
| Create `widgets/reading/ReadingProgress` | Progress | Inline progress bar |
| Update `AppShell` | Shell | Skip sidebar on `/reading`, add ReadingTopbar |

**DoD:** Reading страница открывает topbar вместо стандартного AppShell header.

### Phase 2: TOC + Reader (1 спринт)

| Задача | Компонент | Описание |
|--------|-----------|----------|
| Create `entities/reader/ChapterList` | List | Список глав с прогрессом |
| Create `widgets/reading/ReadingTOC` | TOC | Sidebar с главами, click-to-navigate |
| Create `entities/reader/ChapterReader` | Reader | Режим чтения с автодогрузкой |
| Migrate `page.tsx` | Page | Перевести на новые компоненты |

**DoD:** Reading страница показывает TOC + Reading view. Можно переключаться между главами.

### Phase 3: Navigation + Context (1 спринт)

| Задача | Компонент | Описание |
|--------|-----------|----------|
| Add prev/next navigation | Reader | Кнопки «Пред. / След. глава» |
| Add context actions | Reader | «Спросить о главе», «В геном» |
| Implement scroll tracking | Reader | Автообновление scroll_percent |
| Auto-load more on scroll | Reader | IntersectionObserver для догрузки |

**DoD:** Навигация между главами работает. Контекстные действия ведут на `/` и `/library`.

### Phase 4: Polish (0.5 спринт)

| Задача | Компонент | Описание |
|--------|-----------|----------|
| Typography controls | Settings | Размер шрифта, ширина колонки |
| Theme support | Settings | Светлая / тёмная тема |
| Responsive layout | All | Mobile/tablet adaptation |
| Accessibility audit | All | Keyboard nav, screen reader |

**DoD:** Reading работает на мобильных, доступен для keyboard users.

---

## 16. Acceptance Criteria

### 16.1 Функциональные

| # | Критерий | Как проверить |
|---|----------|---------------|
| 1 | Reading открывается со smart start (позиция или TOC) | Нет сохранённой позиции → TOC; есть → Reading |
| 2 | TOC показывает список всех глав с прогрессом | Сравнить с `/book/chapters` + `/book/reader/progress` |
| 3 | Клик по главе в TOC → Reading этой главы | Проверить URL и контент |
| 4 | Кнопки «Пред. / След.» работают | Переход между главами |
| 5 | Автодогрузка текста при скролле | Текст подгружается без кнопки |
| 6 | «Спросить о главе» → `/` с контекстом | Проверить pre-filled question |
| 7 | «В геном» → `/library` с фильтром | Проверить URL params |
| 8 | Настройки шрифта сохраняются | localStorage, перезагрузка страницы |
| 9 | Progress обновляется при скролле | `reading-progress` endpoint получает актуальные данные |
| 10 | Reading works on mobile | Viewport < 640px, TOC overlay |

### 16.2 Нефункциональные

| # | Критерий | Как проверить |
|---|----------|---------------|
| 11 | 0 ошибок TypeScript | `tsc --noEmit` |
| 12 | 0 lint errors | `npm run lint` |
| 13 | StateView используется везде | Code review |
| 14 | Нет строковых API-путей вне `shared/api` | ESLint rule |
| 15 | Backend не изменён | Git diff `runtime/core/` пустой |

---

## 17. Test Strategy

### 17.1 Unit tests

| Тест | Что проверяет |
|------|---------------|
| `ChapterList.test.tsx` | Рендер списка, прогресс, клик по главе |
| `ChapterReader.test.tsx` | Загрузка текста, навигация, автодогрузка |
| `ReadingTOC.test.tsx` | Toggle sidebar, highlight active chapter |
| `ReadingSettings.test.tsx` | Font size change, persistence |

### 17.2 E2E tests (Playwright)

| Сценарий | Steps |
|----------|-------|
| S1: Reading start | `/reading` → TOC visible → click chapter → Reading view |
| S2: Continue reading | Set position → `/reading` → auto-continue to last chapter |
| S3: Navigate chapters | Click prev/next → URL changes → text updates |
| S4: Context actions | Click «Спросить» → redirect to `/` with context |
| S5: Mobile layout | Viewport 375px → TOC overlay → close |

---

## 18. Что НЕ нужно делать в этой фазе

| Запрещено | Обоснование |
|-----------|-------------|
| Реализация нового Reading UI | Это следующий шаг, после GO |
| Массовый рефакторинг frontend | Вне scope |
| Изменения backend | Backend contracts достаточны |
| Изменения Arkaim data model | Вне scope |
| Изменения temporal/event system | Вне scope |
| Studio, arkaim-media, ComfyUI | Вне scope |
| Генерация изображений/видео/звука | Вне scope |
| Новые функции только ради расширения интерфейса | Противоречит принципу «книга первична» |
| Тёмная тема (как отдельная feature) | В Phase 4, как часть polish |
| Поиск по тексту книги (backend) | Можно сделать frontend search позже |
| Интеграция с World Explorer | Вне scope Reading UX |

---

## 19. Финальный отчёт

### 19.1 Что сейчас реально плохо

1. **Нет ощущения книги** — Reading выглядит как админка
2. **Нет навигации** — 3 клика вместо 1 для перехода между главами
3. **Нет связи с диалогом** — разрыв «читаю → хочу спросить → теряю контекст»
4. **Нет управления типографикой** — фиксированный шрифт, нет настроек
5. **Нет автодогрузки** — кнопка «Загрузить ещё» не UX-friendly
6. **Не responsive** — фиксированный layout для всех экранов
7. **Технические индикаторы** — «Загружено X из Y символов» не несёт пользы

### 19.2 Что уже можно сохранить

- Backend endpoints (`/book/chapters`, `/book/text`, `/book/reader/*`)
- StateView компонент (loading/empty/error)
- TanStack Query pattern
- ApiError handling
- RBAC navigation structure
- AppShell (частично — добавить ReadingTopbar)

### 19.3 Что нужно переделать

| Компонент | Что изменить |
|-----------|--------------|
| `page.tsx` | Полностью переписать на новые компоненты |
| `AppShell` | Добавить ReadingTopbar для `/reading` |
| Дизайн | Читать-first, минималистичный, сserif typography |

### 19.4 Какие компоненты нужно создать

| Компонент | Путь | Статус |
|-----------|------|--------|
| `ChapterList` | `entities/reader/ChapterList.tsx` | Новый |
| `ChapterReader` | `entities/reader/ChapterReader.tsx` | Новый |
| `ReadingTOC` | `widgets/reading/ReadingTOC.tsx` | Новый |
| `ReadingTopbar` | `widgets/reading/ReadingTopbar.tsx` | Новый |
| `ReadingSettings` | `widgets/reading/ReadingSettings.tsx` | Новый |
| `ReadingProgress` | `widgets/reading/ReadingProgress.tsx` | Новый |
| `ReadingContextActions` | `widgets/reading/ReadingContextActions.tsx` | Новый |

### 19.5 Какие API уже достаточны

Все 6 endpoints работают и покрывают UX:
- `GET /book/chapters`
- `GET /book/text`
- `POST /book/reader/reading-event`
- `GET /book/reader/reading-progress`
- `GET /book/reader/reading-position`
- `GET /book/genome` (для контекстных действий)
- `POST /book/ask` (для «Спросить о главе»)

### 19.6 Какие API gaps существуют

| Gap | Влияние | Решаемость |
|-----|---------|------------|
| Текст режется по символам | Текст может обрезаться посередине абзаца | Low: frontend может «дорезать» |
| Нет поиска по тексту | Нельзя найти упоминание в тексте | Medium: frontend search possible |
| Нет semantic chunking | Сложно показать «осталось N абзацев» | Low: estimate from characters |

**Рекомендация:** Gaps не блокируют. Реализовать позже, если понадобится.

### 19.7 Рекомендуемый порядок реализации

1. **Phase 1 (Foundation):** ReadingTopbar + AppShell update
2. **Phase 2 (TOC + Reader):** ChapterList + ChapterReader + ReadingTOC
3. **Phase 3 (Navigation + Context):** Prev/next + context actions + auto-load
4. **Phase 4 (Polish):** Settings + responsive + a11y

### 19.8 Точные acceptance criteria для будущей реализации

```typescript
// Acceptance Criteria Checklist
[ ] Smart start: position exists → Reading view; else → TOC
[ ] TOC shows all chapters with progress indicators
[ ] Click chapter in TOC → Reading that chapter
[ ] Prev/Next buttons navigate between chapters
[ ] Auto-load more on scroll (no manual button)
[ ] "Ask about chapter" → /?context=chapter_title
[ ] "Go to genome" → /library?filter=chapter_topic
[ ] Font size setting persisted in localStorage
[ ] Column width setting persisted in localStorage
[ ] Progress bar updates on scroll
[ ] Reading-event fires on chapter leave (fire-and-forget)
[ ] Mobile: TOC as overlay drawer
[ ] Keyboard: Tab through chapters, Enter to select
[ ] tsc --noEmit passes (0 errors)
[ ] npm run lint passes (0 errors)
[ ] Backend unchanged (git diff empty)
```

---

## 20. Appendix: Reference Files

| Файл | Путь | Роль |
|------|------|------|
| Текущий Reading | `arkaim-web-v2/src/app/(main)/reading/page.tsx` | Базовый код для аудита |
| AppShell | `arkaim-web-v2/src/widgets/app-shell/AppShell.tsx` | Layout для обновления |
| Navigation | `arkaim-web-v2/src/shared/rbac/navigation.ts` | IA reference |
| Book contracts | `arkaim-web-v2/src/shared/api/contracts/book.ts` | API types |
| Reader contracts | `arkaim-web-v2/src/shared/api/contracts/reader.ts` | API types |
| Frontend Arch | `docs/FRONTEND_ARCHITECTURE.md` | Architecture reference |
| F2 Spec | `docs/F2_SPEC.md` | Scope boundaries |

---

**Конец документа. WAITING FOR GO.**
