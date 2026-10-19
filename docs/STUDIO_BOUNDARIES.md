# Границы: Film Studio и Studio

> Статус: **DOCUMENTED / ACCEPTED.** Решение владельца: обе подсистемы **сохраняются раздельно**; их БД и роуты **не сливаются**.

## Простыми словами

В проекте есть две близкие, но разные подсистемы работы с медиа:

- **Film Studio** — про **проект фильма**: структура «проект → сцена → шот», сборка видео.
- **Studio** — про **сессию обсуждения**: диалог с системой, варианты, арт-дирекшн, экспорт.

Они делят **общий реестр медиа-файлов** (`visual_assets.db`), но у каждой — своя база данных для своих сущностей. Сливать их БД или роуты нельзя.

## Разделение по ответственности

| | **Film Studio** | **Studio** |
|---|---|---|
| Назначение | Проекты фильма: сцены и шоты, сборка ролика | Сессии: обсуждение, варианты, арт-дирекшн, экспорт |
| Код | `core/CORE/film_studio/` | `core/CORE/studio/` |
| Роуты | `runtime/core/routes/film_studio.py`, монтируются под `/book/film/*` | `runtime/core/routes/studio.py`, префикс `/studio/*` |
| Роль | `editor` (`require_role("editor")`) | зависит от роута |
| Своя БД | `film_studio.db` (`core/CORE/film_studio/store.py`) | `studio.db` (`core/CORE/studio/store.py`): `studio_sessions`, `studio_messages`, `studio_versions`, `studio_references` |
| Основные сущности | проекты, сцены, шоты | сессии, сообщения, версии, референсы |

## Общий реестр медиа

Обе подсистемы ссылаются на **единый реестр медиа-файлов** — `visual_assets.db`
(`core/CORE/visual_assets/storage.py`, класс `AssetStorage`, DI-ключ `asset_store`):

- Film Studio и Studio хранят в своих БД только **ссылки** (`asset_id`) на записи `AssetStorage`, а не сами файлы.
- Пример: `<img>.approved_image_asset_id`, `reference_asset_id` в `studio/session_models.py` и `studio/art_direction.py` указывают на `asset_id` со статусом `completed`.
- Медиа-файлы физически лежат как файлы (`data/visual_assets/...`), метаданные — в `visual_assets.db`.

## Что НЕЛЬЗЯ делать

- ❌ Сливать `film_studio.db` и `studio.db` в одну базу.
- ❌ Объединять роуты `/book/film/*` и `/studio/*` в один модуль.
- ❌ Дублировать реестр медиа — источник файлов всегда `visual_assets.db` (`AssetStorage`).
- ❌ Писать в чужие таблицы напрямую в обход соответствующих `store`.

## Связанные решения

- `docs/ADR/ADR_ARKAIM_MEDIA_BOUNDARY.md` — граница Arkaim ↔ arkaim-media (генерация медиа вынесена наружу).
- `runtime/tests/test_media_boundary.py` — тесты, фиксирующие отсутствие удалённых media-эндпоинтов и текущие границы.
