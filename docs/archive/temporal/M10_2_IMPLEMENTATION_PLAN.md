# M10.2 IMPLEMENTATION PLAN

Дата: 2026-09-08
Основание: M10.2 PRE-IMPLEMENTATION AUDIT — APPROVED (владелец); оба проектных решения утверждены:
RBAC (reader=просмотр, editor/admin=confirm+reject) и in-memory persistence (без БД).
SPEC DRAFT из `docs/M10_2_PRE_IMPLEMENTATION_AUDIT.md` — основа, не расширяется.

---

## Сверка плана с утверждённым SPEC (7 endpoint'ов)

| SPEC endpoint | Реализация | Контракт-основа |
|---------------|-------------|-----------------|
| POST `/book/temporal/pending-updates/scan` | Нова функция в новом модуле | BookChangeDetector.watch() + TemporalExtractor.extract() + manager.submit_findings() |
| GET `/book/temporal/pending-updates` | list pending | manager.pending |
| GET `/book/temporal/pending-updates/stats` | счётчики | manager.stats() |
| GET `/book/temporal/pending-updates/history` | confirmed+rejected | manager.confirmed / manager.rejected |
| GET `/book/temporal/pending-updates/{finding_id}` | детали | поиск по pending+confirmed+rejected |
| POST `/book/temporal/pending-updates/{finding_id}/confirm` | confirmation gate | manager.confirm() (M10, БЕЗ изменений) |
| POST `/book/temporal/pending-updates/{finding_id}/reject` | reject | manager.reject() (M10, БЕЗ изменений) |

## Файлы для изменения

### Production (1 новый файл + 2 строки в существующем)

| Файл | Тип | Содержимое |
|------|-----|------------|
| `runtime/core/routes/temporal_updates.py` | NEW ~170 строк | singleton-менеджер (lazy, паттерн get_world_engine), 7 endpoint'ов, Pydantic-модели, RBAC (require_role), 404/409/403 |
| `runtime/core/book_routes.py` | EDIT +2 строки | import + include_router (как temporal_router M5) |

### Тесты (1 новый файл)

| Файл | Тестов |
|------|--------|
| `runtime/tests/test_m10_2_pending_updates_api.py` | ~18 |

### НЕ изменяются (весь M10-стек)

- `core/CORE/narrative_engine/research/*` (менеджер, детектор, извлекатель — используются как есть)
- `core/CORE/narrative_engine/world_engine.py` (refresh_temporal M10 не трогаем)
- `core/CORE/narrative_engine/temporal/*` (M2–M8.1)
- `core/CORE/narrative_engine/world_model.py` и data/ (канонические данные)
- `runtime/auth/rbac.py` (существующие RBAC-контракты)
- `runtime/core/routes/temporal.py` (M5 роуты)
- UI, БД, фоновые процессы — не добавляются

## Ключевые решения реализации

1. **Singleton-менеджер**: модульная lazy-функция `_get_manager()` в temporal_updates.py — создаёт `TemporalUpdateManager(world_model=WorldModel.load(), world_engine=get_world_engine())` при первом вызове, держит в module-level переменной. Паттерн идентичен `get_world_engine()` (world_engine.py:341).

2. **Scan-триггер**: один endpoint, вызывающий цепочку M10 по порядку: `detector.watch()` → если snapshot: `extractor.extract(snapshot.content)` → `manager.submit_findings()`. Если детектор не инициализирован — инициализирует (первый вызов = baseline, 0 находок). Никаких таймеров/фоновых задач — только явный POST.

3. **RBAC-проверки**: scan/confirm/reject = `Depends(require_role("editor", "admin"))`; GET-эндпоинты = `Depends(require_role("reader", "editor", "admin"))` (reader+ = все роли). 401 при отсутствии авторизации — обеспечивается get_current_user внутри require_role.

4. **HTTP-коды**: 404 (finding не найден), 409 (не pending / validation fail с reason), 200 с `{"ok": true, "data": ...}` — конвенция проекта.

5. **Тестовая изоляция**: conftest.py глобально подменяет admin — тесты RBAC-границ будут явно переключать `app.dependency_overrides[get_current_user]` на reader/editor/отсутствие и восстанавливать. Тесты confirm-цикла подменяют singleton-менеджер роута на тестовый (world_model_path → tmp, паттерн M10) — канонический WORLD_MODEL.json не затрагивается (hash-проверка до/после в тесте).

## DoD (из SPEC)

1. 7 endpoint'ов работают по конвенции `{"ok": ...}`.
2. RBAC: reader → 403 на confirm/reject/scan; editor → 200; без авторизации → 401.
3. Scan идемпотентен: дважды без изменения книги → второй 0 новых.
4. Confirm через API = путь менеджера M10 (validation→apply→save→refresh), включая refresh_temporal.
5. Reject через API не меняет WorldModel.
6. Регрессия 383 + новые тесты — зелёные.
7. Канонические данные не изменены (hash в тестах).
8. Остановка после отчёта; пост-аудит — отдельно (не автоматически).
