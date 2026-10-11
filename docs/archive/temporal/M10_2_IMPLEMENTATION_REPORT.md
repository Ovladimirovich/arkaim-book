# M10.2 — IMPLEMENTATION REPORT (Pending Updates API)

Дата: 2026-09-08
Статус: **ACCEPTED & CLOSED (2026-09-08)**
Пост-аудит: `docs/M10_2_POST_IMPLEMENTATION_AUDIT.md` (16/16 независимых проверок, регрессия 432/432, все 10 ограничений соблюдены)
Решение владельца: аудит принят, реализация закрыта без изменений; следующий этап — только по отдельному решению
Основание: M10.2 PRE-IMPLEMENTATION AUDIT — APPROVED; оба проектных решения утверждены владельцем
SPEC: `docs/M10_2_PRE_IMPLEMENTATION_AUDIT.md` (SPEC DRAFT утверждён как основа, не расширен)

---

## Простыми словами

**1. Что было целью?**
Открыть через HTTP API очередь temporal-предложений из M10: человек (или будущий UI) может посмотреть, что система нашла в книге, подтвердить или отклонить каждое предложение.

**2. Что реально сделано?**
- **7 API-эндпоинтов** под `/book/temporal/pending-updates`:
  - «Сканировать книгу» (запускает цепочку M10: заметить изменение → извлечь факты → положить в очередь);
  - «Список ожидает решения», «Счётчики», «История подтверждённого/отклонённого», «Детали предложения»;
  - «Подтвердить» и «Отклонить».
- **Права доступа — ровно как вы утвердили**: читатель (reader) видит только список и детали; редактор (editor) и администратор (admin) могут сканировать, подтверждать, отклонять. Без входа в систему — отказ (401). Читатель не имеет ни одного пути изменить модель мира — это отдельно проверено тестом.
- **Ничего лишнего**: persistence не добавлен (очередь в памяти процесса, как утверждено), фоновых процессов нет (сканирование только по явной кнопке), UI не тронут. Endpoint'ы — тонкая обёртка: вся логика подтверждения осталась в менеджере M10, ни строчки его логики не изменено.

**3. Что получилось?** — **PASS**: 24/24 контрактных теста M10.2; полная регрессия временной цепочки M2–M10.2 — **407/407**; канонический файл модели мира не тронут (проверено контрольной суммой в тесте).

**4. Есть ли проблемы?**
- Нет блокирующих. Одно уточнение по ходу: формат ошибок проекта оказался `{"ok": false, "error": {"code", "message"}}` (а не `detail`) — тест приведён к фактической конвенции проекта, поведение API соответствует существующим роутам.
- Напоминание (не проблема): очередь живёт в памяти процесса; после перезапуска сервера неподтверждённые предложения исчезают — пересоздаются одним нажатием «сканировать». Так утверждено вами для M10.2.

**5. Что предлагается дальше?**
Остановлен по вашей инструкции. Предлагаю пост-implementation аудит M10.2 (независимые проверки: git diff, RBAC-матрица на реальном app, изоляция данных, регрессия) — по установленному порядку. После вашего ACCEPTED — закрыть M10.2.

---

## Техническая часть

### Изменённые файлы

| Файл | Тип | Объём | Назначение |
|------|-----|-------|------------|
| `runtime/core/routes/temporal_updates.py` | NEW | ~290 строк | 7 endpoint'ов, singleton-менеджер (lazy), RBAC, 404/409 |
| `runtime/core/book_routes.py` | EDIT | +2 строки | import + include_router (образец: temporal_router M5) |
| `runtime/tests/test_m10_2_pending_updates_api.py` | NEW | 24 теста | RBAC-границы, scan-идемпотентность, confirm/reject-циклы, изоляция |
| `docs/M10_2_IMPLEMENTATION_PLAN.md` | NEW | — | план (зафиксирован до кодирования) |

НЕ изменены: весь M10-стек (`research/*`, `world_engine.py`, `temporal/*`, `world_model.py`), `auth/rbac.py` (существующие контракты), `routes/temporal.py` (M5), канонические данные, UI, БД. Подтверждающий gate менеджера M10 — без изменений, endpoint'ы только вызывают `confirm()/reject()/submit_findings()/stats()/pending/confirmed/rejected`.

### Фактический поток данных

```
Человек (editor/admin) → POST /book/temporal/pending-updates/scan
  → BookChangeDetector.watch()          [M10, без изменений]
      ├─ книга не менялась → {"book_changed": false, "new_findings": 0}
      └─ изменилась → snapshot.content (вся книга)
  → TemporalExtractor.extract(content)  [M10, без изменений]
  → manager.submit_findings()           [M10, без изменений] → pending queue

Человек (reader+) → GET /pending-updates, /stats, /history, /{id}
  → только чтение состояния менеджера

Человек (editor/admin) → POST /{id}/confirm
  → manager.confirm()                   [M10, без изменений: validation → apply → save → refresh]
      ├─ ok → {"applied": true, "world_model_saved": true, "temporal_refreshed": …}
      ├─ не найдено → 404
      └─ validation fail → 409 (reason)

Человек (editor/admin) → POST /{id}/reject
  → manager.reject()                    [M10, без изменений] — WorldModel не трогается
```

### RBAC-матрица (реализована и протестирована)

| Операция | reader | editor | admin | без авторизации |
|----------|:------:|:------:|:-----:|:---------------:|
| GET список/статистика/история/детали | ✅ 200 | ✅ 200 | ✅ 200 | ❌ 401 |
| POST scan | ❌ 403 | ✅ 200 | ✅ 200 | ❌ 401 |
| POST confirm | ❌ 403 | ✅ 200 | ✅ 200 | ❌ 401 |
| POST reject | ❌ 403 | ✅ 200 | ✅ 200 | ❌ 401 |

Проверено тестами: `test_reader_cannot_confirm/reject/scan`, `test_reader_can_view`, `test_reader_never_modifies_world_model` (все mutating-пути → 403, файл не появился), `test_no_auth_401`, `test_editor_can_*`.

### Endpoint-спецификация (фактическая)

| Метод+путь | Роль | 200-ответ | Ошибки |
|------------|------|-----------|--------|
| POST `/book/temporal/pending-updates/scan` | editor,admin | `{ok, data:{book_changed, snapshot?, extracted, new, duplicates, total_pending}}` | 401, 403 |
| GET `/book/temporal/pending-updates` | reader+ | `{ok, data:[findings], total}` | 401 |
| GET `/book/temporal/pending-updates/stats` | reader+ | `{ok, data:{pending, confirmed, rejected}}` | 401 |
| GET `/book/temporal/pending-updates/history` | reader+ | `{ok, data:{confirmed:[…], rejected:[…+reason]}}` | 401 |
| GET `/book/temporal/pending-updates/{finding_id}` | reader+ | `{ok, data:{finding, status, reason?}}` | 401, 404 |
| POST `…/{finding_id}/confirm` | editor,admin | `{ok, data:{applied, world_model_saved, temporal_refreshed, manager}}` | 401, 403, 404, 409 |
| POST `…/{finding_id}/reject` | editor,admin | `{ok, data:{applied:false, manager}}` | 401, 403, 404, 409 |

Формат ошибок — конвенция проекта (`main.py:380`): `{"ok": false, "error": {"code": "HTTP_409", "message": …}}`.

### Тесты (24, все PASS)

| Группа | Тестов | Что покрывает |
|--------|--------|---------------|
| TestEndpointAvailability | 3 | все 7 путей в OpenAPI, конвенция ответов |
| TestRBAC | 9 | матрица ролей, 403 reader на mutating, 401 без авторизации, reader-инвариант «ни одного пути изменить WM» |
| TestScanChain | 3 | идемпотентность (двойной scan без изменения книги), реальная книга без падений |
| TestConfirmRejectViaAPI | 6 | полный confirm-цикл (applied+saved), 404, повторный 409, reject не пишет файл, invalid_category 409, hash канонического файла неизменен |
| TestHistoryAndDetails | 3 | история confirmed+rejected с reason, детали по статусам, 404 |

**Регрессия**: M2–M10.2 одним запуском — **407 passed** (24 M10.2 + 24 M10 + 38 M9 + M8.1 + M8 + M5 + M7 + temporal model/integration/routes/reconstruction + world_engine ×2 + provenance).

**Production-smoke**: реальный singleton (без тестовых подмен) — scan/stats без авторизации → честный 401; singleton сброшен после проверки.

### Соблюдение ограничений владельца

| Ограничение | Статус |
|-------------|--------|
| Не менять M10 | ✅ research/*, world_engine.py, temporal/* — 0 изменений |
| Не менять TemporalEngine/TemporalModel | ✅ |
| Не добавлять persistence | ✅ in-memory singleton, как утверждено |
| Не добавлять фоновые процессы | ✅ scan только по явному POST |
| Не добавлять UI | ✅ |
| Не расширять API сверх SPEC | ✅ ровно 7 endpoint'ов из SPEC DRAFT |
| Не менять существующие RBAC-контракты | ✅ только используется require_role |
| Тонкая обёртка над TemporalUpdateManager | ✅ endpoint'ы только вызывают методы |
| Confirmation gate M10 без изменений | ✅ логика confirm() не тронута |
| reader никогда не изменяет WorldModel | ✅ тест-доказательство (403 на все mutating + файл не появился) |

### Изоляция данных в тестах

- Тесты подменяют singleton роута на изолированный менеджер: `world_model_path` → `tests/tmp_m10_2/…`, очищается фикстурой.
- `test_canonical_world_model_untouched_by_api_cycle`: sha256 канонического `WORLD_MODEL.json` до/после полного API-цикла (confirm + history + scan) — идентичен.
- Тесты RBAC переключают `dependency_overrides` и восстанавливают admin-override conftest'а.
