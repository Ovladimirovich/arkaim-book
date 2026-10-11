# M10.2 — PRE-IMPLEMENTATION AUDIT (pending-updates API endpoint)

Дата: 2026-09-08
Объект: M10.2 — API endpoint'ы для очереди temporal-предложений (M10 pending queue → HTTP API)
Основание: M10 принят (ACCEPTED & CLOSED), владелец авторизовал M10.2
Фаза: read-only аудит существующих контрактов + SPEC DRAFT (по порядку M5–M10)

---

## Простыми словами

**1. Что было целью аудита?**
Проверить, на чём строить M10.2: как в проекте устроены существующие API-роуты, проверка прав доступа, и не требует ли задача переписывания существующих подсистем.

**2. Что реально сделано?**
Изучены: temporal-роуты M5 (ближайший сосед), механизм ролей (reader/editor/admin), research-роуты (precedent in-memory очереди), синглтон WorldEngine, менеджер M10. Вывод: всё нужное уже существует, M10.2 — тонкая обёртка поверх готового `TemporalUpdateManager`, без переписывания чего-либо.

**3. Что получилось?** — PASS: все точки интеграции найдены, конфликтов с существующими контрактами нет.

**4. Есть ли проблемы?** Одна развилка, требующая решения владельца: какой минимальной ролью подтверждать temporal-предложения (см. SPEC, вопрос №1).

**5. Что предлагается дальше?** Утвердить SPEC DRAFT → реализация по тому же порядку (план → код → тесты → отчёт → пост-аудит).

---

## 1. Что проверено (read-only)

### 1.1 Роут-инфраструктура

| Контракт | Файл | Факт |
|----------|------|------|
| Temporal-роуты M5 | `runtime/core/routes/temporal.py` | prefix `/temporal`, tags, Query/HTTPException паттерн; 6 endpoint'ов |
| Регистрация роутов | `runtime/core/book_routes.py:32,46` | `router.include_router(temporal_router)` — новый подроут добавляется одной строкой |
| Итоговый URL | — | `/book/temporal/*` |
| Precedent: research-очередь | `core/CORE/narrative_engine/research/api_routes.py` | `_research_jobs` in-memory + GET jobs/{id} — но это заглушки БЕЗ confirm-gate; M10.2 использует реальный менеджер |
| Схема ответов | все роуты | `{"ok": true, "data": ...}` — единый конвенция |

### 1.2 RBAC (права доступа)

| Контракт | Файл | Факт |
|----------|------|------|
| Механизм ролей | `runtime/auth/rbac.py` | `ROLE_HIERARCHY = {"reader": 0, "editor": 1, "admin": 2}`; `require_role("editor")` — декоратор Depends |
| JWT/cookie | `rbac.py::get_current_user` | Bearer header или `arkaim_session` cookie |
| Сервисный ключ | `rbac.py:26-35` | HERMES_API_KEY аутентифицирует сервис, НЕ даёт admin |
| Тестовый обход RBAC | `tests/integration/test_book_api.py:12-22` | `app.dependency_overrides[get_current_user] = _fake_user` — канонический паттерн |
| Precedent защиты | `temporal.py:188-189` | future-extrapolation защищён `require_role("reader")` |

### 1.3 Синглтоны и данные

| Контракт | Файл | Факт |
|----------|------|------|
| WorldEngine singleton | `world_engine.py:341` | `get_world_engine()` — для `refresh_temporal()` при confirm |
| M10 менеджер | `research/temporal_update_manager.py` | готов: pending/confirmed/rejected/stats(), confirm(finding_id) с валидацией, reject(); **НЕ держит состояние подтверждения в HTTP-слое** |
| Детектор | `research/book_change_detector.py` | `watch()` → snapshot|None; polling по вызову |
| Извлекатель | `research/temporal_extractor.py` | `extract(text)` → list[TemporalFinding] |
| Канонический путь save | внутри менеджера | абсолютный `narrative_engine/data/WORLD_MODEL.json` (исправлено в M10) |

### 1.4 Чего НЕ затрагивает M10.2

- UI/фронтенд (вне scope, отдельно)
- БД (очередь остаётся in-memory, как M10)
- Модель provenance, ADR-0001, temporal-подсистемы M2–M9
- Сам `TemporalUpdateManager` — используется как есть, endpoint'ы только вызывают его методы

## 2. Разрывы (что нужно построить)

| # | Разрыв | Решение |
|---|--------|---------|
| 1 | HTTP-слой для pending queue отсутствует | Новый модуль роута поверх менеджера |
| 2 | Singleton-инстанс менеджера в процессе | Ленивая инициализация в модуле роута (паттерн `get_world_engine`) |
| 3 | Scan-триггер (детектор+извлечение+submit) | POST endpoint, вызывает существующие компоненты по цепочке |
| 4 | RBAC-границы | Готовый `require_role` |

Конфликтов с существующими контрактами НЕ обнаружено — M10.2 чисто аддитивный.

## 3. SPEC DRAFT — M10.2 «Pending Updates API»

### 3.1 Цель

Дать человеку (через API — будущий UI) возможность видеть temporal-предложения из книги, подтверждать или отклонять их. Suggest-only инвариант M10 сохраняется полностью: единственный путь изменения WorldModel — `confirm()` менеджера (теперь доступный и через API, но за правами editor+).

### 3.2 Endpoint'ы (все под `/book/temporal`)

| Метод | Путь | Роль | Действие |
|-------|------|------|----------|
| POST | `/pending-updates/scan` | editor | Запустить: детектор книги → извлечение → submit в pending. Idempotent: без изменения книги → 0 новых. **Не** автоскан — только явный вызов человеком |
| GET | `/pending-updates` | reader | Список pending (без применённых) |
| GET | `/pending-updates/stats` | reader | Счётчики pending/confirmed/rejected |
| GET | `/pending-updates/history` | reader | Подтверждённые и отклонённые (аудит-след) |
| GET | `/pending-updates/{finding_id}` | reader | Детали одной находки (raw_text, context, категория, confidence) |
| POST | `/pending-updates/{finding_id}/confirm` | editor | **Граница подтверждения**: валидация → apply → save → refresh_temporal. Отказ — с причиной |
| POST | `/pending-updates/{finding_id}/reject` | editor | Отклонить с причиной; WorldModel не трогается |

Все ответы: `{"ok": true, "data": ...}`; ошибки: 404 (finding не найден), 409 (не в pending статусе / validation fail), 400, 403.

### 3.3 Инварианты (унаследованные из M10, без изменений)

1. Никаких автономных действий: никаких фоновых сканов/таймеров — scan только по явному POST.
2. Без confirm WorldModel не меняется (менеджер уже это гарантирует; endpoint'ы не обходят менеджер).
3. Canon не понижается, DERIVED не повышается — логика менеджера, endpoint только проксирует.
4. Save — только через confirm-путь менеджера (абсолютный канонический путь).
5. Refresh temporal engine — только после подтверждённого изменения.
6. Никаких изменений в provenance-модели и ADR-0001.

### 3.4 Реализация (минимальная)

- **Новый файл** `runtime/core/routes/temporal_updates.py` (~150 строк): singleton-менеджер (lazy), 7 endpoint'ов, Pydantic-модели ответов.
- **Одна строка** в `book_routes.py`: import + include_router.
- **Новый тест** `runtime/tests/test_m10_2_pending_updates_api.py`: RBAC-границы (401/403/200 по ролям), scan-идемпотентность, confirm-цикл на изолированном менеджере (не на каноническом файле!), reject-путь, 404/409 ошибки.
- Существующий код НЕ изменяется (кроме include_router в book_routes.py).

### 3.5 Изоляция тестов

- Тесты подменяют singleton-менеджер роута на тестовый (с явным `world_model_path` в tmp — паттерн M10) и `dependency_overrides` для ролей.
- Канонический WORLD_MODEL.json не затрагивается (проверка hash в тестах — паттерн M10).

### 3.6 DoD

1. Все 7 endpoint'ов работают, отвечают по конвенции `{"ok": ...}`.
2. RBAC: reader — только чтение; editor — scan/confirm/reject; без авторизации — 401.
3. Scan дважды без изменения книги → второй 0 новых (идемпотентность).
4. Confirm через API = тот же путь, что менеджер M10 (validation + save + refresh); подтверждено тестом.
5. Reject через API не меняет WorldModel.
6. Регрессия: 383 + M10.2 тесты зелёные.
7. Канонические данные не изменены (hash-проверка в тесте).

### 3.7 Вопросы владельцу (блокируют реализацию)

1. **Роль для confirm/reject**: предлагаю `editor` (команда проекта; admin — только для системных операций). Подтвердить или изменить на `admin`?
2. **История подтверждений**: менеджер хранит её in-memory (исчезает при перезапуске процесса). Для M10.2 это приемлемо (как и сама очередь). Персистентность истории — отдельная задача, не сейчас. Подтвердить?

---

## 4. Вердикт аудита

| Проверка | Статус |
|----------|--------|
| Все точки интеграции существуют | ✅ |
| Переписывание существующих подсистем не требуется | ✅ |
| Конфликты с контрактами M2–M10 | не обнаружены |
| Инварианты M10 переносимы на API-слой без изменений | ✅ |
| Готовность к SPEC | ✅ (DRAFT выше, 2 вопроса владельцу) |
