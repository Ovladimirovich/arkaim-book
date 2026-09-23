# ADR — TEMPORAL WORLD MODEL (PRESENT → ARKAIM → FUTURE)

**Тип:** Architecture Decision Record
**Дата:** 2026-09-09
**Статус:** ✅ ACCEPTED (2026-09-14) — решения M8.1 реализованы в engine (`reconstruction_engine.py:563-621`); API-выравнивание (B1+C1) отложено до отдельного owner-GO.
**Контекст принятия:** решение по итогам `TEMPORAL_CHAIN_ARCHITECTURE_AUDIT.md` (4 вопроса §9) в рамках подготовки F3 «Время мира».
**Режим:** только архитектура. Код, backend, temporal-данные, F3-UI — НЕ менялись и НЕ начинались.

---

## Простыми словами

1. **Что было целью?** — Принять архитектурные решения по «времени мира» книги ДО начала F3: что такое «сегодня», какими связями соединены эпохи, как помечать происхождение фактов и какой узел считать главным якорем Аркаима.

2. **Что реально сделано?** — Изучены код временной модели, контракты API (включая живые запросы к работающему серверу) и все документы M8.1/M9/M10.2. Обнаружено главное: **большая часть решений уже была принята в M8.1 и реализована в коде**, но публичный API (то, что видит фронтенд) этого пока не отражает. ADR фиксирует решения M8.1 как канонические, закрывает все 4 вопроса аудита и определяет точную границу: что делать backend'у (после вашего отдельного согласования), что войдёт в F3, а что запрещено.

3. **Что получилось?** — ADR_READY: четыре решения сформулированы (A: «сегодня» — точка наблюдения, а не эпоха книги; B: эпохи соединяются только связью «предшествует»; C: каждый факт несёт метку происхождения, фронт обязан её показывать; D: главный якорь — один, второй уничтожен), противоречий с M9/M10.2 не найдено.

4. **Есть ли проблемы?** — Несерьёзные. (а) API и внутренний движок сейчас отвечают по-разному — выравнивание требует малого backend-этапа (~30–60 строк, только после вашего approval); (б) три мелких вопроса отложены до реализации (перечислены в §8); (в) найденная в тексте ADR пара опечаток исправлена, документ чист.

5. **Что предлагается дальше?** — Ваше ACCEPTED на этот ADR. Затем — малый backend-этап (B1+C1, отдельный approval), затем F3-аudit → SPEC по регламенту. Ничего не начинаю без ваших решений.

---

## 0. Доказательная база (что фактически есть на момент решения)

| # | Факт | Источник (проверено) |
|---|------|----------------------|
| E1 | M8.1 Architecture Decision уже существует и принят (M9 — ACCEPTED & CLOSED 2026-09-06): PRESENT = методологический узел; PRESENT→ARKAIM = computed path, НЕ graph relation; arkaim_era enrichment; orphan-удаление; FUTURE_EXTRAPOLATION-маркировка | `docs/M8_1_ARCHITECTURE_DECISION.md`, `docs/M9_POST_IMPLEMENTATION_AUDIT.md` |
| E2 | M8.1 **реализован в коде**: `reconstruction_engine.py:563-621` — temporal_today добавляется (provenance=HYPOTHESIS, node.py:133-152), arkaim_era provenance-enrichment + confidence 0.85 (reconstruction_engine.py:589-595), orphan temporal_arkaim_anchor удаляется (610-614); future_extrapolator.py:92-112 маркирует FUTURE_EXTRAPOLATION | построчно прочитано |
| E3 | **Два независимых построителя цепочки:** (а) `WorldModel.get_temporal_chain()` (M4-мост) — БЕЗ today/enrichment, provenance эпох пуст/`canonical_provenance`, отдаётся `/book/temporal/chain`, `/nodes`, `/chains` — **публичный frontend-контракт**; (б) `TemporalReconstructionEngine.from_world_model()` (M4+M8.1) — С today/enrichment/orphan-removal, отдаётся через `/book/temporal/reconstruct` | `world_model.py:350-392`, `reconstruction_engine.py:563-621`, `routes/temporal.py` |
| E4 | **Live-факт (проверено запросами):** `/book/temporal/chain?FORWARD` = 12 узлов (temporal_today ОТСУТСТВУЕТ), 11 relations (все PRECEDES), arkaim_era provenance=`[]`, confidence=0.8, is_anchor=true; `/nodes` то же | `scripts/adr-live-evidence.mjs` (запуск от 2026-09-09) |
| E5 | Гэпы аудита G1 (today не в графе) и G4 (пустой provenance) — **верны для публичного API-пути** (E3а/E4), но **закрыты в engine-пути** (E2). G3 (двойной anchor) — закрыт в engine-пути; в API-пути `is_anchor` отмечает только arkaim_era. G5 (M8 без FUTURE_EXTRAPOLATION) — устарел: закрыт M8.1 (E2, `M8_1_IMPLEMENTATION_REPORT.md` 13/13 PASS) | сопоставление аудита с кодом |
| E6 | Существующие relation-типы: 12 (BEFORE/AFTER/OVERLAPS/CONTAINS/CONTAINED_BY/CONTEMPORARY_WITH/PRECEDES/FOLLOWS/DEVELOPS_FROM/TRANSFORMS_INTO/COEXISTS_WITH/UNKNOWN) + таблица REVERSE_RELATIONS; chain-построение в обоих путях использует ТОЛЬКО PRECEDES между последовательными эпохами | `relation.py:17-73`, E3 |
| E7 | Provenance-модель — два измерения: `ProvenanceCategory` (семантика происхождения, 8 категорий) + `SourceLevel` (вес достоверности) в одном `ProvenanceTag`; маппинг категория→default-level + RU-лейблы/цвета уже в backend (`SOURCE_CATEGORY_LABELS`) | `source_levels.py:26-155` |
| E8 | M10.2 pending-контракт (`/book/temporal/pending-updates/*`) изолирован от graph-модели: scan→pending→confirm/reject; «подтверждённые — уже в WorldModel». Reader+: список; editor/admin: confirm/reject/scan | `routes/temporal_updates.py` |
| E9 | Запрет аудита §10: не добавлять relation today→arkaim без решений 1–4; не AUTHOR_CANON для Present-связи; не M9 до решения (M9 уже принят отдельно); не чинить двойной anchor без обсуждения; не создавать TemporalEngine-сервис | `TEMPORAL_CHAIN_ARCHITECTURE_AUDIT.md` §10 |

**Ключевой вывод из evidence:** архитектурные решения M8.1 уже приняты и реализованы в engine-слое; **разрыв — не в семантике, а в несоответствии публичного API-пути (M4) канонической модели (M8.1)**. Настоящий ADR фиксирует M8.1-решения как канонические, распространяет их на API-путь и закрывает 4 вопроса аудита окончательно.

---

## Decision A. Что является TODAY / Present

### Decision

**TODAY — методологический опорный узел `temporal_today` (TemporalNode), существующий В графе, но НЕ участвующий в исторических цепочках. Правила:**

1. **Семантика:** точка отсчёта читателя/системы («сейчас»), reference frame для BACKWARD-reconstruction и FORWARD-extrapolation. НЕ исторический факт мира книги, НЕ исследуемая эпоха, НЕ часть канона.
2. **Canonical representation:** `TemporalNode.present_anchor()` — id=`temporal_today`, label=«Современность», precision=EXACT, bounds `2025 CE..2025 CE`, provenance=[`{category: HYPOTHESIS, source_level: SYSTEM_INTERPRETATION, confidence: 1.0, notes: "methodological anchor…"}`], confidence=1.0. Единственная фабрика — `TemporalNode.present_anchor()`; создавать Today-узлы иными способами запрещено.
3. **Место в графе:** присутствует как узел с НУЛЁМ relations (нет today→arkaim ни в каком типе). Сегодняшняя точка не «встраивается» в историческую ось — она точка наблюдения вне её.
4. **Source of truth для Present:** сам узел `temporal_today` в temporal graph (engine-представление). Его видимость в API — см. Consequences: `/nodes` обязан его отдавать (сегодня не отдаёт — E4); `/chain` отдаёт только исторические цепочки (today в chain НЕ входит, потому что у него нет relations).

### Rationale
- M8.1 уже решил это (E1); воспроизводить дискуссию заново — риск раскола семантики. ADR возводит M8.1 в канон.
- HYPOTHESIS-категория для Present честна: «сейчас читателя» — внешняя по отношению к книге система координат, а не утверждение автора (запрет E9-пункта 2 соблюдён: AUTHOR_CANON для Present отсутствует).
- Узел без relations математически не ломает цепочки: любой BFS/PRECEDES-обход его обходит.

### Existing evidence
node.py:133-152 (present_anchor, HYPOTHESIS); reconstruction_engine.py:606-608 (добавление); M8.1_DECISION §1; live E4 (в API-пути today не виден — несоответствие, не решение).

### Consequences
- **Backend (после отдельного approval):** `/book/temporal/nodes` должен включать temporal_today (сегодня — нет: E4). Это единственное обязательное API-изменение по Decision A. `/chain` остаётся без today.
- **Frontend/F3:** «Современность» отображается как отдельная опорная точка (не эпоха): позиция наблюдателя, а не карточка истории. Если today отсутствует в ответе API — UI не рисует его сам (инвариант §5).
- **Backward compatibility:** additive; ни один существующий потребитель не ломается (today не участвует в chains/reconstruct-результатах).

### Rejected alternatives
- **Present как чистые метаданные (PresentAnchor-dataclass вне графа):** оставляет «today» невидимым для всех graph-алгоритмов; BACKWARD-цепочке всё равно нужна точка старта — она появлялась бы из ниоткуда. Отвергнуто (и M8.1 это уже отверг).
- **Present как исторический узел с relation CONTAINS/DEVELOPS_FROM к arkaim:** создаёт ложную историчность («современность развилась из Аркаима» — недоказуемое утверждение), нарушает E9-запрет №1. Отвергнуто.
- **AUTHOR_CANON для today (было в старом коде):** семантическая ошибка (современность — не канон книги). Исправлено M8.1; не возвращаемся.

---

## Decision B. Канонический тип relation для цепочки эпох

### Decision

**PRECEDES — единственный канонический тип relation для построения оси эпох. Правила:**

1. **Directionality:** направленный ребро `source PRECEDES target` = «источник исторически предшествует цели, строго, без пересечения». Цепочка эпох = последовательность PRECEDES-рёбер по возрастанию порядка (`Epoch.order`), от более ранней к более поздней.
2. **Правила построения цепочки:** ребро создаётся ТОЛЬКО между соседними эпохами в каноническом порядке (i → i+1); пропуск порядка = TemporalGap, а не «перепрыгивающее» ребро; дубликаты запрещены (см. п.3); FORWARD-обход идёт по исходящим PRECEDES, BACKWARD — по входящим (обратный тип FOLLOWS в REVERSE_RELATIONS существует для чтения, но НЕ создается как отдельное ребро).
3. **Запрет дублирования:** между парой узлов (A,B) допустимо РОВНО ОДНО каноническое PRECEDES-ребро оси; семантически дублирующие связи (BEFORE↔AFTER, FOLLOWS-дубль к PRECEDES, второй PRECEDES в обратную сторону) считаются дефектом данных. Контекстные связи (OVERLAPS, CONTEMPORARY_WITH, COEXISTS_WITH) не запрещены как типы, но НЕ входят в ось и не должны создаваться автоматическими построителями до появления подтверждённых данных.
4. **DEVELOPS_FROM / TRANSFORMS_INTO** — зарезервированы для будущих качественных переходов (наследование смыслов между эпохами), создаются ТОЛЬКО человеком через pending-workflow M10.2, никогда автоматически. Сегодня ось их не содержит — и это корректно.

### Rationale
- Вся существующая цепочка (11 рёбер, E4/E6) уже PRECEDES; смена типа = переписывание без выгоды.
- PRECEDES — минимальная недвусмысленная семантика для «временной оси»; DEVELOPS_FROM внёс бы интерпретацию («развитие») туда, где у нас есть только порядок.
- Запрет дублей предотвращает то самое «двойное знание» (как в case двойного anchor), когда две структуры кодируют одно и то же.

### Existing evidence
relation.py:41-42, 61-73; оба построителя создают только PRECEDES (world_model.py:383-386, reconstruction_engine.py:599-604); live: «types of relations: PRECEDES» (E4).

### Consequences
- **Backend:** без изменений для существующих данных; правило-3 становится инвариантом валидации (проверка при confirm в M10.2 — кандидат на будущее, не на F3).
- **Frontend/F3:** ось эпох рендерится как линейная последовательность по PRECEDES; направление FORWARD/BACKWARD — параметр API. UI не выводит никаких других типов на оси.
- **Backward compatibility:** полная — решение описывает существующее поведение, фиксируя его как канон.

### Rejected alternatives
- **DEVELOPS_FROM как канон оси (предлагалось в §9 аудита):** вносит недоказанную интерпретацию развития в чистый порядок; требует переписывания 11 рёбер и семантики BACKWARD/FORWARD BFS. Отвергнуто.
- **Новый тип relation (напр. CONNECTS_TO):** нарушение E9-запрета №5 (новые сущности без нужды); существующих 12 типов достаточно. Отвергнуто.
- **Бидирекциональные ребра:** порождают дубли (PRECEDES+FOLLOWS между одной парой) — прямо запрещено п.3. Отвергнуто.

---

## Decision C. Provenance temporal relations и узлов

### Decision

**Provenance-модель — два измерения в одном теге, живёт на каждом узле и каждом ребре, обязательна к отображению фронтендом. Правила:**

1. **Где хранится:** на самих сущностях: `TemporalNode.provenance: list[ProvenanceTag]` и `TemporalRelation.provenance: list[ProvenanceTag]` (сериализация to_dict/from_dict уже есть). Не в отдельном реестре, не в UI.
2. **Допустимые категории (закрытый список ProvenanceCategory):** AUTHOR_CANON, DERIVED, EXTERNAL_SOURCE, RECONSTRUCTION, HYPOTHESIS, ARTISTIC_MODEL, FUTURE_EXTRAPOLATION, UNKNOWN. Для temporal-оси действует таблица соответствия:
   - **эпохи оси (узлы):** AUTHOR_CANON (канон книги) + EXTERNAL_SOURCE (археология) — комбинируются; **RECONSTRUCTION** — для восстановленных связей эпох из внешних данных; **HYPOTHESIS** — только для методологических сущностей (temporal_today, gap-узлы);
   - **рёбра оси (PRECEDES между эпохами):** DERIVED (порядок выведен из канона) или RECONSTRUCTION (восстановлен по внешним данным); НИКОГДА AUTHOR_CANON (порядок эпох — интерпретация канона, не прямое утверждение текста) и НИКОГДА FUTURE_EXTRAPOLATION (это про будущее);
   - **результаты M8 (сценарии будущего):** FUTURE_EXTRAPOLATION (только; уже реализовано M8.1, E2);
   - **связь Present→Arkaim:** НЕ СУЩЕСТВУЕТ как граф-сущность (Decision B/D), поэтому и provenance для неё не определяется; вычисляемый путь при его будущей реализации получит HYPOTHESIS или RECONSTRUCTION в зависимости от источника — фиксируется при реализации, не сейчас.
3. **Различение канон/реконструкция/экстраполяция:** по категории тега (это онтологическая метка, не вес): AUTHOR_CANON — никто не может переписать; RECONSTRUCTION — внешние данные + канон; FUTURE_EXTRAPOLATION — проекция от канона вперёд. `SourceLevel`/confidence — вторичны (вес), категория первична. «HYPOTHESIS с confidence=1.0 остаётся HYPOTHESIS» — принцип M1 сохраняется.
4. **Frontend-отображение:** UI ОБЯЗАН показывать provenance-категорию каждой эпохи/связи/сценария: бейдж с RU-лейблом и цветом из `SOURCE_CATEGORY_LABELS` (backend уже отдаёт: «Авторский канон»/green, «Реконструкция»/orange, «Гипотеза»/gold, «Экстраполяция будущего»/magenta и т.д.). Переиспользуется F2-паттерн SourceBadge (классификация по строке категории), но с расширенным набором категорий. Сценарии M8 без FUTURE_EXTRAPOLATION-бейджа к показу не допускаются.

### Rationale
- Модель уже реализована в backend (E7) и соответствует двухмерному принципу M1; ADR только закрывает вопрос «как для temporal».
- Разделение «канон vs реконструкция» — стержень доверия к цифровому сознанию книги: читатель обязан видеть, где кончается текст автора и начинается интерпретация.

### Existing evidence
source_levels.py:26-155 (категории, маппинг, RU-лейблы); M8.1-реализация маркировки (E2); live: у arkaim_era в API-пути provenance пуст (E4) — проблема видимости, не модели.

### Consequences
- **Backend (после отдельного approval):** API-путь (M4-мост) обязан отдавать enriched-provenance эпох (сегодня пустой у arkaim_era — E4): минимальное изменение — WorldModel.get_temporal_node для arkaim_era должен включать канон+археологию, как это делает engine-путь E2. Это Decision C-следствие для API, не новая семантика.
- **Frontend/F3:** компонент ProvenanceBadge (расширение SourceBadge) обязателен; правила цветов/лейблов берутся из контракта backend (не хардкод в UI).
- **Backward compatibility:** consumers, игнорирующие provenance, продолжают работать.

### Rejected alternatives
- **Provenance в отдельном реестре/сервисе:** добавляет сущность (нарушение духа E9 №5), рассинхрон при чтении. Отвергнуто.
- **Только SourceLevel без категорий:** теряет семантику (не отличить реконструкцию от экстраполяции при одинаковом весе). Отвергнуто (M1-решение).
- **UI-вычисление provenance (клиентская догадка):» нарушает инвариант §5. Отвергнуто.

---

## Decision D. Canonical anchor Аркаима

### Decision

**`temporal_arkaim_era` — единственный канонический anchor. Правила:**

1. **Canonical:** узел `temporal_arkaim_era` (создаётся из Epoch `arkaim_era`, помечается `is_anchor=true` в обоих представлениях). Все потребители (M8-extrapolation, BACKWARD-цепочка, будущий F3-UI) ссылаются ТОЛЬКО на него.
2. **Второй anchor (`temporal_arkaim_anchor`, dataclass `ArkaimAnchor`):** перестаёт быть узлом графа (орфан удаляется — уже реализовано в engine-пути E2). `ArkaimAnchor` сохраняется КАК ИСТОЧНИК provenance-обогащения: его provenance [AUTHOR_CANON, EXTERNAL_SOURCE] вливается в канонический узел (реализовано reconstruction_engine.py:589-595, confidence 0.85). Dataclass остаётся кодом-фабрикой данных, не граф-сущностью.
3. **Migration/compatibility:** миграция не требуется в данных (данные не содержат орфана — он создавался кодом на лету и кодом же удалён). Для обратной совместимости любые старые ссылки на `arkaim_anchor` (вне графа) трактуются как alias → `temporal_arkaim_era`; механизм alias'а в код не добавляется, правило фиксируется документально: новые кодовые пути используют только `temporal_arkaim_era`.
4. **Принцип:** один объект = один источник истины. Любая будущая «двойная» сущность (две структуры, кодирующие одно) — архитектурный дефект, ловится ревью.

### Rationale
- Двойной anchor (G3) — результат исторического наложения M2 (ArkaimAnchor) на M4 (epoch-мост); M8.1 разрешил слияние, код реализован (E2). ADR фиксирует как канон и не оставляет лазейки «вернуть второй».
- ArkaimAnchor-dataclass несёт ценность (curated provenance) — уничтожать данные глупо, переносить в узел — честно.

### Existing evidence
reconstruction_engine.py:573-614 (enrichment + orphan-removal); live: в API-цепочке существует только temporal_arkaim_era с is_anchor=true (E4); audit §4 (двойной anchor описан до M8.1).

### Consequences
- **Backend:** без изменений (поведение engine-пути уже канонично); API-путь не отдаёт орфана и не должен.
- **Frontend/F3:** единственный якорный узел для входа в «время мира»; anchor-бейдж на эпохе Аркаима; никаких упоминаний arkaim_anchor в UI.
- **Backward compatibility:** старые сохранённые реконструкции, содержавшие temporal_arkaim_anchor, при перезагрузке через engine теряют орфан — это и есть миграция (бесшовная, read-time).

### Rejected alternatives
- **Объединить в новый третий узел (temporal_arkaim_canonical):** третья сущность = новая миграция всех ссылок + нарушение E9 №5. Отвергнуто.
- **Оставить оба (status quo до M8.1):** зафиксированная G3-проблема (двойное знание, разный provenance). Отвергнуто.
- **Удалить ArkaimAnchor-dataclass целиком:** потеря curated-provenance. Отвергнуто.

---

## 5. ИНВАРИАНТ ФРОНТЕНДА (обязательный к соблюдению в F3 и далее)

**Фронтенд НЕ имеет права достраивать temporal graph. Если связь/узел отсутствуют в ответе backend — UI их не выдумывает.**

Следствия для F3:
1. **Отсутствие Present→Arkaim — это текущее состояние модели.** UI показывает ось эпох как есть: от pre_arkaim до arkaim_era (+ сценарии будущего как отдельный тип данных с FUTURE_EXTRAPOLATION-бейджем). Никакой «скрытой линии» от «Современности» к «Аркаиму» не рисуется. Если temporal_today появится в `/nodes` (Decision A-Consequence) — он рендерится как отдельная опорная точка наблюдателя, НЕ соединённая с осью.
2. **Запрещены в UI:** синтетические связи между узлами; вычисление «пропущенных» эпох; обратные рёбра (FOLLOWS) как самостоятельные; элементы оси, не имеющие PRECEDES-рёбер в данных; пометка «канон» у того, чего backend не пометил.
3. **Gap-узлы** (если backend их отдаёт в chain.gaps) отображаются как «данные неполны», не как эпохи.
4. Инвариант двусторонний по духу: и добавление, и скрытие фактов от пользователя — искажение модели.

---

## 6. ГРАНИЦЫ ЭТАПОВ (архитектура / backend / F3)

| Зона | Что входит | КТО/КОГДА |
|------|-----------|-----------|
| **Архитектурное решение (этот ADR)** | Semantics Today/relations/provenance/anchor + инвариант фронтенда + границы | Закрыто этим документом; вступает в силу по ACCEPTED |
| **Backend implementation (после ОТДЕЛЬНОГО approval — не в этой задаче)** | (B1) `/book/temporal/nodes` включает temporal_today; (C1) `/book/temporal/chain`-узлы (минимум arkaim_era) отдают enriched-provenance [AUTHOR_CANON, EXTERNAL_SOURCE] и confidence 0.85 — выравнивание API-пути с engine-путём M8.1; (опционально C2) provenance-теги на PRECEDES-рёбрах оси (DERIVED); (D1) ничего — уже реализовано; сопровождение: ~2 теста на B1+C1, регрессия M8/M10.2 | Отдельный мини-этап backend после ACCEPTED этого ADR (scope: только перечисленное) |
| **F3 frontend implementation (после backend-этапа и F3-audit/SPEC)** | Экран «Время мира» (ось эпох по PRECEDES, FORWARD/BACKWARD); ProvenanceBadge на эпохах/сценариях; anchor-выделение Аркаима; опорная точка «Современность» (если B1 реализован — иначе не показывается); сценарии будущего через `/future-extrapolation` с обязательным FUTURE_EXTRAPOLATION-бейджем; editor-очередь M10.2-UI (pending-updates); соблюдение инварианта §5; backlog F2-A1/A2 | F3-этап по регламенту (audit→SPEC→план→ACCEPTED→реализация) |

**НЕ входит ни в backend-этап, ни в F3:** новые relation-типы; граф-relation Present→Arkaim; HistoricalLayerStack/EpochTransitionModel (G6); изменения M10.2-контрактов; TemporalEngine-сервис; M9-расширения; любые правки arkaim-данных.

---

## 7. SELF-REVIEW (по требованию владельца)

1. **Противоречия с M10.2:** нет. M10.2 — pending-workflow поверх WorldModel; ADR не трогает его контракты; «подтверждённые находки попадают в WorldModel» не конфликтует с enrich-механикой (enrich — read-time мост, не запись). Единственная точка касания: подтверждённые находки должны нести provenance-категории Decision C — но это свойство будущих находок, не изменение M10.2.
2. **Противоречия с temporal contracts:** прямых нет; найденное несоответствие (API-путь M4 без M8.1-обогащения, E3/E4) зафиксировано как backend-следствие B1/C1 и НЕ «тихо» решается в ADR — оно вынесено в отдельный approval-этап. `/reconstruct`-контракт не затрагивается.
3. **Semantic model vs UI concerns:** не смешаны — решения A–D чисто семантические; всё UI живёт в Consequences-«Frontend/F3» и §5 (инвариант). Ни одно решение не мотивировано удобством UI.
4. **Решения, спрятанные в implementation assumptions:** проверено — единственное место, где семантика зависела бы от реализации (computed path Present→Arkaim), явно вынесено: связь НЕ создаётся, будущая реализация обязана получить provenance-решение отдельно (C-п.2). Bounds «2025 CE» у today — допущение данных, отмечено в Decision A (canonical representation), не скрыто.
5. **Свежесть аудита:** аудит §9/§10 (5 сент) частично устарел: G5 закрыт M8.1 (6 сент, E2/E5), M9-запрет снят самим M9 (принят). ADR опирается на фактическое состояние кода (E2), а не на текст аудита без проверки.

---

## 8. ИТОГ

**ADR_READY** — четыре решения сформулированы, обоснованы доказательствами из кода/контрактов/живых ответов, альтернативны отвергнуты явно, границы этапов разведены, инвариант фронтенда зафиксирован. Реализация не производилась. Жду ACCEPTED.

**Решения:**
- **A. TODAY** = методологический TemporalNode `temporal_today` в графе, provenance=HYPOTHESIS, БЕЗ relations; источник истины — сам узел; в API обязателен к отображению через `/nodes` (backend-этап B1).
- **B. Relation** = PRECEDES (единственный тип оси), соседство по order, BACKWARD=обратный обход тех же рёбер, дубли семантически одинаковых связей запрещены; DEVELOPS_FROM/TRANSFORMS_INTO — только человек через pending-workflow.
- **C. Provenance** = ProvenanceTag(category+confidence) на каждом узле/ребре; категории по Decision C-п.2 (оси — DERIVED/RECONSTRUCTION; узлы — AUTHOR_CANON+EXTERNAL_SOURCE/HYPOTHESIS; будущее — FUTURE_EXTRAPOLATION); UI показывает бейджи из SOURCE_CATEGORY_LABELS без собственных интерпретаций.
- **D. Anchor** = `temporal_arkaim_era` единственный; ArkaimAnchor-dataclass → источник enrichment (не граф-сущность); миграция read-time (engine уже выполняет); старые ссылки — alias-правило, без кода.

**Unresolved (не блокируют ADR, требуют отдельного решения при реализации):**
- U1: provenance-категория для будущих computed-path Present→Arkaim (решается при реализации такового, не сейчас).
- U2: точный набор provenance-тегов на PRECEDES-рёбрах оси (C2-опция backend-этапа: DERIVED vs RECONSTRUCTION per-ребро — требует просмотра источников эпох; можно отложить, рёбра сегодня отображаются без бейджа).
- U3: границы «2025 CE» у temporal_today — живой вопрос данных (обновлять при смене года? решит backend-этап B1 как отдельный пункт).

**Backend-изменения после отдельного approval (только эти):**
- B1: `/nodes` + temporal_today (enrichment уже есть в engine-пути).
- C1: `/chain` arkaim_era provenance-enrichment (выравнивание с engine-путём M8.1).
- C2 (опционально): provenance-теги на PRECEDES-рёбрах.
- ~2 теста + регрессия M8/M10.2. Оценка: малый объём (~30–60 строк).

**Входят в F3:** экран оси эпох (PRECEDES, FORWARD/BACKWARD), ProvenanceBadge, anchor-выделение, «Современность» (если B1), сценарии будущего с FUTURE_EXTRAPOLATION-бейджем, M10.2-очередь для editor, инвариант §5, backlog F2-A1/A2.

**НЕ входят в F3:** новые relation-типы; Present→Arkaim relation; HistoricalLayerStack/EpochTransitionModel; правки M10.2-контрактов; TemporalEngine-сервис; M9-расширения; правки arkaim-данных; «маленькие попутные» backend-фиксы вне B1/C1/C2.
