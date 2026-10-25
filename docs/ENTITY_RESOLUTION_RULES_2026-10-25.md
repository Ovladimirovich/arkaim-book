# Правила разрешения сущностей и отношений (дизайн) — 2026-10-25

> Статус: **аналитический шаг, назначен OWNERом 2026-10-25.** Документ
> содержит ПРАВИЛА (семантику), не код. Новый resolver НЕ создаётся, флаг
> `EDM_RES_PILOT_ENABLED` НЕ включается — включение возможно только после
> утверждения этого дизайна (STOP GATE в §7).
>
> Основа: `docs/ENTITY_RESOLUTION_AUDIT_2026-10-25.md` (механизмы,
> ID-пространства, live-аудит), `docs/EDM_RES_PILOT_2026-10-25.md`
> (интеграционный контур), фактические данные production-каталогов
> (live-проверено 2026-10-25, §1).

---

## 0. Простыми словами

**Что было целью.** Зафиксировать, ПО ЧЕМУ система выбирает ту или иную
сущность под конкретный вопрос, ДО включения автоматического EDM-контекста.
Без этого флаг только начнёт автоматически подставлять неоднозначные связи
(кейс «Аркаим» = поселение + регион + язык + канон-мастер-карточка).

**Что сделано.** Разделение на два уровня, как постановлено OWNERом:
(1) *Entity Resolution* — «какие сущности соответствуют запросу» — уже
существующие механизмы (§1.1), ничего не дублируем;
(2) *Context Resolution* — «какая из них нужна этому вопросу» — новый
набор правил (§3–§5), который НЕ требует нового кодового механизма:
таблица намерений + правила фильтрации СУЩЕСТВУЮЩИХ полей EDM-карточек.

**Главные фактические находки (live, 2026-10-25):**

- В production-движке (13 категорий, 503 сущности) **нет ни одной
  типизированной связи**: поле `relationships` пустое во всех 13 файлах
  `core/CORE/WORLD_MODEL/`. Реальные связи есть только в legacy-модели
  `narrative_engine/data/WORLD_MODEL.json` и в EDM-карточках.
- В legacy-модели **уже утверждено 5 канонических связей персонажей**
  (`mentor_of`/`peer_of`, AUTHOR_CANON, confidence 1.0, с главами):
  Учитель→Велик, Световит→Велик, Велик→Мирослав, Учитель→Наставники,
  Радомир↔Велик (peer).
- В пилотных EDM-карточках **уже есть сгенерированные типизированные
  связи** (`located_in: arkaim_settlement→region_arkaim`; `associated_with:
  civ_arkaim_civilization→civ_hyperborea` (0.7, «вывод, не канон»);
  `uses: Световит→warrior_clothing` (0.2, «книга не говорит, кто носит»)),
  но они помечены `derived` — это гипотезы, не канон.
- В каталоге EDM **двойная карточка «Аркаим»-локации**: `region_arkaim`
  (pilot) и `arkaim` (examples, master-карточка из 6 слоёв) — обе
  type=location, обе named «Аркаим» (§5.1, §7-S4).

**Вывод.** Механика «найти» есть. Не хватает (и вводится здесь) — семантики:
намерение вопроса → тип сущности; что делать при неоднозначности; какие
связи доверенные (Tier-2), а какие остаются гипотезами (Tier-1).

---

## 1. Что есть сегодня (фактическая основа)

### 1.1 Механизмы Entity Resolution (не трогаем, переиспользуем)

| Механизм | Где | Что отдаёт |
|---|---|---|
| `resolve_related_entities` | `runtime/core/services/related_entities.py` | до 10 сущностей `{entity_id, entity_type(категория engine), name, description}`; детерминированный stem-скоринг (MIN_SCORE=60), дедупликация семейств `lang_/phil_/phil_deep_` |
| `WorldKnowledgeResolver.resolve` | `core/CORE/knowledge/world_resolver.py` | 4 статуса: `RESOLVED` (canonical_id / approved_crosswalk), `AMBIGUOUS` (несколько утверждённых кандидатов — семантический прецедент бандла!), `CROSSWALK_UNAPPROVED`, `UNRESOLVED` |
| `NameResolver` | Knowledge Core (RAG) | 6 утверждённых групп имён персонажей (Велик и др.), exact-вхождения в `enriched_chunks.json` |
| crosswalk v2 | `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` | 3 APPROVED label→canonical_id (`region_arkaim`, `region_hyperborea`, `region_oceania`); G6: «Соответствия не выводятся по сходству названий» |

Все четыре механизма отвечают БЕЗ LLM — семантический уровень строится
как детерминированные правила (требование OWNERа).

### 1.2 Production-категории engine (live, 2026-10-25; `get_categories()`)

| Категория (`entity_type` в `related_entities`) | Кол-во | Примеры ID |
|---|---|---|
| geography | 17 | `region_arkaim`, `region_hyperborea`, `region_sintashta`, … |
| philosophy | 268 | `phil_…`, `phil_deep_…` |
| language | 134 | `lang_аркаим`, `lang_архат`, … |
| social_structure | 12 | `daily_social_hyperborea_daily_life_clothing`, … |
| religion | 10 | `ritual_герметизм`, … |
| rituals | 10 | те же 10 ритулов (дубликат категории) |
| mythology | 37 | `myth_велик_/_великосвет`, … |
| architecture | 5 | `arkaim_settlement`, `hyperborea_palace`, … |
| daily_life | 3 | `communal_living`, `agricultural_life`, … |
| civilizations | 3 | `civ_arkaim_civilization`, `civ_hyperborea`, `civ_oceania` |
| transport | 2 | `horse_travel`, `river_boats` |
| climate | 2 | `steppe_climate`, `hyperborea_climate` |
| technologies | 0 | (пусто) |

**Критично для правил:** в engine НЕТ категорий `characters` и `clothing`:
персонажи живут в legacy-модели (`characters_living` по эпохам satya/treta/
dvapara yuga) + NameResolver + RAG; одежда — в `social_structure`
(конкретно гиперборейская), в FORM-слое (`FORM.warrior_clothing`) и в
EDM-карточках.

### 1.3 EDM-каталог (8 карточек)

`pilot/` (5: `region_arkaim`, `arkaim_settlement`, `civ_arkaim_civilization`,
`civ_hyperborea`, `steppe_climate`) + `examples/` (3: `arkaim`,
`svetovit_character`, `warrior_clothing`).

Структура карточки (существует, используется правилами §4):
- `identity`: `canonical_id`, `type` (location/building/climate/culture/
  character/clothing), `names`, `aliases`, `one_line`, `is_reconstruction`;
- `claims`: `path`, `value`, `status` (known/unknown/reconstructed),
  `provenance_class` (external_source / canon / ai_model_artistic / …),
  `confidence`, `medium` (art-model), `required_unknown` (constraints);
- `relations`: `{type, target, target_type, label, provenance_class,
  confidence, note}` — сгенерированы при миграции (Tier-1, §4.4);
- `time`: `epoch_ref` (+ required_unknown для эпох).

### 1.4 Данные связей (что реально существует)

| Слой | Что есть | Доверенность |
|---|---|---|
| engine `core/CORE/WORLD_MODEL/*.json` | `relationships: []` во всех 13 файлах (503 записи) | связей нет |
| legacy `narrative_engine/data/WORLD_MODEL.json` | `character_relations` ×5 (mentor_of×4, peer_of×1; AUTHOR_CANON 1.0, примечания по частям/главам); `locations.*.related_entities` — **fuzzy-строки на русском** («Страна Городов», «Гиперборея», «Велик»), не canonical ID; эпоха `arkaim_era`; событие `event_arkaim_construction (epoch=arkaim_era, location=аркаим)` | character relations — канон; related_entities — не ID-согласованы |
| EDM-карточки (`relations`) | `located_in: arkaim_settlement→region_arkaim`; `associated_with: civ_arkaim_civilization→civ_hyperborea` (derived 0.7, «вывод, не канон»); `located_in: Световит→arkaim` (0.3, «локация неизвестна в каноне»); `uses: Световит→warrior_clothing` (ai_model_artistic); `clothing.wearer` у `warrior_clothing` = UNKNOWN («книга не говорит кто носит») | Tier-1: гипотезы (§4.4) |

### 1.5 Карта коллизий «Аркаим» (4 кандидата + дубль в каталоге)

```text
Аркаим
├── region_arkaim        (engine geography + pilot EDM card; crosswalk APPROVED)
├── arkaim_settlement    (engine architecture + pilot EDM card, type=building)
├── lang_аркаим          (engine language, 1 из 134)
└── arkaim               (examples EDM master-card, type=location, 6 слоёв)
```

`arkaim` и `region_arkaim` — две ЛОКАЦИИ в одном каталоге (§5.1, §7-S4).

---

## 2. Двухуровневая модель (архитектура решения)

```text
ЗАПРОС (вопрос + ответ Pulse + контекст сцены, если есть)
   │
   ▼  [уровень 1] Entity Resolution — СУЩЕСТВУЕТ (§1.1)
   │  кандидаты: related_entities (entity_type=категория engine) +
   │             WorldKnowledgeResolver (approved crosswalk) +
   │             явные edm_entity_ids
   │
   ▼  [уровень 2] Context Resolution — ПРАВИЛА ЭТОГО ДОКУМЕНТА (§3–§5)
   │  намерение (intent) из вопроса
   │  → фильтрация кандидатов по типу
   │  → правило выбора (одна / бандл / gap)
   │  → правила отбора claims/relations из карточек
   │
   ▼  EDM-контекст (dialogue / MediaPlan / VisualContext)
```

Уровень 1 — никаких новых механизмов. Уровень 2 — чистые правила,
реализуемые как детерминированная функция (таблицы §3–§5); LLM в выбор
сущности НЕ включается (принцип: книга первична, LLM — голос).

---

## 3. Задача 1 OWNERа: типы контекста запроса (intents)

Детерминированное извлечение: вопросные слова + content-слова вопроса
(те же stop/content-механизмы, что уже есть в `related_entities.py`).
**Без LLM.** Тип намерения определяется ВОПРОСОМ, а не сущностью:
«Где находился Аркаим?» → `where`, хотя «Аркаим» называется архитектурой.

| intent | Триггеры (примеры формулировок) | Желательные типы |
|---|---|---|
| `about` | «Расскажи об X», «Что такое X», «Опиши X» | бандл всех типов (R4) |
| `where` | «Где (находится/расположен/лежит) X», «какая местность» | `location` |
| `appearance` | «Как выглядел(о) X», «какие были стены/постройки/укрепления» | `building`, `location` |
| `clothing` | «Что носили (жители)», «в чём ходили/одеты», «одежда» | `clothing` |
| `climate` | «Какая погода/климат/жара/зима/дожди» | `climate` |
| `language` | «Какой язык / на каком языке говорили» | `language` |
| `character` | «Кто такой X», «Что делал/знает X» | `character` |
| `culture` | «В чём верили», «ценности/обычаи/устройство жизни» | `culture` (+ engine `civilizations`) |
| `era` | «Когда (происходило)», «в какую эпоху/период» | эпоха (`time.epoch_ref`, legacy/EDM) |
| `cause` | «Почему / зачем» | бандл (в v1 нет type-маппинга) |

Правила извлечения:
- **I1.** Совпал ровно один тип намерения → он и есть intent.
- **I2.** Совпало несколько → детерминированный приоритет:
  `where > appearance > clothing > climate > language > character >
  culture > era > cause > about` (конкретнее вопрос wins).
- **I3.** Ни один не совпал → `about`.
- **I4.** Intent определяется только по ВОПРОСУ (не по ответу Pulse) —
  ответ может «перетянуть» тему; выбор сущности — под вопросом, не ответом.

---

## 4. Задачи 2–6 OWNERа: правила Context Resolution

Соответствие задаче OWNERа: §4.1 = задача 2 (выбор между одноимёнными),
§4.2 = задача 3 (multi-entity ответ), §4.3 = задача 5 (неоднозначность),
§4.4 = задача 4 (допустимые crosswalk-связи), §4.5 = задача 6
(отсутствие утверждённой связи).

### 4.1 R: выбор между одноимёнными сущностями

Вход: кандидаты уровня 1 + intent (§3). Кандидат «подходит по типу»,
если его `identity.type` (EDM-карточки) или `entity_type`-категория
(engine-кандидаты, маппинг ниже) входит в желательные типы intent.

| Правило | Условие | Результат |
|---|---|---|
| **R1 single** | подходящих кандидатов ровно 1 | одна сущность, без бандла |
| **R2 ambiguous-bundle** | подходящих кандидатов ≥2 | **бандл всех подходящих**; score/coverage — только порядок внутри бандла, не отсечение |
| **R3 gap** | подходящих кандидатов 0 | НЕ подставляем «не той» сущность; explicit gap (§4.5) |
| **R4 about-bundle** | intent `about` | бандл ВСЕХ названных в вопросе кандидатов + утверждённые Tier-2 связанные; без «главной» карточки |

**Закреплено OWNERом 2026-10-25:** правила приоритета типов вида
«архитектура важнее географии» НЕ принимаются. Выбор — только через intent.

Маппинг engine-категория → EDM-type (v1):
`geography→location`, `architecture→building`, `climate→climate`,
`civilizations→culture`, `language→language`; остальные категории
(mythology/philosophy/daily_life/social_structure/religion/rituals/
transport) EDM-type в v1 не имеют и участвуют в бандле как «контекст
без карточки» (описание engine-категории, без claims-фильтрации §4.2).

Детерминированный порядок бандла (ти-брейкеры, не семантика):
(a) утверждённый в crosswalk canonical_id — первым; (b) engine-кандидат;
(c) examples-карточка; (d) `name_coverage` desc; (e) `entity_id` asc.

### 4.2 C: отбор свойств (claims) внутри (мульти-)ответа

Каждая сущность бандла вносит только своё; claims фильтруются:

| Правило | Условие | Как проецируется |
|---|---|---|
| **C1** | `status=known`, `provenance_class ∈ {canon/author_canon, external_source}` | утверждение фактом, с провенансом (`layer.ref.path`) |
| **C2** | `status=reconstructed` | «реконструкция, не канон» (прецедент: `civ_arkaim_civilization` culture.values 0.7) |
| **C3** | `medium=true` (`provenance_class=ai_model_artistic`) | dialogue: ТОЛЬКО «визуальный образ (допущение)» (G10; прецедент `svetovit` verify.dialogue_sentence); MediaPlan/Visual: допускается с явной меткой |
| **C4** | `status=unknown` ∈ `constraints.required_unknown` | explicit UNKNOWN: «не установлено в книге» (прецедент: weather/season у `region_arkaim`, `arkaim`) — НИКАКИХ дефолтов |
| **C5** | `status=unknown` НЕ в required_unknown | не показывается (не выдумывать неизвестное) |
| **C6** | `is_reconstruction=true` (identity, напр. `warrior_clothing`) | вся карточка входит как «реконструкция», без исключений |

**M1 (multi-entity):** claims берутся из каждой карточки независимо
по C1–C6; в провенансе ответа указывается ID вносившей сущности
(`edm:<id>` / engine-категория) — ответ остаётся traceable.

### 4.3 D: поведение при неоднозначности (R2/R4)

- **D1.** Статус ответа — `AMBIGUOUS` (аналог существующего
  `WorldReferenceStatus.AMBIGUOUS` у `WorldKnowledgeResolver`).
- **D2.** Бандл ограничен: максимум **N=4** (порядок §4.1).
- **D3.** Dialogue-формулировка при N≥2: «под именем X соответствуют
  несколько объектов: …» + claims каждой по C-правилам. Никогда не
  «X — это (угаданное)».
- **D4.** Intent `where` для «Аркаим» → бандл [region_arkaim, arkaim]
  (§5.1): две локации не сливаются, но и не выбираются насильно.

### 4.4 G: допустимые crosswalk-связи (relation vocabulary v1)

Двухуровневая модель доверенности связей:

- **Tier-1 (уже существует):** `relations` в EDM-карточках,
  сгенерированные при миграции; `provenance_class ∈ {derived,
  ai_model_artistic}`, confidence < 1.0. Используются ТОЛЬКО как
  «контекстуальная гипотеза» (обвязка C3), НИКОГДА как утверждение книги.
  `uses: Световит→warrior_clothing` (0.2, «книга не говорит кто носит»)
  и `located_in: Световит→arkaim` (0.3, «локация неизвестна в каноне»)
  остаются в Tier-1.
- **Tier-2 (новая граница доверенности):** секция `relations` в
  `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json` (schema v2.1),
  каждая запись: `{id, source_id, relation, target_id, provenance,
  status: APPROVED, owner_reviewed: true, evidence[]}` — полный аналог
  существующих `mappings` (там же: `owner_decision`, G6-политика,
  `rejected_candidates`).

Словарь relation v1 (минимальный, только то, что есть в данных):

| relation | допустимая пара типов | где уже есть данные |
|---|---|---|
| `located_in` | building/architecture/character → region/location | Tier-1 `arkaim_settlement` + legacy `locations.аркаим` |
| `has_climate` | region → climate | **нет нигде утверждённой** — кандидат (обе карточки в engine) |
| `existed_in` | civilization/settlement → epoch | legacy: эпоха `arkaim_era` + `event_arkaim_construction` (crosswalk evidence уже ссылается) |
| `associated_with` | culture → culture | Tier-1 `civ_arkaim` → `civ_hyperborea` (derived 0.7, «вывод») |
| `mentor_of` / `student_of` / `peer_of` | character → character | legacy `character_relations` ×5 (AUTHOR_CANON 1.0) — готовы к утверждению |
| `uses` | character → clothing | только Tier-1 (0.2) — в v1 НЕ утверждается |

Политика:
- **P1.** «Существует в World Model» ≠ «утверждено для публичного
  EDM-контекста». Перевод Tier-1 → Tier-2 — ТОЛЬКО owner-решением
  (по принципу `mappings`: `owner_reviewed`, `evidence[]`).
- **P2.** G6-политика расширяется на relations: «связи не выводятся по
  сходству названий». `locations.*.related_entities` (fuzzy-строки) в v1
  НЕ утверждаются: «Гиперборея» ID-согласуется с `region_hyperborea`
  (mapping уже есть) и может стать кандидатом; «Страна Городов» не имеет
  ID-соответствия → остаётся unapproved (G6).
- **P3.** Character relations идентифицируются ИМЕНАМИ (ключи
  legacy-модели: Велик, Световит, Мирослав, Радомир, Учитель, Наставники);
  namespace `char_*` НЕ выдумывается (известный gap из audit;
  ID reconciliation персонажей — отдельная задача).

**Кандидатный v1-батч для утверждения OWNERом (10 связей):**

| # | source → target | relation | основание |
|---|---|---|---|
| 1 | `arkaim_settlement` → `region_arkaim` | `located_in` | Tier-1 карточки + engine era «Уральская степь» + GEOGRAPHY |
| 2 | `region_arkaim` → `steppe_climate` | `has_climate` | обе карточки в engine (CLIMATE: «континентальный климат Южного Урала») |
| 3 | `region_hyperborea` → `hyperborea_climate` | `has_climate` | аналогично |
| 4 | `civ_arkaim_civilization` → `arkaim_era` | `existed_in` | legacy эпоха + `event_arkaim_construction (epoch=arkaim_era, location=аркаим)` |
| 5 | Учитель → Велик | `mentor_of` | legacy AUTHOR_CANON 1.0 (части 5–13) |
| 6 | Световит → Велик | `mentor_of` | legacy AUTHOR_CANON 1.0 (части 5–13) |
| 7 | Велик → Мирослав | `mentor_of` | legacy AUTHOR_CANON 1.0 |
| 8 | Учитель → Наставники | `mentor_of` | legacy AUTHOR_CANON 1.0 |
| 9 | Радомир ↔ Велик | `peer_of` | legacy AUTHOR_CANON 1.0 (соратники в одной эпохе) |
| 10 | `civ_arkaim_civilization` → `civ_hyperborea` | `associated_with` | Tier-1 derived 0.7 («потомки гипербореев» из описания) — **самая спорная: «вывод, не канон»; утверждение = OWNER-решение, можно отклонить и оставить Tier-1** |

### 4.5 B: поведение при отсутствии утверждённой связи

- **B1. fail-closed (закреплено):** нет Tier-2 связи → свойство НЕ
  материализуется нигде (dialogue/MediaPlan/Visual). Никогда дефолт,
  никогда «best guess» по score.
- **B2.** Граница знания — explicit: «связь „X … Y“ не установлена в
  каноне» (формат `required_unknown`: значение null + note). Прецеденты:
  `region_arkaim.claims[environment.weather]=UNKNOWN`,
  `warrior_clothing.claims[clothing.wearer]=UNKNOWN`.
- **B3.** Tier-1 связь при отсутствии Tier-2 допускается ТОЛЬКО как
  маркированная гипотеза (C3): «предположительно (не утверждено)».
  В MediaPlan — отдельным полем `hypothesis`, не в canonical-поле.
- **B4.** Ответ не «ломается» от absence: бандл просто короче;
  отсутствующая связь не порождает ложной «связи по умолчанию».

---

## 5. Задача 7 OWNERа: конкретные примеры (реальные сущности)

Легенда: **v0** — текущее состояние (Tier-2 связей нет); **v1** — после
утверждения v1-батча §4.4.

### 5.1 «Аркаим» — 4 вопроса, 1 имя

| Вопрос | intent → типы | Кандидаты | Правило | v0 | v1 |
|---|---|---|---|---|---|
| Где находился Аркаим? | `where` → {location} | `region_arkaim`, `arkaim` | R2 → AMBIGUOUS-бандл (порядок §4.1: crosswalk-approved первым) | claims: координаты 52.98/59.57 (external 0.8); «священное место, хранящее память о Гиперборее» (AUTHOR_CANON, master-карточка); weather/season = UNKNOWN (C4) | то же + Tier-2 `has_climate`: «климат региона — степной (континентальный)» с провенансом |
| Как выглядело поселение Аркаим? | `appearance` → {building, location} | `arkaim_settlement` (building) + 2 location | R2 → бандл | `arkaim_settlement`: form=ancient_settlement, style=circular fortified, materials=[stone, timber, thatch, clay] (known, external 0.8, C1) | + Tier-2 `located_in region_arkaim`: «поселение в регионе Аркаим (Южный Урал, 52.98/59.57)» |
| Какой язык связан с Аркаимом? | `language` → {language} | `lang_аркаим` (единственный language-кандидат) | R1 → single | claims языковой карточки (engine language); без утверждённых language-связей — только «языковая категория» | как v0 (в батче нет language-связей) — явная граница знания |
| Расскажи об Аркаиме | `about` → бандл | все 4: `region_arkaim`, `arkaim`, `arkaim_settlement`, `lang_аркаим` | R4 → бандл (N=4, ровно лимит D2) | claims каждой по C1–C6; явное «связи с климатом/эпохами не утверждены» (B1) | + Tier-2 `located_in`/`has_climate`/`existed_in` связывают бандл в сеть: WORLD MODEL как сеть, а не каталог карточек |

### 5.2 Климат

«Какая была погода (в Аркаиме)?» → intent `climate` → кандидаты типа
climate: `steppe_climate` (Южный Урал / Аркаим), `hyperborea_climate`
(Гиперборея).

- **v0:** утверждённой связи Аркаим→климат нет → **explicit gap (B1/B2)**:
  «климат, связанный с Аркаимом, как утверждённая связь не установлен;
  известна карточка климата степи (Южный Урал): континентальный,
  −30…+35 °C, 300–500 мм/год (external 0.8) — как контекст, не как связь».
- **v1 (после утверждения #2–#3):** «климат региона Аркаим — степной
  (континентальный): −30…+35 °C, осадки 300–500 мм/год» (Tier-2 + C1).
- Отдельно: «погода в конкретный день/сцену» остаётся `UNKNOWN`
  (`required_unknown` у `region_arkaim`) — климат ≠ погода, не смешивается.

### 5.3 Персонаж

«Кто такой Велик?» → intent `character`. Уровень 1: NameResolver
(6 утверждённых групп) + legacy `characters_living` (эпохи satya/treta/
dvapara) + RAG `enriched_chunks`. EDM-карточки у Велика НЕТ (в каталоге
только Световит) — в v1 это GAP (R3), не ошибка.

- **v0:** только канон-факты из legacy/RAG (присутствие, эпохи).
- **v1 (после #5–#9):** «Велик — ученик Учителя и Световита; Мирослав —
  его ученик; Радомир — соратник (одна эпоха); источник: канон автора,
  части 5–13» (5 утверждённых character relations, AUTHOR_CANON 1.0).

### 5.4 Одежда

«Что носили жители?» → intent `clothing` → тип clothing в v1 только у
EDM-карточки `warrior_clothing` (в engine категории clothing нет;
`daily_social_hyperborea_daily_life_clothing` — social_structure,
EDM-type в v1 не имеет). **R1 → single `warrior_clothing`**, но вся
карточка `is_reconstruction=true` (C6):

- dialogue (C3/C6): «воинская одежда — реконструкция (art-model по FORM):
  кожаная туника, шерстяной плащ, меховые сапоги, серебряный ошейник… —
  визуальный образ, допущение, а не канон книги»;
- C4: `clothing.wearer=UNKNOWN` → «кто именно носил — книга не говорит»;
- v1: Tier-2 `uses` НЕ утверждён (в батче нет #10-подобной) → связь
  «Световит носил» остаётся Tier-1 гипотезой (B3).

### 5.5 Архитектура

«Как были устроены стены (укрепления)?» → intent `appearance` →
`arkaim_settlement` (R1 для building; location-кандидаты — контекст).
claims: style «circular fortified» (кольцевое укреплённое поселение),
materials stone/timber/thatch/clay (known, external 0.8, C1).
v1 добавляет Tier-2 `located_in` (показ — §5.1, строка 2).

---

## 6. Wiring после утверждения (короткий, без нового resolver)

Только после §7 и утверждения v1-батча (§4.4):

- **W1. Intent-извлечение:** чистая детерминированная функция
  (таблица §3, правила I1–I4) в `runtime/core/services/` (helper рядом
  с существующими сервисами, без нового механизма разрешения).
  Unit-тесты: каждое из 10 intent на формулировках §5 + ложные срабатывания.
- **W2. Фильтр кандидатов:** `resolve_related_entities` (уже отдаёт
  `entity_type`) → группировка по §3/§4.1 → бандл/одиночка/gap по
  R1–R4 → `edm_pilot.match_entities(explicit_ids=бандл)`
  (существующий strict-match; никакого fuzzy).
- **W3. Отбор claims:** правила C1–C6 как фильтры над СУЩЕСТВУЮЩИМИ
  полями EDM-карточек (по полям §1.3) — фильтрация, не новая схема.
- **W4. Crosswalk v2.1:** секция `relations` (схема §4.4) +
  `_load_approved_relations()` по образцу `_load_approved_crosswalk()`
  (fail-closed при отсутствии) + расширение `test_b3b_crosswalk.py`
  (требования схемы) + read-only контракт (список
  `test_g11_typed_resolver_contract.py`).
- **W5. Включение:** `EDM_RES_PILOT_ENABLED=true` — отдельный OWNER-GO
  после W1–W4 и утверждения v1-батча. До этого — за флагом
  (public-контракты byte-identичны legacy).

---

## 7. STOP GATE — решения OWNERа (семантические, не технические)

| # | Решение | Варианты |
|---|---|---|
| **S1** | Таблица intents §3 (10 типов + приоритет I2) | утвердить / поправить состав |
| **S2** | Политика неоднозначности: бандл (не форс-выбор), N=4, детерминированный порядок §4.1, explicit gap §4.5 | утвердить / изменить лимит или формулировки |
| **S3** | v1-батч утверждённых связей §4.4 (10 связей, включая спорную #10 `associated_with` 0.7) | утвердить целиком / поэлементно / отклонить |
| **S4** | Дубль в каталоге: `arkaim` (examples master-card) vs `region_arkaim` (pilot) — обе location, обе «Аркаим» | сохранить обе (порядок по §4.1) / слить в одну / назначить роль каждой |
| **S5** | Включать ли флаг после W1–W4 и S1–S4 | OWNER-GO на `EDM_RES_PILOT_ENABLED=true` / оставить off |

До принятия S1–S4 документ остаётся аналитическим артефактом:
`docs/ENTITY_RESOLUTION_AUDIT_2026-10-25.md` и
`docs/EDM_RES_PILOT_2026-10-25.md` дополняются ссылкой на этот файл,
код и публичные контракты НЕ меняются.