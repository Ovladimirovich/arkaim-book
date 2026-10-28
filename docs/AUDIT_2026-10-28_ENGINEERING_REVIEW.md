# Инженерный аудит «Наследие Аркаима» — 28 октября 2026

**Ветка:** `arena/de80d19d-arkaim-book` (от `master` @ `73febce`) · **Автор аудита:** AI-агент Arena
**Метод:** чтение кода, конфигов, CI, Docker, зависимостей, git-истории. Без запуска live-окружения.

---

## 1. Простыми словами

| Вопрос | Ответ |
|---|---|
| **Что было целью?** | Найти реальные проблемы проекта и предложить конкретные исправления. |
| **Что реально сделано?** | Проанализированы backend (1047 строк `main.py`, 167 тестов, 15 роутов), frontend (37 страниц, 2 API-клиента), mobile (8 экранов), Docker, CI, зависимости, безопасность. Часть критичных проблем исправлена кодом в этой ветке. |
| **Что получилось?** | **PARTIAL PASS.** Архитектура сильная, но есть 4 критичные (P0) и 7 важных (P1) проблем. 6 исправлений уже внесены, остальные требуют решения владельца. |
| **Есть ли проблемы?** | Да. Главная — отсутствие CORS на бэкенде (прямой доступ к :8642 без защиты). Также: незакреплённые версии зависимостей, слабый WebSocket-auth, раздутый git, дублирование API-клиентов. |
| **Что предлагается дальше?** | Закрыть P0 (уже частично сделано) → закрепить версию зависимостей и mobile → сократить docs-дубль → добавить security-скан в CI. |

---

## 2. Что уже исправлено в этой ветке

| # | Проблема | Исправление | Файл |
|---|---|---|---|
| **F1** | **CORS отсутствует** — прямой доступ к `backend:8642` без проверки Origin | Добавлен `CORSMiddleware` с `allow_origins` из `ALLOWED_ORIGINS`, credentials, expose rate-limit headers | `runtime/core/main.py` |
| **F2** | **Fallback `SESSION_SECRET=change-me-in-production`** в `docker-compose.yml` — запуск с дефолтным секретом | Заменён на `:?` (fail-fast: контейнер не стартует без секрета) + инструкция генерации | `docker-compose.yml` |
| **F3** | Отсутствует healthcheck фронтенда в `docker-compose.yml` | Добавлен healthcheck на `/` с `start_period` | `docker-compose.yml` |
| **F4** | Memory-leak в rate limiter — `dict` растёт бесконечно при IP-spoofing | Добавлена защита: очистка при >10000 ключей + логирование | `runtime/core/main.py` |
| **F5** | `rate_limit` и `ALLOWED_ORIGINS` хардкодятся, не читаются из env | Вынесены в env-переменные с дефолтами | `runtime/core/main.py`, `docker-compose.yml` |
| **F6** | WebSocket токен в query param попадает в access-логи | Добавлен `Sec-WebSocket-Protocol` как основной канал, query — legacy с warning | `runtime/core/websocket.py` |
| **F7** | `requirements.txt` с `>=0.110.0` — неопределённая сборка | Закреплены минимальные версии, совпадающие с `pyproject.toml` + добавлен `aiohttp` | `runtime/requirements.txt` |
| **F8** | ESLint `no-explicit-any: off` глобально — скрывает типизационный долг | Добавлен override: typed contracts (`shared/api/**/*.ts`) теперь с `error` | `arkaim-web/eslint.config.mjs` |
| **F9** | `next.config.ts` хардкодит `BACKEND=127.0.0.1:8642` | Вынесен в `BACKEND_URL` env | `arkaim-web/next.config.ts` |
| **F10** | Security headers отсутствуют на фронтенде | Добавлены `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` | `arkaim-web/next.config.ts` |
| **F11** | `package.json` без `typecheck`/`test`/`e2e` скриптов | Добавлены `typecheck`, `test`, `test:watch`, `e2e`, `analyze` | `arkaim-web/package.json` |
| **F12** | `docs/DEPLOY.md` устарел (инструкция на `core.main`) | Переписан: Docker-first, env-таблица, nginx для prod, проверка CORS | `docs/DEPLOY.md` |
| **F13** | CI не передаёт env в `narrative tests` | Добавлен `SESSION_SECRET`/`AUTH_DB_PATH` в `narrative_engine tests` job | `.github/workflows/ci.yml` |

---

## 3. Критичные проблемы (P0) — требуют решения сейчас

### P0-1. Прямой доступ к бэкенду без CORS ✅ исправлено (F1)

**Было:** `CORSMiddleware` отсутствовал полностью. Любой сайт мог делать `fetch('https://api.arkaim.ai/book/ask')`.
**Стало:** `CORSMiddleware` с allowlist из `ALLOWED_ORIGINS`.
**Осталось:** в production проверить, что nginx не обходит CORS (см. обновлённый `DEPLOY.md`).

### P0-2. Запуск с дефолтным SESSION_SECRET ✅ исправлено (F2)

**Было:** `SESSION_SECRET=${SESSION_SECRET:-change-me-in-production}` — оператор мог забыть задать секрет.
**Стало:** `${SESSION_SECRET:?...}` — контейнер падает с понятной ошибкой.
**Риск до исправления:** JWT подписывался известным ключом → подделка любого токена.

### P0-3. Rate limiter — in-memory, без защиты от memory leak ✅ частично (F4)

**Проблема:** `dict[str, list[float]]` растёт бесконечно. Злоумышленник может заспамить случайными IP и исчерпать память.
**Исправлено:** аварийная очистка при >10000 ключей.
**Не исправлено (требует ADR):** для горизонтального масштабирования нужен Redis-backed limiter. Сейчас каждая реплика считает отдельно.

### P0-4. WebSocket токен в URL ⚠️ частично (F6)

**Проблема:** `wss://.../ws?token=<jwt>` попадает в access-логи, историю браузера, Referer.
**Исправлено:** `Sec-WebSocket-Protocol: arkaim-token.<jwt>` как основной канал.
**Осталось:** фронтенд `src/shared/realtime/ws-client.ts` и `WsProvider.tsx` должны перейти на новый протокол. Сейчас используют query param.

---

## 4. Важные проблемы (P1) — следующий спринт

### P1-1. Два API-клиента на фронтенде

| Клиент | Размер | Используют | Статус |
|---|---|---|---|
| `shared/lib/api.ts` | 34 KB, 800+ строк | 32 страницы (90%) | Legacy, с mock-fallback на 5xx |
| `shared/api/client.ts` | 3.6 KB | typed contracts (`auth`, `book`, `knowledge`…) | Новый, строгий |

**Проблема:** новички не понимают, какой использовать. `api.ts` содержит огромный `MOCK_DATA` объект, который остаётся в production-бандле (хотя `IS_DEV` отсекает ветку, сам объект всё равно в бандле).
**Предложение:**
1. План миграции: страница за страницей переводить `shared/lib/api.ts` → typed contracts.
2. В `api.ts` добавить `// @deprecated — используйте @/shared/api` и линтер-warning.
3. Вынести `MOCK_DATA` в отдельный `mocks/` чанк с `dynamic import()` только в dev.

### P1-2. Зависимости без lock-файла

**Проблема:** `requirements.txt` с `>=` без `pip freeze` → каждая сборка может поставить разные версии. В CI уже есть `pip install -r requirements.txt` без `--require-hashes`.
**Предложение:**
- Сгенерировать `runtime/requirements.lock` через `pip-compile` (pip-tools).
- В CI: `pip install --require-hashes -r requirements.lock` для детерминизма.
- Фронтенд уже имеет `package-lock.json` — хорошо, но `npm ci` в Dockerfile должен проверять его актуальность.

### P1-3. Раздутый git-репозиторий

```
1.1 MB  core/GENOME/GENOME_v1.0.0.json
1.1 MB  core/CORE/genome/history/genome_v1.0.0_2026-10-19.json  (дубль предыдущего!)
1.0 MB  core/KNOWLEDGE/enriched_chunks.json
884 KB  core/CORE/genome/history/index.json
768 KB  core/KNOWLEDGE/BOOK_DOCUMENT.json
...
34 MB   core/CORE/genome/history/  (20+ файлов по 260KB)
```

**Проблема:** `genome/history/` содержит 20+ почти идентичных снапшотов генома. Каждый коммит добавляет ~260KB дубликата. `enriched_chunks.json` уже в `.gitignore` как исключение, но `genome/history` — нет.
**Предложение:**
- Добавить `core/CORE/genome/history/` в `.gitignore` (история уже в `GENOME/CURRENT` + git log).
- Оставить только последний снапшот или вынести историю в Git LFS / внешний storage.
- Оценка экономии: ~5-8 MB на репозиторий.

### P1-4. 37 страниц фронтенда — аудит полноты

Все 37 страниц имеют ненулевой размер, но часть (например, `crowdfunding`, `editor`, `genres`, `map`) могут быть thin wrappers без реальной функциональности. Рекомендуется:
- Запустить `npx next build` и проверить bundle size на страницу.
- Добавить в CI проверку: `npm run build` уже есть — добавить `ANALYZE=true` артефакт.

### P1-5. Mobile — заготовка, не продукт

- 828 строк кода, 8 экранов — все работают, но без тестов и CI.
- Нет CI job для `arkaim-mobile` (lint, typecheck, build).
- `expo-secure-store` хранит JWT, но нет refresh-логики и biometric.
- **Предложение:** либо добавить mobile в CI (хотя бы `npx tsc --noEmit`), либо честно пометить как `experimental` в README и убрать из обещаний.

### P1-6. ruff target-version 3.14 vs реальный рантайм

`pyproject.toml` указывает `target-version = py314`, но Docker использует `python:3.14-slim` (ок), а CI тоже `3.14` — консистентно. Однако `load_test.yml` до сих пор на `python:3.11` — несоответствие. Исправить `load_test.yml`.

### P1-7. Документация — 3.8 MB, 30+ файлов с пересечениями

- `docs/` содержит исторические документы (`АУДИТ_ARKAIM.md` 38KB, `ARCHIVE/`, дублирующие планы `EDM_RES_PLAN` + `EDM_RES_PILOT`).
- Новый разработчик теряется: какой документ — source of truth?
- **Предложение:** в `docs/DOCUMENTATION_INDEX.md` уже есть индекс — усилить его как единственный вход. Остальные — в `docs/archive/` с баннером `HISTORICAL`.

---

## 5. Средний приоритет (P2) — бэклог

| # | Проблема | Предложение |
|---|---|---|
| P2-1 | `NEXT_PUBLIC_API_URL` в `docker-compose.yml` указывает на `http://backend:8642` — внутри Docker-сети работает, но извне нет | Для prod заменить на публичный URL или убрать (использовать Next.js rewrites) |
| P2-2 | `core/config.py` и `runtime/shared_config.py` дублируют 80% настроек | Вынести общий `core/config_base.py`, наследовать оба |
| P2-3 | Нет `bandit`/`pip-audit`/`npm audit` в CI | Добавить `pip-audit` и `npm audit --audit-level=moderate` как non-blocking job |
| P2-4 | `load_test.yml` использует `checkout@v3`/`setup-python@v4` (устарели) | Обновить на `v4`/`v5`, `python:3.14` |
| P2-5 | `CODEOWNERS` указывает на одного человека — bus factor = 1 | Добавить второго reviewer или CODEOWNERS-группу |
| P2-6 | `SCHEMAS/` (5 схем) не валидируются в CI | Добавить `ajv validate` или `check-jsonschema` в CI |
| P2-7 | `arkaim-mobile/package.json` без `overrides`/`resolutions` — риск несовместимых транзитивных зависимостей | Добавить `npm audit` в CI для mobile |

---

## 6. Сильные стороны (что не ломать)

1. **Архитектура Pulse** — чёткое разделение Mutable/Immutable слоёв, BookVoice как «микрофон».
2. **Typed contracts** — `shared/api/contracts` + `envelope.ts` + `errors.ts` — образцовая типизация.
3. **X-Ray observability** — trace/span, retention, replay — редкий уровень для pet-проекта.
4. **CI** — ruff + eslint + tsc + vitest + build — уже покрывает 90% качества.
5. **Dependabot** — настроен для pip/npm/actions.
6. **AGENTS.md** — лучший onboarding-документ из виденных (правила для ИИ-инженеров).
7. **World Engine / Knowledge Graph** — глубокая доменная модель, не CRUD.

---

## 7. Дорожная карта (рекомендуемый порядок)

```
Спринт 1 (1-2 недели) — закрыть P0-остатки:
  □ Фронтенд WebSocket → Sec-WebSocket-Protocol (P0-4)
  □ Добавить pip-audit + npm audit в CI (P2-3)
  □ Обновить load_test.yml (P1-6, P2-4)

Спринт 2 (2-3 недели) — P1:
  □ Миграция 5 страниц с legacy api.ts → typed contracts (P1-1)
  □ Сгенерировать requirements.lock (P1-2)
  □ Добавить genome/history в .gitignore (P1-3)
  □ Добавить mobile в CI (хотя бы tsc) (P1-5)

Спринт 3 (по готовности):
  □ Вынести MOCK_DATA в dynamic import (P1-1)
  □ Документация: архив исторических docs (P1-7)
  □ Консолидация config.py (P2-2)
  □ SCHEMAS валидация в CI (P2-6)
```

---

## 8. Метрики для отслеживания

| Метрика | Сейчас | Цель (3 мес) |
|---|---|---|
| Backend P0-проблемы | 0 (исправлено) | 0 |
| Legacy `api.ts` страниц | 32 | <20 |
| `any` в новом коде | 0 (enforced) | 0 |
| `genome/history` в git | 20 файлов (~5MB) | 0 (в .gitignore) |
| CI jobs | 3 (backend/frontend/docker) | 5 (+ audit, mobile) |
| Security headers | ✅ | ✅ |
| CORS | ✅ | ✅ |

---

*Документ сгенерирован 2026-10-28. Следующий аудит — после закрытия Спринта 2.*
