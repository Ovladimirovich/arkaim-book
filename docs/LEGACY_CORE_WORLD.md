# LEGACY: `core/WORLD/` — происхождение и статус

> Статус: **ARCHIVED (перенесён из `core/WORLD/`, не используется активным кодом).**
> Решение владельца: **архивировать**. Каталог перенесён в
> `docs/archive/subsystems/legacy_core_world/` (см. «Архивация» ниже).

## Что это такое

Три JSON-файла «сырого» графа сущностей, связей и цитат книги (ранее лежали в `core/WORLD/`):

| Файл | Размер | Содержимое |
|------|--------|------------|
| `entities.json` | ~17 КБ | 46 сущностей (поля: `id`, `name`, `type`, `description`, `aliases`, `attributes`, `first_mention_chapter`) |
| `relations.json` | ~3 КБ | 12 связей между сущностями |
| `quotes.json` | ~11 КБ | 18 цитат (поля: `id`, `text`, `chapter_id`, `paragraph_id`, `char_start/end`, `entities_mentioned`, `themes`, `context`) |

Состав `entities.json` по типам: `person` — 30, `location` — 7, `civilization` — 3, `era` — 2, `concept` — 2, `artifact` — 2.

## Происхождение

Это ранний («сырой») граф мира эпохи до появления структурированного World Model. Он упоминается в документах проекта как источник для последующей миграции, но сам по себе является производным (сгенерированным) артефактом, а не авторским каноном.

Подтверждения в репозитории:

- `core/PROJECT_BIBLE/09_BOOK_OS_SPRINT_PLAN.md` (строки 330–332) — план миграции:
  - `WORLD/entities.json → Entity`
  - `WORLD/relations.json → Relationship`
  - `WORLD/quotes.json → Fact (provenance=source)`
- `docs/archive/temporal/M0_ARCHITECTURE_AUDIT.md` (строки 544, 939–940) — описаны как «сырые данные графа сущностей и отношений», отмечен риск «dual/triple source of truth» (`EntityStore`, `RelationStore`, `RelationGraph`).
- `docs/PROJECT_REBASELINE_2026-10-18.md` (строка 47) — прямая формулировка: «`relation_graph` в WorldEngine — ПУСТО; `core/WORLD` (46 сущностей) — legacy».

## Статус в git

Изначально каталог `core/WORLD/` **не отслеживался git** — исключён в обоих `.gitignore`:

- `core/.gitignore:36` — `WORLD/`
- корневой `.gitignore:74` — `core/WORLD/`

Поэтому файлы существовали только локально и не попадали в коммиты/CI.

## Архивация

По решению владельца каталог **архивирован**: файлы перенесены в
`docs/archive/subsystems/legacy_core_world/` (`entities.json`, `relations.json`,
`quotes.json`). Исходный `core/WORLD/` удалён.

Следствие: в `docs/archive/` нет ignore-правил, поэтому архивные файлы **теперь
отслеживаются git** и сохранены в истории репозитория (данные больше не потеряются).
Правила `.gitignore` (`WORLD/`, `core/WORLD/`) оставлены как есть — на новый путь
они не влияют.

## Кто использует (аудит)

**Активный код каталог не читает.** Проверено поиском по репозиторию:

- Нет импортов и обращений к `entities.json`, `relations.json`, `quotes.json` (ни к старому `core/WORLD/`, ни к новому архивному пути).
- `core/CORE/book_os/entity_store.py` и `relationship_store.py` читают другой путь — `OS_DATA/graph/`, а не `core/WORLD/`.
- World Engine работает с `core/CORE/WORLD_MODEL/*.json` и `core/CORE/narrative_engine/data/WORLD_MODEL.json`, а не с `core/WORLD/`.

Ссылки на `core/WORLD/` встречаются только в документации (перечислены выше).

## Как это НЕ путать

В проекте сосуществуют похожие по названию сущности — их важно не смешивать:

| Что | Путь | Назначение |
|-----|------|------------|
| **legacy граф** (этот архив) | `docs/archive/subsystems/legacy_core_world/*.json` | **legacy**, сырой граф, не используется кодом |
| World Model (World Engine) | `core/CORE/WORLD_MODEL/*.json` | рабочие категории мира, номинально собираются `scripts/build_world_model.py` (см. ниже — сборщик неполон) |
| Narrative World Model | `core/CORE/narrative_engine/data/WORLD_MODEL.json` | модель мира для Narrative Engine |
| Book OS граф | `core/CORE/book_os/OS_DATA/graph/*.json` | хранилище сущностей/связей Book OS |

## World Model и сборщик `scripts/build_world_model.py` — статус

> Статус: **DOCUMENTED / INCOMPLETE.** Сборщик **не является источником истины** для `WORLD_MODEL`.

Проверка `python scripts/build_world_model.py --check` (2026-10-19) показала:

| Итог | Значение |
|------|----------|
| same | 0 |
| differ | 4 |
| new | 0 |
| orphan | 9 |

Разбор расхождений:

- **Семантические потери.** `GEOGRAPHY`: файл 38 vs вычислено 17 (теряются 21 сущность,
  напр. `geo_аркаим`, `geo_гиперборея`, `geo_синташта`). `CIVILIZATIONS`: файл 3
  (реальные `civ_hyperborea`, `civ_oceania`, `civ_arkaim_civilization`) vs мусорные
  `civ_type_main`/`civ_type_главные`. `DAILY_LIFE`: файл 3 vs мусорный `daily_topic`.
  У общих записей computed **теряет** поля `provenance_category`, `source_level`,
  `provenance_notes` и ставит `confidence=1.0`.
- **Orphans (9 файлов есть, сборщик их не порождает):** `ARCHITECTURE`, `CLIMATE`,
  `LANGUAGE`, `MYTHOLOGY`, `PHILOSOPHY`, `RELIGION`, `RITUALS`, `TECHNOLOGIES`, `TRANSPORT`.

**Решение владельца:** запуск `--write` **не выполнять** — он удалил бы/испортил данные,
которых в текущем `WORLD_MODEL` (547 сущностей, 13 категорий) существенно больше, чем
воспроизводит сборщик. Скрипт остаётся `--check`-only и не подключён к рантайму.

## Что делать дальше (предложение, не действие)

- Legacy-граф **архивирован** (`docs/archive/subsystems/legacy_core_world/`) — отдельного
  действия не требуется.
- Сборщик World Model: при необходимости когда-либо привести `--write` в соответствие
  реальному `WORLD_MODEL` — отдельная задача; до этого его вывод считать неполным и
  **не** перезаписывать эталонные файлы.

Автоматические действия (перезапись `WORLD_MODEL`) **не выполняются**.
