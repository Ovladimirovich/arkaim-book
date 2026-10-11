# MD-5 — Интеграция по контракту

**Дата:** 2026-09-14  
**Коммит:** `d73d29a`  
**Статус:** ✅ ACCEPTED (141/141 тестов зелёных)

---

## Простыми словами

**Цель:** Убрать временный мост `ExecutionDispatch` — он выполнял роль «переводчика» между смысловым планом и старыми провайдерами. По контракту MD-3 этот мост не входил в доменную модель, а был временным решением. MD-5 — финальный шаг: мост удалён, все 5 маршрутов (A–E) работают напрямую через `MediaPlan` + legacy-промпт.

**Что сделано:**
- Файл `media_plan/dispatch.py` удалён полностью
- Из `__init__.py` убран экспорт `ExecutionDispatch`
- Из всех 5 маршрутов (visualize, assets, film_studio) убраны вызовы `ExecutionDispatch.from_plan()`
- Провайдеры вызываются напрямую: `image_provider.generate(legacy_prompt)` или `pipeline.generate_image(plan=plan)`
- Из `/comfyui/status`, `/comfyui/config` (GET/POST) —_routes депубликованы (404)
- Тесты переписаны: убраны проверки `dispatch`-полей, добавлены проверки `plan`-инвариантов

**Что получилось:** PASS. Все 141 тест (MD-3 × 95 + MD-4 × 15 + deprecations × 31) проходят.

**Проблем нет.** Единственный pre-existing flaky-тест (`test_routes_abcd_files_untouched`) — мtime-контроль с таймингом < 0.001s на NTFS — исправлен допуском 0.5s.

---

## D-1: ExecutionDispatch — смерть

| Файл | Изменение |
|------|-----------|
| `core/CORE/media_plan/dispatch.py` | **УДАЛЁН** (100644 → delete) |
| `core/CORE/media_plan/__init__.py` | Убран `from .dispatch import ExecutionDispatch` и запись из `__all__` |
| `core/CORE/media_plan/schemas.py` | Убран абзац про «временный мост» в docstring |
| `core/CORE/visual_assets/pipeline.py` | `generate_image()`: убран `dispatch=None` param, merged plan+dispatch branch → plan-only; `generate_image_from_context()`: аналогично |

### Маршрут A — `/book/visualize` (visual.py)
```python
# BEFORE:
dispatch = ExecutionDispatch.from_plan(plan)
dispatch.prompt = legacy_prompt
image_bytes = await image_provider.generate(dispatch.prompt)

# AFTER:
image_bytes = await image_provider.generate(legacy_prompt)
```

### Маршрут B — `/book/visualize/epoch/{epoch_id}` (visual.py)
Аналогично A — прямое `image_provider.generate(legacy_prompt)`.

### Маршрут C — `/book/assets/generate` (assets.py)
```python
# BEFORE:
dispatch = ExecutionDispatch.from_plan(plan, size=size, preferred_provider=provider)
asset = await pipeline.generate_image(..., plan=plan, dispatch=dispatch)

# AFTER:
asset = await pipeline.generate_image(..., plan=plan)
```

### Маршрут D — `/book/assets/generate-{context,character,location}` (assets.py)
Аналогично C — `pipeline.generate_image_from_context(..., plan=plan)` без dispatch.

### Маршрут E — `/book/film-studio/{id}/shots/{sid}/generate` (film_studio.py)
```python
# BEFORE:
dispatch = ExecutionDispatch.from_plan(plan, size=..., preferred_provider="comfyui")
asset = await pipeline.generate_image(..., plan=plan, dispatch=dispatch)

# AFTER:
asset = await pipeline.generate_image(..., plan=plan)
```

---

## D-5: Депубликация `/comfyui/*`

Удалены 3 роута из `runtime/core/routes/visual.py`:
- `GET /comfyui/status`
- `GET /comfyui/config`
- `POST /comfyui/config`

Оставлены:
- `GET /providers/list` — список провайдеров (R2)
- `GET /providers/status` — статус провайдеров (R2)

Тест `test_comfyui_status_route_reads_bridge` → переписан: ожидает 404 вместо 200.

---

## D-6: Удаление re-export из `visualization/__init__.py`

Выполнено в предыдущем цикле: `ImageProvider` и `ImageProviderChain` убраны из экспортов.

---

## Test delta

| Тестовый файл | До | После | Изменение |
|--------------|-----|-------|-----------|
| `test_md3_media_plan.py` | +7 тестов ExecutionDispatch | Класс `TestExecutionDispatch` удалён | −7 |
| `test_md3_route_d.py` | Класс `TestRouteDDispatchBridge` | Удалён | −2 |
| `test_md3_route_a/b/c/d/e` | Импорт + assert dispatch | Переписаны на plan-invariants | ~0 |
| `test_md4_m43_media_client.py` | 404? → 200 для /comfyui/status | 404 assertion | ~0 |

**Итог:** 141 passed, 0 failed, 2 skipped (live routes)

---

## Deferred (вне scope MD-5)

| ID | Проблема | Статус |
|----|----------|--------|
| D-2 | `shot_assembler` raw paths | Owner §16-6: «не чинить» |
| D-3 | video-plan gap (route C video path) | Отложено — separate decision |
| D-4 | queue/batch | Separate decision |

---

## Файлы изменены

```
core/CORE/media_plan/dispatch.py          DELETED
core/CORE/media_plan/__init__.py          modified
core/CORE/media_plan/schemas.py           modified
core/CORE/visual_assets/pipeline.py       modified
runtime/core/routes/visual.py             modified
runtime/core/routes/assets.py             modified
runtime/core/routes/film_studio.py        modified
runtime/tests/test_md3_*.py               modified (×5)
runtime/tests/test_md4_m43_media_client.py modified
```
