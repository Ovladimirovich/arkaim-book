# Аудит состояния и план дальнейшей разработки

Дата среза: 2026-10-21 · коммит `c34e69f` · режим: read-only аудит, кроме правок регрессии и линта (см. §2 и §9).

## 1. Резюме

1. **Продуктовая часть (связи сценария с миром) в рабочем состоянии**: 119 сцен, 99 сцен с разрешёнными связями, 11 сцен с подтверждённой эпохой, 2 сцены с подтверждённой локацией, 15 одобренных книжных связей, 15 связей «фрагмент→событие», 3 одобренных соответствия crosswalk, 6 локаций в модели мира, 8 файлов визуального слоя классифицированы.
2. **Инженерная гигиена отстаёт от продукта**: CI сейчас красный в трёх местах (ruff-check, ruff-format, tsc) — весь долг пришёл из незакоммиченной работы в дереве, а не из наших коммитов.
3. **В дереве лежит незавершённая работа**: 31 изменённый файл, 27 новых, 1 удалённый (59 записей). Из них 9 — мусор (отладочные пробы, скриншоты, служебные каталоги). Главный незавершённый кластер — подсистема «Stage 2» (3 новых сервиса + данные + 2 теста). Остальные 110 записей в `git status` — ложные (изменилось только время файла, содержимое совпадает).
4. **Знание о мире дублируется в четырёх местах**, и два реестра правил противоречат друг другу: глобальный `nameresolver` склеивает «Слава»/«Всеслав» и «Архат»/«Высшее Существо», тогда как утверждённая владельцем сценарная таблица это запрещает. Аналогично расходятся два классификационных реестра.
5. **Открытых решений владельца — 8 групп** (см. §5). Ни одно из них не блокирует текущую работу, но четыре из них блокируют содержательное развитие (идентичность, покрытие, provenance визуала).

## 2. Что сломано прямо сейчас (CI)

CI: `.github/workflows/ci.yml` — backend (ruff check + **ruff format --check** в `runtime/`, `pytest tests/`, `pytest tests/test_narrative_*.py`), frontend (eslint, tsc, vitest, next build), docker build на `main`.

| Проверка | Факт | Причина |
|---|---|---|
| `ruff check runtime/` | **19 ошибок** | **предсуществующий долг на HEAD**: `core/services/question_coverage.py`, `tests/test_m10_*`, `test_m12_*`, `test_m3/m4/m5/m6_*`, `test_question_coverage.py` — содержимое этих файлов совпадает с HEAD, т.е. CI был красным до нашей работы |
| `ruff format --check runtime/` | **30 файлов** | 18 — предсуществующие (HEAD), 4 — из незакоммиченной работы (`reader_profile`, `routes/book`, `knowledge_core_context`, `test_milestone_b`), 8 — новые/пробные файлы. **Наш `tests/test_screenplay_scene_world_links.py` тоже был в списке — исправлен (`991af34`)** |
| `tsc --noEmit` | **1 ошибка** | `arkaim-web/src/shared/api/index.ts:21` — `export * from './studio';` ссылается на удалённый модуль `./studio` (в дереве остался `./contracts/studio`, который уже реэкспортируется строкой выше) |
| `eslint` | 79 предупреждений, 0 ошибок | CI проходит (warnings не валят сборку) |
| `pytest runtime/tests` | **2611 passed, 29 skipped, 3 failed** | 2 предсуществующих (`test_temporal_api_alignment`: ждут 11 связей, мир даёт 6) + 1 **наша регрессия**, исправлена в `5ccd9a9` (`test_world_engine_integration` держал старое число связей 287; после чистки географии связей 80) |
| `pytest core/CORE/narrative_engine/tests` | 26 passed | — |
| `pytest tests/test_visual` | 24 passed, 1 failed | предсуществующее (`test_visual_validator::test_missing_title_fails` — падает и на HEAD) |
| `vitest --maxWorkers=2` | 241 passed | при максимальной параллельности на этой машине файлы периодически флакуют (падали `pages`, `studio-director`, `studio-workspace` в разные прогоны) — CI запускает `npx vitest run` без ограничения, риск нестабильности |

**Вывод:** красные пункты в ruff пришли из предсуществующего долга (CI был красным и до наших коммитов) и из незакоммиченной работы; из наших коммитов виноват был ровно один файл с форматированием — исправлен (`991af34`). `tsc` красный из-за незакоммиченного удаления `src/shared/api/studio.ts`. Открытых файлов в дереве всё равно достаточно, чтобы следующая работа смешалась с чужой.

## 3. Незакоммиченная работа в дереве

`git status --short` показывает **169 записей**, но это сырой счёт. После сверки хешей рабочего дерева с индексом (`git hash-object` против `git rev-parse :path`) картина такая:

| Категория | Записей | Что это |
|---|---|---|
| **Изменено по содержимому** | **31** | настоящая незакоммиченная работа (ниже — разбор) |
| **Новые файлы (untracked)** | **27** | в т.ч. 3 новых сервиса Stage 2, `ASK_EXPANSIONS.json`, 6 новых документов, 4 отладочных скрипта аудита |
| **Удалено** | **1** | `arkaim-web/src/shared/api/studio.ts` (реальное удаление — это и есть причина ошибки `tsc`) |
| **Ложно «изменённые»** | **110** | mtime изменён, содержимое совпадает с индексом (артефакт выгрузки репозитория). Лечится `git update-index --refresh` — **правок в них нет** |

То есть реального объёма работы — **59 записей**, а не 169.

### 3.1 Изменённые по содержимому (31)

| Область | Файлов | Что это |
|---|---|---|
| `arkaim-web/src/**` | 17 | фронтенд-консолидация: страницы (`about`, `artifacts`, `genres`, `interpretations`, `library`, `map`, `search`, `world-engine`), панели админа (6 файлов), `Sidebar`, `Topbar` |
| `runtime/core/**` | 4 | `memory/reader_profile.py`, `pulse_manager.py`, `routes/book.py`, `services/knowledge_core_context.py` |
| `core/CORE/**` | 3 | `knowledge_expansion/store/knowledge_store.py`, `narrative_engine/deep_explorer.py`, `narrative_engine/provenance/knowledge_classification.py` (+10 строк: запись `ASK_EXPANSIONS.json`) |
| `docs/**` | 4 | `CURRENT_DEVELOPMENT_STATE.md`, `DOCUMENTATION_INDEX.md`, `DOCUMENTATION_INVENTORY.md`, `ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` |
| прочее | 3 | `README.md`, `core/config.py`, `scripts/enrich_knowledge_provenance.py` (правится именно дубль реестра классификации, §4.2), `runtime/tests/test_milestone_b.py` |

### 3.2 Новые файлы (27)

| Область | Файлов | Что это |
|---|---|---|
| `runtime/core/services/**` | 3 | `ask_expansion_orchestrator.py`, `ask_gap_detector.py`, `world_gap_pilot.py` — незавершённая подсистема «Stage 2» |
| `runtime/tests/**` | 6 | `test_stage2_ask_expansion.py`, `test_world_gap_pilot.py`, `test_agnes_live_run.py`, `test_comfyicu_live_run.py`, `test_dialogue_knowledge_context.py`, `Comfy Desktop.code-workspace` (мусор) |
| `core/KNOWLEDGE/**` | 1 | `ASK_EXPANSIONS.json` — данные новой подсистемы |
| `arkaim-web/**` | 2 | `src/app/knowledge/` (новая страница), `tests/unit/knowledge-route.test.tsx` |
| `docs/**` + `core/**` | 6 | `ARKAIM_PROJECT_STATE.md`, `PLAN_STAGE2_SOURCE_CANDIDATE.md`, `PROJECT_REBASELINE_2026-10-18.md`, `WORLD_MODEL_PROVENANCE_AUDIT_2026-10-20.md`, `core/_wm_audit_report.md`, `core/_wm_migration_plan.md` |
| мусор | 9 | `runtime/_audit_mk_tok.py`, `runtime/_audit_probe_prov.py`, `runtime/_check_gaps.py`, `runtime/_audit_tok.txt` (отладочные пробы), `.playwright-mcp/`, `runtime_data/`, `notebooks/arkaim_colab_free_t4.ipynb`, 2 PNG-скриншота |

**Главный незавершённый кластер**: «Stage 2» — 3 новых сервиса + `ASK_EXPANSIONS.json` + `docs/PLAN_STAGE2_SOURCE_CANDIDATE.md` + 2 новых теста. Похоже на связанную, но незавершённую подсистему, которую нужно либо дописать и закоммитить, либо откатить.

**Риски:** (а) потеря работы; (б) смешивание с новыми коммитами; (в) `core/config.py` и `scripts/enrich_knowledge_provenance.py` изменены — то есть владелец/другая сессия уже трогает конфигурацию и дубль реестра классификации: перед любыми правками в этих зонах нужно согласование, иначе работа перезапишет друг друга.

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
0.1 **Разобрать незакоммиченную работу (59 записей)**: сначала `git update-index --refresh`, чтобы убрать 110 ложно «изменённых» файлов и увидеть реальную картину; затем по каждому из 31 изменённого / 27 новых / 1 удалённого файла принять решение (дописать и закоммитить / откатить / удалить). Первым — кластер «Stage 2»: он меняет `core/config.py` и `scripts/enrich_knowledge_provenance.py` (зоны, которые уже правит другая сессия), поэтому работа может перезаписать друг друга.
0.2 **Вернуть CI в зелёный**: 18 файлов предсуществующего формат-долга + 19 ошибок `ruff check` (это долг на HEAD, не связанный с текущей работой) — либо починить, либо оформить как отдельную задачу с решением владельца; 4 файла из незакоммиченной работы; `tsc` (1) — `src/shared/api/index.ts` ссылается на удалённый `./studio`. **Наши файлы линтером уже чистые** (проверено: `ruff check` + `ruff format --check` по всем 32 нашим Python-файлам — без замечаний).
0.3 **Убрать мусор из дерева**: 4 отладочные пробы (`runtime/_audit_mk_tok.py`, `_audit_probe_prov.py`, `_check_gaps.py`, `_audit_tok.txt`), `runtime/tests/Comfy Desktop.code-workspace`, 2 PNG-скриншота, `.playwright-mcp/`, `runtime_data/` — удалить и закрыть в `.gitignore` (проверно: `runtime/runtime_data/`, `runtime/logs/`, `runtime/memory/data/`, `.ruff_cache/`, `*.tsbuildinfo` уже игнорируются; корневой `runtime_data/` — нет).
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

## 9. Что изменено в ходе аудита (коммиты)

| Коммит | Что | Зачем |
|---|---|---|
| `5ccd9a9` | `runtime/tests/test_world_engine_integration.py`: порог числа связей 287 → 50 | наша регрессия: после чистки географии связей стало 80, тест держал старое число |
| `9c3425f` | этот документ | аудит и план |
| `991af34` | `runtime/tests/test_screenplay_scene_world_links.py`: применён `ruff format` | наш файл ломал `ruff format --check` в CI |
| `3242e19` | `core/CORE/narrative_engine/provenance/knowledge_classification.py`: убран неиспользуемый `from pathlib import Path` | линт-замечание, накопленное ранее (предсуществующий долг) |
| `c34e69f` | `core/CORE/world_extraction/modules/geography.py`: убраны пробелы в пустых строках | то же, 7 мест |

Незакоммиченная работа владельца/другой сессии не тронута: единственная чужая правка в `knowledge_classification.py` (запись `ASK_EXPANSIONS.json`) сохранена и не попала в коммиты.
