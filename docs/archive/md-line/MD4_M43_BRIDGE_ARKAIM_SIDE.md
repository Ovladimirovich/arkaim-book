# MD-4 M4.3 — MediaClient Bridge — IMPLEMENTATION REPORT (Arkaim side)

**Дата:** 2026-09-13
**Статус:** IMPLEMENTED + TESTED + VERIFIED
**Мандат:** owner-GO на последовательность MD-4 (M4.3; MD4_PRE §15, Вариант A)
**Полный отчёт:** `arkaim-media/docs/MD4_M43_MEDIA_CLIENT_BRIDGE_REPORT.md`
**Arkaim commit:** `81612b7` · **Media commit:** `5922dcc`

## Простыми словами

1. **Цель:** мост Аркаим→Media-проект за DI (единая точка подмены adc_deps) + env MEDIA_BACKEND_URL.
2. **Сделано:** `runtime/core/media_client.py` (мост: image/video/health, R2-обязательства); `runtime/core/adc_deps.py` (DI-подмена: мост первый в цепи при env, локальная цепь — fallback ниже; без env — прежняя цепь); `runtime/tests/test_md4_m43_media_client.py` (14 тестов).
3. **Результат:** PASS. Гейт MD4_PRE §15 «134/134 MD-3 с моком» — **134/134**. Визуальный чанк 62/62, temporal 70/70, arkaim-media 114/114.
4. **Проблемы:** нет блокирующих; 2 известных расхождения зафиксированы в полном отчёте (§6), не чинятся без owner-решения.
5. **Дальше:** M4.4 — живой прогон 5 маршрутов через Media-сервис с byte-гейтом (owner-approved последовательность).

## Изменения в Аркаиме (3 файла)

| Файл | Изменение |
|---|---|
| `runtime/core/media_client.py` | НОВЫЙ: MediaClient-мост (TEMPORARY MIGRATION BRIDGE, REMOVE IN MD-5) |
| `runtime/core/adc_deps.py` | `_factory_image_provider`/`_factory_video_provider`: env-ветка MEDIA_BACKEND_URL (мост первым, локальная цепь fallback) |
| `runtime/tests/test_md4_m43_media_client.py` | НОВЫЙ: 14 тестов (unit моста 8, DI 3, роуты R2 2, MD-3-гейт сквозь мост 1) |

## Инварианты

- Роуты `/book/comfyui/*`, `/book/providers/*` — 0 изменений; мост удовлетворяет R2 (`_base_url`, `health()`, `providers[0]`, name-механику) — подтверждено тестами.
- 5 маршрутов генерации — не тронуты; MD-3 134/134 зелёные (гейт).
- Обратимость: без `MEDIA_BACKEND_URL` производство работает на локальной цепи (дефолт не изменён).
- Мост — TEMPORARY: умирает в MD-5 вместе с ExecutionDispatch (контракт §0).
