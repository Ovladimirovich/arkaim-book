# FORENSIC AUDIT — Temporal/Event/Legacy Mechanism of Arkaim

**Тип:** Forensic audit + refinement milestone proposal
**Дата:** 2026-09-15
**Статус:** FINAL — requires owner decision
**Объект:** Temporal chains, events, relations, provenance, carriers, legacy, transmission, mirror epochs
**Метод:** Read-only. Четыре независимых чтения кода (temporal/, world_model, genome, tests). Сверка с ADR_TEMPORAL_WORLD_MODEL (ACCEPTED), TEMPORAL_API_ALIGNMENT_FORENSIC_AUDIT (PASS WITH FINDINGS), 499 тестов. Никаких изменений в коде.

---

## Простыми словами

1. **Что было целью?** — Проверить, может ли текущий механизм Arkaim моделировать не просто линейную хронологию эпох, а сложные связи книги: наследие, носителей знания, передачу через поколения, повторяющиеся состояния эпох, связь прошлого с современностью.

2. **Что реально сделано?** — Прочитаны 12 файлов temporal-пакета, world_model, genome (4796 строк), 14 тест-файлов (499 тестов), 6 ADR/audit документов. Проведены 5 реальных трассировок книжных линий через код.

3. **Что получилось?** — Система УМЕЕТ строить линейную хронологию эпох с provenance. НЕ УМЕЕТ моделировать носителей знания, передачу через поколения, зеркальные эпохи и наследие как самостоятельную сущность. Планировщики (cause_effect.py) знают про эти концепции, но как текстовые шаблоны — не как структуры графа.

4. **Есть ли проблемы?** — Одна критическая: события (17 штук) все привязаны к `epoch: "unknown"` — фактически не привязаны ни к чему. Типы связей DEVELOPS_FROM/TRANSFORMS_INTO объявлены, но нигде не создаются в данных. 5 из 8 типов world-relations никогда не извлекаются.

5. **Что предлагается?** — Один refinement milestone (TEMPORAL_LEGACY_REFINEMENT) без нового архитектурного разрастания. Подробности в разделе F.

---

## A. FACTUAL CURRENT STATE

### A.1 Temporal Package (`core/CORE/narrative_engine/temporal/`)

| Компонент | Файл | Строк | Что делает |
|-----------|------|-------|-----------|
| TemporalNode | node.py | 215 | Узел графа: id, label, precision, era_id, entity_ids, event_ids, provenance, confidence, bounds, is_anchor |
| TemporalRelation | relation.py | 217 | Связь: 12 типов (BEFORE→UNKNOWN), reverse map, factory methods для PRECEDES/DEVELOPS_FROM/TRANSFORMS_INTO/CONTEMPORARY_WITH |
| TemporalChain | chain.py | 197 | Направленный граф: BACKWARD/FORWARD/BI_DIRECTIONAL, nodes[], relations[], gaps[] |
| TemporalGraph | graph.py | 171 | BFS/DFS обход, add_node/relation, get_neighbors, bfs_path, all_paths |
| TemporalGap | gap.py | 134 | Пробел: 6 статусов (DOCUMENTED→UNKNOWN), candidate_bridges |
| ReconstructionPath | reconstruction_path.py | 129 | Результат обхода: nodes + relations + gaps + provenance |
| PathValidator | path_validator.py | 249 | 7 правил валидации: node_missing, relation_missing, direction_conflict, temporal_conflict, provenance_downgrade, self_loop, cycle |
| ArkaimAnchor | arkaim_anchor.py | 127 | Специальный якорь: AUTHOR_CANON + EXTERNAL_SOURCE provenance |
| PresentAnchor | present_anchor.py | 92 | **ORPHANED** — не используется основным пайплайном |
| Precision | precision.py | 110 | 10 уровней точности датирования |
| ReconstructionEngine | reconstruction_engine.py | 691 | **ЯДРО**: from_world_model(), BFS, gap detection, provenance computation, persistence |
| FutureExtrapolator | future_extrapolator.py | 293 | Детерминированные сценарии будущего из шаблонов |

### A.2 World Model (`world_model.py`, 458 строк)

**Pydantic-модели (7):** Epoch, Location, Civilization, Technology, Religion, CharacterPresence, CanonicalEvent, CausalRule

**Данные WORLD_MODEL.json (фактические):**
- 12 эпох (от pre_arkaim до recon_era)
- 17 canonical_events — **ВСЕ с `epoch: "unknown"`**, пустые descriptions, пустые characters_involved
- ~25 персонажей (CharacterPresence) — привязаны к эпохам, статус alive/awakened/departed/mythic
- Локации, цивилизации, технологии, религии

### A.3 Relation Layers (3 независимых слоя)

| Слой | Тип | Файл | Всего типов | Реально используется |
|------|-----|------|-------------|---------------------|
| World Relations | relation_models.py | 8 типов | GEOGRAPHIC, HISTORICAL, MYTHOLOGICAL + 5 пустых | 3 из 8 |
| Temporal Relations | temporal/relation.py | 12 типов | PRECEDES (ось) + 11 объявленных | 1 из 12 |
| Knowledge Graph | knowledge_graph/populate.py | 3 типа | embodies, related_to, conflicts_with | 3 из 3 |

### A.4 Provenance System (`source_levels.py`, 320 строк)

**Два измерения в одном ProvenanceTag:**
- ProvenanceCategory (8): AUTHOR_CANON → DERIVED → EXTERNAL_SOURCE → RECONSTRUCTION → HYPOTHESIS → ARTISTIC_MODEL → FUTURE_EXTRAPOLATION → UNKNOWN
- SourceLevel (7): CANON=1.0 → USER_HYPOTHESIS=0.3

**Инварианты (реализованы и протестированы):**
- AUTHOR_CANON не может быть перезаписан
- DERIVED не может быть повышен до AUTHOR_CANON
- Confidence НЕ повышает категорию (HYPOTHESIS с confidence=1.0 = HYPOTHESIS)
- Path provenance = lowest common denominator

### A.5 API Endpoints (`routes/temporal.py`, 261 строка)

| Endpoint | Что делает |
|----------|-----------|
| GET /book/temporal/chain | Цепочка из WorldModel (M4), C1 enrichment arkaim_era |
| GET /book/temporal/node/{epoch_id} | Один узел |
| GET /book/temporal/context/{epoch_id} | Контекст: узел + события + персонажи + технологии |
| POST /book/temporal/reconstruct | Путь между узлами (M3 engine) |
| GET /book/temporal/chains | BACKWARD + FORWARD цепочки |
| GET /book/temporal/nodes | Все узлы + temporal_today (B1) |
| POST /book/temporal/future-extrapolation | Сценарии будущего (M8) |

### A.6 Test Coverage

**14 файлов, 499 тестов.** Покрытие:
- ✅ TemporalNode, TemporalRelation, TemporalChain (63 теста)
- ✅ ReconstructionEngine, PathValidator (55 тестов)
- ✅ Provenance: категории, теги, реестр, канон-защита (55 тестов)
- ✅ M8.1 Present Anchor (32 теста)
- ✅ M9 Expansion Temporal (38 тестов)
- ✅ M10 Temporal Updates (24 теста)
- ⚠️ RelationGraph — только 3 базовых теста
- ❌ CanonicalEvents — 0 dedicated тестов
- ❌ FutureExtrapolator — 0 unit тестов (только через M8.1 integration)
- ❌ CAUSAL/PHILOSOPHICAL/SYMBOLIC/CULTURAL relations — 0 тестов (не извлекаются)

---

## B. BOOK MODEL MAPPING

### B.1 Что книга моделирует (из genome + WORLD_MODEL + themes)

| Концепция книги | Есть в данных | Есть в коде | Фактически работает |
|-----------------|---------------|-------------|-------------------|
| Эпохи/циклы | ✅ 6 эпох в genome, 12 в WORLD_MODEL | ✅ Epoch model, TemporalNode | ✅ Линейная цепочка PRECEDES |
| Две цивилизации (Гиперборея/Океания) | ✅ civilization_profiles.json | ✅ Civilization model | ⚠️ Не привязаны к temporal graph |
| Персонажи/герои | ✅ 25+ в genome | ✅ CharacterPresence | ⚠️ Плоские, без связей между собой |
| Носители знания (Учитель→ученики) | ✅ 7+ тем в genome | ❌ Нет модели носителя | ❌ Невозможно представить |
| Передача Учения | ✅ 6+ тем (theme_013, 060, 115) | ❌ Нет relation типа | ❌ Невозможно представить |
| Наследие через поколения | ✅ 5+ тем (theme_134, 136, 138) | ❌ Нет модели наследия | ❌ Невозможно представить |
| Зеркальные эпохи | ✅ cause_effect.py pattern | ❌ Нет relation в графе | ❌ Только текстовый шаблон |
| Связь с современностью | ✅ temporal_today | ✅ Present Anchor | ⚠️ Узел есть, но БЕЗ связей |
| Будущие сценарии | ✅ FutureExtrapolator | ✅ Шаблоны + CompatibilityChecker | ✅ Работает (FUTURE_EXTRAPOLATION) |
| События | ✅ 17 в WORLD_MODEL | ✅ CanonicalEvent model | ❌ Все с epoch="unknown" |
| Археология | ✅ ARCHAEOLOGY.json | ✅ EXTERNAL_SOURCE provenance | ✅ Обогащает arkaim_era |

### B.2 Ключевой разрыв

**Планировщики (cause_effect.py) ЗНАЮТ про:**
- "Герой становится хранителем знания"
- "Предки передают мудрость через поколения"
- "Зеркальные эпохи: светлая → упадок"
- "Нынешнее поколение осознаёт наследие"

**Но это ТЕКСТОВЫЕ ШАБЛОНЫ, не структуры графа.** Между планировщиком и temporal model нет моста.

---

## C. GAPS

### C.1 Critical Gaps (блокируют моделирование ключевых линий книги)

**GAP-1: События не привязаны к эпохам**
- 17 canonical_events все с `epoch: "unknown"`
- `get_events(epoch_id)` возвращает пустой список для любой эпохи
- `get_temporal_context()` показывает 0 событий
- **Следствие:** временной контекст эпохи не содержит событий — только метаданные эпохи

**GAP-2: Нет модели носителя знания (Carrier)**
- CharacterPresence плоский: character_name, epoch, status
- Нет связи "mentor→student", "teacher→follower"
- Нет cross-epoch tracking ("тот же носитель в другой эпохе")
- Нет knowledge artifact model (ЧТО передаётся: ритуал, текст, символ, практика)
- **Следствие:** Линия A (Учитель→ученики→наследие→поколения) не может быть представлена

**GAP-3: Нет relation типов для передачи/наследия**
- DEVELOPS_FROM/TRANSFORMS_INTO объявлены, но зарезервированы ADR для "будущих качественных переходов, создаваемых ТОЛЬКО человеком через pending-workflow M10.2"
- Нет типов: `transmits`, `carries`, `inherits_from`, `leaves_legacy`, `preserves`
- **Следствие:** нельзя провести линию "знание передаётся от A к B к C"

**GAP-4: Нет модели поколения**
- CharacterPresence не имеет parent/child/mentor/student links
- Нет generational distance
- Нет generational overlap (когда поколения сосуществуют)
- **Следствие:** Линия B (наследие→потомки→преобразование→укрепление) не моделируется

**GAP-5: Нет relation для зеркальных эпох**
- cause_effect.py имеет текстовый паттерн "Зеркальные эпохи"
- В TemporalRelationType нет `mirrors`/`reflects`/`echoes`
- Нет алгоритма обнаружения структурного сходства эпох
- CulturalParallel/MythParallel существуют в context assemblers, но отключены от temporal graph
- **Следствие:** повторяющиеся состояния эпох не могут быть представлены как связи графа

### C.2 Medium Gaps (ухудшают качество, не блокируют)

**GAP-6: 5 из 8 World Relation типов не извлекаются**
- CAUSAL, PHILOSOPHICAL, ARCHAEOLOGICAL, SYMBOLIC, CULTURAL объявлены в RelationType
- relation_extractor.py извлекает только GEOGRAPHIC, HISTORICAL, MYTHOLOGICAL
- **Следствие:** причинно-следственные связи между эпохами/событиями не существуют в графе

**GAP-7: PresentAnchor.py — orphaned**
- present_anchor.py (92 строки) создаёт PresentAnchor с AUTHOR_CANON provenance
- Основной пайплайм использует TemporalNode.present_anchor() (HYPOTHESIS provenance)
- **Следствие:** dead code, потенциальная путаница

**GAP-8: Два независимых graph-слоя**
- RelationGraph (narrative_engine) — 8 типов, JSON persistence
- GraphEngine (knowledge_graph) — 3 типа, in-memory
- Не интегрированы: нельзя провести путь от knowledge-graph entity через temporal relation
- **Следствие:** "персонаж из knowledge graph" и "эпоха из temporal graph" не связаны

**GAP-9: FutureExtrapolator string comparison**
- `rel.relation_type == "PRECEDES"` (строка) вместо `rel.relation_type == TemporalRelationType.PRECEDES` (enum)
- Работает из-за `str, Enum`, но хрупко
- **Следствие:** potential bug при изменении enum

### C.3 Low Gaps

**GAP-10:** TemporalChain не проверяет дубликаты узлов
**GAP-11:** In-memory pending queue (M10.2) теряется при перезапуске
**GAP-12:** No pagination на /nodes, /chain endpoints
**GAP-13:** No temporal-aware spatial queries (эпоха + локация вместе)

---

## D. DRIFT / DUPLICATES

### D.1 Documentation-Code Drift

| Документ | Утверждение | Факт в коде | Статус |
|----------|-------------|-------------|--------|
| ADR_TEMPORAL (§Decision A) | "temporal_today в /nodes" | ✅ Реализовано (B1) | CORRECT |
| ADR_TEMPORAL (§Decision B) | "PRECEDES — единственный тип оси" | ✅ Только PRECEDES в chain building | CORRECT |
| ADR_TEMPORAL (§Decision C) | "arkaim_era provenance-enriched" | ✅ AUTHOR_CANON + EXTERNAL_SOURCE, 0.85 | CORRECT |
| ADR_TEMPORAL (§Decision D) | "arkaim_anchor orphan удалён" | ✅ Удаляется в engine-пути | CORRECT |
| TEMPORAL_API_ALIGNMENT | "12 эпох, 11 relations, 13 nodes" | ✅ Подтверждено | CORRECT |
| STUDIO_SPEC (§17) | "VideoScenario connected to temporal" | ❌ Нет связи | DRIFT |
| CLAUDE.md | "34 страницы" | ⚠️ Включая Studio = 35+ | MINOR DRIFT |

### D.2 Duplicates

| Что | Где дублируется | Проблема |
|-----|----------------|----------|
| PresentAnchor | present_anchor.py + TemporalNode.present_anchor() | Два разных класса с разным provenance (AUTHOR_CANON vs HYPOTHESIS) |
| ArkaimAnchor enrichment | reconstruction_engine.py + routes/temporal.py (C1) | Два отдельных пути обогащения (engine vs API), одинаковая логика |
| Provenance model | narrative_engine/source_levels.py + visual/ (ищется но не найден) | source_levels.py только в narrative_engine — это CORRECT, не дубликат |

### D.3 Redundancy

| Что | Зачем существует | Можно ли убрать |
|-----|-----------------|----------------|
| present_anchor.py | Предлагает AUTHOR_CANON provenance для Present | Да — orphaned, основной пайплайм не использует |
| 5 неиспользуемых WorldRelation типов | Зарезервированы для будущего | Нет — не мешают, нужны для GAP-6 |

---

## E. TRACE RESULTS

### Trace 1: Носитель → ученики → наследие → поколения

**Ожидание:** Велик (character) → Наставники (characters) → Учение (knowledge) → Гипербореи → Аркаим → Кали Юга

**Факт в коде:**
- `CharacterPresence`: Велик = {epoch: "satya_yuga", status: "awakened"}, Наставники = {epoch: "satya_yuga", status: "alive"}
- Связь между ними: **НЕТ** (characters_involved в events пустое, RelationGraph не содержит character→character)
- Учение: **НЕТ** модели (нет knowledge artifact)
- Гипербореи→Аркаим: есть PRECEDES между эпохами, но НЕТ связи через носителей
- **РЕЗУЛЬТАТ: ❌ НЕВОЗМОЖНО.** Система знает что Велик и Наставники существуют, но не знает что между ними есть связь "учитель→ученик"

### Trace 2: Гиперборейская линия → последующее развитие

**Ожидание:** Гиперборея (расцвет) → Океания (упадок) → Гиперборея (эмиграция) → Аркаим → Кали Юга

**Факт в коде:**
- WORLD_MODEL: 12 эпох с PRECEDES связями между соседними
- Civilization "Гиперборея" существует, привязана к эпохам
- DEVELOPS_FROM/TRANSFORMS_INTO: **объявлены, но НИКОГДА не создаются** (ADR запрещает автоматическое создание)
- **РЕЗУЛЬТАТ: ⚠️ ЧАСТИЧНО.** Линейная последовательность эпох есть. Но качественные переходы (расцвет→упадок→эмиграция) НЕ отмечены — только порядок PRECEDES.

### Trace 3: Атлантическая линия → современность/аналогичный мотив

**Ожидание:** Океания (технологии без духовности) → кризис → современность (сходное состояние)

**Факт в коде:**
- Civilization "Океания" существует в profiles
- cause_effect.py имеет паттерн "Зеркальные эпохи" с ключевыми словами
- TemporalRelationType не содержит `mirrors`
- temporal_today существует, но БЕЗ relations к любой эпохе
- **РЕЗУЛЬТАТ: ❌ НЕВОЗМОЖНО.** Система не может провести связь "Океания зеркалит современность". Паттерн есть в текстовых шаблонах, но не в графе.

### Trace 4: Аркаим → исторические проявления → TODAY

**Ожидание:** Аркаим (4000 до н.э.) → Синташта → исторические народы → современные проявления → TODAY

**Факт в коде:**
- arkaim_era: provenance=[AUTHOR_CANON, EXTERNAL_SOURCE], confidence=0.85, is_anchor=true
- ARCHAEOLOGY.json: Синташта, Гардарика, Мехенго — описаны, привязаны к arkaim_era
- К FORWARD цепочке от arkaim_era: ведёт через PRECEDES к satya_yuga, treta_yuga... → recon_era
- temporal_today: существует, но БЕЗ связи к arkaim_era (ADR Decision A: "точка наблюдения без relations")
- BACKWARD от temporal_today: BFS находит arkaim_era через reverse relations (computed path)
- **РЕЗУЛЬТАТ: ⚠️ ЧАСТИЧНО.** Хронологическая цепочка есть. Археологическое подтверждение есть. Но "исторические проявления" (Синташта как потомок Аркаима) не представлены — только эпохи, не конкретные связи.

### Trace 5: Внешний культурный носитель (гипотеза)

**Ожидание:** Учение Истины → проявляется в разных культурных формах → Веды, Зороастризм, и т.д.

**Факт в коде:**
- Religion model: есть (веды, зороастризм в profiles)
- Персонажи-носители: CharacterPresence не имеет cross-epoch links
- Provenance: HYPOTHESIS/RECONSTRUCTION категории существуют
- M10.2 pending-workflow: позволяет предлагать новые связи (confirm/reject)
- **РЕЗУЛЬТАТ: ⚠️ ЧАСТИЧНО.** Инфраструктура для гипотез есть (provenance, M10.2). Но модели "Учение проявляется в форме X" нет — нет knowledge artifact, нет relation "manifests_as".

---

## F. MINIMAL REFINEMENT MILESTONE

### TEMPORAL_LEGACY_REFINEMENT

**Цель:** Расширить существующий temporal/event механизм минимальными изменениями, чтобы система могла моделировать: (1) события внутри эпох, (2) связи между персонажами (mentor/student/peer), (3) зеркальные/параллельные эпохи, (4) наследие как самостоятельную сущность. Без новой архитектуры, без TemporalEngine сервиса, без графовой БД.

**Принцип:** Каждое изменение расширяет существующий dataclass/enum на несколько полей/значений. Никаких новых файлов-координаторов, никаких новых singleton-сервисов.

### F.1 Задача 1: Привязать события к эпохам

**Проблема:** 17 canonical_events все с `epoch: "unknown"`, `get_events()` возвращает пустой список.

**Изменения:**
- Файл: `core/CORE/narrative_engine/WORLD_MODEL.json` — проставить `epoch` каждому событию из chapter context
- Файл: `core/CORE/narrative_engine/world_model.py` — CanonicalEvent уже имеет поле `epoch`, никаких изменений модели
- Тесты: `runtime/tests/test_temporal_routes.py` — добавить проверку `get_temporal_context("arkaim_era").event_count > 0`

**Критерий ACCEPTED:** `get_temporal_context("arkaim_era")` возвращает ≥3 события. `get_events(epoch_id)` не пуст для ≥3 эпох.

### F.2 Задача 2: Добавить relation типы для наследия и передачи

**Проблема:** DEVELOPS_FROM/TRANSFORMS_INTO зарезервированы ADR. Нет типов для "носит", "передаёт", "наследует".

**Изменения:**
- Файл: `core/CORE/narrative_engine/temporal/relation.py` — добавить 4 типа в TemporalRelationType:
  ```
  CARRIES       = "CARRIES"         # A несёт знание B (character→knowledge)
  TRANSMITS_TO  = "TRANSMITS_TO"    # A передаёт знание B→C (teacher→student)
  INHERITS_FROM = "INHERITS_FROM"   # A наследует от B (descendant→ancestor)
  ECHOES        = "ECHOES"          # A зеркалит/повторяет B (epoch↔epoch, hypothesis)
  ```
- Обновить REVERSE_RELATIONS: CARRIES→CARRIED_BY, TRANSMITS_TO→RECEIVES_FROM, INHERITS_FROM→LEAVES_TO, ECHOES→ECHOES
- Factory methods: `carries()`, `transmits_to()`, `inherits_from()`, `echoes()` — все с HYPOTHESIS provenance по умолчанию
- **ADR Decision B не нарушен:** PRECEDES остаётся единственным типом ОСИ. Новые типы — контекстные связи ВНЕ оси.
- Тесты: `runtime/tests/test_temporal_model.py` — добавить тесты на новые типы, reverse map, factory methods

**Критерий ACCEPTED:** Все 4 новых типа в TemporalRelationType. REVERSE_RELATIONS содержит обратные. Factory methods создают HYPOTHESIS provenance. Существующие 499 тестов не сломаны.

### F.3 Задача 3: Character cross-reference через relation

**Проблема:** CharacterPresence плоский, нет mentor/student/peer links.

**Изменения:**
- Файл: `core/CORE/narrative_engine/world_model.py` — добавить поле в CharacterPresence:
  ```python
  relations: list[dict] = []  # [{"type": "mentor_of", "target": "char_name", "provenance": [...]}]
  ```
- Типы character relations: `mentor_of`, `student_of`, `peer_of`, `predecessor_of`, `successor_of`, `contemporary_of`
- Не требует миграции: поле по умолчанию пустой список
- WORLD_MODEL.json: добавить несколько ключевых связей (Велик→Наставники: mentor_of, и т.д.)
- Тесты: `runtime/tests/test_narrative_world_model.py` — тест roundtrip с relations, тест query "who mentored X"

**Критерий ACCEPTED:** CharacterPresence сериализуется с relations. ≥3 связи в WORLD_MODEL.json. Query "кто наставил Велика?" возвращает результат.

### F.4 Задача 4: Зеркальные/параллельные эпохи

**Проблема:** cause_effect.py знает про зеркальные эпохи, но temporal graph не имеет связи.

**Изменения:**
- Файл: `core/CORE/narrative_engine/WORLD_MODEL.json` — добавить section `epoch_parallels`:
  ```json
  "epoch_parallels": [
    {"source": "okeaniya", "target": "recon_era", "type": "ECHOES", "description": "технологии без духовности", "provenance": "HYPOTHESIS"}
  ]
  ```
- Файл: `core/CORE/narrative_engine/world_model.py` — добавить:
  ```python
  class EpochParallel(BaseModel):
      source: str
      target: str
      type: str = "ECHOES"
      description: str = ""
      provenance: list[ProvenanceTag] = []
  ```
  + `get_epoch_parallels()` method
- Файл: `reconstruction_engine.py` — в `from_world_model()` добавить создание ECHOES relations из epoch_parallels (с HYPOTHESIS provenance)
- Тесты: `runtime/tests/test_temporal_integration.py` — тест что ECHOES relation создаётся, provenance = HYPOTHESIS

**Критерий ACCEPTED:** ≥1 ECHOES relation в temporal graph. Provenance = HYPOTHESIS. Не нарушает PRECEDES-ось (ECHOES не участвует в chain building).

### F.5 Задача 5: Knowledge artifact model (минимальный)

**Проблема:** Система не может представить ЧТО передаётся (Учение, ритуал, символ).

**Изменения:**
- Файл: `core/CORE/narrative_engine/world_model.py` — добавить:
  ```python
  class KnowledgeArtifact(BaseModel):
      id: str
      name: str
      name_ru: str
      artifact_type: str  # "teaching", "ritual", "symbol", "practice", "text"
      description: str = ""
      origin_epoch: str = ""
      provenance: list[ProvenanceTag] = []
  ```
  + поле `knowledge_artifacts: list[KnowledgeArtifact] = []` в WorldModel
  + `get_artifacts()`, `get_artifacts_for_epoch()` methods
- WORLD_MODEL.json: добавить 2-3 ключевых артефакта (Единое Учение, Звукознание, Ритуал Огня)
- CARRIES/TRANSMITS_TO relations привязываются к artifact ID через TemporalRelation.description
- Тесты: `runtime/tests/test_narrative_world_model.py` — тест load/serialize artifacts, query by epoch

**Критерий ACCEPTED:** ≥2 KnowledgeArtifact в WORLD_MODEL.json. `get_artifacts()` возвращает их. TemporalRelation.description может содержать artifact ID.

### F.6 Scope Boundary (что НЕ входит)

| НЕ входит | Почему |
|-----------|--------|
| Новый TemporalEngine сервис | Существующий ReconstructionEngine достаточен |
| Графовая БД (Neo4j и т.д.) | JSON persistence достаточна для текущего масштаба |
| Автоматическое обнаружение зеркальных эпох | Ручное через epoch_parallels + M10.2 workflow |
| LLM-генерация knowledge artifacts | Ручное создание + M10.2 confirmation |
| Интегция RelationGraph + TemporalGraph | Отдельный будущий этап |
| Изменение ADR Decision A/B/C/D | Milestone работает внутри существующих решений |
| Studio/Media/ComfyUI | Не связано |

### F.7 Оценка

| Метрика | Значение |
|---------|----------|
| Изменяемых файлов | 5 (relation.py, world_model.py, reconstruction_engine.py, WORLD_MODEL.json, 2-3 тест-файла) |
| Новых файлов | 0 |
| Новых enum значений | 4 (TemporalRelationType) |
| Новых Pydantic моделей | 2 (EpochParallel, KnowledgeArtifact) |
| Новых тестов | ~15-20 |
| Сломанных существующих тестов | 0 (additive changes) |
| Оценка (реализация + тесты) | 2-3 сессии |

---

## G. ИТОГ

**Текущее состояние:** Система строит линейную хронологию 12 эпох с provenance, gap detection, future extrapolation. 499 тестов, ADR принят и реализован. **Это работает.**

**Что НЕ работает:** События не привязаны к эпохам. Нет связи между персонажами. Нет модели носителя/наследия/передачи. Нет зеркальных эпох в графе. Knowledge artifacts не существуют.

**Критический разрыв:** Планировщики (cause_effect.py) и temporal model (TemporalNode/Relation) — два мира, не интегрированных. Планировщики генерируют текстовые сценарии с упоминанием носителей, поколений, наследия. Temporal model хронологию. Между ними — пустота.

**Предлагаемый refinement milestone (TEMPORAL_LEGACY_REFINEMENT):**
- 5 задач, 5 изменяемых файлов, 0 новых файлов
- Каждая задача additive (не ломает существующее)
- Привязывает события, добавляет relation типы, character cross-references, зеркальные эпохи, knowledge artifacts
- Работает ВНУТРИ существующих ADR-решений

**STOP. Жду решения владельца по refinement milestone.**
