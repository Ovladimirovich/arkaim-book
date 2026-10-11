# Knowledge Core — LIVE VERIFICATION (read-only)

**Дата:** 2026-10-02
**HEAD:** `1e3f812` (fix(knowledge): restore derived genome card projection)
**Режим:** read-only, production-код не изменён, Source of Truth не редактировался, pytest не запускался
**Среда:** backend `uvicorn core.main:app --port 8642` (PID 11368, `.venv` Python 3.14), остановлен по завершении; порт 8642 освобождён
**Клиент:** curl + reader-сессия, полученная через `POST /auth/dev/generate-token` (role=reader) → `POST /auth/telegram/login` → cookie `arkaim_session`
**Сырые ответы:** `%TEMP%\opencode\live\*.json` (card/trace/filters/pagination по каждому entity)

**ИТОГ: PARTIAL** — весь заявленный read-only контур (auth, search, card, trace, фильтры, пагинация, evidence-status) подтверждён live; секции conflicts / reasoning / corrections / lineage подтвердить live невозможно (хранилища пусты), плюс найдены 2 расхождения фактического поведения с контрактными формулировками плана.

---

## 1. ENDPOINTS

### 1.1 Auth / 401 (все три endpoint-а без токена)

| Запрос | HTTP | Ответ |
|---|---|---|
| `GET /knowledge/cards/search?q=Аркаим` | **401** | `{"ok":false,"error":{"code":"HTTP_401","message":"…"}}` |
| `GET /knowledge/cards/region_arkaim` | **401** | то же |
| `GET /knowledge/cards/trace/region_arkaim` | **401** | то же |

С cookie reader-сессии все три отвечают 200. Разделы 401 работают одинаково.

### 1.2 `GET /knowledge/cards/search`

| Запрос | HTTP | Факт |
|---|---|---|
| `q=Аркаим&limit=10` | 200 | `total=10`, 10 entities (WorldEngine: `arkaim_settlement`, `civ_arkaim_civilization`, `geo_…`, `lang_…` + `archaeology:…`) |
| `q=народ`, `q=город`, `q=миф` (limit=10) | 200 | `total=10` у каждого, реальные данные |
| `q=Аркаим&limit=3` | 200 | `total=3`, entities=3 → **`total` = размер страницы, а не глобальное число совпадений** |
| `q=` (пустой) | 422 | FastAPI `string_too_short` |
| без `q` | 422 | `missing` |
| `q`=101 символ | 422 | `string_too_long` |

### 1.3 `GET /knowledge/cards/{entity_id}`

| entity_id | HTTP | Факт |
|---|---|---|
| `region_arkaim` | 200 | 23 604 байт; `sources`=6, `relations`=5, `contradictions`=0, `related_entities`=19 |
| `arkaim_settlement` | 200 | 13 693 байт |
| `civ_arkaim_civilization` | 200 | 15 541 байт |
| `geo_меридиан_аркаима` | 200 | 25 410 байт |
| `lang_энергетика_аркаима` | 200 | 14 420 байт |
| `archaeology:синташта` | 200 | 8 875 байт |
| `archaeology:аркаим` | 200 | 200, `primary_entity` присутствует |
| `nonexistent_live_check_xyz` | **404** | `{"ok":false,"error":{"code":"HTTP_404","message":"Entity 'nonexistent_live_check_xyz' not found in any knowledge source"}}` |

Состав источников карточки `region_arkaim`: `book:AUTHOR_CANON (5)`, `genome:DERIVED (1)`, `world_model:DERIVED (1)`, `archaeology:EXTERNAL_SOURCE (13)`, `cross_references:DERIVED (5)`, `academic:EXTERNAL_SOURCE (0, summary "0 академических подтверждений", confidence 0.0)` → сумма 25 claims.

### 1.4 `GET /knowledge/cards/trace/{entity_id}`

Все реальные entity → **200**; `nonexistent_live_check_xyz` → **200, `status=PARTIAL`** с честными `uncertainty.unknown_aspects` (3 пункта) и `limitations` (в т.ч. "World entity not resolved").

| entity_id | status | totals (claims/evidence/conflicts/reasoning/corrections/lineage) |
|---|---|---|
| `region_arkaim` | COMPLETE | 25 / 25 / 0 / 0 / 0 / 0 |
| `arkaim_settlement` | COMPLETE | 20 / 20 / 0 / 0 / 0 / 0 |
| `civ_arkaim_civilization` | COMPLETE | 21 / 21 / 0 / 0 / 0 / 0 |
| `geo_меридиан_аркаима` | COMPLETE | 19 / 19 / 0 / 0 / 0 / 0 |
| `lang_энергетика_аркаима` | COMPLETE | 20 / 20 / 0 / 0 / 0 / 0 |
| `archaeology:синташта` | COMPLETE | 12 / 12 / 0 / 0 / 0 / 0 |
| `nonexistent_live_check_xyz` | PARTIAL | 0 / 0 / 0 / 0 / 0 / 0 |

**Pagination** (`region_arkaim`):
- `limit=1` → 200, страница 1/1, `next_offset=1`, `totals.claims=25`
- `limit=1&offset=1` → 200, `next_offset=2`, первая claims-страница = `claim_17f6d1b8e567`
- `limit=101` → **422** (`Input should be less than or equal to 100`)
- `limit=0` → **422**
- `offset=9999` → 200, пустые секции, `totals` без изменений

**Фильтры** (`region_arkaim`, `limit=50`):

| Фильтр | HTTP | claims | evidence | totals |
|---|---|---|---|---|
| `claim_category=AUTHOR_CANON` | 200 | 5 | 25 | 25/25/0/0/0/0 |
| `claim_category=HYPOTHESIS` | 200 | 2 | 25 | без изменений |
| `claim_category=EXTERNAL_SOURCE` | 200 | 10 | 25 | без изменений |
| `claim_category=GARBAGE` | 200 | 0 | 25 | без изменений (нет ошибки и нет fabrication) |
| `evidence_status=RESOLVED` | 200 | 25 | 17 | без изменений |
| `evidence_status=UNAVAILABLE` | 200 | 25 | 1 | без изменений |
| `evidence_status=UNKNOWN` | 200 | 25 | 7 | без изменений |
| `evidence_status=NOT_A_STATUS` | 200 | 25 | 0 | без изменений |
| `conflict_status=UNRESOLVED` / `correction_status=PENDING` / `reasoning_status=RESOLVED` | 200 | 25 | 25 | 0/0/0 (секции пусты) |
| `claim_category=EXTERNAL_SOURCE&limit=3` | 200 | 3, `next_offset=3` | — | 25 |
| `…&offset=3` | 200 | 3, `next_offset=6`, все 3 = `EXTERNAL_SOURCE` | — | 25 |
| `evidence_status=UNKNOWN&limit=3` | 200 | — | 3, `next_offset=3`, все `UNKNOWN` | 25 |

Поведение `totals` подтверждает контракт M8: **totals всегда полный нефильтрованный размер цепочки, фильтры и пагинация сужают только содержимое страницы.**

---

## 2. TRACEABILITY (claim → evidence → source → world → temporal → lineage)

Подтверждено live для 7 entity:

1. **Claim → source:** каждый claim несёт `provenance.category`, `source_level`, `confidence`, `source_title`, `source_ref`, `chunk_id`. Пример (`region_arkaim`): `book:chunk_p_0001_16fc149672e4`, `AUTHOR_CANON`, `confidence=1.0`, `source_title="Наследие Аркаима"`.
2. **Claim ID:** формат `claim_<sha256[:12]>` — совпадает с `CanonClaim.make_id` (`core/CORE/narrative_engine/provenance/claim.py:104-107`).
   - `region_arkaim`: ID есть у **18 из 25** claims; без ID — ровно те claims, у которых `source_ref` = `genome:…`, `world_model:…`, `CROSS_REFERENCES.json:…` (fail-closed, guessed ID не выдаётся — соответствует M8h).
   - `archaeology:синташта`: ID у **8 из 12**; категории `DERIVED=4, EXTERNAL_SOURCE=7, RECONSTRUCTION=1`.
   - Дубликатов non-empty ID нет (18/18 и 8/8 уникальны).
3. **Категории claims (`region_arkaim`, 25):** `AUTHOR_CANON=5, DERIVED=7, EXTERNAL_SOURCE=10, RECONSTRUCTION=1, HYPOTHESIS=2`. Гипотезы не повышены до canon.
4. **Claim → evidence:** `evidence` построен 1:1 к claims по `source_ref`/`chunk_id` (25 строк = 25 claims, `distinct source_ref`=25). Строки evidence **не содержат `claim_id`** — join выполняется неявно по `source_ref`/`chunk_id`.
5. **Evidence → resolver status:** `RESOLVED` строки несут `evidence_id` (напр. `evidence_29648d07d7e1bab9`), `UNAVAILABLE`/`UNKNOWN` — `evidence_id=null` + `reason`. Fabricated строк нет.
6. **World:** `world` заполнен (`primary_entity`) у всех 6 реальных entity: id/name/description/properties/relationships. Для `region_arkaim` поля `name`/`name_ru`/`description` содержат mojibake (`"РђСЂРєР°РёРј"`) — это уже описано в плане (M8f) и не устранено.
7. **Temporal:** у каждой entity ровно 1 запись вида `{"claim_ref":"world_model:<id>:description","status":"PROJECTED_FROM_WORLD_REF"}`. Типизированные temporal refs (event/era/node/precision/bounds) live не отдаются.
8. **Lineage:** поле `lineage` присутствует, но `count=0` у всех entity — см. §3.

---

## 3. EVIDENCE STATUS (фактические распределения)

| entity_id | RESOLVED | UNAVAILABLE | UNKNOWN |
|---|---|---|---|
| `region_arkaim` | 17 | 1 | 7 |
| `arkaim_settlement` | 17 | 1 | 2 |
| `civ_arkaim_civilization` | 16 | 2 | 3 |
| `geo_меридиан_аркаима` | 16 | 1 | 2 |
| `lang_энергетика_аркаима` | 17 | 1 | 2 |
| `archaeology:синташта` | 8 | 0 | 4 |

Примеры:

- **RESOLVED (book):** `book:chunk_p_0001_16fc149672e4` → `evidence_29648d07d7e1bab9`, `source_title="Наследие Аркаима"`.
- **RESOLVED (external, M8j registry):** `ARCHAEOLOGY.json:синташта:location` → `evidence_de25ca37478a19f4`; всего 8 таких строк (`location`, `dating`, `facts.*`, `book_connection`, `significance`).
- **UNAVAILABLE:** `book:genome_theme_theme_129` → `evidence_id=null`, `reason="chunk not found in source: genome_theme_theme_129"` ( genomе-выведенная строка, честно недоступная — соответствует M8f).
- **UNKNOWN:** `genome:theme:theme_129` → `reason="unsupported locator format: genome:theme:theme_129"`; `world_model:region_arkaim:description` → `unsupported locator format`; `CROSS_REFERENCES.json:…:book_context` → `unsupported locator format`.

---

## 4. EMPTY / UNPROVEN (что невозможно подтвердить live)

1. **Conflicts (M5):** 0 записей у всех 7 entity. Хранилище `runtime/runtime_data/knowledge/` существует и **пусто**; production-код в него не пишет (grep: `ConflictRepository` используется в `runtime/core/routes/knowledge_cards.py` только на чтение и в тестах). Live-доказательство conflict-цепочки невозможно без новых записей.
2. **Reasoning (M6):** 0 записей — та же причина (`ReasoningRepository` только чтение + тесты).
3. **Corrections (M7):** 0 записей — та же причина (`CorrectionRepository` только чтение + тесты).
4. **Lineage (M8g):** `lineage=0` у всех entity — прямое следствие п.1–3; live-сценарий «связанные M5→M6→M7 записи» существует только в `runtime/tests/test_m8c_trace_journey.py`.
5. **M3 typed resolver (`core/CORE/knowledge/world_resolver.py`)** и **M4 typed resolver (`core/CORE/knowledge/temporal_resolver.py`)** — используются **только в тестах** (`test_m3_…`, `test_m4_…`); в live trace world/temporal собираются из card projection, а не через typed `WorldEntityReference`/`TemporalReference`. Статусы `RESOLVED/UNRESOLVED/AMBIGUOUS` и time-basis `WORLD_TIME/SOURCE_PUBLICATION/INGESTION/ASSERTION` live не наблюдаются.
6. **Frontend/browser-ветка** (Knowledge Trace UI, e2e) — в этот прогон не входила.
7. **`academic` source:** `claim_count=0` (честный пустой источник, не ошибка).

---

## 5. DOC DRIFT (устаревшие утверждения SoT; правки НЕ вносились)

1. `docs/CURRENT_DEVELOPMENT_STATE.md:62` — «`test_knowledge_cards.py` — 37 passed»; фактически в файле **40** тест-функций (`def test_`), последний добавлен коммитом `1e3f812`.
2. `docs/CURRENT_DEVELOPMENT_STATE.md:65` — «Frontend Knowledge Cards | TODO | Отдельного frontend-компонента … не обнаружено» — существует `arkaim-web/src/shared/ui/KnowledgeTraceCard.tsx` + `tests/unit/knowledge-trace-card.test.tsx` (коммит `83f78eb`). Отдельного **route** действительно нет — формулировка «компонента нет» устарела.
3. `docs/CURRENT_DEVELOPMENT_STATE.md:115` и `:129` — «frontend Knowledge Cards … TODO» — та же причина.
4. `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md:143` — «Полный live verification … документация прямо не заявляет такой прогон» — настоящий отчёт и есть такой прогон (backend-ветка); в план по instruction НЕ вносился.
5. `…PLAN.md:157` (§1.5 п.9 «не один full traceability journey»), `:1141` (§7.1 п.7 «Нет общей traceability acceptance test»), `:1102` (§5 «Full traceability journey — NOT PROVEN») — устарели: journey реализован в `test_m8c_trace_journey.py`, теперь подтверждён и live-прогоном claim→evidence→source→world→temporal (кроме lineage).
6. `…PLAN.md:1189` («Контрольный прогон M2+M1+knowledge cards: 88 passed») и END-строка `:1402` («153 Knowledge Core tests green») — числа не пересчитывались после добавления теста в `1e3f812`; в рамках verification не перезапускались.
7. Подтверждено без дрейфа: live 200 для search/card (план `:106`, дата 2026-10-01) воспроизведено на HEAD `1e3f812` 2026-10-02; mojibake `region_arkaim` описан в M8f (`…PLAN.md:1382`) и присутствует live.

---

## 6. PROBLEMS (только фактические; ничего не исправлялось)

1. **`status=COMPLETE` при оборванном пути evidence.** `region_arkaim`: 7 из 25 claims имеют `evidence.status=UNKNOWN` и не имеют `claim_id`, `uncertainty.has_unknowns=false`, `limitations=[]`, но `status=COMPLETE`. Ожидание по `…PLAN.md:250-251` (§2.5: «если путь … обрывается, … PARTIAL/UNKNOWN status») — статус PARTIAL. Фактическая логика: `runtime/core/routes/knowledge_cards.py:431-438` (PARTIAL только если нет `primary_entity`, нет evidence-строк либо есть несвязанные records).
2. **Два разных формата ошибок на одних endpoint-ах.** 401/404 → `{"ok":false,"error":{"code":…}}`; ошибки валидации 422 → голый FastAPI `{"detail":[…]}` (`search?q=`, `limit=0/101`).
3. **`search.total` = размер страницы, а не глобальное число совпадений** (`limit=3` → `total=3`; `limit=10` → `total=10`). В SoT семантика `total` не описана.
4. **`uncertainty` не учитывает evidence-пробелы:** у `region_arkaim` 7 UNKNOWN-evidence строк, при этом `uncertainty={"has_unknowns":false,"unknown_aspects":[]}` (секция приходит из card и отражает «неизвестные аспекты», а не статусы evidence).
5. **Temporal live — только projection-маркеры** (`PROJECTED_FROM_WORLD_REF`), без типизированных temporal refs (см. §4.5).
6. **Побочный эффект запуска backend:** старт приложения дописал запись в отслеживаемый файл `core/CORE/genome/history/index.json` (+11 строк, snapshot `2026-10-02T10:36:02Z`). Код/тесты/SoT не менялись; файл оставлен как есть (автосохранение genome history при старте), `git status` содержит только эту строку.
7. mojibake в данных WorldModel: `world.name`/`world.description` у `region_arkaim` — двойная кодировка UTF-8 → CP1251, источник данных — `core/CORE/WORLD_MODEL/GEOGRAPHY.json` (см. addendum) — известная проблема из M8f, live подтверждена, не исправлялась.

**Не является проблемой (подтверждено как задумано):** честные пустые секции; fail-closed `claim_id`; `UNAVAILABLE`/`UNKNOWN` без `evidence_id`; 404 карточки vs 200/PARTIAL трассировки; неизменные `totals` под фильтрами.

---

## 7. Проверяемые вложения

- Сырые JSON: `%TEMP%\opencode\live\` (`trace_*.json`, `card_*.json`, `p_*.json`, `f_*.json`, `miss_*.json`, `search_*.json`)
- Сводки: `%TEMP%\opencode\live\{summary_endpoints,trace_summary2,pagination,filters,filter_page,missing_entity,region_detail,detail2,detail3,detail4,card_detail,search_validation}.txt`
- Лог backend: `%TEMP%\opencode\live_be_err.log`, `%TEMP%\opencode\live_be_out.log`

---

## ADDENDUM 2026-10-02 — классификация PROBLEMS после решения владельца

Решение владельца: PROBLEM №1 и №2 **не исправлять автоматически** — вынесены в `## OWNER-GO ITEMS` (`docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md`, §13). Прочие пункты можно рассматривать без нового OWNER-GO, если исправление не меняет утверждённый контракт. Ниже — факты дополнительной проверки; код/тесты/API не менялись.

### Без нового OWNER-GO (факты проверки)

1. **`search.total` (PROBLEM №3).** `runtime/core/routes/knowledge_cards.py:34-96`: endpoint объявлен без `response_model`, возвращает `{"query", "entities", "total": len(unique)}`; `limit` ограничен `1..50`, сбор обрывается при `len(unique) >= limit` (строки 76 и 93), поэтому `total` фактически равен размеру ответа. Во frontend `/knowledge/cards/search` упоминается только в `arkaim-web/src/shared/api/envelope.ts:63` как `direct`; потребителя поля `total` в `arkaim-web/src` нет (`contracts/knowledge.ts` знает только trace, строка 99). Семантика `total` в SoT не описана. → GO-free: зафиксировать текущую семантику в документации; перевод на глобальный счётчик уже меняет наблюдаемое поведение поля API и потому принимается явно, а не «по пути».
2. **`uncertainty.has_unknowns` (PROBLEM №4).** `core/CORE/knowledge_card/builder.py:619-634` (`_unknown_aspects`) собирает только card-level аспекты: неразрешённая entity, отсутствие book claims, отсутствие archaeology claims, `unsolved` из entity; `:751-753` — `has_unknowns = bool(unknowns)`. Evidence-статусы относятся к отдельной секции trace и в `uncertainty` контрактно не входят (§2.5, M8/M9 — про status и evidence, а не про эту секцию). → нарушения контракта нет; работа = уточнение формулировки семантики, новый статус не требуется.
3. **Mojibake (PROBLEM №7, данные/представление).** Источник — не API, а данные (двойная кодировка UTF-8 → CP1251). Подтверждено поиском: `core/CORE/WORLD_MODEL/GEOGRAPHY.json:27,28,53,328,329,331` (`region_arkaim.name/name_ru`, описания, `Меридиан Аркаима`), `core/KNOWLEDGE/MAP_DATA.json:25,44,292,308`, `core/KNOWLEDGE/CROSS_REFERENCES.json:8,177,200`; суммарно 3 файла (374/82/66 вхождений маркера двойной кодировки). В `GEOGRAPHY.json` у `region_arkaim` указан `source: "MAP_DATA.json"` → первоисточник, вероятно, `MAP_DATA.json`. → GO не требуется; перед правкой уточнить объём (только затронутые сущности vs все три файла), поскольку `name`/`description` участвуют в retrieval-путях (M8f использует crosswalk `region_arkaim → аркаим`).
4. **`core/CORE/genome/history/index.json` (PROBLEM №6).** Происхождение выяснено, ничего не менялось: `core/CORE/pulse/pulse.py:88` вызывает `self._evolution.snapshot(self._genome, self)` в конце `load()` (также `:292` в `evolve()` и `:317` в `rollback()`); запись в `index.json` делает `core/CORE/pulse/evolution.py:86-92` (`_save_history()`), там же создаются snapshot-файлы (`genome_v1.0.0_2026-10-02.json` — новый untracked файл того же запуска). Любой старт backend → `Pulse.load()` → append записи. Правка tracked-файла (+11 строк) — ожидаемаемый side effect запуска приложения, не вмешательство; по указанию владельца не откатывалась и не исправлялась.
5. **Документационный drift (PROBLEM класса DOC DRIFT).** Закрыт 2026-10-02 синхронизацией `docs/CURRENT_DEVELOPMENT_STATE.md`, `docs/ARKAIM_KNOWLEDGE_DEVELOPMENT_PLAN.md`, `docs/DOCUMENTATION_INDEX.md`; контракт/код/тесты не менялись.

### Требуют отдельного OWNER-GO (не исправлять автоматически)

- **PROBLEM №1** — `trace.status=COMPLETE` при `UNKNOWN` evidence: семантика `KnowledgeTraceResponse.status` → раздел `## OWNER-GO ITEMS` плана, пункт 1.
- **PROBLEM №2** — envelope vs `detail` для 422: API-контракт ответов об ошибках → раздел `## OWNER-GO ITEMS` плана, пункт 2.
- **PROBLEM №5** — temporal live отдаёт только projection-маркеры (`PROJECTED_FROM_WORLD_REF`), typed M3/M4-резолверы (`world_resolver`, `temporal_resolver`) в API не подключены: это расширение API и подпадает под действующий STOP GATE («API expansion требует нового OWNER-GO»).
