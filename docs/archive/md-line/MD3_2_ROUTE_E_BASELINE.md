# MD-3.2 Route E — BASELINE (зафиксировано ДО миграции)

**Дата фиксации:** 2026-09-12 22:00 (TestClient + spy-провайдер + изолированная film-БД `.tmp_md32e/`; скрипт-снимок удалён после фиксации).

## Endpoint + request contract (неизменны)

```
POST /book/film/{project_id}/scenes/{scene_db_id}/shots/{shot_id}/generate
  (SuccessResponse; auth: базовая reader-зависимость роутера)
  query: style?: str (переопределение стиля) · mood?: str · quality?: draft|standard|high|ultra
```

## Response contract — фактический снапшот (200)

```
data: ровно 4 ключа {asset_id, file, shot_id, status}
status: "completed" · asset_id: asset_<ts> · file: <rel_path>
```
Побочный эффект: shot в film-БД обновляется (asset_id, status=completed, prompt=asset.prompt_used, duration/camera при переданных).

## Фактический исторический промпт (shot.prompt="test shot", проект cinematic_fantasy)

```
cinematic fantasy, epic film still, dramatic lighting, test shot
```
SHA256[:16] = `3287ab6c88314433`. Формула (при custom_prompt): `STYLE_PRESETS[asset.style], custom_prompt` — если у стиля ЕСТЬ префикс в словаре; иначе — просто `custom_prompt`.

**Уточнённые baseline-факты (проверено двумя прогонами):**
- Дефолт (стиль проекта cinematic_fantasy): «cinematic fantasy, epic film still, dramatic lighting, test shot» → SHA `3287ab6c88314433`.
- style="mythic_realism" (НЕТ в STYLE_PRESETS-словаре визуал-пайплайна): префикс пуст → промпт = «test shot» → SHA `53a10b4f48714232`. Стиль влияет на текст ТОЛЬКО через известные словарю значения (finding: словари стилей разрознены — Route C-STYLE_PRESETS знает mythic_realism, pipeline-STYLE_PRESETS НЕТ; pre-existing, вне scope).
- **mood НЕ влияет на текст** (dead для промпта — тот же паттерн, что Route C).
- **quality НЕ влияет ни на текст, ни на execution** (запись в asset.generation.quality — dead для провайдера, MP-F1-семья).

## Shot fields / camera / duration / negative — dead-поля (BASELINE FACT, подтверждено кодом)

**MD-3 forensic-факт подтверждён на коде (film_studio.py:330-365):**
- `shot.camera` (CameraSpec шота) — **НЕ передаётся** в pipeline.generate_image: в вызов идут только (chapter, scene_id, overrides, custom_prompt, scene_context). Camera шота остаётся в film-БД (showcase-поле ответа), на генерацию не влияет.
- `shot.duration_sec` — **НЕ передаётся** (не в overrides, не в аргументы): остаётся в БД-поле шота; pipeline генерирует ИЗОБРАЖЕНИЕ (asset_type=IMAGE), длительность к нему не применяется.
- `shot.negative_prompt` (если задан) — **НЕ передаётся**: negative строится pipeline'ом из asset-модели (build_negative_prompt), поле шота не читается.
- Параметры запроса `style/mood/quality`: style → overrides["style"] → asset.style → префикс промпта через STYLE_PRESETS пайплайна (только для известных словарю стилей); **mood → overrides["mood"] → asset.mood НЕ применяется** (pipeline берёт emotion сцены — dead-паттерн Route C); **quality → overrides["generation"]["quality"] → asset.generation.quality** (запись, до провайдера НЕ доходит — dead для execution, MP-F1-семья).

**Вывод: до execution реально доходят ТОЛЬКО: prompt, size (1024x576|1024x1024 по aspect_ratio проекта), preferred_provider="comfyui"** (spy-доказательство: generate_with_metadata(prompt, size, preferred_provider="comfyui")). Camera/duration/negative шота — dead/showcase (не доходят до pipeline) — **не исправлять в MD-3.2** (GO п.4).

## Provider/runtime path (spy-доказательство)

```
shot = film-БД (get_scene → versions → id)         # 404 если нет шота
project = film-БД (get_project)                    # 404 если нет проекта
update_shot(status="generating")
chapter = parse из scene.scene_id ("scene_N" → N, иначе 1)
overrides = {style: style|project.style, mood: mood|project.mood, provider:"comfyui",
             generation:{size: 1024x576|1024x1024, quality?}}
custom_prompt = shot.prompt (если есть)
ctx = build_scene_context(chapter, scene.scene_id)  # MD-2 canonical (уже)
asset = pipeline.generate_image(chapter, scene.scene_id, overrides, custom_prompt, ctx)
  → scene-exists → ValueError → 500 (маршрут E: НЕ ловит ValueError → 500 "Generation failed")
  → prompt = STYLE_PRESETS[style], custom_prompt | build_asset_prompt(asset)
  → provider.generate_with_metadata(prompt, size, preferred_provider="comfyui")
update_shot(asset_id, status=completed, prompt=asset.prompt_used, …)
→ {asset_id, file, shot_id, status}
```

## Семантика ошибок (сохранить)

| Вход | Ответ |
|------|-------|
| unknown scene_db_id / shot_id / project_id | **404** (Scene/Shot/Project not found) |
| шот для НЕсуществующей genome-сцены (unknown_scene_id) | **500** "Generation failed: Scene not found…" (ValueError пайплайна; как в HEAD/MD-2-тесте) |

## Baseline-тесты (существующие)

test_md2_routes.py::TestRouteEFilmShotGenerate: test_film_shot_generate_contract (200/completed/asset_id) · test_film_shot_generate_unknown_scene_fails (500) — зелёные (57P; изолированная БД film_test_*.db — паттерн без F-12).
