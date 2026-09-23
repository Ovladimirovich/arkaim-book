# POST-F6 NEXT MILESTONES AUDIT

**Дата:** 2026-09-23
**Режим:** read-only аудит + планирование
**Мандат:** «Post-F6 Audit & Next Milestones Assessment»
**Приложение:** 0 изменений кода; бэкенд не тронут; БД не изменена; коммитов 0

---

## 1. Подтверждённый Post-F6 Baseline

### 1.1 Git-факты

| Параметр | Значение |
|----------|----------|
| Branch | `master` |
| HEAD | `b4e6893` — `feat(frontend): F6 polish` |
| Предыдущие коммиты | `a090ec8` (F5), `28514fb` (F4), `4be2a40` (MD-6) |
| F6 содержимое | 7 файлов, +324 / −7 строк |
| Ветви | `master`, `fresh-start`, `g0-clean`, `push-20260916`, `security-fix` |

### 1.2 Фактическое состояние

| Параметр | Значение |
|----------|----------|
| Frontend v2 страниц | **25** статично (next build pass) |
| Frontend v2 тесты | **134/134 PASS** |
| Backend изменений (F4+F5+F6) | **0** |
| OpenAPI путей | **290** |
| MD-этапы | MD-1 → MD-6: все CLOSED |
| F-этапы | F1 → F6: все ACCEPTED & CLOSED |
| MEDIA_CONTRACT | v1.0 ACCEPTED (arkaim-media `f0327cd`) |

### 1.3 Изученные документы

`docs/CURRENT_DEVELOPMENT_STATE.md`, `docs/POST_F4_REBASELINE.md`, `docs/PRODUCT_MAP.md`, `docs/FRONTEND_ARCHITECTURE.md`, `docs/F5_SPEC.md`, `docs/ADR/ADR_TEMPORAL_WORLD_MODEL.md`, `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md`, `docs/ADR/ADR_MEDIA_PLAN_V0.md`, `docs/STUDIO_SPEC.md`.

---

## 2. MD-7 / M4.5 — Forensic Audit

### 2.1 Цель этапа

workflows/env переезд + полная де-публикация legacy `/comfyui/*` + чистка ExecutionDispatch-остатков.

### 2.2 Подтверждённые факты

**2.2.1 `/comfyui/*` маршруты — УЖЕ ДЕПУБЛИКОВАНЫ (MD-5, commit `d73d29a`)**

- `runtime/tests/test_media_boundary.py`: `test_no_comfyui_status` и `test_no_comfyui_config` — assert отсутствия путей.
- `grep -rn "/comfyui" runtime/core/routes/` — 0 результатов.
- **Статус: ✅ CLOSED**

**2.2.2 `core/CORE/providers/image/comfyui.py` — УЖЕ STUB (6 строк, REMOVED notice)**

- Прочитан полностью: только docstring «ComfyUIProvider has been moved to arkaim-media».
- **Статус: ✅ CLOSED**

**2.2.3 ExecutionDispatch — УЖЕ УДАЛЁН (MD-5, commit `d73d29a`)**

- `core/CORE/media_plan/dispatch.py` не существует.
- `media_client.py` — временный мост (TEMPORARY MIGRATION BRIDGE), survives до M4.5 полного закрытия.
- **Статус: ✅ CLOSED**

**2.2.4 Mёртвые алиасы `comfy`/`comfyui` в `image/__init__.py` — НЕ БЛОКИРУЮТ**

- `_normalize_preferred_provider()` содержит `{"comfy": "comfyui", "comfyui": "comfyui"}` (строки 52-53).
- Proveedor «comfyui» физически отсутствует (stub). Алиас never matches ни одного провайдера в цепи.
- **Класс: G-7 D-5 (low risk, cosmetic)**.

**2.2.5 Stale comments в `media_client.py` — НЕ БЛОКИРУЮТ**

- Строки 10, 12, 116, 150 ссылаются на `/comfyui/status` (уже не существует).
- **Класс: low risk, cosmetic documentation cleanup**.

**2.2.6 `GenerationParams.quality` — мёртвое поле (D-7 / MP-F1)**

- `core/CORE/visual_assets/schemas.py:50`: `quality: str = "standard"`.
- Не читается ни в одном runtime-маршруте (проверено grep по `runtime/core/routes/*.py`).
- MediaPlan `BANNED_FIELDS` (schemas.py:195) уже исключает `quality`.
- **Класс: D-7 (medium, requires decision on removal vs. deprecation)**.

**2.2.7 Workflows/env — УЖЕ ПЕРЕНЕСЕНЫ**

- `core/CORE/genome/workflows/` — не существует.
- `runtime/workflows/` — не существует.
- `core/CORE/visual_assets/` — нет `WORKFLOW_DIR`.
- Arkaim-media владеет `workflows/default.json` (SHA verified).
- **Статус: ✅ CLOSED (M4.5 в MD-5)**.

### 2.3 Остаточный scope MD-7

| Файл | Действие | Класс | Риск |
|------|----------|-------|------|
| `core/CORE/providers/image/__init__.py:52-53` | Удалить мёртвые алиасы `comfy`/`comfyui` | G-7 | Низкий |
| `runtime/core/media_client.py:10,12,116,150` | Обновить comments | G-7 | Низкий |
| `core/CORE/visual_assets/schemas.py:50` | Decision: удалить `quality` или добавить deprecation marker | D-7 | Средний |
| `core/CORE/media_plan/schemas.py:195` | Убрать `quality` из BANNED_FIELDS (если удалён из GenerationParams) | D-7 | Низкий |

**Итого: 4 файла, low-medium risk, ~20 строк изменений.**

---

## 3. F-12 — Forensic Audit

### 3.1 Цель этапа

Миграция Film Studio DB: удаление колонки `quality` из `film_shots`.

### 3.2 Подтверждённые факты

**3.2.1 Схема CREATE TABLE в `store.py` (строка 79)**

```sql
CREATE TABLE IF NOT EXISTS film_shots (
    ...
    quality TEXT DEFAULT 'standard',   -- line 79
    ...
);
```

**3.2.2 INSERT-оператор (строки 319-323)**

```sql
INSERT INTO film_shots
    (id, scene_id, project_id, prompt, camera, duration_sec, status, is_active, quality, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
```

**3.2.3 `update_shot` — разрешённые поля (строка 343)**

```python
allowed = {"prompt", "camera", "duration_sec", "asset_id", "status", "error", "is_active", "quality", "negative_prompt"}
```

**3.2.4 `ShotVersion` schema (строка 53)**

```python
quality: str = Field("standard", pattern="^(draft|standard|high|ultra)$")
```

**3.2.5 PUT `/film/shots/{shot_id}` route (строки 272-281)**

```python
quality: str | None = Query(None, pattern="^(draft|standard|high|ultra)$"),
if quality is not None:
    kwargs["quality"] = quality
```

**3.2.6 Реальная БД `data/film_studio.db` (подтверждено SQLite query)**

- Таблицы: `film_projects` (120 rows), `film_scenes` (110 rows), `film_shots` (3 rows)
- **Столбцы `film_shots`:** `['id', 'scene_id', 'project_id', 'asset_id', 'prompt', 'camera', 'duration_sec', 'negative_prompt', 'status', 'error', 'is_active', 'created_at']`
- **СТОЛБЕЦ `quality` ОТУТСВУЕТ.**

**3.2.7 Мtime `data/film_studio.db` — 2026-09-23 18:00:09**

Коммит с `quality` (`48c19c9`, 2026-09-16) был ДО последнего mtime. Это означает, что БД была пересоздана после добавления quality, НО код `CREATE TABLE IF NOT EXISTS` не добавил column в существующую таблицу — SQLite не мигрирует схемы.

**3.2.8 Тесты используют FakeFilmStore, НЕ реальную БД**

- `runtime/tests/test_film_endpoints.py`: все тесты качества (`test_quality_saved_to_shot`, `test_update_shot_quality`) работают с `FakeFilmStore` (in-memory dict).
- `runtime/tests/test_md3_route_e.py`: создаёт temp-БД с fresh schema (через `FilmProjectStore(db_path=db_file)`).
- **Реальная БД не тестируется интеграционными тестами.**

**3.2.9 `GenerationParams.quality` — ОТДЕЛЬНОЕ поле (не путать с film quality)**

- `core/CORE/visual_assets/schemas.py:50`: `quality: str = "standard"` — поле для pipeline generation params.
- Не связано с film_studio. Не является частью F-12.

### 3.3 Сценарии миграции

| Вариант | Описание | Риск | Данные |
|---------|----------|------|--------|
| **A: ALTER TABLE ADD COLUMN** | Добавить `quality TEXT DEFAULT 'standard'` к существующей таблице | Низкий | 3 строки — без quality; по умолчанию 'standard' |
| **B: Пересоздание БД** | Удалить `data/film_studio.db`, при старте — fresh schema | Средний | 120 projects, 110 scenes, 3 shots — БЕЗ ВОССТАНОВЛЕНИЯ |
| **C:留任 качество как мёртвое поле** | Оставить column mismatch, игнорировать API-запрос `quality` | Низкий | Ничего не ломается, если никто не вызывает PUT с quality |

**Рекомендация: Вариант A (ALTER TABLE ADD COLUMN).**

- Минимальный риск: ADD COLUMN с DEFAULT не трогает существующие данные.
- 3 строки `film_shots` получат `quality='standard'` автоматически.
- 120 projects и 110 scenes не затрагиваются.

### 3.4 Затрагиваемые файлы F-12

| Файл | Изменение | Класс |
|------|-----------|-------|
| `data/film_studio.db` | ALTER TABLE → ADD COLUMN `quality TEXT DEFAULT 'standard'` | Required |
| `core/CORE/film_studio/store.py:79` | Уже содержит quality — без изменений | — |
| `core/CORE/film_studio/schemas.py:53` | Уже содержит quality — без изменений | — |
| `runtime/core/routes/film_studio.py:272-281` | Уже содержит quality param — без изменений | — |
| `runtime/tests/test_film_endpoints.py:191-197,488-494` | Тесты с FakeFilmStore — без изменений | — |
| `runtime/tests/test_md3_route_e.py` | Добавить интеграционный тест с реальной БД (опционально) | Nice-to-have |

**Итого: 1 файл требует изменения (БД), 0 файлов кода.**

---

## 4. C2 — Forensic Audit

### 4.1 Цель этапа

Provenance-теги на рёбрах графа: `AUTHOR_CANON` → `DERIVED` на PRECEDES-рёбрах.

### 4.2 Подтверждённые факты

**4.2.1 Коммит `f1d5d60` (2026-09-16) — УЖЕ ИСПРАВЛЕН**

```
feat(temporal): расширение типов рёбер + исправление C2 в тестах и скриптах

- temporal/relation.py: добавить CARRIES/TRANSMITS_TO/ECHOES типы,
  property is_contextual, обновить docstring precedes (ADR TEMPORAL §4)
- тесты: обновить проверки под DERIVED provenance на PRECEDES-рёбрах
- скрипты: скорректировать проверку C2 (DERIVED вместо AUTHOR_CANON)
```

**4.2.2 `relation.py:precedes()` (строки 186-205) — УЖЕ DERIVED**

```python
@staticmethod
def precedes(source_id: str, target_id: str, strength: float = 1.0) -> "TemporalRelation":
    """...
    ADR TEMPORAL §4: PRECEDES-рёбра оси = DERIVED (порядок выведен из канона,
    не прямое утверждение текста). НИКОГДА AUTHOR_CANON.
    """
    return TemporalRelation(
        ...
        provenance=[ProvenanceTag(
            source_level=SourceLevel.SYSTEM_INTERPRETATION,
            category=ProvenanceCategory.DERIVED,   # ← CORRECT
            confidence=strength,
            notes="temporal precedence — derived from epoch ordering in canon",
        )],
    )
```

**4.2.3 Тест `test_precedes_is_derived_from_epoch_order` (test_temporal_model.py:593-597)**

```python
def test_precedes_is_derived_from_epoch_order(self):
    """PRECEDES relation из epoch ordering — DERIVED (не AUTHOR_CANON)."""
    rel = TemporalRelation.precedes("satya_yuga", "treta_yuga")
    assert rel.is_canon is False
    assert rel.provenance[0].category == ProvenanceCategory.DERIVED
```

**4.2.4 Другие фабрики — корректны**

| Метод | Категория | Статус |
|-------|-----------|--------|
| `develops_from()` | HYPOTHESIS | ✅ |
| `transforms_into()` | HYPOTHESIS | ✅ |
| `precedes()` | DERIVED | ✅ (C2 fixed) |
| `contemporary_with()` | HYPOTHESIS | ✅ |
| `carries()` | AUTHOR_CANON | ✅ (author interpretation) |
| `transmits_to()` | AUTHOR_CANON | ✅ (author interpretation) |
| `echoes()` | HYPOTHESIS | ✅ |

**4.2.5 Uстаarевшая документация в CURRENT_DEVELOPMENT_STATE.md**

- Строка 218: `✅ кроме C2 (рёбра до сих пор не несут фабричный AUTHOR_CANON — finding, не исправлен)` — **НЕВЕРНО**.
- Строка 382: `D-16 | C2-finding: фабрика рёбер ставит AUTHOR_CANON` — **УСТАРЕЛО**.
- Строка 470: `C2-фабрику (✅ уже исправлена)` — **ВЕРНО**, но противоречит строке 218.

### 4.3 Вывод

**C2 УЖЕ ЗАКРЫТ в коммите `f1d5d60`.** Код и тесты корректны. Требуется только обновление `CURRENT_DEVELOPMENT_STATE.md` для устранения противоречивых утверждений.

**Статус: ✅ CLOSED (коммит `f1d5d60`)**
**Открыто: устаревшая документация (D-16 finding — не баг, а stale doc)**

---

## 5. Сравнительная оценка

| Критерий | MD-7 / M4.5 | F-12 | C2 |
|----------|-------------|------|-----|
| **Подтверждённая проблема** | Mёртвые алиасы + stale comments (+ option: GenerationParams.quality) | Schema drift: БД без quality, код с quality | **Нет проблемы** (C2 уже исправлен) |
| **Текущее состояние** | Код работает, тесты зелёные, 4 косметических файла | API `/film/shots/{id}` PUT с quality → SQL error на production БД | Работает корректно, тесты PASS |
| **Зависимости** | Нет (только cleanup) | Зависит от решения владельца (ALTER vs recreate) | Нет |
| **Риск регрессии** | Низкий (удаление мёртвого кода) | Средний (ALTER vs DROP risk) | Нет (закрыт) |
| **Объём изменений** | 4 файла, ~20 строк | 1 файл (БД), 0 строк кода | 0 (только docs) |
| **Требуемые решения owner** | 1: удалить `GenerationParams.quality` или оставить? | 1: ALTER TABLE ADD COLUMN или recreate DB? | Не требуется |
| **Критерии приёмки** | lint clean, tests pass, no comfyui references | DB has quality column, PUT works | N/A |
| **Статус** | READY FOR SPEC | READY FOR SPEC | ✅ CLOSED |

**Выводы, подтверждённые кодом:**
- C2 закрыт: проверка `relation.py:201` + `test_temporal_model.py:593-597`
- MD-7 частично закрыт: routes removed (test MediaBoundary), stub exists
- F-12 проблема подтверждена: SQLite query показывает отсутствие column

**Выводы, остающиеся гипотезами:**
- Генерация `GenerationParams.quality` не используется в runtime — гипотеза, требуется deeper audit pipeline.py для подтверждения мёртвости.

---

## 6. Архитектурные решения

### 6.1 MD-7: `GenerationParams.quality` — удалить или маркировать deprecated?

**Вопрос:** Поле `quality` в `GenerationParams` (visual_assets/schemas.py:50) не читается runtime-маршрутами. MediaPlan BANNED_FIELDS уже исключает `quality`. Оставить как legacy или удалить?

**Варианты:**
- **A: Удалить** — cleaner schema, меньше мёртвого кода. Требует обновления pipeline.py (убрать default).
- **B: Deprecation marker** — оставить с `Field(deprecated=True)`, убрать из BANNED_FIELDS (так как больше не banned, а просто unused).
- **C: Leave as-is** — минимальный риск, но технический долг растёт.

**Последствия:**
- A:breaking change если кто-то снаружи использует GenerationParams.quality.
- B: forward-compatible, lint warning.
- C: technical debt accumulates.

**Owner decision required: A / B / C?**

### 6.2 F-12: ALTER vs recreate DB

**Вопрос:** `data/film_studio.db` lacks `quality` column. How to migrate?

**Варианты:**
- **A: ALTER TABLE ADD COLUMN** — добавляет column с DEFAULT 'standard'. 3 shot rows get default. Zero data loss.
- **B: Drop and recreate** — loses all 120 projects, 110 scenes, 3 shots. Requires re-seeding.
- **C: Skip migration, patch route to ignore quality** — hacky, breaks PUT /film/shots/{id}?quality=ultra silently.

**Последствия:**
- A: safe, standard SQL migration.
- B: destructive, requires manual re-seeding from film_output/*.
- C: breaks API contract, silent data loss.

**Owner decision required: A / B / C?** (Recommendation: **A**)

### 6.3 C2: Обновить CURRENT_DEVELOPMENT_STATE.md

**Вопрос:** Документ содержит противоречивые утверждения о C2 (строка 218: «не исправлен», строка 470: «✅ уже исправлена»).

**Решение:** Обновить строки 218, 382 на актуальный статус «C2 CLOSED (f1d5d60)».

**Owner decision required:** Согласование обновления docs (автоматическое, если нет возражений).

---

## 7. Предлагаемые минимальные scopes

### MD-7 — minimal cleanup scope

```
Files to touch:
  core/CORE/providers/image/__init__.py   (-2 lines: aliases)
  runtime/core/media_client.py            (~4 lines: comments)
  core/CORE/visual_assets/schemas.py      (decision on quality)
  core/CORE/media_plan/schemas.py         (if quality removed from BANNED)

Tests: existing 134 + 0 (no new tests needed)
Backend changes: 0 functional, only cleanup
```

### F-12 — migration scope

```
Files to touch:
  data/film_studio.db                     (ALTER TABLE)

Optional (nice-to-have):
  runtime/tests/test_md3_route_e.py       (+1 integration test with real DB)

Tests: existing +1 optional
Backend changes: 0
```

### C2 — docs-only scope

```
Files to touch:
  docs/CURRENT_DEVELOPMENT_STATE.md       (2 strings updated)

Tests: none
Backend changes: 0
```

---

## 8. Сравнительная таблица приоритетов

| Направление | Проблема | Объём | Риск | Owner decision | DoD |
|-------------|----------|-------|------|----------------|-----|
| **MD-7** | Мёртвые алиасы, stale comments | ~20 строк | Низкий | GenerationParams.quality → удалить/deprecated/leave | lint clean, no comfyui refs |
| **F-12** | Schema drift (DB без quality) | ALTER TABLE | Средний | ALTER vs recreate vs skip | DB has quality column, PUT works |
| **C2** | Устаревшая документация | 2 строки | Нет | Approve docs update | CURRENT_DEVELOPMENT_STATE.md consistent |

---

## 9. Заключения по каждому направлению

### MD-7 / M4.5

**Статус: READY FOR SPEC**

Проблема подтверждена: 4 файла с мёртвым/устаревшим кодом. Функционально не блокирует (аллиасы never match, comments don't execute). Требуется owner-GO на выбор стратегии по `GenerationParams.quality`.

**Открытый вопрос:** Что делать с `GenerationParams.quality`? (удалить / deprecated / leave)

### F-12

**Статус: READY FOR SPEC**

Проблема подтверждена: production БД lacks `quality` column, код ожидает. API `PUT /film/shots/{id}?quality=ultra` будет fail с `sqlite3.OperationalError: no such column: quality` при вызове на production. Текущие тесты это не ловят (FakeFilmStore).

**Открытый вопрос:** ALTER TABLE ADD COLUMN (recommendation) vs recreate DB vs skip?

### C2

**Статус: ✅ CLOSED**

Исправлен в коммите `f1d5d60` (2026-09-16). Код: `relation.py:201` → `ProvenanceCategory.DERIVED`. Тест: `test_precedes_is_derived_from_epoch_order`. Единственный gap — устаревшая документация в CURRENT_DEVELOPMENT_STATE.md.

**Рекомендация:** Обновить docs (строки 218, 382) как часть любого следующего этапа. Отдельный GO не требуется.

---

## 10. Документация — изменения

| Файл | Изменение | Причина |
|------|-----------|---------|
| `docs/CURRENT_DEVELOPMENT_STATE.md:218` | «C2 кроме… не исправлен» → «C2 ✅ CLOSED (f1d5d60)» | Stale finding |
| `docs/CURRENT_DEVELOPMENT_STATE.md:382` | D-16 «C2-finding» → «C2 ✅ CLOSED» | Stale debt |
| `docs/PRODUCT_MAP.md:124` | «70% product» → «~95% product» (F5+F6 done) | Outdated metric |

**Каждое изменение документировано в此 отчёте.**

---

## 11. Подтверждения ограничений

| Ограничение | Статус | Доказательство |
|-------------|--------|---------------|
| Application code changes = 0 | ✅ | `git diff HEAD --stat` — только docs/ не от этого агента |
| Backend changes = 0 | ✅ | Никаких изменений в runtime/ |
| DB/data changes = 0 | ✅ | `data/film_studio.db` не тронут |
| Commits = 0 | ✅ | HEAD остаётся `b4e6893` |
| New ADRs created = 0 | ✅ | No new ADR files |
| Legacy removed = 0 | ✅ | Ничего не удалялось |
| F6 expanded = 0 | ✅ | F6 завершён в предыдущем коммите |

---

## 12. Следующие шаги (без owner-GO не начинаю)

1. **F-12 migration** — ALTER TABLE ADD COLUMN quality → verification → commit.
2. **MD-7 cleanup** — dead alias removal + comment update + GenerationParams.quality decision.
3. **Docs update** — CURRENT_DEVELOPMENT_STATE.md stale C2 references.

**STOP. Аудит завершён. Жду owner-GO на выбор направления.**
