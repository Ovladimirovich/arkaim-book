# TEMPORAL API ALIGNMENT — INDEPENDENT FORENSIC AUDIT (B1 + C1)

**Дата:** 2026-09-09
**Объект:** этап TEMPORAL API ALIGNMENT (B1: `/book/temporal/nodes` + temporal_today; C1: `/book/temporal/chain` canonical provenance якоря)
**Метод:** read-only. Независимое чтение кода, собственные live-запросы (не скрипт этапа), собственные прогоны тестов, git/mtime-доказательства, AST-анализ media-зависимостей. Отчёт реализации как доказательство НЕ принимался.
**Инструменты аудита:** `arkaim-web-v2/scripts/forensic-audit-temporal.mjs` (35 проверок), `forensic-audit-fixes.mjs` (MEDIA.1 прицельно), `forensic-reg1.mjs` (REG.1 с корректным auth-контрактом).

---

## ВЕРДИКТ

# PASS WITH FINDINGS

B1+C1 корректны, инварианты подтверждены собственными live-проверками и тестами; границы этапа доказаны (2 исходника). Отложенные архитектурные findings зафиксированы (C2-фабрика AUTHOR_CANON + один новый для C2-этапа вопрос order-ссылки). Ни один не делает этап неприемлемым; все требуют отдельного решения.

---

## Простыми словами

1. **Цель аудита** — независимо проверить выравнивание публичного API «времени мира» с каноническим движком M8.1, не веря отчёту этапа на слово.

2. **Что проверено** — я прочитал код сам, поднял сервер сам, провёл свои 40+ живых проверок и сам прогнал 335+ тестов; сравнил границы файлов по датам и git.

3. **Результат** — всё заявленное подтвердилось: «Современность» появляется как точка наблюдения без единой связи; у якоря Аркаима — честные метки происхождения; запретная связь «Современность→Аркаим» нигде не создана; ось эпох не изменилась (12/11); C2 действительно не делался; API остаётся полностью независимым от media-бэкендов (ни одного упоминания ComfyUI/изображений/видео в temporal-контрактах).

4. **Findings** — два отложенных (оба известного класса): фабрика рёбер помечает связи эпох как «авторский канон», что по ADR должно быть «производным» — исправление требует отдельного C2-этапа (сейчас менять запрещено); и вопрос трактовки флага у второй сущности ArkaimAnchor — тоже на C2. Серьёзных проблем нет.

5. **Дальше** — предлагаю принять этап как закрытый; findings внести в C2-решение. F3 не начинался и без вашего решения не начнётся.

---

## 1. Scope

Аудит этапа B1+C1 (разрешённый владельцем scope: только `/nodes` + today; `/chain` + canonical enrichment якоря; C2 — НЕ реализовывать). Проверка ADR-соответствия (A–D), C2-finding, regression boundary, live verification, future media-architecture compatibility. Запрещённое в аудите — не выполнялось: ни C2, ни правки provenance/relations, ни Present→Arkaim, ни World Model/M10.2/F3/Media-проектирование, ни рефакторинг PromptBuilder, ни фиксы старых падений.

## 2. Evidence (независимые источники)

| Источник | Что дал |
|----------|---------|
| Код `runtime/core/routes/temporal.py` (прочитан целиком, 261 строка) | B1: `list_nodes` добавляет `TemporalNode.present_anchor().to_dict()` (210-211); C1: `_enrich_canonical_anchor` (51-75) — источник `ArkaimAnchor.from_existing_data()`, дедуп по category, confidence=0.85; вызов в `get_temporal_chain` (93-94) |
| Код движка (сверка зеркальности) | `reconstruction_engine.py:579-595` (enrichment+дедуп+0.85), `:606-608` (today после эпох), `node.py:133-152` (present_anchor HYPOTHESIS), `arkaim_anchor.py:70-97` (КНИГА.md/ARCHAEOLOGY.json) |
| Live (собственный backend uvicorn :8642) | 35 проверок forensic-audit-temporal.mjs (33 PASS ядро + 2 уточнённые: REG.1 reader-путь, MEDIA.1 прицельно по 14 temporal-путям и схемам — PASS) |
| Тесты (собственные прогоны) | 116 (alignment+routes+M8.1+M10+M10.2) + 219 (model/reconstruction/integration/M5/M8/M9) = **335 passed, 0 failed** |
| Git/mtime | Ровно 2 исходника после 09:00; canonical `WORLD_MODEL.json` нетронут (16.07.2026, tracked, без M); tracked-дифф 39 = pre-existing база (identity/visual/AB-testing/M10-серия; map/page.tsx+GenerationSettings — из той же базы) |
| AST-анализ | `core/CORE/narrative_engine/temporal/*.py` + `routes/temporal.py`: 0 media/comfy/image/video/audio/visual/provider импортов |

## 3. B1 verification — PASS (9/9)

| Проверка | Результат | Evidence |
|----------|-----------|----------|
| `/nodes` возвращает temporal_today | ✅ | live: total=13, id=temporal_today присутствует |
| today = методологическая точка наблюдения, не epoch | ✅ | provenance=[{category:HYPOTHESIS, source_level:SYSTEM_INTERPRETATION, notes:"methodological anchor for temporal reconstruction — not book canon"}]; precision=EXACT; era_id="" |
| today не имеет временных связей | ✅ | (а) `/reconstruct` today→arkaim_era: paths_found=0; (б) во всех chain-рёбрах today не участвует; (в) today не входит ни в FORWARD, ни в BACKWARD chain |
| Порядок и состав исторической оси не изменились | ✅ | 12 эпох в исходном порядке; ось в /nodes — та же; today добавлен последним (canonical order движка) |
| Сегодня ровно один | ✅ | ids.count('temporal_today')==1 |
| Нет дубля-anchor | ✅ | temporal_arkaim_anchor отсутствует (D-принцип) |
| Confidence 1.0 (наблюдение, не интерпретация) | ✅ | today.confidence==1.0 |
| Bounds корректны | ✅ | 2025 CE..2025 CE |
| is_anchor=false | ✅ | today не претендует на роль якоря оси |

## 4. C1 verification — PASS (10/10)

| Проверка | Результат | Evidence |
|----------|-----------|----------|
| Оба направления возвращают канонический якорь | ✅ | FORWARD и BACKWARD: temporal_arkaim_era в chain |
| Provenance = AUTHOR_CANON + EXTERNAL_SOURCE | ✅ | категории live: ["AUTHOR_CANON","EXTERNAL_SOURCE"] |
| Источники — те же, что движок | ✅ | КНИГА.md (CANON 1.0) + ARCHAEOLOGY.json (HISTORICAL 0.7) — байт-в-байт `ArkaimAnchor.from_existing_data()` |
| Confidence = 0.85 | ✅ | как reconstruction_engine.py:595 |
| Дедуп по категории (не дублирует теги) | ✅ | ровно 2 тега, без повторов; код 67-72 зеркален движку 591-594 |
| Enrichment только для arkaim_era | ✅ | остальные 11 узлов: provenance=[], confidence=0.8 (не тронуты) |
| Ось не изменилась | ✅ | 12 узлов / 11 PRECEDES / stats совпадают |
| Present→Arkaim не появился | ✅ | ни одно ребро (обе стороны) не содержит temporal_today |
| Форма ответа сохранена | ✅ | ok/data/stats, 400 на INVALID, 404 на /node |
| Эффект идемпотентен и локален | ✅ | мутация только read-time dict; данные не меняются |

## 5. ADR compliance — PASS (4/4 + расхождения)

| Решение ADR | Факт кода/live | Вердикт |
|--------------|----------------|---------|
| **A. TODAY** = temporal_today, HYPOTHESIS, observation point, БЕЗ relations | node.py:133-152 (present_anchor), routes B1, live-проверки B1.1-9 | ✅ соответствует |
| **B. Ось только PRECEDES; FORWARD/BACKWARD = traversal** | live: FORWARD ≡ BACKWARD по множеству рёбер (одинаково отсортированные source→target — один и тот же набор); все 11 — PRECEDES; REVERSE_RELATIONS только для чтения | ✅ соответствует |
| **C. Provenance = category + confidence** | ProvenanceTag(category, confidence) повсюду; якорь [AUTHOR_CANON 1.0, EXTERNAL_SOURCE 0.7]+0.85; today [HYPOTHESIS 1.0] | ✅ соответствует (для узлов; см. §6 — рёбра расходятся) |
| **D. Canonical anchor = temporal_arkaim_era; ArkaimAnchor — не graph entity** | arkaim_era: is_anchor=true, обогащён; temporal_arkaim_anchor отсутствует в /nodes и /chain; ArkaimAnchor остаётся dataclass-источником provenance | ✅ соответствует |

**Расхождения, зафиксированные за пределами B1+C1 (все — для C2-этапа):**
- **(i) ~~Рёбра оси несут AUTHOR_CANON от фабрики `precedes()`~~ → C2 исправлено: теперь DERIVED** (relation.py:186-201) — ADR Decision C-п.2 предписывает рёбрам DERIVED/RECONSTRUCTION. Исправлено на этапе C2 (2026-09-16).
- **(ii) `ArkaimAnchor.to_node()` (arkaim_anchor.py:55-66) создаёт TemporalNode с `is_anchor=True`** — метод остаётся в dataclass-коде. Он не вызывается никаким graph-путём (движок его не использует: enrichment идёт напрямую из provenance-полей), поэтому второй graph-entity НЕ возникает. Но это «заряженный» метод: если какой-то будущий код вызовет его и добавит результат в граф — получим G3-двойственность заново. Finding: рассмотреть дезактивацию/пометку deprecated в C2-этапе (сейчас НЕ менять).
- **(iii) `/node/{epoch_id}` и `/context/{epoch_id}` по-прежнему без enrichment** (расхождение API/engine сохраняется для одиночных узлов; вне scope B1+C1 — владелец разрешал только /nodes и /chain). Зафиксировано как deferred-элемент: либо выравнять в будущей итерации, либо зафиксировать как осознанную границу.

## 6. C2 finding — исправлен на этапе C2 (2026-09-16) ✅

**Ранее (пред-существующее):** фабрика `TemporalRelation.precedes(source_id, target_id)` (relation.py:186-201) жёстко создавала тег `AUTHOR_CANON @ CANON, confidence=1.0, notes="temporal precedence — from epoch ordering"` для каждого ребра оси. Это поведение M2.

**Исправление C2:** категория заменена на `DERIVED @ SYSTEM_INTERPRETATION`, notes обновлены на "temporal precedence — derived from epoch ordering in canon". Тесты обновлены:
- `test_precedes_is_canon_from_epoch_order` → `test_precedes_is_derived_from_epoch_order`
- `test_canon_preserved` → `test_canon_not_promoted_by_precedes` (AUTHOR_CANON nodes + DERIVED relation → path = HYPOTHESIS, не AUTHOR_CANON)
- `test_temporal_relation_still_works`: `is_canon=True` → `is_canon=False`, добавлена проверка DERIVED

**Статус:** ✅ C2 IMPLEMENTED. Все 167 целевых тестов проходят.

**Классификация:** это **semantic/data-contract issue**, а не только косметика:
- ADR Decision C-п.2: рёбрам оси предписаны DERIVED/RECONSTRUCTION; AUTHOR_CANON для ребра «порядок эпох» семантически завышен — порядок выведен из canon-данных (epoch.order), а не утверждён текстом напрямую;
- канон-статус даёт ребру максимальный вес доверия («никто не может переписать»), что блокирует любые будущие правки порядка (например, подтверждённые M10.2-находки об эпохах) — фактически замораживает ось;
- при этом сами данные рёбер физически не «существуют» отдельно: они создаются фабрикой на лету обоими построителями (WorldModel.get_temporal_chain и engine.from_world_model) — значит исправление возможно как изменение фабрики (одна точка), без миграции данных.

**Реализовано на C2 (2026-09-16):**
1. ✅ Заменена категория в `precedes()` на DERIVED @ SYSTEM_INTERPRETATION (notes: "temporal precedence — derived from epoch ordering in canon")
2. Тесты обновлены: `test_precedes_is_canon_from_epoch_order` → `test_precedes_is_derived_from_epoch_order`, `test_canon_preserved` → `test_canon_not_promoted_by_precedes`
3. Скрипты `temporal-alignment-live.mjs` и `forensic-audit-temporal.mjs` обновлены на проверку DERIVED

**Остаётся отложенным (не блокирует C2):**
- (ii) `ArkaimAnchor.to_node()` — deprecated-пометка (low risk, не вызывается)
- (iii) `/node/{epoch_id}` enrichment — выравнять в будущей итерации

## 7. Regression verification — PASS

| Группа | Собственный прогон |
|--------|--------------------|
| Alignment-тесты этапа | 19/19 (в составе 116) |
| `test_temporal_routes.py` (M5-маршруты) | 41 passed |
| `test_m8_1_present_anchor.py` | 32 passed (канонический эталон) |
| `test_m10_temporal_updates.py` + `test_m10_2_pending_updates_api.py` | 48 passed |
| `test_temporal_model/reconstruction/integration + m5 + m8_future + m9_expansion` | 219 passed |
| **Итого независимо** | **335 passed, 0 failed** |

Pre-existing/environmental (вне этапа, проверено содержимым): auth-migrations (WinError 5 sandbox rmtree), metrics (legacy-тест ×FastAPI 0.141 `_IncludedRouter`), integrations/crowdfunding (sqlite readonly в песочнице). Live `/metrics`=200; M10.2 live: reader 200 на /pending-updates, 403 на /scan (гейты целы).

## 8. Git boundary — PASS

- **Исходники этапа (mtime > 09:00):** ровно `runtime/core/routes/temporal.py` [09:37] + `runtime/tests/test_temporal_api_alignment.py` [09:43]. Ничего больше (core/CORE, legacy frontend, arkaim-web-v2/src, tests-директории — 0 файлов).
- **Tracked-дифф:** 39 M-файлов — все из pre-existing базы предыдущих аудитов (сверка по списку: identity-sanitizer, visual/AB-testing, world_engine/world_model M-серия, map/page.tsx+GenerationSettings, main.py huggingface-удаление — историческое). Ни один не имеет mtime этого этапа.
- **Canonical data:** `WORLD_MODEL.json` (28 KB, единственный источник эпох) — mtime 16.07.2026, tracked, статус чист. Enriched-каталоги/GENOME-workflows — runtime-артефакты сервера (untracked/ignored).
- **M10.2 (`temporal_updates.py`):** не открывался этапом (mtime ранее 09:00), контракты live подтверждены (200/403).
- **core/CORE:** 0 изменений (все temporal-модули — mtime до этапа; WORLD_MODEL.json не тронут).

## 9. Live verification — PASS (40 проверок)

Собственный скрипт (не этапа): `/nodes` (13, today-семантика, порядок), `/chain` FORWARD+BACKWARD (якорь, provenance, источники, 0.85, 12/11, все PRECEDES, today вне, Present→Arkaim отсутствует, FORWARD≡BACKWARD по рёбрам), `/reconstruct` today→arkaim (0 путей), `/pending-updates` (reader 200; scan 403), future-extrapolation (401 без сессии — жив), OpenAPI (14 путей ровно, 0 новых/утерянных). Два исходных FAIL моей проверки оказались дефектами проверки, не этапа (REG.1 — неверный формат регистрации; MEDIA.1 — слишком широкий grep-охват), оба переуточнены до PASS с корректными контрактами.

## 10. Future Media Architecture compatibility — PASS (architectural check only)

Проверка цели: B1+C1 не должны создавать скрытой зависимости Arkaim от конкретного media backend (Book → World Model → Temporal Context → Scene Context → Media Plan → внешний Media-проект).

| Проверка | Результат | Evidence |
|----------|-----------|----------|
| temporal API остаётся media-agnostic | ✅ | OpenAPI 14 temporal-путей: 0 упоминаний comfy/workflow/image/video/audio/prompt_builder/sdxl/checkpoint/generation/render/texture/mesh/lod (прицельный проход по путям + схемы ReconstructRequest/ExtrapolateRequest/RejectRequest/HTTPValidationError) |
| temporal entities/context не завязаны на ComfyUI | ✅ | AST: 13 модулей `core/CORE/narrative_engine/temporal/*.py` — 0 media-импортов; `routes/temporal.py` импортирует только narrative_engine/auth/pydantic/fastapi |
| Нет workflow/node/model-specific полей | ✅ | Node/relation-поля: id/label/precision/era_id/entity_ids/event_ids/provenance/confidence/bounds/notes/is_anchor — доменно-временные, ни одного media-поля |
| Arkaim не должен знать, каким backend генерируется media | ✅ | temporal-модуль не знает ни о ComfyUI, ни о Media Plan; направление зависимости обратное: будущий Media Plan → потребляет temporal через read-only контракты (/chain, /nodes, /context) |
| Scene Context/будущий Media Plan смогут использовать temporal без ломки модели | ✅ | Media Plan сможет строиться поверх существующих доменных контрактов: /context/{epoch_id} уже отдаёт узел+события+персонажей+технологии; новые B1/C1-поля (today, provenance) — аддитивные read-only данные; для branching не требуется ничего: provenance/confidence уже несут «вес доверия», которого хватит Media Plan'у для выбора эпохи-сценария |
| B1+C1 не требуют media-ветвления в core сейчас | ✅ | 0 изменений вне temporal-роутов; никакого image/video/audio кода не добавлено и не потребуется |

**Архитектурный gap (finding/deferred, НЕ запрос на реализацию):** отсутствует формальный Scene Context → Media Plan контракт (существует prompt_builder для визуала M7.2 в другом домене — вне temporal). Это осознанная граница текущей архитектуры, не дефект B1+C1: когда Media Plan будет проектироваться, temporal-информация доступна ему через media-agnostic API как есть. Зафиксировано как deferred architectural item (без действия).

## 11. Findings

| # | Severity | Локация | Суть | Impact | Действие |
|---|----------|----------|------|--------|----------|
| TA-1 | **Medium → ✅ IMPLEMENTED (C2, 2026-09-16)** | `relation.py:186-201` (`TemporalRelation.precedes()`) | ~~Фабрика рёбер оси штампует AUTHOR_CANON~~ → исправлено: DERIVED @ SYSTEM_INTERPRETATION. Миграция не нужна (рёбра read-time); legacy-UI метки рёбер не рендерит (проверено) | Semantic/data-contract: исправлено; порядок эпох теперь корректно маркирован как DERIVED | C2 завершён. TA-2/TA-3 остаются deferred |
| TA-2 | **Low (deferred)** | `arkaim_anchor.py:55-66` (`to_node()`) | Метод dataclass создаёт TemporalNode с is_anchor=True — «заряженный» источник возможного будущего дубля-anchor. Сейчас не вызывается (движок enrichment использует provenance напрямую) — второй graph-entity не возникает | Latent: будущий вызов воссоздал бы G3-двойственность | В C2: рассмотреть дезактивацию/deprecated-пометку; сейчас НЕ менять |
| TA-3 | **Low (documentation/decision)** | `/node/{epoch_id}`, `/context/{epoch_id}` | Одиночные узлы всё ещё без enrichment (расхождение с движком сохранено для них) — осознанный предел scope B1+C1 | Консистентность API: единичные узлы беднее chain; F3-UI следует брать узлы из /chain или /nodes, либо потребует будущей итерации | Зафиксировать: либо расширить alignment в будущей итерации, либо объявить границей. Решение владельца |
| TA-4 | **Informational (deferred architectural, не дефект этапа)** | Архитектура Media Plan | Scene Context → Media Plan контракт не существует; temporal остаётся готовым источником для него (media-agnostic подтверждён) | Никакого немедленного | Никакого действия; при проектировании Media Plan использовать существующие temporal-контракты как есть |
| TA-5 | **Informational (environment)** | Песочница DSH | sqlite-readonly у community-тестов, WinError-5 у auth-migrations, legacy metrics-тест ×FastAPI 0.141 — вне этапа, падали бы и без него | Никакого на этап | CI-среда подтвердит; вне scope |

**Критических/High findings НЕТ.** TA-1 — единственный Medium, и он пред-существующий, известный (задокументирован этапом как C2-finding), аудитом подтверждён и классифицирован как требующий решения в C2, не блокирующий закрытие B1+C1: этап не создал и не усугубил его, а его исправление прямо запрещено scope'ом.

## 12. Final verdict

**PASS WITH FINDINGS**

- Заявления этапа подтверждены независимо и полностью (B1: 9/9; C1: 10/10; инварианты: все; регрессия: 335/335 независимо; live: 40/40 после уточнений; границы: доказаны).
- ADR A–D соответствуют фактическому коду; расхождения за пределами этапа зафиксированы (§5-iii, §6).
- C2-finding подтверждён и правильно отложен: семантический долг фабрики precedes() — реальный, но пред-существующий; его исправление требует отдельного C2-этапа (проект изменений готов, реализация запрещена).
- Media-совместимость: temporal API полностью media-agnostic; скрытых зависимостей от ComfyUI нет; B1+C1 не требуют media-ветвления.

**Этап B1+C1 корректен и может быть закрыт. Отложенные findings (TA-1/TA-2/TA-3) — для C2-решения. F3 не начат.**

---

**STOP GATE:** аудит read-only — ничего не исправлено, не реализовано, не начато. Ни C2, ни F3, ни правки provenance/relations/World Model/M10.2, ни Media-проектирование. Останавливаюсь и жду решения владельца.

---

## 7. C2 follow-up (2026-09-16) ✅

C2 реализован: `TemporalRelation.precedes()` помечает рёбра оси как `DERIVED @ SYSTEM_INTERPRETATION` вместо `AUTHOR_CANON @ CANON`. Проверено:
- 19 тестов alignment: PASS
- 209 temporal-тестов: PASS
- 107 core-тестов: PASS
- Все KNOWLEDGE JSON имеют `_provenance_metadata` (enriched_catalog.json + enriched_chunks.json также обёрнуты)
