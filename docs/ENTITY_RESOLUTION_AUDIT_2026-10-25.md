# Аудит автоматического entity resolution (read-only, 2026-10-25)

> Задача OWNER (2026-10-25): перед включением `EDM_RES_PILOT_ENABLED=true` и любой
> массовой миграцией — read-only исследование того, как **сегодня** система автоматически
> находит сущности из вопроса/сцены, и можно ли направить существующий механизм в EDM
> без создания параллельного резолвера.
>
> Статус: **DOCUMENTED** (только исследование; код не изменялся, временные probe-скрипты удалены).
> Связанные: `docs/EDM_RES_PILOT_2026-10-25.md`, `docs/EDM_PILOT_2026-10-25.md`,
> `docs/WM_MIGRATION_PLAN.md`.

## Простыми словами

Мы проверили, как система сама понимает, о какой сущности идёт речь. Обнаружили, что
**основной механизм автоматического нахождения сущностей уже существует** и работает:
на вопрос «Как выглядело поселение Аркаим вечером?» система без LLM детерминированно
находит три сущности мира («Аркаим-поселение», «Аркаим-регион», «Аркаим-языковая
категория») и собирает по ним проверенные знания. EDM-пилот параллельно ищет свои
8 сущностей простым совпадением имён в тексте. Проблема: между этими двумя
механизмами **нет моста** — они не знают друг о друге, а названия «Аркаим» в разных
категориях создают трёхсторонние коллизии. Хорошая новость: мост не нужно строить
с нуля — ID-пространства уже совпадают (engine-каталог, crosswalk и EDM-пилот
используют одни и те же `region_*`-идентификаторы), нужны только короткие связки и
правило разрешения коллизий.

## 1. Какие механизмы автоматического entity resolution существуют СЕГОДНЯ

| # | Механизм | Где | Что извлекает | LLM? |
|---|---|---|---|---|
| 1 | **`resolve_related_entities`** (детерминированный stem-скоринг) | `runtime/core/services/related_entities.py`, живёт в `/book/ask` (t1 pre-LLM через `build_dialogue_context` + post-LLM merge) | Сущности **всех 13 категорий production-WorldEngine** (geography, architecture, climate, civilizations, language(134), mythology(37), philosophy(268) и др.) по совпадению основ слов имени/описания с вопросом и ответом. Порог score ≥ 60, до 10 результатов, дедупликация семейств | нет |
| 2 | **`WorldKnowledgeResolver` + approved crosswalk v2** | `core/CORE/knowledge/world_resolver.py`, публичный `POST /knowledge/world/resolve` | ТОЧНОЕ разрешение: canonical entity ID (engine) → `RESOLVED`; approved crosswalk ru-label (casefold) → `RESOLVED`/`AMBIGUOUS`; сущность без approved mapping → `CROSSWALK_UNAPPROVED`; иначе → `UNRESOLVED`. Fail-closed | нет |
| 3 | **`NameResolver`** (APPROVED_ALIASES + морфология) | `core/CORE/intelligence/nameresolver.py` | Только **персонажи** (6 утверждённых групп: Велик, Влад, Вера, Славный, Гипербореи, Ученики) — расширение RAG-запросов алиасами | нет |
| 4 | **RAG-обогащение чанков** | `core/KNOWLEDGE/enriched_chunks.json` (824 чанка; 25 персонажей / 132 темы / 12 символов, извлечены enricher'ом при чанкинге) | Автоматические `enriched_characters/themes/symbols` — но используются фильтрацией в ContextAssembler, **не** в `/book/ask` | нет |
| 5 | **EDM-пилот-матчинг** | `runtime/core/services/edm_pilot.py` | Подстроковое (вопрос) / точное casefold (сцена) совпадение 8 EDM-имён/ID с текстом вопроса или строкой локации сцены | нет |

**Вывод по п.1–2 OWNER-вопроса:** из вопроса сегодня извлекаются сущности механизма #1
(все категории engine) + #5 (только EDM-имённый пилот-набор); из сцены — строка
`location` (заголовок сценария / genome-поле), которую обрабатывают точным совпадением
механизм #5 и VisualContextBuilder. «Достать сущность из сцены» как таковой (скоринг
по тексту сцены) сегодня **не существует**.

## 2. ID-пространства (п.3–4 OWNER-вопроса: какие ID, где латиница/кириллица)

| Пространство | Примеры | Регистр/алфавит |
|---|---|---|
| Production-WorldEngine (`get_categories`) | `region_arkaim`, `region_hyperborea`, `steppe_climate`, `civ_arkaim_civilization`, `arkaim_settlement`, `hyperborea_palace`, `lang_аркаим`, `char_location_гиперборея`, `energy_line_уральская_линия` | ID-префиксы латиница (`region_*`, `civ_*`, `lang_*`, `char_location_*`), но у части ID **кириллические суффиксы** (`lang_аркаим`); имена всегда кириллица |
| Crosswalk v2 (3 APPROVED) | `Аркаим→region_arkaim`, `Гиперборея→region_hyperborea`, `Океания→region_oceania` | canonical ID — стабильные латиницей; ru-label хранится casefold |
| EDM-пилот (8 сущностей) | `region_arkaim`, `arkaim_settlement`, `civ_arkaim_civilization`, `civ_hyperborea`, `steppe_climate`, `arkaim` (examples), `svetovit`, `warrior_clothing` | латиница; **совпадает с namespace engine-категорий** (подтверждено: engine climate/civilizations/architecture содержат ровно `steppe_climate`, `civ_hyperborea`, `civ_arkaim_civilization`, `arkaim_settlement`) |
| LOCATION_VISUALS (visual) | ключи: `Аркаим`, `Гиперборея`, `Океания`, `Подземные города`, `Святилища` | русские ProperCase; **case-sensitive dict-lookup** в `VisualContextBuilder._build_location` |
| Сценарный каталог (119 сцен, chapter=0) | `ОКЕАН - ДЕНЬ`, `ПОЕЗД - ПЛАЦКАРТ - ДЕНЬ`, `ОСТРОВА АТЛАНТИДЫ - ДЕНЬ` | free-form uppercase-текст из заголовков сцен (`_screenplay_location`) — **нет ID** |
| Genome-сцены (10) | `Аркаим`, `граница миров`, `` (пустые) | смешанный регистр; fallback — `world_entities` (case-insensitive) |
| Legacy `data/WORLD_MODEL.json` (пульс-слои) | `аркаим`, `гиперборея`, `океания` (кириллица) / `тмутаракан`, `sumer`, `india` (латиница) | **параллельная модель данных**, не production-engine; `Тмутаракань` живёт только здесь |

Заключение по регистру: единого канонического ID-пространства нет; мосты — crosswalk
ru-label (casefold) и engine-поиск (casefold). Чувствительные к регистру места:
crosswalk-lookup в `WorldKnowledgeResolver` (запрос НЕ casefold-ится перед ключом) и
dict-lookup LOCATION_VISUALS.

## 3. Живые probe-результаты (read-only, production-данные)

### 3.1 Вопрос → сущности (механизм #1)

Вопрос: *«Как выглядело поселение Аркаим вечером?»* → `resolve_related_entities`:

| entity_id | category | имя |
|---|---|---|
| `arkaim_settlement` | architecture | Аркаим |
| `lang_аркаим` | language | Аркаим |
| `region_arkaim` | geography | Аркаим |

Трёхсторонняя коллизия по имени «Аркаим» — все три проходят порог; дедупликация их НЕ
сливает (разные описания). Это ответ на п.6 (ambiguous matches): **амбигуити сегодня
решается скорингом/порядком, а не утверждённым правилом**.

### 3.2 WorldKnowledgeResolver (п.4 — регистр)

| Запрос | Статус | Комментарий |
|---|---|---|
| `аркаим` | RESOLVED (approved_crosswalk → `region_arkaim`) | работает только в нижнем регистре |
| `Аркаим` | **CROSSWALK_UNAPPROVED** | ложный сигнал: crosswalk-lookup case-sensitive, а engine search находит сущность casefold'ом |
| `Климат степи` | CROSSWALK_UNAPPROVED | сущность реально есть в engine (`steppe_climate`) и в EDM, но approved crosswalk покрывает только 3 региона |
| `тмутаракан` / `Тмутаракань` | UNRESOLVED | в production-engine нет; только в legacy-модели |

### 3.3 Сцена → EDM (механизм #5, `apply_edm_to_context`)

| Ключи локации | Сопавшиеся EDM-сущности |
|---|---|
| `Аркаим` (genome-сцена) | `arkaim_settlement`, `region_arkaim`, `arkaim` — та же 3-way коллизия |
| `граница миров`, `ОКЕАН - ДЕНЬ`, `Тмутаракань` | пустой список → **честный UNKNOWN** (угодие п.7) |
| без ключей (только explicit_ids) | пилот-вход `edm_entity_ids` |

### 3.4 Вопрос → EDM-текст (`_match_in_text`)

- «Как выглядело поселение Аркаим вечером?» → 3 EDM-сущности (коллизия выше).
- «Климат степи в эпоху Архата» → `steppe_climate` (рабочий автоматический случай).
- «Гиперборея и Аркаим» → `arkaim_settlement`, `civ_hyperborea`, `region_arkaim`, `arkaim`.
- «Что такое Велик?» → пусто: персонажи в EDM-каталоге отсутствуют (NameResolver их знает, EDM — нет).

## 4. Ответы на 8 пунктов OWNER-задания

1. **Что извлекается из вопроса:** все сущности production-engine (13 категорий) через
   детерминированный скоринг #1 + имена 8 EDM-сущностей через #5. RAG-обогащение (#4)
   не участвует в `/book/ask` (только Studio/Knowledge-контекст).
2. **Что извлекается из сцены:** строка `location` (заголовок/поле genome), обрабатываемая
   ТОЛЬКО точным casefold-совпадением с EDM-имёнами и case-sensitive lookup'ом
   LOCATION_VISUALS. Скоринга по тексту сцены нет.
3. **Какие ID:** см. таблицу п.2. Ключевой факт: **EDM-canonical_id совпадает с
   engine-namespace** (`region_*`, `civ_*`, `steppe_climate`, `arkaim_settlement`),
   и с crosswalk canonical_id.
4. **Латиница/кириллица:** см. п.2; чувствительные места — crosswalk-lookup резолвера
   (не casefold-ится) и LOCATION_VISUALS dict.
5. **Сколько случаев уже разрешается без нового механизма:**
   - вопрос → engine-сущности (все категории, до 10 шт.) — **работает сегодня**;
   - вопрос/сцена → EDM: точные совпадения 8 пилотных имён (Аркаим, Гиперборея,
     Климат степи, Световит, Одежда воина…) — **работает** (с коллизиями);
   - crosswalk lowercase → `region_*` — работает; reverse `_approved_rag_aliases`
     (`region_arkaim → ["аркаим"]`) — работает в Knowledge Card builder.
6. **Амбигуити:** 3-way «Аркаим» (arch/lang/geo × 3 EDM-карточки); «Климат степи»
   честно UNRESOLVED в публичном резолвере, хотя сущность существует.
7. **Где не находится:** 119 сценарных каталог-локаций (free text), `граница миров`,
   `Тмутаракань` (отсутствует в production-engine), персонажи (Велик и др. — вне EDM),
   natural-case написание («Аркаим») в crosswalk-цепочке.
8. **Можно ли направить существующий механизм в EDM без параллельного резолвера:**
   **ДА.** Все три элемента уже существуют:
   - (a) `/book/ask` уже вычисляет `result["related_entities"]` — их `entity_id`
     фильтруется по ключам EDM-индекса (`get_entities()`) и подаётся в
     `match_entities(explicit_ids=…)`; никакого нового резолвера не нужно;
   - (b) сцена: `location`-строка → engine-поиск/crosswalk (casefold) → `region_*` →
     EDM по ID; мост «имя → canonical» уже реализован в `WorldKnowledgeResolver`;
   - (c) недостающие швы — код-привязки небольшой длины; **продуктовое решение**:
     политика разрешения 3-way коллизий (какая «Аркаим»-сущность берётся для
     dialogue, а какая для media plan) — OWNER-уровня (provenance semantics).

## 5. Что делать дальше (рекомендация, без изменений в этом прогоне)

> **Обновление 2026-10-25 (OWNER):** вместо жёсткой «политики приоритета
> типов» (архитектура/география) принято двухуровневое разрешение
> (Entity + Context Resolution) с бандлами и Tier-1/Tier-2 связями —
> правила: `docs/ENTITY_RESOLUTION_RULES_2026-10-25.md` (§3–§5). Пункт 2
> ниже (политика 3-way коллизий / расширение crosswalk) вытеснен
> решениями S1–S4 этого документа.

1. **Wiring (инженерный, без изменения публичного контракта):**
   - `/book/ask`: после `related_entities` — фильтр их ID по EDM-индексу и передача в
     `match_entities` (расширение существующего пилот-путь, flag остаётся OWNER-GATE).
   - `WorldKnowledgeResolver`: casefold запроса перед crosswalk-lookup (исправление
     ложного `CROSSWALK_UNAPPROVED` для «Аркаим» — изменение поведения резолвера,
     требует решения: это не публичный контракт, но изменяет семантику статусов).
   - Сцена: опциональный мост location-строки → engine/crosswalk → `region_*` перед EDM.
2. **OWNER-решения (STOP GATE):**
   - Политика 3-way коллизий «Аркаим» (приоритет по категории: geography для
     world-scope, architecture для visual/media-scope?) — это provenance/смысловая
     семантика, не техническая.
   - Расширение approved crosswalk (сейчас 3 mapping'а) на `steppe_climate` и
     остальные категории — артефакт утверждается только владельцем.
3. После wiring и решения по коллизиям — можно вернуться к
   `EDM_RES_PILOT_ENABLED=true` и массовой миграции слоёв.

## Приложение: методика

Read-only пробы выполнялись временными скриптами (удалены) на production-данных:
`get_world_engine()` categories/counts, `resolve_related_entities` на вопросах
владельца, `WorldKnowledgeResolver.resolve` по 10 probe-запросам,
`edm_pilot.match_entities` / `_match_in_text` по сценам/вопросам, разбор JSON
(crosswalk, EDM-каталог, LOCATION_VISUALS, enriched_chunks, genome-история).
Кодовые изменения: отсутствуют.
