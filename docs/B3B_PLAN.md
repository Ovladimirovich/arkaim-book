<!-- HISTORICAL-DOCUMENT -->
> [!WARNING]
> **HISTORICAL — НЕ ЯВЛЯЕТСЯ ТЕКУЩЕЙ ИНСТРУКЦИЕЙ ИЛИ SOURCE OF TRUTH.**
> B3-B реализован в `core/CORE/narrative_engine/world_model.py` и `core/CORE/narrative_engine/tests/test_b3b_crosswalk.py`. План ниже описывает состояние до реализации. Актуальный статус: `docs/CURRENT_DEVELOPMENT_STATE.md`.

# B3b — план: заполнить подтверждённые Temporal-связи (entity_ids)

Исторический статус: **PLAN — этот этап был выполнен после получения OWNER-GO.** Фактическое текущее состояние и ограничения определяются `docs/CURRENT_DEVELOPMENT_STATE.md`.

## Простыми словами

**Что было целью?** Описать, как безопасно связать сущности World Engine с эпохами Temporal, используя только утверждённые crosswalk-соответствия.

**Что было найдено в коде и данных (факты, не предположения):**
- Temporal-узел строится в `core/CORE/narrative_engine/world_model.py` (`get_temporal_node`). На момент планирования поле `entity_ids` было пустым.
- Цепочка эпох: `get_temporal_chain` → `get_temporal_node` для каждой эпохи.
- Событие (`canonical_events`) содержит явные `epoch` и `location_id` — это надёжная связь «где и когда».
- `Location.epochs_present` у Аркаима и Гипербореи был пустым — на него нельзя было опираться.

**Что можно было утверждать на данных:**
- `region_arkaim` → `аркаим`; событие `event_arkaim_construction` имеет `epoch=arkaim_era`, `location_id=аркаим`. Значит `region_arkaim` подтверждённо связан с эпохой `arkaim_era`.
- `region_hyperborea` → `гиперборея`; события `event_journey_to_hyperborea` и `event_transmission_of_teaching` имеют `epoch=satya_yuga`, `location_id=гиперборея`. Значит `region_hyperborea` подтверждённо связан с эпохой `satya_yuga`.

**Суть B3b:** заполнять `entity_ids` temporal-узла только на основе approved crosswalk + реальных canonical events. Никаких новых соответствий, никаких выводов по названию, никаких правок `WORLD_MODEL.json`.

## Историческая область B3b

- Единственная точка изменения: `get_temporal_node` в `core/CORE/narrative_engine/world_model.py`.
- Разрешено заполнять `entity_ids` только значениями `we_id` из approved crosswalk
  (`core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`, `status=APPROVED`).

## Область, которую менять нельзя

- Расширять crosswalk самостоятельно.
- Менять `core/CORE/WORLD_MODEL/*.json`, `core/CORE/narrative_engine/data/WORLD_MODEL.json`, `MAP_DATA.json`.
- Менять UI/Temporal/World до отдельной необходимости.
- Заполнять `entity_ids` по совпадению названий или через пустой `epochs_present`.

## Алгоритм

Для заданного `epoch_id`:
1. Взять только approved mappings crosswalk.
2. Найти canonical events, у которых `epoch == epoch_id`.
3. Собрать уникальные `location_id` этих событий.
4. Сопоставить `location_id` с `target_id` approved mappings.
5. Если совпало — добавить `we_id` в `entity_ids` (уникально, отсортированно).
6. Если совпадений нет — оставить `entity_ids` пустым.

Ожидаемый и фактический результат:
- узел `arkaim_era`: `entity_ids = ["region_arkaim"]`.
- узел `satya_yuga`: `entity_ids = ["region_hyperborea"]`.
- остальные 10 узлов: остаются `[]`.

## Критерии приёмки

- Unit-тесты backend подтверждают ровно эти два заполненных узла и пустые остальные.
- Ни одно другое поле temporal-узла не изменилось.
- Ни один JSON данных не изменён.
- UI не менялся.
- Ruff / pytest зелёные для затронутых файлов.

## Фактическая verification-история

- `test_b3b_crosswalk.py` подтверждает две approved-связи и отсутствие автоматических выдумок.
- Контрольный прогон 2026-10-01: **8/8 passed** для B3-B и World provenance core-тестов.