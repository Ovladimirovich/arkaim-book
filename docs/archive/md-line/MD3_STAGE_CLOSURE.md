# MD-3 — STAGE CLOSURE (зафиксировано как завершённый этап)

> **⚠️ ЧАСТИЧНО УСТАРЕЛ (2026-09-14).** Раздел «Место в линейке» и «Что дальше?» ссылаются на MD-4 как на следующий этап. MD-4 и MD-5 уже завершены (коммиты `81612b7`, `b5d399d`, `d73d29a`). Сам факт закрытия MD-3 — верен. Полный актуальный статус — в `docs/CURRENT_DEVELOPMENT_STATE.md`.

**Дата закрытия:** 2026-09-12
**Статус:** **CLOSED / FINAL GREEN** — все три подэтапа MD-3 приняты владельцем (история ACCEPT ниже).
**Место в линейке (факт):** MD-1 Foundation (✅) → MD-2 Scene Context Consolidation (✅ CLOSED) → **MD-3 MediaPlan Contract v0 (✅ CLOSED — этот документ)** → далее: MD-4 (✅ CLOSED), MD-5 (✅ ACCEPTED). Следующий — MD-6, требует owner-GO.
**Основа:** MEDIA_DIRECTION_FOUNDATION §PROPOSED ROADMAP DELTA (этап MD-3 «MediaPlan Contract v0»); ADR_MEDIA_PLAN_V0 (ACCEPTED, 10 owner decisions).

---

## Простыми словами

1. **Что это за документ?** — официальная фиксация: этап MD-3 («Контракт медиаплана») полностью завершён и закрыт. Больше к нему не возвращаемся без отдельного решения.

2. **Что этап дал проекту?** — в системе появился единый смысловой контракт «задание на генерацию» (MediaPlan): что в кадре, где, когда, в каком стиле, откуда мы это знаем и от какого плана он происходит. Все пять маршрутов генерации работают через него. Контракт гарантированно не знает исполнителя (ни модели, ни сида, ни провайдера) — это доказано тестами на каждом уровне.

3. **Как проходил этап?** — три подэтапа, каждый с вашим STOP и ACCEPT: контракт (MD-3.1) → пять маршрутов по одному (MD-3.2 A/B/C/D/E) → выравнивание внешней схемы и метки устаревания (MD-3.3). Все исторические результаты сохранены байт-в-байт — это проверено крипто-хэшами промптов до/после.

4. **Что осталось за кадром (намеренно)?** — исполнительный мост (ExecutionDispatch) — временный, умрёт в MD-5; «мёртвые» параметры (quality и др.) — не оживлены, решение MD-4/5; часть старых функций помечена устаревшими, но ничего не удалено. Полный регистр отложенных пунктов — §5.

5. **Что дальше?** — MD-4 и MD-5 уже завершены (коммиты `81612b7`, `b5d399d`, `d73d29a`). Следующий шаг — MD-6, требует отдельного owner-GO. См. `docs/CURRENT_DEVELOPMENT_STATE.md` и `docs/MD5_MIGRATION_REPORT.md`.

---

## 1. История приёмки (хронология GO/ACCEPT владельца)

| Подэтап | Объём | Документы | Вердикт владельца |
|---------|-------|-----------|-------------------|
| MD-3 PRE-AUDIT | forensic-аудит, находки MP-F1…F12 | MD3_PRE_IMPLEMENTATION_AUDIT.md | принят (владелец GO на MD-3) |
| **MD-3.1** контракт | MediaPlan v0 (pydantic, 22 поля) + Builder + ExecutionDispatch + JSON-Schema + ADR + 40 тестов | MD3_1_IMPLEMENTATION_REPORT.md, ADR_MEDIA_PLAN_V0.md | **ACCEPTED** |
| **MD-3.2 Route D** `/assets/generate-context|-character|-location` | baseline + миграция + 15 тестов | MD3_2_ROUTE_D_{BASELINE,IMPLEMENTATION_REPORT}.md | **ACCEPTED** |
| **MD-3.2 Route A** `/visualize` | baseline + миграция + 12 тестов; PA-F1 закрыт на уровне MediaPlan | MD3_2_ROUTE_A_{…} | **ACCEPTED / CLOSED** |
| **MD-3.2 Route B** `/visualize/epoch` | baseline + миграция + 10 тестов; temporal read-only | MD3_2_ROUTE_B_{…} | **ACCEPTED / CLOSED / FINAL GREEN** |
| **MD-3.2 Route C** `/assets/generate` | baseline + классификация параметров + 12 тестов | MD3_2_ROUTE_C_{…} | **ACCEPTED / CLOSED** |
| **MD-3.2 Route E** `/film/…/shots/{id}/generate` | baseline + 14 тестов; dead-поля не оживлены | MD3_2_ROUTE_E_{…} | **ACCEPTED / CLOSED** |
| **MD-3.3** schema+deprecation+docs | pre-audit → минимальная реализация: additionalProperties, 2 метки, реестр, 31 тест | MD3_3_PRE_IMPLEMENTATION_AUDIT.md, MD3_3_DEPRECATION_REGISTRY.md, MD3_3_IMPLEMENTATION_REPORT.md | **ACCEPTED / CLOSED** (ждёт финальной фиксации этим документом) |

## 2. Итоговое состояние (что теперь правда в системе)

**Канонический путь (единственный, 7 точек входа):**
```
request → SceneContext (MD-2 builder, 4 варианта входа)
  → MediaPlanBuilder → MediaPlan (extra=forbid, BANNED-инвариант)
  → ExecutionDispatch (TEMPORARY → MD-5)
  → legacy prompt projection (byte-identical) → существующие providers/runtime
```

**Инварианты, которые теперь держат тесты (финальные цифры):**
- execution-поле → MediaPlan/Pydantic **FAILS** (extra="forbid"; 40 тестов MD-3.1);
- execution-поле → JSON Schema **FAILS** (additionalProperties=false; 31 тест MD-3.3);
- исторические промпты всех 5 маршрутов — **байт-в-байт** (SHA-сверки в отчётах маршрутов);
- WorldModel/temporal — только чтение (инварианты маршрутов B/E);
- второй canonical path / второй Builder — **нет** (git-grep: 7 точек через один Builder).

**Финальная регрессия этапа:** 149/149 (MD-3.3+3.1+3.2 A/B/C/D/E + md2, оба порядка); визуальный чанк 257P/4F (4F — pre-existing test_assets_new_params); кино-зона 40/40; MD-3-набор целиком 111 тестов (40+12+10+12+15+14+31 — без учёта md2).

## 3. Что MD-3 сознательно НЕ делал (границы выдержаны)

MD-4/MD-5 · перенос ComfyUI/providers · Media Project · удаление legacy-слоёв/промпт-генераторов/dispatch · frontend · WorldModel/temporal/C2 · quality/negative/camera/duration-оживление · словари стилей · async/batch-миграция · БД/F-12 · audio · «cleanup заодно». Нарушений границ не зафиксировано (forensic-чек-листы всех сессий — зелёные).

## 4. Артефакты этапа (полный список)

**Production-код (новое):** `core/CORE/media_plan/{__init__,schemas,builder,dispatch}.py` (MD-3.1)
**Production-код (изменённый, зоны маршрутов):** `runtime/core/routes/{visual,assets,film_studio}.py` · `core/CORE/visual_assets/pipeline.py` (MD-3.2) · `SCHEMAS/MEDIA_PLAN.schema.json` + 2 docstring-метки (MD-3.3: `visualization/prompt_builder.py`, `runtime/core/adc_deps.py`)
**Тесты (7 файлов, 134 теста MD-3):** test_md3_media_plan.py (40) · route_a (12) · route_b (10) · route_c (12) · route_d (15) · route_e (14) · test_md3_route_deprecations.py (31)
**Документы (17):** MD3_PRE, MD3_1_REPORT, 10 × MD3_2_ROUTE_* (baseline+report), MD3_3_PRE_AUDIT, MD3_3_DEPRECATION_REGISTRY, MD3_3_IMPLEMENTATION_REPORT, ADR_MEDIA_PLAN_V0 + этот closure.

## 5. Открытые пункты, передаваемые дальше (реестр долга — ничего не потеряно)

| Пункт | Где зафиксирован | Чей | Когда |
|------|------------------|-----|------|
| ExecutionDispatch + legacy-промпт-проекции (A/B/C/E) | ADR D4; метки «MD-5: удалить» | MD-5 | при интеграции |
| Quality (MP-F1) — мёртв, управление качеством | BANNED-инвариант; реестр §4 | MD-4/5 | Media-сторона |
| Negative до провайдера (MP-F2) + dispatch.negative без consumers (F-33-2) | MD-3.1 §10; MD-3.3-реестр | MD-4/5 | Media-сторона |
| Video-план Route C не доходит до generate_video (F-33-1) | MD-3.3-реестр | кандидат MD-4 | сигнатура pipeline |
| Словари стилей ×3 (MP-F8) | MD-3.1 §10 | MD-4+ / отдельное решение | консолидация |
| Dead-поля шота E camera/duration/negative (MP-F10) | Route E-отчёт; реестр | решение владельца | отдельно |
| Висячие `__all__`-строки adc_deps (F-33-4) + F401/W293/F822-lint | MD-3.3-отчёт §8 | MD-5+ / cleanup-этап | отдельно |
| Regenerate/async/batch-очередь — без плана | Route C/E-отчёты; реестр §2 | MD-4/5 (migration запрещена в MD-3) | при переносе |
| Персистенция планов (plan_id одноразовые) | MD-3.2-отчёты (оговорки) | MD-4 (Media Project storage) | bootstrap |
| test_assets_new_params ×4 · TestFeedbackStore ×12 (TEMP) · COMFYUI_URL-зависимость тестов | все отчёты §pre-existing | тест-инфра | отдельно |
| Рабочее дерево: работа MD-2/MD-3 не закоммичена (политика сессий) | git status | решение владельца | см. предложение |

## 6. Фиксация

Этап **MD-3 «MediaPlan Contract v0»** — **завершён и закрыт**: контракт спроектирован, внедрён во все пять маршрутов генерации, выверен с внешней схемой, снабжён метками устаревания и документацией; исторические контракты сохранены без единого регресса; границы этапа не нарушены.

Следующий этап — **MD-6**, требует отдельного owner-GO. MD-4 и MD-5 завершены (коммиты `81612b7`, `b5d399d`, `d73d29a`). Ничего не начато автоматически.

---

*Документ создан по команде владельца «зафиксировать MD-3 как законченный этап». Служит точкой входа для будущих аудитов: полная история — в перечисленных отчётах.*
