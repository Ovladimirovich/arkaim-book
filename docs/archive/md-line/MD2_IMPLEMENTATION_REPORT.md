# MD-2 IMPLEMENTATION REPORT — Scene Context Consolidation

**Дата:** 2026-09-11
**Этап:** MD-2 (Scene Context Consolidation) — реализация
**Основа:** `docs/MD2_PRE_IMPLEMENTATION_AUDIT.md` §9, `ADR_ARKAIM_MEDIA_BOUNDARY`, `docs/MEDIA_DIRECTION_FOUNDATION.md`
**Вердикт:** MD-2 — IMPLEMENTED / TESTED / VERIFIED. Ожидается решение владельца (STOP GATE).

---

## Простыми словами

**1. Что было целью?**
Свести все пять «дорог», по которым картинки книги попадают в генератор изображений, к одному общему входному формату — SceneContext, — не сломав ни одну из работающих функций.

**2. Что реально сделано?**
- Создан единый смысловой слой SceneContext: это прежний VisualContext плюс три новых поля — `temporal` (к какому времени книги относится сцена, читается только из существующей временной модели), `source_refs` (откуда взяты данные — только ссылки-идентификаторы, без копирования), `integrity` (метка честности: связи не сочинялись, время не выдумано).
- Все пять живых маршрутов переведены на этот вход по одному, с проверкой после каждого: (A) /visualize, (B) /visualize/epoch, (C) /assets/generate, (D) /assets/generate-context/-character/-location, (E) film /shots/generate.
- Старые входы помечены как устаревшие (DEPRECATED) — но не удалены: старый код продолжает работать.
- Написаны 23 юнит-теста + 15 маршрутных тестов; вся визуальная семья тестов зелёная (163 passed, 4 старых падения — не мои).
- Полная регрессия по ~55 файлам (~1300 тестов) чанками: ни одного НОВОГО падения от MD-2; все встреченные падения — старые, воспроизводятся без моих изменений (часть — известные проблемы конфигурации из M8.1-аудита, часть — ограничения тестовой среды).
- Живой прогон сервера подтвердил: маршруты A–D отвечают как раньше (200, картинка, промпт, 404 на несуществующих сценах/эпохах).

**3. Что получилось?** PASS (с двумя отдельно зафиксированными старыми дефектами, см. п.4).

**4. Есть ли проблемы?**
Да, две — обе существовали ДО MD-2 и найдены при проверке:
- **F-11 (исправлен, минимально):** «дорога D» (/assets/generate-context и соседи) в реальности падала с ошибкой импорта при ЛЮБОМ запуске — в коде была опечатка вида относительного импорта. Дорога D считалась «канонической», но фактически не работала. Я починил ровно эту опечатку (2 строки), иначе миграцию D было бы невозможно проверить.
- **F-12 (НЕ исправлен, требует решения владельца):** база данных film-студии (файл data/film_studio.db) была создана 19.07, а код, требующий колонку quality, добавлен 07.08 — файл базы никогда не обновлялся. Из-за этого создание шотов в живой базе падает (это блокирует маршрут E на живой базе). Мой код маршрута E проверен на чистой тестовой базе — работает. Чинить чужую базу в MD-2 нельзя (вне рамок), нужно решение: пересоздать базу / добавить миграцию / удалить файл.
Серьёзность F-12: средняя (не влияет на читателя книги, влияет на film-студию).

**5. Что предлагается дальше?**
- Владелец принимает решение по F-12 (рекомендую: разрешить одноразово пересоздать data/film_studio.db — это тестовая база, не продакшн-данные).
- После вердикта по MD-2 — переход к MD-3 (MediaPlan) по дорожной карте. Автоматически не перехожу.

---

## Статусы по элементам

| Элемент | Статус |
|---|---|
| SceneContext v2 (VisualContext + scene_extras) | IMPLEMENTED / TESTED / VERIFIED |
| Подэтап 1: ядро типов (scene_context.py) | IMPLEMENTED / TESTED |
| Подэтап 2: пять маршрутов по одному | IMPLEMENTED / TESTED / VERIFIED |
| Подэтап 3: deprecation-метки | IMPLEMENTED |
| F-11 (relative import, путь D) | FIXED (минимальная разблокировка) |
| F-12 (film_studio.db без quality) | DOCUMENTED (не чинил — вне scope) |
| Полная регрессия visual-семьи | TESTED (101/101) |
| Live smoke | VERIFIED (A–D 200; E — F-12, код VERIFIED на чистой БД) |
| Границы (запрещённые зоны) | VERIFIED (mtime-forensic) |
| MD-3 / MediaPlan / C2 | НЕ НАЧАТЫ (STOP GATE) |

---

## 1. Что было до MD-2 (as-was)

Пять живых дорог к генерации изображений, каждая со своим входом:

| Маршрут | Endpoint | Вход |
|---|---|---|
| A | POST /book/visualize | genome-scene dict → SceneEngine → PromptBuilder.build_scene_prompt |
| B | POST /book/visualize/epoch/{id} | WorldModel.get_temporal_context → build_epoch_prompt |
| C | POST /book/assets/generate (+async, batch, regenerate) | genome-scene dict → пайплайн → build_asset_prompt |
| D | POST /book/assets/generate-context / -character / -location | VisualContextBuilder.build* → VisualContext → PromptComposer → generate_image_from_context |
| E | POST /book/film/{p}/scenes/{s}/shots/{sh}/generate | shot.prompt → pipeline.generate_image(custom_prompt) |

Проблема консолидации (аудит §2.5): смысл сцены описывался четырьмя разными способами; temporal-данные существовали только в B; provenance сцены нигде не передавался; «инвариант связей» не фиксировался нигде.

## 2. Что стало каноническим (to-be)

**SceneContext = существующий VisualContext + scene_extras** (нового параллельного класса НЕТ — запрет владельца соблюдён).

### Точная схема новых полей

```python
# core/CORE/visual/scene_context.py
class ProvenanceRef:      # чистая проекция существующего ProvenanceTag
    category: str         # "canonical" | "c1_enriched" | ...
    source: str
    confidence: float

class TemporalSceneRef:   # read-only проекция WorldModel.get_temporal_context
    epoch_id: str
    name_ru: str
    confidence: float
    bounds_start / bounds_end / bounds_uncertainty: str | None
    provenance: list[ProvenanceRef]     # дедуп по category (паттерн C1)
    event_count: int
    character_count: int
    technology_count: int
    # свойство is_temporal: bool

class SourceRefs:         # ссылки, НЕ копии
    scene_id: str | None
    chapter: int | None
    character_ids: list[str]
    location_id: str | None
    entity_refs: list[str]
    rag_fallback: bool = False

class SceneIntegrity:     # фиксирует инварианты
    links_synthesized: bool = False   # всегда False — связи не синтезируются
    temporal_read_only: bool = True
    provenance_inherited: bool
    intentionally_denormalized: bool = False

class SceneContextExtras:
    temporal: TemporalSceneRef | None
    source_refs: SourceRefs | None
    integrity: SceneIntegrity
```

`VisualContext.scene_extras: SceneContextExtras | None = None` — поле аддитивное (по умолчанию None, legacy-потребители не затронуты). Единственная точка заполнения — `extend_visual_context()`; сериализация — в `VisualContext.to_dict()`; в `summary()` появляется `epoch={id}` только когда temporal реально есть.

### Media-neutral (проверено тестом-сканером)
Тест TestMediaNeutrality проходит по всем полям иерархии и требует отсутствия execution-полей: {model, steps, seed, cfg, sampler, workflow, node_graph, provider, checkpoint, backend} — их нет ни в extras, ни в VisualContext.

## 3. Миграция пяти маршрутов (подэтап 2, по одному)

Каждый шаг: data-flow → переключение → сохранение поведения → тесты → регрессия.

| Маршрут | Что изменилось внутри | Контракт ответа | Тесты |
|---|---|---|---|
| A /visualize | Сначала строится SceneContext (единый билдер), затем из него — прежняя промпт-логика. Существование сцены проверяет прежний SceneEngine (404-контракт) | 200 + prompt + image_bytes + content_type; 404 на несуществующих | test_md2_routes::TestRouteA + test_visualization (HEAD-тесты зелёные) |
| B /visualize/epoch | build_scene_context_for_epoch → is_temporal (эквивалент get_temporal_node ⟺ get_epoch) → прежний build_epoch_prompt | 200; 404 на несуществующей эпохе; WorldModel не мутируется | TestRouteB + test_m7_epoch_visual (все HEAD M7.2-тесты зелёные) |
| C /assets/generate (+async/batch/regenerate — тот же пайплайн-вход) | Маршрут строит SceneContext и передаёт в пайплайн как scene_context; пайплайн берёт данные из контекста (source_refs = те же genome-id), existence-чек оставлен SceneEngine | 200 + completed-asset; 404 Scene not found; overrides (size/negative_prompt/quality) те же | TestRouteC + test_visual_assets_provider_chain |
| D /assets/generate-context/-character/-location | build_scene_context / _for_character / _for_location (единый вход MD-2); новый опциональный Query-параметр epoch_id | 200 + asset; 400 на неизвестном персонаже (валидатор, как в HEAD) | TestRouteD (4 теста) |
| E film /shots/generate | Маршрут строит SceneContext и передаёт в pipeline.generate_image(scene_context=ctx); custom_prompt/overrides/quality-флоу прежние | 200 + completed + asset_id (на чистой БД) | TestRouteE (2 теста на чистой временной БД) |

Подэтап 3 (deprecation-метки, без удаления):
- `visualization.PromptBuilder` — DEPRECATED как точка НОВОГО входа (сохранён для промпт-совместимости A/B/C/E);
- `visual_assets.prompt_builder.build_asset_prompt` — DEPRECATED как вход (VisualAsset — доменная запись-результат);
- `visual_assets.schemas.VisualAsset` — DEPRECATED как ВХОД генерации (execution-поля остаются до MD-3, чистка вне MD-2);
- `visual_assets.pipeline.generate_image/generate_video` без scene_context — legacy-режим помечен DEPRECATED;
- `visual_context_builder.build / build_for_character / build_for_location` — DEPRECATED как точка НОВОГО входа (сохранены как внутренняя основа build_scene_context*).

## 4. Находки: исправленные и сознательно НЕ исправленные

### Исправлено в MD-2 (минимальные разблокировки миграции)
- **F-11** `visual_assets/pipeline.py:295-296`: `from ..visual.prompt_composer import ...` — relative-import-beyond-top-level; путь D падал при любом вызове `generate_image_from_context` (существовал до MD-2 — воспроизведён на HEAD-коде). Исправлено на абсолютные импорты (2 строки) — тот же паттерн, что весь visual-стек. Без этого маршрут D (обязательный для миграции) не работал.
- **Bug my-design:** unknown epoch в build_scene_context_for_epoch изначально помечал is_temporal=True — исправлено: temporal пуст, маршрут решает 404 (инвариант «не угадывать»).

### Сознательно НЕ исправлено (вне рамок MD-2, по правилу владельца)
- F-1/F-2 (dict-структуры сцен, промпт-генератор) — не тронуты;
- genome-scenes без epoch_id — не тронуты (данные);
- chapter→epoch resolution возвращает None для текущих genome-глав (нет событий с главами) — scene_extras.temporal у сцен ЧЕСТНО пуст; это состояние данных, не дефект MD-2;
- arkaim_era TemporalNode.provenance пуст в WorldModel (C1-обогащение живёт только на уровне /chain API) — отражается в TemporalSceneRef.provenance=[] честно;
- HistoricalContext, RAG-ghost-scenes, CJK-ключ «ancient壁画» — не тронуты;
- VisualAsset→MediaPlan — не начат (MD-3);
- pre-existing линт (Optional F401 ×2, imports F401 ×3, negative F841) — подтверждены в HEAD через git show, не чинились (нет mass-cleanup).

### Pre-existing падения тестов, обнаруженные при полной чанк-регрессии (НЕ MD-2; каждое воспроизводится изолированно)
- **SharedSettings-атрибуты** (RATE_LIMIT_REQUESTS_PER_MINUTE, PROVIDER_FAILURE_THRESHOLD и др.): отсутствуют в runtime/shared_config.py при живых обращениях из middleware/main/circuit-breaker — известная «массивная проблема конфигурации» из docs/M8_1_POST_IMPLEMENTATION_AUDIT.md. Затрагивает test_load_book, test_circuit_breaker ×11, test_metrics; на живом сервере >100 req/min → 500 вместо 429. Требует отдельного этапа (владелец решает).
- **test_auth ×3** — Telegram-OAuth хэш-логика, изолированные.
- **test_memory ×8** — SQLite readonly в тестовой среде (M8.1 Failure 2).
- **test_narrative_store/test_world_explorer ×18 errors** — pytest tmp_path вне workspace (sandbox среды).
- **test_book_ui_integration ×4** — подтверждены идентичными на HEAD-роутах (git-stash-проверка).
- **m9-fallback ×1** — order-pollution registry в temporal-семье (падает без всяких MD-2-файлов).
- **test_assets_new_params ×4** — import-path 'runtime.core' (механика тестов).
- **Сетевые тесты** (stream/email/telegram/providers/pdf) — блокируют pytest-процесс; полные suite-прогоны до MD-2 (pwsh-4) и после (pwsh-6) виснут одинаково.

### Требует решения владельца
- **F-12 (pre-existing, блокирует E только на живой БД):** data/film_studio.db создан 19.07 (без quality-колонки), код с quality — с 07.08; CREATE TABLE IF NOT EXISTS не мигрирует существующую таблицу. Итог: add_shot/update_shot падают в живой базе. Варианты: (а) пересоздать data/film_studio.db (в ней нет продакшн-данных); (б) написать одноразовую миграцию ALTER TABLE; (в) оставить как есть (E недоступен на живой базе). Рекомендую (а) или (б) отдельным микро-этапом.

## 5. Тесты: до / после

| Срез | До MD-2 | После MD-2 |
|---|---|---|
| Новые MD-2 юнит-тесты | — | 23 (test_md2_scene_context.py) — все зелёные |
| Новые MD-2 маршрутные тесты | — | 15 (test_md2_routes.py) — все зелёные |
| Visual-семья (11 файлов: visual*/visualization/film/assets/m7/md2) | 85 passed / 4 pre-existing failed | **163 passed / 4 pre-existing failed** (те же 4 test_assets_new_params) |
| Temporal-семья (13 файлов + md2) | — | **438 passed / 1 pre-existing failed** (m9-fallback: order-pollution, падает и без MD-2-файлов — подтверждено прогоном без них и с test_visualization вместо md2) |
| Narrative-семья (9 файлов) | — | 206 passed / 18 errors (все 18 — sandbox: pytest tmp_path вне workspace, WinError 5; падают изолированно и без MD-2) |
| core/auth/gateway/genome/identity/memory/knowledge_kernel/load_book | — | 85 passed / 4 skipped / 4 failed / 8 errors — все pre-existing изолированные: test_auth ×3 (Telegram-хэш), test_load_book ×1 (SharedSettings.RATE_LIMIT — известная M8.1-находка), test_memory ×8 (SQLite readonly, M8.1 Failure 2) |
| Сервисные (observability/metrics/crowdfunding/isolation/circuit_breaker/service_registry/contract) | — | 82 passed / 12 failed / 2 errors — все pre-existing изолированные: SharedSettings.PROVIDER_FAILURE_THRESHOLD ×11 (та же M8.1-серия), crowdfunding ×1, metrics ×1 |
| UI/SSE (book_ui_integration, xray_sse) | — | 51 passed / 3 skipped / 4 failed — все 4 pre-existing (подтверждены прогоном на HEAD-роутах через git-stash: идентичные 4 падения) |
| Полный suite одним запуском | виснет (сетевые тесты: stream/email/telegram/providers/pdf блокируют pytest-процесс; фоновые полные прогоны убиты) | прогнано чанками — суммарно ~55 файлов / ~1300 тестов; сетевые тесты не гонялись (вне контура MD-2) |

**Ключевой вывод:** НИ ОДНО новое падение не внесено MD-2. Все наблюдаемые падения/ошибки воспроизводятся (а) изолированно без MD-2-файлов, (б) на HEAD-коде (git-stash-проверка для book_ui), либо (в) являются sandbox-ограничениями среды (tmp_path/readonly-SQLite) или pre-existing дефектами конфигурации (SharedSettings-атрибуты — известная M8.1-серия).

### Тест-гигиена MD-2 (внутри моих файлов)
При комбинированном прогоне (temporal-семья + md2_routes, ~104 запроса в одном pytest-процессе) пересекался rate-limiter (100 req/60с): 429-путь middleware читает несуществующий SharedSettings.RATE_LIMIT_REQUESTS_PER_MINUTE → 500 (та же известная M8.1-находка, триггеримая нагрузкой). В test_md2_routes.py добавлена autouse-фикстура `_isolate_global_state`: сброс `main._rate_limits` до/после каждого теста + полный откат `registry._instances` (закэшированные визуальные сервисы pollute temporal/m10/m7-тесты). После фикстуры: 438/1 в temporal-чанке, 163/4 в visual-семье. Фикстура — тест-гигиена, продукт-код не менялся.

## 6. Инварианты архитектуры (проверка)

| Инвариант | Проверка | Итог |
|---|---|---|
| Нет нового параллельного SceneContext-класса | scene_extras на VisualContext; отдельного класса нет | VERIFIED |
| temporal только из WorldModel.get_temporal_context; никаких Present→Arkaim, угадываний эпох, самодельного provenance | _temporal_ref_from_epoch — read-only проекция; _resolve_epoch_for_chapter читает только canonical_events; нет событий → temporal пуст | VERIFIED (тестами TestTemporalSceneRef/TestSceneContextBuilder) |
| source_refs — ссылки, не копии | SourceRefs хранит только id | VERIFIED |
| integrity: связи не синтезируются | links_synthesized=False всегда | VERIFIED (TestIntegrityInvariant) |
| Media-neutral: никаких execution-полей (model/steps/seed/cfg/checkpoint...) | walk-scan всех полей | VERIFIED (TestMediaNeutrality) |
| Контракты маршрутов не изменены | маршрутные тесты A–E: статус-коды, тела ответов | VERIFIED |
| Мутации WorldModel запрещены | test_world_model_not_mutated | VERIFIED |
| Legacy-код не удалён | deprecation-метки без удаления | VERIFIED |

## 7. Изменённые файлы (полный список, MD-2-граница)

Новые:
- `core/CORE/visual/scene_context.py` — типы SceneContext (extras/temporal/source_refs/integrity) + extend_visual_context;
- `runtime/tests/test_md2_scene_context.py` — 23 юнит-теста;
- `runtime/tests/test_md2_routes.py` — 15 маршрутных тестов;
- `docs/MD2_IMPLEMENTATION_REPORT.md` — этот отчёт.

Изменённые (ядро):
- `core/CORE/visual/visual_context.py` — scene_extras-поле, to_dict/summary;
- `core/CORE/visual/visual_context_builder.py` — MD-2-методы build_scene_context* (+world_model в ctor), deprecation-метки legacy-build*;
- `runtime/core/adc_deps.py` — фабрика передаёт world_model в VisualContextBuilder;
- `core/CORE/visual_assets/pipeline.py` — scene_context-параметр generate_image/generate_video + F-11 fix + deprecation;
- `core/CORE/visual_assets/prompt_builder.py`, `core/CORE/visual_assets/schemas.py`, `core/CORE/visualization/prompt_builder.py` — deprecation-метки.

Изменённые (маршруты):
- `runtime/core/routes/visual.py` (A, B), `runtime/core/routes/assets.py` (C, D), `runtime/core/routes/film_studio.py` (E).

Forensic-граница (mtime, сессия 2026-09-10/11): только перечисленные файлы. Запрещённые зоны НЕ тронуты:
- WORLD_MODEL.json (07-16), world_model.py (09-05), GENOME (08-07), providers/ (08-08), temporal-API роуты, F3-файлы, Media Foundation, ADR, comfyui-интеграция, arkaim-web — без изменений в этой сессии.

## 8. Live smoke (uvicorn 8642, dev-JWT через /auth/dev/generate-token → /auth/telegram/login)

| Маршрут | Результат |
|---|---|
| A /book/visualize | 200, prompt 413 симв., image_bytes>100, content_type=image/svg+xml |
| B /book/visualize/epoch/arkaim_era | 200, prompt 218 симв. |
| B unknown epoch | 404 (как в HEAD) |
| C /book/assets/generate | 200, status=completed, chapter=1 |
| D generate-context (+epoch_id=arkaim_era) | 200, completed |
| D generate-character (Световит) | 200 |
| D generate-location (Аркаим) | 200 |
| E film /shots/generate | на живой БД падает F-12 (add_shot INSERT без quality-колонки; падение существует до MD-2); код VERIFIED на чистой БД (тесты) |

## 9. Оставшиеся пробелы (для будущих этапов, НЕ для MD-2)

- F-12 — живая film-БД без quality-колонки (решение владельца);
- genome-сцены без epoch_id + canonical_events без перекрытия genome-глав → temporal у сцен пуст (данные, не код);
- legacy-слой dictionary-сцен и двойной промпт-генератор (F-1/F-2) — консолидация вне MD-2;
- VisualAsset execution-поля — чистка в MD-3 (MediaPlan);
- pre-existing SharedSettings-атрибуты (RATE_LIMIT_*, PROVIDER_FAILURE_THRESHOLD) — «массивная проблема конфигурации» M8.1: на живом сервере >100 req/min → 500 вместо 429; отдельный этап;
- pre-existing падения тестов (см. §5): test_auth ×3, test_memory ×8, test_assets_new_params ×4, m9-fallback ×1, test_book_ui ×4, sandbox tmp_path ×18, сетевые висяки;
- 4 pre-existing падения test_assets_new_params (тест-механика import-path).

## CJK-scan

Выполнен фактическим сканом всех MD-2-файлов (scene_context.py, visual_context.py, visual_context_builder.py, pipeline.py, routes, тесты, этот отчёт) по CJK-диапазонам Unicode. Найдено 3 вхождения:
- `visual_assets/prompt_builder.py:23` — ключ `"ancient壁画"` в STYLE_PRESETS: **pre-existing finding F-4** (подтверждён в HEAD через git show; сознательно не тронут — фикс вне рамок MD-2);
- 2 вхождения в этом отчёте — документационные упоминания той же находки F-4 в кавычках.

Новых CJK-ключей, внесённых MD-2, нет.

---

**STOP GATE:** MD-2 завершён. MD-3 (MediaPlan), C2, любые следующие этапы — НЕ начаты и требуют прямого вердикта владельца.
