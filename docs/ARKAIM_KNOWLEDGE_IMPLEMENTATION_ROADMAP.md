# ARKAIM KNOWLEDGE — IMPLEMENTATION ROADMAP (рабочая карта)

**Назначение:** единый рабочий документ последовательной реализации Knowledge Core от текущего фактического состояния к TARGET STATE.
**Основа:** `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` (Source of Truth архитектуры) + фактическое состояние репозитория + `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`.
**Отношение к SoT:** этот документ не меняет архитектуру и не создаёт новых сущностей. При расхождении приоритет: код → тесты/live-доказательства → ADR → SoT-план → этот roadmap.
**Создан:** 2026-10-11. **Baseline HEAD:** `1e3f812`.

**Статусы задач:** `NOT STARTED` → `IN PROGRESS` → `DONE`; либо `BLOCKED — OWNER-GO`.

---

## 1. CURRENT BASELINE

**Git:** HEAD `1e3f812` (2026-10-02, `fix(knowledge): restore derived genome card projection`).
**Рабочее дерево на момент создания:** 2 изменённых tracked-файла (`core/CORE/genome/history/index.json` — side effect `Pulse.load()`; `docs/CURRENT_DEVELOPMENT_STATE.md` — синхронизация DOC DRIFT, не закоммичена) и ~81 untracked-путь.

**Факт по документам:** из 175 `docs/**/*.md` в git — 25. Вне версионирования: сам SoT `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md`, `KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md`, `DOCUMENTATION_INDEX.md`, `PROJECT_CURRENT_STATE_AUDIT.md`, `docs/archive/`, `SCHEMAS/`, `scripts/`, `notebooks/`, `arkaim-mobile/`, пустой `tests/`, мусорные логи (`_*.txt`, `*.log`, `arkaim/`).

**Работает (код/тесты/live):**

| Контур | Факт |
|---|---|
| M1 claim semantics | `CanonClaim.make_id`, `normalize_provenance_category`, `Fact.provenance_category`; 8 тестов `test_m1_claim_contract.py`; §12 STOP GATE принят |
| M2 evidence | `core/CORE/evidence/` (repository/resolver/lifecycle/external_registry); 43 теста; три решения приняты |
| M3/M4 boundary | typed refs + read-only резолверы; 17 тестов — **в API не подключены** |
| M5/M6/M7 | typed records + 3 репозитория + deterministic reasoning service; 22 теста — **production-писателей нет, `runtime/runtime_data/knowledge/` пуст** |
| M8 read-only API | search/card/trace, фильтры, пагинация, `totals`, M8e–M8j; live 2026-10-02 — итог **PARTIAL** |
| M9 (вариант A) | `KnowledgeTraceCard.tsx` внутри World Engine Context; после T5 — 11 unit-тестов карточки + 3 контрактных, lineage/totals/состояния в UI; build PASS |
| Тесты | **Re-baseline 2026-10-11, HEAD `1e3f812` (коммит 2026-10-02): targeted Knowledge Core regression (20 файлов) — после H2-A (GO-1+GO-2): 341 collected / 341 passed / 0 failed / 6 warnings / ~5s** (после T4: 338/338; до T4: 333/333; до фикса GO-8: 330 / 329 passed / 1 failed); прежние числа (1616 функций — подсчёт, 153/149/148, 37 passed от 2026-10-01) — исторические снимки; отдельный файл GO-2 `tests/test_error_envelope_422.py` — 6 passed |

**Незакрыто (проверено по коду):**

- **BASELINE-1 — РЕШЕНО (GO-8, 2026-10-11):** падение `test_no_duplicate_claims` устранено фиксом в `_book_claims` (genome-fallback больше не попадает в book claims); targeted regression добавлен; T1-targeted прогон: **333 collected / 333 passed / 0 failed**;
- **NEW-1 (новое, найдено при GO-8, НЕ исправлялось):** при незагруженном World Engine (`_world_engine is False`, т.е. путь деградации из `builder.py:80-90`) источники `world_model` и `archaeology` отдают **одинаковые тексты** (7 пар у `region_arkaim`); в штатном пути (движок загружен) дублей нет; вне объёма GO-8;
- ~~`trace.status=COMPLETE` при `UNKNOWN`-evidence — `runtime/core/routes/knowledge_cards.py:438-445` (PROBLEM №1)~~ — **ЗАКРЫТО (GO-1, 2026-10-11):** правило `COMPLETE` ⇔ есть claims ∧ все evidence `RESOLVED` ∧ нет `limitations`, иначе `PARTIAL` (`UNKNOWN` зарезервирован); live `region_arkaim` → `PARTIAL` (17 RESOLVED + 7 UNKNOWN);
- ~~форматы ошибок: envelope 401/404 vs `detail` 422 (PROBLEM №2)~~ — **ЗАКРЫТО (GO-2, 2026-10-11):** глобальный `RequestValidationError`-handler в `runtime/core/main.py` отдаёт envelope `{"ok":false,"error":{"code":"HTTP_422","message","details":[{loc,msg,type}]}}` на всех routes; фронт без правок (`parseErrorBody` уже парсит envelope);
- `search.total` = размер страницы — `knowledge_cards.py:34-103` (PROBLEM №3, GO-free, семантика задокументирована T3);
- ~~evidence-строки не несут `claim_id` — join с claim неявный по `source_ref`/`chunk_id`~~ — **ЗАКРЫТО (T4, 2026-10-11):** evidence-строки несут `claim_id` через тот же bridge `_card_claim_id`; без достоверного соответствия — `null`;
- `claim_id` только для `book:`+`chunk_id` и allowlist external (M8h/M8i): 18/25 у `region_arkaim`;
- секции trace-DTO — `list[dict]` (`runtime/core/dto/knowledge.py:19-26`), item-level schemas нет;
- frontend `KnowledgeTrace` (`arkaim-web/src/shared/api/contracts/knowledge.ts:84-97`) не содержит `lineage`, `totals`, `offset/limit/next_offset`; `KnowledgeTraceCard` lineage не рендерит; knowledge e2e-спеки нет;
- temporal в live — только маркеры `PROJECTED_FROM_WORLD_REF`; typed M3/M4 резолверы не подключены (PROBLEM №5);
- `KnowledgeCard.contradictions` пуст; M7 не связан с M10 findings.

---

## 2. Статусная карта

### DONE
- M1 — единый claim/provenance контракт + compatibility mapping + STOP GATE §12.
- M2 — evidence contract/policy/lifecycle/external locator (три решения, реализация, тесты).
- M3, M4 — минимальный boundary scope (typed refs + резолверы + тесты).
- M5, M6, M7 — минимальный scope (typed records + repositories + deterministic reasoning + тесты).
- M8 включая M8e–M8j — минимальный read-only API, journey, live-верификация backend-ветки 2026-10-02.
- M9 (вариант A) — embedded read-only drill-down, unit/regression/build/smoke.
- Git-нормализация frontend (`arkaim-web` в git, v2 удалён), DOC DRIFT-синхронизация 2026-10-02 (в working tree).
- M10 / M10.2 — suggest-only gate, RBAC, history (TESTED).

### PARTIAL
- **M0** — решения есть, отдельного mapping/compatibility-документа и acceptance checklist нет (mapping живёт в коде и §12 SoT).
- **M3/M4** — контракты и тесты есть, в read path trace не подключены.
- **M5/M6/M7** — контракты и тесты есть, production-записей нет, lineage live = 0.
- **M8** — нет item-level schemas, claim↔evidence join явный (T4, `claim_id` есть у book/external claims), нет `claim_id` для части источников (genome/world — fail-closed, GO-5), статус-семантика зафиксирована (GO-1), Ask/RAG без claim/evidence IDs.
- **M9** — UI с lineage и синхронизированным контрактом (T5); нет отдельного route и e2e.
- **Traceability journey** — backend live подтверждён; lineage M5→M6→M7 только тестами.

### BLOCKED — OWNER-GO
- PROBLEM №5 (typed M3/M4 в API). ~~PROBLEM №1 (семантика `trace.status`), PROBLEM №2 (формат 422)~~ — закрыты GO-1/GO-2 (2026-10-11, §4).
- Любая production-запись в M5/M6/M7 stores и влияние на карточные `contradictions`.
- Расширение allowlist `claim_id` (сейчас fail-closed — политика M8h/M8i).
- Отдельный Knowledge route, mutation/resolution UI, новые роли.
- Выдача claim/evidence IDs в `/book/ask`.
- Композиция commit и состав untracked-путей (GO-9); объём mojibake-фикса.

### NOT STARTED
- H1-3 (T3) — **DONE**, H1-4 (T4) — **DONE**, H1-5 (T5) — **DONE (2026-10-11, STOP достигнут)**; T1 — DONE, **GO-8 фикс — DONE (baseline зелёный)**, T2 — **DONE (GO-9, 2026-10-11 — commit выполнен)**. **Итог H1: все задачи выполнены и зафиксированы в git; дальше — только новые OWNER-GO (§4).**
- NEW-1 (дубли `world_model`/`archaeology` при деградации World Engine) — не начато, не блокирует H1.
- Browser e2e для knowledge trace; M7 ↔ M10 linkage; relation provenance contract; uncertainty aggregation; production evidence/claim-link records.

### OUT OF SCOPE / D
- D-файлы/D-линейка (по ограничению владельца; точный набор в репозитории не определён — см. §9; ни одна задача их не трогает).
- Media/Studio, mobile, `arkaim-web-v2`, genome/book-продолжение, расширение crosswalk, новый frontend, финальное решение по physical storage (вопрос M0 №2), автономные действия LLM, автоматический conflict resolution.

---

## 3. HORIZON 1 — последовательность задач

> Правило: идти строго по порядку. Обычные инженерные задачи H1 не требуют отдельного GO; остановка — только перед commit (T2) и после T5 (переход в H2).

### T1 — Re-baseline тестов Knowledge Core
- **Статус:** DONE (2026-10-11, HEAD `1e3f812`)
- **Результат:** targeted regression 20 файлов (knowledge_cards, knowledge_kernel, M1, M2 contract/integration/lifecycle, M3, M4, M5, M6, M7, M8 trace/api/b/c/present-anchor/future-extrapolation, provenance, provenance_completion, book_intelligence, visual_conflict): **330 collected — 329 passed / 1 failed, 6 warnings, ~5s**.
- **Падения:**
  - `tests/test_knowledge_cards.py::TestAggregation::test_no_duplicate_claims` — **Knowledge Core, введено HEAD `1e3f812`** (не pre-existing, не unrelated). Эмуляция parent `6f4611b` (отключение нового `_genome_claims`) → 0 дубликатов; diff `1e3f812` в `builder.py` только аддитивный. Причина: `_book_claims` (`builder.py:295-324`) помечает genome-fallback результаты retriever как AUTHOR_CANON `book:{chunk_id}`, `_genome_claims` (`builder.py:326+`) проецирует тот же текст как DERIVED `genome:theme:{id}` → дубликат текста в `book` + `genome`; нарушено требование теста `test_knowledge_cards.py:250` самого коммита `1e3f812`. Исправление не выполнялось → GO-8.
  - Pre-existing/unrelated падений в наборе не обнаружено.
- **Обновлено:** `docs/CURRENT_DEVELOPMENT_STATE.md` (§4.2 + таблица TESTED), `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` (строка Knowledge Card builder + END OF PLAN), настоящий roadmap.
- **Acceptance:** ✅ HEAD проверен; падение классифицировано с executed-доказательством; числа с датой и привязкой к HEAD; исправлений нет; документация обновлена.

### T1b — GO-8: фикс BASELINE-1 (только выявленный регресс)
- **Статус:** DONE (2026-10-11)
- **Решение владельца (GO-8):** исправить только выявленный регресс T1 — устранить двойное попадание genome fallback в `book` и `genome`; не менять M2/M8 contract; не трогать другие проблемы; добавить targeted regression для обычного book claim и genome fallback; после фикса прогнать T1-targeted regression и остановиться.
- **Что сделано:** в `_book_claims` (`core/CORE/knowledge_card/builder.py:308-312`) добавлен пропуск retriever-результатов с `source == "genome"` — genome-fallback больше не абсорбируется как AUTHOR_CANON `book:{chunk_id}`; проекция `_genome_claims` (DERIVED `genome:theme:{id}`) не менялась. Изменение только в read-time построении карточки: M2 contract, M8 DTO, namespace policy, fail-closed не затронуты.
- **Targeted regression (новое в `runtime/tests/test_knowledge_cards.py`):**
  1. `test_ordinary_book_claim_is_kept_as_book_evidence` — обычный book claim (`source=book`, `chunk_id=chunk_123`) остаётся в book, `source_ref=book:chunk_123`, `provenance.category=AUTHOR_CANON`, genome пуст;
  2. `test_genome_fallback_only_is_projected_once_not_as_book_evidence` — только genome fallback → book claims пуст, genome несёт `genome:theme:theme_129` DERIVED (ровно одна копия);
  3. `test_mixed_results_do_not_duplicate_genome_fallback_across_sources` — смешанные результаты → `book:chunk_123` + `genome:theme:theme_129`, отсутствие `book:genome_theme_*`, уникальность текстов book+genome, отсутствие genome-текста в book claims.
- **Проверки:** `tests/test_knowledge_cards.py` — **43 passed**; T1-targeted regression (те же 20 файлов) — **333 collected / 333 passed / 0 failed** на HEAD `1e3f812` (прогон 2026-10-11). `ruff` недоступен в окружении (`No module named ruff`, не в PATH) — линт не выполнялся.
- **Попутно обнаружено (НЕ исправлялось, вне GO-8):** NEW-1 — дубли текстов `world_model`/`archaeology` при незагруженном World Engine (см. §1).
- **Acceptance:** ✅ регресс устранён; контракты M2/M8 и статусы не изменены; baseline зелёный; документация обновлена.

### T2 — Baseline документов и Git
- **Статус:** **DONE (2026-10-11, GO-9).** Решение владельца по составу получено; commit выполнен в рамках GO-9.
- **Готово (фактический анализ `git status` / `git ls-files` / `git check-ignore`):** три списка ниже + проверка секретов (`.env` — gitignored; в кандидатах hardcoded secrets не найдены — повторная проверка 19 документов перед commit тоже чистая).
- **OWNER-GO (GO-9) — решения владельца 2026-10-11:**
  1. **Включить:** код+тесты H1 (10 файлов: `builder.py`, `knowledge_cards.py`, 3 backend-теста, 4 frontend-файла + новый `knowledge-contract.test.ts`), документы A-list (18 untracked `.md` + изменённый `CURRENT_DEVELOPMENT_STATE.md`), `runtime/xray_dashboard/` (4 файла, монтируется `main.py:447`), **`AGENTS.md`** (владелец подтвердил чужий ремонт кодировки), корневой `.gitignore` (junk-паттерны).
  2. **Не включать:** `docs/archive/` (133 файла).
  3. **Не включать:** прочие наборы — `SCHEMAS/`, `scripts/`, `notebooks/`, корневой `tests/` (10), `core/run_*.py`, runtime-утилиты/audit-артефакты, `core/.gitignore`, конфиги `.kilo`/`.clinerules`/`kilo.json`/`opencode.json` — «ничего из этого» (решение владельца).
  4. **Junk:** добавить паттерны в корневой `.gitignore`, файлы **не удалять**.
  5. **Не включать:** `core/CORE/genome/history/index.json` (modified side effect) и 10 genome-снимков; корневой `src/` (устаревшая копия — теперь в gitignore).

**A. Knowledge-документы — должны попасть в git (рекомендация, minimum viable):**
1. `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` — SoT, сейчас untracked (критично: единственный источник истины вне версионирования);
2. `docs/ARKAIM_KNOWLEDGE_IMPLEMENTATION_ROADMAP.md` — рабочая карта (создана 2026-10-11);
3. `docs/KNOWLEDGE_CORE_LIVE_VERIFICATION_2026-10-02.md` — live-отчёт с PROBLEM №1–№5;
4. `docs/PROJECT_CURRENT_STATE_AUDIT.md`, `docs/DOCUMENTATION_INDEX.md` — аудит/индекс;
5. `docs/CURRENT_DEVELOPMENT_STATE.md` — **tracked, изменён** (DOC DRIFT-синхронизация + числа T1) — включить в commit;
6. связанные планы knowledge/World-цепочки: `docs/B3A_ID_RECONCILIATION_REPORT.md`, `docs/B3B_PLAN.md`, `docs/B3B_BASELINE_BEFORE_B4.md`, `docs/B3_CW_CANDIDATES.md`, `docs/B4_PLAN.md`, `docs/B4C_PLAN.md`, `docs/B_WORLD_ENGINE_PLAN.md`, `docs/A1_ROUTE_STATE_MAP_REPORT.md`, `docs/A1R_ROUTE_STATE_CONTRACT.md`, `docs/MVP_CONTRACT_v2.md`;
7. frontend-статус: `docs/FRONTEND_CONSOLIDATION_PLAN.md`, `docs/FRONTEND_TRANSFORMATION_PLAN.md`, `docs/POST_FRONTEND_PRODUCT_ROADMAP.md`.

**B. Junk — не добавлять (рекомендация; удаление/изменение `.gitignore` только по GO):**
- корень: `_backend_err.txt`, `_backend_out.txt`, `_fe_err.txt`, `_fe_out.txt`, `_run_err.txt`, `_run_ok.txt`, `_test_err.txt`, `_test_ok.txt`, `test_auth.txt`, `test_persist.py`, `v2_files.txt`, файл `arkaim` (1695 байт);
- `arkaim-web/_b3_dev_out.txt`, `arkaim-web/_manual_fe_err.txt`, `arkaim-web/_manual_fe_out.txt`;
- `src/` (13 файлов) — **устаревшая копия** `arkaim-web/src/shared/api/contracts/`: 10 файлов идентичны tracked, 3 (`knowledge.ts`, `temporal.ts`, `world.ts`) отличаются тем, что в них **нет** поздних блоков (в т.ч. нет M8/M9 `KnowledgeTrace`) → это старая ревизия, не актуальный контракт; корневого `package.json`/`tsconfig.json` нет, ничего на `src/` не ссылается;
- `runtime/_diag_answers.py`, `runtime/forensic_*.txt`, `runtime/m10_*.txt` (diag-выводы) — если владелец не хочет хранить audit-артефакты (иначе → раздел C).

**C. Требуют отдельного решения владельца:**
- `docs/archive/` — 117 файлов (completed/frontend/historical/md-line/subsystems/temporal);
- `runtime/xray_dashboard/` — 4 файла, **используется бэкендом** (`runtime/core/main.py:447` монтирует `/_ui/admin`) → фактический runtime-asset, рекомендую track;
- `SCHEMAS/` (5 JSON), `scripts/` (26), `notebooks/` (1), `arkaim-mobile/` (30);
- `tests/` (корень, 10 файлов) — **настоящие тесты** `core/CORE/visual/*` (atmosphere/camera/continuity/location/symbol/validator и др.), но вне `runtime/tests` и вне testpaths → сейчас не собираются pytest'ом; решение: перенести/подключить или не хранить;
- `runtime/run-all.ps1`, `runtime/stop-all.ps1`, `runtime/world_engine_demo.html`, `runtime/world_visualization.html`, `runtime/check_*.py`, `runtime/m10*_audit_checks.py|txt`, `runtime/m10_*.txt` (audit-доказательства M10/M10.2);
- `core/run_api.py`, `core/run_extractor.py`, `core/run_index_book.py`, `core/run_index_book_v2.py`;
- **`core/.gitignore` — новый, меняет ignore-правила** (не включать без явного решения);
- `core/CORE/genome/history/genome_v1.0.0_*.json` (9 снимков) и **modified `core/CORE/genome/history/index.json`** — genome-данные; `index.json` изменён побочным эффектом `Pulse.load()` → в genome-область (вне scope H1) без GO не коммитить;
- `.kilo/` (7), `.clinerules/`, `kilo.json` — конфиги AI-инструментов (секретов нет);
- `АУДИТ.md`, `АУДИТ_ARKAIM.md`, `IMAGE_DESCRIPTION_FORENSIC_ANALYSIS.md` (корень).

**D. Нельзя трогать (без отдельного GO):**
- **D-файлы/D-находки** — точный набор не подтверждён владельцем; кандидаты `docs/DEPLOY.md`, `docs/DOCUMENTATION_INVENTORY.md`, `docs/DOCUMENTATION_INDEX.md` — содержимое не редактировать до подтверждения;
- утверждённые контракты: `core/CORE/evidence/*` (M2), `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`, WorldModel/Temporal, M10-gate, утверждённые `SCHEMAS/`, `docs/ADR/*`;
- секреты: `.env` (в gitignore — не добавлять, не выводить);
- существующие данные: `runtime/runtime_data/*`, `core/KNOWLEDGE/*` — не перезаписывать, не удалять;
- удаление файлов «для чистоты» — только по решению владельца (в рамках T2 ничего не удаляется).

**STOP снят GO-9 (2026-10-11):** commit выполнен по составу, подтверждённому владельцем (см. OWNER-GO выше).


### T3 — Фиксация GO-free семантик
- **Статус:** DONE (2026-10-11, HEAD `1e3f812`)
- **Цель:** документально описать фактическое поведение `search.total` и `uncertainty.has_unknowns`.
- **GAP:** SoT/OpenAPI поведение не описывают (live PROBLEM №3/№4, классифицированы addendum'ом как GO-free).
- **Что сделано:**
  1. **Диагностика реальными сценариями** (только чтение, `TestClient` против `core.main.app`; временные скрипты вне репозитория): поиск — 11 комбинаций `q`/`limit` (аркаим×4 лимитов, мир×2, город, богиня, «Аркаимская долина», несуществующий `q`, пустой `q` → 422) + проверка `total==len`/`total<=limit`/префиксности страниц; неопределённость — 15 сущностей (полные, частичные, археологические, несуществующие), включая сверку `trace.uncertainty == card.uncertainty` и round-trip `search→card`.
  2. **Документация в SoT** — новый подраздел «Фактическая семантика `search.total` и `uncertainty.has_unknowns`» в `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` (M8): таблицы фактических результатов, источники и лимиты, `book/arch` claims, HTTP-коды, оговорки о независимости от evidence-статусов и `trace.status`.
  3. **Docstring в OpenAPI** — `runtime/core/routes/knowledge_cards.py`: в `search_entities` описана семантика `total` (страница, не глобальный счётчик; археологический добор без фильтра по `q`), в `get_knowledge_card` — семантика `uncertainty.has_unknowns` (card-level `bool(unknown_aspects)`, 4 источника, 404 на карточке vs 200/PARTIAL в trace).
- **Зафиксированные факты (кратко):** `search.total = len(entities) ≤ limit` (нет offset, нет глобального счётчика; добор из `ARCHAEOLOGY.json` не фильтрует по `q` — при нуле совпадений вернётся ≤limit археологических сущностей); `has_unknowns = bool(unknown_aspects)` по 4 card-level источникам (нет сущности / нет book claims / нет arch claims / `unsolved` — последний по данным `WORLD_MODEL` не срабатывает: 0 сущностей с `unsolved`); **не зависит** от статусов evidence и `trace.status` (у `region_arkaim` 7 `UNKNOWN` evidence при `has_unknowns=false`); round-trip неполный — 4 из 14 `entity_id` при `q=аркаим&limit=50` дают 404 на карточке.
- **Tests/проверки:** тот же состав baseline-набора из T1b (20 файлов, M7 = `test_m7_temporal_correction_lineage.py`) — **333 collected / 333 passed / 0 failed** после правок; `git diff --check` — чисто (exit 0, только CRLF-предупреждения git). Побочно: прогон с `test_m7_epoch_visual.py` вместо correction_lineage даёт 337/337 (другой файл M7, тот же результат — зелёный).
- **Изменённые файлы:** `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md` (SoT, +подраздел M8), `runtime/core/routes/knowledge_cards.py` (**только docstring, +14 строк, синтаксис проверен `ast.parse`**), настоящий roadmap. Поведение endpoint-ов, response-схемы и тесты не менялись.
- **Acceptance:** ✅ документированное поведение совпадает с фактическим (формулировки сверены с кодом `knowledge_cards.py:34-103`, `builder.py:621-756` и с диагностикой); ни один endpoint и ни один тест не изменены; baseline 333/333 зелёный.
- **OWNER-GO:** не требуется (изменение поведения не выполнялось). Новые наблюдения (неполный round-trip `search→card`, археологический добор без фильтра по `q`) — кандидаты в OWNER-GO при решении что-либо менять.

### T4 — Явный claim ↔ evidence join
- **Статус:** DONE (2026-10-11, HEAD `1e3f812`)
- **Цель:** evidence-строки trace несут `claim_id` через уже существующий механизм identity.
- **GAP:** M2-acceptance «claim указывает evidence ID либо `evidence_status=UNKNOWN`» держится на неявном join по `source_ref`.
- **Что сделано:** в `_evidence_projection` (`runtime/core/routes/knowledge_cards.py`) каждая evidence-строка получает поле `claim_id`, вычисляемое тем же мостом `_card_claim_id(claim)`, что и в claims-секции trace: `"claim_id": _card_claim_id(claim)` (+1 строка). Docstring `_evidence_projection` дополнен описанием семантики. Изменение строго additive: добавлен один ключ в dict-строку `list[dict[str, Any]]`; DTO `KnowledgeTraceResponse`, M2-схемы, статусы, namespace policy, fail-closed, `_trace_lineage`, `_evidence_resolver`, WorldModel/Temporal/crosswalk не изменялись.
- **Семантика (зафиксирована):** `claim_id` в evidence-строке **тот же**, что в claims-строке той же claim (обе секции используют один bridge); при невозможности достоверно установить соответствие — `null` (нет text, нет chunk_id у `book:`, схема вне `book:`/`ARCHAEOLOGY.json:`/`external:`, в т.ч. `genome:`/`world_model:`); статус резолвера (RESOLVED/UNAVAILABLE/UNKNOWN) на identity не влияет и из него не выводится; строки без `source_ref`/`chunk_id` по-прежнему не проецируются (fabrication отсутствует).
- **Targeted regression (новое):**
  1. `test_m8_knowledge_trace_api.py::test_evidence_row_carries_the_same_claim_id_as_the_claim` — book claim (text+chunk, RESOLVED): `claim_id` в evidence == `_card_claim_id(claim)` == `CanonClaim.make_id(...)` claims-секции;
  2. `...::test_evidence_claim_id_is_independent_of_resolution_status` — RESOLVED (id есть), UNAVAILABLE (`evidence_id=None`, `claim_id` сохраняется), UNKNOWN без chunk → `claim_id=null` (fail-closed, статус не создаёт identity);
  3. `...::test_evidence_row_exposes_claim_id_for_external_archaeology_ref` — `ARCHAEOLOGY.json:sinta_sha` → `CanonClaim.make_id(text, "archaeology", "external:archaeology:sinta_sha")`;
  4. `...::test_evidence_claim_id_stays_null_without_reliable_bridge` — `genome:theme:…`, `world_model:…`, `book:` без chunk, claim без text → все `claim_id=null`, строки при этом остаются (4/4);
  5. `test_m8c_trace_journey.py::test_evidence_claim_ids_reuse_the_claims_section_identity` — реальный `region_arkaim`: множество `claim_id` из evidence ⊆ claim-секции, все book-строки имеют id и равны claims-строке по `source_ref`, неподдерживаемые ref (`world_model:` и др.) → `null`.
- **Tests/проверки:** M8-набор (trace/api/b/c/present-anchor/future-extrapolation) + knowledge_cards — **118 passed**; baseline 20 файлов — **333 → 338 collected/passed / 0 failed** (5 новых тестов); `git diff --check` — чисто (exit 0). Линт `ruff` недоступен в окружении — не выполнялся.
- **Изменённые файлы (diff = только additions, 0 удалений):** `runtime/core/routes/knowledge_cards.py` (+21: 14 строк T3-docstring + 6 строк T4), `runtime/tests/test_m8_knowledge_trace_api.py` (+113, 4 теста), `runtime/tests/test_m8c_trace_journey.py` (+24, 1 тест). Постороннее переоформление файлов инструментом правок устранено: файлы откачены к HEAD и правки нанесены повторно без форматтера.
- **Acceptance:** ✅ book/external claims несут одинаковый `claim_id` в обеих секциях; без bridge — `null`; fabricated id нет; статусы/namespace/fail-closed/контракты M2/M8 не изменены; targeted regression и baseline зелёные.
- **OWNER-GO:** не потребовался — изменение осталось в additive-read-only границах T4.


### T5 — Синхронизация frontend trace contract + lineage UI
- **Статус:** DONE (2026-10-11)
- **Цель:** frontend-потребитель соответствует уже существующему backend DTO; lineage виден в UI.
- **GAP был:** `contracts/knowledge.ts` не содержал `lineage`, `totals`, `offset/limit/next_offset`; `KnowledgeTraceCard` lineage не рендерил; у карточки не было состояний загрузки/ошибки.
- **Что сделано (только frontend, backend не менялся):**
  1. `src/shared/api/contracts/knowledge.ts` — типы синхронизированы с `runtime/core/dto/knowledge.py::KnowledgeTraceResponse`: добавлены `KnowledgeTraceEvidence` (включая `claim_id` из T4), `KnowledgeTraceLineageLink`/`KnowledgeTraceEvidenceLink`/`KnowledgeTraceCorrectionLink` (структура `_trace_lineage`), `KnowledgeTraceTotals`, поля `lineage?`, `offset`, `limit`, `totals`, `next_offset` в `KnowledgeTrace`; `getKnowledgeTrace(entityId, query?)` теперь передаёт `offset`/`limit` как query-параметры (как принимает backend); существующие вызовы без параметров не изменились.
  2. `src/shared/ui/KnowledgeTraceCard.tsx` — новые пропсы `loading`/`error` (приоритет: error → loading → нет trace → данные); секция **Lineage** (записи `details/summary` с claim/evidence/reasoning/corrections-связями; пусто → «Данных нет»; поле отсутствует в ответе → «Lineage отсутствует в ответе»); блок **totals + pagination** (6 полей totals и `offset/limit/next_offset`, неполный ответ не ломает рендер); `claim_id` показывается в evidence-строке claim-деталей (только когда строка).
  3. `src/app/world-engine/page.tsx` — состояния `knowledgeTraceLoading`/`knowledgeTraceError` вокруг `getKnowledgeTrace`, передаются в карточку (ошибка больше не выглядит как «не загружена»).
- **Tests (новые/обновлённые, разные сущности в каждом сценарии):** `tests/unit/knowledge-trace-card.test.tsx` — 11 тестов: полный рендер + lineage + totals/pagination (`region_arkaim`), loading, error, honest missing state, пустой ответ (`archaeology:мехенго`), отсутствие `lineage` в ответе (`arkaim_settlement`), следующая страница (`geo_гардарика`), неполный ответ без `totals`/`next_offset`/`lineage` (`lang_гардарикия`), не-мутация входа; новый `tests/unit/knowledge-contract.test.ts` — 3 теста `getKnowledgeTrace` (без параметров / `offset=50&limit=10` / только `offset`) через мок `apiCall`.
- **Пройденные проверки:** `npx vitest run` — **84/84 passed (16 файлов)**; `npm run lint` — **0 errors** (77 pre-existing warnings, ни одного в затронутых файлах); `npm run build` (production, включает type-check) — **exit 0**. Холодный первый полный прогон дал таймаут `pages.test.tsx::renders GenresPage` (9.5s из 15s лимита на прогреве импорта) — на повторном прогоне и отдельно проходит; GenresPage не зависит от knowledge-файлов.
- **Acceptance:** ✅ типы соответствуют backend-DTO; lineage виден при наличии связей и честно помечен при отсутствии; состояния loading/error/empty/filled/без lineage/неполный ответ обработаны; frontend regression зелёный; backend, M2/M8-семантика, статусы, namespace, WorldModel/Temporal/crosswalk не менялись.
- **OWNER-GO:** не потребовался.
- **Факт: H1 завершён и зафиксирован** — T1 ✅, T1b/GO-8 ✅, T3 ✅, T4 ✅, T5 ✅, T2/GO-9 ✅ (commit 2026-10-11). **STOP достигнут** — дальше только §4 OWNER-GO.

**После T5 — STOP.** Далее только §4 OWNER-GO.

---

## 4. OWNER-GO (ждёт решения владельца)

| ID | Вопрос | Состояние |
|---|---|---|
| GO-1 | **`trace.status`:** когда `COMPLETE`, когда `PARTIAL`, нужен ли отдельный `UNKNOWN`, что делать при `UNKNOWN` evidence (правило перевода). | **DECIDED + EXECUTED 2026-10-11 (H2-A):** `COMPLETE` ⇔ есть claims ∧ все evidence-строки `RESOLVED` ∧ нет `limitations`; иначе `PARTIAL` (обрыв пути); `UNKNOWN` — зарезервирован, не выдаётся; статус считается по полному набору evidence (до секционных фильтров/пагинации). Правило в docstring trace; +3 unit-теста, journey-правило обновлено; live `region_arkaim` → `PARTIAL` |
| GO-2 | **HTTP 422:** envelope `error.code=HTTP_422` или оставить `detail`; объём (все routes vs knowledge routes); какой frontend contract обновлять. | **DECIDED + EXECUTED 2026-10-11 (H2-A):** envelope `{"ok":false,"error":{"code":"HTTP_422","message","details":[{loc,msg,type}]}}`; объём — **все routes** (глобальный `RequestValidationError`-handler рядом с `HTTPException`-handlerом в `main.py`); frontend contract обновлять не потребовалось — `errors.ts::parseErrorBody` уже парсит envelope (`ApiErrorCode = HTTP_${number}`); 6 новых тестов |
| GO-3 | **M3/M4 read path:** разрешение подключить typed резолверы (`world_resolver`, `temporal_resolver`) к read API. | OPEN — код не менять |
| GO-4 | **Production M5/M6/M7:** триггер conflict detection; триггер reasoning; production persistence; M10 findings → M7 correction proposals; влияние на `KnowledgeCard.contradictions`. | OPEN — код не менять |
| GO-5 | **Claim identity policy:** расширять ли allowlist на `genome:`, `world_model:`, `CROSS_REFERENCES.json` — либо fail-closed становится постоянной политикой. | OPEN — код не менять |
| GO-6 | **M9 Phase 2:** отдельный Knowledge route / mutation-proposal UI / роли. | OPEN — код не менять |
| GO-7 | **Ask/RAG:** разрешается ли менять `/book/ask` для выдачи `claim_id` / `evidence_id`. | OPEN — код не менять |
| GO-8 | **BASELINE-1 (правило ликвидации падения `test_no_duplicate_claims`):** A) фильтровать genome-fallback в `_book_claims` (не принимать `source == "genome"` как book evidence — соответствует докстрингу `_genome_claims` и требованию `test_knowledge_cards.py:250`; book claims теряют genome-текст, но он остаётся в источнике `genome` DERIVED) — рекомендуется; B) дедупликация текста между источниками после агрегации; C) признать обе копии валидными и поправить тест. Меняет фактический состав AUTHOR_CANON book claims в production-карточках. | **DECIDED + IMPLEMENTED 2026-10-11** — выбран вариант A; фикс в T1b, baseline 333/333 |
| GO-9 | **Состав commit (T2):** подтвердить композицию: (1) minimum — A-list (18 untracked knowledge-документов, §3 T2) + изменённый `docs/CURRENT_DEVELOPMENT_STATE.md`; (2) включить ли `docs/archive/` (117 файлов); (3) включать ли runtime-asset `runtime/xray_dashboard/` (рекомендую — монтируется `runtime/core/main.py:447`); (4) track/untrack: `SCHEMAS/`, `scripts/`, `notebooks/`, `arkaim-mobile/`, корневой `tests/` (настоящие тесты `core/CORE/visual/*`, сейчас pytest'ом не собираются), корневой `src/` (рекомендую **не** добавлять — устаревшая копия контрактов), `.kilo/`+`kilo.json`; (5) `core/.gitignore` (меняет ignore-правила), genome-снимки и modified `core/CORE/genome/history/index.json`; (6) добавлять ли junk в `.gitignore` и удалять ли его. **Commit не выполняется без явного GO.** **DECIDED + EXECUTED 2026-10-11** — состав подтверждён владельцем: включить A-list (18 документов) + код/тесты H1 + `runtime/xray_dashboard/` + `AGENTS.md` + junk-паттерны в `.gitignore` (без удаления файлов); НЕ включать `docs/archive/`, прочие наборы (SCHEMAS/scripts/notebooks/корневой tests/core-run/runtime-утилиты/`core/.gitignore`/AI-конфиги), genome-снимки и modified `index.json`; commit выполнен |

**Процедурные (не архитектурные):** композиция commit (GO-9); состав untracked-путей (`SCHEMAS/`, `scripts/`, `notebooks/`, `arkaim-mobile/`, корневой `tests/` — 10 файлов, не «пустой», корневой `src/` — устаревшая копия, мусорные логи); объём mojibake-фикса (3 файла: `GEOGRAPHY.json` / `MAP_DATA.json` / `CROSS_REFERENCES.json` — только затронутые сущности или всё; `name`/`description` участвуют в retrieval-путях M8f).

**Правило после GO:** зафиксировать решение в roadmap → выполнить только соответствующий следующий этап → targeted tests → acceptance → обновить roadmap → показать результат → переходить дальше только при наличии разрешения. Не объединять несколько GO в одну реализацию.

---

## 5. HORIZON 2 (после GO)

- **H2-A — GO-1 + GO-2:** семантика статуса trace + единый формат ошибок. Acceptance: live `region_arkaim` не отдаёт `COMPLETE` при оборванном пути по принятому правилу; ошибки одного формата; regression зелёный. **✅ ВЫПОЛНЕНО 2026-10-11** (TestClient против `core.main.app` на реальных данных: `region_arkaim` → `PARTIAL`; 422 → envelope `HTTP_422`; 404/200 без регрессий; baseline 341/341).
- **H2-B — GO-4:** production-производители M5/M6/M7 + связь с M10. Acceptance: записи в `runtime/runtime_data/knowledge/`; trace возвращает conflicts/reasoning/corrections/lineage > 0 на реальных данных; M10 остаётся единственной mutation-границей WorldModel; HYPOTHESIS не повышается.
- **H2-C — GO-3:** typed M3/M4 в read path. Acceptance: trace отдаёт typed refs со статусами `RESOLVED/UNRESOLVED/AMBIGUOUS` и time-basis; crosswalk/WorldModel/M10 не изменяются.
- **H2-D — GO-5 (+ GO-free часть):** покрытие claim identity + item-level DTO schemas. Acceptance: покрытие расширено и протестировано либо политика задокументирована; элементы секций валидируются типами.
- **H2-E — GO-6 + GO-7:** Ask/RAG IDs, отдельный Knowledge route, read/propose UI, browser e2e. Acceptance: пользователь проходит полную traceability chain; UI не создаёт authority; e2e зелёный; World/Temporal не регрессируют.

Порядок H2: A → B → C → D → E (A даёт честный статус до UI; B наполняет lineage; C/D укрепляют контракты; E — потребители).

---

## 6. HORIZON 3 — TARGET STATE

- Каждый существенный claim имеет устойчивый identity (или явно задокументированное fail-closed исключение), явную связь с evidence, resolver-статус `RESOLVED/UNAVAILABLE/UNKNOWN`, раздельные provenance/confidence, typed world/temporal refs и при наличии — lineage.
- В production существуют и связаны записи M5 (conflicts), M6 (reasoning с ordered inputs), M7 (correction lineage от M10 findings); live-верификация показывает непустую цепочку claim → evidence → source → entity/event → conflict/reasoning/correction → lineage.
- `trace.status` отражает §2.5 SoT; ошибки одного формата; `search.total` и `uncertainty` описаны так, как работают.
- Стабильный read/query contract с item-level схемами; Ask/RAG отдаёт claim/evidence IDs; отдельный Knowledge route + read/propose UI; browser e2e покрывает полный путь.
- Knowledge-документы и baseline в git; targeted regression с пересчитанными числами; production-хранилище M5/M6/M7 не пустое.
- Неизменны: WorldModel, Temporal, crosswalk, M10-gate, M2 contract (без нового GO).

---

## 7. DEVELOPMENT MAP

```
T1 re-baseline тестов ──► T2 git-фиксация baseline (STOP на GO состава)
        │                          │
        └────────► T3 GO-free семантики ◄── параллельно
                   │
        T4 явный claim↔evidence join ──► T5 frontend contract + lineage UI
                   │
                 STOP  ──►  OWNER-GO (GO-1…GO-7)
                   │
   GO-1/GO-2 ─► H2-A ─┐
   GO-4      ─► H2-B ─┼─► GO-3 ─► H2-C ─► GO-5 ─► H2-D ─► GO-6/GO-7 ─► H2-E ─► H3
```

Причины порядка: без T1 статусы «TESTED» непроверенные; без H2-A UI/e2e закрепят неверную семантику; без H2-B lineage остаётся тестовой фикцией; H2-E без A/B превратит пустую и неверно окрашенную цепочку в пользовательский контракт.

---

## 8. RISKS / UNCERTAINTIES

**Подтверждённые факты**
- SoT-план и live-отчёт не в git; в git только 25 из 175 docs — риск потери источника истины.
- Числа тестов в SoT не пересчитывались после `93272cf` и `1e3f812`.
- `runtime/runtime_data/knowledge/` существует и пуст → live-доказательство conflicts/reasoning/corrections/lineage невозможно без production-записей.
- Production-писателей M5/M6/M7 и M2 evidence/link-репозиториев нет (чтение в route + запись в тестах).
- M3/M4 typed резолверы используются только в тестах.
- Frontend-контракт trace отстаёт от backend-DTO; knowledge e2e-спеки нет.
- `pyproject.toml` в корне отсутствует (конфиг — `runtime/pyproject.toml`), вопреки `AGENTS.md`.

**Неизвестные**
- **«D-файлы»** — однозначного набора не найдено (кандидаты: D-prefixed docs `DEPLOY.md`/`DOCUMENTATION_*`; D-класс находки D-5/D-7/D-10; D-F4-* решения). Ограничение применено буквально: ни одна задача не трогает файлы/находки с меткой D; включая `DOCUMENTATION_INDEX.md` до уточнения.
- **«Knowledge Core A/B»** — термин в документации не встречается; ближайшие фактические соответствия — bridge-этапы M8h/M8i и документы A1/A1R. Требуется подтверждение владельца.
- **Состав untracked-путей** — какие из `SCHEMAS/`, `scripts/`, `notebooks/`, `arkaim-mobile/`, `tests/` должны быть в git.
- Цифры из прежних отчётов (1788 passed / 26 skipped / 19 failed; frontend 70/70) не перепроверялись до T1.

---

## 9. ЖУРНАЛ РЕАЛИЗАЦИИ

| Задача | Статус | Дата | Результат |
|---|---|---|---|
| Roadmap создан | DONE | 2026-10-11 | настоящий документ |
| T1 re-baseline | DONE | 2026-10-11 | HEAD `1e3f812`, 330 collected / 329 passed / **1 failed** (BASELINE-1 → GO-8); `CURRENT_DEVELOPMENT_STATE.md`, SoT-план и roadmap обновлены |
| T1b GO-8 фикс BASELINE-1 | DONE | 2026-10-11 | фильтр `source == "genome"` в `_book_claims`; +3 targeted tests; **T1-targeted regression 333 collected / 333 passed / 0 failed**; контракты M2/M8 не менялись; найден NEW-1 (не исправлялся) |
| T2 git baseline | DONE | 2026-10-11 | списки A/B/C/D подготовлены (§3 T2); **GO-9 получен**: состав подтверждён (A-list + код/тесты H1 + xray_dashboard + AGENTS.md + junk → .gitignore без удаления; archive/прочие наборы/genome — нет); **commit выполнен** — см. `git log` |
| T3 GO-free семантики | DONE | 2026-10-11 | семантики `search.total` и `uncertainty.has_unknowns` зафиксированы: подраздел в SoT (M8) + docstring двух endpoint-ов (`knowledge_cards.py`, +14 строк только описания); диагностика 11 сценариями поиска и 15 сущностями; baseline **333/333**, `git diff --check` чисто; поведение/схемы/тесты не менялись; наблюдения: неполный round-trip `search→card` (4/14 → 404), археологический добор без фильтра по `q` |
| T4 claim↔evidence join | DONE | 2026-10-11 | `"claim_id": _card_claim_id(claim)` в `_evidence_projection` (additive, 0 удалений); 5 targeted tests (4 unit + 1 journey на реальном `region_arkaim`); M8-набор 118 passed; **baseline 333 → 338 passed / 0 failed**; `git diff --check` чисто; M2/M8-контракты, статусы, namespace, fail-closed не менялись; постороннее переоформление файлов устранено откатом к HEAD |
| T5 frontend contract + lineage | DONE | 2026-10-11 | типы `knowledge.ts` синхронизированы с `KnowledgeTraceResponse` (lineage/totals/offset/limit/next_offset/evidence `claim_id`) + `getKnowledgeTrace` с query `offset`/`limit`; `KnowledgeTraceCard`: пропсы `loading`/`error`, секция Lineage (filled/empty/missing), блок totals+pagination, `claim_id` в evidence-строке; `world-engine/page.tsx`: состояния загрузки/ошибки; 14 тестов (11 card + 3 contract, разные сущности); **vitest 84/84, lint 0 errors, `next build` exit 0**; backend не менялся |
| H2-A GO-1 + GO-2 | DONE | 2026-10-11 | **GO-1:** правило `trace.status` (COMPLETE ⇔ есть claims ∧ все evidence `RESOLVED` ∧ нет `limitations`; иначе `PARTIAL`; `UNKNOWN` зарезервирован; по полному набору evidence до секционных фильтров) — docstring trace + `evidence_unresolved` в `knowledge_cards.py`; +3 unit-теста (включая live-кейс UNKNOWN), journey-правило обновлено; **live `region_arkaim` → `PARTIAL`** (17 RESOLVED + 7 UNKNOWN, limitations пусты — раньше COMPLETE). **GO-2:** глобальный `RequestValidationError`-handler в `main.py` → envelope `HTTP_422` с `details` (все routes); 401/404/500 без изменений; фронт без правок; 6 новых тестов. **baseline 338 → 341 passed / 0 failed** (+ отдельный `test_error_envelope_422.py` 6 passed; `test_md3_route_a` 11 passed); vitest **84/84**; acceptance TestClient OK; `git diff --check` — см. отчёт; **commit не выполнялся (нет явного GO)** |
