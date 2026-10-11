# MD-3.2 Route D — BASELINE (зафиксировано ДО миграции)

**Дата фиксации:** 2026-09-12 14:43 (локальный снапшот, TestClient + mock-провайдер + dependency_overrides — точно как тест-среда)

## Endpoint + request contract (неизменны)

```
POST /book/assets/generate-context
  chapter: int (>=1, required) · scene_id: str (required)
  time_of_day: "dawn" · generator: "comfyui" · size: "1024x576"
  reader_id: None · epoch_id: None (MD-2)
POST /book/assets/generate-character   (character_id, time_of_day, generator, size, reader_id)
POST /book/assets/generate-location    (location_id, time_of_day, generator, size, reader_id)
```
Auth: editor-role (test-override). 400 от валидатора на неизвестного персонажа.

## Response contract — фактический снапшот (200)

```
data (29 ключей): asset_id · asset_type · audio · book_id · camera · chapter ·
  characters · composition · created_at · duration_sec · error · file_path · fps ·
  generation · intent · mood · objects · palette · prompt_used · reader_id ·
  scene_id · shots · status · style · symbols · thumbnail_path · title ·
  transition · updated_at

status: "completed"
prompt_used: "cinematic fantasy, epic film still, dramatic lighting,
  Конфликт: Гиперборея vs Материальный путь Атлантиды, ancient гран..."
  (= PromptComposer(comfyui).compose_pair(ctx)[0] — БЕЗ изменения после миграции)
generation: {provider: "mock", model: "sdxl", size: "1024x576", seed: None,
  steps: 30, quality: "standard", negative_prompt: ["blurry, low quality, ..."]}
camera: {shot_type: "medium", angle: "eye_level", movement: "static"}
mood: "конфликт" · style: "cinematic_fantasy" · characters: []
file_path: "images/asset_<timestamp>.png"
```

## Семантика (что должен воспроизводить мигрированный путь)

1. SceneContext строится `visual_ctx_builder.build_scene_context(chapter, scene_id, time_of_day, epoch_id)` (MD-2, без изменений);
2. валидация VisualValidator (400-контракт при ошибках);
3. промпт = composer.compose_pair (текст ЗАМОРОЖЕН — сравнение byte-identical после миграции);
4. asset-запись создаётся с projection полей ctx (title/mood/style/palette/camera/characters);
5. провайдер вызывается через generate_with_metadata(prompt, size, preferred_provider=generator);
6. asset.generation заполняется фактическим ответом провайдера (provider_name) — Response-модель VisualAsset НЕ меняется (29 ключей);
7. сохранение файла + status COMPLETED/FAILED — прежняя механика.

## Что относится к MediaPlan vs ExecutionDispatch (решение по приказу)

| Параметр | Классификация |
|----------|---------------|
| prompt/negative (текст) | MediaPlan (prompt, negative_constraints) |
| size | ExecutionDispatch (execution-размер кадра; НЕ поле плана) |
| generator (preferred_provider) | ExecutionDispatch (выбор провайдера; НЕ поле плана) |
| time_of_day / epoch_id / chapter / scene_id | SceneContext-вход (уже там, MD-2) |
| reader_id | asset-метаданные (вне плана — пользовательский контекст) |
| generation.model/steps/seed/quality | legacy-поля VisualAsset-ответа (НЕ переносятся в план; живут в response до MD-3.3+) |

## Baseline-тесты (57 passed до миграции)

test_md2_routes.py: TestRouteDGenerateContext ×4 + TestMD2RouteInvariants ×2 (D-затрагивающие: prompt без execution-утечек; canonical extras) + A/B/C/E ×9 — НЕ должны измениться.
test_md3_media_plan.py: 40. test_visual_assets_provider_chain.py: 27 (pipeline-интеграции).
