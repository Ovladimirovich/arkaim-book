# M10 — IMPLEMENTATION REPORT (Temporal Updates from Book)

Дата: 2026-09-08
Статус: **ACCEPTED & CLOSED (2026-09-08)**
Пост-аудит: `docs/M10_POST_IMPLEMENTATION_AUDIT.md` (16/16 PASS, регрессия 383/383, найденный дефект исправлен)
Продолжение: M10.2 (pending-updates endpoint) — авторизовано владельцем после принятия M10

---

## Простыми словами

**1. Что было целью?**
Научить систему замечать изменения текста книги, находить в них факты о времени (даты, эпохи, длительности), показывать их человеку как «предложения» — и только после явного подтверждения человека вносить их в модель мира, с последующей перестройкой временно́го движка.

**2. Что реально сделано?**
- **Детектор изменений книги**: следит за файлом КНИГА.md по дате изменения + контрольной сумме (как «Пульс» следит за файлами знаний). Если текст реально изменился — сигнал; если файл просто «тронут» без правок — сигнал не подаётся (лишних срабатываний нет).
- **Извлекатель временных фактов**: словарный поиск дат («4000 лет до н.э.»), именованных эпох («в эпоху Кали Юги», «во время Аркаима» — узнаёт эпохи в любом падеже) и относительных выражений («многие века», «спустя тысячелетия»).
- **Разделение фактов по достоверности** (главное требование):
  - прямая дата или прямое имя эпохи в книге → **AUTHOR_CANON** («слова автора»);
  - расплывчатое выражение, которое система сама переводит в «века/тысячелетия» → **DERIVED** («догадка системы»).
- **Очередь предложений**: находки складываются в список «ожидает решения человека». Модель мира при этом НЕ трогается.
- **Ворота подтверждения**: человек говорит «да» → предложение проходит проверку правил (нельзя понизить «слова автора», нельзя выдать «догадку» за «слова автора») → только тогда запись в модель мира + сохранение файла + перестройка временно́го движка.
- **Перестройка движка**: новый метод `refresh_temporal()` в WorldEngine — движок времени заново собирается из обновлённой модели мира.
- **24 теста**, покрывающие все 12 пунктов контракта из спецификации.

**3. Что получилось?** — **PASS** (24/24 новых теста; 383 теста полной регрессии временно́й цепочки M2–M10 — все зелёные).

**4. Есть ли проблемы?**
- **Обнаружена и устранена в процессе**: первый прогон тестов «зацепил» существующую особенность кода — сохранение модели мира без явного пути зависит от текущей папки запуска. Тест записал тестовые данные не туда, из-за чего 8 соседних тестов упали. Мусор удалён, код менеджера исправлен (всегда пишет по абсолютному пути), тесты изолированы. Канонический файл WORLD_MODEL.json при этом **не был повреждён** (проверено по git: ни одного изменения в файлах данных).
- Существующие подсистемы не переписывались: 3 новых модуля + 1 новый метод. Единственный тронутый существующий файл — world_engine.py, и в нём только добавление (не изменение M5.1).

**5. Что предлагается дальше?**
- Пост-implementation аудит M10 (по установленному порядку M5–M9): проверка git diff, инвариантов, регрессии независимым взглядом.
- После принятия M10 — по готовности M10.2 (endpoint очереди предложений), если владелец сочтёт нужным.

---

## Техническая часть

### Изменённые файлы

| Файл | Тип | Объём | Назначение |
|------|-----|-------|------------|
| `core/CORE/narrative_engine/research/book_change_detector.py` | NEW | 135 строк | BookChangeDetector: mtime→hash→snapshot по КНИГА.md (паттерн Pulse.watch) |
| `core/CORE/narrative_engine/research/temporal_extractor.py` | NEW | ~270 строк | TemporalExtractor: словарь temporal-маркеров, AUTHOR_CANON vs DERIVED |
| `core/CORE/narrative_engine/research/temporal_update_manager.py` | NEW | ~290 строк | TemporalUpdateManager: pending queue, confirmation gate, refresh |
| `core/CORE/narrative_engine/world_engine.py` | EDIT | +28 строк | `refresh_temporal(world_model=None) -> bool` — добавлен рядом с enable_temporal (M5.1 не изменён) |
| `runtime/tests/test_m10_temporal_updates.py` | NEW | 24 теста | Контрактные тесты всех 12 пунктов SPEC |
| `docs/M10_IMPLEMENTATION_PLAN.md` | NEW | — | Implementation plan (зафиксирован до кодирования) |

НЕ изменялись: reconstruction_engine.py (M3/M8.1), future_extrapolator.py (M8), pulse/layers.py (M9), world_model.py, entity_extractor.py, world_model_writer.py, canon_validator.py, ADR-0001, модель provenance, роуты, UI.

### Фактический поток данных

```
КНИГА.md (213 KB, ADR-0001: первичный источник)
   │  polling: вызывающий код вызывает watch()
   ▼
BookChangeDetector.watch()
   ├─ mtime не изменился → None (дешёвая проверка, файл не читается)
   ├─ mtime изменился, hash тот же → None (touch без правок)
   └─ hash изменился → BookChangeSnapshot(content=вся книга)
   ▼
TemporalExtractor.extract(content)
   ├─ «4000 лет до н.э.» → TemporalFinding(kind=absolute_date, AUTHOR_CANON)
   ├─ «в эпоху Кали Юги» → TemporalFinding(epoch:kali_yuga, AUTHOR_CANON)
   ├─ «многие века» → TemporalFinding(period:CENTURY, DERIVED)
   └─ ошибка → [] + log (graceful)
   ▼
TemporalUpdateManager.submit_findings()
   ├─ дедупликация по id (повторная submit → 0 новых)
   └─ → pending queue (in-memory)
   ▼
   ════ ГРАНИЦА: WorldModel НЕ ИЗМЕНЁН ════
   ▼
confirm(finding_id)  ← человек
   ├─ валидация: категория ∈ {AUTHOR_CANON, DERIVED}; иначе reject
   ├─ применение: tag добавляется к provenance эпохи (не перезапись);
   │   duration_years для числовых дат на эпоху без duration
   ├─ WorldModel.save() — по абсолютному каноническому пути
   └─ WorldEngine.refresh_temporal(world_model) — новый instance движка
```

### Проверки provenance (реализованные)

| Ситуация | Поведение |
|----------|-----------|
| Прямая дата/имя эпохи в книге | AUTHOR_CANON, confidence 0.9 |
| «Многие века» → «период: ВЕК» | DERIVED, confidence 0.5 |
| confirm() DERIVED-находки | в provenance попадает как DERIVED (никогда не AUTHOR_CANON) |
| confirm() на эпоху с существующим AUTHOR_CANON tag | tag остаётся, добавляется DERIVED (canon не понижается) |
| Finding с невалидной категорией (UNKNOWN) | reject до применения, reason=invalid_category |
| Finding на несуществующую эпоху | reject, reason=apply_failed |
| confirm() несуществующего id | reject, reason=finding_not_found |
| reject() человеком | pending снят, WorldModel не тронут |

### Граница подтверждения (главный инвариант)

- `submit_findings()` не вызывает ни save(), ни изменения полей WorldModel — проверено тестом `test_no_confirmation_worldmodel_unchanged` (сравнение provenance и duration до/после).
- `confirm()` — единственный путь к save(); вызывает валидацию до применения.
- Автоприменение отсутствует как класс: в коде нет пути от extractor'а к WorldModel без confirm().

### Тесты

**M10 контрактные (24 теста, 6 групп):**

| Контракт SPEC | Тест(ы) | Статус |
|---------------|---------|--------|
| 1. Обнаружение изменения книги | test_detect_book_change_mtime | PASS |
| 2. Нет изменения → нет update | test_detect_no_change_no_update, test_touch_without_content_change_no_snapshot | PASS |
| 3. Извлечение temporal фактов | test_extract_absolute_date_author_canon, test_extract_named_epoch_author_canon | PASS |
| 4. AUTHOR_CANON vs DERIVED | test_extract_relative_period_derived, test_derived_never_promoted_to_canon | PASS |
| 5. Pending при создании | test_findings_created_as_pending | PASS |
| 6. Без подтверждения WM не меняется | test_no_confirmation_worldmodel_unchanged | PASS |
| 7. Подтверждённый update валиден | test_confirmed_update_applies_and_refreshes | PASS |
| 8. Невалидный/конфликтный reject | test_invalid_finding_rejected, test_epoch_binding_to_unknown_epoch_rejected, test_confirm_nonexistent_finding_fails | PASS |
| 9. Refresh движка после confirm | test_confirmed_update_applies_and_refreshes, test_refresh_creates_new_engine | PASS |
| 10. Идемпотентность | test_reprocess_idempotent | PASS |
| 11. Provenance после refresh | test_provenance_preserved_after_refresh, test_existing_canon_not_downgraded | PASS |
| 12. Graceful errors | test_extract_graceful_error_handling, test_detector_missing_file_graceful, test_refresh_without_epochs_returns_false | PASS |

**Регрессия (единый запуск):** 383 passed — включает M10 (24) + M9 expansion (38) + M8.1 present anchor + M8 future extrapolation + M5 temporal integration + M7 epoch visual + temporal model/integration/routes/reconstruction + world_engine (2 файла) + provenance.

### Инцидент в процессе (исправлен, раскрыт полностью)

**Что случилось**: первый прогон полной регрессии дал 8 FAIL в M8.1/M5/M7. Причина: `WorldModel.save()` без явного пути пишет в cwd-относительный путь (существующая особенность, не M10-код). Мой менеджер в тестах вызывал save() без пути → тестовые данные (2 эпохи) записались в `runtime/core/CORE/.../WORLD_MODEL.json` → последующие `WorldModel.load()` в соседних тестах нашли мусорный файл первым (search path от cwd).

**Почему важно**: это существовавший quirk, который M10 «зажёг» первым. Для production он означал бы: запуск сервиса не из корня проекта сохранил бы модель мира в случайную папку.

**Исправление**:
1. Мусорный файл удалён (`runtime/core/CORE/narrative_engine` целиком).
2. `TemporalUpdateManager._save_world_model()` резолвит абсолютный канонический путь сам (не полагается на дефолт save()).
3. Тесты используют явный test-local путь (`tests/tmp_m10/world_model_test_output.json`, очищается фикстурой).

**Проверка последствий**: `git diff --stat -- core/CORE/narrative_engine/data/ core/SOURCE_OF_TRUTH/` пуст — канонические данные не изменены. `updated_at` канонического WORLD_MODEL.json = 2026-07-16 (июль, до M10).

### Замечание для владельца (решение НЕ требуется, только информирование)

Обнаруженный quirk `WorldModel.save()` (cwd-зависимость) остаётся в существующем коде — я его НЕ правил, потому что это изменение существующей подсистемы вне рамок M10 (правило: минимальные адаптеры, не переписывать). Мой менеджер его обходит. Если захотите починить сам `world_model.py` — это отдельная микро-задача (одна строка: абсолютный путь по умолчанию).

### DoD SPEC (сверка)

| Пункт SPEC | Статус |
|------------|--------|
| Polling детектор по паттерну Pulse.watch | ✅ mtime→hash, без watcher/websocket |
| Гранулярность: весь файл перечитывается | ✅ snapshot.content = вся книга |
| pending-updates endpoint НЕ реализован | ✅ очередь internal, роутов нет |
| Инкрементальный парсинг НЕ реализован | ✅ |
| Новых зависимостей нет | ✅ только stdlib (hashlib, re, dataclasses) |
| ADR-0001 не изменён | ✅ |
| Модель provenance не изменена | ✅ используются существующие ProvenanceCategory/Tag |
| UI/UX не тронут | ✅ |
| 12 контрактных тестов | ✅ 24 теста |
| Регрессия зелёная | ✅ 383 passed |
| Suggest-only | ✅ подтверждено тестом границы |
