# B3-CW — Proposed Crosswalk: World Engine и WorldModel

> [!WARNING]
> **HISTORICAL / REFERENCE — список кандидатов на дату первого батча.**
> Силу имеет только approved crosswalk `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`.
> С тех пор изменилось:
> - одобрено **3** соответствия (`region_arkaim`, `region_hyperborea`, `region_oceania`), а не 2;
> - canonical ID — language-agnostic stable (`owner_decision: language_agnostic_stable_ids`),
>   а не «русские canonical ID»;
> - crosswalk **подключён к runtime**: `entity_ids` временных узлов заполняются из approved mappings,
>   Temporal и World UI читают эти ID («Runtime connections: 0» ниже — историческая формулировка);
> - EN-дубли (`arkaim`, `hyperborea`) удалены, 7 регионов MAP_DATA остаются несопоставленными (гейт G6).
> Текущая карта: `docs/CURRENT_DEVELOPMENT_STATE.md`.

Статус: **APPROVED / B3-CW FIRST BATCH**.

Approved artifact: `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`.
Он не подключён к runtime, не заполняет `entity_ids`, не подключается к Temporal или World UI.

## Простыми словами

**Что было целью?** Определить минимальный формат crosswalk и найти небольшую группу соответствий, которые можно подтвердить данными проекта, а не похожими названиями.

**Что реально сделано?**
- Проверены World Engine, внешний картографический слой и канонический WorldModel.
- Проверены связи канонических событий с локациями и главами.
- Определён минимальный формат crosswalk.
- Найдены два сильных кандидата для проверки владельцем.
- Явно отделены сущность, эпоха и событие.
- Runtime, API, Temporal и UI не изменялись.

**Что получилось?** **APPROVED для первого малого набора.** Владелец выбрал русские canonical ID: `аркаим` и `гиперборея`. Два соответствия зафиксированы в отдельном approved artifact с evidence; runtime пока не изменён.

**Есть ли проблемы?** Да, ограниченная. Английские дубликаты `arkaim` и `hyperborea` отклонены как неавторитетные. Остальные 520 сущностей по-прежнему нельзя автоматически сопоставлять. Сущность, эпоха и событие также не могут быть смешаны в одном ID.

**Что предлагается дальше?** Не подключать crosswalk автоматически. Отдельная задача B3b должна использовать только approved mappings, заполнить подтверждённые связи в Temporal и отдельно получить OWNER-GO.

## Минимальный формат crosswalk

```json
{
  "schema_version": "1.0",
  "status": "PROPOSED",
  "mappings": [
    {
      "id": "cw_001",
      "we_id": "region_arkaim",
      "we_type": "world_engine_entity",
      "target_id": "arkaim",
      "target_type": "canonical_location",
      "relation": "same_subject",
      "status": "CANDIDATE",
      "evidence": [
        {
          "type": "world_engine_source",
          "file": "core/CORE/WORLD_MODEL/GEOGRAPHY.json",
          "notes": "source MAP_DATA.json; WE id region_arkaim"
        },
        {
          "type": "external_source",
          "file": "core/KNOWLEDGE/MAP_DATA.json",
          "notes": "id arkaim, name Arkaim, coordinates 52.98, 59.57"
        },
        {
          "type": "canonical_location",
          "file": "core/CORE/narrative_engine/data/WORLD_MODEL.json",
          "notes": "location id arkaim, name Arkaim, name_ru Аркаим"
        }
      ],
      "confidence": "MEDIUM",
      "review_required": true
    }
  ]
}
```

Обязательные признаки формата:
- отдельный ID самого соответствия;
- ID из каждого пространства;
- тип цели и тип отношения;
- явный статус;
- массив evidence;
- флаг проверки владельцем.

## Первый проверочный набор

### 1. `region_arkaim`

**Кандидат:** `arkaim` как canonical location.

**Доказательства:**
- World Engine: `region_arkaim`, `source: MAP_DATA.json`.
- Внешний источник: `core/KNOWLEDGE/MAP_DATA.json` содержит `id: arkaim`.
- World Engine: координаты 52.98, 59.57.
- Внешний источник: те же координаты.
- Canonical WorldModel: `location.id: arkaim`, `name: Arkaim`, `name_ru: Аркаим`.

**Почему пока CANDIDATE, а не CONFIRMED:**
- в World Engine нет поля `canonical_location_id`;
- в canonical WorldModel есть второй объект `location.id: аркаим`;
- `MAP_DATA.json` не ссылается на canonical ID.

**Решение владельца:** выбран авторитетный ID `аркаим`. Mapping `region_arkaim -> аркаим` имеет статус APPROVED; английский `arkaim` отклонён как дубликат.

### 2. `region_hyperborea`

**Кандидат:** `hyperborea` как canonical location.

**Доказательства:**
- World Engine: `region_hyperborea`, `source: MAP_DATA.json`.
- Внешний источник: `core/KNOWLEDGE/MAP_DATA.json` содержит `id: hyperborea`.
- Canonical WorldModel: `location.id: hyperborea`, `name_ru: Гиперборея`.

**Почему пока CANDIDATE:**
- в World Engine нет явного canonical link;
- в canonical WorldModel есть второй объект `location.id: гиперборея`;
- событие `event_journey_to_hyperborea` указывает на `location_id: гиперборея`.

**Решение владельца:** выбран авторитетный ID `гиперборея`. Mapping `region_hyperborea -> гиперборея` имеет статус APPROVED; английский `hyperborea` отклонён как дубликат.

## Связи, подтверждённые внутри canonical WorldModel

Это явные связи, но не связь с World Engine.

### `event_arkaim_construction`

- `epoch`: `arkaim_era`.
- `location_id`: `аркаим`.
- `chapter`: 11.
- `source_level`: CANON.

Событие относится к эпохе и локации по прямым полям. Но это не доказывает связь с `region_arkaim`.

### `event_journey_to_hyperborea`

- `epoch`: `satya_yuga`.
- `location_id`: `гиперборея`.
- `chapter`: 3.
- `source_level`: CANON.

Путешествие связано с canonical локацией `гиперборея`. Но это не доказывает связь с `region_hyperborea`.

## Обязательное разделение типов

```text
region_arkaim
arkaim
аркаим
arkaim_era
event_arkaim_construction
```

- `region_arkaim` — сущность World Engine.
- `arkaim` и `аркаим` — candidate canonical locations.
- `arkaim_era` — эпоха, не локация.
- `event_arkaim_construction` — событие, не локация и не эпоха.

Допустимые типы связей:

```text
WE entity --same_subject--> canonical location
canonical location --related_to--> canonical event
canonical event --occurs_in--> canonical epoch
WE entity --related_to--> canonical event
```

Совпадение названия не является доказательством тождества.

## Отложенные записи

| WE ID | Статус | Причина |
|---|---|---|
| `region_gardarika` | NOT_CONFIRMED | Внешний источник содержит `gardarika`, но явного canonical location ID нет |
| `region_sintashta` | NOT_CONFIRMED | Не найден подтверждённый canonical location ID |
| остальные 520 WE entities | NOT_CHECKED_IN_FIRST_BATCH | Намеренно начат с малого проверочного набора; 2 кандидата и 2 явно отложенные записи рассмотрены |

## Итог B3-CW

- Approved mappings в первом batch: **2**.
- Approved artifact: `core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json`.
- Runtime connections: **0**; `entity_ids`, Temporal и UI не изменялись.
- Неподтверждённых сущностей: **520**.
- B3b и B4: **заблокированы до нового OWNER-GO**.

Следующий шаг — отдельная задача B3b, которая использует только approved mappings и получает собственный OWNER-GO перед изменениями данных.
