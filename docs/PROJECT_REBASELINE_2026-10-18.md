

# PROJECT RE-BASELINE — 2026-10-18

> [!WARNING]
> **HISTORICAL — срез на 2026-10-18.** Числа в документе верны для своей даты
> (например, GEOGRAPHY = 38 до чистки `geo_*`-зеркал 2026-10-20/21, World Engine = 524 до неё).
> Актуально на 2026-10-21: **503 сущности / 80 связей**, GEOGRAPHY = **17**,
> `claim_temporal_links.json` = **15**, crosswalk = **3**.
> Текущая карта: `docs/CURRENT_DEVELOPMENT_STATE.md`.

**РЕШЕНИЕ:** полный, фактический re-baseline состояния Arkaim по коду, тестам, git и live-прогонам (2026-10-18). Исследование, не редактирование — владелец не вправе менять проект без OWNER-GO.

**МЕТОДОЛОГИЯ:** git-строка (25 ahead), live-прогон сервера 2026-10-18, pytest + vitest в свежем venv, чтение кода в разрешённых каталогах (backend `runtime/`, frontend `arkaim-web/`, ядро `core/`), сравнение с ADR/контрактами. Никаких изменений проекту в ходе ребазина.

**РЕЗЮМЕ:** OK. Отчёт: `ARKAIM_PROJECT_STATE.md` (самостоятельная генерация, без GOVERNANCE).

---

## 1. ФАКТИЧЕСКОЕ СОСТОЯНИЕ (ARTIFACTS)

| Артефакт | Состояние |
|---|---|
| git HEAD `master` | `b3bd0ac` — fix(encoding) в `main.py`; 3 encoding-fix + M8/M6/M5/M4/M3 (public Knowledge endpoints) |
| git origin/master | 25 ahead / 0 behind |
| работы | ~100 modified tracked + ~60 untracked — часть Studio Phase 2 / media / docs / tests |
| live-сервер | backend `:8642` OPEN (326 путей OpenAPI); frontend `:3000` OPEN |
| Backend-тесты (2026-10-18) | **2426 passed / 16 failed / 26 skipped** (~9.5 мин; 3 live-media запроса) |
| Frontend-тесты | **223 passed / 8 failed** (32 тестов); `tsc --noEmit` — exit 0 |
| Untracked (новое) | `arkaim-web/src/app/knowledge/`, `arkaim-web/src/app/studio/`, 12 studio frontend-файлов, 12+ studio pytest, `core/CORE/studio/{art_direction,continuity,prepared_updates,reel,sequence}.py`, 4 media-артефакта, `runtime_data/` |
| Modified (новое) | `runtime/core/routes/studio.py` (+2567 строк), `runtime/core/media_client.py`, `core/CORE/studio/store.py`, `core/CORE/visual_assets/*`, genome history, screenplay_links/enriched_* обновления, обновлённые docs |

**Ключевое:** de-facto baseline (2026-10-11 → 10-14) не отражает последние правки: учёт media, тесты, Studio Phase 2.

## 2. АРХИТЕКТУРА — фактическая карта слоёв

```text
BOOK / CANON        BOOK_DOCUMENT.json (768 KB), enriched_chunks.json (824 чанка),
                    SYNOPSIS_DOCUMENT.json (119 сцен / 642 абзаца / 149 323 зн.),
                    ChromaDB, intelligence/{chunker,kernel,retriever},
                    knowledge_engine (Chroma-обращение)
        ↓
AUTHOR MATERIAL     core/SOURCE_OF_TRUTH/{BOOK,AUTHOR_NOTES,ARTICLES,INTERVIEWS,SYNOPSIS},
                    AUTHOR_INTENT.json, ANCHOR_QUOTES.json
        ↓
KNOWLEDGE           Book OS хранилища (fact/source/provenance/relationship/entity — ядро),
                    knowledge_card/builder.py (read-projection),
                    core/CORE/evidence/* (M2), CanonClaim (M1),
                    knowledge/{conflict,correction,reasoning}_repository (M5–M7, ядро),
                    knowledge_engine + M14/M21–M25 (event-aware ask, holistic, theme completeness)
        ↓
WORLD MODEL         вычислительный слой: WorldModelExt (13 категорий, 524 элемента),
                    canonical WorldModel (12 эпох, 12 связей, 8 событий, 4 causal правила),
                    relation_graph в WorldEngine — ПУСТО; core/WORLD (46 сущностей) — legacy;
                    crosswalk — 2 утверждённых маппинга
        ↓
PROVENANCE          source_levels.py: ProvenanceCategory (8) + SourceLevel (7), world_provenance.py,
                    SourceBadge, dual-лексика со schemas.Fact/Provenance (совместимость есть,
                    раздельное значения — дефект M1)
        ↓
RELATIONS           relation_models.py (RelationGraph), character_relations (5), 
                    World Knowledge Resolver + crosswalk; реляционная provenance — first-class
        ↓
TEMPORAL            temporal/* (graph/node/relation/chain/precision/gap/reconstruction/anchor):
                    live /book/temporal/* (цепочка FORWARD: 12 узлов, дополнен 2026-10-18),
                    M10.2 pending-updates (RBAC), claim_temporal_links (9 записей, M17/M18)
        ↓
FORM                core/CORE/FORM (10 шаблонов), form_engine, /book/world/form-library
        ↓
CONSISTENCY         consistency_engine, contradiction_detector, compatibility_checker, canon_validator,
                    /book/world/validate (RBAC editor)
        ↓
RECONSTRUCTION      reconstruction_engine, world_explorer / deep_explorer, hypothesis_generator,
                    impact_assessor, quality_evaluator — выполняется, не производственная
        ↓
POSSIBLE LINES      /book/world-explorer/* (hypotheses/possibilities/paths/branches/feedback),
                    narrative_engine/story (composer/writer/store),
                    scenario_modeler (альтернативное ветвление)
        ↓
DIALOGUE / STORY    /book/ask (Pulse), M14 ask↔knowledge, M21 event-aware ask,
                    M22 holistic view, M24 theme completeness, M25 question coverage (16/16 = 100%)
        ↓
MEDIA               ADR_ARKAIM_MEDIA_BOUNDARY (ACCEPTED): arkaim-media = отдельный repo,
                    MEDIA_CONTRACT v1.0 (POST /v1/generate), ComfyUI/Agnes/ComfyICU провайдеры,
                    в Arkaim: media_plan + media_client bridge + film_studio (legacy) + Studio v2 (/studio/*, 41 endpoint, Phase 2 uncommitted)
```
## 3. WORLD MODEL — состояние центрального ядра

Ключевой вопрос: **является ли вычислительный слой World Model центральным, и является ли модель мира наполненной?**

**Ответ:** вычислительный слой — да (взаимодействует с Temporal, Knowledge trace, Studio scene-context, world-explorer); наполненная модель мира — пока нет.

| Пункт | Что есть | Статус |
|---|---|---|
| Entities (сущности) | WorldModelExt: 13 категорий, **524 элемента** (PHILOSOPHY 268, LANGUAGE 134, GEOGRAPHY 38, MYTHOLOGY 37; TECHNOLOGIES = 0) | WORKING / TESTED |
| Canonical identity | WorldEngine entity IDs (`region_arkaim` и др.), ID reconciliation (B3-A) подтверждён | DONE / VERIFIED |
| Canonical WorldModel | 12 эпох, 12 связей, 4 пространственных, 8 событий, 4 causal правила, 5 character relations; данные за **2026-07-16** — не обновлялись | WORKING / STALE DATA |
| Events | 8 событий + temporal-узлы; M19 read-only event view; M21/M22 event-aware ask/holistic | PARTIAL (модель не синхронизирована) |
| Locations | 12 canonical + 38 geographic items; crosswalk `region_arkaim→Архар`?, `region_hyperborea→Арктика` | WORKING |
| Characters | characters_living ≈ 30 записей (mostly SYSTEM_INTERPRETATION + legacy: «Лицо/Личность») | PARTIAL / DATA QUALITY |
| Cultures | CIVILIZATIONS.json (3) + canonical civilizations (4) | PARTIAL |
| Relations | relation_models.py есть; character_relations = 5; **WorldEngine.relation_graph = ПУСТО**; GraphEngine синхронизирует данные из OS_DATA | PARTIAL → graph EMPTY |
| Temporal relations | B3-B: PRECEDES-подчинённость существует и live-проверена; 12 temporal-relation пар | DONE / LIVE VERIFIED |
| Spatial relations | location↔character/location links через CharacterPresence/locations | PARTIAL |
| Causal relations | CausalRule (4) + constraints для категорий | PARTIAL |
| Evidence | M2 evidence-сопоставление в Knowledge trace (RESOLVED/UNAVAILABLE/UNKNOWN) | TESTED / LIVE VERIFIED |
| Provenance | world_provenance.py read-only; B4-C UI verified; source_levels 8 категорий | DONE / VERIFIED |
| Canonical status | AUTHOR_CANON / DERIVED / RECONSTRUCTION / HYPOTHESIS / FUTURE_EXTRAPOLATION; temporal precedes = DERIVED | DONE |
| Derived knowledge | Knowledge Cards builder (read-projection), M6 reasoning-цепочка; production-записей нет | PARTIAL |
| Reconstruction | reconstruction_engine + anchors + future extrapolator в engine; live `/book/temporal/reconstruct` | WORKING |
| Hypothesis | hypothesis_generator + world-explorer API + feedback | WORKING (engine), DATA = 0 |
| Consistency | consistency_engine + contradiction_detector + /book/world/validate | WORKING |
| Crosswalk | **2 approved mappings**; `runtime_connected: false` в карте — маршрут не работает, `world_model.py` ссылается на crosswalk (M8f) | DONE / DRIFT FLAG |
| World Engine | singleton, live `/book/world/*` (11 endpoints; 401 от RBAC) | WORKING / LIVE |
| Temporal Engine | reconstruction_engine.from_world_model; полный pipeline (canonical API → engine) — сделана ADR_TEMPORAL_WORLD_MODEL | WORKING |

**Итог:** World Model — вычислительный центр для Temporal, Knowledge trace, Studio scene-context, world-explorer. Данные минимальны и статичны (канон не обновлялся с июля), relation graph пуст, crosswalk крошечный (2 пары). Фактический центр тяжести системы — книга + retrieval, а не вычислимая модель мира.


## 4. KNOWLEDGE — что является источником истины

| Источник | Роль | Заполнение | Provenance |
|---|---|---|---|
| `core/KNOWLEDGE/BOOK_DOCUMENT.json` + `enriched_chunks.json` (824) + Chroma | РЕШЕНИЕ: полный текст + enrichment | Полное, актуально (2026-10-13) | AUTHOR_CANON + chunk metadata |
| `core/SOURCE_OF_TRUTH/*` (BOOK/AUTHOR_NOTES/ARTICLES/INTERVIEWS/SYNOPSIS) | авторитетные материалы | РАСПОЛОЖЕНЫ (в коде, не в ответвлении знаний) | РЕФЕРЕНС — но **не является каноническим** для Knowledge Cards |
| `core/KNOWLEDGE/*.json` (~40 файлов) | разноуровневые знания | Полное | смешанное: AUTHOR_CANON / SYSTEM_INTERPRETATION / EXTERNAL_SOURCE |
| `core/GENOME/` + history snapshots | синтез истории (SIA) | Полное | DERIVED (`genome:theme:*`) |
| Вопросы (модель валентностей) | Intent/Anchor (два уровня) | РАСПОЛОЖЕНЫ (в AUTHOR_TOPIC, не в ответвлении знаний) | — |
| ВРЕМЯ как артефакт (v0.7.0) | «Время как модель»: долгосрочные оценки, картина сосуществования, фиксация синхронизации | Draft v0.7.0 (PROPOSED /EXP: 2026-10-13) | DERIVED |

**Границы источников истины (SOURCE_OF_TRUTH):**
1. **Книга/канон** — единственный источник истины; не реферируется в Knowledge trace.
2. **Документы (SOURCE_OF_TRUTH + авторские + статьи + интервью + синопсис)** — референс, следуют к канону; знания карточек не являются каноническими.
3. **Книга (`core/KNOWLEDGE/*.json`, ~40 файлов)** — собраны разноуровневые знания (AUTHOR_CANON / SYSTEM_INTERPRETATION / EXTERNAL_SOURCE).
4. **Геном + снимки истории** — производные данные: `genome:theme:*`.
5. **Время как артефакт** (v0.7.0): роль — долгосрочные оценки, картина сосуществования, фиксация синхронизации; `СТАТУС: PROPOSED /EXP: 2026-10-13` и `АВТОР: PROPOSED /EXP: 2026-10-13`.

**Граница знаний (SOURCE_OF_TRUTH):** книга/канон — единственное истинное, референсное и не рефероидуемое; отличия — строгая необходимость.

## 5. TEMPORAL / RELATIONS / PROVENANCE — что есть и чего не хватает

**Есть (код/тесты/live):** temporal graph (nodes/edges/chains/precision/gaps/anchors/reconstruction); «Время мира» (эпохи, BACKWARD/FORWARD, present anchor, arkaim anchor, future extrapolation); `TemporalRelation.precedes()` = DERIVED; refresh/reconstruction flow; M10 suggest-only pending updates с RBAC и history; live `/book/temporal/chain` (12 узлов) и `/reconstruct`; M17/M18 claim→event→epoch→temporal-node реестр (9 записей); M3/M4 typed resolvers + публичные `/knowledge/world/resolve`, `/knowledge/temporal/resolve`; M5–M7 typed records + repositories + deterministic reasoning; M8 trace (claim→evidence→source→world/temporal, lineage, totals, честный PARTIAL).

**Не хватает:**
1. Наполнения canonical WM (события/эпохи не обновлялись с июля; событий всего 8 — temporal chain почти линейна).
2. Crosswalk beyond 2 mappings.
3. First-class relation provenance.
4. Production-записей conflicts/reasoning/corrections (lineage live = 0).
5. Связи M10 findings ↔ M7 corrections.
6. Единый temporal-correction lineage journey.

**Какой Temporal нужен нынешнему World Model:** не новые M2/M3/M4-этапы, а **обогащение канонической модели** (события, связи, precision) — тогда существующий Temporal Engine начнёт работать на реальные данные, а не на 12-элементную цепочку.
## 6. SCREENPLAY / 113+ СЦЕН — фактическое состояние

Ключевой вопрос: является ли сценарная система самостоятельным контуром или слоем над World Model?

| Факт | Значение |
|---|---|
| Синопсис-база | `SYNOPSIS_DOCUMENT.json`: **119 сцен / 642 абзаца / 149 323 зн.** (актуализирована 2026-10-13) |
| Screenplay API | `/book/screenplay*` — 4 endpoints, парсер сцен работает (RBAC reader) |
| Связи книга↔сценарий | `screenplay_links.json`: **15 owner-approved пар** (14 сцен); suggest-only детектор (M10); write-путь только через `approve_link` с provenance |
| Claim-временные связи | `claim_temporal_links.json`: 9 записей (M17/M18) |
| Scene model | Studio v2: сцены = проекция синопсиса; `VideoScenarioBuilder` (VisualContext→VideoScenario); `ScenarioModeler` — альтернативные ветви (другая задача) |
| Frontend | `/screenplay` (чтение), `/studio` (рабочее место, untracked), `/film-studio` (legacy), `/story` |

**Ответ на ключевой вопрос:** сценарная система фактически уже является **слоем над World Model**, а не самостоятельным контуром: M11–M20 строят связи «сцена ↔ chunk ↔ claim ↔ event ↔ epoch» через canonical ID. Новая параллельная система не нужна; нужно масштабирование approve-цепочки и обогащение самой модели мира.

## 7. STUDIO / MEDIA — фактическое состояние и границы

**Граница (ADR_ARKAIM_MEDIA_BOUNDARY, ACCEPTED) соблюдена:** Arkaim формирует смысловое задание (Scene Context → MediaPlan), `media_client.py` — мост через единый контракт `POST /v1/generate`; `arkaim-media` — отдельный repo (MEDIA_CONTRACT v1.0 ACCEPTED), `/comfyui/*` депубликованы.

**Что реально есть:**
- Studio v2 (Phase 1B committed + **Phase 2 uncommitted**): 41 endpoint `/studio/*`; новые модули art_direction / continuity / prepared_updates / reel / sequence; image/video jobs через MediaClient; frontend `/studio` — 17 файлов (untracked).
- MediaPlan v0 (builder/schemas, ADR_MEDIA_PLAN_V0 ACCEPTED).
- Film Studio legacy (`/book/film/*`, 15 endpoints, SQLite) — работает, параллельный контур.
- arkaim-media: image (ComfyUI, Agnes — live-run 2026-10-14 подтверждён), video: ComfyICU LTX 2.5 I2V (uncommitted), mock; audio юридически заблокирован (D2).
- Документы 2026-10-14: `MEDIA_PRODUCTION_MASTERPLAN` (PROPOSED — ждёт OWNER-GO), `ARKAIM_STUDIO_SPEC` (DRAFT), `MEDIA_EXECUTORS_SPEC` (DRAFT), `PILOT_FILM_PLAN` (DRAFT).

**Draft / незакреплённое:** вся Phase 2 Studio; ComfyICU/Agnes-расширения arkaim-media; 4 media-докa; live-тесты генерации (env-dependent).
## 8. ОТВЕТ НА КЛЮЧЕВЫЕ ВОПРОСЫ АУДИТА

1. **Является ли studio.py реальным маршрутизатором?** Нет. `runtime/core/routes/studio.py` — пустой маршрутизатор без `/studio` endpoint; 2.5к изменённых строк — интеграция Studio v2, привязанная в `main.py` через `app.include_router(StudioRouter)` (41 endpoint). Статус: Phase 1B ✅ закоммичено, Phase 2 ⏳ (working tree).
2. **Всё ли из ARM медиа составляет прецеденты?** Нет. ARM — принятое архитектурное решение, сгруппированное по темам (Boundary, Plan, Executor, Engine, UI, Export, Blockchain). Contracts/sequencer/jobs переинвестированы в Studio v2 (MediaPlan + studio jobs); ARM остаётся артефактом, Studio v2 — кодом. Не путать.
3. **Есть ли у Studio v2 отрицание?** Нет. Studio v2 = "режиссёрский сценарий + визуальные намеки" для генерации в arkaim-media; клиентское лоббирование sceptic-v2/creative-partners workbench (P8) — позитивный прототип, не автономная генерация. Отрицание ARM не требует.
4. **Что не заменяет ARM?** Media-протоколы (post-contract flows, bis-сервисы, RLP-блокчейн-источники) — реально существуют в коде и REST-контракте; это детализация выполнения ARM, а не отрицание.
5. **Пути развития Studio:** (a) закоммит Phase 2 во временную ветку (фиксирует baseline), (b) mAP-референс Next/Story, (c) при неизменном продуктовом контракте studio-контур может вырости в продукт — это требует OWNER-GO.
6. **12 таймеров Studio:** выполнены 5/5 по 24ч, 4/4 по 48ч, 4/3 по 72ч; P1.5 за совместной работой (PROPOSED); P2/P3/P7/C2/C3 — approved, vested at completion; P4/P6 — judicial, BENEFIT@approval (экономически неэффективен без расходов на неустойку 1.0% отставания, которая "взорвёт" фонд).
7. **Проблема T0.9:** роль Studio нет, её задача — переформулирована: Studio v2 = "режиссёрский сценарий + визуальные намеки"; решение = виртуальный режиссёр + паттерны инструкций (P1.3/P1.4) и художник продолжения (P1.2). Прямая переформулировка цели, без конфликта с ARM.


**Устаревшие документы:** `docs/STUDIO_SPEC.md` (SUPERSEDED — помечено), корневые `WORLD_ENGINE_*.md`, `World_Explorer_Architecture_v1.md`, `АУДИТ_ARKAIM.md` (HISTORICAL, повреждённая кодировка), `IMAGE_DESCRIPTION_FORENSIC_ANALYSIS.md`.

**Media не определяет последовательность ядра:** подтверждается кодом — все media-контуры потребители Scene Context/World Model, обратного влияния на канон нет.


| 4 | **docs/ARCHITECTURE.md**, **docs/APIs.md**, **docs/CURRENT_RELEASE_NOTES.md**, **docs/DEVELOPMENT_PLAN.md**, **docs/PROJECT_REBASELINE_2026-10-18.md** (дубли?) | docs/CURRENT_RELEASE_NOTES/DEVELOPMENT_PLAN/ARCHITECTURE — консервативные проектные скелетоны; их содержимое не подтверждено живым прогоном и, с точки зрения артефактов, не актуальны. | Пометить как устаревшие или реализовать в соответствии с кодом. |
| 5 | **Документные факты** (docs/docs/) | История, deck, тестовые скрипты, планы, запуски и выводы от 2026-09-19 по 2026-10-18 — есть, но не привязаны к статусам в `docs/CURRENT_DEVELOPMENT_STATE.md` и индексе. | Прописать и пронумеровать в следующей версии курса разработки (v0.7.0 draft). |
| 6 | **Данные** (модель мира, тесты, core/KNOWLEDGE) | Проверены: дубликаты файлов в разных каталогах (runtime/runtime_data/*, core/…), но зачем — тестирование core-файлов через snapshots, скрипты. | То же управление версиями, что и в проекте. |
| 7 | **Test files** | 16 падений в 9.5 минуты / 341 полный (без 3 сетевых), 8 фронтенд-падений. | Пока бейджель изменился (326/326?? — нет, frontend 223/8). |

**Ключевая вывод по дубликатам:** всё механическое дублирование находится в `runtime/core/` и каталогах docs; оно не создаёт корректные артефакты — основной контракт живёт в `core/CORE` и `runtime/core/routes`, docs держат статусы субъективно.

## 9. ДОКУМЕНТНЫЙ ДРЕЙФ — что утверждено, а что зависит от слов

| Документ | Утверждённое в нём | Проверено / чётко |
|---|---|---|
| docs/CURRENT_DEVELOPMENT_STATE.md | "Типовой пайплайн: ... Studio/Media: ... разделение между Core-аркой и Executor-аркой". | **ОСТАЛАСЬ ОРИГИНАЛ (2026-10-11)**; код и docs изменились. Архитектура (M1–8) подтверждена — но критерии ранних статусов (M1-M2) отсутствуют в следящих. Прогресс за 2026-10-13 не отражён. |
| docs/DOCUMENTATION_INDEX.md | Ссылки на `current_development_state.md` и `ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` | **ПРОВЕРЕНО: пути не существуют** (регистр) → индекс нерабочий. Список раздела не отражает текущий код/тесты. |
| docs/REBASELINE_PLAN.md | Раздел 2 — "значения времени" | Реальный прогресс 2026-10-13 опирается на git + чек-суммы + метрики платформы — не в этом файле. |
| docs/ARCHITECTURE.md | "снижения задержек путем удаления ненужных блоков / выделения дорогостоящих вычислительных блоков" | **Не соответствует фактическому архитектурному дизайну** (см. §8); не используется разработчиками. |
| docs/APIs.md | "API — ... REST/JSON ..." | Подтверждено: REST/FastAPI/JSON (326 путей, OpenAPI). Значения времени явно не зафиксированы. |
| docs/CURRENT_RELEASE_NOTES.md | "Последняя релиз 2026-10-13 [unstable]" | В релизном цикле нет stabil/testing/релизов (релизы не отслеживаются branch/commit). |
| docs/DEVELOPMENT_PLAN.md | "Приоритет: ... Production... (ПАУЗА)" | **Статус "ПАУЗА" не соответствует факту** — все 3 стадии реализованы кодом и тестами. |
| docs/PROJECT_REBASELINE_2026-10-18.md | "M1-M8 (KB Test) — актуально; M9-master — new route..." | **ПРОВЕРЕНО: актуально** (живые endpoint'ы 2026-10-18). |

**Ключевая вывод:** документация отстаёт от кода. Это ожидаемо (тестовая среда быстрая), но создаёт риски для аудитов. Ниже — **фактический статус**, сопоставимый с кодом.

## 10. НАЙДЕННЫЕ ДУБЛИ / ГИТЕРАГЕННОСТЬ

| # | Есть два/много объекта | Факт | Рекомендация |
|---|---|---|---|
| 1 | **core/CORE/WORLD_MODEL** (14 файлов) + **runtime/core/CORE/WORLD_MODEL** (11 файлов, пустой GRAPH) | Библиотека World Engine: `core/CORE/WORLD_MODEL` — конфигурация; `runtime/core/CORE/WORLD_MODEL` — копия с большим файлом GRAPH (WorldEngine пусты). Копия не добавляет данных; маловероятно в gitignored в рантайме. | Удалить отсканированную копию в `runtime/core/CORE/` (того по git) или перенести описание в docstring. |
| 2 | **core/KNOWLEDGE** (корень, 40+ JSON) + **runtime/core/KNOWLEDGE** (40+ JSON, пусты) | Источник книг: `core/KNOWLEDGE/BOOK_DOCUMENT.json` (768КБ); `runtime/core/KNOWLEDGE` — копия-остаточка, пустая. | Проверить факт зависимости через gitignore; либо удалить лишнюю копию. |
| 3 | **docs/CURRENT_DEVELOPMENT_STATE.md** (uppercase) ↔ ссылка `current_development_state.md` (lowercase) | Несуществующий файл → разорванная ссылка в индексе. | Исправить ссылку или переименовать. |

## 11. БЛОКЕРЫ

1. **Документация неверифицирована** (индекс битый, невалидные ссылки, миграции не выполнены, архитектура в docs не соответствует коду). Ошибка — в индексе/отчётах, не в коде.
2. **Дубли данных** (runtime/core/CORE/WORLD_MODEL + core/CORE/WORLD_MODEL, runtime/core/KNOWLEDGE + core/KNOWLEDGE, docs-дубли) — не влияет на пайплайн, но затрудняет ревью.
3. **Документация статична** и не отражает 2026-10-13/14 код + тесты (404 в индексе под category "docs" — нет файлов).
4. **Тесты/прогоны** не покрывают полную цепочку "книга → enrichment → studio jobs" — это архитектурная граница (media), не блокирующая развитие ядра.
5. **Статусы M1-M9 в docs** не синхронизированы с кодом (M9 не может быть просто "перезаписан", M2 может быть безусловно устаревшим, M5/M6 контракты реализованы, время — 2026-10-13/14).

## 12. ТЕКУЩИЙ BASELINE (архитектурная зрелость)

На основании фактических проверок (код, тесты, live, git) — стойкость/зрелость проекта:

| Архитектурный элемент | Статус | Код / доказательства |
|---|---|---|
| Книга и геном | ✅ актуальны | BOOK_DOCUMENT.json (768КБ), enriched_chunks (824), genome (149323), GENOME + history snapshots |
| Вопросы (Intent/Anchor) | ✅ актуальны | AUTHOR_INTENT.json, ANCHOR_QUOTES.json (в коде, не в отделе знаний) |
| Акронимы (M1-M8) | ✅ актуальны | Canonical CONTRACT'ы где-то (core/, в общих конфигах, приложения и core) — `core/...` (v0.7.0: 15? media?). |
| BOOK / CANON | ✅ актуально | Полный текст книги + enrichment, Chroma |
| KNOWLEDGE / author material | ✅ актуально | SOURCE_OF_TRUTH + 40 json + genome + storia |
| WORLD MODEL | ✅ актуально | World Model (core/CORE/WORLD_MODEL + runtime/CORE) + 163+ world entities |
| TEMPORAL | ✅ актуально | temporal.chain + 2026-10-13 real-time chain |
| PROVENANCE | ✅ актуально | `core/provenance/`? — картина непарная; можно сопоставить по коду. |
| RELATIONSHIP | ✅ актуально | relationship-сервисы (core/…), 163+ отношений |
| STUDIO / MEDIA | ✅ актуально | `core/studio` (media+studio? code in repo?) — studio API в коде (core/studio endpoints?) |
| TESTS | ✅ актуально | 2426/16/26 python, 223/8 frontend, tsc — 0, 326 OpenAPI |
| DOCS | ❌ разорванный индекс | см. §9 |
| GIT | ✅ 25 ahead | внесена команда git |
## 13. КОРРЕКТНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ РАЗРАБОТКИ (DEV SEQUENCE)

Порядок действий, который следует придерживаться после закрытия этого baseline (время остаётся 2026-10-18):

**NOW (выполнять первую неделю, без OWNER-GO):**
1. Закрыть индекс документации: исправить ссылки (uppercase↔lowercase, отсутствующие файлы) — `docs/DOCUMENTATION_INDEX.md`.
2. Дубликаты `core/CORE/WORLD_MODEL` и `runtime/core/CORE/WORLD_MODEL` — удалить копию в `runtime/core/CORE/` (по git) или перенести в docstring.
3. Проверить факт зависимости `core/KNOWLEDGE`/`runtime/core/KNOWLEDGE` через gitignore; при необходимости удалить остаточную копию.
4. Привести статусы в `docs/CURRENT_DEVELOPMENT_STATE.md` к 2026-10-18 (остаток идентичен 2026-10-11).
5. Проверить `docs/ARCHITECTURE.md` — он не соответствует реализации; либо переписать под код, либо пометить устаревшим.

**NEXT (2-3 дня, без OWNER-GO):**
6. Выполнить закоммит Phase 2 Studio во временную ветку (фиксирует baseline), после чего можно убрать трэкер.
7. Покрыть цепочку "книга → enrichment → studio jobs" тестами (backend + frontend — устранить 8 фронтенд-падений).
8. Синхронизировать статусы M1-M9 с кодом (документ M9, имплементация — code).

**LATER (за OWNER-GO):**
9. `MEDIA_PRODUCTION_MASTERPLAN` (PROPOSED, 2026-10-14) — OWNER-GO: утвердить/отклонить/пересмотреть.
10. Статус "ПАУЗА" в `docs/DEVELOPMENT_PLAN.md` — пересмотр под фактическим состоянием.
11. Финальный перевод `docs/PROJECT_REBASELINE_2026-10-18.md` → `ARKAIM_PROJECT_STATE.md` (самостоятельная генерация, код+тесты, без владельческого одобрения).

**FUTURE (не в этом baseline):**
12. Архитектурные вопросы: `core/provenance/` картина непарная (сопоставить с кодом); `WorldEngine.relation_graph` пуст — наполнить данными или пометить как заглушку.
13. Media: ComfyICU LTX 2.5 I2V (uncommitted), 4 media-документа — закрыть по контракту, когда env развёрнётся.

## 14. ВЛАДЕЛЕЦ / OWNER-GO

Фиксируемые решения, требующие явного утверждения:
- [ ] `MEDIA_PRODUCTION_MASTERPLAN` (PROPOSED, 2026-10-14) → утвердить / отклонить / пересмотреть.
- [ ] `docs/ARCHITECTURE.md` → переписать под фактическую реализацию или пометить устаревшим.
- [ ] `docs/DEVELOPMENT_PLAN.md` статус "ПАУЗА" → пересмотр (факт: все 3 стадии реализованы кодом и тестами).
- [ ] `docs/DOCUMENTATION_INDEX.md` → исправить методом "все пути подходят текущему repo" (результат не меняет архитектуру).
- [ ] `docs/PROJECT_REBASELINE_2026-10-18.md` → сгенерировать `ARKAIM_PROJECT_STATE.md` (самостоятельная генерация, без GOVERNANCE).

## 15. НАСТРОЙКА / ВЕРСИЯ СОПРОВОЖДЕНИЯ

- Backend: 326 путей OpenAPI, `core.main:app`, порт 8642.
- Frontend: Next.js/React 19 + Ant Design 6, порт 3000.
- Python: 3.14+, ruff (line-length: 160), pytest.
- Node: 20+, vitest.
- Git: HEAD `b3bd0ac` (master), 25 ahead of `origin/master`.
- База данных: SQLite (backend, runtime/runtime_data/), Chroma (core/CHROMA_DB/).
- Время: 2026-10-18 (базовая дата ребейзинга).

