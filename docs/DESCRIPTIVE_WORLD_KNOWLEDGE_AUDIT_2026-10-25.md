# Аудит покрытия описательных знаний мира (Descriptive World Knowledge)

**Дата:** 2026-10-25
**Статус:** AUDIT (read-only исследование, код и данные не изменялись)
**Задача владельца:** прежде чем наполнять 12 эпох, составить карту того, **чем сегодня реально наполняется визуальный образ мира**: что система знает о месте, персонаже, архитектуре, одежде, предмете, природе, погоде; откуда знание берётся; где хранится; какие поля существуют; что доходит до MediaPlan; где провалы.

Связанные документы: `docs/G10_VISUAL_CARDS_REVIEW_2026-10-22.md` (8 визуальных библиотек = ARTISTIC_MODEL, авторский ревю pending), `docs/B3A_ID_RECONCILIATION_REPORT.md` (нормализация ID), `docs/PROJECT_REBASELINE_2026-10-18.md` (реестр слоёв).

---

## 1. Что найдено: описательные знания не в одном месте, а в 6 параллельных слоях

| # | Слой | Путь | Что это | Размер (факт) | Качество данных |
|---|------|------|---------|----------------|------------------|
| 1 | **WORLD_MODEL (canonical)** | `core/CORE/narrative_engine/data/WORLD_MODEL.json` | Семантическое ядро мира | 12 эпох, 6 локаций, 8 событий, 3 технологии, 4 цивилизации, 2 религии, 5 character_relations, 4 causal_rules, 27 живых персонажей (20+6+1) | Умеренное: описания есть, `source_level=CANON`, но `provenance=[]` везде, `events` не имеют `start/end_event`, 5 из 8 событий без `location_id`, `related_entities` — строки-названия, не canonical IDs |
| 2 | **WORLD_MODEL (extended)** | `core/CORE/WORLD_MODEL/*.json` (13 категорий, WorldModelExt) | «Что мы знаем о мире» по категориям: GEOGRAPHY(17), CIVILIZATIONS(3), CLIMATE(2), DAILY_LIFE(3), TRANSPORT(2), RELIGION(10), RITUALS(10), SOCIAL_STRUCTURE(12), ARCHITECTURE(5), LANGUAGE(134), MYTHOLOGY(37), PHILOSOPHY(268), **TECHNOLOGIES(0)** | Сильно разное: ARCHITECTURE/CLIMATE/TRANSPORT — курируемые карточки (properties, confidence, provenance_category, relationships); LANGUAGE/MYTHOLOGY/PHILOSOPHY — авто-извлечённые массивы (карточка «Предыстория человечества» повторяется ~268 раз, confidence 0.3) | Смешанное |
| 3 | **FORM (визуальные формы)** | `core/CORE/FORM/*.json` (11 категорий × 5 = 55 форм) | Готовые визуальные шаблоны: architecture, clothes, faces, lighting, weather, materials, textures, colors, rituals, sounds, body_language. У форм — `visual_prompt`, `materials`, `colors`, `era`, `time_of_day` | Курируемое ИИ-агентом (см. G10: ARTISTIC_MODEL, без provenance) | ARTISTIC_MODEL |
| 4 | **VISUAL_KNOWLEDGE (карточки сущностей)** | `core/CORE/visual/VISUAL_KNOWLEDGE/*.json` | Пер-сущностные визуальные профили: LOCATION_VISUALS (5), CHARACTER_VISUALS (3), + библиотеки ATMOSPHERES(8), CAMERA_LIBRARY, STYLE_LIBRARY(6), SHOT_LIBRARY(8), VIDEO_RULES, VISUAL_SYMBOLS(6) | ARTISTIC_MODEL (G10), `_provenance_metadata` отсутствует | ARTISTIC_MODEL, авторский ревю pending |
| 5 | **GENOME CURRENT (авто-извлечение)** | `core/GENOME/CURRENT/*_visuals_from_kg.json` | Массовые авто-профили: character_visuals_from_kg (**73**), location_visuals_from_kg (2, дубль), character_visuals_from_rag (1), world_entities (7), timeline (17) | Низкое: 73 записи с `age_range="не указан"`, `clothing="Высшее Существо Космоса, основатель Иерархии Света..."` (смысл, а не визуал), RAG-запись с `eyes="напрягся и исчез"` | Неадекватно для медиа-образа |
| 6 | **Визуализация/Pulse** | `core/CORE/visualization/` (prompt_builder, visual_genome, character_visualizer, scene_engine, world_visualizer) | Ещё один путь построения SD-промптов из Visual Genome (слоистый, для Pulse-визуализации) | Ре-использует канон `visual.visual_context_builder` | Параллельный канал |

**Вывод по слоям:** единой «системы описательных знаний» ещё нет. Есть 6 мест, каждое со своим словарём полей, своим уровнем качества и своим статусом provenance. Канонические сущности (WORLD_MODEL.json) **не связаны** ни с визуальными карточками, ни с формами — ни canonical ID, ни relations (wears/built_with/existed_in) нигде не существуют.

---

## 2. Покрытие по типам описания (вопрос владельца)

### 2.1 МЕСТО — развито лучше всего
- **Знаем:** локация → тип, описание (semantic), related_entities (строки), `epochs_present` (пустые), `provenance` (пустые). Визуально: LOCATION_VISUALS (5 мест: Аркаим, Гиперборея, Океания, Подземные города, Святилища — 7 полей: architecture{style,materials,features,age,condition}, landscape{terrain,vegetation,water,sky}, palette, atmosphere{default,time_variants}, sound, symbols). В FORM: 5 архитектурных форм. В ext-model: GEOGRAPHY (17) + ARCHITECTURE (5).
- **Доходит до MediaPlan:** ДА — через ComfyUI-шаблон: `architecture.style`, `landscape.terrain/vegetation`, `atmosphere.light/fog/particles`, `palette.description`, `symbols[:3].literal`. Конкретика Аркаима («concentric walls», «Bronze Age», «river valley») подтверждена live-трейсом (25.10).
- **Провалы:** 6 канонических локаций против 5 визуальных (Тмутаракань, Шумер, Индия — без визуала; Подземные города/Святилища — не канонические локации). 4 из 6 локаций без `epochs_present`. `architecture.materials/features/age`, `landscape.water/sky`, `sound` — **обрываются** на пороге: не проецируются ни в MediaPlan-структуру, ни в ComfyUI-промт (там только style/terrain/vegetation). Смешанные ID: `аркаим` (latin, WORLD_MODEL.json) vs «Аркаим» (кириллица, VISUAL_KNOWLEDGE) — связь держится только через lower-case и genome-сцены.

### 2.2 ПЕРСОНАЖ — самый тонкий слой
- **Знаем:** 27 живых персонажей (имена, эпохи, статус) в canonical-модели — без любого визуального поля. Визуальные профили — только 3 из 73: Велик, Учитель, Световит (11 полей: age_range, face, hair, eyes, build, clothing, accessories, mannerisms, movement, emotional_range, style_constants) — и они ARTISTIC_MODEL (G10). Все остальные персонажи падают в genome-fallback: 73 auto-карточки с плейсхолдерами («не указан», «среднее») и мусором RAG.
- **Доходит до MediaPlan:** только `appearance_summary` (одна строка, из build+hair) + `name`. Одежда/глаза/причёска/аксессуары **не проецируются** в структуру плана.
- **Провалы:** требование «нет описания = unknown, а не автогенерация» **не выполняется** ни в каком виде: поля либо пусты, либо содержат авто-мусор («eyes: напрягся и исчез»). Явного состояния UNKNOWN нет. Temporal validity внешнего вида (как персонаж выглядел в разных эпохах) отсутствует вообще.

### 2.3 АРХИТЕКТУРА — есть, но не сущность
- **Знаем:** два представления: (а) поле `architecture` внутри локационных визуальных карточек; (б) FORM/architecture.json — 5 форм с `era`, `materials`, `style`, `features`, `colors` (в т.ч. `arkaim_settlement` — «concentric stone walls, central observatory…»). В ext-model: ARCHITECTURE.json (5, с provenance-полями).
- **Доходит до MediaPlan:** только `style`. Материалы/фичи/возраст — не рендерятся.
- **Провалы (ключевой запрос владельца):** связь **архитектура → эпоха → технология → материалы** как графа **не существует**. `technologies` (3 в canonical) и ARCHITECTURE-карточки не связаны ни одним relationship. «Здание» — не сущность со своим ID, а атрибут локации.

### 2.4 ОДЕЖДА — есть материал, нет модели
- **Знаем:** (а) `clothing` как строка в CHARACTER_VISUALS (3 персонажа) и в genome-fallback (мусор); (б) FORM/clothes.json — 5 форм (warrior/priest/woman/child/noble) с `era`, `materials`, `style`, `items`, `colors`.
- **Доходит до MediaPlan:** как часть `appearance_summary` (и то только для 3 персонажей; в ComfyUI-шаблоне clothing отдельно не рендерится).
- **Провалы:** **отношения `person wears CLOTHING_ENTITY` нигде нет** — одежда не сущность, а строка/форм-категория. Маркировки CANON/DERIVED/RECONSTRUCTION/HYPOTHESIS для одежды отсутствуют. Связь «тип одежды → культура → эпоха → технология» — только на уровне `era`-поля в FORM.

### 2.5 ПРЕДМЕТЫ / КУЛЬТУРЫ
- **Предметы:** отдельного типа сущности «предмет/вещь/оружие/атрибут» **нет ни в одном хранилище**. Ближайшее — FORM/materials+textures (5+5) и DAILY_LIFE (3). Провал полный.
- **Культуры:** есть — CIVILIZATIONS (3 в ext, 4 в canonical), SOCIAL_STRUCTURE (12) — но чисто семантические, без визуального профиля и без links на персонажей/локации.
### 2.6 ПРИРОДА (флора/фауна/рельеф)
- **Знаем:** ландшафт только как поле `landscape` в 5 локационных карточках (4 подполя, заполнены для 2–3). Модули извлечения `world_extraction/modules/flora.py` и `fauna.py` существуют (пайплайн обогащения), но **файлов-хранилищ FLORA/FAUNA в WORLD_MODEL/ нет** — извлечённое некуда складывается.
- **Доходит до MediaPlan:** terrain + vegetation (ComfyUI).
- **Провалы:** воды/небо/флора/фауна как знание — только внутри 5 локаций; для остальных мест — пусто.

### 2.7 ПОГОДА / КЛИМАТ — обнаружены РИСК и провал одновременно
- **Знаем (хорошая новость):** климатическое знание СУЩЕСТВУЕТ: `WORLD_MODEL/CLIMATE.json` — 2 курируемые карточки (steppe_climate «Континентальный климат Южного Урала»: type, temperature_range «-30…+35°C», precipitation «300-500mm», seasons) + FORM/weather.json — 5 форм (dawn_weather/bright_day/storm/night_sky/ritual_fog: light, fog, wind, particles, time_of_day, color_temperature).
- **Доходит до MediaPlan:** **НЕТ, полностью**. `EnvironmentContext` (weather/season/temperature/wind) в VisualContext, но (а) builder заполняет только `time_of_day`, (б) ComfyUI-шаблон environment не рендерит, (в) MediaPlanBuilder в структуру плана его не проецирует. Ни одна из 55 форм погоды/климата до медиа не доходит.
- **РИСК (fail-open):** у `EnvironmentContext` **хардкод-значения по умолчанию** — `weather="clear", season="late summer", temperature="cool", wind="still"` (visual_models.py). Т.е. все текущие медиапланы несут в себе **внушённый false-факт**: «ясно, поздний лето, прохладно, штиль» — даже когда источник ничего такого не говорит. Это ровно тот сценарий, от которого владелец потребовал fail-closed («weather = unknown»). Реализовано некорректно: неизвестность маскируется дефолтом.
- Провалы: нет механизма привязки погоды к (место × время): CLIMATE-карточки не связаны ни с эпохой, ни с локацией; FORM-погоды — свободные шаблоны.

### 2.8 ВРЕМЯ
- Эпохи (12): skeleton + `source_level`; **provenance пуст, event-границы null** (подтверждено live-трейсом 25.10). События (8): 5 из 8 без `location_id`, characters_involved — строки.
- Отношения эпоха ↔ персонаж: `characters_living` (27) — привязка есть, но `location_id: null` у всех.
- В MEDIA-план время доходит только через `temporal_context` (1:1 наследование scene_extras) — т.е. как ссылки, не как знание.

### 2.9 СВЯЗИ (relations)
- Существуют ровно 2 вида: `character_relations` (5 записей, без source) и `related_entities` в локациях (кириллические строки, не IDs).
- **`located_in`, `belongs_to`, `wears`, `built_with`, `existed_in`, `related_to` как типы отношений — отсутствуют.** Ext-model имеет поле `relationships` у сущностей — но у RITUALS/MYTHOLOGY оно пустое (`[]`).
- `knowledge/claim_temporal_links.json` (9 записей, M17/M18) — связи «утверждение → время», единственный работающий relation-механизм.

### 2.10 PROVENANCE
- Канал структурно работает (подтверждено: эпохи → Temporal nodes → ProvenanceRef → MediaPlan.provenance, fail-closed).
- **Содержимое:** в каноническом WORLD_MODEL.json — пусто везде; визуальные слои — без provenance-метаданных (G10); ext-model — `provenance_category`/`notes` есть у авто-карточек, но confidence 0.3 и source = собственные JSON, не книга.
- Итог: «откуда знание» для визуального образа мира сегодня формально отвечает **G10-классификатор** (ARTISTIC_MODEL, source=ИИ-агент) — но эта метка в MediaPlan **не проецируется**: план не знает, что у него в арте стоит художественное допущение.

---

## 3. Что реально доходит до MediaPlan (упаковочный слой)

Контракт ComfyUI-промта (заморожен PA-F1/MP-F12, рендер `visual/prompt_templates/comfyui.py`):

| В промте (есть) | Обрывается (есть знание → не рендерится) |
|---|---|
| style.prefix (хардкод cinematic_fantasy, не STYLE_LIBRARY) | architecture.materials / features / age |
| scene.title | landscape.water / sky |
| architecture.style | atmosphere.sound |
| landscape.terrain / vegetation | environment целиком (weather/season/temperature/wind) |
| atmosphere.light → fallback lighting.description | palette.primary/accent (только description) |
| atmosphere.fog / particles | отдельное clothing/hair/eyes персонажей (только appearance_summary) |
| emotion.visual | symbol метаданные (literal only) |
| appearance_summary персонажей (макс.) | provenance статуса ARTISTIC_MODEL |
| palette.description | FORM-слои (все 55 форм) |
| camera composition/shot | CLIMATE-карточки ext-model |
| symbols[:3].literal | relationships (весь граф связей) |
| quality suffixes | |

Структура MediaPlan проецирует ещё уже: `characters[appearance_summary]`, `location[arch.style, terrain]`, camera, atmosphere.name, constraints, source_refs/temporal/provenance 1:1. Т.е. даже то, что есть в VisualContext, **теряется при упаковке**: MediaPlan — «последний упаковочный слой», но упаковывает он лишь верхушку визуального знания.

---

## 4. Ключевые выводы

1. **Тип «место» готов на ~70%** для медиа: конвейер работает, конкретика подтверждена (Аркаим-трейс). Дозапас: материалы/вода/звук/погода не добираются до промта.
2. **Тип «персонаж» готов на ~20%**: визуальные профили у 3 из 27; у остальных — авто-мусор; requirement «unknown вместо дорисовки» не реализован нигде (нет явного состояния UNKNOWN).
3. **Типы «архитектура», «одежда», «предмет» существуют как атрибуты/категории, а не как сущности** (нет canonical entity + relations wears/built_with). Ключевая для владельца цепочка «архитектура → эпоха → технология → материалы» не смоделирована.
4. **«Природа» и «погода» — самые недообслуженные типы**: погода не доходит до MediaPlan совсем, климатическое знание (2 карточки CLIMATE + 5 FORM-форм) висит мёртвым грузом, а EnvironmentContext одновременно **содержит false-дефолты** («clear / late summer») — единственный найденный fail-open дефект на пути к медиа.
5. **Единая «система описательных знаний» пока отсутствует**: 6 параллельных слоёв с разными словарями, ID-системами (latin vs кириллица) и статусами provenance. Связность между ними — только через genome-сцены и VisualContextBuilder.
6. **Покрытие «где знание»**: каноническое ядро (WORLD_MODEL.json) семантично-пустое от visual-side (визуальные поля отсутствуют по определению); художественный визуал (FORM + VISUAL_KNOWLEDGE + genome) — без provenance к книге и без канонических ID. Это и есть ответ на вопрос «откуда знание берётся»: сегодня визуальный образ мира берётся **от ARTISTIC_MODEL-слоя, который ни к канону, ни друг к другу не привязан**.

## 5. Вопросы, которые аудит ставит перед владельцем (не технические решения)

1. **Консолидация слоёв:** единая «описательная модель сущности» (places/people/buildings/objects/cultures + relations + temporal + claims + provenance) — её **каркас уже существует в трёх местах** (ext-model, FORM, VISUAL_KNOWLEDGE). Решение: (а) выбрать один слой как canonical target и дублировать остальные в него; (б) явно развести роли (ext-model = знание, FORM = шаблоны-формы, VISUAL_KNOWLEDGE = профили сущностей) и создать мосты. Это продуктовое/архитектурное решение.
2. **Fail-open дефект дефолтов EnvironmentContext** (`clear/late summer/cool/still`): для перехода на «unknown, если нет знания» нужно менять контракт `EnvironmentContext`/рендер промтов → **требует OWNER-GO** (контракт заморожен PA-F1/MP-F12).
3. **Статус G10** (8 ARTISTIC_MODEL библиотек + FORM без provenance): пока авторский ревю не снят, все визуальные описания — допущения. Решение владельца: подтвердить/поправить или требовать provenance-привязку до публичного использования в медиа.
4. **Модель описания сущности** (вопрос владельца: «что именно мы хотим знать о месте, человеке, архитектуре, одежде…») — рекомендуется принять как **явную схему-контракт** (перечень полей + типы relations + правило unknown-состояний + уровни provenance) ДО наполнения любых 12 эпох. Аудит показал, что без этого наполнение уйдёт в 6 разных словарей.

---

## Приложение: инвентарь полей (фактические структуры)

- **WORLD_MODEL.json:** epoch{id,name,name_ru,order,description,source_level,provenance[]}; location{id,name,name_ru,type,description,epochs_present[],related_entities[],source_level,provenance[]}; event{id,title,description,epoch,location_id,characters_involved[],chapter,order_in_epoch,source_level,provenance[]}; technologies(3), civilizations(4: +values,technologies,religion_ids,related_locations), religions(2: +practices,key_figures), character_relations(5: character→relation→target), causal_rules(4), epoch_parallels(2), characters_living{satya:20,treta:6,dvapara:1}[{character_name,epoch,location_id,status,notes,source_level}].
- **WORLD_MODEL/ ext:** все категории — {id,name,name_ru,category,description,properties{},relationships[],source,source_level,confidence,provenance_category,provenance_notes}. CLIMATE.properties: type/temperature_range/precipitation/seasons. ARCHITECTURE.properties: type/… (5 карточек).
- **FORM:** {id,name,name_ru,category,description,visual_prompt, + era,materials,colors,style,features (arch/clothes), light,fog,wind,particles,time_of_day,color_temperature (weather), action,meaning (body_language)}.
- **LOCATION_VISUALS:** {type,architecture{style,materials,features,age,condition},landscape{terrain,vegetation,water,sky},palette[],atmosphere{default,time_variants{}},sound,symbols[]}.
- **CHARACTER_VISUALS:** {age_range,face,hair,eyes,build,clothing,accessories[],mannerisms,movement,emotional_range,style_constants[]} (3 записи).
- **GENOME CURRENT:** character_visuals_from_kg[73]{character_id,age_range,clothing,color_palette[],accessories[],style_constants[],source}; location_visuals_from_kg[2 дубля]{location_id,type="unknown",architecture=<semantic desc>,atmosphere="",lighting="",palette=["neutral"],source}.
- **VisualContext:** LocationContext, ArchitectureContext, LandscapeContext, EnvironmentContext(**дефолты clear/late summer/cool/still/dawn**), LightingContext, PaletteContext, AtmosphereContext, SymbolContext, CameraContext, StyleContext, EmotionContext, CharacterVisualContext, NegativePrompt + temporal/provenance/source_refs.
- **MediaPlan:** {plan_id, media_kind, intent, structured_prompt, prompt, negative_constraints[], characters[character_id,name,appearance_summary], location[location_id,name,type,architecture_style,landscape_terrain], visual_style, atmosphere, camera, constraints[], source_refs[], temporal_context, provenance[], lineage}.

