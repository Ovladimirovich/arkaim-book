# LEGACY: `core/WORLD/` — происхождение и статус

> Статус: **DOCUMENTED / LEGACY (не используется активным кодом).**
> Решение владельца: каталог **сохранить**; архивирование или удаление — **только по явному OWNER-GO**.

## Что это такое

`core/WORLD/` — каталог с тремя JSON-файлами «сырого» графа сущностей, связей и цитат книги:

| Файл | Размер | Содержимое |
|------|--------|------------|
| `core/WORLD/entities.json` | ~17 КБ | 46 сущностей (поля: `id`, `name`, `type`, `description`, `aliases`, `attributes`, `first_mention_chapter`) |
| `core/WORLD/relations.json` | ~3 КБ | 12 связей между сущностями |
| `core/WORLD/quotes.json` | ~11 КБ | 18 цитат (поля: `id`, `text`, `chapter_id`, `paragraph_id`, `char_start/end`, `entities_mentioned`, `themes`, `context`) |

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

Каталог **не отслеживается git** — исключён в обоих `.gitignore`:

- `core/.gitignore:36` — `WORLD/`
- корневой `.gitignore:74` — `core/WORLD/`

Поэтому файлы существуют только локально и не попадают в коммиты/CI.

## Кто использует (аудит)

**Активный код каталог не читает.** Проверено поиском по репозиторию:

- Нет импортов и обращений к `core/WORLD/entities.json`, `relations.json`, `quotes.json`.
- `core/CORE/book_os/entity_store.py` и `relationship_store.py` читают другой путь — `OS_DATA/graph/`, а не `core/WORLD/`.
- World Engine работает с `core/CORE/WORLD_MODEL/*.json` и `core/CORE/narrative_engine/data/WORLD_MODEL.json`, а не с `core/WORLD/`.

Ссылки на `core/WORLD/` встречаются только в документации (перечислены выше).

## Как это НЕ путать

В проекте сосуществуют похожие по названию сущности — их важно не смешивать:

| Что | Путь | Назначение |
|-----|------|------------|
| **`core/WORLD/`** (этот каталог) | `core/WORLD/*.json` | **legacy**, сырой граф, не используется кодом |
| World Model (World Engine) | `core/CORE/WORLD_MODEL/*.json` | рабочие категории мира, собираются `scripts/build_world_model.py` |
| Narrative World Model | `core/CORE/narrative_engine/data/WORLD_MODEL.json` | модель мира для Narrative Engine |
| Book OS граф | `core/CORE/book_os/OS_DATA/graph/*.json` | хранилище сущностей/связей Book OS |

## Что делать дальше (предложение, не действие)

Варианты на решение владельца (без выполнения без OWNER-GO):

1. **Оставить как есть** — задокументировано, ничего не ломается, каталог локальный и git-ignored.
2. **Архивировать** — перенести в `docs/archive/` или отдельный `legacy/` с пометкой происхождения.
3. **Удалить** — только если подтверждено, что данные не нужны как источник миграции.

Автоматические действия (архивирование/удаление) **не выполняются**.
