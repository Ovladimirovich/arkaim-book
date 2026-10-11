# M10 PRE-IMPLEMENTATION AUDIT
## Real-Time Temporal Updates from Book Text

Дата: 2026-09-06
Формат: как M9 (аудит → спецификация → утверждение → реализация → post-audit)

---

## ПРОСТЫМИ СЛОВАМИ

1. **Цель аудита?** — Понять, что значит «real-time temporal updates from book text», что для этого уже есть в проекте и можно ли это сделать без ломки архитектуры.
2. **Что реально сделано?** — Прочитал все упоминания M10, изучил 6 подсистем (Pulse watch, Research Engine, WorldExtraction, WorldModel, temporal engine, book source). Ничего не менял.
3. **Что получилось?** — **PARTIAL / NEEDS SPECIFICATION**. Технической блокировки нет, но M10 — самый амбициозный milestone из всех: он требует цепочку из 4 шагов, из которых сегодня реально работает только последний.
4. **Проблемы?** — Главная: **ни один существующий пайплайн не читает текст книги для извлечения temporal данных**. Плюс принцип «Книга — первичный источник» (ADR-0001) означает, что любые auto-update из книги обязаны проходить через CANON-валидацию, иначе нарушится provenance-контракт.
5. **Что дальше?** — Предлагаю спецификацию M10 (ниже в этом же документе, раздел SPEC DRAFT) на ваше утверждение. Без утверждения не реализую.

---

## 1. ЧТО ГОВОРИТ СПЕЦИФИКАЦИЯ

### Найденные упоминания M10

| Документ | Строка | Формулировка |
|----------|--------|--------------|
| `docs/M5_PRE_IMPLEMENTATION_AUDIT.md:841` | DEFERRED WORK | `M10: Real-time temporal updates from book text` |
| `docs/M7_2_PRE_IMPLEMENTATION_AUDIT.md:239` | NOT DONE | `M10 — real-time temporal updates | ❌ НЕ НАЧИНАЛ` |
| `docs/M8_FUTURE_EXTRAPOLATOR_IMPLEMENTATION.md:234` | NOT DONE | `M10 — real-time updates | ❌ НЕ НАЧИНАЛ` |
| `docs/M9_SPEC.md:32, 359` | NON-GOALS | `M10` (как future milestone, вне scope M9) |
| `docs/M9_POST_IMPLEMENTATION_AUDIT.md:8, 215` | статус | `M10 не начат — требует отдельного аудита` |

**Вывод по спецификации:** детальной спецификации M10 НЕ СУЩЕСТВУЕТ. M10 — one-liner в 5 документах. Нет:
- определения «real-time» (watcher? polling? событие сохранения файла?)
- какие temporal данные извлекаются из книги;
- что происходит с Conflict of Authority (книга vs WorldModel vs EXTERNAL_SOURCE);
- что считается «update» (новый узел? правка существующего? gap-закрытие?).

В коде упоминаний M10: **0**.

---

## 2. ЧТО УЖЕ СУЩЕСТВУЕТ (аудит инфраструктуры)

### 2.1 Текст книги (источник)

| Факт | Значение |
|------|----------|
| Путь | `core/SOURCE_OF_TRUTH/BOOK/КНИГА.md` |
| Размер | 213 KB, 2564 строки |
| Статус | PRIMARY AUTHOR CANON (weight 1.0, `source_hierarchy.py`) |
| Читается напрямую | **только 2 модулями** (см. ниже) |

Прямые читатели КНИГА.md:
1. `core/run_index_book.py` — индексация для RAG (одноразовый скрипт, не runtime)
2. `core/CORE/intelligence/character_profiler.py` — профили персонажей
3. `core/CORE/intelligence/kernel.py` — очистка текста от OCR-артефактов

**Ни один не извлекает temporal данные (даты, эпохи, хронологию).**

Временные маркеры в книге: есть, ~27 вхождений паттернов «до н.э»/«год»/«век»/«тысячелет» (пример: L71 «многие века», L157 «тысячелетия истории»). Плотность низкая — книга мифологическая, не хроникальная.

### 2.2 Pulse.watch() — существующий прецедент «real-time»

`core/CORE/pulse/pulse.py:116` — метод `watch(interval=2.0)`:
- проверяет `st_mtime` файла генома;
- при изменении mtime → `check_for_changes()` → хэш-сравнение → `GenomeDiff`;
- `auto_evolve()` применяет diff с блокировкой identity-изменений.

**Это единственный существующий механизм «real-time» в проекте.** Прецедент: дёшево (mtime вместо чтения), event-driven (возврат diff только при изменении), безопасно (identity-блокировка).

Но: `watch()` следит за **геномом JSON**, не за текстом книги.

### 2.3 Research Engine (частично ручной, частично заглушки)

`core/CORE/narrative_engine/research/`:
- `entity_extractor.py` — `extract_entities(text)` — **keyword-based**, словарь KNOWN_ENTITIES (локации/персонажи/концепты/технологии). Temporal-типов НЕТ. Работает по произвольному тексту (принимает `text`!) — это готовый вход для M10.
- `world_model_writer.py` — `apply_findings()` → пишет в WorldModel → `save()` + `reload()`. Механизм обновления WorldModel **уже существует**.
- `source_searcher.py`, `cross_referencer.py`, `api_routes.py` — заглушки/моки («в реальности используется OpenAlex...»).

### 2.4 WorldExtraction Pipeline (из JSON, не из книги)

`core/CORE/world_extraction/`:
- 24 модуля-экстрактора, читают `core/KNOWLEDGE/*.json` (уже обогащённые данные);
- `modules/chronology.py` — извлекает «хронологию», но из `PLOT.json` и `THEMES_EXPANDED.json`, **не из книги**;
- Пайплайн: KNOWLEDGE JSON → WorldKnowledge → WORLD_MODEL/*.json.

**Не является путём «книга → temporal».**

### 2.5 WorldModel + Temporal Engine (потребитель)

- `WorldModel.save()/reload()` — файл `WORLD_MODEL.json`, перезапись + перезагрузка — готово.
- `WorldEngine.enable_temporal()` — **idempotent, НЕ перестраивает**: `if self._temporal_engine is not None: return` (world_engine.py:79-80). Однажды созданный temporal engine **не обновляется** при изменении WorldModel — для M10 нужен `refresh`-путь.
- `TemporalReconstructionEngine.from_world_model(wm)` — пересоздание из WorldModel существует как classmethod, т.е. перестройка возможна без изменения M3/M5.

### 2.6 Вывод по существующему

| Шаг цепочки M10 | Существует? | Что есть |
|------------------|-------------|----------|
| 1. Обнаружить изменение книги | ✅ прецедент | `Pulse.watch()` mtime-паттерн (для генома) |
| 2. Извлечь temporal данные из нового текста | ❌ | `entity_extractor` работает по тексту, но temporal-словаря нет; chronology.py читает JSON, не книгу |
| 3. Записать в WorldModel с валидацией | ⚠️ частично | `world_model_writer.apply_findings()` пишет, но **без canon-валидации** и без temporal-типа finding'а |
| 4. Перестроить temporal engine | ❌ | `enable_temporal()` idempotent, не refresh'ит; `from_world_model()` сам по себе есть |

**Ничего не запрещает M10 архитектурно, но 2 из 4 шагов отсутствуют целиком.**

---

## 3. АРХИТЕКТУРНЫЕ РИСКИ И ИНВАРИАНТЫ

### Риск 1: Нарушение ADR-0001 «Книга — первичный источник»

Книга = AUTHOR_CANON (weight 1.0). Auto-update из книги **обязан**:
- классифицировать находки как AUTHOR_CANON;
- НО: существующие узлы temporal graph'а могут иметь EXTERNAL_SOURCE/RECONSTRUCTION provenance — **перезапись canon'ом внешних данных допустима** (canon > external), а вот понижение canon → anything **запрещено**.

### Риск 2: Превращение auto-update в автономное действие

AGENTS.md: «Никаких автономных действий. Система предлагает — автор решает». Real-time update, молча меняющий WorldModel, нарушает это. **M10 обязан быть suggest-only**: находки → очередь → применение только по подтверждению.

### Риск 3: Provenance-контракт

Извлечение из книги ≠ доказанный факт:
- точная дата из книги → AUTHOR_CANON;
- интерпретация («многие века» → CENTURY precision) → уже DERIVED, не AUTHOR_CANON;
- M10 не должен автоматически повышать RECONSTRUCTION-узлы до AUTHOR_CANON без верификации.

### Риск 4: Зависимость «temporal extractor» от mtime-поллинга

Книга 213 KB — чтение+хэш при каждом tick дёшево, но полный парсинг — нет. Нужен mtime→hash→parse каскад (как в Pulse: mtime дёшево, hash точен).

### Риск 5: Повторное чтение и duplicate-находки

Повторный запуск извлечения по неизменённой главе должен давать 0 diff (idempotency), иначе очередь находок растёт бесконечно.

---

## 4. ВЕРДИКТ

### M10 — NEEDS SPECIFICATION (технически готов, спецификация отсутствует)

**Почему не BLOCKED:** ни один из пробелов не требует изменения базовой архитектуры. Все недостающие шаги — это новые модули поверх существующих контрактов:
- mtime-детектор = копия паттерна `Pulse.watch()`;
- temporal extractor = расширение словаря `entity_extractor` (или отдельный модуль в `research/`);
- refresh temporal engine = новая небольшая функция рядом с `enable_temporal()` (не модификация M5, а дополнение);
- применение findings = существующий `apply_findings` + обязательный confirmation-gate.

**Почему не READY:** 2 из 4 шагов отсутствуют, а критические решения (real-time механика, suggest-only vs auto-apply, конфликт provenance) не зафиксированы. Реализовывать без спецификации = scope creep и риск сломать ADR-0001.

---

# SPEC DRAFT — M10 (на утверждение владельцу)

## 1. Goal

При изменении текста книги система обнаруживает изменения и **предлагает** (не применяет автоматически) обновления temporal данных WorldModel, с соблюдением provenance-контракта и ADR-0001.

## 2. Scope (minimal)

| Входит | НЕ входит |
|--------|-----------|
| `BookChangeDetector` — mtime+hash детектор `КНИГА.md` (паттерн Pulse.watch) | Авто-применение находок (запрещено ADR) |
| `TemporalExtractor` — извлечение temporal маркеров из изменённого текста (словарь: «до н.э», «N лет/век/тысячелет», названия юг/эпох) | LLM-извлечение (заглушки Research Engine не трогаем) |
| `TemporalFinding` — находка с provenance (AUTHOR_CANON для прямых утверждений, DERIVED для интерпретаций) | Новые API endpoints (кроме одного опционального, см. ниже) |
| Очередь находок + подтверждение человеком (suggest-only) | Frontend/UI |
| `WorldEngine.refresh_temporal()` — пересоздание temporal engine из обновлённого WorldModel | Изменение M3/M5/M8 алгоритмов |
| ~12 тестов | M11+ |
| | Real-time websocket-пуш уведомлений |

Опционально (по вашему решению): `GET /book/temporal/pending-updates` — список неподтверждённых находок (read-only, для прозрачности).

## 3. Data flow

```
КНИГА.md (изменён)
  → BookChangeDetector (mtime → hash → подтверждение изменения)
  → TemporalExtractor (только по changed-фрагменту текста)
  → list[TemporalFinding]  (каждая: value, source_line, provenance)
  → pending queue (in-memory, НЕ применена)
  → [подтверждение человека: apply_findings → WorldModel.save()]
  → WorldEngine.refresh_temporal()  (пересоздание из нового WorldModel)
  → temporal graph актуален
```

## 4. Provenance contract

| Находка | Категория |
|---------|-----------|
| Прямая дата из книги («~4000 лет до н.э.») | AUTHOR_CANON |
| Относительное время, распознанное правилом («многие века» → CENTURY) | DERIVED (не AUTHOR_CANON!) |
| Обновление существующего EXTERNAL_SOURCE узла canon'ом | canon выигрывает, но исходный tag сохраняется в notes |

Инварианты (все из M1–M9 сохраняются):
- `AUTHOR_CANON ≠ автоприменён` — находка становится canon'ом только после подтверждения;
- `DERIVED ≠ AUTHOR_CANON`;
- `confidence не повышает provenance`.

## 5. Dependency graph

```
research/temporal_extractor.py   →  КНИГА.md (чтение, read-only)
                              →  narrative_engine.source_levels (типы)
research/change_detector.py    →  pathlib (mtime/hash), без зависимости от temporal
world_engine.refresh_temporal() →  существующий TemporalReconstructionEngine.from_world_model
НОВЫХ зависимостей в pulse/ нет. Циклов нет (все стрелки → narrative_engine).
```

## 6. Тестовый контракт (~12)

1. `test_detect_book_change_mtime` — mtime изменился → детектор срабатывает
2. `test_detect_no_change_no_finding` — файл не менялся → 0 findings (idempotency)
3. `test_extract_absolute_date` — «~4000 лет до н.э.» → finding с AUTHOR_CANON
4. `test_extract_relative_period` — «многие века» → finding с DERIVED
5. `test_extract_no_temporal_text` — обычный текст → 0 findings
6. `test_findings_not_applied_automatically` — после извлечения WorldModel НЕ изменён
7. `test_apply_after_confirmation` — подтверждение → WorldModel.save() вызван
8. `test_refresh_temporal_rebuilds` — refresh_temporal() создаёт НОВЫЙ engine instance
9. `test_refresh_temporal_idempotent_when_no_change` — WorldModel не менялся → engine тот же
10. `test_canon_not_downgraded` — существующий AUTHOR_CANON узел не понижен
11. `test_derived_not_promoted` — DERIVED finding не становится AUTHOR_CANON
12. `test_m8_m9_regression_untouched` — M8/M8.1/M9 тесты проходят без изменений

## 7. DoD

- [ ] `BookChangeDetector` + `TemporalExtractor` + `TemporalFinding` реализованы
- [ ] Findings складываются в pending queue, auto-apply отсутствует физически
- [ ] `WorldEngine.refresh_temporal()` пересоздаёт engine из обновлённого WorldModel
- [ ] 12 тестов проходят; 186 temporal + 38 M9 regression проходят
- [ ] M8/M8.1/M9 код не изменён (кроме добавления `refresh_temporal` рядом с `enable_temporal`)
- [ ] Provenance-контракт подтверждён тестами 10–11

## 8. Открытые вопросы для владельца (решение до реализации)

1. **Real-time механика:** polling `watch()`-стиль (дёшево, прецедент есть) vs FastAPI background task? — **Рекомендую polling**: тот же паттерн, что Pulse, без новых фоновых сервисов.
2. **Место подтверждения:** только тесты/CLI (minimal) vs API endpoint `pending-updates` (transparent)? — **Рекомендую без endpoint в M10.1**, добавить в M10.2 по необходимости.
3. **Гранулярность извлечения:** вся книга при изменении vs только diff-фрагмент? — **Рекомендую вся книга** при изменении (213 KB — дёшево), diff-фрагменты — оптимизация на потом.

---

## FINAL STATUS

**M10 — NEEDS SPECIFICATION**

Технических блокировок нет. Спецификация (SPEC DRAFT выше) подготовлена и ждёт вашего утверждения или правок. Реализация не начнётся до явного подтверждения.

Ответы на 3 открытых вопроса в разделе 8 ускорят старт, но я могу принять рекомендации по умолчанию, если вы согласны.
