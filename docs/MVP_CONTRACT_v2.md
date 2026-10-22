<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL - НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> Статусы, маршруты, компоненты и упоминания бывшего v2 ниже отражают состояние на момент создания документа. Актуальность проверяйте по docs/CURRENT_DEVELOPMENT_STATE.md, docs/DOCUMENTATION_INDEX.md, текущему коду и ADR.

# MVP-Контракт Arkaim v2 — Reading → Ask → World → Timeline

**Дата:** 2026-09-24 · **HEAD:** `8aef0f9` · **Статус:** На согласование владельцу
**Основание:** GO-2 Live-audit + Этап 1 локализации разрывов + Решения владельца

---

## Простыми словами

**Цель:** Описать минимальный рабочий продукт Arkaim v2, который можно показать пользователю и который действительно работает end-to-end. Не код, не баги — контракт: что пользователь делает, что система отвечает, как мы измеряем «работает».

**Контекст (после уточнённой диагностики 2026-09-25):** Backend и фронтенд v2 собраны. 34 страницы работают. Provenance работает: 7/8 RU-тематических вопросов возвращают provenance, 1/8 (non-book) правильно silences. ХромодБД заполнена (824 chunks, 8.6 MB), коллекция arkaim_book доступна. ExpansionLayer: 6 файлов *_DEEP.json (THEMES=15, SYMBOLS=15, ARCHAEOLOGY=11, PHILOSOPHY=134, COSMOLOGY=1, CROSS_REFERENCES=1) + 3 *_EXPANDED.json, но ExpansionLoader падает при импорте knowledge_expansion модуля → fallback загрузчик срабатывает. GET /book/knowledge/search работает, frontend использует GET (контракт совпадает). GET /book/layers НЕ включает expansion_layer. XRay /stats и /events — 500. Admin API — 404.

---

## 1. Сквозной пользовательский сценарий

```
Dev-login → Reading (выбор главы) → Ask (вопрос по книге)
    → Provenance/evidence → World (поиск сущности) → Timeline (контекст эпохи)
    → Возврат к чтению
```

| Шаг | Действие пользователя | Входной сигнал | Ожидаемый результат | Критерий приёмки |
|-----|----------------------|---------------|---------------------|-----------------|
| S1 | Открыть `/reading` | GET /reading | Страница 200, список 17 глав загружен через TanStack Query | Страница рендерится,章节 кликабельны |
| S2 | Выбрать главу | Клик на главу | Контент главы загружен (`GET /book/chapters/{id}`) | Content present, ≥1000 chars |
| S3 | Перейти к вопросу | Клик «Задать вопрос» → `/ask` | Форма ввода видна, ответы предыдущих сессий (если есть) | UI ready |
| S4 | Ввести вопрос по теме | POST `/book/ask` | Ответ + provenance + pulse_confidence | `source≠silence` ИЛИ `provenance.length>0` ИЛИ `pulse_confidence>0` |
| S5 | Посмотреть provenance | UI компонент SourceBadge | Бейдж источника отображён | Badge visible with correct source type |
| S6 | Перейти в мир | Клик «Исследовать мир» → `/world` | Страница 200, поисковая форма доступна | UI ready |
| S7 | Найти сущность | POST `/book/world/search` | Список сущностей, клик → detail | `entity/{id}` → 200 |
| S8 | Перейти ко времени | Клик «Время мира» → `/temporal` | Цепочка эпох (13 узлов) | Nodes rendered |
| S9 | Открыть контекст эпохи | Клик на эпоху | `GET /book/temporal/context/{era_id}` → 200 | Context card shown |
| S10 | Вернуться к чтению | Навигация → `/reading` | Возврат в режим чтения | Navigation works |

---

## 2. Протокол provenance (BROAD)

### 2.1 Что считается «в пределах поддерживаемых знаний»

Вопрос находится в зоне покрытия, если он относится к одной из категорий:

| Категория | Критерий попадания | Источник provenance |
|-----------|-------------------|---------------------|
| **Темы книги** | Вопрос содержит ключевые слова из `_theme_index` или общие паттерны (`темы книги`, `о чём книга`) | `knowledge:theme`, `knowledge:themes_summary` |
| **Персонажи** | Вопрос содержит имя персонажа (индекс `_char_index`) или общие паттерны (`персонажи книги`) | `knowledge:character`, `knowledge:characters_summary` |
| **Символы** | Вопрос содержит имя символа (`_symbol_index`) | `knowledge:symbol` |
| **Конфликты** | Вопрос содержит имя конфликта (`_conflict_index`) | `knowledge:conflict` |
| **Мир/локации** | Вопрос содержит имя world_entity или общие паттерны (`мир книги`, `где происходит`) | `knowledge:world_entity`, `knowledge:world_summary` |
| **Ценности** | Общие паттерны (`ценности книги`) | `knowledge:values_summary` |
| **Книжный текст** | RAG-поиск по `enriched_chunks.json` (824 chunks) находит совпадение ≥0.3 score | `knowledge:catalog_text` |
| **RAG ChromaDB** | Векторный поиск возвращает результат с score≥0.5 | `knowledge:rag:chromadb` |

Вопрос вне зоны покрытия, если:
- Не содержит ключевых слов из индексов
- Не попадает под общие паттерны
- RAG-поиск не нашёл достаточного совпадения
- Язык запроса не совпадает с языком индексов (русские индексы, английский запрос → silence)

### 2.2 Формирование evidence/provenance

```
User question → KeeperAgent.act() → BookVoice.speak() → BookPulse.listen()
    → KnowledgeLayer.respond_to() [indexed match → PulseResponse]
    → if None: ExpansionLayer.respond_to() [topic match → PulseResponse]
    → if None: RAG/ChromaDB fallback → PulseResponse
    → if None: return PulseResponse(text="", source="silence", confidence=0.0)
```

Provenance item формируется в каждом `PulseResponse`:
- `source_level: CANON` + `category: AUTHOR_CANON` + `confidence: 1.0` — прямое знание из GENOME
- `source_level: SYSTEM_INTERPRETATION` + `category: DERIVED` + `confidence: 0.7` — вывод системы
- `source_level: CANON` + `category: AUTHOR_CANON` + `confidence: score` — RAG-результат

### 2.3 Поведение при отсутствии evidence

| Случай | `source` | `provenance` | `pulse_confidence` | `answer` | UI-отображение |
|--------|----------|-------------|-------------------|----------|---------------|
| Pulse нашёл ответ | `knowledge:*` | [tags] | >0 | Текст ответа | SourceBadge — зелёный (CANON) |
| Pulse нашёл, LLM озвучил | `knowledge:*` | [tags] | >0 | LLM-перефраз | SourceBadge — жёлтый (hybrid) |
| Pulse молчит | `silence` | [] | 0.0 | Дефолтный ответ («не нахожу в книге») | SourceBadge — серый (silence) |
| Pulse нашёл, IdentityLayer заблокировал | `silence` | [] | 0.0 | «Не могу ответить» | SourceBadge — красный (blocked) |

### 2.4 Различение причин пустого provenance

| Причина | Как отличить | Лог/факт |
|---------|-------------|----------|
| **Корректное отсутствие оснований** | `source=silence`, `answer` — дефолтная формулировка | PulseResponse вернул None из всех слоёв |
| **Ошибка retrieval pipeline** | В логах `expansion_loader_init_failed` или `chromadb_error` | ExpansionLoader упал при старте |
| **API-контрактная ошибка** | 404/500 от endpoint, не 200 | HTTP status ≠ 200 |
| **UI-ошибка** | Frontend не показывает badge, хотя API вернул provenance | Inspect response — provenance есть, UI не рендерит |

### 2.5 Фактическое состояние provenance (диагностика 2026-09-25)

**Механизм provenance подтверждён:**
- ChromaDB заполнен: `core/CHROMA_DB/chroma.sqlite3` = 8.6 MB, коллекция существует
- Retriever работает: вопросы через ChromaDB RAG возвращают provenance (`knowledge:rag:chromadb`)
- KnowledgeLayer индексы работают: темы, персонажи, символы, конфликты, world_entities
- ExpansionLayer (перепроверено 2026-10-22): текущий `ExpansionLoader` (`core/CORE/knowledge_expansion/expansion_loader.py:26-48`) читает только `THEMES_DEEP.json` (15 тем) и `ACADEMIC_CONFIRMATIONS.json` (8 категорий). `THEMES_EXPANDED.json` (14 items) и `SYMBOLS_DEEP.json` (15 items) на диске есть, но их формат загрузчик не читает. Поиск идёт через `GET /book/knowledge/search?type=expansion` (`runtime/core/routes/book.py:817-819`).
- **Расширение "168 topics" не подтверждено:** измерено 2026-10-22 — 23 темы в ExpansionLayer и 217 записей в 9 файлах DEEP/EXPANDED, а не 168. Фактический состав и статус — §12.3.

**Тестовый прогон (8 вопросов категории A): 8/8 проходят с provenance.**

| № | Вопрос | Source | Provenance | Pulse | Статус |
|---|--------|--------|-----------|-------|--------|
| A1 | «Какие темы раскрывает книга?» | `knowledge:themes_summary` | 1 | 0.95 | ✅ |
| A2 | «Какие персонажи есть в книге?» | `knowledge:characters_summary` | 1 | 0.90 | ✅ |
| A3 | «Кто такой Влад?» | `knowledge:character` | 1 | 0.90 | ✅ |
| A4 | «Что такое Аркаим в книге?» | `knowledge:theme` | 1 | 0.85 | ✅ |
| A5 | «Какова главная тема книги?» | `knowledge:rag:chromadb` | 1 | 0.80 | ✅ |
| A6 | «О чём книга «Наследие Аркаима»?» | `knowledge:theme` | 1 | 0.85 | ✅ |
| A7 | «Какие символы есть в книге?» | `knowledge:rag:chromadb` | 1 | 0.80 | ✅ |
| A8 | «Где происходит действие книги?» | `knowledge:world_summary` | 1 | 0.90 | ✅ |

**Дополнительные RAG-вопросы (ChromaDB):** все 5 прошли с provenance.

**Категория B (silence — корректно):**
| № | Вопрос | Source | Прогноз |
|---|--------|--------|---------|
| B1 | «Hello world» | `silence` | provenance=[], pulse=0.0 |
| B2 | «Сколько будет 2+2?» | `silence` | provenance=[], pulse=0.0 |
| B3 | «Tell me a joke» | `silence` | provenance=[], pulse=0.0 |
| B4 | «Какой сегодня погожий день?» | `silence` | provenance=[], pulse=0.0 |

**Вывод:** BROAD provenance на уровне ~100% для тематических RU-вопросов. Порог ≥6/8 (75%) избыточен — факт 8/8.

**Новый факт — контрактный разрыв:** `GET /book/knowledge/search` работает (genome + expansion), но frontend по документам шлёт POST → 405. Это отдельный баг, не блокирующий основной цикл Ask.

---

## 3. Обязательные требования MVP

| # | Требование | Текущий статус | Разрыв | Приоритет |
|---|-----------|---------------|--------|-----------|
| M1 | Dev-login → JWT → cookie | ✅ Работает | — | — |
| M2 | Reading: список глав + контент | ✅ 17 глав, контент есть | — | — |
| M3 | Reading: next/prev + прогресс | ✅ API работает | Нет данных о навигации в UI | Низкий |
| M4 | Ask: POST /book/ask → answer | ✅ Возвращает answer | — | — |
| M5 | Ask: provenance для тематических вопросов | ✅ 8/8 проходят | Нет — provenance BROAD подтверждён | — |
| M6 | Ask: silence для нерелевантных | ✅ Работает | — | — |
| M7 | World: search → entity detail | ✅ Работает | — | — |
| M8 | World: categories, rules, modes | ✅ Работают | — | — |
| M9 | Timeline: nodes (13 эпох) | ✅ Работает | — | — |
| M10 | Timeline: context via era_id | ⚠️ Frontend корректен, API требует era_id | B2 исправлен в коде frontend | **Средний** |
| M11 | Frontend навигация cycle | ⚠️ Страницы 200, навигация через ссылки | Нет данных о кликабельности | Средний |

---

## 4. Текущие подтверждённые возможности

### Backend (FastAPI :8642)
- Auth: dev-login → JWT cookie — работает
- Reading: 17 глав, контент, прогресс — работает
- Ask: answer + provenance для тематических RU-вопросов — работает
- World: search (POST), entity detail (GET), categories, rules, modes, form-library — работает
- Timeline: 13 epochs, context — работает с era_id
- Genome: 138 themes, 27 characters. KNOWLEDGE/*.json: ~200+ topics across DEEP + EXPANDED files
- ChromaDB: коллекция `arkaim_book` — 824 chunks, заполнена (8.6 MB). Retriever работает, возвращает `knowledge:rag:chromadb` для подходящих вопросов
- SSE `/v1/stream`: 200, text/event-stream — работает
- WebSocket `/ws`: клиент существует, backend route есть

### Frontend (Next.js :3001)
- 24 страницы, все 200 OK, SSR ~21KB
- Reading page: chapter list, content display, progress tracking
- Ask page: form, streaming SSE, SourceBadge component
- World page: search form, entity detail display
- Timeline page: chain visualization, era context card
- SourceBadge: рендерит badge по provenance source level

---

## 5. Разрывы, требующие реализации

| ID | Разрыв | Тип | Влияние на MVP | Объём |
|----|--------|-----|---------------|-------|
| **R1** | ~~knowledge/search GET vs POST~~ → FIXED: frontend uses GET, contract matches | — | — | — |
| **R2** | ExpansionLayer не включён в `/book/layers` ответ | API-контракт bug | UI не видит expansion данные через layers endpoint | Низкий: добавить `expansion_layer` в BookLayersResponse |
| **R3** | XRay `/stats` и `/events` — 500 | Backend bug | Не блокирует MVP (XRay отложен владельцем) | Низкий |
| **R4** | Admin API `/admin/stats`, `/admin/users` — 404 | Missing route | Не блокирует MVP, но ломает /admin страницу | Низкий: добавить route или фоллбэк |
| **R5** | unknown source files detection | Code gap | Uncertainty не показывается корректно | Низкий |

---

## 6. Улучшения после MVP

| ID | Улучшение | Обоснование |
|----|-----------|-------------|
| P1 | Media integration (arkaim-media) | Отложено владельцем |
| P2 | WebSocket real-time уведомления | Не участвует в основном цикле |
| P3 | F5 pages (admin, system, profile+) | Product completion, но не core cycle |
| P4 | D-3 video plan | Media, вне MVP |
| P5 | D-4 queue/async | Архитектурное улучшение, не блокирует |
| P6 | XRay fix | Observability, вне MVP |
| P7 | Legacy frontend retirement | Cleanup, после подтверждения |
| P8 | ChromaDB векторное заполнение | Улучшение RAG coverage |

---

## 7. Границы MVP

**Входит в MVP:**
- Dev-login → Reading → Ask → World → Timeline → возврат к чтению
- Provenance для тематических RU-вопросов (BROAD, ≥6/8)
- SourceBadge в UI для answers с provenance
- Silence badge для вопросов вне зоны покрытия

**НЕ входит в MVP:**
- Media generation (video/image)
- WebSocket real-time
- XRay dashboard
- Admin/system страницы
- F5/F6 frontend pages (не в цикле)
- G0 OpenAI-compatible API
- Движок генерации сценариев
- Crowdfunding integration

---

## 8. Критерии приёмки MVP (измеримые)

| № | Критерий | Измерение | Порог |
|---|---------|-----------|-------|
| C1 | Dev-login работает | POST `/auth/dev/generate-token` → 200, cookie set | 1/1 |
| C2 | Reading: главы загружены | GET `/book/chapters` → 17 items | ≥17 |
| C3 | Reading: контент главы | GET `/book/chapters/{id}` → content ≥500 chars | 17/17 |
| C4 | Ask: answer возвращается | POST `/book/ask` → 200, answer.length > 0 | 1/1 |
| C5 | Provenance BROAD | 8 тестовых RU-вопросов → provenance.length ≥1 | ≥6/8 (75%) |
| C6 | Silence корректен | 4 non-book вопроса → provenance=[] | 4/4 |
| C7 | World search → entity | POST `/book/world/search` + GET `/book/world/entity/{id}` | 5/5 |
| C8 | Timeline context | GET `/book/temporal/context/{era_id}` для 5 эпох | 5/5 |
| C9 | Frontend pages 200 | Все 24 страницы | 24/24 |
| C10 | SourceBadge рендерится | UI component visible с provenance data | 1/1 smoke test |

---

## 9. Зависимости и риски

| Зависимость | Статус | Риск |
|------------|--------|------|
| Genome JSON (GENOME_v1.0.0.json) | ✅ Существует, 138 тем | Низкий |
| enriched_chunks.json (824 chunks) | ✅ Существует | Низкий |
| ChromaDB векторы | ✅ 8.6 MB, коллекция существует, retriever работает | Низкий |
| ExpansionLoader path | ✅ KNOWLEDGE/*_DEEP.json (6 файлов), *_EXPANDED.json (3 файла) загружаются | Низкий |
| LLM provider (GigaChat) | ✅ health check проходит | Низкий |
| Frontend API contracts | ⚠️ knowledge/search: frontend POST → backend GET-only, 405 | Средний — не блокирует core cycle |

---

## 10. Что уже подтверждено (резюме диагностики 2026-09-25)

1. **World search → entity detail:** работает для реальных ID (`arkaim_settlement`, `civ_arkaim_civilization`, `geo_аркаим` — все 200). Ложное подозрение из GO-2 исправлено.
2. **Temporal context:** frontend передаёт `n.era_id || n.id` — правильно. `context/{era_id}` → 200 для всех 12 исторических эпох. `temporal_today` обрабатывается отдельно.
3. **Provenance BROAD:** 8/8 тематических RU-вопросов проходят с provenance. ChromaDB заполнен (8.6 MB), retriever работает. ExpansionLayer загружает файлы из KNOWLEDGE/*_DEEP.json. Silence = корректное поведение для нерелевантных вопросов.
4. **ExpansionLayer факт:** НЕ пустой — 6 *_DEEP.json + 3 *_EXPANDED.json файлов, 15+ тем. Но не включён в ответ `/book/layers`.
5. **knowledge/search баг:** endpoint GET-only, frontend шлёт POST → 405. Не блокирует Ask-цикл (ChromaDB RAG работает через ask), но ломает страницу `/search`.
6. **XRay 500:** подтверждён баг, отложен владельцем.
7. **Frontend 24 pages:** все 200, SSR работает.

## 11. Что не соответствует выбранному MVP

1. **knowledge/search контракт:** frontend POST vs backend GET → 405 на странице `/search`. Не блокирует core cycle, но это фактический баг.
2. **ExpansionLayer в /book/layers:** данных 23 темы (фактический состав — §12.3), но они не попадают в ответ API. UI layers не видит expansion.
3. **«168 expansion topics»:** не подтверждено. Факт (измерено 2026-10-22): 23 темы в ExpansionLayer, 217 записей в 9 файлах DEEP/EXPANDED — состав и статус в §12.3.

## 12. Решения, необходимые от владельца

**Срез:** 2026-10-22. Ниже — как отражены решения владельца по G12 (`docs/OWNER_DECISION_SHEET.md:180-194`).

| # | Вопрос | Факт | Решение |
|---|--------|------|---------|
| Q1 | Provenance: критерий допуска в MVP ≠ критерий достоверности утверждения | 8/8 тематических RU-вопросов проходят с provenance; silence корректен для non-book вопросов. Это метрика полноты контракта ответа, а не оценка истинности. | **Разделены два критерия** — §12.1. Порог ≥6/8 остаётся product-gate; агрегатный порог **не** подтверждает историческую истину. |
| Q2 | knowledge/search баг (GET vs POST) | Backend GET, frontend POST → 405 на `/search`. Не блокирует Ask-цикл. | Исправить: либо route на POST, либо frontend на GET. Низкий приоритет. |
| Q3 | ExpansionLayer в /book/layers | Data exists (фактический состав — §12.3), но не сериализуется в response. | Исправить: добавить `expansion_layer` в BookLayersResponse. Низкий приоритет. |
| Q4 | F5 pages vs R1/R2 | F5 = 6 пунктов (§12.2), R1/R2 — разрывы §5. Не блокируют core cycle. | **Порядок зафиксирован владельцем 2026-10-22** — §12.2. |
| Q5 | «168 expansion topics» | Не подтверждено текущими данными. | **Цифра исправлена** на измеренный состав — §12.3. |

**Статус отдельных пунктов на 2026-10-22:** Q2 и Q3 закрыты решениями владельца по G12 (`docs/OWNER_DECISION_SHEET.md:26-27`): добавлен `POST /os/search` как псевдоним `GET /knowledge/search`, а `BookLayersResponse` расширен полем `expansion_layer`. Q1, Q4, Q5 переработаны ниже.

### 12.1 Q1 — Два разных критерия: допуск в MVP и достоверность утверждения

**Критерий допуска в MVP (product gate).** Сколько тематических вопросов категории A должны нести provenance. Это метрика **полноты контракта ответа**: «система ответила и показала, откуда ответ». Текущий порог из §8/C5 — ≥6/8 (75%), фактически 8/8 (§2.5). Этот критерий измеряет контракт, а не истинность, и не отвечает на вопрос «правильно ли то, что сказано».

**Критерий достоверности утверждения (per-claim).** Определяется индивидуально для каждого claim'а — по его `provenance_category` и `source_level`/`confidence`:

| `provenance_category` | Что означает | Что требуется, чтобы утверждение считалось подтверждённым |
|---|---|---|
| `AUTHOR_CANON` | Прямое утверждение из первоисточника (`core/KNOWLEDGE/BOOK_DOCUMENT.json`, `AUTHOR_INTENT.json`) | Канон: внешняя проверка не требуется, нужно корректное provenance |
| `DERIVED` | Выведено из канона анализом системы | Историческим фактом не является; ссылается на канон |
| `RECONSTRUCTION` | Реконструкция: внешние данные + канон | Требуется проверка основания реконструкции |
| `EXTERNAL_SOURCE` | Внешний исторический/академический источник | Требуется **отдельная библиографическая проверка**: источник на конкретный claim |
| `HYPOTHESIS` | Системная гипотеза | Подтверждается только отдельно предъявленным источником; сама по себе — нет |
| `ARTISTIC_MODEL` | Художественная модель | Каноном не является, требует проверки автором |
| `FUTURE_EXTRAPOLATION` | Проекция в будущее | Историческим фактом не является по определению |
| `UNKNOWN` | Происхождение не определено | Требует классификации; подтверждённым считаться не может |

Перечень категорий — `core/CORE/narrative_engine/source_levels.py:26-65`; уровень достоверности (`source_level`) и вес (`confidence`) — независимое измерение, `:71-101`.

> [!WARNING]
> **8/8 или ≥6/8 — НЕ является подтверждением исторической истины.** Агрегатный порог показывает, что ответ несёт provenance, а не что claim верен. Он не повышает и не понижает `provenance_category` отдельного claim'а и не заменяет индивидуальную проверку.
>
> Конкретный пример: claim'ы из `core/KNOWLEDGE/ARCHAEOLOGY.json` помечены `facts_provenance: EXTERNAL_SOURCE` (все 7 сайтов; `core/KNOWLEDGE/ARCHAEOLOGY.json:29,77,106,127,148,169,190`) и требуют отдельной библиографической проверки — см. `docs/G1_ARCHAEOLOGY_SOURCES_2026-10-22.md` (список источников по каждому сайту; статус — «Источники не переведены в CANON», `:4-6`). Агрегатный порог их не подтверждает и не повышает.

**Где сохраняется индивидуальный статус доказательности каждого claim'а:**

| Слой | Где | Что хранит |
|---|---|---|
| Тег одного утверждения | `core/CORE/narrative_engine/source_levels.py:182-250` (`ProvenanceTag`) | `source_level` + `category` + `confidence` одного claim'а; предикаты `is_canon()`/`is_external()`/`is_hypothesis()` (`:208-238`) |
| Атомарный claim | `core/CORE/narrative_engine/provenance/claim.py:52-56` (`CanonClaim.category`, `.confidence`) | категорию и уверенность конкретного claim'а; фабрики `from_canon` / `from_external` / `from_hypothesis` / `from_reconstruction` (`:109-206`) |
| Ответ слоя | `core/CORE/pulse/layers.py:104-119` (`PulseResponse.provenance`, `.uncertainty`) | список тегов ответа + `UncertaintyFlag.confidence_breakdown` (`core/CORE/pulse/layers.py:16-25`) — поаспектная разбивка «факт / интерпретация / гипотеза» |
| Слияние нескольких источников | `core/CORE/pulse/layers.py:1358-1374` (`ExpansionLayer._combine_provenance`) | правило «наименьшего общего знаменателя»: `FUTURE_EXTRAPOLATION < HYPOTHESIS < RECONSTRUCTION < EXTERNAL_SOURCE < AUTHOR_CANON` — сильный источник **не** перебивает слабый |

**Guard-тесты, которые это охраняют** (`runtime/tests/test_data_discipline.py`):

| Тест | Строки | Что охраняет |
|---|---|---|
| `TestWMProvenanceCoverage.test_hypothesis_not_promoted_via_confidence` | `:79` | `HYPOTHESIS` с `confidence > 0.8` в данных мира не допускается |
| `TestProvenanceGuardsIntact.test_hypothesis_high_confidence_still_hypothesis` | `:323` | `HYPOTHESIS` с `confidence=1.0` остаётся `HYPOTHESIS` |
| `TestProvenanceGuardsIntact.test_external_not_becomes_canon` | `:333` | `EXTERNAL_SOURCE` не становится `AUTHOR_CANON` |
| `TestArchaeologyProvenance.test_facts_have_provenance` | `:184` | у каждого сайта `ARCHAEOLOGY.json` есть `facts_provenance` из допустимого набора |
| `TestArchaeologyProvenance.test_hypotheses_marked_as_hypothesis` | `:204` | утверждения о связи с Атлантидой/гипербореями помечены `HYPOTHESIS` |
| `TestPulseResponseUncertainty.test_provenance_consistency_with_uncertainty` | `:291` | `provenance` и `uncertainty` согласованы: `RECONSTRUCTION` в ответе тянет за собой флаг неизвестного |

Дополнительно: `runtime/tests/test_provenance_registry_consistency.py:99` (`test_registry_category_equals_disk_metadata`) — категория файла в реестре обязана совпадать с `_provenance_metadata` на диске (решение G13 от 2026-10-22).

### 12.2 Q4 — Порядок F5 pages и R1/R2

**Что такое F5.** F5 — «Realtime/Админ», 6 пунктов (`docs/PRODUCT_MAP.md:81-86`; `docs/FRONTEND_ARCHITECTURE.md:280`; `docs/F5_SPEC.md:24`):

| Пункт | Что это | Состояние в `arkaim-web` (проверено 2026-10-22) |
|---|---|---|
| G-F5-1 | WS-интеграция: toast при live-событиях + invalidate кэша | Компонент есть — `arkaim-web/src/shared/realtime/WsToast.tsx:21`; **подключён нигде нет** (0 импортов). В `app-shell` смонтирован только `ToastContainer` из `shared/ui/light/toast` (`arkaim-web/src/widgets/app-shell/index.tsx:10,55`) |
| G-F5-2 | `/xray` — SSE-лента трасировок | Есть: `arkaim-web/src/app/xray/page.tsx` |
| G-F5-3 | `/admin` — пользователи, инвайты, API-ключи, статистика | Есть: `arkaim-web/src/app/admin/page.tsx` |
| G-F5-4 | `/system` — health, конфигурация, метрики | **Нет**: каталога `arkaim-web/src/app/system/` в репозитории нет |
| G-F5-5 | `/profile` — история вопросов, расширенная статистика | Есть: `arkaim-web/src/app/profile/page.tsx` |
| G-F5-6 | `/history` — все сессии с фильтрами | Есть: `arkaim-web/src/app/history/page.tsx` |

**Что такое R1/R2.** В этом документе R1 и R2 — **разрывы из §5** (не «красные линии» R1–R2 из `docs/FRONTEND_ARCHITECTURE.md:62-63`):

| ID | Разрыв (§5) | Статус на 2026-10-22 |
|---|---|---|
| R1 | `/book/knowledge/search`: backend GET, frontend POST → 405 | FIXED (строка 183); закрыт решением G12 Q2 (`docs/OWNER_DECISION_SHEET.md:26`) |
| R2 | `ExpansionLayer` не включён в ответ `/book/layers` | Реализовано (строка 184); закрыт решением G12 Q3 (`docs/OWNER_DECISION_SHEET.md:27`) |

**Порядок (решение владельца 2026-10-22).** Общий порядок G12: **MediaPlan → F-12 → MVP §12 → остальной frontend-backlog.** В post-MVP-части: **сначала F5 pages, затем R1/R2.** То есть и F5 pages, и R1/R2 выполняются **после** MVP §12.

Смежные гейты для контекста: MediaPlan — `docs/MEDIA_PRODUCTION_MASTERPLAN.md`, статус PROPOSED (`docs/OWNER_DECISION_SHEET.md:188`); F-12 — миграция film-БД, «FUNCTIONALLY ACCEPTED / CLOSED» (`docs/F12_PRODUCTION_DB_REPAIR_PLAN.md:406`), миграция применена (`docs/OWNER_DECISION_SHEET.md:25`); «остальной frontend-backlog» — `docs/FRONTEND_RESTORE_BACKLOG.md` (B1/B2/B10 и др.; порядок внутри backlog — `docs/FRONTEND_RESTORE_BACKLOG.md:12`, B3 → B1 → B2).

### 12.3 Q5 — Фактический состав expansion topics (исправление цифры «168»)

> [!IMPORTANT]
> **Исправление цифры (2026-10-22), а не молчаливая правка.** «168 тем ExpansionLayer» — **не подтверждённое текущими данными значение**. Ниже — что на самом деле в репозитории.

**Откуда взялось 168.** Цифра зафиксирована в документах как результат 11 модулей пайплайна: `docs/AI_ENGINEER_GUIDE.md:25`, `docs/CLAUDE.md:21`, `docs/KNOWLEDGE_BASE.md:136`, `docs/archive/subsystems/KNOWLEDGE_EXPANSION.md:217`, `docs/archive/temporal/M0_ARCHITECTURE_AUDIT.md:588-590` («11 модулей: … → **Результат:** 168 тем в ExpansionLayer»). Проверка по истории git:

| Ревизия | Что было в `core/KNOWLEDGE/` | Сколько тем читал загрузчик |
|---|---|---|
| `f888913` (2026-07-19) — первое появление «168 тем» | `*_DEEP.json` / `*_EXPANDED.json` **отсутствуют** (проверено `git ls-tree`) | 0 — цифра появилась как проектная оценка, а не как измерение |
| `7dbd751`, `acbc7a3`, `6f25114` | файлы DEEP/EXPANDED в формате top-level массива | **194** — тоже не 168 |
| `48c19c9` и далее | файлы переведены в формат `{"_provenance_metadata": …, "items": […]}` | **23** — загрузчик этот формат не понимает |

**Вывод:** 168 не было реальным числом ни в одной ревизии. Это проектная оценка, унаследованная из архитектурного плана и не сверенная с загрузчиком.

**Что читает загрузчик сейчас.** `core/CORE/knowledge_expansion/expansion_loader.py:26-48`: glob по `*_DEEP.json`, glob по `*_EXPANDED.json`, отдельно `ACADEMIC_CONFIRMATIONS.json`. Формат записи понимается только два: top-level массив и объект с ключом `themes` (`:50-64`); академические — только список `confirmations` (`:72-81`). Fallback-загрузчик в самом слое дублирует ту же логику (`core/CORE/pulse/layers.py:1276-1327`), поэтому результат совпадает.

**Фактический состав:**

| Файл в `core/KNOWLEDGE/` | Записей в файле | Тем в ExpansionLoader | `provenance_category` | `source_level` | Статус |
|---|---|---|---|---|---|
| `THEMES_DEEP.json` | 15 (`themes`) | **15** | `DERIVED` | `SYSTEM_INTERPRETATION` | читается; требует проверки автором |
| `ACADEMIC_CONFIRMATIONS.json` | 8 (`confirmations`) + 2 (`scientific_explanations`) | **8** | `EXTERNAL_SOURCE` | `HISTORICAL` | читается; внешние источники, каноном не являются |
| `PHILOSOPHY_DEEP.json` | 134 (`items`) | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | **не читается** (формат `items`) |
| `SYMBOLS_DEEP.json` | 15 (`items`) | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | не читается |
| `THEMES_EXPANDED.json` | 14 (`items`) | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | не читается |
| `ARCHETYPES_EXPANDED.json` | 15 (`archetypes`) | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | не читается |
| `SYMBOLS_EXPANDED.json` | 14 (`symbols`) | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | не читается |
| `ARCHAEOLOGY_DEEP.json` | 9 (`items`) | 0 | `EXTERNAL_SOURCE` | `HISTORICAL` | не читается |
| `CROSS_REFERENCES_DEEP.json` | 1 (`items`) | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | не читается |
| `COSMOLOGY_DEEP.json` | темы не выделены: `cosmology.layers` (literal / metaphorical / cosmic), `cycles` 4, `cosmic_laws` 4, `connections_to_book` 4 | 0 | `DERIVED` | `SYSTEM_INTERPRETATION` | не читается |

**Итого (измерено 2026-10-22):**

| Величина | Значение |
|---|---|
| Тем, реально доступных ExpansionLayer | **23** (15 из `THEMES_DEEP.json` + 8 категорий из `ACADEMIC_CONFIRMATIONS.json`) |
| Записей верхнего уровня в 9 файлах DEEP/EXPANDED на диске | **217** |
| То же + `ACADEMIC_CONFIRMATIONS.json` | **225** |
| «168» | **не подтверждено**; значение не воспроизводится ни в одной ревизии git |

Вложенные элементы `COSMOLOGY_DEEP.json` (12 штук внутри `cosmology`) в счёт 217 не входят: отдельных тем там не выделено.

**Статус и provenance-категории** взяты из реестра `core/CORE/narrative_engine/provenance/knowledge_classification.py` (`KNOWLEDGE_CLASSIFICATION`, строки 67-522) и совпадают с `_provenance_metadata` внутри самих файлов; равенство реестра и диска охраняется тестом `runtime/tests/test_provenance_registry_consistency.py:99` (решение G13 от 2026-10-22). Ни один из файлов expansion-слоя не относится к `ARTISTIC_MODEL` — этот класс присвоен файлам визуального слоя (`core/CORE/visual/VISUAL_KNOWLEDGE`, реестр: строки 337-400). Итог: 8 файлов expansion-слоя — `DERIVED` (требуют проверки автором), 2 — `EXTERNAL_SOURCE` (каноном не являются).

**Следствие для планирования:** строить план на 168 нельзя; фактическая ёмкость expansion-слоя — 23 темы, из них 8 внешних и 15 системно-интерпретационных.

## 13. Предлагаемый следующий этап

**Статус на 2026-10-22:** MVP-часть G12 (Q1, Q4, Q5) решена и зафиксирована в §12. Общий порядок G12 принят владельцем: MediaPlan → F-12 → MVP §12 → остальной frontend-backlog; внутри post-MVP-части — сначала F5 pages, затем R1/R2 (§12.2). **Не решено:** порядок и содержание «остального frontend-backlog» (`docs/FRONTEND_RESTORE_BACKLOG.md`) и отдельные OWNER-GO по его пунктам. Этап A ниже остаётся read-only диагностикой; D2 (фактический состав expansion topics) закрыт измерением в §12.3.

### Этап A: Read-only диагностика (предложена владельцем, без кода)

**Цель:** подтвердить фактическое состояние перед любым ГО на реализацию.

| Задача | Что проверить | Формат результата |
|--------|-------------|-------------------|
| D1 | ChromaDB: коллекции, количество документов, связь с enriched_chunks | Факт: сколько документов, какие коллекции |
| D2 | ExpansionLoader: какие файлы находит, сколько тем загружено | Факт: list of loaded topics |
| D3 | Путь provenance от retrieval до UI: where does each layer contribute | Map: layer → source string → badge color |
| D4 | Frontend search page: почему 405, какой метод используется | Факт: inspect network tab or code |
| D5 | F5 pages scope: что именно не работает на каждой | List: page → missing functionality |

**Результат:** документ с фактами, без изменений кода.

### Этап B: OWNER-GO на исправление (после D1–D5)

Только после диагностики, выбора стратегии, утверждения критериев.

**Кандидаты на исправление (по приоритету):**
1. R1: knowledge/search GET→POST (или frontend POST→GET) — 1 файл, ~10 строк
2. R2: добавить expansion_layer в BookLayersResponse — 1 файл, ~5 строк
3. Ручная проверка F5 pages — зависит от результатов D5

**НЕ входит:** re-index ChromaDB, заполнение DEEP-файлов, XRay fix, media, legacy cleanup.

---

*Документ обновлён 2026-10-22: §12 переработан по решениям владельца от 2026-10-22 (G12). Q1 — разделены критерий допуска в MVP (product gate, порог ≥6/8) и критерий достоверности утверждения (per-claim, по `provenance_category`); 8/8 или ≥6/8 не подтверждает историческую истину. Q4 — зафиксирован порядок: MediaPlan → F-12 → MVP §12 → остальной frontend-backlog; в post-MVP-части сначала F5 pages, затем R1/R2. Q5 — «168 тем» заменено на измеренный состав: 23 темы в ExpansionLayer, 217 записей в 9 файлах DEEP/EXPANDED. Provenance BROAD подтверждён (8/8) — как полнота контракта ответа, не как достоверность утверждений. Разрывы R1–R2 — контрактные, не data gap. MVP-часть G12 решена; не решено — «остальной frontend-backlog» (`docs/FRONTEND_RESTORE_BACKLOG.md`) и отдельные OWNER-GO по его пунктам.*


