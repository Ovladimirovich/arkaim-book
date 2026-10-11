# Frontend Inventory & Legacy Audit Report

**Дата:** 2026-09-17
**Тип:** Read-only forensic audit
**Scope:** ВСЕ frontend-директории, скрипты, CI, доки
**Влияние на Reading:** НИКАКОГО — legacy полностью изолирован

---

## Простыми словами

**Что было целью?**
Установить фактическую структуру frontend-кода: какой frontend текущий, какой legacy, есть ли пересечения, влияют ли они на TS/тесты/билд.

**Что реально сделано?**
Полный аудит двух frontend-директорий (`arkaim-web` legacy, `arkaim-web-v2` current), всех скриптов, CI, docker-compose, документации. Проверены кросс-импорты, тестовые конфиги, git-история, пути в tsconfig.

**Что получилось?** PASS — картина ясна. `arkaim-web` (legacy) полностью изолирован от v2. Ни один TS error, тест или build step не пересекается.

---

## 1. Фактическая структура

### Два frontend в одном mono-repo

| Параметр | `arkaim-web` (legacy) | `arkaim-web-v2` (current) |
|----------|----------------------|---------------------------|
| Статус | **Legacy** (заменён, F6 не завершён) | **Текущий** |
| Порт | 3000 (не используется) | **3001** (запущен, HTTP 200) |
| package.json | `arkaim-web/package.json` | `arkaim-web-v2/package.json` |
| Src-файлов | 103 | 57 |
| Страниц (app dirs) | 30 | 14 |
| Структура | Flat `src/app/` | FSD: `entities/features/widgets/shared` |
| API client | `src/shared/lib/api.ts` (ручной, mock при 401) | `src/shared/api/client.ts` (openapi-fetch, typed) |
| Envelope | Нет | `src/shared/api/envelope.ts` |
| RBAC | Нет | `src/shared/rbac/can.ts` |
| Types | Ручные интерфейсы | `generated/schema.d.ts` (из OpenAPI) |
| Test runner | vitest (jsdom) | custom sandbox runner + vitest |
| E2E | Playwright (port 3000) | Playwright (port 3001) |

### Текущий frontend (source of truth)

- **Путь:** `arkaim-web-v2/`
- **package.json:** `arkaim-web-v2/package.json`
- **Dev server:** `npm run dev` → `next dev --turbo --port 3001`
- **Фактически запущен:** http://localhost:3001 ✅ (HTTP 200 подтверждено)
- **Страницы (14):** `/`, `/graph`, `/library`, `/login`, `/no-access`, `/profile`, `/reading`, `/register`, `/status`, `/studio`, `/temporal`, `/temporal/queue`, `/world`, `/world-explorer`
- **FSD структура:** `src/entities/` / `src/features/` / `src/widgets/` / `src/shared/`

### Legacy frontend

- **Путь:** `arkaim-web/`
- **package.json:** `arkaim-web/package.json`
- **Статус:** Не запускался. Порт 3000 не используется.
- **Страницы (30):** Полный набор включая `ask`, `book`, `visual-view`, `world-engine`, `story` и др.
- **Структура:** Flat `src/app/` + `src/shared/lib/` (без FSD)
- **Особенность:** `api.ts` содержит MOCK_DATA для dev-режима (401 → mock)

---

## 2. Cross-reference audit — доказательства изоляции

### Кросс-импорты

| Направление | Результат |
|-------------|-----------|
| `arkaim-web/src` → `arkaim-web-v2` | **0 совпадений** ✅ |
| `arkaim-web-v2/src` → `arkaim-web/` | **0 совпадений** ✅ |

**Вывод:** Полная изоляция. Ни один файл не импортирует ничего из другого frontend'а.

### Git история

```
git log -- arkaim-web/       → нет коммитов в текущей ветке (ветка g0-clean, legacy закоммичен ранее)
git log -- arkaim-web-v2/    → активная разработка (Reading UX, F3 temporal, F2 book)
```

### Общий API-слой — РАЗНЫЕ реализации

| Компонент | Legacy | v2 |
|-----------|--------|-----|
| HTTP client | Ручной fetch + mock при 401 | openapi-fetch + typed |
| Auth handling | Cookie + mock fallback | Cookie + Bearer, 401 → redirect /login |
| Error handling | Встроен в api.ts | `ApiError` class в `errors.ts` |
| контракты | Ручные интерфейсы | Generated из OpenAPI + ручные contract modules |

---

## 3. Влияние на diagnostics текущего frontend

### TypeScript

```
tsc --noEmit (из arkaim-web-v2) → проверяет ТОЛЬКО arkaim-web-v2/src
```

- `arkaim-web-v2/tsconfig.json` include: `"**/*.ts"` резолвится относительно cwd (`arkaim-web-v2/`)
- `arkaim-web/tsconfig.json` имеет идентичную структуру, но НЕ включён в compile chain v2
- **Ни один TS error из legacy НЕ попадает в v2 diagnostics** ✅

**Подтверждено:** `npx tsc --noEmit` → EXIT 0, 0 ошибок.

### ESLint

```
npm run lint (из arkaim-web-v2) → eslint . (cwd = arkaim-web-v2)
```

- Линтер проверяет только файлы в `arkaim-web-v2/`
- Legacy файлы не сканируются
- **Ни один ESLint issue из legacy НЕ попадает в v2 diagnostics** ✅

### Тесты

| Suite | Путь | Работает с |
|-------|------|-----------|
| Unit tests | `arkaim-web-v2/tests/unit/` | **Только v2** ✅ |
| E2E tests | `arkaim-web-v2/tests/e2e/` | **Только v2** (port 3001) ✅ |
| Legacy unit | `arkaim-web/tests/unit/` | Не запускаются в этой сессии |
| Legacy e2e | `arkaim-web/tests/e2e/` | Не запускаются (port 3000) |

**Скрипт `scripts/run-tests.mjs`:** hardcoded TESTS array включает только v2-файлы. Legacy тесты НЕ включены. ✅

### Build

```
npm run build (из arkaim-web-v2) → next build (cwd = arkaim-web-v2)
```

- Next.js build резолвит только `arkaim-web-v2/src/`
- Legacy pages не участвуют
- **Build: 16 страниц сгенерированы, чистый** ✅

---

## 4. Reference audit — где фигурирует legacy

### CI (`.github/workflows/ci.yml`)

```yaml
# Legacy job (минимальный, не блокирующий):
cd arkaim-web
npm ci
npm run lint
npx tsc --noEmit

# Current job (полный pipeline):
cd arkaim-web-v2
npm ci
npm run contracts:verify
npm run lint
npm run typecheck
npm run test
npm run build
```

**Вывод:** CI содержит оба frontend'а. Legacy job делает поверхностную проверку. V2 job — полный pipeline. Legacy CI job НЕ блокирует merge.

### Docker (`docker-compose.yml` + `Dockerfile.frontend`)

```dockerfile
COPY arkaim-web/package.json arkaim-web/package-lock.json* /app/
COPY arkaim-web/ /app/
EXPOSE 3000
```

**Вывод:** `Dockerfile.frontend` использует legacy `arkaim-web/`. Это устаревший Dockerfile. Для v2 нужен отдельный `Dockerfile.frontend-v2` или обновление текущего. **НЕ влияет на локальную разработку.**

### Start scripts

| Скрипт | Использует | Порт |
|--------|-----------|------|
| `start_all.bat` | `arkaim-web-v2` | 3001 ✅ |
| `stop_all.bat` | `arkaim-web-v2` | 3001 ✅ |
| `Makefile dev` | `arkaim-web` | 3000 ⚠️ УСТАРЕЛО |
| `Makefile test` | `arkaim-web` | — ⚠️ УСТАРЕЛО |
| `Makefile lint` | `arkaim-web` | — ⚠️ УСТАРЕЛО |

**Вывод:** Windows-скрипты (`start_all.bat`, `stop_all.bat`) указывают на v2. Makefile (Unix) указывает на legacy. В Windows-среде Makefile не используется.

### Документация

15+ markdown-файлов в `docs/` содержат ссылки на `arkaim-web` (port 3000, legacy paths). Это историческая документация, не влияющая на код.

Ключевые упоминания:
- `AGENTS.md`: "Frontend: http://localhost:3000"
- `CLAUDE.md`: "Frontend (Next.js:3000)"
- `docs/FRONTEND_ARCHITECTURE.md §12`: "legacy выбрасывается поэтапно, см. §12"
- `docs/F1_IMPLEMENTATION_REPORT.md`: "R7: legacy не тронут (0 диффов в arkaim-web/)"

---

## 5. Статус legacy frontend

### Факты

| Вопрос | Ответ | Доказательство |
|--------|-------|---------------|
| Запускается ли legacy? | **Нет** | Порт 3000 свободен, process not found |
| Используется ли в CI? | Частично | Mini-job (lint+tsc), не блокирующий |
| Используется ли в Docker? | Да | `Dockerfile.frontend` копирует `arkaim-web/` |
| Есть ли кросс-импорты? | **Нет** | 0 совпадений при grep |
| Влияет ли на TS v2? | **Нет** | Разные tsconfig, разные cwd |
| Влияет ли на тесты v2? | **Нет** | Разные test dirs, разные runner'ы |
| Влияет ли на build v2? | **Нет** | Next.js build изолирован |
| Упоминается ли в docs? | Да | 15+ файлов, исторические ссылки |

### Что говорит архитектура

`docs/FRONTEND_ARCHITECTURE.md §12` (Судьба legacy):
> 1. **Не чинить и не развивать** legacy с момента утверждения этой архитектуры
> 2. До завершения F4 новый frontend живёт на отдельном app-root
> 4. Class C — **удаляются в F6**
> 8. Legacy удалён, сборка чистая

**F6 (Polish/Regression) не завершён.** Legacy намеренно сохранён как переходный период.

---

## 6. Таблица статусов

| Путь | Что это | Используется текущим? | Используют скрипты/тесты? | Можно удалить? | Доказательство |
| ---- | ------- | ---------------------: | -----------------------: | -------------: | -------------- |
| `arkaim-web/` | Legacy Next.js (port 3000) | **Нет** | **Нет** (CI mini-job не блокирующий) | **Да, но НЕ сейчас** | F6 не завершён; Dockerfile всё ещё ссылается; docs содержат ссылки |
| `arkaim-web-v2/` | Current Next.js (port 3001) | **Да** | **Да** (test, build, lint, contracts) | **Нет** | Source of truth |
| `Dockerfile.frontend` | Docker for legacy | Частично (build context) | Нет (локально не используется) | Обновить на v2 | Копирует `arkaim-web/`, порт 3000 |
| `Makefile` | Unix dev commands | Нет (Windows-среда) | Нет | Обновить ссылки | Указывает на `arkaim-web`, port 3000 |
| `docs/FRONTEND_ARCHITECTURE.md §12` | План миграции | Информационно | Нет | Актуализировать | Описывает поэтапное удаление legacy |

---

## 7. Рекомендации

### НЕМЕДЛЕННО (безопасно)

1. **Ничего не удалять.** Legacy полностью изолирован, не влияет на v2.
2. **Зафиксировать** что `arkaim-web-v2` — единственный source of truth для frontend diagnostics.
3. **Обновить** `Makefile` ссылки с `arkaim-web` на `arkaim-web-v2` (для Unix-разработчиков).
4. **Обновить** `Dockerfile.frontend` на v2 (или добавить `Dockerfile.frontend-v2`).

### ПОСЛЕ F6 (когда legacy будет официально удалён)

1. Удалить `arkaim-web/` полностью (git history сохранить).
2. Удалить или обновить `Dockerfile.frontend`.
3. Актуализировать `docs/` — убрать ссылки на port 3000.
4. Убрать legacy job из `.github/workflows/ci.yml`.
5. Обновить `Makefile` и `AGENTS.md` / `CLAUDE.md`.

### ЧТО УЖЕ СДЕЛАНО

- Reading page работает в v2 без AppShell (layout.tsx guard)
- Все reading-компоненты в `arkaim-web-v2/src/`
- Legacy reading page (`arkaim-web/src/app/reading/page.tsx`) — другая реализация, не используется
- Цепочка диагностики чиста: TS/ESLint/тесты/build — всё из v2 cwd

---

## 8. Финальный вердикт

**Legacy `arkaim-web/` НЕ влияет на текущую разработку `arkaim-web-v2/`:**

- ✅ 0 кросс-импортов
- ✅ 0 общих TS ошибок
- ✅ 0 пересечений в тестах
- ✅ 0 пересечений в build
- ✅ Полная filesystem изоляция

**Reading UX Redesign — полностью в рамках `arkaim-web-v2`. Legacy не причём.**
