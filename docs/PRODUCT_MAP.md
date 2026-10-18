<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL - НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Статусы, маршруты, компоненты и упоминания бывшего v2 ниже отражают состояние на момент создания документа. Актуальность проверяйте по docs/CURRENT_DEVELOPMENT_STATE.md, docs/DOCUMENTATION_INDEX.md, текущему коду и ADR.

﻿<!-- FRONTEND-CONSOLIDATION-BANNER -->
> [!IMPORTANT]
> **Архитектура фронтенда (решение владельца, зафиксировано).**
> - Единственный frontend проекта — `arkaim-web`: единственное направление дальнейшей разработки.
> - `arkaim-web-v2` — **удалён** из репозитория как рабочее направление.
> - Перечень потенциально восстанавливаемой из бывшего v2 функциональности: `docs/FRONTEND_RESTORE_BACKLOG.md`.
> - Дальнейшие сравнения `arkaim-web` против `arkaim-web-v2` не проводятся. Ниже могут встречаться исторические упоминания v2 (в датированных аудитах/спеках) — они относятся к удалённому направлению и НЕ означают сосуществования двух действующих фронтендов.

# PRODUCT MAP — Реальная карта Arkaim на 2026-09-18

> Основано на `CURRENT_DEVELOPMENT_STATE.md` (после R1) + фактический код на диске.
> Никаких новых аудитов. Только synthesis существующих фактов.

---

## 1. Что СЕЙЧАС работает (продукт в сборе)

### Backend (FastAPI :8642) — полный цикл

| Подсистема | Статус | Доказательство |
|-----------|--------|---------------|
| Pulse (10 слоёв) | ✅ | `pulse/layers.py`: Knowledge, VisualStyle, NarrativeArc, Scene, Meaning, Identity, Mission, Expansion, Screenplay, WorldEngine |
| World Engine | ✅ | 547 сущностей, 287 связей, 55 форм, 10 режимов, 10 API-роутов |
| Temporal model | ✅ | 12 эпох + Present + экстраполяция; 7 роутов `/book/temporal/*` |
| M10.2 очередь | ✅ | 7 роутов `routes/temporal_updates.py`, RBAC editor/admin |
| MediaPlan v0 | ✅ | `media_plan/schemas.py` + 5 маршрутов A–E byte-frozen |
| 5 маршрутов A–E | ✅ | visualize, visualize-epoch, assets/generate, assets/generate-context, film/{id}/shots/{id}/generate |
| Film Studio | ✅ | 13 роутов, CRUD проектов/шотов, assemble(ffmpeg) |
| Auth (JWT+Telegram+email+dev) | ✅ | RBAC reader/editor/admin на всех эндпоинтах |
| WebSocket + SSE | ✅ | `/ws`, `/v1/stream`, `/xray/events/stream` |
| ~289 API-путей | ✅ | OpenAPI слепок |
| AssetStorage (файлы+SQLite) | ✅ | `data/visual_assets.db` + файлы `data/visual_assets/{images,videos,thumbnails}` |

### Frontend v2 (Next.js :3001) — F1–F4 всё закрыто

| Фаза | Страницы | Статус |
|------|----------|--------|
| **F1 Foundation** | `/login`, `/register`, `/` (redirect по роли), `/no-access`, `/status` | ✅ CLOSED |
| **F2 Книга/Мир** | `/ask` (SSE), `/reading` (17 глав, прогресс), `/profile` | ✅ CLOSED |
| **F3 Время мира** | `/temporal` (12 эпох + today + future), `/temporal/queue` (M10.2 UI) | ✅ CLOSED |
| **F4 Предложения** | `/community`, `/proposals/presence`, `/proposals/email`, `/proposals/drafts`, `/admin/moderation` | ✅ CLOSED |
| **Бонус (был на диске)** | `/graph`, `/library`, `/world`, `/world-explorer`, `/studio`, `/analytics`, `/upload`, `/ask` (legacy F2-F4 overlap) | ✅ Работают |

**Итого на диске: 22 page.tsx, 30 test-файлов (29 unit + 1 reading-logic).**

### Media-проект (arkaim-media)

| Компонент | Статус | HEAD |
|----------|--------|------|
| Media Contract v1.0 | ✅ ACCEPTED | `f0327cd` |
| ComfyUI provider | ✅ CLOSED | `d4bcef2` |
| Video providers (image_sequence + mock) | ✅ CLOSED | `0256140` |
| Provider chains (ImageProviderChain, MockImage, SVGTemplate) | ✅ CLOSED | `4ccfd8e` |
| MediaClient bridge (adc_deps substitution) | ✅ CLOSED | `81612b7` / `5922dcc` |
| Live route gate (5 маршрутов через Media) | ✅ CLOSED | `b5d399d` / `0d10396` |

### Тесты (фактические прогоны)

| Suite | Результат |
|-------|----------|
| MD-3+MD-4 backend | 141/141 PASS |
| Temporal | 237/237 PASS |
| md2/m7/m10.x | 74/74 PASS |
| arkaim-media | 42/42 PASS |
| arkaim-web-v2 | 85/85 PASS |
| **Всего зелёных тестов** | **~579** |

---

## 2. Чего НЕ ХВАТАЕТ (продуктовые gaps)

### 2.1 Product Completion (пользовательский сценарий не доведён до конца)

| Gap | Что нужно | Класс |
|-----|-----------|-------|
| **G-F5-1** | WS-интеграция: toast при live-событиях, invalidate кэша | F5 |
| **G-F5-2** | `/xray` страница: SSE-лента трасировок, реальная observability | F5 |
| **G-F5-3** | `/admin` полноценный: пользователи, инвайты, API-ключи, статистика | F5 |
| **G-F5-4** | `/system` страница: health, конфигурация, метрики | F5 |
| **G-F5-5** | `/profile` enhancements: история вопросов, расширенная статистика | F5 |
| **G-F5-6** | `/history` страница: все сессии с фильтрами | F5 |
| **G-F6-1** | `/help` страница: справка по функционалу | F6 |
| **G-F6-2** | Accessibility (a11y) проход | F6 |
| **G-F6-3** | Мобильная адаптация фронтенда | F6 |
| **G-F6-4** | Playwright E2E-прогон (все S1–S7 сценарии) | F6 |
| **G-F6-5** | Удаление legacy `arkaim-web/` (F6 согласно §12 FRONTEND_ARCHITECTURE) | F6 |

### 2.2 Architecture / Core (фундаментальные технические пробелы)

| Gap | Что нужно | Класс |
|-----|-----------|-------|
| **G-D3** | Video-план Route C не доходит до `generate_video` (сигнатура pipeline.py:195–201 без plan) | Core |
| **G-D4** | Queue/async/batch/regenerate — без плана (legacy-поведение) | Core |
| **G-D9** | Film-studio БД: отсутствие quality-колонки (`F-12`) | Core |
| **G-D16** | C2: фабрика рёбер ставит AUTHOR_CANON на PRECEDES-рёбрах (семантическое изменение данных) | Core |

### 2.3 Infrastructure / Cleanup

| Gap | Что нужно | Класс |
|-----|-----------|-------|
| **G-G1** | F4-код untracked на master (не закоммичен) | Infra |
| **G-G2** | M8.1 test-isolation fix незакоммичен в рабочем дереве | Infra |
| **G-D1** | AGENTS.md → stale ADR paths, stale Pulse layers count | Infra |
| **G-D2** | Сырые пути в `research/{entity_extractor,source_searcher}.py` | Infra |
| **G-D5** | Депубликованные `/comfyui/*` роуты: код ещё в `visual.py` | Infra |
| **G-D11** | `ModuleNotFoundError: runtime.core` в 4 тестах (pre-existing) | Infra |
| **G-D12–D15** | Мёртвые импорты, pyc-файлы, висячие `__all__`, legacy prompt-проекции | Infra |
| **G-D17** | Genome-history churn при каждом запуске | Infra |
| **README.md** | Устаревшие метрики (29 стр → 34, 195 роутов → 219+) | Infra |

---

## 3. Текущая точка — синтез

```
F1 ✅ → F2 ✅ → F3 ✅ → F4 ✅   (frontend v2: 22 страницы, 85 тестов)
  │
  ├── [не в git] F4-код untracked на master
  │
  ▼
┌─────────────────────────────────────────┐
│           ТЕКУЩАЯ ТОЧКА                  │
│  Backend ✅ · Media ✅ · Frontend v2 ✅  │
│  Но: F4 не в git, F5 не начат           │
│  Product: 70% пользовательского сценария │
└─────────────────────────────────────────┘
  │
  ▼
Что дальше?
```

**Факт:** product работает на ~70% от запланированного по FRONTEND_ARCHITECTURE. Осталось:
- F5 (realtime/admin/xray/system/profile/history) — **6 незакрытых страниц**
- F6 (help/a11y/mobile/E2E/legacy-удаление) — **5 незакрытых пунктов**

**Факт:** backend debt (D3, D4, D9, D16) — это архитектурные решения, а не urgent bugs. Они не блокируют F5.

**Факт:** infra-debt (untracked F4, D1, D2, D5–D17) — это cleanup, а не product value.

---

## 4. Кандидаты на следующий этап — категоризация

### 4.1 Product Completion ⭐

| Кандидат | Объём | Ценность | Блокирует ли что-то? |
|----------|-------|----------|---------------------|
| **F5 Realtime/Admin** | 6 страниц (xray, admin, system, profile+, history, WS-integration) | **Высокая** — product перестаёт быть «наполовину собранным» | Да: F6 зависит от F5 (по FRONTEND_ARCHITECTURE §11) |
| **F6 Polish/Regression** | 5 пунктов (help, a11y, mobile, E2E, legacy-delete) | Средняя — polishing уже готового | Нет, но бессмысленно без F5 |

### 4.2 Architecture / Core

| Кандидат | Объём | Ценность | Блокирует ли что-то? |
|----------|-------|----------|---------------------|
| **D3 video-plan→generate_video** | 1 сигнатура в pipeline.py | Низкая — видео-генерация и так работает через image_sequence | Нет |
| **D9 film-studio БД миграция** | ALTER/пересоздание таблиц | Средняя — quality-поле мёртвое, но data integrity важна | Нет |
| **C2 provenance on edges** | Семантическое изменение 287 рёбер | Средняя — correctness, но чтение не ломается | Нет |

### 4.3 Infrastructure / Cleanup

| Кандидат | Объём | Ценность | Блокирует ли что-то? |
|----------|-------|----------|---------------------|
| **Коммит F4-кода** | 5 pages + 26 tests + 3 contracts | **Критическая** — F4 существует, но не в git. Без этого любой следующий этап рискован | **Да**: работает с untracked-кодом, нельзя безопасно коммитить F5 поверх |
| **M8.1 test-fix коммит** | 1 test file | Низкая — тест уже работает, просто не в git | Нет |
| **MD-7 / M4.5** | workflows/env переезд + чистка comfyui/* кода | Низкая — cosmetic cleanup | Нет |
| **README update** | 1 файл | Низкая | Нет |

---

## 5. Рекомендация: следующий этап

### Простыми словами

Проект сейчас — это **работающий продукт на 70%**: бэкенд полный, media-execution полный, фронтенд v2 имеет все читательские экраны (ask, reading, temporal, community, proposals). Но два факта портят картину:

1. **F4-код не в git** — 5 страниц + 26 тестов + 3 контракта лежат untracked. Это значит: если сегодня произойдёт что-то с рабочей директорией — F4 потеряется. Это не «технический долг», это **риск потери продукта**.

2. **F5 не начат** — и пока F4 не закоммичен, начинать F5 небезопасно (можно случайно затереть untracked-файлы при работе с git).

Поэтому следующий шаг однозначный:

### Главный кандидат: **F5 Realtime/Admin**

**Но сначала решить инфраструктурный вопрос:** коммит F4-кода.

**Последовательность:**
1. **Шаг 0 (Infra, быстрый):** коммит untracked F4-кода + M8.1 test-fix в отдельном GO (это не milestone, это фиксация того, что уже принято)
2. **Шаг 1 (Product, основной):** F5 — 6 страниц + WS-интеграция

**Почему F5, а не debt:**
- Debt (D3, D4, D9, D16) — это «когда-нибудь». Они не ломают product.
- F5 — это «сейчас». Без F5 продукт неполный: нет realtime-уведомлений, нет admin-панели, нет xray. Читатель может задать вопрос, прочитать ответ, исследовать время мира — но не видит live-ленту, не управляет сообществом, не видит системную статистику.
- F5 — логическое продолжение F4 по FRONTEND_ARCHITECTURE §11 (порядок фаз: F1→F2→F3→F4→F5→F6).
- F5 не затрагивает backend (по регламенту F-линейки).

### Что делает F5 (конкретно)

| Экран | Что реализует | Backend-контракт |
|-------|--------------|-----------------|
| `/xray` | SSE-лента трасировок, реальный observability | `GET /xray/events/stream` |
| `/admin` | Users, invites, API-keys, stats | `/auth/*`, `/api/*` |
| `/system` | Health, config, metrics | `/health`, `/metrics` |
| `/profile` enhancements | Расширенная статистика, история вопросов | `/book/reader/*` |
| `/history` | Все сессии с фильтрами | `/book/reader/history` |
| WS-integration | Toast при live-событиях, invalidate кэша | `/ws` |

**Не делает F5:**
- Меняет backend (0 изменений — по регламенту)
- Тянет F6 (только до границы F5)
- Решает debt (D3/D4/D9/D16 — отдельно)

---

## STOP

Карта составлена. Следующий шаг — **owner-GO**:
1. Скоммитить F4-код (инфра-фиксация)
2. Начать F5 (product completion)

Или выбрать другой кандидат из §4.
