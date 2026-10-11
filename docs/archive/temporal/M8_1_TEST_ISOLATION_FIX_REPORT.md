# M8.1 Test Isolation Fix — Report

**Дата:** 2026-09-13
**Статус:** TESTED (готов к принятию)
**Этап:** минимальный test-isolation fix (owner-mandated, Этап 1 перед MD-4)
**Правило:** изменён ТОЛЬКО test-код; production не тронут.

---

## Простыми словами

**Цель:** устранить старый дефект, при котором один тест (M8.1) «включал» временную модель
навсегда и этим ломал следующий тест (M9) при совместном запуске.

**Сделано:** в тесте `test_full_pipeline_via_world_engine` добавлена очистка:
после проверки тест возвращает временную модель в исходное выключенное состояние.

**Результат:** PASS. Полный temporal-набор: **было 206/207 → стало 207/207**.

**Проблемы:** нет. Побочных эффектов не обнаружено (см. контрольные прогоны ниже).

**Дальше:** Этап 2 — MD-4 pre-implementation forensic audit (audit-only), затем STOP
и ожидание owner-GO.

---

## 1. Дефект (forensic)

**Симптом.** Полный temporal chunk падал ровно на одном тесте:

```
tests/test_m9_expansion_temporal.py::TestGracefulFallback::
    test_temporal_query_without_engine_returns_none
AssertionError: result is None or result.source.startswith("expansion:")
    → фактически получен temporal-ответ («[Реконструкция] Предыстория Аркаима…»)
```

при том, что:
- изолированный запуск жертвы — **pass**;
- файл m8_1 целиком + жертва — **fail**;
- m8_1 минус один тест + жертва — **pass** (32 passed, 1 deselected).

**Корневая причина.** `test_full_pipeline_via_world_engine`
(`runtime/tests/test_m8_1_present_anchor.py`, класс `TestPresentToArkaimComputedPath`)
вызывает `get_world_engine().enable_temporal()` на **процессном синглтоне**
`WorldEngine` (`_world_engine_cache`), и после теста не восстанавливает состояние.
Следующие в процессе тесты, резолвящие temporal через facade
`get_world_engine()` (`ExpansionLayer.respond_to` → `we.temporal_engine`),
получают включённый движок, хотя тест жертвы описывает поведение «без движка».

Воспроизведено минимальными комбинациями:
- `test_full_pipeline_via_world_engine` + жертва → **fail** (2 теста достаточно);
- `temporal_model + m8_1 + жертва` → fail (96-я позиция);
- подтверждено, что endpoint `/book/temporal/future-extrapolation` сам temporal
  не включает (`FutureExtrapolator(wm)` строится локально) — загрязнение вносил
  исключительно тест.

**Почему раньше не ловилось.** Дефект существует с фазы M8.1; проявляется только при
совместном прогоне в одном pytest-процессе с определённым порядком тестов
(жертва после загрязнителя). Требование запуска полного набора (CI: `pytest tests/`)
делало его критичным для публикации репозитория.

## 2. Исправление (минимальное, test-only)

Одно место в `runtime/tests/test_m8_1_present_anchor.py`,
метод `test_full_pipeline_via_world_engine`:

- assertions обёрнуты в `try/finally`;
- в `finally` состояние синглтона восстанавливается: `we._temporal_engine = None`.

Обоснование выбора способа:
- `invalidate_world_engine()` (публичная альтернатива) сбрасывает **весь** синглтон
  (пересоздание WorldEngine, переиндексация) — заметно тяжелее и не требуется;
- прямое восстановление приватного поля из теста — минимальное вмешательство,
  не меняет ни production-API, ни фикстуры, ни другие тесты.

Чего фикс НЕ делает (по мандату): не трогает production, WorldModel, temporal runtime,
fixture architecture, другие тесты, другие failures.

## 3. Верификация

| Прогон | До | После |
|---|---|---|
| Минимальная пара (загрязнитель + жертва) | fail | **pass** |
| `temporal_model + m8_1 + жертва` (repro-тройка) | fail (95/96) | **pass (96/96)** |
| Полный temporal chunk (7 файлов) | 206/207 | **207/207** |
| MD-3 suite (контроль инцидентности) | 134/134 | **134/134** |
| `test_m8_1_present_anchor.py` изолированно | 33/33 | **33/33** |
| `test_m9_expansion_temporal.py` изолированно | 38/38 | **38/38** |
| m5-файл + m8_1 + m9-жертва (перекрёстный контроль) | — | **pass** |

Рабочее дерево после отката известного churn (`core/CORE/genome/history/index.json` —
автозапись генома при прогонах тестов): изменён **только** `test_m8_1_present_anchor.py`.

## 4. Остаточный риск

- Тест по-прежнему использует приватное поле `we._temporal_engine` (запись).
  Если M-фазы в будущем сменят механизм хранения temporal на синглтоне, тест
  сломается и потребует актуализации. Учитывая замороженный статус temporal-линии
  (не предмет MD), риск принят сознательно.
- Дефект класса «синглтон без snapshot/restore» может иметь аналоги в других
  тестах (не проверялось — вне мандата; фикс строго одного теста).

## 5. Статусы

- Изоляция теста M8.1: **IMPLEMENTED** (test-only, 1 метод).
- Верификация: **TESTED** (207/207 temporal chunk; 134/134 MD-3 unaffected).
- Production: **не изменён** (git diff подтверждает).

## 6. Что дальше (предложение, не автоматически)

- Зафиксировать этот фикс отдельным коммитом (по желанию владельца).
- Перейти к Этапу 2: MD-4 pre-implementation forensic audit (audit-only).
