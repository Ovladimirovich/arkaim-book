# TEMPORAL LEGACY REFINEMENT — PRE-IMPLEMENTATION DESIGN CHECK

**Тип:** Pre-implementation design verification
**Дата:** 2026-09-15
**Статус:** FINAL — requires owner approval before implementation
**Источник:** `docs/TEMPORAL_LEGACY_FORENSIC_AUDIT.md` (5 proposed tasks)
**Метод:** Read-only. Фактический код + данные. Никаких изменений.

---

## Простыми словами

1. **Что было целью?** — Проверить, действительно ли 5 предложенных задач нужны, можно ли решить их проще, и не создаёт ли предложенное решение лишнюю архитектуру.

2. **Что реально сделано?** — Прочитаны фактические данные (17 событий, 27 персонажей, 12 эпох, 60+ тем), проверен каждый proposed change against existing code.

3. **Главный вывод:** Из 5 задач — 2 избыточны (Knowledge Artifact и отдельная модель «Носителя»), 1 требует корректировки (ECHOES), 2 минимальны и безопасны (привязка событий, 4 новых relation типа). Итого: **3 задачи вместо 5**.

4. **Почему Knowledge Artifact избыточна?** — Существующие `TemporalRelation.description` + `provenance` + `CharacterPresence` + themes в genome уже позволяют выразить «Велик несёт Единое Учение» без отдельной модели. Добавление KnowledgeArtifact создаёт дублирующий слой.

5. **Почему модель «Носителя» избыточна?** — `CharacterPresence` + `TemporalRelation` (новый тип CARRIES) + `provenance` достаточны. Отдельная Carrier-модель = дублирование.

---

## A. CURRENT STRUCTURE

### A.1 Real Models

| Модель | Файл | Поля |
|--------|------|------|
| `TemporalNode` | temporal/node.py | id, label, precision, era_id, entity_ids[], event_ids[], provenance[], confidence, bounds, is_anchor |
| `TemporalRelation` | temporal/relation.py | id, source_id, target_id, relation_type, strength, description, provenance[], confidence, epoch, bidirectional |
| `TemporalChain` | temporal/chain.py | id, label, direction, nodes[], relations[], gaps[], provenance[], confidence |
| `TemporalGap` | temporal/gap.py | id, from_node, to_node, reason, evidence_status, candidate_bridges[] |
| `CharacterPresence` | world_model.py | character_name, epoch, location_id, status (alive/awakened/departed/mythic) |
| `CanonicalEvent` | world_model.py | id, title, title_ru, description, epoch, location_id, characters_involved[], chapter, order_in_epoch, source_level, provenance[] |
| `Epoch` | world_model.py | id, name, name_ru, description, order, duration_years, start/end_event, technologies[], civilizations[], source_level, provenance[] |
| `ProvenanceTag` | source_levels.py | source_level, category, source_url, source_title, confidence, added_at, added_by, notes |
| `KnowledgeArtifact` | **НЕ СУЩЕСТВУЕТ** | — |

### A.2 Real Relation Types (Temporal)

12 типов в `TemporalRelationType`:
```
BEFORE, AFTER, OVERLAPS, CONTAINS, CONTAINED_BY,
CONTEMPORARY_WITH, PRECEDES, FOLLOWS,
DEVELOPS_FROM, TRANSFORMS_INTO, COEXISTS_WITH, UNKNOWN
```

**Реально используется в chain building:** Только PRECEDES.
**DEVELOPS_FROM/TRANSFORMS_INTO:** Объявлены, factory methods есть, но ADR зарезервировал для ручного создания через M10.2.
**Остальные 9:** Reverse mappings существуют, но ни один не создаётся автоматически.

### A.3 Real Temporal Nodes

| ID | Label | Provenance | is_anchor |
|----|-------|-----------|-----------|
| temporal_pre_arkaim | До Аркаима | [] | false |
| temporal_кали_юга_и_сати_юга | Кали Юга и Сатья Юга | [] | false |
| temporal_satya_yuga | Сатья Юга (Золотой Век) | [] | false |
| temporal_гиперборейская_линия | Гиперборейская линия | [] | false |
| temporal_treta_yuga | Трета Юга (Серебряный Век) | [] | false |
| temporal_атлантическая_линия | Атлантическая линия | [] | false |
| temporal_dvapara_yuga | Двапара Юга (Бронзовый Век) | [] | false |
| temporal_кали_юга | Кали Юга | [] | false |
| temporal_пробуждение_и_новый_кали_юга_(кали_юга) | Пробуждение и новый Кали Юга | [] | false |
| temporal_kali_yuga | Кали Юга (Тёмный Век) | [] | false |
| temporal_arkaim_era | Эпоха Аркаима | [AUTHOR_CANON, EXTERNAL_SOURCE] | **true** |
| temporal_новый_мировой_порядок | Новый Мировой Порядок | [] | false |
| temporal_today | Современность | [HYPOTHESIS] | false |

**13 узлов. 11 PRECEDES relations (только между соседними эпохами).**

### A.4 Real Events

Все 17 событий — заглушки глав:
- event_000 = "Глава 0" (Аннотация)
- event_001 = "Пролог"
- event_002–event_015 = "Глава 2" – "Глава 15"
- event_016 = "Эпилог"

Все: `epoch="unknown"`, `description=""`, `characters_involved=[]`, `location_id=null`.

**Это НЕ события книги. Это структурные маркеры файлов.** Настоящие события (миграция гипербореев, потоп Океании, строительство Аркаима) существуют в тексте книги и в themes, но НЕ в canonical_events.

### A.5 Real Characters

**WORLD_MODEL.json:** 0 characters_alive (пусто).
**Genome:** 27 персонажей с id, name, aliases, type, archetype, description.

Ключевые:
- char_001: Велик (Великосвет) — main — Военачальник Океании → Учитель
- char_003: Учитель (Архат) — main — Высшее Существо
- char_004: Мирослав (Славный) — main — Наставник Велика
- char_006: Радомир — main — Лидер общины
- char_014: Световит — main — Наставник
- char_017: Великий Учитель Истины — main
- char_020: Любомир — main — Учитель звукознания

---

## B. FIVE TASKS REVIEW

### Task 1: Привязать события к эпохам

**Можно существующим механизмом?** ✅ ДА. CanonicalEvent уже имеет поле `epoch`. Нужно только заполнить данные.

**Что отсутствует?** Ничего в коде. Только данные в WORLD_MODEL.json.

**Расширение?** Нет расширения моделей. Только data migration.

**Новый код?** Нет. Только изменение WORLD_MODEL.json.

**Дублирование?** Нет.

**Тесты:** `test_temporal_routes.py` — добавить проверку `get_temporal_context()` возвращает >0 событий.

**Проблема:** 17 текущих событий — заглушки глав. Нельзя просто привязать "Глава 5" к эпохе — нужно либо заменить на реальные события, либо оставить как есть и не трогать.

**Решение:** НЕ привязывать заглушки. Вместо этого: определить 5-8 РЕАЛЬНЫХ ключевых событий книги (миграция, потоп, строительство, кризис, пробуждение) и добавить их в WORLD_MODEL.json с корректным `epoch` и `provenance=[AUTHOR_CANON]`.

**Простой вариант?** Да — это data-only change, zero code.

---

### Task 2: Добавить 4 relation типа (CARRIES, TRANSMITS_TO, INHERITS_FROM, ECHOES)

**Можно существующим механизмом?** ⚠️ ЧАСТИЧНО.

- `DEVELOPS_FROM` уже означает "A развивается из B" — это близко к INHERITS_FROM
- `TRANSFORMS_INTO` уже означает "A трансформируется в B" — это близко к TRANSMITS_TO
- Но DEVELOPS_FROM/TRANSFORMS_INTO зарезервированы ADR для "будущих качественных переходов, создаваемых ТОЛЬКО человеком через M10.2"
- Нет типа для "A несёт знание B" (CARRIES)
- Нет типа для "A зеркалит B" (ECHOES)

**Что отсутствует?** 4 новых enum значения в TemporalRelationType.

**Расширение?** Да — additive enum extension + factory methods + reverse mappings.

**Новый код?** ~30 строк в relation.py + ~20 строк тестов.

**Дублирование?** See Section C below.

**Тесты:** `test_temporal_model.py` — добавить тесты на новые типы.

**Простой вариант?** Да — это минимальное enum extension.

---

### Task 3: Character cross-reference (mentor/student)

**Можно существующим механизмом?** ⚠️ ЧАСТИЧНО.

- `CharacterPresence` существует, но плоский (нет relations)
- `RelationGraph` существует, но не используется для character→character
- Genome содержит 27 персонажей с описаниями, но без explicit relations

**Что отсутствует?** Поле `relations` в CharacterPresence (или использование существующего RelationGraph).

**Расширение?** Minimal: добавить `relations: list[dict] = []` в CharacterPresence.

**Новый код?** ~10 строк в world_model.py (одно поле).

**Дублирование?** Нет — CharacterPresence не имеет relation-поля.

**Проблема:** CharacterPresence живёт в WORLD_MODEL.json, а персонажи в GENOME. Два разных источника. CharacterPresence пуст (0 записей). Genome содержит 27 персонажей но БЕЗ relations.

**Решение:** Вместо расширения CharacterPresence (пустого), добавить character relations ПРЯМО В GENOME как дополнительное поле в characters[]. Или: наполнить WORLD_MODEL.json characters_alive реальными данными из genome.

**Простой вариант?** Да — data change + одно поле в модели.

---

### Task 4: Зеркальные/параллельные эпохи

**Можно существующим механизмом?** ⚠️ ЧАСТИЧНО.

- ECHOES relation type (из Task 2) покрывает саму связь
- Нужен механизм определения КАКИЕ эпохи зеркалят друг друга
- cause_effect.py уже имеет текстовый паттерн "Зеркальные эпохи"

**Что отсутствует?** Поле `epoch_parallels` в WORLD_MODEL.json.

**Расширение?** Minimal: добавить секцию в WORLD_MODEL.json.

**Новый код?** ~20 строк в world_model.py (Pydantic модель + query method).

**Дублирование?** Нет — ECHOES relation в temporal graph + epoch_parallels в WorldModel = два уровня одной идеи (relation = edge, parallel = metadata).

**Простой вариант?** Да.

---

### Task 5: Knowledge Artifact Model

**Можно существующим механизмом?** ❌ НЕТ — но это НЕ проблема.

**Анализ:**

Проверю, что именно Knowledge Artifact должен выразить:
- "Единое Учение" — это знание, которое передаётся
- "Звукознание" — это практика/наука
- "Ритуал Огня" — это ритуал

**Можно ли выразить существующими средствами?**

ДА, через комбинацию:
1. **Genome themes** уже содержат: "Наследие Учения" (theme_138), "Передача знаний" (theme_115), "Миссия учителя" (theme_013)
2. **TemporalRelation.description** может содержать "knowledge: Единое Учение"
3. **CharacterPresence.relations** (если добавить поле) может содержать `{type: "carries", target: "единое_учение"}`
4. **WorldModelExt** загружает все JSON из WORLD_MODEL/ — можно добавить `KNOWLEDGE_ARTIFACTS.json` как отдельный файл

**Что НЕ может существующий механизм?**
- Отдельная сущность "знание" с собственным ID, типом, provenance
- Query "кто несёт Единое Учение?"
- Query "какие знания передались из эпохи X в Y?"

**Нужно ли это сейчас?**

НЕТ. Потому что:
1. В genome уже есть themes о передаче знаний (7+ тем)
2. TemporalRelation с типом CARRIES + description достаточен для первичного моделирования
3. Knowledge Artifact как отдельная модель — это отдельная будущая задача, когда будет реальный контент для заполнения

**Решение:** ОТЛОЖИТЬ. Вместо Knowledge Artifact: использовать CARRIES relation с description="knowledge: Единое Учение" + provenance. Если в будущем понадобится query "все носители Единого Учения" — тогда добавить модель.

---

## C. SEMANTIC CONTRACT

### Нужны ли все 4 новых типа?

**CARRIES = "A несёт/хранит знание B"**
- Семантика: персонаж несёт учение, практику, традицию
- Пример: Велик CARRIES Единое Учение (description)
- Отличие от DEVELOPS_FROM: DEVELOPS_FROM = "A развилось из B" (эпоха→эпоха). CARRIES = "A хранит B" (персонаж→знание). Совершенно разные домены.
- **НУЖЕН.** Не дублирует DEVELOPS_FROM.

**TRANSMITS_TO = "A передаёт знание B"**
- Семантика: учитель передаёт ученику
- Пример: Учитель TRANSMITS_TO Велик
- Отличие от TRANSFORMS_INTO: TRANSFORMS_INTO = "A трансформировалось в B" (качественное изменение). TRANSMITS_TO = "A передало B" (механизм передачи). Разные семантики.
- **НУЖЕН.** Не дублирует TRANSFORMS_INTO.

**INHERITS_FROM = "A наследует от B"**
- Семантика: потомок/продолжатель наследует от предшественника
- Пример: Аркаимская культура INHERITS_FROM Гиперборейская линия
- Отличие от DEVELOPS_FROM: DEVELOPS_FROM = "развитие" (может быть без наследия). INHERITS_FROM = "наследование" (обязательно есть что наследовать).
- **НУЖЕН.** Но семантически близок к DEVELOPS_FROM. Разница: DEVELOPS_FROM = качественное развитие без обязательной передачи. INHERITS_FROM = получение основы от предшественника.
- **РИСК:** Может создать путаницу с DEVELOPS_FROM. Если выбирать ОДИН — лучше DEVELOPS_FROM (уже существует) + description для уточнения.

**Решение:** INHERITS_FROM **ИЗБЫТОЧЕН**. DEVELOPS_FROM с description="наследие: ..." уже выражает эту семантику. Убрать из milestone.

**ECHOES = "A аналогично/зеркалит B"**
- Семантика: структурное сходство БЕЗ причинности
- Пример: Океания ECHOES Современность (технологии без духовности)
- Отличие от CONTEMPORARY_WITH: CONTEMPORARY_WITH = "существовали одновременно". ECHOES = "структурно похожи, но в разные эпохи".
- **НУЖЕН.** Не дублирует ни один существующий тип.

### Итого: 3 типа вместо 4

| Тип | Статус | Причина |
|-----|--------|---------|
| CARRIES | ✅ НУЖЕН | Персонаж→знание, не дублирует ничего |
| TRANSMITS_TO | ✅ НУЖЕН | Учитель→ученик, не дублирует TRANSFORMS_INTO |
| INHERITS_FROM | ❌ ИЗБЫТОЧЕН | DEVELOPS_FROM + description уже выражает |
| ECHOES | ✅ НУЖЕН | Зеркальность без причинности, уникальная семантика |

---

## D. ONE TEACHING / TRUTH

### Как представить без привязки к народу/религии

**Текущий механизм позволяет:**

1. **Genome themes** уже выражают Единое Учение:
   - theme_138: "Наследие Учения" (strength=0.95)
   - theme_013: "Миссия учителя" (strength=0.7)
   - theme_060: "Передача знаний от Посвящённых" (strength=0.7)
   - theme_115: "Передача знаний" (strength=0.7)

2. **CharacterPresence** (если наполнить из genome) + CARRIES relation:
   ```
   char_017 (Великий Учитель Истины) —[CARRIES]→ "Единое Учение" (description)
   ```

3. **Provenance** автоматически разделяет:
   - AUTHOR_CANON: "В книге описан Великий Учитель Истины"
   - HYPOTHESIS: "Возможно, этот архетип проявляется в разных культурах"
   - EXTERNAL_SOURCE: "Параллели с ведической традицией"
   - RECONSTRUCTION: "На основе археологических данных + канона"

4. **TemporalRelation с CARRIES/TRANSMITS_TO**:
   ```
   char_001 (Велик) —[CARRIES]→ "Единое Учение" (HYPOTHESIS)
   char_003 (Учитель) —[TRANSMITS_TO]→ char_001 (Велик) (AUTHOR_CANON)
   ```

**Не требуется отдельная модель «Единое Учение».** Достаточно:
- CARRIES relation с description="knowledge: Единое Учение"
- Provenance на relation (разделяет канон/гипотезу)
- CharacterPresence как носитель

**Не привязано к народу/религии** потому что:
- CharacterPresence не имеет поля `religion` или `civilization`
- CARRIES relation connects character→knowledge, не character→civilization
- Provenance позволяет одновременно иметь AUTHOR_CANON (из книги) и HYPOTHESIS (интерпретация)

---

## E. HERITAGE

### Как представить передачу и преобразование наследия

**Логика из книги:**
```
сохранено → передано → преобразовано → укреплено → продолжено
```

**Через существующий граф (после добавления 3 relation типов):**

```
char_003 (Учитель) —[TRANSMITS_TO]→ char_001 (Велик)     # передано
char_001 (Велик) —[CARRIES]→ "Единое Учение"              # сохранено
temporal_arkaim_era —[DEVELOPS_FROM]→ temporal_satya_yuga  # преобразовано (эпоха развилась)
char_001 —[TRANSMITS_TO]→ char_004 (Мирослав)             # передано следующему
```

**Различие трёх типов:**

| Тип | Семантика | Пример | Domain |
|-----|-----------|--------|--------|
| CARRIES | Хранит/несёт знание | Велик CARRIES Учение | character→knowledge |
| TRANSMITS_TO | Передаёт другому | Учитель TRANSMITS_TO Велик | character→character |
| DEVELOPS_FROM | Развивается из основы | Аркаим DEVELOPS_FROM Гиперборея | epoch→epoch |

**Три типа НЕ дублируют друг друга** — работают в разных доменах (character, knowledge, epoch).

**Преобразование наследия** выражается через:
- DEVELOPS_FROM (epoch→epoch): "Аркаим развился из гиперборейской традиции"
- CARRIES с обновлённым description: "Потомок CARRIES 'Учение в преобразованной форме'"
- Provenance: HYPOTHESIS для "преобразованной формы" (не канон, пока не подтверждено)

---

## F. TEMPORAL MIRRORING

### Как представить аналогию без ложной причинности

**ECHOES = структурное сходство, НЕ причинность.**

**Уровень:** Epoch ↔ Epoch (не event↔event, не state↔state).

**Почему epoch level:**
- Состояние цивилизации определяется эпохой, не отдельным событием
- "Океания: технологии без духовности" = состояние эпохи
- "Современность: технологии без духовности" = состояние эпохи
- Связь = ECHOES между эпохами

**Не event↔event** потому что:
- События слишком конкретны (потоп ≠ климатический кризис)
- Сходство на уровне эпох более точно отражает идею книги

**Не state↔state** потому что:
- Нет модели "состояния" в текущем коде
- Epoch уже содержит description, technologies, civilizations — это и есть "состояние"

**Пример:**
```python
TemporalRelation(
    source_id="temporal_атлантическая_линия",  # Океания
    target_id="temporal_today",                 # Современность
    relation_type=TemporalRelationType.ECHOES,
    description="технологии без духовности",
    provenance=[ProvenanceTag(
        category=ProvenanceCategory.HYPOTHESIS,
        notes="structural parallel, not historical causation"
    )],
    confidence=0.5,
)
```

**ECHOES НЕ участвует в chain building** (только PRECEDES участвует). ECHOES — контекстная связь, не часть хронологической оси.

**Не создаёт ложной причинности** потому что:
- Provenance = HYPOTHESIS (не AUTHOR_CANON)
- description явно указывает "structural parallel"
- Не участвует в chain/forward/backward reconstruction

---

## G. 17 EVENTS

### Фактическое состояние

Все 17 событий в WORLD_MODEL.json — заглушки глав:

| ID | title_ru | chapter | epoch | characters | description | Можно привязать? |
|----|----------|---------|-------|-----------|-------------|-----------------|
| event_000 | Глава 0 (Аннотация) | 0 | unknown | [] | "" | ❌ Не событие |
| event_001 | Пролог | 1 | unknown | [] | "" | ⚠️ "Космический импульс → пробуждение носителя" — epoch=pre_arkaim? |
| event_002 | Глава 2 | 2 | unknown | [] | "" | ❌ Без данных |
| event_003 | Глава 3 | 3 | unknown | [] | "" | ❌ Без данных |
| event_004 | Глава 4 | 4 | unknown | [] | "" | ❌ Без данных |
| event_005 | Глава 5 | 5 | unknown | [] | "" | ❌ Без данных |
| event_006 | Глава 6 | 6 | unknown | [] | "" | ❌ Без данных |
| event_007 | Глава 7 | 7 | unknown | [] | "" | ❌ Без данных |
| event_008 | Глава 8 | 8 | unknown | [] | "" | ❌ Без данных |
| event_009 | Глава 9 | 9 | unknown | [] | "" | ❌ Без данных |
| event_010 | Глава 10 | 10 | unknown | [] | "" | ❌ Без данных |
| event_011 | Глава 11 | 11 | unknown | [] | "" | ❌ Без данных |
| event_012 | Глава 12 | 12 | unknown | [] | "" | ❌ Без данных |
| event_013 | Глава 13 | 13 | unknown | [] | "" | ❌ Без данных |
| event_014 | Глава 14 | 14 | unknown | [] | "" | ❌ Без данных |
| event_015 | Глава 15 | 15 | unknown | [] | "" | ❌ Без данных |
| event_016 | Эпилог | 16 | unknown | [] | "" | ⚠️ Завершение — epoch=пробуждение? |

### Решение

**НЕ привязывать заглушки.** Вместо этого: **заменить** 17 заглушек на 5-8 реальных ключевых событий книги с корректными provenance.

**Реальные события из книги (из BOOK_DOCUMENT.json, genome themes, BOOK_PROFILE):**

| Событие | Epoch | Provenance | Источник |
|---------|-------|-----------|----------|
| Космический импульс и пробуждение носителя | pre_arkaim | AUTHOR_CANON | Пролог книги |
| Расцвет Гипербореи | satya_yuga | AUTHOR_CANON | Главы 1-3 |
| Упадок Океании | okeaniya | AUTHOR_CANON | Главы 4-6 |
| Великий потоп | okeaniya | AUTHOR_CANON | Главы 7-8 |
| Миграция гипербореев | giperboreya_emigration | AUTHOR_CANON | Главы 9-10 |
| Строительство Аркаима | arkaim_era | AUTHOR_CANON | Главы 11-12 |
| Наступление Кали Юги | kali_yuga | AUTHOR_CANON | Главы 13-14 |
| Пробуждение | probuzhdenie | AUTHOR_CANON | Эпилог |

**Provenance:** Все AUTHOR_CANON — события прямо описаны в книге.

**Критерий:** Заменить заглушки ТОЛЬКО если chapter-привязка однозначна из текста. Если нет — не добавлять.

---

## H. TRACE RESULTS

### Trace A: Носитель → ученик → наследие → поколение

**Ожидание:** Учитель → Велик → Учение → Мирослав → следующее поколение

**Факт:**
- char_003 (Учитель) существует в genome
- char_001 (Велик) существует в genome
- Связь между ними: **НЕТ** (нет relation в genome, CharacterPresence пуст)
- CARRIES relation: **НЕ СУЩЕСТВУЕТ** (тип не объявлен)
- TRANSMITS_TO relation: **НЕ СУЩЕСТВУЕТ**

**Цепочка обрывается на:** Отсутствие character relations. CharacterPresence пуст. Genome не содержит relation-полей.

**Минимальный structural gap:** Добавить CARRIES + TRANSMITS_TO в TemporalRelationType. Заполнить character relations в genome или WORLD_MODEL.json.

---

### Trace B: Гиперборейская линия → последующее развитие

**Ожидание:** satya_yuga → giperboreya_line → arkaim_era → kali_yuga

**Факт:**
- temporal_satya_yuga существует
- temporal_гиперборейская_линия существует
- temporal_arkaim_era существует (provenance=[AUTHOR_CANON, EXTERNAL_SOURCE])
- PRECEDES relations между соседними: ✅
- DEVELOPS_FROM между satya_yuga и arkaim_era: **НЕТ** (только PRECEDES)
- INHERITS_FROM: **НЕТ** (тип не объявлен)

**Цепочка обрывается на:** Только PRECEDES связи. Нет DEVELOPS_FROM для качественных переходов. ADR запрещает автоматическое создание DEVELOPS_FROM.

**Минимальный structural gap:** Ручное создание DEVELOPS_FROM relation через M10.2 workflow (editor+).

---

### Trace C: Атлантида → состояние эпохи → современность

**Ожидание:** okeaniya (технологии без духовности) → ECHOES → today (сходное состояние)

**Факт:**
- temporal_атлантическая_линия существует
- temporal_today существует (provenance=HYPOTHESIS)
- ECHOES relation: **НЕ СУЩЕСТВУЕТ** (тип не объявлен)
- CONTEMPORARY_WITH: существует но означает "одновременность", не "зеркальность"

**Цепочка обрывается на:** Отсутствие ECHOES типа.

**Минимальный structural gap:** Добавить ECHOES в TemporalRelationType + создать relation между атлантической_линией и today.

---

### Trace D: Arkaim → исторические проявления → TODAY

**Ожидание:** arkaim_era → синташта/гардарика → исторические народы → today

**Факт:**
- temporal_arkaim_era: provenance=[AUTHOR_CANON, EXTERNAL_SOURCE], is_anchor=true
- ARCHAEOLOGY.json: Синташта, Гардарика, Мехенго описаны
- Но: archaeology данные НЕ в temporal graph — они в ArkaimAnchor.provenance
- Связь arkaim_era→today: **НЕТ** в графе (ADR Decision A: computed path only)
- BACKWARD от temp today через BFS: находит arkaim_era через reverse PRECEDES — это работает

**Цепочка работает** через computed path (BACKWARD reconstruction). Нет structural gap.

**Но:** "Исторические проявления" (Синташта как потомок) не в графе — это отдельные данные в ARCHAEOLOGY.json, не temporal relations.

**Минимальный structural gap:** Нет. Computed path работает. Детализация (Синташта как отдельный node) — отдельная будущая задача.

---

### Trace E: Внешний культурный носитель (HYPOTHESIS)

**Ожидание:** Единое Учение → проявляется в Ведах → HYPOTHESIS provenance

**Факт:**
- Religion model: веды существуют в WORLD_MODEL/CIVILIZATIONS.json
- Character "Великий Учитель Истины" (char_017) существует в genome
- CARRIES relation: **НЕТ** (тип не объявлен)
- Provenance HYPOTHESIS: ✅ существует и работает

**Цепочка обрывается на:** Отсутствие CARRIES типа.

**Минимальный structural gap:** Добавить CARRIES. Затем:
```
char_017 —[CARRIES]→ "Единое Учение" (AUTHOR_CANON)
"Ведическая традиция" —[ECHOES]→ "Единое Учение" (HYPOTHESIS)
```

---

## I. MINIMAL IMPLEMENTATION PLAN

### Scope

**3 задачи вместо 5.** Две задачи отложены (Knowledge Artifact — избыточна; INHERITS_FROM — дублирует DEVELOPS_FROM).

### Task 1: Add 3 relation types (CARRIES, TRANSMITS_TO, ECHOES)

**Файл:** `core/CORE/narrative_engine/temporal/relation.py`

**Изменения:**
- Добавить 3 значения в `TemporalRelationType`:
  ```python
  CARRIES = "CARRIES"           # A несёт/хранит знание B
  TRANSMITS_TO = "TRANSMITS_TO" # A передаёт знание B
  ECHOES = "ECHOES"             # A зеркалит/аналогично B (без причинности)
  ```
- Добавить 3 записи в `REVERSE_RELATIONS`:
  ```python
  CARRIES: CARRIED_BY,
  TRANSMITS_TO: RECEIVES_FROM,
  ECHOES: ECHOES,
  ```
- Добавить 3 новых reverse типа: `CARRIED_BY`, `RECEIVES_FROM` (ECHOES — self-reverse)
- Factory methods: `carries()`, `transmits_to()`, `echoes()` — все с HYPOTHESIS provenance по умолчанию

**Тесты:** `runtime/tests/test_temporal_model.py` — 6 новых тестов (reverse map, factory methods, roundtrip)

**НЕ затрагивает:** Chain building (только PRECEDES), existing 644 tests, ADR decisions.

---

### Task 2: Replace 17 event stubs with real events

**Файл:** `core/CORE/narrative_engine/data/WORLD_MODEL.json`

**Изменения:**
- Заменить `canonical_events` на 5-8 реальных событий:
  ```json
  {
    "id": "event_awakening",
    "title_ru": "Пробуждение носителя",
    "epoch": "pre_arkaim",
    "chapter": 1,
    "characters_involved": ["Велик"],
    "source_level": "CANON",
    "provenance": [{"category": "AUTHOR_CANON", "source_level": "CANON"}]
  }
  ```
- Каждое событие: корректный epoch, characters (из genome), provenance=[AUTHOR_CANON]
- ТОЛЬКО события, chapter-привязка которых однозначна из текста

**Тесты:** `runtime/tests/test_temporal_routes.py` — проверить `get_context()` возвращает >0 событий для ≥2 эпох

**НЕ затрагивает:** Модели, код, relation types.

---

### Task 3: Add epoch parallels + character relations (data-only)

**Файлы:**
- `core/CORE/narrative_engine/data/WORLD_MODEL.json` — добавить `epoch_parallels` секцию
- `core/CORE/narrative_engine/world_model.py` — добавить `EpochParallel` Pydantic модель + `get_epoch_parallels()` method

**Изменения в world_model.py:**
```python
class EpochParallel(BaseModel):
    source: str       # epoch ID
    target: str       # epoch ID
    description: str = ""
    provenance: list[ProvenanceTag] = []

# В WorldModel:
epoch_parallels: list[EpochParallel] = []

def get_epoch_parallels(self) -> list[EpochParallel]:
    return self.epoch_parallels
```

**WORLD_MODEL.json:**
```json
"epoch_parallels": [
  {
    "source": "атлантическая_линия",
    "target": "пробуждение_и_новый_кали_юга_(кали_юга)",
    "description": "технологии без духовности",
    "provenance": [{"category": "HYPOTHESIS", "notes": "structural parallel"}]
  }
]
```

**Character relations:** Добавить в genome `characters[].relations`:
```json
{
  "id": "char_003",
  "name": "Учитель",
  "relations": [
    {"type": "mentor_of", "target": "char_001", "provenance": "AUTHOR_CANON"}
  ]
}
```

**Тесты:** `runtime/tests/test_narrative_world_model.py` — 4 новых теста (EpochParallel load, get_epoch_parallels, character relations roundtrip)

**НЕ затрагивает:** Chain building, existing tests, ADR decisions.

---

### What's NOT in this milestone

| Что | Почему исключено |
|-----|-----------------|
| Knowledge Artifact Model | Избыточна — CARRIES relation + description + themes уже выражают |
| INHERITS_FROM relation | Дублирует DEVELOPS_FROM + description |
| TemporalEngine service | Не нужен — ReconstructionEngine достаточен |
| Графовая БД | Не нужна — JSON persistence достаточна |
| Автоматическое обнаружение зеркальных эпох | Ручное через epoch_parallels |
| LLM-генерация events | Ручное создание |
| Интеграция RelationGraph + TemporalGraph | Отдельный будущий этап |
| Изменение ADR Decision A/B/C/D | Milestone работает внутри |

---

### Acceptance Criteria

1. **3 новых типа** в TemporalRelationType (CARRIES, TRANSMITS_TO, ECHOES) с reverse mappings и factory methods
2. **5-8 реальных событий** в WORLD_MODEL.json с корректным epoch, characters, provenance
3. **≥1 ECHOES relation** в epoch_parallels с HYPOTHESIS provenance
4. **Character relations** в genome (≥3 связи)
5. **Все существующие 644 теста** не сломаны
6. **≥10 новых тестов** для новых типов и данных
7. **`get_temporal_context()`** возвращает >0 событий для ≥2 эпох

### Files Changed

| Файл | Тип изменения |
|------|--------------|
| `core/CORE/narrative_engine/temporal/relation.py` | +3 enum values + 3 reverse types + 3 factory methods |
| `core/CORE/narrative_engine/world_model.py` | +1 Pydantic model (EpochParallel) + 1 field + 1 method |
| `core/CORE/narrative_engine/data/WORLD_MODEL.json` | Replace events + add epoch_parallels |
| `core/GENOME/GENOME_v1.0.0.json` | Add character relations |
| `runtime/tests/test_temporal_model.py` | +6 tests |
| `runtime/tests/test_narrative_world_model.py` | +4 tests |
| `runtime/tests/test_temporal_routes.py` | +2 tests |

**Total: 7 files, ~80 строк нового кода, ~12 новых тестов.**

---

**STOP — PRE-IMPLEMENTATION DESIGN CHECK COMPLETE. Жду утверждения минимального milestone.**
