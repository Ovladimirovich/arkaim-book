# MD-3.2 Route C — BASELINE (зафиксировано ДО миграции)

**Дата фиксации:** 2026-09-12 21:37 (TestClient + spy-провайдер + dependency_overrides; скрипт-снимок удалён после фиксации).

## Endpoint + request contract (неизменны)

```
POST /book/assets/generate          (SuccessResponse; auth: editor)
  chapter: int >=1 (required) · scene_id: str (required)
  asset_type: "image"|"video" ("image")
  style: "cinematic_fantasy" · mood: "neutral" · provider: "auto"
  reader_id: None · size: "1024x1024" · negative_prompt: "" 
  quality: "standard" (pattern draft|standard|high|ultra)
```

## Response contract — фактический снапшот (200)

```
data: asset-модель, 29 ключей (как Route D) · status: "completed"
prompt_used: <legacy build_asset_prompt(asset)>
generation: {provider: "mock"(spy)/"auto", model: "sdxl", size: <size-param>, seed: None,
             steps: 30, quality: <quality-param>, negative_prompt: [<negative_prompt> or []]}
```

## Фактический исторический промпт (дефолт-параметры)

```
cinematic fantasy, epic film still, dramatic lighting, Конфликт: Гиперборея vs
Материальный путь Атлантиды, конфликт, symbolic elements: конфликт:гиперборея,
конфликт:материальный_путь_атлантиды, cinematic lighting, highly detailed,
intricate details, epic composition, atmospheric
```
SHA256[:16] = `e5e41db21768c86e` (дефолт). С style="mythic_realism", mood="трепет" → другой текст (SHA `29443ace06ff8894`) — style/mood ВЛИЯЮТ на промпт (STYLE_PRESETS + mood-строка).

## Provider/runtime path (spy-доказательство)

```
ctx = build_scene_context(chapter, scene_id)             # MD-2 canonical (уже)
pipeline.generate_image(chapter, scene_id, overrides, scene_context=ctx):
  scene-exists check (SceneEngine) → ValueError → 404
  scene-проекция из ctx (MD-2) → asset-модель (style/mood из overrides)
  prompt = build_asset_prompt(asset)                     # LEGACY (visual_assets/prompt_builder.py)
  negative = build_negative_prompt(asset)
  provider.generate_with_metadata(prompt, size=size, preferred_provider=provider)
  → файл → COMPLETED
```
**До execution реально доходят:** prompt, size, preferred_provider (через generate_with_metadata); asset.generation = {provider, size, quality, negative_prompt[...]} (записывается в asset-модель).

## Классификация параметров Route C (по GO-приказу п.3)

| Параметр | Класс | Куда |
|----------|-------|------|
| chapter, scene_id | смысловые идентификаторы | SceneContext (уже) |
| style, mood | СМЫСЛОВЫЕ (влияют на текст промпта: STYLE_PRESETS, mood-строка) | MediaPlan (visual_style/atmosphere) — но исторический текст строится из asset-модели; см. ниже |
| negative_prompt | смысловой (что НЕ рисовать) | MediaPlan.negative_constraints (уже есть); до провайдера — через dispatch |
| provider | EXECUTION (выбор генератора) | ТОЛЬКО ExecutionDispatch.preferred_provider; НЕ в план |
| size | EXECUTION (размер кадра) | ТОЛЬКО ExecutionDispatch.size; НЕ в план |
| quality | EXECUTION (dead — MP-F1; owner: НЕ оживлять) | НЕ в план, НЕ оживляется; остаётся как есть в legacy-asset-модели до MD-3.3+ |
| reader_id | asset-метаданные | вне плана |
| asset_type | смысловой (вид медиа) | MediaPlan.media_kind (image/video) |

## Семантика ошибок (сохранить)

| Вход | Ответ |
|------|-------|
| chapter=99 | **404** "Scene not found: chapter=99, scene_id=nope" |
| корректная сцена, asset_type=video | 200 + asset(video), но generation падает с pre-existing ошибкой `'VideoProviderChain' object has no attribute 'health'` → asset.status="failed" (pre-existing defect, ВНЕ scope — зафиксирован) |

## Baseline-тесты (существующие)

test_md2_routes.py::TestRouteCGenerateAsset: test_generate_image_contract · test_generate_404_unknown_scene — зелёные (57P).
test_visual_assets_provider_chain.py (27P) — pipeline-интеграции.
