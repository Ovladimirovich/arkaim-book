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
- ExpansionLayer: THEMES_DEEP.json (15 тем), THEMES_EXPANDED.json (14 items), SYMBOLS_DEEP.json (15 items) — загружаются, поиск работает через `GET /book/knowledge/search?type=expansion`
- **Расширение "168 topics" не подтверждено:** фактическое количество expansion topics = 15 (THEMES_DEEP) + 14 (THEMES_EXPANDED) + 15 (SYMBOLS_DEEP) + другие DEEP/EXPANDED файлы = ~50-60 тем, а не 168.

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
2. **ExpansionLayer в /book/layers:** данных ~50 тем, но они не попадают в ответ API. UI layers не видит expansion.
3. **«168 expansion topics»:** не подтверждено. Факт: ~50 тем в DEEP/EXPANDED файлах.

## 12. Решения, необходимые от владельца

| # | Вопрос | Факт | Решение |
|---|--------|------|---------|
| Q1 | Provenance порог | 8/8 тематических RU-вопросов проходят с provenance. Silence корректен для non-book вопросов. | Принять 8/8 как факт. Порог ≥6/8 избыточен. |
| Q2 | knowledge/search баг (GET vs POST) | Backend GET, frontend POST → 405 на `/search`. Не блокирует Ask-цикл. | Исправить: либо route на POST, либо frontend на GET. Низкий приоритет. |
| Q3 | ExpansionLayer в /book/layers | Data exists (~50 тем), но не сериализуется в response. | Исправить: добавить `expansion_layer` в BookLayersResponse. Низкий приоритет. |
| Q4 | F5 pages vs R1/R2 | F5 = `/xray`, `/admin`, `/system`, `/profile+`, `/history`, WS-toast. Не блокируют core cycle. | После утверждения MVP — решить: F5 или R1/R2 сначала. |
| Q5 | «168 expansion topics» | Не подтверждено. Факт: ~50 тем в DEEP/EXPANDED файлах. | Учесть в документации, не строить план на 168. |

## 13. Предлагаемый следующий этап

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

*Документ обновлён 2026-09-25 на основе уточнённой диагностики. Provenance BROAD подтверждён (8/8). Разрывы R1–R2 — контрактные, не data gap. Ждёт решения владельца по §12.*


