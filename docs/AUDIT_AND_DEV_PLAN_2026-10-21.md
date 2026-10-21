# Аудит состояния и план дальнейшей разработки

Дата среза: 2026-10-21 · коммит `5ccd9a9` · режим: read-only аудит, кроме одного исправления регрессии (см. §2).

## 1. Резюме

1. **Продуктовая часть (связи сценария с миром) в рабочем состоянии**: 119 сцен, 99 сцен с разрешёнными связями, 11 сцен с подтверждённой эпохой, 2 сцены с подтверждённой локацией, 15 одобренных книжных связей, 15 связей «фрагмент→событие», 3 одобренных соответствия crosswalk, 6 локаций в модели мира, 8 файлов визуального слоя классифицированы.
2. **Инженерная гигиена отстаёт от продукта**: CI сейчас красный в трёх местах (ruff-check, ruff-format, tsc) — весь долг пришёл из незакоммиченной работы в дереве, а не из наших коммитов.
3. **В дереве лежит незавершённая работа объёмом 149 файлов** (кластер «Stage 2: ask-expansion / world-gap» + правки evidence-модулей + фронтенд-консолидация). Это главный риск потери и главный источник дрейфа.
4. **Знание о мире дублируется в четырёх местах**, и два реестра правил противоречат друг другу: глобальный `nameresolver` склеивает «Слава»/«Всеслав» и «Архат»/«Высшее Существо», тогда как утверждённая владельцем сценарная таблица это запрещает. Аналогично расходятся два классификационных реестра.
5. **Открытых решений владельца — 8 групп** (см. §5). Ни одно из них не блокирует текущую работу, но четыре из них блокируют содержательное развитие (идентичность, покрытие, provenance визуала).

## 2. Что сломано прямо сейчас (CI)

CI: `.github/workflows/ci.yml` — backend (ruff check + **ruff format --check** в `runtime/`, `pytest tests/`, `pytest tests/test_narrative_*.py`), frontend (eslint, tsc, vitest, next build), docker build на `main`.

| Проверка | Факт | Причина |
|---|---|---|
| `ruff check runtime/` | **19 ошибок** | чужое: `core/services/question_coverage.py`, `tests/test_m10_*`, `test_m12_*`, `test_m3/m4/m5/m6_*`, `test_question_coverage.py`, `test_stage2_ask_expansion.py` — все в незакоммиченной работе |
| `ruff format --check runtime/` | **29 файлов** переформатировать | то же (в т.ч. `core/routes/book.py`, новые `tests/test_world_gap_*.py`) |
| `tsc --noEmit` | **1 ошибка** | `arkaim-web/src/shared/api/index.ts:21` — `export * from './studio';` ссылается на удалённый модуль `./studio` (в дереве остался `./contracts/studio`, который уже реэкспортируется строкой выше) |
| `eslint` | 79 предупреждений, 0 ошибок | CI проходит (warnings не валят сборку) |
| `pytest runtime/tests` | **2611 passed, 29 skipped, 3 failed** | 2 предсуществующих (`test_temporal_api_alignment`: ждут 11 связей, мир даёт 6) + 1 **наша регрессия**, исправлена в `5ccd9a9` (`test_world_engine_integration` держал старое число связей 287; после чистки географии связей 80) |
| `pytest core/CORE/narrative_engine/tests` | 26 passed | — |
| `pytest tests/test_visual` | 24 passed, 1 failed | предсуществующее (`test_visual_validator::test_missing_title_fails` — падает и на HEAD) |
| `vitest --maxWorkers=2` | 241 passed | при максимальной параллельности на этой машине файлы периодически флакуют (падали `pages`, `studio-director`, `studio-workspace` в разные прогоны) — CI запускает `npx vitest run` без ограничения, риск нестабильности |

**Вывод:** ни один красный пункт не вызван нашими коммитами, но CI красный **сейчас**, и это блокирует любую следующую работу в коммитах.

## 3. Незакоммиченная работа в дереве (149 файлов)

| Область | Файлов | Что это |
|---|---|---|
| `core/CORE/**` | 35 | evidence-модули (repository/resolver/lifecycle/external_registry), `narrative_engine/deep_explorer.py`, `knowledge/*` (reasoning_repository, screenplay_link_candidates, screenplay_links_provenance, world_resolver), `knowledge_classification.py` (+10 строк: запись `ASK_EXPANSIONS.json`), `knowledge_export`, `pulse/layers.py` |
| `docs/**` | 25 | переписаны отчёты и планы (`CURRENT_DEVELOPMENT_STATE`, `B3*`, `B4*`, `PROJECT_REBASELINE`, `WORLD_MODEL_PROVENANCE_AUDIT` и др.) |
| `arkaim-web/src/**` | 23 | фронтенд-консолидация: удалён `src/shared/api/studio.ts`, правлены контракты, изменены страницы (`about`, `artifacts`, `genres`, `interpretations`, `library`, `map`, `search`, `temporal`, `world-engine`), удалён `EntityCard`/`StateView`/`WorldProvenanceCard`? — см. `git status` |
| `runtime/tests/**` | 19 | переписаны тесты M1/M2/m10/m16/milestone_b/multi_topic/pulse/related/screenplay_parsing |
| `arkaim-web/tests/**` | 13 | переписаны unit-тесты фронтенда |
| `runtime/core/**` | 7 | `reader_profile`, `pulse_manager`, `book.py`, `knowledge_core_context` + новые сервисы |
| `core/KNOWLEDGE/**` | 6 | `ASK_EXPANSIONS.json` (новый), `SYNOPSIS_DOCUMENT`, `SYNOPSIS_PROFILE`, `enriched_catalog`, `enriched_chunks`, `screenplay_links` — **перегенерированные данные** |
| прочее | 19 | `scripts/*`, `.clinerules/*`, `README.md`, `АУДИТ_ARКАIM.md`, `notebooks/`, `runtime_data/`, `.playwright-mcp/`, 2 PNG-скриншота, `docs/ARKAIM_PROJECT_STATE.md`, `core/_wm_audit_report.md`, `core/_wm_migration_plan.md` (новые, не закоммичены) |

**Главный незавершённый кластер**: «Stage 2» — `runtime/core/services/ask_expansion_orchestrator.py`, `ask_gap_detector.py`, `world_gap_pilot.py` (все три новые, не закоммичены) + `core/KNOWLEDGE/ASK_EXPANSIONS.json` + `docs/PLAN_STAGE2_SOURCE_CANDIDATE.md` + 19 переписанных тестов. Похоже на связанную, но незавершённую подсистему, которую нужно либо дописать и закоммитить, либо откатить.

**Риски:** (а) потеря работы; (б) смешивание с новыми коммитами; (в) `enriched_chunks.json`/`enriched_catalog.json`/`screenplay_links.json` перегенерированы в дереве — при коммите они изменят хеши, от которых зависят guard'ы (каталог сцен считает хеш только сценария, но `enriched_chunks` влияет на claim_id и на связи сцен).

## 4. Расхождения в данных и правилах (существо, а не оформление)

### 4.1 Два реестра правил имён — противоречат друг другу
| | `core/CORE/intelligence/nameresolver.py` (`CANONICAL_MAP`, 14 имён) | `core/CORE/knowledge/screenplay_scene_aliases.py` (утверждено владельцем) |
|---|---|---|
| «Слава», «Всеслав» | склеены со `Славный` | **запрещено**: «Слава — обычное слово, а не имя персонажа» |
| «Архат» | склеен с `Высшее Существо`, `Основатель Иерархии Света` | **запрещено** склеивать `Архат`/`Учитель` |
| «Наставники» | ← `Посвящённые` | ← `Наставник*` (регулярное выражение) |
| `Славный` | ← `Славным`, `Славного` | `Славн(ый|ого|ому|ым|ом)` |

Последствия: при пересборке одной таблицы из другой `screenplay_scene_knowledge` и `screenplay_scene_world_links` начнут давать **разные** `canonical_name` для одних и тех же написаний → разные связи персонажей у одной сцены. **Guard-теста на согласованность нет.**

### 4.2 Два классификационных реестра
- Канон: `core/CORE/narrative_engine/provenance/knowledge_classification.py` (список `KnowledgeFileClassification`, теперь с `source_path`, 50+ записей, читается рантаймом).
- Дубль: `scripts/enrich_knowledge_provenance.py` (свой локальный dict `filename → (category, source_level, notes)`, обходит только `core/KNOWLEDGE/*.json`, визуальный слой не трогает). Расхождение схем: у канона `category`+`description`+`is_canon`+`requires_author_review`, у дубля — тройка без `is_canon`/`requires_author_review`.

### 4.3 Документы противоречат артефактам (нормативные)
- `docs/B3_CW_CANDIDATES.md:20,91,107,167,169,171` — «русские canonical ID», «2 approved mappings», «runtime connections: 0», «B3b и B4 заблокированы» — фактически crosswalk **v2**, 3 mappings, подключён к runtime, миграция частично выполнена.
- `core/_wm_audit_report.md:3,20-24,44-46,72,110-126` и `core/_wm_migration_plan.md:3,14-15,72-74,89` — «STOP GATE, миграция не реализована», «2 approved», «EN/RU записи не удаляются» — фактически EN-дубли удалены, принято решение «одно место — один id», кроссворк расширен.
- `docs/WORLD_MODEL_PROVENANCE_AUDIT_2026-10-20.md:5,43,45,62,78,81-84` — «38 записей GEOGRAPHY», «10 дублей region_*/geo_*», «дубли не устранены» — теперь 17 записей, дубли устранены (`7c3ee30`); G1/G5 остаются открытыми.
- `docs/CURRENT_DEVELOPMENT_STATE.md:3,72,151,157` — re-baseline от 2026-10-11 (HEAD `1e3f812`), перечень выполненного без новых результатов, числа тестов устарели (frontend «84/84» — сейчас 241), «расширение crosswalk, новые production-функции, изменения данных — требуют отдельного OWNER-GO» — фактически изменения данных уже одобрены владельцем 2026-10-20.
- `docs/CLAUDE.md:90,102,153,165`, `runtime/API_DOCUMENTATION.md:5,182`, `docs/LEGACY_CORE_WORLD.md:88-98`, `docs/B3A_ID_RECONCILIATION_REPORT.md`, `docs/B_WORLD_ENGINE_PLAN.md`, `docs/ARKAIM_PROJECT_STATE.md`, `docs/PROJECT_REBASELINE_2026-10-18.md` — «547 сущностей», «413 сущностей», «38 географических», «9 записей claim_temporal_links», «2 маппинга» — фактически 503/17/15/3.
- `docs/SCREENPLAY_SCENE_WORLD_LINKS_REPORT.md` §7 и генератор — числа **захардкожены** («9», «2») вместо вычисления; числовые разделы §2–§6 актуальны.
- `arkaim-web/src/shared/lib/api.ts:156` — мок `locations_count: 13`, фактически **6**.
- `core/CORE/narrative_engine/data/WORLD_MODEL.json:2` — `updated_at` не обновлялся при правках 2026-10-20/21.
- `docs/DOCUMENTATION_INDEX.md` / `DOCUMENTATION_INVENTORY.md` — новые документы (`SCREENPLAY_SCENE_WORLD_LINKS_REPORT.md`, `VISUAL_CARDS_ATLANTIDA_OCEANIA_2026-10-21.md`) не внесены.

### 4.4 Параллельные представления одной сущности
| Сущность | Представления | Канон сегодня |
|---|---|---|
| Южная цивилизация | `WORLD_MODEL.locations[океания]`, `WORLD_MODEL.civilizations[океания]`, `MAP_DATA.regions[oceania]`, `LOCATION_VISUALS[Океания]`, `civilization_profiles[oceania]`, `CROSS_REFERENCES[Атлантида]`, `ARCHAEOLOGY[Океании/Атлантиды]` | модель мира + реестр алиасов; **геном сущности не содержит** (проверено: в `GENOME_v1.0.0.json` слово «Атлантида» встречается только в нарративных названиях `modules.scenes[].title`, `modules.narrative_arcs[]`, `modules.conflicts[].name` — это историческое имя в тексте, а не отдельная сущность) |
| Гиперборея | `WORLD_MODEL.locations[гиперборея]` **и** `WORLD_MODEL.civilizations[гиперборея]` — один и тот же id в двух категориях | требует решения: сущность одна, категории две |
| EN-цивилизации | `WORLD_MODEL.civilizations[hyperborean]`, `[vedic]` — EN-id без пары в `locations` | либо дописать EN-локации, либо пометить как псевдонимы |
| Имена персонажей | `nameresolver.CANONICAL_MAP`, `screenplay_scene_aliases`, `nameResolver` в пульсе | две несогласованные таблицы (§4.1) |
| Классификация знаний | `knowledge_classification.py`, `scripts/enrich_knowledge_provenance.py` | первый (§4.2) |
| Эпохи | `WORLD_MODEL.epochs` (12), `EPOCH_PALETTES.json`, `GENOME.modules.timeline` (17) | модель мира; палитры — художественная модель (оклассифицировано) |
| Локации | `WORLD_MODEL.locations` (6), `GEOGRAPHY.json` (17), `MAP_DATA.regions` (10), `LOCATION_VISUALS` (5), `GENOME.modules.location_visuals` (5) | модель мира; остальное — производные/внешние/художественные |

## 5. Открытые решения владельца (сводка)

| # | Вопрос | Где зафиксирован | Статус |
|---|---|---|---|
| G1 | Ссылки на внешние источники по каждому claim'у `ARCHAEOLOGY.json` (или `source: UNKNOWN`) | `docs/WORLD_MODEL_PROVENANCE_AUDIT_2026-10-20.md:33,76` | **открыт** |
| G5 | «Каргонодская культура» — подтвердить/отклонить | там же `:16,61` | **открыт** (мягко: `geo_*`-зеркало удалено, `ARCHAEOLOGY.json` не тронут) |
| G6 | Статус 7 незамапленных регионов MAP_DATA (по умолчанию `PRESERVE_UNCHANGED`, но это не решение) | `core/_wm_audit_report.md:119-126` | **открыт** |
| G7 | Какой реестр имён канонический (§4.1) | следствие двух таблиц | **открыт** |
| G8 | «Ученики» ↔ «Ученики (плеяда)» — тождество? | отчёт о связях, §6 | **открыт** |
| G9 | 3 сцены с одобренной книжной связью без claim-связи (scene_003, scene_021 и ещё одна) — одобрять claim-связи? | там же | **открыт** |
| G10 | Ревизия содержимого 8 файлов визуального слоя (помечены `requires_author_review`) | `knowledge_classification.py` | **открыт** |
| G11 | Knowledge roadmap GO-3…GO-7 (typed-резолверы в API, конфликт-детект, claim identity policy, /knowledge-маршрут) | `docs/ARKAIM_KNOWLEDGE_IMPLEMENTATION_ROADMAP.md:208-220` | **открыт** |
| G12 | Медиа-план (PROPOSED), F-12 (миграция film-БД), MVP-контракт §12, frontend-backlog B1/B2/B10 | `docs/ARKAIM_PROJECT_STATE.md`, `docs/MVP_CONTRACT_v2.md:311`, `docs/FRONTEND_RESTORE_BACKLOG.md:10-12` | **открыт** |

## 6. Что система умеет по миру сейчас (покрытие)

| Срез | Значение | Комментарий |
|---|---|---|
| Сцены в каталоге | 119 | read-only, заморожен хеш сценария |
| Сцены с разрешёнными связями | 99 | подтверждённые или производные |
| Сцены с подтверждённой эпохой | 11 | из них 6 — по решениям владельца 2026-10-20 |
| Сцены с подтверждённой локацией | 2 | «Острова Атлантиды» и «Острова Океании» → одна локация `океания` |
| Сцены без места действия | 117 | осознанный пробел: сценарий не называет места |
| Одобренные связи сценарий↔книга | 15 | `screenplay_links.json` |
| Одобренные связи фрагмент→событие | 15 | `claim_temporal_links.json` (было 9) |
| Одобренные соответствия crosswalk | 3 | `region_arkaim`, `region_hyperborea`, `region_oceania` |
| Локации в модели мира | 6 | было 13 |
| Сущности World Engine | 503 | было 524; связи графа 80 (было 287) |
| Регионы мира, не сопоставленные ни с одной сценой | **7 из 10** | `gardarika`, `sintashta`, `mehenjo`, `sumer`, `gobekli`, `bolgar`, `lepeni_vir` — гейт G6 |
| Записи `GEOGRAPHY.json` | 17 (было 38) | 10 регионов + 4 маршрута + 2 энергетические линии + 1 персональная локация; 21 зеркало `geo_*` удалено (`7c3ee30`) |
| Файлы визуального слоя с классом | 8 | `ARTISTIC_MODEL`, требуют проверки автором |

## 7. План дальнейшей разработки

### Шаг 0. Инженерная гигиена (инженерная работа, без решений владельца) — «разблокировать CI»
0.1 **Разобрать 149 незакоммиченных файлов**: определить судьбу каждого кластера (дописать и закоммитить / откатить / убрать в отдельную ветку). Первым — кластер «Stage 2»: он уже меняет `enriched_chunks.json`, `screenplay_links.json` и 19 тестов, то есть затрагивает ровно те артефакты, от которых зависят наши связи сцен.
0.2 **Вернуть CI в зелёный**: `ruff check runtime/` (19) и `ruff format --check runtime/` (29) — починить в том же кластере, которому они принадлежат; `tsc` (1) — `src/shared/api/index.ts` ссылается на удалённый `./studio`.
0.3 **Определить судьбу артефактов в дереве**: `runtime_data/`, `.playwright-mcp/`, `experiments-panel-*.png`, `notebooks/` — в `.gitignore` или удалить.
0.4 **Сделать числа в отчётах и доках вычисляемыми**: §7 генератора отчёта связей и «Источники» (§4.3) — сейчас 9/2 захардкожены. Добавить тест «числа в отчёте равны данным».
0.5 **Ограничить параллельность vitest** (или починить флакующие файлы) — CI запускает `vitest run` без `--maxWorkers`, на этой машине бывают падения.

### Шаг 1. Решения владельца (блокируют содержательную часть) — по §5
1.1 **Один канонический реестр имён**: `nameresловер` или сценарная таблица; что делать с «Слава/Всеслав», «Архат/Высшее Существо», «Наставники/Посвящённые»; затем — единый источник + guard-тест на согласованность.
1.2 **Судьба 7 регионов MAP_DATA**: оставить `PRESERVE_UNCHANGED` как явное решение или часть кандидатов.
1.3 **G1/G5**: внешние источники по claim'ам `ARCHAEOLOGY.json`; «Каргонодская культура» — подтвердить/отклонить.
1.4 **«Ученики» ↔ «Ученики (плеяда)»**: тождество (и где тогда «Наставники»?) или разные сущности.
1.5 **3 сцены без claim-связи**: одобрять ли (тогда сцены получают эпоху) или оставить как есть.
1.6 **Ревизия визуальных карточек**: 8 файлов помечены «требует проверки автором» — что подтверждаем, что переписываем.
1.7 **Продуктовые гейты** (G11–G12): подключать ли typed-резолверы к API, принимать ли медиа-план, F-12, MVP §12, порядок frontend-backlog.

### Шаг 2. Содержательная работа (после шага 1) — «связи с миром глубже»
2.1 **Устранить дубли id и устаревшие метки в модели мира** (проверено: геном здесь не при чём — «Атлантида» встречается в нём только в нарративных названиях сцен и арок, конфликта с решением «Атлантида = Океания» нет): `WORLD_MODEL.civilizations[гиперборея]` дублирует `locations[гиперборея]`; `civilizations[hyperborean]` и `[vedic]` — EN-id без пары в `locations`; `updated_at` = `2026-10-19T06:44:13`, хотя данные правились 20–21.10.
2.2 **Убрать второй классификационный реестр** (`scripts/enrich_knowledge_provenance.py`) в пользу канонического; покрыть визуальный слой тем же механизмом, что и `core/KNOWLEDGE`.
2.3 **Актуализировать нормативные документы** под факты (§4.3): `CURRENT_DEVELOPMENT_STATE`, `B3B_*`, `B3_CW_CANDIDATES`, `WORLD_MODEL_PROVENANCE_AUDIT`, `_wm_audit_report`, `_wm_migration_plan`, `CLAUDE.md`, `API_DOCUMENTATION`, `LEGACY_CORE_WORLD`; внести новые документы в индекс.
2.4 **Двигать покрытие, а не проценты**: сейчас 2 сцены с местом действия и 11 с эпохой. Следующие кандидаты по честным основаниям: (а) место действия сцены — 117 сцен без него; решение возможно только через утверждённые правила (владелец), не через морфологию; (б) эпохи — через 3 неодобренные claim-связи и новые события; (в) персонажи — уже 211 связей, покрытие 99 сцен.
2.5 **Временная линия**: панель уже есть (`GET /studio/timeline`); следующий шаг — связать её с каноническими событиями и temporal-узлами (то, что уже есть в `WORLD_MODEL`), не вводя реконструкцию.

### Шаг 3. Что сознательно не делаем
- Не расширяем таблицы алиасов автоматически и не склеиваем сущности по смыслу.
- Не запускаем пересборку данных (`build_world_model.py --write`, `enrich_knowledge_provenance.py`) без отдельного решения владельца: это перезапишет `WORLD_MODEL/*.json` и потеряет provenance-поля.
- Не подключаем typed-резолверы к публичному API без решения (действующий STOP GATE).
- Не начинаем визуальную работу и генерацию медиа: содержательная модель мира — первитет.

## 8. Критерии готовности шага 0
1. `git status` содержит только осознанные изменения (или пуст).
2. `cd runtime && ruff check . && ruff format --check .` — чисто; `cd arkaim-web && npx tsc --noEmit && npm run lint` — чисто.
3. `cd runtime && python -m pytest tests -q` — без падений; `python -m pytest tests/test_visual -q` (с `PYTHONPATH=core/CORE`) — без падений; `cd arkaim-web && npx vitest run --maxWorkers=2` — без падений.
4. `python scripts/generate_screenplay_world_links_report.py --check` — отчёт актуален, числа в §7 отчёта вычисляемые.
