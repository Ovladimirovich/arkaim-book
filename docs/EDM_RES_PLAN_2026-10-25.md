# EDM-RES — поэтапный план реализации (roadmap, 2026-10-25)

> Статус: **рабочий план (engineering artifact)** — переводит результаты
> аудита и правил в последовательность phases с OWNER-gates. Сам по себе
> код не меняет и публичные контракты не затрагивает.
>
> Исходники: `docs/EDM_RES_PILOT_2026-10-25.md` (интеграционный контур),
> `docs/ENTITY_RESOLUTION_AUDIT_2026-10-25.md` (аудит механизмов),
> `docs/ENTITY_RESOLUTION_RULES_2026-10-25.md` (семантика: intents §3,
> R1–R4/C1–C6/D1–D4 §4, Tier-1/Tier-2 связи + v1-батч §4.4, STOP GATE S1–S5 §7).

## 0. Простыми словами

1. **Что сделано (фаза 0, CLOSED).** EDM-каталог и «живой» пилот:
   5 пилотных + 8 examples EDM-карточек; EDM подключён к `/book/ask` и
   `/visualize` за выключенным флагом (выключен = ответы точно как раньше,
   проверено); аудит автоматического разрешения сущностей (read-only) и
   дизайн-документ правил разрешения с кандидатным набором из 10 связей.
   Всё это закоммичено (`aedd13e…15e19a3`), 45 EDM-тестов + регрессии зелёные.
2. **Что дальше (фазы 1–4).** Сначала — решения владельца (GATE A: S1–S4).
   Потом — инженерная привязка правил (W1–W4, код только внутри пилотных
   швов, флаг остаётся выключен). Потом — GO на флаг (GATE B: S5) + live
   проверка. И только потом — расширения (каталог, авто-матчинг,
   каталог-сцены) — каждое со своим отдельным GO.
3. **Что НЕ входит.** Новый LLM-резолвер, изменение семантики
   provenance без GO, массовая миграция слоёв, любые публичные
   контракты до GATE B.

## 1. Карта phases

| Фаза | Назначение | Кто | Gate | Критерий выхода |
|---|---|---|---|---|
| **0** | База: пилоты, аудит, правила | инженер | CLOSED | закоммичено, тесты зелёные |
| **1** | Решения S1–S4 (GATE A) | OWNER | **CLOSED 2026-10-25** | решения зафиксированы в §7 правил |
| **2** | W1–W4 wiring + Tier-2 батч | инженер | — (после GATE A) | unit + regression, контракты byte-identical при flag off — **DONE 2026-10-25** |
| **3** | GO на флаг S5 (GATE B) + live e2e | OWNER | **GO дан 2026-10-25** (применяется после фазы 2) | флаг on в `.env`, live-проверка задокументирована |
| **4** | Расширения E1–E5 (каждое — свой GO) | инженер + OWNER | OPEN | см. §6 |

Порядок строгий: `0 → 1 → 2 → 3 → 4`. GATE A (S1–S4) **CLOSED
2026-10-25** — все четыре решения OWNERом утверждены (подписи в
`docs/ENTITY_RESOLUTION_RULES_2026-10-25.md` §7). S5 GO дан тем же
решением: включение `EDM_RES_PILOT_ENABLED=true` выполняется в фазе 3,
после завершённой фазы 2 (W1–W4 + регрессии) — подтверждённое решение
владельца от 2026-10-25: «GO на флаг приостановлено до утверждения правил
и wiring'а W1–W4». Фаза 4 стартует только отдельным GO.

## 2. Фаза 0 — фактический срез (CLOSED)

| Артефакт | Коммиты | Состояние |
|---|---|---|
| Аудит описательных знаний (6 слоёв, fail-open дефолты, G10) | `aedd13e` | DOCUMENTED+TESTED |
| EDM v0.1: пилот 5 сущностей (extended_world→EDM), round-trip | `105f774` | TESTED (24 теста `test_edm_pilot.py`) |
| EDM v0.2: schema + resolver (`resolutions.py`), операции | `53a31c8`, `1d7e0d4` | TESTED |
| EDM-RES: швы `/book/ask` + `/visualize` за флагом | `10f635e` | TESTED (21 тест `test_edm_res_pilot.py`) |
| Аудит entity resolution (5 механизмов, ID-пространства, live-probes) | `9eb5e73` | DOCUMENTED |
| Правила разрешения (S1–S5 + v1-батч из 10 связей) | `15e19a3` | DOCUMENTED, **ждёт GATE A** |

Факты (live, 2026-10-25): флаг `EDM_RES_PILOT_ENABLED` выключен;
45 EDM-тестов + регрессионный батч зелёные; в production-движке
(13 категорий, 503 сущности) **ноль** типизированных связей — связи
живут только в legacy-модели и EDM-карточках.

**Решения владельца, уже зафиксированные (decision log):**
- двухуровневая модель разрешения (Entity + Context) принята 2026-10-25
  (замена «приоритета типов»);
- политики вида «архитектура важнее географии» — НЕ принимаются
  (правила §4.1, закреплено OWNERом);
- GO на флаг `EDM_RES_PILOT_ENABLED` — приостановлен до GATE A + W1–W4;
- **GATE A CLOSED 2026-10-25:** S1 (таблица intents §3) — утверждаю;
  S2 (бандл N=4, порядок §4.1, explicit gap) — утверждаю; S3 (v1-батч
  10 связей, включая #10 `associated_with`) — утверждаю целиком; S4
  (дубль `arkaim`/`region_arkaim`) — утверждаю, сохранить обе;
  S5 — GO: `EDM_RES_PILOT_ENABLED=true` после W1–W4 (фаза 3).

## 3. Фаза 1 — GATE A: решения S1–S4 (вход OWNERа)

Один артефакт для ревью: `docs/ENTITY_RESOLUTION_RULES_2026-10-25.md` §7.

| # | Вопрос | Варианты | Что влияет |
|---|---|---|---|
| **S1** | Таблица intents §3 (10 типов + приоритет I2) | утвердить / поправить состав | W1 (intent-функция) |
| **S2** | Политика неоднозначности: бандл (не форс-выбор), N=4, порядок §4.1, explicit gap §4.5 | утвердить / изменить лимит или формулировки | W2 |
| **S3** | v1-батч из 10 связей §4.4 (включая спорную #10 `associated_with` 0.7) | утвердить целиком / поэлементно / отклонить | состав Tier-2 записей (W4) |
| **S4** | Дубль «Аркаим»: `arkaim` (examples master-card) vs `region_arkaim` (pilot) — обе location | сохранить обе (порядок §4.1) / слить / назначить роли | порядок бандлов §5.1 |

Формат решения: по каждому S1–S4 — «утверждаю / утверждаю с правками
(какими) / отклоняю». При поэлементном S3 — перечислить утверждённые
номера. **Код на этой фазе не меняется**; результат записывается в §7
правил + decision log §2. GATE A закрыт, когда все четыре строки имеют
решение.

## 4. Фаза 2 — W1–W4: инженерная привязка правил (без GATE)

Полный spec — §6 правил-документа; ниже — декомпозиция с тестами.
Инварианты фазы: **флаг остаётся off**; публичные контракты
byte-identical legacy; мир не мутируется; новый resolver не создаётся;
всё — фильтрация существующих полей и детерминированные функции.

### W1 — intent-извлечение (по S1)

- Новая чистая функция в `runtime/core/services/` (helper рядом с
  существующими сервисами): вопрос → intent по таблице §3 правил
  (10 типов, приоритет I1–I4). Ничего LLM, детерминировано.
- **Тесты:** новые unit-тесты (напр. `runtime/tests/test_edm_intent.py`):
  каждое из 10 intents на формулировках §5 правил + ложные срабатывания
  («Расскажи про мир» ≠ intent `about` на конкретную сущность и т.п.).

### W2 — фильтр кандидатов (по S2)

- `/book/ask`: `resolve_related_entities` (уже отдаёт `entity_type`) →
  группировка по типам intent (§3/§4.1) → R1–R4 → бандл (N≤4, порядок
  §4.1) → существующий strict-match `edm_pilot.match_entities(
  explicit_ids=бандл)`. Fuzzy отсутствует по конструкции.
- **Тесты:** бандл «Аркаим» (N=4, ровно лимит D2), single, gap,
  `about`-бандл; все 4 строки §5.1 правил воспроизводятся на реальных данных.

### W3 — отбор claims (C1–C6)

- Фильтры над СУЩЕСТВУЮЩИМИ полями EDM-карточек (§1.3 правил):
  C1 known+canon/external, C2 reconstructed, C3 medium, C4 required_unknown,
  C5 hidden unknown, C6 is_reconstruction. Не новая схема — фильтрация.
- **Тесты:** по каждому C-правилу позитив/негатив + M1 (провенанс
  `edm:<id>` у каждой вносившей сущности в бандле).

### W4 — Crosswalk v2.1 `relations` (по S3)

- Секция `relations` в `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`
  (schema §4.4 правил): `{id, source_id, relation, target_id, provenance,
  status: APPROVED, owner_reviewed: true, evidence[]}`.
- Записываются **только утверждённые OWNERом** связи из v1-батча
  (S3-решение; отклонённые остаются Tier-1 гипотезами, B3).
- Loader `_load_approved_relations()` по образцу
  `_load_approved_crosswalk()` (fail-closed при отсутствии); G6-политика
  на отношения.
- **Тесты:** расширение `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`
  (схема relations) + read-only контракт в
  `runtime/tests/test_g11_typed_resolver_contract.py`.

### MP-1 (опционально, отдельный микро-GO) — casefold-баг

Живой баг из аудита §3.2: «Аркаим» (natural case) → ложный
`CROSSWALK_UNAPPROVED` в `WorldKnowledgeResolver`, тогда как engine
находит сущность casefold'ом. Фикс = casefold запроса перед
crosswalk-lookup. Это изменение **семантики статусов** резолвера
(не публичный контракт, но меняет поведение) → отдельное решение
владельца (микро-GO), реализация — минимальная + тест. Не входит в
W1–W4 и не блокирует фазу 2.

### Выход фазы 2 (все четыре W-шага)

- Unit-тесты W1–W4 зелёные; целевой прогон: `test_edm_pilot.py`
  + `test_edm_res_pilot.py` + `test_b3b_crosswalk.py`
  + `test_g11_typed_resolver_contract.py` (45 EDM-тестов на входе);
- Регрессионный батч флага-off (98 тестов из RES-пилота) зелёные;
- byte-identity публичных контрактов при флаге off подтверждена
  (SHA-промпт /visualize + отсутствие ключа `edm` в /book/ask);
- Отчёт: DONE / VERIFIED / PROBLEMS / STOP GATE = CLOSED, GATE B готов.

### Фаза 2 — фактический срез (DONE, 2026-10-25)

| W-шаг | Артефакт | Состояние |
|---|---|---|
| W1 `extract_intent` | `runtime/core/services/edm_context.py` (таблица intents §3, приоритет I2, fallback I3; намерение — только из вопроса I4, без LLM) | IMPLEMENTED+TESTED |
| W2 `select_bundle` | тот же модуль: R1–R4, бандл N=4 (D2), порядок §4.1 (approved → engine/pilot → examples → id asc), explicit gap B2, fallback §5.4, era-special (time.epoch_ref), context-only §4.2 | IMPLEMENTED+TESTED |
| W3 `filter_claims` | тот же модуль: C1 (known + утверждённые provenance-классы), C2, C3 (art-model: dialogue «визуальный образ (допущение)» / visual «с меткой»), C4 (required_unknown), C5 (скрытие), C6 (card-level флаг) | IMPLEMENTED+TESTED |
| W4 `approved_relations` | обёртка fail-closed над `_load_approved_relations` (crosswalk v2.1, 10 owner-утверждённых связей; сбой — пусто, B1) + связывание Tier-2 в бандл и в EDM-блок с провенансом | IMPLEMENTED+TESTED |
| Wiring пилота | `edm_pilot.build_edm_dialogue_block` (уровень 1: related_entities engine + точные имена каталога + явные ids → уровень 2 → claims), `entity_sources()` (pilot/examples ранги), `/book/ask` передаёт `related_entities`; flag off — `None` (legacy) | TESTED |

Тесты: `runtime/tests/test_edm_context.py` (28: W1–W3 + W4 fail-closed +
интеграция с реальным каталогом) + `test_edm_res_pilot.py` (21, включая
byte-identity flag-off) + `test_b3b_crosswalk.py` (11) — зелёные.
Provenance EDM-блока: C-правило у каждого claim + Tier-2 связи
(`owner_reviewed` из кросскока). Флаг `EDM_RES_PILOT_ENABLED` остаётся
выключенным — включение = GATE B (фаза 3), GO владельцем уже дан 2026-10-25
и применяется после этой фазы.

## 5. Фаза 3 — GATE B (S5): включение флага + live e2e

- **Решение:** `EDM_RES_PILOT_ENABLED=true` в `runtime/.env`
  (конфиг окружения, не код).
- **Live-проверка после включения:**
  - `/book/ask` «Что такое Аркаим?», «Климат степи…» — блок `edm`
    (entities, слоистый dialogue, provenance-таблица);
  - `/visualize` с явными `edm_entity_ids` — MediaPlan с EDM-значениями,
    `weather/season = UNKNOWN` (не fail-open), `edm:<id>` в source_refs;
  - авто-матчинг с несовпадающими claims → ctx не мутирован
    (SHA-идентичность legacy).
- **Фиксация:** результаты live-проверки записываются в
  `docs/EDM_RES_PILOT_2026-10-25.md` (обновление статусов),
  регрессионный батч перезапускается с флагом on. Выход: GATE B CLOSED.

## 6. Фаза 4 — расширения (каждое — отдельный OWNER-GO)

| # | Расширение | Что делает | GO |
|---|---|---|---|
| **E1** | Увеличение EDM-каталога | Персонажи (Велик и др. — группы NameResolver), каталог-сцены, недостающие локации; генерация pipeline'ом + round-trip-отчёт (как v0.1) | состав карточек — артефакт владельца |
| **E2** | Расширение авто-матчинга | RAG/локационный матчинг (аудит §5.1(c): location-строка → engine/crosswalk → `region_*` → EDM); закрывает ограничение «авто-матчинг по location на реальных данных не реализуется» | затрагивает production-швы |
| **E3** | Каталог-сцены `/visualize` | Обойти ограничение `chapter ge=1` / `CATALOG_CHAPTER=0` (изв. ограничение RES-пилота) | изменение DTO-контракта |
| **E4** | Массовая миграция слоёв + default флага | full слои extended_world → EDM; `EDM_RES_PILOT_ENABLED` по умолчанию true (или снятие флага) | смена default production-поведения |
| **E5** | Расширение approved crosswalk | сверх 3 mappings (напр. `steppe_climate`) на другие категории | артефакт утверждается только владельцем (G6) |

Порядок рекомендуемый: E1 → E2 → E3 → E4 (E5 может идти параллельно
E1 по решению владельца). Каждая фаза E: spec → owner GO → реализация →
тесты → live-проверка → фиксация в docs. Автономного запуска нет.

## 7. Инварианты и контроль рисков (действуют во всех фазах)

| Инвариант | Контроль |
|---|---|
| Мир не мутируется (resolver чистый, ctx-only мутации) | layer-isolation e2e тесты (`test_edm_res_pilot.py`) |
| unknown/gap не материализуется (B1: fail-closed) | W3-тесты C4/C5 + e2e «UNKNOWN вместо clear» |
| Флаг off = публичные контракты byte-identical | SHA-промпт /visualize + отсутствие ключа `edm` (regression batch) |
| Нет нового LLM-резолвера | W1–W3 — чистые детерминированные функции, unit-тесты |
| Tier-1 → Tier-2 только OWNER-решением (P1, G6) | W4-схема: `owner_reviewed: true`, `evidence[]`; отклонённые остаются Tier-1 (B3) |
| Расширение crosswalk «по ходу» не допускается | W4 — одна секция v2.1 + test-gates; E5 — отдельный GO |

## 8. Статус

| Item | Статус |
|---|---|
| Фаза 0 (пилоты, аудит, правила) | CLOSED |
| Фаза 1 GATE A (S1–S4) | CLOSED 2026-10-25 (решения в §7 правил) |
| Фаза 2 W1–W4 | **DONE 2026-10-25** (`edm_context.py` + wiring + 28 тестов; slice §4) |
| MP-1 casefold-микрофикс | open, отдельный микро-GO, не блокирует фазу 2 |
| Фаза 3 GATE B (S5) | READY — фаза 2 завершена, GO на флаг дан 2026-10-25 (включение + live e2e) |
| Фаза 4 E1–E5 | запланирована, не запускается автоматически |